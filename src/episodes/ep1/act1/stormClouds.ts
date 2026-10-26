import { seededRandom } from "../../../audio/synth";

/**
 * The monsoon night's cloud, as two maps for the sky dome (StormSky): a high,
 * unbroken rain deck faintly lit from behind by a hidden moon, and the low,
 * ragged scud that races under it. Both wrap horizontally round the dome; rows
 * run from the zenith (row 0) to the nadir. Values are 0–255 RGBA.
 */
export interface CloudMap {
  width: number;
  height: number;
  data: Uint8Array;
}

/** Tileable (in x) value noise on an integer lattice of `period` cells across. */
function lattice(random: () => number, period: number, rows: number): Float32Array {
  const grid = new Float32Array(period * rows);
  for (let i = 0; i < grid.length; i++) grid[i] = random();
  return grid;
}

function sample(grid: Float32Array, period: number, rows: number, x: number, y: number): number {
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
  const a = grid[j0 * period + i0],
    b = grid[j0 * period + i1];
  const c = grid[j1 * period + i0],
    d = grid[j1 * period + i1];
  return (a + (b - a) * sx) * (1 - sy) + (c + (d - c) * sx) * sy;
}

/**
 * Fractal noise, wrapping in u (0–1 round the dome); v is 0–1 from zenith to nadir.
 * `rows` is cells down per cell across: 0.5 keeps features round on the dome
 * (360° by 180°), more stretches them along the horizon, as wind does to cloud.
 */
function fbm(seed: number, octaves: number, base: number, stretch: number) {
  const random = seededRandom(seed);
  const layers = Array.from({ length: octaves }, (_, k) => {
    const period = base * 2 ** k;
    const rows = Math.ceil(period * stretch) + 2;
    return { period, rows, grid: lattice(random, period, rows) };
  });
  return (u: number, v: number, warp = 0) => {
    let sum = 0,
      amp = 0.5,
      norm = 0;
    for (const { period, rows, grid } of layers) {
      sum += amp * sample(grid, period, rows, u * period + warp * period * 0.05, v * period * stretch);
      norm += amp;
      amp *= 0.5;
    }
    return sum / norm;
  };
}

function smoothstep(a: number, b: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

/** Elevation of a row, in radians (+π/2 zenith, 0 horizon). */
export function elevation(v: number): number {
  return Math.PI / 2 - v * Math.PI;
}

/**
 * The high deck: rolling, heavy cloud bases, a little lighter near the horizon
 * (scattered light, so trees stand dark against it) and darkest overhead.
 * RGB carries the cloud's own light (glow and lightning), alpha unused.
 */
export function cloudDeck(width = 1024, height = 512, seed = 7331): CloudMap {
  // Layered, wind-stretched rain cloud rather than heaped cumulus.
  const noise = fbm(seed, 6, 5, 1.6);
  const detail = fbm(seed + 1, 4, 22, 1.4);
  const data = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++) {
    const v = (y + 0.5) / height;
    const e = elevation(v);
    // Light pools just above the horizon and fades to the zenith; below, fog.
    const band = e < 0 ? Math.max(0, 1 + e * 6) * 0.6 : 0.35 + 0.65 * Math.exp(-e * 2.6);
    for (let x = 0; x < width; x++) {
      const u = x / width;
      const billow = noise(u, v);
      const fine = detail(u, v, billow);
      // Heavy bases: lighter where the cloud thins, dark rolls where it is thick.
      const shape = smoothstep(0.25, 0.85, billow * 0.8 + fine * 0.35);
      const light = band * (0.28 + 0.72 * shape ** 1.4);
      const i = (y * width + x) * 4;
      data[i] = Math.round(255 * Math.min(1, light * 0.82));
      data[i + 1] = Math.round(255 * Math.min(1, light * 0.9));
      data[i + 2] = Math.round(255 * Math.min(1, light));
      data[i + 3] = 255;
    }
  }
  return { width, height, data };
}

/**
 * The low scud: torn, wind-stretched rain cloud that darkens what lies behind
 * it. RGB is a multiplier: 255 where the deck shows through, dark under scud.
 */
export function cloudScud(width = 1024, height = 512, seed = 9113): CloudMap {
  const noise = fbm(seed, 5, 6, 2.4);
  const tear = fbm(seed + 1, 3, 24, 2.4);
  const data = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++) {
    const v = (y + 0.5) / height;
    const e = elevation(v);
    // Scud is low cloud: thick near the horizon, thinning towards the zenith.
    const reach = e < 0 ? 1 : smoothstep(1.3, 0.15, e);
    for (let x = 0; x < width; x++) {
      const u = x / width;
      const mass = noise(u, v) * 0.85 + tear(u, v) * 0.3;
      const cover = smoothstep(0.42, 0.72, mass) * reach;
      const shade = 1 - 0.78 * cover;
      const i = (y * width + x) * 4;
      const g = Math.round(255 * shade);
      data[i] = g;
      data[i + 1] = g;
      data[i + 2] = Math.round(255 * Math.min(1, shade * 1.03));
      data[i + 3] = 255;
    }
  }
  return { width, height, data };
}
