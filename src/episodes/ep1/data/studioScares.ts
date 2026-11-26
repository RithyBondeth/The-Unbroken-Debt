import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/**
 * The studio's three scares (Episode 1 prologue; the user's picks on November 24, 2026,
 * in place of the dancer ghost, which was too much for the first scene of the first
 * episode). Each fires once per playthrough (StudioScares.ts):
 *
 * - picture: in the front room, while Sora has her back to it, the framed picture by the
 *   balcony doors comes off its nail and smashes face down on the floor.
 * - shadow: walking up to the partition (on her way to the back room), a flash of
 *   lightning throws a woman's shadow on the wall beside her, as if someone stood just
 *   behind her; she turns and there is no one. The figure is the Preay, the episode's
 *   ghost, there for the light only.
 * - altar: once Sora has lifted her satchel off the bed and turned away, the family altar
 *   behind her tears out of the wall: the vase smashes, the brass clatters, the bowl
 *   spins, the oil lamp falls and goes out, every light in the house dies and comes back
 *   stuttering. Then the storm breaks and the telephone rings (Prologue.ts).
 *
 * Positions are Blender's (tools/areas/ep1_area_studio.py: x east, y north, z up);
 * `runtime` turns them into the game's (x = -x, y = z, z = -y).
 */
export type StudioScareId = "picture" | "shadow" | "altar";

export const studioScareFlag = (id: StudioScareId): string => `ep1.scare.studio.${id}`;

/** Where what fell came to rest (node name to position and rotation), for checkpoints. */
export const FALLEN_FLAG = "ep1.studio.fallen";

export const runtime = (x: number, y: number, z: number): Vector3 => new Vector3(-x, z, -y);

/** Blender (x, y) of a runtime point. */
const plan = (p: Vector3): [number, number] => [-p.x, -p.z];

/** The front studio, between the facade (y 0) and the partition (y 6). */
export const FRONT = { y0: 0, y1: 6.0 };
/** The partition's face on the studio side, its doorway and the plain wall beside it. */
export const PARTITION = { y: 6.0, door: [0.15, 1.15], wall: [1.3, 4.3] } as const;
/** The back room begins past the airwell's back wall. */
export const BACK_ROOM_Y = 9.27;

export const PICTURE = {
  /** Not before Sora has been in the room this long (s). */
  after: 20,
  /** How far she must be from it (m, along the floor). */
  near: 1.6,
  far: 5.5,
  /** At least this far round from where she is looking (degrees): behind her. */
  behind: 110,
  /** How long the fall runs before what fell is laid still (s). */
  settle: 3,
};

export const SHADOW = {
  /** Not before Sora has been in the room this long (s). */
  after: 15,
  /** How far from the partition she must be (m): close, so the figure is behind her. */
  near: 0.5,
  far: 1.35,
  /** How squarely she must face it (her view's share pointing north). */
  facing: 0.6,
  /** Where the shadow's head falls: this far beside where she looks (m). */
  aside: 0.35,
  /** The flash comes in at a balcony door: its light starts just inside the glass (y),
   * this high (m), low enough that her shadow is thrown up the wall, not onto the floor.
   * From outside, 9 m off, it reached the partition's dark boards too weak to show her. */
  lightAt: 0.3,
  lightHeight: 1.8,
  /** The middles of the two balcony doors (x). */
  doors: [1.2, 3.4],
  /** The figure stands this much nearer the doors than Sora: just behind her (m). */
  behindSora: 0.6,
  /** The flash: pulses (s after the first), how fast each dies (s), how much brighter
   * than the storm's usual flashes (the strike is over the house, and the partition's
   * boards are dark). */
  pulses: [0, 0.13, 0.36],
  decay: 0.075,
  gain: 6,
  /** The reach clip's moment for her pose (s of 2): arms half up, towards Sora. */
  reach: 1.1,
};

export const ALTAR = {
  /** At least this long after the satchel is taken (s). */
  settle: 0.7,
  /** The altar this far round from where Sora is looking (degrees)... */
  behind: 75,
  /** ...or she has been in the back room with the satchel this long (s). */
  patience: 6,
  /** Out of the back room with the satchel this long, it falls anyway, heard from there (s). */
  offstage: 12,
  /** The shelf swings down on its east bracket to this (degrees). */
  tilt: 38,
  /** How long the fall runs before what fell is laid still (s). */
  rest: 5,
  /** After the tear: the lights die (s), and the scare is over once they are back. */
  powerCut: 1.35,
};

/** Degrees between where Sora looks (along the floor) and the direction to `target`. */
export function angleTo(eye: Vector3, forward: Vector3, target: Vector3): number {
  const look = new Vector3(forward.x, 0, forward.z);
  const to = new Vector3(target.x - eye.x, 0, target.z - eye.z);
  if (look.lengthSquared() < 1e-8 || to.lengthSquared() < 1e-8) return 0;
  const cos = Vector3.Dot(look.normalize(), to.normalize());
  return (Math.acos(Math.max(-1, Math.min(1, cos))) * 180) / Math.PI;
}

/** Is Sora in the front studio? */
export function inFrontStudio(eye: Vector3): boolean {
  const [, y] = plan(eye);
  return y > FRONT.y0 && y < FRONT.y1;
}

/** Is Sora in the back room? */
export function inBackRoom(eye: Vector3): boolean {
  return plan(eye)[1] > BACK_ROOM_Y;
}

/** Should the picture fall now? */
export function pictureDue(
  time: number,
  eye: Vector3,
  forward: Vector3,
  picture: Vector3,
): boolean {
  if (time < PICTURE.after || !inFrontStudio(eye)) return false;
  const d = Math.hypot(picture.x - eye.x, picture.z - eye.z);
  if (d < PICTURE.near || d > PICTURE.far) return false;
  return angleTo(eye, forward, picture) >= PICTURE.behind;
}

/** The shadow scare's set-up, in runtime coordinates. */
export interface ShadowShot {
  /** Where the flash comes from, and the point on the wall it is aimed at (the head's shadow). */
  light: Vector3;
  wall: Vector3;
  /** Where the figure stands, and which way she faces (yaw, 0 = +Z). */
  feet: Vector3;
  yaw: number;
}

/**
 * Where to put the light and the figure so her head's shadow falls on the partition just
 * beside where Sora is looking, the figure standing behind her; null if Sora is not
 * walking up to the partition. `headHeight`: the figure's head above her feet (m).
 */
export function shadowShot(
  time: number,
  eye: Vector3,
  forward: Vector3,
  headHeight = 1.55,
): ShadowShot | null {
  if (time < SHADOW.after || !inFrontStudio(eye)) return null;
  const [x, y] = plan(eye);
  const fromWall = PARTITION.y - y;
  if (fromWall < SHADOW.near || fromWall > SHADOW.far) return null;
  // Her view along the floor, in Blender's axes; north is +y.
  const flat = Math.hypot(forward.x, forward.z);
  if (flat < 1e-6) return null;
  const fx = -forward.x / flat,
    fy = -forward.z / flat;
  if (fy < SHADOW.facing) return null;
  // Where her eyes meet the wall, then a step aside onto plain wall (never the doorway).
  const look = x + (fx * fromWall) / fy;
  const [w0, w1] = PARTITION.wall;
  const clamp = (t: number) => Math.max(w0, Math.min(w1, t));
  const east = clamp(look + SHADOW.aside),
    west = clamp(look - SHADOW.aside);
  // Beside her gaze, not on it; where the wall runs out on one side, the other.
  const tx = Math.abs(east - look) >= 0.2 ? east : Math.abs(west - look) >= 0.2 ? west : east;
  const wallY = PARTITION.y - 0.01;
  // The figure stands just behind Sora, on the line from that point on the wall back
  // through the middle of the nearer balcony door.
  const door = SHADOW.doors.reduce((a, b) => (Math.abs(b - tx) < Math.abs(a - tx) ? b : a));
  const head = { y: y - SHADOW.behindSora, x: 0 };
  head.x = tx + ((door - tx) * (wallY - head.y)) / wallY;
  // The light on the same line, just inside the door; her head's shadow lands where that
  // line, tipped down through her head, meets the wall (a little under her own height).
  const ly = SHADOW.lightAt;
  const light = {
    x: tx + ((head.x - tx) * (wallY - ly)) / (wallY - head.y),
    y: ly,
    z: SHADOW.lightHeight,
  };
  const reach = (wallY - ly) / (head.y - ly);
  const wall = { x: tx, y: wallY, z: light.z + (headHeight - light.z) * reach };
  if (wall.z < 0.8) return null;
  const feet = runtime(head.x, head.y, 0);
  return {
    light: runtime(light.x, light.y, light.z),
    wall: runtime(wall.x, wall.y, wall.z),
    feet,
    yaw: Math.atan2(eye.x - feet.x, eye.z - feet.z),
  };
}

/**
 * Should the altar fall now? Sora has had the satchel `holding` seconds, has been in the
 * back room with it `waited` seconds (and out of it `outside` seconds), and the altar is
 * `away` degrees round from her view. Out of the room it still falls in the end: the
 * telephone rings only after it, and she must not be left waiting for it.
 */
export function altarDue(holding: number, waited: number, away: number, outside = 0): boolean {
  if (holding < ALTAR.settle) return false;
  return away >= ALTAR.behind || waited >= ALTAR.patience || outside >= ALTAR.offstage;
}

/** Poses of what fell, as stored in FALLEN_FLAG (millimetres and four decimals). */
export function encodePoses(poses: Record<string, readonly number[]>): string {
  const out: Record<string, number[]> = {};
  for (const [name, values] of Object.entries(poses))
    out[name] = values.map((v, i) =>
      i < 3 ? Math.round(v * 1000) / 1000 : Math.round(v * 1e4) / 1e4,
    );
  return JSON.stringify(out);
}

export function decodePoses(text: unknown): Record<string, number[]> {
  if (typeof text !== "string" || !text) return {};
  try {
    const parsed = JSON.parse(text) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    const out: Record<string, number[]> = {};
    for (const [name, values] of Object.entries(parsed as Record<string, unknown>))
      if (
        Array.isArray(values) &&
        values.length === 7 &&
        values.every((v) => typeof v === "number")
      )
        out[name] = values;
    return out;
  } catch {
    return {};
  }
}
