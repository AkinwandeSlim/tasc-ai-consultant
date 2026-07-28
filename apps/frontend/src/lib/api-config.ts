/** API configuration — base URL and defaults. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const API_ROOT_URL =
  process.env.NEXT_PUBLIC_API_ROOT_URL ?? "http://localhost:8000";

export const API_CONFIG = {
  baseUrl: API_BASE_URL,
  rootUrl: API_ROOT_URL,
  timeout: 90_000,
  headers: {
    "Content-Type": "application/json",
  },
} as const;
