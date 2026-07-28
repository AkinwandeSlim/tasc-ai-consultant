/** Visitor-facing copy keys for the consultation feature. */

export const COPY = {
  greeting: {
    title: "Nova",
    subtitle: "AI Solutions Consultant",
  },
  empty: {
    panel: "Analysis results will appear here as the conversation progresses.",
    conversation: "Your conversation with Nova will appear here.",
    score: "Gathering context",
    status: "Getting to know your business",
    industry: "Not identified yet",
    businessSize: "Not identified yet",
    painPoints: "Listening for challenges",
    recommendations: "Recommendations appear once I understand the problem",
  },
  actions: {
    send: "Send message",
    restart: "Start over",
    retry: "Try again",
    copy: "Copy summary",
    close: "Close",
  },
  status: {
    connected: "Connected",
    disconnected: "Reconnecting...",
  },
  errors: {
    generic: "Something went wrong. Please try again.",
    expired: "This session has ended. Start a new consultation to continue.",
    rateLimited: "Too many requests. Please wait a moment.",
  },
  phases: {
    understanding: "Understanding your business...",
    retrieving: "Searching company knowledge...",
    evaluating: "Evaluating requirements...",
    preparing: "Preparing recommendations...",
  },
  completion: {
    queued: "Your consultation has been submitted. A consultant will follow up.",
    confirmed: "Your consultation has been submitted and confirmed.",
  },
} as const;
