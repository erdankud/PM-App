import SwiftUI

/// Consequences (spec §10.9, P0-08).
/// This text is authored and arrives with the submission, so it never depends on the
/// AI evaluation being available.
struct ConsequenceStepView: View {
    @ObservedObject var viewModel: ChallengeViewModel

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    if let consequence = viewModel.consequence {
                        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                            Text(S.Challenge.youChose)
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(Theme.Palette.secondaryText)
                            Text(consequence.optionLabel)
                                .font(.title3.weight(.bold))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .appear(0)

                        CardContainer(isHighlighted: true) {
                            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                                Label(
                                    S.Challenge.whatHappensNext,
                                    systemImage: "arrow.turn.down.right"
                                )
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(Theme.Palette.accent)
                                Text(consequence.text)
                                    .font(.body)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                        .appear(1)
                    } else {
                        LoadingState(message: S.Challenge.loadingOutcome)
                    }

                    statusSection.appear(2)
                }
                .padding(Theme.Spacing.l)
                .animation(Motion.standard, value: feedbackStatus)
            }

            PrimaryButton(
                title: buttonTitle,
                isLoading: viewModel.isPollingFeedback && feedbackStatus == .pending
            ) {
                if feedbackStatus == .failed {
                    Task { await viewModel.retryCoaching() }
                } else {
                    viewModel.advance()
                }
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
        .task { await viewModel.refreshFeedback() }
    }

    private var feedbackStatus: FeedbackStatus {
        viewModel.feedback?.status ?? .pending
    }

    private var buttonTitle: String {
        switch feedbackStatus {
        case .complete: return S.Challenge.seeCoaching
        case .failed: return S.Challenge.retryCoaching
        case .pending:
            return viewModel.isPollingFeedback
                ? S.Challenge.preparingCoaching : S.Challenge.checkAgain
        }
    }

    @ViewBuilder
    private var statusSection: some View {
        switch feedbackStatus {
        case .complete:
            InlineNotice(
                text: S.Challenge.coachingReady,
                systemImage: "checkmark.circle",
                tint: Theme.Palette.positive
            )
        case .pending:
            InlineNotice(
                text: S.Challenge.coachingPending,
                systemImage: "hourglass",
                tint: Theme.Palette.secondaryText
            )
        case .failed:
            InlineNotice(
                text: S.Challenge.coachingFailedNotice,
                systemImage: "exclamationmark.triangle",
                tint: Theme.Palette.caution
            )
        }
    }
}
