import type { Scene } from "@babylonjs/core/scene";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import { ShadowFigure } from "@/shared/entities/ShadowFigure";

/** The lead form and its smear: lag behind the lead (s) and how solid each copy is. */
const TRAIL = [
  [0, 1],
  [0.018, 0.55],
  [0.036, 0.3],
  [0.058, 0.14],
] as const;
/** Not lacquer: a figure-shaped hole in the night, its chalk eyes the only pale thing. */
const VOID = new Color3(0.004, 0.004, 0.005);

const smooth = (p: number) => p * p * (3 - 2 * p);

/**
 * A black shadow sprinting past faster than a person can, as on the taxi ride:
 * bent forward, smeared by its own speed, shedding a soot-dark wisp that hangs
 * in the air a moment after it has gone. Runs from `from` to `to` (feet).
 */
export class ShadowRunner {
  private readonly forms: ShadowFigure[] = [];
  private readonly wisp: ParticleSystem;
  private readonly emitter = new Vector3();
  private run: { from: Vector3; to: Vector3; start: number; seconds: number } | null = null;
  private time = 0;

  constructor(scene: Scene, name: string, height = 2.15) {
    for (const [index] of TRAIL.entries()) {
      const form = new ShadowFigure(scene, `${name}_${index}`, height);
      form.darken(VOID, true);
      form.root.setEnabled(false);
      this.forms.push(form);
    }
    const wisp = (this.wisp = new ParticleSystem(`${name}_wisp`, 160, scene));
    wisp.particleTexture = sootPuff(scene, name);
    wisp.emitter = this.emitter;
    wisp.minEmitBox.set(-0.25, 0.1, -0.25);
    wisp.maxEmitBox.set(0.25, 1.9, 0.25);
    wisp.direction1 = new Vector3(-0.2, 0.15, -0.2);
    wisp.direction2 = new Vector3(0.2, 0.45, 0.2);
    wisp.minEmitPower = 0.05;
    wisp.maxEmitPower = 0.25;
    wisp.minLifeTime = 0.6;
    wisp.maxLifeTime = 1.4;
    wisp.addSizeGradient(0, 0.25);
    wisp.addSizeGradient(1, 0.9);
    wisp.minAngularSpeed = -1.2;
    wisp.maxAngularSpeed = 1.2;
    wisp.color1 = new Color4(0.01, 0.01, 0.012, 0.55);
    wisp.color2 = new Color4(0.02, 0.018, 0.02, 0.35);
    wisp.colorDead = new Color4(0, 0, 0, 0);
    wisp.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    wisp.emitRate = 0;
    wisp.isLocal = false;
    wisp.start();
  }

  get running(): boolean {
    return this.run !== null;
  }

  /** The lead form's feet, while it runs. */
  get position(): Vector3 {
    return this.forms[0].root.position;
  }

  /** Sprints from `from` to `to` (feet positions) in `seconds`, `delay` seconds from now. */
  dash(from: Vector3, to: Vector3, seconds: number, delay = 0): void {
    this.run = { from: from.clone(), to: to.clone(), start: this.time + delay, seconds };
  }

  update(dt: number): void {
    this.time += dt;
    const run = this.run;
    if (!run) return;
    const heading = Math.atan2(run.to.x - run.from.x, run.to.z - run.from.z);
    let any = false;
    TRAIL.forEach(([lag, solid], i) => {
      const form = this.forms[i];
      const p = (this.time - lag - run.start) / run.seconds;
      const on = p >= 0 && p <= 1;
      form.root.setEnabled(on);
      if (!on) return;
      any = true;
      const edge = Math.min(1, p / 0.08, (1 - p) / 0.1);
      form.setPresence(solid * edge);
      Vector3.LerpToRef(run.from, run.to, smooth(p), form.root.position);
      form.root.position.y -= 0.1;
      // Bent hard into the sprint, the copies behind leaning further, as if dragged.
      form.root.rotation.set(0.34 + i * 0.05, heading, Math.sin(this.time * 31 + i) * 0.03);
      form.animate(this.time * 4.6, 1, 0);
    });
    const lead = (this.time - run.start) / run.seconds;
    this.wisp.emitRate = lead >= 0 && lead <= 1 ? 260 : 0;
    this.emitter.copyFrom(this.forms[0].root.position);
    if (!any && lead > 1) this.run = null;
  }

  /** Shows the lead form at `feet` so its materials compile during loading; returns the undo. */
  prepareRenderWarmup(feet: Vector3): () => void {
    for (const form of this.forms) {
      form.root.position.copyFrom(feet);
      form.setPresence(1);
      form.root.setEnabled(true);
    }
    return () => {
      for (const form of this.forms) {
        form.setPresence(0);
        form.root.setEnabled(false);
      }
    };
  }

  dispose(): void {
    for (const form of this.forms) form.dispose();
    this.wisp.dispose();
  }
}

/** A ragged, soft-edged puff for the soot it sheds. */
function sootPuff(scene: Scene, name: string): DynamicTexture {
  const texture = new DynamicTexture(`T_${name}_soot`, { width: 64, height: 64 }, scene, false);
  const ctx = texture.getContext();
  for (let k = 0; k < 6; k++) {
    const x = 32 + Math.cos(k * 1.9) * 9,
      y = 32 + Math.sin(k * 2.7) * 9;
    const g = ctx.createRadialGradient(x, y, 0, x, y, 22);
    g.addColorStop(0, "rgba(255,255,255,0.35)");
    g.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 64, 64);
  }
  texture.hasAlpha = true;
  texture.update();
  return texture;
}
