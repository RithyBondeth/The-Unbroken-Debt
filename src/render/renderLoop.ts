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
