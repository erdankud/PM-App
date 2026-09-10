/** Точка входа веб-клиента.
 *
 *  Корневых разделов пять: Уроки, Карта, Практика, Прогресс, Профиль. Гейт
 *  открывается поверх всего — это отдельная работа, из которой не переключаются
 *  вкладками, ровно как `fullScreenCover` в iOS.
 */
import { h, fill } from "./dom.js";
import { initLanguage, onLanguageChange } from "./l10n.js";
import { session, ROUTE } from "./session.js";
import { route, resolve, currentPath, startRouter, navigate } from "./router.js";
import { loadingState } from "./components.js";
import { S } from "./strings.js";
import { sidebar } from "./views/chrome.js";
import { welcomeView } from "./views/welcome.js";
import { onboardingView } from "./views/onboarding.js";
import { mapView } from "./views/map.js";
import { learnView } from "./views/learn.js";
import { blockView } from "./views/block.js";
import { lessonView } from "./views/lesson.js";
import { exerciseView } from "./views/exercise.js";
import { glossaryView } from "./views/glossary.js";
import { challengeView } from "./views/challenge.js";
import { practiceView, practiceTrackView, practiceSessionView } from "./views/practice.js";
import { progressView } from "./views/progress.js";
import { historyView, resultView } from "./views/history.js";
import { profileView } from "./views/profile.js";

route("/learn", learnView);
route("/map", mapView);
route("/block/:id", blockView);
route("/lesson/:id", lessonView);
route("/exercise/:id", exerciseView);
route("/glossary", glossaryView);
route("/gate/:gateId", challengeView);
route("/practice", practiceView);
route("/practice/session/:id", practiceSessionView);
route("/practice/:track", practiceTrackView);
route("/progress", progressView);
route("/history", historyView);
route("/history/:attemptId", resultView);
route("/profile", profileView);

const root = document.getElementById("root");
let mounted = null;
let renderedRoute = null;
let bootDismissed = false;

/** Экран загрузки из `index.html` уходит, когда на месте появляется экран.
 *
 *  Он висит с первого байта документа и потому единственный, кто вообще видим,
 *  пока едут модули. Прежняя заставка со счётчиком жила в модуле и появлялась
 *  уже после того, как ожидание кончилось, то есть добавляла к нему свои две
 *  секунды; здесь счёт кончается ровно тогда, когда есть что показать.
 */
function dismissBoot() {
  if (bootDismissed) return;
  bootDismissed = true;
  window.__pmBoot?.done();
}

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
      break;
    case ROUTE.onboarding:
      mount(onboardingView());
      break;
    default:
      // Маршрут мог не найтись — тогда экран ещё не построен, а идёт переход
      // на /learn, и снимать заставку рано: под ней пусто.
      if (!renderMain()) return;
  }
  dismissBoot();
}

function renderMain() {
  const path = currentPath();
  const match = resolve(path);
  if (!match) {
    navigate("/learn", { replace: true });
    return false;
  }
  const view = match.view(match.params);
  // Гейт занимает экран целиком: боковая навигация в нём была бы приглашением
  // уйти из наполовину заполненной формы.
  if (path.startsWith("/gate/")) {
    mount(view);
    return true;
  }
  mount(
    h(
      "div.shell",
      // Первая цель табуляции — вход в содержание мимо навигации.
      h("a.skip-link", { href: "#main" }, S.Common.skipToContent),
      sidebar(),
      h("main.main#main", { tabindex: "-1" }, view)
    )
  );
  return true;
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
