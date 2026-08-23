import XCTest
@testable import PMThinkingCoach

@MainActor
final class ChallengeViewModelTests: XCTestCase {

    private func makeViewModel(
        client: StubAPIClient
    ) -> ChallengeViewModel {
        ChallengeViewModel(
            assignmentId: "assignment-1",
            client: client,
            localStore: LocalStore(filename: "test-store-\(UUID().uuidString).json"),
            analytics: NoopAnalytics()
        )
    }

    func testLoadPopulatesFormFromTheServerState() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge()
        let viewModel = makeViewModel(client: client)

        await viewModel.load()

        XCTAssertEqual(viewModel.phase, .ready)
        XCTAssertEqual(viewModel.form.totalEvidenceCards, 3)
        XCTAssertEqual(viewModel.form.step, .brief)
        XCTAssertFalse(viewModel.form.isSubmitted)
    }

    func testLoadFailureSurfacesARetryableState() async {
        let client = StubAPIClient()
        client.challengeError = .offline
        let viewModel = makeViewModel(client: client)

        await viewModel.load()

        XCTAssertEqual(viewModel.phase, .failed(.offline))
    }

    func testSubmitIsBlockedUntilTheFormIsValid() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge()
        client.submitResponse = Fixture.submitted()
        let viewModel = makeViewModel(client: client)
        await viewModel.load()

        await viewModel.submit()
        XCTAssertTrue(client.submitCalls.isEmpty, "submitting an invalid form must not call the API")

        viewModel.select(option: viewModel.scenario!.decisionOptions[0])
        viewModel.updateRationale(String(repeating: "x", count: 45))
        XCTAssertTrue(viewModel.form.canSubmit)
    }

    func testSubmitStoresConsequenceAndLocksTheAttempt() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge()
        client.submitResponse = Fixture.submitted()
        client.feedbackResponses = [Fixture.feedback(status: .complete)]
        let viewModel = makeViewModel(client: client)
        await viewModel.load()

        viewModel.openEvidence(viewModel.scenario!.evidenceCards[0])
        viewModel.select(option: viewModel.scenario!.decisionOptions[0])
        viewModel.updateRationale(
            "I would take this option because the evidence points at one step, and I accept "
            + "slower delivery in exchange for reversibility."
        )

        await viewModel.submit()

        XCTAssertEqual(client.submitCalls.count, 1)
        XCTAssertTrue(viewModel.form.isSubmitted)
        XCTAssertEqual(viewModel.form.step, .consequence)
        XCTAssertNotNil(viewModel.consequence)
        XCTAssertFalse(viewModel.consequence?.text.isEmpty ?? true)
    }

    func testRepeatedSubmitReusesTheSameIdempotencyKey() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge()
        client.submitResponse = Fixture.submitted()
        let store = LocalStore(filename: "test-store-\(UUID().uuidString).json")
        let viewModel = ChallengeViewModel(
            assignmentId: "assignment-1", client: client, localStore: store,
            analytics: NoopAnalytics()
        )
        await viewModel.load()
        viewModel.select(option: viewModel.scenario!.decisionOptions[0])
        viewModel.updateRationale(String(repeating: "x", count: 45))

        let first = await store.idempotencyKey(forAttempt: "attempt-1")
        let second = await store.idempotencyKey(forAttempt: "attempt-1")
        XCTAssertEqual(first, second, "the key must survive until the submission resolves")

        await viewModel.submit()
        XCTAssertEqual(client.submitCalls.first?.key, first)
    }

    func testOpeningEvidenceIsRecordedOnceAndUnlocksTheDecision() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge()
        let viewModel = makeViewModel(client: client)
        await viewModel.load()

        let card = viewModel.scenario!.evidenceCards[0]
        viewModel.openEvidence(card)
        viewModel.openEvidence(card)

        XCTAssertEqual(viewModel.form.reviewedCount, 1)
        XCTAssertTrue(viewModel.form.canAdvanceToDecision)
    }

    func testReopeningASubmittedAttemptLandsOnTheConsequenceStep() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge(state: .awaitingFeedback)
        client.feedbackResponses = [Fixture.feedback(status: .pending)]
        let viewModel = makeViewModel(client: client)

        await viewModel.load()

        XCTAssertTrue(viewModel.form.isSubmitted)
        XCTAssertEqual(viewModel.form.step, .consequence)
        XCTAssertEqual(viewModel.feedback?.status, .pending)
    }

    func testCompletedAttemptOpensOnFeedback() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge(state: .complete)
        client.feedbackResponses = [Fixture.feedback(status: .complete)]
        let viewModel = makeViewModel(client: client)

        await viewModel.load()

        XCTAssertEqual(viewModel.form.step, .feedback)
        XCTAssertEqual(viewModel.feedback?.feedback?.score, 78)
    }

    func testRatingIsSentOnce() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge(state: .complete)
        client.feedbackResponses = [Fixture.feedback(status: .complete)]
        let viewModel = makeViewModel(client: client)
        await viewModel.load()

        await viewModel.rate("useful")

        XCTAssertEqual(client.ratings, ["useful"])
        XCTAssertEqual(viewModel.ratingSubmitted, "useful")
    }

    func testFailedEvaluationKeepsTheConsequenceAndOffersRetry() async {
        let client = StubAPIClient()
        client.challengeResponse = Fixture.challenge(state: .feedbackFailed)
        client.feedbackResponses = [Fixture.feedback(status: .failed)]
        let viewModel = makeViewModel(client: client)

        await viewModel.load()

        XCTAssertEqual(viewModel.feedback?.status, .failed)
        XCTAssertTrue(viewModel.feedback?.retryAvailable ?? false)
        XCTAssertNotNil(viewModel.consequence)
        XCTAssertNil(viewModel.feedback?.feedback, "no feedback body is invented on device")
    }
}
