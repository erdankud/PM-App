import SwiftUI

/// Глоссарий домена System Design.
///
/// ICP — новичок, и в первом же уроке шесть незнакомых слов. Без карточки термина и
/// этого экрана домен для целевой аудитории нечитаем: это условие работоспособности,
/// а не украшение. Поиск идёт и по русскому, и по английскому — без английского
/// человек не найдёт материал вовне.
struct GlossaryView: View {
    @StateObject var viewModel: GlossaryViewModel
    @State private var selected: TermView?

    var body: some View {
        List {
            if viewModel.terms.isEmpty, !viewModel.isLoading {
                Text(S.Glossary.empty)
                    .foregroundStyle(Theme.Palette.secondaryText)
            }
            ForEach(viewModel.terms) { term in
                Button {
                    selected = term
                } label: {
                    row(term)
                }
                .buttonStyle(.plain)
            }
        }
        .listStyle(.plain)
        .searchable(text: $viewModel.query, prompt: S.Glossary.searchPrompt)
        .navigationTitle(S.Glossary.title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
        .onChange(of: viewModel.query) { _, _ in viewModel.scheduleSearch() }
        .sheet(item: $selected) { term in
            TermCard(term: term)
                .presentationDetents([.medium])
        }
    }

    private func row(_ term: TermView) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: Theme.Spacing.s) {
                Text(term.term).font(.body.weight(.medium))
                if term.seen {
                    // Отметка «встречал» ставится сама, когда термин попался в уроке.
                    Image(systemName: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.positive)
                        .accessibilityLabel(S.Glossary.seen)
                }
            }
            Text(term.termEn)
                .font(.caption)
                .foregroundStyle(Theme.Palette.tertiaryText)
            Text(term.definition)
                .font(.footnote)
                .foregroundStyle(Theme.Palette.secondaryText)
                .lineLimit(2)
        }
        .padding(.vertical, 4)
    }
}

/// Карточка термина: определение, английский эквивалент и переход в урок-источник.
struct TermCard: View {
    let term: TermView
    var onOpenLesson: ((String) -> Void)?

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            Text(term.term).font(.title3.weight(.bold))
            Text(term.termEn)
                .font(.subheadline)
                .foregroundStyle(Theme.Palette.secondaryText)
            Text(term.definition).font(.body)
            if let lessonId = term.sourceLessonId, let onOpenLesson {
                Button(S.Glossary.openLesson) { onOpenLesson(lessonId) }
                    .buttonStyle(.borderedProminent)
            }
            Spacer(minLength: 0)
        }
        .padding(Theme.Spacing.l)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
