import SwiftUI

struct ContentView: View {
    @State private var showCamera = false
    @StateObject private var welcomeAudioService = GuidanceAudioService()

    private let accentGradient = LinearGradient(
        colors: [
            Color(red: 0.55, green: 0.18, blue: 0.82),
            Color(red: 0.96, green: 0.18, blue: 0.58)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    var body: some View {
        NavigationStack {
            ZStack {
                Color.white.ignoresSafeArea()

                VStack {
                    Text("LUCIA")
                        .font(.system(size: 48, weight: .black, design: .rounded))
                        .foregroundStyle(accentGradient)
                        .accessibilityAddTraits(.isHeader)
                        .padding(.top, 28)

                    Spacer()
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)

                Button {
                    welcomeAudioService.stop()
                    showCamera = true
                } label: {
                    Image(systemName: "camera.fill")
                        .font(.system(size: 82, weight: .bold))
                        .foregroundStyle(.white)
                        .frame(width: 210, height: 210)
                        .background(accentGradient, in: Circle())
                        .overlay(
                            Circle()
                                .stroke(.white.opacity(0.7), lineWidth: 4)
                                .padding(8)
                        )
                        .shadow(
                            color: Color(red: 0.78, green: 0.16, blue: 0.70).opacity(0.35),
                            radius: 24,
                            x: 0,
                            y: 14
                        )
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open camera")
                .accessibilityHint("Starts scanning for nearby objects")
            }
            .navigationDestination(isPresented: $showCamera) {
                CameraView()
            }
            .onAppear {
                welcomeAudioService.speak(
                    "Welcome to LUCIA. Tap the center of the screen to start live object recognition.",
                    respectsVoiceSetting: false
                )
            }
            .onDisappear {
                welcomeAudioService.stop()
            }
        }
    }
}

#Preview {
    ContentView()
}
