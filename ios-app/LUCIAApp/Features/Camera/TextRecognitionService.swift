import Foundation
import ImageIO
import Vision

enum TextRecognitionLevel {
    case fast
    case accurate
}

struct RecognizedTextBoundingBox: Codable, Hashable {
    // Apple Vision unit coordinates: origin is at the image's bottom-left.
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct RecognizedTextLine: Codable, Hashable {
    let text: String
    let confidence: Double
    let boundingBox: RecognizedTextBoundingBox

    enum CodingKeys: String, CodingKey {
        case text
        case confidence
        case boundingBox = "bounding_box"
    }
}

struct TextRecognitionResult: Hashable {
    let lines: [RecognizedTextLine]

    var combinedText: String {
        lines.map(\.text).joined(separator: "\n")
    }

    var averageConfidence: Double? {
        guard !lines.isEmpty else { return nil }
        return lines.map(\.confidence).reduce(0, +) / Double(lines.count)
    }

    var isEmpty: Bool { lines.isEmpty }
}

final class TextRecognitionService {
    func recognizeText(
        in imageData: Data,
        level: TextRecognitionLevel
    ) async throws -> TextRecognitionResult {
        try await Task.detached(priority: .userInitiated) {
            guard let source = CGImageSourceCreateWithData(imageData as CFData, nil),
                  let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
                throw TextRecognitionError.invalidImage
            }

            let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil)
                as? [CFString: Any]
            let rawOrientation = (properties?[kCGImagePropertyOrientation] as? NSNumber)?
                .uint32Value ?? 1
            let orientation = CGImagePropertyOrientation(rawValue: rawOrientation) ?? .up

            let request = VNRecognizeTextRequest()
            request.recognitionLevel = level == .accurate ? .accurate : .fast
            request.usesLanguageCorrection = level == .accurate
            request.automaticallyDetectsLanguage = true
            request.minimumTextHeight = level == .accurate ? 0.01 : 0.02

            let handler = VNImageRequestHandler(
                cgImage: image,
                orientation: orientation,
                options: [:]
            )
            try handler.perform([request])

            let minimumConfidence: Float = level == .accurate ? 0.35 : 0.50
            let observations = (request.results ?? []).sorted { first, second in
                let verticalDifference = abs(first.boundingBox.midY - second.boundingBox.midY)
                if verticalDifference < 0.03 {
                    return first.boundingBox.minX < second.boundingBox.minX
                }
                return first.boundingBox.maxY > second.boundingBox.maxY
            }

            let lines = observations.compactMap { observation -> RecognizedTextLine? in
                guard let candidate = observation.topCandidates(1).first,
                      candidate.confidence >= minimumConfidence else {
                    return nil
                }
                let text = candidate.string.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !text.isEmpty else { return nil }
                return RecognizedTextLine(
                    text: text,
                    confidence: Double(candidate.confidence),
                    boundingBox: RecognizedTextBoundingBox(
                        x: Double(observation.boundingBox.minX),
                        y: Double(observation.boundingBox.minY),
                        width: Double(observation.boundingBox.width),
                        height: Double(observation.boundingBox.height)
                    )
                )
            }

            return TextRecognitionResult(lines: lines)
        }.value
    }
}

enum TextRecognitionError: LocalizedError {
    case invalidImage

    var errorDescription: String? {
        "The captured image could not be prepared for text recognition."
    }
}
