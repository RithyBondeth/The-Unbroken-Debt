import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsShapeBox } from "@babylonjs/core/Physics/v2/physicsShape";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { Scene } from "@babylonjs/core/scene";

/**
 * Open-front roadside shop indices in `tools/areas/village_road.py` (`SHOPS`):
 * 0 = Noodle Stall, 2 = Moto Shop, 3 = Grocery, 5 = Barber Shop, 6 = Dentist/Salon, 7 = Salon.
 * (Shop 1 TV/Coffee has a waist-high serving counter; Shop 4 Outpost has barred storm doors.)
 */
const OPEN_FRONT_SHOPS: readonly { idx: number; hw: number }[] = [
  { idx: 0, hw: 2.75 },
  { idx: 2, hw: 2.85 },
  { idx: 3, hw: 2.95 },
  { idx: 5, hw: 2.75 },
  { idx: 6, hw: 3.15 },
  { idx: 7, hw: 2.65 },
];

/** Open doorway width matches `taxi_roadside_details.py` (`door_w = 1.95 m`). */
const DOOR_HALF_WIDTH = 0.94;
const INTERIOR_DEPTH = 3.62; // local x in [-3.50, +0.12]
const WALL_THICK = 0.22;
const WALL_HEIGHT = 4.2;

export interface OpenShopsHandle {
  openedCount: number;
  dispose(): void;
}

/**
 * Replaces the solid blocking interior collider (`col_vroad_shop_{idx}_in`) on all six open-front
 * roadside shops with hollow perimeter walls + a seamless interior floor flush with the veranda
 * deck (`deck_top + 0.006 m`), leaving the full `1.88 m` doorway open so Sora can walk straight
 * inside every open roadside shop to inspect its detailed interior and clues.
 */
export function openWalkableShopInteriors(scene: Scene): OpenShopsHandle {
  const created: { node: TransformNode; body: PhysicsBody }[] = [];
  let openedCount = 0;

  const addBox = (
    name: string,
    origin: Vector3,
    front: Vector3,
    side: Vector3,
    rot: Quaternion,
    x0: number,
    x1: number,
    y0: number,
    y1: number,
    z0: number,
    z1: number,
  ): void => {
    const cx = (x0 + x1) * 0.5;
    const cy = (y0 + y1) * 0.5;
    const cz = (z0 + z1) * 0.5;
    const pos = origin
      .add(front.scale(cx))
      .add(side.scale(cy))
      .add(new Vector3(0, cz, 0));
    const size = new Vector3(Math.abs(x1 - x0), Math.abs(z1 - z0), Math.abs(y1 - y0));

    const node = new TransformNode(name, scene);
    node.position.copyFrom(pos);
    node.rotationQuaternion = rot.clone();
    node.metadata = { surface: "teak" };
    const body = new PhysicsBody(node, PhysicsMotionType.STATIC, false, scene);
    const shape = new PhysicsShapeBox(Vector3.Zero(), Quaternion.Identity(), size, scene);
    shape.material = { friction: 0.8 };
    body.shape = shape;
    created.push({ node, body });
  };

  for (const { idx, hw } of OPEN_FRONT_SHOPS) {
    const inMesh = scene.getMeshByName(`col_vroad_shop_${idx}_in`);
    const deckMesh = scene.getMeshByName(`col_vroad_shop_${idx}_deck`);
    const oldBodyNode = scene.getTransformNodeByName(`col_vroad_shop_${idx}_in_body`);
    if (!(inMesh instanceof AbstractMesh) || !(deckMesh instanceof AbstractMesh)) continue;

    // Dispose the original solid blocking physics body (keeps the hidden source mesh untouched)
    if (oldBodyNode?.physicsBody) {
      oldBodyNode.physicsBody.shape?.dispose();
      oldBodyNode.physicsBody.dispose();
    }

    inMesh.computeWorldMatrix(true);
    deckMesh.computeWorldMatrix(true);
    const inBox = inMesh.getBoundingInfo().boundingBox;
    const deckBox = deckMesh.getBoundingInfo().boundingBox;

    // Derive exact world-space horizontal shop frame directly from interior->veranda direction
    // (100% invariant to glTF handedness mirroring across both north & south sides of the road!)
    const front = new Vector3(
      deckBox.centerWorld.x - inBox.centerWorld.x,
      0,
      deckBox.centerWorld.z - inBox.centerWorld.z,
    );
    if (front.lengthSquared() < 1e-4) continue;
    front.normalize();
    const up = Vector3.Up();
    // Right-handed/left-handed safe orthonormal basis matching Babylon's TransformNode local axes:
    // local +X = front, local +Y = up, local +Z = side (cross(front, up) in LH gives det = +1)
    const side = Vector3.Cross(front, up).normalize();
    const rotMat = Matrix.FromValues(
      front.x,
      front.y,
      front.z,
      0,
      up.x,
      up.y,
      up.z,
      0,
      side.x,
      side.y,
      side.z,
      0,
      0,
      0,
      0,
      1,
    );
    const rot = Quaternion.FromRotationMatrix(rotMat);

    // Reference origin at center of interior footprint (x=0), y=0 at interior floor level
    const floorTopY = deckBox.maximumWorld.y + 0.006;
    const origin = new Vector3(inBox.centerWorld.x, floorTopY, inBox.centerWorld.z);
    const halfD = INTERIOR_DEPTH * 0.5; // 1.81 m -> back at -1.81, front doorway threshold at +1.81

    // 1. Walkable interior floor seamlessly bridging from the veranda deck to the back wall
    addBox(
      `col_vroad_shop_${idx}_open_floor`,
      origin,
      front,
      side,
      rot,
      -halfD,
      halfD + 0.14,
      -hw - 0.1,
      hw + 0.1,
      -0.85,
      0.0,
    );
    // 2. Solid back wall
    addBox(
      `col_vroad_shop_${idx}_open_back`,
      origin,
      front,
      side,
      rot,
      -halfD - 0.05,
      -halfD + WALL_THICK,
      -hw - 0.16,
      hw + 0.16,
      -0.5,
      WALL_HEIGHT,
    );
    // 3. Left & right interior side walls
    addBox(
      `col_vroad_shop_${idx}_open_wall_l`,
      origin,
      front,
      side,
      rot,
      -halfD,
      halfD + 0.06,
      -hw - WALL_THICK,
      -hw + 0.04,
      -0.5,
      WALL_HEIGHT,
    );
    addBox(
      `col_vroad_shop_${idx}_open_wall_r`,
      origin,
      front,
      side,
      rot,
      -halfD,
      halfD + 0.06,
      hw - 0.04,
      hw + WALL_THICK,
      -0.5,
      WALL_HEIGHT,
    );
    // 4. Front flanking doorway walls (leaving [-DOOR_HALF_WIDTH, +DOOR_HALF_WIDTH] wide open!)
    addBox(
      `col_vroad_shop_${idx}_open_front_l`,
      origin,
      front,
      side,
      rot,
      halfD - 0.18,
      halfD + 0.06,
      -hw - 0.14,
      -DOOR_HALF_WIDTH,
      -0.5,
      WALL_HEIGHT,
    );
    addBox(
      `col_vroad_shop_${idx}_open_front_r`,
      origin,
      front,
      side,
      rot,
      halfD - 0.18,
      halfD + 0.06,
      DOOR_HALF_WIDTH,
      hw + 0.14,
      -0.5,
      WALL_HEIGHT,
    );

    openedCount++;
  }

  return {
    openedCount,
    dispose(): void {
      for (const rec of created) {
        rec.body.shape?.dispose();
        rec.body.dispose();
        rec.node.dispose();
      }
      created.length = 0;
    },
  };
}
