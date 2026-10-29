import type { Flags } from "../../../core/Flags";
import { passageRequired } from "./VigilPassage";

/** A1-12: an incense cycle may pass even if Sora renews the sticks early. */
export class VigilProgress {
  private elapsed: number;

  constructor(
    private readonly flags: Flags,
    private readonly cycleSeconds: number,
  ) {
    this.elapsed = flags.get("ep1.vigil.seconds", 0);
  }

  update(dt: number): void {
    if (!this.flags.get("ep1.vigil.started", false) || this.flags.get("ep1.act2.started", false))
      return;
    this.elapsed += dt;
    if (this.elapsed >= this.cycleSeconds) this.flags.set("ep1.incense.cyclePassed", true);
  }

  ready(underTent: boolean, handsFree: boolean): boolean {
    return (
      underTent &&
      handsFree &&
      !passageRequired(this.flags) &&
      this.flags.get("ep1.betel.done", false) &&
      (!this.flags.get("ep1.arrival.phoneFlow", false) ||
        this.flags.get("ep1.arrival.matchesTaken", false)) &&
      this.flags.get("ep1.incense.cyclePassed", false) &&
      !this.flags.get("ep1.act2.started", false)
    );
  }

  save(): void {
    this.flags.set("ep1.vigil.seconds", this.elapsed);
  }
}
