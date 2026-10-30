import type { MistPocket } from "../../../render/mist";

/** Eye level stays clear; mist collects in understory, paddy edges and below the house. */
export const GROUND_MIST: readonly MistPocket[] = [
  { x: -5, z: 52, radiusX: 4.5, radiusZ: 4, baseY: -0.04, height: 0.7, density: 0.13 },
  { x: 5.5, z: 43, radiusX: 4.8, radiusZ: 4, baseY: -0.04, height: 0.75, density: 0.12 },
  { x: -5.4, z: 34, radiusX: 4.3, radiusZ: 5, baseY: -0.04, height: 0.8, density: 0.14 },
  { x: 7.2, z: 24, radiusX: 5, radiusZ: 4.6, baseY: -0.04, height: 0.65, density: 0.12 },
  { x: -7.3, z: 16, radiusX: 4.5, radiusZ: 4, baseY: -0.04, height: 0.65, density: 0.11 },
  { x: 15, z: 72, radiusX: 10, radiusZ: 6, baseY: -0.12, height: 0.9, density: 0.1 },
  { x: -3.8, z: -12, radiusX: 3, radiusZ: 2.4, baseY: -0.04, height: 0.45, density: 0.1 },
  { x: 3.5, z: -16, radiusX: 3.2, radiusZ: 2.3, baseY: -0.04, height: 0.5, density: 0.1 },
];

/** Real bushes beside the trail. Sources never follow the camera or cross the path. */
export const FOREST_SOURCES: readonly (readonly [number, number])[] = [
  [-6, 54],
  [5, 53],
  [-6.5, 43],
  [7, 44],
  [-5.5, 34],
  [7, 33],
  [-6, 23],
  [7.5, 24],
  [-6.5, 13],
  [7, 12],
  [-9, -27],
  [9, -28],
];

export function inUneaseForest(x: number, y: number, z: number): boolean {
  return (
    y > -0.5 &&
    y < 0.7 &&
    ((z > 8 && z < 59 && Math.abs(x) < 12) || (z < -23 && z > -32 && Math.abs(x) < 20))
  );
}

/** Pick an audible, off-screen bush, never a point directly in front of Sora. */
export function forestSource(
  x: number,
  z: number,
  forwardX: number,
  forwardZ: number,
  variation = 0,
): readonly [number, number] | null {
  const facingLength = Math.hypot(forwardX, forwardZ);
  if (facingLength < 0.01) return null;
  const candidates = FOREST_SOURCES.filter(([sx, sz]) => {
    const dx = sx - x,
      dz = sz - z,
      distance = Math.hypot(dx, dz);
    return (
      distance >= 4 &&
      distance <= 13 &&
      (dx * forwardX + dz * forwardZ) / (distance * facingLength) < 0.15
    );
  });
  return candidates.length ? candidates[variation % candidates.length] : null;
}
