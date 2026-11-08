import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { PhysicsRaycastResult } from "@babylonjs/core/Physics/physicsRaycastResult";
import type { PhysicsEngine } from "@babylonjs/core/Physics/v2/physicsEngine";
import type { Game } from "@/core/Game";
import { GhostAudio, PASS_NEAREST } from "./audio/ghostSounds";
import { GhostRig } from "./GhostRig";
import type { PagodaLights } from "./PagodaLights";
import type { PagodaSoundscape } from "./PagodaSoundscape";
import type { PagodaStage } from "./PagodaProgress";

/** Where a scare happens and what the player has to do to set it off. Runtime X east, Z south. */
export interface ScareContext {
  stage: PagodaStage;
  feet: { x: number; z: number };
  yaw: number;
  offerings: number;
  inKuti: boolean;
  mirrorsTurned: boolean;
  nearestPret: number;
  /** The lost-garden zone Sora stands in, or null in the compound. */
  zone: string | null;
  /** The tank's lotus has just been taken. */
  pickedLotus: boolean;
}

export type ScareKind = "glimpse" | "lunge" | "behind" | "stare" | "rise" | "rush";

/** Where a scare puts her, and for a rush, where she is carried to. */
export interface Placement {
  x: number;
  z: number;
  to?: { x: number; z: number };
}

export interface Scare {
  id: string;
  kind: ScareKind;
  /** True when the moment has come; may arm a "behind" scare that waits for a turn. */
  ready(c: ScareContext): boolean;
  /** Where she appears, given the player; null if there is nowhere fit this moment. */
  place(c: ScareContext): Placement | null;
}

const HALL_DOOR = { x: 22, z: 6.6 };
const KUTI_DOOR = { x: -18, z: 15.5 };
/** The far end of the reclining Buddha's bed, in the clearing east of the compound. */
const SALA_FAR = { x: 40.2, z: 12.9 };
/** The Sunken Tank's landing, where the lotus is taken (tools/areas/pagoda_lost_garden.py). */
const TANK_LANDING = { x: -53, z: -39.2 };
const dist = (a: { x: number; z: number }, b: { x: number; z: number }) =>
  Math.hypot(a.x - b.x, a.z - b.z);
const ahead = (c: ScareContext, d: number, side = 0) => ({
  x: c.feet.x + Math.sin(c.yaw) * d + Math.cos(c.yaw) * side,
  z: c.feet.z + Math.cos(c.yaw) * d - Math.sin(c.yaw) * side,
});
/** How squarely the player faces a point: 1 straight at it, -1 away. */
export function facing(c: ScareContext, p: { x: number; z: number }): number {
  const dx = p.x - c.feet.x,
    dz = p.z - c.feet.z,
    d = Math.hypot(dx, dz) || 1;
  return (Math.sin(c.yaw) * dx + Math.cos(c.yaw) * dz) / d;
}

/**
 * A pass across the view `d` metres ahead, `half` metres either side of the line of sight:
 * she comes out of the dark on one side and is carried across to the other.
 */
export function rushAcross(
  c: ScareContext,
  d: number,
  half: number,
  rightward: boolean,
): Placement {
  const from = ahead(c, d, rightward ? -half : half),
    to = ahead(c, d + 0.6, rightward ? half : -half);
  return { x: from.x, z: from.z, to };
}

/**
 * Where else she could be if the first place is blocked: a pass is tried nearer to Sora
 * (stupas and trunks crowd the far lanes) and the other way across.
 */
export function alternatives(c: ScareContext, p: Placement | null): Placement[] {
  if (!p) return [];
  if (!p.to) return [p];
  const out: Placement[] = [];
  for (const k of [1, 0.8, 0.65, 0.5]) {
    const near = (q: { x: number; z: number }) => ({
      x: c.feet.x + (q.x - c.feet.x) * k,
      z: c.feet.z + (q.z - c.feet.z) * k,
    });
    const from = near(p),
      to = near(p.to);
    out.push({ ...from, to }, { ...to, to: from });
  }
  return out;
}

/** The one-time scares of the episode, in story order. */
export const SCARES: Scare[] = [
  {
    // Crossing the threshold: something red is carried across the processional path ahead.
    id: "gate",
    kind: "rush",
    ready: (c) =>
      ["arrival", "garden"].includes(c.stage) &&
      c.feet.z < 22 &&
      c.feet.z > 15 &&
      Math.abs(c.feet.x) < 3,
    place: (c) => rushAcross(c, 9, 6.5, true),
  },
  {
    // Facing the sealed hall: she throws herself at the chains from inside.
    id: "hall_door",
    kind: "lunge",
    ready: (c) =>
      ["garden", "library"].includes(c.stage) &&
      dist(c.feet, HALL_DOOR) < 3.2 &&
      facing(c, HALL_DOOR) > 0.6,
    // Beside the yantra cloth, so nothing hides her face as she hits the chains.
    place: () => ({ x: HALL_DOOR.x + 0.8, z: HALL_DOOR.z - 1.3 }),
  },
  {
    // Leaving Sophal's room: she waits behind, and screams when Sora turns round.
    id: "kuti_leave",
    kind: "behind",
    ready: (c) =>
      c.stage === "garden" &&
      !c.inKuti &&
      dist(c.feet, KUTI_DOOR) > 3 &&
      dist(c.feet, KUTI_DOOR) < 6 &&
      c.nearestPret > 6,
    place: (c) => ahead(c, -1.7),
  },
  {
    // Among the graves after the second offering: she stands and stares, then is gone.
    id: "garden_stare",
    kind: "stare",
    ready: (c) => c.stage === "garden" && c.offerings >= 2 && c.nearestPret > 7 && !c.inKuti,
    place: (c) => ahead(c, 7.5, 1.2),
  },
  {
    // On the bridge: she rises from the black water beside the planks.
    id: "bridge",
    kind: "rise",
    ready: (c) =>
      c.stage === "library" && Math.abs(c.feet.x) < 1.2 && c.feet.z < -20 && c.feet.z > -26,
    place: (c) => ({ x: c.feet.x + 2.2, z: c.feet.z - 1.6 }),
  },
  {
    // In the clearing: she stands at the far end of the reclining Buddha's bed.
    id: "sala",
    kind: "stare",
    ready: (c) =>
      c.stage !== "escape" &&
      c.stage !== "memory" &&
      c.feet.x > 33 &&
      c.feet.x < 37 &&
      facing(c, SALA_FAR) > 0.8,
    place: () => SALA_FAR,
  },
  {
    // In the Court's lanes: she crosses the lane ahead between the stupas, low and fast.
    id: "court_lanes",
    kind: "rush",
    ready: (c) => c.stage === "garden" && c.zone === "court" && c.nearestPret > 6,
    place: (c) => rushAcross(c, 7.5, 5.5, false),
  },
  {
    // The lotus taken: she rises out of the tank's black water, facing the landing.
    id: "tank_rise",
    kind: "rise",
    ready: (c) => c.pickedLotus && dist(c.feet, TANK_LANDING) < 4,
    place: () => ({ x: TANK_LANDING.x + 1.4, z: TANK_LANDING.z - 3.4 }),
  },
  {
    // Deep in the grove: far off between the trunks, something red is carried past.
    id: "grove_far",
    kind: "rush",
    ready: (c) => c.stage === "garden" && c.zone === "grove" && c.feet.z < -55 && c.nearestPret > 6,
    place: (c) => rushAcross(c, 13, 8, true),
  },
  {
    // At the head of the ruined gallery: she stands at the end of the walk, then is gone.
    id: "gallery_end",
    kind: "stare",
    ready: (c) =>
      c.stage === "garden" && c.zone === "gallery" && c.feet.z < -50 && c.nearestPret > 6,
    place: (c) => ahead(c, 8),
  },
  {
    // On the Bone Terrace: she goes across the tiers in front of the altar.
    id: "terrace",
    kind: "rush",
    ready: (c) => c.zone === "terrace" && c.stage !== "memory" && c.stage !== "escape",
    place: (c) => rushAcross(c, 8, 6, false),
  },
  {
    // After the first mirror turns: she is behind Sora in the archive.
    id: "mirror",
    kind: "behind",
    ready: (c) => c.stage === "library" && c.mirrorsTurned && c.feet.z < -29,
    place: (c) => ahead(c, -1.5),
  },
];

/** Her head's roll at full lean, in radians: past comfortable, not past human. */
const NECK_ROLL = 0.72;

/** Seconds each kind of appearance lasts once it shows. */
const DURATION: Record<ScareKind, number> = {
  glimpse: 1.3,
  lunge: 0.9,
  behind: 0.8,
  stare: 2.6,
  rise: 1.3,
  rush: 1.2,
};

/** Which performance she gives in each appearance, and how fast. */
export const CLIPS: Record<ScareKind, { clip: string; rate: number }> = {
  glimpse: { clip: "glimpse", rate: 1 },
  lunge: { clip: "lunge", rate: 2.3 },
  behind: { clip: "behind", rate: 2.1 },
  stare: { clip: "stare", rate: 0.9 },
  rise: { clip: "rise", rate: 1.3 },
  // Carried, not running: the slack standing performance, barely moving, arms hanging.
  rush: { clip: "stare", rate: 0.35 },
};

/** What the timing asks of her at one moment of an appearance. */
export interface GhostPose {
  visible: boolean;
  /** How far her head has rolled over: +1 one way, -1 the other. */
  neck: number;
  /** 0..1 along the appearance's own movement (crossing, lunging, closing in). */
  travel: number;
}

/** She arrives as a flicker: on, off, on, off, on. */
const FLICKER = [0, 0.05, 0.09, 0.14, 0.17];
const flickering = (t: number) => FLICKER.filter((edge) => t >= edge).length % 2 === 1;
const ramp = (t: number, from: number, to: number) => {
  const u = Math.min(1, Math.max(0, (t - from) / (to - from)));
  return u * u * (3 - 2 * u);
};

/** The timing of an appearance of `kind`, `t` seconds after she shows. */
export function ghostPose(kind: ScareKind, t: number): GhostPose {
  switch (kind) {
    case "lunge":
      // She comes at the chains; her head rolls over, then across to the other side.
      return {
        visible: flickering(t),
        neck: ramp(t, 0.3, 0.42) - 1.8 * ramp(t, 0.62, 0.8),
        travel: ramp(t, 0, 0.3),
      };
    case "behind":
      return { visible: t >= 0, neck: ramp(t, 0.25, 0.42), travel: t / 0.8 };
    case "glimpse":
      // Crossing the path bent over and stumbling; she stops, and her head comes round.
      return {
        visible: flickering(t),
        neck: -ramp(t, 0.82, 1.02),
        travel: Math.min(1, t / 0.82),
      };
    case "stare":
      // Standing still and breathing; gone for a blink, back a step nearer; the head goes.
      return {
        visible: flickering(t) && !(t > 0.9 && t < 1.02),
        neck: ramp(t, 1.5, 1.72),
        travel: t >= 1.02 ? 1 : 0,
      };
    case "rise":
      return {
        visible: flickering(t),
        neck: ramp(t, 0.9, 1.08),
        travel: Math.min(1, t * 1.6),
      };
    case "rush":
      // Out of the dark on one side, across in about a second, gone into the dark beyond;
      // her head turns towards Sora as she passes nearest.
      return {
        visible: t < 1.08,
        neck: ramp(t, PASS_NEAREST - 0.15, PASS_NEAREST + 0.05) * 0.6,
        travel: ramp(t, 0, 1.08) * 0.85 + Math.min(1, t / 1.08) * 0.15,
      };
  }
}

/** Her voice and body in each appearance: when the neck cracks, when she laughs. */
export const BEATS: Record<ScareKind, { at: number; sound: "crack" | "laugh" }[]> = {
  lunge: [{ at: 0.3, sound: "crack" }],
  behind: [{ at: 0.25, sound: "crack" }],
  glimpse: [
    { at: 0.82, sound: "crack" },
    { at: 0.95, sound: "laugh" },
  ],
  stare: [
    { at: 1.5, sound: "crack" },
    { at: 1.9, sound: "laugh" },
  ],
  rise: [{ at: 0.9, sound: "crack" }],
  rush: [],
};

/**
 * The woman in red (the Kuntilanak Merah, on real human motion: tools/ep2/build-ghosts.py).
 * She never fades: she flickers in and moves as a person moves, stumbling across the
 * path, rising from a crouch, coming at you with her arms lifting, her head rolling over
 * on her neck with a crack and her laugh ringing out, and then she is simply gone, with a
 * breath sucked in where she stood and the lamps flickering. Each scare happens once and
 * is saved in `ep2.scare.<id>`.
 */
export class PagodaApparition {
  private rig: GhostRig | null = null;
  /** Fainter copies of her, a few frames behind, while she is carried past. */
  private trail: GhostRig[] = [];
  /** Her head's roll this frame, applied on top of the clip. */
  private neck = 0;
  private showing: {
    scare: Scare;
    t: number;
    at: Vector3;
    to: Vector3 | null;
    /** Unit direction she crosses in, for a glimpse. */
    across: { x: number; z: number };
    armed: boolean;
  } | null = null;
  private waiting = 0;
  /** The lamps' flicker after she vanishes, in seconds remaining. */
  private afterglow = 0;
  private readonly hit = new PhysicsRaycastResult();
  private readonly audio: GhostAudio;

  constructor(
    private readonly game: Game,
    private readonly sounds: PagodaSoundscape,
    private readonly lights: PagodaLights,
  ) {
    this.audio = new GhostAudio(game);
  }

  /** Loads her own asset, parked out of sight until the first scare. */
  async load(): Promise<void> {
    const scene = this.game.scene;
    const asset = await GhostRig.load(scene, "ep2_red");
    this.rig = new GhostRig(asset, "pagoda_ghost");
    this.rig.root.setEnabled(false);
    // Faint smears of her a few hundredths of a second behind: their own see-through copies
    // of her material (hers is authored opaque, which ignores a mesh's visibility).
    this.trail = [0.3, 0.12].map((alpha, i) => {
      const rig = new GhostRig(asset, "pagoda_ghost_trail_" + i);
      rig.root.setEnabled(false);
      for (const mesh of rig.root.getChildMeshes()) {
        if (!(mesh.material instanceof PBRMaterial)) continue;
        const smear = mesh.material.clone(mesh.material.name + "_trail_" + i);
        smear.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
        smear.alpha = alpha;
        smear.disableDepthWrite = true;
        mesh.material = smear;
      }
      return rig;
    });
    scene.onAfterAnimationsObservable.add(() => {
      for (const rig of [this.rig, ...this.trail])
        if (rig?.root.isEnabled()) rig.turn("Head_021", "forward", this.neck * NECK_ROLL);
    });
    await this.audio.load();
  }

  get visible(): boolean {
    return !!this.showing && !this.showing.armed;
  }

  /** True when nothing solid lies between `a` and `b` (the player's own capsule aside). */
  private clear(a: Vector3, b: Vector3): boolean {
    const physics = this.game.scene.getPhysicsEngine() as PhysicsEngine | null;
    if (!physics) return true;
    physics.raycastToRef(a, b, this.hit);
    const player = this.game.player.collisionShape;
    return (
      !this.hit.hasHit ||
      this.hit.shape === player ||
      this.hit.body?.shape === player ||
      this.hit.hitDistance >= Vector3.Distance(a, b) - 0.15
    );
  }

  /**
   * Whether she can be put at `p` (and carried to `to`): not inside a wall, a stupa or a tree,
   * seen from Sora's eyes, and for a pass, the whole way across open.
   */
  fits(p: Placement, kind: ScareKind, c: ScareContext): boolean {
    // Her eyes, from where her feet are now (the camera's own matrix can lag a teleport).
    const feetY = (c.feet as { y?: number }).y ?? 0;
    const eye = new Vector3(c.feet.x, feetY + 1.55, c.feet.z);
    const chest = new Vector3(p.x, 1.25, p.z);
    // Inside something solid: a ray down from just above her shoulders hits it at once.
    if (!this.clear(new Vector3(p.x, 2.2, p.z), new Vector3(p.x, 0.3, p.z))) return false;
    if (kind === "behind" || kind === "rise") return true;
    if (!this.clear(eye, chest)) return false;
    if (!p.to) return true;
    const end = new Vector3(p.to.x, 1.0, p.to.z);
    const mid = new Vector3((p.x + p.to.x) / 2, 1.25, (p.z + p.to.z) / 2);
    return this.clear(new Vector3(p.x, 1.0, p.z), end) && this.clear(eye, mid);
  }

  update(dt: number, c: ScareContext, active: boolean): void {
    const g = this.game;
    const root = this.rig?.root;
    if (!root) return;
    if (this.afterglow > 0) {
      this.afterglow = Math.max(0, this.afterglow - dt);
      this.lights.scare =
        this.afterglow > 0 ? (Math.random() < 0.5 ? 1 : 0.2) * this.afterglow * 2 : 0;
    }
    if (!active) {
      if (this.showing && !this.showing.armed) this.hide(false);
      return;
    }
    if (!this.showing) {
      for (const scare of SCARES) {
        if (g.flags.get(`ep2.scare.${scare.id}`, false) || !scare.ready(c)) continue;
        // A staring ghost waits a moment so it never lands on top of another scare.
        if (scare.kind === "stare" && (this.waiting += dt) < 3) break;
        // Somewhere fit, or not this frame: she is tried again as Sora moves.
        const p = alternatives(c, scare.place(c)).find((q) => this.fits(q, scare.kind, c));
        if (!p) continue;
        this.waiting = 0;
        this.begin(scare, c, p);
        break;
      }
      return;
    }
    const s = this.showing;
    if (s.armed) {
      // Waiting behind: reveal only when Sora turns to face her; give up after a while.
      s.t += dt;
      if (facing(c, s.at) > 0.75) {
        s.armed = false;
        s.t = 0;
        root.setEnabled(true);
        this.rig!.start(CLIPS.behind.clip, CLIPS.behind.rate);
        this.sounds.scare(1);
        this.jolt();
      } else if (s.t > 9) this.hide(false);
      return;
    }
    const before = s.t;
    s.t += dt;
    const kind = s.scare.kind;
    const pose = ghostPose(kind, s.t);
    this.neck = pose.neck;
    root.setEnabled(pose.visible);
    let x = s.at.x,
      z = s.at.z,
      y = 0;
    const dx = c.feet.x - s.at.x,
      dz = c.feet.z - s.at.z,
      d = Math.hypot(dx, dz) || 1;
    if (kind === "glimpse") {
      x += s.across.x * 3.2 * pose.travel;
      z += s.across.z * 3.2 * pose.travel;
    } else if (kind === "rush" && s.to) {
      x += (s.to.x - s.at.x) * pose.travel;
      z += (s.to.z - s.at.z) * pose.travel;
      // Carried a hand's breadth off the ground, bobbing as if on a current.
      y = 0.12 + 0.05 * Math.sin(s.t * 9);
    } else if (kind === "lunge") {
      x += (dx / d) * 1.05 * pose.travel;
      z += (dz / d) * 1.05 * pose.travel;
    } else if (kind === "stare") {
      // Back from the blink a step nearer.
      x += (dx / d) * 1.4 * pose.travel;
      z += (dz / d) * 1.4 * pose.travel;
    } else if (kind === "rise")
      y = -0.8 + pose.travel * 0.7; // getting up out of the black water
    else if (kind === "behind") {
      x += (dx / d) * 0.4 * pose.travel;
      z += (dz / d) * 0.4 * pose.travel;
    }
    root.position.set(x, y, z);
    // She faces Sora, except while she crosses or is carried past, when she faces where she
    // is going and leans into it.
    const toward = Math.atan2(c.feet.x - x, c.feet.z - z);
    if (kind === "rush" && s.to) {
      root.rotation.set(0.32, Math.atan2(s.to.x - s.at.x, s.to.z - s.at.z), 0);
      this.trailAfter(s.t, s.at, s.to, root.rotation.y, pose.visible);
    } else
      root.rotation.set(
        0,
        kind === "glimpse" && s.t < 0.82 ? Math.atan2(s.across.x, s.across.z) : toward,
        0,
      );
    const here = new Vector3(x, 1.5, z);
    for (const beat of BEATS[kind])
      if (before < beat.at && s.t >= beat.at) {
        if (beat.sound === "crack") this.sounds.crack(here);
        else this.sounds.laugh(here);
      }
    if (kind === "rush" && before < PASS_NEAREST && s.t >= PASS_NEAREST) g.atmosphere.scare();
    // The lamps stutter as she arrives and burn low while she is there; a pass makes the
    // flame bow and nearly die as she goes by.
    this.lights.scare =
      kind === "rush"
        ? Math.max(0, 1 - Math.abs(s.t - PASS_NEAREST) * 2.4) * 0.9
        : s.t < 0.2
          ? pose.visible
            ? 1
            : 0.1
          : 0.55 + 0.1 * Math.sin(s.t * 31);
    if (s.t >= DURATION[kind]) this.hide(kind !== "rush");
  }

  /** The after-image: copies a few hundredths of a second behind her along the pass. */
  private trailAfter(t: number, from: Vector3, to: Vector3, yaw: number, visible: boolean): void {
    this.trail.forEach((rig, i) => {
      const lag = 0.03 + i * 0.035;
      const travel = ghostPose("rush", Math.max(0, t - lag)).travel;
      rig.root.setEnabled(visible && t > lag);
      rig.root.position.set(
        from.x + (to.x - from.x) * travel,
        0.12 + 0.05 * Math.sin((t - lag) * 9),
        from.z + (to.z - from.z) * travel,
      );
      rig.root.rotation.set(0.32, yaw, 0);
    });
  }

  private begin(scare: Scare, c: ScareContext, p: Placement): void {
    const g = this.game;
    g.flags.set(`ep2.scare.${scare.id}`, true);
    const at = new Vector3(p.x, 0, p.z);
    const to = p.to ? new Vector3(p.to.x, 0, p.to.z) : null;
    // A glimpse crosses the line of sight: along the camera's right, whichever side she is on.
    const right = { x: Math.cos(c.yaw), z: -Math.sin(c.yaw) };
    const side = (p.x - c.feet.x) * right.x + (p.z - c.feet.z) * right.z;
    const across = side > 0 ? { x: -right.x, z: -right.z } : right;
    this.showing = { scare, t: 0, at, to, across, armed: scare.kind === "behind" };
    const root = this.rig!.root;
    root.position.set(p.x, -50, p.z);
    root.rotation.set(0, Math.atan2(c.feet.x - p.x, c.feet.z - p.z), 0);
    this.neck = 0;
    if (scare.kind === "behind") {
      root.setEnabled(false);
      // Steps and a breath behind her, so the player has a reason to turn.
      this.sounds.behind(at);
      return;
    }
    root.setEnabled(true);
    this.rig!.start(CLIPS[scare.kind].clip, CLIPS[scare.kind].rate);
    if (scare.kind === "rush" && to) {
      for (const rig of this.trail) rig.start(CLIPS.rush.clip, CLIPS.rush.rate);
      // The whoosh moves the way she does, across the listener; the sting lands as she passes.
      const rightward = (to.x - at.x) * right.x + (to.z - at.z) * right.z > 0;
      this.audio.pass(rightward);
      this.audio.hit(PASS_NEAREST - 0.06, 0.8);
    } else if (scare.kind === "glimpse" || scare.kind === "stare") this.sounds.unease();
    else {
      this.sounds.scare(1);
      this.jolt();
    }
  }

  private jolt(): void {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const g = this.game;
    g.player.pitch += 0.05;
    g.player.yaw += (Math.random() - 0.5) * 0.04;
  }

  /** Gone: abruptly, with a breath sucked in where she was (`vanished`), or quietly. */
  private hide(vanished: boolean): void {
    const root = this.rig?.root;
    if (vanished && root) {
      const p = root.position;
      this.sounds.vanish(new Vector3(p.x, 1.5, p.z));
      this.afterglow = 0.45;
    } else this.lights.scare = 0;
    this.showing = null;
    root?.setEnabled(false);
    for (const rig of this.trail) rig.root.setEnabled(false);
  }

  /** The grab's own sting, for the corpses (they share her sounds). */
  grabSting(): void {
    this.audio.hit(0, 1);
  }
}
