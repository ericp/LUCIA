import Combine
import Foundation

enum CaptureType: String, Codable, Hashable {
    case object
    case text
}

struct ScannedObject: Identifiable, Hashable {
    let id: Int
    let name: String
    let confidence: Double?
    let details: String?
    let scannedAt: Date
    let thumbnailURL: URL?
    let captureType: CaptureType
    let recognizedTextLines: [RecognizedTextLine]
}

struct ScannedObjectResponse: Decodable {
    let id: Int
    let label: String
    let confidence: Double?
    let details: String?
    let scannedAt: Date
    let imageURL: String?
    let captureType: CaptureType?
    let recognizedTextLines: [RecognizedTextLine]?

    enum CodingKeys: String, CodingKey {
        case id
        case label
        case confidence
        case details
        case scannedAt = "scanned_at"
        case imageURL = "image_url"
        case captureType = "capture_type"
        case recognizedTextLines = "recognized_text_lines"
    }

    func scannedObject(baseURL: URL) -> ScannedObject {
        let thumbnailURL = imageURL.flatMap {
            URL(string: $0, relativeTo: baseURL)?.absoluteURL
        }
        return ScannedObject(
            id: id,
            name: label,
            confidence: confidence,
            details: details,
            scannedAt: scannedAt,
            thumbnailURL: thumbnailURL,
            captureType: captureType ?? (label.lowercased() == "visible text" ? .text : .object),
            recognizedTextLines: recognizedTextLines ?? []
        )
    }
}

struct ScannedObjectSection: Identifiable {
    let date: Date
    let objects: [ScannedObject]

    var id: Date { date }
}

extension Array where Element == ScannedObject {
    var groupedByDay: [ScannedObjectSection] {
        let calendar = Calendar.current
        return Dictionary(grouping: self) { calendar.startOfDay(for: $0.scannedAt) }
            .map { ScannedObjectSection(date: $0.key, objects: $0.value.sorted { $0.scannedAt > $1.scannedAt }) }
            .sorted { $0.date > $1.date }
    }
}

@MainActor
final class ObjectDetailsViewModel: ObservableObject {
    @Published private(set) var objects: [ScannedObject]
    @Published private(set) var isLoading: Bool
    @Published private(set) var errorMessage: String?

    private let initialObjects: [ScannedObject]?
    private let apiClient: APIClient
    private var hasLoaded = false

    init(initialObjects: [ScannedObject]? = nil, apiClient: APIClient = .shared) {
        self.initialObjects = initialObjects
        self.apiClient = apiClient
        self.objects = initialObjects ?? []
        self.isLoading = initialObjects == nil
    }

    func load(forceRefresh: Bool = false) async {
        if let initialObjects, !forceRefresh {
            objects = initialObjects
            isLoading = false
            hasLoaded = true
            return
        }
        guard forceRefresh || !hasLoaded else { return }

        isLoading = true
        errorMessage = nil

        do {
            objects = try await apiClient.fetchDetections()
            hasLoaded = true
        } catch is CancellationError {
            return
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}
