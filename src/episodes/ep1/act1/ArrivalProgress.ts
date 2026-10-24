import type { Flags } from "../../../core/Flags";

/** Durable arrival state; an interrupted call starts again without granting items. */
export class ArrivalProgress {
  constructor(private readonly flags: Flags) {
    if (!flags.has("ep1.arrival.phoneFlow") && !flags.get("ep1.vigil.started", false))
      flags.set("ep1.arrival.phoneFlow", true);
    if (!flags.get("ep1.resolution.started", false)) flags.set("ep1.vuthy.left", true);
  }
  get called(): boolean {
    return (
      this.flags.get("ep1.arrival.callComplete", false) ||
      this.flags.get("ep1.vigil.started", false)
    );
  }
  get taken(): boolean {
    return (
      this.flags.get("ep1.arrival.matchesTaken", false) ||
      (!this.flags.get("ep1.arrival.phoneFlow", false) && this.flags.get("ep1.betel.done", false))
    );
  }
  finishCall(): void {
    this.flags.set("ep1.arrival.callComplete", true);
    this.flags.set("ep1.vigil.started", true);
  }
  takeMatches(): boolean {
    if (this.taken) return false;
    this.flags.set("ep1.arrival.matchesTaken", true);
    return true;
  }
}
