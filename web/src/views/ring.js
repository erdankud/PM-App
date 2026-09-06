/** Карта: секторы — домены, кольца — круги, ровно как в источнике.
 *
 *  Каждая ячейка — отдельный элемент со своей целью нажатия и своей подписью для
 *  скринридера: карта должна быть проходима без зрения, а восемнадцать фигур стоят
 *  дёшево (спека v0.2 §14).
 */
import { svg } from "../dom.js";
import { iconPath } from "../icons.js";
import { S } from "../strings.js";

/** По оттенку на домен. Статус меняет насыщенность заливки, но не тон — иначе
 *  почти закрытая карта читается одним серым диском и перестаёт быть обещанием. */
const HUES = {
  discovery: "#3d78d9",
  value_design: "#735ad9",
  delivery: "#2e948d",
  marketing: "#d98533",
  growth: "#cc5273",
  economics: "#5c8c40",
  // Шесть областей System Design: та же грамматика карты, свои оттенки.
  data: "#3385b8",
  integration: "#6b66c7",
  scale: "#bf6b47",
  performance: "#d99e33",
  ai_systems: "#4d996f",
  security: "#b84d6b",
};

const FILL_OPACITY = {
  passed: 0.9,
  gate_ready: 0.45,
  in_progress: 0.3,
  available: 0.2,
  // Видно, но явно ещё не ваше.
  locked: 0.09,
};

const STROKE_OPACITY = {
  passed: 1,
  gate_ready: 1,
  in_progress: 0.65,
  available: 0.65,
  locked: 0.25,
};

const SIZE = 460;
const CENTRE_HOLE = 54;
const GAP = 3;

export function ringMap(tree, { highlighted = null, onSelect }) {
  const centre = SIZE / 2;
  const outer = centre - 18;
  const ringWidth = (outer - CENTRE_HOLE) / 3;
  const domains = tree.domains;
  const sweep = 360 / Math.max(domains.length, 1);

  const root = svg("svg", {
    class: "ring",
    viewBox: `0 0 ${SIZE} ${SIZE}`,
    role: "group",
    "aria-label": S.Tree.passedOfTotal(
      tree.blocks.filter((block) => block.status === "passed").length,
      tree.blocks.length
    ),
  });

  domains.forEach((domain, index) => {
    const blocks = tree.blocks
      .filter((block) => block.domainKey === domain.key)
      .sort((a, b) => a.tier - b.tier);
    // Начало сверху и по часовой стрелке, чтобы карта читалась как циферблат.
    const start = index * sweep - 90;
    const end = (index + 1) * sweep - 90;
    const hue = HUES[domain.key] || "#0a63d6";

    for (const block of blocks) {
      const inner = CENTRE_HOLE + ringWidth * (block.tier - 1);
      const outerRadius = CENTRE_HOLE + ringWidth * block.tier;
      const cell = svg("g", {
        class: `cell${highlighted === block.id ? " highlighted" : ""}`,
        role: "button",
        tabindex: "0",
        "aria-label": blockAccessibility(block, tree),
        onclick: () => onSelect(block),
        onkeydown: (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onSelect(block);
          }
        },
      });
      cell.append(
        svg("path", {
          d: annularSector(centre, centre, inner, outerRadius, start, end),
          fill: hue,
          "fill-opacity": FILL_OPACITY[block.status] ?? 0.1,
          stroke: hue,
          "stroke-opacity": STROKE_OPACITY[block.status] ?? 0.25,
          "stroke-width": highlighted === block.id ? 2 : 0.75,
        })
      );
      const mid = ((start + end) / 2) * (Math.PI / 180);
      const radius = (inner + outerRadius) / 2;
      const x = centre + radius * Math.cos(mid);
      const y = centre + radius * Math.sin(mid);
      const ink = block.status === "passed" ? "#fff" : hue;
      cell.append(
        svg(
          "text",
          {
            x,
            y: y - 5,
            "text-anchor": "middle",
            "dominant-baseline": "central",
            "font-size": "11",
            "font-weight": "700",
            fill: ink,
            "fill-opacity": block.status === "locked" ? 0.55 : 1,
            "pointer-events": "none",
          },
          block.id
        ),
        // Состояние отмечено значком, а не только насыщенностью заливки: цвет
        // не должен быть единственным носителем смысла.
        statusMark(S.Tree.statusSymbol(block.status), x, y + 7, ink, block.status === "locked" ? 0.55 : 1)
      );
      root.append(cell);
    }

    // Буквы идентификатора на внешней кромке: у трёх доменов названия начинаются
    // с одной буквы, а идентификаторы System Design двухбуквенные.
    const code = blocks[0] ? blocks[0].id.slice(0, -1) : "";
    const mid = ((start + end) / 2) * (Math.PI / 180);
    root.append(
      svg(
        "text",
        {
          x: centre + (outer + 9) * Math.cos(mid),
          y: centre + (outer + 9) * Math.sin(mid),
          "text-anchor": "middle",
          "dominant-baseline": "central",
          "font-size": "10",
          "font-weight": "700",
          fill: hue,
          "aria-hidden": "true",
        },
        code
      )
    );
  });

  const passed = tree.blocks.filter((block) => block.status === "passed").length;
  root.append(
    svg(
      "text",
      {
        x: centre,
        y: centre - 6,
        "text-anchor": "middle",
        "font-size": "20",
        "font-weight": "700",
        fill: "currentColor",
        "aria-hidden": "true",
      },
      String(passed)
    ),
    svg(
      "text",
      {
        x: centre,
        y: centre + 12,
        "text-anchor": "middle",
        "font-size": "11",
        fill: "currentColor",
        "fill-opacity": "0.55",
        "aria-hidden": "true",
      },
      S.Tree.ofBlocks(tree.blocks.length)
    )
  );

  return root;
}

/** Значок состояния внутри ячейки: путь из общей таблицы, сжатый до 12 пунктов. */
function statusMark(name, x, y, colour, opacity) {
  const [d, filled] = iconPath(name);
  const scale = 12 / 24;
  return svg(
    "g",
    {
      transform: `translate(${(x - 6).toFixed(2)} ${(y - 6).toFixed(2)}) scale(${scale})`,
      fill: filled ? colour : "none",
      stroke: colour,
      "stroke-width": filled ? 1.4 : 1.7,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      opacity,
      "pointer-events": "none",
      "aria-hidden": "true",
    },
    svg("path", { d })
  );
}

/** Скринридер должен получить то же, что глаз: домен, круг и состояние блока. */
export function blockAccessibility(block, tree) {
  const domain =
    tree.domains.find((candidate) => candidate.key === block.domainKey)?.title || block.domainKey;
  const tier = tree.tiers.find((candidate) => candidate.tier === block.tier)?.title
    || S.Tree.tierName(block.tier);
  return `${domain}, ${tier}. ${block.title}. ${S.Tree.statusLabel(block.status)}. ` +
    S.Tree.lessonsProgress(block.lessonsCompleted, block.lessonsTotal);
}

/** Кольцевой сектор с зазором между соседями, чтобы сетка читалась как отдельные
 *  блоки. Линейный зазор переводится в угловой — иначе ячейки перестают быть
 *  параллельносторонними. */
function annularSector(cx, cy, innerRadius, outerRadius, startDeg, endDeg) {
  const outer = Math.max(0, outerRadius - GAP / 2);
  const inner = Math.max(0, innerRadius + GAP / 2);
  const padOuter = ((GAP / Math.max(outer, 1) / 2) * 180) / Math.PI;
  const padInner = ((GAP / Math.max(inner, 1) / 2) * 180) / Math.PI;

  const a0 = ((startDeg + padOuter) * Math.PI) / 180;
  const a1 = ((endDeg - padOuter) * Math.PI) / 180;
  const b1 = ((endDeg - padInner) * Math.PI) / 180;
  const b0 = ((startDeg + padInner) * Math.PI) / 180;
  const large = endDeg - startDeg > 180 ? 1 : 0;

  const point = (radius, angle) =>
    `${(cx + radius * Math.cos(angle)).toFixed(2)} ${(cy + radius * Math.sin(angle)).toFixed(2)}`;

  return [
    `M ${point(outer, a0)}`,
    `A ${outer} ${outer} 0 ${large} 1 ${point(outer, a1)}`,
    `L ${point(inner, b1)}`,
    `A ${inner} ${inner} 0 ${large} 0 ${point(inner, b0)}`,
    "Z",
  ].join(" ");
}
