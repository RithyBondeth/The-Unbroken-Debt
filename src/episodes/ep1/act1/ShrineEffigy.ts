import type { Scene } from "@babylonjs/core/scene";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { realiseInstances } from "../../../core/AreaLoader";

const templates = new WeakMap<Scene, AssetContainer>();

/** An original timber carving with incised fingers, hollow sockets, a split
 * brow and integral folded robes. Its neck is a rigid wooden joint. */
export class ShrineEffigy {
  readonly root: TransformNode;
  private readonly head: TransformNode;

  static async prepare(scene: Scene): Promise<void> {
    if (templates.has(scene)) return;
    const asset = await LoadAssetContainerAsync(
      `${import.meta.env.BASE_URL}assets/ep1/phra_phum_effigy.glb`,
      scene,
    );
    realiseInstances(asset);
    asset.removeAllFromScene();
    for (const material of asset.materials)
      if (material instanceof PBRMaterial) material.maxSimultaneousLights = 8;
    templates.set(scene, asset);
    scene.onDisposeObservable.addOnce(() => asset.dispose());
  }

  constructor(scene: Scene, parent: TransformNode) {
    const template = templates.get(scene);
    if (!template)
      throw new Error("Prepare the carved wooden effigy before building the spirit house");
    this.root = new TransformNode("phra_phum_carved_ancestor", scene);
    this.root.parent = parent;
    this.root.position.set(0, 1.29, -0.1);
    const copy = template.instantiateModelsToScene((name) => `phra_phum_${name}`, false, {
      doNotInstantiate: true,
    });
    for (const node of copy.rootNodes) node.parent = this.root;
    const head = this.root
      .getDescendants()
      .find((node) => node.name === "phra_phum_effigy_head_joint");
    if (!(head instanceof TransformNode))
      throw new Error("The wooden effigy requires its carved head and neck pivot");
    this.head = head;
    for (const mesh of this.root.getChildMeshes()) {
      mesh.receiveShadows = true;
      mesh.isPickable = true;
    }
    this.update(0);
  }

  update(attention: number): void {
    this.head.rotationQuaternion = null;
    this.head.rotation.y = -0.32 * (1 - attention);
    this.head.rotation.z = attention * 0.045;
  }
}
