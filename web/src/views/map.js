/** Карта — первый раздел: вся карта навыков, с одним открытым маршрутом.
 *
 *  Зеркало `Features/Tree/TreeView.swift`. Две карты одной грамматики стоят под
 *  переключателем, а не рядом: восемнадцать блоков System Design не помещаются
 *  седьмым сектором, и четвёртого корневого раздела здесь нет.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { card, chip, button, notice, sectionHeader, progressTrack, loadingState, errorState } from "../components.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate, currentQuery } from "../router.js";
import { ringMap, blockAccessibility } from "./ring.js";

const KIND_KEY = "pmcoach.treeKind";

function storedKind() {
  try {
    return localStorage.getItem(KIND_KEY) || "product";
  } catch {
    return "product";
  }
}

export function mapView() {
  const node = h("div.page.wide");
  let kind = currentQuery().get("tree") || storedKind();
  let tree = null;
  let trees = [];
  let error = null;

  const setKind = (next) => {
    if (next === kind) return;
    kind = next;
    try {
      localStorage.setItem(KIND_KEY, kind);
    } catch {
      /* приватный режим */
    }
    tree = null;
    render();
    load();
  };

  /** Блок, который стоит открыть следующим: самый дальний из ещё открытых.
   *  Это рекомендация — любой разблокированный блок остаётся доступен. */
  const suggested = () => {
    if (!tree) return null;
    const open = tree.blocks.filter(
      (block) => block.status !== "locked" && block.status !== "passed" && block.contentStatus === "published"
    );
    return (
      open.find((block) => block.status === "gate_ready") ||
      open.find((block) => block.status === "in_progress") ||
      open[0] ||
      null
    );
  };

  /** System Design открыт с первого дня, но начинать полезнее с блока о клиенте.
   *  Подсказка, а не замок (спека SD §2.3). */
  const shouldSuggestDiscovery = () => {
    const product = trees.find((summary) => summary.kind === "product");
    return kind === "system_design" && product && product.blocksPassed === 0;
  };

  const load = async () => {
    try {
      const [treeResponse, treesResponse] = await Promise.all([
        api.tree(kind),
        api.trees().catch(() => null),
      ]);
      tree = treeResponse;
      if (treesResponse) trees = treesResponse.trees;
      error = null;
    } catch (apiError) {
      if (!tree) error = apiError;
    }
    render();
  };

  const switcher = () =>
    h(
      "div.segmented",
      { role: "group" },
      h(`button${kind === "product" ? ".selected" : ""}`, { type: "button", onclick: () => setKind("product") }, S.Trees.product),
      h(`button${kind === "system_design" ? ".selected" : ""}`, { type: "button", onclick: () => setKind("system_design") }, S.Trees.systems)
    );

  const render = () => {
    const header = h("div.page-header", h("h1", S.Tab.tree), switcher());
    if (error && !tree) {
      fill(node, header, errorState(S.Tree.loadFailed, error.userMessage, load));
      return;
    }
    if (!tree) {
      fill(node, header, loadingState(S.Tree.loading));
      return;
    }

    const next = suggested();
    fill(
      node,
      header,
      shouldSuggestDiscovery() && notice(S.Trees.recommendation, { symbol: "info.circle" }),
      h(
        "div.map-layout",
        h(
          "div.stack.xl",
          ringMap(tree, { highlighted: next?.id, onSelect: openBlock }),
          legend(tree),
          h("p.caption.tertiary", tree.sourceAttribution)
        ),
        h("div.stack.xl", next && nextCard(next), domains(tree))
      )
    );
  };

  /** Кольца показывают форму пути; эта карточка говорит, что нажать сейчас —
   *  именно это и нужно новичку. */
  const nextCard = (block) =>
    card(
      [
        h(
          "div.row.wrap",
          chip(tree.tiers.find((tier) => tier.tier === block.tier)?.title || S.Tree.tierName(block.tier), {
            symbol: "circle.circle",
            tone: "accent",
          }),
          chip(block.id, { symbol: "point.3.connected.trianglepath.dotted" })
        ),
        h("p.small", { style: { color: "var(--accent)", fontWeight: "600", marginTop: "12px" } }, S.Tree.continueHere),
        h("h2", { style: { marginTop: "4px" } }, block.title),
        h("p.small.muted", { style: { marginTop: "8px" } }, S.Tree.lessonsProgress(block.lessonsCompleted, block.lessonsTotal)),
        h("div", { style: { marginTop: "8px" } }, progressTrack(lessonProgress(block))),
        h("div", { style: { marginTop: "16px" } }, button(S.Tree.openBlock, () => openBlock(block), { wide: true })),
      ],
      { highlighted: true }
    );

  const legend = (treeResponse) =>
    h(
      "div.stack.s",
      sectionHeader(S.Tree.ringsTitle, S.Tree.ringsSubtitle),
      // Номер круга не дублируется цифрой слева: он уже в самом названии.
      treeResponse.tiers.map((tier) =>
        h(
          "div.stack.s",
          h("div", { style: { fontWeight: "600", color: "var(--accent)" } }, tier.title),
          h("div.caption.muted", tier.subtitle)
        )
      )
    );

  const domains = (treeResponse) =>
    h(
      "div.stack",
      sectionHeader(S.Tree.domainsTitle, S.Tree.domainsSubtitle),
      treeResponse.domains.map((domain) => {
        const blocks = treeResponse.blocks
          .filter((block) => block.domainKey === domain.key)
          .sort((a, b) => a.tier - b.tier);
        return h(
          "div.domain-group",
          h("div", { style: { fontWeight: "600", marginBottom: "8px" } }, domain.title),
          h(
            "div.blocks",
            blocks.map((block) =>
              h(
                `button.block-pill${block.status === "passed" ? ".passed" : ""}${block.status === "locked" ? ".locked" : ""}`,
                {
                  type: "button",
                  onclick: () => openBlock(block),
                  "aria-label": blockAccessibility(block, treeResponse),
                },
                h("span.row", icon(S.Tree.statusSymbol(block.status), { size: 11 }), h("span.id", block.id)),
                h("span.title", block.title)
              )
            )
          )
        );
      })
    );

  const openBlock = (block) => navigate(`/block/${block.id}`);

  render();
  load();
  return node;
}

export function lessonProgress(block) {
  return block.lessonsTotal > 0 ? block.lessonsCompleted / block.lessonsTotal : 0;
}
