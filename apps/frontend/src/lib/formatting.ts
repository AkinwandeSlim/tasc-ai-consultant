/** Display formatting utilities. */

export function formatScoreDelta(delta: number): string {
  if (delta > 0) return `+${delta}`;
  return `${delta}`;
}

export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 1) + "…";
}
