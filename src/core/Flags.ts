import type { EventBus } from "./EventBus";
import type { GameEvents } from "./events";

export type FlagValue = boolean | number | string;

/**
 * Story state as key-value pairs, e.g. `ep1.betel.done`, `lore.ep1.L1`, `series.respect`.
 * Every change goes through `set` so that `flag:changed` is always emitted.
 */
export class Flags {
  private readonly values = new Map<string, FlagValue>();

  constructor(private readonly bus?: EventBus<GameEvents>) {}

  get<T extends FlagValue>(key: string, fallback: T): T {
    const value = this.values.get(key);
    return value === undefined ? fallback : (value as T);
  }

  has(key: string): boolean {
    return this.values.has(key);
  }

  set(key: string, value: FlagValue): void {
    if (this.values.get(key) === value) return;
    this.values.set(key, value);
    this.bus?.emit("flag:changed", { key, value });
  }

  increment(key: string, by = 1): number {
    const next = this.get(key, 0) + by;
    this.set(key, next);
    return next;
  }

  /** Plain object for saving. */
  toJSON(): Record<string, FlagValue> {
    return Object.fromEntries(this.values);
  }

  /** Replaces all flags from a save, without emitting events. */
  load(record: Record<string, FlagValue>): void {
    this.values.clear();
    for (const [key, value] of Object.entries(record)) this.values.set(key, value);
  }
}
