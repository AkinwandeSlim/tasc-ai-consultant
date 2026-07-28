/** Exhaustive check helper for TypeScript unions. */

export function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${value}`);
}
