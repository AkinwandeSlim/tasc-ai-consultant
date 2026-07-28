"use client";

import { cn } from "@/utils/cn";
import { Wifi, FlaskConical } from "lucide-react";

interface HeaderProps {
  className?: string;
  isConnected: boolean;
  isSimulationMode: boolean;
  phase: string;
}

export function Header({
  className,
  isConnected,
  isSimulationMode,
  phase,
}: HeaderProps) {
  return (
    <header
      className={cn(
        "flex items-center justify-between border-b border-border px-4 py-2.5",
        className,
      )}
    >
      {/* Left: Brand */}
      <div className="flex items-center gap-3">
        <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-body-sm font-bold text-primary-foreground">
          T
        </div>
        <div className="hidden sm:block">
          <p className="text-body-sm font-semibold">TASC AI Consultant</p>
          <p className="text-body-xs text-muted-foreground">
            Enterprise AI Consultation Platform
          </p>
        </div>
      </div>

      {/* Right: Status + Phase */}
      <div className="flex items-center gap-3">
        {/* Phase badge */}
        {phase && phase !== "idle" && (
          <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-body-xs font-medium capitalize text-primary">
            {phase}
          </span>
        )}

        {/* Simulation badge */}
        {isSimulationMode && (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-body-xs font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
            <FlaskConical className="size-3" />
            Simulation
          </span>
        )}

        {/* Connection status */}
        <span
          className={cn(
            "inline-flex items-center gap-1.5 text-body-xs",
            isConnected
              ? "text-status-hot"
              : "text-muted-foreground",
          )}
        >
          <Wifi
            className={cn(
              "size-3",
              !isConnected && "animate-pulse",
            )}
          />
          {isConnected ? "Connected" : "Reconnecting..."}
        </span>
      </div>
    </header>
  );
}