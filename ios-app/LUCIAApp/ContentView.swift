import SwiftUI

struct ContentView: View {
    @State private var showCamera = false

    var body: some View {
        NavigationStack {
            ZStack {
                LinearGradient(
                    colors: [
                        Color(red: 0.97, green: 0.95, blue: 0.89),
                        Color(red: 0.88, green: 0.92, blue: 0.96)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                VStack(alignment: .leading, spacing: 28) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("LUCIA")
                            .font(.system(size: 42, weight: .black, design: .rounded))
                            .foregroundStyle(Color.black)

                        Text("Open the camera quickly and use large actions for guidance, capture, and corrections.")
                            .font(.title3.weight(.medium))
                            .foregroundStyle(Color.black.opacity(0.78))
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    VStack(spacing: 18) {
                        LargeActionButton(
                            title: "Open Camera",
                            subtitle: "Primary access for live guidance",
                            systemImage: "camera.fill",
                            backgroundColor: Color(red: 0.12, green: 0.38, blue: 0.27)
                        ) {
                            showCamera = true
                        }

                        LargeActionButton(
                            title: "Capture Image",
                            subtitle: "Send a photo to the detection API",
                            systemImage: "camera.aperture",
                            backgroundColor: Color(red: 0.06, green: 0.28, blue: 0.54)
                        ) {
                            showCamera = true
                        }

                        LargeActionButton(
                            title: "Start Guidance",
                            subtitle: "Use voice and hints while aiming",
                            systemImage: "speaker.wave.3.fill",
                            backgroundColor: Color(red: 0.58, green: 0.32, blue: 0.12)
                        ) {
                            showCamera = true
                        }

                        LargeActionButton(
                            title: "Send Correction",
                            subtitle: "Capture an object, then correct its label",
                            systemImage: "pencil.circle.fill",
                            backgroundColor: Color(red: 0.36, green: 0.18, blue: 0.46)
                        ) {
                            showCamera = true
                        }
                    }

                    Text("Designed with high-contrast, oversized touch targets for quick access.")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(Color.black.opacity(0.65))
                        .padding(.top, 6)

                    Spacer()
                }
                .padding(.horizontal, 24)
                .padding(.vertical, 28)
            }
            .navigationDestination(isPresented: $showCamera) {
                CameraView()
            }
        }
    }
}
