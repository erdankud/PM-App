/** Сессия: токены, профиль и корневой маршрут.
 *
 *  Зеркало `App/SessionStore.swift`. Ничего здесь не считает баллы, XP, уровень
 *  или доступность блока — это приезжает с сервера и только показывается.
 */
import { api, APIError } from "./api.js";
import { adoptLanguageFromServer, hasExplicitLanguage, language } from "./l10n.js";

const ACCESS_KEY = "pmcoach.accessToken";
const REFRESH_KEY = "pmcoach.refreshToken";
const DEVICE_KEY = "pmcoach.deviceId";

/** Токены живут в localStorage: у браузера нет Keychain, а httpOnly-cookie
 *  потребовала бы менять контракт сервера, который сейчас общий с iOS. */
function read(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* приватный режим */
  }
}

export function deviceIdentifier() {
  let id = read(DEVICE_KEY);
  if (!id) {
    id = `web-${crypto.randomUUID()}`;
    write(DEVICE_KEY, id);
  }
  return id;
}

const timezone = () => Intl.DateTimeFormat().resolvedOptions().timeZone;

export const ROUTE = {
  launching: "launching",
  signedOut: "signed_out",
  onboarding: "onboarding",
  main: "main",
};

class SessionStore extends EventTarget {
  constructor() {
    super();
    this.route = ROUTE.launching;
    this.me = null;
    this.authError = null;
    this.isAuthenticating = false;
    this.accessToken = read(ACCESS_KEY);
    this.refreshToken = read(REFRESH_KEY);
    this.refreshInFlight = null;
  }

  changed() {
    this.dispatchEvent(new CustomEvent("change"));
  }

  // --- TokenProviding ------------------------------------------------------

  async currentAccessToken() {
    return this.accessToken;
  }

  /** Обновление сворачивается в одну попытку: параллельные 401 не должны
   *  сжечь одноразовый refresh-токен по разу каждый. */
  async refreshAccessToken() {
    if (!this.refreshToken) return null;
    if (!this.refreshInFlight) {
      this.refreshInFlight = (async () => {
        try {
          const response = await api.refresh(this.refreshToken);
          this.store(response);
          return response.accessToken;
        } catch {
          return null;
        } finally {
          this.refreshInFlight = null;
        }
      })();
    }
    return this.refreshInFlight;
  }

  async handleAuthenticationFailure() {
    await this.clear();
  }

  // --- Запуск --------------------------------------------------------------

  async bootstrap() {
    if (!this.accessToken && !this.refreshToken) {
      this.route = ROUTE.signedOut;
      this.changed();
      return;
    }
    try {
      this.apply(await api.me());
    } catch (error) {
      if (error instanceof APIError && error.kind === "unauthorized") {
        await this.clear();
        return;
      }
      // Офлайн или сбой сервера при внешне валидных токенах: пускаем внутрь, а
      // экраны сами покажут своё состояние, вместо выброса на вход.
      this.route = ROUTE.main;
      this.changed();
    }
  }

  async refreshProfile() {
    if (this.route !== ROUTE.main && this.route !== ROUTE.onboarding) return;
    try {
      this.apply(await api.me());
    } catch {
      /* оставляем то, что на экране */
    }
  }

  // --- Вход ----------------------------------------------------------------

  async signInAsDeveloper() {
    await this.signIn(() => api.signInDeveloper(deviceIdentifier(), timezone()));
  }

  async signUp(email, password) {
    await this.signIn(() => api.signUp(email, password, timezone()));
  }

  async signInWithPassword(email, password) {
    await this.signIn(() => api.signInWithPassword(email, password, timezone()));
  }

  async signInWithGoogle(idToken) {
    await this.signIn(() => api.signInWithGoogle(idToken, timezone()));
  }

  async signInWithApple(identityToken) {
    await this.signIn(() => api.signInWithApple(identityToken, timezone()));
  }

  async signIn(operation) {
    this.isAuthenticating = true;
    this.authError = null;
    this.changed();
    try {
      const response = await operation();
      this.store(response);
      this.apply(response.user);
    } catch (error) {
      this.authError = error instanceof APIError ? error : new APIError("server");
    } finally {
      this.isAuthenticating = false;
      this.changed();
    }
  }

  store(response) {
    this.accessToken = response.accessToken;
    this.refreshToken = response.refreshToken;
    write(ACCESS_KEY, this.accessToken);
    write(REFRESH_KEY, this.refreshToken);
  }

  apply(profile) {
    this.me = profile;
    this.reconcileLanguage(profile);
    this.route = profile.onboardingStatus === "complete" ? ROUTE.main : ROUTE.onboarding;
    this.changed();
  }

  /** Аккаунт и устройство могут расходиться: язык выбрали до входа или на другом
   *  устройстве. Осознанный выбор здесь побеждает и уезжает наверх; иначе
   *  принимается предпочтение аккаунта. Серверную копию читает воркер, когда
   *  позже пишет разбор, поэтому оставлять её устаревшей нельзя. */
  reconcileLanguage(profile) {
    if (!hasExplicitLanguage()) {
      adoptLanguageFromServer(profile.language);
      return;
    }
    if (profile.language !== language()) this.pushLanguage(language());
  }

  pushLanguage(code) {
    api.updateProfile({ language: code }).catch(() => {});
  }

  async signOut() {
    try {
      await api.signOut(this.refreshToken);
    } catch {
      /* локальную сессию всё равно чистим */
    }
    await this.clear();
  }

  async deleteAccount() {
    await api.deleteAccount();
    await this.clear();
  }

  async clear() {
    this.accessToken = null;
    this.refreshToken = null;
    write(ACCESS_KEY, null);
    write(REFRESH_KEY, null);
    this.me = null;
    this.route = ROUTE.signedOut;
    this.changed();
  }
}

export const session = new SessionStore();
api.attach(session);
