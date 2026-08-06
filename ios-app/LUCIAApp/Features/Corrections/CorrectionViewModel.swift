import Foundation

@MainActor
final class CorrectionViewModel: ObservableObject {
    static let supportedLabels = [
        "bottle", "cup", "fork", "spoon", "knife",
        "book", "laptop", "cell phone", "remote", "plant"
    ]

    @Published var selectedLabel: String
    @Published private(set) var isSubmitting = false
    @Published private(set) var submittedLabel: String?
    @Published var errorMessage: String?

    let detectionID: Int
    private let service: CorrectionService

    init(
        detectionID: Int,
        currentLabel: String?,
        service: CorrectionService = CorrectionService()
    ) {
        self.detectionID = detectionID
        self.selectedLabel = currentLabel ?? Self.supportedLabels[0]
        self.service = service
    }

    func submit() async {
        guard !isSubmitting else { return }
        isSubmitting = true
        errorMessage = nil

        do {
            let response = try await service.submit(
                detectionID: detectionID,
                newLabel: selectedLabel
            )
            submittedLabel = response.newLabel ?? selectedLabel
        } catch {
            errorMessage = error.localizedDescription
        }

        isSubmitting = false
    }
}
