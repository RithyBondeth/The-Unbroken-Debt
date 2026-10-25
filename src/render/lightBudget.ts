import { SceneLoader } from "@babylonjs/core/Loading/sceneLoader";
import { GetSupportedSimultaneousLights } from "@babylonjs/core/Materials/materialHelper.functions";
import type { Scene } from "@babylonjs/core/scene";

interface LightLimited {
  maxSimultaneousLights?: number;
}

/** Each material's own light limit, before a load changes it. */
export function snapshotLightLimits(materials: readonly object[]): Map<object, number> {
  const limits = new Map<object, number>();
  for (const material of materials as readonly LightLimited[])
    if (material.maxSimultaneousLights !== undefined)
      limits.set(material, material.maxSimultaneousLights);
  return limits;
}

/**
 * Puts back each material's own limit; a material the snapshot does not know
 * (new since) is only held to what the device supports.
 */
export function restoreLightLimits(
  materials: readonly object[],
  before: ReadonlyMap<object, number>,
  supported: number,
): void {
  for (const material of materials as readonly LightLimited[]) {
    if (material.maxSimultaneousLights === undefined) continue;
    material.maxSimultaneousLights = Math.min(
      before.get(material) ?? material.maxSimultaneousLights,
      supported,
    );
  }
}

/**
 * When a glTF load is ready, Babylon's loader raises every material already in
 * the scene to the scene's light count (glTFLoader, "enough lights to have all
 * lights together"). In the village that is 18 or more: the 8 VillageLights
 * sets and the sketchbook's 4 are lost, every material compiles larger shaders,
 * and WebGPU, which fits at most 8 (12 uniform buffers per stage), clamps them
 * back with a warning per light count. This undoes the raise as each load becomes
 * ready, before the caller continues, so no frame renders with it.
 */
export function keepLightBudgets(scene: Scene): void {
  const supported = GetSupportedSimultaneousLights(scene, Number.MAX_SAFE_INTEGER);
  SceneLoader.OnPluginActivatedObservable.add((plugin) => {
    const gltf = plugin as Partial<{
      onLoaderStateChangedObservable: { add(callback: (state: unknown) => void): unknown };
    }>;
    if (!gltf.onLoaderStateChangedObservable) return;
    const before = snapshotLightLimits(scene.materials);
    // GLTFLoaderState.READY is 1; the enum lives in the loaders package.
    gltf.onLoaderStateChangedObservable.add((state) => {
      if (state === 1) restoreLightLimits(scene.materials, before, supported);
    });
  });
}
