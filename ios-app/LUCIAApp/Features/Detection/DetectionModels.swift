import Foundation

struct DetectionResult: Codable, Identifiable, Hashable {
    let id: Int?
    let objectDetected: String?
    let confidence: Double?
    let message: String
    let hints: DetectionHints?

    enum CodingKeys: String, CodingKey {
        case id
        case objectDetected = "object_detected"
        case confidence
        case message
        case hints
    }

    var displayLabel: String { objectDetected ?? "No object detected" }
    var confidenceText: String? {
        confidence.map { "\(Int(($0 * 100).rounded()))% confidence" }
    }
}

struct DetectionHints: Codable, Hashable {
    let distance: String?
    let center: String?
    let light: String?
}
