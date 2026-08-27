import Foundation

/// Drives the challenge flow: Brief → Investigate → Decide → Consequences → Feedback
/// (spec §10.6-§10.10).
@MainActor
final class ChallengeViewModel: ObservableObject {

    enum Phase: Equatable {
        case loading
        case ready
        case failed(APIError)
    }

    @Published private(set) var phase: Phase = .loading
    @Published private(set) var challenge: ChallengeResponse?
    @Published var form: ChallengeFormState = ChallengeFormState(
        totalEvidenceCards: 0, validOptionIds: []
    )
    @Published private(set) var consequence: ConsequenceView?
    @Published private(set) var feedback: FeedbackResponse?
    @Published private(set) var isSubmitting = false
    @Published private(set) var isPollingFeedback = false
    @Published private(set) var draftSavedAt: Date?
    @Published private(set) var isOfflineDraft = false
    @Published var submissionError: APIError?
    @Published var ratingSubmitted: String?

    /// The gate payload comes from `POST /gates/{id}/start`, which is also where
    /// availability is enforced — the client never opens a gate on its own say-so.
    let gateId: String
    let blockId: String
    private let initialChallenge: ChallengeResponse

    private let client: any APIClientProtocol
    private let localStore: LocalStore
    private let analytics: any AnalyticsTracking
    private var autosaveTask: Task<Void, Never>?
    private var pollTask: Task<Void, Never>?
    private var submittedAt: Date?

    init(
        challenge: ChallengeResponse,
        client: any APIClientProtocol,
        localStore: LocalStore,
        analytics: any AnalyticsTracking
    ) {
        self.gateId = challenge.gateId
        self.blockId = challenge.blockId
        self.initialChallenge = challenge
        self.client = client
        self.localStore = localStore
        self.analytics = analytics
    }

    var scenario: ScenarioView? { challenge?.scenario }
    var attemptId: String? { challenge?.attempt.attemptId }

    // MARK: - Loading

    func load() async {
        phase = .loading
        do {
            // Re-entering a gate returns the same open attempt, so this is safe to
            // call again after a background/foreground round trip.
            let response = try await client.startGate(id: gateId)
            challenge = response

            var state = ChallengeFormState(
                totalEvidenceCards: response.scenario.evidenceCards.count,
                validOptionIds: Set(response.scenario.decisionOptions.map(\.id))
            )
            state.reviewedEvidenceIds = Set(response.attempt.reviewedEvidenceIds)
            state.selectedOptionId = response.attempt.selectedOptionId
            state.rationale = response.attempt.rationale ?? ""
            state.isSubmitted = response.state != .notStarted && response.state != .inProgress
            state.step = ChallengeFormState.step(for: response.state)

            // A local draft newer than the server copy wins, so a change made offline is
            // never silently discarded (spec §18).
            if let local = await localStore.draft(forAttempt: response.attempt.attemptId),
               local.pendingSync, !state.isSubmitted {
                state.rationale = local.rationale
                state.selectedOptionId = local.selectedOptionId ?? state.selectedOptionId
                state.reviewedEvidenceIds.formUnion(local.reviewedEvidenceIds)
                isOfflineDraft = true
            }

            form = state
            phase = .ready

            if state.isSubmitted {
                await refreshFeedback()
            }
        } catch let error as APIError {
            // The payload we were handed still works offline; only a cold start fails.
            if challenge == nil { phase = .failed(error) } else { phase = .ready }
        } catch {
            if challenge == nil { phase = .failed(.server(status: -1, code: "unknown")) }
        }
    }

    // MARK: - Investigate

    func openEvidence(_ card: EvidenceCard) {
        guard let attemptId, !form.reviewedEvidenceIds.contains(card.id) else { return }
        form.markReviewed(card.id)
        analytics.track(
            .evidenceOpened(
                scenarioId: scenario?.id ?? "",
                evidenceId: card.id,
                countOpened: form.reviewedCount
            )
        )
        Task {
            _ = try? await client.recordEvidence(attemptId: attemptId, cardId: card.id)
        }
        persistDraftLocally(pendingSync: false)
    }

    // MARK: - Decide

    func select(option: DecisionOption) {
        form.select(option: option.id)
        analytics.track(
            .decisionOptionSelected(scenarioId: scenario?.id ?? "", optionId: option.id)
        )
        scheduleAutosave(immediate: true)
    }

    func updateRationale(_ text: String) {
        form.setRationale(text)
        scheduleAutosave(immediate: false)
    }

    /// Debounced while typing, immediate on an option change. Typing is never blocked
    /// by a sync in flight (spec §16).
    private func scheduleAutosave(immediate: Bool) {
        autosaveTask?.cancel()
        persistDraftLocally(pendingSync: true)
        autosaveTask = Task { [weak self] in
            if !immediate {
                try? await Task.sleep(for: .milliseconds(700))
                if Task.isCancelled { return }
            }
            await self?.syncDraft()
        }
    }

    private func persistDraftLocally(pendingSync: Bool) {
        guard let attemptId, !form.isSubmitted else { return }
        let draft = LocalStore.Draft(
            attemptId: attemptId,
            assignmentId: gateId,
            selectedOptionId: form.selectedOptionId,
            rationale: form.rationale,
            reviewedEvidenceIds: Array(form.reviewedEvidenceIds),
            updatedAt: Date(),
            pendingSync: pendingSync
        )
        Task { await localStore.saveDraft(draft) }
    }

    private func syncDraft() async {
        guard let attemptId, !form.isSubmitted else { return }
        let formatter = ISO8601DateFormatter()
        do {
            let response = try await client.saveDraft(
                attemptId: attemptId,
                request: DraftRequest(
                    selectedOptionId: form.selectedOptionId,
                    rationale: form.rationale,
                    clientUpdatedAt: formatter.string(from: Date())
                )
            )
            draftSavedAt = Date()
            isOfflineDraft = false
            await localStore.markDraftSynced(attemptId: attemptId)
            analytics.track(
                .attemptDraftSaved(
                    scenarioId: scenario?.id ?? "",
                    hasOption: response.selectedOptionId != nil,
                    rationaleLengthBucket: AnalyticsBuckets.rationaleLength(response.rationaleLength)
                )
            )
        } catch {
            // The local copy is already saved; surface offline state and retry later.
            isOfflineDraft = true
        }
    }

    // MARK: - Submit

    func submit() async {
        guard let attemptId, form.canSubmit, !isSubmitting else { return }
        isSubmitting = true
        submissionError = nil
        defer { isSubmitting = false }

        autosaveTask?.cancel()
        let key = await localStore.idempotencyKey(forAttempt: attemptId)

        do {
            let response = try await client.submit(
                attemptId: attemptId,
                request: SubmitRequest(
                    selectedOptionId: form.selectedOptionId ?? "",
                    rationale: form.trimmedRationale
                ),
                idempotencyKey: key
            )
            submittedAt = Date()
            consequence = response.consequence
            form.markSubmitted()
            analytics.track(
                .attemptSubmitted(
                    scenarioId: scenario?.id ?? "",
                    evidenceCount: form.reviewedCount,
                    rationaleLengthBucket: AnalyticsBuckets.rationaleLength(form.trimmedRationale.count)
                )
            )
            await localStore.removeDraft(attemptId: attemptId)
            startFeedbackPolling()
        } catch let error as APIError {
            submissionError = error
        } catch {
            submissionError = .server(status: -1, code: "unknown")
        }
    }

    // MARK: - Feedback

    /// Bounded polling, then a pending state the user can act on. No endless spinner.
    private func startFeedbackPolling() {
        pollTask?.cancel()
        guard let attemptId else { return }
        isPollingFeedback = true
        pollTask = Task { [weak self] in
            guard let self else { return }
            for attempt in 0..<AppConfig.feedbackPollAttempts {
                if Task.isCancelled { break }
                if attempt > 0 {
                    try? await Task.sleep(for: AppConfig.feedbackPollInterval)
                }
                guard let response = try? await self.client.feedback(attemptId: attemptId) else {
                    continue
                }
                await self.apply(feedback: response)
                if response.status != .pending { break }
            }
            self.isPollingFeedback = false
        }
    }

    func refreshFeedback() async {
        guard let attemptId else { return }
        do {
            let response = try await client.feedback(attemptId: attemptId)
            await apply(feedback: response)
        } catch {
            // Keep whatever is on screen; the retry control stays available.
        }
    }

    func retryCoaching() async {
        guard let attemptId else { return }
        isPollingFeedback = true
        defer { isPollingFeedback = false }
        if let response = try? await client.retryFeedback(attemptId: attemptId) {
            await apply(feedback: response)
        }
        startFeedbackPolling()
    }

    private func apply(feedback response: FeedbackResponse) async {
        feedback = response
        consequence = response.consequence
        ratingSubmitted = response.rating

        let latency = submittedAt.map { Date().timeIntervalSince($0) } ?? 0
        analytics.track(
            .feedbackStatusChanged(
                scenarioId: scenario?.id ?? "",
                status: response.status.rawValue,
                latencyBucket: AnalyticsBuckets.latency(latency),
                errorCode: response.status == .failed ? "evaluation_failed" : nil
            )
        )
        if response.status == .complete, let body = response.feedback {
            analytics.track(
                .feedbackViewed(
                    scenarioId: scenario?.id ?? "",
                    scoreBand: AnalyticsBuckets.scoreBand(body.score)
                )
            )
            await localStore.clearSubmission(attemptId: response.attemptId)
        }
    }

    func rate(_ rating: String) async {
        guard let attemptId else { return }
        ratingSubmitted = rating
        analytics.track(.feedbackRated(scenarioId: scenario?.id ?? "", rating: rating))
        try? await client.rateFeedback(attemptId: attemptId, rating: rating)
    }

    // MARK: - Navigation

    func advance() {
        if form.step == .consequence {
            form.advance()
            Task { await refreshFeedback() }
            return
        }
        form.advance()
    }

    func goBack() {
        form.goBack()
    }

    func leave() {
        autosaveTask?.cancel()
        pollTask?.cancel()
        Task { await syncDraft() }
    }
}
