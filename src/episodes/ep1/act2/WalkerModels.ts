import type { Scene } from "@babylonjs/core/scene";
import type { Area } from "../../../core/AreaLoader";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreateLathe } from "@babylonjs/core/Meshes/Builders/latheBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsShapeBox } from "@babylonjs/core/Physics/v2/physicsShape";
import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { seededRandom } from "../../../audio/synth";
import { WARDROBES } from "../data/walker";

export interface HidingWardrobe {
  id: string;
  root: TransformNode;
  doors: TransformNode[];
  front: Vector3;
  yaw: number;
  open: number;
}

/** Physical louvred wardrobes and a shadow whose brass face catches the player's lamp. */
export class WalkerModels {
  readonly wardrobes: HidingWardrobe[] = [];
  readonly walker: TransformNode;
  readonly meshes: Mesh[] = [];
  private readonly wood: PBRMaterial;
  private readonly edge: PBRMaterial;
  private readonly brass: PBRMaterial;
  private readonly shadow: PBRMaterial;

  constructor(
    private readonly scene: Scene,
    area: Area,
  ) {
    this.wood = this.material("wardrobe_teak", "#ffffff", 0.84);
    this.edge = this.material("wardrobe_trim", "#3d291e", 0.74);
    this.brass = this.material("walker_brass", "#8d7950", 0.67, 0.72);
    this.shadow = this.material("walker_cloth", "#080c0f", 0.99);
    this.shadow.emissiveColor = new Color3(0.002, 0.003, 0.004);
    const tex = new DynamicTexture("T_wardrobe_teak", 512, scene, true),
      c = tex.getContext(),
      rand = seededRandom(906);
    c.fillStyle = "#5b4030";
    c.fillRect(0, 0, 512, 512);
    for (let k = 0; k < 1100; k++) {
      c.fillStyle = `rgba(${rand() > 0.5 ? "156,119,78" : "18,16,12"},${rand() * 0.13})`;
      c.fillRect(rand() * 512, 0, rand() * 1.5 + 0.3, 512);
    }
    tex.update();
    this.wood.albedoTexture = tex;
    for (const id of ["H1", "H2"]) {
      scene.getMeshByName(`hide_wardrobe_${id}`)?.setEnabled(false);
      const old = scene.getTransformNodeByName(`col_wardrobe_${id}_body`),
        shape = old?.physicsBody?.shape;
      old?.physicsBody?.dispose();
      shape?.dispose();
      old?.dispose();
    }
    for (const spot of WARDROBES) this.makeWardrobe(spot.id, spot.at, spot.yaw);
    this.walker = new TransformNode("hallway_walker", scene);
    this.makeWalker();
    this.walker.setEnabled(false);
    area.container.meshes.push(...this.meshes);
    area.container.transformNodes.push(
      this.walker,
      ...this.wardrobes.flatMap((w) => [w.root, ...w.doors]),
    );
  }

  animate(dt: number, opening: string | null): void {
    for (const w of this.wardrobes) {
      w.open += ((opening === w.id ? 1 : 0) - w.open) * (1 - Math.exp(-dt * 9));
      w.doors[0].rotation.y = -w.open * 1.15;
      w.doors[1].rotation.y = w.open * 1.15;
    }
  }

  pose(at: Vector3, direction: Vector3, time: number): void {
    this.walker.position.copyFrom(at);
    this.walker.position.y += Math.sin(time * 3) * 0.012;
    this.walker.rotation.y = Math.atan2(direction.x, direction.z);
    this.walker.rotation.z = Math.sin(time * 2.2) * 0.018;
  }

  private material(name: string, hex: string, roughness: number, metallic = 0): PBRMaterial {
    const m = new PBRMaterial(`M_${name}`, this.scene);
    m.albedoColor = Color3.FromHexString(hex);
    m.roughness = roughness;
    m.metallic = metallic;
    m.maxSimultaneousLights = 8;
    return m;
  }

  private box(
    root: TransformNode,
    name: string,
    size: number[],
    at: number[],
    mat: PBRMaterial,
  ): Mesh {
    const m = CreateBox(name, { width: size[0], height: size[1], depth: size[2] }, this.scene);
    m.parent = root;
    m.position.set(at[0], at[1], at[2]);
    m.material = mat;
    this.meshes.push(m);
    return m;
  }

  private solid(root: TransformNode, name: string, size: number[], at: number[]): void {
    root.computeWorldMatrix(true);
    const anchor = new TransformNode(name, this.scene);
    anchor.position.copyFrom(
      Vector3.TransformCoordinates(Vector3.FromArray(at), root.getWorldMatrix()),
    );
    anchor.rotation.y = root.rotation.y;
    anchor.metadata = { surface: "teak" };
    const body = new PhysicsBody(anchor, PhysicsMotionType.STATIC, false, this.scene);
    body.shape = new PhysicsShapeBox(
      Vector3.Zero(),
      Quaternion.Identity(),
      Vector3.FromArray(size),
      this.scene,
    );
  }

  private makeWardrobe(id: string, at: Vector3, yaw: number): void {
    const root = new TransformNode(`interact_wardrobe_${id}`, this.scene);
    root.position.copyFrom(at);
    root.rotation.y = yaw;
    this.box(root, `${id}_back`, [0.96, 2.1, 0.06], [0, 1.05, -0.37], this.wood);
    for (const x of [-0.45, 0.45]) {
      this.box(root, `${id}_side`, [0.06, 2.1, 0.8], [x, 1.05, 0], this.wood);
      this.solid(root, `${id}_side_body_${x}`, [0.06, 2.1, 0.8], [x, 1.05, 0]);
    }
    this.solid(root, `${id}_back_body`, [0.96, 2.1, 0.06], [0, 1.05, -0.37]);
    this.solid(root, `${id}_front_body`, [0.9, 2.1, 0.035], [0, 1.05, 0.42]);
    for (const y of [0.035, 2.075])
      this.box(root, `${id}_cap`, [1.02, 0.07, 0.86], [0, y, 0], this.edge);
    this.box(root, `${id}_lintel`, [1.04, 0.075, 0.9], [0, 2.14, 0], this.edge);
    const doors: TransformNode[] = [];
    for (const side of [-1, 1]) {
      const hinge = new TransformNode(`${id}_door_${side}`, this.scene);
      hinge.parent = root;
      hinge.position.set(side * 0.444, 0, 0.405);
      doors.push(hinge);
      const dx = -side * 0.222;
      for (const x of [dx - 0.205, dx + 0.205])
        this.box(hinge, `${id}_door_stile`, [0.036, 1.97, 0.035], [x, 1.055, 0], this.edge);
      this.box(hinge, `${id}_lower_panel`, [0.38, 0.91, 0.026], [dx, 0.545, 0], this.wood);
      for (const y of [0.095, 1.02, 1.96])
        this.box(hinge, `${id}_rail`, [0.42, 0.04, 0.04], [dx, y, 0], this.edge);
      const slats: Mesh[] = [];
      for (let k = 0; k < 14; k++) {
        const slat = this.box(
          hinge,
          `${id}_louvre_${k}`,
          [0.378, 0.045, 0.025],
          [dx, 1.095 + k * 0.061, 0],
          this.wood,
        );
        slat.rotation.x = 0.13;
        slats.push(slat);
      }
      // All louvres share one material and move with one hinge: one draw per door.
      const merged = Mesh.MergeMeshes(slats, true, true);
      if (merged) {
        merged.name = `${id}_door_louvres_${side}`;
        merged.setParent(hinge, true);
        for (const slat of slats) this.meshes.splice(this.meshes.indexOf(slat), 1);
        this.meshes.push(merged);
      }
      this.box(
        hinge,
        `${id}_handle`,
        [0.015, 0.11, 0.03],
        [dx - side * 0.155, 1.02, 0.029],
        this.brass,
      );
    }
    const front = at.add(new Vector3(Math.sin(yaw) * 1.1, 0, Math.cos(yaw) * 1.1));
    this.wardrobes.push({ id, root, doors, front, yaw, open: 0 });
  }

  private sphere(name: string, size: number[], at: number[], mat: PBRMaterial): Mesh {
    const m = CreateSphere(name, { diameter: 1, segments: 16 }, this.scene);
    m.parent = this.walker;
    m.scaling.set(size[0], size[1], size[2]);
    m.position.set(at[0], at[1], at[2]);
    m.material = mat;
    this.meshes.push(m);
    return m;
  }

  private makeWalker(): void {
    const robe = CreateLathe(
      "walker_robe",
      {
        shape: [
          [0.38, 0.03],
          [0.4, 0.2],
          [0.27, 1.1],
          [0.34, 1.7],
          [0.18, 1.97],
        ].map(([r, y]) => new Vector3(r, y, 0)),
        tessellation: 40,
        closed: true,
      },
      this.scene,
    );
    robe.parent = this.walker;
    robe.material = this.shadow;
    this.meshes.push(robe);
    this.sphere("walker_hood", [0.43, 0.6, 0.36], [0, 2.05, 0], this.shadow);
    this.sphere("walker_mask", [0.3, 0.45, 0.13], [0, 2.08, 0.17], this.brass);
    this.sphere("walker_nose", [0.055, 0.15, 0.07], [0, 2.08, 0.25], this.brass);
    for (const side of [-1, 1]) {
      this.sphere("walker_eye", [0.075, 0.029, 0.025], [side * 0.068, 2.15, 0.237], this.shadow);
      const arm = CreateTube(
        "walker_arm",
        {
          path: [
            new Vector3(side * 0.27, 1.76, 0),
            new Vector3(side * 0.4, 1.19, 0.02),
            new Vector3(side * 0.38, 0.68, 0.13),
          ],
          radius: 0.075,
          tessellation: 12,
        },
        this.scene,
      );
      arm.parent = this.walker;
      arm.material = this.shadow;
      this.meshes.push(arm);
      for (let k = 0; k < 3; k++)
        this.sphere(
          "walker_finger",
          [0.018, 0.17, 0.023],
          [side * (0.35 + k * 0.027), 0.59, 0.15],
          this.shadow,
        );
    }
    this.sphere("walker_mouth", [0.1, 0.018, 0.02], [0, 1.96, 0.235], this.shadow);
    for (const side of [-1, 1])
      this.sphere("walker_foot", [0.16, 0.09, 0.32], [side * 0.14, 0.045, 0.075], this.shadow);
    for (const mesh of this.walker.getChildMeshes()) mesh.isPickable = false;
  }
}
