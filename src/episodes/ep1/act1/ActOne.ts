import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Material } from "@babylonjs/core/Materials/material";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Game } from "@/core/Game";
import { loadArea, type Area } from "@/core/areaLoader";
import { seededRandom } from "@/audio/synth";
import { thunder } from "../audio/prologueSounds";
import { dawnBirds, villageRain } from "@/audio/sounds/nightSounds";
import { Soundscape } from "./Soundscape";
import { DreadScore } from "@/audio/DreadScore";
import { RainStreaks } from "@/render/weather/Rain";
import { VillageLights } from "./VillageLights";
import { StormSky } from "@/render/weather/StormSky";
import { ForestBorder } from "./ForestBorder";
import { TallGrass } from "./TallGrass";
import { TreeOmens } from "./TreeOmens";
import { blendPathGround } from "./pathGround";
import { GROW_FOREST, PLAY } from "../data/forestBorder";
import { ROOFS } from "../data/farmLayout";
import { DAWN_LOOK } from "@/render/nightLook";
import { FUNERAL_LOOK, HOUSE_LOOK, VILLAGE_NIGHT } from "../data/villageLook";
import { NIGHT_GRADE } from "@/render/nightGrade";
import { GROUND_MIST } from "../data/forestAtmosphere";
import { forestMistField, spawnForestWisp } from "./forestMist";
import { ForestAtmosphere } from "./ForestAtmosphere";
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
import { Apparitions } from "./Apparitions";
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
import { EarlyStealth } from "./EarlyStealth";
import { SavePoint } from "@/systems/saves/SavePoint";
import { PhraPhum } from "./PhraPhum";
import { KrasueEncounter } from "../entities/KrasueEncounter";
import { KrasueFlyer } from "../entities/KrasueFlyer";
import { DEV_SPOTS } from "../data/devSpots";
import { FuneralRoom } from "./FuneralRoom";
import { FuneralWatcher } from "./FuneralWatcher";
import { JumpScares } from "./JumpScares";
import { applySkyShelter } from "@/render/skyShelter";
import { HOUSE_SHELTER } from "../data/shelter";
import { BarnGate, BARN_GATE_MESH } from "../act3/BarnGate";
import { Trapdoor, TRAPDOOR_MESH } from "./Trapdoor";
import {
  SAVE_SHRINE_POSITION,
  SAVE_SHRINE_LOCATION,
  inSaveShrineClearing,
} from "../data/saveShrine";

/** Props smaller than this (bounding radius, m) are not drawn past SMALL_PROP_DISTANCE. */
const SMALL_PROP_RADIUS = 0.35;
const SMALL_PROP_DISTANCE = 14;
/**
 * How far the merged plant batches are drawn (m, to a batch's middle; its cell is up to
 * 24 m across). Past it the rain mist has the farm: at the farmstead's fog a tree 70 m
 * off keeps a tenth of its contrast (Nov 22, 2026: the farm's plants are 7 M triangles).
 */
const PLANT_DISTANCE: Record<string, number> = { low: 62, medium: 86, high: 120 };
/**
 * What a full lightning flash adds to the mist's own light (linear RGB): the previews'
 * flash frames, a deep slate blue in which the red earth still shows (0.3, 0.34, 0.42
 * washed the farm out to grey-white; Nov 23 side-by-sides).
 */
const FLASH_MIST: readonly [number, number, number] = [0.15, 0.19, 0.29];

/** Materials of the scattered plants (painted and library), batched coarsely. */
const PLANTS =
  /^(M_(banana|palm|tree_leaves|bamboo|grass|forest_|coconut|wet_bark|flora_|paddy_)|shrub_|fern_|pachira_|grass_medium|moss_01|island_tree)/;

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
  funeralRoom!: FuneralRoom;
  grass: TallGrass | null = null;
  omens: TreeOmens | null = null;
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
  krasue!: KrasueEncounter;
  barnGate!: BarnGate;
  trapdoor!: Trapdoor;
  watcher!: FuneralWatcher;
  scares!: JumpScares;
  private resolutionDelay = 0;
  private running = false;
  forest!: ForestAtmosphere;
  private lowMist: LowGroundMist | null = null;
  private readonly rainAt = new Vector3();
  private rainSound: StaticSound | null = null;
  private readonly thunderSounds: StaticSound[] = [];
  private score = new DreadScore(null);
  private soundscape!: Soundscape;
  private windAudio!: WindAudio;
  private plantSites: PlantSite[] = [];
  private wasFlashing = false;
  /** 0-1: how far night sight has turned to candlelight (the funeral room). */
  private candlelit = 0;
  /** 0 outside, 1 up in the house's rooms (HOUSE_LOOK), eased. */
  private housebound = 0;

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
        // The rooms' candle flames, each wavering on its wick (FuneralRoom).
        /^house_flame_[\d_]+$/,
        // The barn gate's leaf, padlock and chain (O3: BarnGate swings it open).
        BARN_GATE_MESH,
        // The hall trapdoor's lid (O6: Trapdoor lifts it).
        TRAPDOOR_MESH,
        // What the jump scares change (JumpScares): the sheet on the washing board (it
        // sits up, J2) and the nailed back door (smashed through, J3).
        /^wash_room_sheet(\.|_|$)/,
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
      // The forest's plants are everywhere: batch them in large cells.
      coarse: { pattern: PLANTS, cellSize: 24 },
      // The forest round the village grows from copies of its own plants.
      beforeBatch: (container) => {
        this.border.capture(container);
        // Nothing that grows or lies on the ground may hover over a dip in it.
        const grounded = snapToGround(container, (x, z) => this.border.terrainAt(x, z));
        if (grounded.length)
          console.info(`[ActOne] ${grounded.length} objects set down on the ground`);
        // Heights for the wind, before the plants are merged into batches.
        this.plantSites = bakePlantHeights(container);
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
    // The farmstead (Nov 22, 2026) is overgrown: tall grass wherever nobody walks
    // (data/grass.ts). The threads and rags tied round trunks stay with GROW_FOREST.
    this.grass = new TallGrass(
      game.scene,
      game.preset,
      game.wind,
      (x, z) => this.border.groundAt(x, z),
      (x, z, r) => this.border.clear(x, z, r),
      this.border.grassClump,
    );
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
    // The hall the coffin lies in: wavering flames, incense smoke, the haze under its ceiling.
    this.funeralRoom = new FuneralRoom(game.scene, this.area, game.preset.name === "low");
    game.scene.onDisposeObservable.addOnce(() => this.funeralRoom.dispose());
    this.lights = new VillageLights(
      game.scene,
      this.area,
      game.camera,
      game.preset.clusteredLights,
    );
    gradeJungle(game.scene.materials);
    sheerNets(game.scene.materials);
    blendPathGround(game.scene);
    applyFoliageWind(game.scene.materials, game.wind);
    this.windAudio = new WindAudio(game, game.wind, {
      sites: [...this.plantSites, ...this.border.sites],
      voices: game.preset.name === "low" ? 2 : 4,
    });
    // Rain in a box round Sora, following her (moved each frame).
    this.rain = new RainStreaks(game.scene, 6000, 7000);
    this.rain.system.emitter = this.rainAt;
    this.rain.system.minEmitBox.set(-9, 0, -9);
    this.rain.system.maxEmitBox.set(9, 0, 9);
    // Never through a roof: dry under the house (the funeral), in the sheds and huts.
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
    // Development: `?start=act1&at=hall` (see DEV_SPOTS) starts Sora inside the house.
    const devAt = import.meta.env.DEV ? new URLSearchParams(location.search).get("at") : null;
    const devSpot = devAt ? DEV_SPOTS[devAt] : undefined;
    if (devSpot) {
      game.player.teleport(new Vector3(...devSpot.feet), devSpot.yaw);
      game.fallGuard.reset(game.player.feet);
    }
    // The area's ladders (the trapdoor's, the attic's, the barn loft's and the kitchen
    // and servants' houses'): the player climbs only the ones it is given.
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
    this.barnGate = new BarnGate(game, this.area);
    this.trapdoor = new Trapdoor(game, this.area);
    this.vigil = new Vigil(game, this.area, this.lights);
    await this.vigil.load();
    this.night = new NightLife(game, this.area, () =>
      Math.max(this.saveShrine?.silence ?? 0, this.forest?.silence ?? 0),
    );
    this.soundscape = new Soundscape(game, () =>
      Math.max(this.night.threatSilence, this.forest?.silence ?? 0),
    );
    this.forest = new ForestAtmosphere(game);
    this.apparitions = new Apparitions(game, this.area, this.lights, preay);
    // The Preay walks on the village's real ground: down into the paddies, up the banks.
    this.apparitions.walksOn((x, z) => this.border.groundAt(x, z));
    // The approved previews' watcher behind the monks' table at the funeral (Act I).
    this.watcher = new FuneralWatcher(game, preay, (x, z) => this.border.groundAt(x, z));
    game.scene.onDisposeObservable.addOnce(() => this.watcher.dispose());
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
    // The five jump scares (J1-J5 of the approved gameplay map); J4 is a jar the hunt opens.
    this.scares = new JumpScares(game, this.area, preay, this.lights.storm);
    await this.scares.load();
    game.scene.onDisposeObservable.addOnce(() => this.scares.dispose());
    this.hunt.onJarOpened = (jar) => this.scares.jarOpened(jar.id, jar.root, jar.contents);
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
    this.early = new EarlyStealth(game, this.vigil, () => this.beats.captureProgress(), preay);
    this.krasue = new KrasueEncounter(game, this.vigil, () => this.beats.captureProgress());
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
    this.cullSmallProps();
    this.cullFarPlants();
    this.unpickDecor();
    // No sky in the rooms or under the floor: the previews are black there but for the
    // candles, the lamps and Sora's lantern.
    const sheltered = applySkyShelter(game.scene.materials, HOUSE_SHELTER);
    console.info(`[ActOne] ${sheltered} materials sheltered from the sky in the house`);
    // The paddies' ripe rice (tools/areas/village_fields.py, Nov 24, 2026): its thin stalks
    // fell out of the smaller mip levels at the default 0.5 cut-off and the fields went
    // patchy past a few metres. The atlas's colour is bled into its clear pixels
    // (tools/areas/bleed-alpha.py), so a lower cut keeps them full without dark fringes.
    for (const material of game.scene.materials)
      if (/^M_paddy_rice_/.test(material.name) && "alphaCutOff" in material)
        (material as { alphaCutOff: number }).alphaCutOff = 0.34;
  }

  /**
   * Under the house at the funeral the dark round Sora is candlelit, not moonlit
   * (FUNERAL_LOOK, against the approved previews, Nov 20 and 24, 2026): night sight
   * turns warm and all but goes, the blue mist light and the sky fall away, the
   * shadows warm, and the eye stays near the previews' exposure. It eases in and out
   * over about a second as she crosses the front block's edge.
   */
  private candlelitSight(dt: number): void {
    // Dawn sets its own night sight (DawnResolution); leave it be then.
    if (this.resolution?.active) return;
    const atmosphere = this.game.atmosphere;
    const sight = atmosphere.nightSight;
    const feet = this.game.player.feet;
    const inside = underFuneralFloor(feet) ? 1 : 0;
    this.candlelit += (inside - this.candlelit) * Math.min(1, dt * 1.5);
    const rooms = inHouseRooms(feet) ? 1 : 0;
    this.housebound += (rooms - this.housebound) * Math.min(1, dt * 1.2);
    const k = this.candlelit;
    // Up in the rooms the house's own dark look (HOUSE_LOOK, Nov 24, 2026); the two never
    // hold at once (one is under the floor, the other on it).
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

  /**
   * Decoration does not stop the interaction ray: the offerings, candles, cloth, fences
   * and plants are dense merged meshes, and testing the ray against their triangles
   * every frame cost 40 ms at the altar. What hangs under an `interact_` node stays.
   * The house's Nov 24 dressing (`M_hr_`: Sok's photograph on the altar, the bathroom)
   * is decoration too.
   */
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

  /**
   * Small things are not drawn from far off: a matchbox, a hinge or a jar's lid 14 m
   * away is a pixel in the dark, and the house's props were a thousand draw calls seen
   * from the lane (Nov 20, 2026). Flames, skinned figures and merged batches are left.
   */
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
    // The fog's halos: Sora's lamp and the four flames that reach her most, chosen afresh
    // each frame (VillageLights.chooseFogLights).
    this.lights.fogLights = game.pipeline.fog?.lights ?? null;
    // A dark monsoon night: the lamp's warm pool, flames and lightning, and little
    // else; adapted eyes find shapes a few metres out. The exposure cap still keeps
    // extinguishing the lamp meaningfully darker.
    game.atmosphere.baseExposure = VILLAGE_NIGHT.baseExposure;
    game.atmosphere.maxExposure = VILLAGE_NIGHT.maxExposure;
    game.atmosphere.nightSightIntensity = VILLAGE_NIGHT.nightSightIntensity;
    game.atmosphere.nightSight.range = VILLAGE_NIGHT.nightSightRange;
    // Night sight is the dark around her, not a light on what she holds: the cold
    // lantern stays a dark shape at her side.
    game.atmosphere.nightSight.excludedMeshes.push(...this.vigil.heldMeshes, ...game.hands.meshes);
    // Rain mist: distance fades into a dim blue-black, still just lighter than the
    // trees, so their silhouettes stand against it.
    const fog = game.pipeline.fog;
    if (fog) {
      fog.density = VILLAGE_NIGHT.fogDensity;
      // The previews' rain mist stands 16 m deep over the farm, veiling the sky as well
      // as the trees: it thins slowly with height.
      fog.heightFalloff = 0.09;
      fog.ambient.set(...VILLAGE_NIGHT.fogAmbient);
      fog.setMistPockets(GROUND_MIST);
      fog.setMistField(forestMistField(game.scene));
    } else {
      game.scene.fogDensity = VILLAGE_NIGHT.fogDensity;
      game.scene.fogColor.set(...VILLAGE_NIGHT.fogAmbient);
      // No volumetric fog on the Low preset: drifting wisps placed by the same mist map.
      this.lowMist = new LowGroundMist(game.scene, GROUND_MIST, spawnForestWisp, 160);
    }
    // A monsoon night: the wind is heard at full strength, but nothing drawn moves
    // in it. Trees, palms, grass and hanging cloth stand still (the user, Nov 20:
    // "Everything is so shake. Don't make interact with the wind").
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
    // The farmstead (Nov 22, 2026): the walker in the hall over the funeral, the hunter
    // among the jars under the back block.
    this.walker.models.pose(new Vector3(0, 2.5, -14.5), new Vector3(0, 0, -1), 0);
    this.walker.models.walker.setEnabled(true);
    this.hunt.models.pose(new Vector3(2.6, 0, -26.5), new Vector3(0, 0, -1), 0, 1);
    try {
      // Where Sora will look: the track from the gate, the yard and the house, the funeral
      // under it, the hall, the long corridor, Sok's study, the kitchen house, the barn.
      await warmSceneViews(this.game.scene, this.game.camera, [
        { eye: new Vector3(0, 1.58, 42), target: new Vector3(-1, 1.3, 26) },
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
    this.windAudio.update(dt);
    this.funeralRoom.update(dt, this.lights.tentLevel);
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
    this.early.update(dt);
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
    this.scares.update(dt, this.early.active || this.apparitions.active);
    this.krasue.update(dt, this.early.active || this.apparitions.active);
    this.watcher.update(dt, !this.early.active && !this.apparitions.active);
    // Story scripts get first refusal on the soundscape every frame.
    this.forest.update(
      dt,
      this.night.threatSilence > 0 || this.apparitions.active || this.early.active,
    );
    this.soundscape.update(dt);
    // Act 1's dread swells under the silence and while the Neak Ta shows itself.
    // The vigil passage keeps its own tension bed, so the score stays out of it.
    const pressure =
      game.flags.get("ep1.act2.started", false) || this.early.active
        ? 0
        : Math.max(
            this.apparitions.dread * 0.55,
            this.night.threatSilence * 0.4,
            (this.forest?.silence ?? 0) * 0.35,
            (this.saveShrine?.silence ?? 0) * 0.4,
          );
    this.score.pressure(pressure);
    // The forest holds its breath when the night falls silent for a threat, and
    // gusts harder as the dread climbs.
    game.wind.calm = Math.max(
      this.night.threatSilence,
      this.forest?.silence ?? 0,
      this.saveShrine?.silence ?? 0,
    );
    game.wind.tension = Math.max(pressure, this.apparitions.dread * 0.6);
    this.score.update(dt);
    this.night.update(dt);
    this.lights.lookingAt = game.interaction.distance;
    this.lights.update(dt);
    // The rain slants with the wind; the box moves upwind so it still falls round her.
    const wind = game.wind,
      slant = wind.at(eye.x, eye.z) * 0.32;
    this.rain.system.direction1.set(wind.dirX * slant - 0.05, -1, wind.dirZ * slant + 0.02);
    this.rain.system.direction2.set(wind.dirX * slant + 0.01, -1, wind.dirZ * slant + 0.08);
    this.rainAt.set(eye.x - wind.dirX * slant * 4, eye.y + 7, eye.z - wind.dirZ * slant * 4);
    // Unlit streaks: faint in the dark, warmed a little by the lamp, white in lightning.
    // Pale streaks against the dark, as the previews' rain (warmed by the lamp, white in
    // lightning); at a quarter of this they were never seen.
    this.rain.light(this.lights.storm.level, this.lights.lampFlame * 0.25, 0.55);
    // The lightning lights the mist: the whole night goes a pale blue-grey for the flash.
    // Under the funeral the mist's own blue-grey falls away (FUNERAL_LOOK.mist); the
    // flash still shows between the stilts.
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
    if (flashing && !this.wasFlashing)
      setTimeout(
        () => {
          if (!this.thunderSounds.length || this.resolution.active) return;
          // A different roll each time, from a different part of the sky:
          // the far ones lower and longer, the near ones sharp.
          const sound = this.thunderSounds[Math.floor(Math.random() * this.thunderSounds.length)];
          const a = Math.random() * Math.PI * 2,
            far = 25 + Math.random() * 55;
          sound.spatial.position = new Vector3(
            eye.x + Math.cos(a) * far,
            eye.y + 20 + far * 0.3,
            eye.z + Math.sin(a) * far,
          );
          sound.playbackRate = 1.1 - (far / 80) * 0.25;
          sound.play();
        },
        1500 + Math.random() * 2500,
      );
    this.wasFlashing = flashing;
  }

  private dawn(): void {
    const g = this.game;
    this.rain.system.stop();
    this.rainSound?.stop();
    for (const sound of this.thunderSounds) sound.stop();
    this.score.pressure(0);
    // The storm has blown itself out: a light morning air through the palms.
    g.wind.base = 0.16;
    g.wind.calm = 0;
    g.wind.tension = 0;
    this.night.stopForDawn();
    this.soundscape.stop();
    this.forest.stop();
    this.krasue.stop();
    this.lowMist?.stop();
    this.sky.dome.setEnabled(false);
    this.lights.dawn();
    g.scene.clearColor.set(...DAWN_LOOK.clearColor, 1);
    g.atmosphere.baseExposure = DAWN_LOOK.baseExposure;
    g.atmosphere.maxExposure = DAWN_LOOK.maxExposure;
    g.atmosphere.nightSightIntensity = DAWN_LOOK.nightSightIntensity;
    g.atmosphere.nightSight.range = DAWN_LOOK.nightSightRange;
    g.pipeline.main.imageProcessing.exposure = DAWN_LOOK.baseExposure;
    if (g.pipeline.fog) {
      g.pipeline.fog.mistStrength = 0;
      // Dawn burns the night mist off to a thin haze over the fields.
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

  /** Placeholder rain and thunder until the recordings exist. */
  private async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) {
      await this.investigation.makeSounds();
      return;
    }
    const rate = audio.context.sampleRate;
    const eye = this.game.camera.globalPosition;
    // Two takes, one per ear: rain all round, not a point at the listener's head.
    this.rainSound = await audio.sound(
      "rain",
      audio.buffer([villageRain(rate, seededRandom(3)), villageRain(rate, seededRandom(5))], rate),
      "ambience",
      // Under everything else: the frogs, the chant and Sora's steps carry over it.
      0.32,
    );
    this.rainSound.loop = true;
    this.rainSound.play();
    for (const [k, seed] of [4, 8, 9].entries())
      this.thunderSounds.push(
        await audio.spatialSound(
          `thunder_${k}`,
          audio.buffer(thunder(rate, seededRandom(seed)), rate),
          "ambience",
          eye,
          { minDistance: 40 },
        ),
      );
    this.score = new DreadScore(audio);
    this.score.onSting = (kind, volume) =>
      stingGust(this.game.wind, kind, volume, this.score.lead(kind));
    await this.score.load();
    this.apparitions.score = this.score;
    this.saveShrine.score = this.score;
    this.scares.score = this.score;
    await this.night.makeSounds();
    await this.soundscape.makeSounds();
    await this.forest.makeSounds();
    await this.windAudio.makeSounds();
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
    await this.krasue.makeSounds();
    await this.saveShrine.makeSounds();
  }
}

/**
 * The mosquito nets: sheer, as in the approved previews. Exported as a cut-out of fine
 * threads, they thinned to nothing once mipmapped and the nets vanished; drawn instead
 * as one see-through layer of the net's own colour.
 */
function sheerNets(materials: readonly Material[]): void {
  for (const material of materials) {
    if (!(material instanceof PBRMaterial) || !/mosquito_net/.test(material.name)) continue;
    material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    material.useAlphaFromAlbedoTexture = false;
    material.alpha = 0.26;
    material.backFaceCulling = false;
  }
}
