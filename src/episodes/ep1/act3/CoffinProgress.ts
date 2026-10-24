import type { Flags } from "../../../core/Flags";
export type CoffinPhase = "waiting" | "rattle" | "opening" | "open" | "closing" | "closed";
/** Saved milestones; transient movement resumes safely open after an interrupted scare. */
export class CoffinProgress {
  phase: CoffinPhase;
  elapsed = 0;
  closing = 0;
  seenSeconds = 0;
  constructor(readonly flags: Flags) {
    this.phase = flags.get("ep1.coffin.closed", false)
      ? "closed"
      : flags.get("ep1.coffin.triggered", false)
        ? "open"
        : "waiting";
    if (flags.get("ep1.coffin.revealed", false)) this.seenSeconds = 2;
  }
  get openness(): number {
    if (this.phase === "opening") return Math.min(1, this.elapsed / 0.45);
    if (this.phase === "open") return 1;
    if (this.phase === "closing") return 1 - this.closing / 3;
    return 0;
  }
  update(
    dt: number,
    ready: boolean,
    near: boolean,
    visible: boolean,
    held: boolean,
    paused: boolean,
  ): "rattle" | "bang" | "closed" | null {
    if (paused) return null;
    dt = Math.max(0, Math.min(dt, 0.1));
    if (this.phase === "waiting" && ready && near && visible) {
      this.flags.set("ep1.coffin.triggered", true);
      this.flags.set("ep1.corpse.pose", 0);
      this.phase = "rattle";
      this.elapsed = 0;
      return "rattle";
    }
    if (this.phase === "rattle") {
      this.elapsed += dt;
      if (this.elapsed >= 1.1) {
        this.phase = "opening";
        this.elapsed = 0;
        return "bang";
      }
    } else if (this.phase === "opening") {
      this.elapsed += dt;
      if (this.elapsed >= 0.45) {
        this.phase = "open";
        this.elapsed = 0;
      }
    } else if (this.phase === "open" || this.phase === "closing") {
      if (visible) this.seenSeconds += dt;
      if (this.seenSeconds >= 2) this.flags.set("ep1.coffin.revealed", true);
      if (held && near && this.seenSeconds >= 2) {
        this.phase = "closing";
        this.closing += dt;
      } else {
        this.closing = Math.max(0, this.closing - dt * 2);
        if (this.closing === 0) this.phase = "open";
      }
      if (this.closing >= 3 - 1e-6) {
        this.phase = "closed";
        this.flags.set("ep1.coffin.closed", true);
        return "closed";
      }
    }
    return null;
  }
}
