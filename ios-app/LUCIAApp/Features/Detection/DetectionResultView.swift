import SwiftUI

struct DetectionResultView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var showCorrection = false
    @StateObject private var audioService = GuidanceAudioService()

    let result: DetectionResult

    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()

            VStack(spacing: 24) {
                Image(systemName: resultIcon)
                    .font(.system(size: 88))
                    .foregroundStyle(.black)

                Text(result.displayLabel.capitalized)
                    .font(.system(size: 42, weight: .black, design: .rounded))
                    .multilineTextAlignment(.center)

                if let confidenceText = result.confidenceText {
                    Text(confidenceText)
                        .font(.title2.weight(.bold))
                        .foregroundStyle(.black.opacity(0.65))
                }

                Text(result.displayMessage)
                    .font(.title3.weight(.medium))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.black.opacity(0.65))
                    .padding(.horizontal)

                if result.hasRecognizedText {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("Recognized Text", systemImage: "text.viewfinder")
                            .font(.headline.weight(.bold))

                        ScrollView {
                            Text(result.recognizedTextString)
                                .font(.body.weight(.medium))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .textSelection(.enabled)
                        }
                        .frame(maxHeight: 180)

                        Button {
                            audioService.stop()
                        } label: {
                            Label("Stop reading", systemImage: "speaker.slash.fill")
                                .font(.subheadline.weight(.bold))
                        }
                        .foregroundStyle(.black)
                    }
                    .padding(18)
                    .background(
                        Color.black.opacity(0.05),
                        in: RoundedRectangle(cornerRadius: 20, style: .continuous)
                    )
                    .accessibilityElement(children: .contain)
                }

                if let persistenceWarning = result.persistenceWarning {
                    Label(persistenceWarning, systemImage: "exclamationmark.triangle.fill")
                        .font(.headline.weight(.bold))
                        .foregroundStyle(.black)
                        .multilineTextAlignment(.leading)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(18)
                        .background(
                            Color.black.opacity(0.08),
                            in: RoundedRectangle(cornerRadius: 20, style: .continuous)
                        )
                        .accessibilityLabel("Save warning. \(persistenceWarning)")
                }

                Spacer()

                VStack(spacing: 14) {
                    if result.id != nil && result.objectDetected != nil {
                        Button {
                            audioService.stop()
                            showCorrection = true
                        } label: {
                            Label("Correct Result", systemImage: "pencil.circle.fill")
                                .font(.title3.weight(.bold))
                                .frame(maxWidth: .infinity, minHeight: 64)
                                .foregroundStyle(.white)
                                .background(.black, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                        }
                        .accessibilityHint("Choose the correct object label")
                    }

                    Button {
                        audioService.stop()
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
        .onAppear {
            audioService.speak(result.spokenSummary, respectsVoiceSetting: false)
        }
        .onDisappear {
            audioService.stop()
        }
        .sheet(isPresented: $showCorrection) {
            if let detectionID = result.id {
                CorrectionView(
                    detectionID: detectionID,
                    currentLabel: result.objectDetected
                )
            }
        }
    }

    private var resultIcon: String {
        if result.objectDetected != nil { return "checkmark.circle.fill" }
        if result.hasRecognizedText { return "text.viewfinder" }
        return "questionmark.circle.fill"
    }
}
