/** Урок: одна мысль и решение идти дальше.
 *
 *  Зеркало `Features/Lesson/LessonView.swift`. Читатель остаётся на этом экране весь
 *  блок — законченный урок предлагает следующий здесь же, а не выбрасывает в список.
 *  На десктопе текст идёт колонкой, а вывод, термины и плеер стоят сбоку: ширины
 *  хватает на оба, и главное не уезжает под сгиб.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { card, chip, button, loadingState, errorState, sheet } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate } from "../router.js";
import { breadcrumb } from "./chrome.js";
import { renderBlocks, termCard } from "./content.js";
import { audioPlayer, initialState } from "./audio.js";

export function lessonView({ id }) {
  const node = h("div.page");
  let lessonId = id;
  let lesson = null;
  let error = null;
  let result = null;
  let completed = false;
  let player = null;

  node.dispose = () => player?.teardown();

  const load = async () => {
    player?.teardown();
    player = null;
    try {
      lesson = await api.lesson(lessonId);
      completed = lesson.completed;
      error = null;
    } catch (apiError) {
      error = apiError;
    }
    render();
  };

  const complete = async () => {
    result = await api.completeLesson(lessonId);
    completed = true;
    render();
  };

  // Переход, а не перезагрузка на месте: экран строит маршрутизатор, и «назад»
  // в браузере возвращает к предыдущему уроку.
  const advance = (nextId) => navigate(`/lesson/${nextId}`);

  const openTerm = (termId) => {
    const term = lesson.terms.find((candidate) => candidate.id === termId);
    if (!term) return;
    sheet(term.term, termCard(term, (sourceLessonId) => advance(sourceLessonId)));
  };

  /** Урок основного дерева приходит плоскими блоками, System Design — секциями.
   *  Заголовки секций не показываем: «Вопрос», «Цена» — структура для автора, а
   *  вывод и так стоит отдельным блоком. */
  const bodyBlocks = () =>
    lesson.sections?.length
      ? lesson.sections.filter((section) => section.kind !== "takeaway").flatMap((section) => section.blocks)
      : lesson.blocks;

  const render = () => {
    if (!lesson && error) {
      fill(node, breadcrumb(S.Lesson.backToBlock), errorState(S.Common.couldntLoad, error.userMessage, load));
      return;
    }
    if (!lesson) {
      fill(node, breadcrumb(S.Lesson.backToBlock), loadingState());
      return;
    }

    const audio = lesson.audio;
    if (audio && initialState(audio) !== "unavailable") {
      player = audioPlayer(audio, {
        lessonId: lesson.id,
        onReload: async () => {
          const fresh = await api.lesson(lessonId);
          lesson = fresh;
          return fresh.audio;
        },
      });
    }

    fill(
      node,
      breadcrumb(lesson.nodeTitle, `/block/${lesson.blockId}`),
      h(
        "div.lesson-layout",
        h(
          "div.stack.xl",
          h(
            "div.stack.s",
            h(
              "div.row.wrap",
              chip(lesson.nodeTitle, { symbol: "point.3.connected.trianglepath.dotted" }),
              chip(S.Common.minutes(lesson.estimatedMinutes), { symbol: "clock" })
            ),
            h("h1", lesson.title)
          ),
          h("div.lesson-body", renderBlocks(bodyBlocks(), { diagrams: lesson.diagrams, onTapTerm: openTerm })),
          checkQuestion(),
          lesson.exerciseId && exerciseLink(lesson.exerciseId),
          footer()
        ),
        h("aside.lesson-aside", player, takeaway(), terms())
      )
    );
  };

  const takeaway = () =>
    card(
      [
        h("div.row.caption", { style: { color: "var(--accent)", fontWeight: "600" } }, icon("key", { size: 13 }), S.Lesson.takeaway),
        h("p.text", { style: { marginTop: "6px" } }, lesson.keyTakeaway),
      ],
      { highlighted: true }
    );

  const terms = () => {
    if (!lesson.terms?.length) return null;
    return card([
      h("div.caption.muted", { style: { fontWeight: "600" } }, S.Lesson.terms),
      h(
        "div.row.wrap",
        { style: { marginTop: "8px" } },
        lesson.terms.map((term) =>
          h("button.term-chip", { type: "button", onclick: () => openTerm(term.id) }, term.term)
        )
      ),
    ]);
  };

  const checkQuestion = () => {
    if (!lesson.checkQuestion) return null;
    return card([
      h("div.row.caption.muted", { style: { fontWeight: "600" } }, icon("questionmark.circle", { size: 13 }), S.Lesson.checkYourself),
      h("p", { style: { marginTop: "6px" } }, lesson.checkQuestion),
      // Осознанно не оценивается: это приглашение подумать, а не тест. Применение
      // проверяет гейт (спека v0.2 §8).
      h("p.caption.tertiary", { style: { marginTop: "6px" } }, S.Lesson.checkNotScored),
    ]);
  };

  const exerciseLink = (exerciseId) =>
    h(
      "button.rowlink.card",
      { type: "button", onclick: () => navigate(`/exercise/${exerciseId}`) },
      icon("function", { size: 18 }),
      h("span.grow.title", S.Lesson.exercise),
      icon("chevron.right", { size: 14, className: "tertiary" })
    );

  const footer = () => {
    if (completed && lesson.nextLessonId) {
      return h(
        "div.stack.s",
        result?.xpAwarded > 0 && chip(S.Challenge.xpAwarded(result.xpAwarded), { symbol: "sparkles", tone: "accent" }),
        button(S.Lesson.nextLesson, () => advance(lesson.nextLessonId), { symbol: "arrow.right", wide: true })
      );
    }
    if (completed) {
      return h(
        "div.stack.s",
        result?.xpAwarded > 0 && chip(S.Challenge.xpAwarded(result.xpAwarded), { symbol: "sparkles", tone: "accent" }),
        button(S.Lesson.backToBlock, () => navigate(`/block/${lesson.blockId}`), { wide: true, variant: "secondary" })
      );
    }
    const control = button(S.Lesson.markRead, async () => {
      control.setLoading(true);
      try {
        await complete();
      } finally {
        control.setLoading(false);
      }
    }, { symbol: "checkmark", wide: true });
    return control;
  };

  render();
  load();
  return node;
}
