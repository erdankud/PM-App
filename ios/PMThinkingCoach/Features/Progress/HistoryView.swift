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
                ErrorState(title: S.History.loadFailed, message: error.userMessage) {
                    Task { await viewModel.loadFirstPage() }
                }
            } else if viewModel.items.isEmpty {
                ContentUnavailableView(
                    S.History.emptyTitle,
                    systemImage: "flag.checkered",
                    description: Text(S.History.emptyBody)
                )
            } else {
                list
            }
        }
        .animation(Motion.standard, value: viewModel.items.count)
        .background(Theme.Palette.background)
        .navigationTitle(S.History.title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.loadFirstPage() }
    }

    private var list: some View {
        ScrollView {
            LazyVStack(spacing: Theme.Spacing.m) {
                ForEach(Array(viewModel.items.enumerated()), id: \.element.id) { index, item in
                    NavigationLink {
                        ResultDetailView(
                            viewModel: ResultDetailViewModel(
                                attemptId: item.attemptId, client: container.apiClient
                            )
                        )
                    } label: {
                        row(item)
                    }
                    .buttonStyle(.pressable)
                    .appear(index)
                    .simultaneousGesture(TapGesture().onEnded { viewModel.itemOpened(item) })
                }

                if viewModel.canLoadMore {
                    Button(S.History.loadMore) {
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
                    Text(S.History.blockAndAttempt(item.blockTitle, item.attemptIndex))
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
            Chip(
                text: item.passed == true ? S.History.passed : S.History.notPassed,
                systemImage: item.passed == true ? "checkmark" : "arrow.counterclockwise",
                tint: item.passed == true ? Theme.Palette.positive : Theme.Palette.caution
            )
        case .pending:
            Chip(
                text: S.History.feedbackPending,
                systemImage: "hourglass",
                tint: Theme.Palette.secondaryText
            )
        case .failed:
            Chip(
                text: S.History.coachingFailed,
                systemImage: "exclamationmark",
                tint: Theme.Palette.caution
            )
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
                    ErrorState(title: S.History.resultLoadFailed, message: error.userMessage) {
                        Task { await viewModel.load() }
                    }
                } else if let response = viewModel.feedback {
                    Text(response.scenarioTitle)
                        .font(.title2.weight(.bold))
                        .fixedSize(horizontal: false, vertical: true)
                        .appear(0)

                    CardContainer(isHighlighted: true) {
                        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                            Label(
                                S.Challenge.whatHappenedNext,
                                systemImage: "arrow.turn.down.right"
                            )
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(Theme.Palette.accent)
                            Text(response.consequence.optionLabel)
                                .font(.headline)
                            Text(response.consequence.text)
                                .font(.body)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                    .appear(1)

                    if let body = response.feedback {
                        CardContainer {
                            VStack(spacing: Theme.Spacing.m) {
                                ScoreHeadline(score: body.score, band: body.band)
                            }
                        }
                        .appear(2)
                        readOnlyPoints(S.Challenge.strengthsTitle, body.strengths).appear(3)
                        readOnlyPoints(S.Challenge.improvementsTitle, body.improvements).appear(4)
                        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                            SectionHeader(title: S.Challenge.sharperApproach)
                            CardContainer {
                                Text(body.sharperApproach)
                                    .font(.body)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                        .appear(5)
                    } else {
                        CardContainer {
                            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                                Label(
                                    response.status == .failed
                                        ? S.Challenge.coachingDidntFinish
                                        : S.Challenge.coachingStillPending,
                                    systemImage: "hourglass"
                                )
                                .font(.headline)
                                Text(S.History.pendingXpNote)
                                    .font(.subheadline)
                                    .foregroundStyle(Theme.Palette.secondaryText)
                                if response.retryAvailable {
                                    SecondaryButton(
                                        title: S.Challenge.retryCoaching,
                                        systemImage: "arrow.clockwise"
                                    ) {
                                        Task { await viewModel.retry() }
                                    }
                                }
                            }
                        }
                        .appear(2)
                    }
                }
            }
            .padding(Theme.Spacing.l)
            .animation(Motion.standard, value: viewModel.isLoading)
        }
        .background(Theme.Palette.background)
        .navigationTitle(S.History.resultTitle)
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
