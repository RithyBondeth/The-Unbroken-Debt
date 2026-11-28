import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it } from "vitest";
import HavokPhysics from "@babylonjs/havok";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { HavokPlugin } from "@babylonjs/core/Physics/v2/Plugins/havokPlugin";
import "@babylonjs/core/Physics/joinedPhysicsEngineComponent";
import { addStaticBox, GRAVITY } from "@/core/physics";
import { PlayerController } from "@/player/PlayerController";
import type { InputSource } from "@/player/InputSource";
import type { MoveIntent } from "@/player/movement";

/** Walks forward while `walk` is set; never looks. */
class Script implements InputSource {
  walk = false;
  readMove(out: MoveIntent): MoveIntent {
    out.x = 0;
    out.z = this.walk ? 1 : 0;
    out.hurry = false;
    out.crouch = false;
    return out;
  }
  consumeLook(out: { yaw: number; pitch: number }): void {
    out.yaw = 0;
    out.pitch = 0;
  }
  dispose(): void {}
}

const engines: NullEngine[] = [];
afterEach(() => {
  for (const engine of engines.splice(0)) engine.dispose();
});

async function setup() {
  const engine = new NullEngine();
  engines.push(engine);
  engine.getDeltaTime = () => 1000 / 60;
  const scene = new Scene(engine);
  const wasm = readFileSync("node_modules/@babylonjs/havok/lib/esm/HavokPhysics.wasm");
  const havok = await HavokPhysics({ wasmBinary: new Uint8Array(wasm).buffer });
  scene.enablePhysics(GRAVITY.clone(), new HavokPlugin(false, havok));
  scene.getPhysicsEngine()!.setTimeStep(1 / 60);
  const floor = CreateBox("floor", { width: 20, depth: 20, height: 0.2 }, scene);
  floor.position.y = -0.1;
  addStaticBox(floor, "teak");
  const camera = new UniversalCamera("eye", new Vector3(0, 1.6, 0), scene);
  scene.activeCamera = camera;
  const input = new Script();
  const player = new PlayerController(scene, camera, input, new Vector3(0, 0, 0));
  return { scene, camera, input, player };
}

describe("PlayerController on flat ground (real Havok)", () => {
  it("stops where the player lets go, instead of creeping on", async () => {
    const { scene, input, player } = await setup();
    for (let frame = 0; frame < 150; frame++) {
      input.walk = frame > 30 && frame < 120;
      scene.render();
    }
    const stopped = player.feet;
    for (let frame = 0; frame < 300; frame++) scene.render();
    expect(Vector3.Distance(player.feet, stopped)).toBeLessThan(0.002);
    expect(player.speed).toBeLessThan(0.01);
  });

  it("walks at a steady speed, not one that flips every frame", async () => {
    const { scene, input, player } = await setup();
    input.walk = true;
    const steps: number[] = [];
    let last = player.feet.z;
    for (let frame = 0; frame < 120; frame++) {
      scene.render();
      const z = player.feet.z;
      if (frame > 60) steps.push((z - last) * 60);
      last = z;
    }
    for (const speed of steps) expect(speed).toBeCloseTo(1.6, 2);
  });
});

describe("PlayerController camera at rest (TAA needs an exactly still camera)", () => {
  it("holds the view exactly still once Sora stops walking", async () => {
    const { scene, camera, input } = await setup();
    const moved: boolean[] = [];
    for (let frame = 0; frame < 600; frame++) {
      input.walk = frame > 30 && frame < 120;
      scene.render();
      if (frame >= 300) moved.push(camera.hasMoved);
    }
    // Five seconds of standing still: not one frame with a moved camera.
    expect(moved.filter(Boolean)).toHaveLength(0);
  });

  it("still moves the camera smoothly while walking", async () => {
    const { scene, camera, input } = await setup();
    input.walk = true;
    let movedFrames = 0;
    for (let frame = 0; frame < 120; frame++) {
      scene.render();
      if (frame > 30 && camera.hasMoved) movedFrames++;
    }
    expect(movedFrames).toBeGreaterThan(85);
    expect(camera.position.z).toBeGreaterThan(1);
  });
});
