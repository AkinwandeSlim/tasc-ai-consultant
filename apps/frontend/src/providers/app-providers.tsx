"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { ThemeProvider } from "./theme-provider";
import { SessionProvider } from "@/contexts/session-context";
import { ConversationProvider } from "@/contexts/conversation-context";
import { AnalysisProvider } from "@/contexts/analysis-context";
import { UIProvider } from "@/contexts/ui-context";

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <SessionProvider>
          <ConversationProvider>
            <AnalysisProvider>
              <UIProvider>{children}</UIProvider>
            </AnalysisProvider>
          </ConversationProvider>
        </SessionProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}