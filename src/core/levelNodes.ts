/**
 * Node naming rules for levels built in Blender (Technical Design Document,
 * section 7.1). Pure functions, so the rules can be tested without a scene.
 */

export type NodeKind =
  | "trigger"
  | "interact"
  | "spawn"
  | "patrol"
  | "hide"
  | "audiozone"
  | "light_flame"
  | "col"
  | "ladder"
  | "nav"
  | "marker";

export interface ParsedNode {
  kind: NodeKind;
  /** The rest of the name after the prefix (`col_stairs_front` → `stairs_front`). */
  id: string;
  /** Patrol nodes only: position in the route (`patrol_bot_03` → 3). */
  order?: number;
}

// Longest prefixes first so `light_flame_` is not read as something shorter.
const PREFIXES: NodeKind[] = [
  "light_flame",
  "audiozone",
  "interact",
  "trigger",
  "ladder",
  "patrol",
  "spawn",
  "hide",
  "col",
  "nav",
  "marker",
];

/** Reads a node name; returns null for plain render meshes. */
export function parseNodeName(name: string): ParsedNode | null {
  const kind = PREFIXES.find((prefix) => name.startsWith(`${prefix}_`));
  if (!kind) return null;
  const rest = name.slice(kind.length + 1);
  if (kind !== "patrol") return { kind, id: rest };
  // patrol_<id>_NN: the route id may itself contain underscores.
  const match = /^(.+)_(\d+)$/.exec(rest);
  if (!match) return null;
  return { kind, id: match[1], order: Number(match[2]) };
}

/**
 * Converts a ladder's `facing` property, written in Blender's axes ("+x", "-x",
 * "+y", "-y"; Z up), into the glTF direction it exports as (Y up, Blender +Y
 * becomes glTF -Z). Returns null for anything else.
 */
export function facingToGltf(facing: unknown): [number, number, number] | null {
  switch (typeof facing === "string" ? facing.trim().toLowerCase() : "") {
    case "+x":
    case "x":
      return [1, 0, 0];
    case "-x":
      return [-1, 0, 0];
    case "+y":
    case "y":
      return [0, 0, -1];
    case "-y":
      return [0, 0, 1];
    default:
      return null;
  }
}

/**
 * True when every vertex sits on a face of the mesh's own bounding box and
 * each axis has exactly two values: a box, which becomes a cheap box collider
 * (any other `col_` mesh becomes a triangle mesh collider).
 */
export function isBoxShape(positions: ArrayLike<number>, tolerance = 1e-4): boolean {
  if (positions.length < 24) return false;
  for (let axis = 0; axis < 3; axis++) {
    let min = Infinity;
    let max = -Infinity;
    for (let i = axis; i < positions.length; i += 3) {
      min = Math.min(min, positions[i]);
      max = Math.max(max, positions[i]);
    }
    if (max - min < tolerance) return false;
    for (let i = axis; i < positions.length; i += 3) {
      const v = positions[i];
      if (Math.abs(v - min) > tolerance && Math.abs(v - max) > tolerance) return false;
    }
  }
  return true;
}
