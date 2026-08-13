import Foundation

struct ScannedObject: Identifiable, Hashable {
    let id: Int
    let name: String
    let details: String?
    let scannedAt: Date
    let thumbnailURL: URL?
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
