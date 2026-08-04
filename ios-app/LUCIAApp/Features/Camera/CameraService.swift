import AVFoundation
import Foundation

final class CameraService: NSObject {
    let session = AVCaptureSession()

    private let sessionQueue = DispatchQueue(label: "lucia.camera.session")
    private let photoOutput = AVCapturePhotoOutput()
    private var isConfigured = false
    private var photoCaptureDelegate: PhotoCaptureDelegate?

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

    func capturePhoto() async throws -> Data {
        guard isConfigured else { throw CameraError.sessionNotConfigured }

        return try await withCheckedThrowingContinuation { continuation in
            sessionQueue.async {
                let settings = AVCapturePhotoSettings()

                let delegate = PhotoCaptureDelegate { [weak self] result in
                    self?.photoCaptureDelegate = nil
                    continuation.resume(with: result)
                }
                self.photoCaptureDelegate = delegate
                self.photoOutput.capturePhoto(with: settings, delegate: delegate)
            }
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

                    guard self.session.canAddOutput(self.photoOutput) else {
                        throw CameraError.cannotAddPhotoOutput
                    }
                    self.session.addOutput(self.photoOutput)
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
    case cannotAddPhotoOutput
    case sessionNotConfigured
    case photoDataUnavailable

    var errorDescription: String? {
        switch self {
        case .noCameraFound:
            return "No back camera was found on this device."
        case .cannotAddInput:
            return "The camera could not be attached to the session."
        case .cannotAddPhotoOutput:
            return "Photo capture could not be attached to the camera session."
        case .sessionNotConfigured:
            return "The camera is not ready yet."
        case .photoDataUnavailable:
            return "The captured photo could not be processed."
        }
    }
}

private final class PhotoCaptureDelegate: NSObject, AVCapturePhotoCaptureDelegate {
    private let completion: (Result<Data, Error>) -> Void

    init(completion: @escaping (Result<Data, Error>) -> Void) {
        self.completion = completion
    }

    func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        if let error {
            completion(.failure(error))
        } else if let data = photo.fileDataRepresentation() {
            completion(.success(data))
        } else {
            completion(.failure(CameraError.photoDataUnavailable))
        }
    }
}
