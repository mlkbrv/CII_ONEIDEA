/*
 * Three languages, one dictionary per language.
 *
 * The app picks a language in this order:
 *   1. what the account says  — the server remembers it, so a choice follows
 *      the player to another device and the bot writes in the same language;
 *   2. what Telegram says     — before the account has loaded, or for a first
 *      visit, the client's own language is the best guess available;
 *   3. Russian.
 *
 * Changing the language PATCHes the account, because the bot composes its
 * messages server-side and would otherwise keep writing in the old one.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import az from "./az";
import en from "./en";
import ru from "./ru";

const TABLES = { ru, en, az };
export const LANGUAGES = [
  { code: "ru", label: "Русский" },
  { code: "en", label: "English" },
  { code: "az", label: "Azərbaycan" },
];

const DEFAULT = "ru";
const STORAGE_KEY = "colafest.lang";

/** Reduce an IETF tag ("az-AZ", "en-GB") to a language we actually have. */
export function normalise(value) {
  if (!value) return DEFAULT;
  const primary = String(value).toLowerCase().replace("_", "-").split("-")[0];
  return primary in TABLES ? primary : DEFAULT;
}

function telegramLanguage() {
  return window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
}

function stored() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    // Private windows throw on access rather than returning null.
    return null;
  }
}

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  // Start from the last local choice, then Telegram. The account's stored
  // language arrives a moment later with /users/me and takes over — but only
  // if the user has not already picked something in this session, otherwise
  // the switcher would appear to snap back.
  const [language, setLanguage] = useState(() => normalise(stored() || telegramLanguage()));
  const [pinned, setPinned] = useState(() => Boolean(stored()));

  const adoptFromAccount = useCallback(
    (accountLanguage) => {
      if (pinned || !accountLanguage) return;
      setLanguage(normalise(accountLanguage));
    },
    [pinned]
  );

  const choose = useCallback((next) => {
    const value = normalise(next);
    setLanguage(value);
    setPinned(true);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* see stored() */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo(
    () => ({
      language,
      choose,
      adoptFromAccount,
      t: (key, params) => translate(language, key, params),
    }),
    [language, choose, adoptFromAccount]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside <I18nProvider>");
  return context;
}

/** Shorthand for the common case: `const t = useT()`. */
export function useT() {
  return useI18n().t;
}

function translate(language, key, params) {
  const table = TABLES[language] || TABLES[DEFAULT];
  // Falling back to Russian rather than showing the key: a line in the wrong
  // language is still a sentence, and "battle.vote_for" is not.
  const template = table[key] ?? TABLES[DEFAULT][key];

  if (template === undefined) {
    if (import.meta.env.DEV) console.warn(`[i18n] no translation for ${key}`);
    return key;
  }
  if (!params) return template;

  return template.replace(/\{(\w+)\}/g, (whole, name) =>
    params[name] === undefined ? whole : String(params[name])
  );
}
