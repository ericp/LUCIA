import SwiftUI

struct CorrectionView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel: CorrectionViewModel

    init(detectionID: Int, currentLabel: String?) {
        _viewModel = StateObject(
            wrappedValue: CorrectionViewModel(
                detectionID: detectionID,
                currentLabel: currentLabel
            )
        )
    }

    var body: some View {
        NavigationStack {
            Group {
                if let submittedLabel = viewModel.submittedLabel {
                    confirmation(label: submittedLabel)
                } else {
                    correctionForm
                }
            }
            .navigationTitle("Correct Result")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
            .alert(
                "Correction Failed",
                isPresented: Binding(
                    get: { viewModel.errorMessage != nil },
                    set: { if !$0 { viewModel.errorMessage = nil } }
                )
            ) {
                Button("OK", role: .cancel) { viewModel.errorMessage = nil }
            } message: {
                Text(viewModel.errorMessage ?? "Please try again.")
            }
        }
    }

    private var correctionForm: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("What object is shown?")
                .font(.title2.weight(.bold))
                .padding(.horizontal)

            List(CorrectionViewModel.supportedLabels, id: \.self) { label in
                Button {
                    viewModel.selectedLabel = label
                } label: {
                    HStack {
                        Text(label.capitalized)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(.primary)
                        Spacer()
                        Image(systemName: viewModel.selectedLabel == label ? "checkmark.circle.fill" : "circle")
                            .font(.title2)
                            .foregroundStyle(viewModel.selectedLabel == label ? .blue : .secondary)
                    }
                    .contentShape(Rectangle())
                    .padding(.vertical, 6)
                }
                .accessibilityLabel(label.capitalized)
                .accessibilityValue(viewModel.selectedLabel == label ? "Selected" : "Not selected")
            }
            .listStyle(.plain)

            Button {
                Task { await viewModel.submit() }
            } label: {
                HStack {
                    if viewModel.isSubmitting {
                        ProgressView().tint(.white)
                    }
                    Text(viewModel.isSubmitting ? "Submitting…" : "Submit Correction")
                }
                .font(.title3.weight(.bold))
                .frame(maxWidth: .infinity, minHeight: 64)
                .foregroundStyle(.white)
                .background(.blue, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            }
            .disabled(viewModel.isSubmitting)
            .padding()
        }
        .padding(.top)
    }

    private func confirmation(label: String) -> some View {
        VStack(spacing: 24) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 88))
                .foregroundStyle(.green)

            Text("Correction Saved")
                .font(.largeTitle.weight(.bold))

            Text("The object was labeled as \(label.capitalized).")
                .font(.title3.weight(.medium))
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)

            Button("Done") { dismiss() }
                .font(.title3.weight(.bold))
                .frame(maxWidth: .infinity, minHeight: 64)
                .foregroundStyle(.white)
                .background(.green, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        }
        .padding(24)
    }
}
