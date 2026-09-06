/** Блок: его узлы, их уроки и гейт, который блок закрывает.
 *
 *  Закрытый блок тоже открывается — он показывает, что внутри и что нужно сдать,
 *  чтобы до него дойти. Серая заглушка превратила бы карту в стену вместо маршрута.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { card, chip, button, notice, sectionHeader, progressTrack, loadingState, errorState } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate } from "../router.js";
import { breadcrumb } from "./chrome.js";
import { lessonProgress } from "./map.js";

const STATUS_TONE = {
  locked: "tertiary",
  available: "muted",
  in_progress: "muted",
  gate_ready: "accent",
  passed: "positive",
};

export function blockView({ id }) {
  const node = h("div.page");
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
      header(),
      h("div.stack.l", detail.nodes.map(nodeCard)),
      gateSection()
    );
  };

  const header = () => {
    const block = detail.block;
    const isOpen = block.status !== "locked";
    return card(
      [
        h(
          "div.row.wrap",
          chip(detail.domainTitle, { symbol: "square.grid.3x3" }),
          chip(detail.tierTitle, { symbol: "circle.circle", tone: "accent" })
        ),
        h("h1", { style: { marginTop: "12px" } }, block.title),
        h(
          "p.small",
          {
            style: { marginTop: "6px", fontWeight: "600" },
            class: STATUS_TONE[block.status] || "muted",
          },
          S.Tree.statusLabel(block.status)
        ),
        block.status === "locked"
          ? notice(S.Tree.lockedExplanation(block.prerequisiteBlockIds), { symbol: "lock" })
          : block.contentStatus !== "published"
            ? notice(S.Tree.comingSoon, { symbol: "hammer" })
            : h(
                "div.stack.s",
                { style: { marginTop: "12px" } },
                progressTrack(lessonProgress(block)),
                h("p.caption.tertiary", S.Tree.lessonsProgress(block.lessonsCompleted, block.lessonsTotal))
              ),
      ],
      { highlighted: isOpen }
    );
  };

  const nodeCard = (node_) =>
    card([
      h("h3", node_.node.title),
      h("p.small.muted", { style: { marginTop: "4px" } }, node_.node.keyQuestion),
      node_.node.models.length &&
        h(
          "div.row.wrap",
          { style: { marginTop: "12px" } },
          // Названия моделей — термины и остаются в исходной форме.
          node_.node.models.map((model) => chip(model))
        ),
      node_.lessons.length
        ? h(
            "div.list-card",
            { style: { marginTop: "12px" } },
            node_.lessons.map((lesson) => lessonRow(lesson))
          )
        : h("div", { style: { marginTop: "12px" } }, notice(S.Tree.lessonsComingSoon, { symbol: "hourglass" })),
    ]);

  const lessonRow = (lesson) => {
    const isOpen = detail.block.status !== "locked";
    return h(
      "button.rowlink",
      {
        type: "button",
        disabled: !isOpen,
        onclick: () => navigate(`/lesson/${lesson.id}`),
      },
      icon(lesson.completed ? "checkmark.circle.fill" : "book", {
        size: 18,
        className: lesson.completed ? "positive" : "",
      }),
      h(
        "span.grow",
        h("span.title", { style: { display: "block" } }, lesson.title),
        h("span.caption.tertiary", S.Common.minutes(lesson.estimatedMinutes))
      ),
      isOpen && icon("chevron.right", { size: 14, className: "tertiary" })
    );
  };

  const gateSection = () =>
    h(
      "div.stack",
      sectionHeader(S.Tree.gateTitle, S.Tree.gateSubtitle(detail.passThreshold)),
      error && notice(error.userMessage, { symbol: "exclamationmark.circle", tone: "negative" }),
      detail.gateAvailable
        ? button(
            detail.block.attemptCount > 0 ? S.Tree.retakeGate : S.Tree.takeGate,
            startGate,
            { symbol: "flag.checkered", wide: true }
          )
        : h(
            "div.stack.s",
            button(S.Tree.takeGate, () => {}, { disabled: true, wide: true }),
            notice(
              S.Tree.gateBlockedReason(
                detail.gateBlockedReason,
                Math.max(0, detail.block.lessonsTotal - detail.block.lessonsCompleted)
              ),
              { symbol: "info.circle" }
            )
          )
    );

  render();
  load();
  return node;
}
