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

            PrimaryButton(title: S.Challenge.finish) { onFinish() }
                .padding(Theme.Spacing.l)
                .background(.bar)
        }
        .task { await viewModel.refreshFeedback() }
    }

    // MARK: - Complete

    private func completeContent(_ response: FeedbackResponse, _ body: FeedbackBody) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
            CardContainer(isHighlighted: true) {
                VStack(spacing: Theme.Spacing.m) {
                    ScoreHeadline(score: body.score, band: body.band)
                    if body.xpAwarded > 0 {
                        Chip(
                            text: S.Challenge.xpAwarded(body.xpAwarded),
                            systemImage: "sparkles",
                            tint: Theme.Palette.accent
                        )
                    }
                    breakdown(body.breakdown)
                }
            }
            .appear(0)
            .onAppear { Haptics.success() }

            if body.needsRetry {
                InlineNotice(
                    text: S.Challenge.needsRetryNotice,
                    systemImage: "info.circle",
                    tint: Theme.Palette.caution
                )
                .appear(1)
            }

            pointsSection(
                title: S.Challenge.strengthsTitle,
                symbol: "checkmark.seal",
                tint: Theme.Palette.positive,
                points: body.strengths,
                startIndex: 2
            )

            pointsSection(
                title: S.Challenge.improvementsTitle,
                symbol: "arrow.up.forward",
                tint: Theme.Palette.caution,
                points: body.improvements,
                startIndex: 4
            )

            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                SectionHeader(title: S.Challenge.sharperApproach)
                CardContainer {
                    Text(body.sharperApproach)
                        .font(.body)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .appear(6)

            skillImpactSection(body.skillImpact).appear(7)

            ratingSection(response).appear(8)

            InlineNotice(text: S.Challenge.practiceSignalDisclaimer).appear(8)
        }
    }

    private func breakdown(_ breakdown: ScoreBreakdown) -> some View {
        VStack(spacing: Theme.Spacing.s) {
            ForEach(breakdown.rows, id: \.label) { row in
                VStack(spacing: Theme.Spacing.xs) {
                    HStack {
                        Text(row.label)
                            .font(.caption)
                            .foregroundStyle(Theme.Palette.secondaryText)
                        Spacer()
                        Text("\(row.value)/\(row.max)")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(Theme.Palette.primaryText)
                    }
                    ProgressTrack(
                        progress: row.max > 0 ? Double(row.value) / Double(row.max) : 0,
                        height: 4
                    )
                }
                .accessibilityElement(children: .combine)
                .accessibilityLabel(
                    S.Challenge.breakdownAccessibility(row.label, row.value, row.max)
                )
            }
        }
        .padding(.top, Theme.Spacing.s)
    }

    private func pointsSection(
        title: String, symbol: String, tint: Color, points: [FeedbackPoint], startIndex: Int
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
                .appear(startIndex)
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
                        title: S.Challenge.skillImpactTitle,
                        subtitle: S.Challenge.skillImpactSubtitle
                    )
                    CardContainer {
                        VStack(spacing: Theme.Spacing.m) {
                            ForEach(impacts) { impact in
                                HStack {
                                    Text(impact.localizedLabel).font(.subheadline)
                                    Spacer()
                                    Text(impact.deltaText)
                                        .font(.subheadline.weight(.semibold).monospacedDigit())
                                        .foregroundStyle(
                                            impact.delta >= 0
                                                ? Theme.Palette.positive : Theme.Palette.caution
                                        )
                                    HStack(spacing: 2) {
                                        Image(systemName: "arrow.right").font(.caption2)
                                        CountUpText(value: impact.score, font: .subheadline)
                                    }
                                    .foregroundStyle(Theme.Palette.secondaryText)
                                }
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(
                                    S.Challenge.skillImpactAccessibility(
                                        impact.localizedLabel, impact.delta, impact.score
                                    )
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
            SectionHeader(title: S.Challenge.wasThisUseful)
            HStack(spacing: Theme.Spacing.m) {
                ratingButton(title: S.Challenge.useful, symbol: "hand.thumbsup", value: "useful")
                ratingButton(
                    title: S.Challenge.notUseful, symbol: "hand.thumbsdown", value: "not_useful"
                )
            }
            if viewModel.ratingSubmitted != nil {
                InlineNotice(text: S.Challenge.ratingThanks)
            }
        }
        .animation(Motion.standard, value: viewModel.ratingSubmitted)
    }

    private func ratingButton(title: String, symbol: String, value: String) -> some View {
        let isSelected = viewModel.ratingSubmitted == value
        return Button {
            Haptics.tap()
            Task { await viewModel.rate(value) }
        } label: {
            Label(title, systemImage: symbol)
                .frame(maxWidth: .infinity, minHeight: Theme.minimumTapTarget)
        }
        .buttonStyle(.bordered)
        .tint(isSelected ? Theme.Palette.accent : Theme.Palette.neutral)
        .scaleEffect(isSelected ? 1.03 : 1)
        .animation(Motion.quick, value: isSelected)
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }

    // MARK: - Pending / failed

    private var unavailableContent: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
            if let consequence = viewModel.consequence {
                CardContainer {
                    VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                        Label(S.Challenge.whatHappensNext, systemImage: "arrow.turn.down.right")
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(Theme.Palette.accent)
                        Text(consequence.text)
                            .font(.body)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .appear(0)
            }

            CardContainer {
                VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                    Label(
                        viewModel.feedback?.status == .failed
                            ? S.Challenge.coachingDidntFinish : S.Challenge.coachingTakingLonger,
                        systemImage: "hourglass"
                    )
                    .font(.headline)

                    Text(S.Challenge.unavailableBody)
                        .font(.subheadline)
                        .foregroundStyle(Theme.Palette.secondaryText)
                        .fixedSize(horizontal: false, vertical: true)

                    SecondaryButton(
                        title: S.Challenge.retryCoaching, systemImage: "arrow.clockwise"
                    ) {
                        Task { await viewModel.retryCoaching() }
                    }
                }
            }
            .appear(1)
        }
    }
}
