import SwiftUI

struct ContentView: View {
    @State private var showCamera = false
    @StateObject private var welcomeAudioService = GuidanceAudioService()

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
                            color: Color(red: 0.08, green: 0.72, blue: 0.76).opacity(0.32),
                            radius: 24,
                            x: 0,
                            y: 14
                        )
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open camera")
                .accessibilityHint("Starts scanning for nearby objects")

                VStack {
                    Spacer()

                    Button {
                        welcomeAudioService.stop()
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: "clock.arrow.circlepath")
                            Text("Scanned Objects")
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
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Scanned Objects")
                    .accessibilityHint("Opens your previously scanned objects")
                    .padding(.horizontal, 16)
                    .padding(.bottom, 24)
                }
            }
            .navigationDestination(isPresented: $showCamera) {
                CameraView()
            }
            .onAppear {
                welcomeAudioService.speak(
                    "Welcome to LUCIA. Tap the center of the screen to start live object recognition. Tap the bottom of the screen to check your scanned objects.",
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
