import type { SaveData } from "./SaveData";
import type { SaveStore } from "./SaveStore";

const NAMES: Record<string, string> = {
  CP0: "Studio · Before the journey",
  CP1: "Village · Flooded road",
  CP2: "House · Sok’s open doorway",
  CP3: "House · Sok’s room",
  CP4: "Courtyard · Broken thread",
  CP5: "Under the house · Safe entrance",
  CP6: "Funeral tent · Final ritual",
};
export function checkpointName(save: SaveData): string {
  const name = save.flags["checkpoint.location"];
  return typeof name === "string" && name ? name : (NAMES[save.checkpoint] ?? "Last safe place");
}

/** An immutable retry snapshot, separate from puzzle-progress autosaves. */
export class Checkpoints {
  private snapshot: SaveData | null = null;
  private pending: Promise<void> = Promise.resolve();
  constructor(private readonly store: () => SaveStore) {}
  get last(): SaveData | null {
    return this.snapshot ? structuredClone(this.snapshot) : null;
  }
  async load(fallback: SaveData): Promise<void> {
    const result = await this.store().load("checkpoint");
    const candidate = result.save;
    this.snapshot = structuredClone(
      candidate &&
        candidate.episode === fallback.episode &&
        candidate.flags["game.run"] === fallback.flags["game.run"] &&
        candidate.savedAt <= fallback.savedAt
        ? candidate
        : fallback,
    );
  }
  async mark(data: SaveData, location: string): Promise<SaveData> {
    const saved = structuredClone(data);
    saved.flags["checkpoint.location"] = location;
    saved.savedAt = new Date().toISOString();
    const write = this.pending.then(async () => {
      await this.store().saveCheckpoint(saved);
      this.snapshot = structuredClone(saved);
    });
    this.pending = write.catch(() => undefined);
    await write;
    return saved;
  }
  async prepareRetry(): Promise<SaveData> {
    if (!this.snapshot) throw new Error("No checkpoint is available to retry");
    const saved = structuredClone(this.snapshot);
    await this.store().save("autosave", saved);
    return saved;
  }
}
