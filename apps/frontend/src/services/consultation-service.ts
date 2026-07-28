/** Consultation API service — maps to backend /api/v1/chat/message. */

import { apiClient } from "./api-client";
import type { MessageResponse } from "@/types/api";

export const consultationService = {
  /** POST /api/v1/chat/message — send a message in an active session. */
  send: (payload: { session_id: string; message: string; client_turn_id?: string }) =>
    apiClient.post<MessageResponse>("/chat/message", payload),
};