import SwiftUI

struct CameraView: View {
    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(spacing: 24) {
                Spacer()

                Image(systemName: "camera.viewfinder")
                    .font(.system(size: 84, weight: .bold))
                    .foregroundStyle(.white)

                Text("Camera Screen")
                    .font(.largeTitle.weight(.bold))
                    .foregroundStyle(.white)

                Text("This is the next place to connect the live camera preview and the current LUCIA API guidance flow.")
                    .font(.title3.weight(.medium))
                    .foregroundStyle(.white.opacity(0.82))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)

                Spacer()

                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(Color.white.opacity(0.12))
                    .frame(height: 120)
                    .overlay(
                        Text("Large capture controls can live here")
                            .font(.title2.weight(.semibold))
                            .foregroundStyle(.white)
                    )
                    .padding(.horizontal, 24)
                    .padding(.bottom, 34)
            }
        }
        .navigationTitle("Camera")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        CameraView()
    }
}
