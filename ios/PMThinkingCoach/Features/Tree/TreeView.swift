import SwiftUI

/// The first tab: the whole skill map, with exactly one route open at the start.
struct TreeView: View {
    @EnvironmentObject private var container: AppContainer
    @StateObject private var viewModel: TreeViewModel

    init(viewModel: @autoclosure @escaping () -> TreeViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel())
    }

    var body: some View {
        NavigationStack {
            Group {
                switch viewModel.state {
                case .idle, .loading:
                    LoadingState(message: S.Tree.loading)
                case .failed(let error):
                    ErrorState(title: S.Tree.loadFailed, message: error.userMessage) {
                        Task { await viewModel.load() }
                    }
                case .loaded(let tree):
                    content(tree)
                }
            }
            .animation(Motion.standard, value: viewModel.state)
            .background(Theme.Palette.background)
            .navigationTitle(S.Tab.tree)
            // Компактный заголовок обязателен: с крупным вместе с `safeAreaInset`
            // система резервирует под него место, но текст не рисует — шапка выходит
            // пустой на 100pt. Компактный к тому же возвращает эту высоту карте,
            // которая на этом экране и есть содержание.
            .navigationBarTitleDisplayMode(.inline)
            .safeAreaInset(edge: .top) { treeSwitcher }
            .navigationDestination(item: $viewModel.selectedBlockId) { blockId in
                BlockDetailView(viewModel: container.makeBlockViewModel(blockId: blockId))
            }
        }
        .task { await viewModel.load() }
    }

    /// Две карты одной грамматики. Переключатель, а не объединение: восемнадцать
    /// блоков System Design не помещаются седьмым сектором — сектор стал бы вчетверо
    /// плотнее остальных, и карта перестала бы читаться. Четвёртого таба тоже нет:
    /// корневых табов ровно три.
    private var treeSwitcher: some View {
        Picker("", selection: $viewModel.kind) {
            Text(S.Trees.product).tag("product")
            Text(S.Trees.systems).tag("system_design")
        }
        .pickerStyle(.segmented)
        .padding(.horizontal, Theme.Spacing.l)
        .padding(.bottom, Theme.Spacing.s)
        .background(.bar)
    }

    private func content(_ tree: TreeResponse) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {

                if let suggested = viewModel.suggested {
                    nextCard(suggested).appear(0)
                }

                SkillRingMap(
                    tree: tree,
                    highlighted: viewModel.suggested?.id,
                    onSelect: { viewModel.open($0) }
                )
                .padding(.horizontal, Theme.Spacing.s)
                .appear(1)

                legend(tree).appear(2)
                domains(tree).appear(3)

                Text(tree.sourceAttribution)
                    .font(.caption2)
                    .foregroundStyle(Theme.Palette.tertiaryText)
                    .fixedSize(horizontal: false, vertical: true)
                    .appear(4)
            }
            .padding(Theme.Spacing.l)
        }
        .refreshable { await viewModel.load(showLoading: false) }
    }

    /// The practical entry point. The rings show the shape of the journey; this says
    /// what to press right now, which is what a beginner actually needs.
    private func nextCard(_ block: BlockSummary) -> some View {
        CardContainer(isHighlighted: true) {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                HStack(spacing: Theme.Spacing.s) {
                    Chip(
                        text: viewModel.tree?.tierName(block.tier)
                            ?? S.Tree.tierName(block.tier),
                        systemImage: "circle.circle",
                        tint: Theme.Palette.accent
                    )
                    Chip(text: block.id, systemImage: "point.3.connected.trianglepath.dotted")
                    Spacer(minLength: 0)
                }
                Text(S.Tree.continueHere)
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(Theme.Palette.accent)
                Text(block.title)
                    .font(.title2.weight(.bold))
                    .fixedSize(horizontal: false, vertical: true)
                Text(S.Tree.lessonsProgress(block.lessonsCompleted, block.lessonsTotal))
                    .font(.subheadline)
                    .foregroundStyle(Theme.Palette.secondaryText)
                ProgressTrack(progress: block.lessonProgress, height: 8)
                PrimaryButton(title: S.Tree.openBlock) { viewModel.open(block) }
            }
        }
    }

    private func legend(_ tree: TreeResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            SectionHeader(title: S.Tree.tiersTitle, subtitle: S.Tree.tiersSubtitle)
            // Номер круга не дублируется цифрой слева: он уже в самом названии.
            ForEach(tree.tiers) { tier in
                VStack(alignment: .leading, spacing: 0) {
                    Text(tier.title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Theme.Palette.accent)
                    Text(tier.subtitle)
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.secondaryText)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .accessibilityElement(children: .combine)
            }
        }
    }

    private func domains(_ tree: TreeResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            SectionHeader(title: S.Tree.domainsTitle, subtitle: S.Tree.domainsSubtitle)
            ForEach(tree.domains) { domain in
                let blocks = tree.blocks(inDomain: domain.key)
                VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                    Text(domain.title).font(.subheadline.weight(.semibold))
                    HStack(spacing: Theme.Spacing.s) {
                        ForEach(blocks) { block in
                            Button {
                                Haptics.tap()
                                viewModel.open(block)
                            } label: {
                                blockPill(block)
                            }
                            .buttonStyle(.pressable)
                        }
                    }
                }
                .padding(Theme.Spacing.m)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    Theme.Palette.surface,
                    in: RoundedRectangle(cornerRadius: Theme.Radius.control)
                )
            }
        }
    }

    private func blockPill(_ block: BlockSummary) -> some View {
        VStack(spacing: 2) {
            HStack(spacing: 4) {
                Image(systemName: S.Tree.statusSymbol(block.status))
                    .font(.caption2)
                Text(block.id).font(.caption.weight(.bold))
            }
            Text(block.title)
                .font(.caption2)
                .lineLimit(2)
                .multilineTextAlignment(.leading)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, Theme.Spacing.s)
        .padding(.vertical, Theme.Spacing.s)
        .frame(maxWidth: .infinity, alignment: .leading)
        .foregroundStyle(
            block.status.isOpen ? Theme.Palette.primaryText : Theme.Palette.tertiaryText
        )
        .background(
            block.status == .passed
                ? Theme.Palette.accent.opacity(0.18)
                : Theme.Palette.separator.opacity(0.18),
            in: RoundedRectangle(cornerRadius: Theme.Radius.control)
        )
        .accessibilityElement(children: .combine)
    }
}
