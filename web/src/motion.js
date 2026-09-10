/** Каскадное появление — из исходного промпта.
 *
 *  Правило то же, что было у заставки: движение объясняет порядок. Каскад по
 *  секции показывает, из чего она собрана, в том порядке, в каком её читают.
 *
 *  Счётчик загрузки жил здесь же и переехал в `web/index.html`. Причина не в
 *  вкусе: он ждал те самые модули, в числе которых приезжал сам, и потому
 *  начинал считать уже после того, как ожидание кончилось — две секунды поверх
 *  готового экрана. Считать загрузку может только то, что не грузится.
 *
 *  `prefers-reduced-motion` уважается: там секции просто появляются.
 */
const reduced = () =>
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

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
