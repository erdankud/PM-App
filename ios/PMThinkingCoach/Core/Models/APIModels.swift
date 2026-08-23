import Foundation

// Wire models. These mirror server/app/schemas.py exactly; the server emits camelCase.
//
// Note what is absent by design: no rubric, no option consequence before submission,
// no prompt or model metadata. The client cannot compute a score even if it wanted to.

// MARK: - Auth & profile

struct AuthResponse: Codable, Sendable {
    let accessToken: String
    let refreshToken: String
    let expiresIn: Int
    let user: MeResponse
}

struct SkillView: Codable, Identifiable, Hashable, Sendable {
    let key: String
    let label: String
    let score: Int
    let trend: String

    var id: String { key }

    var trendSymbol: String {
        switch trend {
        case "up": return "arrow.up.right"
        case "down": return "arrow.down.right"
        default: return "minus"
        }
    }

    /// Trend is also stated in words so meaning never depends on colour alone (spec §16).
    var trendDescription: String {
        switch trend {
        case "up": return "trending up"
        case "down": return "trending down"
        default: return "steady"
        }
    }
}

struct MeResponse: Codable, Sendable {
    let userId: String
    let onboardingStatus: String
    let goal: String?
    let timezone: String
    let startingLevel: String?
    let currentLevel: String?
    let level: Int
    let totalXp: Int
    let xpForNextLevel: Int?
    let streakCount: Int
    let entitlement: String
    let focusSkills: [String]
    let skills: [SkillView]

    enum OnboardingStatus: String {
        case signedIn = "signed_in"
        case goalSet = "goal_set"
        case assessed
        case complete
        case deleted
    }

    var status: OnboardingStatus {
        OnboardingStatus(rawValue: onboardingStatus) ?? .signedIn
    }
}

// MARK: - Assessment

struct AssessmentOption: Codable, Identifiable, Sendable {
    let id: String
    let label: String
}

struct AssessmentItem: Codable, Identifiable, Sendable {
    let id: String
    let index: Int
    let total: Int
    let prompt: String
    let context: String
    let question: String
    let options: [AssessmentOption]
}

struct AssessmentState: Codable, Sendable {
    let notice: String
    let totalItems: Int
    let completedItems: Int
    let completed: Bool
    let nextItem: AssessmentItem?
}

struct PathPreviewDay: Codable, Identifiable, Sendable {
    let localDate: String
    let dayIndex: Int
    let scenarioId: String
    let title: String
    let primarySkill: String
    let primarySkillLabel: String
    let level: String
    let estimatedMinutes: Int
    let isToday: Bool

    var id: String { localDate }
}

struct AssessmentResult: Codable, Sendable {
    let startingLevel: String
    let focusSkills: [SkillView]
    let skills: [SkillView]
    let path: [PathPreviewDay]
    let disclaimer: String
}

struct AssessmentAnswerResponse: Codable, Sendable {
    let completed: Bool
    let nextItem: AssessmentItem?
    let result: AssessmentResult?
}

// MARK: - Today & challenge

enum ChallengeState: String, Codable, Sendable {
    case notStarted = "not_started"
    case inProgress = "in_progress"
    case submitted
    case awaitingFeedback = "awaiting_feedback"
    case complete
    case feedbackFailed = "feedback_failed"

    var callToAction: String {
        switch self {
        case .notStarted: return "Start"
        case .inProgress: return "Continue"
        case .submitted, .awaitingFeedback: return "See coaching"
        case .complete: return "Review"
        case .feedbackFailed: return "Retry coaching"
        }
    }

    var statusLabel: String? {
        switch self {
        case .notStarted: return nil
        case .inProgress: return "Continue later"
        case .submitted, .awaitingFeedback: return "Coaching in progress"
        case .complete: return "Completed"
        case .feedbackFailed: return "Coaching didn't finish"
        }
    }
}

struct TodayAssignment: Codable, Sendable {
    let assignmentId: String
    let localDate: String
    let scenarioId: String
    let title: String
    let summary: String
    let estimatedMinutes: Int
    let level: String
    let primarySkill: String
    let primarySkillLabel: String
    let contextLabel: String
    let state: ChallengeState
    let attemptId: String?
    let score: Int?
}

struct TodayResponse: Codable, Sendable {
    let localDate: String
    let assignment: TodayAssignment
    let upcoming: [PathPreviewDay]
    let level: Int
    let totalXp: Int
    let streakCount: Int
    let focusSkills: [SkillView]
}

struct BriefView: Codable, Sendable {
    let role: String
    let company: String
    let context: String
    let objective: String
    let constraints: String
    let task: String
    let whatGoodLooksLike: String
}

struct EvidenceCard: Codable, Identifiable, Sendable {
    let id: String
    let title: String
    let type: String
    let order: Int
    let content: String

    var typeLabel: String {
        switch type {
        case "quantitative": return "Data"
        case "qualitative": return "Voices"
        case "technical": return "Technical"
        case "business": return "Business"
        default: return type.capitalized
        }
    }

    var symbolName: String {
        switch type {
        case "quantitative": return "chart.bar"
        case "qualitative": return "quote.bubble"
        case "technical": return "wrench.and.screwdriver"
        case "business": return "briefcase"
        default: return "doc.text"
        }
    }
}

struct DecisionOption: Codable, Identifiable, Sendable {
    let id: String
    let label: String
    let description: String
}

struct ScenarioView: Codable, Sendable {
    let id: String
    let version: Int
    let title: String
    let summary: String
    let estimatedMinutes: Int
    let level: String
    let primarySkill: String
    let primarySkillLabel: String
    let tags: [String]
    let brief: BriefView
    let evidenceCards: [EvidenceCard]
    let decisionPrompt: String
    let decisionOptions: [DecisionOption]
}

struct AttemptView: Codable, Sendable {
    let attemptId: String
    let status: String
    let selectedOptionId: String?
    let rationale: String?
    let reviewedEvidenceIds: [String]
    let rationaleMin: Int
    let rationaleMax: Int
}

struct ChallengeResponse: Codable, Sendable {
    let assignmentId: String
    let localDate: String
    let state: ChallengeState
    let scenario: ScenarioView
    let attempt: AttemptView
}

struct DraftResponse: Codable, Sendable {
    let attemptId: String
    let status: String
    let selectedOptionId: String?
    let rationaleLength: Int
    let savedAt: String
}

struct EvidenceResponse: Codable, Sendable {
    let attemptId: String
    let reviewedEvidenceIds: [String]
    let reviewedCount: Int
    let totalCount: Int
}

struct ConsequenceView: Codable, Sendable {
    let optionId: String
    let optionLabel: String
    let text: String
}

enum FeedbackStatus: String, Codable, Sendable {
    case pending, complete, failed
}

struct SubmitResponse: Codable, Sendable {
    let attemptId: String
    let status: String
    let consequence: ConsequenceView
    let feedbackStatus: FeedbackStatus
}

// MARK: - Feedback

struct FeedbackPoint: Codable, Identifiable, Sendable {
    let title: String
    let detail: String
    var id: String { title + detail }
}

struct SkillImpact: Codable, Identifiable, Sendable {
    let key: String
    let label: String
    let delta: Int
    let score: Int
    var id: String { key }

    var deltaText: String { delta > 0 ? "+\(delta)" : "\(delta)" }
}

struct ScoreBreakdown: Codable, Sendable {
    let evidence: Int
    let evidenceMax: Int
    let decision: Int
    let decisionMax: Int
    let rationale: Int
    let rationaleMax: Int
    let communication: Int
    let communicationMax: Int

    var rows: [(label: String, value: Int, max: Int)] {
        [
            ("Evidence engagement", evidence, evidenceMax),
            ("Decision quality", decision, decisionMax),
            ("Rationale quality", rationale, rationaleMax),
            ("Communication clarity", communication, communicationMax)
        ]
    }
}

struct FeedbackBody: Codable, Sendable {
    let score: Int
    let band: String
    let breakdown: ScoreBreakdown
    let strengths: [FeedbackPoint]
    let improvements: [FeedbackPoint]
    let sharperApproach: String
    let skillImpact: [SkillImpact]
    let xpAwarded: Int
    let needsRetry: Bool
}

struct FeedbackResponse: Codable, Sendable {
    let attemptId: String
    let status: FeedbackStatus
    let consequence: ConsequenceView
    let feedback: FeedbackBody?
    let rating: String?
    let retryAvailable: Bool
    let scenarioTitle: String
    let learnTakeawayTitle: String?
}

// MARK: - Progress & history

struct ActivityDay: Codable, Identifiable, Sendable {
    let localDate: String
    let state: String
    var id: String { localDate }
}

struct ProgressResponse: Codable, Sendable {
    let level: Int
    let totalXp: Int
    let xpForNextLevel: Int?
    let completedCount: Int
    let streakCount: Int
    let activity: [ActivityDay]
    let skills: [SkillView]
    let footnote: String
}

struct HistoryItem: Codable, Identifiable, Sendable {
    let attemptId: String
    let scenarioId: String
    let title: String
    let localDate: String
    let primarySkill: String
    let primarySkillLabel: String
    let level: String
    let score: Int?
    let feedbackStatus: FeedbackStatus

    var id: String { attemptId }
}

struct HistoryResponse: Codable, Sendable {
    let items: [HistoryItem]
    let nextOffset: Int?
}

struct SimpleOk: Codable, Sendable {
    let ok: Bool
}

// MARK: - Requests

struct DevSignInRequest: Encodable { let deviceId: String; let timezone: String }
struct AppleSignInRequest: Encodable { let identityToken: String; let timezone: String }
struct RefreshRequest: Encodable { let refreshToken: String }
struct SignOutRequest: Encodable { let refreshToken: String? }

struct ProfileUpdateRequest: Encodable {
    var goal: String?
    var timezone: String?
    var completeOnboarding: Bool?
}

struct AssessmentAnswerRequest: Encodable {
    let itemId: String
    let choiceId: String
    let rationale: String?
}

struct DraftRequest: Encodable {
    let selectedOptionId: String?
    let rationale: String?
    let clientUpdatedAt: String?
}

struct EvidenceRequest: Encodable { let evidenceCardId: String }
struct SubmitRequest: Encodable { let selectedOptionId: String; let rationale: String }
struct RatingRequest: Encodable { let rating: String }

struct AnalyticsEventPayload: Encodable {
    let name: String
    let properties: [String: AnalyticsValue]
    let appVersion: String
    let platform: String
    let clientTimestamp: String
}

struct AnalyticsBatch: Encodable { let events: [AnalyticsEventPayload] }

/// Only scalars are representable, which is what keeps free text out of analytics
/// at the type level (spec §19).
enum AnalyticsValue: Encodable, Sendable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value): try container.encode(value)
        case .int(let value): try container.encode(value)
        case .double(let value): try container.encode(value)
        case .bool(let value): try container.encode(value)
        }
    }
}
