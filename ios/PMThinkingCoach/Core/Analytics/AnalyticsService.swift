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
    case onboardingCompleted(targetRole: String)
    case treeViewed(blocksPassed: Int, blocksAvailable: Int)
    // System Design (спека домена §9). Свободный текст ответов на упражнения
    // в аналитику не уходит — только факт и попадание в интервал.
    case treeSwitched(from: String, to: String)
    case diagramOpened(diagramId: String, lessonId: String)
    case termTapped(termId: String, lessonId: String, isFirstEncounter: Bool)
    case glossaryOpened(source: String, searchQueryLength: Int)
    case exerciseStarted(exerciseId: String, type: String)
    case exerciseSubmitted(exerciseId: String, type: String, withinRange: Bool, seconds: Int)
    case exerciseSkipped(exerciseId: String)
    case blockOpened(blockId: String, status: String)
    case lessonOpened(lessonId: String, nodeId: String)
    case lessonCompleted(lessonId: String, nodeId: String, seconds: Int)
    case remediationLessonOpened(lessonId: String, fromGateId: String)
    case gateStarted(gateId: String, scenarioId: String, attemptIndex: Int, lessonsCompletedRatio: Double)
    case gateResult(gateId: String, passed: Bool, scoreBand: String, attemptIndex: Int)
    case blockUnlocked(blockId: String)
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
        case .treeViewed: return "tree_viewed"
        case .treeSwitched: return "tree_switched"
        case .diagramOpened: return "diagram_opened"
        case .termTapped: return "term_tapped"
        case .glossaryOpened: return "glossary_opened"
        case .exerciseStarted: return "exercise_started"
        case .exerciseSubmitted: return "exercise_submitted"
        case .exerciseSkipped: return "exercise_skipped"
        case .blockOpened: return "block_opened"
        case .lessonOpened: return "lesson_opened"
        case .lessonCompleted: return "lesson_completed"
        case .remediationLessonOpened: return "remediation_lesson_opened"
        case .gateStarted: return "gate_started"
        case .gateResult: return "gate_result"
        case .blockUnlocked: return "block_unlocked"
        case .onboardingCompleted: return "onboarding_completed"
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
        case .onboardingCompleted(let role):
            return ["targetRole": .string(role)]
        case .treeViewed(let passed, let available):
            return ["blocksPassed": .int(passed), "blocksAvailable": .int(available)]
        case .treeSwitched(let from, let to):
            return ["fromKind": .string(from), "toKind": .string(to)]
        case .diagramOpened(let diagramId, let lessonId):
            return ["diagramId": .string(diagramId), "lessonId": .string(lessonId)]
        case .termTapped(let termId, let lessonId, let first):
            return [
                "termId": .string(termId),
                "lessonId": .string(lessonId),
                "isFirstEncounter": .bool(first),
            ]
        case .glossaryOpened(let source, let length):
            return ["source": .string(source), "searchQueryLength": .int(length)]
        case .exerciseStarted(let exerciseId, let type):
            return ["exerciseId": .string(exerciseId), "type": .string(type)]
        case .exerciseSubmitted(let exerciseId, let type, let within, let seconds):
            return [
                "exerciseId": .string(exerciseId),
                "type": .string(type),
                "withinRange": .bool(within),
                "timeSeconds": .int(seconds),
            ]
        case .exerciseSkipped(let exerciseId):
            return ["exerciseId": .string(exerciseId)]
        case .blockOpened(let blockId, let status):
            return ["blockId": .string(blockId), "status": .string(status)]
        case .lessonOpened(let lessonId, let nodeId):
            return ["lessonId": .string(lessonId), "nodeId": .string(nodeId)]
        case .lessonCompleted(let lessonId, let nodeId, let seconds):
            return [
                "lessonId": .string(lessonId), "nodeId": .string(nodeId),
                "secondsOnScreen": .int(seconds),
            ]
        case .remediationLessonOpened(let lessonId, let gateId):
            return ["lessonId": .string(lessonId), "fromGateId": .string(gateId)]
        case .gateStarted(let gateId, let scenarioId, let index, let ratio):
            // The guard against people clicking through lessons just to unlock a gate
            // (spec v0.2 §5): if this ratio falls, the lessons are the problem.
            return [
                "gateId": .string(gateId), "scenarioId": .string(scenarioId),
                "attemptIndex": .int(index),
                "lessonsCompletedRatio": .int(Int((ratio * 100).rounded())),
            ]
        case .gateResult(let gateId, let passed, let band, let index):
            return [
                "gateId": .string(gateId), "passed": .bool(passed),
                "scoreBand": .string(band), "attemptIndex": .int(index),
            ]
        case .blockUnlocked(let blockId):
            return ["blockId": .string(blockId)]
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
