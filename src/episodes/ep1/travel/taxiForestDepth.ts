import type { Scene } from "@babylonjs/core/scene";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import type { Material } from "@babylonjs/core/Materials/material";
import { seededRandom } from "@/audio/synth";
import { buildFarTreeCards, CARD_VARIANT, type FarTreeCard } from "@/render/farTreeCards";
import type { WindState } from "@/render/wind";
import { taxiRoadPoint, taxiRoadX } from "./taxiMotion";

/** The authored route, with a little either end for what is seen beyond it. */
const ROUTE = { from: -70, to: 610 };
/**
 * The modelled forest (build-taxi.py) reaches about 37 m either side; the cards
 * begin just inside it and run out past where the haze swallows everything.
 */
const BELT = { near: 33, far: 125 };
/** Metres of route merged into one batch of cards, as the authored roadside's chunks. */
const CHUNK = 40;
/** The road's own ground runs out at 70 m; the floor carries on under the far cards. */
const FLOOR = { near: 64, far: 132, y: -0.32 };

/**
 * The far forest as Episode 2 lays it: crossed painted cards in a belt, densest
 * near the modelled ranks and thinning outwards, about one tree per 18 m², every
 * crown as wide as it is tall so they close into one canopy, and tall emergents
 * standing above the canopy line here and there. Broadleaf old growth; a few sugar
 * palms and dead trees, no bamboo. Route frame: x across, z along.
 */
export function layoutTaxiFarForest(seed = 6242311): FarTreeCard[] {
  const random = seededRandom(seed);
  const trees: FarTreeCard[] = [];
  const length = ROUTE.to - ROUTE.from,
    depth = BELT.far - BELT.near;
  const place = (count: number, tall: boolean) => {
    for (let i = 0; i < count; i++) {
      const side = random() < 0.5 ? -1 : 1;
      // Biased towards the near edge of the belt; emergents spread evenly.
      const t = tall ? 0.05 + random() * 0.95 : random() ** 1.45;
      const lateral = side * (BELT.near + depth * t),
        along = ROUTE.from + random() * length;
      const at = taxiRoadPoint(lateral, along);
      const height = tall ? 30 + random() * 10 : 17 + random() * 13 + t * 6;
      const roll = random();
      const variant = tall
        ? CARD_VARIANT.emergent
        : roll < 0.06
          ? CARD_VARIANT.sugarPalm
          : roll < 0.1
            ? CARD_VARIANT.dead
            : roll < 0.3
              ? CARD_VARIANT.emergent
              : CARD_VARIANT.broadleaf[Math.floor(random() * 3)];
      trees.push({
        x: at.x,
        y: -0.35,
        z: at.z,
        yaw: random() * Math.PI,
        width: height * (tall ? 0.6 + random() * 0.25 : 0.75 + random() * 0.3),
        height,
        variant,
        cell: `${side}_${Math.floor((along - ROUTE.from) / CHUNK)}`,
      });
    }
  };
  const area = 2 * length * depth;
  place(Math.round(area / 18), false);
  place(Math.round(area / 220), true);
  return trees;
}

/**
 * The forest behind the forest. Past the last modelled rank the far cards carry
 * the old growth on to the haze on both sides, over a dark forest floor, so
 * whichever window Sora looks from, the trees never seem to end.
 */
export function buildTaxiFarForest(
  scene: Scene,
  route: TransformNode,
  wind: WindState,
  ground: Material | null,
): Mesh[] {
  const meshes = buildFarTreeCards(scene, "taxi_far_forest", layoutTaxiFarForest(), wind, route);
  if (!ground) return meshes;
  for (const side of [-1, 1])
    for (let from = ROUTE.from; from < ROUTE.to; from += CHUNK) {
      const positions: number[] = [],
        normals: number[] = [],
        uvs: number[] = [],
        indices: number[] = [];
      const steps = 4;
      for (let i = 0; i <= steps; i++) {
        const along = from + (i / steps) * CHUNK;
        for (const lateral of [FLOOR.near, FLOOR.far]) {
          const at = taxiRoadPoint(side * lateral, along);
          positions.push(at.x, FLOOR.y, at.z);
          normals.push(0, 1, 0);
          uvs.push(at.x / 3, at.z / 3);
        }
        if (i < steps) {
          const v = i * 2;
          // Wound to face up whichever side of the road it lies.
          if (side > 0) indices.push(v, v + 1, v + 2, v + 1, v + 3, v + 2);
          else indices.push(v, v + 2, v + 1, v + 1, v + 2, v + 3);
        }
      }
      const floor = new Mesh(`taxi_far_forest_floor_${side}_${from}`, scene);
      const data = new VertexData();
      data.positions = positions;
      data.normals = normals;
      data.uvs = uvs;
      data.indices = indices;
      data.applyToMesh(floor);
      floor.material = ground;
      floor.parent = route;
      floor.isPickable = false;
      meshes.push(floor);
    }
  return meshes;
}

/** Understorey plants cheap enough to plant twice: ferns, shrubs and fan palms (not bamboo). */
const UNDERSTOREY = /^(fern_02|shrub_02|M_palm_fan|M_palm_fan_dead)$/;

/**
 * A second planting of the understorey, sharing the first one's geometry: each
 * cell of ferns and shrubs again, a few metres further along and turned to the
 * road's new line there. It fills the gaps at trunk height without one more
 * vertex in memory, and it bends to the same wind.
 */
export function thickenTaxiUnderstorey(landscape: readonly Mesh[]): AbstractMesh[] {
  const copies: AbstractMesh[] = [];
  for (const mesh of landscape) {
    if (!UNDERSTOREY.test(mesh.material?.name ?? "")) continue;
    const z = mesh.getBoundingInfo().boundingBox.centerWorld.z;
    for (const shift of [9.5, -13]) {
      const to = z + shift;
      if (to < 0 || to > 540) continue;
      const copy = mesh.clone(`${mesh.name}_again_${shift}`, mesh.parent);
      copy.position.x += taxiRoadX(to) - taxiRoadX(z);
      copy.position.z += shift;
      copy.isPickable = false;
      copy.receiveShadows = true;
      copies.push(copy);
    }
  }
  return copies;
}
