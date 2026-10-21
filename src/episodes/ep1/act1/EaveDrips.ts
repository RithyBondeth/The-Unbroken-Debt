import type { Scene } from "@babylonjs/core/scene";
import { Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import type { Area } from "../../../core/AreaLoader";
import "@babylonjs/core/Particles/particleSystemComponent";

/**
 * Rain running off the roofs: thin streams of drops falling from the eaves of the
 * pavilion and the house. Each roof edge is a pair of markers in the area
 * (`marker_eave_<n>_a` and `_b`); drops start anywhere between them.
 */
export class EaveDrips {
  readonly system: ParticleSystem;
  private readonly edges: [Vector3, Vector3][] = [];

  constructor(scene: Scene, area: Area) {
    for (const [id, a] of area.level.markers) {
      const match = /^eave_(\d+)_a$/.exec(id);
      const b = match && area.level.markers.get(`eave_${match[1]}_b`);
      if (b) this.edges.push([a.position.clone(), b.position.clone()]);
    }
    const drop = new DynamicTexture("T_eave_drop", { width: 8, height: 32 }, scene, false);
    const ctx = drop.getContext();
    const gradient = ctx.createLinearGradient(0, 0, 0, 32);
    gradient.addColorStop(0, "rgba(255,255,255,0)");
    gradient.addColorStop(0.6, "rgba(255,255,255,1)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(2, 0, 4, 32);
    drop.hasAlpha = true;
    drop.update();

    const length = this.edges.reduce((sum, [a, b]) => sum + Vector3.Distance(a, b), 0);
    const ps = new ParticleSystem("eave_drips", 1500, scene);
    ps.particleTexture = drop;
    // Drops leave from a random point along the edges (weighted by their length).
    ps.startPositionFunction = (_matrix, position) => {
      let at = Math.random() * length;
      for (const [a, b] of this.edges) {
        const d = Vector3.Distance(a, b);
        if (at <= d) {
          Vector3.LerpToRef(a, b, at / d, position);
          return;
        }
        at -= d;
      }
    };
    ps.emitter = Vector3.Zero();
    ps.direction1 = new Vector3(0, -1, 0);
    ps.direction2 = new Vector3(0, -1, 0);
    ps.gravity = new Vector3(0, -9.8, 0);
    ps.minEmitPower = 0.2;
    ps.maxEmitPower = 0.8;
    ps.minLifeTime = 0.5;
    ps.maxLifeTime = 0.8;
    ps.emitRate = length * 30;
    ps.minSize = 0.012;
    ps.maxSize = 0.02;
    ps.minScaleY = 4;
    ps.maxScaleY = 7;
    ps.billboardMode = ParticleSystem.BILLBOARDMODE_STRETCHED;
    ps.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    ps.color1 = new Color4(0.6, 0.62, 0.66, 0.35);
    ps.color2 = new Color4(0.5, 0.52, 0.56, 0.25);
    ps.colorDead = new Color4(0.5, 0.52, 0.56, 0);
    ps.updateSpeed = 1 / 60;
    ps.preWarmCycles = 60;
    ps.start();
    this.system = ps;
  }

  /** Lightning catches the falling water. */
  light(flash: number): void {
    const a = 0.3 + flash * 0.5;
    this.system.color1.set(0.6 + flash * 0.4, 0.62 + flash * 0.38, 0.66 + flash * 0.34, a);
  }
}
