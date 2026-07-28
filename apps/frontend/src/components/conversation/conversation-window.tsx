"use client";

import { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare } from "lucide-react";
import { ChatMessage } from "./chat-message";
import { TypingIndicator } from "./typing-indicator";
import { ThinkingPanel } from "./thinking-panel";
import type { ConsultationMessage } from "@/types/events";

interface ConversationWindowProps {
  messages: ConsultationMessage[];
  isStreaming: boolean;
  isThinking: boolean;
  isEmpty: boolean;
  greeting: string | null;
  error: string | null;
}

export function ConversationWindow({
  messages,
  isStreaming,
  isThinking,
  isEmpty,
  greeting,
  error,
}: ConversationWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Empty state — welcome screen
  if (isEmpty && !greeting) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-4 text-center">
        <div className="mb-4 flex size-16 items-center justify-center rounded-2xl bg-primary/10">
          <MessageSquare className="size-8 text-primary" />
        </div>
        <h2 className="text-heading-md font-semibold text-foreground">
          Enterprise AI Consultation
        </h2>
        <p className="mt-2 max-w-md text-body text-muted-foreground">
          Your conversation with Nova will appear here. Click{" "}
          <strong>Start AI Consultation</strong> to begin.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto px-4 py-4">
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChatMessage message={msg} />
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Thinking panel — shown while waiting for response */}
        <ThinkingPanel isThinking={isThinking} />

        {/* Typing indicator — shown while streaming */}
        {isStreaming && !isThinking && <TypingIndicator />}

        {/* Error banner */}
        {error && (
          <div className="mx-auto max-w-lg rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-center text-body-sm text-destructive">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}