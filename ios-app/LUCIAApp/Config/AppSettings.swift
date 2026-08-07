import Foundation

enum AppSettingsStore {
    enum Key {
        static let apiBaseURL = "settings.apiBaseURL"
        static let voiceGuidanceEnabled = "settings.voiceGuidanceEnabled"
        static let speechRate = "settings.speechRate"
        static let hapticsEnabled = "settings.hapticsEnabled"
        static let guidanceInterval = "settings.guidanceInterval"
    }

    static var defaultAPIBaseURLString: String {
        AppConstants.apiBaseURL.absoluteString
    }

    static var apiBaseURL: URL {
        let storedValue = UserDefaults.standard.string(forKey: Key.apiBaseURL)
        return normalizedURL(from: storedValue) ?? AppConstants.apiBaseURL
    }

    static var voiceGuidanceEnabled: Bool {
        value(for: Key.voiceGuidanceEnabled, default: true)
    }

    static var speechRate: Float {
        Float(value(for: Key.speechRate, default: 0.48))
    }

    static var hapticsEnabled: Bool {
        value(for: Key.hapticsEnabled, default: true)
    }

    static var guidanceInterval: TimeInterval {
        value(for: Key.guidanceInterval, default: 2.0)
    }

    static func normalizedURL(from value: String?) -> URL? {
        guard var value else { return nil }
        value = value.trimmingCharacters(in: .whitespacesAndNewlines)
        while value.hasSuffix("/") { value.removeLast() }

        guard let url = URL(string: value),
              let scheme = url.scheme?.lowercased(),
              ["http", "https"].contains(scheme),
              url.host != nil else {
            return nil
        }
        return url
    }

    private static func value<T>(for key: String, default defaultValue: T) -> T {
        UserDefaults.standard.object(forKey: key) as? T ?? defaultValue
    }
}
