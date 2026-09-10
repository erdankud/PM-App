/** Язык интерфейса. Зеркало `Core/Localization/Localization.swift`.
 *
 *  Таблица строк лежит в `strings.js` и генерируется из iOS-исходника, поэтому
 *  здесь только сам выбор языка и три хелпера, на которые она опирается.
 */

const KEY = "app.language";

export const LANGUAGES = [
  { code: "en", displayName: "English", short: "EN" },
  { code: "ru", displayName: "Русский", short: "RU" },
];

const state = {
  language: "en",
  /** false, пока язык не выбран человеком: тогда значение с аккаунта важнее догадки. */
  explicit: false,
  listeners: new Set(),
};

/** Английский, пока человек не выберет другое.
 *
 *  Раньше здесь стоял язык браузера. Интерфейс продукта — английский, и Practice
 *  проводится по-английски при любом языке чромa; угаданный русский означал, что
 *  посетитель из русской локали видел не тот язык, которого от продукта ждут.
 *  Выбор в Профиле никуда не делся и по-прежнему сильнее этого значения.
 */
function deviceDefault() {
  return "en";
}

export function initLanguage() {
  let stored = null;
  try {
    stored = localStorage.getItem(KEY);
  } catch {
    stored = null;
  }
  state.explicit = stored === "en" || stored === "ru";
  state.language = state.explicit ? stored : deviceDefault();
  document.documentElement.lang = state.language;
}

export const language = () => state.language;
export const hasExplicitLanguage = () => state.explicit;

/** Осознанный выбор человека. */
export function selectLanguage(code) {
  state.explicit = true;
  try {
    localStorage.setItem(KEY, code);
  } catch {
    /* приватный режим — переживём без запоминания */
  }
  if (code === state.language) return;
  apply(code);
}

/** Язык с аккаунта: применяется, только если на этом устройстве выбора не делали. */
export function adoptLanguageFromServer(code) {
  if (state.explicit || code === state.language || !code) return;
  apply(code);
}

function apply(code) {
  state.language = code;
  document.documentElement.lang = code;
  for (const listener of state.listeners) listener(code);
}

export function onLanguageChange(listener) {
  state.listeners.add(listener);
  return () => state.listeners.delete(listener);
}

/** Единственная точка локализации: `t("Today", "Сегодня")`. */
export function t(english, russian) {
  return state.language === "ru" ? russian : english;
}

/** Русский выбирает форму по числу; английский этого хелпера не касается. */
export function plural(count, one, few, many) {
  const lastTwo = Math.abs(count) % 100;
  if (lastTwo >= 11 && lastTwo <= 14) return many;
  const last = Math.abs(count) % 10;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

export function capitalize(value) {
  const text = String(value ?? "");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Даты сервера — календарные дни UTC, поэтому разбор фиксирован на UTC. */
export function formatDate(isoDate) {
  if (!isoDate) return "";
  const date = new Date(isoDate.length <= 10 ? `${isoDate}T00:00:00Z` : isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString(state.language, {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}
