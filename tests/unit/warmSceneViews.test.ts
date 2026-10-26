import { afterEach, describe, expect, it, vi } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { UniversalCamera } from "@babylonjs/core/Cameras/universalCamera";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { warmSceneViews } from "../../src/render/warmSceneViews";
const engines: NullEngine[] = [];
afterEach(() => engines.splice(0).forEach((engine) => engine.dispose()));
function setup() {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine);
  const camera = new UniversalCamera("test_camera", new Vector3(1, 2, 3), scene);
  const mesh = new Mesh("test_surface", scene);
  scene.getActiveMeshes().push(mesh);
  const ready = vi.spyOn(mesh, "isReady").mockReturnValue(true);
  let frame = () => {};
  vi.spyOn(engine, "runRenderLoop").mockImplementation((callback) => {
    frame = callback;
  });
  const stop = vi.spyOn(engine, "stopRenderLoop").mockImplementation(() => {});
  const seen: Vector3[] = [];
  const render = vi.spyOn(scene, "render").mockImplementation(() => {
    scene.onBeforeRenderObservable.notifyObservers(scene);
    seen.push(camera.position.clone());
  });
  return { scene, camera, ready, render, stop, seen, frame: () => frame() };
}
describe("loading render warm-up", () => {
  it("draws each view after shaders become ready, then restores the original camera", async () => {
    const s = setup();
    const original = s.camera.position.clone();
    const views = [
      { eye: new Vector3(0, 1.58, 46), target: new Vector3(5, 1.25, 37.2) },
      { eye: new Vector3(0, 1.58, 8), target: new Vector3(0, 1.3, -10) },
    ];
    const result = warmSceneViews(s.scene, s.camera, views);
    s.ready.mockReturnValueOnce(false);
    for (let i = 0; i < 7; i++) s.frame();
    await result;
    expect(s.seen.slice(0, 4).every((p) => p.equals(views[0].eye))).toBe(true);
    expect(s.seen.slice(4).every((p) => p.equals(views[1].eye))).toBe(true);
    expect(s.camera.position.equals(original)).toBe(true);
    expect(s.stop).toHaveBeenCalledTimes(1);
    s.scene.onBeforeRenderObservable.notifyObservers(s.scene);
    expect(s.camera.position.equals(original)).toBe(true);
  });
  it("restores the camera and stops the temporary loop if a loading frame fails", async () => {
    const s = setup();
    const original = s.camera.position.clone();
    s.render.mockImplementation(() => {
      throw new Error("render failed");
    });
    const result = warmSceneViews(s.scene, s.camera, [
      { eye: Vector3.Zero(), target: Vector3.One() },
    ]);
    s.frame();
    await expect(result).rejects.toThrow("render failed");
    expect(s.camera.position.equals(original)).toBe(true);
    s.scene.onBeforeRenderObservable.notifyObservers(s.scene);
    expect(s.camera.position.equals(original)).toBe(true);
    expect(s.stop).toHaveBeenCalledTimes(1);
  });
});
