"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

interface SessionContextValue {
  sessionId: string | null;
  setSessionId: (id: string) => void;
  status: SessionStatus;
  setStatus: (status: SessionStatus) => void;
  clearSession: () => void;
}

type SessionStatus =
  | "idle"
  | "creating"
  | "active"
  | "completing"
  | "completed"
  | "expired"
  | "error";

const SessionContext = createContext<SessionContextValue>({
  sessionId: null,
  setSessionId: () => {},
  status: "idle",
  setStatus: () => {},
  clearSession: () => {},
});

export function useSession() {
  return useContext(SessionContext);
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<SessionStatus>("idle");

  const clearSession = useCallback(() => {
    setSessionId(null);
    setStatus("idle");
  }, []);

  return (
    <SessionContext.Provider
      value={{ sessionId, setSessionId, status, setStatus, clearSession }}
    >
      {children}
    </SessionContext.Provider>
  );
}
