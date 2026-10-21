/**
 * The episode colour grade (Art Bible, sections 2 and 4: "one lookup table per
 * episode, built from the palettes"). A grade is a few numbers kept with the
 * episode's data; `buildLut` bakes it into a 3D lookup table that the final
 * post-process applies after tone mapping, in display colours (0–1).
 */

export type Rgb = [number, number, number];

export interface GradeParams {
  /** -1 (grey) to 1 (double); the 1930s look is around -0.3. */
  saturation: number;
  /** Colour pushed into the shadows, mid-tones and highlights, with a strength 0–1. */
  shadows: { tint: Rgb; strength: number };
  midtones: { tint: Rgb; strength: number };
  highlights: { tint: Rgb; strength: number };
  /** Input level mapped to black: deepens the night (0.02) or, negative, lifts it (daylight). */
  blackPoint: number;
}

/** A grade that changes nothing. */
export const NEUTRAL_GRADE: GradeParams = {
  saturation: 0,
  shadows: { tint: [1, 1, 1], strength: 0 },
  midtones: { tint: [1, 1, 1], strength: 0 },
  highlights: { tint: [1, 1, 1], strength: 0 },
  blackPoint: 0,
};

const luminance = ([r, g, b]: Rgb) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(1, Math.max(0, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

/** Converts a hex palette colour (#C9A46A) to a tint with the same brightness as white. */
export function tintFromHex(hex: string): Rgb {
  const n = Number.parseInt(hex.replace("#", ""), 16);
  const rgb: Rgb = [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  const l = luminance(rgb);
  return [rgb[0] / l, rgb[1] / l, rgb[2] / l];
}

/** Grades one display colour. */
export function gradeColor(input: Rgb, p: GradeParams): Rgb {
  const black = p.blackPoint;
  let c: Rgb = input.map((v) => (v - black) / (1 - black)) as Rgb;
  c = c.map((v) => Math.min(1, Math.max(0, v))) as Rgb;

  const l = luminance(c);
  c = c.map((v) => l + (v - l) * (1 + p.saturation)) as Rgb;

  // Split toning by brightness: each band multiplies towards its tint.
  const wShadow = 1 - smoothstep(0.05, 0.45, l);
  const wHigh = smoothstep(0.55, 0.95, l);
  const wMid = Math.max(0, 1 - wShadow - wHigh);
  for (const [band, w] of [
    [p.shadows, wShadow],
    [p.midtones, wMid],
    [p.highlights, wHigh],
  ] as const) {
    const k = band.strength * w;
    c = c.map((v, i) => v * (1 + (band.tint[i] - 1) * k)) as Rgb;
  }
  return c.map((v) => Math.min(1, Math.max(0, v))) as Rgb;
}

/**
 * Bakes the grade into a `size`³ RGBA table, red fastest, then green, then
 * blue (the layout of a 3D texture: x = red, y = green, z = blue).
 */
export function buildLut(p: GradeParams, size = 32): Uint8Array {
  const data = new Uint8Array(size * size * size * 4);
  let i = 0;
  for (let b = 0; b < size; b++) {
    for (let g = 0; g < size; g++) {
      for (let r = 0; r < size; r++) {
        const out = gradeColor([r / (size - 1), g / (size - 1), b / (size - 1)], p);
        data[i++] = Math.round(out[0] * 255);
        data[i++] = Math.round(out[1] * 255);
        data[i++] = Math.round(out[2] * 255);
        data[i++] = 255;
      }
    }
  }
  return data;
}
