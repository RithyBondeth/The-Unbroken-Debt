import type { AbstractEngine } from "@babylonjs/core/Engines/abstractEngine";

export interface RenderLoopOptions {
  /** Called once frames have failed back to back for a while. The loop keeps retrying. */
  onStall?: (error: unknown) => void;
  /** Called when a frame renders again after `onStall`. */
  onRecover?: () => void;
}

/**
 * Runs `render` every frame, and keeps the loop alive when a frame throws.
 *
 * Babylon's own loop has no guard: an exception skips `endFrame()` and the
 * request for the next frame, so one bad frame freezes the game on a black
 * canvas for good (the SSAO first-frame bug). Here a throwing frame is logged
 * and the next one is tried as usual (createEngine makes sure a bind group the
 * throw left half-built doesn't break the frames after it). Each distinct error
 * is logged once, with a summary when frames render again.
 *
 * Frames that keep failing don't stop the loop: the failure we know of (a
 * shader chunk arriving late) clears by itself, after as long as the network
 * takes. After two seconds `onStall` lets the caller show that something is
 * wrong instead of a silent black screen.
 *
 * @returns stops the loop
 */
export function runRenderLoop(
  engine: AbstractEngine,
  render: () => void,
  options: RenderLoopOptions = {},
): () => void {
  const failures = new FrameFailures();
  const frame = () => {
    try {
      render();
    } catch (error) {
      const result = failures.failed(error, performance.now());
      if (result.log) {
        console.error(
          `[render] A frame failed (#${failures.frames} in a row); the loop keeps going. Repeats of this error are not logged.`,
          error,
        );
      }
      if (result.limitReached) {
        console.error(
          `[render] ${MAX_LOGGED_ERRORS} different errors so far; not logging new ones.`,
        );
      }
      if (result.stalled) {
        console.warn(`[render] Frames have failed for ${STALL_MS / 1000} s; still retrying.`);
        options.onStall?.(error);
      }
      return;
    }
    const streak = failures.rendered(performance.now());
    if (streak) {
      console.warn(
        `[render] Rendering again after ${streak.frames} failed frame${streak.frames === 1 ? "" : "s"} (${(streak.ms / 1000).toFixed(2)} s).`,
      );
      if (streak.stalled) options.onRecover?.();
    }
  };
  engine.runRenderLoop(frame);
  return () => engine.stopRenderLoop(frame);
}

/** Different errors logged before new ones go unlogged (in case a message changes every frame). */
export const MAX_LOGGED_ERRORS = 20;

/** Back-to-back failing time before the loop counts as stalled. */
const STALL_MS = 2000;

/** Longer gaps between frames are a hidden tab or a debugger pause, not failing time. */
const MAX_GAP_MS = 250;

export interface FailedStreak {
  frames: number;
  ms: number;
  /** Whether the streak lasted long enough to count as a stall. */
  stalled: boolean;
}

/**
 * Bookkeeping for failing frames: which errors were already logged and how
 * long frames have been failing in a row. Pure logic so it can be unit-tested.
 */
export class FrameFailures {
  /** Failed frames in the current streak (0 while frames render). */
  frames = 0;
  private ms = 0;
  private last = 0;
  private stalled = false;
  private readonly logged = new Set<string>();

  constructor(private readonly stallMs = STALL_MS) {}

  /**
   * Records a frame that threw.
   * @returns whether to log this error (the first time it is seen), whether
   * the log limit was reached just now, and whether the stall began on this frame
   */
  failed(error: unknown, now: number): { log: boolean; limitReached: boolean; stalled: boolean } {
    if (this.frames > 0) this.ms += Math.min(now - this.last, MAX_GAP_MS);
    this.frames++;
    this.last = now;

    const key = errorKey(error);
    let log = false;
    let limitReached = false;
    if (!this.logged.has(key) && this.logged.size < MAX_LOGGED_ERRORS) {
      this.logged.add(key);
      log = true;
      limitReached = this.logged.size === MAX_LOGGED_ERRORS;
    }

    const stalled = !this.stalled && this.ms >= this.stallMs;
    if (stalled) this.stalled = true;
    return { log, limitReached, stalled };
  }

  /**
   * Records a frame that rendered.
   * @returns the failing streak this frame ended, or null if the last frame was fine too
   */
  rendered(now: number): FailedStreak | null {
    if (this.frames === 0) return null;
    const streak = {
      frames: this.frames,
      ms: this.ms + Math.min(now - this.last, MAX_GAP_MS),
      stalled: this.stalled,
    };
    this.frames = 0;
    this.ms = 0;
    this.stalled = false;
    return streak;
  }
}

/** Errors count as the same when their type and message match. */
function errorKey(error: unknown): string {
  if (error instanceof Error) return `${error.name}: ${error.message}`;
  return String(error);
}

/**
 * Display refreshes per rendered frame: at a 60 fps target, every refresh up to
 * about 75 Hz and every second one on 120–165 Hz panels (60–82 fps); at 30 fps,
 * every second refresh at 60 Hz. A target of 0 renders every refresh. Pure, for tests.
 */
export function refreshesPerFrame(refreshMs: number, targetMs = 1000 / 60): number {
  if (!(refreshMs > 0)) return 1;
  return Math.max(1, Math.floor(targetMs / refreshMs + 0.1));
}

/**
 * Steady frame pacing on high-refresh displays, and the frame-rate cap (the
 * engine's frame requester).
 *
 * On a 120 Hz MacBook the studio took 8 ms on some frames and just over 8 ms on
 * others, so frames alternated between 8.3 and 16.7 ms on screen: the picture
 * shook as the player turned (November 2026). Rendering on every second refresh
 * gives an even 16.7 ms instead. The same holds a 30 fps cap on a phone: every
 * second refresh at 60 Hz, every fourth at 120 Hz. The engine's own clock (delta
 * time, animation ratio, particles) only sees rendered frames, so nothing runs
 * slow. A target of 0 (`?fps=max`, or "Unlimited" in the settings) renders every refresh.
 */
export class FramePacer {
  /** Read and written by Babylon to cancel the loop. */
  requestID?: number;
  private every = 1;
  private lastRender = 0;
  private refreshMs = 0;
  private readonly samples: number[] = [];
  private lastTick = 0;
  private targetMs: number;

  /** @param targetFps frames per second to aim for; 0 renders on every refresh */
  constructor(targetFps = 60) {
    this.targetMs = targetFps > 0 ? 1000 / targetFps : 0;
  }

  readonly requestAnimationFrame = (render: FrameRequestCallback): number => {
    const tick = (now: number) => {
      this.measure(now);
      if (!this.due(now)) {
        this.requestID = window.requestAnimationFrame(tick);
        return;
      }
      this.lastRender = now;
      render(now);
    };
    this.requestID = window.requestAnimationFrame(tick);
    return this.requestID;
  };

  readonly cancelAnimationFrame = (id: number): void => {
    window.cancelAnimationFrame(this.requestID ?? id);
  };

  /** Refreshes per rendered frame now in use. */
  get interval(): number {
    return this.every;
  }

  /** Frames per second aimed for (0: every refresh). Can change while playing. */
  set targetFps(fps: number) {
    this.targetMs = fps > 0 ? 1000 / fps : 0;
    if (this.refreshMs > 0) this.every = refreshesPerFrame(this.refreshMs, this.targetMs);
  }

  /** Frame budget the pacing gives, in ms, once the display has been measured. */
  get frameMs(): number {
    return this.refreshMs > 0 ? this.refreshMs * this.every : this.targetMs || 1000 / 60;
  }

  /**
   * By time, not by counting callbacks: a frame that overran a refresh produces
   * no callback for it, and counting would then skip a whole extra frame (a 30 fps
   * cap falling to 20). Half a refresh of slack absorbs callback timing jitter.
   */
  private due(now: number): boolean {
    if (this.every <= 1 || this.lastRender === 0) return true;
    return now - this.lastRender >= this.frameMs - this.refreshMs * 0.5;
  }

  /** Measures the display's refresh interval over the first second, then fixes the pace. */
  private measure(now: number): void {
    if (this.samples.length >= 60) return;
    if (this.lastTick > 0) this.samples.push(now - this.lastTick);
    this.lastTick = now;
    if (this.samples.length === 60) {
      const sorted = [...this.samples].sort((a, b) => a - b);
      // Refreshes are skipped once pacing starts, so measure while it is off.
      this.refreshMs = sorted[Math.floor(sorted.length * 0.25)];
      this.every = refreshesPerFrame(this.refreshMs, this.targetMs);
    }
  }
}
