import SwiftUI

/// History (spec §10.12, P0-11). Reverse chronological; tapping opens a read-only result.
struct HistoryView: View {
    @EnvironmentObject private var container: AppContainer
    @StateObject private var viewModel: HistoryViewModel

    init(viewModel: @autoclosure @escaping () -> HistoryViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        Group {
            if viewModel.items.isEmpty, viewModel.isLoading {
                LoadingState()
            } else if viewModel.items.isEmpty, let error = viewModel.error {
                ErrorState(title: "Couldn't load history", message: error.userMessage) {
                    Task { await viewModel.loadFirstPage() }
                }
            } else if viewModel.items.isEmpty {
                ContentUnavailableView(
                    "No completed challenges yet",
                    systemImage: "list.bullet.rectangle",
                    description: Text("Finish today's challenge and it will appear here.")
                )
            } else {
                list
            }
        }
        .background(Theme.Palette.background)
        .navigationTitle("History")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.loadFirstPage() }
    }

    private var list: some View {
        ScrollView {
            LazyVStack(spacing: Theme.Spacing.m) {
                ForEach(viewModel.items) { item in
                    NavigationLink {
                        ResultDetailView(
                            viewModel: ResultDetailViewModel(
                                attemptId: item.attemptId, client: container.apiClient
                            )
                        )
                    } label: {
                        row(item)
                    }
                    .buttonStyle(.plain)
                    .simultaneousGesture(TapGesture().onEnded { viewModel.itemOpened(item) })
                }

                if viewModel.canLoadMore {
                    Button("Load more") {
                        Task { await viewModel.loadNextPage() }
                    }
                    .frame(minHeight: Theme.minimumTapTarget)
                    .disabled(viewModel.isLoading)
                }
            }
            .padding(Theme.Spacing.l)
        }
        .refreshable { await viewModel.loadFirstPage() }
    }

    private func row(_ item: HistoryItem) -> some View {
        CardContainer(padding: Theme.Spacing.m) {
            HStack(alignment: .top, spacing: Theme.Spacing.m) {
                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                    Text(item.title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Theme.Palette.primaryText)
                        .multilineTextAlignment(.leading)
                        .lineLimit(2)
                    Text("\(Theme.formattedDate(item.localDate)) · \(item.primarySkillLabel)")
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.tertiaryText)
                    statusChip(item)
                }
                Spacer(minLength: 0)
                if let score = item.score {
                    VStack(spacing: 0) {
                        Text("\(score)")
                            .font(.title3.weight(.bold).monospacedDigit())
                        Text("/100")
                            .font(.caption2)
                            .foregroundStyle(Theme.Palette.tertiaryText)
                    }
                }
                Image(systemName: "chevron.right")
                    .font(.footnote)
                    .foregroundStyle(Theme.Palette.tertiaryText)
            }
        }
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder
    private func statusChip(_ item: HistoryItem) -> some View {
        switch item.feedbackStatus {
        case .complete:
            Chip(text: "Coaching ready", systemImage: "checkmark", tint: Theme.Palette.positive)
        case .pending:
            Chip(text: "Feedback pending", systemImage: "hourglass", tint: Theme.Palette.secondaryText)
        case .failed:
            Chip(text: "Coaching failed", systemImage: "exclamationmark", tint: Theme.Palette.caution)
        }
    }
}

/// Read-only result. Nothing on this screen can change a submitted attempt.
struct ResultDetailView: View {
    @StateObject private var viewModel: ResultDetailViewModel

    init(viewModel: @autoclosure @escaping () -> ResultDetailViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                if viewModel.isLoading {
                    LoadingState()
                } else if let error = viewModel.error {
                    ErrorState(title: "Couldn't load result", message: error.userMessage) {
                        Task { await viewModel.load() }
                    }
                } else if let response = viewModel.feedback {
                    Text(response.scenarioTitle)
                        .font(.title2.weight(.bold))
                        .fixedSize(horizontal: false, vertical: true)

                    CardContainer {
                        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                            Label("What happened next", systemImage: "arrow.turn.down.right")
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(Theme.Palette.accent)
                            Text(response.consequence.optionLabel)
                                .font(.headline)
                            Text(response.consequence.text)
                                .font(.body)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    if let body = response.feedback {
                        CardContainer {
                            VStack(spacing: Theme.Spacing.m) {
                                ScoreHeadline(score: body.score, band: body.band)
                            }
                        }
                        readOnlyPoints("What you did well", body.strengths)
                        readOnlyPoints("What to strengthen", body.improvements)
                        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                            SectionHeader(title: "A sharper approach")
                            CardContainer {
                                Text(body.sharperApproach)
                                    .font(.body)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    } else {
                        CardContainer {
                            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                                Label(
                                    response.status == .failed
                                        ? "Coaching didn't finish" : "Coaching still pending",
                                    systemImage: "hourglass"
                                )
                                .font(.headline)
                                Text("Your answer is saved. XP is pending until coaching completes.")
                                    .font(.subheadline)
                                    .foregroundStyle(Theme.Palette.secondaryText)
                                if response.retryAvailable {
                                    SecondaryButton(
                                        title: "Retry coaching", systemImage: "arrow.clockwise"
                                    ) {
                                        Task { await viewModel.retry() }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            .padding(Theme.Spacing.l)
        }
        .background(Theme.Palette.background)
        .navigationTitle("Result")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
    }

    private func readOnlyPoints(_ title: String, _ points: [FeedbackPoint]) -> some View {
        Group {
            if points.isEmpty {
                EmptyView()
            } else {
                VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                    SectionHeader(title: title)
                    ForEach(points) { point in
                        CardContainer {
                            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                                Text(point.title).font(.headline)
                                Text(point.detail)
                                    .font(.subheadline)
                                    .foregroundStyle(Theme.Palette.secondaryText)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                        .accessibilityElement(children: .combine)
                    }
                }
            }
        }
    }
}
