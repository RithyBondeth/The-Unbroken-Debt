import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Material } from "@babylonjs/core/Materials/material";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Game } from "@/core/Game";
import { loadArea, type Area } from "@/core/areaLoader";
import { seededRandom } from "@/audio/synth";
import { dawnBirds, villageRain } from "@/audio/sounds/nightSounds";
import { Soundscape } from "./Soundscape";
import { DreadScore } from "@/audio/DreadScore";
import { RainStreaks } from "@/render/weather/Rain";
import { VillageLights } from "./VillageLights";
import { StormSky } from "@/render/weather/StormSky";
import { ForestBorder } from "./ForestBorder";
import { TallGrass } from "./TallGrass";
import { Draught } from "../data/draught";
import { TreeOmens } from "./TreeOmens";
import { blendPathGround } from "./pathGround";
import { GROW_FOREST, PLAY } from "../data/forestBorder";
import { ROOFS } from "../data/farmLayout";
import { DAWN_LOOK } from "@/render/nightLook";
import { FUNERAL_LOOK, HOUSE_LOOK, VILLAGE_NIGHT } from "../data/villageLook";
import { NIGHT_GRADE } from "@/render/nightGrade";
import { GROUND_MIST } from "../data/forestAtmosphere";
import { forestMistField, spawnForestWisp } from "./forestMist";
import { LowGroundMist } from "@/render/LowGroundMist";
import { EaveDrips } from "./EaveDrips";
import { warmSceneViews } from "@/render/warmSceneViews";
import { applyFoliageWind } from "@/render/FoliageWind";
import { gradeJungle } from "./jungleGrade";
import { bakePlantHeights, type PlantSite } from "@/render/plantHeights";
import { snapToGround } from "@/render/groundSnap";
import { WindAudio, stingGust } from "../audio/WindAudio";
import { Vigil } from "./Vigil";
import { NightLife } from "./NightLife";
import { ShadowFigure } from "@/shared/entities/ShadowFigure";
import { Preay } from "../entities/Preay";
import { BetelOffering } from "./BetelOffering";
import { ArrivalModels } from "./ArrivalModels";
import { ActOneBeats, CP2_FEET } from "./ActOneBeats";
import { TENT_FLAME_MESH } from "../data/arrival";
import { inHouseRooms, underFuneralFloor } from "../data/funeral";
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
import { SavePoint } from "@/systems/saves/SavePoint";
import { PhraPhum } from "./PhraPhum";
import { KrasueEncounter } from "../entities/KrasueEncounter";
import { KrasueFlyer } from "../entities/KrasueFlyer";
import { DEV_SPOTS } from "../data/devSpots";
import { FuneralRoom } from "./FuneralRoom";
import { applySkyShelter } from "@/render/skyShelter";
import { HOUSE_SHELTER } from "../data/shelter";
import { BarnGate, BARN_GATE_MESH } from "../act3/BarnGate";
import { Trapdoor, TRAPDOOR_MESH } from "./Trapdoor";
import { cullVillageRoad, dressVillageRoad } from "./villageRoadLook";
import { VillageAudio, ep1AudioUrls } from "../audio/VillageAudio";
import { VillageHorrorDirector } from "../village/VillageHorrorDirector";
import { VillagePuzzles } from "../village/VillagePuzzles";
import { openWalkableShopInteriors } from "../village/openShopInteriors";
import { EpisodeClockUi } from "../clock/EpisodeClock";
import {
  SAVE_SHRINE_POSITION,
  SAVE_SHRINE_LOCATION,
  inSaveShrineClearing,
} from "../data/saveShrine";

const SMALL_PROP_RADIUS = 0.35;
const SMALL_PROP_DISTANCE = 14;
const PLANT_DISTANCE: Record<string, number> = { low: 62, medium: 86, high: 120 };
const FLASH_MIST: readonly [number, number, number] = [0.15, 0.19, 0.29];
const FARM_GRASS = false;
const PLANTS =
  /^(M_(banana|palm|tree_leaves|bamboo|grass|forest_|coconut|wet_bark|flora_|paddy_)|shrub_|fern_|pachira_|grass_medium|moss_01|island_tree)/;

/**
 * Episode 1 village: redesigned Asian psychological horror, 4 interconnected village puzzles
 * & obstacles, upgraded Preay & rice-field Krasue, Episode 1 Night Clock, and mastered CC0
 * spatial sound system, carrying cleanly through CP1–CP6 and Dawn.
 */
export class ActOne {
  area!: Area;
  lights!: VillageLights;
  private rain!: RainStreaks;
  private sky!: StormSky;
  border!: ForestBorder;
  funeralRoom!: FuneralRoom;
  grass: TallGrass | null = null;
  readonly draught = new Draught();
  omens: TreeOmens | null = null;
  private drips!: EaveDrips;
  vigil!: Vigil;
  night!: NightLife;
  betel!: BetelOffering;
  beats!: ActOneBeats;
  investigation!: SokInvestigation;
  walker!: HallwayWalker;
  desk!: DeskInvestigation;
  hunt!: UnderHouseHunt;
  chest!: ChestInvestigation;
  ritual!: FinalRitual;
  resolution!: DawnResolution;
  saveShrine!: PhraPhum;
  krasue!: KrasueEncounter;
  barnGate!: BarnGate;
  trapdoor!: Trapdoor;
  villageAudio!: VillageAudio;
  horror!: VillageHorrorDirector;
  puzzles!: VillagePuzzles;
  clock!: EpisodeClockUi;

  private resolutionDelay = 0;
  private running = false;
  private lowMist: LowGroundMist | null = null;
  private readonly rainAt = new Vector3();
  private rainSound: StaticSound | null = null;
  private score = new DreadScore(null);
  private soundscape!: Soundscape;
  private windAudio!: WindAudio;
  private plantSites: PlantSite[] = [];
  private wasFlashing = false;
  private candlelit = 0;
  private housebound = 0;

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const game = this.game;
    this.border = new ForestBorder(game.scene, game.preset);
    this.area = await loadArea(game.scene, "ep1", "ep1_area_village", {
      cellSize: 8,
      keep: [
        /^tingmong_\d+$/,
        "neakta_stone_watch",
        "door_sok_padlock",
        "shed_padlock",
        TENT_FLAME_MESH,
        /^house_flame_[\d_]+$/,
        BARN_GATE_MESH,
        TRAPDOOR_MESH,
        /^door_back_(leaf|nail)/,
        /^sok_desk(?:$|_|\.)/,
        "portrait_sok",
        /^floor_board_(10|11|12|13)(\.|$)/,
        "joist_13",
        /^coffin_/,
        /^main_burner/,
        "prop_chinese_armchair",
        ...FAILING_LAMPS.map((lamp) => lamp.mesh),
      ],
      coarse: { pattern: PLANTS, cellSize: 24 },
      beforeBatch: (container) => {
        this.border.capture(container);
        const grounded = snapToGround(container, (x, z) => this.border.terrainAt(x, z));
        if (grounded.length)
          console.info(`[ActOne] ${grounded.length} objects set down on the ground`);
        this.plantSites = bakePlantHeights(container);
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
    const openedShops = openWalkableShopInteriors(game.scene);
    game.scene.onDisposeObservable.addOnce(() => openedShops.dispose());
    console.info(
      `[ActOne] ${openedShops.openedCount} roadside shop interiors opened for exploration`,
    );
    this.border.build();
    this.grass = FARM_GRASS
      ? new TallGrass(
          game.scene,
          game.preset,
          game.wind,
          (x, z) => this.border.groundAt(x, z),
          (x, z, r) => this.border.clear(x, z, r),
          this.border.grassClump,
        )
      : null;
    if (GROW_FOREST) {
      this.omens = new TreeOmens(game.scene, game.wind, (x, z) => this.border.groundAt(x, z));
      this.omens.build(this.plantSites);
    }
    game.fallGuard.bounds = PLAY;

    const [, , , preay] = await Promise.all([
      ShadowFigure.prepare(game.scene),
      PhraPhum.prepare(game.scene),
      KrasueFlyer.prepare(game.scene),
      Preay.load(game.scene),
    ]);

    const offeringModels = new OfferingModels(game.scene);
    offeringModels.replacePickups(this.area);
    const sokModels = new SokRoomModels(game.scene, this.area);
    const walkerModels = new WalkerModels(game.scene, this.area, preay);
    const deskModels = new DeskModels(game.scene, this.area);
    const huntModels = new HuntModels(game.scene, this.area, preay, (x, z) =>
      this.border.groundAt(x, z),
    );
    const chestModels = new ChestModels(game.scene, this.area);
    const corpseModels = await CorpseModels.load(game.scene, this.area);
    const arrivalModels = new ArrivalModels(game.scene);
    this.sky = new StormSky(game.scene);
    this.funeralRoom = new FuneralRoom(game.scene, this.area, game.preset.name === "low");
    game.scene.onDisposeObservable.addOnce(() => this.funeralRoom.dispose());
    this.lights = new VillageLights(
      game.scene,
      this.area,
      game.camera,
      game.preset.clusteredLights,
    );
    this.lights.draught = this.draught;
    gradeJungle(game.scene.materials);
    sheerNets(game.scene.materials);
    blendPathGround(game.scene);
    applyFoliageWind(game.scene.materials, game.wind);
    this.windAudio = new WindAudio(game, game.wind, {
      sites: [...this.plantSites, ...this.border.sites],
      voices: game.preset.name === "low" ? 2 : 4,
    });

    this.rain = new RainStreaks(game.scene, 6000, 7000);
    this.rain.system.emitter = this.rainAt;
    this.rain.system.minEmitBox.set(-9, 0, -9);
    this.rain.system.maxEmitBox.set(9, 0, 9);
    this.rain.shelter(ROOFS);
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
    const devAt = import.meta.env.DEV ? new URLSearchParams(location.search).get("at") : null;
    const devSpot = devAt ? DEV_SPOTS[devAt] : undefined;
    if (devSpot) {
      game.player.teleport(new Vector3(...devSpot.feet), devSpot.yaw);
      game.fallGuard.reset(game.player.feet);
    }
    for (const ladder of this.area.level.ladders) game.player.addLadder(ladder);
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
      else game.interaction.add(name, node);
    }

    this.villageAudio = new VillageAudio(game.audio);
    this.barnGate = new BarnGate(game, this.area);
    this.trapdoor = new Trapdoor(game, this.area);
    this.vigil = new Vigil(game, this.area, this.lights);
    await this.vigil.load();

    this.night = new NightLife(game, this.area, () =>
      Math.max(this.saveShrine?.silence ?? 0, this.villageAudio?.silence ?? 0),
    );
    this.soundscape = new Soundscape(game, () =>
      Math.max(this.night.threatSilence, this.villageAudio?.silence ?? 0),
    );

    this.clock = new EpisodeClockUi(
      game.flags,
      () =>
        this.running &&
        !game.paused &&
        !game.cutscene &&
        !this.puzzles?.uiOpen &&
        !game.satchel.isOpen &&
        !game.sketchbook?.isOpen,
      (glitched) => {
        this.villageAudio.play(
          glitched ? "clockChimeLow" : "clockChime",
          game.camera.globalPosition.add(new Vector3(0, 6, -12)),
          0.65,
        );
      },
      () => this.villageAudio.play("clockTick", game.camera.globalPosition, 0.5),
    );
    game.scene.onDisposeObservable.addOnce(() => this.clock.dispose());

    this.horror = new VillageHorrorDirector(game, this.lights, this.villageAudio, preay, (x, z) =>
      this.border.groundAt(x, z),
    );
    this.horror.onClockGlitch = (sec) => this.clock.glitch(sec);
    await this.horror.load();

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

    if (!actTwo && !game.flags.has("ep1.village.puzzlesActive")) {
      game.flags.set("ep1.village.puzzlesActive", true);
    }
    this.puzzles = new VillagePuzzles(
      game,
      this.vigil,
      this.villageAudio,
      (x, z) => this.border.groundAt(x, z),
      () => this.beats.saveProgress(),
      {
        onBarberRadioSilenced: () => this.horror.triggerBarberHeadless(),
        onFenceWardSnapped: (at) => this.horror.triggerProvokedPreay(at),
        onWellTugFailed: (wellPos) => this.horror.triggerWellHeadless(wellPos),
        onWardMistake: (stPos) => this.horror.triggerProvokedPreay(stPos),
        onClockCursed: (clockPos) => {
          this.clock.glitch(12);
          this.horror.triggerProvokedPreay(clockPos);
        },
        onMilestoneClock: (time, label) => this.clock.announce(time, label, true),
      },
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
    this.krasue = new KrasueEncounter(game, this.vigil, this.villageAudio);

    this.saveShrine = new PhraPhum(game, SAVE_SHRINE_POSITION);
    new SavePoint(
      game,
      "interact_save_courtyard",
      SAVE_SHRINE_POSITION,
      "COURTYARD",
      async () => {
        const data = this.beats.captureProgress();
        const feet = game.player.feet;
        Object.assign(data.flags, {
          "checkpoint.spawn.cp": data.checkpoint,
          "checkpoint.spawn.x": feet.x,
          "checkpoint.spawn.y": feet.y,
          "checkpoint.spawn.z": feet.z,
          "checkpoint.spawn.yaw": game.player.yaw,
        });
        await game.checkpoints.mark(data, SAVE_SHRINE_LOCATION);
      },
      () => !game.hiding && !game.flags.get("ep1.seal1.broken", false),
      this.saveShrine,
    );

    this.cullSmallProps();
    this.cullFarPlants();
    this.unpickDecor();
    const sheltered = applySkyShelter(game.scene.materials, HOUSE_SHELTER);
    console.info(`[ActOne] ${sheltered} materials sheltered from the sky in the house`);
    for (const material of game.scene.materials)
      if (/^M_paddy_rice_/.test(material.name) && "alphaCutOff" in material)
        (material as { alphaCutOff: number }).alphaCutOff = 0.34;
    const roadDressed = dressVillageRoad(game.scene.materials);
    const roadLimited = cullVillageRoad(game.scene.meshes);
    console.info(
      `[ActOne] ${roadDressed} village road materials dressed, ${roadLimited} road meshes drawn only near`,
    );
  }

  private candlelitSight(dt: number): void {
    if (this.resolution?.active) return;
    const atmosphere = this.game.atmosphere;
    const sight = atmosphere.nightSight;
    const feet = this.game.player.feet;
    const inside = underFuneralFloor(feet) ? 1 : 0;
    this.candlelit += (inside - this.candlelit) * Math.min(1, dt * 1.5);
    const rooms = inHouseRooms(feet) ? 1 : 0;
    this.housebound += (rooms - this.housebound) * Math.min(1, dt * 1.2);
    const k = this.candlelit;
    const h = this.housebound * (1 - k);
    const mix = (night: number, funeral: number, house: number) =>
      night + (funeral - night) * k + (house - night) * h;
    this.lights.indoors = Math.max(k, h);
    sight.diffuse.set(0.55 + 0.27 * k, 0.62 + 0.02 * k, 0.75 - 0.3 * k);
    atmosphere.nightSightIntensity =
      VILLAGE_NIGHT.nightSightIntensity * mix(1, FUNERAL_LOOK.nightSight, HOUSE_LOOK.nightSight);
    atmosphere.baseExposure = mix(
      VILLAGE_NIGHT.baseExposure,
      FUNERAL_LOOK.baseExposure,
      HOUSE_LOOK.baseExposure,
    );
    atmosphere.maxExposure = mix(
      VILLAGE_NIGHT.maxExposure,
      FUNERAL_LOOK.maxExposure,
      HOUSE_LOOK.maxExposure,
    );
    if (h > k) atmosphere.blendGrade(NIGHT_GRADE, HOUSE_LOOK.grade, h);
    else atmosphere.blendGrade(NIGHT_GRADE, FUNERAL_LOOK.grade, k);
  }

  private unpickDecor(): void {
    const decor =
      /(offering|phra_phum_|^M_fo_|^M_hr_|shroud|^M_cp_|^M_rk_|^M_flora_|incense|flame|marigold|jasmine|beeswax|^M_funeral_petal|^M_rice$)/i;
    let n = 0;
    for (const mesh of this.game.scene.meshes) {
      if (!mesh.isPickable || !decor.test(mesh.material?.name ?? "")) continue;
      let used = false;
      for (let p = mesh.parent; p && !used; p = p.parent) used = /^interact_/.test(p.name);
      if (used || /^interact_/.test(mesh.name)) continue;
      mesh.isPickable = false;
      n++;
    }
    console.info(`[ActOne] ${n} decorative meshes left out of the interaction ray`);
  }

  private cullFarPlants(): void {
    const distance = PLANT_DISTANCE[this.game.preset.name];
    if (!distance) return;
    let culled = 0;
    for (const mesh of this.game.scene.meshes) {
      if (!(mesh instanceof Mesh) || !/^batch_/.test(mesh.name) || mesh.hasLODLevels) continue;
      if (!PLANTS.test(mesh.material?.name ?? "")) continue;
      mesh.addLODLevel(distance, null);
      culled++;
    }
    console.info(`[ActOne] ${culled} plant batches drawn only within ${distance} m`);
  }

  private cullSmallProps(): void {
    let culled = 0;
    for (const mesh of this.game.scene.meshes) {
      if (!(mesh instanceof Mesh) || mesh.skeleton || mesh.getTotalVertices() === 0) continue;
      if (/^batch/.test(mesh.name) || mesh.material?.name === "M_flame") continue;
      if (mesh.hasLODLevels) continue;
      mesh.computeWorldMatrix(true);
      if (mesh.getBoundingInfo().boundingSphere.radiusWorld > SMALL_PROP_RADIUS) continue;
      mesh.addLODLevel(SMALL_PROP_DISTANCE, null);
      culled++;
    }
    console.info(`[ActOne] ${culled} small props drawn only within ${SMALL_PROP_DISTANCE} m`);
  }

  async begin(): Promise<void> {
    const game = this.game;
    this.lights.fogLights = game.pipeline.fog?.lights ?? null;
    game.atmosphere.baseExposure = VILLAGE_NIGHT.baseExposure;
    game.atmosphere.maxExposure = VILLAGE_NIGHT.maxExposure;
    game.atmosphere.nightSightIntensity = VILLAGE_NIGHT.nightSightIntensity;
    game.atmosphere.nightSight.range = VILLAGE_NIGHT.nightSightRange;
    game.atmosphere.nightSight.excludedMeshes.push(...this.vigil.heldMeshes, ...game.hands.meshes);

    const fog = game.pipeline.fog;
    if (fog) {
      fog.density = VILLAGE_NIGHT.fogDensity;
      fog.heightFalloff = 0.09;
      fog.ambient.set(...VILLAGE_NIGHT.fogAmbient);
      fog.setMistPockets(GROUND_MIST);
      fog.setMistField(forestMistField(game.scene));
    } else {
      game.scene.fogDensity = VILLAGE_NIGHT.fogDensity;
      game.scene.fogColor.set(...VILLAGE_NIGHT.fogAmbient);
      this.lowMist = new LowGroundMist(game.scene, GROUND_MIST, spawnForestWisp, 160);
    }

    game.wind.base = 0.55;
    game.wind.sway = 0;
    game.scene.onDisposeObservable.addOnce(() => (game.wind.sway = 1));
    game.scene.onBeforeRenderObservable.add(() => this.update(game.deltaSeconds));
    if (import.meta.env.DEV) (window as unknown as { act: ActOne }).act = this;

    game.cutscene = true;
    await game.fade.to(1, 0);
    await game.fade.waitForEnter(() => {
      void game.input.lockPointer();
      void game.audio?.unlock();
    });
    await game.audio?.unlock().catch(() => undefined);
    await this.makeSounds();
    void game.fade.to(0, 3);
    game.cutscene = false;
    this.running = true;
    this.vigil.begin();
    this.clock.announce(this.clock.state.rawTime, undefined, false);
    await this.beats.begin();
  }

  async warmup(): Promise<void> {
    await ShadowFigure.warmup(this.game.scene);
    const actors = [this.walker.models.walker, this.hunt.models.roamer].map((node) => ({
      node,
      position: node.position.clone(),
      rotation: node.rotation.clone(),
      enabled: node.isEnabled(),
    }));
    this.walker.models.pose(new Vector3(0, 2.5, -14.5), new Vector3(0, 0, -1), 0);
    this.walker.models.walker.setEnabled(true);
    this.hunt.models.pose(new Vector3(2.6, 0, -26.5), new Vector3(0, 0, -1), 0, 1);
    try {
      await warmSceneViews(this.game.scene, this.game.camera, [
        { eye: new Vector3(0, 1.58, 46), target: new Vector3(-1, 1.3, 30) },
        { eye: new Vector3(1, 1.58, 18), target: new Vector3(0.5, 1.3, 2) },
        { eye: new Vector3(0, 1.58, 0), target: new Vector3(0, 1.8, -12) },
        { eye: new Vector3(-2.4, 1.58, -11.4), target: new Vector3(-1.2, 1.0, -19) },
        {
          eye: SAVE_SHRINE_POSITION.add(new Vector3(0, 1.58, 3)),
          target: SAVE_SHRINE_POSITION.add(new Vector3(0, 1.6, 0)),
        },
        { eye: new Vector3(-2.2, 4.12, -12.1), target: new Vector3(0.6, 3.4, -17.4) },
        { eye: new Vector3(-0.15, 4.1, -22.55), target: new Vector3(0, 3.6, -34) },
        { eye: new Vector3(1.7, 4.05, -25), target: new Vector3(7.5, 3.2, -25.3) },
        { eye: new Vector3(14.5, 1.7, -6.5), target: new Vector3(24, 3.2, -19) },
        { eye: new Vector3(-22.2, 2.8, -22.5), target: new Vector3(-28.5, 1.7, -23) },
      ]);
    } finally {
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
    this.windAudio.update(dt);
    this.villageAudio.update(dt);
    this.clock.update(dt);
    this.draught.update(dt, game.player.feet);
    this.funeralRoom.update(dt, this.lights.tentLevel, this.draught);
    this.candlelitSight(dt);
    this.grass?.update(dt, eye);

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
    this.barnGate.update(dt);
    this.trapdoor.update(dt);
    this.puzzles.update(dt);
    this.betel.update(dt);
    this.beats.update(dt);
    this.investigation.update(dt);
    this.walker.update(dt);
    this.desk.update(dt);
    this.hunt.update(dt);
    this.chest.update(dt);
    this.ritual.update(dt);

    this.horror.update(dt, this.puzzles.uiOpen);
    this.krasue.update(dt, this.horror.active || this.puzzles.uiOpen);
    this.soundscape.update(dt);

    // Cold lamp-choking aura when Preay (village haunt, hallway walker, or roamer) draws near
    const walkerChill = this.walker.brain.active
      ? Math.max(0, 1 - Vector3.Distance(eye, this.walker.brain.position) / 8.5) ** 2
      : 0;
    const huntChill = this.hunt.brain.active
      ? Math.max(0, 1 - Vector3.Distance(eye, this.hunt.brain.position) / 8.5) ** 2
      : 0;
    this.lights.coldAura = Math.max(this.horror.preayChill, walkerChill, huntChill);

    const pressure = Math.max(
      this.horror.dread * 0.78,
      this.night.threatSilence * 0.45,
      this.villageAudio.silence * 0.5,
      (this.saveShrine?.silence ?? 0) * 0.4,
      this.krasue.brain.active ? 0.65 : 0,
      walkerChill * 0.85,
      huntChill * 0.9,
    );
    this.score.pressure(pressure);
    // Drive Sora's physical fear vignette, subtle handheld tremor, and chest heartbeat directly from horror pressure
    const fearTarget = Math.min(1, Math.max(this.horror.dread * 0.9, pressure * 0.85));
    game.atmosphere.mood.fear += (fearTarget - game.atmosphere.mood.fear) * Math.min(1, dt * 3.0);
    game.player.dreadTremor = Math.max(0, (fearTarget - 0.28) / 0.72);
    this.villageAudio.setHeartbeat(Math.max(0, (fearTarget - 0.3) / 0.7));
    game.wind.calm = Math.max(
      this.night.threatSilence,
      this.villageAudio.silence,
      this.saveShrine?.silence ?? 0,
    );
    game.wind.tension = Math.max(pressure, this.horror.dread * 0.65);
    this.score.update(dt);
    this.night.update(dt);
    this.lights.lookingAt = game.interaction.distance;
    this.lights.update(dt);

    const wind = game.wind;
    const slant = wind.at(eye.x, eye.z) * 0.32;
    this.rain.system.direction1.set(wind.dirX * slant - 0.05, -1, wind.dirZ * slant + 0.02);
    this.rain.system.direction2.set(wind.dirX * slant + 0.01, -1, wind.dirZ * slant + 0.08);
    this.rainAt.set(eye.x - wind.dirX * slant * 4, eye.y + 7, eye.z - wind.dirZ * slant * 4);
    this.rain.light(this.lights.storm.level, this.lights.lampFlame * 0.25, 0.55);

    const mist = game.pipeline.fog;
    if (mist && !this.resolution.active) {
      const f = this.lights.storm.level;
      const own =
        1 +
        (FUNERAL_LOOK.mist - 1) * this.candlelit +
        (HOUSE_LOOK.mist - 1) * this.housebound * (1 - this.candlelit);
      const [r, g, b] = VILLAGE_NIGHT.fogAmbient;
      mist.ambient.set(
        r * own + f * FLASH_MIST[0],
        g * own + f * FLASH_MIST[1],
        b * own + f * FLASH_MIST[2],
      );
    }
    this.drips.light(this.lights.storm.level);
    this.sky.update(this.lights.storm.level, game.pipeline.main.imageProcessing.exposure, dt);
    game.atmosphere.update(dt, this.lights.lightAtEye(eye));

    const flashing = this.lights.flashing;
    if (flashing && !this.wasFlashing) {
      setTimeout(
        () => {
          if (this.resolution.active) return;
          const a = Math.random() * Math.PI * 2;
          const far = 25 + Math.random() * 55;
          const at = new Vector3(
            eye.x + Math.cos(a) * far,
            eye.y + 20 + far * 0.3,
            eye.z + Math.sin(a) * far,
          );
          this.villageAudio.play("thunder", at, 0.95, 1.08 - (far / 80) * 0.22);
        },
        1400 + Math.random() * 2400,
      );
    }
    this.wasFlashing = flashing;
  }

  private dawn(): void {
    const g = this.game;
    this.rain.system.stop();
    this.rainSound?.stop();
    this.score.pressure(0);
    this.villageAudio.stopAll();
    g.wind.base = 0.16;
    g.wind.calm = 0;
    g.wind.tension = 0;
    this.night.stopForDawn();
    this.soundscape.stop();
    this.krasue.stop();
    this.lowMist?.stop();
    this.sky.dome.setEnabled(false);
    this.lights.dawn();
    this.clock.announce("05:30", "Dawn", false);
    g.scene.clearColor.set(...DAWN_LOOK.clearColor, 1);
    g.atmosphere.baseExposure = DAWN_LOOK.baseExposure;
    g.atmosphere.maxExposure = DAWN_LOOK.maxExposure;
    g.atmosphere.nightSightIntensity = DAWN_LOOK.nightSightIntensity;
    g.atmosphere.nightSight.range = DAWN_LOOK.nightSightRange;
    g.pipeline.main.imageProcessing.exposure = DAWN_LOOK.baseExposure;
    if (g.pipeline.fog) {
      g.pipeline.fog.mistStrength = 0;
      g.pipeline.fog.fieldStrength = 0.25;
      g.pipeline.fog.density = DAWN_LOOK.fogDensity;
      g.pipeline.fog.ambient.set(...DAWN_LOOK.fogAmbient);
    } else {
      g.scene.fogDensity = DAWN_LOOK.fogDensity;
      g.scene.fogColor.set(...DAWN_LOOK.fogAmbient);
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

  /** Loads the redesigned mastered CC0 Village soundscape and SFX pools. */
  private async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) {
      await this.investigation.makeSounds();
      return;
    }
    const rate = audio.context.sampleRate;
    const recRain = await audio.load(ep1AudioUrls("amb_ep1_village_rain"));
    this.rainSound = await audio.sound(
      "village_rain",
      recRain ??
        audio.buffer(
          [villageRain(rate, seededRandom(3)), villageRain(rate, seededRandom(5))],
          rate,
        ),
      "ambience",
      recRain ? 0.66 : 0.34,
    );
    this.rainSound.loop = true;
    this.rainSound.play();

    this.score = new DreadScore(audio);
    this.score.onSting = (kind, volume) =>
      stingGust(this.game.wind, kind, volume, this.score.lead(kind));
    await this.score.load(ep1AudioUrls("amb_ep1_village_dread"));
    this.horror.score = this.score;
    this.saveShrine.score = this.score;

    await this.villageAudio.load();
    await this.night.makeSounds();
    await this.soundscape.makeSounds();
    await this.windAudio.makeSounds();
    await this.puzzles.makeSounds();
    await this.betel.makeSounds();
    await this.beats.makeSounds();
    await this.investigation.makeSounds();
    await this.walker.makeSounds();
    await this.desk.makeSounds();
    await this.hunt.makeSounds();
    await this.chest.makeSounds();
    await this.ritual.makeSounds();
    await this.krasue.makeSounds();
    await this.saveShrine.makeSounds();
  }
}

function sheerNets(materials: readonly Material[]): void {
  for (const material of materials) {
    if (!(material instanceof PBRMaterial) || !/mosquito_net/.test(material.name)) continue;
    material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    material.useAlphaFromAlbedoTexture = false;
    material.alpha = 0.26;
    material.backFaceCulling = false;
  }
}
