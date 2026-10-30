import type { Flags } from "../../../core/Flags";

const CORPSE_POSES = 5;
const CORPSE_LOOK_AWAY_SECONDS = 4;

/** A3-02. Each pose must be seen before the next can replace it; changes are instantaneous offscreen. */
export class CorpseProgress {
  constructor(readonly flags: Flags) {}
  get pose(): number {
    return Math.max(0, Math.min(CORPSE_POSES - 1, this.flags.get("ep1.corpse.pose", 0)));
  }
  update(dt: number, observed: boolean, paused: boolean): boolean {
    if (
      !this.flags.get("ep1.act3.started", false) ||
      this.flags.get("ep1.seal1.broken", false) ||
      paused
    )
      return false;
    if (observed) {
      this.flags.set("ep1.corpse.seen", true);
      this.flags.set("ep1.corpse.unseenSeconds", 0);
      return false;
    }
    if (!this.flags.get("ep1.corpse.seen", false) || this.pose >= CORPSE_POSES - 1) return false;
    const unseen = this.flags.get("ep1.corpse.unseenSeconds", 0) + Math.max(0, dt);
    this.flags.set("ep1.corpse.unseenSeconds", Math.min(CORPSE_LOOK_AWAY_SECONDS, unseen));
    if (unseen + 1e-8 < CORPSE_LOOK_AWAY_SECONDS) return false;
    this.flags.set("ep1.corpse.pose", this.pose + 1);
    this.flags.set("ep1.corpse.seen", false);
    this.flags.set("ep1.corpse.unseenSeconds", 0);
    return true;
  }
}
