import { bookTurnFrame, type BookTurnState } from "../ui/diegetic/BookMotion";
import handContact from "../../art-source/characters/sora/sora-hands.drawing.json";
import { createTelephoneReceiver } from "./TelephoneReceiver";
import { decodeHandAsset, type HandAsset } from "./HandAsset";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { BaseTexture } from "@babylonjs/core/Materials/Textures/baseTexture";
import { drawingFrame } from "./DrawingPose";
import { HandRig, type HandGrip } from "./HandRig";
import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
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
  private drawing: TransformNode | null = null;
  private readonly drawingContact = new Vector3();
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
    this.receiver = createTelephoneReceiver(scene, "sora_held_receiver");
    this.receiver.parent = this.right;
    // Match the authored phone pose in sora_grip.py: seat the 26 mm barrel
    // against the palm and follow the natural stagger of the knuckles.
    this.receiver.position.set(0, 0.06, 0.02);
    this.receiver.rotation.y = 0;
    this.receiver.rotation.z = Math.PI / 2 - 0.15;
    this.meshes.push(...this.receiver.getChildMeshes<Mesh>());
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
  /** Cord exits below the grip; the world cord follows this point during calls. */
  get phoneCordPoint(): Vector3 | null {
    if (!this.phone) return null;
    return Vector3.TransformCoordinates(
      new Vector3(0, -0.116, 0),
      this.receiver.computeWorldMatrix(true),
    );
  }
  /** The opening uses the anatomical tripod grip in the paper's own space. */
  holdDrawing(pen: TransformNode | null): void {
    this.drawing = pen;
    this.duration = 0;
    this.elapsed = 0;
    this.right.parent = pen ?? this.camera;
    this.right.scaling.setAll(0.85);
    if (pen) {
      // The glTF paper's reflected parent would otherwise turn the right hand
      // into a left hand and hide the thumb behind the shaft.
      this.right.scaling.x = -0.85;
      const frame = drawingFrame();
      this.drawingContact.copyFrom(frame.contact);
      this.right.rotationQuaternion = frame.hand;
    } else this.right.rotationQuaternion = null;
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
  update(
    dt: number,
    hidden: boolean,
    book: TransformNode | null,
    speed: number,
    turn: BookTurnState | null = null,
  ): void {
    this.time += dt;
    // Bring out fingertip contact and the photographic knuckle detail while
    // drawing. This light affects the hand meshes only and eases back afterward.
    this.fill.intensity +=
      ((this.drawing ? 0.85 : 0.32) - this.fill.intensity) * (1 - Math.exp(-dt * 8));
    if (this.drawing) {
      this.left.setEnabled(false);
      this.right.setEnabled(true);
      this.match.setEnabled(false);
      this.flame.setEnabled(false);
      this.receiver.setEnabled(false);
      if (this.lamp) this.lamp.setEnabled(false);
      this.rightRig.update(dt, "drawing");
      this.right.position.set(
        -this.drawingContact.x,
        0.03 - this.drawingContact.y,
        -this.drawingContact.z,
      );
      return;
    }
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
    if (this.left.isEnabled() && !(reading && turn?.direction === -1))
      this.leftRig.update(dt, leftGrip);
    if (this.right.isEnabled() && !(reading && turn?.direction === 1))
      this.rightRig.update(dt, rightGrip);
    this.left.rotation.set(0, 0, -0.12);
    this.right.rotation.set(0, 0, 0.1);
    this.camera.computeWorldMatrix();
    this.camera.getWorldMatrix().invertToRef(this.inverse);
    if (reading && book) {
      book.computeWorldMatrix(true);
      for (const [hand, x] of [
        [this.left, -0.178],
        [this.right, 0.178],
      ] as const) {
        const side = hand === this.left ? -1 : 1;
        hand.rotation.y = -side * 1.05;
        hand.rotation.z = side * 0.28;
        const anchor = new Vector3(x, 0.004, -0.128);
        if (turn) {
          const motion = bookTurnFrame(turn);
          if (side === turn.direction) {
            hand.rotation.y += side * motion.curl * motion.carry * 0.65;
            hand.rotation.x -= motion.curl * motion.carry * 0.45;
            hand.rotation.z -= side * motion.carry * 0.35;
            const rig = side < 0 ? this.leftRig : this.rightRig;
            rig.blend(dt, {
              journal: 1 - motion.carry,
              drawing: motion.pinch,
              reach: Math.max(0, motion.carry - motion.pinch),
            });
          } else {
            anchor.y -= motion.settle * 0.002;
            hand.rotation.z += side * motion.settle * 0.035;
          }
        }
        Vector3.TransformCoordinatesToRef(anchor, book.getWorldMatrix(), this.grip);
        Vector3.TransformCoordinatesToRef(this.grip, this.inverse, hand.position);
        if (turn?.direction === side) {
          const motion = bookTurnFrame(turn);
          const pageContact = Vector3.TransformCoordinates(
            Vector3.FromArray(motion.contact),
            book.getWorldMatrix(),
          );
          const cameraContact = Vector3.TransformCoordinates(pageContact, this.inverse);
          // Reuse the opposed fingertip pads, without its pencil. Seat that contact,
          // rather than guessing a wrist offset that leaves fingers floating apart.
          const pads = Vector3.FromArray(handContact.contact);
          pads.x *= -side;
          pads.scaleInPlace(hand.scaling.x);
          const offset = Vector3.TransformNormal(
            pads,
            Matrix.RotationYawPitchRoll(hand.rotation.y, hand.rotation.x, hand.rotation.z),
          );
          Vector3.LerpToRef(
            hand.position,
            cameraContact.subtract(offset),
            motion.carry,
            hand.position,
          );
        }
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
      const t = Math.min(1, this.phoneAge / 0.65);
      const lift = t * t * (3 - 2 * t);
      // Turn the palm toward Sora and bring the ear cup above the thumb.
      // The elbow stays outside the right edge instead of rising from the chest.
      this.right.position.set(0.13, -0.35 + 0.325 * lift, 0.46 - 0.06 * lift);
      this.right.rotation.set(
        0.08 * lift + Math.sin(this.time * 1.2) * 0.004,
        Math.PI + 0.15 * lift,
        -1.0 * lift,
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
