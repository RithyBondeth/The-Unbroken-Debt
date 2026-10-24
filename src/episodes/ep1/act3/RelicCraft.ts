import type { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { CreateTube } from "@babylonjs/core/Meshes/Builders/tubeBuilder";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { seededRandom } from "../../../audio/synth";

type XYZ = readonly [number, number, number];
/** Small real-scale prop primitives with deterministic surface wear. */
export class RelicCraft {
  readonly meshes: Mesh[] = [];
  constructor(readonly scene: Scene) {}
  root(name: string, at: XYZ, parent?: TransformNode): TransformNode {
    const n = new TransformNode(name, this.scene);
    n.position.set(...at);
    if (parent) n.parent = parent;
    return n;
  }
  mat(name: string, color: string, roughness = 0.8, metallic = 0): PBRMaterial {
    const m = new PBRMaterial(`M_relic_${name}`, this.scene);
    m.albedoColor = Color3.FromHexString(color);
    m.roughness = roughness;
    m.metallic = metallic;
    m.maxSimultaneousLights = 8;
    return m;
  }
  finish(mesh: Mesh, parent: TransformNode, at: XYZ, mat: PBRMaterial): Mesh {
    mesh.parent = parent;
    mesh.position.set(...at);
    mesh.material = mat;
    this.meshes.push(mesh);
    return mesh;
  }
  box(parent: TransformNode, name: string, size: XYZ, at: XYZ, mat: PBRMaterial): Mesh {
    return this.finish(
      CreateBox(name, { width: size[0], height: size[1], depth: size[2] }, this.scene),
      parent,
      at,
      mat,
    );
  }
  sphere(parent: TransformNode, name: string, size: XYZ, at: XYZ, mat: PBRMaterial): Mesh {
    const m = this.finish(
      CreateSphere(name, { diameter: 1, segments: 24 }, this.scene),
      parent,
      at,
      mat,
    );
    m.scaling.set(...size);
    return m;
  }
  cylinder(
    parent: TransformNode,
    name: string,
    diameter: number,
    height: number,
    at: XYZ,
    mat: PBRMaterial,
  ): Mesh {
    return this.finish(
      CreateCylinder(name, { diameter, height, tessellation: 64 }, this.scene),
      parent,
      at,
      mat,
    );
  }
  ring(
    parent: TransformNode,
    name: string,
    diameter: number,
    thickness: number,
    at: XYZ,
    mat: PBRMaterial,
  ): Mesh {
    return this.finish(
      CreateTorus(name, { diameter, thickness, tessellation: 64 }, this.scene),
      parent,
      at,
      mat,
    );
  }
  tube(parent: TransformNode, name: string, path: XYZ[], radius: number, mat: PBRMaterial): Mesh {
    return this.finish(
      CreateTube(
        name,
        { path: path.map((p) => new Vector3(...p)), radius, tessellation: 10, cap: Mesh.CAP_ALL },
        this.scene,
      ),
      parent,
      [0, 0, 0],
      mat,
    );
  }
  painted(name: string, paint: (c: CanvasRenderingContext2D) => void, size = 512): DynamicTexture {
    const t = new DynamicTexture(`T_relic_${name}`, size, this.scene, true);
    paint(t.getContext() as CanvasRenderingContext2D);
    t.update();
    return t;
  }
  surface(
    name: string,
    color: string,
    kind: "wood" | "cloth" | "metal" | "skin" | "paper",
  ): PBRMaterial {
    const m = this.mat(
      name,
      "#ffffff",
      kind === "metal" ? 0.65 : 0.92,
      kind === "metal" ? 0.72 : 0,
    );
    m.albedoTexture = this.painted(name, (c) => {
      const r = seededRandom(1380 + name.length);
      c.fillStyle = color;
      c.fillRect(0, 0, 512, 512);
      if (kind === "wood")
        for (let i = 0; i < 750; i++) {
          const x = r() * 512;
          c.strokeStyle = `rgba(${r() > 0.5 ? "210,173,116" : "12,13,11"},${0.06 + r() * 0.18})`;
          c.lineWidth = 0.4 + r();
          c.beginPath();
          c.moveTo(x, 0);
          c.bezierCurveTo(x + 8, 170, x - 12, 330, x + 2, 512);
          c.stroke();
        }
      if (kind === "cloth")
        for (let i = 0; i < 512; i += 3) {
          c.fillStyle = "rgba(20,18,14,.13)";
          c.fillRect(i, 0, 1, 512);
          c.fillRect(0, i, 512, 1);
          c.fillStyle = "rgba(225,217,192,.12)";
          c.fillRect(i + 1, 0, 1, 512);
          c.fillRect(0, i + 1, 512, 1);
        }
      for (let i = 0; i < 1800; i++) {
        c.fillStyle =
          kind === "metal" ? `rgba(30,46,34,${r() * 0.18})` : `rgba(17,14,10,${r() * 0.06})`;
        c.beginPath();
        c.ellipse(
          r() * 512,
          r() * 512,
          0.5 + r() * (kind === "metal" ? 8 : 3),
          0.5 + r() * 3,
          r() * 6,
          0,
          Math.PI * 2,
        );
        c.fill();
      }
      if (kind === "metal")
        for (let i = 0; i < 180; i++) {
          c.strokeStyle = "rgba(218,192,133,.2)";
          c.lineWidth = 0.5;
          const x = r() * 512,
            y = r() * 512;
          c.beginPath();
          c.moveTo(x, y);
          c.lineTo(x + r() * 20, y + 2);
          c.stroke();
        }
    });
    return m;
  }
}
