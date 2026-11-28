export interface GovernorOptions {
  /** Frame budget in ms (16.7 for 60 fps, 33.3 under a 30 fps cap). */
  targetMs: number;
  minScale: number;
  maxScale?: number;
  /** Smallest change per adjustment. */
  step?: number;
}

/** Load the governor aims for after lowering (fraction of the budget). */
const AIM_LOAD = 0.85;
/** With GPU timing, step up only while the GPU stays below this share of the budget… */
const HEADROOM_LOAD = 0.7;
/** …and only if the predicted load after the step stays below this one. */
const RAISE_CEILING = 0.85;
/** Seconds between any two changes: each one rebuilds every render target. */
const COOLDOWN = 0.6;
/** Largest single change: a bigger jump would be a visible pop in sharpness. */
const MAX_JUMP = 0.2;

/**
 * Chooses the render scale to hold the frame budget (dynamic resolution).
 * Pure logic so it can be unit-tested.
 *
 * Every change resizes every render target (SSAO, fog, TAA history, bloom), a
 * hitch of its own that also restarts TAA, so the governor changes the scale as
 * rarely as it can: it drops straight to the scale it predicts will fit (pixel
 * cost grows with the square of the scale) instead of stepping down frame after
 * frame, and only steps up when the step is predicted to fit too.
 *
 * With GPU timing it reacts to real GPU load in both directions, and leaves the
 * resolution alone when the CPU is the bottleneck. Without it the browser caps
 * frame time at the display refresh, so headroom is invisible: the governor
 * drops on missed frames and then "probes" upwards now and then, waiting longer
 * each time a probe fails (up to a minute).
 */
export class ResolutionGovernor {
  scale: number;
  targetMs: number;
  private readonly minScale: number;
  private maxScale: number;
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

  /** Back to the top scale with fresh timing, e.g. once loading's shader compiles are over. */
  reset(): void {
    this.scale = Math.max(this.floor, this.maxScale);
    this.smoothedMs = this.targetMs;
    this.cooldown = 0;
    this.headroomTime = 0;
    this.overTime = 0;
    this.sinceProbe = Infinity;
    this.probeInterval = 3;
  }

  /** The highest scale allowed (the player's resolution setting). */
  setMaxScale(max: number): void {
    this.maxScale = Math.max(this.minScale, Math.min(1, max));
    if (this.floor > this.maxScale) this.floor = this.maxScale;
    if (this.scale > this.maxScale) this.scale = this.maxScale;
    this.probeInterval = 3;
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
        this.lower(gpuMs !== null ? load : null);
        // A probe that caused this means the last scale was the limit: wait longer next time.
        if (this.sinceProbe < 2) this.probeInterval = Math.min(this.probeInterval * 2, 60);
        this.overTime = 0;
      }
      return this.scale;
    }
    this.overTime = 0;

    if (gpuMs !== null) {
      // Real headroom: step up after a while of light load, if the step will fit.
      this.headroomTime = load < HEADROOM_LOAD ? this.headroomTime + dt : 0;
      if (this.headroomTime > 1.5 && this.cooldown === 0 && this.scale < this.maxScale) {
        this.raise(load);
        this.headroomTime = 0;
      }
    } else {
      // No GPU timer: probe upwards occasionally.
      this.headroomTime += dt;
      if (
        this.headroomTime > this.probeInterval &&
        this.cooldown === 0 &&
        this.scale < this.maxScale
      ) {
        this.raise(null);
        this.headroomTime = 0;
        this.sinceProbe = 0;
      }
      // A probe that held for a few seconds means the scale fits: probe promptly again.
      if (this.sinceProbe > 4 && this.sinceProbe < 4 + dt) this.probeInterval = 3;
    }
    return this.scale;
  }

  private get lowest(): number {
    return Math.max(this.minScale, this.floor);
  }

  /**
   * Down to the scale predicted to fit (GPU cost ∝ pixels ∝ scale²), at least
   * one step and at most MAX_JUMP. Without a GPU timer the load only says that
   * frames were missed, not by how much: one step.
   */
  private lower(load: number | null): void {
    let next = this.scale - this.step;
    if (load !== null) {
      const fit = this.scale * Math.sqrt(AIM_LOAD / load);
      next = Math.min(next, Math.max(fit, this.scale - MAX_JUMP));
    }
    this.scale = Math.max(this.lowest, snapDown(next, this.step));
    this.cooldown = COOLDOWN;
  }

  /** Up one step, or two when the GPU is nearly idle, as long as the result is predicted to fit. */
  private raise(load: number | null): void {
    let next = this.scale + this.step;
    if (load !== null) {
      const room = this.scale * Math.sqrt(RAISE_CEILING / Math.max(load, 0.01));
      if (room < next) return; // the next step would not fit: stay
      next = Math.min(room, this.scale + 2 * this.step);
    }
    this.scale = Math.min(this.maxScale, snapDown(next, this.step));
    this.cooldown = COOLDOWN;
  }
}

/** Rounds down to the step grid, so the same few scales come back instead of new sizes. */
function snapDown(value: number, step: number): number {
  return Math.round(Math.floor(value / step + 1e-6) * step * 1000) / 1000;
}
