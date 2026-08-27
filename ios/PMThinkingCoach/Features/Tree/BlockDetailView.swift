import SwiftUI

/// A block: its nodes, their lessons, and the gate that closes it.
///
/// A locked block opens too — it shows what it contains and what has to be passed to
/// reach it. A grey placeholder would make the map a wall instead of a route.
struct BlockDetailView: View {
    @EnvironmentObject private var container: AppContainer
    @StateObject private var viewModel: BlockViewModel
    @State private var openLessonId: String?

    init(viewModel: @autoclosure @escaping () -> BlockViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        Group {
            if let detail = viewModel.detail {
                content(detail)
            } else if viewModel.isLoading {
                LoadingState()
            } else if let error = viewModel.error {
                ErrorState(title: S.Common.couldntLoad, message: error.userMessage) {
                    Task { await viewModel.load() }
                }
            } else {
                LoadingState()
            }
        }
        .background(Theme.Palette.background)
        .navigationTitle(viewModel.detail?.block.title ?? "")
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .navigationDestination(item: $openLessonId) { lessonId in
            LessonView(viewModel: container.makeLessonViewModel(lessonId: lessonId)) {
                Task { await viewModel.load() }
            }
        }
        .fullScreenCover(item: $viewModel.startedGate) { challenge in
            ChallengeFlowView(
                viewModel: container.makeChallengeViewModel(challenge: challenge)
            )
            .onDisappear { Task { await viewModel.load() } }
        }
    }

    private func content(_ detail: BlockDetailResponse) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                header(detail).appear(0)

                ForEach(Array(detail.nodes.enumerated()), id: \.element.id) { index, node in
                    nodeCard(node, isOpen: detail.block.status.isOpen).appear(index + 1)
                }

                gateSection(detail).appear(detail.nodes.count + 1)
            }
            .padding(Theme.Spacing.l)
        }
        .refreshable { await viewModel.load() }
    }

    private func header(_ detail: BlockDetailResponse) -> some View {
        CardContainer(isHighlighted: detail.block.status.isOpen) {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                HStack(spacing: Theme.Spacing.s) {
                    Chip(text: detail.domainTitle, systemImage: "square.grid.3x3")
                    Chip(
                        text: detail.tierTitle,
                        systemImage: "circle.circle",
                        tint: Theme.Palette.accent
                    )
                    Spacer(minLength: 0)
                }
                Text(S.Tree.statusLabel(detail.block.status))
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(S.Tree.statusTint(detail.block.status))

                if detail.block.status == .locked {
                    InlineNotice(
                        text: S.Tree.lockedExplanation(detail.block.prerequisiteBlockIds),
                        systemImage: "lock"
                    )
                } else if !detail.block.isWritten {
                    InlineNotice(text: S.Tree.comingSoon, systemImage: "hammer")
                } else {
                    ProgressTrack(progress: detail.block.lessonProgress, height: 8)
                    Text(
                        S.Tree.lessonsProgress(
                            detail.block.lessonsCompleted, detail.block.lessonsTotal
                        )
                    )
                    .font(.caption)
                    .foregroundStyle(Theme.Palette.tertiaryText)
                }
            }
        }
    }

    private func nodeCard(_ node: NodeDetail, isOpen: Bool) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                    Text(node.node.title)
                        .font(.headline)
                        .fixedSize(horizontal: false, vertical: true)
                    Text(node.node.keyQuestion)
                        .font(.subheadline)
                        .foregroundStyle(Theme.Palette.secondaryText)
                        .fixedSize(horizontal: false, vertical: true)
                }

                if !node.node.models.isEmpty {
                    // Model names are terms of art and stay in their original form.
                    FlowChips(items: node.node.models)
                }

                if node.lessons.isEmpty {
                    InlineNotice(text: S.Tree.lessonsComingSoon, systemImage: "hourglass")
                } else {
                    VStack(spacing: Theme.Spacing.s) {
                        ForEach(node.lessons) { lesson in
                            lessonRow(lesson, isOpen: isOpen)
                        }
                    }
                }
            }
        }
        .accessibilityElement(children: .contain)
    }

    private func lessonRow(_ lesson: LessonSummary, isOpen: Bool) -> some View {
        Button {
            guard isOpen else { return }
            Haptics.tap()
            openLessonId = lesson.id
        } label: {
            HStack(spacing: Theme.Spacing.m) {
                Image(systemName: lesson.completed ? "checkmark.circle.fill" : "book")
                    .foregroundStyle(
                        lesson.completed ? Theme.Palette.positive : Theme.Palette.accent
                    )
                    .contentTransition(.symbolEffect(.replace))
                VStack(alignment: .leading, spacing: 1) {
                    Text(lesson.title)
                        .font(.subheadline)
                        .foregroundStyle(Theme.Palette.primaryText)
                        .multilineTextAlignment(.leading)
                    Text(S.Common.minutes(lesson.estimatedMinutes))
                        .font(.caption2)
                        .foregroundStyle(Theme.Palette.tertiaryText)
                }
                Spacer(minLength: 0)
                if isOpen {
                    Image(systemName: "chevron.right")
                        .font(.footnote)
                        .foregroundStyle(Theme.Palette.tertiaryText)
                }
            }
            .frame(minHeight: Theme.minimumTapTarget)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(!isOpen)
        .opacity(isOpen ? 1 : 0.5)
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isButton)
    }

    private func gateSection(_ detail: BlockDetailResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            SectionHeader(title: S.Tree.gateTitle, subtitle: S.Tree.gateSubtitle(detail.passThreshold))

            if let error = viewModel.error {
                InlineNotice(
                    text: error.userMessage,
                    systemImage: "exclamationmark.circle",
                    tint: Theme.Palette.negative
                )
            }

            if detail.gateAvailable {
                PrimaryButton(
                    title: detail.block.attemptCount > 0 ? S.Tree.retakeGate : S.Tree.takeGate,
                    systemImage: "flag.checkered",
                    isLoading: viewModel.isStartingGate
                ) {
                    Task { await viewModel.startGate() }
                }
            } else {
                PrimaryButton(title: S.Tree.takeGate, isEnabled: false) {}
                InlineNotice(
                    text: S.Tree.gateBlockedReason(
                        detail.gateBlockedReason, remaining: detail.lessonsRemaining
                    ),
                    systemImage: "info.circle"
                )
            }
        }
        .animation(Motion.standard, value: detail.gateAvailable)
    }
}

/// Wrapping row of small labels. Used for the models a node draws on.
struct FlowChips: View {
    let items: [String]

    var body: some View {
        FlowLayout(spacing: Theme.Spacing.xs) {
            ForEach(items, id: \.self) { item in
                Text(item)
                    .font(.caption2)
                    .padding(.horizontal, Theme.Spacing.s)
                    .padding(.vertical, 3)
                    .background(Theme.Palette.separator.opacity(0.22), in: Capsule())
                    .foregroundStyle(Theme.Palette.secondaryText)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(items.joined(separator: ", "))
    }
}

/// Left-aligned wrapping layout. Model names vary from "5 Whys" to "Value Proposition
/// Canvas", so a fixed grid either truncates or wastes most of a row.
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x > 0, x + size.width > width {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
        return CGSize(width: proposal.width ?? x, height: y + rowHeight)
    }

    func placeSubviews(
        in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()
    ) {
        var x = bounds.minX
        var y = bounds.minY
        var rowHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x > bounds.minX, x + size.width > bounds.maxX {
                x = bounds.minX
                y += rowHeight + spacing
                rowHeight = 0
            }
            subview.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
    }
}
