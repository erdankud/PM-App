import XCTest
@testable import PMThinkingCoach

/// Step gating and form validation (spec §23 step 2, §21 quality acceptance).
final class ChallengeFormStateTests: XCTestCase {

    private func makeState(cards: Int = 4, options: [String] = ["a", "b", "c"]) -> ChallengeFormState {
        ChallengeFormState(totalEvidenceCards: cards, validOptionIds: Set(options))
    }

    // MARK: - Evidence gating

    func testDecisionIsBlockedUntilOneSignalIsReviewed() {
        var state = makeState()
        state.step = .investigate
        XCTAssertFalse(state.canAdvanceToDecision)
        XCTAssertFalse(state.advance())
        XCTAssertEqual(state.step, .investigate)

        state.markReviewed("funnel")
        XCTAssertTrue(state.canAdvanceToDecision)
        XCTAssertTrue(state.advance())
        XCTAssertEqual(state.step, .decide)
    }

    func testReviewingTheSameCardTwiceCountsOnce() {
        var state = makeState()
        state.markReviewed("funnel")
        state.markReviewed("funnel")
        XCTAssertEqual(state.reviewedCount, 1)
        XCTAssertEqual(state.evidenceCounterText, "1 of 4 signals reviewed")
    }

    // MARK: - Rationale validation

    func testSubmitRequiresBothAnOptionAndAValidRationale() {
        var state = makeState()
        state.markReviewed("funnel")
        XCTAssertFalse(state.canSubmit)

        state.select(option: "a")
        XCTAssertFalse(state.canSubmit, "an option alone is not enough")

        state.setRationale(String(repeating: "x", count: 29))
        XCTAssertFalse(state.canSubmit, "29 characters is below the minimum")

        state.setRationale(String(repeating: "x", count: 30))
        XCTAssertTrue(state.canSubmit)
    }

    func testWhitespaceDoesNotCountTowardTheMinimum() {
        var state = makeState()
        state.select(option: "a")
        state.setRationale("   " + String(repeating: "x", count: 25) + "   ")
        XCTAssertFalse(state.canSubmit)
        XCTAssertEqual(state.trimmedRationale.count, 25)
    }

    func testRationaleIsCappedAtTheMaximum() {
        var state = makeState()
        state.setRationale(String(repeating: "x", count: 900))
        XCTAssertEqual(state.rationaleCharacterCount, ChallengeFormState.rationaleMaximum)
        XCTAssertTrue(state.isRationaleValid)
    }

    func testValidationMessageCountsDownToTheMinimum() {
        var state = makeState()
        state.setRationale(String(repeating: "x", count: 10))
        XCTAssertEqual(state.rationaleValidationMessage, "20 more characters to go.")

        state.setRationale(String(repeating: "x", count: 40))
        XCTAssertNil(state.rationaleValidationMessage)
    }

    func testUnknownOptionIsRejected() {
        var state = makeState()
        state.select(option: "not-an-option")
        XCTAssertNil(state.selectedOptionId)
        XCTAssertFalse(state.hasValidOption)
    }

    // MARK: - Immutability after submit

    func testSubmittedAttemptsCannotBeEdited() {
        var state = makeState()
        state.select(option: "a")
        state.setRationale(String(repeating: "x", count: 60))
        state.markSubmitted()

        XCTAssertEqual(state.step, .consequence)
        state.select(option: "b")
        state.setRationale("changed my mind entirely about this decision")
        XCTAssertEqual(state.selectedOptionId, "a")
        XCTAssertEqual(state.rationale.count, 60)
        XCTAssertFalse(state.canSubmit)
    }

    func testBackIsUnavailableAfterSubmission() {
        var state = makeState()
        state.markReviewed("funnel")
        state.step = .decide
        state.markSubmitted()
        XCTAssertFalse(state.goBack())
        XCTAssertEqual(state.step, .consequence)
    }

    // MARK: - Navigation

    func testBackMovesAmongPreSubmissionStepsOnly() {
        var state = makeState()
        XCTAssertFalse(state.goBack(), "cannot go back from the first step")

        state.step = .investigate
        XCTAssertTrue(state.goBack())
        XCTAssertEqual(state.step, .brief)

        state.step = .decide
        XCTAssertTrue(state.goBack())
        XCTAssertEqual(state.step, .investigate)
    }

    func testFeedbackCannotBeReachedBeforeSubmission() {
        var state = makeState()
        state.markReviewed("funnel")
        state.step = .decide
        XCTAssertFalse(state.advance(), "decide cannot advance until submitted")
        XCTAssertEqual(state.step, .decide)
    }

    func testStepIsDerivedFromServerState() {
        XCTAssertEqual(ChallengeFormState.step(for: .notStarted), .brief)
        XCTAssertEqual(ChallengeFormState.step(for: .inProgress), .brief)
        XCTAssertEqual(ChallengeFormState.step(for: .submitted), .consequence)
        XCTAssertEqual(ChallengeFormState.step(for: .awaitingFeedback), .consequence)
        XCTAssertEqual(ChallengeFormState.step(for: .feedbackFailed), .consequence)
        XCTAssertEqual(ChallengeFormState.step(for: .complete), .feedback)
    }

    func testDraftProgressDetection() {
        var state = makeState()
        XCTAssertFalse(state.hasDraftProgress)
        state.markReviewed("funnel")
        XCTAssertTrue(state.hasDraftProgress)
    }
}
