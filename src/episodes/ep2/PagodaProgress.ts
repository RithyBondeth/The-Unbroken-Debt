import type { Flags } from "@/core/Flags";
import type { Inventory } from "@/systems/inventory/Inventory";
import type { SaveData } from "@/systems/saves/SaveData";
import {
  ANCESTORS,
  BELL_ORDER,
  MIRROR_TARGETS,
  NOTES,
  type AncestorId,
  type NoteId,
  type Offering,
} from "./data/pagoda";

export type PagodaStage =
  "arrival" | "garden" | "library" | "memory" | "escape" | "dawn" | "complete";

/** Durable episode state. Rewards are idempotent and every gate is derived from saved flags. */
export class PagodaProgress {
  constructor(
    readonly flags: Flags,
    readonly inventory: Inventory,
  ) {}
  get stage(): PagodaStage {
    if (this.flags.get("ep2.complete", false)) return "complete";
    if (this.flags.get("ep2.escaped", false)) return "dawn";
    if (this.flags.has("ep2.memory.choice")) return "escape";
    if (this.flags.get("ep2.archive.open", false)) return "memory";
    if (this.flags.get("ep2.bridge.open", false)) return "library";
    return this.flags.get("ep2.monk.met", false) ? "garden" : "arrival";
  }
  get offerings(): number {
    return ANCESTORS.filter((a) => this.offered(a.id)).length;
  }
  get pretCount(): number {
    return this.stage === "arrival" ? 1 : Math.min(5, 2 + this.offerings);
  }
  get mirrors(): number[] {
    return MIRROR_TARGETS.map((_, i) => this.flags.get(`ep2.mirror.${i}`, 0));
  }
  get mirrorsAligned(): boolean {
    return this.mirrors.every((v, i) => v === MIRROR_TARGETS[i]);
  }
  get lore(): NoteId[] {
    return (Object.keys(NOTES) as NoteId[]).filter((id) => this.flags.get(`lore.ep2.${id}`, false));
  }
  offered(id: AncestorId): boolean {
    return this.flags.get(`ep2.offering.${id}`, false);
  }
  meetMonk(): void {
    if (this.flags.get("ep2.monk.met", false)) return;
    this.flags.set("ep2.monk.met", true);
    this.inventory.add("blessed_thread");
    this.inventory.add("clay_bowl", 4);
  }
  collect(item: Offering | "bowls"): boolean {
    if (this.stage !== "garden" || this.flags.get(`ep2.pickup.${item}`, false)) return false;
    this.flags.set(`ep2.pickup.${item}`, true);
    this.inventory.add(
      item === "bowls" ? "clay_bowl" : item,
      item === "rice" ? 2 : item === "bowls" ? 3 : 1,
    );
    return true;
  }
  offer(id: AncestorId, item: Offering): "placed" | "wrong" | "missing" | "done" | "locked" {
    if (this.stage !== "garden") return "locked";
    if (this.offered(id)) return "done";
    const ancestor = ANCESTORS.find((a) => a.id === id)!;
    // An incorrect suggestion never destroys a required puzzle resource.
    if (ancestor.item !== item) return "wrong";
    if (!this.inventory.remove(item)) return "missing";
    this.flags.set(`ep2.offering.${id}`, true);
    return "placed";
  }
  openBridge(): boolean {
    if (this.offerings !== 4) return false;
    this.flags.set("ep2.bridge.open", true);
    return true;
  }
  ring(bell: number): boolean {
    if (this.stage !== "garden" || bell < 0 || bell > 2) return false;
    if (this.flags.get("ep2.hall.open", false)) return true;
    const previous = this.flags.get("ep2.bells", "");
    const next = previous + bell;
    const solution = BELL_ORDER.join("");
    this.flags.set(
      "ep2.bells",
      solution.startsWith(next) ? next : String(bell) === solution[0] ? String(bell) : "",
    );
    if (next === solution) this.flags.set("ep2.hall.open", true);
    return this.flags.get("ep2.hall.open", false);
  }
  rotateMirror(index: number): number {
    if (this.stage !== "library" || index < 0 || index >= MIRROR_TARGETS.length) return -1;
    const value = (this.mirrors[index] + 1) % 4;
    this.flags.set(`ep2.mirror.${index}`, value);
    return value;
  }
  read(id: NoteId): boolean {
    if (
      (id.startsWith("hall") && !this.flags.get("ep2.hall.open", false)) ||
      (id.startsWith("library") && !this.flags.get("ep2.bridge.open", false))
    )
      return false;
    this.flags.set(`lore.ep2.${id}`, true);
    return true;
  }
  openArchive(): boolean {
    if (this.stage !== "library" || !this.mirrorsAligned) return false;
    this.flags.set("ep2.archive.open", true);
    this.inventory.add("family_record");
    this.inventory.add("silver_betel_box");
    return true;
  }
  remember(choice: number): boolean {
    if (this.stage !== "memory" || ![0, 1, 2].includes(choice)) return false;
    this.flags.set("ep2.memory.choice", choice);
    if (choice === 2) this.reward("honesty");
    return true;
  }
  escape(): boolean {
    if (this.stage !== "escape") return false;
    this.flags.set("ep2.escaped", true);
    return true;
  }
  finish(names: readonly string[]): boolean {
    if (this.stage !== "dawn") return false;
    if (names.join(",") !== ANCESTORS.map((a) => a.id).join(",")) {
      this.flags.set("ep2.names.mistake", true);
      return false;
    }
    this.inventory.remove("silver_betel_box");
    this.inventory.add("silver_inlay");
    this.inventory.add("clinic_photo");
    if (!this.flags.get("ep2.names.mistake", false)) this.reward("names");
    if (!this.flags.get("ep2.rice.wasted", false)) this.reward("offerings");
    this.flags.set("ep2.seal2.broken", true);
    this.flags.set("ep2.complete", true);
    this.flags.set("series.nextEpisode", 3);
    this.flags.set("series.night", 4);
    return true;
  }
  private reward(id: string): void {
    if (this.flags.get(`ep2.respect.${id}`, false)) return;
    this.flags.set(`ep2.respect.${id}`, true);
    this.flags.increment("series.respect");
  }
}

/** Carries the real Episode 1 payload forward without changing its archive or inventing rewards. */
export function enterPagoda(previous: SaveData): SaveData {
  if (previous.episode !== 1 || previous.flags["ep1.complete"] !== true)
    throw new Error("Complete Episode 1 before entering the pagoda.");
  const save = structuredClone(previous);
  save.episode = 2;
  save.checkpoint = "CP0";
  save.clock = "23:45";
  for (const key of Object.keys(save.flags))
    if (key.startsWith("checkpoint.")) delete save.flags[key];
  save.flags["ep2.checkpoint"] = "CP0";
  save.flags["ep2.clock"] = "23:45";
  save.flags["checkpoint.location"] = "Pagoda · Temple gate";
  save.flags["series.nextEpisode"] = 2;
  // New night: Sophal supplies kerosene and matches; retained quest items stay in the satchel.
  save.inventory.matches = Math.max(10, save.inventory.matches ?? 0);
  save.inventory.oil = Math.max(2, save.inventory.oil ?? 0);
  save.lamp = { oil: 1, state: "open" };
  save.savedAt = new Date().toISOString();
  return save;
}
