import * as React from "react";

export const FONT_SCALE_STEPS = [0.9, 1, 1.1, 1.2] as const;
const FONT_SCALE_STORAGE_KEY = "app-font-scale";
const LANGUAGE_STORAGE_KEY = "app-language";

export type Language = "EN" | "HI";

function readStepIndex() {
  const saved = Number(localStorage.getItem(FONT_SCALE_STORAGE_KEY));
  const idx = FONT_SCALE_STEPS.indexOf(saved as (typeof FONT_SCALE_STEPS)[number]);
  return idx >= 0 ? idx : 1;
}

function readLanguage(): Language {
  return localStorage.getItem(LANGUAGE_STORAGE_KEY) === "HI" ? "HI" : "EN";
}

/**
 * Shared, localStorage-backed accessibility state so the Topbar controls and
 * the Settings page reflect and change the same values.
 */
export function useAccessibilitySettings() {
  const [stepIndex, setStepIndex] = React.useState(readStepIndex);
  const [language, setLanguageState] = React.useState<Language>(readLanguage);

  React.useEffect(() => {
    const scale = FONT_SCALE_STEPS[stepIndex];
    document.documentElement.style.setProperty("--app-font-scale", String(scale));
    localStorage.setItem(FONT_SCALE_STORAGE_KEY, String(scale));
  }, [stepIndex]);

  const setLanguage = React.useCallback((lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem(LANGUAGE_STORAGE_KEY, lang);
  }, []);

  return {
    fontScale: FONT_SCALE_STEPS[stepIndex],
    stepIndex,
    decreaseFont: () => setStepIndex((i) => Math.max(0, i - 1)),
    resetFont: () => setStepIndex(1),
    increaseFont: () => setStepIndex((i) => Math.min(FONT_SCALE_STEPS.length - 1, i + 1)),
    language,
    setLanguage,
  };
}
