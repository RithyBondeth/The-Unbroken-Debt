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
import { realiseInstances } from "../../../core/AreaLoader";

const templates = new WeakMap<Scene, AssetContainer>();
const loading = new WeakMap<Scene, Promise<void>>();
const forms = new WeakMap<Scene, Set<ShadowFigure>>();
/** Multiplies the pale painted map down to near-black (linear). */
const BLACK_PAINT = new Color3(0.07, 0.066, 0.062);

/** The shrine's ancestral effigy seen upright in the forest and house.
 * Baked anatomical geometry, inset eyes, weathered paint and woven cotton are
 * authored together in ancestor-forms.blend. Foot origin, facing +Z, in metres.
 */
export class ShadowFigure {
  readonly root: Mesh;
  readonly meshes: Mesh[];
  private readonly posture: TransformNode;
  private readonly fades: { mesh: Mesh; plugin: DitheredTileFadeMaterialPlugin }[] = [];

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
            if (material.name === "M_ancestor_painted_mineral") {
              material.albedoColor = BLACK_PAINT.clone();
              material.roughness = 0.58;
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

  /** A nearly still, weighted lean. The effigy never floats above its foot pivot. */
  animate(seconds: number, travel = 0): void {
    this.posture.rotation.z = Math.sin(seconds * 0.29 + 0.8) * (0.002 + travel * 0.003);
    this.posture.rotation.x = Math.sin(seconds * 0.37) * 0.002;
  }

  dispose(): void {
    // Shared geometry/materials belong to the scene template, not to one encounter.
    forms.get(this.scene)?.delete(this);
    this.root.dispose(false, false);
  }
}
