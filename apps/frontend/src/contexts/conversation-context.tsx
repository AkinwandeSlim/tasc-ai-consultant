"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { ConsultationMessage } from "@/types/events";

interface ConversationContextValue {
  messages: ConsultationMessage[];
  addMessage: (_msg: ConsultationMessage) => void;
  updateLastAssistant: (_content: string) => void;
  setMessageStatus: (_id: string, _status: ConsultationMessage["status"]) => void;
  hasMessages: boolean;
  clearMessages: () => void;
  isStreaming: boolean;
  setIsStreaming: (_v: boolean) => void;
}

const ConversationContext = createContext<ConversationContextValue>({
  messages: [],
  addMessage: (_msg: ConsultationMessage) => {},
  updateLastAssistant: (_content: string) => {},
  setMessageStatus: (_id: string, _status: ConsultationMessage["status"]) => {},
  hasMessages: false,
  clearMessages: () => {},
  isStreaming: false,
  setIsStreaming: (_v: boolean) => {},
});

export function useConversation() {
  return useContext(ConversationContext);
}

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ConsultationMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const addMessage = useCallback((msg: ConsultationMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const updateLastAssistant = useCallback((content: string) => {
    setMessages((prev) => {
      const idx = prev.length - 1;
      if (idx < 0 || prev[idx].role !== "assistant") return prev;
      const updated = [...prev];
      updated[idx] = { ...updated[idx], content };
      return updated;
    });
  }, []);

  const setMessageStatus = useCallback(
    (id: string, status: ConsultationMessage["status"]) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status } : m)),
      );
    },
    [],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setIsStreaming(false);
  }, []);

  const hasMessages = messages.length > 0;

  return (
    <ConversationContext.Provider
      value={{
        messages,
        addMessage,
        updateLastAssistant,
        setMessageStatus,
        hasMessages,
        clearMessages,
        isStreaming,
        setIsStreaming,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}