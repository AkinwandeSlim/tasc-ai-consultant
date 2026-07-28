/** Base API client — fetch wrapper with error handling and correlation IDs. */

import { API_CONFIG } from "@/lib/api-config";

export class ApiClientError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public retryable: boolean,
    public correlationId?: string
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

interface ApiClientConfig {
  baseUrl: string;
  timeout: number;
}

export class ApiClient {
  private config: ApiClientConfig;
  private correlationId: string;

  constructor(config?: Partial<ApiClientConfig>) {
    this.config = {
      baseUrl: API_CONFIG.baseUrl,
      timeout: API_CONFIG.timeout,
      ...config,
    };
    this.correlationId = crypto.randomUUID();
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(`${this.config.baseUrl}${path}`, {
        method: "POST",
        headers: {
          ...API_CONFIG.headers,
          "X-Correlation-Id": this.correlationId,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ApiClientError(
          response.status,
          error?.error?.code ?? "UNKNOWN",
          error?.error?.message ?? "Request failed",
          error?.error?.retryable ?? false,
          error?.error?.correlation_id
        );
      }

      return (await response.json()) as T;
    } catch (err) {
      if (err instanceof ApiClientError) throw err;
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new ApiClientError(408, "TIMEOUT", "Request timed out", true);
      }
      throw new ApiClientError(0, "NETWORK_ERROR", "Network error", true);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async get<T>(path: string): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(`${this.config.baseUrl}${path}`, {
        method: "GET",
        headers: {
          ...API_CONFIG.headers,
          "X-Correlation-Id": this.correlationId,
        },
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ApiClientError(
          response.status,
          error?.error?.code ?? "UNKNOWN",
          error?.error?.message ?? "Request failed",
          error?.error?.retryable ?? false
        );
      }

      return (await response.json()) as T;
    } catch (err) {
      if (err instanceof ApiClientError) throw err;
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new ApiClientError(408, "TIMEOUT", "Request timed out", true);
      }
      throw new ApiClientError(0, "NETWORK_ERROR", "Network error", true);
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

export const apiClient = new ApiClient();
