import { decodeHandAsset, type HandAsset } from "./HandAsset";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { BaseTexture } from "@babylonjs/core/Materials/Textures/baseTexture";
import { HandRig, type HandGrip } from "./HandRig";
import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";

/** Presentation only: animation never spends inventory or completes an interaction. */
export class FirstPersonHands {
  readonly left: TransformNode;
  readonly right: TransformNode;
  readonly meshes: Mesh[] = [];
  readonly leftRig: HandRig;
  readonly rightRig: HandRig;
  private readonly fill: PointLight;
  private readonly match: Mesh;
  private readonly flame: Mesh;
  private readonly receiver: TransformNode;
  private lamp: TransformNode | null = null;
  private lampVisible: () => boolean = () => false;
  private phone = false;
  private phoneAge = 0;
  private action: "reach" | "strike" | "pour" = "reach";
  private elapsed = 0;
  private duration = 0;
  private time = 0;
  private readonly inverse = Matrix.Identity();
  private readonly grip = new Vector3();

  constructor(
    private readonly scene: Scene,
    private readonly camera: Camera,
  ) {
    const material = (name: string, color: string) => {
      const mat = new StandardMaterial(name, scene);
      mat.diffuseColor = Color3.FromHexString(color);
      mat.emissiveColor = mat.diffuseColor.scale(0.08);
      mat.specularColor.set(0.03, 0.03, 0.03);
      return mat;
    };
    this.leftRig = new HandRig(scene, "sora_left_hand", -1);
    this.rightRig = new HandRig(scene, "sora_right_hand", 1);
    this.left = this.leftRig.root;
    this.right = this.rightRig.root;
    this.left.parent = camera;
    this.right.parent = camera;
    this.meshes.push(...this.leftRig.meshes, ...this.rightRig.meshes);
    const wood = material("sora_match_wood", "#d6bb84");
    this.match = CreateTube(
      "sora_held_match",
      {
        path: [new Vector3(-0.035, 0.06, 0.044), new Vector3(0.045, 0.06, 0.044)],
        radius: 0.002,
        tessellation: 6,
        cap: Mesh.CAP_ALL,
      },
      scene,
    );
    this.match.material = wood;
    this.match.parent = this.right;
    const fire = material("sora_match_flame", "#ffc06c");
    fire.disableLighting = true;
    fire.emissiveColor.set(1, 0.55, 0.1);
    this.flame = CreateSphere("sora_match_flame", { diameter: 1, segments: 8 }, scene);
    this.flame.scaling.set(0.012, 0.03, 0.012);
    this.flame.position.set(-0.04, 0.074, 0.044);
    this.flame.parent = this.right;
    this.flame.material = fire;
    this.receiver = new TransformNode("sora_held_receiver", scene);
    this.receiver.parent = this.right;
    this.receiver.rotation.y = Math.PI / 2;
    const black = material("sora_receiver", "#20231e");
    for (const [z, width, height] of [
      [0, 0.045, 0.045],
      [-0.13, 0.095, 0.085],
      [0.13, 0.095, 0.085],
    ]) {
      const mesh = CreateSphere("sora_receiver_part", { diameter: 1, segments: 10 }, scene);
      mesh.scaling.set(width, height, z === 0 ? 0.27 : 0.09);
      mesh.position.set(0, 0.052, z + 0.025);
      mesh.parent = this.receiver;
      mesh.material = black;
      this.meshes.push(mesh);
    }
    this.meshes.push(this.match, this.flame);
    for (const mesh of this.meshes) {
      mesh.isPickable = false;
      mesh.renderingGroupId = 1;
      mesh.alwaysSelectAsActiveMesh = true;
    }
    // A soft view light keeps hands readable without the nearby wick bleaching them.
    const fill = new PointLight("sora_hands_fill", new Vector3(-0.4, 0.3, 0.1), scene);
    this.fill = fill;
    fill.parent = camera;
    fill.diffuse.set(1, 0.83, 0.66);
    fill.intensity = 0.32;
    fill.renderPriority = 20;
    fill.includedOnlyMeshes = this.meshes;
    fill.range = 1.5;
    this.left.setEnabled(false);
    this.right.setEnabled(false);
  }
  /** Load the authored anatomical asset before the world registers its light masks. */
  async load(): Promise<void> {
    const base = `${import.meta.env.BASE_URL}assets/shared/`;
    const response = await fetch(`${base}sora_hand.mesh`);
    if (!response.ok) throw new Error("Sora’s hand mesh could not load");
    const asset = decodeHandAsset(await response.arrayBuffer());
    const texture = new Texture(`${base}sora_hand_skin.png`, this.scene);
    texture.anisotropicFilteringLevel = 8;
    const normal = new Texture(`${base}sora_hand_normal.png`, this.scene);
    normal.gammaSpace = false;
    normal.anisotropicFilteringLevel = 8;
    const roughness = new Texture(`${base}sora_hand_roughness.png`, this.scene);
    roughness.gammaSpace = false;
    roughness.anisotropicFilteringLevel = 8;
    this.initialize(asset, texture, normal, roughness);
  }
  initialize(
    asset: HandAsset,
    texture: BaseTexture | null = null,
    normal: BaseTexture | null = null,
    roughness: BaseTexture | null = null,
  ): void {
    if (this.leftRig.meshes.length) return;
    this.leftRig.install(asset, texture, normal, roughness);
    this.rightRig.install(asset, texture, normal, roughness);
    this.meshes.push(...this.leftRig.meshes, ...this.rightRig.meshes);
    for (const mesh of this.meshes) {
      mesh.isPickable = false;
      mesh.renderingGroupId = 1;
      mesh.alwaysSelectAsActiveMesh = true;
    }
    this.fill.includedOnlyMeshes = [...this.meshes];
  }
  attachLamp(root: TransformNode, visible: () => boolean = () => true): void {
    this.lamp = root;
    this.lampVisible = visible;
    root.setEnabled(false);
  }
  holdPhone(active: boolean): void {
    this.phone = active;
    if (active) this.phoneAge = 0;
    this.duration = 0;
  }
  animate(action: "reach" | "strike" | "pour"): void {
    if (this.phone || (this.duration > this.elapsed && this.action === "strike")) return;
    this.action = action;
    this.elapsed = 0;
    this.duration = action === "strike" ? 0.85 : action === "pour" ? 1.1 : 0.55;
  }
  update(dt: number, hidden: boolean, book: TransformNode | null, speed: number): void {
    this.time += dt;
    this.elapsed = Math.min(this.duration, this.elapsed + dt);
    const active = this.elapsed < this.duration;
    const reading = book?.isEnabled() ?? false;
    const show = !hidden || this.phone;
    const carrying = !!this.lamp && this.lampVisible() && !this.phone;
    this.left.setEnabled(show && (carrying || reading));
    this.right.setEnabled(show && (active || this.phone || reading));
    if (this.lamp) this.lamp.setEnabled(show && carrying && !reading);
    this.match.setEnabled(active && this.action === "strike" && !this.phone && !reading);
    this.flame.setEnabled(this.match.isEnabled() && this.elapsed >= 0.22 && this.elapsed < 0.72);
    this.receiver.setEnabled(this.phone);
    const leftGrip: HandGrip = reading ? "journal" : "lamp";
    const rightGrip: HandGrip = this.phone
      ? "phone"
      : reading
        ? "journal"
        : active && this.action === "strike"
          ? "pinch"
          : active
            ? "reach"
            : "relaxed";
    if (this.left.isEnabled()) this.leftRig.update(dt, leftGrip);
    if (this.right.isEnabled()) this.rightRig.update(dt, rightGrip);
    this.left.rotation.set(0, 0, -0.12);
    this.right.rotation.set(0, 0, 0.1);
    this.camera.computeWorldMatrix();
    this.camera.getWorldMatrix().invertToRef(this.inverse);
    if (reading && book) {
      book.computeWorldMatrix(true);
      for (const [hand, x] of [
        [this.left, -0.16],
        [this.right, 0.16],
      ] as const) {
        hand.rotation.y = hand === this.left ? 1.15 : -1.15;
        hand.rotation.z = hand === this.left ? -0.15 : 0.15;
        Vector3.TransformCoordinatesToRef(
          new Vector3(x, 0.012, -0.11),
          book.getWorldMatrix(),
          this.grip,
        );
        Vector3.TransformCoordinatesToRef(this.grip, this.inverse, hand.position);
      }
      return;
    }
    if (this.lamp) {
      this.left.rotation.copyFrom(this.lamp.rotation);
      // The lamp turns 180 degrees to face its gauge toward Sora. The grip's
      // authored back-of-hand view must not inherit that model-facing turn.
      this.left.rotation.y -= Math.PI;
      this.lamp.computeWorldMatrix(true);
      Vector3.TransformCoordinatesToRef(
        new Vector3(-0.005, 0.24, -0.005),
        this.lamp.getWorldMatrix(),
        this.grip,
      );
      Vector3.TransformCoordinatesToRef(this.grip, this.inverse, this.left.position);
    }
    if (this.phone) {
      this.left.setEnabled(false);
      this.phoneAge += dt;
      const t = Math.min(1, this.phoneAge / 0.32);
      const lift = t * t * (3 - 2 * t);
      this.right.position.set(0.21, -0.35 + 0.29 * lift, 0.46);
      this.right.rotation.set(
        0.15 * lift + Math.sin(this.time * 1.2) * 0.006,
        -0.2 * lift,
        -0.35 * lift,
      );
    } else {
      const p = this.duration ? this.elapsed / this.duration : 1;
      const lift = Math.sin(Math.PI * p);
      this.right.position.set(0.18 - 0.11 * lift, -0.35 + 0.17 * lift, 0.42 + 0.06 * lift);
      if (this.action === "strike") {
        this.right.position.x -= 0.12 * Math.sin(Math.min(1, p * 3) * Math.PI);
        this.right.rotation.z -= 0.3 * lift;
      } else if (this.action === "pour") this.right.rotation.z -= lift;
      this.right.position.y += Math.sin(this.time * 6.2) * 0.005 * Math.min(1, speed / 2);
    }
  }
  dispose(): void {
    const materials = new Set(this.meshes.flatMap((m) => (m.material ? [m.material] : [])));
    this.leftRig.dispose();
    this.rightRig.dispose();
    this.fill.dispose();
    for (const mat of materials) mat.dispose();
  }
}
