/** Блок: его узлы, их уроки и гейт, который блок закрывает.
 *
 *  Закрытый блок тоже открывается — он показывает, что внутри и что нужно сдать,
 *  чтобы до него дойти. Серая заглушка превратила бы карту в стену вместо маршрута.
 *
 *  Экран построен как ответ на три вопроса подряд: что этот блок даёт, из чего он
 *  состоит и чем заканчивается. Поэтому цели идут до уроков, а гейт — отдельной
 *  плашкой в конце, а не кнопкой среди прочих.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { chip, button, notice, loadingState, errorState } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate } from "../router.js";
import { breadcrumb } from "./chrome.js";
import { revealOnScroll } from "../motion.js";
import { lessonProgress } from "./map.js";

const STATUS_TONE = {
  locked: "tertiary",
  available: "muted",
  in_progress: "muted",
  gate_ready: "accent",
  passed: "positive",
};

export function blockView({ id }) {
  const node = h("div.page.full");
  let detail = null;
  let error = null;

  const load = async () => {
    try {
      detail = await api.block(id);
      error = null;
    } catch (apiError) {
      error = apiError;
    }
    render();
  };

  const startGate = async () => {
    if (!detail?.block.gateId) return;
    try {
      // Сервер перепроверяет доступность на каждый вызов, поэтому ошибка здесь —
      // это отказ сервера, а не рассинхрон кнопки.
      await api.startGate(detail.block.gateId);
      navigate(`/gate/${detail.block.gateId}`);
    } catch (apiError) {
      error = apiError;
      render();
    }
  };

  const render = () => {
    if (!detail && error) {
      fill(node, breadcrumb(S.Tab.tree), errorState(S.Common.couldntLoad, error.userMessage, load));
      return;
    }
    if (!detail) {
      fill(node, breadcrumb(S.Tab.tree), loadingState());
      return;
    }

    fill(
      node,
      breadcrumb(S.Tab.tree),
      hero(),
      detail.block.status === "locked"
        ? notice(S.Tree.lockedExplanation(detail.block.prerequisiteBlockIds), { symbol: "lock" })
        : detail.block.contentStatus !== "published"
          ? notice(S.Tree.comingSoon, { symbol: "hammer" })
          : null,
      goals(),
      lessons(),
      gateSection()
    );
    // Секция появляется каскадом в том порядке, в каком её читают.
    revealOnScroll(node, { selector: ":scope > header, :scope > section" });
  };

  /** Сколько минут займёт блок целиком: сумма самих уроков, а не оценка сверху. */
  const totals = () => {
    const lessonList = detail.nodes.flatMap((entry) => entry.lessons);
    return {
      nodes: detail.nodes.length,
      lessons: lessonList.length,
      minutes: lessonList.reduce((sum, lesson) => sum + (lesson.estimatedMinutes || 0), 0),
    };
  };

  const hero = () => {
    const block = detail.block;
    const { nodes, lessons: lessonCount, minutes } = totals();
    return h(
      "header.block-hero",
      h(
        "div.row.wrap",
        chip(detail.domainTitle, { symbol: "square.grid.3x3" }),
        chip(detail.tierTitle, { symbol: "circle.circle", tone: "accent" }),
        chip(block.id, { symbol: "point.3.connected.trianglepath.dotted" })
      ),
      h("h1", block.title),
      h(
        "p.block-hero-status",
        { class: STATUS_TONE[block.status] || "muted" },
        icon(block.status === "passed" ? "checkmark.circle.fill" : "circle.circle", { size: 15 }),
        h("span", S.Tree.statusLabel(block.status))
      ),
      lessonCount > 0 &&
        h(
          "div.block-hero-meter",
          h("div.track", h("div", { style: { width: `${lessonProgress(block) * 100}%` } })),
          h(
            "div.block-hero-facts",
            h("span", S.Tree.lessonsProgress(block.lessonsCompleted, block.lessonsTotal)),
            h("span.tertiary", S.Tree.blockSummary(nodes, lessonCount, minutes))
          )
        )
    );
  };

  /** Ключевые вопросы узлов — это и есть цели блока: каждый вопрос равен одному
   *  навыку, и гейт в конце просит применить именно их. Придумывать поверх них
   *  отдельный список «целей» значило бы писать второй, менее точный. */
  const goals = () =>
    h(
      "section.block-section.split",
      h("div.split-head", h("h2", S.Tree.blockGoalTitle), h("p.section-lede", S.Tree.blockGoalSubtitle)),
      h(
        "div.goal-grid",
        detail.nodes.map((entry, index) =>
          h(
            "article.goal-card",
            h("span.goal-index", String(index + 1).padStart(2, "0")),
            h("h3", entry.node.title),
            h("p", entry.node.keyQuestion),
            entry.node.models.length > 0 &&
              h(
                "div.row.wrap.goal-models",
                // Названия моделей — термины и остаются в исходной форме.
                entry.node.models.map((model) => chip(model))
              )
          )
        )
      )
    );

  const lessons = () => {
    const flat = detail.nodes.flatMap((entry) =>
      entry.lessons.map((lesson) => ({ lesson, nodeTitle: entry.node.title }))
    );
    if (!flat.length) {
      return h(
        "section.block-section",
        h("h2", S.Tree.lessonsTitle),
        notice(S.Tree.lessonsComingSoon, { symbol: "hourglass" })
      );
    }
    return h(
      "section.block-section",
      h("h2", S.Tree.lessonsTitle),
      h("div.lesson-grid", flat.map((item, index) => lessonCard(item, index + 1)))
    );
  };

  const lessonCard = ({ lesson, nodeTitle }, number) => {
    const isOpen = detail.block.status !== "locked";
    return h(
      `button.lesson-card${lesson.completed ? ".done" : ""}`,
      {
        type: "button",
        disabled: !isOpen,
        onclick: () => navigate(`/lesson/${lesson.id}`),
        "aria-label": `${S.Tree.lessonNumber(number)}. ${lesson.title}`,
      },
      h(
        "div.lesson-card-top",
        h("span.lesson-card-number", String(number).padStart(2, "0")),
        lesson.completed
          ? icon("checkmark.circle.fill", { size: 18, className: "positive" })
          : isOpen
            ? icon("chevron.right", { size: 14, className: "tertiary" })
            : icon("lock", { size: 14, className: "tertiary" })
      ),
      h("span.lesson-card-eyebrow", nodeTitle),
      h("span.lesson-card-title", lesson.title),
      h("span.lesson-card-meta", icon("clock", { size: 13 }), h("span", S.Common.minutes(lesson.estimatedMinutes)))
    );
  };

  const gateSection = () => {
    const available = detail.gateAvailable;
    const remaining = Math.max(0, detail.block.lessonsTotal - detail.block.lessonsCompleted);
    return h(
      `section.gate-panel${available ? ".ready" : ""}`,
      h(
        "div.gate-panel-body",
        h("span.gate-panel-eyebrow", icon("flag.checkered", { size: 14 }), h("span", S.Tree.gateTitle)),
        // Заголовок не повторяет кнопку: он говорит, что это за проверка,
        // а действие называет сама кнопка.
        h("h2", S.Tree.gateHeadline),
        h("p.gate-panel-pitch", S.Tree.gatePitch),
        h(
          "div.gate-panel-facts",
          h("span", S.Tree.gateSubtitle(detail.passThreshold)),
          h("span", S.Tree.gateNoPenalty)
        )
      ),
      h(
        "div.gate-panel-action",
        error && notice(error.userMessage, { symbol: "exclamationmark.circle", tone: "negative" }),
        available
          ? button(
              detail.block.attemptCount > 0 ? S.Tree.retakeGate : S.Tree.takeGate,
              startGate,
              { symbol: "flag.checkered", wide: true, arrow: true }
            )
          : h(
              "div.stack.s",
              button(S.Tree.takeGate, () => {}, { disabled: true, wide: true }),
              notice(S.Tree.gateBlockedReason(detail.gateBlockedReason, remaining), { symbol: "info.circle" })
            )
      )
    );
  };

  render();
  load();
  return node;
}
