import type { Game } from "../../core/Game";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreatePlane } from "@babylonjs/core/Meshes/Builders/planeBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { addStaticBox } from "../../core/Physics";

/** A physical writing folio, available only in safe play; success follows the actual write. */
export class SavePoint {
  private busy = false;
  constructor(
    game: Game,
    readonly id: string,
    position: Vector3,
    label: string,
    save: () => Promise<unknown>,
    available: () => boolean = () => true,
  ) {
    const scene = game.scene;
    const root = new TransformNode(id, scene);
    root.position.copyFrom(position);
    if (position.y < 0.2) {
      const stand = CreateBox(`${id}_stand`, { width: 0.7, height: 0.76, depth: 0.46 }, scene);
      stand.position.copyFrom(position.add(new Vector3(0, 0.38, 0)));
      const wood = new PBRMaterial(`${id}_wood`, scene);
      wood.albedoColor = Color3.FromHexString("#4b3828").toLinearSpace();
      wood.roughness = 0.8;
      stand.material = wood;
      addStaticBox(stand, "teak");
      root.position.y += 0.79;
    }
    const folio = CreateBox(`${id}_folio`, { width: 0.25, height: 0.025, depth: 0.18 }, scene);
    folio.parent = root;
    const cover = new PBRMaterial(`${id}_leather`, scene);
    cover.albedoColor = Color3.FromHexString("#35443a").toLinearSpace();
    cover.roughness = 0.8;
    folio.material = cover;
    const page = CreatePlane(`${id}_page`, { width: 0.23, height: 0.16 }, scene);
    page.parent = root;
    page.position.y = 0.013;
    page.rotation.x = Math.PI / 2;
    page.rotation.y = Math.PI;
    const tex = new DynamicTexture(`${id}_writing`, { width: 512, height: 384 }, scene, true);
    const c = tex.getContext() as CanvasRenderingContext2D;
    c.fillStyle = "#ddd0ab";
    c.fillRect(0, 0, 512, 384);
    c.fillStyle = "#353c31";
    c.textAlign = "center";
    c.font = "bold 44px serif";
    c.fillText("RECORD PROGRESS", 256, 145);
    c.font = "30px serif";
    c.fillText(label, 256, 207);
    c.fillText("A SAFE PLACE", 256, 281);
    tex.update();
    const paper = new PBRMaterial(`${id}_paper`, scene);
    paper.albedoTexture = tex;
    paper.emissiveTexture = tex;
    paper.emissiveColor.set(0.075, 0.065, 0.04);
    paper.roughness = 1;
    paper.backFaceCulling = false;
    page.material = paper;
    // A small votive marks a safe writing place even with Sora's lamp out.
    const wax = new PBRMaterial(`${id}_wax`, scene);
    wax.albedoColor = Color3.FromHexString("#c4a879").toLinearSpace();
    wax.roughness = 0.9;
    const candle = CreateCylinder(
      `${id}_candle`,
      { diameter: 0.055, height: 0.09, tessellation: 20 },
      scene,
    );
    candle.parent = root;
    candle.position.set(-0.2, 0.045, 0);
    candle.material = wax;
    const flame = CreateSphere(`${id}_flame`, { diameter: 0.021, segments: 8 }, scene);
    flame.parent = root;
    flame.position.set(-0.2, 0.116, 0);
    flame.scaling.y = 2.4;
    const glow = new PBRMaterial(`${id}_glow`, scene);
    glow.unlit = true;
    glow.emissiveColor.set(2.8, 1.25, 0.24);
    flame.material = glow;
    const light = new PointLight(`${id}_reading_candle`, new Vector3(-0.2, 0.15, 0), scene);
    light.parent = root;
    light.diffuse.set(1, 0.68, 0.32);
    light.intensity = 0.12;
    light.range = 1.5;
    light.includedOnlyMeshes = [folio, page, candle];
    candle.isPickable = false;
    flame.isPickable = false;
    game.interaction.add(id, root, { outline: false });
    game.bus.on("interact:focus", ({ id: focus }) => {
      if (focus === id) game.hints.show("hint.savePoint", 8);
    });
    game.bus.on("interact:use", ({ id: used }) => {
      if (used !== id || this.busy || game.cutscene || game.threatActive || !available()) return;
      this.busy = true;
      void save()
        .then(() => game.hints.show("note.checkpointSaved", 5))
        .catch(() => game.hints.show("note.saveFailed", 8))
        .finally(() => {
          this.busy = false;
        });
    });
  }
}
