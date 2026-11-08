import type { GradeParams } from "@/render/grade";
import type { MistPocket } from "@/render/mist";
import { NIGHT_GRADE } from "@/render/nightGrade";
import { NIGHT_LOOK, type Look } from "@/render/nightLook";

/**
 * The pagoda's night: darker than the village, the air thick with mist under the canopy.
 * Light falls off into grey-green haze, so the forest goes on until it is only shapes,
 * and nothing past the lamp and the few flames is ever quite clear.
 */
export const PAGODA_LOOK: Look = {
  ...NIGHT_LOOK,
  baseExposure: 1.25,
  maxExposure: 1.8,
  fogDensity: 0.03,
  // A shade lighter than the trees, so trunks and crowns stand dark against the haze.
  fogAmbient: [0.0062, 0.0102, 0.0122],
  skyIntensity: 0.18,
  moonIntensity: 0.22,
};

/** How the haze sits: it thins only slowly with height, and is marched far out. */
export const PAGODA_FOG = {
  /** Per metre of height; low, so mist climbs into the crowns instead of hugging the floor. */
  heightFalloff: 0.15,
  /** The volume reaches past the real trees into the far tree cards. */
  maxDistance: 75,
};

/** Deeper blacks and a little less colour than the village, the shadows colder. */
export const PAGODA_GRADE: GradeParams = {
  ...NIGHT_GRADE,
  saturation: -0.16,
  shadows: { ...NIGHT_GRADE.shadows, strength: 0.34 },
  blackPoint: 0.008,
};

/**
 * Ground mist (runtime X east, Z south), at most eight pockets. Over the pond, through the
 * garden lanes, and lying in the lost garden: the Court's lanes, the Sunken Tank and the
 * Spirit Grove. The Root Gallery is roofed and stays clear.
 */
export const PAGODA_MIST: MistPocket[] = [
  { x: -8, z: -25, radiusX: 9, radiusZ: 12, baseY: 0.04, height: 1, density: 0.5 },
  { x: 8, z: -25, radiusX: 9, radiusZ: 12, baseY: 0.04, height: 1, density: 0.5 },
  { x: 0, z: 0, radiusX: 15, radiusZ: 17, baseY: 0.02, height: 0.8, density: 0.28 },
  // The Bone Terrace: mist lying shin-deep over the bricks and round the skulls.
  { x: 47, z: 33, radiusX: 12, radiusZ: 7.5, baseY: 0.08, height: 0.75, density: 0.42 },
  { x: -55, z: 5, radiusX: 24, radiusZ: 24, baseY: 0.02, height: 0.9, density: 0.32 },
  { x: -55, z: -46, radiusX: 15, radiusZ: 15, baseY: -1.2, height: 1.8, density: 0.45 },
  { x: 0, z: -70, radiusX: 28, radiusZ: 26, baseY: 0.02, height: 1, density: 0.36 },
  { x: 0, z: 37, radiusX: 9, radiusZ: 7, baseY: 0.02, height: 0.8, density: 0.3 },
];
