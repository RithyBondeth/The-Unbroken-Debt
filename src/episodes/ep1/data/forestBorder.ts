import { seededRandom } from "@/audio/synth";
import { FARM_PATHS } from "./farmLayout";
import { inSaveShrineClearing } from "./saveShrine";
import { LANE_WIDTH, inClearing, inNewGround, laneDistance } from "./villageAreas";

/**
 * The forest round the village's authored ground, and where Sora's walk ends.
 * All in Babylon space (the glTF mirror of Blender: x = -x, z = -y), metres.
 *
 * The Blender terrain stops at TERRAIN. Sora is held inside PLAY by walls set
 * in the thicket a few metres short of it; past them the ground and the forest
 * carry on into the fog until the storm sky takes over, so there is no edge to
 * see or reach. The compound's own belt of forest is filled out at the same time,
 * and the ground the village expansion added (data/villageAreas) is grown over
 * with forest round its clearings.
 */
export interface Rect {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

export const TERRAIN: Rect = { minX: -65, maxX: 65, minZ: -62, maxZ: 92 };
/**
 * The farmstead (the user, Nov 21-22 2026: "a big tangled farmstead"): its outer fence
 * (tools/areas/farmstead.py FARM, Blender x -46..44, y -40..58) and, outside its gate, the
 * village road where the taxi leaves Sora (VILLAGE_ROAD) with the shops along it. The fence,
 * the road's ditches, its fallen trees and the shops have their own colliders in the area;
 * these walls only back them up, well behind the shops on the road's far side.
 */
export const PLAY: Rect = { minX: -44.5, maxX: 46.5, minZ: -58.5, maxZ: 70 };
/**
 * The village road outside the gate (tools/areas/village_road.py, the user, Nov 25, 2026:
 * "road along with the shop and shop's poster for each shop just like driving scene"): its
 * centre line's z (Blender ROAD_Y0, mirrored; it drifts under a metre either way), and how
 * far along it either way Sora can walk before the fallen trees across it.
 */
export const VILLAGE_ROAD = { z: 51.8, walkX: 30.5 } as const;
/**
 * Whether ForestBorder grows its forest round PLAY. The farm's wall of old trees is
 * authored in the area itself (compound.tree_wall round farmstead.FARM), so nothing
 * more is grown.
 */
export const GROW_FOREST = false;
/** Centre of the road along the paddies (A1-01). */
export const ROAD_Z = 63.5;
/** The flooded rice fields between the road bank and the far bank. */
const PADDIES = { minZ: 60.5, maxZ: 86.5 };
/** Raised bunds close the fields east and west, inside the walls' thicket. */
const BUND_X = 53.5;
/** The compound inside its fence; the back fence stands behind the porch stairs (colonial_house.py). */
export const YARD: Rect = { minX: -13, maxX: 13, minZ: -32, maxZ: 3 };
/**
 * The cart track from the farm's gate to the house's yard gate, winding between the
 * fields and the groves (the user, Nov 22, 2026: "don't make the road feel like just a
 * straight line"; tools/areas/farmstead.py TRACK, exported to farmLayout.ts last of
 * FARM_PATHS).
 */
export const PATH: readonly (readonly [number, number])[] =
  FARM_PATHS[FARM_PATHS.length - 1].points;
const POND = { x: 20, z: -19, rx: 4, rz: 3 };
const WELLS: readonly (readonly [number, number])[] = [
  [17, -7.5],
  [-9.5, 33],
];
/** The paddies' mud and their water (tools/areas/village_nature.py PADDY_FLOOR, WATER_Z). */
export const PADDY_FLOOR = -0.32;
export const WATER_Y = -0.1;

/** 0-1: how much a spot past the walls is a hamlet's ground (bananas, palms, a shade tree). */
export function hamlet(x: number, z: number): number {
  const n =
    0.5 +
    0.28 * Math.sin(x * 0.043 + 1.7) * Math.cos(z * 0.051 - 0.6) +
    0.22 * Math.sin(x * 0.11 - z * 0.083 + 2.4);
  return Math.max(0, Math.min(1, n));
}

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

/**
 * The Nov 19 village's straight road, which the tree omens (data/treeOmens.ts, grown only
 * with GROW_FOREST) were set out along.
 */
export const OLD_ROAD: readonly (readonly [number, number])[] = [
  [0, 46.5],
  [0, 3],
];

/** Metres from (x, z) to the old straight road (the tree omens' reference). */
export function oldRoadDistance(x: number, z: number): number {
  return lineDistance(OLD_ROAD, x, z);
}

/** Metres from (x, z) to the cart track's centre line. */
export function pathDistance(x: number, z: number): number {
  return lineDistance(PATH, x, z);
}

function lineDistance(PATH: readonly (readonly [number, number])[], x: number, z: number): number {
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
  // The countryside past the walls (the user, Nov 19): the tree line's raised ground
  // along the terrain's edge, then flooded paddies cut by dikes, a hamlet's mound here
  // and there, on into the mist.
  const raised = 0.04 + 0.04 * Math.sin(x * 0.37 + 1.1) * Math.cos(z * 0.29 + 0.4);
  const dikeX = Math.abs(((((x + 4 + 0.6 * Math.sin(z * 0.2)) % 16) + 16) % 16) - 8);
  const dikeZ = Math.abs(((((z + 2 + 0.5 * Math.sin(x * 0.17)) % 13) + 13) % 13) - 6.5);
  const ridge = Math.max(0, 0.42 - 0.6 * Math.min(8 - dikeX, 6.5 - dikeZ));
  let field = PADDY_FLOOR + 0.02 * Math.sin(x * 0.7 + z * 0.4) + Math.min(0.42, ridge);
  field = field + (raised - field) * smoothstep(0.55, 0.75, hamlet(x, z));
  let natural = raised + (field - raised) * smoothstep(3, 7, d);
  if (r < 2.6) natural = roadBank(r);
  else if (r < 6 && Math.abs(x) > TERRAIN.maxX)
    natural = Math.max(natural, roadBank(2.6) - 0.12 * (r - 2.6));
  return edge + (natural - edge) * smoothstep(0, 4, d);
}

export type Species =
  | "broadleaf"
  | "fig"
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
  /** Its trunk blocks Sora (the forest on the expansion's new ground). */
  solid?: boolean;
}

/** A far tree drawn as crossed painted cards (impostor), beyond the modelled ring. */
export interface Card {
  x: number;
  z: number;
  yaw: number;
  height: number;
  width: number;
  /** Painted atlas cell: 0–2 broadleaf crowns, 3 and 6 fig, 4 and 7 sugar palm, 5 banana clump. */
  variant: number;
}

export interface BorderOptions {
  /** How far past the terrain the modelled trees go (m). */
  nearDepth: number;
  /** How far the painted far forest goes (m); the storm dome is 50 m from the eye. */
  farDepth: number;
  /** Fraction of understory and midstory kept (lower presets thin them). */
  density: number;
  /** Fraction of the walk's extra giants kept (the Low preset thins them). */
  walkCanopy?: number;
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
 * Old-growth lowland forest (31 October 2026): broadleaf giants close overhead,
 * bamboo and a few dead trees between them, saplings and shrubs beneath and
 * ferns over the floor. Palms and bananas belong to the village, not here.
 */
const RING: LayerSpec[] = [
  // The next village's tree line along the walls: bananas and sugar palms set close, a
  // shade tree or a fig here and there (the user, Nov 19: countryside, and no bamboo).
  {
    layer: "canopy",
    spacing: 5.2,
    keep: 0.95,
    radius: 2.2,
    mix: [
      ["banana", 0.4],
      ["sugarPalm", 0.4],
      ["broadleaf", 0.12],
      ["fig", 0.08],
    ],
  },
  {
    layer: "mid",
    spacing: 3.2,
    keep: 0.85,
    radius: 1.1,
    mix: [
      ["banana", 0.5],
      ["shrub", 0.3],
      ["pachira", 0.2],
    ],
  },
  {
    layer: "under",
    spacing: 2.2,
    keep: 0.8,
    radius: 0.6,
    mix: [
      ["shrub", 0.5],
      ["fern", 0.5],
    ],
  },
];

/**
 * The fields past the tree line: open paddies with lone sugar palms standing in them,
 * and the hamlets' banana groves under palms round a shade tree (hamlet()).
 */
const COUNTRY: LayerSpec[] = [
  {
    layer: "canopy",
    spacing: 7,
    keep: 1,
    radius: 2.5,
    mix: [
      ["sugarPalm", 0.72],
      ["banana", 0.18],
      ["broadleaf", 0.1],
    ],
  },
];
const HAMLET: Mix = [
  ["banana", 0.5],
  ["sugarPalm", 0.32],
  ["broadleaf", 0.12],
  ["fig", 0.06],
];

/** Beside the walk, inside the authored terrain: off the trodden path, short of the road. */
export function inWalk(x: number, z: number): boolean {
  if (z < 6 || z > ROAD_Z - 4.5 || !inside(TERRAIN, x, z, 2)) return false;
  // The first Neak Ta's patrol and its sight-lines (EarlyStealthBrain) stay as authored.
  if (x > -7 && x < 8 && z > 7 && z < 29) return false;
  const d = pathDistance(x, z);
  return d > 3.4 && d < 22;
}

const SCALE: Record<Species, [number, number]> = {
  broadleaf: [0.8, 1.12],
  fig: [0.72, 0.95],
  young: [0.34, 0.52],
  sugarPalm: [0.8, 1.2],
  coconut: [0.85, 1.15],
  bamboo: [0.8, 1.25],
  banana: [0.55, 0.85],
  dead: [0.6, 0.88],
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
/** The tree line: past the authored terrain, close along the walls. */
function inTreeline(x: number, z: number): boolean {
  return outside(TERRAIN, x, z) > 0 && outside(PLAY, x, z) < 10 && !onOuterRoad(x, z, 0.8);
}

/** The fields past the tree line, as far as the modelled ring goes. */
function inCountry(x: number, z: number, nearDepth: number): boolean {
  const d = outside(PLAY, x, z);
  return d >= 10 && outside(TERRAIN, x, z) <= nearDepth && !onOuterRoad(x, z, 1.5);
}

/** The forest belt round the house and compound, short of the walls' thicket. */
export function inBelt(x: number, z: number): boolean {
  if (!inside(PLAY, x, z, 2.5) || inNewGround(x, z)) return false;
  const sides = Math.abs(x) >= 14.5 && z > -33 && z < 6;
  const rear = z <= -28.5;
  return (sides || rear) && !inside(YARD, x, z, -1.8) && pathDistance(x, z) > 3;
}

/** The expansion's new ground inside the walls' thicket, north of the road bank. */
export function inWild(x: number, z: number): boolean {
  return inNewGround(x, z) && inside(PLAY, x, z, 2.5) && z < ROAD_Z - 4.5;
}

/** Fixed clearances every layout respects: the yard, path, pond and wells. */
export function openGround(x: number, z: number, radius: number): boolean {
  if (inSaveShrineClearing(x, z, radius)) return false;
  // The expansion's clearings and the lanes that lead to them.
  if (inClearing(x, z, radius + 0.5)) return false;
  if (laneDistance(x, z) < LANE_WIDTH / 2 + 1.1 + radius) return false;
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
  // Inside the walls the village file carries its own plants now (the countryside round
  // the house, tools/areas/countryside.py): the runtime grows only past them.
  const zones: [LayerSpec[], (x: number, z: number) => boolean][] = [
    [RING, inTreeline],
    [COUNTRY, (x, z) => inCountry(x, z, options.nearDepth)],
  ];
  for (const [specs, within] of zones) {
    for (const spec of specs) {
      const s = spec.spacing;
      const keep = spec.layer !== "canopy" ? spec.keep * options.density : spec.keep;
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
          let species = choose(
            specs === COUNTRY && hamlet(x, z) > 0.62 ? HAMLET : spec.mix,
            random(),
          );
          // Open field: most spots stay bare water and rice; a hamlet's ground is close set.
          if (specs === COUNTRY && hamlet(x, z) <= 0.62 && u > 0.42) continue;
          // Past the paddies the ring is the next village's tree line: sugar palms over
          // bananas, a shade tree here and there (Khmer countryside).
          if (specs === RING && spec.layer === "canopy" && z > PADDIES.maxZ - 1) {
            const u = random();
            species = u < 0.45 ? "sugarPalm" : u < 0.85 ? "banana" : "broadleaf";
          }
          const inTerrain = outside(TERRAIN, x, z) < 0;
          if (inTerrain && (!openGround(x, z, spec.radius) || !options.clear(x, z, spec.radius)))
            continue;
          if (!inTerrain && !openGround(x, z, 0)) continue;
          if (trunks.some((t) => Math.hypot(x - t.x, z - t.z) < t.r + spec.radius * 0.6)) continue;
          const [lo, hi] = SCALE[species];
          const plant: Plant = {
            species,
            layer: spec.layer,
            x,
            z,
            yaw,
            scale: lo + (hi - lo) * k,
            pick,
          };
          plants.push(plant);
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
  // The country's horizon (no leafless trees and no bamboo, the user, Nov 19): tree lines
  // of crowns and banana groves round distant hamlets, sugar palms standing over the fields.
  card(
    6.5,
    (u) => (u < 0.42 ? Math.floor((u / 0.42) * 3) : u < 0.55 ? 3 : u < 0.72 ? 5 : u < 0.86 ? 4 : 7),
    [12, 22],
  );
  card(9, (u) => (u < 0.5 ? 4 : 7), [15, 22]);
  return { plants, cards };
}
