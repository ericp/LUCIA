import SwiftUI

struct DetectionResultView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var showCorrection = false

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

                VStack(spacing: 14) {
                    if result.id != nil {
                        Button {
                            showCorrection = true
                        } label: {
                            Label("Correct Result", systemImage: "pencil.circle.fill")
                                .font(.title3.weight(.bold))
                                .frame(maxWidth: .infinity, minHeight: 64)
                                .foregroundStyle(.white)
                                .background(.blue, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                        }
                        .accessibilityHint("Choose the correct object label")
                    }

                    Button {
                        dismiss()
                    } label: {
                        Label("Try Again", systemImage: "camera.fill")
                            .font(.title3.weight(.bold))
                            .frame(maxWidth: .infinity, minHeight: 64)
                            .foregroundStyle(.primary)
                            .background(.white.opacity(0.85), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                    }
                    .accessibilityHint("Returns to the camera")
                }
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 36)
        }
        .navigationTitle("Detection Result")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showCorrection) {
            if let detectionID = result.id {
                CorrectionView(
                    detectionID: detectionID,
                    currentLabel: result.objectDetected
                )
            }
        }
    }
}
