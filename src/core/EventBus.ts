export type EventHandler<T> = (payload: T) => void;

/**
 * Typed publish/subscribe channel. Systems talk to each other only through
 * events and the flag store, never by importing each other (TDD section 1).
 */
export class EventBus<Events extends Record<string, unknown>> {
  private readonly handlers = new Map<keyof Events, Set<EventHandler<never>>>();

  /** Subscribes to an event. Returns a function that unsubscribes. */
  on<K extends keyof Events>(type: K, handler: EventHandler<Events[K]>): () => void {
    let set = this.handlers.get(type);
    if (!set) {
      set = new Set();
      this.handlers.set(type, set);
    }
    set.add(handler);
    return () => this.off(type, handler);
  }

  off<K extends keyof Events>(type: K, handler: EventHandler<Events[K]>): void {
    this.handlers.get(type)?.delete(handler);
  }

  /** Calls every handler. A failing handler is logged and never stops the others. */
  emit<K extends keyof Events>(type: K, payload: Events[K]): void {
    const set = this.handlers.get(type);
    if (!set) return;
    for (const handler of [...set]) {
      try {
        (handler as EventHandler<Events[K]>)(payload);
      } catch (error) {
        console.error(`[EventBus] handler for "${String(type)}" failed`, error);
      }
    }
  }

  clear(): void {
    this.handlers.clear();
  }
}
