/** Base API client — fetch wrapper with error handling and correlation IDs. */

import { API_CONFIG } from "@/lib/api-config";

export class ApiClientError extends Error {
  constructor(
    _status: number,
    _code: string,
    message: string,
    _retryable: boolean,
    _correlationId?: string
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

interface ApiClientConfig {
  baseUrl: string;
  rootUrl: string;
  timeout: number;
}

export class ApiClient {
  private config: ApiClientConfig;
  public correlationId: string;

  constructor(config?: Partial<ApiClientConfig>) {
    this.config = {
      baseUrl: API_CONFIG.baseUrl,
      rootUrl: API_CONFIG.rootUrl,
      timeout: API_CONFIG.timeout,
      ...config,
    };
    this.correlationId = crypto.randomUUID();
  }

  private async request<T>(
    method: string,
    path: string,
    options?: { body?: unknown; useRoot?: boolean },
  ): Promise<T> {
    const base = options?.useRoot ? this.config.rootUrl : this.config.baseUrl;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(`${base}${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-Correlation-Id": this.correlationId,
        },
        body: options?.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ApiClientError(
          response.status,
          error?.error?.code ?? "UNKNOWN",
          error?.error?.message ?? "Request failed",
          error?.error?.retryable ?? false,
          error?.error?.correlation_id,
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

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("POST", path, { body });
  }

  async get<T>(path: string, opts?: { useRoot?: boolean }): Promise<T> {
    return this.request<T>("GET", path, opts);
  }
}

export const apiClient = new ApiClient();
