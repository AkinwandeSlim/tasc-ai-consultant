"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

export type SessionStatus =
  | "idle"
  | "landing"
  | "starting"
  | "active"
  | "streaming"
  | "completed"
  | "terminated"
  | "error";

interface SessionContextValue {
  sessionId: string | null;
  setSessionId: (_id: string) => void;
  status: SessionStatus;
  setStatus: (_status: SessionStatus) => void;
  currentTurnIndex: number;
  setCurrentTurnIndex: (_idx: number) => void;
  clearSession: () => void;
}

const SessionContext = createContext<SessionContextValue>({
  sessionId: null,
  setSessionId: (_id: string) => {},
  status: "idle" as SessionStatus,
  setStatus: (_status: SessionStatus) => {},
  currentTurnIndex: 0,
  setCurrentTurnIndex: (_idx: number) => {},
  clearSession: () => {},
});

export function useSession() {
  return useContext(SessionContext);
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<SessionStatus>("idle");
  const [currentTurnIndex, setCurrentTurnIndex] = useState(0);

  const clearSession = useCallback(() => {
    setSessionId(null);
    setStatus("idle");
    setCurrentTurnIndex(0);
  }, []);

  return (
    <SessionContext.Provider
      value={{
        sessionId,
        setSessionId,
        status,
        setStatus,
        currentTurnIndex,
        setCurrentTurnIndex,
        clearSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}