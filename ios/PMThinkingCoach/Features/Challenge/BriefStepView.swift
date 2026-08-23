import SwiftUI

/// Challenge brief (spec §10.6). No scoring hints and no answer options on this screen.
struct BriefStepView: View {
    @ObservedObject var viewModel: ChallengeViewModel

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
                        HStack(spacing: Theme.Spacing.s) {
                            Chip(
                                text: Theme.levelLabel(scenario.level),
                                systemImage: "chart.bar"
                            )
                            Chip(
                                text: scenario.primarySkillLabel,
                                systemImage: "target",
                                tint: Theme.Palette.accent
                            )
                            Chip(
                                text: "\(scenario.estimatedMinutes) min",
                                systemImage: "clock"
                            )
                        }
                        Text(scenario.title)
                            .font(.title.weight(.bold))
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    briefRow("Your role", scenario.brief.role, "person.crop.circle")
                    briefRow("The company", scenario.brief.company, "building.2")
                    briefRow("What's happening", scenario.brief.context, "doc.text")
                    briefRow("The objective", scenario.brief.objective, "scope")
                    briefRow("Constraints", scenario.brief.constraints, "lock")
                    briefRow("Your task", scenario.brief.task, "checkmark.circle")

                    CardContainer {
                        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                            Text("What good looks like")
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(Theme.Palette.accent)
                            Text(scenario.brief.whatGoodLooksLike)
                                .font(.subheadline)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                .padding(Theme.Spacing.l)
            }

            PrimaryButton(title: "Investigate", systemImage: "magnifyingglass") {
                viewModel.advance()
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
    }

    private func briefRow(_ title: String, _ body: String, _ symbol: String) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            Label(title, systemImage: symbol)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Theme.Palette.secondaryText)
            Text(body)
                .font(.body)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }
}
