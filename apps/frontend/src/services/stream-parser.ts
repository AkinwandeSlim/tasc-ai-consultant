/** SSE stream parser — decodes backend SSE events into typed event objects. */

import type { SSEEvent } from "@/types/events";

export class StreamParser {
  private buffer: string = "";

  /**
   * Feed raw text chunks to the parser. Returns any complete events found.
   */
  feed(chunk: string): SSEEvent[] {
    this.buffer += chunk;
    const events: SSEEvent[] = [];
    const blocks = this.buffer.split("\n\n");

    // Keep the last (potentially incomplete) block in the buffer
    this.buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const event = this.parseBlock(block.trim());
      if (event) events.push(event);
    }

    return events;
  }

  private parseBlock(block: string): SSEEvent | null {
    const lines = block.split("\n");
    let eventType = "";
    let dataStr = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        dataStr = line.slice(6).trim();
      }
    }

    if (!eventType || !dataStr) return null;

    try {
      const data = JSON.parse(dataStr);

      switch (eventType) {
        case "phase":
          return { type: "phase", data };
        case "token":
          return { type: "token", data };
        case "analysis_snapshot":
          return { type: "analysis_snapshot", data };
        case "error":
          return { type: "error", data };
        case "done":
          return { type: "done", data };
        default:
          // Unknown event type — ignore for forward compatibility
          return null;
      }
    } catch {
      return null;
    }
  }

  reset() {
    this.buffer = "";
  }
}
