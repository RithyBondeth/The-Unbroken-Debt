export type UneasePhase = "waiting" | "hush" | "movement" | "listening" | "recover";

/** Game-time pacing only. Nothing here spawns an enemy, spends items or writes saves. */
export class ForestUnease {
  phase: UneasePhase = "waiting";
  silence = 0;
  sequence = 0;
  private elapsed = 0;
  private wait: number;

  constructor(private readonly random: () => number = Math.random) {
    this.wait = 22 + random() * 16;
  }

  /** Development review can rehearse a sequence through the same state transitions. */
  scheduleSoon(): void {
    if (this.phase === "waiting") this.wait = 0;
  }

  update(dt: number, allowed: boolean, lookingAtSource: boolean): void {
    dt = Math.max(0, Math.min(dt, 0.1));
    if (!allowed) {
      if (this.phase !== "waiting") this.wait = 45 + this.random() * 45;
      this.phase = "waiting";
      this.elapsed = 0;
      this.silence += (0 - this.silence) * (1 - Math.exp(-dt / 0.6));
      return;
    }
    if (this.phase === "waiting") {
      this.silence += (0 - this.silence) * (1 - Math.exp(-dt / 1.2));
      this.wait -= dt;
      if (this.wait > 0) return;
      this.phase = "hush";
      this.elapsed = 0;
      this.sequence++;
    }
    this.elapsed += dt;
    if (this.phase === "hush") {
      this.silence += (0.95 - this.silence) * (1 - Math.exp(-dt / 0.9));
      if (this.elapsed >= 3.2) this.enter(lookingAtSource ? "listening" : "movement");
    } else if (this.phase === "movement") {
      if (lookingAtSource || this.elapsed >= 4.6) this.enter("listening");
    } else if (this.phase === "listening") {
      if (this.elapsed >= 2.6) this.enter("recover");
    } else if (this.phase === "recover") {
      this.silence *= Math.exp(-dt / 1.2);
      if (this.elapsed >= 5) {
        this.enter("waiting");
        this.wait = 75 + this.random() * 65;
      }
    }
  }

  private enter(phase: UneasePhase): void {
    this.phase = phase;
    this.elapsed = 0;
  }
}
