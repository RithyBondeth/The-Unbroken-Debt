/** Local ground volumes; no camera-wide increase in brightness or fog density. */
export interface MistPocket {
  x: number;
  z: number;
  radiusX: number;
  radiusZ: number;
  baseY: number;
  height: number;
  density: number;
}

export const MAX_MIST_POCKETS = 8;

const smooth = (a: number, b: number, value: number) => {
  const t = Math.max(0, Math.min(1, (value - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** Matches the volume's smooth footprint and low ceiling, for layout checks. */
export function mistDensityAt(p: MistPocket, x: number, y: number, z: number, time = 0): number {
  const h = (y - p.baseY) / p.height;
  if (h <= 0 || h >= 1) return 0;
  const dx = (x - p.x + Math.sin(z * 0.7 + time * 0.09) * 0.25) / p.radiusX;
  const dz = (z - p.z + Math.sin(x * 0.6 - time * 0.07) * 0.2) / p.radiusZ;
  const edge = Math.max(0, 1 - dx * dx - dz * dz);
  return p.density * edge * edge * smooth(0, 0.15, h) * (1 - smooth(0.35, 1, h));
}
