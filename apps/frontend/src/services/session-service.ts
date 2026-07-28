/** Session API service. */

import { apiClient } from "./api-client";
import type { CreateSessionResponse } from "@/types/api";

export const sessionService = {
  create: (payload?: {
    locale?: string;
    referrer?: string;
    utm?: Record<string, string>;
    client_metadata?: Record<string, string>;
  }) => apiClient.post<CreateSessionResponse>("/sessions", payload ?? {}),

  get: (id: string) => apiClient.get<CreateSessionResponse>(`/sessions/${id}`),

  end: (id: string) => apiClient.post<{ status: string }>(`/sessions/${id}/delete`, {}),
};
