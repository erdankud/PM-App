/** Прогресс: пройденные блоки и прочитанные уроки.
 *
 *  Календаря в этом продукте больше нет (спека v0.2 §1, §10) — счёт идёт по блокам,
 *  а не по дням.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { card, button, sectionHeader, progressTrack, skillRow, loadingState, errorState } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate } from "../router.js";

export function progressView() {
  const node = h("div.page");
  let progress = null;
  let error = null;

  const load = async () => {
    try {
      progress = await api.progress();
      error = null;
    } catch (apiError) {
      error = apiError;
    }
    render();
  };

  const counter = (title, value, total, symbol) =>
    h(
      "div.stack.s",
      h(
        "div.row",
        icon(symbol, { size: 14 }),
        h("span.grow", { style: { fontWeight: "500" } }, title),
        h("span.mono.muted", `${value} / ${total}`)
      ),
      progressTrack(total > 0 ? value / total : 0)
    );

  const summary = () => {
    const next = progress.xpForNextLevel;
    return card(
      [
        h("h1", S.Progress.level(progress.level)),
        h("p.muted", { style: { marginTop: "2px" } }, S.Progress.totalXp(progress.totalXp)),
        next && next > progress.totalXp
          ? h(
              "div.stack.s",
              { style: { marginTop: "16px" } },
              progressTrack(progress.totalXp / Math.max(next, 1)),
              h("p.caption.tertiary", S.Progress.xpToNextLevel(next - progress.totalXp, progress.level + 1))
            )
          : null,
      ],
      { highlighted: true }
    );
  };

  const render = () => {
    if (!progress && error) {
      fill(node, h("h1", S.Progress.title), errorState(S.Progress.loadFailed, error.userMessage, load));
      return;
    }
    if (!progress) {
      fill(node, h("h1", S.Progress.title), loadingState());
      return;
    }

    fill(
      node,
      h("h1", S.Progress.title),
      summary(),
      card([
        counter(S.Progress.blocksPassed, progress.blocksPassed, progress.blocksTotal, "flag.checkered"),
        h("div", { style: { height: "16px" } }),
        counter(S.Progress.lessonsRead, progress.lessonsCompleted, progress.lessonsTotal, "book"),
      ]),
      h(
        "div.stack",
        sectionHeader(S.Progress.skillsTitle, S.Progress.skillsSubtitle),
        card(h("div.stack.l", progress.skills.map(skillRow)))
      ),
      h(
        "button.rowlink.card",
        { type: "button", onclick: () => navigate("/history") },
        icon("list.bullet.rectangle", { size: 18 }),
        h("span.grow.title", S.Progress.gateHistory(progress.gatesAttempted)),
        icon("chevron.right", { size: 14, className: "tertiary" })
      ),
      h("p.small.tertiary", progress.footnote)
    );
  };

  render();
  load();
  return node;
}
