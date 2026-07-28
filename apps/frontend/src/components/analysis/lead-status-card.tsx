"use client";

import { cn } from "@/utils/cn";

interface LeadStatusCardProps {
  status: string;
  explanation?: string;
}

const STATUS_STYLES: Record<string, string> = {
  exploring: "bg-status-exploring/10 text-status-exploring",
  cold: "bg-status-cold/10 text-status-cold",
  warm: "bg-status-warm/10 text-status-warm",
  qualified: "bg-status-qualified/10 text-status-qualified",
  hot: "bg-status-hot/10 text-status-hot",
};

const STATUS_LABELS: Record<string, string> = {
  exploring: "Exploring",
  cold: "Cold",
  warm: "Warm",
  qualified: "Qualified",
  hot: "Priority",
};

const STATUS_EXPLANATIONS: Record<string, string> = {
  exploring: "Still learning about your business",
  cold: "Early stage conversation",
  warm: "Clear need identified",
  qualified: "Strong fit with Trizen services",
  hot: "Priority lead, a consultant will follow up quickly",
};

export function LeadStatusCard({
  status,
  explanation,
}: LeadStatusCardProps) {
  const label = STATUS_LABELS[status] ?? status;
  const explanationText = explanation ?? STATUS_EXPLANATIONS[status] ?? "";

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
        Lead Status
      </p>
      <span
        className={cn(
          "inline-flex items-center rounded-full px-2.5 py-0.5 text-body-sm font-medium",
          STATUS_STYLES[status] ?? "bg-muted text-muted-foreground"
        )}
      >
        {label}
      </span>
      {explanationText && (
        <p className="mt-1.5 text-body-sm text-muted-foreground">
          {explanationText}
        </p>
      )}
    </div>
  );
}
