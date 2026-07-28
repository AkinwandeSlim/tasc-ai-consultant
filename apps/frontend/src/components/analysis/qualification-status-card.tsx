"use client";

import type { QualificationStatusDTO } from "@/types/events";
import { cn } from "@/utils/cn";

interface QualificationStatusCardProps {
  status: QualificationStatusDTO;
}

const CRITERIA_LABELS: Record<keyof QualificationStatusDTO, string> = {
  business_context_understood: "Business context understood",
  challenges_identified: "Challenges identified",
  solution_matched: "Solution matched",
  timeline_established: "Timeline established",
  budget_discussed: "Budget discussed",
  contact_captured: "Contact captured",
};

export function QualificationStatusCard({
  status,
}: QualificationStatusCardProps) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-heading-xs text-muted-foreground mb-3 uppercase tracking-wider">
        Qualification Status
      </p>
      <ul className="space-y-2">
        {(Object.keys(CRITERIA_LABELS) as Array<keyof QualificationStatusDTO>).map(
          (key) => {
            const value = status[key];
            return (
              <li key={key} className="flex items-center gap-2 text-body-sm">
                <span
                  className={cn(
                    "size-4 rounded-full flex items-center justify-center text-xs shrink-0",
                    value === "met" && "bg-status-hot/10 text-status-hot",
                    value === "unmet" && "bg-muted text-muted-foreground",
                    value === "declined" && "bg-muted text-muted-foreground line-through"
                  )}
                >
                  {value === "met" ? "✓" : value === "declined" ? "—" : "○"}
                </span>
                <span className={cn(value === "declined" && "text-muted-foreground")}>
                  {CRITERIA_LABELS[key]}
                </span>
              </li>
            );
          }
        )}
      </ul>
    </div>
  );
}