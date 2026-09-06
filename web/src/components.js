/** Общие элементы. Зеркало `Core/DesignSystem/Components.swift`. */
import { h, fill } from "./dom.js";
import { icon } from "./icons.js";
import { S } from "./strings.js";

export function card(children, { highlighted = false, tight = false, className = "" } = {}) {
  const node = h(`div.card${highlighted ? ".highlighted" : ""}${tight ? ".tight" : ""}`);
  if (className) node.classList.add(...className.split(" "));
  node.append(...[children].flat(Infinity).filter(Boolean));
  return node;
}

export function chip(text, { symbol = null, tone = "" } = {}) {
  return h(`span.chip${tone ? "." + tone : ""}`, symbol && icon(symbol, { size: 12 }), text);
}

/** Цвет никогда не единственный носитель смысла: рядом всегда слово или значок. */
export function notice(text, { symbol = "info.circle", tone = "" } = {}) {
  return h(`div.notice${tone ? "." + tone : ""}`, icon(symbol, { size: 15 }), h("span", text));
}

export function sectionHeader(title, subtitle) {
  return h(
    "div.section-header",
    h("div.title", title),
    subtitle && h("div.subtitle", subtitle)
  );
}

export function progressTrack(progress, { thin = false } = {}) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(progress) ? progress : 0));
  return h(
    `div.track${thin ? ".thin" : ""}`,
    { role: "progressbar", "aria-valuenow": Math.round(clamped * 100), "aria-valuemin": 0, "aria-valuemax": 100 },
    h("div", { style: { width: `${clamped * 100}%` } })
  );
}

export function button(title, onClick, { symbol = null, variant = "", disabled = false, wide = false } = {}) {
  const node = h(
    `button.btn${variant ? "." + variant : ""}${wide ? ".wide" : ""}`,
    { type: "button", onclick: onClick, disabled },
    symbol && icon(symbol, { size: 16 }),
    h("span", title)
  );
  /** Кнопка сама показывает работу: иначе двойной клик уходит вторым запросом. */
  node.setLoading = (loading) => {
    node.disabled = loading || disabled;
    fill(node, loading ? h("span.spinner") : symbol && icon(symbol, { size: 16 }), h("span", title));
  };
  return node;
}

export function loadingState(message = S.Common.loading) {
  return h("div.state", h("div.spinner"), h("div", message));
}

export function errorState(title, message, onRetry) {
  return h(
    "div.state",
    icon("exclamationmark.triangle", { size: 28 }),
    h("h3", title),
    h("p.small", message),
    onRetry && button(S.Common.tryAgain, onRetry, { variant: "secondary" })
  );
}

export function scoreHeadline(score, band) {
  return h(
    "div.score",
    h("span.value", String(score)),
    h("span.max", "/100"),
    h("span.band", S.Labels.band(band))
  );
}

export function skillRow(skill) {
  return h(
    "div.stack.s",
    h(
      "div.row",
      h("span.grow", S.Labels.skill(skill.key, skill.label)),
      h(
        "span.row.caption.muted",
        icon(trendSymbol(skill.trend), { size: 12 }),
        S.Labels.trendDescription(skill.trend)
      ),
      h("span.mono", { style: { fontWeight: "600" } }, String(skill.score))
    ),
    progressTrack(skill.score / 100, { thin: true })
  );
}

function trendSymbol(trend) {
  if (trend === "up") return "arrow.up.right";
  if (trend === "down") return "arrow.down.right";
  return "minus";
}

/** Подтверждение действия. Нативный `<dialog>`: фокус и Esc уже работают. */
export function confirmDialog({ title, message, confirmTitle, destructive = false }) {
  return new Promise((resolve) => {
    const dialog = h("dialog");
    const done = (value) => {
      dialog.close();
      dialog.remove();
      resolve(value);
    };
    dialog.append(
      h(
        "div.content",
        h("h3", title),
        message && h("p.small.muted", message),
        h(
          "div.actions",
          button(S.Common.cancel, () => done(false), { variant: "quiet" }),
          button(confirmTitle, () => done(true), { variant: destructive ? "destructive" : "" })
        )
      )
    );
    dialog.addEventListener("cancel", () => done(false));
    document.body.append(dialog);
    dialog.showModal();
  });
}

/** Лист с произвольным содержимым (карточка термина, приватность). */
export function sheet(title, content) {
  const dialog = h("dialog");
  dialog.append(
    h(
      "div.content",
      h("div.row", h("h3.grow", title), button(S.Common.close, () => close(), { variant: "quiet" })),
      content
    )
  );
  const close = () => {
    dialog.close();
    dialog.remove();
  };
  dialog.addEventListener("cancel", close);
  document.body.append(dialog);
  dialog.showModal();
  return dialog;
}
