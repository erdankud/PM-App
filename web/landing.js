/** Лендинг: заставка, ступенчатое появление и рисованные схемы.
 *
 *  Фотографий здесь нет и быть не может: у продукта нет предметного мира, зато
 *  есть собственный — карта навыков, рубрика гейта, линия рубежа. Поэтому фон,
 *  общий для нескольких карточек, рисуется в canvas, а карточки показывают
 *  каждая своё окно в один и тот же рисунок. Приём из референса, источник —
 *  свой.
 */

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const INK = "#000000";
const PAPER = "#ffffff";
const FRONTIER = "#d92b1f";

/** Детерминированный шум: рисунок обязан совпадать при каждой перерисовке,
 *  иначе окна соседних карточек разойдутся между собой. */
function seeded(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

function roundRect(ctx, x, y, w, h, r) {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

// --- Рисунки ----------------------------------------------------------------

/** Карта навыков: шесть секторов, три кольца, карточки-узлы.
 *  `mode` меняет только чернила — на чёрной карточке та же карта белым. */
function drawAtlas(ctx, w, h, mode = "light") {
  const ink = mode === "dark" ? PAPER : INK;
  const ground = mode === "dark" ? INK : "#fafaf9";
  ctx.fillStyle = ground;
  ctx.fillRect(0, 0, w, h);

  const cx = w * 0.5;
  const cy = h * 0.52;
  const outer = Math.max(w, h) * 0.66;
  const inner = outer * 0.19;
  const rings = [0.34, 0.58, 0.84];
  const rand = seeded(20260909);

  // Границы направлений — сплошные и тяжёлые: это территории, а не подсказка
  // под карточками.
  ctx.strokeStyle = ink;
  ctx.globalAlpha = mode === "dark" ? 0.35 : 0.22;
  ctx.lineWidth = 1.6;
  for (let s = 0; s < 6; s += 1) {
    const angle = (Math.PI * 2 * s) / 6 - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner);
    ctx.lineTo(cx + Math.cos(angle) * outer, cy + Math.sin(angle) * outer);
    ctx.stroke();
  }
  ctx.globalAlpha = mode === "dark" ? 0.18 : 0.12;
  ctx.lineWidth = 1;
  for (const ring of rings) {
    ctx.beginPath();
    ctx.arc(cx, cy, outer * ring, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;

  // Узлы. Их плотность растёт к внешнему кольцу, как на настоящей карте.
  const cardW = Math.max(58, Math.min(w, h) * 0.135);
  const cardH = cardW * 0.52;
  for (let s = 0; s < 6; s += 1) {
    rings.forEach((ring, ringIndex) => {
      const count = 3 + ringIndex * 2;
      for (let i = 0; i < count; i += 1) {
        const spread = (Math.PI * 2) / 6;
        const base = (Math.PI * 2 * s) / 6 - Math.PI / 2;
        const angle = base + spread * ((i + 0.5) / count) + (rand() - 0.5) * 0.06;
        const radius = outer * ring + (rand() - 0.5) * outer * 0.07;
        const x = cx + Math.cos(angle) * radius - cardW / 2;
        const y = cy + Math.sin(angle) * radius - cardH / 2;
        if (x > w || y > h || x + cardW < 0 || y + cardH < 0) continue;

        const done = rand() < 0.34;
        roundRect(ctx, x, y, cardW, cardH, cardH * 0.28);
        ctx.fillStyle = mode === "dark"
          ? (done ? "rgba(255,255,255,0.14)" : "rgba(255,255,255,0.05)")
          : (done ? "rgba(0,0,0,0.055)" : PAPER);
        ctx.fill();
        ctx.strokeStyle = ink;
        ctx.globalAlpha = mode === "dark" ? 0.32 : 0.2;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Две строки-заглушки вместо названия: на этом масштабе настоящий текст
        // всё равно был бы кашей, а карточка должна читаться как карточка.
        ctx.globalAlpha = mode === "dark" ? 0.4 : 0.28;
        ctx.fillStyle = ink;
        const px = x + cardW * 0.14;
        ctx.fillRect(px, y + cardH * 0.3, cardW * 0.56, 2);
        ctx.fillRect(px, y + cardH * 0.52, cardW * 0.36, 2);
        ctx.globalAlpha = 1;
      }
    });
  }

  // Линия рубежа: единственный цвет. Радиус между осями секторов сглажен
  // косинусом — прогресс, нарисованный шестиугольником, читался бы как фигура
  // с углами, а не как занятая земля.
  const covered = [0.62, 0.44, 0.5, 0.3, 0.36, 0.24];
  ctx.beginPath();
  const steps = 260;
  for (let i = 0; i <= steps; i += 1) {
    const t = (i / steps) * 6;
    const a = Math.floor(t) % 6;
    const b = (a + 1) % 6;
    const local = t - Math.floor(t);
    const eased = (1 - Math.cos(local * Math.PI)) / 2;
    const share = covered[a] + (covered[b] - covered[a]) * eased;
    const radius = inner + (outer * 0.88 - inner) * share;
    const angle = (Math.PI * 2 * t) / 6 - Math.PI / 2 + Math.PI / 6;
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.strokeStyle = FRONTIER;
  ctx.lineWidth = 2.4;
  ctx.stroke();
}

/** Решётка узлов и связей — карта вблизи. */
function drawLattice(ctx, w, h) {
  ctx.fillStyle = "#eeeeef";
  ctx.fillRect(0, 0, w, h);
  const rand = seeded(881203);
  const step = Math.max(88, Math.min(w, h) * 0.17);
  const cols = Math.ceil(w / step) + 2;
  const rows = Math.ceil(h / step) + 2;
  const points = [];
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      points.push({
        x: (c - 0.5) * step + (rand() - 0.5) * step * 0.4,
        y: (r - 0.5) * step + (rand() - 0.5) * step * 0.4,
        solid: rand() < 0.18,
      });
    }
  }
  ctx.strokeStyle = INK;
  ctx.globalAlpha = 0.22;
  ctx.lineWidth = 1;
  for (const p of points) {
    for (const q of points) {
      const d = Math.hypot(p.x - q.x, p.y - q.y);
      if (d > 0 && d < step * 1.15) {
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(q.x, q.y);
        ctx.stroke();
      }
    }
  }
  ctx.globalAlpha = 1;
  const cw = step * 0.62;
  const ch = cw * 0.5;
  for (const p of points) {
    roundRect(ctx, p.x - cw / 2, p.y - ch / 2, cw, ch, ch * 0.3);
    ctx.fillStyle = p.solid ? INK : PAPER;
    ctx.fill();
    ctx.strokeStyle = INK;
    ctx.globalAlpha = p.solid ? 1 : 0.3;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.globalAlpha = p.solid ? 0.5 : 0.26;
    ctx.fillStyle = p.solid ? PAPER : INK;
    ctx.fillRect(p.x - cw * 0.32, p.y - 3, cw * 0.44, 2);
    ctx.fillRect(p.x - cw * 0.32, p.y + 3, cw * 0.28, 2);
    ctx.globalAlpha = 1;
  }
}

/** Рубрика гейта: настоящие веса из `app/services/scoring.py`. */
function drawRubric(ctx, w, h) {
  ctx.fillStyle = "#fafaf9";
  ctx.fillRect(0, 0, w, h);
  const parts = [
    ["Rationale", 45],
    ["Decision", 25],
    ["Evidence", 15],
    ["Communication", 15],
  ];
  const padX = w * 0.1;
  const top = h * 0.38;
  const barH = Math.max(9, h * 0.075);
  const gap = barH * 0.75;
  const full = w - padX * 2;

  ctx.font = `600 ${Math.max(8, h * 0.062)}px "IBM Plex Mono", monospace`;
  parts.forEach(([label, value], i) => {
    const y = top + i * (barH + gap);
    ctx.fillStyle = "rgba(0,0,0,0.08)";
    roundRect(ctx, padX, y, full, barH, barH / 2);
    ctx.fill();
    ctx.fillStyle = INK;
    roundRect(ctx, padX, y, full * (value / 45), barH, barH / 2);
    ctx.fill();
    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.textBaseline = "middle";
    ctx.fillText(`${label} ${value}`, padX, y - gap * 0.62);
  });

  // Порог: 70 из 100, и вариант плюс разбор доказательств до него не дотягивают.
  const y = top + parts.length * (barH + gap) + barH * 0.5;
  ctx.strokeStyle = FRONTIER;
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(padX + full * 0.7, y);
  ctx.lineTo(padX + full * 0.7, top - gap);
  ctx.stroke();
  ctx.fillStyle = FRONTIER;
  ctx.font = `600 ${Math.max(8, h * 0.062)}px "IBM Plex Mono", monospace`;
  ctx.fillText("pass 70", padX + full * 0.7 + 5, y - barH * 0.2);
}

/** Блок: уроки, а последней строкой — гейт. */
function drawRoute(ctx, w, h) {
  ctx.fillStyle = "#fafaf9";
  ctx.fillRect(0, 0, w, h);
  const padX = w * 0.11;
  const rows = 5;
  const top = h * 0.3;
  const rowH = Math.max(8, h * 0.082);
  const gap = rowH * 0.62;
  for (let i = 0; i < rows; i += 1) {
    const y = top + i * (rowH + gap);
    const gate = i === rows - 1;
    roundRect(ctx, padX, y, w - padX * 2, rowH, rowH * 0.34);
    ctx.fillStyle = gate ? INK : PAPER;
    ctx.fill();
    ctx.strokeStyle = INK;
    ctx.globalAlpha = gate ? 1 : 0.22;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.globalAlpha = gate ? 0.65 : 0.3;
    ctx.fillStyle = gate ? PAPER : INK;
    ctx.fillRect(padX + rowH * 0.55, y + rowH / 2 - 1, (w - padX * 2) * (gate ? 0.42 : 0.3 + i * 0.07), 2);
    ctx.globalAlpha = 1;
    if (!gate) {
      ctx.beginPath();
      ctx.arc(padX + rowH * 0.32, y + rowH / 2, rowH * 0.13, 0, Math.PI * 2);
      ctx.fillStyle = i < 3 ? INK : "rgba(0,0,0,0.2)";
      ctx.fill();
    }
  }
}

// --- Общий фон для нескольких карточек --------------------------------------

/** Одно дорогое рисование в буфер, дальше — дешёвые копии в окна карточек. */
function mosaic(section, draw, mode) {
  const cards = [...section.querySelectorAll("[data-window]")];
  if (!cards.length) return () => {};
  const buffer = document.createElement("canvas");
  const bufferCtx = buffer.getContext("2d");

  const paint = () => {
    const box = section.getBoundingClientRect();
    const w = Math.ceil(box.width);
    const h = Math.ceil(box.height);
    if (w === 0 || h === 0) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    buffer.width = w * dpr;
    buffer.height = h * dpr;
    bufferCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw(bufferCtx, w, h, mode);

    for (const card of cards) {
      let canvas = card.querySelector(":scope > canvas");
      if (!canvas) {
        canvas = document.createElement("canvas");
        card.prepend(canvas);
      }
      const c = card.getBoundingClientRect();
      canvas.width = buffer.width;
      canvas.height = buffer.height;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      canvas.style.left = `${box.left - c.left}px`;
      canvas.style.top = `${box.top - c.top}px`;
      const ctx = canvas.getContext("2d");
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(buffer, 0, 0);
    }
  };

  paint();
  return paint;
}

function figure(canvas, draw, mode) {
  const paint = () => {
    const box = canvas.getBoundingClientRect();
    const w = Math.ceil(box.width);
    const h = Math.ceil(box.height);
    if (w === 0 || h === 0) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw(ctx, w, h, mode);
  };
  paint();
  return paint;
}

// --- Заставка и появление ----------------------------------------------------

function splash() {
  const node = document.getElementById("splash");
  if (!node) return;
  if (REDUCED) {
    node.remove();
    return;
  }
  const readout = node.querySelector(".count");
  const started = performance.now();
  const DURATION = 2000;
  let done = false;

  const finish = () => {
    if (done) return;
    done = true;
    node.classList.add("exiting");
    setTimeout(() => node.remove(), 700);
  };

  const tick = (now) => {
    const share = Math.min(1, (now - started) / DURATION);
    readout.textContent = String(Math.round(share * 100));
    if (share < 1) requestAnimationFrame(tick);
    else setTimeout(finish, 200);
  };
  requestAnimationFrame(tick);
  // Скрытая вкладка кадров не получает вовсе, и заставка осталась бы навсегда.
  setTimeout(finish, DURATION + 1600);
}

function reveal() {
  const items = [...document.querySelectorAll(".rise")];
  if (REDUCED) {
    items.forEach((item) => item.classList.add("shown"));
    return;
  }
  const show = (item, index) => {
    item.style.transitionDelay = `${index * 110}ms`;
    item.classList.add("shown");
  };
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const section = entry.target;
        [...section.querySelectorAll(".rise")].forEach(show);
        observer.unobserve(section);
      }
    },
    { threshold: 0.15 }
  );
  document.querySelectorAll("section").forEach((section) => observer.observe(section));
  // Страховка: анимация — украшение, содержимое им не является.
  setTimeout(() => items.forEach((item) => item.classList.add("shown")), 1200);
}

// --- Сборка ------------------------------------------------------------------

const painters = [];
const s1 = document.getElementById("s1");
const s2 = document.getElementById("s2");
if (s1) painters.push(mosaic(s1, drawAtlas, "light"));
if (s2) painters.push(mosaic(s2, drawLattice));

const figures = {
  rubric: drawRubric,
  route: drawRoute,
  frontier: (ctx, w, h) => drawAtlas(ctx, w, h, "dark"),
};
document.querySelectorAll("[data-figure]").forEach((canvas) => {
  const draw = figures[canvas.dataset.figure];
  if (draw) painters.push(figure(canvas, draw));
});

let resizeTimer = null;
const repaint = () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => painters.forEach((paint) => paint()), 120);
};
window.addEventListener("resize", repaint);
// Шрифты меняют высоту заголовков, а с ней и положение окон.
if (document.fonts?.ready) document.fonts.ready.then(() => painters.forEach((paint) => paint()));

splash();
reveal();
