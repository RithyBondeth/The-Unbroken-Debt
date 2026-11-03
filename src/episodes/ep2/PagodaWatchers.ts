import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../core/Game";
import type { PagodaSoundscape } from "./PagodaSoundscape";
import { facing, type ScareContext } from "./PagodaApparition";

/** Where the goddess stands, from the treeline to the hall steps. Runtime X east, Z south. */
export const GODDESS_PATH: readonly { x: number; z: number }[] = [
  { x: 43.0, z: 18.5 },
  { x: 37.5, z: 17.6 },
  { x: 33.2, z: 15.8 },
  { x: 30.4, z: 12.6 },
  { x: 26.0, z: 12.0 },
  { x: 24.9, z: 9.9 },
];

/** The fallen bay of the east wall: beyond it lies the clearing. */
export const CLEARING_X = 28.4;

/** Heading that turns a node in the mirrored cinematic root to face `to`. */
const headingTo = (from: { x: number; z: number }, to: { x: number; z: number }) =>
  -Math.atan2(to.x - from.x, to.z - from.z);

/**
 * The images that move when no one is looking. The painted alms-monks lining the
 * path to the reclining Buddha turn, one by one, to face Sora whenever she has her
 * back to them; the bound stone goddess comes a little nearer each time she is out
 * of sight, from the treeline to the foot of the hall steps. Never in view.
 */
export class PagodaWatchers {
  private readonly monks: { node: TransformNode; at: Vector3; turned: boolean }[] = [];
  private goddess: TransformNode | null = null;
  private cooldown = 0;

  constructor(
    private readonly game: Game,
    private readonly sounds: PagodaSoundscape,
  ) {}

  attach(): void {
    const s = this.game.scene;
    for (let k = 0; ; k++) {
      const node =
        s.getTransformNodeByName("pagoda_watcher_" + k) ?? s.getMeshByName("pagoda_watcher_" + k);
      if (!node) break;
      this.monks.push({
        node: this.free(node),
        at: node.getAbsolutePosition().clone(),
        turned: false,
      });
    }
    const goddess = s.getTransformNodeByName("pagoda_goddess") ?? s.getMeshByName("pagoda_goddess");
    if (goddess) {
      this.goddess = this.free(goddess);
      this.place(this.step);
    }
  }

  /** Saved progress along GODDESS_PATH. */
  private get step(): number {
    return this.game.flags.get("ep2.goddess.step", 0);
  }

  /** Detaches a node from the mirrored root, keeping where it is, so it can turn. */
  private free(node: TransformNode): TransformNode {
    node.setParent(null);
    node.rotationQuaternion = null;
    for (const mesh of node.getChildMeshes(false)) mesh.isPickable = false;
    return node;
  }

  private place(step: number): void {
    const g = this.goddess;
    if (!g) return;
    const p = GODDESS_PATH[Math.min(step, GODDESS_PATH.length - 1)];
    // She always faces the way to the hall, the way she is going.
    const next = GODDESS_PATH[Math.min(step + 1, GODDESS_PATH.length - 1)];
    g.position.x = p.x;
    g.position.z = p.z;
    g.rotation.y =
      step < GODDESS_PATH.length - 1 ? headingTo(p, next) : headingTo(p, { x: 22, z: 6.6 });
  }

  update(dt: number, c: ScareContext, active: boolean): void {
    if (!active) return;
    const g = this.game;
    this.cooldown = Math.max(0, this.cooldown - dt);
    if (c.feet.x > CLEARING_X + 2 && !g.flags.get("ep2.clearing.seen", false))
      g.flags.set("ep2.clearing.seen", true);
    // The monks: within the clearing, each one turns when it is behind her.
    for (const m of this.monks) {
      const d = Math.hypot(m.at.x - c.feet.x, m.at.z - c.feet.z);
      if (d < 1.6 || d > 16 || facing(c, m.at) > 0.05) continue;
      if (Math.random() > dt * 0.35) continue;
      m.node.rotation.y = headingTo(m.at, c.feet);
      if (!m.turned) {
        m.turned = true;
        if (this.cooldown === 0) {
          this.sounds.grind(new Vector3(m.at.x, 0.4, m.at.z));
          this.cooldown = 4;
        }
      }
    }
    // The goddess moves only after the clearing has been seen, and never in sight.
    if (!this.goddess || !g.flags.get("ep2.clearing.seen", false)) return;
    const step = this.step;
    if (step >= GODDESS_PATH.length - 1 || this.cooldown > 0) return;
    const here = GODDESS_PATH[step],
      next = GODDESS_PATH[step + 1];
    const away = (p: { x: number; z: number }) =>
      Math.hypot(p.x - c.feet.x, p.z - c.feet.z) > 6 && facing(c, p) < 0.2;
    if (!away(here) || !away(next) || Math.random() > dt * 0.12) return;
    g.flags.set("ep2.goddess.step", step + 1);
    this.place(step + 1);
    this.sounds.grind(new Vector3(next.x, 0.4, next.z));
    this.cooldown = 10;
  }
}
