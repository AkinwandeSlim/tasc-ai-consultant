"use client";

import type { RecommendedService } from "@/types/api";
import { cn } from "@/utils/cn";

interface RecommendedServicesCardProps {
  services: RecommendedService[];
}

export function RecommendedServicesCard({
  services,
}: RecommendedServicesCardProps) {
  if (services.length === 0) {
    return (
      <div className="rounded-lg border border-border p-3">
        <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
          Recommended Services
        </p>
        <p className="text-body-sm text-muted-foreground">
          Recommendations appear once I understand the problem
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
        Recommended Services
      </p>
      <div className="space-y-2">
        {services.slice(0, 3).map((svc) => (
          <div
            key={svc.service_code}
            className={cn(
              "rounded-md border p-2.5",
              svc.rank === 1 ? "border-primary/30 bg-primary/5" : "border-border"
            )}
          >
            <div className="flex items-center justify-between">
              <p className="text-body-sm font-medium">{svc.name}</p>
              {svc.confidence >= 0.8 && (
                <span className="text-body-xs rounded bg-status-hot/10 text-status-hot px-1.5 py-0.5">
                  High
                </span>
              )}
              {svc.confidence >= 0.6 && svc.confidence < 0.8 && (
                <span className="text-body-xs rounded bg-status-warm/10 text-status-warm px-1.5 py-0.5">
                  Medium
                </span>
              )}
            </div>
            <p className="mt-1 text-body-sm text-muted-foreground">
              {svc.rationale}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
