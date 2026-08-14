import Foundation

final class APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let baseURLOverride: URL?

    init(session: URLSession = .shared, baseURL: URL? = nil) {
        self.session = session
        self.baseURLOverride = baseURL
    }

    func detect(imageData: Data) async throws -> DetectionResult {
        try await upload(imageData: imageData, path: "detect", as: DetectionResult.self)
    }

    func guide(imageData: Data) async throws -> GuidanceResult {
        try await upload(imageData: imageData, path: "guide", as: GuidanceResult.self)
    }

    func fetchDetections() async throws -> [ScannedObject] {
        let baseURL = baseURLOverride ?? AppSettingsStore.apiBaseURL
        var request = URLRequest(url: baseURL.appendingPathComponent("detections"))
        request.httpMethod = "GET"
        request.timeoutInterval = 15

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.server(statusCode: httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        do {
            return try decoder
                .decode([ScannedObjectResponse].self, from: data)
                .map { $0.scannedObject(baseURL: baseURL) }
        } catch {
            throw APIError.invalidPayload
        }
    }

    private func upload<Response: Decodable>(
        imageData: Data,
        path: String,
        as responseType: Response.Type
    ) async throws -> Response {
        let boundary = "Boundary-\(UUID().uuidString)"
        let baseURL = baseURLOverride ?? AppSettingsStore.apiBaseURL
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
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
            return try JSONDecoder().decode(Response.self, from: data)
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
        case .server(let statusCode): return "The server returned error \(statusCode)."
        case .invalidPayload: return "The server response could not be read."
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
