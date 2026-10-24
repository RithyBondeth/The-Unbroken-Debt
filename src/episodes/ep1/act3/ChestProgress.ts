import type { Flags } from "../../../core/Flags";
import type { Inventory } from "../../../systems/inventory/Inventory";

export const CHEST_ITEMS = ["bronze_token", "seal_map", "folded_slip"] as const;
export type ChestItem = (typeof CHEST_ITEMS)[number];

/** A3-05–06: planks, keyed chest, three independent discoveries; no early slip reveal. */
export class ChestProgress {
  constructor(
    readonly flags: Flags,
    readonly inventory: Inventory,
  ) {}
  get available(): boolean {
    return this.flags.get("ep1.act3.started", false);
  }
  get planksOpen(): boolean {
    return this.flags.get("ep1.chest.planksOpen", false);
  }
  get unlocked(): boolean {
    return this.flags.get("ep1.chest.unlocked", false);
  }
  get ready(): boolean {
    return this.flags.get("ep1.ritual.ready", false);
  }
  taken(item: ChestItem): boolean {
    return this.flags.get(`ep1.chest.${item}.taken`, false);
  }
  liftPlanks(): boolean {
    if (!this.available || this.planksOpen) return false;
    this.flags.set("ep1.chest.planksOpen", true);
    return true;
  }
  unlock(): boolean {
    if (!this.available || !this.planksOpen || this.unlocked || !this.inventory.has("brass_key"))
      return false;
    this.flags.set("ep1.chest.unlocked", true);
    this.inventory.remove("brass_key");
    return true;
  }
  take(item: string): boolean {
    if (
      !CHEST_ITEMS.includes(item as ChestItem) ||
      !this.available ||
      !this.unlocked ||
      this.taken(item as ChestItem)
    )
      return false;
    this.flags.set(`ep1.chest.${item}.taken`, true);
    this.inventory.add(item);
    if (item === "folded_slip") this.flags.set("ep1.slip.unread", true);
    if (CHEST_ITEMS.every((id) => this.taken(id))) {
      this.flags.set("ep1.ritual.ready", true);
      this.flags.set("ep1.clock", "02:45");
    }
    return true;
  }
}
