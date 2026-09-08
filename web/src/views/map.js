/** Карта — первый раздел: весь атлас навыков, одна карточка на навык.
 *
 *  Раскладка повторяет исходную схему («Skill Map of Product Management»): шесть
 *  секторов, три кольца, карточка = название + ключевой вопрос + модели. Карта
 *  интерактивная — её двигают и масштабируют, потому что целиком на экран она
 *  читаемой не помещается, а печатный лист можно поднести к глазам.
 *
 *  Карточка ведёт в урок. Гейт с карты убран совсем: он живёт на странице блока,
 *  и смешивать «прочитать» со «сдать» на одной поверхности незачем.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { chip, button, sectionHeader, progressTrack, loadingState, errorState } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate, currentQuery } from "../router.js";
import { atlas, panZoom, zoomControls } from "./atlas.js";
import { revealOnScroll } from "../motion.js";
import { treeKind, setTreeKind } from "../tree-kind.js";

export function mapView() {
  const node = h("div.page");
  let kind = currentQuery().get("tree") || treeKind();
  let selectedId = null;
  let map = null;
  let error = null;

  const setKind = (next) => {
    if (next === kind) return;
    kind = next;
    setTreeKind(kind);
    map = null;
    selectedId = null;
    render();
    load();
  };

  const load = async () => {
    try {
      map = await api.treeMap(kind);
      error = null;
    } catch (apiError) {
      if (!map) error = apiError;
    }
    render();
  };

  const switcher = () =>
    h(
      "div.segmented.glass",
      { role: "group" },
      h(`button${kind === "product" ? ".selected" : ""}`, { type: "button", onclick: () => setKind("product") }, S.Trees.product),
      h(`button${kind === "system_design" ? ".selected" : ""}`, { type: "button", onclick: () => setKind("system_design") }, S.Trees.systems)
    );

  const openLesson = (mapNode) => {
    const next = mapNode.lessons.find((lesson) => !lesson.completed) || mapNode.lessons[0];
    if (next) navigate(`/lesson/${next.id}`);
  };

  const select = (mapNode) => {
    selectedId = mapNode.id;
    renderPanel();
  };

  const render = () => {
    const header = h("div.page-header", h("h1", S.Tab.tree), switcher());
    if (error && !map) {
      fill(node, header, errorState(S.Tree.loadFailed, error.userMessage, load));
      return;
    }
    if (!map) {
      fill(node, header, loadingState(S.Tree.loading));
      return;
    }

    const { root, scene } = atlas(map, { selected: selectedId, onSelect: select, onOpen: openLesson });
    const controls = panZoom(root, scene);

    fill(
      node,
      header,
      h(
        "div.map-board",
        h(
          "div.map-canvas",
          root,
          zoomControls(controls),
          h("p.map-hint.glass", icon("hand.tap", { size: 12 }), h("span", S.Tree.mapHint))
        ),
        h("aside.map-panel")
      ),
      h("div.map-footer", tiers(), h("p.caption.tertiary", map.sourceAttribution))
    );
    revealOnScroll(node, { selector: ":scope > .map-board, :scope > .map-footer", stagger: 140 });
    renderPanel();
  };

  /** Панель перерисовывается отдельно от карты: пересборка атласа сбросила бы
   *  и масштаб, и положение, к которому человек только что доехал. */
  const renderPanel = () => {
    const panel = node.querySelector(".map-panel");
    if (!panel || !map) return;
    const chosen = map.nodes.find((item) => item.id === selectedId);
    const cards = node.querySelectorAll(".atlas-card");
    cards.forEach((element) => element.classList.remove("selected"));
    if (chosen) cards[map.nodes.indexOf(chosen)]?.classList.add("selected");
    fill(panel, chosen ? detail(chosen) : emptyPanel());
  };

  const emptyPanel = () =>
    h(
      "div.detail-card.detail-empty",
      icon("hand.tap", { size: 22, className: "tertiary" }),
      h("p.small.muted", S.Tree.mapHint)
    );

  const detail = (mapNode) => {
    const done = mapNode.lessons.filter((lesson) => lesson.completed).length;
    const minutes = mapNode.lessons.reduce((sum, lesson) => sum + lesson.estimatedMinutes, 0);
    // Тот же урок, который откроет кнопка: первый непрочитанный, иначе первый.
    const lead = mapNode.lessons.find((lesson) => !lesson.completed) || mapNode.lessons[0];
    return h(
      "div.detail-card",
      h(
        "div.row.wrap",
        chip(mapNode.blockId, { symbol: "point.3.connected.trianglepath.dotted" }),
        chip(
          map.tiers.find((tier) => tier.tier === mapNode.tier)?.title || S.Tree.tierName(mapNode.tier),
          { symbol: "circle.circle", tone: "accent" }
        )
      ),
      // Навык — надзаголовок, урок — заголовок: карточка на карте это вход
      // в урок, и панель должна открывать именно его.
      h("p.detail-skill", mapNode.title),
      h("h2.detail-title", lead ? lead.title : mapNode.title),
      h(
        "p.detail-meta-line",
        icon(lead && lead.completed ? "checkmark.circle.fill" : "clock", { size: 13 }),
        h("span", lead ? S.Common.minutes(lead.estimatedMinutes) : ""),
        h("span.detail-dot", "·"),
        h("span", mapNode.keyQuestion)
      ),
      mapNode.models.length > 0 &&
        h("div.row.wrap.detail-models", mapNode.models.map((model) => chip(model))),
      button(S.Tree.openLesson, () => openLesson(mapNode), { wide: true, arrow: true }),
      // Остальные уроки навыка — под кнопкой, если их больше одного.
      mapNode.lessons.length > 1 &&
        h(
          "div.detail-lessons",
          h(
            "p.caption.tertiary",
            `${S.Tree.lessonsInNode(mapNode.lessons.length)} · ${S.Common.minutes(minutes)}`
          ),
          progressTrack(mapNode.lessons.length ? done / mapNode.lessons.length : 0),
          mapNode.lessons.map((lesson) =>
            h(
              `button.detail-lesson${lesson.completed ? ".done" : ""}`,
              { type: "button", onclick: () => navigate(`/lesson/${lesson.id}`) },
              icon(lesson.completed ? "checkmark.circle.fill" : "book", { size: 15 }),
              h("span.grow", lesson.title),
              h("span.caption.tertiary", S.Common.minutes(lesson.estimatedMinutes))
            )
          )
        )
    );
  };

  const tiers = () =>
    h(
      "div.tier-key",
      sectionHeader(S.Tree.tiersTitle, S.Tree.tiersSubtitle),
      map.tiers.map((tier) =>
        h(
          "div.stack.s",
          h("div.tier-name", tier.title),
          h("div.caption.muted", tier.subtitle)
        )
      )
    );

  render();
  load();
  return node;
}

/** Доля пройденных уроков блока. Используется страницей блока. */
export function lessonProgress(block) {
  return block.lessonsTotal > 0 ? block.lessonsCompleted / block.lessonsTotal : 0;
}
