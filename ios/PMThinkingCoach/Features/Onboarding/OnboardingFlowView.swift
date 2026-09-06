import SwiftUI

/// Two screens, then straight into the map with the root block open.
struct OnboardingFlowView: View {

    @StateObject private var viewModel: OnboardingViewModel

    init(viewModel: @autoclosure @escaping () -> OnboardingViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.step {
                case .howItWorks:
                    HowItWorksView(viewModel: viewModel).transition(.stepForward)
                case .role:
                    RoleSelectionView(viewModel: viewModel).transition(.stepForward)
                }
            }
            .animation(Motion.standard, value: viewModel.step)
            .background(Theme.Palette.background)
        }
    }
}

private struct HowItWorksView: View {
    @ObservedObject var viewModel: OnboardingViewModel

    private var steps: [(symbol: String, title: String, body: String)] {
        [
            ("map", S.Onboarding.stepMapTitle, S.Onboarding.stepMapBody),
            ("circle.circle", S.Onboarding.stepRingsTitle, S.Onboarding.stepRingsBody),
            ("book", S.Onboarding.stepLessonsTitle, S.Onboarding.stepLessonsBody),
            ("flag.checkered", S.Onboarding.stepGateTitle, S.Onboarding.stepGateBody),
            ("lock.open", S.Onboarding.stepUnlockTitle, S.Onboarding.stepUnlockBody),
        ]
    }

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                        Text(S.Onboarding.howItWorksTitle)
                            .font(.largeTitle.weight(.bold))
                        Text(S.Onboarding.howItWorksSubtitle)
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }
                    .appear(0)

                    VStack(spacing: Theme.Spacing.m) {
                        ForEach(Array(steps.enumerated()), id: \.element.title) { index, step in
                            CardContainer {
                                HStack(alignment: .top, spacing: Theme.Spacing.m) {
                                    Image(systemName: step.symbol)
                                        .font(.title3)
                                        .foregroundStyle(Theme.Palette.accent)
                                        .frame(width: 28)
                                    VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                                        Text(step.title).font(.headline)
                                        Text(step.body)
                                            .font(.subheadline)
                                            .foregroundStyle(Theme.Palette.secondaryText)
                                            .fixedSize(horizontal: false, vertical: true)
                                    }
                                }
                            }
                            .appear(index + 1)
                            .accessibilityElement(children: .combine)
                        }
                    }

                    InlineNotice(text: S.Onboarding.ownPace, systemImage: "tortoise")
                        .appear(6)
                }
                .padding(Theme.Spacing.l)
            }

            PrimaryButton(title: S.Common.continueAction) { viewModel.advance() }
                .padding(Theme.Spacing.l)
                .background(.bar)
        }
        .navigationTitle(S.Onboarding.setUpTitle)
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct RoleSelectionView: View {
    @ObservedObject var viewModel: OnboardingViewModel

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                        Text(S.Onboarding.roleTitle)
                            .font(.largeTitle.weight(.bold))
                        Text(S.Onboarding.roleSubtitle)
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }
                    .appear(0)

                    VStack(spacing: Theme.Spacing.s) {
                        ForEach(Array(viewModel.roles.enumerated()), id: \.element) { index, key in
                            roleRow(key).appear(index + 1)
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
                .animation(Motion.standard, value: viewModel.error)
            }

            VStack(spacing: Theme.Spacing.s) {
                PrimaryButton(title: S.Onboarding.startLearning, isLoading: viewModel.isBusy) {
                    Task { await viewModel.finish(withRole: viewModel.selectedRole) }
                }
                Button(S.Onboarding.skipRole) {
                    Task { await viewModel.finish(withRole: nil) }
                }
                .font(.footnote)
                .foregroundStyle(Theme.Palette.secondaryText)
                .frame(minHeight: Theme.minimumTapTarget)
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
        .navigationTitle(S.Onboarding.setUpTitle)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func roleRow(_ key: String) -> some View {
        let isSelected = viewModel.selectedRole == key
        return Button {
            Haptics.selection()
            withAnimation(Motion.quick) {
                viewModel.selectedRole = isSelected ? nil : key
            }
        } label: {
            HStack(spacing: Theme.Spacing.m) {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isSelected ? Theme.Palette.accent : Theme.Palette.tertiaryText)
                    .contentTransition(.symbolEffect(.replace))
                Text(S.Roles.title(key))
                    .font(.body)
                    .foregroundStyle(Theme.Palette.primaryText)
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
        .buttonStyle(.pressable)
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }
}
