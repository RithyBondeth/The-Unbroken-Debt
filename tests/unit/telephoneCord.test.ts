import { afterEach, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import { TelephoneCord } from "../../src/player/TelephoneCord";

const engines: NullEngine[] = [];
afterEach(() => {
  for (const engine of engines.splice(0)) engine.dispose();
});

function setup() {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine);
  const phone = new TransformNode("phone", scene);
  phone.position.set(2.75, 3.7, -17.2);
  phone.rotation.y = Math.PI / 2;
  const terminal = new TransformNode("terminal", scene);
  terminal.parent = phone;
  terminal.position.set(-0.005, -0.149, 0.092);
  const receiver = new TransformNode("receiver", scene);
  receiver.parent = phone;
  receiver.position.set(-0.103, 0.16, 0);
  const rest = new TransformNode("rest", scene);
  rest.parent = receiver;
  rest.position.z = 0.17;
  const cord = new TelephoneCord(scene, "cord", terminal, rest, new PBRMaterial("cloth", scene));
  return { scene, phone, terminal, receiver, rest, cord };
}

function expectConnected(mesh: AbstractMesh, at: Vector3) {
  const vertices = mesh.getVerticesData("position")!;
  let distance = Infinity;
  for (let i = 0; i < vertices.length; i += 3)
    distance = Math.min(distance, Vector3.Distance(at, Vector3.FromArray(vertices, i)));
  expect(distance).toBeLessThan(0.00001);
  expect(vertices.every(Number.isFinite)).toBe(true);
}

it("keeps the lead connected while the receiver is lifted, moved and returned to its hook", () => {
  const { scene, terminal, receiver, rest, cord } = setup();
  const mesh = scene.getMeshByName("cord")!;
  expectConnected(mesh, terminal.getAbsolutePosition());
  expectConnected(mesh, rest.getAbsolutePosition());
  receiver.setEnabled(false);
  for (const hand of [new Vector3(2.1, 4, -17), new Vector3(1.9, 3.9, -17.4)]) {
    cord.update(hand);
    expect(mesh.isEnabled()).toBe(true);
    expectConnected(mesh, terminal.getAbsolutePosition());
    expectConnected(mesh, hand);
  }
  receiver.setEnabled(true);
  cord.update(null);
  expectConnected(mesh, rest.getAbsolutePosition());
  expect(scene.getMeshByName("cord")).toBe(mesh);
  expect(scene.meshes).toHaveLength(1);
  expect(mesh.isPickable).toBe(false);
});

it("refreshes both endpoints when the telephone moves even if the held receiver stays still", () => {
  const { scene, phone, terminal, cord } = setup();
  const hand = new Vector3(2, 4, -17);
  cord.update(hand);
  phone.position.x += 0.4;
  cord.update(hand);
  expectConnected(scene.getMeshByName("cord")!, terminal.getAbsolutePosition());
  expectConnected(scene.getMeshByName("cord")!, hand);
});
