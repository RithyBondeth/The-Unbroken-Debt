import type { Scene } from "@babylonjs/core/scene";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { seededRandom } from "@/audio/synth";

/** Exposure the sky is painted for; as Sora's eyes adapt, it stays night. */
const BASE_EXPOSURE = 1.25;
/** The brightest the sky gets (by the moon), in linear light at the base exposure. */
const LEVEL = 0.045;

/** A dome direction for texture coordinates (u round, v from zenith to nadir), as the sphere lays them. */
export function skyDirection(u: number, v: number): [number, number, number] {
  const a = v * Math.PI,
    b = u * Math.PI * 2;
  return [Math.sin(a) * Math.cos(b), Math.cos(a), -Math.sin(a) * Math.sin(b)];
}

/** Wrapping value noise on a lattice `period` cells round and `rows` cells down. */
function noise(seed: number, period: number, rows: number) {
  const random = seededRandom(seed);
  const grid = Float32Array.from({ length: period * rows }, () => random());
  return (x: number, y: number) => {
    const x0 = Math.floor(x),
      y0 = Math.floor(y);
    const tx = x - x0,
      ty = y - y0;
    const sx = tx * tx * (3 - 2 * tx),
      sy = ty * ty * (3 - 2 * ty);
    const i0 = ((x0 % period) + period) % period,
      i1 = (i0 + 1) % period;
    const j0 = Math.min(rows - 1, Math.max(0, y0)),
      j1 = Math.min(rows - 1, j0 + 1);
    const top = grid[j0 * period + i0] + (grid[j0 * period + i1] - grid[j0 * period + i0]) * sx;
    const bottom = grid[j1 * period + i0] + (grid[j1 * period + i1] - grid[j1 * period + i0]) * sx;
    return top + (bottom - top) * sy;
  };
}

/**
 * The night sky as RGBA rows from zenith to nadir: almost black overhead, a faint grey-green
 * band of scattered light at the horizon (so the canopy stands black against it), thin
 * high cloud drawn out by the wind, and a cold glow round the moon that lights the cloud
 * nearest it. Values are relative; `LEVEL` sets the brightness.
 */
export function nightSkyMap(
  moon: [number, number, number],
  width = 512,
  height = 256,
  seed = 4417,
) {
  const layers = [
    { n: noise(seed, 8, 10), period: 8, stretch: 1.2, amp: 0.55 },
    { n: noise(seed + 1, 16, 20), period: 16, stretch: 1.2, amp: 0.3 },
    { n: noise(seed + 2, 40, 48), period: 40, stretch: 1.2, amp: 0.15 },
  ];
  const data = new Uint8Array(width * height * 4);
  const [mx, my, mz] = moon;
  for (let y = 0; y < height; y++) {
    const v = (y + 0.5) / height;
    const elevation = Math.PI / 2 - v * Math.PI;
    // Scattered light pools above the horizon; below it the dome is fog-dark ground.
    const band =
      elevation < 0
        ? Math.max(0, 1 + elevation * 5) * 0.28
        : 0.1 + 0.2 * Math.exp(-elevation * 5.5);
    for (let x = 0; x < width; x++) {
      const u = x / width;
      let cloud = 0;
      for (const { n, period, stretch, amp } of layers)
        cloud += amp * n(u * period, v * period * stretch);
      // Thin, broken high cloud, only above the horizon.
      const wisp = Math.max(0, Math.min(1, (cloud - 0.5) / 0.25)) * (elevation > 0.04 ? 1 : 0);
      const [dx, dy, dz] = skyDirection(u, v);
      const toMoon = Math.max(0, dx * mx + dy * my + dz * mz);
      const halo = toMoon ** 18 * 0.5 + toMoon ** 4 * 0.12;
      const light = band + halo + wisp * (0.06 + 0.9 * halo + 0.08 * band);
      const i = (y * width + x) * 4;
      data[i] = Math.round(255 * Math.min(1, light * 0.78));
      data[i + 1] = Math.round(255 * Math.min(1, light * 0.9));
      data[i + 2] = Math.round(255 * Math.min(1, light));
      data[i + 3] = 255;
    }
  }
  return { width, height, data };
}

/**
 * A dark night sky round Sora, so the forest has something faintly lighter to stand
 * against: without it the crowns melt into the black clear colour and the jungle reads
 * as a wall. Drawn inside the far plane at the same distance wherever she stands.
 */
export class PagodaSky {
  readonly dome: Mesh;
  private readonly glow: Texture;

  constructor(scene: Scene, moonPosition: Vector3) {
    this.dome = CreateSphere(
      "pagoda_sky_dome",
      { diameter: 200, segments: 32, sideOrientation: Mesh.BACKSIDE },
      scene,
    );
    this.dome.infiniteDistance = true;
    this.dome.isPickable = false;
    this.dome.receiveShadows = false;
    const moon = moonPosition.normalizeToNew();
    const map = nightSkyMap([moon.x, moon.y, moon.z]);
    // Rows run zenith to nadir, as the sphere's V does: uploaded as they are.
    this.glow = RawTexture.CreateRGBATexture(
      map.data,
      map.width,
      map.height,
      scene,
      true,
      false,
      Texture.TRILINEAR_SAMPLINGMODE,
    );
    this.glow.name = "T_ep2_night_sky";
    this.glow.wrapU = Texture.WRAP_ADDRESSMODE;
    this.glow.wrapV = Texture.CLAMP_ADDRESSMODE;
    const material = new StandardMaterial("M_ep2_night_sky", scene);
    material.emissiveTexture = this.glow;
    material.emissiveColor = Color3.Black();
    material.diffuseColor = Color3.Black();
    material.specularColor = Color3.Black();
    material.disableLighting = true;
    material.backFaceCulling = false;
    material.fogEnabled = false;
    this.dome.material = material;
    this.update(BASE_EXPOSURE);
  }

  /**
   * `exposure` is the camera's, which the sky cancels so it doesn't brighten as her eyes
   * adjust. The cloud stays put: drifting it would carry the moon's glow away from the moon.
   */
  update(exposure: number): void {
    this.glow.level = LEVEL * (BASE_EXPOSURE / Math.max(BASE_EXPOSURE, exposure));
  }

  /** Dawn: the sky is the clear colour's job again. */
  hide(): void {
    this.dome.setEnabled(false);
  }
}
