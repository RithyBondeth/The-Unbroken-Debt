import type { AbstractEngine } from "@babylonjs/core/Engines/abstractEngine";
import type { Observer } from "@babylonjs/core/Misc/observable";
import type { QualityPreset } from "./qualityPresets";
import { ResolutionGovernor } from "./ResolutionGovernor";

export interface DynamicResolutionOptions {
  /** Scale the resolution to hold the frame rate (otherwise it stays at `maxScale`). */
  enabled?: boolean;
  /** GPU time of the last measured frame in ms, or null when the browser can't measure it. */
  gpuMs?: () => number | null;
  /** Frame budget in ms: 16.7 at 60 fps, 33.3 under a 30 fps cap. */
  targetMs?: number;
  /** The player's resolution setting: the highest share of the preset's height to render. */
  maxScale?: number;
}

/**
 * Sets the internal render resolution: capped at the preset's height (a
 * Retina laptop's native 3024×1964 is far more than the game needs) and, when
 * enabled, scaled down and up to hold the frame rate. The image is upscaled to
 * the canvas; TAA hides most of the softness.
 *
 * The canvas size comes from a ResizeObserver rather than from reading
 * `clientHeight` each frame: that read forced the browser to lay out the page
 * whenever a hint or subtitle had changed it, in the middle of a frame.
 */
export class DynamicResolution {
  readonly governor: ResolutionGovernor;
  private _enabled: boolean;
  private fixedScale: number;
  private floor = 0;
  private readonly observer: Observer<AbstractEngine>;
  private readonly resizeObserver: ResizeObserver | null = null;
  private cssHeight = 0;
  private level = 0;

  constructor(
    private readonly engine: AbstractEngine,
    private readonly preset: QualityPreset,
    options: DynamicResolutionOptions = {},
  ) {
    this._enabled = options.enabled ?? true;
    this.fixedScale = clampScale(options.maxScale ?? 1);
    this.governor = new ResolutionGovernor({
      targetMs: options.targetMs ?? 1000 / 60,
      minScale: Math.min(preset.minRenderScale, this.fixedScale),
      maxScale: this.fixedScale,
    });
    const gpuMs = options.gpuMs ?? (() => null);
    this.observer = engine.onEndFrameObservable.add(() => {
      if (this._enabled) this.governor.update(engine.getDeltaTime(), gpuMs());
      this.apply();
    });

    const canvas = engine.getRenderingCanvas();
    if (canvas) {
      this.cssHeight = canvas.clientHeight;
      if (typeof ResizeObserver !== "undefined") {
        this.resizeObserver = new ResizeObserver((entries) => {
          const box = entries[entries.length - 1]?.contentRect;
          this.cssHeight = box ? box.height : canvas.clientHeight;
          this.apply();
        });
        this.resizeObserver.observe(canvas);
      }
    }
    this.apply();
  }

  /** Current render scale relative to the preset's capped height (1 = full). */
  get scale(): number {
    return this._enabled ? this.governor.scale : Math.max(this.fixedScale, this.floor);
  }

  get enabled(): boolean {
    return this._enabled;
  }

  set enabled(value: boolean) {
    this._enabled = value;
    this.apply();
  }

  /** Changes the frame budget (the frame-rate setting) while playing. */
  set targetMs(ms: number) {
    this.governor.targetMs = ms;
  }

  /** Changes the player's resolution setting while playing. */
  set maxScale(scale: number) {
    this.fixedScale = clampScale(scale);
    this.governor.setMaxScale(this.fixedScale);
    this.apply();
  }

  /** Starts measuring afresh at the top scale (after loading and warm-up). */
  restart(): void {
    this.governor.reset();
    this.apply();
  }

  /**
   * While text must stay sharp (the sketchbook is open), never drop below this
   * share of the preset's height; `null` releases it. Spike S5: 0.85.
   */
  holdAtLeast(scale: number | null): void {
    const floor = scale ?? 0;
    if (floor === this.floor) return;
    this.floor = floor;
    this.governor.setFloor(scale);
    this.apply();
  }

  dispose(): void {
    this.observer.remove();
    this.resizeObserver?.disconnect();
  }

  private apply(): void {
    const cssHeight = this.cssHeight;
    if (cssHeight === 0) return;
    const nativeHeight = cssHeight * window.devicePixelRatio;
    const renderHeight = Math.min(nativeHeight, this.preset.maxRenderHeight) * this.scale;
    // Hardware scaling level = CSS pixels per rendered pixel.
    const level = cssHeight / renderHeight;
    if (Math.abs(level - this.level) > 0.001) {
      this.level = level;
      this.engine.setHardwareScalingLevel(level);
    }
  }
}

function clampScale(scale: number): number {
  return Math.min(1, Math.max(0.5, scale));
}

/**
 * GPU frame time from the engine's timestamp queries, where the browser offers
 * them (Chromium); null elsewhere (Safari), and the governor falls back to frame time.
 */
export function gpuFrameTimer(engine: AbstractEngine): () => number | null {
  const timed = engine as AbstractEngine & {
    captureGPUFrameTime?: (value: boolean) => void;
    getGPUFrameTimeCounter?: () => { current: number };
  };
  if (!engine.getCaps().timerQuery || !timed.captureGPUFrameTime || !timed.getGPUFrameTimeCounter)
    return () => null;
  timed.captureGPUFrameTime(true);
  const counter = timed.getGPUFrameTimeCounter();
  return () => {
    const ns = counter.current;
    return ns > 0 ? ns * 1e-6 : null;
  };
}
