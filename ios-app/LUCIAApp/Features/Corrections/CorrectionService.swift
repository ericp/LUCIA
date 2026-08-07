import Foundation

struct CorrectionResponse: Decodable, Equatable {
    let status: String
    let id: Int
    let newLabel: String?

    enum CodingKeys: String, CodingKey {
        case status
        case id
        case newLabel = "new_label"
    }
}

final class CorrectionService {
    private let session: URLSession
    private let baseURLOverride: URL?

    init(session: URLSession = .shared, baseURL: URL? = nil) {
        self.session = session
        self.baseURLOverride = baseURL
    }

    func submit(detectionID: Int, newLabel: String) async throws -> CorrectionResponse {
        var components = URLComponents()
        components.queryItems = [
            URLQueryItem(name: "id", value: String(detectionID)),
            URLQueryItem(name: "new_label", value: newLabel)
        ]

        let baseURL = baseURLOverride ?? AppSettingsStore.apiBaseURL
        var request = URLRequest(url: baseURL.appendingPathComponent("correct"))
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = components.percentEncodedQuery?.data(using: .utf8)
        request.timeoutInterval = 30

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.server(statusCode: httpResponse.statusCode)
        }

        let correction: CorrectionResponse
        do {
            correction = try JSONDecoder().decode(CorrectionResponse.self, from: data)
        } catch {
            throw APIError.invalidPayload
        }

        guard correction.status == "updated" else {
            throw CorrectionError.detectionNotFound
        }
        return correction
    }
}

enum CorrectionError: LocalizedError {
    case detectionNotFound

    var errorDescription: String? {
        "The original detection could not be found. Please capture the object again."
    }
}
