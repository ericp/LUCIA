import SwiftUI

struct CameraView: View {
    @StateObject private var viewModel = CameraViewModel()

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            switch viewModel.state {
            case .ready:
                CameraPreviewView(session: viewModel.session)
                    .ignoresSafeArea()

            case .loading:
                ProgressView("Opening camera...")
                    .progressViewStyle(.circular)
                    .tint(.white)
                    .foregroundStyle(.white)

            case .denied:
                cameraMessage(
                    title: "Camera Access Needed",
                    message: "Allow camera access in iPhone Settings to use LUCIA."
                )

            case .unavailable:
                cameraMessage(
                    title: "Camera Unavailable",
                    message: viewModel.message
                )
            }

            VStack {
                topOverlay
                Spacer()
                bottomOverlay
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 24)
        }
        .navigationTitle("Camera")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.start()
        }
        .onDisappear {
            viewModel.stop()
        }
        .navigationDestination(item: $viewModel.detectionResult) { result in
            DetectionResultView(result: result)
        }
        .alert(
            "Detection Failed",
            isPresented: Binding(
                get: { viewModel.captureError != nil },
                set: { if !$0 { viewModel.captureError = nil } }
            )
        ) {
            Button("OK", role: .cancel) { viewModel.captureError = nil }
        } message: {
            Text(viewModel.captureError ?? "Please try again.")
        }
    }

    private var topOverlay: some View {
        HStack {
            Label("Live Preview", systemImage: "viewfinder")
                .font(.headline.weight(.bold))
                .foregroundStyle(.white)
                .padding(.horizontal, 18)
                .padding(.vertical, 12)
                .background(.black.opacity(0.45), in: Capsule())

            Spacer()
        }
    }

    private var bottomOverlay: some View {
        VStack(spacing: 14) {
            Text("Hold the camera steady, then capture an object to identify it.")
                .font(.headline.weight(.semibold))
                .multilineTextAlignment(.center)
                .foregroundStyle(.white)
                .padding(.horizontal, 18)
                .padding(.vertical, 14)
                .frame(maxWidth: .infinity)
                .background(.black.opacity(0.45), in: RoundedRectangle(cornerRadius: 24, style: .continuous))

            Button {
                Task { await viewModel.capture() }
            } label: {
                HStack(spacing: 14) {
                    if viewModel.isCapturing {
                        ProgressView().tint(.white)
                    } else {
                        Image(systemName: "camera.fill")
                    }
                    Text(viewModel.isCapturing ? "Detecting…" : "Capture Object")
                }
                    .font(.system(size: 24, weight: .heavy, design: .rounded))
                    .foregroundStyle(.white.opacity(0.92))
                    .frame(maxWidth: .infinity, minHeight: 90)
                    .background(.white.opacity(0.18), in: RoundedRectangle(cornerRadius: 28, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 28, style: .continuous)
                            .stroke(.white.opacity(0.24), lineWidth: 1.5)
                    )
            }
            .disabled(viewModel.state != .ready || viewModel.isCapturing)
            .accessibilityHint("Takes a photo and identifies the object")
        }
    }

    private func cameraMessage(title: String, message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "camera.circle.fill")
                .font(.system(size: 72, weight: .bold))
                .foregroundStyle(.white)

            Text(title)
                .font(.largeTitle.weight(.bold))
                .foregroundStyle(.white)

            Text(message)
                .font(.title3.weight(.medium))
                .multilineTextAlignment(.center)
                .foregroundStyle(.white.opacity(0.82))
                .padding(.horizontal, 24)
        }
    }
}

#Preview {
    NavigationStack {
        CameraView()
    }
}
