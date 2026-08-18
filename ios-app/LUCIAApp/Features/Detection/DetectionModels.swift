import Foundation

struct DetectionResult: Codable, Identifiable, Hashable {
    let id: Int?
    let objectDetected: String?
    let confidence: Double?
    let message: String
    let hints: DetectionHints?
    let recognizedText: [RecognizedTextLine]?

    enum CodingKeys: String, CodingKey {
        case id
        case objectDetected = "object_detected"
        case confidence
        case message
        case hints
        case recognizedText = "recognized_text"
    }

    var displayLabel: String {
        if let objectDetected { return objectDetected }
        return hasRecognizedText ? "Visible text" : "No object detected"
    }

    var confidenceText: String? {
        confidence.map { "\(Int(($0 * 100).rounded()))% confidence" }
    }

    var recognizedTextString: String {
        (recognizedText ?? []).map(\.text).joined(separator: "\n")
    }

    var hasRecognizedText: Bool {
        !recognizedTextString.isEmpty
    }

    var displayMessage: String {
        objectDetected == nil && hasRecognizedText
            ? "Text recognized on this device."
            : message
    }

    var spokenSummary: String {
        var parts: [String] = []
        if let objectDetected {
            if let confidence {
                parts.append(
                    "\(objectDetected) detected, \(Int((confidence * 100).rounded())) percent confidence."
                )
            } else {
                parts.append("\(objectDetected) detected.")
            }
        }
        if hasRecognizedText {
            parts.append("Visible text reads: \(recognizedTextString)")
        } else if objectDetected == nil {
            parts.append("No supported object or clear text was detected.")
        }
        return parts.joined(separator: " ")
    }

    func includingRecognizedText(_ lines: [RecognizedTextLine]) -> DetectionResult {
        DetectionResult(
            id: id,
            objectDetected: objectDetected,
            confidence: confidence,
            message: message,
            hints: hints,
            recognizedText: lines
        )
    }

    func includingDetectionID(_ detectionID: Int) -> DetectionResult {
        DetectionResult(
            id: detectionID,
            objectDetected: objectDetected,
            confidence: confidence,
            message: message,
            hints: hints,
            recognizedText: recognizedText
        )
    }
}

struct DetectionHints: Codable, Hashable {
    let distance: String?
    let center: String?
    let light: String?
}

struct GuidanceResult: Codable, Hashable {
    let objectDetected: String?
    let confidence: Double?
    let hints: DetectionHints
    let ready: Bool

    enum CodingKeys: String, CodingKey {
        case objectDetected = "object_detected"
        case confidence
        case hints
        case ready
    }
}
