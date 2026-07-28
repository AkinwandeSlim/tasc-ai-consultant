/**
 * useThinkingAnimation — manages the animated AI Thinking Panel checklist.
 *
 * When isThinking becomes true, steps activate sequentially every ~350ms.
 * Returns the current active step index and which steps are completed.
 * When isThinking becomes false, resets all steps to pending.
 */

import { useState, useEffect, useRef } from "react";

export interface ThinkingStep {
  key: string;
  label: string;
}

export const THINKING_STEPS: ThinkingStep[] = [
  { key: "context", label: "Understanding business context" },
  { key: "profile", label: "Updating business profile" },
  { key: "requirements", label: "Extracting business requirements" },
  { key: "readiness", label: "Evaluating AI readiness" },
  { key: "qualification", label: "Assessing lead qualification" },
  { key: "matching", label: "Matching implementation opportunities" },
  { key: "recommendations", label: "Preparing recommendations" },
  { key: "response", label: "Generating consultation response" },
];

interface ThinkingAnimationState {
  activeIndex: number;
  completedIndices: number[];
  isVisible: boolean;
}

export function useThinkingAnimation(isThinking: boolean) {
  const [state, setState] = useState<ThinkingAnimationState>({
    activeIndex: -1,
    completedIndices: [],
    isVisible: false,
  });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wasThinkingRef = useRef(false);

  useEffect(() => {
    if (isThinking && !wasThinkingRef.current) {
      // Thinking just started — begin animation
      wasThinkingRef.current = true;
      setState({
        activeIndex: 0,
        completedIndices: [],
        isVisible: true,
      });

      // Advance steps every 350ms
      intervalRef.current = setInterval(() => {
        setState((prev) => {
          const nextActive = prev.activeIndex + 1;
          if (nextActive >= THINKING_STEPS.length) {
            // Loop: mark all as pending and restart
            return {
              activeIndex: 0,
              completedIndices: [],
              isVisible: true,
            };
          }
          return {
            activeIndex: nextActive,
            completedIndices: [...prev.completedIndices, prev.activeIndex],
            isVisible: true,
          };
        });
      }, 350);
    } else if (!isThinking && wasThinkingRef.current) {
      // Thinking just ended — hide immediately
      wasThinkingRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setState({
        activeIndex: -1,
        completedIndices: [],
        isVisible: false,
      });
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isThinking]);

  return state;
}