import AVFoundation
import Foundation
import UIKit

enum CameraMode: String, CaseIterable, Identifiable {
    case objects
    case text

    var id: String { rawValue }

    var title: String {
        switch self {
        case .objects: return "Objects"
        case .text: return "Read Text"
        }
    }

    var systemImage: String {
        switch self {
        case .objects: return "viewfinder"
        case .text: return "text.viewfinder"
        }
    }

    var captureTitle: String {
        switch self {
        case .objects: return "Capture for more detail"
        case .text: return "Capture text for detail"
        }
    }
}

@MainActor
final class CameraViewModel: ObservableObject {
    enum State {
        case loading
        case ready
        case denied
        case unavailable
    }

    @Published private(set) var state: State = .loading
    @Published private(set) var mode: CameraMode = .objects
    @Published private(set) var message = "Preparing camera..."
    @Published private(set) var isCapturing = false
    @Published var detectionResult: DetectionResult?
    @Published var captureError: String?
    @Published private(set) var guidanceMessage = "Preparing live guidance…"
    @Published private(set) var guidanceObject: String?
    @Published private(set) var liveRecognizedText: String?
    @Published private(set) var isGuidanceAvailable = true

    let session: AVCaptureSession

    var canCaptureForMoreDetail: Bool {
        guard state == .ready, !isCapturing else { return false }
        switch mode {
        case .objects:
            return isGuidanceAvailable && guidanceObject != nil
        case .text:
            return true
        }
    }

    var captureButtonTitle: String {
        isCapturing ? "Analyzing…" : mode.captureTitle
    }

    private let service: CameraService
    private let textRecognitionService: TextRecognitionService
    private let audioService = GuidanceAudioService()
    private var hasStarted = false
    private var guidanceTask: Task<Void, Never>?
    private var liveTextTask: Task<Void, Never>?
    private var analysisGeneration: UInt = 0

    private var liveTextCandidateKey: String?
    private var liveTextCandidateCount = 0
    private var consecutiveEmptyTextFrames = 0
    private var lastSpokenTextKey: String?
    private var lastSpokenTextAt = Date.distantPast

    init(
        service: CameraService = CameraService(),
        textRecognitionService: TextRecognitionService = TextRecognitionService()
    ) {
        self.service = service
        self.textRecognitionService = textRecognitionService
        self.session = service.session
    }

    func start() async {
        guard !hasStarted else { return }
        hasStarted = true
        invalidateOngoingAnalysis()
        let startGeneration = analysisGeneration

        do {
            let accessGranted = try await service.prepareSession()
            guard isCurrentStart(startGeneration) else { return }
            if accessGranted {
                state = .ready
                message = "Camera ready"
                guidanceMessage = "Object mode. Searching for an object."
                service.startRunning()
                audioService.speak(
                    "Camera ready. Object mode. Use Read Text at the top to hear visible text live. Tap the bottom to capture more detail.",
                    respectsVoiceSetting: false
                )
                startGuidance()
                startLiveTextRecognition()
            } else {
                state = .denied
                message = "Camera permission was denied."
                guidanceMessage = "Camera access is required."
                guidanceObject = nil
                isGuidanceAvailable = false
                audioService.speak(
                    "Camera access is required. Please allow camera access in Settings.",
                    respectsVoiceSetting: false
                )
            }
        } catch {
            guard isCurrentStart(startGeneration) else { return }
            state = .unavailable
            message = error.localizedDescription
        }
    }

    func stop() {
        invalidateOngoingAnalysis()
        service.stopRunning()
        guidanceTask?.cancel()
        guidanceTask = nil
        liveTextTask?.cancel()
        liveTextTask = nil
        audioService.stop()
        hasStarted = false
        isCapturing = false
        resetLiveTextState()
    }

    func selectMode(_ newMode: CameraMode) {
        guard mode != newMode, state == .ready, !isCapturing else { return }
        invalidateOngoingAnalysis()
        mode = newMode
        audioService.stop()
        resetLiveTextState()
        guidanceObject = nil
        isGuidanceAvailable = true

        switch newMode {
        case .objects:
            guidanceMessage = "Object mode. Searching for an object."
            audioService.speak(
                "Object mode. Point the camera toward an object.",
                respectsVoiceSetting: false
            )
        case .text:
            guidanceMessage = "Read Text mode. Searching for visible text."
            audioService.speak(
                "Read Text mode. Point the camera toward text and hold steady.",
                respectsVoiceSetting: false
            )
        }
    }

    func capture() async {
        guard canCaptureForMoreDetail else { return }
        invalidateOngoingAnalysis()
        let captureGeneration = analysisGeneration
        isCapturing = true
        captureError = nil
        audioService.stop()

        defer {
            if analysisGeneration == captureGeneration {
                isCapturing = false
            }
        }

        do {
            let imageData = try await service.capturePhoto()
            guard isCurrentCapture(captureGeneration) else { return }

            async let detectionAnalysis = try? APIClient.shared.detect(imageData: imageData)
            async let textAnalysis = try? textRecognitionService.recognizeText(
                in: imageData,
                level: .accurate
            )

            let (detectedResult, textResult) = await (detectionAnalysis, textAnalysis)
            guard isCurrentCapture(captureGeneration) else { return }

            guard detectedResult != nil || textResult?.isEmpty == false else {
                throw CaptureAnalysisError.analysisUnavailable
            }

            let baseResult = detectedResult ?? DetectionResult(
                id: nil,
                objectDetected: nil,
                confidence: nil,
                message: "Object detection was unavailable.",
                hints: nil,
                recognizedText: nil,
                persistenceWarning: nil
            )
            var combinedResult = baseResult.includingRecognizedText(textResult?.lines ?? [])

            if let detectionID = combinedResult.id,
               let textResult,
               !textResult.isEmpty {
                do {
                    try await APIClient.shared.saveRecognizedText(
                        detectionID: detectionID,
                        result: textResult
                    )
                } catch {
                    combinedResult = combinedResult.includingPersistenceWarning(
                        "The object scan was saved, but its recognized text could not be added to history."
                    )
                }
            } else if combinedResult.id == nil,
                      let textResult,
                      !textResult.isEmpty {
                do {
                    let textCaptureID = try await APIClient.shared.saveTextCapture(
                        imageData: imageData,
                        result: textResult
                    )
                    combinedResult = combinedResult.includingDetectionID(textCaptureID)
                } catch {
                    combinedResult = combinedResult.includingPersistenceWarning(
                        "The text was recognized, but this scan could not be saved to history."
                    )
                }
            }

            guard isCurrentCapture(captureGeneration) else { return }
            detectionResult = combinedResult
            provideHaptic(.success)
        } catch {
            guard isCurrentCapture(captureGeneration) else { return }
            captureError = error.localizedDescription
            provideHaptic(.error)
        }
    }

    private func startGuidance() {
        guidanceTask?.cancel()
        guidanceTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(1))

            while !Task.isCancelled {
                await self?.requestGuidance()
                try? await Task.sleep(for: .seconds(AppSettingsStore.guidanceInterval))
            }
        }
    }

    private func startLiveTextRecognition() {
        liveTextTask?.cancel()
        liveTextTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(1))

            while !Task.isCancelled {
                await self?.requestLiveTextRecognition()
                try? await Task.sleep(for: .seconds(1))
            }
        }
    }

    private func requestGuidance() async {
        guard mode == .objects,
              !isCapturing,
              let frame = service.latestGuidanceFrame() else {
            return
        }
        let generation = analysisGeneration

        do {
            let result = try await APIClient.shared.guide(imageData: frame)
            guard shouldApplyLiveResult(generation, mode: .objects) else { return }
            let instruction = GuidanceInstruction.message(for: result)
            guidanceMessage = instruction
            guidanceObject = result.objectDetected
            isGuidanceAvailable = true
            audioService.speak(instruction)
        } catch {
            guard shouldApplyLiveResult(generation, mode: .objects) else { return }
            guidanceMessage = "Live object guidance unavailable"
            guidanceObject = nil
            isGuidanceAvailable = false
        }
    }

    private func requestLiveTextRecognition() async {
        guard mode == .text,
              !isCapturing,
              let frame = service.latestGuidanceFrame() else {
            return
        }
        let generation = analysisGeneration

        do {
            let result = try await textRecognitionService.recognizeText(
                in: frame,
                level: .fast
            )
            guard shouldApplyLiveResult(generation, mode: .text) else { return }
            processLiveText(result)
        } catch {
            guard shouldApplyLiveResult(generation, mode: .text) else { return }
            guidanceMessage = "Live text recognition unavailable"
            liveRecognizedText = nil
            isGuidanceAvailable = false
        }
    }

    private func processLiveText(_ result: TextRecognitionResult) {
        let text = result.lines
            .prefix(8)
            .map(\.text)
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        guard !text.isEmpty else {
            consecutiveEmptyTextFrames += 1
            if consecutiveEmptyTextFrames >= 2 {
                liveRecognizedText = nil
                liveTextCandidateKey = nil
                liveTextCandidateCount = 0
                guidanceMessage = "Read Text mode. Searching for visible text."
            }
            return
        }

        consecutiveEmptyTextFrames = 0
        isGuidanceAvailable = true
        let limitedText = String(text.prefix(240))
        let key = normalizedTextKey(limitedText)
        guard !key.isEmpty else {
            guidanceMessage = "Text found. Hold steady."
            return
        }

        if let candidateKey = liveTextCandidateKey,
           textSimilarity(key, candidateKey) >= AppConstants.liveTextSimilarityThreshold {
            liveTextCandidateCount += 1
        } else {
            liveTextCandidateKey = key
            liveTextCandidateCount = 1
        }

        guard liveTextCandidateCount >= AppConstants.liveTextStableFrameCount else {
            guidanceMessage = "Text found. Hold steady."
            return
        }

        liveRecognizedText = limitedText
        guidanceMessage = "Text detected: \(limitedText)"

        let now = Date()
        let matchesLastSpokenText = lastSpokenTextKey.map {
            textSimilarity(key, $0) >= AppConstants.liveTextSimilarityThreshold
        } ?? false
        if !matchesLastSpokenText || now.timeIntervalSince(lastSpokenTextAt) >= 15 {
            audioService.enqueue("Text reads: \(limitedText)")
            lastSpokenTextKey = key
            lastSpokenTextAt = now
        }
    }

    private func normalizedTextKey(_ text: String) -> String {
        text.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: .current)
            .lowercased()
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { !$0.isEmpty }
            .joined(separator: " ")
    }

    private func textSimilarity(_ first: String, _ second: String) -> Double {
        guard first != second else { return 1 }
        guard min(first.count, second.count) >= 5 else { return 0 }

        let firstCharacters = Array(first)
        let secondCharacters = Array(second)
        let editDistance = levenshteinDistance(firstCharacters, secondCharacters)
        let characterSimilarity = 1 - (
            Double(editDistance) / Double(max(firstCharacters.count, secondCharacters.count))
        )

        let firstTokens = Set(first.split(separator: " "))
        let secondTokens = Set(second.split(separator: " "))
        let tokenTotal = firstTokens.count + secondTokens.count
        let tokenSimilarity = tokenTotal == 0
            ? 0
            : Double(2 * firstTokens.intersection(secondTokens).count) / Double(tokenTotal)

        return max(characterSimilarity, tokenSimilarity)
    }

    private func levenshteinDistance(_ first: [Character], _ second: [Character]) -> Int {
        var previous = Array(0...second.count)

        for (firstIndex, firstCharacter) in first.enumerated() {
            var current = [firstIndex + 1]
            current.reserveCapacity(second.count + 1)

            for (secondIndex, secondCharacter) in second.enumerated() {
                let insertion = current[secondIndex] + 1
                let deletion = previous[secondIndex + 1] + 1
                let substitution = previous[secondIndex]
                    + (firstCharacter == secondCharacter ? 0 : 1)
                current.append(
                    min(insertion, min(deletion, substitution))
                )
            }
            previous = current
        }

        return previous[second.count]
    }

    private func invalidateOngoingAnalysis() {
        analysisGeneration &+= 1
    }

    private func shouldApplyLiveResult(_ generation: UInt, mode expectedMode: CameraMode) -> Bool {
        analysisGeneration == generation
            && hasStarted
            && state == .ready
            && mode == expectedMode
            && !isCapturing
            && !Task.isCancelled
    }

    private func isCurrentStart(_ generation: UInt) -> Bool {
        analysisGeneration == generation
            && hasStarted
            && !Task.isCancelled
    }

    private func isCurrentCapture(_ generation: UInt) -> Bool {
        analysisGeneration == generation
            && hasStarted
            && state == .ready
            && isCapturing
            && !Task.isCancelled
    }

    private func resetLiveTextState() {
        liveRecognizedText = nil
        liveTextCandidateKey = nil
        liveTextCandidateCount = 0
        consecutiveEmptyTextFrames = 0
        lastSpokenTextKey = nil
        lastSpokenTextAt = .distantPast
    }

    private func provideHaptic(_ type: UINotificationFeedbackGenerator.FeedbackType) {
        guard AppSettingsStore.hapticsEnabled else { return }
        UINotificationFeedbackGenerator().notificationOccurred(type)
    }
}

enum CaptureAnalysisError: LocalizedError {
    case analysisUnavailable

    var errorDescription: String? {
        "The captured image could not be analyzed. Please try again."
    }
}
