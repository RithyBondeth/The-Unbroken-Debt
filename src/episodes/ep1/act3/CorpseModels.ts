import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { Area } from "../../../core/AreaLoader";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { MorphTargetManager } from "@babylonjs/core/Morph/morphTargetManager";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { BoundingBox } from "@babylonjs/core/Culling/boundingBox";
import { Frustum } from "@babylonjs/core/Maths/math.frustum";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Ray } from "@babylonjs/core/Culling/ray";
import { extrasOf } from "../../../core/LevelBuilder";
import { RelicCraft } from "./RelicCraft";

/** Anatomical, textured funeral body with five baked, instantaneous offscreen poses. */
export class CorpseModels {
  readonly root: TransformNode;
  readonly lid: TransformNode;
  readonly closeGrip: TransformNode;
  private readonly scene: Scene;
  private current = -1;
  private readonly managers: MorphTargetManager[] = [];
  // Covers every baked pose, including the raised head and lifted lotus.
  // Conservative visibility prevents a change even at the edge of the screen.
  private readonly bounds: Vector3[] = [];

  private constructor(scene: Scene, area: Area) {
    this.scene = scene;
    const b = new RelicCraft(scene);
    const lid = (this.lid = b.root("coffin_lid_hinge", [0, 1.12, -6.25]));
    const original = area.container.meshes.find((mesh) => mesh.name === "coffin_body");
    const authoredShell = original ? extrasOf(original).hollow === true : false;
    const timber =
      original?.material instanceof PBRMaterial
        ? original.material
        : b.surface("coffin_teak", "#3b2119", "wood");
    for (const mesh of area.container.meshes) {
      if (/^coffin_(lid|ridge|finial)/.test(mesh.name)) {
        mesh.computeWorldMatrix(true);
        mesh.setParent(lid, true);
        const material = mesh.material?.clone(`${mesh.name}_propped_lid`);
        if (material) {
          material.backFaceCulling = false;
          mesh.material = material;
        }
      }
      if (/^coffin_(cloth|garland)/.test(mesh.name)) mesh.setEnabled(false);
      if (!authoredShell && /^coffin_(body|band)/.test(mesh.name)) mesh.setEnabled(false);
    }
    // Four separate walls and a low bed leave a genuine open cavity.
    const shell = b.root("coffin_open_shell", [0, 0, -5.9]);
    if (!authoredShell) {
      b.box(shell, "coffin_bed", [1.96, 0.045, 0.66], [0, 0.7, 0], timber);
      for (const z of [-0.335, 0.335])
        b.box(shell, "coffin_side_wall", [2, 0.48, 0.03], [0, 0.88, z], timber);
      for (const x of [-0.985, 0.985])
        b.box(shell, "coffin_end_wall", [0.03, 0.48, 0.7], [x, 0.88, 0], timber);
    }
    const gilt = b.mat("coffin_rim_brass", "#8c7134", 0.54, 0.7);
    for (const z of [-0.34, 0.34])
      b.box(shell, "coffin_rim_rail", [2.02, 0.025, 0.035], [0, 1.115, z], gilt);
    for (const x of [-1, 1])
      b.box(shell, "coffin_end_rail", [0.035, 0.025, 0.7], [x, 1.115, 0], gilt);
    const underside = b.surface("coffin_lid_inner", "#352319", "wood");
    b.box(lid, "coffin_lid_inner_board", [2.08, 0.025, 0.76], [0, -0.016, 0.35], underside);
    for (const x of [-0.7, 0.7])
      b.box(lid, "coffin_lid_inner_brace", [0.045, 0.035, 0.7], [x, -0.045, 0.35], underside);
    this.closeGrip = b.root("coffin_close_grip", [0.65, 1.13, -5.53]);
    b.box(this.closeGrip, "coffin_close_handle", [0.28, 0.035, 0.045], [0, 0, 0], gilt);
    area.container.transformNodes.push(shell, this.closeGrip);
    this.root = b.root("sok_funeral_body", [0, 0.725, -5.9]);
    const authoredLining = area.container.materials.find(
      (material) => material.name === "M_funeral_lining",
    );
    const dark =
      authoredLining instanceof PBRMaterial ? authoredLining : b.mat("coffin_lining", "#211b15", 1);
    b.box(this.root, "coffin_inner_padding", [1.88, 0.018, 0.61], [0, 0, 0], dark);
    for (const z of [-0.305, 0.305])
      b.box(this.root, "coffin_inner_rim", [1.96, 0.035, 0.017], [0, 0.015, z], dark);
    for (const x of [-1.04, 1.04])
      for (const y of [0.69, 2.1])
        for (const z of [-6.4, -5.25]) this.bounds.push(new Vector3(x, y, z));
    area.container.meshes.push(...b.meshes);
    area.container.transformNodes.push(this.root, lid);
  }

  static async load(scene: Scene, area: Area): Promise<CorpseModels> {
    const body = new CorpseModels(scene, area);
    const asset = await LoadAssetContainerAsync(
      `${import.meta.env.BASE_URL}assets/ep1/sok_corpse.glb`,
      scene,
    );
    for (const node of asset.rootNodes) node.parent = body.root;
    for (const mesh of asset.meshes) {
      mesh.isPickable = false;
      mesh.receiveShadows = true;
      const manager = mesh.morphTargetManager;
      if (manager && !body.managers.includes(manager)) body.managers.push(manager);
    }
    if (!body.managers.some((manager) => manager.numTargets === 4)) {
      asset.dispose();
      throw new Error("Sok's anatomical body is missing its four saved encounter poses");
    }
    asset.addAllToScene();
    // Transfer ownership to the area so restarting / unloading releases the asset too.
    area.container.meshes.push(...asset.meshes);
    area.container.transformNodes.push(...asset.transformNodes);
    area.container.materials.push(...asset.materials);
    area.container.textures.push(...asset.textures);
    area.container.geometries.push(...asset.geometries);
    area.container.morphTargetManagers.push(...asset.morphTargetManagers);
    body.pose(0);
    return body;
  }

  setLid(open: number): void {
    this.lid.rotation.x = -1.75 * Math.max(0, Math.min(1, open));
  }

  headCovered(camera: Camera): boolean {
    const target = new Vector3(0.72, 1.0, -5.9);
    const from = camera.globalPosition;
    const direction = target.subtract(from);
    const ray = new Ray(from, direction.normalize(), Vector3.Distance(from, target));
    const hit = this.scene.pickWithRay(ray, (mesh) => mesh.isDescendantOf(this.lid));
    return !!hit?.hit;
  }

  observed(camera: Camera): boolean {
    return BoundingBox.IsInFrustum(
      this.bounds,
      Frustum.GetPlanes(camera.getTransformationMatrix()),
    );
  }

  pose(index: number): void {
    const next = Math.max(0, Math.min(4, Math.trunc(index)));
    if (this.current === next) return;
    this.current = next;
    for (const manager of this.managers)
      for (let i = 0; i < manager.numTargets; i++)
        manager.getTarget(i).influence = manager.getTarget(i).name === `Sok_pose_${next}` ? 1 : 0;
    // The lifted lotus can extend beyond its resting bounds. Refresh once per
    // pose so render culling and shadows follow the actual held geometry.
    for (const mesh of this.root.getChildMeshes()) mesh.refreshBoundingInfo({ applyMorph: true });
  }
}
