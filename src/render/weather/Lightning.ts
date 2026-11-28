/** Seconds between lightning flashes (Episode 1 Beat Sheet, section 4.1: every 20–40 s). */
const GAP = { min: 20, max: 40 };

/** The farmstead's storm (the user, Nov 21, 2026: rain and lightning, darker): closer together. */
export const FARM_STORM_GAP = { min: 8, max: 20 } as const;

/**
 * The storm's rhythm: one to three quick pulses, then darkness for 20–40 s.
 * `level` (0–1) drives whatever each area lights with it.
 */
export class Lightning {
  level = 0;
  private time = 0;
  private nextFlash: number;
  private flash: { start: number; pulses: number[]; decay: number } | null = null;
  /** The next flash's shape, when a scare sets it (strike). */
  private pattern: { pulses: number[]; decay: number } | null = null;

  constructor(
    private readonly random: () => number = Math.random,
    private readonly gap: { min: number; max: number } = GAP,
  ) {
    this.nextFlash = 6 + random() * 6;
  }

  /** True during a flash (thunder follows a few seconds later). */
  get flashing(): boolean {
    return this.flash !== null;
  }

  /**
   * A flash now, for a scripted scare; the rhythm carries on after it. A scare can give
   * its pulses (seconds after the first) and how fast each dies (s); by default the
   * flash is one to three quick pulses like any other.
   */
  strike(pattern?: { pulses: number[]; decay?: number }): void {
    this.nextFlash = this.time;
    this.pattern = pattern ? { pulses: pattern.pulses, decay: pattern.decay ?? 0.05 } : null;
  }

  update(dt: number): number {
    this.time += dt;
    const r = this.random;
    if (!this.flash && this.time >= this.nextFlash) {
      const pulses = [0, 0.09 + r() * 0.08, 0.25 + r() * 0.2].slice(0, 1 + Math.floor(r() * 3));
      this.flash = { start: this.time, ...(this.pattern ?? { pulses, decay: 0.05 }) };
      this.pattern = null;
      this.nextFlash = this.time + this.gap.min + r() * (this.gap.max - this.gap.min);
    }
    let level = 0;
    const flash = this.flash;
    if (flash) {
      const since = this.time - flash.start;
      for (const p of flash.pulses)
        if (since >= p) level = Math.max(level, Math.exp(-(since - p) / flash.decay));
      if (since > Math.max(1, ...flash.pulses.map((p) => p + 6 * flash.decay))) this.flash = null;
    }
    this.level = level;
    return level;
  }
}
