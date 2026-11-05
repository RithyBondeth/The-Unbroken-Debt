import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../core/Game";
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
}

export type ScareKind = "glimpse" | "lunge" | "behind" | "stare" | "rise";

export interface Scare {
  id: string;
  kind: ScareKind;
  /** True when the moment has come; may arm a "behind" scare that waits for a turn. */
  ready(c: ScareContext): boolean;
  /** Where she appears, given the player. */
  place(c: ScareContext): { x: number; z: number };
}

const HALL_DOOR = { x: 22, z: 6.6 };
const KUTI_DOOR = { x: -18, z: 15.5 };
/** The far end of the reclining Buddha's bed, in the clearing east of the compound. */
const SALA_FAR = { x: 40.2, z: 12.9 };
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

/** The one-time scares of the episode, in story order. */
export const SCARES: Scare[] = [
  {
    // Crossing the threshold: something red crosses the processional path far ahead.
    id: "gate",
    kind: "glimpse",
    ready: (c) =>
      ["arrival", "garden"].includes(c.stage) &&
      c.feet.z < 22 &&
      c.feet.z > 15 &&
      Math.abs(c.feet.x) < 3,
    place: (c) => ahead(c, 9, -2.5),
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
};

/** Which performance she gives in each appearance, and how fast. */
export const CLIPS: Record<ScareKind, { clip: string; rate: number }> = {
  glimpse: { clip: "glimpse", rate: 1 },
  lunge: { clip: "lunge", rate: 2.3 },
  behind: { clip: "behind", rate: 2.1 },
  stare: { clip: "stare", rate: 0.9 },
  rise: { clip: "rise", rate: 1.3 },
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
  /** Her head's roll this frame, applied on top of the clip. */
  private neck = 0;
  private showing: {
    scare: Scare;
    t: number;
    at: Vector3;
    heading: number;
    armed: boolean;
  } | null = null;
  private waiting = 0;
  /** The lamps' flicker after she vanishes, in seconds remaining. */
  private afterglow = 0;

  constructor(
    private readonly game: Game,
    private readonly sounds: PagodaSoundscape,
    private readonly lights: PagodaLights,
  ) {}

  /** Loads her own asset, parked out of sight until the first scare. */
  async load(): Promise<void> {
    const scene = this.game.scene;
    const asset = await GhostRig.load(scene, "ep2_red");
    this.rig = new GhostRig(asset, "pagoda_ghost");
    this.rig.root.setEnabled(false);
    scene.onAfterAnimationsObservable.add(() => {
      if (this.rig?.root.isEnabled()) this.rig.turn("Head_021", "forward", this.neck * NECK_ROLL);
    });
  }

  get visible(): boolean {
    return !!this.showing && !this.showing.armed;
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
        this.waiting = 0;
        this.begin(scare, c);
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
      x += Math.cos(s.heading) * 3.2 * pose.travel;
      z -= Math.sin(s.heading) * 3.2 * pose.travel;
    } else if (kind === "lunge") {
      x += (dx / d) * 1.05 * pose.travel;
      z += (dz / d) * 1.05 * pose.travel;
    } else if (kind === "stare") {
      // Back from the blink a step nearer.
      x += (dx / d) * 1.4 * pose.travel;
      z += (dz / d) * 1.4 * pose.travel;
    } else if (kind === "rise")
      y = -0.8 + pose.travel * 0.7; // getting up out of the black water beside the planks
    else if (kind === "behind") {
      x += (dx / d) * 0.4 * pose.travel;
      z += (dz / d) * 0.4 * pose.travel;
    }
    root.position.set(x, y, z);
    // She faces Sora, except while she crosses, when she faces where she is going.
    const toward = Math.atan2(c.feet.x - x, c.feet.z - z);
    root.rotation.y =
      kind === "glimpse" && s.t < 0.82
        ? Math.atan2(Math.cos(s.heading), -Math.sin(s.heading))
        : toward;
    const here = new Vector3(x, 1.5, z);
    for (const beat of BEATS[kind])
      if (before < beat.at && s.t >= beat.at) {
        if (beat.sound === "crack") this.sounds.crack(here);
        else this.sounds.laugh(here);
      }
    // The lamps stutter as she arrives and burn low while she is there.
    this.lights.scare = s.t < 0.2 ? (pose.visible ? 1 : 0.1) : 0.55 + 0.1 * Math.sin(s.t * 31);
    if (s.t >= DURATION[kind]) this.hide(true);
  }

  private begin(scare: Scare, c: ScareContext): void {
    const g = this.game;
    g.flags.set(`ep2.scare.${scare.id}`, true);
    const p = scare.place(c);
    const at = new Vector3(p.x, 0, p.z);
    const heading = -Math.atan2(c.feet.x - p.x, c.feet.z - p.z);
    this.showing = { scare, t: 0, at, heading, armed: scare.kind === "behind" };
    const root = this.rig!.root;
    root.position.set(p.x, -50, p.z);
    root.rotation.y = Math.atan2(c.feet.x - p.x, c.feet.z - p.z);
    this.neck = 0;
    if (scare.kind === "behind") {
      root.setEnabled(false);
      // Steps and a breath behind her, so the player has a reason to turn.
      this.sounds.behind(at);
      return;
    }
    root.setEnabled(true);
    this.rig!.start(CLIPS[scare.kind].clip, CLIPS[scare.kind].rate);
    if (scare.kind === "glimpse" || scare.kind === "stare") this.sounds.unease();
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
  }
}
