import { afterEach, describe, expect, it, vi } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { AssetContainer } from "@babylonjs/core/assetContainer";
import { LoadAssetContainerAsync } from "@babylonjs/core/Loading/sceneLoader";
import { DitheredTileFadeMaterialPlugin } from "@babylonjs/core/Materials/ditheredTileFadeMaterialPlugin";
import { ShadowFigure } from "../../src/episodes/ep1/entities/ShadowFigure";

vi.mock("@babylonjs/core/Loading/sceneLoader", () => ({ LoadAssetContainerAsync: vi.fn() }));
const engines: NullEngine[] = [];
afterEach(() => {
  for (const engine of engines.splice(0)) engine.dispose();
  vi.clearAllMocks();
});
function setup() {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine);
  const asset = new AssetContainer(scene);
  const mesh = CreateBox("authored_effigy", { height: 2.5, width: 0.65, depth: 0.4 }, scene);
  mesh.position.y = 1.25;
  const mat = new PBRMaterial("painted_stone", scene);
  mesh.material = mat;
  const repeated = mesh.createInstance("repeated_eye");
  asset.meshes.push(mesh, repeated);
  asset.materials.push(mat);
  asset.geometries.push(mesh.geometry!);
  asset.rootNodes.push(mesh, repeated);
  asset.removeAllFromScene();
  vi.mocked(LoadAssetContainerAsync).mockResolvedValue(asset);
  return { scene, asset };
}

describe("authored shadow encounters", () => {
  it("shares one asynchronous asset load across concurrent encounter preparation", async () => {
    const { scene } = setup();
    await Promise.all([ShadowFigure.prepare(scene), ShadowFigure.prepare(scene)]);
    await ShadowFigure.prepare(scene);
    expect(LoadAssetContainerAsync).toHaveBeenCalledTimes(1);
    expect(scene.meshes).toHaveLength(0);
    expect(scene.meshes.every((m) => m.getClassName() !== "InstancedMesh")).toBe(true);
    expect(LoadAssetContainerAsync).toHaveBeenCalledWith(
      expect.stringContaining("neakta_shadow.glb"),
      scene,
    );
  });

  it("scales around a stationary foot origin and fits the low encounter", async () => {
    const { scene } = setup();
    await ShadowFigure.prepare(scene);
    const form = new ShadowFigure(scene, "low_encounter", 1.87);
    expect(form.root.getChildMeshes().every((m) => m.getClassName() !== "InstancedMesh")).toBe(
      true,
    );
    for (let t = 0; t < 30; t += 0.17) form.animate(t, 1);
    expect(form.root.position.length()).toBe(0);
    expect(form.meshes.every((mesh) => !mesh.isPickable)).toBe(true);
    const top = Math.max(
      ...form.meshes.map((mesh) => {
        mesh.computeWorldMatrix(true);
        return mesh.getBoundingInfo().boundingBox.maximumWorld.y;
      }),
    );
    expect(top).toBeGreaterThan(1.85);
    expect(top).toBeLessThan(1.9);
  });

  it("fades shared meshes independently without switching to alpha blending", async () => {
    const { scene } = setup();
    await ShadowFigure.prepare(scene);
    const first = new ShadowFigure(scene, "first");
    const second = new ShadowFigure(scene, "second");
    first.setPresence(0.25);
    second.setPresence(0.8);
    const read = (form: ShadowFigure) => {
      const mesh = form.meshes.find((m) => m.geometry)!;
      const mat = mesh.material as PBRMaterial;
      const bounds = { lowerBound: 0, upperBound: 0 };
      DitheredTileFadeMaterialPlugin.GetOrCreate(mat).getFadeBoundsToRef(mesh, bounds);
      expect(mat.needAlphaBlendingForMesh(mesh)).toBe(false);
      return bounds.upperBound;
    };
    expect(read(first)).toBe(0.25);
    expect(read(second)).toBe(0.8);
    expect(first.root.getBoundingInfo().boundingBox.maximum.y).toBeGreaterThan(2.45);
  });

  it("warms hidden figure shaders before the encounter without showing them", async () => {
    const { scene, asset } = setup();
    await ShadowFigure.prepare(scene);
    const form = new ShadowFigure(scene, "warmup");
    form.root.setEnabled(false);
    const compile = vi.spyOn(asset.materials[0], "forceCompilationAsync").mockResolvedValue();
    await ShadowFigure.warmup(scene);
    expect(compile).toHaveBeenCalled();
    expect(compile.mock.calls.every(([mesh]) => mesh.getTotalVertices() > 0)).toBe(true);
    expect(form.root.isEnabled()).toBe(false);
  });

  it("disposes one form without removing another form's shared material or geometry", async () => {
    const { scene } = setup();
    await ShadowFigure.prepare(scene);
    const first = new ShadowFigure(scene, "forest");
    const second = new ShadowFigure(scene, "hall");
    const a = first.meshes.find((m) => m.geometry)!;
    const b = second.meshes.find((m) => m.geometry)!;
    expect(a.material).toBe(b.material);
    expect(a.geometry).toBe(b.geometry);
    first.dispose();
    expect(b.isDisposed()).toBe(false);
    expect(b.getTotalVertices()).toBeGreaterThan(0);
    expect(scene.materials).toContain(b.material);
  });
});
