import Foundation

/// Pure step-gating and form validation, kept free of networking so it can be unit
/// tested directly (spec §23 step 2, §21 quality acceptance).
struct ChallengeFormState: Equatable {

    enum Step: Int, CaseIterable, Comparable {
        case brief = 0
        case investigate
        case decide
        case consequence
        case feedback

        static func < (lhs: Step, rhs: Step) -> Bool { lhs.rawValue < rhs.rawValue }

        var title: String {
            switch self {
            case .brief: return S.Challenge.Step.situation
            case .investigate: return S.Challenge.Step.investigate
            case .decide: return S.Challenge.Step.decide
            case .consequence: return S.Challenge.Step.consequence
            case .feedback: return S.Challenge.Step.feedback
            }
        }

        /// Steps the user can move backwards among before submitting (spec §9).
        var isPreSubmission: Bool { self <= .decide }
    }

    let totalEvidenceCards: Int
    let validOptionIds: Set<String>
    var step: Step = .brief
    var reviewedEvidenceIds: Set<String> = []
    var selectedOptionId: String?
    var rationale: String = ""
    var isSubmitted: Bool = false

    static let rationaleMinimum = AppConfig.rationaleMinimum
    static let rationaleMaximum = AppConfig.rationaleMaximum

    // MARK: - Derived

    var reviewedCount: Int { reviewedEvidenceIds.count }

    var evidenceCounterText: String {
        S.Challenge.evidenceCounter(reviewedCount, totalEvidenceCards)
    }

    var trimmedRationale: String {
        rationale.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var rationaleCharacterCount: Int { rationale.count }

    /// At least one evidence card must be opened before a decision can be made (P0-06).
    var canAdvanceToDecision: Bool { reviewedCount >= 1 }

    var hasValidOption: Bool {
        guard let selectedOptionId else { return false }
        return validOptionIds.contains(selectedOptionId)
    }

    var isRationaleValid: Bool {
        (Self.rationaleMinimum...Self.rationaleMaximum).contains(trimmedRationale.count)
    }

    /// Submit stays disabled until both a decision and a valid rationale exist (P0-07).
    var canSubmit: Bool { !isSubmitted && hasValidOption && isRationaleValid }

    var rationaleValidationMessage: String? {
        let count = trimmedRationale.count
        if count == 0 { return nil }
        if count < Self.rationaleMinimum {
            return S.Challenge.charactersToGo(Self.rationaleMinimum - count)
        }
        if count > Self.rationaleMaximum {
            return S.Challenge.charactersOver(count - Self.rationaleMaximum)
        }
        return nil
    }

    var hasDraftProgress: Bool {
        selectedOptionId != nil || !trimmedRationale.isEmpty || !reviewedEvidenceIds.isEmpty
    }

    // MARK: - Transitions

    mutating func markReviewed(_ evidenceId: String) {
        reviewedEvidenceIds.insert(evidenceId)
    }

    mutating func select(option id: String) {
        guard validOptionIds.contains(id), !isSubmitted else { return }
        selectedOptionId = id
    }

    mutating func setRationale(_ text: String) {
        guard !isSubmitted else { return }
        rationale = String(text.prefix(Self.rationaleMaximum))
    }

    /// Returns true when the move was allowed.
    @discardableResult
    mutating func advance() -> Bool {
        switch step {
        case .brief:
            step = .investigate
            return true
        case .investigate:
            guard canAdvanceToDecision else { return false }
            step = .decide
            return true
        case .decide:
            guard isSubmitted else { return false }
            step = .consequence
            return true
        case .consequence:
            step = .feedback
            return true
        case .feedback:
            return false
        }
    }

    @discardableResult
    mutating func goBack() -> Bool {
        // Submitted attempts are immutable; there is no route back into editing (spec §9).
        guard step.isPreSubmission, !isSubmitted, step != .brief else { return false }
        step = Step(rawValue: step.rawValue - 1) ?? .brief
        return true
    }

    mutating func markSubmitted() {
        isSubmitted = true
        step = .consequence
    }

    /// Rebuilds the step from an authoritative server state after a reopen (spec §16).
    static func step(for state: ChallengeState) -> Step {
        switch state {
        case .notStarted: return .brief
        case .inProgress: return .brief
        case .submitted, .awaitingFeedback, .feedbackFailed: return .consequence
        case .complete: return .feedback
        }
    }
}
