import type { Flags } from "../../../core/Flags";
import type { Inventory } from "../../../systems/inventory/Inventory";

export const PORTRAIT_TIMEOUT = 120;

/** A2-07–10 → A3-01. Story changes are durable and cannot award items twice. */
export class DeskProgress {
  constructor(
    readonly flags: Flags,
    private readonly inventory: Inventory,
  ) {}

  get available(): boolean {
    return this.flags.get("ep1.walker.complete", false);
  }
  get compartmentOpen(): boolean {
    return this.flags.get("ep1.altar.compartmentOpen", false);
  }
  get keyTaken(): boolean {
    return this.flags.get("ep1.desk.keyTaken", false);
  }
  get drawerOpen(): boolean {
    return this.flags.get("ep1.desk.open", false);
  }
  get journalRead(): boolean {
    return this.flags.get("ep1.journalB.read", false);
  }
  get portraitAwake(): boolean {
    return this.flags.get("ep1.portrait.awake", false);
  }
  get actThree(): boolean {
    return this.flags.get("ep1.act3.started", false);
  }

  openCompartment(): boolean {
    if (!this.available || this.compartmentOpen) return false;
    this.flags.set("ep1.altar.compartmentOpen", true);
    return true;
  }

  takeKey(): boolean {
    if (!this.available || !this.compartmentOpen || this.keyTaken) return false;
    this.flags.set("ep1.desk.keyTaken", true);
    this.inventory.add("drawer_key");
    return true;
  }

  unlockDesk(): boolean {
    if (!this.available || this.drawerOpen || !this.inventory.remove("drawer_key")) return false;
    this.flags.set("ep1.desk.open", true);
    return true;
  }

  readJournal(): boolean {
    if (!this.drawerOpen || this.journalRead) return false;
    this.flags.set("ep1.journalB.read", true);
    this.inventory.add("sok_journal_b");
    this.flags.set("ep1.clock", "01:35");
    return true;
  }

  /** The return beat and the snap happen under the tent, with the player's hands free. */
  update(
    dt: number,
    underTent: boolean,
    handsFree: boolean,
    incenseAlive: boolean,
  ): "portrait" | "snap" | null {
    if (!this.available || !this.journalRead || !handsFree || this.actThree) return null;
    if (!this.portraitAwake) {
      if (!underTent) return null;
      this.flags.set("ep1.portrait.awake", true);
      this.flags.set("ep1.incense.scripted", true);
      this.flags.set("ep1.portrait.seconds", 0);
      this.flags.set("ep1.clock", "01:40");
      return "portrait";
    }
    const seconds = this.flags.get("ep1.portrait.seconds", 0) + Math.max(0, dt);
    this.flags.set("ep1.portrait.seconds", seconds);
    // A short breath separates the scare from an immediate relight. The timeout
    // can expire away from the tent, but CP4 only begins when Sora returns to it.
    if (!underTent || seconds < 3 || (!incenseAlive && seconds < PORTRAIT_TIMEOUT)) return null;
    this.flags.set("ep1.act2.complete", true);
    this.flags.set("ep1.act3.started", true);
    this.flags.set("ep1.thread.broken", true);
    this.flags.set("ep1.act3.seconds", 0);
    this.flags.set("ep1.checkpoint", "CP4");
    this.flags.set("ep1.clock", "02:00");
    return "snap";
  }
}
