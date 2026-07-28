/**
 * useHealthCheck — polls the backend health endpoint.
 *
 * Returns connection status, backend version, and simulation mode flag.
 * Polls every 30 seconds while the component is mounted.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/api-client";
import type { HealthResponse } from "@/types/api";

export interface HealthState {
  status: string;
  version: string;
  simulationMode: boolean;
}

const EMPTY: HealthState = {
  status: "unknown",
  version: "",
  simulationMode: false,
};

async function fetchHealth(): Promise<HealthState> {
  const data = await apiClient.get<HealthResponse>("/api/health", {
    useRoot: true,
  });
  return {
    status: data.status,
    version: data.version,
    simulationMode: data.simulation_mode,
  };
}

export function useHealthCheck() {
  const { data, isError, isLoading } = useQuery<HealthState>({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
    retry: 2,
    retryDelay: 2_000,
    staleTime: 10_000,
  });

  return {
    health: data ?? EMPTY,
    isConnected: data?.status === "ok" && !isError,
    isLoading,
    isError,
  };
}