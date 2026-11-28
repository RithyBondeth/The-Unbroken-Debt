import { Constants } from "@babylonjs/core/Engines/constants";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { Scene } from "@babylonjs/core/scene";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { MistField } from "@/render/VolumetricFog";
import { MIST_BOUNDS, MIST_HEIGHT, bakeMistField, mistAt } from "../data/forestMist";

/**
 * The village's night mist as the volumetric fog's mist map (data/forestMist): thick
 * drifting banks through the forest and a wall of it past the walls, low mist on the
 * paddies, a thin ground mist on the path and in the yard.
 */
export function forestMistField(scene: Scene): MistField {
  const { data, width, height } = bakeMistField();
  const texture = RawTexture.CreateRGBATexture(
    data,
    width,
    height,
    scene,
    false,
    false,
    Texture.BILINEAR_SAMPLINGMODE,
    Constants.TEXTURETYPE_UNSIGNED_BYTE,
  );
  texture.name = "T_forest_mist_field";
  texture.wrapU = texture.wrapV = Texture.CLAMP_ADDRESSMODE;
  return {
    texture,
    ...MIST_BOUNDS,
    baseY: -0.35,
    height: MIST_HEIGHT,
    density: 0.11,
    // The monsoon wind off the paddies (ActOne sets wind.base 0.55): a slow drift north.
    wind: [0.18, -0.32],
    // Pale, cold, just above the night's own fog: the banks read as shapes in the dark.
    glow: [0.0045, 0.0062, 0.0085],
  };
}

/**
 * Where a Low-preset mist wisp starts: anywhere in the village, kept in proportion to
 * how thick the mist map says the mist lies there, at a height inside its bank.
 */
export function spawnForestWisp(random: () => number, position: Vector3): void {
  for (let tries = 0; tries < 24; tries++) {
    const x = MIST_BOUNDS.minX + random() * MIST_BOUNDS.width;
    const z = MIST_BOUNDS.minZ + random() * MIST_BOUNDS.depth;
    const m = mistAt(x, z);
    if (random() > m.density) continue;
    position.set(x, 0.2 + random() * m.height * MIST_HEIGHT * 0.45, z);
    return;
  }
  position.set(0, -50, 0);
}
