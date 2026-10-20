import { EngineInstrumentation } from "@babylonjs/core/Instrumentation/engineInstrumentation";
import { SceneInstrumentation } from "@babylonjs/core/Instrumentation/sceneInstrumentation";
import type { AbstractEngine } from "@babylonjs/core/Engines/abstractEngine";
import type { Scene } from "@babylonjs/core/scene";

/**
 * Small live readout for spikes and profiling: fps, frame and GPU time,
 * draw calls, active triangles and render resolution. Toggle with F3.
 */
export class PerfOverlay {
  readonly engineStats: EngineInstrumentation;
  readonly sceneStats: SceneInstrumentation;
  private readonly element: HTMLElement;
  private readonly abort = new AbortController();
  private lastUpdate = 0;

  constructor(
    private readonly engine: AbstractEngine,
    private readonly scene: Scene,
    parent: HTMLElement = document.body,
  ) {
    this.engineStats = new EngineInstrumentation(engine);
    this.engineStats.captureGPUFrameTime = true;
    this.sceneStats = new SceneInstrumentation(scene);
    this.sceneStats.captureFrameTime = true;
    this.sceneStats.captureRenderTime = true;

    this.element = document.createElement("pre");
    this.element.className = "perf-overlay";
    parent.appendChild(this.element);

    window.addEventListener(
      "keydown",
      (e) => {
        if (e.code === "F3") {
          e.preventDefault();
          this.element.hidden = !this.element.hidden;
        }
      },
      { signal: this.abort.signal },
    );
    scene.onAfterRenderObservable.add(() => this.update());
  }

  /** Average GPU frame time over the last second in ms, or null if the browser can't measure it. */
  get gpuMs(): number | null {
    const counter = this.engineStats.gpuFrameTimeCounter;
    const ns = counter.lastSecAverage || counter.average;
    return ns > 0 ? ns * 1e-6 : null;
  }

  dispose(): void {
    this.abort.abort();
    this.engineStats.dispose();
    this.sceneStats.dispose();
    this.element.remove();
  }

  private update(): void {
    const now = performance.now();
    if (now - this.lastUpdate < 250 || this.element.hidden) return;
    this.lastUpdate = now;

    const gpu = this.gpuMs;
    const frame = this.sceneStats.frameTimeCounter.lastSecAverage;
    const render = this.sceneStats.renderTimeCounter.lastSecAverage;
    const lines = [
      `${this.engine.getFps().toFixed(0)} fps`,
      `cpu frame ${frame.toFixed(2)} ms · render ${render.toFixed(2)} ms`,
      `gpu ${gpu === null ? "n/a" : `${gpu.toFixed(2)} ms`}`,
      `draw calls ${this.sceneStats.drawCallsCounter.current}`,
      `triangles drawn ${(this.scene.getActiveIndices() / 3 / 1e6).toFixed(2)} M (all passes)`,
      `${this.engine.getRenderWidth()}×${this.engine.getRenderHeight()}`,
    ];
    this.element.textContent = lines.join("\n");
  }
}
