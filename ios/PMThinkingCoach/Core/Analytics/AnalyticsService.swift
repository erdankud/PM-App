import Foundation

/// Product analytics (spec §19).
///
/// The payload type only admits scalars, and `Event` exposes no way to attach the
/// rationale, the AI feedback text, or an identity token. Rationale length is reported
/// as a bucket, never as the text or an exact count.
protocol AnalyticsTracking: Sendable {
    func track(_ event: AnalyticsEvent)
    func flush() async
}

enum AnalyticsEvent: Sendable {
    case appOpened(source: String)
    case authStarted(method: String)
    case authCompleted(method: String)
    case authFailed(method: String, errorCode: String)
    case onboardingGoalSelected(goal: String)
    case assessmentItemCompleted(itemId: String, choiceId: String, index: Int)
    case onboardingCompleted(startingLevel: String, focusSkills: String)
    case todayViewed(assignmentState: String, scenarioId: String)
    case challengeStarted(scenarioId: String, level: String, primarySkill: String)
    case evidenceOpened(scenarioId: String, evidenceId: String, countOpened: Int)
    case decisionOptionSelected(scenarioId: String, optionId: String)
    case attemptDraftSaved(scenarioId: String, hasOption: Bool, rationaleLengthBucket: String)
    case attemptSubmitted(scenarioId: String, evidenceCount: Int, rationaleLengthBucket: String)
    case feedbackStatusChanged(scenarioId: String, status: String, latencyBucket: String, errorCode: String?)
    case feedbackViewed(scenarioId: String, scoreBand: String)
    case feedbackRated(scenarioId: String, rating: String)
    case progressViewed(level: Int, completedCount: Int)
    case historyItemOpened(scenarioId: String)
    case accountDeletionRequested

    var name: String {
        switch self {
        case .appOpened: return "app_opened"
        case .authStarted: return "auth_started"
        case .authCompleted: return "auth_completed"
        case .authFailed: return "auth_failed"
        case .onboardingGoalSelected: return "onboarding_goal_selected"
        case .assessmentItemCompleted: return "assessment_item_completed"
        case .onboardingCompleted: return "onboarding_completed"
        case .todayViewed: return "today_viewed"
        case .challengeStarted: return "challenge_started"
        case .evidenceOpened: return "evidence_opened"
        case .decisionOptionSelected: return "decision_option_selected"
        case .attemptDraftSaved: return "attempt_draft_saved"
        case .attemptSubmitted: return "attempt_submitted"
        case .feedbackStatusChanged: return "feedback_status_changed"
        case .feedbackViewed: return "feedback_viewed"
        case .feedbackRated: return "feedback_rated"
        case .progressViewed: return "progress_viewed"
        case .historyItemOpened: return "history_item_opened"
        case .accountDeletionRequested: return "account_deletion_requested"
        }
    }

    var properties: [String: AnalyticsValue] {
        switch self {
        case .appOpened(let source):
            return ["source": .string(source)]
        case .authStarted(let method), .authCompleted(let method):
            return ["method": .string(method)]
        case .authFailed(let method, let errorCode):
            return ["method": .string(method), "errorCode": .string(errorCode)]
        case .onboardingGoalSelected(let goal):
            return ["goal": .string(goal)]
        case .assessmentItemCompleted(let itemId, let choiceId, let index):
            return ["itemId": .string(itemId), "choiceId": .string(choiceId), "index": .int(index)]
        case .onboardingCompleted(let level, let focus):
            return ["startingLevel": .string(level), "focusSkills": .string(focus)]
        case .todayViewed(let state, let scenarioId):
            return ["assignmentState": .string(state), "scenarioId": .string(scenarioId)]
        case .challengeStarted(let scenarioId, let level, let skill):
            return [
                "scenarioId": .string(scenarioId), "level": .string(level),
                "primarySkill": .string(skill)
            ]
        case .evidenceOpened(let scenarioId, let evidenceId, let count):
            return [
                "scenarioId": .string(scenarioId), "evidenceId": .string(evidenceId),
                "countOpened": .int(count)
            ]
        case .decisionOptionSelected(let scenarioId, let optionId):
            return ["scenarioId": .string(scenarioId), "optionId": .string(optionId)]
        case .attemptDraftSaved(let scenarioId, let hasOption, let bucket):
            return [
                "scenarioId": .string(scenarioId), "hasOption": .bool(hasOption),
                "rationaleLengthBucket": .string(bucket)
            ]
        case .attemptSubmitted(let scenarioId, let evidenceCount, let bucket):
            return [
                "scenarioId": .string(scenarioId), "evidenceCount": .int(evidenceCount),
                "rationaleLengthBucket": .string(bucket)
            ]
        case .feedbackStatusChanged(let scenarioId, let status, let latency, let errorCode):
            var properties: [String: AnalyticsValue] = [
                "scenarioId": .string(scenarioId), "status": .string(status),
                "latencyBucket": .string(latency)
            ]
            if let errorCode { properties["errorCode"] = .string(errorCode) }
            return properties
        case .feedbackViewed(let scenarioId, let band):
            return ["scenarioId": .string(scenarioId), "scoreBand": .string(band)]
        case .feedbackRated(let scenarioId, let rating):
            return ["scenarioId": .string(scenarioId), "rating": .string(rating)]
        case .progressViewed(let level, let completed):
            return ["level": .int(level), "completedCount": .int(completed)]
        case .historyItemOpened(let scenarioId):
            return ["scenarioId": .string(scenarioId)]
        case .accountDeletionRequested:
            return [:]
        }
    }
}

enum AnalyticsBuckets {
    /// Rationale length is bucketed so the analytics store never holds anything that
    /// could reconstruct what somebody wrote.
    static func rationaleLength(_ count: Int) -> String {
        switch count {
        case 0: return "empty"
        case 1..<30: return "under_minimum"
        case 30..<120: return "30_119"
        case 120..<300: return "120_299"
        case 300..<500: return "300_499"
        default: return "500_plus"
        }
    }

    static func latency(_ seconds: TimeInterval) -> String {
        switch seconds {
        case ..<2: return "under_2s"
        case ..<5: return "2_5s"
        case ..<15: return "5_15s"
        case ..<45: return "15_45s"
        default: return "over_45s"
        }
    }

    static func scoreBand(_ score: Int) -> String {
        switch score {
        case 85...: return "85_100"
        case 70..<85: return "70_84"
        case 55..<70: return "55_69"
        case 40..<55: return "40_54"
        default: return "under_40"
        }
    }
}

/// Buffers events and posts them in batches. Failures are dropped rather than retried
/// forever — analytics must never block or break the product flow.
actor AnalyticsService: AnalyticsTracking {

    private let client: any APIClientProtocol
    private var buffer: [AnalyticsEventPayload] = []
    private let batchSize: Int
    private var isEnabled = true

    init(client: any APIClientProtocol, batchSize: Int = 10) {
        self.client = client
        self.batchSize = batchSize
    }

    nonisolated func track(_ event: AnalyticsEvent) {
        Task { await enqueue(event) }
    }

    nonisolated func flush() async {
        await drain()
    }

    func setEnabled(_ enabled: Bool) {
        isEnabled = enabled
        if !enabled { buffer.removeAll() }
    }

    private func enqueue(_ event: AnalyticsEvent) async {
        guard isEnabled else { return }
        let formatter = ISO8601DateFormatter()
        buffer.append(
            AnalyticsEventPayload(
                name: event.name,
                properties: event.properties,
                appVersion: AppConfig.appVersion,
                platform: "ios",
                clientTimestamp: formatter.string(from: Date())
            )
        )
        if buffer.count >= batchSize {
            await drain()
        }
    }

    private func drain() async {
        guard isEnabled, !buffer.isEmpty else { return }
        let batch = AnalyticsBatch(events: buffer)
        buffer.removeAll()
        try? await client.sendEvents(batch)
    }
}

/// Used in previews and unit tests.
struct NoopAnalytics: AnalyticsTracking {
    func track(_ event: AnalyticsEvent) {}
    func flush() async {}
}
