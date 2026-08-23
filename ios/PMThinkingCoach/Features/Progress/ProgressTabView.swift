import SwiftUI

/// Progress (spec §10.11, P0-10). Reinforces a habit, not competition.
struct ProgressTabView: View {
    @EnvironmentObject private var container: AppContainer
    @StateObject private var viewModel: ProgressViewModel

    init(viewModel: @autoclosure @escaping () -> ProgressViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        NavigationStack {
            Group {
                if let progress = viewModel.progress {
                    content(progress)
                } else if viewModel.isLoading {
                    LoadingState()
                } else if let error = viewModel.error {
                    ErrorState(title: "Couldn't load progress", message: error.userMessage) {
                        Task { await viewModel.load() }
                    }
                } else {
                    LoadingState()
                }
            }
            .background(Theme.Palette.background)
            .navigationTitle("Progress")
        }
        .task { await viewModel.load() }
    }

    private func content(_ progress: ProgressResponse) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                summaryCard(progress)
                activityCard(progress)
                skillsSection(progress)

                NavigationLink {
                    HistoryView(viewModel: container.makeHistoryViewModel())
                } label: {
                    HStack {
                        Label(
                            "\(progress.completedCount) completed challenge"
                            + (progress.completedCount == 1 ? "" : "s"),
                            systemImage: "list.bullet.rectangle"
                        )
                        Spacer()
                        Image(systemName: "chevron.right").foregroundStyle(Theme.Palette.tertiaryText)
                    }
                    .padding(Theme.Spacing.l)
                    .frame(maxWidth: .infinity, minHeight: Theme.minimumTapTarget)
                    .background(
                        Theme.Palette.surface, in: RoundedRectangle(cornerRadius: Theme.Radius.card)
                    )
                }
                .buttonStyle(.plain)

                Text(progress.footnote)
                    .font(.footnote)
                    .foregroundStyle(Theme.Palette.tertiaryText)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(Theme.Spacing.l)
        }
        .refreshable { await viewModel.load() }
    }

    private func summaryCard(_ progress: ProgressResponse) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Level \(progress.level)")
                            .font(.title.weight(.bold))
                        Text("\(progress.totalXp) XP total")
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }
                    Spacer()
                    if progress.streakCount > 0 {
                        Chip(
                            text: "\(progress.streakCount) day streak",
                            systemImage: "flame",
                            tint: Theme.Palette.caution
                        )
                    }
                }

                if let next = progress.xpForNextLevel, next > progress.totalXp {
                    let remaining = next - progress.totalXp
                    VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                        GeometryReader { geometry in
                            ZStack(alignment: .leading) {
                                Capsule().fill(Theme.Palette.separator.opacity(0.4))
                                Capsule()
                                    .fill(Theme.Palette.accent)
                                    .frame(width: geometry.size.width * levelProgress(progress, next: next))
                            }
                        }
                        .frame(height: 8)
                        Text("\(remaining) XP to level \(progress.level + 1)")
                            .font(.caption)
                            .foregroundStyle(Theme.Palette.tertiaryText)
                    }
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("\(remaining) XP to level \(progress.level + 1)")
                }
            }
        }
    }

    private func levelProgress(_ progress: ProgressResponse, next: Int) -> CGFloat {
        guard next > 0 else { return 0 }
        return max(0, min(1, CGFloat(progress.totalXp) / CGFloat(next)))
    }

    private func activityCard(_ progress: ProgressResponse) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                Text("Last 7 days").font(.headline)
                HStack(spacing: Theme.Spacing.s) {
                    ForEach(progress.activity) { day in
                        VStack(spacing: Theme.Spacing.xs) {
                            Text(Theme.shortWeekday(day.localDate))
                                .font(.caption2)
                                .foregroundStyle(Theme.Palette.tertiaryText)
                            ZStack {
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(activityColor(day.state))
                                    .frame(height: 36)
                                Image(systemName: activitySymbol(day.state))
                                    .font(.caption)
                                    .foregroundStyle(activityForeground(day.state))
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel(
                            "\(Theme.formattedDate(day.localDate)): \(activityLabel(day.state))"
                        )
                    }
                }
            }
        }
    }

    private func activityColor(_ state: String) -> Color {
        switch state {
        case "completed": return Theme.Palette.positive.opacity(0.2)
        case "today": return Theme.Palette.accent.opacity(0.18)
        case "upcoming": return Theme.Palette.separator.opacity(0.25)
        default: return Theme.Palette.separator.opacity(0.35)
        }
    }

    private func activityForeground(_ state: String) -> Color {
        switch state {
        case "completed": return Theme.Palette.positive
        case "today": return Theme.Palette.accent
        default: return Theme.Palette.tertiaryText
        }
    }

    private func activitySymbol(_ state: String) -> String {
        switch state {
        case "completed": return "checkmark"
        case "today": return "sun.max"
        case "upcoming": return "circle.dotted"
        default: return "minus"
        }
    }

    private func activityLabel(_ state: String) -> String {
        switch state {
        case "completed": return "completed"
        case "today": return "today"
        case "upcoming": return "upcoming"
        default: return "missed"
        }
    }

    private func skillsSection(_ progress: ProgressResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            SectionHeader(
                title: "Skills",
                subtitle: "Trend is based on your last five completed challenges."
            )
            CardContainer {
                VStack(spacing: Theme.Spacing.l) {
                    ForEach(progress.skills) { skill in
                        SkillRow(skill: skill)
                    }
                }
            }
        }
    }
}
