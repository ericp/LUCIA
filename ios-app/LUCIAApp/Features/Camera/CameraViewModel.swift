import AVFoundation
import Foundation

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

    let session: AVCaptureSession

    private let service: CameraService
    private var hasStarted = false

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
                service.startRunning()
            } else {
                state = .denied
                message = "Camera permission was denied."
            }
        } catch {
            state = .unavailable
            message = error.localizedDescription
        }
    }

    func stop() {
        service.stopRunning()
        hasStarted = false
    }
}
