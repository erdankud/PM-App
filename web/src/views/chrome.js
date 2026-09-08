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

/** Меню свёрнуто по умолчанию: разделов ровно три, их значки узнаются с первого
 *  дня, а место на экране нужнее содержанию — карте, уроку, разбору гейта.
 *  Выбор запоминается, поэтому развернувший его один раз больше об этом не думает. */
const COLLAPSED_KEY = "pmcoach.sidebarCollapsed";

function isCollapsed() {
  try {
    const stored = localStorage.getItem(COLLAPSED_KEY);
    return stored === null ? true : stored === "1";
  } catch {
    return true;
  }
}

function setCollapsed(value) {
  try {
    localStorage.setItem(COLLAPSED_KEY, value ? "1" : "0");
  } catch {
    /* приватный режим */
  }
}

const TABS = [
  { path: "/learn", symbol: "book", label: () => S.Tab.learn, match: /^\/(learn|block|lesson|exercise|glossary)/ },
  // Значок карты не должен повторять знак приложения — иначе два пункта из четырёх
  // выглядят одним.
  { path: "/map", symbol: "compass", label: () => S.Tab.tree, match: /^\/map/ },
  { path: "/progress", symbol: "chart.line.uptrend.xyaxis", label: () => S.Tab.progress, match: /^\/(progress|history)/ },
  { path: "/profile", symbol: "person.crop.circle", label: () => S.Tab.profile, match: /^\/profile/ },
];

export function sidebar() {
  const path = currentPath();
  const collapsed = isCollapsed();
  const node = h(
    `nav.sidebar.glass${collapsed ? ".collapsed" : ""}`,
    // Логотип в две строки прописными с плотным трекингом и подписью под ним —
    // приём из исходного промпта. В свёрнутом виде остаётся только знак.
    h(
      "div.mark",
      icon("circle.hexagongrid", { size: 22 }),
      h(
        "span.mark-words",
        h("span.mark-line", "PM Thinking"),
        h("span.mark-line", "Coach"),
        h("span.mark-tagline", S.Common.tagline)
      )
    ),
    h(
      "button.sidebar-toggle",
      {
        type: "button",
        // Значок и подпись говорят одно и то же: кнопка без текста должна
        // объясняться скринридеру.
        title: collapsed ? S.Common.expandMenu : S.Common.collapseMenu,
        "aria-label": collapsed ? S.Common.expandMenu : S.Common.collapseMenu,
        "aria-expanded": collapsed ? "false" : "true",
        onclick: () => {
          setCollapsed(!collapsed);
          node.replaceWith(sidebar());
        },
      },
      icon(collapsed ? "chevron.right" : "chevron.left", { size: 14 })
    ),
    TABS.map((tab) =>
      h(
        `button.nav-item${tab.match.test(path) ? ".selected" : ""}`,
        {
          type: "button",
          onclick: () => navigate(tab.path),
          title: collapsed ? tab.label() : null,
          "aria-label": tab.label(),
        },
        icon(tab.symbol, { size: 18 }),
        h("span", tab.label())
      )
    ),
    h("div.spacer"),
    h("div.footnote", session.me ? `${S.Progress.level(session.me.level)} · ${session.me.totalXp} XP` : "")
  );
  return node;
}

export function languagePicker() {
  return h(
    "div.segmented.glass",
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
