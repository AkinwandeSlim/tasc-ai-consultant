"use client";

import { cn } from "@/utils/cn";
import type { ConsultationMessage } from "@/types/events";

interface ChatMessageProps {
  message: ConsultationMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isError = message.status === "error";

  return (
    <div
      className={cn(
        "flex w-full gap-3",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-body-xs font-semibold text-primary-foreground">
          N
        </div>
      )}

      <div
        className={cn(
          "max-w-[75%]",
          isUser
            ? "rounded-2xl bg-primary px-4 py-2.5 text-primary-foreground"
            : "px-1 py-0.5",
        )}
      >
        <p
          className={cn(
            "text-body whitespace-pre-wrap break-words",
            isError && "text-destructive",
          )}
        >
          {message.content}
        </p>
        {isError && (
          <p className="mt-1 text-body-xs text-destructive/80">
            Failed to send — please try again
          </p>
        )}
      </div>

      {/* User avatar placeholder */}
      {isUser && (
        <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-body-xs font-medium text-muted-foreground">
          U
        </div>
      )}
    </div>
  );
}