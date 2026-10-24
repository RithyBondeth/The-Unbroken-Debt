import type { Flags } from "../../../core/Flags";
import { GOVERNOR } from "../data/investigation";

/** Speed and sustained listening; independent of rendering and audio availability. */
export class GramophoneGovernor {
  rpm: number;
  private steady = 0;

  constructor(private readonly flags: Flags) {
    const saved = flags.get<number>("ep1.gramophone.rpm", GOVERNOR.initial);
    this.rpm = this.solved
      ? GOVERNOR.correct
      : this.clamp(Number.isFinite(saved) ? saved : GOVERNOR.initial);
  }

  get solved(): boolean {
    return this.flags.get("ep1.gramophone.solved", false);
  }
  get clarity(): number {
    return Math.max(0, 1 - Math.abs(this.rpm - GOVERNOR.correct) / 8);
  }

  adjust(steps: number): void {
    if (this.solved) return;
    this.rpm = this.clamp(this.rpm + steps);
    this.steady = 0;
    this.flags.set("ep1.gramophone.rpm", this.rpm);
  }

  /** A quick sweep past the answer cannot solve it; Sora must listen at the right speed. */
  update(dt: number, listening: boolean): boolean {
    if (this.solved) return false;
    this.steady =
      listening && Math.abs(this.rpm - GOVERNOR.correct) <= 0.5 ? this.steady + Math.max(0, dt) : 0;
    if (this.steady < GOVERNOR.holdSeconds) return false;
    this.flags.set("ep1.gramophone.rpm", GOVERNOR.correct);
    this.flags.set("ep1.gramophone.solved", true);
    return true;
  }

  private clamp(rpm: number): number {
    return Math.max(GOVERNOR.min, Math.min(GOVERNOR.max, Math.round(rpm)));
  }
}
