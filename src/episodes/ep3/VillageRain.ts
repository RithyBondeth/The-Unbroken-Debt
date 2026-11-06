import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../core/Game";
import { RainStreaks } from "../../render/weather/Rain";

/** Rain beyond the windows remains visible while Sora shelters indoors. */
export class VillageRain {
  private readonly local: RainStreaks;
  private readonly windows: RainStreaks[];
  constructor(private readonly game: Game) {
    const low = game.preset.name === "low";
    this.local = new RainStreaks(game.scene, low ? 500 : 1400, 0);
    this.windows = Array.from({ length: 3 }, () => new RainStreaks(game.scene, low ? 220 : 650, 0));
    for (const rain of [this.local, ...this.windows]) {
      rain.system.minLifeTime = 0.8;
      rain.system.maxLifeTime = 1.15;
      rain.system.minEmitPower = 9;
      rain.system.maxEmitPower = 12;
      rain.system.direction1.set(-0.17, -1, 0.08);
      rain.system.direction2.set(-0.08, -1, 0.14);
      rain.system.maxSize = 0.018;
      rain.system.minSize = 0.009;
    }
    game.scene.onDisposeObservable.addOnce(() => {
      this.local.dispose();
      for (const rain of this.windows) rain.dispose();
    });
  }
  update(wet: boolean, afternoon: boolean, flash: number, flame: number): void {
    const p = this.game.camera.globalPosition;
    const low = this.game.preset.name === "low";
    const rate = wet ? (afternoon ? 0.65 : 1) : 0;
    const nearClinic = Math.abs(p.x) < 30 && p.z > -36 && p.z < 27;
    const inClinic = Math.abs(p.x) < 12.2 && p.z > -11.5 && p.z < 10.8;
    const underAttic = p.x > -14 && p.x < -1.5 && p.z > -12.5 && p.z < 4 && p.y < 7.5;
    const marketRoof = [
      [-72, -5],
      [-56, -6],
      [-72, 4],
      [-56, 3],
      [-64, -13],
    ].find(([x, z]) => Math.abs(p.x - x) < 4.1 && Math.abs(p.z - z) < 3.7 && p.y < 4.5);
    const system = this.local.system;
    system.emitRate = rate * (low ? 380 : 1100);
    system.emitter = new Vector3(p.x, p.y + 5, p.z);
    system.minEmitBox.set(-8, 0, -8);
    system.maxEmitBox.set(8, 0, 8);
    if (inClinic || underAttic) system.emitRate = 0;
    else if (marketRoof) {
      // A strip outside the open front: particles never fall through the roof.
      system.emitter = new Vector3(marketRoof[0], 8.5, marketRoof[1] + 4.5);
      system.minEmitBox.set(-4, 0, -0.6);
      system.maxEmitBox.set(4, 0, 0.6);
    }
    this.local.light(flash, flame * 0.1, afternoon ? 0.85 : 0.45);
    for (let i = 0; i < this.windows.length; i++) {
      const rain = this.windows[i],
        ps = rain.system;
      ps.emitRate = nearClinic ? rate * (low ? 170 : 480) : 0;
      if (i < 2) {
        ps.emitter = new Vector3(i === 0 ? -13.5 : 13.5, 7.8, Math.max(-7, Math.min(6, p.z)));
        ps.minEmitBox.set(-0.7, 0, -8);
        ps.maxEmitBox.set(0.7, 0, 8);
      } else {
        ps.emitter = new Vector3(0, 7.8, -12.2);
        ps.minEmitBox.set(-11, 0, -0.6);
        ps.maxEmitBox.set(11, 0, 0.6);
      }
      rain.light(flash, 0, afternoon ? 0.85 : 0.45);
    }
  }
}
