export interface GovernorOptions {
  /** Frame budget in ms (16.7 for 60 fps). */
  targetMs: number;
  minScale: number;
  maxScale?: number;
  /** Change per adjustment. */
  step?: number;
}

/**
 * Chooses the render scale each frame to hold the frame budget (dynamic
 * resolution). Pure logic so it can be unit-tested.
 *
 * With GPU timing it reacts to real GPU load in both directions. Without it,
 * the browser caps frame time at the display refresh, so headroom is invisible:
 * the governor drops on missed frames and then "probes" upwards now and then,
 * backing off for longer each time a probe causes misses.
 */
export class ResolutionGovernor {
  scale: number;
  private readonly targetMs: number;
  private readonly minScale: number;
  private readonly maxScale: number;
  private readonly step: number;

  private smoothedMs: number;
  private cooldown = 0;
  private headroomTime = 0;
  private overTime = 0;
  private sinceProbe = Infinity;
  private probeInterval = 3;
  /** Temporary lower limit, e.g. while the sketchbook is open. */
  private floor = 0;

  constructor(options: GovernorOptions) {
    this.targetMs = options.targetMs;
    this.minScale = options.minScale;
    this.maxScale = options.maxScale ?? 1;
    this.step = options.step ?? 0.05;
    this.scale = this.maxScale;
    this.smoothedMs = options.targetMs;
  }

  /**
   * Holds the scale at or above `floor` until released with `null`: text on the
   * sketchbook's pages blurs below about 85% of 900p (Spike S5), and reading is
   * a calm moment where a few missed frames matter less than legible text.
   */
  setFloor(floor: number | null): void {
    this.floor = floor === null ? 0 : Math.min(this.maxScale, floor);
    if (this.scale < this.floor) this.scale = this.floor;
  }

  /**
   * @param frameMs time since the last frame
   * @param gpuMs GPU time for the frame, or null when the browser can't measure it
   * @returns the render scale to use
   */
  update(frameMs: number, gpuMs: number | null): number {
    // Frames this long mean a hidden tab, a debugger pause or a loading stall,
    // not rendering load: ignore them.
    if (frameMs > 250) return this.scale;
    const dt = frameMs / 1000;
    const sample = gpuMs ?? frameMs;
    // Smooth over roughly a quarter of a second so single hitches don't react.
    this.smoothedMs += (sample - this.smoothedMs) * Math.min(1, dt / 0.25);
    this.cooldown = Math.max(0, this.cooldown - dt);
    this.sinceProbe += dt;

    const load = this.smoothedMs / this.targetMs;
    const limit = gpuMs !== null ? 0.95 : 1.15;
    // Both this frame and the recent average must be over: after a one-frame
    // hitch the average stays high for a moment, but the frames are fine again.
    const overBudget = load > limit && sample / this.targetMs > limit;

    if (overBudget) {
      this.headroomTime = 0;
      this.overTime += dt;
      // React to sustained load (0.2 s), not to a single hitch.
      if (this.overTime >= 0.2 && this.cooldown === 0 && this.scale > this.lowest) {
        this.lower();
        // A probe that caused this means the last scale was the limit: wait longer next time.
        if (this.sinceProbe < 1.5) this.probeInterval = Math.min(this.probeInterval * 2, 30);
      }
      return this.scale;
    }
    this.overTime = 0;

    if (gpuMs !== null) {
      // Real headroom: step up after a second of light load.
      this.headroomTime = load < 0.75 ? this.headroomTime + dt : 0;
      if (this.headroomTime > 1 && this.scale < this.maxScale) {
        this.raise();
        this.headroomTime = 0;
      }
    } else {
      // No GPU timer: probe upwards occasionally.
      this.headroomTime += dt;
      if (this.headroomTime > this.probeInterval && this.scale < this.maxScale) {
        this.raise();
        this.headroomTime = 0;
        this.sinceProbe = 0;
      }
      if (this.sinceProbe > 1.5 && this.sinceProbe < 1.5 + dt) this.probeInterval = 3;
    }
    return this.scale;
  }

  private get lowest(): number {
    return Math.max(this.minScale, this.floor);
  }

  private lower(): void {
    this.scale = Math.max(this.lowest, round(this.scale - this.step));
    this.cooldown = 0.3;
  }

  private raise(): void {
    this.scale = Math.min(this.maxScale, round(this.scale + this.step));
    this.cooldown = 0.3;
  }
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
