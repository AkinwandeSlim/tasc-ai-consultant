"use client";

import { cn } from "@/utils/cn";

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  return (
    <header
      className={cn(
        "flex items-center gap-3 border-b border-border px-4 py-3",
        className
      )}
    >
      <div className="size-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-body-sm font-semibold">
        N
      </div>
      <div>
        <p className="text-body-sm font-medium">Nova</p>
        <p className="text-body-xs text-muted-foreground">
          AI Solutions Consultant
        </p>
      </div>
    </header>
  );
}
