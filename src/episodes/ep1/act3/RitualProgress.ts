import type { Flags } from "../../../core/Flags";
import type { Inventory } from "../../../systems/inventory/Inventory";

export const RITUAL_SECONDS = 25;
export const RITUAL_TURN_LIMIT = (100 * Math.PI) / 180;

/** A3-07–08. Durable costs, but never resume a half-finished hold after loading. */
export class RitualProgress {
  elapsed = 0;
  active = false;
  constructor(
    readonly flags: Flags,
    readonly inventory: Inventory,
  ) {}
  get ready(): boolean {
    return this.flags.get("ep1.ritual.ready", false);
  }
  get placed(): boolean {
    return this.flags.get("ep1.ritual.tokenPlaced", false);
  }
  get broken(): boolean {
    return this.flags.get("ep1.seal1.broken", false);
  }
  place(): boolean {
    if (!this.ready || this.placed || this.broken || !this.inventory.has("bronze_token"))
      return false;
    this.flags.set("ep1.ritual.tokenPlaced", true);
    this.flags.set("ep1.checkpoint", "CP6");
    this.flags.set("ep1.clock", "02:50");
    return true;
  }
  start(): boolean {
    if (!this.placed || this.active || this.broken || !this.inventory.remove("blessed_matches"))
      return false;
    this.active = true;
    this.elapsed = 0;
    this.flags.increment("ep1.ritual.attempts");
    return true;
  }
  spare(): boolean {
    if (
      !this.ready ||
      !this.placed ||
      this.broken ||
      this.active ||
      this.inventory.has("blessed_matches")
    )
      return false;
    this.inventory.add("blessed_matches");
    this.flags.increment("ep1.ritual.spares");
    return true;
  }
  update(dt: number, angle: number, paused = false): "failed" | "broken" | null {
    if (!this.active || paused) return null;
    if (Math.abs(angle) > RITUAL_TURN_LIMIT) {
      this.active = false;
      this.elapsed = 0;
      this.flags.increment("ep1.ritual.failures");
      return "failed";
    }
    this.elapsed += Math.max(0, dt);
    if (this.elapsed + 1e-8 < RITUAL_SECONDS) return null;
    this.active = false;
    this.flags.set("ep1.seal1.broken", true);
    this.flags.set("ep1.clock", "03:00");
    this.inventory.remove("bronze_token");
    return "broken";
  }
}
