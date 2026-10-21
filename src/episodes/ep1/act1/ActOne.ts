import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import { loadArea, type Area } from "../../../core/AreaLoader";
import { seededRandom } from "../../../audio/synth";
import { thunder } from "../audio/prologueSounds";
import { villageRain } from "../audio/nightSounds";
import { RainStreaks } from "../Rain";
import { VillageLights } from "./VillageLights";
import { StormSky } from "./StormSky";
import { EaveDrips } from "./EaveDrips";
import { Vigil } from "./Vigil";
import { NightLife } from "./NightLife";
import { Apparitions } from "./Apparitions";

/** Materials of the scattered plants (painted and library), batched coarsely. */
const PLANTS =
  /^(M_(banana|palm|tree_leaves|bamboo|grass|coconut|wet_bark)|shrub_|fern_|pachira_|grass_medium|moss_01|island_tree)/;

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
  vigil!: Vigil;
  night!: NightLife;
  apparitions!: Apparitions;
  private readonly rainAt = new Vector3();
  private rainSound: StaticSound | null = null;
  private thunderSound: StaticSound | null = null;
  private wasFlashing = false;

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const game = this.game;
    this.area = await loadArea(game.scene, "ep1", "ep1_area_village", {
      cellSize: 8,
      // The figures that turn to watch Sora (Apparitions) stay nodes of their own.
      keep: [/^tingmong_\d+$/, "neakta_stone_watch"],
      // The forest's plants are everywhere: batch them in large cells.
      coarse: { pattern: PLANTS, cellSize: 24 },
    });
    this.sky = new StormSky(game.scene);
    this.lights = new VillageLights(game.scene, this.area, game.camera);
    // Rain in a box round Sora, following her (moved each frame).
    this.rain = new RainStreaks(game.scene, 6000, 7000);
    this.rain.system.emitter = this.rainAt;
    this.rain.system.minEmitBox.set(-9, 0, -9);
    this.rain.system.maxEmitBox.set(9, 0, 9);
    this.drips = new EaveDrips(game.scene, this.area);

    const spawn = this.area.level.spawns.get("player");
    game.spawnPlayer(spawn?.position, spawn?.yaw ?? 0);
    for (const { name, node } of this.area.level.interactables) game.interaction.add(name, node);
    this.vigil = new Vigil(game, this.area, this.lights);
    await this.vigil.load();
    this.night = new NightLife(game, this.area);
    this.apparitions = new Apparitions(game, this.area, this.lights, this.vigil);
  }

  async begin(): Promise<void> {
    const game = this.game;
    game.addFlameLights(...this.lights.flames.slice(0, 4), this.lights.lamp);
    // A dark night, as horror games keep it: the lamp is what Sora sees by, and
    // beyond it the forest is only shapes; her eyes adjust less than in a shut room.
    // With the lamp out the eyes open only a little, and night sight finds no more
    // than the nearest shapes: the dark stays dark.
    game.atmosphere.baseExposure = 1.5;
    game.atmosphere.maxExposure = 2.1;
    game.atmosphere.nightSightIntensity = 1.6;
    // Night sight is the dark around her, not a light on what she holds: the cold
    // lantern stays a dark shape at her side.
    game.atmosphere.nightSight.excludedMeshes.push(...this.vigil.heldMeshes);
    // Rain mist: distance fades into a faint blue-grey, so silhouettes stand against it.
    const fog = game.pipeline.fog;
    if (fog) {
      fog.density = 0.034;
      fog.heightFalloff = 0.25;
      fog.ambient.set(0.005, 0.006, 0.009);
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
    this.vigil.begin();
  }

  private update(dt: number): void {
    const game = this.game;
    const eye = game.camera.globalPosition;
    this.vigil.update(dt);
    this.night.update(dt);
    this.apparitions.update(dt);
    this.lights.update(dt);
    this.rainAt.set(eye.x, eye.y + 7, eye.z);
    // Unlit streaks: faint in the dark, warmed a little by the lamp, white in lightning.
    this.rain.light(this.lights.storm.level, this.lights.lampFlame * 0.12, 0.25);
    this.drips.light(this.lights.storm.level);
    this.sky.update(this.lights.storm.level, game.pipeline.main.imageProcessing.exposure);
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
      audio.buffer(villageRain(rate, seededRandom(3)), rate),
      "ambience",
      eye,
      // Under everything else: the frogs, the chant and Sora's steps carry over it.
      { loop: true, minDistance: 4, volume: 0.32 },
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
    await this.night.makeSounds();
    await this.apparitions.makeSounds();
  }
}
