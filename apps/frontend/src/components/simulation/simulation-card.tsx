"use client";

import { FlaskConical, Clock, Fingerprint } from "lucide-react";

interface SimulationCardProps {
  scenarioId?: string | null;
  sessionId?: string | null;
  startedAt?: string | null;
}

export function SimulationCard({
  scenarioId,
  sessionId,
  startedAt,
}: SimulationCardProps) {
  if (!sessionId) return null;

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
        Simulation
      </p>
      <div className="space-y-1.5">
        {scenarioId && (
          <div className="flex items-center gap-2 text-body-sm">
            <FlaskConical className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Scenario:</span>
            <span className="font-medium capitalize">{scenarioId}</span>
          </div>
        )}
        <div className="flex items-center gap-2 text-body-sm">
          <Fingerprint className="size-3.5 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">Session ID:</span>
          <span className="font-mono text-body-xs">{sessionId.slice(0, 12)}...</span>
        </div>
        {startedAt && (
          <div className="flex items-center gap-2 text-body-sm">
            <Clock className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-muted-foreground">Started:</span>
            <span className="text-body-xs">
              {new Date(startedAt).toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}