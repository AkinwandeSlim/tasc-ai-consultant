"use client";

import { useState, useRef, useCallback, type KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSend: (_message: string) => void;
  disabled: boolean;
  placeholder?: string;
  /** When true, shows a checkmark instead of a spinner for the disabled icon.
   *  Use when disabled is due to consultation completion rather than loading. */
  conversationFinished?: boolean;
}

const MAX_CHARS = 2000;

export function ChatInput({
  onSend,
  disabled,
  placeholder = "Tell Nova about your business...",
  conversationFinished = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    // Focus back on textarea
    textareaRef.current?.focus();
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const charCount = value.length;
  const isNearLimit = charCount > MAX_CHARS * 0.8;

  return (
    <div className="border-t border-border bg-surface-raised px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              // Auto-grow
              const el = e.target;
              el.style.height = "auto";
              el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            maxLength={MAX_CHARS}
            rows={1}
            className="w-full resize-none rounded-xl border border-border bg-surface-base px-4 py-2.5 text-body placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
            aria-label="Message input"
          />
          {/* Character count */}
          {isNearLimit && (
            <span className="absolute bottom-2 right-3 text-body-xs text-muted-foreground">
              {MAX_CHARS - charCount}
            </span>
          )}
        </div>

        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="Send message"
        >
          {conversationFinished ? (
            <span className="size-4 text-green-500">✓</span>
          ) : disabled ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Send className="size-4" />
          )}
        </button>
      </div>
      {/* Helper text */}
      <p className="mt-1 text-center text-body-xs text-muted-foreground">
        Press Enter to send · Shift+Enter for a new line
      </p>
    </div>
  );
}