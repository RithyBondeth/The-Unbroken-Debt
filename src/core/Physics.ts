import HavokPhysics from "@babylonjs/havok";
import havokWasmUrl from "@babylonjs/havok/lib/esm/HavokPhysics.wasm?url";
import { HavokPlugin } from "@babylonjs/core/Physics/v2/Plugins/havokPlugin";
import { PhysicsAggregate } from "@babylonjs/core/Physics/v2/physicsAggregate";
import { PhysicsShapeType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Scene } from "@babylonjs/core/scene";
// Babylon 9 splits physics registration: the joined component adds scene.enablePhysics.
import "@babylonjs/core/Physics/joinedPhysicsEngineComponent";
import "@babylonjs/core/Physics/v2/physicsEngineComponent";

export const GRAVITY = new Vector3(0, -9.81, 0);

/** Surfaces drive footstep sounds and noise (TDD section 7.1, `col_` surface property). */
export type Surface = "teak" | "dirt" | "mud" | "leaves" | "stone" | "water";

/** Loads the Havok WASM module and enables physics on the scene (TDD section 4). */
export async function enablePhysics(scene: Scene): Promise<void> {
  const havok = await HavokPhysics({ locateFile: () => havokWasmUrl });
  const ok = scene.enablePhysics(GRAVITY.clone(), new HavokPlugin(true, havok));
  if (!ok || !scene.getPhysicsEngine()) {
    throw new Error(`Physics failed to start (enablePhysics returned ${String(ok)})`);
  }
}

/**
 * Makes a mesh a static box collider and tags its surface. Stand-in for what
 * LevelBuilder will do with `col_` nodes from Blender.
 */
export function addStaticBox(mesh: Mesh, surface: Surface): PhysicsAggregate {
  mesh.metadata = { ...(mesh.metadata as object | null), surface };
  return new PhysicsAggregate(
    mesh,
    PhysicsShapeType.BOX,
    { mass: 0, friction: 0.8 },
    mesh.getScene(),
  );
}

/** Reads the surface tag from whatever a physics query hit. */
export function surfaceOf(node: { metadata?: unknown } | null | undefined): Surface | undefined {
  const metadata = node?.metadata as { surface?: Surface } | null | undefined;
  return metadata?.surface;
}

/**
 * Adds an invisible ramp collider from `bottom` to `top` (both on the ramp's
 * walking surface, centred across its width). Stairs get one of these over the
 * step noses so walking up and down is smooth; in levels this is a `col_` mesh.
 */
export function addStaticRamp(
  scene: Scene,
  name: string,
  bottom: Vector3,
  top: Vector3,
  width: number,
  surface: Surface,
): Mesh {
  const thickness = 0.1;
  const direction = top.subtract(bottom);
  const length = direction.length();
  direction.normalize();
  const side = Vector3.Cross(Vector3.Up(), direction).normalize();
  const normal = Vector3.Cross(direction, side).normalize();

  const ramp = CreateBox(name, { width, height: thickness, depth: length }, scene);
  ramp.rotationQuaternion = Quaternion.FromLookDirectionLH(direction, normal);
  // Centre the box so its top face lies on the bottom→top line.
  ramp.position = Vector3.Center(bottom, top).subtract(normal.scale(thickness / 2));
  ramp.isVisible = false;
  ramp.isPickable = false;
  addStaticBox(ramp, surface);
  return ramp;
}
