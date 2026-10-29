import type { Scene } from "@babylonjs/core/scene";
import type { AssetContainer } from "@babylonjs/core/assetContainer";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { BoundingInfo } from "@babylonjs/core/Culling/boundingInfo";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { DitheredTileFadeMaterialPlugin } from "@babylonjs/core/Materials/ditheredTileFadeMaterialPlugin";
import type { MorphTarget } from "@babylonjs/core/Morph/morphTarget";
import { realiseInstances } from "../../../core/AreaLoader";

const templates = new WeakMap<Scene, AssetContainer>();
const loading = new WeakMap<Scene, Promise<void>>();
const forms = new WeakMap<Scene, Set<ShadowFigure>>();
/** Multiplies the pale painted map down to near-black (linear). */
const BLACK_PAINT = new Color3(0.14, 0.125, 0.105);

/** The shrine's ancestral effigy seen upright in the forest and house.
 * Baked anatomical geometry, inset eyes, weathered paint and woven cotton are
 * authored together in ancestor-forms.blend. Foot origin, facing +Z, in metres.
 */
export class ShadowFigure {
  readonly root: Mesh;
  readonly meshes: Mesh[];
  private readonly posture: TransformNode;
  private readonly fades: { mesh: Mesh; plugin: DitheredTileFadeMaterialPlugin }[] = [];
  private readonly gestures = new Map<string, MorphTarget[]>();

  /** Load once before constructing the three encounter forms. Clones share GPU assets. */
  static async prepare(scene: Scene): Promise<void> {
    if (templates.has(scene)) return;
    let pending = loading.get(scene);
    if (!pending) {
      pending = (async () => {
        const asset = await LoadAssetContainerAsync(
          `${import.meta.env.BASE_URL}assets/ep1/neakta_shadow.glb`,
          scene,
        );
        // glTF dedup can instance the inset eyes. Babylon's WebGPU pre-pass
        // needs ordinary meshes, including before cloning the template.
        realiseInstances(asset);
        asset.removeAllFromScene();
        for (const material of asset.materials)
          if (material instanceof PBRMaterial) {
            material.maxSimultaneousLights = 8;
            // The apparition is the black Neak Ta: the shrine statues' mineral paint
            // darkened to soot-black lacquer, its mottling and relief kept, with a
            // dull sheen so the lamp still finds the face. The chalk eyes stay pale.
            if (/^M_(ancestor_painted_mineral|neakta_worn_skin)$/.test(material.name)) {
              material.albedoColor = BLACK_PAINT.clone();
              material.roughness = 0.72;
              if (material.bumpTexture) material.bumpTexture.level = 1.05;
            }
            if (material.name === "M_ancestor_chalk_eye") {
              material.albedoColor = new Color3(0.21, 0.19, 0.13);
              material.roughness = 0.32;
            }
            if (/cotton/.test(material.name)) {
              material.albedoColor = new Color3(0.55, 0.5, 0.43);
              material.roughness = 0.88;
            }
            // Coverage changes stay opaque and keep depth / prepass outputs coherent.
            // The plugin uses per-mesh uniforms, so the three forms remain independent.
            DitheredTileFadeMaterialPlugin.GetOrCreate(material);
          }
        templates.set(scene, asset);
        scene.onDisposeObservable.addOnce(() => asset.dispose());
      })();
      loading.set(scene, pending);
    }
    try {
      await pending;
    } finally {
      loading.delete(scene);
    }
  }

  /** Compile the hidden encounters after the game's lights and post effects exist. */
  static async warmup(scene: Scene): Promise<void> {
    await Promise.all(
      [...(forms.get(scene) ?? [])].flatMap((form) =>
        form.fades.map(({ mesh }) => mesh.material!.forceCompilationAsync(mesh)),
      ),
    );
  }

  constructor(
    private readonly scene: Scene,
    name: string,
    height = 2.5,
  ) {
    const template = templates.get(scene);
    if (!template) throw new Error("Prepare the ancestral shadow asset before creating a form");
    this.root = new Mesh(`${name}_effigy`, scene);
    this.root.scaling.setAll(height / 2.5);
    this.posture = new TransformNode(`${name}_posture`, scene);
    this.posture.parent = this.root;
    const copy = template.instantiateModelsToScene((source) => `${name}_${source}`, false, {
      doNotInstantiate: true,
    });
    for (const node of copy.rootNodes) node.parent = this.posture;
    this.meshes = [
      this.root,
      ...this.root.getChildMeshes().filter((m): m is Mesh => m instanceof Mesh),
    ];
    for (const mesh of this.meshes) {
      mesh.isPickable = false;
      mesh.receiveShadows = true;
      const manager = mesh.morphTargetManager;
      if (manager) {
        // Reserve all five influences during loading: a head turn must never
        // trigger shader compilation in the middle of an encounter.
        manager.numMaxInfluencers = 5;
        for (let i = 0; i < manager.numTargets; i++) {
          const target = manager.getTarget(i);
          const targets = this.gestures.get(target.name) ?? [];
          targets.push(target);
          this.gestures.set(target.name, targets);
        }
      }
      if (mesh.getTotalVertices() > 0 && mesh.material instanceof PBRMaterial)
        this.fades.push({
          mesh,
          plugin: DitheredTileFadeMaterialPlugin.GetOrCreate(mesh.material),
        });
    }
    const bounds = this.root.getHierarchyBoundingVectors(true);
    const inverse = Matrix.Invert(this.root.computeWorldMatrix(true));
    this.root.setBoundingInfo(
      new BoundingInfo(
        Vector3.TransformCoordinates(bounds.min, inverse),
        Vector3.TransformCoordinates(bounds.max, inverse),
      ),
    );
    let group = forms.get(scene);
    if (!group) forms.set(scene, (group = new Set()));
    group.add(this);
  }

  /** Opaque dither coverage avoids glass-like overlapping body parts during a fade. */
  setPresence(value: number): void {
    const coverage = Math.max(0, Math.min(1, value));
    for (const { mesh, plugin } of this.fades) plugin.setFadeBounds(mesh, 0, coverage);
  }

  /** Grounded weight shifts, opposed arms and a delayed, half-finished head turn. */
  animate(seconds: number, travel = 0, attention = 0): void {
    const moving = Math.max(0, Math.min(1, travel));
    const stride = seconds * 3.7;
    this.posture.rotation.z = Math.sin(stride) * moving * 0.012;
    this.posture.rotation.x = 0.014 * moving + Math.sin(seconds * 1.6) * 0.003;
    this.posture.position.y = -Math.abs(Math.sin(stride)) * moving * 0.009;
    const weights: Record<string, number> = {
      inhale: 0.5 + 0.5 * Math.sin(seconds * 1.55),
      head_turn: Math.max(-1, Math.min(1, attention + Math.sin(seconds * 0.43) * 0.35)),
      stride_left: Math.max(0, Math.sin(stride)) * moving,
      stride_right: Math.max(0, -Math.sin(stride)) * moving,
      clutch: (0.5 + 0.5 * Math.sin(seconds * 0.71 + 1.8)) * (moving ? 0.35 : 0.8),
    };
    for (const [name, targets] of this.gestures)
      for (const target of targets) target.influence = weights[name] ?? 0;
  }

  dispose(): void {
    // Shared geometry/materials belong to the scene template, not to one encounter.
    forms.get(this.scene)?.delete(this);
    this.root.dispose(false, false);
  }
}
