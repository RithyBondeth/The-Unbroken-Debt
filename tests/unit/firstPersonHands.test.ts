import { readFileSync } from "node:fs";
import { decodeHandAsset } from "../../src/player/HandAsset";
import { VertexData } from "@babylonjs/core/Meshes/mesh.vertexData";
import { afterEach, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { FirstPersonHands } from "../../src/player/FirstPersonHands";
const asset = decodeHandAsset(
  new Uint8Array(readFileSync("public/assets/shared/sora_hand.mesh")).buffer,
);
const engines: NullEngine[] = [];
afterEach(() => {
  for (const engine of engines.splice(0)) engine.dispose();
});
function setup() {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine);
  const camera = new UniversalCamera("eye", Vector3.Zero(), scene);
  const hands = new FirstPersonHands(scene, camera);
  hands.initialize(asset);
  const lamp = new TransformNode("lamp", scene);
  lamp.parent = camera;
  lamp.position.set(-0.26, -0.27, 0.58);
  lamp.rotation.y = Math.PI;
  hands.attachLamp(lamp);
  return { scene, hands, lamp, camera };
}
it("keeps the exploration view clear and first-person meshes out of world picking", () => {
  const { hands, lamp } = setup();
  hands.update(0.016, false, null, 2);
  expect(hands.left.isEnabled()).toBe(true);
  expect(hands.right.isEnabled()).toBe(false);
  expect(lamp.isEnabled()).toBe(true);
  expect(hands.meshes.every((m) => !m.isPickable && m.renderingGroupId === 1)).toBe(true);
  expect(hands.meshes.length).toBeLessThan(10);
});
it("strikes a visible match, then stows it without leaving a permanent flame", () => {
  const { hands, scene } = setup();
  hands.animate("strike");
  hands.update(0.3, false, null, 0);
  expect(hands.right.isEnabled()).toBe(true);
  expect(scene.getMeshByName("sora_match_flame")!.isEnabled()).toBe(true);
  hands.animate("reach"); // An interaction cannot interrupt the strike.
  hands.update(0.6, false, null, 0);
  expect(hands.right.isEnabled()).toBe(false);
  expect(scene.getMeshByName("sora_match_flame")!.isEnabled()).toBe(false);
});
it("stows an unlit lamp and restores the carrying pose only while presented", () => {
  const { hands, lamp, scene } = setup();
  let presented = false;
  hands.attachLamp(lamp, () => presented);
  hands.update(0.016, false, null, 0);
  expect(lamp.isEnabled() || hands.left.isEnabled()).toBe(false);
  presented = true;
  hands.update(0.016, false, null, 0);
  expect(lamp.isEnabled() && hands.left.isEnabled()).toBe(true);
  presented = false;
  hands.update(0.016, false, null, 0);
  expect(lamp.isEnabled() || hands.left.isEnabled()).toBe(false);
  const book = new TransformNode("book", scene);
  hands.update(0.016, false, book, 0);
  expect(hands.left.isEnabled() && hands.right.isEnabled()).toBe(true);
  expect(lamp.isEnabled()).toBe(false);
  hands.update(0.016, false, null, 0);
  expect(lamp.isEnabled() || hands.left.isEnabled()).toBe(false);
});
it("puts away the lamp for calls and restores it when the call ends", () => {
  const { hands, lamp } = setup();
  hands.holdPhone(true);
  hands.update(0.016, true, null, 0);
  expect(hands.right.isEnabled()).toBe(true);
  expect(hands.left.isEnabled()).toBe(false);
  expect(lamp.isEnabled()).toBe(false);
  hands.holdPhone(false);
  hands.update(0.016, false, null, 0);
  expect(lamp.isEnabled()).toBe(true);
  expect(hands.right.isEnabled()).toBe(false);
});
it("supports the book and hides hands and lamp during hiding or overlays", () => {
  const { hands, lamp, scene } = setup();
  const book = new TransformNode("book", scene);
  hands.update(0.016, false, book, 0);
  expect(hands.left.isEnabled() && hands.right.isEnabled()).toBe(true);
  expect(lamp.isEnabled()).toBe(false);
  hands.update(0.016, true, null, 0);
  expect(hands.left.isEnabled() || hands.right.isEnabled() || lamp.isEnabled()).toBe(false);
});
it("keeps the lamp grip attached when the camera rotates and moves", () => {
  const { hands, camera, lamp } = setup();
  camera.position.set(30, 2, -18);
  camera.rotation.y = 2;
  hands.update(0.016, false, null, 0);
  const expected = Vector3.TransformCoordinates(
    new Vector3(-0.005, 0.24, -0.005),
    lamp.computeWorldMatrix(true),
  );
  const actual = Vector3.TransformCoordinates(Vector3.Zero(), hands.left.computeWorldMatrix(true));
  expect(Vector3.Distance(actual, expected)).toBeLessThan(0.0001);
});
it("blends authored anatomical poses on the GPU without rebuilding meshes", () => {
  const { hands, scene } = setup();
  const count = scene.meshes.length,
    rig = hands.rightRig;
  rig.update(0.016, "phone");
  const early = rig.poseWeights[2];
  for (let i = 0; i < 40; i++) rig.update(0.016, "phone");
  expect(early).toBeGreaterThan(0);
  expect(early).toBeLessThan(rig.poseWeights[2]);
  expect(rig.poseWeights[2]).toBeGreaterThan(0.99);
  for (let i = 0; i < 40; i++) rig.update(0.016, "journal");
  expect(rig.poseWeights[3]).toBeGreaterThan(0.99);
  expect(rig.poseWeights[2]).toBeLessThan(0.01);
  expect(rig.poseWeights.reduce((a, b) => a + b, 0)).toBeCloseTo(1);
  expect(scene.meshes.length).toBe(count);
  expect(rig.skin.morphTargetManager?.numTargets).toBe(6);
});
it("follows lamp raising without turning the hand around with the gauge", () => {
  const { hands, lamp } = setup();
  lamp.rotation.set(-0.2, Math.PI + 0.3, 0.07);
  hands.update(0.016, false, null, 0);
  expect(hands.left.rotation.x).toBeCloseTo(-0.2);
  expect(hands.left.rotation.y).toBeCloseTo(0.3);
  expect(hands.left.rotation.z).toBeCloseTo(0.07);
});

it("keeps skin surface winding aligned with its lighting normals", () => {
  const { hands } = setup();
  const mesh = hands.leftRig.skin;
  const computed: number[] = [];
  VertexData.ComputeNormals(mesh.getVerticesData("position")!, mesh.getIndices()!, computed);
  const normal = mesh.getVerticesData("normal")!;
  // UV seams duplicate boundary vertices, so test the averaged agreement over the surface.
  let agreement = 0,
    total = 0;
  for (let at = 0; at < normal.length; at += 3) {
    const dot =
      computed[at] * normal[at] +
      computed[at + 1] * normal[at + 1] +
      computed[at + 2] * normal[at + 2];
    if (Number.isFinite(dot)) {
      agreement += dot;
      total++;
    }
  }
  expect(agreement / total).toBeGreaterThan(0.9);
});
it("ships a textured anatomical mesh and rejects incomplete asset data", () => {
  expect(asset.vertexCount).toBeGreaterThan(5000);
  expect(asset.uvs.length).toBe(asset.vertexCount * 2);
  expect(Object.keys(asset.poses)).toHaveLength(6);
  expect(asset.poses.phone.positions).not.toEqual(asset.poses.journal.positions);
  expect(() => decodeHandAsset(new ArrayBuffer(12))).toThrow("Invalid Sora");
});
it("closes the lamp grip instead of retaining the open hand's finger and thumb splay", () => {
  const span = (positions: Float32Array) => {
    let min = Infinity,
      max = -Infinity;
    for (let i = 0; i < positions.length; i += 3) {
      if (positions[i + 1] <= 0) continue; // Exclude the wider forearm.
      min = Math.min(min, positions[i]);
      max = Math.max(max, positions[i]);
    }
    return max - min;
  };
  expect(span(asset.poses.lamp.positions)).toBeLessThan(span(asset.poses.reach.positions) * 0.72);
});
