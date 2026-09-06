import Foundation
@testable import PMThinkingCoach

/// In-memory stand-in for the API so view-model behaviour can be tested without a server.
final class StubAPIClient: APIClientProtocol, @unchecked Sendable {

    var challengeResponse: ChallengeResponse?
    var treeResponse: TreeResponse?
    var blockResponse: BlockDetailResponse?
    var lessonResponse: LessonResponse?
    var lessonCompleteResponse: LessonCompleteResponse?
    var submitResponse: SubmitResponse?
    var feedbackResponses: [FeedbackResponse] = []
    var challengeError: APIError?
    var submitError: APIError?

    private(set) var recordedEvidenceIds: [String] = []
    private(set) var draftSaves: [DraftRequest] = []
    private(set) var submitCalls: [(request: SubmitRequest, key: String)] = []
    private(set) var ratings: [String] = []
    private(set) var feedbackFetches = 0
    private(set) var completedLessonIds: [String] = []
    private(set) var gateStarts: [String] = []

    // MARK: - Challenge

    // MARK: - Skill tree

    func tree() async throws -> TreeResponse {
        guard let treeResponse else { throw APIError.notFound }
        return treeResponse
    }

    var treesResponse: TreesResponse?
    var glossaryResponse: GlossaryResponse?
    var exerciseResponse: ExerciseResponse?
    var exerciseSubmitResponse: ExerciseSubmitResponse?

    func trees() async throws -> TreesResponse {
        guard let treesResponse else { throw APIError.notFound }
        return treesResponse
    }

    func tree(kind: String) async throws -> TreeResponse {
        try await tree()
    }

    func glossary(query: String?, blockId: String?) async throws -> GlossaryResponse {
        guard let glossaryResponse else { throw APIError.notFound }
        return glossaryResponse
    }

    func exercise(id: String) async throws -> ExerciseResponse {
        guard let exerciseResponse else { throw APIError.notFound }
        return exerciseResponse
    }

    func submitExercise(
        id: String, values: [String: String]
    ) async throws -> ExerciseSubmitResponse {
        guard let exerciseSubmitResponse else { throw APIError.notFound }
        return exerciseSubmitResponse
    }

    func block(id: String) async throws -> BlockDetailResponse {
        guard let blockResponse else { throw APIError.notFound }
        return blockResponse
    }

    func lesson(id: String) async throws -> LessonResponse {
        guard let lessonResponse else { throw APIError.notFound }
        return lessonResponse
    }

    var downloadedAudioPaths: [String] = []
    var audioFileURL: URL?

    var generatedAudioLessonIds: [String] = []
    var generateAudioResponse: LessonAudioView?

    func generateAudio(lessonId: String) async throws -> LessonAudioView {
        generatedAudioLessonIds.append(lessonId)
        guard let generateAudioResponse else { throw APIError.notFound }
        return generateAudioResponse
    }

    func downloadAudio(path: String, cacheKey: String) async throws -> URL {
        downloadedAudioPaths.append(path)
        guard let audioFileURL else { throw APIError.notFound }
        return audioFileURL
    }

    func completeLesson(id: String) async throws -> LessonCompleteResponse {
        completedLessonIds.append(id)
        guard let lessonCompleteResponse else { throw APIError.notFound }
        return lessonCompleteResponse
    }

    func startGate(id: String) async throws -> ChallengeResponse {
        gateStarts.append(id)
        if let challengeError { throw challengeError }
        guard let challengeResponse else { throw APIError.notFound }
        return challengeResponse
    }

    func saveDraft(attemptId: String, request: DraftRequest) async throws -> DraftResponse {
        draftSaves.append(request)
        return DraftResponse(
            attemptId: attemptId,
            status: "draft",
            selectedOptionId: request.selectedOptionId,
            rationaleLength: request.rationale?.count ?? 0,
            savedAt: "2026-08-23T10:00:00Z"
        )
    }

    func recordEvidence(attemptId: String, cardId: String) async throws -> EvidenceResponse {
        if !recordedEvidenceIds.contains(cardId) { recordedEvidenceIds.append(cardId) }
        return EvidenceResponse(
            attemptId: attemptId,
            reviewedEvidenceIds: recordedEvidenceIds,
            reviewedCount: recordedEvidenceIds.count,
            totalCount: challengeResponse?.scenario.evidenceCards.count ?? 0
        )
    }

    func submit(
        attemptId: String, request: SubmitRequest, idempotencyKey: String
    ) async throws -> SubmitResponse {
        submitCalls.append((request, idempotencyKey))
        if let submitError { throw submitError }
        guard let submitResponse else { throw APIError.server(status: 500, code: nil) }
        return submitResponse
    }

    func feedback(attemptId: String) async throws -> FeedbackResponse {
        feedbackFetches += 1
        guard !feedbackResponses.isEmpty else { throw APIError.notFound }
        if feedbackResponses.count == 1 { return feedbackResponses[0] }
        return feedbackResponses.removeFirst()
    }

    func retryFeedback(attemptId: String) async throws -> FeedbackResponse {
        try await feedback(attemptId: attemptId)
    }

    func rateFeedback(attemptId: String, rating: String) async throws {
        ratings.append(rating)
    }

    // MARK: - Unused in these tests

    func authMethods() async throws -> AuthMethodsResponse {
        AuthMethodsResponse(
            password: true, google: false, apple: false, developer: true, googleClientId: nil
        )
    }
    func signUp(email: String, password: String, timezone: String) async throws -> AuthResponse {
        throw APIError.notFound
    }
    func signIn(email: String, password: String, timezone: String) async throws -> AuthResponse {
        throw APIError.notFound
    }
    func signInWithGoogle(idToken: String, timezone: String) async throws -> AuthResponse {
        throw APIError.notFound
    }
    func signInWithApple(identityToken: String, timezone: String) async throws -> AuthResponse {
        throw APIError.notFound
    }
    func signInDeveloper(deviceId: String, timezone: String) async throws -> AuthResponse {
        throw APIError.notFound
    }
    func refresh(refreshToken: String) async throws -> AuthResponse { throw APIError.notFound }
    func signOut(refreshToken: String?) async throws {}
    func me() async throws -> MeResponse { throw APIError.notFound }
    func updateProfile(_ request: ProfileUpdateRequest) async throws -> MeResponse {
        throw APIError.notFound
    }
    func deleteAccount() async throws {}
    func progress() async throws -> ProgressResponse { throw APIError.notFound }
    func history(limit: Int, offset: Int) async throws -> HistoryResponse { throw APIError.notFound }
    func sendEvents(_ batch: AnalyticsBatch) async throws {}
}

// MARK: - Fixtures

enum Fixture {

    static func scenario(cards: Int = 3, options: Int = 3) -> ScenarioView {
        ScenarioView(
            id: "onboarding-retention-drop",
            version: 1,
            title: "Retention drops after an onboarding redesign",
            summary: "A redesigned signup flow lifted completion but week-one retention fell.",
            estimatedMinutes: 8,
            level: "foundation",
            primarySkill: "discovery",
            primarySkillLabel: "Дискавери и исследования",
            tags: ["onboarding", "retention"],
            brief: BriefView(
                role: "You are the PM for growth.",
                company: "Tempo, a consumer habit app.",
                context: "The team shipped a shorter onboarding flow ten days ago.",
                objective: "Protect week-one retention.",
                constraints: "Two engineers this sprint.",
                task: "Recommend what the team does next.",
                whatGoodLooksLike: "Use the evidence, make a trade-off, and explain your choice."
            ),
            evidenceCards: (0..<cards).map { index in
                EvidenceCard(
                    id: "card-\(index)",
                    title: "Signal \(index)",
                    type: "quantitative",
                    order: index + 1,
                    content: "Some authored evidence for signal \(index)."
                )
            },
            decisionPrompt: "What do you recommend the team does next?",
            decisionOptions: (0..<options).map { index in
                DecisionOption(
                    id: "option-\(index)",
                    label: "Option \(index)",
                    description: "A plausible course of action number \(index)."
                )
            }
        )
    }

    static func challenge(state: ChallengeState = .notStarted) -> ChallengeResponse {
        let scenario = scenario()
        return ChallengeResponse(
            gateId: "gate-d1",
            blockId: "D1",
            blockTitle: "Услышать клиента",
            attemptIndex: 1,
            passThreshold: 70,
            state: state,
            scenario: scenario,
            attempt: AttemptView(
                attemptId: "attempt-1",
                status: state == .notStarted ? "draft" : "submitted",
                selectedOptionId: nil,
                rationale: nil,
                reviewedEvidenceIds: [],
                rationaleMin: 30,
                rationaleMax: 600
            )
        )
    }

    static func submitted() -> SubmitResponse {
        SubmitResponse(
            attemptId: "attempt-1",
            status: "awaiting_feedback",
            consequence: ConsequenceView(
                optionId: "option-0",
                optionLabel: "Option 0",
                text: "The team ships the change and retention recovers over two weeks."
            ),
            feedbackStatus: .pending
        )
    }

    static func feedback(status: FeedbackStatus, score: Int = 78) -> FeedbackResponse {
        FeedbackResponse(
            attemptId: "attempt-1",
            status: status,
            consequence: ConsequenceView(
                optionId: "option-0",
                optionLabel: "Option 0",
                text: "The team ships the change and retention recovers over two weeks."
            ),
            feedback: status == .complete
                ? FeedbackBody(
                    score: score,
                    band: "Solid reasoning",
                    breakdown: ScoreBreakdown(
                        evidence: 12, evidenceMax: 15,
                        decision: 25, decisionMax: 25,
                        rationale: 29, rationaleMax: 45,
                        communication: 12, communicationMax: 15
                    ),
                    strengths: [FeedbackPoint(title: "Named the trade-off", detail: "You said what you gave up.")],
                    improvements: [FeedbackPoint(title: "Add a measure", detail: "Say what you would watch next.")],
                    sharperApproach: "Lead with the recommendation, then the strongest evidence.",
                    skillImpact: [
                        SkillImpact(key: "discovery", label: "Дискавери", delta: 4, score: 58)
                    ],
                    xpAwarded: 78,
                    needsRetry: false
                )
                : nil,
            rating: nil,
            retryAvailable: status == .failed,
            scenarioTitle: "Retention drops after an onboarding redesign",
            learnTakeawayTitle: "Look for the mechanism, not the trade-off",
            gateId: "gate-d1",
            blockId: "D1",
            blockTitle: "Услышать клиента",
            passed: status == .complete ? score >= 70 : nil,
            passThreshold: 70,
            attemptIndex: 1,
            unlockedBlockIds: status == .complete && score >= 70 ? ["V1"] : [],
            remediation: []
        )
    }
}
