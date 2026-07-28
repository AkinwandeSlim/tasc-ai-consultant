"use client";

interface LeadScoreCardProps {
  score: number | null;
  delta?: number | null;
  nextContributor?: string | null;
}

export function LeadScoreCard({
  score,
  delta,
  nextContributor,
}: LeadScoreCardProps) {
  if (score === null) {
    return (
      <div className="rounded-lg border border-border p-3">
        <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
          Lead Score
        </p>
        <p className="text-body-sm text-muted-foreground">Gathering context</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-heading-xs text-muted-foreground mb-2 uppercase tracking-wider">
        Lead Score
      </p>
      <div className="flex items-baseline gap-2">
        <span className="text-heading-lg font-semibold">{score}</span>
        <span className="text-heading-sm text-muted-foreground">/ 100</span>
        {delta !== null && delta !== undefined && delta !== 0 && (
          <span
            className={`text-body-sm font-medium ${
              delta > 0 ? "text-status-hot" : "text-destructive"
            } animate-score-delta`}
          >
            {delta > 0 ? `+${delta}` : delta}
          </span>
        )}
      </div>
      {nextContributor && (
        <p className="mt-1 text-body-sm text-muted-foreground">
          {nextContributor}
        </p>
      )}
    </div>
  );
}
