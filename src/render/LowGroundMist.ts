import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Scene } from "@babylonjs/core/scene";
import type { MistPocket } from "./mist";
import { seededRandom } from "../audio/synth";
import "@babylonjs/core/Particles/particleSystemComponent";

/** Low preset: one draw, 40 faint, flattened wisps; no extra depth/pre-pass. */
export class LowGroundMist {
  readonly system: ParticleSystem;
  private readonly texture: DynamicTexture;

  constructor(scene: Scene, pockets: readonly MistPocket[]) {
    const random = seededRandom(7821);
    this.texture = new DynamicTexture("low_ground_mist", 128, scene, true);
    const ctx = this.texture.getContext();
    const pixels = ctx.getImageData(0, 0, 128, 128);
    for (let y = 0; y < 128; y++)
      for (let x = 0; x < 128; x++) {
        const dx = (x - 63.5) / 64,
          dy = (y - 63.5) / 64;
        const edge = Math.max(0, 1 - dx * dx - dy * dy);
        const cloud =
          0.65 + 0.2 * Math.sin(x * 0.12 + y * 0.07) + 0.15 * Math.sin(x * 0.06 - y * 0.16);
        const i = (y * 128 + x) * 4;
        pixels.data[i] = pixels.data[i + 1] = pixels.data[i + 2] = 255;
        pixels.data[i + 3] = Math.round(255 * edge * edge * cloud);
      }
    ctx.putImageData(pixels, 0, 0);
    this.texture.hasAlpha = true;
    this.texture.update(false);
    const system = (this.system = new ParticleSystem("low_ground_mist", 40, scene));
    system.particleTexture = this.texture;
    system.blendMode = ParticleSystem.BLENDMODE_STANDARD;
    system.emitter = Vector3.Zero();
    system.startPositionFunction = (_world, position) => {
      const p = pockets[Math.floor(random() * pockets.length)];
      const angle = random() * Math.PI * 2,
        radius = Math.sqrt(random()) * 0.55;
      position.set(
        p.x + Math.cos(angle) * radius * p.radiusX,
        p.baseY + p.height * 0.35,
        p.z + Math.sin(angle) * radius * p.radiusZ,
      );
    };
    system.minSize = 2.4;
    system.maxSize = 4;
    system.minScaleY = 0.1;
    system.maxScaleY = 0.14;
    system.minLifeTime = 10;
    system.maxLifeTime = 15;
    system.emitRate = 3;
    system.direction1.set(-0.03, 0, 0.015);
    system.direction2.set(0.015, 0, 0.025);
    system.minEmitPower = system.maxEmitPower = 1;
    system.gravity = Vector3.Zero();
    system.color1 = new Color4(0.035, 0.043, 0.055, 0.055);
    system.color2 = new Color4(0.026, 0.034, 0.045, 0.035);
    system.colorDead = new Color4(0.026, 0.034, 0.045, 0);
    system.addColorGradient(0, new Color4(0.03, 0.04, 0.05, 0));
    system.addColorGradient(0.2, system.color1);
    system.addColorGradient(0.65, system.color2);
    system.addColorGradient(1, system.colorDead);
    system.preWarmCycles = 120;
    system.start();
  }

  stop(): void {
    this.system.stop();
    this.system.reset();
  }
}
