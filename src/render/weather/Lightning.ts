/** Seconds between lightning flashes (Episode 1 Beat Sheet, section 4.1: every 20–40 s). */
const GAP = { min: 20, max: 40 };

/**
 * The storm's rhythm: one to three quick pulses, then darkness for 20–40 s.
 * `level` (0–1) drives whatever each area lights with it.
 */
export class Lightning {
  level = 0;
  private time = 0;
  private nextFlash: number;
  private flash: { start: number; pulses: number[] } | null = null;

  constructor(private readonly random: () => number = Math.random) {
    this.nextFlash = 6 + random() * 6;
  }

  /** True during a flash (thunder follows a few seconds later). */
  get flashing(): boolean {
    return this.flash !== null;
  }

  /** A flash now, for a scripted scare; the rhythm carries on after it. */
  strike(): void {
    this.nextFlash = this.time;
  }

  update(dt: number): number {
    this.time += dt;
    const r = this.random;
    if (!this.flash && this.time >= this.nextFlash) {
      const pulses = [0, 0.09 + r() * 0.08, 0.25 + r() * 0.2].slice(0, 1 + Math.floor(r() * 3));
      this.flash = { start: this.time, pulses };
      this.nextFlash = this.time + GAP.min + r() * (GAP.max - GAP.min);
    }
    let level = 0;
    if (this.flash) {
      const since = this.time - this.flash.start;
      for (const p of this.flash.pulses)
        if (since >= p) level = Math.max(level, Math.exp(-(since - p) / 0.05));
      if (since > 1) this.flash = null;
    }
    this.level = level;
    return level;
  }
}
