import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { MorphTargetManager } from "@babylonjs/core/Morph/morphTargetManager";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { ParticleSystem } from "@babylonjs/core/Particles/particleSystem";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { CreateGround } from "@babylonjs/core/Meshes/Builders/groundBuilder";
import { loadArea, type Area } from "../../../core/AreaLoader";
import type { Game } from "../../../core/Game";
import type { PagodaSoundscape } from "../PagodaSoundscape";
import { CinematicDirector } from "./CinematicDirector";
import { LibraryCollapse } from "./LibraryCollapse";
import {
  HARVEST_SCENE,
  FAMINE_SCENE,
  SOPHAL_SCENE,
  BARGAIN_SCENE,
  COLLAPSE_SCENE,
  DAWN_SCENE,
  PHOTO_SCENE,
} from "./scripts";
import { RelicCraft } from "../../ep1/act3/RelicCraft";
import "@babylonjs/core/Particles/particleSystemComponent";

/** Authored humans and Episode 1's surface kit, all staged in the existing world. */
export class PagodaCinematics {
  area!: Area;
  readonly director: CinematicDirector;
  collapse!: LibraryCollapse;
  private people: { root: TransformNode; managers: MorphTargetManager[] }[] = [];
  private monk: MorphTargetManager[] = [];
  private village!: TransformNode;
  private rice!: TransformNode;
  private fireLogs!: TransformNode;
  private baskets: TransformNode[] = [];
  private fire!: ParticleSystem;
  private fireLight: PointLight;
  private memoryMode: "hidden" | "harvest" | "famine" = "hidden";
  private time = 0;
  private readonly props: RelicCraft;
  private box!: TransformNode;
  private lid!: TransformNode;
  private earth!: TransformNode;
  private photo!: TransformNode;
  constructor(
    private readonly game: Game,
    private readonly sounds: PagodaSoundscape,
  ) {
    this.director = new CinematicDirector(game);
    this.fireLight = new PointLight("harvest_fire_light", new Vector3(80, 0.8, 3), game.scene);
    this.fireLight.diffuse = Color3.FromHexString("#FFD4A0");
    this.fireLight.intensity = 0;
    this.fireLight.range = 12;
    this.fireLight.shadowEnabled = false;
    this.fireLight.renderPriority = 8;
    this.props = new RelicCraft(game.scene);
  }
  async load(): Promise<void> {
    const g = this.game;
    this.area = await loadArea(g.scene, "ep2", "ep2_cinematics", {
      keep: [
        /^harvest_/,
        /^sophal_living/,
        /^memory_basket_/,
        /^pagoda_ghost/,
        /^pagoda_watcher_/,
        /^pagoda_goddess/,
      ],
      cellSize: 8,
    });
    const find = (name: string) =>
      g.scene.getTransformNodeByName(name) ?? g.scene.getMeshByName(name);
    const need = (name: string) => {
      const n = find(name);
      if (!n) throw new Error("Cinematic node missing: " + name);
      return n;
    };
    this.village = need("harvest_village");
    this.rice = need("harvest_rice");
    this.fireLogs = need("harvest_fire");
    this.baskets = g.scene.transformNodes.filter((n) => /^memory_basket_/.test(n.name));
    const managers = (root: TransformNode) => [
      ...new Set(
        [root, ...root.getChildMeshes()]
          .filter((m): m is Mesh => m instanceof Mesh)
          .flatMap((m) => (m.morphTargetManager ? [m.morphTargetManager] : [])),
      ),
    ];
    for (let i = 0; i < 4; i++) {
      const root = need("harvest_person_" + i);
      if (root.rotationQuaternion) root.rotation.copyFrom(root.rotationQuaternion.toEulerAngles());
      root.rotationQuaternion = null;
      this.people.push({ root, managers: managers(root) });
      for (const mesh of root.getChildMeshes()) mesh.isPickable = false;
    }
    const monk = need("sophal_living");
    this.monk = managers(monk);
    for (const manager of [...this.monk, ...this.people.flatMap((p) => p.managers)])
      manager.numMaxInfluencers = Math.min(4, manager.numTargets);
    for (const mesh of this.area.container.meshes) {
      mesh.isPickable = false;
      if (mesh.material instanceof PBRMaterial) mesh.material.maxSimultaneousLights = 8;
    }
    this.collapse = new LibraryCollapse(g);
    this.makeFire();
    this.makeDawnProps();
    this.setMemory("hidden");
  }
  begin(): void {
    this.game.addFlameLights(this.fireLight);
  }
  private makeFire(): void {
    const s = this.game.scene,
      texture = new DynamicTexture("harvest_fire_particle", 64, s, false);
    const c = texture.getContext(),
      gradient = c.createRadialGradient(32, 40, 0, 32, 32, 31);
    gradient.addColorStop(0, "rgba(255,245,204,1)");
    gradient.addColorStop(0.35, "rgba(255,172,76,.8)");
    gradient.addColorStop(1, "rgba(145,62,23,0)");
    c.fillStyle = gradient;
    c.fillRect(0, 0, 64, 64);
    texture.hasAlpha = true;
    texture.update();
    const p = (this.fire = new ParticleSystem("harvest_fire", 80, s));
    p.particleTexture = texture;
    p.emitter = new Vector3(80, 0.15, 3);
    p.minEmitBox.set(-0.2, 0, -0.2);
    p.maxEmitBox.set(0.2, 0.04, 0.2);
    p.direction1.set(-0.08, 1, -0.08);
    p.direction2.set(0.08, 1, 0.08);
    p.minEmitPower = 0.5;
    p.maxEmitPower = 1.2;
    p.minLifeTime = 0.5;
    p.maxLifeTime = 1;
    p.minSize = 0.12;
    p.maxSize = 0.3;
    p.emitRate = 0;
    p.color1 = new Color4(1, 0.83, 0.5, 0.8);
    p.color2 = new Color4(1, 0.5, 0.16, 0.6);
    p.colorDead = new Color4(0.25, 0.1, 0.04, 0);
    p.start();
  }
  private makeDawnProps(): void {
    const c = this.props,
      bronze = c.mat("dawn_betel_silver", "#928e80", 0.55, 0.8),
      earth = c.surface("dawn_pact_earth", "#433a29", "skin");
    this.box = c.root("dawn_betel_box", [-12, 0.27, 7.34]);
    for (const x of [-0.17, 0.17])
      c.box(this.box, "betel_side", [0.025, 0.12, 0.24], [x, 0.06, 0], bronze);
    for (const z of [-0.12, 0.12])
      c.box(this.box, "betel_end", [0.34, 0.12, 0.025], [0, 0.06, z], bronze);
    c.box(this.box, "betel_base", [0.34, 0.02, 0.24], [0, 0, 0], bronze);
    this.lid = c.root("dawn_box_lid", [0, 0.13, -0.12], this.box);
    c.box(this.lid, "silver_lid", [0.37, 0.025, 0.27], [0, 0, 0.12], bronze);
    this.earth = c.root("dawn_returned_earth", [0, 0.025, 0], this.box);
    for (let i = 0; i < 16; i++)
      c.sphere(
        this.earth,
        "old_earth",
        [0.035, 0.02, 0.035],
        [((i % 4) - 1.5) * 0.065, 0, (Math.floor(i / 4) - 1.5) * 0.045],
        earth,
      );
    const paper = c.surface("clinic_photo_paper", "#c5b79d", "paper");
    this.photo = c.root("clinic_photo_in_lining", [0, 0.02, 0], this.box);
    c.box(this.photo, "clinic_photo", [0.23, 0.003, 0.175], [0, 0, 0], paper);
    const print = new PBRMaterial("clinic_contact_print", this.game.scene);
    print.albedoTexture = new Texture(
      `${import.meta.env.BASE_URL}assets/ep2/clinic_photo.png`,
      this.game.scene,
    );
    print.albedoColor = Color3.FromHexString("#C5B092").toLinearSpace();
    print.roughness = 0.92;
    print.metallic = 0;
    const face = CreateGround(
      "clinic_photo_emulsion",
      { width: 0.213, height: 0.16 },
      this.game.scene,
    );
    face.parent = this.photo;
    face.position.y = 0.002;
    face.material = print;
    face.isPickable = false;
    this.box.setEnabled(false);
  }
  private morph(managers: readonly MorphTargetManager[], weights: Record<string, number>): void {
    for (const m of managers) {
      for (let i = 0; i < m.numTargets; i++) {
        const t = m.getTarget(i);
        t.influence = weights[t.name] ?? 0;
      }
    }
  }
  setMemory(mode: "hidden" | "harvest" | "famine"): void {
    this.memoryMode = mode;
    this.village.setEnabled(mode !== "hidden");
    this.rice.setEnabled(mode === "harvest");
    this.fireLogs.setEnabled(mode !== "hidden");
    for (const basket of this.baskets) basket.setEnabled(mode === "harvest");
    for (const [i, p] of this.people.entries()) {
      p.root.setEnabled(mode === "harvest" || (mode === "famine" && i === 0));
      if (mode === "famine") this.morph(p.managers, { famine: 1 });
    }
    this.fire.emitRate = mode === "harvest" ? 45 : 0;
    this.fireLight.intensity = mode === "harvest" ? 10 : 0;
    this.sounds.memory(mode);
  }
  update(dt: number): void {
    this.time += dt;
    this.morph(this.monk, { listen: 0.35 + 0.15 * Math.sin(this.time * 0.7) });
    if (this.memoryMode === "harvest") {
      for (const [i, p] of this.people.entries()) {
        const phase = this.time * 1.7 + i * 0.8,
          a = 0.5 + 0.5 * Math.sin(phase);
        this.morph(p.managers, {
          left: a * 0.7,
          right: (1 - a) * 0.7,
          clap: Math.max(0, Math.sin(phase * 0.5)) * 0.25,
        });
        p.root.rotation.y = Math.sin(phase * 0.5) * 0.05;
      }
      this.fireLight.intensity =
        10 * (0.9 + 0.07 * Math.sin(this.time * 8.3) + 0.03 * Math.sin(this.time * 13.1));
    }
    this.sounds.cinematicPause(document.hidden || (this.director.active && this.director.isPaused));
  }
  async sophal(): Promise<void> {
    const g = this.game,
      feet = g.player.feet,
      yaw = g.player.yaw,
      pitch = g.player.pitch;
    g.player.teleport(new Vector3(-18, 0.22, 13.7), Math.PI);
    g.player.pitch = 0.19;
    try {
      await this.director.play(SOPHAL_SCENE, (frame) => {
        g.player.yaw =
          Math.PI + (frame.reducedMotion ? 0 : Math.sin(frame.progress * Math.PI) * 0.035);
      });
    } finally {
      g.player.teleport(feet, yaw);
      g.player.pitch = pitch;
    }
  }
  async harvest(): Promise<void> {
    const g = this.game;
    this.setMemory("harvest");
    g.player.teleport(new Vector3(80, 0.08, 9), Math.PI);
    g.player.pitch = -0.035;
    await g.fade.to(0, 1.2);
    try {
      await this.director.play(HARVEST_SCENE, (frame) => {
        g.player.yaw =
          Math.PI + (frame.reducedMotion ? 0 : Math.sin(frame.progress * Math.PI * 2) * 0.07);
      });
    } finally {
      await g.fade.to(1, 0.7);
      this.setMemory("famine");
    }
    g.player.teleport(new Vector3(80, 0.08, 9), Math.PI);
    g.player.pitch = 0.03;
    await g.fade.to(0, 1.2);
    await this.director.play(FAMINE_SCENE);
  }
  async bargain(): Promise<void> {
    await this.director.play(BARGAIN_SCENE);
  }
  async breakLibrary(): Promise<void> {
    this.setMemory("hidden");
    this.collapse.start();
    const g = this.game;
    g.player.pitch = -0.28;
    this.sounds.crash();
    await this.director.play(COLLAPSE_SCENE, (frame) => {
      this.collapse.pose(frame.elapsed);
      g.player.pitch = -0.28 + (frame.reducedMotion ? 0 : Math.sin(frame.elapsed * 8) * 0.006);
    });
    this.collapse.restoreBroken();
    g.player.yaw = 0;
    g.player.pitch = 0;
  }
  async dawn(): Promise<void> {
    const g = this.game;
    this.box.setEnabled(true);
    this.photo.setEnabled(false);
    g.player.teleport(new Vector3(-12, 0.08, 8.3), Math.PI);
    g.player.pitch = 0.7;
    this.sounds.dawnBell();
    await this.director.play(DAWN_SCENE, (frame) => {
      this.lid.rotation.x = -Math.min(1, frame.elapsed / 2) * 1.8;
      this.earth.position.y = 0.025 - Math.min(1, Math.max(0, (frame.elapsed - 3) / 4)) * 0.18;
      this.earth.rotation.z = Math.min(0.6, Math.max(0, frame.elapsed - 3) * 0.12);
    });
    this.earth.setEnabled(false);
    this.lid.rotation.x = -1.8;
    this.photo.setEnabled(true);
  }
  async photograph(): Promise<void> {
    const g = this.game;
    g.player.teleport(new Vector3(-12, 0.08, 8.3), Math.PI);
    g.player.pitch = 0.8;
    this.box.setEnabled(true);
    this.photo.setEnabled(true);
    this.earth.setEnabled(false);
    this.lid.rotation.x = -1.8;
    await this.director.play(PHOTO_SCENE, (frame) => {
      const k = Math.min(1, frame.elapsed / 3);
      this.photo.position.set(0.08 * k, 1.0 * k, 0.62 * k);
      this.photo.rotation.y = 0.2 * k;
    });
  }
}
