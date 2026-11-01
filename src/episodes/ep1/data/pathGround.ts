import { ROAD_Z, TERRAIN, YARD, outside, pathDistance } from "./forestBorder";

/**
 * Where the village's ground is trodden mud and where it is leaf litter, as a
 * soft, ragged mask instead of the terrain's 1 m material steps (which drew the
 * path as a flat stripe with a ruled edge). Babylon x/z, metres.
 */

/** Mask texels per metre. */
export const MASK_RESOLUTION = 4;

function hash(x: number, z: number): number {
  const s = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
  return s - Math.floor(s);
}

function valueNoise(x: number, z: number): number {
  const ix = Math.floor(x),
    iz = Math.floor(z);
  const fx = x - ix,
    fz = z - iz;
  const ux = fx * fx * (3 - 2 * fx),
    uz = fz * fz * (3 - 2 * fz);
  const a = hash(ix, iz),
    b = hash(ix + 1, iz),
    c = hash(ix, iz + 1),
    d = hash(ix + 1, iz + 1);
  return a + (b - a) * ux + (c - a) * uz + (a - b - c + d) * ux * uz;
}

/** Three octaves of value noise, 0–1. */
export function fbm(x: number, z: number): number {
  return (
    valueNoise(x, z) * 0.55 +
    valueNoise(x * 2.1 + 17, z * 2.1 - 9) * 0.3 +
    valueNoise(x * 4.3 - 5, z * 4.3 + 31) * 0.15
  );
}

function smoothstep(a: number, b: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

export interface GroundMix {
  /** 1 = trodden mud, 0 = leaf litter. */
  mud: number;
  /** 1 = the wettest, darkest mud (where feet and cart wheels keep it churned). */
  wet: number;
}

/** The ground at (x, z): how much of it is mud, and how wet. */
export function groundMix(x: number, z: number): GroundMix {
  const wobble = fbm(x * 0.45, z * 0.45);
  const grain = fbm(x * 1.6 + 40, z * 1.6 - 12);

  // The path: worn about a metre and a half wide, its edge eaten into by the litter
  // and the roots, never a ruled line.
  const d = pathDistance(x, z);
  const edge = 0.95 + 0.75 * wobble + 0.25 * (grain - 0.5);
  let path = 1 - smoothstep(edge - 0.45, edge + 0.4, d);
  // Fallen leaves drift over it in patches, most at its shoulders.
  const drift = smoothstep(0.58, 0.78, fbm(x * 0.9 - 7, z * 0.9 + 3));
  path *= 1 - drift * (0.35 + 0.5 * smoothstep(0.2, 1.1, d));

  // The courtyard is trodden bare up to a ragged margin past the fence line.
  const yard = 1 - smoothstep(-0.6, 0.9, outside(YARD, x, z) - 0.5 + 1.2 * (wobble - 0.5));

  // South of the grove the road's bank and the flooded fields are all mud.
  const road = smoothstep(59.6, 61.2, z + 1.6 * (wobble - 0.5));

  const mud = Math.max(path, yard, road);
  // Two churned lines down the path where people walk single file, and the road's ruts.
  const lane = Math.abs(d - 0.32) < 0.22 ? 1 - Math.abs(d - 0.32) / 0.22 : 0;
  const rut = Math.max(0, 1 - Math.abs(Math.abs(z - ROAD_Z) - 0.8) / 0.35) * road;
  const wet = Math.min(1, (lane * 0.6 + rut + 0.35 * smoothstep(0.55, 0.85, grain)) * mud);
  return { mud, wet };
}

/** The mask over the authored terrain, as RGBA bytes (R mud, G wet), rows along +z. */
export function bakeGroundMask(): { data: Uint8Array; width: number; height: number } {
  const width = (TERRAIN.maxX - TERRAIN.minX) * MASK_RESOLUTION;
  const height = (TERRAIN.maxZ - TERRAIN.minZ) * MASK_RESOLUTION;
  const data = new Uint8Array(width * height * 4);
  for (let j = 0; j < height; j++)
    for (let i = 0; i < width; i++) {
      const x = TERRAIN.minX + (i + 0.5) / MASK_RESOLUTION;
      const z = TERRAIN.minZ + (j + 0.5) / MASK_RESOLUTION;
      const { mud, wet } = groundMix(x, z);
      const k = (j * width + i) * 4;
      data[k] = Math.round(mud * 255);
      data[k + 1] = Math.round(wet * 255);
      data[k + 3] = 255;
    }
  return { data, width, height };
}
