import { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import type { WebGPUCacheBindGroups } from "@babylonjs/core/Engines/WebGPU/webgpuCacheBindGroups";
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
  repairHalfBuiltBindGroups(engine);

  window.addEventListener("resize", () => engine.resize());
  return engine;
}

/**
 * Babylon 9.31 puts a new bind-group array in its cache, and on the draw,
 * before filling it. If createBindGroup throws part-way (a texture the effect
 * didn't bind), the half-filled array stays cached and every later draw with
 * the same bindings reuses it: no exception, but a GPU validation error that
 * drops the whole frame, every frame, for good. runRenderLoop survives the
 * throw itself; this rebuilds the half-filled entry the next time it is used.
 */
function repairHalfBuiltBindGroups(engine: WebGPUEngine): void {
  const cache = (engine as unknown as { _cacheBindGroups?: WebGPUCacheBindGroups })
    ._cacheBindGroups;
  if (!cache) {
    console.warn("[render] WebGPU engine internals changed: recheck repairHalfBuiltBindGroups");
    return;
  }
  const getBindGroups = cache.getBindGroups.bind(cache);
  const halfBuilt = new WeakSet<GPUBindGroup[]>();
  cache.getBindGroups = (pipelineContext, drawContext, materialContext) => {
    try {
      const bindGroups = getBindGroups(pipelineContext, drawContext, materialContext);
      if (!halfBuilt.has(bindGroups)) return bindGroups;
      // The cache handed back an entry a throw left half-filled. The cache is
      // keyed by bindings, so the entry can't be removed: build the bind groups
      // again outside the cache, then fill the cached array in place.
      const disabled = cache.disabled;
      cache.disabled = true;
      let rebuilt: GPUBindGroup[];
      try {
        rebuilt = getBindGroups(pipelineContext, drawContext, materialContext);
      } finally {
        cache.disabled = disabled;
      }
      bindGroups.splice(0, bindGroups.length, ...rebuilt);
      halfBuilt.delete(bindGroups);
      drawContext.bindGroups = bindGroups;
      return bindGroups;
    } catch (error) {
      // The draw holds the half-filled array too: remember it, and make the
      // draw look its bind groups up again next time instead of reusing it.
      if (drawContext.bindGroups) halfBuilt.add(drawContext.bindGroups);
      materialContext.isDirty = true;
      throw error;
    }
  };
}
