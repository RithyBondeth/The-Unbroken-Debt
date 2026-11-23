import type { Scene } from "@babylonjs/core/scene";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { RainStreaks } from "@/render/weather/Rain";

/** Heavy tropical monsoon storm streaks driven sideways across the twin headlight fog cones. */
export class TaxiWeather {
  private readonly near: RainStreaks;
  private readonly far: RainStreaks;
  constructor(scene: Scene, low: boolean) {
    this.near = new RainStreaks(scene, low ? 3400 : 7600, low ? 4600 : 9600);
    const near = this.near.system;
    near.emitter = new Vector3(0, 6.2, 0);
    near.minEmitBox.set(-7.5, 0, 5.5);
    near.maxEmitBox.set(7.5, 0, 26);
    near.minEmitPower = near.maxEmitPower = 1;
    near.minLifeTime = 0.54;
    near.maxLifeTime = 0.68;
    // Fast, slashing storm streaks catching the golden headlamp fog and silver lightning.
    near.minSize = 0.0065;
    near.maxSize = 0.0115;
    near.minScaleY = 26;
    near.maxScaleY = 44;
    this.far = new RainStreaks(scene, low ? 2100 : 4400, low ? 2800 : 5400);
    const far = this.far.system;
    far.emitter = new Vector3(0, 9.2, 0);
    far.minEmitBox.set(-18, 0, 10);
    far.maxEmitBox.set(18, 0, 52);
    far.minEmitPower = far.maxEmitPower = 1;
    far.minLifeTime = 0.65;
    far.maxLifeTime = 0.82;
    far.minSize = 0.0055;
    far.maxSize = 0.009;
    far.minScaleY = 24;
    far.maxScaleY = 38;
    this.update(0, 6.8, 0);
  }
  update(t: number, speed: number, flash: number): void {
    const squall = 0.5 + 0.5 * Math.sin(t * 0.29 + 0.8);
    const gust =
      1.05 + Math.sin(t * 0.61) * 0.48 + Math.sin(t * 1.43) * 0.26 + squall * 0.5 + flash * 0.9;
    for (const field of [this.near, this.far]) {
      field.system.direction1.set(-gust, -12.4, -speed - 0.55);
      field.system.direction2.set(-gust * 0.58, -10.5, -speed + 0.35);
    }
    this.near.light(flash, 0.28, 0.72);
    this.far.light(flash, 0.02, 0.2);
  }
}
