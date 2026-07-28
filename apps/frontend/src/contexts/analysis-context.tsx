"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { AnalysisSnapshot } from "@/types/api";

interface AnalysisContextValue {
  snapshot: AnalysisSnapshot | null;
  previousSnapshot: AnalysisSnapshot | null;
  replaceSnapshot: (snapshot: AnalysisSnapshot) => void;
  clearSnapshot: () => void;
}

const AnalysisContext = createContext<AnalysisContextValue>({
  snapshot: null,
  previousSnapshot: null,
  replaceSnapshot: () => {},
  clearSnapshot: () => {},
});

export function useAnalysis() {
  return useContext(AnalysisContext);
}

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<AnalysisSnapshot | null>(null);
  const [previousSnapshot, setPreviousSnapshot] =
    useState<AnalysisSnapshot | null>(null);

  /**
   * Replace snapshot wholesale by turn_index.
   * Discard stale snapshots (lower turn_index than current).
   */
  const replaceSnapshot = useCallback(
    (newSnapshot: AnalysisSnapshot) => {
      if (
        snapshot &&
        newSnapshot.turn_index < snapshot.turn_index
      ) {
        return; // stale
      }
      setPreviousSnapshot(snapshot);
      setSnapshot(newSnapshot);
    },
    [snapshot]
  );

  const clearSnapshot = useCallback(() => {
    setSnapshot(null);
    setPreviousSnapshot(null);
  }, []);

  return (
    <AnalysisContext.Provider
      value={{ snapshot, previousSnapshot, replaceSnapshot, clearSnapshot }}
    >
      {children}
    </AnalysisContext.Provider>
  );
}
