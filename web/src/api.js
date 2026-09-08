/** Единственное место, которое разговаривает с сервером.
 *
 *  Зеркало `Core/Networking/APIClient.swift`: те же пути, те же заголовки, тот же
 *  разбор ошибок. Здесь, как и там, нет ни ключа провайдера, ни имени модели —
 *  оценка живёт только на сервере.
 */
import { S } from "./strings.js";
import { language } from "./l10n.js";

export const API_PREFIX = "/v1";

/** Ограничения формы ответа. Сервер проверяет их сам; клиент только не даёт
 *  отправить заведомо неподходящее. */
export const RATIONALE_MIN = 30;
export const RATIONALE_MAX = 600;
export const FEEDBACK_POLL_ATTEMPTS = 5;
export const FEEDBACK_POLL_INTERVAL_MS = 2000;

export class APIError extends Error {
  constructor(kind, { status = 0, code = null } = {}) {
    super(code || kind);
    this.kind = kind;
    this.status = status;
    this.code = code || kind;
  }

  get isRetryable() {
    return ["offline", "timed_out", "rate_limited", "unavailable", "server"].includes(this.kind);
  }

  /** Разбор один в один с `APIError.userMessage` в iOS. */
  get userMessage() {
    switch (this.kind) {
      case "offline":
        return S.Errors.offline;
      case "timed_out":
        return S.Errors.timedOut;
      case "unauthorized":
        return this.code === "invalid_credentials"
          ? S.Auth.invalidCredentials
          : S.Errors.unauthorized;
      case "forbidden":
      case "not_found":
        return S.Errors.notAvailable;
      case "conflict":
        if (this.code === "email_taken") return S.Auth.emailTaken;
        return this.code === "onboarding_incomplete"
          ? S.Errors.onboardingIncomplete
          : S.Errors.alreadySubmitted;
      case "validation":
        // 422 на форме входа — это адрес или короткий пароль; общее «что-то не так»
        // здесь бесполезно, человеку надо знать, какое поле чинить.
        if (this.code === "signup_invalid") return S.Auth.emailInvalid;
        if (this.code === "no_evidence_reviewed") return S.Errors.noEvidenceReviewed;
        if (this.code === "rationale_length_invalid") {
          return S.Errors.rationaleLength(RATIONALE_MIN, RATIONALE_MAX);
        }
        return S.Errors.invalidSubmission;
      case "rate_limited":
        return S.Errors.rateLimited;
      case "unavailable":
        if (this.code === "google_not_configured") return S.Auth.googleUnavailable;
        return this.code === "no_scenario_available"
          ? S.Errors.noScenarioAvailable
          : S.Errors.serverProblem;
      case "server":
        return S.Errors.serverProblem;
      default:
        return S.Errors.unexpectedResponse;
    }
  }
}

function errorFor(status, code) {
  switch (status) {
    case 401:
      return new APIError("unauthorized", { status, code });
    case 403:
      return new APIError("forbidden", { status, code });
    case 404:
      return new APIError("not_found", { status, code });
    case 409:
      return new APIError("conflict", { status, code });
    case 422:
      return new APIError("validation", { status, code });
    case 429:
      return new APIError("rate_limited", { status, code });
    case 503:
      return new APIError("unavailable", { status, code });
    default:
      return new APIError("server", { status, code: code || `http_${status}` });
  }
}

export class APIClient {
  /** `tokenProvider` реализует SessionStore: он же умеет обновлять токен. */
  constructor({ baseURL = "" } = {}) {
    this.baseURL = baseURL;
    this.tokenProvider = null;
  }

  attach(tokenProvider) {
    this.tokenProvider = tokenProvider;
  }

  async request(method, path, { query, body, headers = {}, authenticated = true, retry = true } = {}) {
    const url = new URL(this.baseURL + API_PREFIX + path, window.location.origin);
    for (const [key, value] of Object.entries(query || {})) {
      if (value !== null && value !== undefined && value !== "") url.searchParams.set(key, value);
    }

    const requestHeaders = {
      Accept: "application/json",
      // Осознанно не `Accept-Language`: браузер выставляет его из системной локали,
      // и она молча перебила бы язык, выбранный в приложении. Долговременное
      // предпочтение хранится в профиле — его читает воркер, когда пишет разбор.
      "X-Content-Language": language(),
      ...headers,
    };
    if (body !== undefined) requestHeaders["Content-Type"] = "application/json";
    if (authenticated) {
      const token = await this.tokenProvider?.currentAccessToken();
      if (token) requestHeaders.Authorization = `Bearer ${token}`;
    }

    let response;
    try {
      response = await fetch(url, {
        method,
        headers: requestHeaders,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(45000),
      });
    } catch (error) {
      if (error.name === "TimeoutError") throw new APIError("timed_out");
      throw new APIError("offline");
    }

    if (response.status === 401 && authenticated && retry) {
      const refreshed = await this.tokenProvider?.refreshAccessToken();
      if (refreshed) {
        return this.request(method, path, { query, body, headers, authenticated, retry: false });
      }
      await this.tokenProvider?.handleAuthenticationFailure();
      throw new APIError("unauthorized", { status: 401 });
    }

    if (!response.ok) throw errorFor(response.status, await codeOf(response));
    if (response.status === 204) return null;

    try {
      return await response.json();
    } catch {
      throw new APIError("decoding");
    }
  }

  get = (path, options) => this.request("GET", path, options);
  post = (path, options) => this.request("POST", path, options);
  put = (path, options) => this.request("PUT", path, options);
  patch = (path, options) => this.request("PATCH", path, options);
  del = (path, options) => this.request("DELETE", path, options);

  // --- Auth ---------------------------------------------------------------

  authMethods() {
    return this.get("/auth/methods", { authenticated: false });
  }

  signUp(email, password, timezone) {
    return this.post("/auth/signup", {
      body: { email, password, timezone },
      authenticated: false,
    });
  }

  signInWithPassword(email, password, timezone) {
    return this.post("/auth/signin", {
      body: { email, password, timezone },
      authenticated: false,
    });
  }

  signInWithGoogle(idToken, timezone) {
    return this.post("/auth/google", { body: { idToken, timezone }, authenticated: false });
  }

  signInDeveloper(deviceId, timezone) {
    return this.post("/auth/dev", { body: { deviceId, timezone }, authenticated: false });
  }

  signInWithApple(identityToken, timezone) {
    return this.post("/auth/apple", { body: { identityToken, timezone }, authenticated: false });
  }

  refresh(refreshToken) {
    return this.post("/auth/refresh", { body: { refreshToken }, authenticated: false, retry: false });
  }

  signOut(refreshToken) {
    return this.post("/auth/signout", { body: { refreshToken } });
  }

  // --- Профиль ------------------------------------------------------------

  me = () => this.get("/me");
  updateProfile = (body) => this.patch("/me/profile", { body });
  deleteAccount = () => this.del("/me");

  // --- Карта, блоки, уроки -------------------------------------------------

  trees = () => this.get("/trees");
  tree = (kind = "product") => this.get(`/tree/${kind}`);
  /** Карта на уровне узлов: карточка — навык, а не блок. */
  treeMap = (kind = "product") => this.get(`/tree/${kind}/map`);
  block = (id) => this.get(`/blocks/${id}`);
  lesson = (id) => this.get(`/lessons/${id}`);
  completeLesson = (id) => this.post(`/lessons/${id}/complete`);
  generateAudio = (lessonId) => this.post(`/lessons/${lessonId}/audio/generate`);
  startGate = (id) => this.post(`/gates/${id}/start`);

  // --- Гейт ----------------------------------------------------------------

  saveDraft = (attemptId, body) => this.put(`/attempts/${attemptId}/draft`, { body });
  recordEvidence = (attemptId, evidenceCardId) =>
    this.post(`/attempts/${attemptId}/evidence`, { body: { evidenceCardId } });
  submit = (attemptId, body, idempotencyKey) =>
    this.post(`/attempts/${attemptId}/submit`, { body, headers: { "Idempotency-Key": idempotencyKey } });
  feedback = (attemptId) => this.get(`/attempts/${attemptId}/feedback`);
  retryFeedback = (attemptId) => this.post(`/attempts/${attemptId}/feedback/retry`);
  rateFeedback = (attemptId, rating) =>
    this.post(`/attempts/${attemptId}/feedback-rating`, { body: { rating } });

  // --- Прогресс ------------------------------------------------------------

  progress = () => this.get("/progress");
  history = (limit = 20, offset = 0) => this.get("/history", { query: { limit, offset } });

  // --- System Design -------------------------------------------------------

  glossary = (q, blockId) => this.get("/glossary", { query: { q, blockId } });
  exercise = (id) => this.get(`/exercises/${id}`);
  submitExercise = (id, values) => this.post(`/exercises/${id}/submit`, { body: { values } });

  // --- Аналитика -----------------------------------------------------------

  sendEvents = (events) => this.post("/events", { body: { events } });

  /** Аудио закрыто тем же Bearer-токеном, что и остальное, поэтому `<audio src>`
   *  его не получит: файл берётся запросом и подставляется как blob. Заодно это
   *  значит, что перемотка идёт по уже скачанному, без Range-запросов. */
  async audioBlobURL(path) {
    const token = await this.tokenProvider?.currentAccessToken();
    const response = await fetch(new URL(this.baseURL + path, window.location.origin), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw errorFor(response.status, await codeOf(response));
    return URL.createObjectURL(await response.blob());
  }
}

async function codeOf(response) {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    return detail?.code ?? null;
  } catch {
    return null;
  }
}

export const api = new APIClient();
