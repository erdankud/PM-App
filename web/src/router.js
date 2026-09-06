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
  if (replace) window.location.replace(target);
  else window.location.hash = target;
}

export function back(fallback = "/map") {
  if (window.history.length > 1) window.history.back();
  else navigate(fallback);
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
  onNavigate = handler;
  window.addEventListener("hashchange", handler);
  handler();
}
