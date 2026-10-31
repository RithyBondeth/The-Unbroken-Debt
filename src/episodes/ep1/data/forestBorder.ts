import { seededRandom } from "../../../audio/synth";
import { inSaveShrineClearing } from "./saveShrine";

/**
 * The forest round the village's authored ground, and where Sora's walk ends.
 * All in Babylon space (the glTF mirror of Blender: x = -x, z = -y), metres.
 *
 * The Blender terrain stops at TERRAIN. Sora is held inside PLAY by walls set
 * in the thicket a few metres short of it; past them the ground and the forest
 * carry on into the fog until the storm sky takes over, so there is no edge to
 * see or reach. The compound's own belt of forest is filled out at the same time.
 */
export interface Rect {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

export const TERRAIN: Rect = { minX: -40, maxX: 40, minZ: -40, maxZ: 92 };
export const PLAY: Rect = { minX: -35, maxX: 35, minZ: -35.5, maxZ: 88 };
/** Centre of the road along the paddies (A1-01). */
export const ROAD_Z = 63.5;
/** The flooded rice fields between the road bank and the far bank. */
const PADDIES = { minZ: 60.5, maxZ: 86.5 };
/** Raised bunds close the fields east and west, inside the walls' thicket. */
const BUND_X = 33.5;
export const YARD: Rect = { minX: -13, maxX: 13, minZ: -22, maxZ: 3 };
export const PATH: readonly (readonly [number, number])[] = [
  [-1.5, 60],
  [-2.5, 50],
  [-0.5, 40],
  [2.5, 30],
  [2, 20],
  [-0.5, 10],
  [0, 3],
];
const POND = { x: 20, z: -19, rx: 4, rz: 3 };
const WELLS: readonly (readonly [number, number])[] = [
  [17, -7.5],
  [-9.5, 33],
];
/** Floor-UV tile of the terrain's mud and forest floor (kit.world_uvs). */
export const GROUND_TILE = 2.25;

/** Signed distance from the rectangle's boundary: positive outside, negative inside. */
export function outside(rect: Rect, x: number, z: number): number {
  const dx = Math.max(rect.minX - x, x - rect.maxX);
  const dz = Math.max(rect.minZ - z, z - rect.maxZ);
  if (dx <= 0 && dz <= 0) return Math.max(dx, dz);
  return Math.hypot(Math.max(dx, 0), Math.max(dz, 0));
}

export function inside(rect: Rect, x: number, z: number, margin = 0): boolean {
  return outside(rect, x, z) < -margin;
}

export function pathDistance(x: number, z: number): number {
  let best = Infinity;
  for (let i = 0; i + 1 < PATH.length; i++) {
    const [ax, az] = PATH[i];
    const [bx, bz] = PATH[i + 1];
    const t = Math.max(
      0,
      Math.min(
        1,
        ((x - ax) * (bx - ax) + (z - az) * (bz - az)) / ((bx - ax) ** 2 + (bz - az) ** 2),
      ),
    );
    best = Math.min(best, Math.hypot(x - ax - t * (bx - ax), z - az - t * (bz - az)));
  }
  return best;
}

function smoothstep(a: number, b: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
}

/** The road bank's crown and cart ruts (terrain(), ep1_area_village.py), `r` from its centre. */
export function roadBank(r: number): number {
  return 0.14 - 0.02 * r - 0.07 * Math.exp(-(((r - 0.8) / 0.25) ** 2));
}

/** Is this the raised bund along the paddies' east or west side? */
export function inBund(x: number, z: number): boolean {
  return Math.abs(x) >= BUND_X && z > PADDIES.minZ - 1 && z < PADDIES.maxZ + 1;
}

/** Is this the road beyond the walls, continuing into the fog? */
export function onOuterRoad(x: number, z: number, margin = 0): boolean {
  return Math.abs(x) > TERRAIN.maxX && Math.abs(z - ROAD_Z) < 2.5 + margin;
}

/**
 * Ground height beyond the terrain and along the bunds. `terrainAt` gives the
 * authored terrain's height: at its edge the new ground meets it exactly, then
 * runs on in low wet rises that lift slowly away from the village.
 */
export function borderHeight(
  x: number,
  z: number,
  terrainAt: (x: number, z: number) => number,
): number {
  const signed = outside(TERRAIN, x, z);
  const r = Math.abs(z - ROAD_Z);
  // Authored height, raised along the bunds (the road keeps its own bank).
  const base = (bx: number, bz: number) => {
    const t = terrainAt(bx, bz);
    if (!inBund(bx, bz) || r < 2.7) return t;
    const bund = 0.06 + 0.03 * Math.sin(bz * 0.9 + bx);
    return Math.max(t, t + (bund - t) * smoothstep(BUND_X, BUND_X + 2, Math.abs(bx)));
  };
  if (signed < 0) {
    const b = base(x, z);
    return b > terrainAt(x, z) ? b : b - 0.05; // otherwise tucked under the authored ground
  }
  const d = signed;
  const edge = base(
    Math.max(TERRAIN.minX, Math.min(TERRAIN.maxX, x)),
    Math.max(TERRAIN.minZ, Math.min(TERRAIN.maxZ, z)),
  );
  let natural =
    0.1 * Math.sin(x * 0.37 + 1.1) * Math.cos(z * 0.29 + 0.4) +
    0.05 * Math.sin(x * 1.1 + z * 0.7 + 2.3) +
    0.9 * smoothstep(6, 46, d) +
    0.35 * Math.sin(x * 0.06 + 0.8) * Math.sin(z * 0.05 + 2.1) * smoothstep(8, 30, d);
  if (r < 2.6) natural = roadBank(r);
  else if (r < 6 && Math.abs(x) > TERRAIN.maxX)
    natural = Math.min(natural, roadBank(2.6) - 0.05 * (r - 2.6));
  return edge + (natural - edge) * smoothstep(0, 4, d);
}

export type Species =
  | "broadleaf"
  | "young"
  | "sugarPalm"
  | "coconut"
  | "bamboo"
  | "banana"
  | "dead"
  | "pachira"
  | "shrub"
  | "fern";

export type Layer = "canopy" | "mid" | "under";

export interface Plant {
  species: Species;
  layer: Layer;
  x: number;
  z: number;
  yaw: number;
  scale: number;
  /** 0–1, picks a template variant. */
  pick: number;
}

/** A far tree drawn as crossed painted cards (impostor), beyond the modelled ring. */
export interface Card {
  x: number;
  z: number;
  yaw: number;
  height: number;
  width: number;
  /** Painted atlas cell: 0–3 broadleaf crowns, 4 sugar palm, 5 bamboo, 6 coconut, 7 dead tree. */
  variant: number;
}

export interface BorderOptions {
  /** How far past the terrain the modelled trees go (m). */
  nearDepth: number;
  /** How far the painted far forest goes (m); the storm dome is 50 m from the eye. */
  farDepth: number;
  /** Fraction of understory and midstory kept (lower presets thin them). */
  density: number;
  seed?: number;
  /** False where existing art, colliders or gameplay need the ground. */
  clear: (x: number, z: number, radius: number) => boolean;
}

export interface BorderLayout {
  plants: Plant[];
  cards: Card[];
}

type Mix = readonly (readonly [Species, number])[];

interface LayerSpec {
  layer: Layer;
  spacing: number;
  keep: number;
  /** Clearance from existing art and from this layer's own trunks. */
  radius: number;
  mix: Mix;
}

/**
 * The dying forest (31 October 2026): grey broadleaf giants and dead trees,
 * dead bamboo between them, withered saplings and shrubs beneath and dead
 * ferns over the floor. Palms and bananas belong to the village, not here.
 */
const RING: LayerSpec[] = [
  {
    layer: "canopy",
    spacing: 7.5,
    keep: 0.97,
    radius: 3,
    mix: [
      ["broadleaf", 0.56],
      ["dead", 0.3],
      ["bamboo", 0.08],
      ["sugarPalm", 0.06],
    ],
  },
  {
    layer: "mid",
    spacing: 4.4,
    keep: 0.85,
    radius: 1.4,
    mix: [
      ["young", 0.28],
      ["pachira", 0.3],
      ["bamboo", 0.1],
      ["shrub", 0.32],
    ],
  },
  {
    layer: "under",
    spacing: 2.4,
    keep: 0.85,
    radius: 0.6,
    mix: [
      ["shrub", 0.35],
      ["fern", 0.65],
    ],
  },
];

/** The belt round the compound: fewer new crowns, a fuller layered understory. */
const BELT: LayerSpec[] = [
  {
    layer: "canopy",
    spacing: 6.5,
    keep: 1,
    radius: 3.2,
    mix: [
      ["broadleaf", 0.56],
      ["sugarPalm", 0.08],
      ["bamboo", 0.08],
      ["dead", 0.28],
    ],
  },
  {
    layer: "mid",
    spacing: 3.8,
    keep: 0.75,
    radius: 1.6,
    mix: [
      ["young", 0.24],
      ["pachira", 0.32],
      ["banana", 0.1],
      ["bamboo", 0.08],
      ["shrub", 0.26],
    ],
  },
  {
    layer: "under",
    spacing: 2.3,
    keep: 0.7,
    radius: 0.7,
    mix: [
      ["shrub", 0.4],
      ["fern", 0.6],
    ],
  },
];

const SCALE: Record<Species, [number, number]> = {
  broadleaf: [0.8, 1.2],
  young: [0.32, 0.5],
  sugarPalm: [0.8, 1.2],
  coconut: [0.85, 1.15],
  bamboo: [0.8, 1.25],
  banana: [0.8, 1.2],
  dead: [0.8, 1.2],
  pachira: [1.5, 2.6],
  shrub: [0.9, 1.9],
  fern: [0.8, 1.5],
};

function choose(mix: Mix, u: number): Species {
  let total = 0;
  for (const [, w] of mix) total += w;
  let acc = 0;
  for (const [species, w] of mix) {
    acc += w / total;
    if (u < acc) return species;
  }
  return mix[mix.length - 1][0];
}

/** Ground the walls' thicket and the outer forest grow on. */
function inRing(x: number, z: number, nearDepth: number): boolean {
  const d = outside(TERRAIN, x, z);
  if (outside(PLAY, x, z) < -2.5 || d > nearDepth) return false;
  if (onOuterRoad(x, z, 0.8)) return false;
  // Inside the terrain the fields and the road stay open, apart from the bunds.
  if (d < 0 && z > PADDIES.minZ - 0.5 && z < PADDIES.maxZ && Math.abs(x) < BUND_X + 1) return false;
  if (d < 0 && Math.abs(z - ROAD_Z) < 3.2) return false;
  return true;
}

/** The forest belt round the house and compound, short of the walls' thicket. */
export function inBelt(x: number, z: number): boolean {
  if (!inside(PLAY, x, z, 2.5)) return false;
  const sides = Math.abs(x) >= 14.5 && z > -33 && z < 6;
  const rear = z <= -23.5;
  return (sides || rear) && !inside(YARD, x, z, -1.8) && pathDistance(x, z) > 3;
}

/** Fixed clearances every layout respects: the yard, path, pond and wells. */
export function openGround(x: number, z: number, radius: number): boolean {
  if (inSaveShrineClearing(x, z, radius)) return false;
  if (inside(YARD, x, z, -(1.2 + radius))) return false;
  if (pathDistance(x, z) < 2.2 + radius) return false;
  if (
    ((x - POND.x) / (POND.rx + 1.5 + radius)) ** 2 +
      ((z - POND.z) / (POND.rz + 1.5 + radius)) ** 2 <
    1
  )
    return false;
  return WELLS.every(([wx, wz]) => Math.hypot(x - wx, z - wz) > 2.5 + radius);
}

/**
 * Plants on jittered grids, one per layer: even cover with no regular rows, and
 * nothing standing on the path, in the yard or in another trunk. Deterministic.
 */
export function layoutBorder(options: BorderOptions): BorderLayout {
  const random = seededRandom(options.seed ?? 6242025);
  const plants: Plant[] = [];
  const trunks: { x: number; z: number; r: number }[] = [];
  const bounds: Rect = {
    minX: TERRAIN.minX - options.nearDepth,
    maxX: TERRAIN.maxX + options.nearDepth,
    minZ: TERRAIN.minZ - options.nearDepth,
    maxZ: TERRAIN.maxZ + options.nearDepth,
  };
  const zones: [LayerSpec[], (x: number, z: number) => boolean][] = [
    [RING, (x, z) => inRing(x, z, options.nearDepth)],
    [BELT, inBelt],
  ];
  for (const [specs, within] of zones) {
    for (const spec of specs) {
      const s = spec.spacing;
      const keep = spec.layer === "canopy" ? spec.keep : spec.keep * options.density;
      for (let gx = bounds.minX; gx < bounds.maxX; gx += s) {
        for (let gz = bounds.minZ; gz < bounds.maxZ; gz += s) {
          const x = gx + s * (0.15 + 0.7 * random());
          const z = gz + s * (0.15 + 0.7 * random());
          const u = random();
          const yaw = random() * Math.PI * 2;
          const k = random();
          const pick = random();
          if (u > keep || !within(x, z)) continue;
          // Low ground layers only matter near where Sora can stand.
          if (spec.layer === "under" && outside(TERRAIN, x, z) > options.nearDepth * 0.45) continue;
          const species = choose(spec.mix, random());
          const inTerrain = outside(TERRAIN, x, z) < 0;
          if (inTerrain && (!openGround(x, z, spec.radius) || !options.clear(x, z, spec.radius)))
            continue;
          if (!inTerrain && !openGround(x, z, 0)) continue;
          if (trunks.some((t) => Math.hypot(x - t.x, z - t.z) < t.r + spec.radius * 0.6)) continue;
          const [lo, hi] = SCALE[species];
          plants.push({ species, layer: spec.layer, x, z, yaw, scale: lo + (hi - lo) * k, pick });
          if (spec.layer !== "under") trunks.push({ x, z, r: spec.layer === "canopy" ? 2.2 : 1 });
        }
      }
    }
  }

  const cards: Card[] = [];
  const far: Rect = {
    minX: TERRAIN.minX - options.farDepth,
    maxX: TERRAIN.maxX + options.farDepth,
    minZ: TERRAIN.minZ - options.farDepth,
    maxZ: TERRAIN.maxZ + options.farDepth,
  };
  const card = (spacing: number, variants: (u: number) => number, height: [number, number]) => {
    for (let gx = far.minX; gx < far.maxX; gx += spacing) {
      for (let gz = far.minZ; gz < far.maxZ; gz += spacing) {
        const x = gx + spacing * random();
        const z = gz + spacing * random();
        const variant = variants(random());
        const h = height[0] + (height[1] - height[0]) * random();
        const yaw = random() * Math.PI;
        const d = outside(TERRAIN, x, z);
        if (d < options.nearDepth - 6 || d > options.farDepth || onOuterRoad(x, z, 1.5)) continue;
        cards.push({ x, z, yaw, height: h, width: h, variant });
      }
    }
  };
  // Bare dead trees and thinning crowns to the horizon, a little dead bamboo; few palms.
  card(4.2, (u) => (u < 0.5 ? 7 : u < 0.9 ? Math.floor(((u - 0.5) / 0.4) * 4) : 5), [13, 22]);
  card(12, (u) => (u < 0.7 ? 7 : 4), [16, 24]);
  return { plants, cards };
}
