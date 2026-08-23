import Foundation

/// Supplies and refreshes credentials for the API client. Implemented by SessionStore.
protocol TokenProviding: AnyObject, Sendable {
    func currentAccessToken() async -> String?
    /// Returns a new access token, or nil if the session cannot be restored.
    func refreshAccessToken() async -> String?
    func handleAuthenticationFailure() async
}

/// The one place that talks to the server. Injected as a protocol so features can be
/// tested against a stub (spec §16).
protocol APIClientProtocol: Sendable {
    func signInWithApple(identityToken: String, timezone: String) async throws -> AuthResponse
    func signInDeveloper(deviceId: String, timezone: String) async throws -> AuthResponse
    func refresh(refreshToken: String) async throws -> AuthResponse
    func signOut(refreshToken: String?) async throws

    func me() async throws -> MeResponse
    func updateProfile(_ request: ProfileUpdateRequest) async throws -> MeResponse
    func deleteAccount() async throws

    func assessment() async throws -> AssessmentState
    func answerAssessment(_ request: AssessmentAnswerRequest) async throws -> AssessmentAnswerResponse
    func assessmentResult() async throws -> AssessmentResult

    func today() async throws -> TodayResponse
    func challenge(assignmentId: String) async throws -> ChallengeResponse

    func saveDraft(attemptId: String, request: DraftRequest) async throws -> DraftResponse
    func recordEvidence(attemptId: String, cardId: String) async throws -> EvidenceResponse
    func submit(attemptId: String, request: SubmitRequest, idempotencyKey: String) async throws -> SubmitResponse
    func feedback(attemptId: String) async throws -> FeedbackResponse
    func retryFeedback(attemptId: String) async throws -> FeedbackResponse
    func rateFeedback(attemptId: String, rating: String) async throws

    func progress() async throws -> ProgressResponse
    func history(limit: Int, offset: Int) async throws -> HistoryResponse

    func sendEvents(_ batch: AnalyticsBatch) async throws
}

final class APIClient: APIClientProtocol, @unchecked Sendable {

    private let session: URLSession
    private let baseURL: () -> URL
    private weak var tokenProvider: (any TokenProviding)?
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(
        session: URLSession = .shared,
        baseURL: @escaping () -> URL = { AppConfig.apiBaseURL }
    ) {
        self.session = session
        self.baseURL = baseURL
        self.decoder = JSONDecoder()
        self.encoder = JSONEncoder()
    }

    func attach(tokenProvider: any TokenProviding) {
        self.tokenProvider = tokenProvider
    }

    // MARK: - Request plumbing

    private enum Method: String {
        case get = "GET", post = "POST", put = "PUT", patch = "PATCH", delete = "DELETE"
    }

    private func makeRequest(
        _ method: Method,
        _ path: String,
        query: [URLQueryItem]? = nil,
        body: Data? = nil,
        headers: [String: String] = [:]
    ) throws -> URLRequest {
        var components = URLComponents(
            url: baseURL().appendingPathComponent(AppConfig.apiVersionPath + path),
            resolvingAgainstBaseURL: false
        )
        components?.queryItems = query
        guard let url = components?.url else { throw APIError.invalidURL }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.httpBody = body
        request.timeoutInterval = 30
        if body != nil {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }
        return request
    }

    private func perform<Response: Decodable>(
        _ method: Method,
        _ path: String,
        query: [URLQueryItem]? = nil,
        body: Encodable? = nil,
        headers: [String: String] = [:],
        authenticated: Bool = true,
        allowRetryAfterRefresh: Bool = true
    ) async throws -> Response {
        var headers = headers
        if authenticated, let provider = tokenProvider, let token = await provider.currentAccessToken() {
            headers["Authorization"] = "Bearer \(token)"
        }

        let payload: Data? = try body.map { try encoder.encode(AnyEncodable($0)) }
        let request = try makeRequest(method, path, query: query, body: payload, headers: headers)

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch let error as URLError {
            switch error.code {
            case .notConnectedToInternet, .networkConnectionLost, .dataNotAllowed,
                 .cannotConnectToHost, .cannotFindHost:
                throw APIError.offline
            case .timedOut:
                throw APIError.timedOut
            default:
                throw APIError.server(status: -1, code: "network_\(error.code.rawValue)")
            }
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.server(status: -1, code: nil)
        }

        if http.statusCode == 401, authenticated, allowRetryAfterRefresh, let provider = tokenProvider {
            if let refreshed = await provider.refreshAccessToken() {
                var retryHeaders = headers
                retryHeaders["Authorization"] = "Bearer \(refreshed)"
                return try await perform(
                    method, path, query: query, body: body, headers: retryHeaders,
                    authenticated: false, allowRetryAfterRefresh: false
                )
            }
            await provider.handleAuthenticationFailure()
            throw APIError.unauthorized
        }

        guard (200..<300).contains(http.statusCode) else {
            throw Self.mapError(status: http.statusCode, data: data)
        }

        if Response.self == EmptyResponse.self {
            return EmptyResponse() as! Response
        }

        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decoding(String(describing: error))
        }
    }

    private static func mapError(status: Int, data: Data) -> APIError {
        let code = (try? JSONDecoder().decode(APIErrorBody.self, from: data))?.detail?.code
        switch status {
        case 401: return .unauthorized
        case 403: return .forbidden
        case 404: return .notFound
        case 409: return .conflict(code: code ?? "conflict")
        case 422, 400: return .validation(code: code ?? "invalid_request")
        case 429: return .rateLimited
        case 503: return .unavailable(code: code ?? "unavailable")
        default: return .server(status: status, code: code)
        }
    }

    // MARK: - Auth

    func signInWithApple(identityToken: String, timezone: String) async throws -> AuthResponse {
        try await perform(
            .post, "/auth/apple",
            body: AppleSignInRequest(identityToken: identityToken, timezone: timezone),
            authenticated: false
        )
    }

    func signInDeveloper(deviceId: String, timezone: String) async throws -> AuthResponse {
        try await perform(
            .post, "/auth/dev",
            body: DevSignInRequest(deviceId: deviceId, timezone: timezone),
            authenticated: false
        )
    }

    func refresh(refreshToken: String) async throws -> AuthResponse {
        try await perform(
            .post, "/auth/refresh",
            body: RefreshRequest(refreshToken: refreshToken),
            authenticated: false
        )
    }

    func signOut(refreshToken: String?) async throws {
        let _: EmptyResponse = try await perform(
            .post, "/auth/signout", body: SignOutRequest(refreshToken: refreshToken)
        )
    }

    // MARK: - Profile

    func me() async throws -> MeResponse {
        try await perform(.get, "/me")
    }

    func updateProfile(_ request: ProfileUpdateRequest) async throws -> MeResponse {
        try await perform(.patch, "/me/profile", body: request)
    }

    func deleteAccount() async throws {
        let _: EmptyResponse = try await perform(.delete, "/me")
    }

    // MARK: - Assessment

    func assessment() async throws -> AssessmentState {
        try await perform(.get, "/assessment")
    }

    func answerAssessment(_ request: AssessmentAnswerRequest) async throws -> AssessmentAnswerResponse {
        try await perform(.post, "/assessment/responses", body: request)
    }

    func assessmentResult() async throws -> AssessmentResult {
        try await perform(.get, "/assessment/result")
    }

    // MARK: - Today & challenge

    func today() async throws -> TodayResponse {
        try await perform(.get, "/today")
    }

    func challenge(assignmentId: String) async throws -> ChallengeResponse {
        try await perform(.get, "/challenges/\(assignmentId)")
    }

    func saveDraft(attemptId: String, request: DraftRequest) async throws -> DraftResponse {
        try await perform(.put, "/attempts/\(attemptId)/draft", body: request)
    }

    func recordEvidence(attemptId: String, cardId: String) async throws -> EvidenceResponse {
        try await perform(
            .post, "/attempts/\(attemptId)/evidence", body: EvidenceRequest(evidenceCardId: cardId)
        )
    }

    func submit(
        attemptId: String, request: SubmitRequest, idempotencyKey: String
    ) async throws -> SubmitResponse {
        try await perform(
            .post, "/attempts/\(attemptId)/submit",
            body: request,
            headers: ["Idempotency-Key": idempotencyKey]
        )
    }

    func feedback(attemptId: String) async throws -> FeedbackResponse {
        try await perform(.get, "/attempts/\(attemptId)/feedback")
    }

    func retryFeedback(attemptId: String) async throws -> FeedbackResponse {
        try await perform(.post, "/attempts/\(attemptId)/feedback/retry")
    }

    func rateFeedback(attemptId: String, rating: String) async throws {
        let _: EmptyResponse = try await perform(
            .post, "/attempts/\(attemptId)/feedback-rating", body: RatingRequest(rating: rating)
        )
    }

    // MARK: - Progress

    func progress() async throws -> ProgressResponse {
        try await perform(.get, "/progress")
    }

    func history(limit: Int, offset: Int) async throws -> HistoryResponse {
        try await perform(
            .get, "/history",
            query: [
                URLQueryItem(name: "limit", value: String(limit)),
                URLQueryItem(name: "offset", value: String(offset))
            ]
        )
    }

    func sendEvents(_ batch: AnalyticsBatch) async throws {
        let _: EmptyResponse = try await perform(.post, "/events", body: batch)
    }
}

struct EmptyResponse: Decodable {}

private struct AnyEncodable: Encodable {
    private let encodeClosure: (Encoder) throws -> Void
    init(_ wrapped: Encodable) {
        encodeClosure = wrapped.encode
    }
    func encode(to encoder: Encoder) throws {
        try encodeClosure(encoder)
    }
}
