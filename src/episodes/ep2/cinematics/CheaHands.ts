import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { decodeHandAsset } from "../../../player/HandAsset";
import { HandRig } from "../../../player/HandRig";
import type { Game } from "../../../core/Game";
import type { PagodaEquipment } from "../PagodaEquipment";
/** Separately authored old male anatomy and photographic skin, on Episode 1's actual grip rig. */
export class CheaHands {
  readonly left: HandRig;
  readonly right: HandRig;
  private readonly fill: PointLight;
  active = false;
  private time = 0;
  constructor(private readonly game: Game) {
    this.left = new HandRig(game.scene, "chea_left_hand", -1);
    this.right = new HandRig(game.scene, "chea_right_hand", 1);
    this.left.root.parent = this.right.root.parent = game.camera;
    this.fill = new PointLight("chea_hand_fill", new Vector3(-0.4, 0.3, 0.1), game.scene);
    this.fill.parent = game.camera;
    this.fill.diffuse = new Color3(1, 0.84, 0.65);
    this.fill.intensity = 0.32;
    this.fill.shadowEnabled = false;
    game.scene.onDisposeObservable.addOnce(() => this.dispose());
  }
  async load(): Promise<void> {
    const g = this.game,
      base = `${import.meta.env.BASE_URL}assets/ep2/`;
    const response = await fetch(base + "chea_hand.mesh");
    if (!response.ok) throw new Error("Chea’s authored hands could not load");
    const asset = decodeHandAsset(await response.arrayBuffer());
    const skin = new Texture(base + "chea_hand_skin.png", g.scene),
      normal = new Texture(base + "chea_hand_normal.png", g.scene),
      rough = new Texture(base + "chea_hand_roughness.png", g.scene);
    normal.gammaSpace = rough.gammaSpace = false;
    for (const tex of [skin, normal, rough])
      tex.anisotropicFilteringLevel = g.preset.name === "low" ? 4 : 8;
    for (const rig of [this.left, this.right]) {
      rig.install(asset, skin, normal, rough);
      rig.root.scaling.setAll(0.85);
      for (const mesh of rig.meshes) {
        mesh.renderingGroupId = 1;
        mesh.isPickable = false;
        mesh.alwaysSelectAsActiveMesh = true;
        if (mesh.material instanceof PBRMaterial) {
          if (mesh === rig.skin) {
            mesh.material.albedoColor.set(0.62, 0.46, 0.33);
            mesh.material.roughness = 0.9;
          } else mesh.material.albedoColor.set(0.27, 0.22, 0.15);
        }
      }
    }
    this.fill.includedOnlyMeshes = [...this.left.meshes, ...this.right.meshes];
    for (const light of g.scene.lights)
      if (light !== this.fill) light.excludedMeshes.push(...this.left.meshes, ...this.right.meshes);
    this.left.root.setEnabled(false);
    this.right.root.setEnabled(false);
  }
  update(dt: number, equipment: PagodaEquipment): void {
    this.time += dt;
    const g = this.game,
      show =
        this.active &&
        !g.cutscene &&
        !g.notebook.isOpen &&
        !g.satchel.isOpen &&
        !g.sketchbook?.isVisible;
    this.left.root.setEnabled(show);
    this.right.root.setEnabled(false);
    this.fill.intensity = show ? 0.32 : 0;
    if (!show) return;
    this.left.root.position.copyFrom(g.hands.left.position);
    this.left.root.rotation.copyFrom(g.hands.left.rotation);
    // Weak, unhurried tremor follows the hand, not the camera.
    this.left.root.rotation.z +=
      Math.sin(this.time * 5.8) * 0.009 + Math.sin(this.time * 11.3) * 0.003;
    this.left.update(dt, "lamp");
    equipment.held.root.setEnabled(true);
  }
  dispose(): void {
    this.left.dispose();
    this.right.dispose();
    this.fill.dispose();
  }
}
