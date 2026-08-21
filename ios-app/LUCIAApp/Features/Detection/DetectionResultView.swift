import SwiftUI

struct DetectionResultView: View {
    @Environment(\.dismiss) private var dismiss
    @ScaledMetric(relativeTo: .largeTitle) private var resultIconSize = 72
    @State private var showCorrection = false
    @StateObject private var audioService = GuidanceAudioService()

    let result: DetectionResult

    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 24) {
                    Image(systemName: resultIcon)
                        .font(.system(size: resultIconSize))
                        .foregroundStyle(.black)
                        .accessibilityHidden(true)

                    Text(result.displayLabel.capitalized)
                        .font(.largeTitle.weight(.black))
                        .multilineTextAlignment(.center)
                        .accessibilityAddTraits(.isHeader)

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
                        VStack(alignment: .leading, spacing: 14) {
                            Label("Recognized Text", systemImage: "text.viewfinder")
                                .font(.headline.weight(.bold))
                                .accessibilityAddTraits(.isHeader)

                            Text(result.recognizedTextString)
                                .font(.body.weight(.medium))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .textSelection(.enabled)

                            Button {
                                audioService.stop()
                            } label: {
                                Label("Stop reading", systemImage: "speaker.slash.fill")
                                    .font(.headline.weight(.bold))
                                    .frame(minHeight: 44)
                            }
                            .foregroundStyle(.black)
                            .accessibilityHint("Stops LUCIA from reading the result aloud")
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

                    VStack(spacing: 14) {
                        if result.id != nil && result.objectDetected != nil {
                            Button {
                                audioService.stop()
                                showCorrection = true
                            } label: {
                                Label("Correct Result", systemImage: "pencil.circle.fill")
                                    .font(.headline.weight(.bold))
                                    .frame(maxWidth: .infinity, minHeight: 64)
                                    .fixedSize(horizontal: false, vertical: true)
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
                                .font(.headline.weight(.bold))
                                .frame(maxWidth: .infinity, minHeight: 64)
                                .fixedSize(horizontal: false, vertical: true)
                                .foregroundStyle(.black)
                                .background(.white, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                                        .stroke(.black, lineWidth: 2)
                                )
                        }
                        .accessibilityHint("Returns to the camera")
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.horizontal, 24)
                .padding(.vertical, 28)
            }
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
