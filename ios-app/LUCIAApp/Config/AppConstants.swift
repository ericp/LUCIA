import Foundation

enum AppConstants {
    static let liveTextStableFrameCount = 2
    static let liveTextSimilarityThreshold = 0.80

    // Override API_BASE_URL in the app's Info.plist for a physical iPhone,
    // for example: http://192.168.1.20:8000
    static let apiBaseURL: URL = {
        if let value = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String,
           let url = URL(string: value),
           !value.isEmpty {
            return url
        }
        return URL(string: "http://127.0.0.1:8000")!
    }()
}
