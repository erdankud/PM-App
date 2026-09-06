/** Точка входа веб-клиента.
 *
 *  Корневых разделов ровно три, как в приложении: Карта, Прогресс, Профиль. Гейт
 *  открывается поверх всего — это отдельная работа, из которой не переключаются
 *  вкладками, ровно как `fullScreenCover` в iOS.
 */
import { h, fill } from "./dom.js";
import { initLanguage, onLanguageChange } from "./l10n.js";
import { session, ROUTE } from "./session.js";
import { route, resolve, currentPath, startRouter, navigate } from "./router.js";
import { loadingState } from "./components.js";
import { sidebar } from "./views/chrome.js";
import { welcomeView } from "./views/welcome.js";
import { onboardingView } from "./views/onboarding.js";
import { mapView } from "./views/map.js";
import { blockView } from "./views/block.js";
import { lessonView } from "./views/lesson.js";
import { exerciseView } from "./views/exercise.js";
import { glossaryView } from "./views/glossary.js";
import { challengeView } from "./views/challenge.js";
import { progressView } from "./views/progress.js";
import { historyView, resultView } from "./views/history.js";
import { profileView } from "./views/profile.js";

route("/map", mapView);
route("/block/:id", blockView);
route("/lesson/:id", lessonView);
route("/exercise/:id", exerciseView);
route("/glossary", glossaryView);
route("/gate/:gateId", challengeView);
route("/progress", progressView);
route("/history", historyView);
route("/history/:attemptId", resultView);
route("/profile", profileView);

const root = document.getElementById("root");
let mounted = null;
let renderedRoute = null;

function mount(node) {
  // Уходя с экрана, view может закрыть за собой: плеер отпускает файл,
  // профиль — подписку на сессию.
  mounted?.dispose?.();
  mounted = node;
  fill(root, node);
}

/** Профиль меняется чаще, чем маршрут: XP приходит после урока, уровень — после
 *  гейта. Пересобирать на это весь экран нельзя — под гейтом это выбросило бы
 *  человека из наполовину заполненной формы вместе с недосохранённым текстом.
 *  Пока корневой маршрут тот же, обновляется только боковая панель.
 *
 *  `force` — для смены языка: там пересобрать нужно всё, потому что и подписи, и
 *  контент приходят на другом языке.
 */
function render({ force = false } = {}) {
  if (!force && session.route === renderedRoute && session.route === ROUTE.main) {
    root.querySelector(".sidebar")?.replaceWith(sidebar());
    return;
  }
  renderedRoute = session.route;
  switch (session.route) {
    case ROUTE.launching:
      mount(h("div.page", loadingState()));
      return;
    case ROUTE.signedOut:
      mount(welcomeView());
      return;
    case ROUTE.onboarding:
      mount(onboardingView());
      return;
    default:
      renderMain();
  }
}

function renderMain() {
  const path = currentPath();
  const match = resolve(path);
  if (!match) {
    navigate("/map", { replace: true });
    return;
  }
  const view = match.view(match.params);
  // Гейт занимает экран целиком: боковая навигация в нём была бы приглашением
  // уйти из наполовину заполненной формы.
  if (path.startsWith("/gate/")) {
    mount(view);
    return;
  }
  mount(h("div.shell", sidebar(), h("main.main", view)));
}

initLanguage();
session.addEventListener("change", () => render());
// Язык меняет и подписи, и текст с сервера: экран строится заново целиком, и
// следующий запрос уже уходит с новым `X-Content-Language`.
onLanguageChange(() => render({ force: true }));
startRouter(() => {
  if (session.route === ROUTE.main) renderMain();
});

// Возврат во вкладку — повод перечитать профиль: XP и уровень могли измениться
// в приложении на телефоне.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") session.refreshProfile();
});

render();
session.bootstrap();
