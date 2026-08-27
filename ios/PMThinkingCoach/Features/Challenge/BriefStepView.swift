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
                                text: scenario.localizedPrimarySkill,
                                systemImage: "target",
                                tint: Theme.Palette.accent
                            )
                            Chip(
                                text: S.Common.minutes(scenario.estimatedMinutes),
                                systemImage: "clock"
                            )
                        }
                        Text(scenario.title)
                            .font(.title.weight(.bold))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .appear(0)

                    ForEach(Array(rows(scenario).enumerated()), id: \.element.title) { index, row in
                        briefRow(row.title, row.body, row.symbol).appear(index + 1)
                    }

                    CardContainer(isHighlighted: true) {
                        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                            Text(S.Challenge.whatGoodLooksLike)
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(Theme.Palette.accent)
                            Text(scenario.brief.whatGoodLooksLike)
                                .font(.subheadline)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .appear(7)
                }
                .padding(Theme.Spacing.l)
            }

            PrimaryButton(title: S.Challenge.Step.investigate, systemImage: "magnifyingglass") {
                viewModel.advance()
            }
            .padding(Theme.Spacing.l)
            .background(.bar)
        }
    }

    private func rows(_ scenario: ScenarioView) -> [(title: String, body: String, symbol: String)] {
        [
            (S.Challenge.yourRole, scenario.brief.role, "person.crop.circle"),
            (S.Challenge.theCompany, scenario.brief.company, "building.2"),
            (S.Challenge.whatsHappening, scenario.brief.context, "doc.text"),
            (S.Challenge.theObjective, scenario.brief.objective, "scope"),
            (S.Challenge.constraints, scenario.brief.constraints, "lock"),
            (S.Challenge.yourTask, scenario.brief.task, "checkmark.circle")
        ]
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
