import SwiftUI

/// AI feedback (spec §10.10).
/// Sections appear in the specified order. Nothing here is generated on device — if the
/// server has no validated evaluation, the screen says so instead.
struct FeedbackStepView: View {
    @ObservedObject var viewModel: ChallengeViewModel
    let onFinish: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    if let feedback = viewModel.feedback, let body = feedback.feedback {
                        completeContent(feedback, body)
                    } else {
                        unavailableContent
                    }
                }
                .padding(Theme.Spacing.l)
            }

            PrimaryButton(title: "Finish") { onFinish() }
                .padding(Theme.Spacing.l)
                .background(.bar)
        }
        .task { await viewModel.refreshFeedback() }
    }

    // MARK: - Complete

    private func completeContent(_ response: FeedbackResponse, _ body: FeedbackBody) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
            CardContainer {
                VStack(spacing: Theme.Spacing.m) {
                    ScoreHeadline(score: body.score, band: body.band)
                    if body.xpAwarded > 0 {
                        Chip(
                            text: "+\(body.xpAwarded) XP",
                            systemImage: "sparkles",
                            tint: Theme.Palette.accent
                        )
                    }
                    breakdown(body.breakdown)
                }
            }

            if body.needsRetry {
                InlineNotice(
                    text: "There wasn't much reasoning to work with this time. A longer answer "
                        + "gives the coaching more to respond to.",
                    systemImage: "info.circle",
                    tint: Theme.Palette.caution
                )
            }

            pointsSection(
                title: "What you did well",
                symbol: "checkmark.seal",
                tint: Theme.Palette.positive,
                points: body.strengths
            )

            pointsSection(
                title: "What to strengthen",
                symbol: "arrow.up.forward",
                tint: Theme.Palette.caution,
                points: body.improvements
            )

            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                SectionHeader(title: "A sharper approach")
                CardContainer {
                    Text(body.sharperApproach)
                        .font(.body)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            skillImpactSection(body.skillImpact)

            ratingSection(response)

            InlineNotice(
                text: "Skill scores are practice signals based on your in-app work, not an "
                    + "assessment of job readiness."
            )
        }
    }

    private func breakdown(_ breakdown: ScoreBreakdown) -> some View {
        VStack(spacing: Theme.Spacing.s) {
            ForEach(breakdown.rows, id: \.label) { row in
                HStack {
                    Text(row.label)
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.secondaryText)
                    Spacer()
                    Text("\(row.value)/\(row.max)")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(Theme.Palette.primaryText)
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel("\(row.label): \(row.value) out of \(row.max)")
            }
        }
        .padding(.top, Theme.Spacing.s)
    }

    private func pointsSection(
        title: String, symbol: String, tint: Color, points: [FeedbackPoint]
    ) -> some View {
        Group {
            if points.isEmpty {
                EmptyView()
            } else {
                VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                    SectionHeader(title: title)
                    ForEach(points) { point in
                        CardContainer {
                            HStack(alignment: .top, spacing: Theme.Spacing.m) {
                                Image(systemName: symbol)
                                    .foregroundStyle(tint)
                                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                                    Text(point.title).font(.headline)
                                    Text(point.detail)
                                        .font(.subheadline)
                                        .foregroundStyle(Theme.Palette.secondaryText)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                        .accessibilityElement(children: .combine)
                    }
                }
            }
        }
    }

    private func skillImpactSection(_ impacts: [SkillImpact]) -> some View {
        Group {
            if impacts.isEmpty {
                EmptyView()
            } else {
                VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                    SectionHeader(
                        title: "Skill impact",
                        subtitle: "Only the skills this challenge touched."
                    )
                    CardContainer {
                        VStack(spacing: Theme.Spacing.m) {
                            ForEach(impacts) { impact in
                                HStack {
                                    Text(impact.label).font(.subheadline)
                                    Spacer()
                                    Text(impact.deltaText)
                                        .font(.subheadline.weight(.semibold).monospacedDigit())
                                        .foregroundStyle(
                                            impact.delta >= 0
                                                ? Theme.Palette.positive : Theme.Palette.caution
                                        )
                                    Text("→ \(impact.score)")
                                        .font(.subheadline.monospacedDigit())
                                        .foregroundStyle(Theme.Palette.secondaryText)
                                }
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(
                                    "\(impact.label) changed by \(impact.delta), now \(impact.score)"
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    private func ratingSection(_ response: FeedbackResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            SectionHeader(title: "Was this useful?")
            HStack(spacing: Theme.Spacing.m) {
                ratingButton(title: "Useful", symbol: "hand.thumbsup", value: "useful")
                ratingButton(title: "Not useful", symbol: "hand.thumbsdown", value: "not_useful")
            }
            if viewModel.ratingSubmitted != nil {
                InlineNotice(text: "Thanks — this helps us improve the coaching.")
            }
        }
    }

    private func ratingButton(title: String, symbol: String, value: String) -> some View {
        let isSelected = viewModel.ratingSubmitted == value
        return Button {
            Task { await viewModel.rate(value) }
        } label: {
            Label(title, systemImage: symbol)
                .frame(maxWidth: .infinity, minHeight: Theme.minimumTapTarget)
        }
        .buttonStyle(.bordered)
        .tint(isSelected ? Theme.Palette.accent : Theme.Palette.neutral)
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }

    // MARK: - Pending / failed

    private var unavailableContent: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
            if let consequence = viewModel.consequence {
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
            }

            CardContainer {
                VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                    Label(
                        viewModel.feedback?.status == .failed
                            ? "Coaching didn't finish" : "Coaching is taking longer",
                        systemImage: "hourglass"
                    )
                    .font(.headline)

                    Text(
                        "Your answer is saved and your XP is pending until coaching completes. "
                        + "Nothing is lost — you can come back to this from Progress."
                    )
                    .font(.subheadline)
                    .foregroundStyle(Theme.Palette.secondaryText)
                    .fixedSize(horizontal: false, vertical: true)

                    SecondaryButton(title: "Retry coaching", systemImage: "arrow.clockwise") {
                        Task { await viewModel.retryCoaching() }
                    }
                }
            }
        }
    }
}
