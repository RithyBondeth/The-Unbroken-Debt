import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import { foliageKind } from "@/render/FoliageWind";
import { namedRoot, type PlantRules } from "@/render/plantHeights";

/**
 * Which of the pagoda's meshes are trees. Everything in the area hangs off one root
 * (`pagoda_axes`, or a lost-garden `zone_`), so the trees are named: `tree_12`, `bamboo_40`,
 * `banyan.002`, `dead_3`. Their primitives (bark, moss, leaves) are children of that node
 * and bend together from its foot.
 */
export const TREE_NODE = /^(tree_\d+|bamboo_\d+|banyan|dead_\d+)(\.\d+)?$/;

/**
 * Wind-material meshes that are not trees. Bark here is mostly fig roots poured over
 * stupas, creeper stems on the walls, fallen logs and bamboo stakes: they must not move,
 * or they slide off what they grip. Fig crowns and creeper leaves only shiver; undergrowth
 * and grass patches bend from their own feet.
 */
export function looseMotion(mesh: Mesh): "rigid" | "flutter" | "ground" {
  const kind = foliageKind(mesh.material?.name ?? "");
  if (kind === "grass") return "ground";
  if (kind !== "leaf") return "rigid";
  return /fig|creeper|liana/.test(mesh.name) ? "flutter" : "ground";
}

export const PAGODA_PLANTS: PlantRules = { rootOf: namedRoot(TREE_NODE), loose: looseMotion };
