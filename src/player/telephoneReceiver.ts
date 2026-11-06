import type { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateLathe } from "@babylonjs/core/Meshes/Builders/latheBuilder";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { CreateCylinder } from "@babylonjs/core/Meshes/Builders/cylinderBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** The same single-ear magneto receiver on its hook and in Sora's hand. Metres, Y up. */
export function createTelephoneReceiver(scene: Scene, name: string): TransformNode {
  const root = new TransformNode(name, scene);
  const rubber = new PBRMaterial(`${name}_ebonite`, scene);
  rubber.albedoColor = Color3.FromHexString("#38362f").toLinearSpace();
  rubber.metallic = 0.08;
  rubber.roughness = 0.36;
  rubber.clearCoat.isEnabled = true;
  rubber.clearCoat.intensity = 0.22;
  const brass = new PBRMaterial(`${name}_nickel_brass`, scene);
  brass.albedoColor = Color3.FromHexString("#998967").toLinearSpace();
  brass.metallic = 0.7;
  brass.roughness = 0.45;
  for (const mat of [rubber, brass]) mat.maxSimultaneousLights = 8;
  const lathe = (part: string, profile: number[][], at: number[], material = rubber) => {
    const mesh = CreateLathe(
      `${name}_${part}`,
      { shape: profile.map(([r, y]) => new Vector3(r, y, 0)), tessellation: 48 },
      scene,
    );
    mesh.parent = root;
    mesh.position.set(at[0], at[1], at[2]);
    mesh.material = material;
    return mesh;
  };
  lathe(
    "turned_grip",
    [
      [0, -0.102],
      [0.009, -0.102],
      [0.015, -0.094],
      [0.018, -0.079],
      [0.016, -0.063],
      [0.013, -0.044],
      [0.013, 0.034],
      [0.017, 0.056],
      [0.021, 0.069],
      [0.021, 0.089],
      [0, 0.094],
    ],
    [0, 0, 0],
  );
  const cup = lathe(
    "ear_shell",
    [
      [0, -0.012],
      [0.023, -0.012],
      [0.039, 0],
      [0.048, 0.016],
      [0.051, 0.033],
      [0.05, 0.043],
      [0.044, 0.046],
      [0.04, 0.036],
      [0, 0.032],
    ],
    [0, 0.092, 0],
  );
  cup.rotation.x = Math.PI / 2;
  // Keep the listening cup in proportion to an adult hand; its neck still
  // meets the original grip while the shell is an 80 mm earpiece.
  cup.scaling.setAll(0.8);
  for (const y of [-0.087, -0.061, 0.058]) {
    const band = CreateTorus(
      `${name}_grip_collar`,
      { diameter: y > 0 ? 0.036 : 0.032, thickness: 0.002, tessellation: 40 },
      scene,
    );
    band.parent = root;
    band.position.y = y;
    band.material = brass;
  }
  const rim = CreateTorus(
    `${name}_ear_rim`,
    { diameter: 0.0752, thickness: 0.002, tessellation: 48 },
    scene,
  );
  rim.parent = root;
  rim.position.set(0, 0.092, 0.0352);
  rim.rotation.x = Math.PI / 2;
  rim.material = brass;
  const socket = lathe(
    "cord_socket",
    [
      [0.007, -0.009],
      [0.007, 0],
      [0.011, 0.003],
      [0.011, 0.009],
    ],
    [0, -0.106, 0],
    brass,
  );
  socket.rotation.z = Math.PI;
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2;
    const hole = CreateCylinder(
      `${name}_ear_perforation`,
      { diameter: 0.0032, height: 0.0008, tessellation: 12 },
      scene,
    );
    hole.parent = root;
    hole.position.set(Math.cos(a) * 0.0152, 0.092 + Math.sin(a) * 0.0152, 0.0264);
    hole.rotation.x = Math.PI / 2;
    hole.material = rubber;
  }
  // Two draw calls, shared geometry proportions in both presentations.
  for (const material of [rubber, brass]) {
    const parts = root
      .getChildMeshes()
      .filter((m): m is Mesh => m instanceof Mesh && m.material === material);
    const merged = Mesh.MergeMeshes(parts, true, true)!;
    merged.name = `${name}_${material === rubber ? "body" : "fittings"}`;
    merged.setParent(root);
    merged.isPickable = false;
  }
  return root;
}
