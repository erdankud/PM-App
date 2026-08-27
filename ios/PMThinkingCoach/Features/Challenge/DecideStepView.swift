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
                        Text(S.Challenge.severalAnswers)
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }
                    .appear(0)

                    VStack(spacing: Theme.Spacing.m) {
                        ForEach(Array(scenario.decisionOptions.enumerated()), id: \.element.id) {
                            index, option in
                            optionCard(option).appear(index + 1)
                        }
                    }

                    rationaleSection.appear(5)

                    if let error = viewModel.submissionError {
                        InlineNotice(
                            text: error.userMessage,
                            systemImage: "exclamationmark.circle",
                            tint: Theme.Palette.negative
                        )
                    }

                    if viewModel.isOfflineDraft {
                        InlineNotice(
                            text: S.Challenge.offlineDraft,
                            systemImage: "wifi.slash",
                            tint: Theme.Palette.caution
                        )
                    } else if viewModel.draftSavedAt != nil {
                        InlineNotice(text: S.Challenge.saved, systemImage: "checkmark.circle")
                    }
                }
                .padding(Theme.Spacing.l)
                .animation(Motion.standard, value: viewModel.submissionError)
                .animation(Motion.quick, value: viewModel.draftSavedAt)
            }

            VStack(spacing: Theme.Spacing.s) {
                Text(S.Challenge.reasoningNotOptionNote)
                    .font(.caption)
                    .foregroundStyle(Theme.Palette.tertiaryText)
                    .multilineTextAlignment(.center)
                HStack(spacing: Theme.Spacing.m) {
                    SecondaryButton(title: S.Common.back, systemImage: "chevron.left") {
                        viewModel.goBack()
                    }
                    PrimaryButton(
                        title: S.Challenge.submitDecision,
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
            Haptics.selection()
            withAnimation(Motion.quick) { viewModel.select(option: option) }
        } label: {
            HStack(alignment: .top, spacing: Theme.Spacing.m) {
                Image(systemName: isSelected ? "largecircle.fill.circle" : "circle")
                    .font(.title3)
                    .foregroundStyle(isSelected ? Theme.Palette.accent : Theme.Palette.tertiaryText)
                    .contentTransition(.symbolEffect(.replace))
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
            .shadow(color: Theme.Palette.accent.opacity(isSelected ? 0.16 : 0), radius: 12, y: 6)
        }
        .buttonStyle(.pressable)
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }

    private var rationaleSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            Text(S.Challenge.defendYourDecision).font(.headline)

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
                .scrollContentBackground(.hidden)
                .background {
                    RoundedRectangle(cornerRadius: Theme.Radius.control)
                        .fill(Theme.Palette.surface)
                        .overlay {
                            // A quiet focus ring: the text field is the work on this screen.
                            RoundedRectangle(cornerRadius: Theme.Radius.control)
                                .strokeBorder(
                                    Theme.Palette.accent.opacity(isEditingRationale ? 0.55 : 0),
                                    lineWidth: 2
                                )
                        }
                }
                .animation(Motion.quick, value: isEditingRationale)
                .accessibilityLabel(S.Challenge.yourReasoning)

                if viewModel.form.rationale.isEmpty {
                    Text(S.Challenge.rationalePlaceholder)
                        .font(.body)
                        .foregroundStyle(Theme.Palette.tertiaryText)
                        .padding(.horizontal, Theme.Spacing.m)
                        .padding(.vertical, Theme.Spacing.m + 2)
                        .allowsHitTesting(false)
                        .transition(.opacity)
                }
            }

            HStack {
                if let message = viewModel.form.rationaleValidationMessage {
                    Text(message)
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.caution)
                        .transition(.opacity)
                } else if viewModel.form.isRationaleValid {
                    Label(S.Challenge.longEnough, systemImage: "checkmark")
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.positive)
                        .transition(.scale.combined(with: .opacity))
                }
                Spacer()
                Text("\(viewModel.form.rationaleCharacterCount)/\(ChallengeFormState.rationaleMaximum)")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(Theme.Palette.tertiaryText)
                    .contentTransition(.numericText())
            }
            .animation(Motion.quick, value: viewModel.form.isRationaleValid)
            .accessibilityElement(children: .combine)
        }
    }
}
