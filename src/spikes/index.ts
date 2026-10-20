import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";

/**
 * Phase 1 technical spikes (Development Plan, section 2.2). Each is a small
 * scene that answers one risky question. Loaded on demand with `?spike=<id>`,
 * so none of this code is downloaded by the game itself.
 */
const SPIKES: Record<
  string,
  () => Promise<(engine: WebGPUEngine, params: URLSearchParams) => Promise<void>>
> = {
  s1: async () => (await import("./s1-movement/S1MovementSpike")).runS1,
  s2: async () => (await import("./s2-lighting/S2LightingSpike")).runS2,
};

export function hasSpike(id: string | null): id is string {
  return id !== null && id in SPIKES;
}

export async function runSpike(
  id: string,
  engine: WebGPUEngine,
  params: URLSearchParams,
): Promise<void> {
  const run = await SPIKES[id]();
  await run(engine, params);
}
