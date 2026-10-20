import type { Scene } from "@babylonjs/core/scene";
import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import type { PerfOverlay } from "./PerfOverlay";
import { checkSixtyFps, summarizeFrames, type BudgetResult, type FrameSummary } from "./frameStats";

export interface BenchmarkResult {
  summary: FrameSummary;
  /** Every measured frame time (ms), for finding when slow frames happen. */
  frameMs: number[];
  gpuAvgMs: number | null;
  budget: BudgetResult;
  width: number;
  height: number;
  maxDrawCalls: number;
  adapter: string;
}

export interface BenchmarkOptions {
  warmupSec: number;
  durationSec: number;
  /** Called every frame with progress 0–1 so the scene can move the camera. */
  onProgress?: (t: number) => void;
}

/**
 * Records frame times for a fixed duration after a warm-up (shader compilation,
 * texture uploads) and checks the result against the 60 fps budget.
 */
export function runBenchmark(
  scene: Scene,
  perf: PerfOverlay,
  options: BenchmarkOptions,
): Promise<BenchmarkResult> {
  const engine = scene.getEngine();
  const frames: number[] = [];
  const gpuSamples: number[] = [];
  let maxDrawCalls = 0;
  let resolutionChanged = false;
  const startWidth = engine.getRenderWidth();
  const startHeight = engine.getRenderHeight();
  let elapsed = 0;
  const total = options.warmupSec + options.durationSec;

  return new Promise((resolve) => {
    const observer = scene.onAfterRenderObservable.add(() => {
      const dt = engine.getDeltaTime();
      elapsed += dt / 1000;
      options.onProgress?.(Math.min(1, elapsed / total));
      if (elapsed < options.warmupSec) return;

      frames.push(dt);
      if (engine.getRenderWidth() !== startWidth || engine.getRenderHeight() !== startHeight) {
        resolutionChanged = true;
      }
      const gpuNs = perf.engineStats.gpuFrameTimeCounter.current;
      if (gpuNs > 0) gpuSamples.push(gpuNs * 1e-6);
      maxDrawCalls = Math.max(maxDrawCalls, perf.sceneStats.drawCallsCounter.current);

      if (elapsed >= total) {
        observer.remove();
        const summary = summarizeFrames(frames);
        const gpuAvgMs =
          gpuSamples.length > 0 ? gpuSamples.reduce((a, b) => a + b, 0) / gpuSamples.length : null;
        const budget = checkSixtyFps(summary, gpuAvgMs);
        if (resolutionChanged) {
          budget.pass = false;
          budget.reasons.push("render resolution changed during the run; result not valid");
        }
        resolve({
          summary,
          frameMs: frames,
          gpuAvgMs,
          budget,
          width: engine.getRenderWidth(),
          height: engine.getRenderHeight(),
          maxDrawCalls,
          adapter: describeAdapter(engine as WebGPUEngine),
        });
      }
    });
  });
}

function describeAdapter(engine: WebGPUEngine): string {
  const info = engine.getInfo();
  return [info.vendor, info.renderer].filter(Boolean).join(" · ") || "unknown GPU";
}

/** Formats a result for the on-screen report and the console. */
export function formatBenchmark(result: BenchmarkResult): string {
  const s = result.summary;
  return [
    result.budget.pass ? "PASS: 60 fps budget met" : "FAIL: 60 fps budget missed",
    ...result.budget.reasons.map((r) => `  · ${r}`),
    `GPU: ${result.adapter}`,
    `Resolution: ${result.width}×${result.height}`,
    `Frames: ${s.frames} · average ${s.avgFps.toFixed(1)} fps (${s.avgMs.toFixed(2)} ms)`,
    `1% low: ${s.low1Fps.toFixed(1)} fps · p99 ${s.p99Ms.toFixed(2)} ms · worst ${s.maxMs.toFixed(1)} ms`,
    `GPU time: ${result.gpuAvgMs === null ? "not available in this browser" : `${result.gpuAvgMs.toFixed(2)} ms average`}`,
    `Peak draw calls: ${result.maxDrawCalls}`,
  ].join("\n");
}
