import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { CreateDisc } from "@babylonjs/core/Meshes/Builders/discBuilder";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { DreadScore } from "@/audio/DreadScore";
import type { Area } from "@/core/areaLoader";
import type { Game } from "@/core/Game";
import { applySkyShelter } from "@/render/skyShelter";
import type { Lightning } from "@/render/weather/Lightning";
import { HOUSE_SHELTER } from "../data/shelter";
import {
  BACK_DOOR_FIGURE,
  JAR_WATER,
  JAR_WATER_RADIUS,
  KITCHEN_DOOR,
  SCARE_JAR,
  WASHING_FIGURE,
  backDoorTrigger,
  kitchenTrigger,
  loftTrigger,
  scareFlag,
  washingTrigger,
  type ScareId,
} from "../data/scares";
import { Preay } from "../entities/Preay";

/** How long a lunging figure stays at the hit before she is gone (s). */
const HOLD = 0.16;
/** The black water's dark, glossy surface. */
const WATER = new Color3(0.008, 0.009, 0.008);

interface Cue {
  at: number;
  play: () => void;
}

interface Run {
  id: ScareId;
  time: number;
  cues: Cue[];
  /** Moves the scare on; true once it is over. */
  step: (t: number, dt: number) => boolean;
}

/**
 * Episode 1's five jump scares (data/scares.ts; the user approved them from Cycles
 * previews, Nov 24, 2026). Each fires once per playthrough and lasts under a second at
 * its hit: the score's shock, a lightning flash and the picture's jolt. None hurts Sora
 * or takes her control.
 *
 * - kitchen (Act I): the betel leaves taken, Sora turns to the kitchen house's east
 *   door and the Preay is coming through it, arms out, onto her face.
 * - washing (Act II): the sheet on the washing board has sat up over her; it lunges.
 * - backdoor (Act II): at the long corridor's nailed door her hands smash through the
 *   planks, her face in the hole; the door stays broken, and shut.
 * - jar (Act III): the jar with the first key piece is black water; Sok's face rises
 *   out of it to look up at her, then sinks, and the water goes back to dark.
 * - loft (Act III): at the top of the barn loft ladder she is there, face to face.
 */
export class JumpScares {
  score: DreadScore | null = null;
  private preay!: Preay;
  private props: AssetContainer | null = null;
  private sheet: TransformNode | null = null;
  private brokenDoor: TransformNode | null = null;
  private corpse: TransformNode | null = null;
  private water: Mesh | null = null;
  private waterMaterial: PBRMaterial | null = null;
  private run: Run | null = null;
  private readonly washSheet: AbstractMesh[];
  private readonly wholeDoor: AbstractMesh[];
  private readonly forward = new Vector3();

  constructor(
    private readonly game: Game,
    area: Area,
    private readonly preayAsset: AssetContainer,
    private readonly storm: Lightning,
  ) {
    const meshes = area.container.meshes;
    this.washSheet = meshes.filter((m) => /^wash_room_sheet(\.|_|$)/.test(m.name));
    this.wholeDoor = meshes.filter((m) => /^door_back_(leaf|nail)/.test(m.name));
  }

  /** True while a scare is playing: other scripts leave the screen to it. */
  get active(): boolean {
    return this.run !== null;
  }

  async load(): Promise<void> {
    const scene = this.game.scene;
    this.preay = new Preay(this.preayAsset, "scare_preay", 0.4);
    this.preay.setEnabled(false);
    const base = import.meta.env.BASE_URL;
    const [props, corpse] = await Promise.all([
      LoadAssetContainerAsync(`${base}assets/ep1/scares.glb`, scene),
      LoadAssetContainerAsync(`${base}assets/ep1/sok_corpse.glb`, scene),
    ]);
    props.addAllToScene();
    this.props = props;
    // The house's rooms: no sky reaches them (as for the village's own materials).
    applySkyShelter([...props.materials, ...corpse.materials], HOUSE_SHELTER);
    for (const m of [...props.materials, ...corpse.materials])
      if (m instanceof PBRMaterial) m.maxSimultaneousLights = 8;
    const node = (name: string) => props.transformNodes.find((n) => n.name === name) ?? null;
    // The sheet sits at the glTF's origin; hang it from a node of its own to move it,
    // keeping its world placement (and the importer's mirror).
    const sheet = node("scare_sheet");
    if (sheet) {
      this.sheet = new TransformNode("scare_sheet_anchor", scene);
      sheet.setParent(this.sheet, true);
      this.sheet.setEnabled(false);
    }
    this.brokenDoor = node("scare_door_broken");
    this.brokenDoor?.setEnabled(false);
    for (const m of props.meshes) m.isPickable = false;

    // Sok's face for the jar: only his body and his clouded eyes.
    corpse.addAllToScene();
    const keep = /^sok_anatomical_(body|eye_[LR])/;
    const anchor = new TransformNode("scare_jar_sok", scene);
    for (const m of corpse.meshes) {
      m.isPickable = false;
      if (keep.test(m.name)) m.setParent(anchor, true);
      else if (m.getTotalVertices() > 0) m.setEnabled(false);
    }
    anchor.setEnabled(false);
    this.corpse = anchor;
    this.water = CreateDisc(
      "scare_jar_water",
      { radius: JAR_WATER_RADIUS, tessellation: 40, sideOrientation: Mesh.DOUBLESIDE },
      scene,
    );
    this.water.rotation.x = Math.PI / 2;
    this.water.isPickable = false;
    const water = new PBRMaterial("scare_jar_water", scene);
    water.albedoColor = WATER;
    water.metallic = 0;
    water.roughness = 0.06;
    water.alpha = 1;
    // It goes back to dark at the end (fades), so it blends.
    water.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    water.maxSimultaneousLights = 8;
    this.water.material = this.waterMaterial = water;
    this.water.setEnabled(false);

    // A scare already had stays had: the sheet gone from the board, the door broken.
    if (this.done("washing")) for (const m of this.washSheet) m.setEnabled(false);
    if (this.done("backdoor")) this.breakDoor();

    if (import.meta.env.DEV) (window as unknown as { scares: JumpScares }).scares = this;
  }

  /** Each frame; `quiet` while another scene owns the screen (the early stealth, an apparition). */
  update(dt: number, quiet: boolean): void {
    const run = this.run;
    if (run) {
      run.time += dt;
      for (const cue of run.cues.filter((c) => c.at <= run.time)) {
        run.cues.splice(run.cues.indexOf(cue), 1);
        cue.play();
      }
      if (run.step(run.time, dt)) {
        this.game.flags.set(scareFlag(run.id), true);
        this.run = null;
      }
      return;
    }
    const g = this.game;
    if (quiet || g.cutscene || g.hiding || !g.player) return;
    const feet = g.player.feet;
    g.camera.getDirectionToRef(Vector3.Forward(), this.forward);
    const flags = g.flags;
    const actTwo = flags.get("ep1.act2.started", false);
    if (
      !this.done("kitchen") &&
      kitchenTrigger(feet, this.forward, flags.get("ep1.pickup.interact_betel_leaves", false))
    )
      this.fire("kitchen");
    else if (!this.done("washing") && washingTrigger(feet, this.forward, actTwo))
      this.fire("washing");
    else if (!this.done("backdoor") && backDoorTrigger(feet, this.forward, actTwo))
      this.fire("backdoor");
    else if (
      !this.done("loft") &&
      loftTrigger(g.camera.globalPosition, g.player.climbing, flags.get("ep1.act3.started", false))
    )
      this.fire("loft");
  }

  /** The hunt opened a jar (UnderHouseHunt): the first key piece's is the scare's. */
  jarOpened(id: string, root: TransformNode, contents: TransformNode): void {
    if (id !== SCARE_JAR || this.done("jar") || this.run) return;
    this.startJar(root, contents);
  }

  /** Plays one now, whatever the triggers say (development: filming each). */
  fire(id: ScareId): void {
    if (this.run) return;
    if (id === "kitchen") this.startKitchen();
    else if (id === "washing") this.startWashing();
    else if (id === "backdoor") this.startBackDoor();
    else if (id === "loft") this.startLoft();
  }

  dispose(): void {
    this.preay?.dispose();
    this.props?.dispose();
  }

  private done(id: ScareId): boolean {
    return this.game.flags.get(scareFlag(id), false);
  }

  private eye(): Vector3 {
    return this.game.camera.globalPosition.clone();
  }

  /** The score's shock landing at `at`, the flash just before it, the jolt on it, the ears ringing after. */
  private hit(at: number, volume = 1): Cue[] {
    const lead = this.score?.lead("shock") ?? 0;
    return [
      { at: Math.max(0, at - lead), play: () => this.score?.sting("shock", volume) },
      { at: Math.max(0, at - 0.04), play: () => this.storm.strike() },
      { at, play: () => this.game.atmosphere.scare() },
      { at: at + 0.5, play: () => this.score?.ring() },
    ];
  }

  /**
   * The Preay comes from `from` to `to` (her feet) in `seconds`, faster and faster, her
   * arms coming up (the reach clip from `clip` to its end), looking into Sora's eyes.
   */
  private lunge(id: ScareId, from: Vector3, to: Vector3, seconds: number, clip = 0.4): void {
    const preay = this.preay,
      eye = this.eye();
    preay.place(from, Math.atan2(eye.x - from.x, eye.z - from.z));
    preay.watch(eye);
    preay.perform("reach", clip);
    preay.standStill(0);
    preay.setPresence(1);
    const at = new Vector3();
    this.run = {
      id,
      time: 0,
      cues: this.hit(seconds),
      step: (t, dt) => {
        const k = Math.min(1, t / seconds);
        Vector3.LerpToRef(from, to, k * k, at);
        preay.root.position.copyFrom(at);
        preay.perform("reach", clip + (1 - clip) * k);
        preay.standStill(dt);
        if (t < seconds + HOLD) return false;
        preay.release();
        preay.setEnabled(false);
        return true;
      },
    };
  }

  /** J1: she is coming in by the east door, arms out, and is on Sora's face. */
  private startKitchen(): void {
    const feet = this.game.player.feet.clone();
    const way = KITCHEN_DOOR.subtract(feet);
    way.y = 0;
    const far = way.length();
    way.normalize();
    const from = feet.add(way.scale(Math.min(2.4, Math.max(1.4, far - 0.2))));
    // The hit is the J1 preview's frame: her feet 0.75 m from Sora's.
    const to = feet.add(way.scale(0.75));
    from.y = to.y = feet.y;
    this.lunge("kitchen", from, to, 0.32);
  }

  /** J3: her hands smash through the nailed planks and her face is in the hole. */
  private startBackDoor(): void {
    this.breakDoor();
    const to = BACK_DOOR_FIGURE.clone();
    const from = to.add(new Vector3(0, 0, -0.35));
    this.lunge("backdoor", from, to, 0.22, 0.5);
  }

  /** J5: at the top of the loft ladder she is there, a hand's breadth further, face to face. */
  private startLoft(): void {
    const eye = this.eye();
    const ahead = this.game.camera.getDirection(Vector3.Forward());
    ahead.y = 0;
    ahead.normalize();
    // The hit is the J5 preview's frame: her feet 0.62 m ahead of Sora's eye.
    const from = eye.add(ahead.scale(0.95));
    const to = eye.add(ahead.scale(0.62));
    from.y = to.y = eye.y - 1.47;
    this.lunge("loft", from, to, 0.2, 0.7);
  }

  /** J2: the sheet sits up off the board, over her, and lunges. */
  private startWashing(): void {
    const sheet = this.sheet;
    if (!sheet) return;
    for (const m of this.washSheet) m.setEnabled(false);
    const eye = this.eye();
    const rest = WASHING_FIGURE.clone();
    const way = eye.subtract(rest);
    way.y = 0;
    way.normalize();
    const yaw = Math.atan2(way.x, way.z);
    // It lunges a step's length: the hit is the J2 preview's frame, sat up about 1.2 m away.
    const end = rest.add(way.scale(0.25));
    const RISE = 0.22,
      LUNGE = 0.2;
    sheet.position.copyFrom(rest);
    sheet.rotation.set(-1.0, yaw, 0);
    sheet.setEnabled(true);
    this.run = {
      id: "washing",
      time: 0,
      cues: this.hit(RISE + LUNGE),
      step: (t) => {
        const up = Math.min(1, t / RISE);
        // Sitting up: from lying back low on the board to upright, quick at the end.
        sheet.rotation.x = -1.0 * (1 - up * up);
        const k = Math.max(0, Math.min(1, (t - RISE) / LUNGE));
        Vector3.LerpToRef(rest, end, k * k, sheet.position);
        sheet.position.y = rest.y - 0.45 * (1 - up);
        if (t < RISE + LUNGE + HOLD) return false;
        sheet.setEnabled(false);
        return true;
      },
    };
  }

  /** J4: black water in the jar; Sok's face rises out of it, looks up at her, and sinks. */
  private startJar(jar: TransformNode, contents: TransformNode): void {
    const corpse = this.corpse,
      water = this.water,
      waterMaterial = this.waterMaterial;
    if (!corpse || !water || !waterMaterial) return;
    jar.computeWorldMatrix(true);
    const mouth = jar.getAbsolutePosition().add(new Vector3(0, JAR_WATER, 0));
    const eye = this.eye();
    const toward = eye.subtract(mouth);
    toward.y = 0;
    toward.normalize();
    // Lying, his head is to +x and his face up (+y). Tipped 40 degrees from upright, as
    // in the preview: the crown leans away from her, the face looks up into her eyes.
    const tip = (40 * Math.PI) / 180;
    const head = toward.scale(-Math.cos(tip)).add(Vector3.Up().scale(Math.sin(tip)));
    const face = toward.scale(Math.sin(tip)).add(Vector3.Up().scale(Math.cos(tip)));
    const side = Vector3.Cross(head, face);
    const turn = new Matrix();
    Matrix.FromXYZAxesToRef(head, face, side, turn);
    corpse.position.setAll(0);
    corpse.rotationQuaternion = Quaternion.FromRotationMatrix(turn);
    corpse.computeWorldMatrix(true);
    // The eyes just over the water, the face in the middle of the jar's mouth.
    const eyes = corpse
      .getChildMeshes()
      .filter((m) => /eye_[LR]/.test(m.name))
      .map((m) => {
        m.computeWorldMatrix(true);
        return m.getBoundingInfo().boundingBox.centerWorld.clone();
      });
    const at = eyes.length
      ? eyes.reduce((a, b) => a.addInPlace(b), Vector3.Zero()).scaleInPlace(1 / eyes.length)
      : Vector3.Zero();
    const top = mouth.subtract(at).add(toward.scale(-0.04));
    top.y = mouth.y + 0.015 - at.y;
    const low = top.add(new Vector3(0, -0.3, 0));
    water.position.copyFrom(mouth);
    waterMaterial.alpha = 1;
    water.setEnabled(true);
    contents.setEnabled(false);
    corpse.position.copyFrom(low);
    const LIFT = 0.35,
      RISE = 0.25,
      STAY = 0.9,
      SINK = 0.6,
      CLEAR = 0.8;
    this.run = {
      id: "jar",
      time: 0,
      cues: this.hit(LIFT + RISE, 0.9),
      step: (t) => {
        corpse.setEnabled(t > LIFT && t < LIFT + RISE + STAY + SINK);
        const rise = Math.max(0, Math.min(1, (t - LIFT) / RISE));
        const sink = Math.max(0, Math.min(1, (t - LIFT - RISE - STAY) / SINK));
        const up = 1 - (1 - rise) * (1 - rise); // eases out: up fast, then still
        Vector3.LerpToRef(low, top, up * (1 - sink * sink), corpse.position);
        const clear = Math.max(0, Math.min(1, (t - LIFT - RISE - STAY - SINK) / CLEAR));
        waterMaterial.alpha = 1 - clear;
        if (clear < 1) return false;
        water.setEnabled(false);
        contents.setEnabled(true);
        return true;
      },
    };
  }

  /** The whole back door away, the smashed one in its place. */
  private breakDoor(): void {
    for (const m of this.wholeDoor) m.setEnabled(false);
    this.brokenDoor?.setEnabled(true);
  }
}
