import SwiftUI

/// Упражнение — формирующее. Оно не оценивает: кнопка называется «Понятно», а не
/// «Правильно/Неправильно», эталонный разбор показывается всегда — в том числе на
/// пустой ответ, потому что именно тот, кто не знал, как подступиться, и должен его
/// увидеть. В скоринг гейта упражнения не входят и XP не дают.
struct ExerciseView: View {
    @StateObject var viewModel: ExerciseViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                if let exercise = viewModel.exercise {
                    Text(exercise.title).font(.title3.weight(.bold))
                    ForEach(Array(exercise.promptBlocks.enumerated()), id: \.offset) { _, block in
                        LessonBlockRenderer(block: block, diagrams: exercise.diagrams)
                    }
                    inputs(exercise)
                    if let result = viewModel.result {
                        reference(result)
                    } else {
                        actions
                    }
                } else if viewModel.isLoading {
                    ProgressView()
                }
            }
            .padding(Theme.Spacing.l)
        }
        .navigationTitle(S.Exercise.title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await viewModel.load() }
    }

    private func inputs(_ exercise: ExerciseResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            ForEach(exercise.inputs) { input in
                VStack(alignment: .leading, spacing: 4) {
                    Text(input.unit.map { "\(input.label), \($0)" } ?? input.label)
                        .font(.footnote.weight(.semibold))
                    field(for: input)
                    if let outcome = viewModel.outcome(for: input.id) {
                        Text(outcome)
                            .font(.caption)
                            .foregroundStyle(Theme.Palette.secondaryText)
                    }
                }
            }
        }
    }

    /// Варианты выбора — меню, а не сегменты: формулировки здесь длинные
    /// («только цитата из данных или отказ»), и в сегменты они не помещаются.
    @ViewBuilder
    private func field(for input: ExerciseInputView) -> some View {
        if input.choices.isEmpty {
            TextField("", text: viewModel.binding(for: input.id))
                .textFieldStyle(.roundedBorder)
                .keyboardType(input.type == "number" ? .decimalPad : .default)
        } else {
            let selection = viewModel.binding(for: input.id)
            let chosen = selection.wrappedValue
            Menu {
                Picker(input.label, selection: selection) {
                    Text(S.Exercise.chooseAnswer).tag("")
                    ForEach(input.choices, id: \.self) { Text($0).tag($0) }
                }
                .pickerStyle(.inline)
            } label: {
                HStack {
                    Text(chosen.isEmpty ? S.Exercise.chooseAnswer : chosen)
                        .foregroundStyle(
                            chosen.isEmpty ? Theme.Palette.secondaryText : Theme.Palette.primaryText
                        )
                        .multilineTextAlignment(.leading)
                    Spacer(minLength: Theme.Spacing.s)
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.caption)
                        .foregroundStyle(Theme.Palette.secondaryText)
                }
                .padding(.horizontal, Theme.Spacing.s)
                .padding(.vertical, 10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: Theme.Radius.control)
                        .strokeBorder(Theme.Palette.separator)
                )
            }
            .accessibilityLabel(input.label)
            .accessibilityValue(chosen.isEmpty ? S.Exercise.notAnswered : chosen)
        }
    }

    private var actions: some View {
        VStack(spacing: Theme.Spacing.s) {
            Button(S.Exercise.check) {
                Task { await viewModel.submit(skipped: false) }
            }
            .buttonStyle(.borderedProminent)
            .disabled(viewModel.isSubmitting)

            // «Посмотреть разбор» доступно всегда: разбор — и есть ценность.
            Button(S.Exercise.showReference) {
                Task { await viewModel.submit(skipped: true) }
            }
            .buttonStyle(.plain)
            .foregroundStyle(Theme.Palette.accent)
        }
        .frame(maxWidth: .infinity)
    }

    private func reference(_ result: ExerciseSubmitResponse) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            Text(S.Exercise.reference)
                .font(.footnote.weight(.semibold))
                .foregroundStyle(Theme.Palette.secondaryText)
            ForEach(Array(result.referenceReasoningBlocks.enumerated()), id: \.offset) { _, block in
                LessonBlockRenderer(block: block, diagrams: viewModel.exercise?.diagrams ?? [])
            }
            Button(S.Exercise.understood) { dismiss() }
                .buttonStyle(.borderedProminent)
                .frame(maxWidth: .infinity)
        }
        .padding(.top, Theme.Spacing.s)
    }
}
