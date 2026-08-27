import SwiftUI

/// A lesson: three to five minutes, one idea, ending in a decision to move on.
///
/// The reader stays on this screen for the whole block — finishing one lesson offers
/// the next in place rather than bouncing back to the list.
struct LessonView: View {
    @StateObject private var viewModel: LessonViewModel
    @EnvironmentObject private var container: AppContainer
    @Environment(\.dismiss) private var dismiss
    @State private var selectedTerm: TermView?
    @StateObject private var audio: LessonAudioViewModel
    let onFinish: () -> Void

    init(
        viewModel: @autoclosure @escaping () -> LessonViewModel,
        audio: @autoclosure @escaping () -> LessonAudioViewModel,
        onFinish: @escaping () -> Void
    ) {
        _viewModel = StateObject(wrappedValue: viewModel())
        _audio = StateObject(wrappedValue: audio())
        self.onFinish = onFinish
    }

    var body: some View {
        Group {
            if let lesson = viewModel.lesson {
                content(lesson)
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
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .onChange(of: viewModel.lesson?.id) { _, _ in
            audio.nowPlayingTitle = viewModel.lesson?.title ?? ""
            audio.configure(with: viewModel.lesson?.audio)
        }
        // Звук не переживает экран: уходя с урока, плеер останавливается и
        // освобождает аудиосессию, иначе музыка пользователя не вернётся.
        .onDisappear { audio.teardown() }
        .sheet(item: $selectedTerm) { term in
            TermCard(term: term)
                .presentationDetents([.medium])
        }
    }

    private func content(_ lesson: LessonResponse) -> some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                    header(lesson).appear(0)

                    if audio.state != .unavailable {
                        LessonAudioPlayer(viewModel: audio).appear(1)
                    }

                    let body = renderedBlocks(lesson)
                    ForEach(Array(body.enumerated()), id: \.offset) { index, block in
                        LessonBlockRenderer(
                            block: block,
                            diagrams: lesson.diagrams,
                            onTapTerm: { openTerm($0, in: lesson) }
                        )
                        .appear(index + 1)
                    }

                    takeaway(lesson).appear(body.count + 1)

                    if !lesson.terms.isEmpty {
                        termChips(lesson).appear(body.count + 2)
                    }

                    if let question = lesson.checkQuestion {
                        checkQuestion(question).appear(body.count + 3)
                    }

                    if let exerciseId = lesson.exerciseId {
                        exerciseLink(exerciseId).appear(body.count + 4)
                    }
                }
                .padding(Theme.Spacing.l)
                .id(lesson.id)
            }

            footer(lesson)
        }
        .animation(Motion.standard, value: lesson.id)
    }

    /// Урок основного дерева приходит плоскими блоками, System Design — секциями.
    /// Заголовки секций не показываем: «Вопрос», «Цена» — структура для автора,
    /// а вывод и так выделен отдельным блоком под текстом.
    private func renderedBlocks(_ lesson: LessonResponse) -> [LessonBlockView] {
        guard lesson.isSectioned else { return lesson.blocks }
        return lesson.sections
            .filter { $0.kind != "takeaway" }
            .flatMap(\.blocks)
    }

    private func openTerm(_ termId: String, in lesson: LessonResponse) {
        guard let term = lesson.terms.first(where: { $0.id == termId }) else { return }
        selectedTerm = term
        container.analytics.track(
            .termTapped(termId: term.id, lessonId: lesson.id, isFirstEncounter: !term.seen)
        )
    }

    /// Термины урока: тап открывает карточку с определением и английским эквивалентом.
    private func termChips(_ lesson: LessonResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            Text(S.Lesson.terms)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Theme.Palette.secondaryText)
            FlowLayout(spacing: Theme.Spacing.s) {
                ForEach(lesson.terms) { term in
                    Button {
                        selectedTerm = term
                        container.analytics.track(
                            .termTapped(
                                termId: term.id,
                                lessonId: lesson.id,
                                isFirstEncounter: !term.seen
                            )
                        )
                    } label: {
                        Text(term.term)
                            .font(.caption)
                            .padding(.horizontal, Theme.Spacing.s)
                            .padding(.vertical, 4)
                            .background(
                                Theme.Palette.accent.opacity(0.12),
                                in: Capsule()
                            )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func exerciseLink(_ exerciseId: String) -> some View {
        NavigationLink {
            ExerciseView(
                viewModel: ExerciseViewModel(
                    exerciseId: exerciseId,
                    client: container.apiClient,
                    analytics: container.analytics
                )
            )
        } label: {
            HStack {
                Image(systemName: "function")
                Text(S.Lesson.exercise)
                Spacer()
                Image(systemName: "chevron.right").font(.caption)
            }
            .padding(Theme.Spacing.m)
            .background(
                Theme.Palette.surface,
                in: RoundedRectangle(cornerRadius: Theme.Radius.control)
            )
        }
        .buttonStyle(.plain)
    }

    private func header(_ lesson: LessonResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            HStack(spacing: Theme.Spacing.s) {
                Chip(text: lesson.nodeTitle, systemImage: "point.3.filled.connected.trianglepath.dotted")
                Chip(text: S.Common.minutes(lesson.estimatedMinutes), systemImage: "clock")
                Spacer(minLength: 0)
            }
            Text(lesson.title)
                .font(.title2.weight(.bold))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func takeaway(_ lesson: LessonResponse) -> some View {
        CardContainer(isHighlighted: true) {
            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Label(S.Lesson.takeaway, systemImage: "key")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(Theme.Palette.accent)
                Text(lesson.keyTakeaway)
                    .font(.body)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func checkQuestion(_ question: String) -> some View {
        CardContainer {
            VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                Label(S.Lesson.checkYourself, systemImage: "questionmark.circle")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(Theme.Palette.secondaryText)
                Text(question)
                    .font(.subheadline)
                    .fixedSize(horizontal: false, vertical: true)
                // Deliberately unscored: this is a prompt to think, not a quiz. The
                // gate is where application is checked (spec v0.2 §8).
                Text(S.Lesson.checkNotScored)
                    .font(.caption2)
                    .foregroundStyle(Theme.Palette.tertiaryText)
            }
        }
    }

    private func footer(_ lesson: LessonResponse) -> some View {
        VStack(spacing: Theme.Spacing.s) {
            if let result = viewModel.result, result.xpAwarded > 0 {
                Chip(
                    text: S.Challenge.xpAwarded(result.xpAwarded),
                    systemImage: "sparkles",
                    tint: Theme.Palette.accent
                )
                .transition(.scale.combined(with: .opacity))
            }

            if viewModel.isCompleted, let nextId = lesson.nextLessonId {
                PrimaryButton(title: S.Lesson.nextLesson, systemImage: "arrow.right") {
                    Task { await viewModel.advance(to: nextId) }
                }
            } else if viewModel.isCompleted {
                PrimaryButton(title: S.Lesson.backToBlock) {
                    onFinish()
                    dismiss()
                }
            } else {
                PrimaryButton(
                    title: S.Lesson.markRead,
                    systemImage: "checkmark",
                    isLoading: viewModel.isCompleting
                ) {
                    Task {
                        await viewModel.complete()
                        Haptics.success()
                        onFinish()
                    }
                }
            }
        }
        .padding(Theme.Spacing.l)
        .background(.bar)
        .animation(Motion.standard, value: viewModel.isCompleted)
    }
}

/// Renders one authored content block. An unknown type is skipped rather than shown
/// raw, so adding a block type on the server cannot break an older client.
struct LessonBlockRenderer: View {
    let block: LessonBlockView
    /// Схемы приезжают вместе с уроком, поэтому ссылка на схему рисуется на месте.
    var diagrams: [DiagramView] = []
    /// Термин в тексте открывает карточку; без обработчика подчёркивание не рисуется.
    var onTapTerm: ((String) -> Void)?

    var body: some View {
        switch block.type {
        case "table":
            table
        case "diagram_ref":
            if let id = block.diagramId, let diagram = diagrams.first(where: { $0.id == id }) {
                DiagramCanvas(diagram: diagram)
            }
        case "code":
            Text(block.text ?? "")
                .font(.system(.footnote, design: .monospaced))
                .padding(Theme.Spacing.m)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    Theme.Palette.background,
                    in: RoundedRectangle(cornerRadius: Theme.Radius.control)
                )
        case "paragraph":
            text(block.text ?? "")
                .font(.body)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)

        case "list":
            VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                ForEach(Array((block.items ?? []).enumerated()), id: \.offset) { index, item in
                    HStack(alignment: .top, spacing: Theme.Spacing.s) {
                        Text(block.ordered == true ? "\(index + 1)." : "•")
                            .font(.body.weight(.semibold).monospacedDigit())
                            .foregroundStyle(Theme.Palette.accent)
                        text(item)
                            .font(.body)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

        case "model_card":
            CardContainer {
                VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                    Text(block.title ?? "").font(.headline)
                    if let subtitle = block.subtitle {
                        Text(subtitle)
                            .font(.subheadline)
                            .foregroundStyle(Theme.Palette.secondaryText)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                        ForEach(Array((block.items ?? []).enumerated()), id: \.offset) { _, item in
                            HStack(alignment: .top, spacing: Theme.Spacing.s) {
                                Circle()
                                    .fill(Theme.Palette.accent)
                                    .frame(width: 5, height: 5)
                                    .padding(.top, 7)
                                MarkdownText(item)
                                    .font(.subheadline)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }
                    }
                }
            }

        case "example":
            CardContainer {
                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                    Label(block.title ?? S.Lesson.example, systemImage: "text.book.closed")
                        .font(.footnote.weight(.semibold))
                        .foregroundStyle(Theme.Palette.secondaryText)
                    Text(block.text ?? "")
                        .font(.subheadline)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

        case "callout":
            InlineNotice(
                text: [block.title, block.text].compactMap { $0 }.joined(separator: " — "),
                systemImage: Self.symbol(for: block.tone),
                tint: Self.tint(for: block.tone)
            )

        default:
            EmptyView()
        }
    }

    /// Абзац с размеченными терминами, если обработчик тапа передан; иначе обычный
    /// текст — у уроков основного дерева терминов нет.
    @ViewBuilder private func text(_ raw: String) -> some View {
        if let onTapTerm, raw.contains("[[") {
            TermText(raw: raw, onTapTerm: onTapTerm)
        } else {
            MarkdownText(raw)
        }
    }

    /// Таблица рисуется сеткой, а не текстом: в уроках домена она несёт сравнение,
    /// и слипшиеся строки его теряют.
    private var table: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let header = block.header {
                HStack(alignment: .top, spacing: Theme.Spacing.m) {
                    ForEach(Array(header.enumerated()), id: \.offset) { _, cell in
                        Text(cell)
                            .font(.caption.weight(.semibold))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                Divider()
            }
            ForEach(Array((block.rows ?? []).enumerated()), id: \.offset) { _, row in
                HStack(alignment: .top, spacing: Theme.Spacing.m) {
                    ForEach(Array(row.enumerated()), id: \.offset) { _, cell in
                        text(cell)
                            .font(.footnote)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
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

    private static func symbol(for tone: String?) -> String {
        switch tone {
        case "warning": return "exclamationmark.triangle"
        case "limit": return "scope"
        default: return "info.circle"
        }
    }

    private static func tint(for tone: String?) -> Color {
        switch tone {
        case "warning": return Theme.Palette.caution
        case "limit": return Theme.Palette.accent
        default: return Theme.Palette.secondaryText
        }
    }
}

/// Authored text uses `**bold**` for emphasis; anything unparseable falls back to the
/// raw string rather than dropping the paragraph.
struct MarkdownText: View {
    let raw: String

    init(_ raw: String) { self.raw = raw }

    var body: some View {
        if let attributed = try? AttributedString(
            markdown: raw,
            options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        ) {
            Text(attributed)
        } else {
            Text(raw)
        }
    }
}
