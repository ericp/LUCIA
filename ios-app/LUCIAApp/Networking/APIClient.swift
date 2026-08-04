import Foundation

final class APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let baseURL: URL

    init(session: URLSession = .shared, baseURL: URL = AppConstants.apiBaseURL) {
        self.session = session
        self.baseURL = baseURL
    }

    func detect(imageData: Data) async throws -> DetectionResult {
        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: baseURL.appendingPathComponent("detect"))
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.httpBody = MultipartFormData.image(imageData, boundary: boundary)
        request.timeoutInterval = 60

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.server(statusCode: httpResponse.statusCode)
        }

        do {
            return try JSONDecoder().decode(DetectionResult.self, from: data)
        } catch {
            throw APIError.invalidPayload
        }
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case server(statusCode: Int)
    case invalidPayload

    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "The server returned an invalid response."
        case .server(let statusCode): return "Detection failed with server error \(statusCode)."
        case .invalidPayload: return "The detection response could not be read."
        }
    }
}

private enum MultipartFormData {
    static func image(_ data: Data, boundary: String) -> Data {
        var body = Data()
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\n")
        body.append("Content-Type: image/jpeg\r\n\r\n")
        body.append(data)
        body.append("\r\n--\(boundary)--\r\n")
        return body
    }
}

private extension Data {
    mutating func append(_ string: String) {
        append(Data(string.utf8))
    }
}
