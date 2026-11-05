import type { Scene } from "@babylonjs/core/scene";
import type { Observer } from "@babylonjs/core/Misc/observable";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { PAGODA_BALANCE as B } from "./data/balance";
import type { GhostRig } from "./GhostRig";
import type { PretMode } from "./PretBrain";
import type { PagodaSoundscape } from "./PagodaSoundscape";
import type { PagodaLights } from "./PagodaLights";

/** What each clip was performed at, and where in its loop a foot comes down. */
export const GAITS = {
  walk: { speed: 0.5, steps: [0.131, 0.345, 0.643, 0.845] },
  lurch: { speed: 1.12, steps: [0, 0.41, 0.754] },
} as const;

/** Which clip suits what the corpse is doing. */
export function gaitFor(moved: boolean, mode: PretMode): "walk" | "lurch" | "listen" {
  if (!moved) return "listen";
  return mode === "investigate" ? "lurch" : "walk";
}

/** Playback rate so the feet keep pace with the ground: `moving` metres a second. */
export function playbackRate(gait: keyof typeof GAITS, moving: number): number {
  return moving / GAITS[gait].speed;
}

/** Whether a loop's phase passed one of `steps` between two moments, wrapping at the end. */
export function steppedOn(before: number, after: number, steps: readonly number[]): boolean {
  return after >= before
    ? steps.some((s) => before < s && s <= after)
    : steps.some((s) => s > before || s <= after);
}

/** `from` turned towards `to` by at most `limit` radians, the short way round. */
export function turnToward(from: number, to: number, limit: number): number {
  const d = Math.atan2(Math.sin(to - from), Math.cos(to - from));
  return from + Math.sign(d) * Math.min(Math.abs(d), limit);
}

/** How the neck has gone over, `t` seconds after it jerked: at once, then slowly back. */
export function headJerk(t: number): number {
  if (t < 0.1) return t / 0.1;
  return t < 0.7 ? 1 - (t - 0.1) * 1.05 : Math.max(0, 0.37 - (t - 0.7) * 0.5);
}

interface Body {
  rig: GhostRig;
  yaw: number;
  gait: "walk" | "lurch" | "listen";
  phase: number;
  /** Seconds since the head last jerked over, and to which side. */
  twitch: number;
  side: number;
  nextTwitch: number;
  /** How long the player has looked straight at it. */
  gaze: number;
  /** Seconds left out of sight after vanishing. */
  hidden: number;
}

const HEAD_TILT = 0.75;

/**
 * The garden's hungry dead: starved corpses in rotting white, one per PretBrain, walking on
 * real human motion. On patrol they drag a bad leg; at a sound they lurch; stopped, they
 * stand with their arms hanging and listen. Their heads jerk over and crack, and looked at
 * too long one is gone, with a breath sucked in where it stood, and back a moment later
 * wherever it now is. Hearing and catching never change: only what the player sees does.
 */
export class ShroudedDead {
  private readonly bodies: Body[];
  private cooldown = 5;
  private flicker = 0;
  private readonly lateness: Observer<Scene>;

  constructor(
    private readonly scene: Scene,
    rigs: readonly GhostRig[],
    private readonly sounds: PagodaSoundscape,
    private readonly lights: PagodaLights,
  ) {
    this.bodies = rigs.map((rig, i) => ({
      rig,
      yaw: 0,
      gait: "listen",
      phase: 0,
      twitch: 9,
      side: 1,
      nextTwitch: 2 + i * 1.3,
      gaze: 0,
      hidden: 0,
    }));
    // The neck goes over on top of whatever the clip is doing.
    this.lateness = scene.onAfterAnimationsObservable.add(() => {
      for (const b of this.bodies) {
        if (!b.rig.root.isEnabled() || b.twitch >= 2) continue;
        b.rig.turn("head", "forward", b.side * HEAD_TILT * headJerk(b.twitch));
      }
    })!;
  }

  dispose(): void {
    this.scene.onAfterAnimationsObservable.remove(this.lateness);
  }

  /**
   * Poses corpse `i` at `at`, turned towards `yaw`, for this frame. `moved` says whether
   * its brain moved, `mode` what it is about; `feet` is the player's, for the sounds.
   */
  update(
    dt: number,
    i: number,
    at: { x: number; z: number },
    yaw: number,
    moved: boolean,
    mode: PretMode,
    feet: Vector3,
  ): void {
    const b = this.bodies[i];
    const root = b.rig.root;
    const here = new Vector3(at.x, 0.2, at.z);
    const d = Math.hypot(at.x - feet.x, at.z - feet.z) || 1;
    b.rig.pause(dt === 0);
    const gait = gaitFor(moved, mode);
    if (gait === "listen") b.rig.play("listen");
    else {
      const speed = mode === "investigate" ? B.investigateSpeed : B.patrolSpeed;
      b.rig.play(gait, playbackRate(gait, speed));
    }
    if (gait !== b.gait) {
      b.gait = gait;
      b.phase = b.rig.phase(gait);
    }
    b.rig.update(dt);
    // A foot comes down: heavy, and quieter the further off it is, like all spatial sound.
    if (gait !== "listen") {
      const phase = b.rig.phase(gait);
      if (b.hidden <= 0 && dt > 0 && steppedOn(b.phase, phase, GAITS[gait].steps))
        this.sounds.thud(i, here, gait === "lurch" ? 0.42 : 0.26);
      b.phase = phase;
    }
    // The head jerks over now and then, and sometimes the neck cracks or it moans.
    b.twitch += dt;
    b.nextTwitch -= dt;
    if (b.nextTwitch <= 0) {
      b.twitch = 0;
      b.side = Math.random() < 0.5 ? 1 : -1;
      b.nextTwitch = 1.6 + Math.random() * 4;
      if (d < 9 && Math.random() < 0.4) this.sounds.crack(here.add(new Vector3(0, 1.4, 0)));
      else if (d < 16 && Math.random() < 0.3) this.sounds.groan(i, here);
    }
    // The body comes round; its path turns square corners, a body does not.
    b.yaw = turnToward(b.yaw, yaw, dt * (mode === "investigate" ? 5 : 3));
    root.position.set(at.x, 0, at.z);
    root.rotation.y = b.yaw;
    // Gone after being looked at too long (see watch), and back where it now is.
    if (b.hidden > 0) {
      b.hidden -= dt;
      root.setEnabled(false);
      if (b.hidden <= 0) this.sounds.thud(i, here, 0.75);
    } else root.setEnabled(true);
  }

  /** Puts corpse `i` away, as when the story has no use for it yet. */
  hide(i: number): void {
    this.bodies[i].rig.root.setEnabled(false);
  }

  /**
   * The vanishing, judged once per frame across all corpses: `seen(i)` gives how
   * squarely the player faces corpse `i` (1 dead ahead) and how far it is.
   */
  watch(
    dt: number,
    seen: (i: number) => { facing: number; distance: number; at: Vector3 } | null,
  ): void {
    this.cooldown = Math.max(0, this.cooldown - dt);
    if (this.flicker > 0) {
      this.flicker = Math.max(0, this.flicker - dt);
      this.lights.scare = this.flicker > 0 ? (Math.random() < 0.5 ? 0.9 : 0.2) : 0;
    }
    this.bodies.forEach((b, i) => {
      const v = seen(i);
      if (!v || b.hidden > 0) {
        b.gaze = 0;
        return;
      }
      b.gaze =
        v.facing > 0.93 && v.distance > 3 && v.distance < 14
          ? b.gaze + dt
          : Math.max(0, b.gaze - dt * 2);
      if (b.gaze > 1 && this.cooldown === 0 && Math.random() < dt * 1.5) {
        b.hidden = 1.2 + Math.random() * 1.2;
        b.gaze = 0;
        this.cooldown = 7;
        this.flicker = 0.35;
        this.sounds.vanish(v.at.add(new Vector3(0, 1.3, 0)));
      }
    });
  }
}
