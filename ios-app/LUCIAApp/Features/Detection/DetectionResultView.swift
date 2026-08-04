import SwiftUI

struct DetectionResultView: View {
    let result: DetectionResult

    var body: some View {
        ZStack {
            LinearGradient(
                colors: result.objectDetected == nil
                    ? [Color.orange.opacity(0.22), Color.white]
                    : [Color.green.opacity(0.25), Color.white],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: 24) {
                Image(systemName: result.objectDetected == nil ? "questionmark.circle.fill" : "checkmark.circle.fill")
                    .font(.system(size: 88))
                    .foregroundStyle(result.objectDetected == nil ? .orange : .green)

                Text(result.displayLabel.capitalized)
                    .font(.system(size: 42, weight: .black, design: .rounded))
                    .multilineTextAlignment(.center)

                if let confidenceText = result.confidenceText {
                    Text(confidenceText)
                        .font(.title2.weight(.bold))
                        .foregroundStyle(.secondary)
                }

                Text(result.message)
                    .font(.title3.weight(.medium))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)

                Spacer()
            }
            .padding(.horizontal, 24)
            .padding(.top, 54)
        }
        .navigationTitle("Detection Result")
        .navigationBarTitleDisplayMode(.inline)
    }
}
