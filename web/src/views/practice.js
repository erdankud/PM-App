/** Practice — репетиционная.
 *
 *  Здесь не сдают и не набирают: ни XP, ни компетенций, ни открытых блоков.
 *  Задачу пишет модель в тот момент, когда её попросили: банка вопросов не
 *  заведена намеренно. Пятьдесят заготовленных задач кончаются, а заготовленную
 *  задачу второй человек уже видел в чужом разборе.
 *
 *  Содержимое — по-английски при любом языке интерфейса: собеседования на эти
 *  роли идут по-английски, и репетировать формулировку на одном языке, чтобы
 *  произносить её на другом, бессмысленно. Подписи вокруг остаются двуязычными —
 *  инструкция не то, что человек будет произносить.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { S } from "../strings.js";
import { api } from "../api.js";
import { navigate } from "../router.js";
import {
  button,
  chip,
  notice,
  sectionHeader,
  loadingState,
  errorState,
  confirmDialog,
} from "../components.js";
import { breadcrumb } from "./chrome.js";
import { revealOnScroll } from "../motion.js";

const DRAFT_PREFIX = "pmcoach.practice.";

/** Черновик живёт в браузере, а не на сервере: незаконченная мысль — не
 *  содержимое продукта, и отправлять её куда-то, чтобы она пережила F5, незачем. */
function readDraft(id) {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_PREFIX + id) || "{}");
  } catch {
    return {};
  }
}

function writeDraft(id, draft) {
  try {
    localStorage.setItem(DRAFT_PREFIX + id, JSON.stringify(draft));
  } catch {
    /* приватный режим */
  }
}

function dropDraft(id) {
  try {
    localStorage.removeItem(DRAFT_PREFIX + id);
  } catch {
    /* приватный режим */
  }
}

const barLabel = (bar) => (bar && S.Practice.Bar[bar]) || "";

function clock(seconds) {
  const total = Math.max(0, Math.round(seconds || 0));
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function shortDate(iso) {
  if (!iso) return "";
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString();
}

/** Ошибка провайдера здесь своя. Общее «что-то пошло не так» не говорит, что
 *  делать, а делать надо разное: подождать сутки или нажать ещё раз. */
function practiceError(apiError, fallback) {
  if (apiError?.status === 429) return S.Practice.limitReached;
  if (apiError?.status === 409) return S.Practice.notReady;
  return apiError?.status === 503 ? fallback : apiError?.userMessage || fallback;
}

/** Оба обращения к модели синхронные и идут десятки секунд. Крутящийся кружок
 *  без слов на таком отрезке — это место, где человек перезагружает страницу. */
function waiting(text) {
  return h("p.practice-waiting", h("span.spinner"), h("span", text));
}

// --- Список направлений ------------------------------------------------------

export function practiceView() {
  const node = h("div.page");
  let tracks = null;
  let sessions = null;
  let error = null;
  let message = null;
  let busy = null;

  const load = async () => {
    try {
      const [catalogue, saved] = await Promise.all([
        api.practiceTracks(),
        api.practiceSessions(),
      ]);
      tracks = catalogue.tracks;
      sessions = saved.sessions;
      error = null;
    } catch (apiError) {
      if (!tracks) error = apiError;
    }
    render();
  };

  const start = async (track) => {
    busy = track.id;
    message = null;
    render();
    try {
      const created = await api.practiceGenerate(track.id);
      navigate(`/practice/session/${created.id}`);
    } catch (apiError) {
      message = practiceError(apiError, S.Practice.generationFailed);
      busy = null;
      render();
    }
  };

  const trackCard = (track) => {
    const action = track.live
      ? button(track.sessionsTotal > 0 ? S.Practice.anotherTask : S.Practice.newTask, () => start(track), {
          arrow: true,
        })
      : null;
    if (action && busy) action.disabled = true;

    return h(
      `div.practice-card${track.live ? "" : ".preparing"}`,
      h(
        "div.practice-card-head",
        h("h2", track.title),
        track.live
          ? track.sessionsAnswered > 0 &&
              chip(S.Practice.sessionsSaved(track.sessionsAnswered), { symbol: "checkmark.seal" })
          : chip(S.Practice.inPreparation, { symbol: "hourglass" })
      ),
      h("p.practice-blurb", track.blurb),
      h(
        "dl.practice-facts",
        h("dt", S.Practice.tests),
        h("dd", track.tests),
        h("dt", S.Practice.format),
        h("dd", track.format)
      ),
      h(
        "div.practice-card-foot",
        busy === track.id ? waiting(S.Practice.writingTask) : action,
        track.live &&
          track.sessionsTotal > 0 &&
          h(
            "button.practice-link",
            { type: "button", onclick: () => navigate(`/practice/${track.id}`) },
            h("span", S.Practice.saved),
            icon("chevron.right", { size: 12 })
          )
      )
    );
  };

  const render = () => {
    const header = h("div.page-header", h("h1", S.Practice.title));
    if (error && !tracks) {
      fill(node, header, errorState(S.Common.couldntLoad, error.userMessage, load));
      return;
    }
    if (!tracks) {
      fill(node, header, loadingState());
      return;
    }

    fill(
      node,
      header,
      message && notice(message, { symbol: "exclamationmark.circle", tone: "caution" }),
      h("div.practice-grid", tracks.map(trackCard)),
      sessions && sessions.length ? savedSection(sessions, load) : null
    );
    revealOnScroll(node, { selector: ":scope > .practice-grid > *", stagger: 60 });
  };

  render();
  load();
  return node;
}

// --- Одно направление --------------------------------------------------------

export function practiceTrackView({ track: trackId }) {
  const node = h("div.page");
  let track = null;
  let sessions = null;
  let error = null;
  let message = null;
  let busy = false;

  const load = async () => {
    try {
      const [catalogue, saved] = await Promise.all([
        api.practiceTracks(),
        api.practiceSessions(trackId),
      ]);
      track = catalogue.tracks.find((item) => item.id === trackId) || null;
      sessions = saved.sessions;
      error = track ? null : error;
    } catch (apiError) {
      error = apiError;
    }
    render();
  };

  const start = async () => {
    busy = true;
    message = null;
    render();
    try {
      const created = await api.practiceGenerate(trackId);
      navigate(`/practice/session/${created.id}`);
    } catch (apiError) {
      message = practiceError(apiError, S.Practice.generationFailed);
      busy = false;
      render();
    }
  };

  const render = () => {
    const crumb = breadcrumb(S.Practice.backToTracks, "/practice");
    if (!track) {
      fill(
        node,
        crumb,
        error ? errorState(S.Common.couldntLoad, error.userMessage, load) : loadingState()
      );
      return;
    }

    fill(
      node,
      crumb,
      h("h1", track.title),
      h("p.section-lede", track.blurb),
      h(
        "div.row.wrap",
        chip(S.Common.minutes(track.targetMinutes), { symbol: "clock" }),
        chip(track.format, { symbol: "list.bullet.rectangle" })
      ),
      h("p.text.practice-track-tests", track.tests),
      message && notice(message, { symbol: "exclamationmark.circle", tone: "caution" }),
      track.live
        ? h(
            "div.row",
            busy ? waiting(S.Practice.writingTask) : button(S.Practice.newTask, start, { arrow: true })
          )
        : notice(S.Practice.notReady, { symbol: "hourglass" }),
      sessions && sessions.length
        ? savedSection(sessions, load)
        : h("p.small.muted", S.Practice.noSessions)
    );
  };

  render();
  load();
  return node;
}

// --- Сохранённые тренировки --------------------------------------------------

function savedSection(sessions, reload) {
  const wrapper = h("div.stack");

  const remove = async (session) => {
    const confirmed = await confirmDialog({
      title: S.Practice.deleteConfirm,
      message: session.title,
      confirmTitle: S.Practice.delete,
      destructive: true,
    });
    if (!confirmed) return;
    await api.deletePracticeSession(session.id);
    dropDraft(session.id);
    reload();
  };

  fill(
    wrapper,
    sectionHeader(S.Practice.saved, S.Practice.savedHint),
    h(
      "div.stack.s",
      sessions.map((session) =>
        h(
          "div.practice-row",
          h(
            "button.practice-row-open",
            { type: "button", onclick: () => navigate(`/practice/session/${session.id}`) },
            h("span.practice-row-title", session.title),
            h(
              "span.practice-row-meta",
              h("span", session.company),
              h("span.detail-dot", "·"),
              h("span", shortDate(session.answeredAt || session.createdAt))
            )
          ),
          session.status === "answered"
            ? chip(barLabel(session.bar) || S.Practice.reviewed, {
                symbol: "checkmark.seal",
                tone: "accent",
              })
            : chip(S.Practice.unanswered, { symbol: "clock" }),
          h(
            "button.practice-delete",
            {
              type: "button",
              title: S.Practice.delete,
              "aria-label": S.Practice.delete,
              onclick: () => remove(session),
            },
            icon("trash", { size: 15 })
          )
        )
      )
    )
  );
  return wrapper;
}

// --- Рабочее место -----------------------------------------------------------

export function practiceSessionView({ id }) {
  const node = h("div.page.practice-session");
  let session = null;
  let track = null;
  let error = null;
  let message = null;
  let busy = false;

  const draft = readDraft(id);
  const answers = draft.answers || {};
  const asked = new Set(draft.asked || []);
  let seconds = draft.seconds || 0;
  let ticker = null;

  const persist = () => writeDraft(id, { answers, asked: [...asked], seconds });

  const stopClock = () => {
    if (ticker) clearInterval(ticker);
    ticker = null;
  };

  const startClock = () => {
    if (ticker) return;
    ticker = setInterval(() => {
      seconds += 1;
      persist();
      const readout = node.querySelector(".practice-clock-value");
      if (readout) readout.textContent = clock(seconds);
    }, 1000);
  };

  // Интервал, переживший уход с экрана, продолжает тикать чужую тренировку.
  node.dispose = stopClock;

  const load = async () => {
    try {
      const [loaded, catalogue] = await Promise.all([
        api.practiceSession(id),
        api.practiceTracks(),
      ]);
      session = loaded;
      track = catalogue.tracks.find((item) => item.id === loaded.track) || null;
      error = null;
    } catch (apiError) {
      error = apiError;
    }
    render();
  };

  const submit = async () => {
    busy = true;
    message = null;
    stopClock();
    render();
    try {
      session = await api.practiceRespond(id, {
        answers,
        asked: [...asked],
        elapsedSeconds: Math.round(seconds),
      });
      dropDraft(id);
    } catch (apiError) {
      message = practiceError(apiError, S.Practice.feedbackFailed);
    }
    busy = false;
    render();
    // Разбор — это то, ради чего нажимали, а нажимали внизу длинной формы.
    // Оставить человека там же значит спрятать ответ, который он только что купил.
    if (session.status === "answered") window.scrollTo({ top: 0 });
  };

  const canvasField = (field) => {
    const value = answers[field.id] || "";
    const left = field.minChars - value.trim().length;
    const counter = h("span.practice-counter", left > 0 ? S.Practice.charactersLeft(left) : "");
    return h(
      "div.practice-field",
      h(
        "label.practice-field-label",
        h("span.practice-field-name", field.label),
        counter
      ),
      h("p.practice-field-hint", field.hint),
      h("textarea", {
        rows: field.rows,
        value,
        "aria-label": field.label,
        oninput: (event) => {
          answers[field.id] = event.target.value;
          persist();
          const remaining = field.minChars - event.target.value.trim().length;
          counter.textContent = remaining > 0 ? S.Practice.charactersLeft(remaining) : "";
        },
      })
    );
  };

  /** Ответ и замечание к нему — рядом. Разбор, собранный отдельным списком внизу,
   *  читается как приговор; рядом с собственной фразой — как правка. */
  const reviewedField = (field) => {
    const item = (session.feedback?.fields || []).find((entry) => entry.id === field.id);
    return h(
      "div.practice-field.reviewed",
      h(
        "div.practice-field-label",
        h("span.practice-field-name", field.label),
        item && h("span.practice-score", `${item.score}/5`)
      ),
      h("p.practice-answer", session.answers[field.id] || "—"),
      item && h("p.practice-note", item.note)
    );
  };

  const clarifiers = () => {
    const list = session.brief.clarifiers || [];
    if (!list.length) return null;
    return h(
      "div.practice-clarifiers",
      sectionHeader(S.Practice.clarifiers, S.Practice.clarifiersHint),
      list.map((item) => {
        const row = h("div.practice-clarifier", h("p.practice-clarifier-q", item.question));
        // Открывается только эта строка: перерисовка всего экрана вынула бы
        // курсор из поля, в котором человек в этот момент пишет.
        const reveal = () => {
          asked.add(item.question);
          persist();
          row.classList.add("open");
          row.lastChild.replaceWith(h("p.practice-clarifier-a", item.answer));
        };
        row.append(
          asked.has(item.question)
            ? h("p.practice-clarifier-a", item.answer)
            : h("button.practice-link", { type: "button", onclick: reveal }, S.Practice.ask)
        );
        if (asked.has(item.question)) row.classList.add("open");
        return row;
      })
    );
  };

  const brief = () =>
    h(
      "div.practice-brief",
      h(
        "div.row.wrap",
        chip(session.brief.kind, { symbol: "scope", tone: "accent" }),
        chip(session.brief.company, { symbol: "building.2" }),
        track && chip(S.Practice.target(track.targetMinutes), { symbol: "clock" })
      ),
      h("h1", session.brief.title),
      h("p.practice-context", session.brief.context),
      h("p.practice-prompt", session.brief.prompt),
      session.brief.constraints.length > 0 &&
        h(
          "div.practice-constraints",
          h("p.caption.tertiary", S.Practice.constraints),
          h("ul", session.brief.constraints.map((line) => h("li", line)))
        )
    );

  const bullets = (title, items, symbol) =>
    items.length > 0 &&
    h(
      "div.practice-bullets",
      h("p.caption.tertiary", title),
      h(
        "ul",
        items.map((item) =>
          h(
            "li",
            icon(symbol, { size: 14 }),
            h("span", h("strong", item.title), " — ", item.detail)
          )
        )
      )
    );

  const feedback = () =>
    h(
      "div.practice-feedback",
      h(
        "div.practice-feedback-head",
        chip(barLabel(session.feedback.bar), { symbol: "flag.checkered", tone: "accent" }),
        session.elapsedSeconds != null && chip(clock(session.elapsedSeconds), { symbol: "clock" })
      ),
      h("p.practice-headline", session.feedback.headline),
      bullets(S.Practice.strengths, session.feedback.strengths, "checkmark.circle.fill"),
      bullets(S.Practice.improvements, session.feedback.improvements, "arrow.up.right"),
      h(
        "div.practice-closers",
        h(
          "div.practice-closer",
          h("p.caption.tertiary", S.Practice.missedQuestion),
          h("p.text", session.feedback.missedQuestion)
        ),
        h(
          "div.practice-closer",
          h("p.caption.tertiary", S.Practice.sharperApproach),
          h("p.text", session.feedback.sharperApproach)
        )
      )
    );

  const workspace = () => {
    startClock();
    return h(
      "div.stack",
      clarifiers(),
      h(
        "div.practice-canvas",
        h(
          "div.practice-canvas-head",
          sectionHeader(S.Practice.yourAnswer),
          h(
            "div.practice-clock",
            { title: S.Practice.timeOnTask },
            icon("clock", { size: 13 }),
            h("span.practice-clock-value", clock(seconds))
          )
        ),
        track.canvas.map(canvasField)
      ),
      message && notice(message, { symbol: "exclamationmark.circle", tone: "caution" }),
      busy
        ? waiting(S.Practice.readingAnswer)
        : button(S.Practice.submit, submit, { wide: true, arrow: true })
    );
  };

  const reviewed = () =>
    h(
      "div.stack",
      feedback(),
      h(
        "div.practice-canvas",
        sectionHeader(S.Practice.byField, null),
        track.canvas.map(reviewedField)
      ),
      session.asked.length > 0 &&
        h(
          "div.practice-clarifiers",
          sectionHeader(S.Practice.clarifiers, null),
          session.asked.map((question) => h("p.practice-clarifier-q", question))
        )
    );

  const render = () => {
    const crumb = breadcrumb(S.Practice.title, "/practice");
    if (!session || !track) {
      fill(
        node,
        crumb,
        error ? errorState(S.Common.couldntLoad, error.userMessage, load) : loadingState()
      );
      return;
    }
    const answered = session.status === "answered" && session.feedback;
    if (answered) stopClock();
    fill(node, crumb, brief(), answered ? reviewed() : workspace());
  };

  render();
  load();
  return node;
}
