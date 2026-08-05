import SwiftUI

struct GuidanceView: View {
    let message: String
    let detectedObject: String?
    let isAvailable: Bool

    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 10) {
                Image(systemName: isAvailable ? "speaker.wave.2.fill" : "wifi.exclamationmark")
                Text(message)
                    .font(.headline.weight(.bold))
            }

            if let detectedObject {
                Text("Detected: \(detectedObject.capitalized)")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.white.opacity(0.82))
            }
        }
        .multilineTextAlignment(.center)
        .foregroundStyle(.white)
        .padding(.horizontal, 18)
        .padding(.vertical, 14)
        .frame(maxWidth: .infinity)
        .background(.black.opacity(0.55), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
        .accessibilityElement(children: .combine)
        .accessibilityLabel(message)
    }
}
