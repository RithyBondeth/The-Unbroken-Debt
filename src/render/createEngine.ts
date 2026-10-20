import { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
// Tree-shaken imports leave out WebGPU engine features (multiple render targets
// for the pre-pass, cube render targets for point-light shadows, timestamp
// queries for GPU timing, raw and dynamic textures). Load them all once here.
import "@babylonjs/core/Engines/WebGPU/Extensions";

/**
 * Creates the WebGPU engine. The game requires WebGPU (no WebGL2 fallback);
 * returns null when it is unavailable so the caller can show the requirements page.
 */
export async function createEngine(canvas: HTMLCanvasElement): Promise<WebGPUEngine | null> {
  if (!(await WebGPUEngine.IsSupportedAsync)) return null;

  const engine = new WebGPUEngine(canvas, {
    antialias: true,
    adaptToDeviceRatio: true,
    powerPreference: "high-performance",
    // High-end target: request every adapter feature (timestamp queries for GPU
    // timing, float32 filtering, BC/ASTC texture compression) and the full limits.
    enableAllFeatures: true,
    setMaximumLimits: true,
  });
  await engine.initAsync();

  window.addEventListener("resize", () => engine.resize());
  return engine;
}
