"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { SSEEvent } from "@/types/events";

interface Message {
  id: string;
  role: "visitor" | "assistant";
  content: string;
  status: "pending" | "streaming" | "complete" | "error";
  createdAt: string;
}

interface ConversationContextValue {
  messages: Message[];
  addMessage: (msg: Message) => void;
  updateLastAssistant: (content: string) => void;
  setMessageStatus: (id: string, status: Message["status"]) => void;
  currentTurnIndex: number;
  setCurrentTurnIndex: (idx: number) => void;
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;
  clearMessages: () => void;
}

const ConversationContext = createContext<ConversationContextValue>({
  messages: [],
  addMessage: () => {},
  updateLastAssistant: () => {},
  setMessageStatus: () => {},
  currentTurnIndex: 0,
  setCurrentTurnIndex: () => {},
  isStreaming: false,
  setIsStreaming: () => {},
  clearMessages: () => {},
});

export function useConversation() {
  return useContext(ConversationContext);
}

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentTurnIndex, setCurrentTurnIndex] = useState(0);
  const [isStreaming, setIsStreaming] = useState(false);

  const addMessage = useCallback((msg: Message) => {
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
    (id: string, status: Message["status"]) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status } : m))
      );
    },
    []
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentTurnIndex(0);
    setIsStreaming(false);
  }, []);

  return (
    <ConversationContext.Provider
      value={{
        messages,
        addMessage,
        updateLastAssistant,
        setMessageStatus,
        currentTurnIndex,
        setCurrentTurnIndex,
        isStreaming,
        setIsStreaming,
        clearMessages,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}
