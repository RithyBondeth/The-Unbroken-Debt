import type { Scene } from "@babylonjs/core/scene";
import type { Area } from "../../../core/AreaLoader";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { PhysicsBody } from "@babylonjs/core/Physics/v2/physicsBody";
import { PhysicsShapeBox } from "@babylonjs/core/Physics/v2/physicsShape";
import { PhysicsMotionType } from "@babylonjs/core/Physics/v2/IPhysicsEnginePlugin";
import { seededRandom } from "../../../audio/synth";
import { WARDROBES } from "../data/walker";
import { ShadowFigure } from "../entities/ShadowFigure";

export interface HidingWardrobe {
  id: string;
  root: TransformNode;
  doors: TransformNode[];
  front: Vector3;
  yaw: number;
  open: number;
}

/** Physical louvred wardrobes and the shrine's ancestral effigy in the hallway. */
export class WalkerModels {
  readonly wardrobes: HidingWardrobe[] = [];
  readonly walker: TransformNode;
  readonly meshes: Mesh[] = [];
  private readonly wood: PBRMaterial;
  private readonly edge: PBRMaterial;
  private readonly brass: PBRMaterial;
  private form!: ShadowFigure;

  constructor(
    private readonly scene: Scene,
    area: Area,
  ) {
    this.wood = this.material("wardrobe_teak", "#ffffff", 0.84);
    this.edge = this.material("wardrobe_trim", "#3d291e", 0.74);
    this.brass = this.material("walker_brass", "#8d7950", 0.67, 0.72);
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
    this.walker.rotation.y = Math.atan2(direction.x, direction.z);
    this.form.animate(time, 1);
  }

  private material(name: string, hex: string, roughness: number, metallic = 0): PBRMaterial {
    const m = new PBRMaterial(`M_${name}`, this.scene);
    m.albedoColor = Color3.FromHexString(hex).toLinearSpace();
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

  private makeWalker(): void {
    this.form = new ShadowFigure(this.scene, "walker", 2.3);
    this.form.root.parent = this.walker;
    this.meshes.push(...this.form.meshes);
  }
}
