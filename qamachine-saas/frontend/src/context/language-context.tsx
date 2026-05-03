"use client";

import {
  createContext, useContext, useEffect, useState, useCallback,
} from "react";
import type { Lang } from "@/lib/i18n";
import { translations } from "@/lib/i18n";

const STORAGE_KEY = "qamachine_lang";

interface LanguageContextValue {
  lang:       Lang;
  t:          typeof translations.en;
  setLang:    (lang: Lang) => void;
  isDetecting: boolean;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang:       "en",
  t:          translations.en,
  setLang:    () => {},
  isDetecting: false,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState]   = useState<Lang>("en");
  const [isDetecting, setDetecting] = useState(true);

  useEffect(() => {
    const saved = typeof window !== "undefined"
      ? (localStorage.getItem(STORAGE_KEY) as Lang | null)
      : null;

    if (saved === "en" || saved === "ru" || saved === "uk" || saved === "es") {
      setLangState(saved);
      setDetecting(false);
      return;
    }

    // No preference saved — detect from backend (IP + Accept-Language)
    fetch(`/api/v1/locale/detect`, {
      headers: { "Accept-Language": navigator.language },
    })
      .then((r) => r.json())
      .then((data: { language: Lang }) => {
        const detected = (["en","ru","uk","es"] as const).includes(data.language as Lang)
          ? data.language as Lang : "en";
        setLangState(detected);
      })
      .catch(() => {
        // Fallback: use browser language
        const browserLang = navigator.language.toLowerCase();
        if (browserLang.startsWith("uk")) setLangState("uk");
        else if (browserLang.startsWith("ru")) setLangState("ru");
        else if (browserLang.startsWith("es")) setLangState("es");
        else setLangState("en");
      })
      .finally(() => setDetecting(false));
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, next);
      document.documentElement.lang = next;
    }
  }, []);

  // Keep html[lang] in sync
  useEffect(() => {
    if (typeof window !== "undefined") {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  return (
    <LanguageContext.Provider value={{ lang, t: translations[lang] as typeof translations.en, setLang, isDetecting }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLang() {
  return useContext(LanguageContext);
}
