import SwiftUI

struct CameraView: View {
    @StateObject private var viewModel = CameraViewModel()

    private let accentGradient = LinearGradient(
        colors: [
            Color(red: 0.12, green: 0.86, blue: 0.70),
            Color(red: 0.08, green: 0.75, blue: 0.80),
            Color(red: 0.18, green: 0.55, blue: 0.98)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()

            VStack(spacing: 18) {
                ZStack {
                    Color.black

                    switch viewModel.state {
                    case .ready:
                        CameraPreviewView(session: viewModel.session)

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
                        guidanceOverlay
                    }
                    .padding(18)
                }
                .frame(maxHeight: .infinity)
                .clipShape(RoundedRectangle(cornerRadius: 30, style: .continuous))
                .overlay(
                    RoundedRectangle(cornerRadius: 30, style: .continuous)
                        .stroke(.black.opacity(0.08), lineWidth: 1)
                )

                captureButton
            }
            .padding(.horizontal, 16)
            .padding(.top, 18)
            .padding(.bottom, 24)
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

    private var guidanceOverlay: some View {
        GuidanceView(
            message: viewModel.guidanceMessage,
            isAvailable: viewModel.isGuidanceAvailable
        )
    }

    private var captureButton: some View {
        Button {
            Task { await viewModel.capture() }
        } label: {
            HStack(spacing: 12) {
                if viewModel.isCapturing {
                    ProgressView().tint(.white)
                } else {
                    Image(systemName: "camera.fill")
                }
                Text(viewModel.isCapturing ? "Detecting…" : "Capture for more detail")
            }
            .font(.system(size: 20, weight: .heavy, design: .rounded))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity, minHeight: 76)
            .background(accentGradient, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(.white.opacity(0.65), lineWidth: 2)
            )
            .shadow(
                color: Color(red: 0.08, green: 0.72, blue: 0.76).opacity(0.28),
                radius: 14,
                x: 0,
                y: 8
            )
            .saturation(viewModel.canCaptureForMoreDetail ? 1 : 0)
            .opacity(viewModel.canCaptureForMoreDetail ? 1 : 0.42)
        }
        .disabled(!viewModel.canCaptureForMoreDetail)
        .accessibilityLabel("Capture for more detail")
        .accessibilityHint("Takes a detailed photo and identifies the object")
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
    CameraView()
}
