import Foundation

enum GuidanceInstruction {
    static func message(for result: GuidanceResult) -> String {
        if result.hints.light == "too_dark" { return "Need more light." }
        if result.objectDetected == nil { return "Searching for an object." }
        if result.hints.distance == "too_far" { return "Move closer." }
        if result.hints.distance == "too_close" { return "Move farther away." }
        if result.hints.center == "off_center" { return "Center the object." }
        if result.hints.center == "slightly_off" { return "Adjust slightly toward the center." }

        let label = result.objectDetected ?? "object"
        if let confidence = result.confidence {
            return "Object detected: \(label) (\(String(format: "%.1f", confidence * 100))%)."
        }
        return "Object detected: \(label)."
    }
}
