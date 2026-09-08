/** Заставка и каскадное появление — из исходного промпта.
 *
 *  Обе вещи держатся на одном правиле: движение объясняет порядок. Счётчик на
 *  заставке показывает, что приложение грузится и сколько осталось; каскад по
 *  секции показывает, из чего она собрана, в том порядке, в каком её читают.
 *
 *  Всё уважает `prefers-reduced-motion`: там, где движение выключено, заставка
 *  не показывается вовсе, а секции просто появляются.
 */
import { h } from "./dom.js";

const SPLASH_KEY = "pmcoach.splashShown";
/** Две секунды на счёт — как в исходном промпте. Но считаем не тиками по 20 мс:
 *  фоновой вкладке браузер зажимает таймеры до секунды, и счётчик, который должен
 *  занять две секунды, полз бы полторы минуты. Отсчёт идёт от реального времени. */
const COUNT_MS = 2000;
const HOLD_MS = 200;
const FADE_MS = 700;

const reduced = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

/** Показывать ли заставку. Один раз за сессию: на каждом переходе она была бы
 *  не приёмом, а задержкой. */
export function shouldShowSplash() {
  if (reduced()) return false;
  try {
    return !sessionStorage.getItem(SPLASH_KEY);
  } catch {
    return true;
  }
}

/** Белый экран со счётчиком 0→100 в левом нижнем углу. Возвращает узел;
 *  сам себя убирает и зовёт `onComplete`. */
export function splashScreen(onComplete) {
  try {
    sessionStorage.setItem(SPLASH_KEY, "1");
  } catch {
    /* приватный режим */
  }
  const counter = h("span.splash-count", "0");
  const node = h(
    "div.splash",
    { role: "status", "aria-live": "polite", "aria-label": "0%" },
    counter
  );

  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    counter.textContent = "100";
    node.setAttribute("aria-label", "100%");
    setTimeout(() => node.classList.add("exiting"), HOLD_MS);
    setTimeout(() => {
      node.remove();
      onComplete?.();
    }, HOLD_MS + FADE_MS);
  };

  const started = performance.now();
  const step = (now) => {
    const progress = Math.min(1, (now - started) / COUNT_MS);
    const value = Math.round(progress * 100);
    counter.textContent = String(value);
    node.setAttribute("aria-label", `${value}%`);
    if (progress < 1) requestAnimationFrame(step);
    else finish();
  };
  requestAnimationFrame(step);

  // Страховка: в скрытой вкладке кадры не приходят вовсе, и заставка осталась бы
  // на экране навсегда. Экран приложения важнее анимации.
  setTimeout(finish, COUNT_MS + 400);

  return node;
}

/** Каскадное появление детей контейнера, когда он входит в кадр.
 *
 *  Срабатывает один раз: повторное появление при каждой прокрутке превращает
 *  страницу в аттракцион и мешает перечитывать.
 */
export function revealOnScroll(container, { selector = ":scope > *", stagger = 120 } = {}) {
  const items = [...container.querySelectorAll(selector)];
  if (!items.length) return;
  if (reduced() || !("IntersectionObserver" in window)) return;

  items.forEach((item) => {
    item.style.opacity = "0";
    item.style.transform = "translateY(24px)";
  });

  const show = () => {
    items.forEach((item, index) => {
      const delay = index * stagger;
      item.style.transition =
        `opacity 0.6s var(--ease-out) ${delay}ms, transform 0.6s var(--ease-out) ${delay}ms`;
      item.style.opacity = "1";
      item.style.transform = "translateY(0)";
    });
  };

  let done = false;
  const reveal = () => {
    if (done) return;
    done = true;
    observer.disconnect();
    clearTimeout(safety);
    show();
  };

  const observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) reveal();
    },
    { threshold: 0.15 }
  );
  observer.observe(container);

  // Страховка. В скрытой вкладке наблюдатель не срабатывает вовсе, и содержимое
  // осталось бы прозрачным навсегда: человек вернулся бы на пустой экран.
  // Появление — украшение, содержимое — нет.
  const safety = setTimeout(reveal, 1200);
}
