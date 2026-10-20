import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Scene } from "@babylonjs/core/scene";
import { addStaticBox, addStaticRamp, type Surface } from "../../core/Physics";
import type { Ladder } from "../../player/PlayerController";

/** Axis-aligned box in feet-space, used for checklist zones. */
export interface Zone {
  min: Vector3;
  max: Vector3;
}

export interface Waypoint {
  x: number;
  z: number;
  /** Feet height to reach before the waypoint counts (ladders, stairs). */
  y?: number;
  crouch?: boolean;
  hurry?: boolean;
}

export interface Course {
  spawn: Vector3;
  spawnYaw: number;
  ladders: Ladder[];
  zones: Record<
    "frontStairs" | "backStairs" | "houseFloor" | "lowPassage" | "granary" | "plankPad",
    Zone
  >;
  route: Waypoint[];
}

/** Real dimensions from the Art Bible: floor 2 m up, planks 14 cm with 1 cm gaps. */
const FLOOR_Y = 2;
const PLANK_W = 0.14;
const GAP = 0.01;
const PLANK_T = 0.04;

/**
 * Builds the S1 movement course: a stilt-house floor with gapped planks, a
 * comfortable front stair, a steep back stair, a door threshold, a low passage
 * for crouching, a ladder to a rice granary, and a plank stress-test pad.
 */
export function buildCourse(scene: Scene): Course {
  const mats = makeMaterials(scene);

  // Ground.
  solid(scene, "ground", [0, -0.1, 0], [80, 0.2, 80], mats.dirt, "dirt");

  // House floor: z 2.5 → 12, x -4 → 4, planks run along X.
  for (let z = 2.5, i = 0; z + PLANK_W <= 12 + 1e-6; z += PLANK_W + GAP, i++) {
    const mat = i % 2 === 0 ? mats.teakA : mats.teakB;
    solid(
      scene,
      `plank_${i}`,
      [0, FLOOR_Y - PLANK_T / 2, z + PLANK_W / 2],
      [8, PLANK_T, PLANK_W],
      mat,
      "teak",
    );
  }
  // Joists under the planks and stilts.
  for (const x of [-3.9, -2, 0, 2, 3.9]) {
    solid(
      scene,
      `joist_${x}`,
      [x, FLOOR_Y - PLANK_T - 0.06, 7.25],
      [0.1, 0.12, 9.5],
      mats.darkWood,
      "teak",
    );
    for (const z of [2.6, 7.25, 11.9]) {
      solid(
        scene,
        `stilt_${x}_${z}`,
        [x, (FLOOR_Y - PLANK_T - 0.12) / 2, z],
        [0.22, FLOOR_Y - PLANK_T - 0.12, 0.22],
        mats.darkWood,
        "teak",
      );
    }
  }

  // Walls with a front door (with a 6 cm threshold) and a back opening to the steep stair.
  const wallH = 2.3;
  const wallY = FLOOR_Y + wallH / 2;
  solid(scene, "wall_front_l", [-2.3, wallY, 5], [3.4, wallH, 0.08], mats.wall, "teak");
  solid(scene, "wall_front_r", [2.3, wallY, 5], [3.4, wallH, 0.08], mats.wall, "teak");
  solid(scene, "lintel", [0, FLOOR_Y + 2.1, 5], [1.2, 0.4, 0.08], mats.wall, "teak");
  solid(scene, "threshold", [0, FLOOR_Y + 0.03, 5], [1.2, 0.06, 0.1], mats.darkWood, "teak");
  solid(scene, "wall_back_l", [-0.8, wallY, 12], [6.4, wallH, 0.08], mats.wall, "teak");
  solid(scene, "wall_back_r", [3.7, wallY, 12], [0.6, wallH, 0.08], mats.wall, "teak");
  solid(scene, "wall_left", [-4, wallY, 8.5], [0.08, wallH, 7], mats.wall, "teak");
  solid(scene, "wall_right", [4, wallY, 8.5], [0.08, wallH, 7], mats.wall, "teak");
  // Veranda rail (front, both sides of the stair).
  solid(scene, "rail_l", [-2.3, FLOOR_Y + 0.45, 2.55], [3.4, 0.08, 0.06], mats.darkWood, "teak");
  solid(scene, "rail_r", [2.3, FLOOR_Y + 0.45, 2.55], [3.4, 0.08, 0.06], mats.darkWood, "teak");

  // Front stair: 10 steps, 20 cm rise, 26 cm tread, up along +Z to the veranda.
  // A hidden ramp over the step noses carries the player (see PlayerConfig.maxStepHeight).
  for (let i = 1; i <= 10; i++) {
    const zEnd = 2.5 - 0.26 * (10 - i);
    solid(
      scene,
      `stairA_${i}`,
      [0, (0.2 * i) / 2, zEnd - 0.13],
      [1.2, 0.2 * i, 0.26],
      mats.teakA,
      "teak",
    );
  }
  stairRamp(scene, "stairA_ramp", [0, -0.1, 0.2], [0, 2.24, 2], 1.2);

  // Back stair: 8 steps, 25 cm rise, 22 cm tread (steep, like a real stilt house).
  for (let i = 1; i <= 8; i++) {
    const zStart = 12 + 0.22 * (8 - i);
    solid(
      scene,
      `stairB_${i}`,
      [2.9, (0.25 * i) / 2, zStart + 0.11],
      [1, 0.25 * i, 0.22],
      mats.teakB,
      "teak",
    );
  }
  stairRamp(scene, "stairB_ramp", [2.9, 13.76, 0.25], [2.9, 12.22, 2], 1);

  // Low passage: 1.25 m clearance, crouch required.
  solid(scene, "passage_roof", [-8, 1.35, 5.5], [2.4, 0.2, 5], mats.wall, "teak");
  solid(scene, "passage_wall_l", [-9.15, 0.725, 5.5], [0.1, 1.45, 5], mats.wall, "teak");
  solid(scene, "passage_wall_r", [-6.85, 0.725, 5.5], [0.1, 1.45, 5], mats.wall, "teak");

  // Rice granary with a ladder on its west face.
  const granaryTop = 2.4;
  solid(scene, "granary", [8, granaryTop / 2, 7.5], [3, granaryTop, 3], mats.darkWood, "teak");
  for (const z of [7.12, 7.88]) {
    solid(scene, `ladder_rail_${z}`, [6.42, 1.35, z], [0.05, 2.7, 0.05], mats.teakA, "teak");
  }
  for (let y = 0.3; y < granaryTop + 0.2; y += 0.3) {
    const rung = CreateBox(
      `ladder_rung_${y.toFixed(1)}`,
      { width: 0.04, height: 0.04, depth: 0.76 },
      scene,
    );
    rung.position.set(6.42, y, 7.5);
    rung.material = mats.teakA;
  }
  const ladder: Ladder = {
    min: new Vector3(5.9, 0, 7.1),
    max: new Vector3(6.5, granaryTop + 0.3, 7.9),
    normal: new Vector3(-1, 0, 0),
  };

  // Plank stress pad (8 cm high, low enough to step onto): 1 cm gaps, then 2 cm gaps with ±3 mm
  // height jitter, then planks laid at 45°.
  let seed = 7;
  const random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) * 2 - 1;
  const padTop = 0.08;
  for (let z = -8, i = 0; z < -4; z += PLANK_W + 0.01, i++) {
    solid(
      scene,
      `padA_${i}`,
      [-13.5, padTop - 0.02, z + PLANK_W / 2],
      [5, 0.04, PLANK_W],
      i % 2 ? mats.teakA : mats.teakB,
      "teak",
    );
  }
  for (let z = -4, i = 0; z < -1; z += PLANK_W + 0.02, i++) {
    const jitter = random() * 0.003;
    solid(
      scene,
      `padB_${i}`,
      [-13.5, padTop - 0.02 + jitter, z + PLANK_W / 2],
      [5, 0.04, PLANK_W],
      i % 2 ? mats.teakA : mats.teakB,
      "teak",
    );
  }
  // At 45°, a 15 cm plank pitch is 0.15 / sin 45° ≈ 0.212 m along X.
  for (let i = -8; i <= 8; i++) {
    solid(
      scene,
      `padC_${i}`,
      [-13.5 + i * 0.212, padTop - 0.02, 0.5],
      [0.14, 0.04, 2.8],
      i % 2 ? mats.teakA : mats.teakB,
      "teak",
      Math.PI / 4,
    );
  }
  // Base under the pad so the planks sit on something.
  solid(
    scene,
    "pad_base",
    [-13.5, (padTop - 0.04) / 2, -3],
    [5, padTop - 0.04, 10],
    mats.darkWood,
    "teak",
  );

  return {
    spawn: new Vector3(0, 0, -4),
    spawnYaw: 0,
    ladders: [ladder],
    zones: {
      frontStairs: zone([-0.6, 0.6, -0.4, 2.5], 0.6, 1.6),
      backStairs: zone([2.4, 3.4, 12, 13.8], 0.6, 1.6),
      houseFloor: zone([-4, 4, 2.5, 12], FLOOR_Y - 0.1, FLOOR_Y + 0.3),
      lowPassage: zone([-9, -7, 4, 7], -0.1, 0.3),
      granary: zone([6.5, 9.5, 6, 9], granaryTop - 0.1, granaryTop + 0.3),
      plankPad: zone([-16, -11, -8, 2.5], padTop - 0.05, padTop + 0.1),
    },
    route: [
      { x: 0, z: -1.2 },
      { x: 0, z: 3.4, y: FLOOR_Y },
      { x: 0, z: 6.5 },
      { x: -3, z: 11 },
      { x: 3, z: 6 },
      { x: 2.9, z: 11.4 },
      { x: 2.9, z: 14.6, y: 0 },
      { x: -2, z: 14.6 },
      { x: -8, z: 9.5 },
      { x: -8, z: 7.6, crouch: true },
      { x: -8, z: 3.4, crouch: true },
      { x: -8, z: 1.5 },
      { x: -13.5, z: -9 },
      { x: -13.5, z: 2.6, hurry: true },
      { x: -15.5, z: -7.5 },
      { x: -11.5, z: -1.5, crouch: true },
      { x: -5, z: -2 },
      { x: 5.2, z: -2 },
      { x: 5.2, z: 7.5 },
      { x: 6.1, z: 7.5 },
      { x: 7.6, z: 7.5, y: granaryTop },
    ],
  };
}

/**
 * Ramp through the noses of a straight stair, extended down to the ground.
 * `first` and `last` are [x, z, y] of the first and last step noses.
 */
function stairRamp(
  scene: Scene,
  name: string,
  first: number[],
  last: number[],
  width: number,
): void {
  const [x0, z0, y0] = first;
  const [x1, z1, y1] = last;
  // Extend the nose line down to y = 0 so the ramp starts on the ground.
  const t = y0 / (y1 - y0);
  const bottom = new Vector3(x0 - (x1 - x0) * t, 0, z0 - (z1 - z0) * t);
  addStaticRamp(scene, name, bottom, new Vector3(x1, y1, z1), width - 0.04, "teak");
}

function zone([x0, x1, z0, z1]: number[], y0: number, y1: number): Zone {
  return { min: new Vector3(x0, y0, z0), max: new Vector3(x1, y1, z1) };
}

function solid(
  scene: Scene,
  name: string,
  [x, y, z]: number[],
  [w, h, d]: number[],
  material: StandardMaterial,
  surface: Surface,
  rotationY = 0,
): Mesh {
  const mesh = CreateBox(name, { width: w, height: h, depth: d }, scene);
  mesh.position.set(x, y, z);
  mesh.rotation.y = rotationY;
  mesh.material = material;
  mesh.freezeWorldMatrix();
  addStaticBox(mesh, surface);
  return mesh;
}

function makeMaterials(scene: Scene) {
  const make = (name: string, hex: string) => {
    const m = new StandardMaterial(name, scene);
    m.diffuseColor = Color3.FromHexString(hex);
    m.specularColor = new Color3(0.05, 0.05, 0.05);
    m.freeze();
    return m;
  };
  return {
    dirt: make("dirt", "#5b4a39"),
    teakA: make("teakA", "#9a6a3e"),
    teakB: make("teakB", "#86593a"),
    darkWood: make("darkWood", "#4a3424"),
    wall: make("wall", "#b49a78"),
  };
}
