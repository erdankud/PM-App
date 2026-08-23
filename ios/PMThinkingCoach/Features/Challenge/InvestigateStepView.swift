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
                        Text("What do you want to look at?")
                            .font(.title3.weight(.bold))
                        Text(viewModel.form.evidenceCounterText)
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }

                    ForEach(scenario.evidenceCards) { card in
                        evidenceCard(card)
                    }

                    InlineNotice(
                        text: "This is everything you get. Real decisions are made on partial "
                            + "evidence — say what you can't know as well as what you can."
                    )
                }
                .padding(Theme.Spacing.l)
            }

            VStack(spacing: Theme.Spacing.s) {
                if !viewModel.form.canAdvanceToDecision {
                    InlineNotice(
                        text: "Open at least one signal before deciding.",
                        systemImage: "hand.tap"
                    )
                }
                HStack(spacing: Theme.Spacing.m) {
                    SecondaryButton(title: "Back", systemImage: "chevron.left") {
                        viewModel.goBack()
                    }
                    PrimaryButton(
                        title: "Make a decision",
                        isEnabled: viewModel.form.canAdvanceToDecision
                    ) {
                        viewModel.advance()
                    }
                }
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
    }

    private func evidenceCard(_ card: EvidenceCard) -> some View {
        let isOpen = expanded.contains(card.id)
        let isReviewed = viewModel.form.reviewedEvidenceIds.contains(card.id)

        return CardContainer(padding: Theme.Spacing.m) {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) {
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
                            Chip(text: "Reviewed", systemImage: "checkmark", tint: Theme.Palette.positive)
                        }
                        Image(systemName: isOpen ? "chevron.up" : "chevron.down")
                            .font(.footnote)
                            .foregroundStyle(Theme.Palette.tertiaryText)
                    }
                    .frame(minHeight: Theme.minimumTapTarget)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityHint(isOpen ? "Collapses this signal" : "Opens this signal")
                .accessibilityAddTraits(.isButton)

                if isOpen {
                    Text(card.content)
                        .font(.callout)
                        .foregroundStyle(Theme.Palette.primaryText)
                        .fixedSize(horizontal: false, vertical: true)
                        .transition(.opacity)
                }
            }
        }
    }
}
