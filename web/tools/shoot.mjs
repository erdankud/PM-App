/* Снимки экранов для лендинга.
 *
 *     node web/tools/shoot.mjs /tmp/shots light
 *     node web/tools/shoot.mjs /tmp/shots dark
 *
 * Нужен запущенный сервер на localhost:8000 с включённой dev-авторизацией.
 * Скрипт заводит собственную учётную запись (`deviceId: web-shots`), проходит
 * онбординг и снимает шесть маршрутов в 1440x900 при dpr 2.
 *
 * Chrome управляется по сырому DevTools Protocol: ни puppeteer, ни playwright
 * в этом репозитории нет, а в Node 26 есть встроенный WebSocket.
 *
 * Две вещи, без которых он молча снимает не то:
 *  - клиент читает сессию один раз при загрузке документа, а переход на URL,
 *    отличающийся только хешем, документ не перезагружает. Поэтому после
 *    `Page.navigate` идёт явный `Page.reload`, иначе каждый кадр — экран входа;
 *  - `getBoundingClientRect()` при `returnByValue` сериализуется в `{}`, потому
 *    что DOMRect отдаёт значения геттерами прототипа. Поля копируются в обычный
 *    объект прямо в выражении, иначе выбор карточки на карте сравнивает undefined.
 *
 * Снимать стоит на учётной записи, где что-то пройдено: на пустой все шесть
 * направлений печатают «0 of 3 blocks», а рубеж на карте вырождается в круг.
 */

import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";

const OUT = process.argv[2];
const THEME = process.argv[3] || "light";
const BASE = "http://localhost:8000";
const W = 1440, H = 900;

const ROUTES = [
  ["learn",    "#/learn"],
  ["map",      "#/map"],
  ["block",    "#/block/D1"],
  ["lesson",   "#/lesson/d1-feedback-matrix"],
  ["practice", "#/practice"],
  ["progress", "#/progress"],
];

const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new", "--remote-debugging-port=9333", "--no-first-run", "--no-default-browser-check",
  `--window-size=${W},${H}`, "--hide-scrollbars", "--force-device-scale-factor=2",
  "--user-data-dir=/tmp/chrome-shots-profile", "about:blank",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function targets() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch("http://localhost:9333/json/list");
      const list = await r.json();
      const page = list.find((t) => t.type === "page");
      if (page) return page;
    } catch {}
    await sleep(250);
  }
  throw new Error("chrome did not come up");
}

const page = await targets();
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));

let id = 0;
const pending = new Map();
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
};
function send(method, params = {}) {
  const n = ++id;
  return new Promise((res, rej) => {
    pending.set(n, (m) => (m.error ? rej(new Error(method + ": " + m.error.message)) : res(m.result)));
    ws.send(JSON.stringify({ id: n, method, params }));
  });
}

await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width: W, height: H, deviceScaleFactor: 2, mobile: false,
});
await send("Emulation.setEmulatedMedia", {
  features: [{ name: "prefers-color-scheme", value: THEME }],
});

async function goto(url, hard = false) {
  await send("Page.navigate", { url });
  await sleep(400);
  // Смена только хеша документ не перезагружает, а сессия читается один раз
  // при загрузке — без явного reload клиент остаётся на экране входа.
  if (hard) { await send("Page.reload", { ignoreCache: false }); }
  await sleep(2400);
}

// Свежий токен на устройство «web-shots», чтобы снимки делались настоящим
// клиентом, а не подставной разметкой.
const auth = await (await fetch(`${BASE}/v1/auth/dev`, {
  method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ deviceId: "web-shots" }),
})).json();
// Онбординг пройден и язык английский — снимки делаются с того экрана, на
// который человек попадает после входа, а не с анкеты перед ним.
await fetch(`${BASE}/v1/me/profile`, {
  method: "PATCH",
  headers: { "content-type": "application/json", authorization: `Bearer ${auth.accessToken}` },
  body: JSON.stringify({ completeOnboarding: true, language: "en" }),
});

await goto(`${BASE}/app/`);
const seed = await send("Runtime.evaluate", {
  awaitPromise: true, returnByValue: true,
  expression: `(() => {
    localStorage.setItem("pmcoach.accessToken",${JSON.stringify(auth.accessToken)});
    localStorage.setItem("pmcoach.refreshToken",${JSON.stringify(auth.refreshToken)});
    localStorage.setItem("pmcoach.deviceId","web-shots");
    return { href: location.href, token: (localStorage.getItem("pmcoach.accessToken")||"").slice(0,12) };
  })()`,
});
console.log("seed:", JSON.stringify(seed.result.value), seed.exceptionDetails ? seed.exceptionDetails.text : "");

for (const [name, hash] of ROUTES) {
  await goto(`${BASE}/app/${hash}`, true);
  await sleep(1600);
  const probe = await send("Runtime.evaluate", { returnByValue: true,
    expression: `({ href: location.href, sidebar: !!document.querySelector(".sidebar"), h1: (document.querySelector("h1")||{}).textContent })` });
  console.log("  probe:", JSON.stringify(probe.result.value));

  if (name === "map") {
    // Панель справа пуста, пока не выбран навык, и подсказка тогда висит
    // дважды. Настоящий клик по карточке — не dispatchEvent: атлас ловит
    // указатель, и синтетическое событие мимо hit-testing до него не доходит.
    const spot = await send("Runtime.evaluate", { returnByValue: true, expression: `(() => {
      const cards = [...document.querySelectorAll(".atlas-card")].map(c => {
        const r = c.getBoundingClientRect();
        return { x: r.left + r.width/2, y: r.top + r.height/2, w: r.width, h: r.height };
      }).filter(r => r.w > 20 && r.x > 380 && r.x < innerWidth * 0.55 && r.y > 220 && r.y < innerHeight - 180);
      if (!cards.length) return null;
      cards.sort((a, b) => a.y - b.y || a.x - b.x);
      const p = cards[Math.floor(cards.length * 0.4)];
      return { x: Math.round(p.x), y: Math.round(p.y), n: cards.length };
    })()` });
    const s2 = spot.result.value;
    console.log("  card:", JSON.stringify(s2));
    if (s2) {
      for (const type of ["mousePressed", "mouseReleased"]) {
        await send("Input.dispatchMouseEvent", { type, x: s2.x, y: s2.y, button: "left", clickCount: 1, buttons: type === "mousePressed" ? 1 : 0 });
        await sleep(80);
      }
      await sleep(900);
    }
  }
  const { data } = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  writeFileSync(`${OUT}/${name}-${THEME}.png`, Buffer.from(data, "base64"));
  console.log(name, THEME, "ok");
}

ws.close();
chrome.kill();
process.exit(0);
