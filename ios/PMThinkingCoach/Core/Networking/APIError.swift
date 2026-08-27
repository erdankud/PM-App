import Foundation

/// Typed API errors so views can show a specific, recoverable message rather than
/// a generic failure (spec §18, §21).
enum APIError: Error, Equatable {
    case offline
    case timedOut
    case unauthorized
    case forbidden
    case notFound
    case conflict(code: String)
    case validation(code: String)
    case rateLimited
    case unavailable(code: String)
    case server(status: Int, code: String?)
    case decoding(String)
    case invalidURL

    var isRetryable: Bool {
        switch self {
        case .offline, .timedOut, .rateLimited, .unavailable, .server:
            return true
        case .unauthorized, .forbidden, .notFound, .conflict, .validation, .decoding, .invalidURL:
            return false
        }
    }

    /// Machine-readable code, safe for analytics. Never contains user content.
    var code: String {
        switch self {
        case .offline: return "offline"
        case .timedOut: return "timed_out"
        case .unauthorized: return "unauthorized"
        case .forbidden: return "forbidden"
        case .notFound: return "not_found"
        case .conflict(let code): return code
        case .validation(let code): return code
        case .rateLimited: return "rate_limited"
        case .unavailable(let code): return code
        case .server(let status, let code): return code ?? "http_\(status)"
        case .decoding: return "decoding_failed"
        case .invalidURL: return "invalid_url"
        }
    }

    var userMessage: String {
        switch self {
        case .offline:
            return S.Errors.offline
        case .timedOut:
            return S.Errors.timedOut
        case .unauthorized:
            return S.Errors.unauthorized
        case .forbidden, .notFound:
            return S.Errors.notAvailable
        case .conflict(let code) where code == "onboarding_incomplete":
            return S.Errors.onboardingIncomplete
        case .conflict:
            return S.Errors.alreadySubmitted
        case .validation(let code) where code == "no_evidence_reviewed":
            return S.Errors.noEvidenceReviewed
        case .validation(let code) where code == "rationale_length_invalid":
            return S.Errors.rationaleLength(
                AppConfig.rationaleMinimum, AppConfig.rationaleMaximum
            )
        case .validation:
            return S.Errors.invalidSubmission
        case .rateLimited:
            return S.Errors.rateLimited
        case .unavailable(let code) where code == "no_scenario_available":
            return S.Errors.noScenarioAvailable
        case .unavailable, .server:
            return S.Errors.serverProblem
        case .decoding, .invalidURL:
            return S.Errors.unexpectedResponse
        }
    }
}

/// Error envelope the API returns: `{"detail": {"code": "..."}}`.
struct APIErrorBody: Decodable {
    struct Detail: Decodable {
        let code: String?
        let message: String?
    }

    let detail: Detail?

    private enum CodingKeys: String, CodingKey { case detail }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        if let detail = try? container.decode(Detail.self, forKey: .detail) {
            self.detail = detail
        } else if let text = try? container.decode(String.self, forKey: .detail) {
            self.detail = Detail(code: text, message: text)
        } else {
            self.detail = nil
        }
    }
}
