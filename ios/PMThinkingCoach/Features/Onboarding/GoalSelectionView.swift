import SwiftUI

/// Goal selection (spec §10.2). Single select, one line of description each, no ranking.
struct GoalSelectionView: View {
    @ObservedObject var viewModel: OnboardingViewModel

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                        Text("Why are you here?")
                            .font(.largeTitle.weight(.bold))
                        Text("This shapes which scenarios you see first. You can change it later.")
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }

                    VStack(spacing: Theme.Spacing.m) {
                        ForEach(viewModel.goals, id: \.id) { goal in
                            goalCard(goal)
                        }
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
                title: "Continue",
                isLoading: viewModel.isBusy,
                isEnabled: viewModel.canContinueFromGoal
            ) {
                Task { await viewModel.saveGoal() }
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
        .navigationTitle("Set up")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func goalCard(_ goal: (id: String, title: String, subtitle: String)) -> some View {
        let isSelected = viewModel.selectedGoal == goal.id
        return Button {
            viewModel.selectedGoal = goal.id
        } label: {
            HStack(alignment: .top, spacing: Theme.Spacing.m) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .font(.title3)
                    .foregroundStyle(isSelected ? Theme.Palette.accent : Theme.Palette.tertiaryText)
                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                    Text(goal.title)
                        .font(.headline)
                        .foregroundStyle(Theme.Palette.primaryText)
                    Text(goal.subtitle)
                        .font(.subheadline)
                        .foregroundStyle(Theme.Palette.secondaryText)
                        .multilineTextAlignment(.leading)
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
}
