/** Микро-слой над DOM. Ни фреймворка, ни сборки: в проекте нет node-тулчейна,
 *  а экранов здесь два десятка — этого хватает, и приложение остаётся файлами,
 *  которые сервер отдаёт как есть.
 */

/** h("div.card", { onclick }, ...children) — селектор в первом аргументе. */
export function h(selector, props, ...children) {
  const [tag, ...rest] = String(selector).split(/(?=[.#])/);
  const node = document.createElement(tag || "div");
  for (const token of rest) {
    if (token[0] === "#") node.id = token.slice(1);
    else node.classList.add(token.slice(1));
  }
  if (props && (props.nodeType || Array.isArray(props) || typeof props !== "object")) {
    children.unshift(props);
    props = null;
  }
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.classList.add(...String(value).split(" ").filter(Boolean));
    else if (key === "style" && typeof value === "object") Object.assign(node.style, value);
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else if (key === "html") node.innerHTML = value;
    else if (key in node && key !== "list") node[key] = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  append(node, children);
  return node;
}

export function append(node, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

/** Полная замена содержимого узла. */
export function fill(node, ...children) {
  node.replaceChildren();
  append(node, children);
  return node;
}

export function svg(tag, props = {}, ...children) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

/** Инлайновая разметка авторского текста: `**жирный**` и `*курсив*`.
 *  Разбор идёт по уже экранированному тексту, поэтому вставка HTML безопасна:
 *  из разметки рождаются только `<strong>` и `<em>`.
 */
export function markdown(raw) {
  const escaped = escapeHtml(String(raw ?? ""));
  return escaped
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
}

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

/** Абзац авторского текста с разметкой. */
export function rich(raw, selector = "p.text") {
  return h(selector, { html: markdown(raw) });
}

export function debounce(fn, ms) {
  let timer = null;
  const wrapped = (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
  wrapped.cancel = () => clearTimeout(timer);
  wrapped.flush = (...args) => {
    clearTimeout(timer);
    fn(...args);
  };
  return wrapped;
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
