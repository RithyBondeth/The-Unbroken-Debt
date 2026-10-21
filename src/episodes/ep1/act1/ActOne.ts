import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import { loadArea, type Area } from "../../../core/AreaLoader";
import { seededRandom } from "../../../audio/synth";
import { rainLoop, thunder } from "../../../audio/prologueSounds";
import { RainStreaks } from "../Rain";
import { VillageLights } from "./VillageLights";
import { StormSky } from "./StormSky";
import { EaveDrips } from "./EaveDrips";

/**
 * Episode 1, Act I · Arrival and the vigil (Beat Sheet, section 3.2), from
 * checkpoint CP1 at the carriage on the flooded road, 11:30 PM. Phase 2,
 * first step: the village blockout, walkable, in rain and lightning.
 */
export class ActOne {
  area!: Area;
  lights!: VillageLights;
  private rain!: RainStreaks;
  private sky!: StormSky;
  private drips!: EaveDrips;
  private readonly rainAt = new Vector3();
  private rainSound: StaticSound | null = null;
  private thunderSound: StaticSound | null = null;
  private wasFlashing = false;

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const game = this.game;
    this.area = await loadArea(game.scene, "ep1", "ep1_area_village", { cellSize: 8 });
    this.sky = new StormSky(game.scene);
    this.lights = new VillageLights(game.scene, this.area, game.preset, game.camera);
    // Rain in a box round Sora, following her (moved each frame).
    this.rain = new RainStreaks(game.scene, 6000, 7000);
    this.rain.system.emitter = this.rainAt;
    this.rain.system.minEmitBox.set(-9, 0, -9);
    this.rain.system.maxEmitBox.set(9, 0, 9);
    this.drips = new EaveDrips(game.scene, this.area);

    const spawn = this.area.level.spawns.get("player");
    game.spawnPlayer(spawn?.position, spawn?.yaw ?? 0);
    for (const { name, node } of this.area.level.interactables) game.interaction.add(name, node);
  }

  async begin(): Promise<void> {
    const game = this.game;
    game.addFlameLights(...this.lights.flames.slice(0, 4), this.lights.lamp);
    // Rain mist: distance fades into a faint blue-grey, so silhouettes stand against it.
    const fog = game.pipeline.fog;
    if (fog) {
      fog.density = 0.024;
      fog.heightFalloff = 0.25;
      fog.ambient.set(0.011, 0.013, 0.018);
    }
    game.scene.onBeforeRenderObservable.add(() => this.update(game.deltaSeconds));
    if (import.meta.env.DEV) (window as unknown as { act: ActOne }).act = this;

    game.cutscene = true;
    await game.fade.to(1, 0);
    await game.fade.waitForClick(() => {
      void game.input.lockPointer();
      void game.audio?.unlock();
    });
    await this.makeSounds();
    void game.fade.to(0, 3);
    game.cutscene = false;
  }

  private update(dt: number): void {
    const game = this.game;
    const eye = game.camera.globalPosition;
    this.lights.update(dt);
    this.rainAt.set(eye.x, eye.y + 7, eye.z);
    this.rain.light(this.lights.storm.level);
    this.drips.light(this.lights.storm.level);
    this.sky.update(this.lights.storm.level);
    if (this.rainSound) this.rainSound.spatial.position = eye.clone();
    game.atmosphere.update(dt, this.lights.lightAtEye(eye));
    const flashing = this.lights.flashing;
    if (flashing && !this.wasFlashing)
      setTimeout(
        () => {
          if (!this.thunderSound) return;
          this.thunderSound.spatial.position = new Vector3(eye.x - 30, eye.y + 25, eye.z - 20);
          this.thunderSound.play();
        },
        1500 + Math.random() * 2500,
      );
    this.wasFlashing = flashing;
  }

  /** Placeholder rain and thunder until the recordings exist. */
  private async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const eye = this.game.camera.globalPosition;
    this.rainSound = await audio.spatialSound(
      "rain",
      audio.buffer(rainLoop(rate, seededRandom(3)), rate),
      "ambience",
      eye,
      {
        loop: true,
        minDistance: 4,
      },
    );
    this.rainSound.play();
    this.thunderSound = await audio.spatialSound(
      "thunder",
      audio.buffer(thunder(rate, seededRandom(4)), rate),
      "ambience",
      eye,
      {
        minDistance: 40,
      },
    );
  }
}
