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
    let thumbnailPath: String?
    let captureType: CaptureType?
    let recognizedTextLines: [RecognizedTextLine]?

    enum CodingKeys: String, CodingKey {
        case id
        case label
        case confidence
        case details
        case scannedAt = "scanned_at"
        case imageURL = "image_url"
        case thumbnailPath = "thumbnail_url"
        case captureType = "capture_type"
        case recognizedTextLines = "recognized_text_lines"
    }

    func scannedObject(baseURL: URL) -> ScannedObject {
        let thumbnailURL = (thumbnailPath ?? imageURL).flatMap {
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

struct ScannedObjectPage {
    let items: [ScannedObject]
    let nextCursor: String?
}

struct ScannedObjectPageResponse: Decodable {
    let items: [ScannedObjectResponse]
    let nextCursor: String?

    enum CodingKeys: String, CodingKey {
        case items
        case nextCursor = "next_cursor"
    }

    func scannedObjectPage(baseURL: URL) -> ScannedObjectPage {
        ScannedObjectPage(
            items: items.map { $0.scannedObject(baseURL: baseURL) },
            nextCursor: nextCursor
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
    @Published private(set) var isLoadingMore = false
    @Published private(set) var paginationErrorMessage: String?

    private let initialObjects: [ScannedObject]?
    private let apiClient: APIClient
    private var hasLoaded = false
    private var nextCursor: String?
    private var historyGeneration: UInt = 0

    var hasMore: Bool { nextCursor != nil }

    init(initialObjects: [ScannedObject]? = nil, apiClient: APIClient = .shared) {
        self.initialObjects = initialObjects
        self.apiClient = apiClient
        self.objects = initialObjects ?? []
        self.isLoading = initialObjects == nil
        self.nextCursor = nil
    }

    func load(forceRefresh: Bool = false) async {
        if let initialObjects, !forceRefresh {
            objects = initialObjects
            isLoading = false
            hasLoaded = true
            nextCursor = nil
            return
        }
        guard forceRefresh || !hasLoaded else { return }

        historyGeneration &+= 1
        let generation = historyGeneration
        isLoading = true
        isLoadingMore = false
        errorMessage = nil
        paginationErrorMessage = nil

        do {
            let page = try await apiClient.fetchDetectionPage()
            guard generation == historyGeneration else { return }
            objects = page.items
            nextCursor = page.nextCursor
            hasLoaded = true
        } catch is CancellationError {
            if generation == historyGeneration { isLoading = false }
            return
        } catch {
            guard generation == historyGeneration else { return }
            errorMessage = error.localizedDescription
        }
        if generation == historyGeneration { isLoading = false }
    }

    func loadMoreIfNeeded(currentItem: ScannedObject) async {
        guard let index = objects.firstIndex(where: { $0.id == currentItem.id }),
              index >= max(objects.count - 5, 0) else {
            return
        }
        await loadMore()
    }

    func retryLoadingMore() async {
        await loadMore()
    }

    private func loadMore() async {
        guard hasLoaded,
              !isLoading,
              !isLoadingMore,
              let cursor = nextCursor else {
            return
        }

        isLoadingMore = true
        paginationErrorMessage = nil
        let generation = historyGeneration
        defer {
            if generation == historyGeneration { isLoadingMore = false }
        }

        do {
            let page = try await apiClient.fetchDetectionPage(cursor: cursor)
            guard generation == historyGeneration else { return }
            let existingIDs = Set(objects.map(\.id))
            objects.append(contentsOf: page.items.filter { !existingIDs.contains($0.id) })
            nextCursor = page.nextCursor
        } catch is CancellationError {
            return
        } catch {
            guard generation == historyGeneration else { return }
            paginationErrorMessage = error.localizedDescription
        }
    }
}
