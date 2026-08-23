import SwiftUI

/// Three fixed mini-cases, one per page (spec §10.3).
/// Rationale is optional here; a choice is required. No AI call happens during onboarding.
struct AssessmentView: View {
    @ObservedObject var viewModel: OnboardingViewModel

    var body: some View {
        Group {
            if let item = viewModel.assessmentState?.nextItem {
                content(for: item)
            } else if viewModel.isBusy {
                LoadingState(message: "Preparing your questions…")
            } else if let error = viewModel.error {
                ErrorState(title: "Couldn't load", message: error.userMessage) {
                    Task { await viewModel.loadAssessment() }
                }
            } else {
                LoadingState()
            }
        }
        .navigationTitle("Starting point")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func content(for item: AssessmentItem) -> some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                        HStack {
                            Text("\(item.index) of \(item.total)")
                                .font(.footnote.weight(.medium))
                                .foregroundStyle(Theme.Palette.secondaryText)
                            Spacer()
                        }
                        StepProgressBar(current: item.index, total: item.total)
                    }

                    VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                        Text(item.prompt).font(.title2.weight(.bold))
                        Text(item.context)
                            .font(.body)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }

                    VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                        Text(item.question).font(.headline)
                        ForEach(item.options) { option in
                            optionRow(option)
                        }
                    }

                    VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                        Text("Why? (optional)").font(.subheadline.weight(.medium))
                        TextEditor(text: $viewModel.currentRationale)
                            .frame(minHeight: 90)
                            .padding(Theme.Spacing.s)
                            .background(
                                Theme.Palette.surface,
                                in: RoundedRectangle(cornerRadius: Theme.Radius.control)
                            )
                            .accessibilityLabel("Optional explanation")
                    }

                    if let notice = viewModel.assessmentState?.notice, !notice.isEmpty {
                        InlineNotice(text: notice)
                    }

                    if let error = viewModel.error {
                        InlineNotice(
                            text: error.userMessage,
                            systemImage: "exclamationmark.circle",
                            tint: Theme.Palette.negative
                        )
                    }
                }
                .padding(Theme.Spacing.l)
            }

            PrimaryButton(
                title: item.index == item.total ? "See my starting point" : "Next",
                isLoading: viewModel.isBusy,
                isEnabled: viewModel.canSubmitAssessmentAnswer
            ) {
                Task { await viewModel.submitAnswer() }
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
    }

    private func optionRow(_ option: AssessmentOption) -> some View {
        let isSelected = viewModel.currentChoiceId == option.id
        return Button {
            viewModel.currentChoiceId = option.id
        } label: {
            HStack(alignment: .top, spacing: Theme.Spacing.m) {
                Image(systemName: isSelected ? "largecircle.fill.circle" : "circle")
                    .foregroundStyle(isSelected ? Theme.Palette.accent : Theme.Palette.tertiaryText)
                Text(option.label)
                    .font(.body)
                    .foregroundStyle(Theme.Palette.primaryText)
                    .multilineTextAlignment(.leading)
                Spacer(minLength: 0)
            }
            .padding(Theme.Spacing.m)
            .frame(maxWidth: .infinity, minHeight: Theme.minimumTapTarget, alignment: .leading)
            .background(Theme.Palette.surface, in: RoundedRectangle(cornerRadius: Theme.Radius.control))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.control)
                    .stroke(isSelected ? Theme.Palette.accent : .clear, lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }
}
