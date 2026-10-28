import { vi } from "vitest";

type Listener = (event: MessageEvent<string>) => void;

/**
 * Stand-in for the browser's `EventSource` (jsdom has none): tests open no connection and push
 * the Server-Sent Events themselves with `emit`.
 */
export class FakeEventSource {
  static instances: FakeEventSource[] = [];

  readonly url: string;
  closed = false;
  private readonly listeners = new Map<string, Set<Listener>>();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)?.add(listener);
  }

  close() {
    this.closed = true;
  }

  /** Delivers an event to the listeners of its type, like the server would. */
  emit(type: string, data: unknown) {
    if (this.closed) return;
    const event = new MessageEvent(type, { data: JSON.stringify(data) });
    for (const listener of this.listeners.get(type) ?? []) listener(event);
  }

  /** The stream the app has open for a URL ending like `suffix`. */
  static open(suffix: string): FakeEventSource | undefined {
    return FakeEventSource.instances.find((s) => !s.closed && s.url.endsWith(suffix));
  }
}

/** Replaces `EventSource` for the current test; `setup.ts` restores it. */
export function installFakeEventSource() {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
}
