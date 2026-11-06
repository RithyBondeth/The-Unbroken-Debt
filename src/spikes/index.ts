import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import type { DeviceProfile } from "../render/DeviceProfile";

export type SpikeRunner = (
  engine: WebGPUEngine,
  params: URLSearchParams,
  device: DeviceProfile,
) => Promise<void>;

/**
 * Phase 1 technical spikes (Development Plan, section 2.2). Only S4, the
 * spatial-audio listening test, is still open; the rest were retired once the
 * game covered them. Loaded on demand with `?spike=<id>`,
 * so none of this code is downloaded by the game itself.
 */
const SPIKES: Record<string, () => Promise<SpikeRunner>> = {
  s4: async () => (await import("./s4-audio/S4SpatialAudioSpike")).runS4,
};

export function hasSpike(id: string | null): id is string {
  return id !== null && id in SPIKES;
}

export async function runSpike(
  id: string,
  engine: WebGPUEngine,
  params: URLSearchParams,
  device: DeviceProfile,
): Promise<void> {
  const run = await SPIKES[id]();
  await run(engine, params, device);
}
