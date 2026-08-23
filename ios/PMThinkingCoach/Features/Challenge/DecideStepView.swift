import SwiftUI

/// Decide & defend (spec §10.8, P0-07).
/// Submit stays disabled until an option is chosen and the rationale is 30-600 characters.
struct DecideStepView: View {
    @ObservedObject var viewModel: ChallengeViewModel
    @FocusState private var isEditingRationale: Bool

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
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                        Text(scenario.decisionPrompt)
                            .font(.title3.weight(.bold))
                            .fixedSize(horizontal: false, vertical: true)
                        Text("Several answers can be defended. What matters is the reasoning.")
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }

                    VStack(spacing: Theme.Spacing.m) {
                        ForEach(scenario.decisionOptions) { option in
                            optionCard(option)
                        }
                    }

                    rationaleSection

                    if let error = viewModel.submissionError {
                        InlineNotice(
                            text: error.userMessage,
                            systemImage: "exclamationmark.circle",
                            tint: Theme.Palette.negative
                        )
                    }

                    if viewModel.isOfflineDraft {
                        InlineNotice(
                            text: "Saved on this device. It will sync when you're back online — "
                                + "you can't submit until it does.",
                            systemImage: "wifi.slash",
                            tint: Theme.Palette.caution
                        )
                    } else if viewModel.draftSavedAt != nil {
                        InlineNotice(text: "Saved", systemImage: "checkmark.circle")
                    }
                }
                .padding(Theme.Spacing.l)
            }

            VStack(spacing: Theme.Spacing.s) {
                Text("Feedback assesses your reasoning, not only which option you picked.")
                    .font(.caption)
                    .foregroundStyle(Theme.Palette.tertiaryText)
                    .multilineTextAlignment(.center)
                HStack(spacing: Theme.Spacing.m) {
                    SecondaryButton(title: "Back", systemImage: "chevron.left") {
                        viewModel.goBack()
                    }
                    PrimaryButton(
                        title: "Submit decision",
                        isLoading: viewModel.isSubmitting,
                        isEnabled: viewModel.form.canSubmit
                    ) {
                        isEditingRationale = false
                        Task { await viewModel.submit() }
                    }
                }
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
    }

    private func optionCard(_ option: DecisionOption) -> some View {
        let isSelected = viewModel.form.selectedOptionId == option.id
        return Button {
            viewModel.select(option: option)
        } label: {
            HStack(alignment: .top, spacing: Theme.Spacing.m) {
                Image(systemName: isSelected ? "largecircle.fill.circle" : "circle")
                    .font(.title3)
                    .foregroundStyle(isSelected ? Theme.Palette.accent : Theme.Palette.tertiaryText)
                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                    Text(option.label)
                        .font(.headline)
                        .foregroundStyle(Theme.Palette.primaryText)
                        .multilineTextAlignment(.leading)
                    Text(option.description)
                        .font(.subheadline)
                        .foregroundStyle(Theme.Palette.secondaryText)
                        .multilineTextAlignment(.leading)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
            }
            .padding(Theme.Spacing.l)
            .frame(maxWidth: .infinity, minHeight: Theme.minimumTapTarget, alignment: .leading)
            .background(Theme.Palette.surface, in: RoundedRectangle(cornerRadius: Theme.Radius.card))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.card)
                    .stroke(isSelected ? Theme.Palette.accent : .clear, lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }

    private var rationaleSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            Text("Defend your decision").font(.headline)

            ZStack(alignment: .topLeading) {
                TextEditor(
                    text: Binding(
                        get: { viewModel.form.rationale },
                        set: { viewModel.updateRationale($0) }
                    )
                )
                .focused($isEditingRationale)
                .frame(minHeight: 160)
                .padding(Theme.Spacing.s)
                .background(
                    Theme.Palette.surface,
                    in: RoundedRectangle(cornerRadius: Theme.Radius.control)
                )
                .accessibilityLabel("Your reasoning")

                if viewModel.form.rationale.isEmpty {
                    Text("What evidence, trade-off, and risk informed your choice?")
                        .font(.body)
                        .foregroundStyle(Theme.Palette.tertiaryText)
                        .padding(.horizontal, Theme.Spacing.m)
                        .padding(.vertical, Theme.Spacing.m + 2)
                        .allowsHitTesting(false)
                }
            }

            HStack {
                if let message = viewModel.form.rationaleValidationMessage {
                    Text(message)
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.caution)
                } else if viewModel.form.isRationaleValid {
                    Label("Long enough", systemImage: "checkmark")
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.positive)
                }
                Spacer()
                Text("\(viewModel.form.rationaleCharacterCount)/\(ChallengeFormState.rationaleMaximum)")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(Theme.Palette.tertiaryText)
            }
            .accessibilityElement(children: .combine)
        }
    }
}
