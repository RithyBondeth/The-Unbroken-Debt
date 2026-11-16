import type { Scene } from "@babylonjs/core/scene";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { AnimationGroup } from "@babylonjs/core/Animations/animationGroup";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Node } from "@babylonjs/core/node";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { realiseInstances } from "@/core/areaLoader";

const scratchL = new Matrix();
const scratchP = new Matrix();

/** Recomputes a node's world matrix from the top of its hierarchy down. */
function refresh(node: TransformNode): void {
  const chain: TransformNode[] = [];
  for (let n: Node | null = node; n; n = n.parent) if (n instanceof TransformNode) chain.unshift(n);
  for (const n of chain) n.computeWorldMatrix(true);
}

/**
 * Turns a node about the world's vertical by `angle` (positive turns +Z towards +X),
 * after its own rotation: whatever mirrors and turns its parents carry.
 */
function turnAboutWorldUp(node: TransformNode, angle: number): void {
  refresh(node);
  const parent = node.parent instanceof TransformNode ? node.parent : null;
  node.rotationQuaternion ??= Quaternion.FromEulerVector(node.rotation);
  Matrix.FromQuaternionToRef(node.rotationQuaternion, scratchL);
  // Local' = Local · Parent · Turn · Parent⁻¹ (rotation parts only; Babylon is row-vector).
  scratchP.copyFrom(parent ? parent.getWorldMatrix() : Matrix.IdentityReadOnly);
  scratchP.setTranslationFromFloats(0, 0, 0);
  const result = scratchL
    .multiply(scratchP)
    .multiply(Matrix.RotationY(angle))
    .multiply(scratchP.clone().invert());
  Quaternion.FromRotationMatrixToRef(result, node.rotationQuaternion);
  node.rotationQuaternion.normalize();
}

/**
 * A skinned figure moving on motion capture, posed straight from a clock: `pose(clip, s)`
 * shows exactly the frame `s` seconds into that clip, so a scripted scare that is skipped
 * into, paused or replayed always looks the same. Facing +Z at its root, feet on the ground.
 * The glTF loads once (`load`); each figure gets its own skeleton and clips.
 */
export class MocapFigure {
  readonly root: TransformNode;
  readonly meshes: AbstractMesh[] = [];
  private readonly clips = new Map<string, AnimationGroup>();
  private current: AnimationGroup | null = null;
  private readonly neck: TransformNode | null;
  private readonly head: TransformNode | null;
  private faceAxis: Vector3 | null = null;

  /** Loads a figure's asset; give the result to `new MocapFigure` for each figure. */
  static async load(scene: Scene, url: string): Promise<AssetContainer> {
    const asset = await LoadAssetContainerAsync(url, scene);
    realiseInstances(asset);
    asset.removeAllFromScene();
    for (const material of asset.materials)
      if (material instanceof PBRMaterial) material.maxSimultaneousLights = 8;
    scene.onDisposeObservable.addOnce(() => asset.dispose());
    return asset;
  }

  constructor(asset: AssetContainer, name: string) {
    const scene = asset.scene;
    this.root = new TransformNode(name, scene);
    const copy = asset.instantiateModelsToScene((source) => `${name}_${source}`, false, {
      doNotInstantiate: true,
    });
    for (const node of copy.rootNodes) node.parent = this.root;
    for (const group of copy.animationGroups) {
      group.stop();
      this.clips.set(group.name.replace(`${name}_`, ""), group);
    }
    for (const mesh of this.root.getChildMeshes(false)) {
      mesh.isPickable = false;
      mesh.receiveShadows = true;
      // A skinned body's rest bounds do not cover its poses: never cull it in the act.
      mesh.alwaysSelectAsActiveMesh = true;
      // Authoring colours ride along in the file; they are not paint.
      mesh.useVertexColors = false;
      this.meshes.push(mesh);
    }
    const bone = (bone: string) =>
      this.root
        .getChildTransformNodes(false)
        .find((n) => n.name === `${name}_${bone}` || n.name.endsWith(`_${bone}`)) ?? null;
    this.neck = bone("neck03");
    this.head = bone("head");
    // Which of the head bone's own axes the face looks along, from the rest pose (+Z).
    if (this.head) {
      refresh(this.head);
      const world = this.head.getWorldMatrix();
      let best = -Infinity;
      for (const axis of [
        Vector3.Right(),
        Vector3.Left(),
        Vector3.Up(),
        Vector3.Down(),
        Vector3.Forward(),
        Vector3.Backward(),
      ]) {
        const along = Vector3.TransformNormal(axis, world).normalize().z;
        if (along > best) {
          best = along;
          this.faceAxis = axis;
        }
      }
    }
  }

  /** Clip names, as authored. */
  get clipNames(): string[] {
    return [...this.clips.keys()];
  }

  /** Shows the frame `seconds` into `clip`, wrapping round a looped clip. */
  pose(clip: string, seconds: number, loop = true): void {
    const group = this.clips.get(clip);
    if (!group) return;
    if (this.current !== group) {
      this.current?.stop();
      group.start(loop, 1, group.from, group.to, false);
      group.pause();
      this.current = group;
    }
    const fps = group.targetedAnimations[0]?.animation.framePerSecond ?? 60;
    const span = group.to - group.from;
    let frame = seconds * fps;
    frame = loop ? ((frame % span) + span) % span : Math.max(0, Math.min(span, frame));
    group.goToFrame(group.from + frame);
  }

  /**
   * Turns the head (and a little of the neck) towards a world point, by up to `amount` of
   * the way, as far as a neck can, from wherever the performance has it looking. Call
   * after `pose`.
   */
  lookAt(target: Vector3, amount: number): void {
    const head = this.head;
    if (amount <= 0 || !head || !this.faceAxis) return;
    refresh(head);
    const face = Vector3.TransformNormal(this.faceAxis, head.getWorldMatrix());
    const to = target.subtract(head.getAbsolutePosition());
    face.y = 0;
    to.y = 0;
    if (to.lengthSquared() < 1e-6 || face.lengthSquared() < 1e-6) return;
    face.normalize();
    to.normalize();
    const angle =
      Math.max(
        -1.4,
        Math.min(1.4, Math.atan2(face.z * to.x - face.x * to.z, Vector3.Dot(face, to))),
      ) * amount;
    for (const [node, share] of [
      [this.neck, 0.35],
      [head, 0.65],
    ] as const) {
      if (!node) continue;
      turnAboutWorldUp(node, angle * share);
    }
  }

  setEnabled(on: boolean): void {
    if (this.root.isEnabled() !== on) this.root.setEnabled(on);
  }

  dispose(): void {
    for (const group of this.clips.values()) group.dispose();
    this.root.dispose(false, false);
  }
}
