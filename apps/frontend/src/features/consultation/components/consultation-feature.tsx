"use client";

import { type ReactNode } from "react";

/**
 * ConsultationFeature — main composition root for the consultation experience.
 *
 * Manages the two-panel layout (conversation + analysis) and session lifecycle.
 * Business logic is handled by the backend; this component renders state
 * from backend snapshots.
 */
export function ConsultationFeature({
  sessionId: _initialSessionId,
}: {
  sessionId?: string;
}): ReactNode {
  // TODO: Implement session bootstrap, conversation panel, analysis panel
  return (
    <div className="flex h-screen">
      <div className="flex-1 border-r border-border">
        {/* Conversation Panel */}
        <div className="flex h-full flex-col">
          <div className="flex items-center gap-3 border-b border-border px-4 py-3">
            <div className="size-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-body-sm font-semibold">
              N
            </div>
            <div>
              <p className="text-body-sm font-medium">Nova</p>
              <p className="text-body-xs text-muted-foreground">
                AI Solutions Consultant
              </p>
            </div>
          </div>
          <div className="flex-1 flex items-center justify-center text-muted-foreground text-body-sm">
            Start a consultation to begin
          </div>
        </div>
      </div>
      <div className="hidden w-[380px] lg:block p-4">
        {/* Analysis Panel */}
        <div className="text-center text-muted-foreground text-body-sm mt-8">
          Analysis panel
        </div>
      </div>
    </div>
  );
}
