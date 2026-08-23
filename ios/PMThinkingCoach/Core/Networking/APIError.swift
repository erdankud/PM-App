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
            return "You're offline. Your work is saved on this device and will sync when you reconnect."
        case .timedOut:
            return "That took too long. Check your connection and try again."
        case .unauthorized:
            return "Your session expired. Sign in again to continue."
        case .forbidden, .notFound:
            return "That challenge isn't available on this account."
        case .conflict(let code) where code == "onboarding_incomplete":
            return "Finish setting up your account to see today's challenge."
        case .conflict:
            return "That's already been submitted. Pull to refresh for the latest state."
        case .validation(let code) where code == "no_evidence_reviewed":
            return "Open at least one signal before making a decision."
        case .validation(let code) where code == "rationale_length_invalid":
            return "Your reasoning needs to be between 30 and 600 characters."
        case .validation:
            return "Something in that submission wasn't valid. Check your answer and try again."
        case .rateLimited:
            return "You've reached today's coaching limit. Try again tomorrow."
        case .unavailable(let code) where code == "no_scenario_available":
            return "Today's challenge isn't ready yet. Try again in a moment."
        case .unavailable, .server:
            return "The server had a problem. Your answer is safe — try again shortly."
        case .decoding, .invalidURL:
            return "Something unexpected came back from the server. Try again shortly."
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
