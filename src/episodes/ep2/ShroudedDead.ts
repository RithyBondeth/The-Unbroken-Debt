import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { MorphTargetManager } from "@babylonjs/core/Morph/morphTargetManager";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { PagodaSoundscape } from "./PagodaSoundscape";
import type { PagodaLights } from "./PagodaLights";

/** How a bound corpse's body is shaped at one point of a hop (shape-key weights). */
export interface HopPose {
  /** Metres off the ground. */
  lift: number;
  squash: number;
  stretch: number;
}

/** Hops per second while moving. */
export const HOP_RATE = 2.1;
/** Where in each hop cycle the feet strike the ground. */
export const LANDING = 0.75;

/**
 * One hop, `u` from 0 to 1: a crouch, a stretched leap, a heavy squashed landing.
 * The bound dead cannot walk; this is how they move.
 */
export function hopPose(u: number): HopPose {
  if (u < 0.15) return { lift: 0, squash: (u / 0.15) * 0.7, stretch: 0 };
  if (u < LANDING) {
    const a = (u - 0.15) / (LANDING - 0.15);
    return { lift: Math.sin(Math.PI * a) * 0.22, squash: 0, stretch: (1 - a) * 0.9 };
  }
  return { lift: 0, squash: 1 - (u - LANDING) / (1 - LANDING), stretch: 0 };
}

interface Body {
  morph: MorphTargetManager | null;
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

/**
 * The garden's shrouded dead (the Pocong scan, one root per PretBrain). They hop,
 * squashing as they land with a thud through the ground; their heads jerk over and
 * crack; they breathe inside the shroud. Look at one too long and it is gone, with
 * a breath sucked in where it stood, and back a moment later wherever it now is.
 * Hearing and catching never change: only what the player sees does.
 */
export class ShroudedDead {
  private readonly bodies: Body[];
  private cooldown = 5;
  private flicker = 0;

  constructor(
    actors: readonly TransformNode[],
    private readonly sounds: PagodaSoundscape,
    private readonly lights: PagodaLights,
  ) {
    this.bodies = actors.map((actor, i) => {
      const mesh = actor.getChildMeshes().find((m) => m instanceof Mesh && !!m.morphTargetManager);
      return {
        morph: mesh instanceof Mesh ? mesh.morphTargetManager : null,
        phase: 0,
        twitch: 9,
        side: 1,
        nextTwitch: 2 + i * 1.3,
        gaze: 0,
        hidden: 0,
      };
    });
  }

  /**
   * Poses corpse `i` at `at`, turned to `yaw`, for this frame. `moved` says whether
   * its brain moved; `feet` is the player's, for how near the sounds are.
   */
  update(
    dt: number,
    i: number,
    actor: TransformNode,
    at: { x: number; z: number },
    yaw: number,
    moved: boolean,
    feet: Vector3,
    time: number,
  ): void {
    const b = this.bodies[i];
    // The hop: while moving, and to finish a hop already in the air.
    const before = b.phase % 1;
    if (moved || (before > 0.05 && before < 0.99)) b.phase += dt * HOP_RATE;
    const u = b.phase % 1;
    const hop = moved || u > 0.05 ? hopPose(u) : { lift: 0, squash: 0, stretch: 0 };
    const here = new Vector3(at.x, 0.2, at.z);
    const dx = at.x - feet.x,
      dz = at.z - feet.z,
      d = Math.hypot(dx, dz) || 1;
    if (before < LANDING && u >= LANDING && b.hidden <= 0) this.sounds.thud(i, here);
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
    const head =
      b.twitch < 0.12
        ? 1
        : b.twitch < 0.7
          ? 1 - (b.twitch - 0.12) * 1.1
          : Math.max(0, 0.36 - (b.twitch - 0.7) * 0.5);
    this.weights(b, {
      squash: hop.squash,
      stretch: hop.stretch,
      lean: moved ? 0.55 : 0,
      head_a: b.side > 0 ? head : 0,
      head_b: b.side < 0 ? head : 0,
      breathe: 0.5 + 0.5 * Math.sin(time * 1.9 + i),
    });
    actor.setAbsolutePosition(new Vector3(at.x, hop.lift, at.z));
    actor.rotation.y = yaw;
    actor.rotation.z = Math.sin(time * 0.8 + i) * 0.03;
    // Gone after being looked at too long (see watch), and back where it now is.
    if (b.hidden > 0) {
      b.hidden -= dt;
      actor.setEnabled(false);
      if (b.hidden <= 0) this.sounds.thud(i, here, 0.75);
    } else actor.setEnabled(true);
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

  private weights(b: Body, w: Record<string, number>): void {
    const m = b.morph;
    if (!m) return;
    for (let k = 0; k < m.numTargets; k++) {
      const target = m.getTarget(k);
      target.influence = w[target.name] ?? 0;
    }
  }
}
