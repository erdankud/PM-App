import Foundation

/// Onboarding state machine (spec §10.2-§10.4, §18).
///
/// The step is derived from the server's onboarding status, so closing the app mid-way
/// resumes at the last completed step rather than starting over.
@MainActor
final class OnboardingViewModel: ObservableObject {

    enum Step: Equatable {
        case goal
        case assessment
        case pathReveal
    }

    @Published private(set) var step: Step = .goal
    @Published private(set) var assessmentState: AssessmentState?
    @Published private(set) var result: AssessmentResult?
    @Published var selectedGoal: String?
    @Published var currentChoiceId: String?
    @Published var currentRationale: String = ""
    @Published private(set) var isBusy = false
    @Published var error: APIError?

    let goals: [(id: String, title: String, subtitle: String)] = [
        ("break_into_pm", "Break into PM",
         "Build the judgment interviews actually test."),
        ("grow_in_first_role", "Grow in my first PM role",
         "Sharpen instincts outside your day job."),
        ("practise_product_thinking", "Practise product thinking",
         "Keep a short daily habit of real decisions.")
    ]

    private let client: any APIClientProtocol
    private let session: SessionStore
    private let analytics: any AnalyticsTracking

    init(client: any APIClientProtocol, session: SessionStore, analytics: any AnalyticsTracking) {
        self.client = client
        self.session = session
        self.analytics = analytics
        self.selectedGoal = session.me?.goal
        self.step = Self.step(for: session.me?.status ?? .signedIn)
    }

    static func step(for status: MeResponse.OnboardingStatus) -> Step {
        switch status {
        case .signedIn: return .goal
        case .goalSet: return .assessment
        case .assessed, .complete, .deleted: return .pathReveal
        }
    }

    var canContinueFromGoal: Bool { selectedGoal != nil }
    var canSubmitAssessmentAnswer: Bool { currentChoiceId != nil }

    // MARK: - Goal

    func saveGoal() async {
        guard let goal = selectedGoal else { return }
        await run {
            let profile = try await self.client.updateProfile(
                ProfileUpdateRequest(goal: goal, timezone: TimeZone.current.identifier,
                                     completeOnboarding: nil)
            )
            self.analytics.track(.onboardingGoalSelected(goal: goal))
            self.session.apply(profile)
            self.step = .assessment
            await self.loadAssessment()
        }
    }

    // MARK: - Assessment

    func loadAssessment() async {
        await run {
            let state = try await self.client.assessment()
            self.assessmentState = state
            if state.completed {
                self.result = try? await self.client.assessmentResult()
                self.step = .pathReveal
            }
        }
    }

    func submitAnswer() async {
        guard let item = assessmentState?.nextItem, let choiceId = currentChoiceId else { return }
        let trimmed = currentRationale.trimmingCharacters(in: .whitespacesAndNewlines)
        await run {
            let response = try await self.client.answerAssessment(
                AssessmentAnswerRequest(
                    itemId: item.id,
                    choiceId: choiceId,
                    rationale: trimmed.isEmpty ? nil : trimmed
                )
            )
            self.analytics.track(
                .assessmentItemCompleted(itemId: item.id, choiceId: choiceId, index: item.index)
            )
            self.currentChoiceId = nil
            self.currentRationale = ""

            if response.completed, let result = response.result {
                self.result = result
                self.assessmentState = AssessmentState(
                    notice: self.assessmentState?.notice ?? "",
                    totalItems: item.total,
                    completedItems: item.total,
                    completed: true,
                    nextItem: nil
                )
                self.step = .pathReveal
            } else {
                self.assessmentState = AssessmentState(
                    notice: self.assessmentState?.notice ?? "",
                    totalItems: item.total,
                    completedItems: item.index,
                    completed: false,
                    nextItem: response.nextItem
                )
            }
        }
    }

    // MARK: - Path reveal

    func loadResultIfNeeded() async {
        guard result == nil else { return }
        await run {
            self.result = try await self.client.assessmentResult()
        }
    }

    func finishOnboarding() async {
        await run {
            let profile = try await self.client.updateProfile(
                ProfileUpdateRequest(goal: nil, timezone: TimeZone.current.identifier,
                                     completeOnboarding: true)
            )
            self.analytics.track(
                .onboardingCompleted(
                    startingLevel: profile.startingLevel ?? "unknown",
                    focusSkills: profile.focusSkills.joined(separator: ",")
                )
            )
            self.session.apply(profile)
        }
    }

    // MARK: - Helpers

    private func run(_ operation: @escaping () async throws -> Void) async {
        isBusy = true
        error = nil
        defer { isBusy = false }
        do {
            try await operation()
        } catch let apiError as APIError {
            error = apiError
        } catch {
            self.error = .server(status: -1, code: "unknown")
        }
    }
}
