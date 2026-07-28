/** Session API service — maps to backend /api/v1/chat endpoints. */

import { apiClient } from "./api-client";
import type { StartConsultationResponse, SessionSnapshotResponse } from "@/types/api";

export const sessionService = {
  /** POST /api/v1/chat/start — create a new consultation session. */
  start: (payload?: {
    locale?: string;
    referrer?: string;
    utm?: Record<string, string>;
    client_metadata?: Record<string, string>;
  }) =>
    apiClient.post<StartConsultationResponse>("/chat/start", payload ?? {}),

  /** GET /api/v1/chat/{session_id} — current consultation snapshot. */
  get: (id: string) =>
    apiClient.get<SessionSnapshotResponse>(`/chat/${id}`),
};