/** Гейт: ситуация с неполными данными.
 *
 *  Зеркало `Features/Challenge/*`. Шаги: Ситуация → Изучить → Решить → Последствия
 *  → Разбор. Назад можно только между первыми тремя и только до отправки:
 *  отправленная попытка неизменна (спека §9).
 *
 *  Проверки формы здесь ровно те же, что в `ChallengeFormState`, и по той же
 *  причине: пока не открыт хотя бы один сигнал, решение недоступно (P0-06), а
 *  «Отправить» не включается без выбора и аргументации в 30–600 символов (P0-07).
 *  Сервер проверяет это заново — клиент лишь не даёт отправить заведомо негодное.
 */
import { h, fill, debounce } from "../dom.js";
import { icon } from "../icons.js";
import {
  card, chip, button, notice, sectionHeader, progressTrack, scoreHeadline,
  loadingState, errorState, confirmDialog,
} from "../components.js";
import { S } from "../strings.js";
import { api, RATIONALE_MIN, RATIONALE_MAX, FEEDBACK_POLL_ATTEMPTS, FEEDBACK_POLL_INTERVAL_MS } from "../api.js";
import { navigate, up } from "../router.js";

const STEPS = ["brief", "investigate", "decide", "consequence", "feedback"];

const EVIDENCE_SYMBOL = {
  quantitative: "chart.bar",
  qualitative: "quote.bubble",
  technical: "wrench.and.screwdriver",
  business: "briefcase",
};

/** Ключ идемпотентности живёт столько же, сколько попытка: повтор отправки после
 *  обрыва сети не должен создать вторую попытку. */
function idempotencyKey(attemptId) {
  const key = `pmcoach.idempotency.${attemptId}`;
  try {
    let value = localStorage.getItem(key);
    if (!value) {
      value = crypto.randomUUID();
      localStorage.setItem(key, value);
    }
    return value;
  } catch {
    return crypto.randomUUID();
  }
}

export function challengeView({ gateId }) {
  const node = h("div.fullscreen");
  let challenge = null;
  let error = null;
  let submissionError = null;
  let consequence = null;
  let feedback = null;
  let rating = null;
  let step = "brief";
  let submitted = false;
  let submitting = false;
  let polling = false;
  let draftSaved = false;
  let offlineDraft = false;
  let pollHandle = null;

  const form = {
    reviewed: new Set(),
    selectedOptionId: null,
    rationale: "",
  };
  const expanded = new Set();

  node.dispose = () => clearTimeout(pollHandle);

  const scenario = () => challenge?.scenario;
  const attemptId = () => challenge?.attempt.attemptId;

  // --- Загрузка ------------------------------------------------------------

  const load = async () => {
    try {
      // Повторный вход в гейт возвращает ту же открытую попытку.
      challenge = await api.startGate(gateId);
      form.reviewed = new Set(challenge.attempt.reviewedEvidenceIds);
      form.selectedOptionId = challenge.attempt.selectedOptionId;
      form.rationale = challenge.attempt.rationale || "";
      submitted = challenge.state !== "not_started" && challenge.state !== "in_progress";
      step = stepFor(challenge.state);
      error = null;
      if (submitted) await refreshFeedback();
    } catch (apiError) {
      if (!challenge) error = apiError;
    }
    render();
  };

  /** Шаг восстанавливается из состояния сервера, а не из памяти клиента. */
  const stepFor = (state) => {
    switch (state) {
      case "submitted":
      case "awaiting_feedback":
      case "feedback_failed":
        return "consequence";
      case "complete":
        return "feedback";
      default:
        return "brief";
    }
  };

  // --- Черновик ------------------------------------------------------------

  const syncDraft = async () => {
    if (!attemptId() || submitted) return;
    try {
      await api.saveDraft(attemptId(), {
        selectedOptionId: form.selectedOptionId,
        rationale: form.rationale,
        clientUpdatedAt: new Date().toISOString(),
      });
      draftSaved = true;
      offlineDraft = false;
    } catch {
      offlineDraft = true;
    }
    paintDraftStatus();
  };

  /** Пока человек печатает, синхронизация не мешает: отложенная запись, а на
   *  смену варианта — сразу. */
  const scheduledSync = debounce(syncDraft, 700);

  const openEvidence = (cardId) => {
    if (form.reviewed.has(cardId)) return;
    form.reviewed.add(cardId);
    api.recordEvidence(attemptId(), cardId).catch(() => {});
  };

  // --- Проверки формы ------------------------------------------------------

  const trimmed = () => form.rationale.trim();
  const canAdvanceToDecision = () => form.reviewed.size >= 1;
  const hasValidOption = () =>
    !!form.selectedOptionId &&
    scenario().decisionOptions.some((option) => option.id === form.selectedOptionId);
  const isRationaleValid = () =>
    trimmed().length >= RATIONALE_MIN && trimmed().length <= RATIONALE_MAX;
  const canSubmit = () => !submitted && hasValidOption() && isRationaleValid();
  const hasDraftProgress = () =>
    !!form.selectedOptionId || trimmed().length > 0 || form.reviewed.size > 0;

  const rationaleMessage = () => {
    const count = trimmed().length;
    if (count === 0) return null;
    if (count < RATIONALE_MIN) return S.Challenge.charactersToGo(RATIONALE_MIN - count);
    if (count > RATIONALE_MAX) return S.Challenge.charactersOver(count - RATIONALE_MAX);
    return null;
  };

  // --- Отправка ------------------------------------------------------------

  const submit = async () => {
    if (!canSubmit() || submitting) return;
    submitting = true;
    submissionError = null;
    scheduledSync.cancel();
    render();
    try {
      const response = await api.submit(
        attemptId(),
        { selectedOptionId: form.selectedOptionId, rationale: trimmed() },
        idempotencyKey(attemptId())
      );
      consequence = response.consequence;
      submitted = true;
      step = "consequence";
      startPolling();
    } catch (apiError) {
      submissionError = apiError;
    } finally {
      submitting = false;
      render();
    }
  };

  /** Опрос ограничен по числу попыток, дальше — состояние, с которым можно
   *  что-то сделать. Бесконечного спиннера не бывает (спека §16). */
  const startPolling = () => {
    clearTimeout(pollHandle);
    polling = true;
    let attempt = 0;
    const tick = async () => {
      attempt += 1;
      await refreshFeedback();
      if (feedback?.status !== "pending" || attempt >= FEEDBACK_POLL_ATTEMPTS) {
        polling = false;
        render();
        return;
      }
      pollHandle = setTimeout(tick, FEEDBACK_POLL_INTERVAL_MS);
      render();
    };
    tick();
  };

  const refreshFeedback = async () => {
    if (!attemptId()) return;
    try {
      const response = await api.feedback(attemptId());
      feedback = response;
      consequence = response.consequence;
      rating = response.rating;
    } catch {
      /* оставляем то, что уже на экране */
    }
  };

  const retryCoaching = async () => {
    polling = true;
    render();
    try {
      feedback = await api.retryFeedback(attemptId());
    } catch {
      /* состояние покажет опрос */
    }
    startPolling();
  };

  const rate = async (value) => {
    rating = value;
    render();
    api.rateFeedback(attemptId(), value).catch(() => {});
  };

  // --- Выход ---------------------------------------------------------------

  const close = async () => {
    if (submitted || !hasDraftProgress()) {
      scheduledSync.cancel();
      leave();
      return;
    }
    const confirmed = await confirmDialog({
      title: S.Challenge.leaveTitle,
      message: S.Challenge.leaveMessage,
      confirmTitle: S.Challenge.saveAndLeave,
    });
    if (confirmed) {
      await syncDraft();
      leave();
    }
  };

  const leave = () => {
    clearTimeout(pollHandle);
    if (challenge) navigate(`/block/${challenge.blockId}`, { replace: true });
    else up("/learn");
  };

  // --- Отрисовка -----------------------------------------------------------

  const render = () => {
    if (!challenge && error) {
      fill(node, errorState(S.Common.couldntLoad, error.userMessage, load));
      return;
    }
    if (!challenge) {
      fill(node, loadingState(S.Challenge.loadingScenario));
      return;
    }

    fill(
      node,
      bar(),
      h("div.scroll", h("div.page", body())),
      h("div.footer", h("div.inner", footer()))
    );
  };

  const bar = () =>
    h(
      "div.bar",
      h(
        "div.inner.row",
        button(submitted ? S.Common.done : S.Common.close, close, { variant: "quiet" }),
        h("div.grow.row", { style: { justifyContent: "center" } }, stepBar()),
        h("span.caption.tertiary", challenge.blockTitle)
      )
    );

  const stepBar = () =>
    h(
      "div.gate-steps",
      { style: { width: "160px" }, "aria-label": S.Challenge.stepProgress(STEPS.indexOf(step) + 1, STEPS.length) },
      STEPS.map((name, index) => h(`div.step${index <= STEPS.indexOf(step) ? ".done" : ""}`))
    );

  const body = () => {
    switch (step) {
      case "brief":
        return briefStep();
      case "investigate":
        return investigateStep();
      case "decide":
        return decideStep();
      case "consequence":
        return consequenceStep();
      default:
        return feedbackStep();
    }
  };

  // Ситуация. Ни подсказок про оценку, ни вариантов ответа на этом экране.
  const briefStep = () => {
    const view = scenario();
    const rows = [
      [S.Challenge.yourRole, view.brief.role, "person.crop.circle"],
      [S.Challenge.theCompany, view.brief.company, "building.2"],
      [S.Challenge.whatsHappening, view.brief.context, "doc.text"],
      [S.Challenge.theObjective, view.brief.objective, "scope"],
      [S.Challenge.constraints, view.brief.constraints, "lock"],
      [S.Challenge.yourTask, view.brief.task, "checkmark.circle.fill"],
    ];
    return h(
      "div.stack.xl",
      h(
        "div.stack.s",
        h(
          "div.row.wrap",
          chip(S.Labels.level(view.level), { symbol: "chart.bar" }),
          chip(S.Labels.skill(view.primarySkill, view.primarySkillLabel), { symbol: "scope", tone: "accent" }),
          chip(S.Common.minutes(view.estimatedMinutes), { symbol: "clock" })
        ),
        h("h1", view.title)
      ),
      rows.map(([title, text, symbol]) =>
        h(
          "div.stack.s",
          h("div.row.caption.muted", { style: { fontWeight: "600" } }, icon(symbol, { size: 13 }), title),
          h("p.text", text)
        )
      ),
      card(
        [
          h("div.caption", { style: { color: "var(--accent)", fontWeight: "600" } }, S.Challenge.whatGoodLooksLike),
          h("p.small", { style: { marginTop: "6px" } }, view.brief.whatGoodLooksLike),
        ],
        { highlighted: true }
      )
    );
  };

  // Изучить. Карточки закрыты; открытие отмечает сигнал изученным.
  const investigateStep = () => {
    const view = scenario();
    return h(
      "div.stack.l",
      h(
        "div.stack.s",
        h("h2", S.Challenge.investigatePrompt),
        h("p.muted", S.Challenge.evidenceCounter(form.reviewed.size, view.evidenceCards.length))
      ),
      view.evidenceCards.map(evidenceCard),
      notice(S.Challenge.partialEvidenceNotice)
    );
  };

  const evidenceCard = (item) => {
    const isOpen = expanded.has(item.id);
    const reviewed = form.reviewed.has(item.id);
    return h(
      `div.evidence${isOpen ? ".open" : ""}`,
      h(
        "button.head",
        {
          type: "button",
          "aria-expanded": isOpen ? "true" : "false",
          onclick: () => {
            if (isOpen) expanded.delete(item.id);
            else {
              expanded.add(item.id);
              openEvidence(item.id);
            }
            render();
          },
        },
        icon(EVIDENCE_SYMBOL[item.type] || "doc.text", { size: 20 }),
        h(
          "span.grow",
          h("span", { style: { display: "block", fontWeight: "600" } }, item.title),
          h("span.caption.tertiary", S.Labels.evidenceType(item.type))
        ),
        reviewed && chip(S.Challenge.reviewed, { symbol: "checkmark", tone: "positive" }),
        icon("chevron.down", { size: 14, className: "chevron" })
      ),
      isOpen && h("div.body", item.content)
    );
  };

  // Решить и обосновать.
  const decideStep = () => {
    const view = scenario();
    return h(
      "div.stack.xl",
      h("div.stack.s", h("h2", view.decisionPrompt), h("p.muted", S.Challenge.severalAnswers)),
      h("div.stack", view.decisionOptions.map(optionCard)),
      rationaleSection(),
      submissionError && notice(submissionError.userMessage, { symbol: "exclamationmark.circle", tone: "negative" }),
      draftStatus()
    );
  };

  const optionCard = (option) =>
    h(
      `button.option${form.selectedOptionId === option.id ? ".selected" : ""}`,
      {
        type: "button",
        "aria-pressed": form.selectedOptionId === option.id ? "true" : "false",
        onclick: () => {
          form.selectedOptionId = option.id;
          syncDraft();
          render();
        },
      },
      icon(form.selectedOptionId === option.id ? "largecircle.fill.circle" : "circle", { size: 20 }),
      h("span.grow", h("span.label", { style: { display: "block" } }, option.label), h("span.description", option.description))
    );

  const rationaleSection = () => {
    const counter = h("span.caption.tertiary.mono", `${form.rationale.length}/${RATIONALE_MAX}`);
    const message = h("span.caption");
    const paint = () => {
      counter.textContent = `${form.rationale.length}/${RATIONALE_MAX}`;
      const problem = rationaleMessage();
      fill(message, problem ? h("span", { style: { color: "var(--caution)" } }, problem) : null);
      if (!problem && isRationaleValid()) {
        fill(message, h("span.row", { style: { color: "var(--positive)" } }, icon("checkmark", { size: 12 }), S.Challenge.longEnough));
      }
      submitControl.disabled = !canSubmit() || submitting;
    };

    const textarea = h("textarea", {
      rows: 7,
      maxlength: String(RATIONALE_MAX),
      placeholder: S.Challenge.rationalePlaceholder,
      "aria-label": S.Challenge.yourReasoning,
      value: form.rationale,
      oninput: (event) => {
        form.rationale = event.target.value.slice(0, RATIONALE_MAX);
        paint();
        scheduledSync();
      },
    });

    queueMicrotask(paint);
    return h(
      "div.stack.s",
      h("h3", S.Challenge.defendYourDecision),
      textarea,
      h("div.row", message, h("div.grow"), counter)
    );
  };

  const draftStatusNode = h("div");
  const paintDraftStatus = () => {
    fill(
      draftStatusNode,
      offlineDraft
        ? notice(S.Challenge.offlineDraft, { symbol: "wifi.slash", tone: "caution" })
        : draftSaved
          ? notice(S.Challenge.saved, { symbol: "checkmark.circle.fill", tone: "positive" })
          : null
    );
  };
  const draftStatus = () => {
    paintDraftStatus();
    return draftStatusNode;
  };

  // Последствия. Текст авторский и приезжает вместе с отправкой, поэтому он
  // никогда не зависит от доступности оценщика.
  const consequenceStep = () =>
    h(
      "div.stack.xl",
      consequence
        ? h(
            "div.stack.l",
            h("div.stack.s", h("p.caption.muted", { style: { fontWeight: "600" } }, S.Challenge.youChose), h("h2", consequence.optionLabel)),
            card(
              [
                h(
                  "div.row.caption",
                  { style: { color: "var(--accent)", fontWeight: "600" } },
                  icon("arrow.turn.down.right", { size: 13 }),
                  S.Challenge.whatHappensNext
                ),
                h("p.text", { style: { marginTop: "8px" } }, consequence.text),
              ],
              { highlighted: true }
            )
          )
        : loadingState(S.Challenge.loadingOutcome),
      feedbackStatusNotice()
    );

  const feedbackStatus = () => feedback?.status ?? "pending";

  const feedbackStatusNotice = () => {
    switch (feedbackStatus()) {
      case "complete":
        return notice(S.Challenge.coachingReady, { symbol: "checkmark.circle.fill", tone: "positive" });
      case "failed":
        return notice(S.Challenge.coachingFailedNotice, { symbol: "exclamationmark.triangle", tone: "caution" });
      default:
        return notice(S.Challenge.coachingPending, { symbol: "hourglass" });
    }
  };

  // Разбор. Ничего здесь не считается на клиенте: если у сервера нет проверенной
  // оценки, экран так и говорит.
  const feedbackStep = () => {
    const body_ = feedback?.feedback;
    if (!body_) return unavailableFeedback();

    return h(
      "div.stack.xl",
      card(
        [
          scoreHeadline(body_.score, body_.band),
          body_.xpAwarded > 0 &&
            h("div", { style: { marginTop: "12px" } }, chip(S.Challenge.xpAwarded(body_.xpAwarded), { symbol: "sparkles", tone: "accent" })),
          h("div.stack.s", { style: { marginTop: "16px" } }, breakdownRows(body_.breakdown)),
        ],
        { highlighted: true }
      ),
      body_.needsRetry && notice(S.Challenge.needsRetryNotice, { symbol: "info.circle", tone: "caution" }),
      pointsSection(S.Challenge.strengthsTitle, "checkmark.seal", body_.strengths),
      pointsSection(S.Challenge.improvementsTitle, "arrow.up.forward", body_.improvements),
      h("div.stack", sectionHeader(S.Challenge.sharperApproach), card(h("p.text", body_.sharperApproach))),
      skillImpact(body_.skillImpact),
      remediation(),
      ratingSection(),
      notice(S.Challenge.practiceSignalDisclaimer)
    );
  };

  const breakdownRows = (breakdown) => {
    const rows = [
      [S.Labels.Breakdown.evidence, breakdown.evidence, breakdown.evidenceMax],
      [S.Labels.Breakdown.decision, breakdown.decision, breakdown.decisionMax],
      [S.Labels.Breakdown.rationale, breakdown.rationale, breakdown.rationaleMax],
      [S.Labels.Breakdown.communication, breakdown.communication, breakdown.communicationMax],
    ];
    return rows.map(([label, value, max]) =>
      h(
        "div.stack.s",
        h("div.row", h("span.caption.muted.grow", label), h("span.caption.mono", `${value}/${max}`)),
        progressTrack(max > 0 ? value / max : 0, { thin: true })
      )
    );
  };

  const pointsSection = (title, symbol, points) => {
    if (!points?.length) return null;
    return h(
      "div.stack",
      sectionHeader(title),
      points.map((point) =>
        card(
          h(
            "div.row.top",
            icon(symbol, { size: 16 }),
            h("div", h("h3", point.title), h("p.small.muted", { style: { marginTop: "4px" } }, point.detail))
          )
        )
      )
    );
  };

  const skillImpact = (impacts) => {
    if (!impacts?.length) return null;
    return h(
      "div.stack",
      sectionHeader(S.Challenge.skillImpactTitle, S.Challenge.skillImpactSubtitle),
      card(
        h(
          "div.stack.s",
          impacts.map((impact) =>
            h(
              "div.row",
              h("span.grow", S.Labels.skill(impact.key, impact.label)),
              h(
                "span.mono",
                { style: { fontWeight: "600", color: impact.delta >= 0 ? "var(--positive)" : "var(--caution)" } },
                impact.delta > 0 ? `+${impact.delta}` : String(impact.delta)
              ),
              h("span.row.muted", icon("arrow.right", { size: 12 }), h("span.mono", String(impact.score)))
            )
          )
        )
      )
    );
  };

  /** Провал — это информация: XP не отбирают, ничего не закрывается, а в ответе
   *  приходят конкретные уроки, к которым стоит вернуться. */
  const remediation = () => {
    if (!feedback?.remediation?.length) return null;
    return h(
      "div.stack",
      sectionHeader(S.Challenge.remediationTitle),
      h(
        "div.stack.s",
        feedback.remediation.map((link) =>
          h(
            "button.rowlink.card.tight",
            { type: "button", onclick: () => { leave(); navigate(`/lesson/${link.lessonId}`); } },
            icon("book", { size: 16 }),
            h("span.grow", h("span.title", { style: { display: "block" } }, link.lessonTitle), h("span.caption.tertiary", link.gap)),
            icon("chevron.right", { size: 13, className: "tertiary" })
          )
        )
      )
    );
  };

  const ratingSection = () =>
    h(
      "div.stack",
      sectionHeader(S.Challenge.wasThisUseful),
      h(
        "div.row",
        button(S.Challenge.useful, () => rate("useful"), {
          symbol: "hand.thumbsup",
          variant: rating === "useful" ? "" : "secondary",
        }),
        button(S.Challenge.notUseful, () => rate("not_useful"), {
          symbol: "hand.thumbsdown",
          variant: rating === "not_useful" ? "" : "secondary",
        })
      ),
      rating && notice(S.Challenge.ratingThanks)
    );

  const unavailableFeedback = () =>
    h(
      "div.stack.xl",
      consequence &&
        card([
          h(
            "div.row.caption",
            { style: { color: "var(--accent)", fontWeight: "600" } },
            icon("arrow.turn.down.right", { size: 13 }),
            S.Challenge.whatHappensNext
          ),
          h("p.text", { style: { marginTop: "8px" } }, consequence.text),
        ]),
      card([
        h(
          "div.row",
          icon("hourglass", { size: 16 }),
          h("h3", feedbackStatus() === "failed" ? S.Challenge.coachingDidntFinish : S.Challenge.coachingTakingLonger)
        ),
        h("p.small.muted", { style: { marginTop: "8px" } }, S.Challenge.unavailableBody),
        h("div", { style: { marginTop: "12px" } }, button(S.Challenge.retryCoaching, retryCoaching, { variant: "secondary", symbol: "arrow.clockwise" })),
      ])
    );

  // --- Нижняя панель --------------------------------------------------------

  let submitControl = button("", () => {});

  const footer = () => {
    switch (step) {
      case "brief":
        return button(S.Challenge.investigatePrompt, () => go("investigate"), { symbol: "magnifyingglass", wide: true });

      case "investigate":
        return h(
          "div.stack.s",
          !canAdvanceToDecision() && notice(S.Challenge.openOneSignal, { symbol: "hand.tap" }),
          h(
            "div.row",
            button(S.Common.back, () => go("brief"), { variant: "secondary", symbol: "chevron.left" }),
            h("div.grow", button(S.Challenge.makeADecision, () => go("decide"), { disabled: !canAdvanceToDecision(), wide: true }))
          )
        );

      case "decide":
        submitControl = button(S.Challenge.submitDecision, submit, { disabled: !canSubmit(), wide: true });
        if (submitting) submitControl.setLoading(true);
        return h(
          "div.stack.s",
          h("p.caption.tertiary", { style: { textAlign: "center" } }, S.Challenge.reasoningNotOptionNote),
          h(
            "div.row",
            button(S.Common.back, () => go("investigate"), { variant: "secondary", symbol: "chevron.left" }),
            h("div.grow", submitControl)
          )
        );

      case "consequence": {
        const status = feedbackStatus();
        const title =
          status === "complete"
            ? S.Challenge.seeCoaching
            : status === "failed"
              ? S.Challenge.retryCoaching
              : polling
                ? S.Challenge.preparingCoaching
                : S.Challenge.checkAgain;
        return button(
          title,
          () => {
            if (status === "failed") retryCoaching();
            else if (status === "complete") go("feedback");
            else startPolling();
          },
          { wide: true, disabled: polling && status === "pending" }
        );
      }

      default:
        return button(S.Challenge.finish, leave, { wide: true });
    }
  };

  const go = (next) => {
    step = next;
    if (next === "feedback") refreshFeedback().then(render);
    render();
    node.querySelector(".scroll")?.scrollTo({ top: 0 });
  };

  render();
  load();
  return node;
}
