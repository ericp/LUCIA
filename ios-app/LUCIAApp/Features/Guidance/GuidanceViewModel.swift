import Foundation

enum GuidanceInstruction {
    static func message(for result: GuidanceResult) -> String {
        if result.ready { return "Ready. Take the picture." }
        if result.hints.light == "too_dark" { return "More light is needed." }
        if result.hints.distance == "too_far" { return "Move closer." }
        if result.hints.distance == "too_close" { return "Move farther away." }
        if result.hints.center == "off_center" { return "Center the object." }
        if result.hints.center == "slightly_off" { return "Adjust slightly toward the center." }
        if result.objectDetected == nil { return "Searching for an object." }
        return "Hold steady."
    }
}
