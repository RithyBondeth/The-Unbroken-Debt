import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { CreateGround } from "@babylonjs/core/Meshes/Builders/groundBuilder";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Color3, Color4 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { EventBus } from "./EventBus";
import { Flags } from "./Flags";
import type { GameEvents } from "./events";

/**
 * Owns the engine, the scene, the shared event bus and flags, and the render loop.
 * The scene built here is a placeholder until the Phase 1 spikes replace it.
 */
export class Game {
  readonly bus = new EventBus<GameEvents>();
  readonly flags = new Flags(this.bus);
  readonly scene: Scene;

  constructor(private readonly engine: WebGPUEngine) {
    this.scene = new Scene(engine);
    this.buildPlaceholderScene();
  }

  start(): void {
    this.engine.runRenderLoop(() => this.scene.render());
  }

  private buildPlaceholderScene(): void {
    const scene = this.scene;
    scene.clearColor = new Color4(0.09, 0.07, 0.06, 1);

    const camera = new UniversalCamera("player", new Vector3(0, 1.58, -4), scene);
    camera.setTarget(new Vector3(0, 1, 0));
    camera.attachControl(true);
    camera.minZ = 0.05;

    const ambient = new HemisphericLight("ambient", new Vector3(0, 1, 0), scene);
    ambient.intensity = 0.08;

    // Stand-in for Sora's kerosene lamp (Art Bible: #FF9A3C, useful light 6–8 m).
    const lamp = new PointLight("lamp", new Vector3(0.3, 1.4, -3), scene);
    lamp.diffuse = Color3.FromHexString("#FF9A3C");
    lamp.range = 8;
    lamp.intensity = 1.2;

    // Tree-shaken imports have no default material, so placeholders get an explicit one.
    const grey = new StandardMaterial("placeholder", scene);
    grey.diffuseColor = new Color3(0.55, 0.52, 0.48);
    grey.specularColor = Color3.Black();

    const ground = CreateGround("ground", { width: 24, height: 18 }, scene);
    ground.material = grey;

    const coffin = CreateBox("coffin-placeholder", { width: 0.7, height: 0.6, depth: 2 }, scene);
    coffin.position.y = 0.3;
    coffin.material = grey;
  }
}
