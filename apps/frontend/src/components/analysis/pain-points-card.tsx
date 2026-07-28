"use client";

import type { PainPoint } from "@/types/api";
import { cn } from "@/utils/cn";
import { truncate } from "@/lib/formatting";

interface PainPointsCardProps {
  painPoints: PainPoint[];
}

export function PainPointsCard({ painPoints }: PainPointsCardProps) {
  if (painPoints.length === 0) {
    return (
      <div className="rounded-lg border border-border p-3">
        <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
          Pain Points
        </p>
        <p className="text-body-sm text-muted-foreground">
          Listening for challenges
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
        Pain Points
      </p>
      <ul className="space-y-1.5">
        {painPoints.slice(0, 6).map((pp) => (
          <li key={pp.id} className="flex items-start gap-2 text-body-sm">
            <span className="mt-1 size-1.5 rounded-full bg-primary shrink-0" />
            <span>{truncate(pp.label, 60)}</span>
            {pp.service_codes.map((code) => (
              <span
                key={code}
                className={cn(
                  "text-body-xs rounded px-1 py-0.5",
                  "bg-muted text-muted-foreground"
                )}
              >
                {code}
              </span>
            ))}
          </li>
        ))}
      </ul>
      {painPoints.length > 6 && (
        <button className="mt-2 text-body-sm text-primary underline underline-offset-2">
          Show all ({painPoints.length})
        </button>
      )}
    </div>
  );
}
