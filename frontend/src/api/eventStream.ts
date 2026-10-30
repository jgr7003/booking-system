import { authorizedFetch } from "./session";

/**
 * Server-Sent Events read with `fetch`, because `EventSource` can't send the `Authorization`
 * and `DPoP` headers the booking stream needs (03-usuarios-y-acceso.md §13).
 *
 * It behaves like an `EventSource`: `addEventListener(type, …)` gets a `MessageEvent` with the
 * `data` of each event, and the stream reconnects on its own (sending `Last-Event-ID`) when the
 * server closes it, for example when the access token expires, until `close()` is called.
 */
export interface EventStream {
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void;
  close(): void;
}

export type EventStreamFactory = (url: string) => EventStream;

// Wait before reconnecting after the server closed the stream or the network failed.
const RECONNECT_MS = 1000;

class FetchEventStream implements EventStream {
  private readonly listeners = new Map<string, Set<(event: MessageEvent<string>) => void>>();
  private readonly controller = new AbortController();
  private lastEventId: string | null = null;

  constructor(private readonly url: string) {
    void this.run();
  }

  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)?.add(listener);
  }

  close() {
    this.controller.abort();
  }

  private get closed() {
    return this.controller.signal.aborted;
  }

  private async run() {
    while (!this.closed) {
      try {
        const headers: Record<string, string> = { Accept: "text/event-stream" };
        if (this.lastEventId) headers["Last-Event-ID"] = this.lastEventId;
        const response = await authorizedFetch(this.url, { headers, signal: this.controller.signal });
        // Not found or not allowed: no point in insisting; the page keeps polling with GET.
        if (!response.ok || !response.body) return;
        await this.read(response.body);
      } catch {
        if (this.closed) return;
      }
      await new Promise((resolve) => setTimeout(resolve, RECONNECT_MS));
    }
  }

  private async read(body: ReadableStream<Uint8Array>) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (!this.closed) {
      const { value, done } = await reader.read();
      if (done) return;
      buffer += decoder.decode(value, { stream: true });
      let end = buffer.indexOf("\n\n");
      while (end !== -1) {
        this.dispatch(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
        end = buffer.indexOf("\n\n");
      }
    }
  }

  private dispatch(block: string) {
    let type = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith(":")) continue; // comment, e.g. the server's ping
      const [field, ...rest] = line.split(":");
      const value = rest.join(":").replace(/^ /, "");
      if (field === "event") type = value;
      else if (field === "data") data.push(value);
      else if (field === "id") this.lastEventId = value;
    }
    if (data.length === 0) return;
    const event = new MessageEvent(type, { data: data.join("\n") });
    for (const listener of this.listeners.get(type) ?? []) listener(event);
  }
}

let factory: EventStreamFactory = (url) => new FetchEventStream(url);

/** Opens an event stream of the API. */
export function openEventStream(url: string): EventStream {
  return factory(url);
}

/** Replaces how streams are opened (tests); `null` goes back to `fetch`. */
export function setEventStreamFactory(next: EventStreamFactory | null): void {
  factory = next ?? ((url) => new FetchEventStream(url));
}
