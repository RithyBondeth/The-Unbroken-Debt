import type { EventBus } from "../../core/EventBus";
import type { GameEvents } from "../../core/events";

/**
 * What Sora carries: item id to count (letters 1, matches 10). Items are data
 * (episode files); every change emits `inventory:changed` (TDD section 5).
 */
export class Inventory {
  private readonly items = new Map<string, number>();

  constructor(private readonly bus?: EventBus<GameEvents>) {}

  count(id: string): number {
    return this.items.get(id) ?? 0;
  }

  has(id: string): boolean {
    return this.count(id) > 0;
  }

  add(id: string, count = 1): void {
    this.set(id, this.count(id) + count);
  }

  /** Takes `count` of an item; false (and no change) if there are not enough. */
  remove(id: string, count = 1): boolean {
    if (this.count(id) < count) return false;
    this.set(id, this.count(id) - count);
    return true;
  }

  /** Items held, in the order they were first picked up. */
  list(): [string, number][] {
    return [...this.items].filter(([, n]) => n > 0);
  }

  toJSON(): Record<string, number> {
    return Object.fromEntries(this.list());
  }

  /** Replaces the contents from a save, without emitting events. */
  load(record: Record<string, number>): void {
    this.items.clear();
    for (const [id, n] of Object.entries(record)) if (n > 0) this.items.set(id, n);
  }

  private set(id: string, count: number): void {
    if (count === this.count(id)) return;
    this.items.set(id, count);
    this.bus?.emit("inventory:changed", { itemId: id, count });
  }
}
