import SwiftUI

/// Progress is measured in blocks passed and lessons read — there is no calendar in
/// this product any more (spec v0.2 §1, §10).
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
                } else if let error = viewModel.error {
                    ErrorState(title: S.Progress.loadFailed, message: error.userMessage) {
                        Task { await viewModel.load() }
                    }
                } else {
                    LoadingState()
                }
            }
            .animation(Motion.standard, value: viewModel.isLoading)
            .background(Theme.Palette.background)
            .navigationTitle(S.Progress.title)
        }
        .task { await viewModel.load() }
    }

    private func content(_ progress: ProgressResponse) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                summaryCard(progress).appear(0)
                journeyCard(progress).appear(1)
                skillsSection(progress).appear(2)

                NavigationLink {
                    HistoryView(viewModel: container.makeHistoryViewModel())
                } label: {
                    HStack {
                        Label(
                            S.Progress.gateHistory(progress.gatesAttempted),
                            systemImage: "list.bullet.rectangle"
                        )
                        Spacer()
                        Image(systemName: "chevron.right")
                            .foregroundStyle(Theme.Palette.tertiaryText)
                    }
                    .padding(Theme.Spacing.l)
                    .frame(maxWidth: .infinity, minHeight: Theme.minimumTapTarget)
                    .background(
                        Theme.Palette.surface,
                        in: RoundedRectangle(cornerRadius: Theme.Radius.card)
                    )
                }
                .buttonStyle(.pressable)
                .appear(3)

                Text(progress.footnote)
                    .font(.footnote)
                    .foregroundStyle(Theme.Palette.tertiaryText)
                    .fixedSize(horizontal: false, vertical: true)
                    .appear(4)
            }
            .padding(Theme.Spacing.l)
        }
        .refreshable { await viewModel.load() }
    }

    private func summaryCard(_ progress: ProgressResponse) -> some View {
        CardContainer(isHighlighted: true) {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(S.Progress.level(progress.level))
                            .font(.title.weight(.bold))
                        HStack(spacing: 0) {
                            Text(S.Progress.totalXpPrefix)
                            CountUpText(value: progress.totalXp, font: .subheadline)
                            Text(S.Progress.totalXpSuffix)
                        }
                        .font(.subheadline)
                        .foregroundStyle(Theme.Palette.secondaryText)
                        .accessibilityElement(children: .ignore)
                        .accessibilityLabel(S.Progress.totalXp(progress.totalXp))
                    }
                    Spacer()
                }

                if let next = progress.xpForNextLevel, next > progress.totalXp {
                    let remaining = next - progress.totalXp
                    VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                        ProgressTrack(
                            progress: Double(progress.totalXp) / Double(max(next, 1)),
                            height: 8
                        )
                        Text(S.Progress.xpToNextLevel(remaining, progress.level + 1))
                            .font(.caption)
                            .foregroundStyle(Theme.Palette.tertiaryText)
                    }
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel(S.Progress.xpToNextLevel(remaining, progress.level + 1))
                }
            }
        }
    }

    private func journeyCard(_ progress: ProgressResponse) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                counter(
                    title: S.Progress.blocksPassed,
                    value: progress.blocksPassed,
                    total: progress.blocksTotal,
                    symbol: "flag.checkered"
                )
                counter(
                    title: S.Progress.lessonsRead,
                    value: progress.lessonsCompleted,
                    total: progress.lessonsTotal,
                    symbol: "book"
                )
            }
        }
    }

    private func counter(title: String, value: Int, total: Int, symbol: String) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            HStack(spacing: Theme.Spacing.s) {
                Image(systemName: symbol)
                    .font(.footnote)
                    .foregroundStyle(Theme.Palette.accent)
                Text(title).font(.subheadline.weight(.medium))
                Spacer()
                Text("\(value) / \(total)")
                    .font(.subheadline.monospacedDigit())
                    .foregroundStyle(Theme.Palette.secondaryText)
            }
            ProgressTrack(progress: total > 0 ? Double(value) / Double(total) : 0)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(title): \(value) / \(total)")
    }

    private func skillsSection(_ progress: ProgressResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            SectionHeader(title: S.Progress.skillsTitle, subtitle: S.Progress.skillsSubtitle)
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
