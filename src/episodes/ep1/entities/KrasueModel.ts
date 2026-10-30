import type { Scene } from "@babylonjs/core/scene";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { Bone } from "@babylonjs/core/Bones/bone";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Space } from "@babylonjs/core/Maths/math.axis";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { realiseInstances } from "../../../core/AreaLoader";
import { KrasueDynamics } from "./KrasueDynamics";
import { krasueScreamMouth } from "./KrasueExpression";
import type { MorphTarget } from "@babylonjs/core/Morph/morphTarget";

const assets = new WeakMap<Scene, AssetContainer>();

interface AnimatedBone {
  bone: Bone;
  rest: Quaternion;
  parentBasis: Matrix;
  inverseBasis: Matrix;
  kind: "hair" | "gut" | "organ";
  index: number;
  joint: number;
}

/** Closed, skinned GLB: sculpted head, dense layered hair and real viscera.
 * All movement is skeletal; no camera-facing surface or image silhouette.
 */
export class KrasueModel {
  readonly root: TransformNode;
  readonly meshes: AbstractMesh[];
  readonly light: PointLight;
  readonly ready = true;
  private readonly bones: AnimatedBone[] = [];
  private readonly offset = Quaternion.Identity();
  private readonly rotation = Quaternion.Identity();
  private readonly localOffset = Quaternion.Identity();
  private readonly offsetMatrix = Matrix.Identity();
  private readonly localMatrix = Matrix.Identity();
  private readonly localOffsetMatrix = Matrix.Identity();
  private readonly mouthTargets: MorphTarget[] = [];
  mouthOpen = 0;
  private readonly scale = new Vector3();
  private readonly heart: TransformNode | null;
  private readonly restHeart: Vector3 | null;
  private yaw = 0;
  private lastTime = -1;
  private readonly dynamics: KrasueDynamics;

  static async prepare(scene: Scene): Promise<void> {
    if (assets.has(scene)) return;
    const container = await LoadAssetContainerAsync(
      `${import.meta.env.BASE_URL}assets/ep1/krasue/krasue-creature.glb`,
      scene,
    );
    realiseInstances(container);
    assets.set(scene, container);
    scene.onDisposeObservable.addOnce(() => container.dispose());
  }

  constructor(scene: Scene) {
    const asset = assets.get(scene);
    if (!asset) throw new Error("Prepare the Krasue GLB before constructing its encounter");
    this.root = new TransformNode("krasue", scene);
    // The village's glTF conversion maps Blender +Y to Babylon -Z. Normalize
    // the imported body to +Z before applying the shared flight/head heading.
    const facing = new TransformNode("krasue_asset_facing", scene);
    facing.parent = this.root;
    facing.rotation.y = Math.PI;
    asset.addAllToScene();
    for (const node of [...asset.transformNodes, ...asset.meshes])
      if (!node.parent) node.parent = facing;
    this.meshes = asset.meshes.filter((m) => m.getTotalVertices() > 0);
    for (const mesh of this.meshes) {
      mesh.isPickable = false;
      mesh.alwaysSelectAsActiveMesh = true;
      const targets = mesh.morphTargetManager;
      if (targets)
        for (let i = 0; i < targets.numTargets; i++) {
          const target = targets.getTarget(i);
          if (target.name === "Scream") this.mouthTargets.push(target);
        }
    }
    for (const material of asset.materials) {
      if (!(material instanceof PBRMaterial)) continue;
      material.maxSimultaneousLights = 8;
      material.useAlphaFromAlbedoTexture = false;
      material.transparencyMode = PBRMaterial.PBRMATERIAL_OPAQUE;
      material.emissiveColor.set(0, 0, 0);
      material.enableSpecularAntiAliasing = true;
      if (material.name === "M_krasue_face") material.albedoColor.set(0.65, 0.68, 0.64);
    }
    for (const skeleton of asset.skeletons)
      for (const bone of skeleton.bones) {
        const hair = /^krasue_hair_(\d+)_(\d+)$/.exec(bone.name);
        const gut = /^krasue_gut_(\d+)_(\d+)$/.exec(bone.name);
        const organ = /^krasue_organs_(\d+)$/.exec(bone.name);
        if (!hair && !gut && !organ) continue;
        // Joint axes follow each curved strand. Convert root-space bending
        // into its parent's rest basis so every strand trails the flight.
        const parentBasis =
          bone.getTransformNode()?.parent?.computeWorldMatrix(true).clone() ?? Matrix.Identity();
        this.bones.push({
          bone,
          rest: bone.getRotationQuaternion(Space.LOCAL).clone(),
          parentBasis,
          inverseBasis: Matrix.Invert(parentBasis),
          kind: hair ? "hair" : gut ? "gut" : "organ",
          index: Number((hair ?? gut)?.[1] ?? 0),
          joint: Number((hair ?? gut)?.[2] ?? organ?.[1] ?? 0),
        });
      }
    this.heart =
      asset.transformNodes.find((n) => n.name === "krasue_heart") ??
      asset.meshes.find((m) => m.name === "krasue_heart") ??
      null;
    this.restHeart = this.heart?.scaling.clone() ?? null;
    this.dynamics = new KrasueDynamics(this.bones);
    this.light = new PointLight("krasue_moonlit_face", new Vector3(-0.4, 0.55, 0.8), scene);
    this.light.parent = this.root;
    this.light.diffuse.set(0.55, 0.65, 0.61);
    this.light.specular.set(0.1, 0.12, 0.11);
    this.light.intensity = 1.05;
    this.light.range = 3.2;
    this.light.renderPriority = 10;
    this.light.includedOnlyMeshes = this.meshes;
    const rim = new PointLight("krasue_moon_rim", new Vector3(0.45, -0.5, -0.65), scene);
    rim.parent = this.root;
    rim.diffuse.set(0.33, 0.43, 0.46);
    rim.specular.set(0.28, 0.34, 0.36);
    rim.intensity = 0.7;
    rim.range = 3;
    rim.renderPriority = 10;
    rim.includedOnlyMeshes = this.meshes;
    this.root.setEnabled(false);
  }

  /** Flight heading reveals cheeks and profile; an alerted head turns toward Sora. */
  pose(
    position: Vector3,
    target: Vector3,
    time: number,
    attack: boolean,
    flight?: Vector3,
    watching = false,
    screamAge = -1,
  ): void {
    const gap = this.lastTime < 0 || time < this.lastTime ? 1 : time - this.lastTime;
    const dt = Math.min(0.1, gap);
    this.lastTime = time;
    this.root.position.copyFrom(position);
    const facing =
      attack || watching || !flight || flight.lengthSquared() < 0.0001
        ? target.subtract(position)
        : flight;
    const desired = Math.atan2(facing.x, facing.z);
    this.yaw +=
      Math.atan2(Math.sin(desired - this.yaw), Math.cos(desired - this.yaw)) *
      (1 - Math.exp(-dt * (attack ? 12 : 3.5)));
    this.root.rotation.set(Math.sin(time * 1.3) * 0.035, this.yaw, Math.sin(time * 0.83) * 0.075);
    this.dynamics.update(gap, position, this.yaw, time);
    for (let i = 0; i < this.bones.length; i++) {
      const { bone, rest, parentBasis, inverseBasis } = this.bones[i],
        angle = this.dynamics.angles[i];
      Quaternion.RotationYawPitchRollToRef(0, angle.pitch, angle.roll, this.offset);
      // Matrix conjugation preserves glTF's handedness reflection. Extracting
      // only a quaternion from that basis would reverse the trailing direction.
      this.offset.toRotationMatrix(this.offsetMatrix);
      parentBasis.multiplyToRef(this.offsetMatrix, this.localMatrix);
      this.localMatrix.multiplyToRef(inverseBasis, this.localOffsetMatrix);
      this.localOffsetMatrix.decompose(undefined, this.localOffset);
      this.localOffset.multiplyToRef(rest, this.rotation);
      const node = bone.getTransformNode();
      // glTF bones are driven by their linked transform nodes each frame.
      if (node) {
        if (!node.rotationQuaternion) node.rotationQuaternion = this.rotation.clone();
        else node.rotationQuaternion.copyFrom(this.rotation);
      } else bone.setRotationQuaternion(this.rotation, Space.LOCAL);
    }
    this.mouthOpen = krasueScreamMouth(screamAge);
    for (const target of this.mouthTargets) target.influence = this.mouthOpen;
    if (this.heart && this.restHeart) {
      this.scale.copyFrom(this.restHeart).scaleInPlace(1 + Math.sin(time * 7.8) * 0.025);
      this.heart.scaling.copyFrom(this.scale);
    }
  }
}
