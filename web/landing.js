/* Лендинг. Единственное, что здесь делает скрипт, — появление секций при
 * прокрутке. Рисование ушло вместе с рисунками: страница собрана из заливок и
 * снимков экранов, и ни то ни другое не нужно перерисовывать при смене темы
 * или размера окна.
 *
 * Класс `.rise` вешается отсюда, а не пишется в разметке: без скрипта страница
 * должна приходить видимой, а не с opacity: 0 в ожидании наблюдателя.
 */

const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function reveal() {
  const items = [...document.querySelectorAll("main > section > .inner > *")];
  items.forEach((node) => node.classList.add("rise"));

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
  document.querySelectorAll("main > section").forEach((section) => observer.observe(section));

  // Страховка: в скрытой вкладке наблюдатель не срабатывает ни разу, а
  // анимация — украшение, содержимое им не является.
  setTimeout(() => items.forEach((item) => item.classList.add("shown")), 1200);
}

reveal();
