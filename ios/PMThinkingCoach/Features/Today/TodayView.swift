import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var container: AppContainer
    @StateObject private var viewModel: TodayViewModel

    init(viewModel: @autoclosure @escaping () -> TodayViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.state {
                case .idle, .loading:
                    LoadingState(message: "Getting today's challenge…")
                case .failed(let error):
                    ErrorState(
                        title: "Today isn't ready",
                        message: error.userMessage
                    ) {
                        Task { await viewModel.load() }
                    }
                case .loaded(let response, let isStale):
                    content(response, isStale: isStale)
                }
            }
            .background(Theme.Palette.background)
            .navigationTitle("Today")
            .navigationBarTitleDisplayMode(.large)
        }
        .task { await viewModel.load() }
        .fullScreenCover(item: Binding(
            get: { viewModel.presentedAssignmentId.map(AssignmentRoute.init) },
            set: { newValue in
                if newValue == nil { Task { await viewModel.challengeDismissed() } }
            }
        )) { route in
            ChallengeFlowView(viewModel: container.makeChallengeViewModel(assignmentId: route.id))
        }
    }

    private func content(_ response: TodayResponse, isStale: Bool) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                header(response)
                if isStale {
                    InlineNotice(
                        text: "Showing your last saved view. Pull down to refresh when you're back online.",
                        systemImage: "wifi.slash",
                        tint: Theme.Palette.caution
                    )
                }
                heroCard(response.assignment)
                focusSection(response)
                upcomingSection(response)
            }
            .padding(Theme.Spacing.l)
        }
        .refreshable { await viewModel.load(showLoading: false) }
    }

    private func header(_ response: TodayResponse) -> some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Text(Theme.greeting())
                    .font(.title3.weight(.semibold))
                Text(Theme.formattedDate(response.localDate))
                    .font(.subheadline)
                    .foregroundStyle(Theme.Palette.secondaryText)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: Theme.Spacing.xs) {
                Chip(text: "Level \(response.level)", systemImage: "star.fill", tint: Theme.Palette.accent)
                Text("\(response.totalXp) XP")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(Theme.Palette.secondaryText)
                if response.streakCount > 0 {
                    Text("\(response.streakCount) day streak")
                        .font(.caption2)
                        .foregroundStyle(Theme.Palette.tertiaryText)
                }
            }
        }
        .accessibilityElement(children: .contain)
    }

    private func heroCard(_ assignment: TodayAssignment) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                HStack(spacing: Theme.Spacing.s) {
                    Chip(text: assignment.contextLabel, systemImage: "building.2")
                    Chip(
                        text: assignment.primarySkillLabel,
                        systemImage: "target",
                        tint: Theme.Palette.accent
                    )
                    Spacer(minLength: 0)
                }

                Text(assignment.title)
                    .font(.title2.weight(.bold))
                    .fixedSize(horizontal: false, vertical: true)

                Text(assignment.summary)
                    .font(.subheadline)
                    .foregroundStyle(Theme.Palette.secondaryText)
                    .fixedSize(horizontal: false, vertical: true)

                HStack(spacing: Theme.Spacing.m) {
                    Label("\(assignment.estimatedMinutes) min", systemImage: "clock")
                    Label(Theme.levelLabel(assignment.level), systemImage: "chart.bar")
                    if let score = assignment.score {
                        Label("\(score)/100", systemImage: "checkmark.seal")
                    }
                }
                .font(.caption)
                .foregroundStyle(Theme.Palette.tertiaryText)

                if let status = assignment.state.statusLabel {
                    InlineNotice(text: status, systemImage: statusSymbol(assignment.state))
                }

                PrimaryButton(title: assignment.state.callToAction) {
                    viewModel.openChallenge()
                }
            }
        }
    }

    private func statusSymbol(_ state: ChallengeState) -> String {
        switch state {
        case .inProgress: return "pencil.line"
        case .submitted, .awaitingFeedback: return "hourglass"
        case .complete: return "checkmark.circle"
        case .feedbackFailed: return "exclamationmark.triangle"
        case .notStarted: return "circle"
        }
    }

    private func focusSection(_ response: TodayResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            SectionHeader(title: "Your focus", subtitle: "The two skills this week leans on.")
            ForEach(response.focusSkills) { skill in
                CardContainer(padding: Theme.Spacing.m) { SkillRow(skill: skill) }
            }
        }
    }

    private func upcomingSection(_ response: TodayResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            SectionHeader(title: "Coming up", subtitle: "Preview only — one challenge a day.")
            ForEach(response.upcoming.dropFirst()) { day in
                HStack(spacing: Theme.Spacing.m) {
                    VStack(spacing: 2) {
                        Text(Theme.shortWeekday(day.localDate))
                            .font(.caption2.weight(.bold))
                        Text(String(day.localDate.suffix(2)))
                            .font(.footnote.monospacedDigit())
                    }
                    .frame(width: 32)
                    .foregroundStyle(Theme.Palette.secondaryText)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(day.title).font(.subheadline).lineLimit(2)
                        Text("\(day.primarySkillLabel) · \(day.estimatedMinutes) min")
                            .font(.caption)
                            .foregroundStyle(Theme.Palette.tertiaryText)
                    }
                    Spacer(minLength: 0)
                }
                .padding(Theme.Spacing.m)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    Theme.Palette.surface, in: RoundedRectangle(cornerRadius: Theme.Radius.control)
                )
                .accessibilityElement(children: .combine)
            }
        }
    }
}

struct AssignmentRoute: Identifiable, Equatable {
    let id: String
}
