import AVFoundation
import Foundation

final class CameraService: NSObject {
    let session = AVCaptureSession()

    private let sessionQueue = DispatchQueue(label: "lucia.camera.session")
    private var isConfigured = false

    func prepareSession() async throws -> Bool {
        let granted = await requestAccessIfNeeded()
        guard granted else { return false }

        if !isConfigured {
            try await configureSession()
        }

        return true
    }

    func startRunning() {
        sessionQueue.async {
            guard !self.session.isRunning else { return }
            self.session.startRunning()
        }
    }

    func stopRunning() {
        sessionQueue.async {
            guard self.session.isRunning else { return }
            self.session.stopRunning()
        }
    }

    private func requestAccessIfNeeded() async -> Bool {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            return true
        case .notDetermined:
            return await AVCaptureDevice.requestAccess(for: .video)
        default:
            return false
        }
    }

    private func configureSession() async throws {
        try await withCheckedThrowingContinuation { continuation in
            sessionQueue.async {
                do {
                    self.session.beginConfiguration()
                    self.session.sessionPreset = .photo

                    self.session.inputs.forEach { self.session.removeInput($0) }

                    guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else {
                        throw CameraError.noCameraFound
                    }

                    let input = try AVCaptureDeviceInput(device: camera)
                    guard self.session.canAddInput(input) else {
                        throw CameraError.cannotAddInput
                    }

                    self.session.addInput(input)
                    self.session.commitConfiguration()
                    self.isConfigured = true
                    continuation.resume()
                } catch {
                    self.session.commitConfiguration()
                    continuation.resume(throwing: error)
                }
            }
        }
    }
}

enum CameraError: LocalizedError {
    case noCameraFound
    case cannotAddInput

    var errorDescription: String? {
        switch self {
        case .noCameraFound:
            return "No back camera was found on this device."
        case .cannotAddInput:
            return "The camera could not be attached to the session."
        }
    }
}
