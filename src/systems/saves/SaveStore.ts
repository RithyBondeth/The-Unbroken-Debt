import { createStore, del, get, set, type UseStore } from "idb-keyval";
import { SaveError, type SaveData } from "./SaveData";
import { migrate } from "./migrations";

/** Save slots: the player's slot and the checkpoint autosave (Technical Design Document, section 13). */
export type SlotName = "slot1" | "autosave" | "episode1";

export interface LoadResult {
  save: SaveData | null;
  /** Why a stored save could not be used (damaged, from a newer game); null if none was stored. */
  problem: SaveError | null;
}

/**
 * Saves in the browser's IndexedDB. While a write is in progress the browser's
 * "leave site?" warning is armed (Controls and Interface, section 10) and
 * `onSaving` lets the screen show the small lamp save indicator.
 */
export class SaveStore {
  private readonly store: UseStore;
  private writes = 0;

  constructor(
    private readonly onSaving: (saving: boolean) => void = () => undefined,
    database = "boon-sop",
  ) {
    this.store = createStore(database, "saves");
  }

  get saving(): boolean {
    return this.writes > 0;
  }

  async save(slot: SlotName, data: SaveData): Promise<void> {
    if (this.writes++ === 0) {
      window.addEventListener("beforeunload", warnLeaving);
      this.onSaving(true);
    }
    try {
      await set(`save.${slot}`, data, this.store);
    } finally {
      if (--this.writes === 0) {
        window.removeEventListener("beforeunload", warnLeaving);
        this.onSaving(false);
      }
    }
  }

  /** Reads and upgrades a slot. A damaged save never throws: it is reported and ignored. */
  async load(slot: SlotName): Promise<LoadResult> {
    const raw: unknown = await get(`save.${slot}`, this.store);
    if (raw === undefined) return { save: null, problem: null };
    try {
      return { save: migrate(raw), problem: null };
    } catch (error) {
      if (error instanceof SaveError) return { save: null, problem: error };
      throw error;
    }
  }

  async clear(slot: SlotName): Promise<void> {
    await del(`save.${slot}`, this.store);
  }

  /** For tests: stores anything under a slot's key, bypassing the checks. */
  async writeRaw(slot: SlotName, value: unknown): Promise<void> {
    await set(`save.${slot}`, value, this.store);
  }
}

function warnLeaving(event: BeforeUnloadEvent): void {
  event.preventDefault();
}
