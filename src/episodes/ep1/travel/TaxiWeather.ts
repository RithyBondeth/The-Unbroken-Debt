import type { Scene } from "@babylonjs/core/scene";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { RainStreaks } from "@/render/weather/Rain";

/** Act I's monsoon streaks, with car-relative wind and a denser headlight field. */
export class TaxiWeather {
  private readonly near: RainStreaks;
  private readonly far: RainStreaks;
  constructor(scene: Scene, low: boolean) {
    this.near = new RainStreaks(scene, low ? 2600 : 5200, low ? 3400 : 6800);
    const near = this.near.system;
    near.emitter = new Vector3(0, 6, 0);
    near.minEmitBox.set(-7, 0, 8);
    near.maxEmitBox.set(7, 0, 26);
    near.minEmitPower = near.maxEmitPower = 1;
    near.minLifeTime = 0.6;
    near.maxLifeTime = 0.72;
    // Thin, fast streaks: lit where the lamps reach, nearly invisible past them.
    near.minSize = 0.006;
    near.maxSize = 0.01;
    near.minScaleY = 24;
    near.maxScaleY = 38;
    this.far = new RainStreaks(scene, low ? 1800 : 3200, low ? 2200 : 4000);
    const far = this.far.system;
    far.emitter = new Vector3(0, 9, 0);
    far.minEmitBox.set(-17, 0, 12);
    far.maxEmitBox.set(17, 0, 54);
    far.minEmitPower = far.maxEmitPower = 1;
    far.minLifeTime = 0.7;
    far.maxLifeTime = 0.85;
    far.minSize = 0.005;
    far.maxSize = 0.008;
    far.minScaleY = 22;
    far.maxScaleY = 34;
    this.update(0, 6.8, 0);
  }
  update(t: number, speed: number, flash: number): void {
    const gust = 0.6 + Math.sin(t * 0.47) * 0.25 + Math.sin(t * 1.13) * 0.12;
    for (const field of [this.near, this.far]) {
      field.system.direction1.set(-gust, -10.5, -speed - 0.35);
      field.system.direction2.set(-gust * 0.6, -9.2, -speed + 0.35);
    }
    this.near.light(flash, 0.2, 0.5);
    this.far.light(flash, 0, 0.12);
  }
}
