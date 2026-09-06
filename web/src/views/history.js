/** История попыток и разбор одной попытки, доступный только на чтение.
 *
 *  Ничего на этих экранах не может изменить отправленную попытку.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { card, chip, button, sectionHeader, scoreHeadline, loadingState, errorState } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate } from "../router.js";
import { breadcrumb } from "./chrome.js";

const PAGE = 20;

export function historyView() {
  const node = h("div.page");
  let items = [];
  let nextOffset = 0;
  let canLoadMore = true;
  let error = null;
  let loading = false;

  const loadPage = async (reset = false) => {
    if (loading) return;
    loading = true;
    try {
      const response = await api.history(PAGE, reset ? 0 : nextOffset);
      items = reset ? response.items : items.concat(response.items);
      nextOffset = response.nextOffset ?? 0;
      canLoadMore = response.nextOffset !== null && response.nextOffset !== undefined;
      error = null;
    } catch (apiError) {
      if (!items.length) error = apiError;
    } finally {
      loading = false;
      render();
    }
  };

  const statusChip = (item) => {
    if (item.feedbackStatus === "complete") {
      return chip(item.passed ? S.History.passed : S.History.notPassed, {
        symbol: item.passed ? "checkmark" : "arrow.counterclockwise",
        tone: item.passed ? "positive" : "caution",
      });
    }
    if (item.feedbackStatus === "pending") {
      return chip(S.History.feedbackPending, { symbol: "hourglass" });
    }
    return chip(S.History.coachingFailed, { symbol: "exclamationmark", tone: "caution" });
  };

  const row = (item) =>
    h(
      "button.rowlink.card.tight",
      { type: "button", onclick: () => navigate(`/history/${item.attemptId}`) },
      h(
        "span.grow.stack.s",
        h("span.title", { style: { fontWeight: "600" } }, item.title),
        h("span.caption.tertiary", S.History.blockAndAttempt(item.blockTitle, item.attemptIndex)),
        statusChip(item)
      ),
      item.score !== null && item.score !== undefined
        ? h(
            "span",
            { style: { textAlign: "center" } },
            h("span.mono", { style: { display: "block", fontSize: "20px", fontWeight: "700" } }, String(item.score)),
            h("span.caption.tertiary", "/100")
          )
        : null,
      icon("chevron.right", { size: 14, className: "tertiary" })
    );

  const render = () => {
    const head = [breadcrumb(S.Progress.title, "/progress"), h("h1", S.History.title)];
    if (!items.length && error) {
      fill(node, head, errorState(S.History.loadFailed, error.userMessage, () => loadPage(true)));
      return;
    }
    if (!items.length && loading) {
      fill(node, head, loadingState());
      return;
    }
    if (!items.length) {
      fill(
        node,
        head,
        h("div.state", icon("flag.checkered", { size: 28 }), h("h3", S.History.emptyTitle), h("p.small", S.History.emptyBody))
      );
      return;
    }
    fill(
      node,
      head,
      h("div.stack.s", items.map(row)),
      canLoadMore && button(S.History.loadMore, () => loadPage(), { variant: "secondary" })
    );
  };

  render();
  loadPage(true);
  return node;
}

/** Результат попытки: последствие, счёт и разбор — только на чтение. */
export function resultView({ attemptId }) {
  const node = h("div.page");
  let response = null;
  let error = null;

  const load = async () => {
    try {
      response = await api.feedback(attemptId);
      error = null;
    } catch (apiError) {
      error = apiError;
    }
    render();
  };

  const points = (title, list) => {
    if (!list?.length) return null;
    return h(
      "div.stack",
      sectionHeader(title),
      list.map((point) =>
        card([h("h3", point.title), h("p.small.muted", { style: { marginTop: "4px" } }, point.detail)])
      )
    );
  };

  const render = () => {
    const head = [breadcrumb(S.History.title, "/history"), h("h1", S.History.resultTitle)];
    if (!response && error) {
      fill(node, head, errorState(S.History.resultLoadFailed, error.userMessage, load));
      return;
    }
    if (!response) {
      fill(node, head, loadingState());
      return;
    }

    fill(
      node,
      head,
      h("h2", response.scenarioTitle),
      card(
        [
          h(
            "div.row.caption",
            { style: { color: "var(--accent)", fontWeight: "600" } },
            icon("arrow.turn.down.right", { size: 13 }),
            S.Challenge.whatHappenedNext
          ),
          h("h3", { style: { marginTop: "8px" } }, response.consequence.optionLabel),
          h("p.text", { style: { marginTop: "6px" } }, response.consequence.text),
        ],
        { highlighted: true }
      ),
      response.feedback
        ? [
            card(scoreHeadline(response.feedback.score, response.feedback.band)),
            points(S.Challenge.strengthsTitle, response.feedback.strengths),
            points(S.Challenge.improvementsTitle, response.feedback.improvements),
            h(
              "div.stack",
              sectionHeader(S.Challenge.sharperApproach),
              card(h("p.text", response.feedback.sharperApproach))
            ),
          ]
        : card([
            h(
              "div.row",
              icon("hourglass", { size: 16 }),
              h("h3", response.status === "failed" ? S.Challenge.coachingDidntFinish : S.Challenge.coachingStillPending)
            ),
            h("p.small.muted", { style: { marginTop: "8px" } }, S.History.pendingXpNote),
            response.retryAvailable
              ? h(
                  "div",
                  { style: { marginTop: "12px" } },
                  button(S.Challenge.retryCoaching, async () => {
                    response = await api.retryFeedback(attemptId);
                    render();
                  }, { variant: "secondary", symbol: "arrow.clockwise" })
                )
              : null,
          ])
    );
  };

  render();
  load();
  return node;
}
