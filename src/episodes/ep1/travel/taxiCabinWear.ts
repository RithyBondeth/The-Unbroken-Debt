import type { Scene } from "@babylonjs/core/scene";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { seededRandom } from "@/audio/synth";

/** How each cabin surface has aged: tiling, how far grime darkens it, and how it dulls or polishes. */
const WEAR: Record<string, { tile: number; grime: number; rough: number; dim: number }> = {
  // The Rosalie's own seats, wheel and small trim, its doors and body, in their maps.
  M_internal: { tile: 3, grime: 0.85, rough: 0.8, dim: 0.62 },
  M_door: { tile: 2.5, grime: 0.9, rough: 0.9, dim: 0.72 },
  M_external: { tile: 2.5, grime: 0.9, rough: 0.9, dim: 0.72 },
  M_taxi_body_lacquer_door: { tile: 2, grime: 0.8, rough: 0.5, dim: 0.8 },
  M_taxi_body_lacquer_external: { tile: 2, grime: 0.8, rough: 0.5, dim: 0.8 },
  M_taxi_body_lacquer_gardeboue: { tile: 2, grime: 0.8, rough: 0.5, dim: 0.8 },
  // The photo-textured linings laid over its flat paint.
  M_taxi_headliner: { tile: 2, grime: 1, rough: 0.4, dim: 0.62 },
  M_taxi_trim_cloth: { tile: 2, grime: 1, rough: 0.4, dim: 0.7 },
  M_taxi_carpet: { tile: 4, grime: 1, rough: 0.3, dim: 0.6 },
  M_taxi_painted_steel: { tile: 2.5, grime: 0.9, rough: 0.9, dim: 0.78 },
  M_taxi_dashboard_walnut: { tile: 2, grime: 0.55, rough: 0.7, dim: 0.85 },
  M_taxi_bakelite: { tile: 4, grime: 0.6, rough: 0.9, dim: 0.85 },
  M_taxi_aged_nickel: { tile: 5, grime: 0.8, rough: 1, dim: 0.8 },
  M_taxi_rubber: { tile: 4, grime: 0.7, rough: 0.6, dim: 0.85 },
};

/**
 * Babylon's detail-map layout: R = albedo (0.5 leaves it alone), G and A = the
 * normal (flat here), B = roughness (0.5 leaves it alone).
 */
function wearTexture(scene: Scene): RawTexture {
  const size = 512,
    data = new Uint8Array(size * size * 4),
    albedo = new Float32Array(size * size).fill(0.5),
    rough = new Float32Array(size * size).fill(0.5),
    r = seededRandom(1934);
  const stamp = (layer: Float32Array, cx: number, cy: number, radius: number, amount: number) => {
    for (let y = -radius; y <= radius; y++)
      for (let x = -radius; x <= radius; x++) {
        const d = Math.hypot(x, y) / radius;
        if (d >= 1) continue;
        const i = ((cy + y + size * 4) % size) * size + ((cx + x + size * 4) % size);
        layer[i] += amount * (1 - d * d) ** 2;
      }
  };
  // Years of damp and hands: broad stains, sweat-darkened patches, tide marks.
  for (let i = 0; i < 90; i++)
    stamp(
      albedo,
      Math.floor(r() * size),
      Math.floor(r() * size),
      14 + Math.floor(r() * 60),
      -(0.05 + r() * 0.13),
    );
  for (let i = 0; i < 40; i++)
    stamp(
      rough,
      Math.floor(r() * size),
      Math.floor(r() * size),
      10 + Math.floor(r() * 44),
      (r() - 0.35) * 0.4,
    );
  // Scuffs and scratches: short pale strokes, mostly along one direction of travel.
  for (let i = 0; i < 520; i++) {
    let x = r() * size,
      y = r() * size;
    const a = r() < 0.7 ? (r() - 0.5) * 0.5 : r() * Math.PI,
      length = 6 + r() * 60,
      pale = 0.05 + r() * 0.12;
    for (let s = 0; s < length; s++) {
      const i = ((Math.floor(y) + size) % size) * size + ((Math.floor(x) + size) % size);
      albedo[i] += pale;
      rough[i] += 0.22;
      x += Math.cos(a);
      y += Math.sin(a);
    }
  }
  // Grit, fly-specks and cigarette burns.
  for (let i = 0; i < 9000; i++) {
    const at = Math.floor(r() * size * size);
    albedo[at] -= 0.08 + r() * 0.22;
    rough[at] += 0.2;
  }
  for (let i = 0; i < size * size; i++) {
    data[i * 4] = Math.max(0, Math.min(255, albedo[i] * 255));
    data[i * 4 + 1] = 128;
    data[i * 4 + 2] = Math.max(0, Math.min(255, rough[i] * 255));
    data[i * 4 + 3] = 128;
  }
  const texture = RawTexture.CreateRGBATexture(
    data,
    size,
    size,
    scene,
    true,
    false,
    Texture.TRILINEAR_SAMPLINGMODE,
  );
  texture.name = "T_taxi_cabin_wear";
  texture.wrapU = texture.wrapV = Texture.WRAP_ADDRESSMODE;
  return texture;
}

/**
 * The taxi is a twenty-year-old Citroën that has worked every monsoon since:
 * stained headlining, cracked and sweat-dark seats, scratched paint, dull
 * plating. One shared wear map, laid over each surface at its own scale.
 */
export function ageTaxiCabin(scene: Scene): void {
  let wear: RawTexture | null = null;
  for (const material of scene.materials) {
    if (!(material instanceof PBRMaterial)) continue;
    const age = WEAR[material.name];
    if (!age) continue;
    wear ??= wearTexture(scene);
    const map = wear.clone();
    map.uScale = map.vScale = age.tile;
    material.detailMap.texture = map;
    material.detailMap.isEnabled = true;
    material.detailMap.diffuseBlendLevel = age.grime;
    material.detailMap.roughnessBlendLevel = age.rough;
    material.detailMap.bumpLevel = 0;
    material.albedoColor.scaleInPlace(age.dim);
  }
}
