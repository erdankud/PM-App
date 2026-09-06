/** Каркас приложения: боковая навигация и переключатель языка.
 *
 *  Корневых разделов ровно три — Карта, Прогресс, Профиль (спека v0.1 §24, в силе).
 *  На десктопе они стоят сбоку, а не таб-баром внизу; правило про три раздела это
 *  не меняет.
 */
import { h } from "../dom.js";
import { icon } from "../icons.js";
import { S } from "../strings.js";
import { LANGUAGES, language, selectLanguage } from "../l10n.js";
import { navigate, currentPath, back } from "../router.js";
import { session } from "../session.js";

const TABS = [
  { path: "/map", symbol: "circle.hexagongrid", label: () => S.Tab.tree, match: /^\/(map|block|lesson|exercise|glossary)/ },
  { path: "/progress", symbol: "chart.line.uptrend.xyaxis", label: () => S.Tab.progress, match: /^\/(progress|history)/ },
  { path: "/profile", symbol: "person.crop.circle", label: () => S.Tab.profile, match: /^\/profile/ },
];

export function sidebar() {
  const path = currentPath();
  return h(
    "nav.sidebar",
    h("div.mark", icon("circle.hexagongrid", { size: 22 }), h("span", "PM Thinking Coach")),
    TABS.map((tab) =>
      h(
        `button.nav-item${tab.match.test(path) ? ".selected" : ""}`,
        { type: "button", onclick: () => navigate(tab.path) },
        icon(tab.symbol, { size: 18 }),
        h("span", tab.label())
      )
    ),
    h("div.spacer"),
    languagePicker(),
    h("div.footnote", session.me ? `${S.Progress.level(session.me.level)} · ${session.me.totalXp} XP` : "")
  );
}

export function languagePicker() {
  return h(
    "div.segmented",
    { role: "group", "aria-label": S.Profile.languageLabel },
    LANGUAGES.map((option) =>
      h(
        `button${option.code === language() ? ".selected" : ""}`,
        { type: "button", onclick: () => selectLanguage(option.code) },
        option.short
      )
    )
  );
}

/** Строка возврата. На вебе «назад» — это история браузера, а не стек экранов. */
export function breadcrumb(title, fallback = "/map") {
  return h(
    "button.breadcrumb",
    { type: "button", onclick: () => back(fallback) },
    icon("chevron.left", { size: 13 }),
    h("span", title)
  );
}
