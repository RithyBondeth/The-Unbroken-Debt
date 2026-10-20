import { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";

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
  });
  await engine.initAsync();

  window.addEventListener("resize", () => engine.resize());
  return engine;
}
