import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../core/Game";
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

/** Seconds each kind of appearance lasts once it shows. */
const DURATION: Record<ScareKind, number> = {
  glimpse: 0.9,
  lunge: 0.75,
  behind: 0.6,
  stare: 1.6,
  rise: 1.1,
};

/**
 * The dead woman in red. She is a real body (MakeHuman, built in
 * tools/ep2/build-cinematics.py), shown for a second at a time: she crosses the
 * path, lunges at the chained door, waits behind Sora, stares from the graves,
 * rises from the pond. Each scare happens once and is saved in `ep2.scare.<id>`.
 */
export class PagodaApparition {
  private root: TransformNode | null = null;
  private showing: {
    scare: Scare;
    t: number;
    at: Vector3;
    heading: number;
    armed: boolean;
  } | null = null;
  private waiting = 0;

  constructor(
    private readonly game: Game,
    private readonly sounds: PagodaSoundscape,
    private readonly lights: PagodaLights,
  ) {}

  attach(): void {
    const root = this.game.scene.getTransformNodeByName("pagoda_ghost");
    if (!root) return;
    // Free of the cinematic mirror root, keeping its world transform (and its mirroring).
    root.setParent(null);
    root.rotationQuaternion = null;
    root.setEnabled(false);
    for (const mesh of root.getChildMeshes()) mesh.isPickable = false;
    this.root = root;
  }

  get visible(): boolean {
    return !!this.showing && !this.showing.armed;
  }

  update(dt: number, c: ScareContext, active: boolean): void {
    const g = this.game;
    if (!this.root) return;
    if (!active) {
      if (this.showing && !this.showing.armed) this.hide();
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
        this.root.setEnabled(true);
        this.sounds.scare(1);
        this.jolt();
      } else if (s.t > 9) this.hide();
      return;
    }
    s.t += dt;
    const k = s.t / DURATION[s.scare.kind];
    const eye = g.player.feet.y + 1.58;
    let x = s.at.x,
      z = s.at.z,
      // She floats a little: her face comes level with Sora's eyes.
      y = eye - 1.28;
    if (s.scare.kind === "glimpse") {
      x += Math.cos(s.heading) * 4 * k;
      z -= Math.sin(s.heading) * 4 * k;
    } else if (s.scare.kind === "lunge") {
      const toward = Math.min(1, k * 2.5) ** 0.5;
      const dx = c.feet.x - s.at.x,
        dz = c.feet.z - s.at.z,
        d = Math.hypot(dx, dz) || 1;
      x += (dx / d) * 1.05 * toward;
      z += (dz / d) * 1.05 * toward;
    } else if (s.scare.kind === "rise") y = -1.4 + Math.min(1, k * 1.6) * 1.6 + (eye - 1.58);
    else if (s.scare.kind === "behind") {
      x += Math.sin(s.heading + Math.PI) * 0.4 * k;
      z += Math.cos(s.heading + Math.PI) * 0.4 * k;
    }
    // A shudder, not a smooth glide.
    x += (Math.random() - 0.5) * 0.02;
    z += (Math.random() - 0.5) * 0.02;
    this.root.position.set(x, y, z);
    this.root.rotation.y = s.heading;
    this.lights.scare = Math.max(0, 1 - Math.abs(k - 0.5) * 1.4);
    if (k >= 1) this.hide();
  }

  private begin(scare: Scare, c: ScareContext): void {
    const g = this.game;
    g.flags.set(`ep2.scare.${scare.id}`, true);
    const p = scare.place(c);
    const at = new Vector3(p.x, 0, p.z);
    // She always faces Sora; the cinematic root is mirrored in X, so the heading is too.
    const heading = -Math.atan2(c.feet.x - p.x, c.feet.z - p.z);
    this.showing = { scare, t: 0, at, heading, armed: scare.kind === "behind" };
    this.root!.position.set(p.x, -50, p.z);
    this.root!.rotation.y = heading;
    if (scare.kind === "behind") {
      this.root!.setEnabled(false);
      // Steps and a breath behind her, so the player has a reason to turn.
      this.sounds.behind(at);
      return;
    }
    this.root!.setEnabled(true);
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

  private hide(): void {
    this.showing = null;
    this.lights.scare = 0;
    this.root?.setEnabled(false);
  }
}
