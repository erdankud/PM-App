/** Каркас приложения: боковая навигация и переключатель языка.
 *
 *  Корневых разделов пять — Уроки, Карта, Практика, Прогресс, Профиль. Правило
 *  «мало корней» осталось: чата нет, платного экрана нет, лент нет. Практика
 *  выделена в корень потому, что это другая работа: курс объясняет и проверяет
 *  усвоенное, а здесь человек репетирует собеседование, и внутрь урока или карты
 *  такое не вкладывается — туда за ним никто не пойдёт.
 *  На десктопе разделы стоят сбоку, а не таб-баром внизу; правила это не меняет.
 */
import { h } from "../dom.js";
import { icon } from "../icons.js";
import { S } from "../strings.js";
import { LANGUAGES, language, selectLanguage } from "../l10n.js";
import { navigate, currentPath, up } from "../router.js";
import { session } from "../session.js";

/** Меню свёрнуто по умолчанию: разделов немного, их значки узнаются с первого
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
  // Практика — не курс: значок мишени, а не книги, потому что здесь целятся в
  // собеседование, а не читают. Стоит сразу за уроками: репетируют то, что читают,
  // а карта профессии — вид сверху, к которому возвращаются реже.
  { path: "/practice", symbol: "scope", label: () => S.Tab.practice, match: /^\/practice/ },
  // Значок карты не должен повторять знак приложения — иначе два пункта из пяти
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
    // приём из исходного промпта. Знака приложения здесь больше нет: в свёрнутой
    // колонке одиночный значок стоял над кнопками и читался как ещё одна кнопка,
    // хотя нажать на него было нельзя. В свёрнутом виде строка убирается целиком.
    h(
      "div.mark",
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

/** Стрелка «вверх»: экран, которому этот принадлежит, а не предыдущий по времени.
 *
 *  `parent` — маршрут, а не запасной вариант. Раньше он и был запасным: клик
 *  разматывал историю браузера и попадал сюда, только если истории нет. Из-за
 *  этого «Следующий урок» десять раз подряд превращал стрелку в перемотку той же
 *  ленты назад, вместо выхода к списку уроков.
 */
export function breadcrumb(title, parent = "/learn") {
  return h(
    "button.breadcrumb",
    { type: "button", onclick: () => up(parent) },
    icon("chevron.left", { size: 13 }),
    h("span", title)
  );
}
