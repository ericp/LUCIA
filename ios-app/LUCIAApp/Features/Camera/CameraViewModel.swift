import AVFoundation
import Foundation
import UIKit

@MainActor
final class CameraViewModel: ObservableObject {
    enum State {
        case loading
        case ready
        case denied
        case unavailable
    }

    @Published private(set) var state: State = .loading
    @Published private(set) var message = "Preparing camera..."
    @Published private(set) var isCapturing = false
    @Published var detectionResult: DetectionResult?
    @Published var captureError: String?
    @Published private(set) var guidanceMessage = "Preparing live guidance…"
    @Published private(set) var guidanceObject: String?
    @Published private(set) var isGuidanceAvailable = true

    let session: AVCaptureSession

    var canCaptureForMoreDetail: Bool {
        state == .ready &&
            isGuidanceAvailable &&
            guidanceObject != nil &&
            !isCapturing
    }

    private let service: CameraService
    private let audioService = GuidanceAudioService()
    private var hasStarted = false
    private var guidanceTask: Task<Void, Never>?

    init(service: CameraService = CameraService()) {
        self.service = service
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
                guidanceMessage = "Camera ready. Tap the bottom to capture more detail."
                service.startRunning()
                audioService.speak(
                    "Camera ready. Tap the bottom to capture more detail.",
                    respectsVoiceSetting: false
                )
                startGuidance()
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
        audioService.stop()
        hasStarted = false
    }

    func capture() async {
        guard canCaptureForMoreDetail else { return }
        isCapturing = true
        captureError = nil

        do {
            let imageData = try await service.capturePhoto()
            detectionResult = try await APIClient.shared.detect(imageData: imageData)
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

    private func requestGuidance() async {
        guard !isCapturing, let frame = service.latestGuidanceFrame() else { return }

        do {
            let result = try await APIClient.shared.guide(imageData: frame)
            let instruction = GuidanceInstruction.message(for: result)
            guidanceMessage = instruction
            guidanceObject = result.objectDetected
            isGuidanceAvailable = true
            audioService.speak(instruction)
        } catch {
            guidanceMessage = "Live guidance unavailable"
            guidanceObject = nil
            isGuidanceAvailable = false
        }
    }

    private func provideHaptic(_ type: UINotificationFeedbackGenerator.FeedbackType) {
        guard AppSettingsStore.hapticsEnabled else { return }
        UINotificationFeedbackGenerator().notificationOccurred(type)
    }
}
