/** Карта навыков — радиальный атлас, повторяющий исходную схему.
 *
 *  Референс: «Skill Map of Product Management», Product Architecture Framework,
 *  Сергей Тихомиров. Из него взята вся грамматика: шесть секторов по кругу, три
 *  концентрических уровня, и карточка как «название навыка + ключевой вопрос +
 *  набор моделей». Легенда исходной схемы описывает карточку именно так.
 *
 *  Одна карточка — один навык, и нажатие ведёт в его урок, а не в гейт. Гейт живёт
 *  на странице блока; на карте его нет вовсе.
 *
 *  Раскладка вычисляется, а не забита руками: узел получает начальное место в своём
 *  клине (сектор × кольцо), после чего расталкивание разводит перекрытия. Поэтому
 *  карта переживает добавление узла — в отличие от исходной схемы, нарисованной
 *  вручную.
 */
import { svg, h } from "../dom.js";
import { iconPath } from "../icons.js";
import { S } from "../strings.js";

/** По оттенку на домен — те же значения, что в `SkillRing.swift`. */
const HUES = {
  discovery: "#2f6fa8",
  value_design: "#6a5aa8",
  delivery: "#1f7f79",
  marketing: "#a85b18",
  growth: "#b24a63",
  economics: "#7c6b22",
  data: "#2b7a9e",
  integration: "#5c5ea8",
  scale: "#a85a38",
  performance: "#8a6712",
  ai_systems: "#5f7a26",
  security: "#a3486b",
};

/** Порядок секторов по часовой стрелке от верха — как на исходной схеме.
 *  Поле `order` в контенте задаёт порядок чтения, а не место на круге. */
const SECTOR_ORDER = [
  "discovery",
  "value_design",
  "delivery",
  "growth",
  "marketing",
  "economics",
];

const CARD_W = 176;
const CARD_H = 92;
/** Кольца: внутреннее — атомарные задачи, внешнее — стратегия (легенда схемы).
 *  Радиусы заданы плотностью, а не на глаз: в полосу должно поместиться до
 *  двадцати четырёх карточек 176×92, иначе расталкивание выдавливает их наружу
 *  и рисунок расползается. Площадь полосы держим вдвое больше суммарной площади
 *  её карточек. */
const BANDS = [
  [280, 640],
  [640, 1020],
  [1020, 1440],
];
const OUTER = 1720;
/** Внутренний круг: там счётчик, и от него же начинается граница освоенного. */
const HOLE = 210;

const rad = (deg) => (deg * Math.PI) / 180;

// --- Раскладка ---------------------------------------------------------------

/** Начальное место узла в его клине, потом — расталкивание.
 *
 *  Радиус чередуется между третями полосы, а угол распределяется равномерно:
 *  без этого четыре карточки одного блока встают в одну дугу и перекрываются
 *  ещё до расталкивания.
 */
function seed(nodes, domains) {
  const sectors = new Map();
  const order = domains.map((d) => d.key);
  const wheel = SECTOR_ORDER.filter((key) => order.includes(key));
  const keys = wheel.length === order.length ? wheel : order;
  keys.forEach((key, index) => {
    const span = 360 / keys.length;
    sectors.set(key, { start: -90 - span / 2 + index * span, span, index });
  });

  const groups = new Map();
  for (const node of nodes) {
    const key = `${node.domainKey}:${node.tier}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(node);
  }

  const placed = [];
  for (const [key, group] of groups) {
    const [domainKey, tierText] = key.split(":");
    const sector = sectors.get(domainKey);
    if (!sector) continue;
    const [inner, outer] = BANDS[Number(tierText) - 1] || BANDS[BANDS.length - 1];
    group.sort((a, b) => a.order - b.order);
    const n = group.length;
    group.forEach((node, i) => {
      const t = n > 1 ? (i + 0.5) / n : 0.5;
      // Чередование по радиусу: соседи по углу расходятся по глубине.
      const depth = n > 1 ? (i % 2 === 0 ? 0.3 : 0.72) : 0.5;
      const angle = sector.start + sector.span * (0.08 + 0.84 * t);
      const radius = inner + (outer - inner - CARD_H) * depth + CARD_H / 2;
      placed.push({
        node,
        hue: HUES[domainKey] || "#2f6b4a",
        sector,
        band: [inner, outer],
        x: radius * Math.cos(rad(angle)),
        y: radius * Math.sin(rad(angle)),
      });
    });
  }
  return { placed, sectors };
}

/** Расталкивание перекрытий с возвратом в свой клин.
 *
 *  Полностью жёсткое удержание в клине сделало бы перекрытия неразрешимыми, поэтому
 *  границы мягкие: карточка может немного выйти за пунктир, как на исходной схеме.
 */
function relax(placed, iterations = 260) {
  const padX = 26;
  const padY = 22;
  for (let step = 0; step < iterations; step += 1) {
    let moved = 0;
    for (let i = 0; i < placed.length; i += 1) {
      for (let j = i + 1; j < placed.length; j += 1) {
        const a = placed[i];
        const b = placed[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const overlapX = CARD_W + padX - Math.abs(dx);
        const overlapY = CARD_H + padY - Math.abs(dy);
        if (overlapX <= 0 || overlapY <= 0) continue;
        // Расталкиваем по той оси, где перекрытие мельче — так карточки
        // расходятся, а не проскакивают друг сквозь друга.
        if (overlapX / (CARD_W + padX) < overlapY / (CARD_H + padY)) {
          const push = (overlapX / 2) * (dx >= 0 ? 1 : -1) * 0.5;
          a.x -= push;
          b.x += push;
        } else {
          const push = (overlapY / 2) * (dy >= 0 ? 1 : -1) * 0.5;
          a.y -= push;
          b.y += push;
        }
        moved += 1;
      }
    }
    // Мягкий возврат в свой сектор и кольцо.
    for (const item of placed) {
      const r = Math.hypot(item.x, item.y) || 1;
      const [inner, outer] = item.band;
      const lo = inner + CARD_H / 2;
      const hi = outer - CARD_H / 2;
      const target = Math.min(Math.max(r, lo), hi);
      let angle = (Math.atan2(item.y, item.x) * 180) / Math.PI;
      const start = item.sector.start;
      const end = start + item.sector.span;
      // Угол разворачиваем в окно сектора, иначе −170° и 190° считаются разными.
      while (angle < start - 180) angle += 360;
      while (angle > start + 180) angle -= 360;
      const clamped = Math.min(Math.max(angle, start + 3), end - 3);
      const blend = 0.12;
      const newAngle = angle + (clamped - angle) * blend;
      const newR = r + (target - r) * blend;
      item.x = newR * Math.cos(rad(newAngle));
      item.y = newR * Math.sin(rad(newAngle));
    }
    if (!moved && step > 30) break;
  }
  return placed;
}

// --- Отрисовка ---------------------------------------------------------------

function wrap(text, limit, maxLines) {
  const words = String(text || "").split(/\s+/);
  const lines = [];
  let line = "";
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (next.length > limit && line) {
      lines.push(line);
      line = word;
      if (lines.length === maxLines) break;
    } else {
      line = next;
    }
  }
  if (lines.length < maxLines && line) lines.push(line);
  if (lines.length === maxLines && words.join(" ").length > lines.join(" ").length) {
    lines[maxLines - 1] = `${lines[maxLines - 1].replace(/[\s.,;:]+$/, "")}…`;
  }
  return lines;
}

function card(item, { selected, onOpen, onSelect }) {
  const { node, hue } = item;
  const x = item.x - CARD_W / 2;
  const y = item.y - CARD_H / 2;
  const done = node.lessons.length > 0 && node.lessons.every((l) => l.completed);
  const locked = node.blockStatus === "locked";

  const group = svg("g", {
    class: `atlas-card${selected ? " selected" : ""}${done ? " done" : ""}`,
    role: "button",
    tabindex: "0",
    "aria-label": `${node.title}. ${node.keyQuestion}. ${
      done ? S.Tree.legendLessonDone : S.Common.minutes(node.lessons.reduce((s, l) => s + l.estimatedMinutes, 0))
    }`,
    onclick: (event) => {
      if (event.detail === 0) return;
      onSelect(node);
    },
    ondblclick: () => onOpen(node),
    onkeydown: (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        onOpen(node);
      } else if (event.key === " ") {
        event.preventDefault();
        onSelect(node);
      }
    },
  });

  group.append(
    svg("rect", {
      x,
      y,
      width: CARD_W,
      height: CARD_H,
      rx: 14,
      fill: hue,
      "fill-opacity": locked ? 0.04 : done ? 0.2 : 0.11,
      stroke: selected ? "var(--text-primary)" : hue,
      "stroke-opacity": locked ? 0.2 : selected ? 1 : 0.45,
      "stroke-width": selected ? 2.4 : 1,
    })
  );

  const ink = locked ? 0.55 : 1;
  let cursor = y + 18;
  wrap(node.title, 26, 2).forEach((line) => {
    const t = svg("text", {
      class: "atlas-title",
      x: item.x,
      y: cursor,
      "text-anchor": "middle",
      "font-size": "10.5",
      "font-weight": "700",
      fill: "var(--text-primary)",
      "fill-opacity": ink,
    });
    t.textContent = line;
    group.append(t);
    cursor += 12;
  });

  cursor += 4;
  wrap(node.keyQuestion, 34, 2).forEach((line) => {
    const t = svg("text", {
      class: "atlas-question",
      x: item.x,
      y: cursor,
      "text-anchor": "middle",
      "font-size": "8.5",
      fill: "var(--text-secondary)",
      "fill-opacity": ink,
    });
    t.textContent = line;
    group.append(t);
    cursor += 10;
  });

  // Модели — серыми плашками внизу, как в легенде исходной схемы.
  const models = node.models.slice(0, 3);
  if (models.length) {
    cursor += 3;
    const models_group = svg("g", { class: "atlas-models" });
    group.append(models_group);
    const widths = models.map((m) => Math.min(m.length * 4.6 + 10, CARD_W - 16));
    const total = widths.reduce((s, w) => s + w, 0) + (models.length - 1) * 4;
    let cx = item.x - total / 2;
    models.forEach((model, index) => {
      const w = widths[index];
      models_group.append(
        svg("rect", {
          x: cx,
          y: cursor - 7,
          width: w,
          height: 11,
          rx: 3,
          fill: "var(--text-tertiary)",
          "fill-opacity": locked ? 0.25 : 0.55,
        })
      );
      const t = svg("text", {
        class: "atlas-model",
        x: cx + w / 2,
        y: cursor + 1.5,
        "text-anchor": "middle",
        "font-size": "6.6",
        fill: "var(--surface)",
      });
      t.textContent = model.length > w / 4.6 ? `${model.slice(0, Math.floor(w / 4.6))}…` : model;
      models_group.append(t);
      cx += w + 4;
    });
  }

  if (done) {
    const [d] = iconPath("checkmark.circle.fill");
    group.append(
      svg(
        "g",
        {
          transform: `translate(${x + CARD_W - 20} ${y + 6}) scale(${13 / 256})`,
          fill: hue,
          "aria-hidden": "true",
        },
        svg("path", { d })
      )
    );
  }
  return group;
}

function edgePath(a, b) {
  // Дуга наружу от центра: прямая хорда прошла бы сквозь соседние карточки.
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const r = Math.hypot(mx, my) || 1;
  const bulge = 1 + 42 / r;
  return `M ${a.x.toFixed(1)} ${a.y.toFixed(1)} Q ${(mx * bulge).toFixed(1)} ${(my * bulge).toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
}

/** Строит карту. Возвращает элемент и рычаги управления масштабом. */
export function atlas(map, { selected = null, onSelect, onOpen }) {
  const { placed, sectors } = seed(map.nodes, map.domains);
  relax(placed);
  const byId = new Map(placed.map((item) => [item.node.id, item]));

  const root = svg("svg", {
    class: "atlas",
    viewBox: `${-OUTER} ${-OUTER} ${OUTER * 2} ${OUTER * 2}`,
    role: "group",
    "aria-label": map.sourceAttribution,
  });
  const scene = svg("g", { class: "atlas-scene" });
  root.append(scene);

  // Кольца: три вложенных круга, как на исходной схеме.
  const RING_FILL = ["var(--ink-2)", "var(--ink-3)", "var(--ink-4)"];
  [...BANDS].reverse().forEach(([, outer], index) => {
    scene.append(
      svg("circle", {
        cx: 0,
        cy: 0,
        r: outer,
        fill: RING_FILL[index],
        stroke: "var(--separator-strong)",
        "stroke-width": 2,
      })
    );
  });

  // Границы направлений — жирные и сплошные: шесть секторов должны читаться как
  // шесть отдельных территорий, а не как пунктирная разметка под карточками.
  for (const sector of sectors.values()) {
    const a = rad(sector.start);
    scene.append(
      svg("line", {
        x1: HOLE * Math.cos(a),
        y1: HOLE * Math.sin(a),
        x2: OUTER * 0.97 * Math.cos(a),
        y2: OUTER * 0.97 * Math.sin(a),
        stroke: "var(--text-primary)",
        "stroke-opacity": 0.2,
        "stroke-width": 7,
        "stroke-linecap": "round",
      })
    );
  }

  const wires = svg("g", { class: "atlas-wires", "aria-hidden": "true" });
  scene.append(wires);
  for (const edge of map.edges) {
    const a = byId.get(edge.source);
    const b = byId.get(edge.target);
    if (!a || !b) continue;
    wires.append(
      svg("path", {
        d: edgePath(a, b),
        fill: "none",
        stroke: a.hue,
        "stroke-opacity": edge.kind === "prerequisite" ? 0.5 : 0.3,
        "stroke-width": edge.kind === "prerequisite" ? 1.6 : 1.1,
        "stroke-dasharray": edge.kind === "prerequisite" ? "none" : "3 4",
      })
    );
  }

  for (const item of placed) {
    scene.append(card(item, { selected: selected === item.node.id, onSelect, onOpen }));
  }

  // Подписи секторов — чёрными плашками по кругу, как в источнике.
  const labels = svg("g", { class: "atlas-sectors", "aria-hidden": "true" });
  scene.append(labels);
  for (const domain of map.domains) {
    const sector = sectors.get(domain.key);
    if (!sector) continue;
    const mid = sector.start + sector.span / 2;
    const r = OUTER - 150;
    const x = r * Math.cos(rad(mid));
    const y = r * Math.sin(rad(mid));
    // Разворачиваем подпись вдоль окружности и переворачиваем на левой половине.
    let rotation = mid + 90;
    if (mid > 0 && mid < 180) rotation = mid - 90;
    // Кегль задан обзором, а не вкусом: на нём вся карта сжата примерно в 0.21
    // пикселя на единицу, и подпись меньше ~55 единиц превращается в полоску.
    const width = domain.title.length * 33 + 90;
    const g = svg("g", { transform: `translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${rotation.toFixed(1)})` });
    g.append(
      svg("rect", {
        x: -width / 2,
        y: -54,
        width,
        height: 108,
        rx: 26,
        fill: "var(--panel)",
      })
    );
    const t = svg("text", {
      x: 0,
      y: 20,
      "text-anchor": "middle",
      "font-size": "58",
      "font-weight": "800",
      "letter-spacing": "-0.01em",
      fill: "var(--panel-ink)",
    });
    t.textContent = domain.title;
    g.append(t);
    labels.append(g);
  }

  scene.append(frontier(map, sectors));
  scene.append(tally(map));

  return { root, scene, placed };
}

/** Граница освоенного — единственная цветная линия на карте.
 *
 *  По каждому направлению она отходит от центра тем дальше, чем больше уроков в
 *  нём пройдено. Пока не пройдено ничего — это круг во внутреннем круге; дальше
 *  фигура растёт и вытягивается в те сектора, где вы работали. Радиусы между
 *  осями секторов сглажены косинусом, иначе граница выходит шестиугольником:
 *  прогресс — не многогранник, и рисоваться так не должен.
 */
function frontier(map, sectors) {
  const totals = new Map();
  for (const node of map.nodes) {
    const entry = totals.get(node.domainKey) || { done: 0, total: 0 };
    entry.total += node.lessons.length;
    entry.done += node.lessons.filter((lesson) => lesson.completed).length;
    totals.set(node.domainKey, entry);
  }

  // Контрольная точка на ось каждого сектора.
  const controls = [...sectors.entries()]
    .map(([key, sector]) => {
      const entry = totals.get(key) || { done: 0, total: 0 };
      const share = entry.total ? entry.done / entry.total : 0;
      return {
        angle: sector.start + sector.span / 2,
        radius: HOLE + share * (BANDS[BANDS.length - 1][1] + 40 - HOLE),
      };
    })
    .sort((a, b) => a.angle - b.angle);
  if (!controls.length) return svg("g");

  const at = (deg) => {
    // Между осями радиус идёт по косинусу: гладко и без углов.
    let i = 0;
    while (i < controls.length && controls[i].angle <= deg) i += 1;
    const a = controls[(i - 1 + controls.length) % controls.length];
    const b = controls[i % controls.length];
    let span = b.angle - a.angle;
    if (span <= 0) span += 360;
    let offset = deg - a.angle;
    if (offset < 0) offset += 360;
    const t = span ? offset / span : 0;
    const eased = (1 - Math.cos(Math.PI * t)) / 2;
    return a.radius + (b.radius - a.radius) * eased;
  };

  const points = [];
  for (let deg = 0; deg < 360; deg += 3) {
    const r = at(deg);
    points.push(`${(r * Math.cos(rad(deg))).toFixed(1)} ${(r * Math.sin(rad(deg))).toFixed(1)}`);
  }

  const group = svg("g", { class: "atlas-frontier", "aria-hidden": "true" });
  const d = `M ${points[0]} L ${points.slice(1).join(" L ")} Z`;
  group.append(
    svg("path", { d, fill: "var(--frontier)", "fill-opacity": 0.07, stroke: "none" })
  );
  group.append(
    svg("path", {
      d,
      fill: "none",
      stroke: "var(--frontier)",
      "stroke-width": 5,
      "stroke-linejoin": "round",
    })
  );
  return group;
}

/** Счётчик освоенного в середине: сколько уроков пройдено из скольких. */
function tally(map) {
  const lessons = map.nodes.flatMap((node) => node.lessons);
  const done = lessons.filter((lesson) => lesson.completed).length;
  const group = svg("g", { class: "atlas-tally", "aria-hidden": "true" });
  group.append(
    svg("circle", {
      cx: 0,
      cy: 0,
      r: HOLE - 26,
      fill: "var(--background)",
      stroke: "var(--text-primary)",
      "stroke-width": 3,
    })
  );
  const number = svg("text", {
    class: "atlas-tally-number",
    x: 0,
    y: 18,
    "text-anchor": "middle",
    "font-size": "84",
    "font-weight": "800",
    "letter-spacing": "-0.04em",
    fill: "var(--text-primary)",
  });
  number.textContent = String(done);
  group.append(number);
  const label = svg("text", {
    class: "atlas-tally-label",
    x: 0,
    y: 56,
    "text-anchor": "middle",
    "font-size": "19",
    "font-weight": "600",
    fill: "var(--text-secondary)",
  });
  label.textContent = S.Tree.skillsLearned(lessons.length);
  group.append(label);
  return group;
}

/** Панорамирование и масштаб. Живёт отдельно от отрисовки: перерисовка карты
 *  не должна сбрасывать положение, к которому человек только что доехал. */
export function panZoom(root, scene, { min = 0.45, max = 7 } = {}) {
  // Открываемся с обзора: сперва видно форму карты, потом в неё въезжают.
  const view = { k: 0.95, x: 0, y: 0 };
  let frame = null;

  /** Пикселей на единицу сцены при k = 1.
   *
   *  viewBox квадратный, а холст широкий, поэтому `preserveAspectRatio` вписывает
   *  по меньшей стороне. Считать по ширине — та самая ошибка, из-за которой зум
   *  уезжает от курсора, а карта дёргается при перетаскивании. */
  const unit = () => {
    const rect = root.getBoundingClientRect();
    return Math.min(rect.width, rect.height) / (OUTER * 2) || 1;
  };

  /** Масштаб, при котором карточка выходит на экран примерно в свою натуральную
   *  ширину: обзор красив, но подписи на нём нечитаемы, а карта — чтобы читать. */
  const readable = () => Math.min(max, Math.max(min, 190 / (CARD_W * unit())));

  const apply = () => {
    frame = null;
    // Уровень детализации: на обзоре вопрос и модели превращаются в кашу,
    // и честнее их убрать, чем делать вид, что карта читается целиком.
    root.classList.toggle("lod-far", view.k < 1.7);
    root.classList.toggle("lod-shapes", view.k < 0.9);
    scene.setAttribute(
      "transform",
      `translate(${view.x.toFixed(2)} ${view.y.toFixed(2)}) scale(${view.k.toFixed(4)})`
    );
  };
  /** Кадр откладывается, но не теряется.
   *
   *  В скрытой вкладке `requestAnimationFrame` не вызывается вовсе. Если просто
   *  запомнить «кадр уже заказан», то первый же заказ в скрытой вкладке остаётся
   *  висеть навсегда, и после возвращения ни колесо, ни кнопки, ни перетаскивание
   *  уже ничего не двигают — состояние меняется, а на экран не попадает. */
  const schedule = () => {
    if (frame !== null) return;
    if (document.hidden) {
      apply();
      return;
    }
    frame = requestAnimationFrame(apply);
  };
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && frame !== null) {
      cancelAnimationFrame(frame);
      apply();
    }
  });

  /** Экранные координаты → координаты сцены, чтобы зум шёл от курсора.
   *  Начало координат сцены — центр холста. */
  const toScene = (event) => {
    const rect = root.getBoundingClientRect();
    const px = unit();
    return {
      vx: (event.clientX - rect.left - rect.width / 2) / px,
      vy: (event.clientY - rect.top - rect.height / 2) / px,
    };
  };

  const zoomTo = (k, anchor) => {
    const next = Math.min(max, Math.max(min, k));
    if (next === view.k) return;
    if (anchor) {
      view.x = anchor.vx - ((anchor.vx - view.x) / view.k) * next;
      view.y = anchor.vy - ((anchor.vy - view.y) / view.k) * next;
    }
    view.k = next;
    schedule();
  };

  root.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const factor = Math.exp(-event.deltaY * 0.0016);
      zoomTo(view.k * factor, toScene(event));
    },
    { passive: false }
  );

  const pointers = new Map();
  let pinch = null;
  let dragging = false;
  let origin = null;
  let suppressClick = false;
  /** Ниже этого сдвига жест считается нажатием, а не перетаскиванием. */
  const DRAG_SLOP = 4;

  root.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 && event.pointerType === "mouse") return;
    pointers.set(event.pointerId, event);
    origin = { x: event.clientX, y: event.clientY };
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { distance: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY), k: view.k };
      // Щипок однозначен: захватываем сразу, нажатием он быть не может.
      startDrag(event);
    }
    // Захват указателя откладывается до настоящего движения. Захват на
    // pointerdown перенаправляет все последующие события на сам <svg>, и нативный
    // click до карточки уже не доходит — карта переставала открывать уроки.
  });

  const startDrag = (event) => {
    if (dragging) return;
    dragging = true;
    try {
      root.setPointerCapture(event.pointerId);
    } catch {
      /* указатель мог уже уйти */
    }
    root.classList.add("dragging");
  };

  root.addEventListener("pointermove", (event) => {
    const previous = pointers.get(event.pointerId);
    if (!previous) return;

    if (!dragging && origin) {
      const moved = Math.hypot(event.clientX - origin.x, event.clientY - origin.y);
      if (moved <= DRAG_SLOP) return;
      startDrag(event);
    }

    pointers.set(event.pointerId, event);
    if (pointers.size === 2 && pinch) {
      const [a, b] = [...pointers.values()];
      const distance = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      const centre = toScene({
        clientX: (a.clientX + b.clientX) / 2,
        clientY: (a.clientY + b.clientY) / 2,
      });
      zoomTo(pinch.k * (distance / pinch.distance), centre);
      return;
    }
    const px = unit();
    view.x += (event.clientX - previous.clientX) / px;
    view.y += (event.clientY - previous.clientY) / px;
    schedule();
  });

  const release = (event) => {
    pointers.delete(event.pointerId);
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) {
      // Клик после перетаскивания — не выбор карточки, а хвост жеста.
      suppressClick = dragging;
      dragging = false;
      origin = null;
      root.classList.remove("dragging");
    }
  };
  root.addEventListener("pointerup", release);
  root.addEventListener("pointercancel", release);

  root.addEventListener(
    "click",
    (event) => {
      if (!suppressClick) return;
      suppressClick = false;
      event.stopPropagation();
      event.preventDefault();
    },
    true
  );

  const api = {
    // Кнопки масштабируют вокруг центра холста, а не вокруг начала координат:
    // в середине карты дырка, и зум «в никуда» выглядит поломкой.
    zoomBy: (factor) =>
      zoomTo(view.k * factor, { vx: -view.x / view.k, vy: -view.y / view.k }),
    /** «Вся карта»: обзор целиком. */
    reset: () => {
      view.k = 0.95;
      view.x = 0;
      view.y = 0;
      schedule();
    },
    /** Читаемый масштаб — то, с чего карта открывается. */
    readable: () => {
      view.k = readable();
      view.x = 0;
      view.y = 0;
      schedule();
    },
    /** Подвести карточку под центр экрана, не меняя масштаб. */
    centreOn: (item) => {
      view.x = -item.x * view.k;
      view.y = -item.y * view.k;
      schedule();
    },
    get scale() {
      return view.k;
    },
  };
  apply();
  return api;
}

/** Кнопки масштаба. Колесо есть не у всех, и клавиатуре тоже нужен путь. */
export function zoomControls(api) {
  const button = (symbol, label, action) =>
    h(
      "button.atlas-zoom-button",
      { type: "button", title: label, "aria-label": label, onclick: action },
      h("span", symbol)
    );
  return h(
    "div.atlas-zoom.glass",
    button("+", S.Tree.zoomIn, () => api.zoomBy(1.3)),
    button("−", S.Tree.zoomOut, () => api.zoomBy(1 / 1.3)),
    button("⤢", S.Tree.zoomReset, () => api.reset())
  );
}
