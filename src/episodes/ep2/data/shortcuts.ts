import { LOST_GARDEN, type Point } from "./pagoda";

/**
 * A barred breach in the compound wall: a way back from the lost garden that can only be
 * opened from the garden's side (tools/areas/pagoda_lost_garden.py, SHORTCUTS). Runtime
 * X east, Z south.
 */
export interface Shortcut {
  id: string;
  /** Centre of the barricade. */
  at: Point;
  /** Which way the garden lies from it: +1 along X (east) or Z (south), -1 the other way. */
  axis: "x" | "z";
  side: 1 | -1;
  /** What Sora says when she pulls it down. */
  opened: string;
}

export const SHORTCUTS: Shortcut[] = [
  {
    id: "terrace",
    at: { x: 29.25, z: 24.9 },
    axis: "x",
    side: 1,
    opened: "The bar comes away in my hands. The way back into the garden is open.",
  },
  {
    id: "grove",
    at: { x: -23.35, z: -41.75 },
    axis: "z",
    side: -1,
    opened: "I lift the bar and the planks fall inward. The pond is just beyond the wall.",
  },
];

/** True when Sora stands within reach of the barricade, on the garden's side of it. */
export function onGardenSide(way: Shortcut, feet: Point): boolean {
  const along = way.axis === "x" ? feet.x - way.at.x : feet.z - way.at.z;
  const across = way.axis === "x" ? feet.z - way.at.z : feet.x - way.at.x;
  return along * way.side > 0.05 && Math.abs(along) < 3 && Math.abs(across) < 2.5;
}

/** The lost-garden zone Sora stands in, or null in the compound. */
export function visitedZone(feet: Point): string | null {
  for (const zone of LOST_GARDEN)
    if (feet.x > zone.minX && feet.x < zone.maxX && feet.z > zone.minZ && feet.z < zone.maxZ)
      return zone.id;
  return null;
}
