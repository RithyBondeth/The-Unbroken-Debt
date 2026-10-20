import type { AbstractEngine } from "@babylonjs/core/Engines/abstractEngine";
import type { Observer } from "@babylonjs/core/Misc/observable";
import type { QualityPreset } from "./QualityPresets";
import { ResolutionGovernor } from "./ResolutionGovernor";

/**
 * Sets the internal render resolution: capped at the preset's height (a
 * Retina laptop's native 3024×1964 is far more than the game needs) and, when
 * enabled, scaled down and up each frame to hold 60 fps. The image is upscaled
 * to the canvas; TAA hides most of the softness.
 */
export class DynamicResolution {
  readonly governor: ResolutionGovernor;
  enabled: boolean;
  private readonly observer: Observer<AbstractEngine>;
  private level = 0;

  constructor(
    private readonly engine: AbstractEngine,
    private readonly preset: QualityPreset,
    options: { enabled?: boolean; gpuMs?: () => number | null } = {},
  ) {
    this.enabled = options.enabled ?? true;
    this.governor = new ResolutionGovernor({
      targetMs: 1000 / 60,
      minScale: preset.minRenderScale,
    });
    const gpuMs = options.gpuMs ?? (() => null);
    this.observer = engine.onEndFrameObservable.add(() => {
      if (this.enabled) this.governor.update(engine.getDeltaTime(), gpuMs());
      this.apply();
    });
    this.apply();
  }

  /** Current render scale relative to the preset's capped height (1 = full). */
  get scale(): number {
    return this.enabled ? this.governor.scale : 1;
  }

  dispose(): void {
    this.observer.remove();
  }

  private apply(): void {
    const canvas = this.engine.getRenderingCanvas();
    if (!canvas || canvas.clientHeight === 0) return;
    const cssHeight = canvas.clientHeight;
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
