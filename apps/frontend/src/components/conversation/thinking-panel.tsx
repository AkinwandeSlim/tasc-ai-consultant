"use client";

import { Check, Brain } from "lucide-react";
import { cn } from "@/utils/cn";
import {
  useThinkingAnimation,
  THINKING_STEPS,
} from "@/hooks/use-thinking-animation";

interface ThinkingPanelProps {
  isThinking: boolean;
}

export function ThinkingPanel({ isThinking }: ThinkingPanelProps) {
  const { activeIndex, completedIndices, isVisible } =
    useThinkingAnimation(isThinking);

  if (!isVisible) return null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-4">
      <div className="rounded-xl border border-border/60 bg-surface-raised/80 p-4 backdrop-blur-sm">
        {/* Header */}
        <div className="mb-3 flex items-center gap-2">
          <Brain className="size-4 text-primary" />
          <span className="text-body-sm font-medium">
            AI Consultation Engine
          </span>
          <span className="text-body-xs text-muted-foreground">
            Analyzing your business context...
          </span>
        </div>

        {/* Steps */}
        <div className="space-y-1.5">
          {THINKING_STEPS.map((step, idx) => {
            const isActive = idx === activeIndex;
            const isCompleted = completedIndices.includes(idx);

            return (
              <div
                key={step.key}
                className={cn(
                  "flex items-center gap-2 text-body-sm transition-colors duration-200",
                  isCompleted && "text-status-hot",
                  isActive && "text-foreground",
                  !isCompleted && !isActive && "text-muted-foreground/50",
                )}
              >
                {/* Icon */}
                <span className="flex size-4 shrink-0 items-center justify-center">
                  {isCompleted ? (
                    <Check className="size-3.5 text-status-hot" />
                  ) : isActive ? (
                    <span className="size-2 animate-pulse rounded-full bg-primary" />
                  ) : (
                    <span className="size-1.5 rounded-full bg-muted-foreground/30" />
                  )}
                </span>

                {/* Label */}
                <span
                  className={cn(
                    isActive && "font-medium",
                    isCompleted && "line-through opacity-70",
                  )}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}