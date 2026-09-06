/** Плеер аудиообзора урока: одна строка над текстом, а не отдельный экран.
 *
 *  Урок можно читать и слушать одновременно, поэтому плеер не забирает экран.
 *  Файл закрыт тем же токеном, что и остальное API, поэтому он скачивается
 *  запросом и подставляется как blob — заодно перемотка идёт по готовому файлу.
 */
import { h, fill } from "../dom.js";
import { icon } from "../icons.js";
import { S } from "../strings.js";
import { api } from "../api.js";

const RATES = [1, 1.25, 1.5, 1.75];

export function audioPlayer(audio, { lessonId, onReload }) {
  const node = h("div.player");
  const element = new Audio();
  let state = initialState(audio);
  let objectURL = null;

  element.addEventListener("timeupdate", () => paint());
  element.addEventListener("ended", () => paint());
  element.addEventListener("play", () => paint());
  element.addEventListener("pause", () => paint());

  node.teardown = () => {
    // Звук не переживает экран: уходя с урока, плеер останавливается и отпускает
    // файл, иначе вкладка держит десятки мегабайт до перезагрузки.
    element.pause();
    element.src = "";
    if (objectURL) URL.revokeObjectURL(objectURL);
  };

  const needsBuild = () => state === "buildable" || state === "buildFailed";

  const load = async () => {
    if (!audio?.url) return;
    state = "loading";
    paint();
    try {
      objectURL = await api.audioBlobURL(audio.url);
      element.src = objectURL;
      state = "ready";
    } catch {
      state = "failed";
    }
    paint();
  };

  const toggle = async () => {
    if (state === "idle" || state === "failed") {
      await load();
      if (state === "ready") element.play();
      return;
    }
    if (state !== "ready") return;
    if (element.paused) element.play();
    else element.pause();
  };

  /** Сборка занимает около минуты, поэтому это опрос, а не одно долгое ожидание:
   *  запрос, висящий минуту, оборвётся на первом же переключении сети. */
  const build = async () => {
    state = "building";
    paint();
    try {
      await api.generateAudio(lessonId);
    } catch {
      state = "buildFailed";
      paint();
      return;
    }
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      const fresh = await onReload();
      if (fresh?.available || fresh?.status === "failed") {
        audio = fresh;
        state = initialState(fresh);
        paint();
        return;
      }
    }
    state = "buildFailed";
    paint();
  };

  const caption = () => {
    switch (state) {
      case "buildable":
        return S.Lesson.audioSubtitle;
      case "building":
        return S.Lesson.audioBuilding;
      case "buildFailed":
        return S.Lesson.audioBuildFailed;
      case "loading":
        return S.Lesson.audioLoading;
      case "failed":
        return S.Lesson.audioFailed;
      case "ready":
        return `${time(element.currentTime)} / ${time(element.duration || audio?.durationSeconds || 0)}`;
      default:
        return audio?.durationSeconds
          ? `${S.Lesson.audioSubtitle} · ${time(audio.durationSeconds)}`
          : S.Lesson.audioSubtitle;
    }
  };

  const symbol = () => {
    if (state === "buildFailed") return "arrow.clockwise";
    if (needsBuild()) return "wand.and.stars";
    return element.paused ? "play.fill" : "pause.fill";
  };

  const paint = () => {
    const busy = state === "loading" || state === "building";
    fill(
      node,
      h(
        "div.row",
        h(
          "button.play",
          {
            type: "button",
            disabled: busy,
            "aria-label": needsBuild() ? S.Lesson.audioBuild : element.paused ? S.Lesson.audioPlay : S.Lesson.audioPause,
            onclick: () => (needsBuild() ? build() : toggle()),
          },
          busy ? h("span.spinner") : icon(symbol(), { size: 17 })
        ),
        h(
          "div.grow",
          h("div", { style: { fontWeight: "600" } }, needsBuild() ? S.Lesson.audioBuild : S.Lesson.audioTitle),
          h("div.caption.muted.mono", caption())
        ),
        state === "ready" && rateControl()
      ),
      state === "ready" && transport()
    );
  };

  const rateControl = () => {
    const select = h(
      "select",
      {
        style: { width: "auto" },
        "aria-label": S.Lesson.audioSpeed,
        onchange: (event) => {
          element.playbackRate = Number(event.target.value);
        },
      },
      RATES.map((rate) =>
        h("option", { value: String(rate), selected: element.playbackRate === rate }, `${rate}×`)
      )
    );
    return select;
  };

  const transport = () => {
    const duration = element.duration || audio?.durationSeconds || 1;
    return h(
      "div.transport",
      h(
        "button.skip",
        { type: "button", "aria-label": S.Lesson.audioBack15, onclick: () => (element.currentTime -= 15) },
        icon("gobackward.15", { size: 20 })
      ),
      h("input", {
        type: "range",
        min: "0",
        max: String(Math.max(duration, 1)),
        value: String(element.currentTime || 0),
        step: "1",
        "aria-label": S.Lesson.audioPosition,
        oninput: (event) => {
          element.currentTime = Number(event.target.value);
        },
      }),
      h(
        "button.skip",
        { type: "button", "aria-label": S.Lesson.audioForward15, onclick: () => (element.currentTime += 15) },
        icon("goforward.15", { size: 20 })
      )
    );
  };

  paint();
  return node;
}

/** `available == false` — это норма, а не сбой: файл собирается заранее скриптом,
 *  и урок без него просто не показывает плеер. */
export function initialState(audio) {
  if (!audio) return "unavailable";
  if (!audio.available || !audio.url) {
    if (audio.status === "generating") return "building";
    if (audio.status === "failed") return audio.canGenerate ? "buildFailed" : "unavailable";
    return audio.canGenerate ? "buildable" : "unavailable";
  }
  return "idle";
}

function time(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const total = Math.round(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}
