import type { ShelterBox } from "@/render/skyShelter";

/**
 * Where the sky can't reach in the farmstead's house (tools/areas/stilt_house.py and
 * colonial_house.py): its rooms, its attic under the roof, and the ground under it, the
 * funeral's. The approved previews (Nov 21-22, 2026) are black there but for candles,
 * lamps and Sora's lantern; in the game the sky's and the moon's light would otherwise
 * reach every surface. Written in Blender's axes (x east, y north, z up) and turned into
 * Babylon's (x = -x, y = z, z = -y).
 *
 * The rooms are boxed to the walls' inner faces (the front block's walls stand 6 m out,
 * the back block's 8 m, each 6 cm thick), so their outer weatherboards stay in the sky;
 * the attic boxes stop under the 42-degree roof; the ground's boxes stand back from the
 * stilts, the sky coming back in between them (but not up through the floor).
 */
const FLOOR = 2.5;
const WALL_TOP = FLOOR + 2.6;

function blender(
  x0: number,
  x1: number,
  y0: number,
  y1: number,
  z0: number,
  z1: number,
  inside: number,
  soft: number,
  softUp = soft,
): ShelterBox {
  return {
    minX: -x1,
    maxX: -x0,
    minY: z0,
    maxY: z1,
    minZ: -y1,
    maxZ: -y0,
    inside,
    soft: [soft, softUp, soft],
  };
}

export const HOUSE_SHELTER: readonly ShelterBox[] = [
  // The rooms: the front block (x -6..6, y 11.5..22) and the back block (x -8..8, y 22..34).
  blender(-5.955, 5.955, 11.47, 22.05, FLOOR - 0.06, WALL_TOP + 0.02, 0.04, 0.02),
  blender(-7.955, 7.955, 21.95, 33.955, FLOOR - 0.06, WALL_TOP + 0.02, 0.04, 0.02),
  // The attics, under the ridges at y 16 and 28.
  blender(-5.93, 5.93, 11.6, 20.4, WALL_TOP + 0.02, 6.45, 0.05, 0.02),
  blender(-7.93, 7.93, 23.6, 32.4, WALL_TOP + 0.02, 6.45, 0.05, 0.02),
  // The ground under the house: the funeral's (front block) and the jars' (back block).
  blender(-5.0, 5.0, 11.0, 21.0, -2.0, FLOOR - 0.08, 0.08, 2.5, 0.05),
  blender(-7.0, 7.0, 23.0, 33.0, -2.0, FLOOR - 0.08, 0.08, 2.5, 0.05),
];
