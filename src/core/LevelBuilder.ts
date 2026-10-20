import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { VertexBuffer } from "@babylonjs/core/Buffers/buffer";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsShapeBox, PhysicsShapeMesh } from "@babylonjs/core/Physics/v2/physicsShape";
import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import type { Node } from "@babylonjs/core/node";
import type { Scene } from "@babylonjs/core/scene";
import type { Surface } from "./Physics";
import type { Ladder } from "../player/PlayerController";
import { facingToGltf, isBoxShape, parseNodeName } from "./levelNodes";

/** Custom properties from Blender arrive as glTF extras. */
export type Extras = Record<string, unknown>;

export interface LevelMarker {
  name: string;
  position: Vector3;
  /** Direction the node's forward axis (Blender +Y) points, as a yaw in radians. */
  yaw: number;
  extras: Extras;
}

export interface Level {
  spawns: Map<string, LevelMarker>;
  ladders: Ladder[];
  /** Patrol routes by id, nodes in order. */
  patrols: Map<string, LevelMarker[]>;
  interactables: LevelMarker[];
  colliders: { name: string; shape: "box" | "mesh"; surface: Surface }[];
  /** Problems found while building, for the spike panel and the console. */
  warnings: string[];
}

const SURFACES: Surface[] = ["teak", "dirt", "mud", "leaves", "stone", "water"];

/** Reads the extras the glTF loader keeps in `metadata.gltf.extras`. */
export function extrasOf(node: Node): Extras {
  const metadata = node.metadata as { gltf?: { extras?: Extras } } | null | undefined;
  return metadata?.gltf?.extras ?? {};
}

/**
 * Turns named nodes from a loaded area into game objects (TDD section 7.1).
 * This first version, from Spike S3, handles `col_`, `ladder_`, `spawn_`,
 * `patrol_` and `interact_`; the other prefixes are reported and left for Phase 3.
 *
 * Colliders are rebuilt in world space rather than attached to the imported
 * meshes: the glTF loader mirrors the scene into Babylon's left-handed space
 * with a negative scale on its root node, which physics bodies must not inherit.
 */
export function buildLevel(scene: Scene, nodes: readonly Node[]): Level {
  const level: Level = {
    spawns: new Map(),
    ladders: [],
    patrols: new Map(),
    interactables: [],
    colliders: [],
    warnings: [],
  };
  const unsupported = new Set<string>();

  for (const node of nodes) {
    const parsed = parseNodeName(node.name);
    if (!parsed) continue;
    const extras = extrasOf(node);
    if (node instanceof TransformNode) node.computeWorldMatrix(true);

    switch (parsed.kind) {
      case "col": {
        if (!(node instanceof Mesh)) {
          level.warnings.push(`${node.name}: col_ node has no mesh`);
          break;
        }
        const surface = SURFACES.find((s) => s === extras.surface);
        if (!surface) level.warnings.push(`${node.name}: missing or unknown surface, using dirt`);
        const shape = addCollider(scene, node, surface ?? "dirt");
        level.colliders.push({ name: node.name, shape, surface: surface ?? "dirt" });
        hide(node);
        break;
      }
      case "ladder": {
        if (!(node instanceof Mesh)) break;
        const ladder = ladderFrom(node, extras);
        if (ladder) level.ladders.push(ladder);
        else level.warnings.push(`${node.name}: ladder needs facing "+x", "-x", "+y" or "-y"`);
        hide(node);
        break;
      }
      case "spawn":
        level.spawns.set(parsed.id, marker(node as TransformNode, extras));
        break;
      case "patrol": {
        const route = level.patrols.get(parsed.id) ?? [];
        route[parsed.order ?? route.length] = marker(node as TransformNode, extras);
        level.patrols.set(parsed.id, route);
        break;
      }
      case "interact":
        level.interactables.push(marker(node as TransformNode, extras));
        break;
      default:
        unsupported.add(parsed.kind);
    }
  }

  // Patrol numbers may skip (01, 02, 05); keep the order and drop the holes.
  for (const [id, route] of level.patrols) level.patrols.set(id, route.filter(Boolean));
  for (const kind of unsupported) level.warnings.push(`${kind}_ nodes are not built yet`);
  return level;
}

function hide(mesh: AbstractMesh): void {
  mesh.isVisible = false;
  mesh.isPickable = false;
}

function marker(node: TransformNode, extras: Extras): LevelMarker {
  const world = node.getWorldMatrix();
  // Blender +Y (the forward axis of an empty) is glTF -Z.
  const forward = Vector3.TransformNormal(new Vector3(0, 0, -1), world);
  return {
    name: node.name,
    position: node.getAbsolutePosition().clone(),
    yaw: Math.atan2(forward.x, forward.z),
    extras,
  };
}

/** The ladder volume is the box's world bounds; `facing` gives its normal. */
function ladderFrom(mesh: Mesh, extras: Extras): Ladder | null {
  const facing = facingToGltf(extras.facing);
  if (!facing) return null;
  const box = mesh.getBoundingInfo().boundingBox;
  // `facing` is in Blender world axes, so convert it with the parent's matrix only.
  const parent =
    mesh.parent instanceof TransformNode ? mesh.parent.getWorldMatrix() : Matrix.Identity();
  const normal = Vector3.TransformNormal(Vector3.FromArray(facing), parent);
  normal.y = 0;
  normal.normalize();
  return { min: box.minimumWorld.clone(), max: box.maximumWorld.clone(), normal };
}

/** Static collider in world space; box shapes for boxes, triangle meshes otherwise. */
function addCollider(scene: Scene, mesh: Mesh, surface: Surface): "box" | "mesh" {
  const positions = mesh.getVerticesData(VertexBuffer.PositionKind) ?? [];
  const world = mesh.getWorldMatrix();
  const anchor = new TransformNode(`${mesh.name}_body`, scene);
  anchor.metadata = { surface };
  const body = new PhysicsBody(anchor, PhysicsMotionType.STATIC, false, scene);

  if (isBoxShape(positions)) {
    const { minimum, maximum } = mesh.getBoundingInfo().boundingBox;
    const shape = new PhysicsShapeBox(...orientedBox(minimum, maximum, world), scene);
    shape.material = { friction: 0.8 };
    body.shape = shape;
    return "box";
  }

  const indices = mesh.getIndices() ?? [];
  const baked = new Float32Array(positions.length);
  const v = new Vector3();
  for (let i = 0; i < positions.length; i += 3) {
    Vector3.TransformCoordinatesFromFloatsToRef(
      positions[i],
      positions[i + 1],
      positions[i + 2],
      world,
      v,
    );
    v.toArray(baked, i);
  }
  // A mirrored transform flips triangle winding; swap two corners to restore it.
  const flipped = Array.from(indices);
  if (world.determinant() < 0) {
    for (let i = 0; i < flipped.length; i += 3) {
      [flipped[i + 1], flipped[i + 2]] = [flipped[i + 2], flipped[i + 1]];
    }
  }
  const proxy = new Mesh(`${mesh.name}_shape`, scene);
  const data = new VertexData();
  data.positions = baked;
  data.indices = flipped;
  data.applyToMesh(proxy);
  proxy.isVisible = false;
  proxy.isPickable = false;
  const shape = new PhysicsShapeMesh(proxy, scene);
  shape.material = { friction: 0.8 };
  body.shape = shape;
  return "mesh";
}

/**
 * Centre, rotation and size of a local-space box after a world transform that
 * may include rotation, scale and a mirror, as the arguments of `PhysicsShapeBox`.
 */
export function orientedBox(
  min: Vector3,
  max: Vector3,
  world: Matrix,
): [center: Vector3, rotation: Quaternion, extents: Vector3] {
  const origin = Vector3.TransformCoordinates(min, world);
  const edge = (x: number, y: number, z: number) =>
    Vector3.TransformCoordinates(new Vector3(x, y, z), world).subtractInPlace(origin);
  const ax = edge(max.x, min.y, min.z);
  const ay = edge(min.x, max.y, min.z);
  const az = edge(min.x, min.y, max.z);
  const extents = new Vector3(ax.length(), ay.length(), az.length());
  ax.normalize();
  ay.normalize();
  az.normalize();
  // A mirror makes the axes left-handed; a box is symmetric, so flip one back.
  if (Vector3.Dot(Vector3.Cross(ax, ay), az) < 0) az.scaleInPlace(-1);
  const rotation = Quaternion.RotationQuaternionFromAxis(ax, ay, az);
  const center = Vector3.TransformCoordinates(Vector3.Center(min, max), world);
  return [center, rotation, extents];
}
