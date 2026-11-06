import type { Flags } from "@/core/Flags";
import type { Inventory } from "@/systems/inventory/Inventory";
import type { SaveData } from "@/systems/saves/SaveData";
import {
  FUSE_IDS,
  LEAK_IDS,
  NOTES,
  SAFE_CODE,
  type FuseId,
  type LeakId,
  type NoteId,
} from "./data/village";

export type VillageStage =
  | "market"
  | "crossing"
  | "clinic"
  | "vault"
  | "memory"
  | "purification"
  | "escape"
  | "dawn"
  | "complete";

/** All chapter gates and rewards survive reloads; no reward can be farmed by repeating a beat. */
export class VillageProgress {
  constructor(
    readonly flags: Flags,
    readonly inventory: Inventory,
  ) {}
  get stage(): VillageStage {
    const f = this.flags;
    if (f.get("ep3.complete", false)) return "complete";
    if (f.get("ep3.escaped", false)) return "dawn";
    if (f.has("ep3.mother.freed")) return "escape";
    if (f.get("ep3.memory.written", false)) return "purification";
    if (f.get("ep3.jar.taken", false)) return "memory";
    if (f.get("ep3.pump.running", false)) return "vault";
    if (f.get("ep3.docked", false)) return "clinic";
    return f.get("ep3.boat.borrowed", false) ? "crossing" : "market";
  }
  get fuses(): number {
    return FUSE_IDS.filter((id) => this.flags.get(`ep3.fuse.${id}`, false)).length;
  }
  get sealed(): number {
    return LEAK_IDS.filter((id) => this.flags.get(`ep3.sealed.${id}`, false)).length;
  }
  get lore(): NoteId[] {
    return (Object.keys(NOTES) as NoteId[]).filter((id) => this.flags.get(`lore.ep3.${id}`, false));
  }
  meet(id: "seller" | "vuthy" | "lok"): boolean {
    if (this.stage !== "market") return false;
    this.flags.set(`ep3.met.${id}`, true);
    return true;
  }
  borrowBoat(): boolean {
    if (
      this.stage !== "market" ||
      !this.flags.get("ep3.met.lok", false) ||
      !this.flags.get("ep3.met.vuthy", false)
    )
      return false;
    this.flags.set("ep3.boat.borrowed", true);
    this.inventory.add("clinic_supplies", 2);
    this.inventory.add("yellow_candle", 4);
    return true;
  }
  dock(): boolean {
    if (this.stage !== "crossing") return false;
    this.flags.set("ep3.docked", true);
    return true;
  }
  seal(id: LeakId): boolean {
    if (
      this.stage !== "clinic" ||
      !LEAK_IDS.includes(id) ||
      this.flags.get(`ep3.sealed.${id}`, false) ||
      !this.inventory.remove("clinic_supplies")
    )
      return false;
    this.flags.set(`ep3.sealed.${id}`, true);
    return true;
  }
  collectFuse(id: FuseId): boolean {
    if (
      this.stage !== "clinic" ||
      !FUSE_IDS.includes(id) ||
      this.flags.get(`ep3.fuse.${id}`, false)
    )
      return false;
    this.flags.set(`ep3.fuse.${id}`, true);
    this.inventory.add("brass_fuse");
    return true;
  }
  startPump(): boolean {
    if (
      this.stage !== "clinic" ||
      this.fuses !== 3 ||
      this.sealed !== 2 ||
      !this.inventory.remove("brass_fuse", 3)
    )
      return false;
    this.flags.set("ep3.pump.running", true);
    return true;
  }
  read(id: NoteId): boolean {
    if (!(id in NOTES) || ["market", "crossing", "memory"].includes(this.stage)) return false;
    if (id === "letter" && !this.flags.get("ep3.safe.open", false)) return false;
    this.flags.set(`lore.ep3.${id}`, true);
    return true;
  }
  get dials(): number[] {
    return SAFE_CODE.map((_, i) => this.flags.get(`ep3.dial.${i}`, 0));
  }
  turnDial(index: number): number {
    if (this.stage !== "vault" || !Number.isInteger(index) || index < 0 || index > 3) return -1;
    const value = (this.dials[index] + 1) % 10;
    this.flags.set(`ep3.dial.${index}`, value);
    return value;
  }
  openSafe(): boolean {
    if (this.stage !== "vault" || !this.dials.every((v, i) => v === SAFE_CODE[i])) return false;
    this.flags.set("ep3.safe.open", true);
    return true;
  }
  takeJar(): boolean {
    if (this.stage !== "vault" || !this.flags.get("ep3.safe.open", false)) return false;
    this.flags.set("ep3.jar.taken", true);
    this.inventory.add("terracotta_jar");
    return true;
  }
  scrapeName(): boolean {
    if (this.stage !== "memory" || this.flags.get("ep3.memory.scraped", false)) return false;
    this.flags.set("ep3.memory.scraped", true);
    return true;
  }
  writeName(): boolean {
    if (this.stage !== "memory" || !this.flags.get("ep3.memory.scraped", false)) return false;
    this.flags.set("ep3.memory.written", true);
    return true;
  }
  pourWater(): boolean {
    if (this.stage !== "purification" || this.flags.get("ep3.ritual.water", false)) return false;
    this.flags.set("ep3.ritual.water", true);
    return true;
  }
  lightCandle(index: number): boolean {
    if (
      this.stage !== "purification" ||
      !this.flags.get("ep3.ritual.water", false) ||
      !Number.isInteger(index) ||
      index < 0 ||
      index > 2 ||
      this.flags.get(`ep3.candle.${index}`, false) ||
      !this.inventory.remove("yellow_candle")
    )
      return false;
    this.flags.set(`ep3.candle.${index}`, true);
    return true;
  }
  get candles(): number {
    return [0, 1, 2].filter((i) => this.flags.get(`ep3.candle.${i}`, false)).length;
  }
  release(free: boolean): boolean {
    if (this.stage !== "purification" || this.candles !== 3) return false;
    if (free && !this.inventory.remove("yellow_candle")) return false;
    this.flags.set("ep3.mother.freed", free);
    this.flags.set("ep3.seal3.broken", true);
    this.flags.set("series.kanha.freed", free);
    if (free) this.flags.increment("series.respect", 2);
    this.inventory.remove("terracotta_jar");
    this.inventory.add("shrine_soil");
    return true;
  }
  escape(): boolean {
    if (this.stage !== "escape") return false;
    this.flags.set("ep3.escaped", true);
    return true;
  }
  finish(): boolean {
    if (this.stage !== "dawn") return false;
    this.inventory.add("brass_compass");
    this.inventory.add("burnt_rubber");
    this.flags.set("ep3.complete", true);
    this.flags.set("series.nextEpisode", 4);
    this.flags.set("series.night", 5);
    return true;
  }
}

export function enterVillage(previous: SaveData): SaveData {
  if (previous.episode !== 2 || previous.flags["ep2.complete"] !== true)
    throw new Error("Complete Episode 2 before entering The Drowned Village.");
  const save = structuredClone(previous);
  save.episode = 3;
  save.checkpoint = "CP0";
  save.clock = "16:30";
  for (const key of Object.keys(save.flags))
    if (key.startsWith("checkpoint.")) delete save.flags[key];
  Object.assign(save.flags, {
    "ep3.checkpoint": "CP0",
    "ep3.clock": "16:30",
    "checkpoint.location": "Tonle Sap · Floating market",
    "series.nextEpisode": 3,
  });
  save.inventory.matches = Math.max(12, save.inventory.matches ?? 0);
  save.inventory.oil = Math.max(3, save.inventory.oil ?? 0);
  save.lamp = { oil: 1, state: "open" };
  save.savedAt = new Date().toISOString();
  return save;
}
