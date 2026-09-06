/** Отрисовка авторского контента: блоки урока, схемы, термины в тексте.
 *
 *  Зеркало `LessonBlockRenderer`, `DiagramCanvas` и `TermText`. Неизвестный тип
 *  блока пропускается, а не показывается сырым: добавленный на сервере тип не
 *  должен ломать более старый клиент.
 */
import { h, markdown } from "../dom.js";
import { icon } from "../icons.js";
import { card, notice } from "../components.js";
import { S } from "../strings.js";

export function renderBlocks(blocks, { diagrams = [], onTapTerm = null } = {}) {
  return (blocks || []).map((block) => renderBlock(block, { diagrams, onTapTerm })).filter(Boolean);
}

export function renderBlock(block, { diagrams = [], onTapTerm = null } = {}) {
  switch (block.type) {
    case "paragraph":
      return richText(block.text, onTapTerm, "p.text");

    case "list": {
      const list = h(block.ordered ? "ol" : "ul");
      for (const item of block.items || []) list.append(richText(item, onTapTerm, "li"));
      return list;
    }

    case "table":
      return table(block, onTapTerm);

    case "code":
      return h("pre", h("code", block.text || ""));

    case "diagram_ref": {
      const diagram = diagrams.find((candidate) => candidate.id === block.diagramId);
      return diagram ? renderDiagram(diagram) : null;
    }

    case "model_card":
      return card([
        h("h3", block.title || ""),
        block.subtitle && h("p.small.muted", { style: { marginTop: "4px" } }, block.subtitle),
        h(
          "ul",
          { style: { marginTop: "12px" } },
          (block.items || []).map((item) => richText(item, onTapTerm, "li"))
        ),
      ]);

    case "example":
      return card([
        h(
          "div.row.caption.muted",
          icon("text.book.closed", { size: 13 }),
          block.title || S.Lesson.example
        ),
        h("p.text", { style: { marginTop: "6px" } }, block.text || ""),
      ]);

    case "callout":
      return notice([block.title, block.text].filter(Boolean).join(" — "), {
        symbol: calloutSymbol(block.tone),
        tone: block.tone === "warning" ? "caution" : "",
      });

    default:
      return null;
  }
}

function calloutSymbol(tone) {
  if (tone === "warning") return "exclamationmark.triangle";
  if (tone === "limit") return "scope";
  return "info.circle";
}

/** Таблица рисуется сеткой, а не текстом: в уроках домена она несёт сравнение,
 *  и слипшиеся строки его теряют. */
function table(block, onTapTerm) {
  const wrapper = h("div.lesson-table");
  const element = h("table");
  if (block.header?.length) {
    element.append(h("thead", h("tr", block.header.map((cell) => h("th", cell)))));
  }
  const body = h("tbody");
  for (const row of block.rows || []) {
    body.append(h("tr", row.map((cell) => richText(cell, onTapTerm, "td"))));
  }
  element.append(body);
  wrapper.append(element);
  return wrapper;
}

/** Текст с разметкой и, если урок их прислал, терминами `[[id|как в тексте]]`.
 *  Подчёркивание, ведущее в никуда, хуже обычного слова, поэтому без обработчика
 *  термины остаются просто текстом. */
export function richText(raw, onTapTerm, selector = "p.text") {
  const node = h(selector);
  const source = String(raw ?? "");
  if (!onTapTerm || !source.includes("[[")) {
    node.innerHTML = markdown(stripTermMarkup(source));
    return node;
  }
  let rest = source;
  while (true) {
    const open = rest.indexOf("[[");
    const close = rest.indexOf("]]", open);
    if (open === -1 || close === -1) break;
    if (open > 0) node.append(fragment(rest.slice(0, open)));
    const inner = rest.slice(open + 2, close);
    const separator = inner.indexOf("|");
    if (separator === -1) {
      node.append(document.createTextNode(inner));
    } else {
      const termId = inner.slice(0, separator);
      const label = inner.slice(separator + 1);
      node.append(
        h("button.term", { type: "button", onclick: () => onTapTerm(termId) }, label)
      );
    }
    rest = rest.slice(close + 2);
  }
  if (rest) node.append(fragment(rest));
  return node;
}

function fragment(raw) {
  const span = document.createElement("span");
  span.innerHTML = markdown(raw);
  return span;
}

function stripTermMarkup(raw) {
  return raw.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, "$2").replace(/\[\[([^\]]+)\]\]/g, "$1");
}

/** Схема из структуры, а не картинка.
 *
 *  Раскладка по слоям: клиенты слева, сервисы в середине, хранилища ниже, внешние
 *  системы справа. Постоянство расположения важнее компактности — человек должен
 *  узнавать схему, а не разбирать её заново. Побочная выгода структуры: словесное
 *  описание читается скринридером, чего картинка не умеет.
 */
const LAYERS = [["actor", "client"], ["service", "queue", "cache"], ["store"], ["external"]];

export function renderDiagram(diagram) {
  const columns = LAYERS.map(() => []);
  const leftovers = [];
  for (const node of diagram.nodes) {
    const index = LAYERS.findIndex((types) => types.includes(node.type));
    if (index === -1) leftovers.push(node);
    else columns[index].push(node);
  }
  columns[1].push(...leftovers);

  const labels = Object.fromEntries(diagram.nodes.map((node) => [node.id, node.label]));

  return h(
    "figure.diagram",
    { style: { margin: 0 }, role: "img", "aria-label": diagram.textDescription },
    diagram.title && h("div.caption.muted", diagram.title),
    h(
      "div.columns",
      { style: { marginTop: diagram.title ? "12px" : 0 } },
      columns
        .filter((column) => column.length)
        .map((column) =>
          h("div.column", column.map((node) => h(`div.node.${node.type}`, node.label)))
        )
    ),
    diagram.edges.length &&
      h(
        "div.edges",
        diagram.edges.map((edge) =>
          h(
            "div.edge",
            icon(edgeSymbol(edge.type), { size: 12 }),
            `${labels[edge.from] || edge.from} → ${labels[edge.to] || edge.to}` +
              (edge.label ? ` — ${edge.label}` : "")
          )
        )
      )
  );
}

function edgeSymbol(type) {
  if (type === "async") return "arrow.right.to.line.compact";
  if (type === "data") return "minus";
  return "arrow.right";
}

/** Карточка термина: определение, английский эквивалент и ссылка на урок-источник. */
export function termCard(term, onOpenLesson) {
  return h(
    "div.stack",
    h("p.muted", term.termEn),
    h("p.text", term.definition),
    term.sourceLessonId &&
      onOpenLesson &&
      h(
        "button.btn.secondary",
        { type: "button", onclick: () => onOpenLesson(term.sourceLessonId) },
        S.Glossary.openLesson
      )
  );
}
