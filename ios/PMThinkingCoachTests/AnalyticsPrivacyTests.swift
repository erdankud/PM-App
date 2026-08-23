import XCTest
@testable import PMThinkingCoach

/// Analytics must never carry free text (spec §19, §21 quality acceptance).
final class AnalyticsPrivacyTests: XCTestCase {

    func testRationaleIsReportedOnlyAsABucket() {
        XCTAssertEqual(AnalyticsBuckets.rationaleLength(0), "empty")
        XCTAssertEqual(AnalyticsBuckets.rationaleLength(12), "under_minimum")
        XCTAssertEqual(AnalyticsBuckets.rationaleLength(30), "30_119")
        XCTAssertEqual(AnalyticsBuckets.rationaleLength(250), "120_299")
        XCTAssertEqual(AnalyticsBuckets.rationaleLength(430), "300_499")
        XCTAssertEqual(AnalyticsBuckets.rationaleLength(600), "500_plus")
    }

    func testSubmittedEventCarriesNoUserText() throws {
        let rationale = "A sentence the user actually wrote that must never leave the device."
        let event = AnalyticsEvent.attemptSubmitted(
            scenarioId: "onboarding-retention-drop",
            evidenceCount: 3,
            rationaleLengthBucket: AnalyticsBuckets.rationaleLength(rationale.count)
        )

        let payload = AnalyticsEventPayload(
            name: event.name,
            properties: event.properties,
            appVersion: "1.0",
            platform: "ios",
            clientTimestamp: "2026-08-23T10:00:00Z"
        )
        let encoded = try JSONEncoder().encode(payload)
        let text = String(data: encoded, encoding: .utf8) ?? ""

        XCTAssertFalse(text.contains("A sentence the user actually wrote"))
        XCTAssertTrue(text.contains("30_119"))
        XCTAssertTrue(text.contains("onboarding-retention-drop"))
    }

    func testFeedbackEventCarriesOnlyAScoreBand() throws {
        let event = AnalyticsEvent.feedbackViewed(
            scenarioId: "smb-churn-signal", scoreBand: AnalyticsBuckets.scoreBand(87)
        )
        XCTAssertEqual(event.name, "feedback_viewed")
        let encoded = try JSONEncoder().encode(
            AnalyticsEventPayload(
                name: event.name, properties: event.properties,
                appVersion: "1.0", platform: "ios", clientTimestamp: "2026-08-23T10:00:00Z"
            )
        )
        let text = String(data: encoded, encoding: .utf8) ?? ""
        XCTAssertTrue(text.contains("85_100"))
        XCTAssertFalse(text.contains("\"87\""))
    }

    func testLatencyBuckets() {
        XCTAssertEqual(AnalyticsBuckets.latency(1), "under_2s")
        XCTAssertEqual(AnalyticsBuckets.latency(3), "2_5s")
        XCTAssertEqual(AnalyticsBuckets.latency(10), "5_15s")
        XCTAssertEqual(AnalyticsBuckets.latency(30), "15_45s")
        XCTAssertEqual(AnalyticsBuckets.latency(120), "over_45s")
    }
}

/// The client never derives a score, XP or a level: those arrive from the server.
final class ClientHasNoScoringLogicTests: XCTestCase {

    func testScoreBreakdownIsDisplayedExactlyAsReceived() {
        let breakdown = ScoreBreakdown(
            evidence: 12, evidenceMax: 15,
            decision: 25, decisionMax: 25,
            rationale: 34, rationaleMax: 45,
            communication: 12, communicationMax: 15
        )
        let rows = breakdown.rows
        XCTAssertEqual(rows.count, 4)
        XCTAssertEqual(rows.map(\.value), [12, 25, 34, 12])
        XCTAssertEqual(rows.map(\.max), [15, 25, 45, 15])
    }

    func testChallengeStateCallToActionMatchesServerState() {
        XCTAssertEqual(ChallengeState.notStarted.callToAction, "Start")
        XCTAssertEqual(ChallengeState.inProgress.callToAction, "Continue")
        XCTAssertEqual(ChallengeState.complete.callToAction, "Review")
        XCTAssertEqual(ChallengeState.feedbackFailed.callToAction, "Retry coaching")
    }
}
