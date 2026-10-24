import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";

/** The glow the flame gives its glass chimney and the brass round it, at full flame. */
const GLASS_GLOW = new Color3(1.0, 0.55, 0.2).scale(0.55);
const BRASS_GLOW = new Color3(1.0, 0.6, 0.25).scale(0.06);

/** Where the lamp hangs in Sora's left hand, and where she lifts it to read the gauge (camera space, m). */
// Low enough to leave the view clear, high enough that its lit chimney shows.
const LOWERED = new Vector3(-0.26, -0.36, 0.65);
const RAISED = new Vector3(-0.12, -0.22, 0.5);

/**
 * The hurricane lamp in Sora's left hand (Controls and Interface, section 6):
 * the lantern with its flame and the glass gauge on the tank
 * (`assets/shared/shared_lamp.glb`, tools/areas/shared_lamp.py). Drawn after the
 * world with its own depth, like the sketchbook, so it never sinks into a wall.
 */
export class HeldLamp {
  readonly root: TransformNode;
  /** Where the lamp's light belongs: at the wick. */
  readonly flamePoint: TransformNode;
  private readonly flame: AbstractMesh | null;
  private readonly oil: TransformNode | null;
  /** The flame's scale as loaded (quantised meshes carry one), which its size multiplies. */
  private readonly flameScale = new Vector3(1, 1, 1);
  private readonly oilLevel: BottomScaler | null;
  private readonly glass: PBRMaterial[] = [];
  private readonly brass: PBRMaterial[] = [];
  private raise = 0;
  private time = 0;
  private constructor(
    scene: Scene,
    camera: Camera,
    private readonly container: AssetContainer,
  ) {
    this.root = new TransformNode("held_lamp", scene);
    this.root.parent = camera;
    this.root.position.copyFrom(LOWERED);
    container.addAllToScene();
    for (const node of container.rootNodes) node.parent = this.root;
    for (const mesh of container.meshes) {
      mesh.renderingGroupId = 1;
      mesh.isPickable = false;
    }
    const find = (name: string) => container.transformNodes.find((n) => n.name === name) ?? null;
    this.flame = container.meshes.find((m) => m.name.startsWith("lamp_flame")) ?? null;
    this.oil =
      find("lamp_oil") ?? container.meshes.find((m) => m.name.startsWith("lamp_oil")) ?? null;
    this.flamePoint = find("marker_flame") ?? this.root;
    this.oilLevel = this.oil ? new BottomScaler(this.oil as AbstractMesh) : null;
    if (this.flame) this.flameScale.copyFrom(this.flame.scaling);
    for (const material of container.materials) {
      if (!(material instanceof PBRMaterial)) continue;
      // The library lantern's glass is glTF transmission: refraction re-renders the
      // whole scene every frame, and blended at full opacity it hid the flame.
      material.subSurface.isRefractionEnabled = false;
      if (/glass/i.test(material.name) && material.name !== "M_gauge_glass") {
        material.alpha = 0.16;
        material.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
        material.metallic = 0;
        material.roughness = 0.15;
        material.albedoColor.set(0.9, 0.85, 0.75);
        this.glass.push(material);
      } else if (/brass/i.test(material.name)) {
        // No environment map to reflect: full metal would read black.
        material.metallic = 0.55;
        this.brass.push(material);
      }
    }
    // Drawn after the flame, so the flame shows through the glass.
    for (const mesh of container.meshes) if (/glass/i.test(mesh.name)) mesh.alphaIndex = 1;
  }

  static async load(scene: Scene, camera: Camera): Promise<HeldLamp> {
    const url = `${import.meta.env.BASE_URL}assets/shared/shared_lamp.glb`;
    const container = await LoadAssetContainerAsync(url, scene);
    return new HeldLamp(scene, camera, container);
  }

  /** Every mesh of the lamp, for lights to include or exclude. */
  get meshes(): AbstractMesh[] {
    return this.container.meshes;
  }

  /**
   * `flame` 0..1 sizes the flame card, `oil` 0..1 fills the gauge, `raised`
   * lifts the lamp towards the eye, `walking` (m/s) swings it.
   */
  update(dt: number, flame: number, oil: number, raised: boolean, walking: number): void {
    this.time += dt;
    const t = this.time;
    this.raise += ((raised ? 1 : 0) - this.raise) * Math.min(1, dt * 6);
    Vector3.LerpToRef(LOWERED, RAISED, this.raise, this.root.position);
    const swing = Math.min(1, walking / 2) * (1 - this.raise);
    this.root.position.y += Math.sin(t * 6.2) * 0.012 * swing + Math.sin(t * 1.3) * 0.003;
    this.root.rotation.set(
      0.05 * Math.sin(t * 3.1) * swing - this.raise * 0.25,
      // Turned so the gauge on the tank faces Sora.
      Math.PI + this.raise * 0.3,
      0.06 * Math.sin(t * 6.2 + 0.4) * swing,
    );
    if (this.flame) {
      this.flame.isVisible = flame > 0.01;
      const s = Math.max(0.05, flame) * (0.9 + 0.1 * Math.sin(t * 17) * Math.sin(t * 5.3));
      this.flameScale.scaleToRef(s, this.flame.scaling);
    }
    this.oilLevel?.set(Math.max(0.001, oil));
    // The chimney glows with the flame inside it, and the brass catches a little of it.
    const glow = Math.max(0, flame) * (0.92 + 0.08 * Math.sin(t * 17));
    for (const m of this.glass) GLASS_GLOW.scaleToRef(glow, m.emissiveColor);
    for (const m of this.brass) BRASS_GLOW.scaleToRef(glow, m.emissiveColor);
  }

  dispose(): void {
    this.container.dispose();
    this.root.dispose();
  }
}

/**
 * Scales a mesh's height from its base, so it grows or shrinks upwards. Works
 * with compressed (quantised) meshes, whose node carries a scale and an offset.
 */
export class BottomScaler {
  private readonly y: number;
  private readonly scale: number;
  private readonly base: number;

  constructor(private readonly mesh: AbstractMesh) {
    this.y = mesh.position.y;
    this.scale = mesh.scaling.y;
    this.base = mesh.getBoundingInfo().boundingBox.minimum.y;
  }

  /** `k` is the height as a fraction of the original. */
  set(k: number): void {
    this.mesh.scaling.y = this.scale * k;
    this.mesh.position.y = this.y + this.scale * this.base * (1 - k);
  }
}
