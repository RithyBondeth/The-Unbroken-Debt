import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { Scene } from "@babylonjs/core/scene";

/**
 * Procedural stand-in textures so the lighting test pays realistic texture
 * costs (albedo + normal maps, mip-mapped, anisotropic) before real art exists.
 */

function hash(x: number, y: number): number {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}

/** Tileable value noise with the given period. */
function noise(x: number, y: number, period: number): number {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const xf = x - xi;
  const yf = y - yi;
  const u = xf * xf * (3 - 2 * xf);
  const v = yf * yf * (3 - 2 * yf);
  const x0 = ((xi % period) + period) % period;
  const y0 = ((yi % period) + period) % period;
  const x1 = (x0 + 1) % period;
  const y1 = (y0 + 1) % period;
  const a = hash(x0, y0);
  const b = hash(x1, y0);
  const c = hash(x0, y1);
  const d = hash(x1, y1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

export interface SurfaceTextures {
  albedo: Texture;
  normal: Texture;
}

/** Height field for a surface type, 0–1, tileable over [0, 1). */
type HeightFn = (u: number, v: number) => number;

const woodHeight: HeightFn = (u, v) => {
  const warp = noise(u * 6, v * 2, 6) * 2 + noise(u * 24, v * 6, 24) * 0.4;
  const grain = Math.sin((u * 18 + warp) * Math.PI * 2) * 0.5 + 0.5;
  return grain * 0.7 + noise(u * 64, v * 4, 64) * 0.3;
};

const clothHeight: HeightFn = (u, v) => {
  const weave = Math.sin(u * 256 * Math.PI) * Math.sin(v * 256 * Math.PI) * 0.5 + 0.5;
  return weave * 0.6 + noise(u * 16, v * 16, 16) * 0.4;
};

const stoneHeight: HeightFn = (u, v) =>
  noise(u * 8, v * 8, 8) * 0.5 +
  noise(u * 32, v * 32, 32) * 0.3 +
  noise(u * 128, v * 128, 128) * 0.2;

const HEIGHTS = { wood: woodHeight, cloth: clothHeight, stone: stoneHeight };

export function makeSurfaceTextures(
  scene: Scene,
  kind: keyof typeof HEIGHTS,
  size: number,
  dark: [number, number, number],
  light: [number, number, number],
): SurfaceTextures {
  const heightFn = HEIGHTS[kind];
  const heights = new Float32Array(size * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) heights[y * size + x] = heightFn(x / size, y / size);
  }

  const albedo = new Uint8Array(size * size * 4);
  const normal = new Uint8Array(size * size * 4);
  const strength = 3;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = y * size + x;
      const h = heights[i];
      for (let c = 0; c < 3; c++)
        albedo[i * 4 + c] = Math.round((dark[c] + (light[c] - dark[c]) * h) * 255);
      albedo[i * 4 + 3] = 255;

      const hx = heights[y * size + ((x + 1) % size)] - heights[y * size + ((x - 1 + size) % size)];
      const hy = heights[((y + 1) % size) * size + x] - heights[((y - 1 + size) % size) * size + x];
      const nx = -hx * strength;
      const ny = -hy * strength;
      const len = Math.hypot(nx, ny, 1);
      normal[i * 4] = Math.round((nx / len) * 127.5 + 127.5);
      normal[i * 4 + 1] = Math.round((ny / len) * 127.5 + 127.5);
      normal[i * 4 + 2] = Math.round((1 / len) * 127.5 + 127.5);
      normal[i * 4 + 3] = 255;
    }
  }

  const make = (data: Uint8Array, name: string) => {
    const texture = RawTexture.CreateRGBATexture(
      data,
      size,
      size,
      scene,
      true,
      false,
      Texture.TRILINEAR_SAMPLINGMODE,
    );
    texture.name = name;
    texture.anisotropicFilteringLevel = 8;
    texture.wrapU = Texture.WRAP_ADDRESSMODE;
    texture.wrapV = Texture.WRAP_ADDRESSMODE;
    return texture;
  };
  return { albedo: make(albedo, `${kind}_BC`), normal: make(normal, `${kind}_N`) };
}
