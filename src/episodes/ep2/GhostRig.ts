import type { Scene } from "@babylonjs/core/scene";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import type { AnimationGroup } from "@babylonjs/core/Animations/animationGroup";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { Color3 } from "@babylonjs/core/Maths/math.color";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { realiseInstances } from "../../core/AreaLoader";

/** In the glTF's own axes, which is the frame its bones' rotations are written in. */
const FORWARD = new Vector3(0, 0, 1);
const UP = new Vector3(0, 1, 0);
const scratch = new Quaternion();

/** One clip's share of the body, easing towards where it should be. */
interface Layer {
  group: AnimationGroup;
  weight: number;
  target: number;
  playing: boolean;
}

/**
 * A skinned, motion-captured figure from its own glTF (tools/ep2/build-ghosts.py). The
 * asset loads once; each figure gets its own skeleton and clips, sharing the geometry
 * and textures. Facing +Z at its root's origin, feet on the ground.
 */
export class GhostRig {
  readonly root: TransformNode;
  readonly meshes: AbstractMesh[] = [];
  private readonly layers = new Map<string, Layer>();
  private readonly nodes = new Map<string, TransformNode>();
  private readonly axes = new Map<string, Vector3>();

  /**
   * Loads the asset; give the result to `new GhostRig` for each figure. `tints` multiply
   * materials by name, so a pale figure does not burn out under the player's lantern.
   */
  static async load(
    scene: Scene,
    file: string,
    tints: Record<string, Color3> = {},
  ): Promise<AssetContainer> {
    const asset = await LoadAssetContainerAsync(
      `${import.meta.env.BASE_URL}assets/ep2/${file}.glb`,
      scene,
    );
    realiseInstances(asset);
    asset.removeAllFromScene();
    for (const material of asset.materials)
      if (material instanceof PBRMaterial) {
        material.maxSimultaneousLights = 8;
        const tint = tints[material.name];
        if (tint) material.albedoColor = tint;
      }
    scene.onDisposeObservable.addOnce(() => asset.dispose());
    return asset;
  }

  constructor(asset: AssetContainer, name: string) {
    const made = asset.instantiateModelsToScene((n) => `${name}_${n}`, false, {
      doNotInstantiate: true,
    });
    this.root = new TransformNode(name, asset.scene);
    for (const node of made.rootNodes) {
      node.parent = this.root;
      for (const child of node.getDescendants(false))
        if (child instanceof TransformNode)
          this.nodes.set(child.name.slice(name.length + 1), child);
      for (const mesh of node.getChildMeshes(false)) {
        mesh.isPickable = false;
        // A skinned body moves far from its rest bounds, and there are only a few parts.
        mesh.alwaysSelectAsActiveMesh = true;
        if (mesh instanceof Mesh) this.meshes.push(mesh);
      }
    }
    this.learnAxes();
    for (const group of made.animationGroups) {
      group.stop();
      group.loopAnimation = true;
      this.layers.set(group.name.slice(name.length + 1), {
        group,
        weight: 0,
        target: 0,
        playing: false,
      });
    }
  }

  /** A bone's node, to turn on top of the clips (see onAfterAnimations). */
  bone(name: string): TransformNode | undefined {
    return this.nodes.get(name);
  }

  /**
   * Turns a bone by `angle` about one of the figure's own axes as they were at rest: call
   * after the animations have run for the frame, so the turn adds to the clip.
   */
  turn(name: string, axis: "forward" | "up", angle: number): void {
    const node = this.nodes.get(name);
    if (!node?.rotationQuaternion || angle === 0) return;
    const local = this.axes.get(name + axis);
    if (!local) return;
    Quaternion.RotationAxisToRef(local, angle, scratch);
    node.rotationQuaternion.multiplyInPlace(scratch);
  }

  /** Starts a clip from its beginning, at full weight at once, for a scare. */
  start(name: string, speed = 1, loop = false): void {
    for (const [key, layer] of this.layers) {
      if (key === name) continue;
      layer.target = 0;
      layer.weight = 0;
      if (layer.playing) layer.group.stop();
      layer.playing = false;
    }
    const layer = this.layers.get(name);
    if (!layer) return;
    if (layer.playing) layer.group.stop();
    layer.group.start(loop, speed, layer.group.from, layer.group.to);
    layer.group.setWeightForAllAnimatables(1);
    layer.weight = layer.target = 1;
    layer.playing = true;
  }

  /** Each axis the turns above need, in a bone's own frame, read while it is at rest. */
  private learnAxes(): void {
    for (const [name, node] of this.nodes) {
      let q = (node.rotationQuaternion ?? Quaternion.Identity()).clone();
      for (let p = node.parent; p instanceof TransformNode && !p.name.endsWith("__root__");) {
        q = (p.rotationQuaternion ?? Quaternion.Identity()).multiply(q);
        p = p.parent;
      }
      const inverse = Quaternion.Inverse(q);
      this.axes.set(name + "forward", FORWARD.applyRotationQuaternion(inverse));
      this.axes.set(name + "up", UP.applyRotationQuaternion(inverse));
    }
  }

  /** How far through its loop a clip is, 0 to 1. */
  phase(name: string): number {
    const layer = this.layers.get(name);
    if (!layer?.playing) return 0;
    const from = layer.group.from,
      to = layer.group.to;
    const frame = layer.group.animatables[0]?.masterFrame ?? from;
    return to > from ? (frame - from) / (to - from) : 0;
  }

  /** Eases onto clip `name`, played at `speed` times its recorded rate. */
  play(name: string, speed = 1): void {
    for (const [key, layer] of this.layers) layer.target = key === name ? 1 : 0;
    const layer = this.layers.get(name);
    if (!layer) return;
    layer.group.speedRatio = speed;
    if (!layer.playing) {
      layer.group.start(true, speed);
      layer.group.setWeightForAllAnimatables(layer.weight);
      layer.playing = true;
    }
  }

  /** Moves the crossfade on; `fade` is how many seconds a full change takes. */
  update(dt: number, fade = 0.35): void {
    const step = fade > 0 ? dt / fade : 1;
    for (const layer of this.layers.values()) {
      if (layer.weight === layer.target) continue;
      const d = layer.target - layer.weight;
      layer.weight += Math.sign(d) * Math.min(Math.abs(d), step);
      layer.group.setWeightForAllAnimatables(layer.weight);
      if (layer.weight === 0 && layer.playing) {
        layer.group.stop();
        layer.playing = false;
      }
    }
  }

  /** Holds or releases every clip, for menus and readers. */
  pause(paused: boolean): void {
    for (const layer of this.layers.values())
      if (layer.playing) {
        if (paused) layer.group.pause();
        else layer.group.play(true);
      }
  }
}
