import type { Flags } from "../../../core/Flags";
import type { Inventory } from "../../../systems/inventory/Inventory";
import { JARS, FRAGMENT_IDS } from "../data/hunt";

/** Durable jar contents and a single, atomic three-piece key recipe. */
export class HuntProgress {
  constructor(
    readonly flags: Flags,
    readonly inventory: Inventory,
  ) {}
  get available(): boolean {
    return this.flags.get("ep1.act3.started", false);
  }
  get started(): boolean {
    return this.flags.get("ep1.hunt.started", false);
  }
  get assembled(): boolean {
    return this.flags.get("ep1.brassKey.assembled", false);
  }
  get pieces(): number {
    return FRAGMENT_IDS.filter((id) => this.inventory.has(id)).length;
  }
  open(id: string): boolean {
    if (
      !this.available ||
      !this.started ||
      this.flags.get(`ep1.jar.${id}.open`, false) ||
      !JARS.some((j) => j.id === id)
    )
      return false;
    this.flags.set(`ep1.jar.${id}.open`, true);
    return true;
  }
  take(id: string): boolean {
    const jar = JARS.find((j) => j.id === id);
    if (
      !jar ||
      !this.available ||
      !this.started ||
      !this.flags.get(`ep1.jar.${id}.open`, false) ||
      this.flags.get(`ep1.jar.${id}.taken`, false)
    )
      return false;
    this.flags.set(`ep1.jar.${id}.taken`, true);
    if (jar.contents === "key") this.inventory.add(FRAGMENT_IDS[jar.piece]);
    else if (jar.contents === "oil") this.inventory.add("oil");
    else {
      this.flags.set("lore.ep1.L2", true);
      this.flags.increment("ep1.lore");
    }
    if (this.pieces === 3) {
      this.flags.set("ep1.fragments.3", true);
      this.flags.set("ep1.clock", "02:30");
    }
    return true;
  }
  assemble(): boolean {
    if (!this.available || this.assembled || this.pieces !== 3) return false;
    // Validate all three before emitting any inventory changes.
    this.flags.set("ep1.brassKey.assembled", true);
    for (const id of FRAGMENT_IDS) this.inventory.remove(id);
    this.inventory.add("brass_key");
    this.flags.set("ep1.clock", "02:35");
    return true;
  }
}
