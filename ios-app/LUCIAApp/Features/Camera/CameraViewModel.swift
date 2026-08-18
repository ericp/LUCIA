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

        do {
            let accessGranted = try await service.prepareSession()
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
            state = .unavailable
            message = error.localizedDescription
        }
    }

    func stop() {
        service.stopRunning()
        guidanceTask?.cancel()
        guidanceTask = nil
        liveTextTask?.cancel()
        liveTextTask = nil
        audioService.stop()
        hasStarted = false
        resetLiveTextState()
    }

    func selectMode(_ newMode: CameraMode) {
        guard mode != newMode, state == .ready else { return }
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
        isCapturing = true
        captureError = nil
        audioService.stop()

        do {
            let imageData = try await service.capturePhoto()
            let detectionTask = Task {
                try? await APIClient.shared.detect(imageData: imageData)
            }
            let textTask = Task { [textRecognitionService] in
                try? await textRecognitionService.recognizeText(
                    in: imageData,
                    level: .accurate
                )
            }

            let detectedResult = await detectionTask.value
            let textResult = await textTask.value

            guard detectedResult != nil || textResult?.isEmpty == false else {
                throw CaptureAnalysisError.analysisUnavailable
            }

            let baseResult = detectedResult ?? DetectionResult(
                id: nil,
                objectDetected: nil,
                confidence: nil,
                message: "Object detection was unavailable.",
                hints: nil,
                recognizedText: nil
            )
            var combinedResult = baseResult.includingRecognizedText(textResult?.lines ?? [])

            if let detectionID = combinedResult.id,
               let textResult,
               !textResult.isEmpty {
                try? await APIClient.shared.saveRecognizedText(
                    detectionID: detectionID,
                    result: textResult
                )
            } else if combinedResult.id == nil,
                      let textResult,
                      !textResult.isEmpty,
                      let textCaptureID = try? await APIClient.shared.saveTextCapture(
                          imageData: imageData,
                          result: textResult
                      ) {
                combinedResult = combinedResult.includingDetectionID(textCaptureID)
            }

            detectionResult = combinedResult
            provideHaptic(.success)
        } catch {
            captureError = error.localizedDescription
            provideHaptic(.error)
        }

        isCapturing = false
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

        do {
            let result = try await APIClient.shared.guide(imageData: frame)
            let instruction = GuidanceInstruction.message(for: result)
            guidanceMessage = instruction
            guidanceObject = result.objectDetected
            isGuidanceAvailable = true
            audioService.speak(instruction)
        } catch {
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

        do {
            let result = try await textRecognitionService.recognizeText(
                in: frame,
                level: .fast
            )
            processLiveText(result)
        } catch {
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
        let key = normalizedTextKey(text)

        if key == liveTextCandidateKey {
            liveTextCandidateCount += 1
        } else {
            liveTextCandidateKey = key
            liveTextCandidateCount = 1
        }

        guard liveTextCandidateCount >= 2 else {
            guidanceMessage = "Text found. Hold steady."
            return
        }

        let limitedText = String(text.prefix(240))
        liveRecognizedText = limitedText
        guidanceMessage = "Text detected: \(limitedText)"

        let now = Date()
        if key != lastSpokenTextKey || now.timeIntervalSince(lastSpokenTextAt) >= 15 {
            audioService.enqueue("Text reads: \(limitedText)")
            lastSpokenTextKey = key
            lastSpokenTextAt = now
        }
    }

    private func normalizedTextKey(_ text: String) -> String {
        text.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: .current)
            .components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }
            .joined(separator: " ")
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
