/** Упражнение — формирующее.
 *
 *  Оно не оценивает: кнопка называется «Понятно», а не «Правильно/Неправильно», и
 *  эталонный разбор показывается всегда — в том числе на пустой ответ, потому что
 *  именно тот, кто не знал, как подступиться, и должен его увидеть. В скоринг гейта
 *  упражнения не входят и XP не дают.
 */
import { h, fill } from "../dom.js";
import { button, loadingState, errorState } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { breadcrumb } from "./chrome.js";
import { renderBlocks } from "./content.js";

export function exerciseView({ id }) {
  const node = h("div.page");
  let exercise = null;
  let result = null;
  let error = null;
  const values = {};

  const load = async () => {
    try {
      exercise = await api.exercise(id);
      Object.assign(values, exercise.submittedValues || {});
      error = null;
    } catch (apiError) {
      error = apiError;
    }
    render();
  };

  const submit = async (skipped) => {
    result = await api.submitExercise(id, skipped ? {} : values);
    render();
  };

  /** Формулировка зависит от типа упражнения и нигде не говорит «неправильно»:
   *  у прикидки сверяется порядок величины, у разбора по категориям — совпадение
   *  с эталоном. */
  const outcome = (inputId) => {
    if (!result) return null;
    const item = result.results.find((candidate) => candidate.inputId === inputId);
    if (!item) return null;
    if (item.withinRange === null || item.withinRange === undefined) return S.Exercise.notAnswered;
    const base =
      exercise.type === "classification"
        ? item.withinRange
          ? S.Exercise.sameAsReference
          : S.Exercise.otherThanReference
        : item.withinRange
          ? S.Exercise.orderRight
          : S.Exercise.orderOff;
    return item.expectedHint && !item.withinRange ? `${base} · ${item.expectedHint}` : base;
  };

  const field = (input) => {
    if (!input.choices?.length) {
      return h("input", {
        type: "text",
        inputmode: input.type === "number" ? "decimal" : "text",
        value: values[input.id] || "",
        "aria-label": input.label,
        oninput: (event) => {
          values[input.id] = event.target.value;
        },
      });
    }
    // Варианты выбора — список, а не сегменты: формулировки здесь длинные.
    return h(
      "select",
      {
        "aria-label": input.label,
        onchange: (event) => {
          values[input.id] = event.target.value;
        },
      },
      h("option", { value: "", selected: !values[input.id] }, S.Exercise.chooseAnswer),
      input.choices.map((choice) =>
        h("option", { value: choice, selected: values[input.id] === choice }, choice)
      )
    );
  };

  const render = () => {
    if (!exercise && error) {
      fill(node, breadcrumb(S.Common.back), errorState(S.Common.couldntLoad, error.userMessage, load));
      return;
    }
    if (!exercise) {
      fill(node, breadcrumb(S.Common.back), loadingState());
      return;
    }

    fill(
      node,
      breadcrumb(S.Exercise.title),
      h("h1", exercise.title),
      h("div.lesson-body", renderBlocks(exercise.promptBlocks, { diagrams: exercise.diagrams })),
      h(
        "div.stack",
        exercise.inputs.map((input) =>
          h(
            "div.stack.s",
            h("label.small", { style: { fontWeight: "600" } }, input.unit ? `${input.label}, ${input.unit}` : input.label),
            field(input),
            outcome(input.id) && h("div.caption.muted", outcome(input.id))
          )
        )
      ),
      result ? reference() : actions()
    );
  };

  const actions = () =>
    h(
      "div.stack.s",
      button(S.Exercise.check, () => submit(false), { wide: true }),
      // «Посмотреть разбор» доступно всегда: разбор — и есть ценность.
      button(S.Exercise.showReference, () => submit(true), { variant: "quiet" })
    );

  const reference = () =>
    h(
      "div.stack",
      h("div.caption.muted", { style: { fontWeight: "600" } }, S.Exercise.reference),
      h("div.lesson-body", renderBlocks(result.referenceReasoningBlocks, { diagrams: exercise.diagrams })),
      button(S.Exercise.understood, () => window.history.back(), { wide: true })
    );

  render();
  load();
  return node;
}
