import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "../../../core/Game";
import { loadArea, type Area } from "../../../core/AreaLoader";
import { seededRandom } from "../../../audio/synth";
import { thunder } from "../audio/prologueSounds";
import { dawnBirds, villageRain } from "../audio/nightSounds";
import { Soundscape } from "./Soundscape";
import { RainStreaks } from "../Rain";
import { VillageLights } from "./VillageLights";
import { StormSky } from "./StormSky";
import { ForestBorder } from "./ForestBorder";
import { PLAY } from "../data/forestBorder";
import { DAWN_LOOK, NIGHT_LOOK } from "../data/nightLook";
import { EaveDrips } from "./EaveDrips";
import { warmSceneViews } from "../../../render/warmSceneViews";
import { Vigil } from "./Vigil";
import { NightLife } from "./NightLife";
import { Apparitions } from "./Apparitions";
import { ShadowFigure } from "../entities/ShadowFigure";
import { BetelOffering } from "./BetelOffering";
import { ArrivalModels } from "./ArrivalModels";
import { ActOneBeats, CP2_FEET } from "./ActOneBeats";
import { TENT_FLAME_MESH } from "../data/arrival";
import { OfferingModels } from "./OfferingModels";
import { SokRoomModels } from "../act2/SokRoomModels";
import { SokInvestigation } from "../act2/SokInvestigation";
import { WalkerModels } from "../act2/WalkerModels";
import { HallwayWalker } from "../act2/HallwayWalker";
import { CP3_FEET, CP3_YAW } from "../data/walker";
import { DeskModels } from "../act2/DeskModels";
import { DeskInvestigation } from "../act2/DeskInvestigation";
import { CP4_FEET, CP4_YAW, FAILING_LAMPS } from "../data/desk";

import { HuntModels } from "../act3/HuntModels";
import { UnderHouseHunt } from "../act3/UnderHouseHunt";
import { CP5_FEET, CP5_YAW } from "../data/hunt";
import { DawnResolution } from "../resolution/DawnResolution";
import { FinalRitual } from "../act3/FinalRitual";
import { CP6_FEET, CP6_YAW } from "../data/ritual";
import { ChestModels } from "../act3/ChestModels";
import { CorpseModels } from "../act3/CorpseModels";
import { ChestInvestigation } from "../act3/ChestInvestigation";
import { EarlyStealth } from "./EarlyStealth";
import { SavePoint } from "../../../systems/saves/SavePoint";
import { PhraPhum } from "./PhraPhum";
import { ShrineEffigy } from "./ShrineEffigy";
import {
  SAVE_SHRINE_POSITION,
  SAVE_SHRINE_LOCATION,
  inSaveShrineClearing,
} from "../data/saveShrine";

/** Materials of the scattered plants (painted and library), batched coarsely. */
const PLANTS =
  /^(M_(banana|palm|tree_leaves|bamboo|grass|forest_|coconut|wet_bark)|shrub_|fern_|pachira_|grass_medium|moss_01|island_tree)/;

/**
 * Episode 1 village: arrival and vigil, Sok’s investigations, the hallway
 * walker, and the under-house hunt, from CP1 through CP6. The area stays loaded
 * across acts so every prop, practical light and path retains its story state.
 */
export class ActOne {
  area!: Area;
  lights!: VillageLights;
  private rain!: RainStreaks;
  private sky!: StormSky;
  border!: ForestBorder;
  private drips!: EaveDrips;
  vigil!: Vigil;
  night!: NightLife;
  apparitions!: Apparitions;
  betel!: BetelOffering;
  beats!: ActOneBeats;
  investigation!: SokInvestigation;
  walker!: HallwayWalker;
  desk!: DeskInvestigation;
  hunt!: UnderHouseHunt;
  chest!: ChestInvestigation;
  ritual!: FinalRitual;
  resolution!: DawnResolution;
  early!: EarlyStealth;
  saveShrine!: PhraPhum;
  private resolutionDelay = 0;
  private running = false;
  private readonly rainAt = new Vector3();
  private rainSound: StaticSound | null = null;
  private thunderSound: StaticSound | null = null;
  private soundscape!: Soundscape;
  private wasFlashing = false;

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const game = this.game;
    this.border = new ForestBorder(game.scene, game.preset);
    this.area = await loadArea(game.scene, "ep1", "ep1_area_village", {
      cellSize: 8,
      // The figures that turn to watch Sora (Apparitions) stay nodes of their own.
      keep: [
        /^tingmong_\d+$/,
        "neakta_stone_watch",
        "door_sok_padlock",
        "shed_padlock",
        TENT_FLAME_MESH,
        /^sok_desk(?:$|_|\.)/,
        "portrait_sok",
        /^floor_board_(10|11|12|13)(\.|$)/,
        "joist_13",
        /^coffin_/,
        /^main_burner/,
        "prop_chinese_armchair",
        ...FAILING_LAMPS.map((lamp) => lamp.mesh),
      ],
      // The forest's plants are everywhere: batch them in large cells.
      coarse: { pattern: PLANTS, cellSize: 24 },
      // The forest round the village grows from copies of its own plants.
      beforeBatch: (container) => {
        this.border.capture(container);
        // Authored low plants predate the shrine. Keep their leaf crowns out
        // of the roof and the approach, just as the generated forest does.
        for (const mesh of container.meshes) {
          if (!/^(banana_\d+|fern_|shrub_|grass_)/.test(mesh.name)) continue;
          mesh.computeWorldMatrix(true);
          const box = mesh.getBoundingInfo().boundingBox;
          const centre = box.centerWorld;
          const radius = Math.min(2.5, Math.max(box.extendSizeWorld.x, box.extendSizeWorld.z));
          if (!inSaveShrineClearing(centre.x, centre.z, radius)) continue;
          mesh.isVisible = false;
          mesh.isPickable = false;
          mesh.setEnabled(false);
        }
      },
    });
    this.border.build();
    game.fallGuard.bounds = PLAY;
    await Promise.all([ShadowFigure.prepare(game.scene), ShrineEffigy.prepare(game.scene)]);
    const offeringModels = new OfferingModels(game.scene);
    offeringModels.replacePickups(this.area);
    const sokModels = new SokRoomModels(game.scene, this.area);
    const walkerModels = new WalkerModels(game.scene, this.area);
    const deskModels = new DeskModels(game.scene, this.area);
    const huntModels = new HuntModels(game.scene, this.area);
    const chestModels = new ChestModels(game.scene, this.area);
    const corpseModels = await CorpseModels.load(game.scene, this.area);
    const arrivalModels = new ArrivalModels(game.scene);
    this.sky = new StormSky(game.scene);
    this.lights = new VillageLights(game.scene, this.area, game.camera);
    // Rain in a box round Sora, following her (moved each frame).
    this.rain = new RainStreaks(game.scene, 6000, 7000);
    this.rain.system.emitter = this.rainAt;
    this.rain.system.minEmitBox.set(-9, 0, -9);
    this.rain.system.maxEmitBox.set(9, 0, 9);
    this.drips = new EaveDrips(game.scene, this.area);

    const spawn = this.area.level.spawns.get("player");
    const actTwo = game.flags.get("ep1.act2.started", false);
    const cp3 = game.resumedSave?.checkpoint === "CP3";
    const cp4 = game.resumedSave?.checkpoint === "CP4";
    const cp5 = game.resumedSave?.checkpoint === "CP5";
    const cp6 = game.resumedSave?.checkpoint === "CP6";
    game.spawnPlayer(
      cp6
        ? CP6_FEET
        : cp5
          ? CP5_FEET
          : cp4
            ? CP4_FEET
            : cp3
              ? CP3_FEET
              : actTwo
                ? CP2_FEET
                : spawn?.position,
      cp6
        ? CP6_YAW
        : cp5
          ? CP5_YAW
          : cp4
            ? CP4_YAW
            : cp3
              ? CP3_YAW
              : actTwo
                ? Math.PI
                : (spawn?.yaw ?? 0),
    );
    const saved = game.resumedSave;
    if (saved && saved.flags["checkpoint.spawn.cp"] === saved.checkpoint) {
      const p = ["x", "y", "z", "yaw"].map((axis) => saved.flags[`checkpoint.spawn.${axis}`]);
      if (p.every((v) => typeof v === "number" && Number.isFinite(v))) {
        game.player.teleport(
          new Vector3(p[0] as number, p[1] as number, p[2] as number),
          p[3] as number,
        );
        game.fallGuard.reset(game.player.feet);
      }
    }
    for (const { name, node } of this.area.level.interactables) {
      if (game.flags.get(`ep1.pickup.${name}`, false)) node.setEnabled(false);
      else
        game.interaction.add(name, node, {
          outline: name !== "interact_altar" && !offeringModels.pickupIds.has(name),
        });
    }
    this.vigil = new Vigil(game, this.area, this.lights);
    await this.vigil.load();
    this.night = new NightLife(game, this.area, () => this.saveShrine?.silence ?? 0);
    this.soundscape = new Soundscape(game, () => this.night.threatSilence);
    this.apparitions = new Apparitions(game, this.area, this.lights, this.vigil);
    this.betel = new BetelOffering(game, this.area, offeringModels);
    this.beats = new ActOneBeats(
      game,
      this.area,
      this.lights,
      this.vigil,
      this.betel,
      this.night,
      arrivalModels,
    );
    this.investigation = new SokInvestigation(game, sokModels, () => this.beats.saveProgress());
    this.walker = new HallwayWalker(game, walkerModels, this.vigil, this.investigation, () =>
      this.beats.saveProgress(),
    );
    this.desk = new DeskInvestigation(game, this.area, deskModels, this.vigil, this.lights, () =>
      this.beats.saveProgress(),
    );
    this.hunt = new UnderHouseHunt(
      game,
      huntModels,
      this.vigil,
      () => this.beats.captureProgress(),
      () => this.beats.saveProgress(),
    );
    this.chest = new ChestInvestigation(game, chestModels, corpseModels, () => {
      this.hunt.refreshCheckpoint();
      return this.beats.saveProgress();
    });
    this.resolution = new DawnResolution(
      game,
      () => this.beats.captureProgress(),
      () => this.dawn(),
    );
    this.ritual = new FinalRitual(game, this.area, this.lights, () => this.beats.saveProgress());
    this.early = new EarlyStealth(game, this.vigil, () => this.beats.captureProgress());
    this.saveShrine = new PhraPhum(game, SAVE_SHRINE_POSITION);
    new SavePoint(
      game,
      "interact_save_courtyard",
      SAVE_SHRINE_POSITION,
      "COURTYARD",
      async () => {
        const data = this.beats.captureProgress(),
          feet = game.player.feet;
        Object.assign(data.flags, {
          "checkpoint.spawn.cp": data.checkpoint,
          "checkpoint.spawn.x": feet.x,
          "checkpoint.spawn.y": feet.y,
          "checkpoint.spawn.z": feet.z,
          "checkpoint.spawn.yaw": game.player.yaw,
        });
        await game.checkpoints.mark(data, SAVE_SHRINE_LOCATION);
      },
      () => !this.early.active && !game.hiding && !game.flags.get("ep1.seal1.broken", false),
      this.saveShrine,
    );
  }

  async begin(): Promise<void> {
    const game = this.game;
    game.addFlameLights(...this.lights.flames.slice(0, 4), this.lights.lamp);
    // A dark monsoon night: the lamp's warm pool, flames and lightning, and little
    // else; adapted eyes find shapes a few metres out. The exposure cap still keeps
    // extinguishing the lamp meaningfully darker.
    game.atmosphere.baseExposure = NIGHT_LOOK.baseExposure;
    game.atmosphere.maxExposure = NIGHT_LOOK.maxExposure;
    game.atmosphere.nightSightIntensity = NIGHT_LOOK.nightSightIntensity;
    game.atmosphere.nightSight.range = NIGHT_LOOK.nightSightRange;
    // Night sight is the dark around her, not a light on what she holds: the cold
    // lantern stays a dark shape at her side.
    game.atmosphere.nightSight.excludedMeshes.push(...this.vigil.heldMeshes, ...game.hands.meshes);
    // Rain mist: distance fades into a dim blue-black, still just lighter than the
    // trees, so their silhouettes stand against it.
    const fog = game.pipeline.fog;
    if (fog) {
      fog.density = NIGHT_LOOK.fogDensity;
      fog.heightFalloff = 0.25;
      fog.ambient.set(...NIGHT_LOOK.fogAmbient);
    }
    game.scene.onBeforeRenderObservable.add(() => this.update(game.deltaSeconds));
    if (import.meta.env.DEV) (window as unknown as { act: ActOne }).act = this;

    game.cutscene = true;
    await game.fade.to(1, 0);
    await game.fade.waitForEnter(() => {
      void game.input.lockPointer();
      void game.audio?.unlock();
    });
    await this.makeSounds();
    void game.fade.to(0, 3);
    game.cutscene = false;
    this.running = true;
    this.vigil.begin();
    await this.beats.begin();
  }

  async warmup(): Promise<void> {
    await ShadowFigure.warmup(this.game.scene);
    const finishForest = this.apparitions.prepareRenderWarmup();
    const actors = [this.walker.models.walker, this.hunt.models.roamer].map((node) => ({
      node,
      position: node.position.clone(),
      rotation: node.rotation.clone(),
      enabled: node.isEnabled(),
    }));
    this.walker.models.pose(new Vector3(-1.65, 2.5, -13.8), new Vector3(0, 0, -1), 0);
    this.walker.models.walker.setEnabled(true);
    this.hunt.models.pose(new Vector3(-1.5, 0, -10.65), new Vector3(0, 0, -1), 0, 1);
    try {
      await warmSceneViews(this.game.scene, this.game.camera, [
        { eye: new Vector3(0, 1.58, 53), target: new Vector3(0, 1.3, 40) },
        { eye: new Vector3(0, 1.58, 46), target: new Vector3(5, 1.25, 37.2) },
        { eye: new Vector3(0, 1.58, 24), target: new Vector3(0, 1.3, 6) },
        { eye: new Vector3(0, 1.58, 8), target: new Vector3(0, 1.3, -10) },
        {
          eye: SAVE_SHRINE_POSITION.add(new Vector3(0, 1.58, 3)),
          target: SAVE_SHRINE_POSITION.add(new Vector3(0, 1.6, 0)),
        },
        { eye: new Vector3(0, 1.58, -2), target: new Vector3(0, 1.3, -12) },
        { eye: new Vector3(-1.65, 4.08, -17.05), target: new Vector3(-1.65, 3.65, -13.8) },
        { eye: new Vector3(-2.4, 1.58, -12.8), target: new Vector3(-1.5, 0.96, -10.65) },
      ]);
    } finally {
      finishForest();
      for (const actor of actors) {
        actor.node.position.copyFrom(actor.position);
        actor.node.rotation.copyFrom(actor.rotation);
        actor.node.setEnabled(actor.enabled);
      }
    }
  }

  private update(dt: number): void {
    if (!this.running) return;
    const game = this.game;
    const eye = game.camera.globalPosition;
    if (this.resolution.active) {
      this.resolution.update(dt);
      return;
    }
    if (game.flags.get("ep1.seal1.broken", false)) {
      this.resolutionDelay += dt;
      if (game.flags.get("ep1.resolution.started", false) || this.resolutionDelay >= 12) {
        void this.resolution.begin();
        return;
      }
    }
    this.vigil.update(dt);
    this.early.update(dt);
    this.soundscape.update(dt);
    this.night.update(dt);
    if (!this.early.active) {
      this.apparitions.update(dt);
      this.betel.update(dt);
      this.beats.update(dt);
      this.investigation.update(dt);
      this.walker.update(dt);
      this.desk.update(dt);
      this.hunt.update(dt);
      this.chest.update(dt);
      this.ritual.update(dt);
    }
    this.lights.lookingAt = game.interaction.distance;
    this.lights.update(dt);
    this.rainAt.set(eye.x, eye.y + 7, eye.z);
    // Unlit streaks: faint in the dark, warmed a little by the lamp, white in lightning.
    this.rain.light(this.lights.storm.level, this.lights.lampFlame * 0.12, 0.25);
    this.drips.light(this.lights.storm.level);
    this.sky.update(this.lights.storm.level, game.pipeline.main.imageProcessing.exposure, dt);
    if (this.rainSound) this.rainSound.spatial.position = eye.clone();
    game.atmosphere.update(dt, this.lights.lightAtEye(eye));
    const flashing = this.lights.flashing;
    if (flashing && !this.wasFlashing)
      setTimeout(
        () => {
          if (!this.thunderSound || this.resolution.active) return;
          this.thunderSound.spatial.position = new Vector3(eye.x - 30, eye.y + 25, eye.z - 20);
          this.thunderSound.play();
        },
        1500 + Math.random() * 2500,
      );
    this.wasFlashing = flashing;
  }

  private dawn(): void {
    const g = this.game;
    this.rain.system.stop();
    this.rainSound?.stop();
    this.thunderSound?.stop();
    this.night.stopForDawn();
    this.soundscape.stop();
    this.sky.dome.setEnabled(false);
    this.lights.dawn();
    g.scene.clearColor.set(...DAWN_LOOK.clearColor, 1);
    g.atmosphere.baseExposure = DAWN_LOOK.baseExposure;
    g.pipeline.main.imageProcessing.exposure = DAWN_LOOK.baseExposure;
    if (g.pipeline.fog) {
      g.pipeline.fog.density = DAWN_LOOK.fogDensity;
      g.pipeline.fog.ambient.set(...DAWN_LOOK.fogAmbient);
    }
    this.chest.body.pose(0);
    this.chest.body.setLid(0);
    const audio = g.audio;
    if (audio) {
      const rate = audio.context.sampleRate;
      const birds = dawnBirds(rate, seededRandom(5));
      void audio
        .spatialSound("dawn_birds", audio.buffer(birds, rate), "ambience", new Vector3(10, 4, 8), {
          loop: true,
          minDistance: 10,
          volume: 0.2,
        })
        .then((sound) => sound.play())
        .catch(() => undefined);
    }
  }

  /** Placeholder rain and thunder until the recordings exist. */
  private async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) {
      await this.investigation.makeSounds();
      return;
    }
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
    await this.soundscape.makeSounds();
    await this.apparitions.makeSounds();
    await this.betel.makeSounds();
    await this.beats.makeSounds();
    await this.investigation.makeSounds();
    await this.walker.makeSounds();
    await this.desk.makeSounds();
    await this.hunt.makeSounds();
    await this.chest.makeSounds();
    await this.ritual.makeSounds();
    await this.early.makeSounds();
    await this.saveShrine.makeSounds();
  }
}
