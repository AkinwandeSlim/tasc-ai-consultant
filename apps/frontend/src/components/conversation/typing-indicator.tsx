"use client";

import { motion } from "framer-motion";

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-1 py-2">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-body-xs font-semibold text-primary-foreground">
        N
      </div>
      <div className="flex items-center gap-1">
        <motion.span
          className="size-1.5 rounded-full bg-muted-foreground/40"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
        />
        <motion.span
          className="size-1.5 rounded-full bg-muted-foreground/40"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
        />
        <motion.span
          className="size-1.5 rounded-full bg-muted-foreground/40"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
        />
      </div>
    </div>
  );
}