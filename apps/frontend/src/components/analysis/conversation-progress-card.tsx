"use client";

import type { ConversationProgress } from "@/types/api";
import { cn } from "@/utils/cn";

interface ConversationProgressCardProps {
  progress: ConversationProgress;
}

const STAGE_LABELS = [
  "Understanding",
  "Exploring",
  "Recommending",
  "Qualifying",
  "Wrapping up",
];

export function ConversationProgressCard({
  progress,
}: ConversationProgressCardProps) {
  const stages = STAGE_LABELS;
  const currentStage = Math.min(progress.stage_index, stages.length - 1);

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-heading-xs text-muted-foreground mb-3 uppercase tracking-wider">
        Conversation Progress
      </p>

      {/* Segmented progress bar */}
      <div className="flex gap-1 mb-3">
        {stages.map((label, idx) => (
          <div
            key={label}
            className={cn(
              "h-2 flex-1 rounded-full transition-colors duration-300",
              idx < currentStage && "bg-primary",
              idx === currentStage && "bg-primary/50",
              idx > currentStage && "bg-muted"
            )}
          />
        ))}
      </div>

      {/* Stage labels */}
      <div className="flex justify-between mb-2">
        {stages.map((label, idx) => (
          <span
            key={label}
            className={cn(
              "text-body-xs",
              idx === currentStage
                ? "text-foreground font-medium"
                : "text-muted-foreground"
            )}
          >
            {label}
          </span>
        ))}
      </div>

      {/* Slot counter */}
      <p className="text-body-sm text-muted-foreground text-center">
        {progress.slots_filled} of {progress.slots_total} details captured
      </p>
    </div>
  );
}
