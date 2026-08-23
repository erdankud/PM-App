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
                            Text("You chose")
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(Theme.Palette.secondaryText)
                            Text(consequence.optionLabel)
                                .font(.title3.weight(.bold))
                                .fixedSize(horizontal: false, vertical: true)
                        }

                        CardContainer {
                            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                                Label("What happens next", systemImage: "arrow.turn.down.right")
                                    .font(.footnote.weight(.semibold))
                                    .foregroundStyle(Theme.Palette.accent)
                                Text(consequence.text)
                                    .font(.body)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    } else {
                        LoadingState(message: "Loading the outcome…")
                    }

                    statusSection
                }
                .padding(Theme.Spacing.l)
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
        case .complete: return "See coaching"
        case .failed: return "Retry coaching"
        case .pending: return viewModel.isPollingFeedback ? "Preparing coaching…" : "Check again"
        }
    }

    @ViewBuilder
    private var statusSection: some View {
        switch feedbackStatus {
        case .complete:
            InlineNotice(
                text: "Your coaching is ready.",
                systemImage: "checkmark.circle",
                tint: Theme.Palette.positive
            )
        case .pending:
            InlineNotice(
                text: "Coaching is taking a moment. Your answer is saved — you can leave and "
                    + "come back to it from Today.",
                systemImage: "hourglass",
                tint: Theme.Palette.secondaryText
            )
        case .failed:
            InlineNotice(
                text: "Coaching didn't finish this time. Your answer and this outcome are "
                    + "saved, and XP is pending until coaching completes.",
                systemImage: "exclamationmark.triangle",
                tint: Theme.Palette.caution
            )
        }
    }
}
