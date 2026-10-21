import type { Game } from "../../../core/Game";
import { loadArea, type Area } from "../../../core/AreaLoader";
import { StudioLights } from "./Studio";

/**
 * Episode 1 prologue: Sora's studio in Phnom Penh, 8:00 PM, rain (Beat Sheet,
 * section 3.1, beats P01–P07). Phase 2 greybox.
 */
export class Prologue {
  area!: Area;
  lights!: StudioLights;

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const game = this.game;
    this.area = await loadArea(game.scene, "ep1", "ep1_area_studio", { keep: ["window_glass"] });
    this.lights = new StudioLights(game.scene, this.area, game.preset);

    // P01: fade in at the drafting table.
    const spawn = this.area.level.spawns.get("player");
    game.spawnPlayer(spawn?.position, spawn?.yaw ?? Math.PI);
    // Looking down at the drafting table and the half-finished illustration.
    game.player.pitch = 0.42;
  }

  /** Starts the prologue once the game's post-processing exists. */
  begin(): void {
    const game = this.game;
    game.addFlameLights(this.lights.deskLamp, this.lights.candle);
    game.scene.onBeforeRenderObservable.add(() => {
      const dt = game.deltaSeconds;
      this.lights.update(dt);
      game.atmosphere.update(dt, this.lights.lightAtEye(game.camera.globalPosition));
    });
  }
}
