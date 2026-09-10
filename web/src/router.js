/** Маршрутизация по хешу.
 *
 *  Хеш, а не History API: тогда приложение живёт по любому префиксу и серверу не
 *  нужен catch-all — он раздаёт статику как есть.
 */

const routes = [];
let onNavigate = () => {};

export function route(pattern, view) {
  const names = [];
  const regex = new RegExp(
    "^" +
      pattern.replace(/:([\w]+)/g, (_, name) => {
        names.push(name);
        return "([^/?]+)";
      }) +
      "$"
  );
  routes.push({ regex, names, view });
}

export function currentPath() {
  const hash = window.location.hash.slice(1) || "/";
  return hash.split("?")[0];
}

export function currentQuery() {
  const hash = window.location.hash.slice(1);
  const index = hash.indexOf("?");
  return new URLSearchParams(index === -1 ? "" : hash.slice(index + 1));
}

export function navigate(path, { replace = false } = {}) {
  const target = `#${path}`;
  if (window.location.hash === target) {
    onNavigate();
    return;
  }
  if (replace) {
    replacing = true;
    window.location.replace(target);
  } else {
    window.location.hash = target;
  }
}

/** Где мы в истории. Нужно ровно одно: что стоит на шаг назад.
 *
 *  Хеш-переход не даёт отличить «вперёд» от «назад» — оба приходят одним
 *  `hashchange`. Поэтому каждой записи проставляется номер через `replaceState`:
 *  у новой записи состояния нет (значит, это переход вперёд и всё, что было
 *  впереди, обнуляется), у пройденной оно возвращается вместе с ней.
 */
const trail = [];
let position = -1;
let replacing = false;

function markPosition() {
  const state = window.history.state;
  const numbered = state && typeof state.i === "number";
  if (numbered) {
    position = state.i;
  } else if (replacing) {
    // Замена записи, а не новая: номер тот же, иначе счётчик разъедется с
    // историей браузера и «на шаг назад» стало бы указывать мимо.
    position = Math.max(position, 0);
  } else {
    position += 1;
    trail.length = position;
  }
  replacing = false;
  if (!numbered) {
    try {
      window.history.replaceState({ ...(state || {}), i: position }, "");
    } catch {
      /* приватный режим — переживём без разматывания истории */
    }
  }
  trail[position] = currentPath();
}

/** Экран выше по иерархии, а не предыдущий по времени.
 *
 *  Стрелка в интерфейсе — это «вверх», и ведёт она туда, где этот экран лежит:
 *  из урока — в список уроков блока, из блока — в Учёбу. По истории она вела бы
 *  в предыдущий урок, то есть вниз по тому же уровню, и цепочка «Следующий урок»
 *  превращала возврат в обратную перемотку той же ленты.
 *
 *  Родитель уже на шаг назад — разматываем историю вместо того, чтобы удлинять
 *  её: иначе десять уроков подряд оставили бы двадцать записей, и кнопка
 *  «назад» самого браузера водила бы человека кругами.
 */
export function up(parent) {
  if (!parent) return;
  if (position > 0 && trail[position - 1] === parent) {
    window.history.back();
    return;
  }
  navigate(parent);
}

export function resolve(path) {
  for (const { regex, names, view } of routes) {
    const match = regex.exec(path);
    if (!match) continue;
    const params = {};
    names.forEach((name, index) => {
      params[name] = decodeURIComponent(match[index + 1]);
    });
    return { view, params };
  }
  return null;
}

export function startRouter(handler) {
  onNavigate = () => {
    markPosition();
    handler();
  };
  window.addEventListener("hashchange", onNavigate);
  onNavigate();
}
