import SwiftUI

/// Investigate (spec §10.7). Cards start collapsed; opening one marks it Reviewed.
/// At least one must be reviewed before a decision can be made.
struct InvestigateStepView: View {
    @ObservedObject var viewModel: ChallengeViewModel
    @State private var expanded: Set<String> = []

    var body: some View {
        if let scenario = viewModel.scenario {
            content(scenario)
        } else {
            LoadingState()
        }
    }

    private func content(_ scenario: ScenarioView) -> some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                    VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                        Text(S.Challenge.investigatePrompt)
                            .font(.title3.weight(.bold))
                        Text(viewModel.form.evidenceCounterText)
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                            .contentTransition(.numericText())
                            .animation(Motion.quick, value: viewModel.form.reviewedCount)
                    }
                    .appear(0)

                    ForEach(Array(scenario.evidenceCards.enumerated()), id: \.element.id) {
                        index, card in
                        evidenceCard(card).appear(index + 1)
                    }

                    InlineNotice(text: S.Challenge.partialEvidenceNotice)
                        .appear(scenario.evidenceCards.count + 1)
                }
                .padding(Theme.Spacing.l)
            }

            VStack(spacing: Theme.Spacing.s) {
                if !viewModel.form.canAdvanceToDecision {
                    InlineNotice(
                        text: S.Challenge.openOneSignal,
                        systemImage: "hand.tap"
                    )
                }
                HStack(spacing: Theme.Spacing.m) {
                    SecondaryButton(title: S.Common.back, systemImage: "chevron.left") {
                        viewModel.goBack()
                    }
                    PrimaryButton(
                        title: S.Challenge.makeADecision,
                        isEnabled: viewModel.form.canAdvanceToDecision
                    ) {
                        viewModel.advance()
                    }
                }
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
            .animation(Motion.standard, value: viewModel.form.canAdvanceToDecision)
        }
    }

    private func evidenceCard(_ card: EvidenceCard) -> some View {
        let isOpen = expanded.contains(card.id)
        let isReviewed = viewModel.form.reviewedEvidenceIds.contains(card.id)

        return CardContainer(padding: Theme.Spacing.m) {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                Button {
                    Haptics.tap()
                    withAnimation(Motion.standard) {
                        if isOpen {
                            expanded.remove(card.id)
                        } else {
                            expanded.insert(card.id)
                            viewModel.openEvidence(card)
                        }
                    }
                } label: {
                    HStack(spacing: Theme.Spacing.m) {
                        Image(systemName: card.symbolName)
                            .font(.title3)
                            .foregroundStyle(Theme.Palette.accent)
                            .frame(width: 28)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(card.title)
                                .font(.headline)
                                .foregroundStyle(Theme.Palette.primaryText)
                            Text(card.typeLabel)
                                .font(.caption)
                                .foregroundStyle(Theme.Palette.tertiaryText)
                        }
                        Spacer(minLength: 0)
                        if isReviewed {
                            Chip(
                                text: S.Challenge.reviewed,
                                systemImage: "checkmark",
                                tint: Theme.Palette.positive
                            )
                            .transition(.scale.combined(with: .opacity))
                        }
                        Image(systemName: "chevron.down")
                            .font(.footnote)
                            .foregroundStyle(Theme.Palette.tertiaryText)
                            .rotationEffect(.degrees(isOpen ? 180 : 0))
                    }
                    .frame(minHeight: Theme.minimumTapTarget)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityHint(isOpen ? S.Challenge.collapsesSignal : S.Challenge.opensSignal)
                .accessibilityAddTraits(.isButton)

                if isOpen {
                    Text(card.content)
                        .font(.callout)
                        .foregroundStyle(Theme.Palette.primaryText)
                        .fixedSize(horizontal: false, vertical: true)
                        .transition(.expand)
                }
            }
        }
    }
}
