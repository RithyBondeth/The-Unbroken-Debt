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
export type StudioScareId =
  | "picture"
  | "shadow"
  | "altar"
  | "fan"
  | "book"
  | "bathFaucet"
  | "bathMirror"
  | "bathTank"
  | "bathDoor"
  | "doorWatcher"
  | "stairSteps"
  | "balconyKnock"
  | "phantomRing"
  | "partitionDoor"
  | "bedBreath"
  | "chairTurn"
  | "dropBook"
  | "balconySlam"
  | "hallFlash";

export type StudioDoorId =
  "haunt_partition_door" | "haunt_bedroom_door" | "haunt_bath_door" | "haunt_balcony_door";

export interface StudioDoorConfig {
  openDeg: number;
  closedDeg: number;
  ajarDeg: number;
  initialDeg: number;
}

export const STUDIO_DOORS: Record<StudioDoorId, StudioDoorConfig> = {
  haunt_partition_door: { openDeg: 88, closedDeg: 0, ajarDeg: 24, initialDeg: 88 },
  haunt_bedroom_door: { openDeg: 88, closedDeg: 0, ajarDeg: 26, initialDeg: 88 },
  haunt_bath_door: { openDeg: 132, closedDeg: 0, ajarDeg: 36, initialDeg: 132 },
  // West balcony French casement swings inward (+42° around east stile hinge = -42° in Blender Z)
  haunt_balcony_door: { openDeg: -42, closedDeg: 0, ajarDeg: -16, initialDeg: 0 },
};

export type StudioSpaceName = "studio" | "studioBack" | "bathroom";
export type StudioHauntPhase = 1 | 2 | 3 | 4;

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
/** The rear bathroom annex behind the back bedroom (doorway at y 14.0..14.15). */
export const BATHROOM = {
  y0: 14.08,
  y1: 16.75,
  x0: 0,
  x1: 3.35,
  doorOpenDeg: 132,
  doorAjarDeg: 40,
} as const;

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

/** Is Sora inside the rear tiled bathroom annex? */
export function inBathroom(eye: Vector3): boolean {
  const [x, y] = plan(eye);
  return y >= BATHROOM.y0 && x >= BATHROOM.x0 - 0.1 && x <= BATHROOM.x1 + 0.1;
}

/** Acoustic zone for Sora's current position in the shophouse studio. */
export function studioSpaceAt(eye: Vector3): StudioSpaceName {
  if (inBathroom(eye)) return "bathroom";
  if (plan(eye)[1] >= 9.0) return "studioBack";
  return "studio";
}

/** Current psychological horror escalation phase across the studio floor. */
export function studioHauntPhase(state: {
  kitCount: number;
  visitedBackOrBath: boolean;
  altarDone: boolean;
  phoneAnswered: boolean;
}): StudioHauntPhase {
  if (state.phoneAnswered) return 4;
  if (state.altarDone) return 3;
  if (state.visitedBackOrBath || state.kitCount >= 2) return 2;
  return 1;
}

/** Phase 1: ceiling fan creeps silently off-camera in the front studio. */
export function fanDriftDue(time: number, eye: Vector3, forward: Vector3, fan: Vector3): boolean {
  if (time < 10 || !inFrontStudio(eye)) return false;
  return angleTo(eye, forward, fan) >= 65;
}

/** Phase 1: featured shelf book slides out of the bookcase while Sora looks away. */
export function bookSlideDue(time: number, eye: Vector3, forward: Vector3, book: Vector3): boolean {
  if (time < 16 || !inFrontStudio(eye)) return false;
  const d = Math.hypot(book.x - eye.x, book.z - eye.z);
  if (d < 1.1 || d > 4.6) return false;
  return angleTo(eye, forward, book) >= 95;
}

/** Phase 2: Sora steps into the bathroom and faces the antique foxed mirror. */
export function bathMirrorDue(eye: Vector3, forward: Vector3, mirror: Vector3): boolean {
  if (!inBathroom(eye)) return false;
  const d = Math.hypot(mirror.x - eye.x, mirror.z - eye.z);
  if (d > 2.15) return false;
  return angleTo(eye, forward, mirror) <= 34;
}

/** Phase 2: looking toward the dark tiled Khmer water cistern triggers ripples and dipper shift. */
export function bathTankDue(eye: Vector3, forward: Vector3, tank: Vector3): boolean {
  if (!inBathroom(eye)) return false;
  const d = Math.hypot(tank.x - eye.x, tank.z - eye.z);
  if (d > 2.35) return false;
  return angleTo(eye, forward, tank) <= 45;
}

/** Phase 2: after the mirror scare, the louvred door creaks partway shut behind her. */
export function bathDoorDue(
  eye: Vector3,
  forward: Vector3,
  door: Vector3,
  mirrorDone: boolean,
): boolean {
  if (!mirrorDone || !inBathroom(eye)) return false;
  const d = Math.hypot(door.x - eye.x, door.z - eye.z);
  if (d > 2.7) return false;
  return angleTo(eye, forward, door) >= 75;
}

/** Phase 4: glancing north down the corridor reveals a figure peeking around the back doorway. */
export function doorWatcherDue(
  eye: Vector3,
  forward: Vector3,
  watcher: Vector3,
  phoneAnswered: boolean,
): boolean {
  if (!phoneAnswered || inBackRoom(eye)) return false;
  const [, y] = plan(eye);
  if (y < 2.2 || y > 8.6) return false;
  return angleTo(eye, forward, watcher) <= 32;
}

/** Phase 4: reaching the stair gate with the full kit triggers hurried footsteps behind Sora. */
export function stairStepsDue(
  eye: Vector3,
  stairDoor: Vector3,
  phoneAnswered: boolean,
  kitComplete: boolean,
): boolean {
  if (!phoneAnswered || !kitComplete) return false;
  return Math.hypot(stairDoor.x - eye.x, stairDoor.z - eye.z) <= 2.2;
}

/** Phase 1/2: three urgent knocks tap directly on the wet balcony glass behind Sora. */
export function balconyKnockDue(
  time: number,
  eye: Vector3,
  forward: Vector3,
  balcony: Vector3,
): boolean {
  if (time < 26 || !inFrontStudio(eye)) return false;
  const d = Math.hypot(balcony.x - eye.x, balcony.z - eye.z);
  if (d < 1.2 || d > 5.4) return false;
  return angleTo(eye, forward, balcony) >= 85;
}

/** Phase 2: solitary impossible half-ring from the unpowered hallway phone before the altar falls. */
export function phantomRingDue(
  time: number,
  eye: Vector3,
  visitedBackOrBath: boolean,
  altarDone: boolean,
): boolean {
  if (altarDone || !visitedBackOrBath || time < 32) return false;
  return inBackRoom(eye) || inFrontStudio(eye);
}

/** Phase 2: close-mic low breathing rises from under the bed as Sora nears the satchel. */
export function bedBreathDue(eye: Vector3, bedAt: Vector3, altarDone: boolean): boolean {
  if (altarDone || !inBackRoom(eye) || inBathroom(eye)) return false;
  return Math.hypot(bedAt.x - eye.x, bedAt.z - eye.z) <= 2.1;
}

/** Phase 2/3: wooden stool silently rotates toward the doorway while Sora looks away. */
export function chairTurnDue(
  time: number,
  eye: Vector3,
  forward: Vector3,
  stoolAt: Vector3,
  visitedBackOrBath: boolean,
): boolean {
  if (!visitedBackOrBath || time < 22 || !inFrontStudio(eye)) return false;
  const d = Math.hypot(stoolAt.x - eye.x, stoolAt.z - eye.z);
  if (d < 0.8 || d > 4.8) return false;
  return angleTo(eye, forward, stoolAt) >= 80;
}

/** Phase 2/3: upper bookcase volume drops heavily onto the cement floor behind Sora. */
export function dropBookDue(
  time: number,
  eye: Vector3,
  forward: Vector3,
  bookAt: Vector3,
  visitedBackOrBath: boolean,
): boolean {
  if (!visitedBackOrBath || time < 28 || !inFrontStudio(eye)) return false;
  const d = Math.hypot(bookAt.x - eye.x, bookAt.z - eye.z);
  if (d < 1.2 || d > 4.6) return false;
  return angleTo(eye, forward, bookAt) >= 85;
}

/** Phase 4: glancing north through the flickering airwell flashes a motionless figure in the hall. */
export function hallFlashDue(
  eye: Vector3,
  forward: Vector3,
  backDoorAt: Vector3,
  phoneAnswered: boolean,
): boolean {
  if (!phoneAnswered || inBackRoom(eye)) return false;
  const [, y] = plan(eye);
  if (y < 5.6 || y > 8.6) return false;
  return angleTo(eye, forward, backDoorAt) <= 38;
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
