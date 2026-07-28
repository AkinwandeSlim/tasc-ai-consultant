/** Consultation API service. */

import { apiClient } from "./api-client";

export const consultationService = {
  complete: (sessionId: string, payload: { reason: string; contact?: unknown }) =>
    apiClient.post<{
      consultation_id: string;
      status: string;
      summary: { executive_summary: string; word_count: number };
      qualification: { score: number; band: string };
      dispatch: { status: string };
    }>(`/sessions/${sessionId}/complete`, payload),

  getAnalysis: (sessionId: string) =>
    apiClient.get<Record<string, unknown>>(`/sessions/${sessionId}/analysis`),
};
