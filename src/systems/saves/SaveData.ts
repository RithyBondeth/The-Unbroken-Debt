import type { FlagValue } from "../../core/Flags";

/** The save format (Technical Design Document, section 13). Bump it and add a migration when it changes. */
export const SAVE_VERSION = 1;

export interface SaveV1 {
  saveVersion: 1;
  episode: number;
  /** Checkpoint to restart from, e.g. "CP4" (Episode 1 Beat Sheet). */
  checkpoint: string;
  /** In-world time at the checkpoint, "HH:MM". */
  clock: string;
  /** Story flags: `ep1.*`, `lore.*` and the cross-episode `series.*` counters. */
  flags: Record<string, FlagValue>;
  /** Item id to count. */
  inventory: Record<string, number>;
  lamp: { oil: number; state: "open" | "shuttered" | "out" };
  playTimeSec: number;
  /** ISO 8601 time of saving. */
  savedAt: string;
}

/** The current save type; follows `SAVE_VERSION`. */
export type SaveData = SaveV1;

export class SaveError extends Error {
  constructor(
    readonly reason: "format" | "checksum" | "version" | "data",
    message: string,
  ) {
    super(message);
    this.name = "SaveError";
  }
}

/** A fresh Episode 1 game, before the prologue. */
export function newGameSave(now = new Date()): SaveData {
  return {
    saveVersion: 1,
    episode: 1,
    checkpoint: "CP0",
    clock: "20:00",
    flags: {},
    inventory: {},
    lamp: { oil: 1, state: "out" },
    playTimeSec: 0,
    savedAt: now.toISOString(),
  };
}

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

/**
 * Checks that untrusted data (IndexedDB, a pasted code) really is a current
 * save, field by field, so a damaged save can't put the game in a broken state.
 */
export function assertSave(data: unknown): asserts data is SaveData {
  const fail = (what: string): never => {
    throw new SaveError("data", `Save data is damaged: ${what}`);
  };
  if (!isRecord(data)) fail("not an object");
  const d = data as Record<string, unknown>;
  if (d.saveVersion !== SAVE_VERSION) fail(`version ${String(d.saveVersion)}`);
  if (!Number.isInteger(d.episode) || (d.episode as number) < 1 || (d.episode as number) > 5)
    fail("episode");
  if (typeof d.checkpoint !== "string" || !/^CP\d+$/.test(d.checkpoint)) fail("checkpoint");
  if (typeof d.clock !== "string" || !/^\d\d:\d\d$/.test(d.clock)) fail("clock");
  if (!isRecord(d.flags)) fail("flags");
  for (const v of Object.values(d.flags as object)) {
    if (!["boolean", "number", "string"].includes(typeof v)) fail("flag value");
  }
  if (!isRecord(d.inventory)) fail("inventory");
  for (const v of Object.values(d.inventory as object)) {
    if (!Number.isInteger(v) || (v as number) < 0) fail("item count");
  }
  const lamp = d.lamp as Record<string, unknown>;
  if (!isRecord(lamp) || typeof lamp.oil !== "number" || lamp.oil < 0 || lamp.oil > 1)
    fail("lamp oil");
  if (!["open", "shuttered", "out"].includes(lamp.state as string)) fail("lamp state");
  if (typeof d.playTimeSec !== "number" || d.playTimeSec < 0) fail("play time");
  if (typeof d.savedAt !== "string" || Number.isNaN(Date.parse(d.savedAt))) fail("saved at");
}
