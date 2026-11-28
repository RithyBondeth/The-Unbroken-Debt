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
const scratchRot = new Matrix();

/** Recomputes a node's world matrix from the top of its hierarchy down. */
function refresh(node: TransformNode): void {
  const chain: TransformNode[] = [];
  for (let n: Node | null = node; n; n = n.parent) if (n instanceof TransformNode) chain.unshift(n);
  for (const n of chain) n.computeWorldMatrix(true);
}

/** Rotates `node` around a world-space axis (right-handed axis) after its own rotation. */
function turnAboutWorldAxis(node: TransformNode, axis: Vector3, angle: number): void {
  if (Math.abs(angle) < 1e-5) return;
  refresh(node);
  const parent = node.parent instanceof TransformNode ? node.parent : null;
  node.rotationQuaternion ??= Quaternion.FromEulerVector(node.rotation);
  Matrix.FromQuaternionToRef(node.rotationQuaternion, scratchL);
  scratchP.copyFrom(parent ? parent.getWorldMatrix() : Matrix.IdentityReadOnly);
  scratchP.setTranslationFromFloats(0, 0, 0);
  Matrix.RotationAxisToRef(axis, angle, scratchRot);
  const result = scratchL
    .multiply(scratchP)
    .multiply(scratchRot)
    .multiply(scratchP.clone().invert());
  Quaternion.FromRotationMatrixToRef(result, node.rotationQuaternion);
  node.rotationQuaternion.normalize();
}

function turnAboutWorldUp(node: TransformNode, angle: number): void {
  turnAboutWorldAxis(node, Vector3.UpReadOnly, angle);
}

export interface HorrorDistortion {
  /** Broken-neck lateral roll (radians; e.g. 0.65 = ~37° snap tilt). */
  neckRoll?: number;
  /** Extra yaw twist (radians; enables unnatural 110°+ over-shoulder head turns). */
  neckYaw?: number;
  /** Forward/back head pitch (radians). */
  neckPitch?: number;
  /** 0–1 predatory hunched spine/shoulder lean forward. */
  hunch?: number;
  /** 0–1 high-frequency Jacob's-Ladder / P.T. convulsive shudder. */
  twitch?: number;
  /** 0–1 blend toward active locomotion (fades idle arm/weight sway so walk mocap leads cleanly). */
  walkBlend?: number;
  /** Running clock in seconds for organic breathing, sway, and convulsion oscillation. */
  time?: number;
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
  private readonly channels: {
    target: TransformNode;
    property: "rotationQuaternion" | "position" | "scaling";
  }[] = [];
  private readonly held: (Quaternion | Vector3)[] = [];
  private readonly neckLow: TransformNode | null;
  private readonly neckMid: TransformNode | null;
  private readonly neck: TransformNode | null;
  private readonly head: TransformNode | null;
  private readonly spineUpper: TransformNode | null;
  private readonly spineChest: TransformNode | null;
  private readonly spineMid: TransformNode | null;
  private readonly spineLower: TransformNode | null;
  private readonly clavL: TransformNode | null;
  private readonly clavR: TransformNode | null;
  private readonly upperArmL: TransformNode | null;
  private readonly upperArmR: TransformNode | null;
  private readonly lowerArmL: TransformNode | null;
  private readonly lowerArmR: TransformNode | null;
  private readonly wristL: TransformNode | null;
  private readonly wristR: TransformNode | null;
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
    const seen = new Set<string>();
    for (const group of copy.animationGroups) {
      group.start(true, 1, group.from, group.to, false);
      group.pause();
      this.clips.set(group.name.replace(`${name}_`, ""), group);
      for (const { target, animation } of group.targetedAnimations) {
        const property = animation.targetProperty;
        if (!(target instanceof TransformNode)) continue;
        if (property !== "rotationQuaternion" && property !== "position" && property !== "scaling")
          continue;
        const key = `${target.uniqueId}:${property}`;
        if (seen.has(key)) continue;
        seen.add(key);
        this.channels.push({ target, property });
        this.held.push(property === "rotationQuaternion" ? new Quaternion() : new Vector3());
      }
    }
    for (const mesh of this.root.getChildMeshes(false)) {
      mesh.isPickable = false;
      mesh.receiveShadows = true;
      mesh.alwaysSelectAsActiveMesh = true;
      mesh.useVertexColors = false;
      this.meshes.push(mesh);
    }
    const bone = (boneName: string) =>
      this.root
        .getChildTransformNodes(false)
        .find((n) => n.name === `${name}_${boneName}` || n.name.endsWith(`_${boneName}`)) ?? null;
    this.neckLow = bone("neck01");
    this.neckMid = bone("neck02");
    this.neck = bone("neck03");
    this.head = bone("head");
    this.spineUpper = bone("spine01");
    this.spineChest = bone("spine02");
    this.spineMid = bone("spine03");
    this.spineLower = bone("spine04");
    this.clavL = bone("clavicle.L");
    this.clavR = bone("clavicle.R");
    this.upperArmL = bone("upperarm01.L");
    this.upperArmR = bone("upperarm01.R");
    this.lowerArmL = bone("lowerarm01.L");
    this.lowerArmR = bone("lowerarm01.R");
    this.wristL = bone("wrist.L");
    this.wristR = bone("wrist.R");

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

  /** Head bone transform node (for attaching faint eye glints or sound anchors). */
  get headNode(): TransformNode | null {
    return this.head;
  }

  /** Clip names, as authored. */
  get clipNames(): string[] {
    return [...this.clips.keys()];
  }

  /** Shows the frame `seconds` into `clip`, wrapping round a looped clip. */
  pose(clip: string, seconds: number, loop = true): void {
    const group = this.clips.get(clip);
    if (!group) return;
    const fps = group.targetedAnimations[0]?.animation.framePerSecond ?? 60;
    const span = group.to - group.from;
    let frame = seconds * fps;
    frame = loop ? ((frame % span) + span) % span : Math.max(0, Math.min(span, frame));
    group.goToFrame(group.from + frame);
  }

  /** Length of a clip in seconds (0 if there is none). */
  seconds(clip: string): number {
    const group = this.clips.get(clip);
    if (!group) return 0;
    const fps = group.targetedAnimations[0]?.animation.framePerSecond ?? 60;
    return (group.to - group.from) / fps;
  }

  /** Blends two clips smoothly across all animated channels. */
  blend(
    a: string,
    ta: number,
    b: string,
    tb: number,
    weight: number,
    loopA = true,
    loopB = true,
  ): void {
    if (weight <= 0.002) return this.pose(a, ta, loopA);
    if (weight >= 0.998) return this.pose(b, tb, loopB);
    this.pose(a, ta, loopA);
    for (const [i, { target, property }] of this.channels.entries()) {
      const value = target[property];
      if (value) (this.held[i] as Quaternion & Vector3).copyFrom(value as Quaternion & Vector3);
    }
    this.pose(b, tb, loopB);
    for (const [i, { target, property }] of this.channels.entries()) {
      const value = target[property];
      if (!value) continue;
      if (value instanceof Quaternion)
        Quaternion.SlerpToRef(this.held[i] as Quaternion, value, weight, value);
      else Vector3.LerpToRef(this.held[i] as Vector3, value, weight, value);
    }
  }

  /**
   * Turns the upper spine, neck chain, and head smoothly towards a world point, including gentle
   * vertical eye-line pitch so taller figures naturally incline their gaze toward Sora's eye height.
   * `maxAngle` defaults to 1.4 rad (human limit) and can widen up to ~2.1 rad for supernatural turns.
   */
  lookAt(target: Vector3, amount: number, maxAngle = 1.4): void {
    const head = this.head;
    if (amount <= 0 || !head || !this.faceAxis) return;
    refresh(head);
    const face = Vector3.TransformNormal(this.faceAxis, head.getWorldMatrix());
    const to3D = target.subtract(head.getAbsolutePosition());
    const horizLen = Math.hypot(to3D.x, to3D.z);
    const faceHoriz = new Vector3(face.x, 0, face.z);
    if (horizLen < 1e-4 || faceHoriz.lengthSquared() < 1e-6) return;
    faceHoriz.normalize();
    const toHoriz = new Vector3(to3D.x / horizLen, 0, to3D.z / horizLen);

    const yawAngle =
      Math.max(
        -maxAngle,
        Math.min(
          maxAngle,
          Math.atan2(
            faceHoriz.z * toHoriz.x - faceHoriz.x * toHoriz.z,
            Vector3.Dot(faceHoriz, toHoriz),
          ),
        ),
      ) * amount;

    // Distribute yaw smoothly through upper spine -> 3 neck joints -> head for natural S-curve turns
    for (const [node, share] of [
      [this.spineUpper, 0.1],
      [this.neckLow, 0.15],
      [this.neckMid, 0.2],
      [this.neck, 0.23],
      [head, 0.32],
    ] as const) {
      if (!node) continue;
      turnAboutWorldUp(node, yawAngle * share);
    }

    // Subtle vertical eye-line tracking (downward when towering over Sora, upward on stairs)
    const targetPitch = Math.atan2(-to3D.y, horizLen);
    const clampedPitch = Math.max(-0.34, Math.min(0.38, targetPitch)) * amount * 0.72;
    if (Math.abs(clampedPitch) > 0.01) {
      const pitchAxis = Vector3.Cross(Vector3.UpReadOnly, toHoriz);
      if (pitchAxis.lengthSquared() > 1e-5) {
        pitchAxis.normalize();
        for (const [node, share] of [
          [this.neckMid, 0.22],
          [this.neck, 0.3],
          [head, 0.48],
        ] as const) {
          if (!node) continue;
          turnAboutWorldAxis(node, pitchAxis, clampedPitch * share);
        }
      }
    }
  }

  /**
   * Layers organic living secondary motion (asymmetric ragged breathing, subtle weight sway,
   * relaxed drooping elbows/wrists, listening head micro-drift) together with Asian-horror
   * bone distortions (broken-neck roll, over-shoulder yaw twist, predatory hunch, and sharp
   * convulsion shudders). Call after `pose`/`blend` and `lookAt`.
   */
  distortHorror(d: HorrorDistortion): void {
    const yaw = this.root.rotation.y;
    const forward = new Vector3(Math.sin(yaw), 0, Math.cos(yaw));
    const right = new Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
    const t = d.time ?? 0;
    const twitch = Math.max(0, Math.min(1, d.twitch ?? 0));
    const hunch = Math.max(0, Math.min(1, d.hunch ?? 0));
    const walkBlend = Math.max(0, Math.min(1, d.walkBlend ?? 0));
    const still = 1 - walkBlend;

    // 1. Asymmetric ragged breathing & slow non-repeating idle weight transfer
    const breath =
      Math.sin(t * 1.15) * 0.62 + Math.sin(t * 2.3 + 0.7) * 0.24 + Math.sin(t * 0.48 - 0.4) * 0.14;
    const breathLag = Math.sin(t * 1.15 - 0.65) * 0.7 + Math.sin(t * 2.3 - 0.1) * 0.3;
    const swaySide = still * (Math.sin(t * 0.61) * 0.026 + Math.sin(t * 1.37 + 1.1) * 0.011);
    const swayFore = still * (Math.cos(t * 0.47 + 0.4) * 0.02 + Math.sin(t * 0.94) * 0.009);

    // Irregular jagged burst oscillation for violent shuddering (never smooth sine bobbing)
    const burst =
      twitch > 0.01
        ? twitch *
          (Math.sin(t * 47.3) * 0.55 + Math.sin(t * 73.1 + 1.7) * 0.35 + Math.cos(t * 111.0) * 0.25)
        : 0;
    const burst2 =
      twitch > 0.01 ? twitch * (Math.cos(t * 59.7 + 0.9) * 0.6 + Math.sin(t * 89.2) * 0.4) : 0;

    // Spine cascade: organic weight sway + ragged chest heave + predatory hunch
    if (this.spineLower) {
      turnAboutWorldAxis(this.spineLower, forward, swaySide * 0.55);
      turnAboutWorldAxis(this.spineLower, right, swayFore * 0.5 + hunch * 0.08);
    }
    if (this.spineMid) {
      turnAboutWorldAxis(this.spineMid, forward, swaySide * 0.45);
      turnAboutWorldAxis(this.spineMid, right, swayFore * 0.5 + hunch * 0.22 - breath * 0.016);
    }
    if (this.spineChest) {
      turnAboutWorldAxis(this.spineChest, right, hunch * 0.14 - breath * 0.028);
      turnAboutWorldAxis(this.spineChest, forward, -swaySide * 0.35);
    }
    if (this.spineUpper) {
      turnAboutWorldAxis(this.spineUpper, right, hunch * 0.18 - breath * 0.022);
      turnAboutWorldAxis(this.spineUpper, forward, -swaySide * 0.25);
    }

    // Clavicles rise unevenly on ragged inhales and roll slightly inward when hunched
    if (this.clavL) {
      turnAboutWorldAxis(this.clavL, forward, -hunch * 0.15 - breath * 0.026 + burst2 * 0.14);
    }
    if (this.clavR) {
      turnAboutWorldAxis(this.clavR, forward, hunch * 0.15 + breath * 0.022 - burst2 * 0.14);
    }

    // 2. Natural relaxed/eerie arms & drooping wrists when standing/stalking (fades cleanly during walks)
    if (still > 0.02) {
      const armDriftL = Math.sin(t * 0.73 + 0.3) * 0.035 + breathLag * 0.022;
      const armDriftR = Math.sin(t * 0.67 + 2.1) * 0.032 - breathLag * 0.018;
      // Subtle forward shoulder drape & asymmetric elbow relaxation (negative X-axis brings -Y arm forward)
      if (this.upperArmL) {
        turnAboutWorldAxis(this.upperArmL, right, still * (-0.04 - hunch * 0.14 + armDriftL));
        turnAboutWorldAxis(this.upperArmL, forward, still * (-0.035 - swaySide * 0.4));
      }
      if (this.upperArmR) {
        turnAboutWorldAxis(this.upperArmR, right, still * (-0.07 - hunch * 0.17 + armDriftR));
        turnAboutWorldAxis(this.upperArmR, forward, still * (0.045 - swaySide * 0.4));
      }
      if (this.lowerArmL) {
        turnAboutWorldAxis(
          this.lowerArmL,
          right,
          still * (-0.08 - hunch * 0.18 + breathLag * 0.035) + burst * 0.09,
        );
      }
      if (this.lowerArmR) {
        turnAboutWorldAxis(
          this.lowerArmR,
          right,
          still * (-0.13 - hunch * 0.22 - breathLag * 0.032) - burst2 * 0.09,
        );
      }
      if (this.wristL) {
        turnAboutWorldAxis(
          this.wristL,
          right,
          still * (0.09 + hunch * 0.12 - breathLag * 0.045) + burst2 * 0.12,
        );
      }
      if (this.wristR) {
        turnAboutWorldAxis(
          this.wristR,
          right,
          still * (0.12 + hunch * 0.14 + breathLag * 0.048) - burst * 0.12,
        );
      }
    }

    // 3. Natural listening micro-cocking of the head + broken-neck horror angles & shudders
    const listenRoll = still * (Math.sin(t * 0.82 + 0.4) * 0.042 + Math.sin(t * 1.87) * 0.016);
    const listenYaw = still * (Math.cos(t * 0.54 + 1.1) * 0.032);
    const breathCounterPitch = breath * 0.032;

    const roll = (d.neckRoll ?? 0) + listenRoll + burst * 0.36;
    const pitch = (d.neckPitch ?? 0) - hunch * 0.48 + breathCounterPitch + burst2 * 0.2;
    const extraYaw = (d.neckYaw ?? 0) + listenYaw + burst * 0.26;

    if (Math.abs(roll) > 1e-4) {
      if (this.neckLow) turnAboutWorldAxis(this.neckLow, forward, roll * 0.14);
      if (this.neckMid) turnAboutWorldAxis(this.neckMid, forward, roll * 0.22);
      if (this.neck) turnAboutWorldAxis(this.neck, forward, roll * 0.28);
      if (this.head) turnAboutWorldAxis(this.head, forward, roll * 0.36);
    }
    if (Math.abs(pitch) > 1e-4) {
      if (this.neckLow) turnAboutWorldAxis(this.neckLow, right, pitch * 0.16);
      if (this.neckMid) turnAboutWorldAxis(this.neckMid, right, pitch * 0.22);
      if (this.neck) turnAboutWorldAxis(this.neck, right, pitch * 0.26);
      if (this.head) turnAboutWorldAxis(this.head, right, pitch * 0.36);
    }
    if (Math.abs(extraYaw) > 1e-4) {
      if (this.neckLow) turnAboutWorldUp(this.neckLow, extraYaw * 0.15);
      if (this.neckMid) turnAboutWorldUp(this.neckMid, extraYaw * 0.24);
      if (this.neck) turnAboutWorldUp(this.neck, extraYaw * 0.26);
      if (this.head) turnAboutWorldUp(this.head, extraYaw * 0.35);
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
