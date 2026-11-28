import type { Scene } from "@babylonjs/core/scene";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { Area } from "@/core/areaLoader";
import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { MorphTargetManager } from "@babylonjs/core/Morph/morphTargetManager";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { BoundingBox } from "@babylonjs/core/Culling/boundingBox";
import { Frustum } from "@babylonjs/core/Maths/math.frustum";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Ray } from "@babylonjs/core/Culling/ray";
import { extrasOf } from "@/core/levelBuilder";
import { RelicCraft } from "@/shared/RelicCraft";
import { hallAt, inHall } from "../data/funeral";

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
  /** Sok's head in the coffin, under the krama end of the lid. */
  private readonly head: Vector3;

  private constructor(scene: Scene, area: Area) {
    this.scene = scene;
    const b = new RelicCraft(scene);
    // The coffin under the house (funeral_under.coffin, Nov 22, 2026) is hollow and lined:
    // its body's meshes say so (`hollow`), and everything is placed from their bounds. The
    // old tent's solid coffin got a shell of plain boards, at the tent's numbers.
    const body = area.container.meshes.filter((mesh) => /^coffin_body/.test(mesh.name));
    const authoredShell = body.some((mesh) => extrasOf(mesh).hollow === true);
    const coffin = authoredShell ? worldBounds(body) : null;
    const centre = coffin
      ? new Vector3(
          (coffin.min.x + coffin.max.x) / 2,
          coffin.min.y,
          (coffin.min.z + coffin.max.z) / 2,
        )
      : inHall(0, 0, -5.9);
    const top = coffin ? coffin.max.y : 1.12;
    // The lid hinges along the coffin's back (north) edge, away from the wreath.
    const lid = (this.lid = b.root(
      "coffin_lid_hinge",
      coffin ? xyz(new Vector3(centre.x, top, coffin.min.z)) : hallAt([0, 1.12, -6.25]),
    ));
    const original = area.container.meshes.find((mesh) => mesh.name === "coffin_body");
    const timber =
      original?.material instanceof PBRMaterial
        ? original.material
        : b.surface("coffin_teak", "#3b2119", "wood");
    for (const mesh of area.container.meshes) {
      // The lid with its crest and finials, and the krama and the garlands that lie on
      // it and hang from its edge, lift together.
      const onLid = authoredShell
        ? /^coffin_(lid|ridge|finial|cloth|garland)/.test(mesh.name)
        : /^coffin_(lid|ridge|finial)/.test(mesh.name);
      if (onLid) {
        mesh.computeWorldMatrix(true);
        mesh.setParent(lid, true);
        const material = mesh.material?.clone(`${mesh.name}_propped_lid`);
        if (material) {
          material.backFaceCulling = false;
          mesh.material = material;
        }
        continue;
      }
      if (!authoredShell && /^coffin_(cloth|garland)/.test(mesh.name)) mesh.setEnabled(false);
      if (!authoredShell && /^coffin_(body|band)/.test(mesh.name)) mesh.setEnabled(false);
    }
    // Four separate walls and a low bed leave a genuine open cavity.
    const shell = b.root("coffin_open_shell", authoredShell ? xyz(centre) : hallAt([0, 0, -5.9]));
    if (!authoredShell) {
      b.box(shell, "coffin_bed", [1.96, 0.045, 0.66], [0, 0.7, 0], timber);
      for (const z of [-0.335, 0.335])
        b.box(shell, "coffin_side_wall", [2, 0.48, 0.03], [0, 0.88, z], timber);
      for (const x of [-0.985, 0.985])
        b.box(shell, "coffin_end_wall", [0.03, 0.48, 0.7], [x, 0.88, 0], timber);
    }
    const gilt = b.mat("coffin_rim_brass", "#8c7134", 0.54, 0.7);
    if (!authoredShell) {
      for (const z of [-0.34, 0.34])
        b.box(shell, "coffin_rim_rail", [2.02, 0.025, 0.035], [0, 1.115, z], gilt);
      for (const x of [-1, 1])
        b.box(shell, "coffin_end_rail", [0.035, 0.025, 0.7], [x, 1.115, 0], gilt);
    }
    const underside = b.surface("coffin_lid_inner", "#352319", "wood");
    const length = coffin ? coffin.max.x - coffin.min.x : 2.0;
    const width = coffin ? coffin.max.z - coffin.min.z : 0.7;
    b.box(
      lid,
      "coffin_lid_inner_board",
      [length + 0.06, 0.025, width + 0.04],
      [0, -0.016, width / 2],
      underside,
    );
    for (const x of [-0.35, 0.35])
      b.box(
        lid,
        "coffin_lid_inner_brace",
        [0.045, 0.035, width],
        [x * length, -0.045, width / 2],
        underside,
      );
    // Where Sora takes hold of the lid to close it: the front edge, towards the foot.
    this.closeGrip = b.root(
      "coffin_close_grip",
      coffin
        ? xyz(new Vector3(centre.x + 0.65, top + 0.01, coffin.max.z + 0.02))
        : hallAt([0.65, 1.13, -5.53]),
    );
    b.box(this.closeGrip, "coffin_close_handle", [0.28, 0.035, 0.045], [0, 0, 0], gilt);
    area.container.transformNodes.push(shell, this.closeGrip);
    // Sok lies on the padding: 3 cm of floor and 2 cm of cotton over the coffin's bottom.
    this.root = b.root(
      "sok_funeral_body",
      coffin ? xyz(new Vector3(centre.x, coffin.min.y + 0.05, centre.z)) : hallAt([0, 0.725, -5.9]),
    );
    const authoredLining = area.container.materials.find(
      (material) => material.name === "M_funeral_lining",
    );
    const dark =
      authoredLining instanceof PBRMaterial ? authoredLining : b.mat("coffin_lining", "#211b15", 1);
    if (!authoredShell) {
      b.box(this.root, "coffin_inner_padding", [1.88, 0.018, 0.61], [0, 0, 0], dark);
      for (const z of [-0.305, 0.305])
        b.box(this.root, "coffin_inner_rim", [1.96, 0.035, 0.017], [0, 0.015, z], dark);
    }
    // Everything a pose can reach: the cavity and what rises out of it, up to the lifted lotus.
    const lo = coffin ? coffin.min : inHall(-1.04, 0.69, -0.5);
    const hi = coffin ? coffin.max.add(new Vector3(0, 0.98, 0)) : inHall(1.04, 2.1, 0.65);
    for (const x of [lo.x - 0.04, hi.x + 0.04])
      for (const y of [lo.y, hi.y])
        for (const z of [lo.z - 0.04, hi.z + 0.04]) this.bounds.push(new Vector3(x, y, z));
    this.head = coffin
      ? new Vector3(centre.x + 0.58, top - 0.12, centre.z)
      : inHall(0.72, 1.0, -5.9);
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
    const target = this.head;
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

/** The world-space box round `meshes`. */
function worldBounds(meshes: readonly AbstractMesh[]): { min: Vector3; max: Vector3 } {
  const min = new Vector3(Infinity, Infinity, Infinity),
    max = new Vector3(-Infinity, -Infinity, -Infinity);
  for (const mesh of meshes) {
    mesh.computeWorldMatrix(true);
    const box = mesh.getBoundingInfo().boundingBox;
    min.minimizeInPlace(box.minimumWorld);
    max.maximizeInPlace(box.maximumWorld);
  }
  return { min, max };
}

function xyz(v: Vector3): [number, number, number] {
  return [v.x, v.y, v.z];
}
