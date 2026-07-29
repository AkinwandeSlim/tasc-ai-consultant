/**
 * Minimal smoke test — validates the Vitest test infrastructure.
 *
 * If this test passes, the test runner, jsdom environment,
 * and TypeScript path aliases are all working correctly.
 */
import { describe, it, expect } from "vitest";
import { API_CONFIG } from "@/lib/api-config";

describe("test infrastructure", () => {
  it("runs a basic assertion", () => {
    expect(1 + 1).toBe(2);
  });

  it("resolves @ path alias", () => {
    // Importing via the @/ alias confirms tsconfig path resolution works
    expect(API_CONFIG).toBeDefined();
    expect(API_CONFIG.baseUrl).toContain("localhost");
  });
});
