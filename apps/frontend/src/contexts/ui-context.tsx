"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

interface UIContextValue {
  isMobilePanelOpen: boolean;
  setMobilePanelOpen: (_v: boolean) => void;
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  reducedMotion: boolean;
}

const UIContext = createContext<UIContextValue>({
  isMobilePanelOpen: false,
  setMobilePanelOpen: (_v: boolean) => {},
  isDarkMode: false,
  toggleDarkMode: () => {},
  reducedMotion: false,
});

export function useUI() {
  return useContext(UIContext);
}

export function UIProvider({ children }: { children: ReactNode }) {
  const [isMobilePanelOpen, setMobilePanelOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [reducedMotion] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  const toggleDarkMode = useCallback(() => {
    setIsDarkMode((prev) => !prev);
    document.documentElement.classList.toggle("dark");
  }, []);

  return (
    <UIContext.Provider
      value={{
        isMobilePanelOpen,
        setMobilePanelOpen,
        isDarkMode,
        toggleDarkMode,
        reducedMotion,
      }}
    >
      {children}
    </UIContext.Provider>
  );
}
