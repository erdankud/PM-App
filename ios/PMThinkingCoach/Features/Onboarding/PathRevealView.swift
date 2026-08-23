import SwiftUI

/// Path reveal (spec §10.4). Shows a band, not a precise score, and says plainly that
/// this is not a validated assessment.
struct PathRevealView: View {
    @ObservedObject var viewModel: OnboardingViewModel

    var body: some View {
        Group {
            if let result = viewModel.result {
                content(result)
            } else if let error = viewModel.error {
                ErrorState(title: "Couldn't load your path", message: error.userMessage) {
                    Task { await viewModel.loadResultIfNeeded() }
                }
            } else {
                LoadingState(message: "Working out where to start you…")
            }
        }
        .navigationTitle("Your path")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func content(_ result: AssessmentResult) -> some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    CardContainer {
                        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                            Text("Starting level")
                                .font(.footnote.weight(.medium))
                                .foregroundStyle(Theme.Palette.secondaryText)
                            Text(Theme.levelLabel(result.startingLevel))
                                .font(.largeTitle.weight(.bold))
                            Text(result.disclaimer)
                                .font(.footnote)
                                .foregroundStyle(Theme.Palette.tertiaryText)
                        }
                    }

                    VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                        SectionHeader(
                            title: "Your focus",
                            subtitle: "The two skills your first week leans on."
                        )
                        ForEach(result.focusSkills) { skill in
                            CardContainer(padding: Theme.Spacing.m) { SkillRow(skill: skill) }
                        }
                    }

                    VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                        SectionHeader(
                            title: "Next 7 days",
                            subtitle: "One scenario a day. Day 1 is ready now."
                        )
                        ForEach(Array(result.path.enumerated()), id: \.element.id) { index, day in
                            dayRow(day, index: index)
                        }
                    }
                }
                .padding(Theme.Spacing.l)
            }

            PrimaryButton(
                title: "Start today's challenge",
                isLoading: viewModel.isBusy
            ) {
                Task { await viewModel.finishOnboarding() }
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
    }

    private func dayRow(_ day: PathPreviewDay, index: Int) -> some View {
        let isActive = index == 0
        return HStack(spacing: Theme.Spacing.m) {
            ZStack {
                Circle()
                    .fill(isActive ? Theme.Palette.accent : Theme.Palette.separator.opacity(0.4))
                    .frame(width: 32, height: 32)
                Text("\(index + 1)")
                    .font(.footnote.weight(.bold))
                    .foregroundStyle(isActive ? Color.white : Theme.Palette.secondaryText)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(day.title)
                    .font(.subheadline.weight(isActive ? .semibold : .regular))
                    .foregroundStyle(isActive ? Theme.Palette.primaryText : Theme.Palette.secondaryText)
                    .lineLimit(2)
                Text("\(day.primarySkillLabel) · \(day.estimatedMinutes) min")
                    .font(.caption)
                    .foregroundStyle(Theme.Palette.tertiaryText)
            }
            Spacer(minLength: 0)
            if isActive {
                Chip(text: "Today", tint: Theme.Palette.accent)
            }
        }
        .padding(Theme.Spacing.m)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.Palette.surface, in: RoundedRectangle(cornerRadius: Theme.Radius.control))
        .accessibilityElement(children: .combine)
        .accessibilityLabel(
            "Day \(index + 1)\(isActive ? ", today" : ""). \(day.title). "
            + "\(day.primarySkillLabel), \(day.estimatedMinutes) minutes."
        )
    }
}
