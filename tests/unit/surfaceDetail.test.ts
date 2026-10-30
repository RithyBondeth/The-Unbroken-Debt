import { afterEach, describe, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { TimingTools } from "@babylonjs/core/Misc/timingTools";
import { applyRainWetness, keepSurfaceDetail } from "../../src/render/SurfaceDetail";

describe("surface detail", () => {
  const engines: NullEngine[] = [];
  const makeScene = () => {
    const engine = new NullEngine();
    engines.push(engine);
    return new Scene(engine);
  };
  afterEach(() => engines.splice(0).forEach((engine) => engine.dispose()));

  it("prepares late-loaded surfaces after construction without changing their texture data", async () => {
    const scene = makeScene();
    keepSurfaceDetail(scene, "medium");
    const leaf = new PBRMaterial("leaf", scene);
    leaf.backFaceCulling = false;
    const wood = new PBRMaterial("wood", scene);
    const texture = new Texture(null, scene);
    texture.uScale = 3;
    texture.gammaSpace = false;
    leaf.albedoTexture = texture;
    // Babylon defers its material-added event until the next event-loop turn.
    await new Promise<void>((resolve) => TimingTools.SetImmediate(resolve));
    scene.onBeforeRenderObservable.notifyObservers(scene);
    expect(leaf.twoSidedLighting).toBe(true);
    expect(wood.twoSidedLighting).toBe(false);
    expect(wood.enableSpecularAntiAliasing).toBe(true);
    expect(texture.anisotropicFilteringLevel).toBe(8);
    expect(texture.uScale).toBe(3);
    expect(texture.gammaSpace).toBe(false);
    // Process only new resources: no repeated property writes to existing ones.
    texture.anisotropicFilteringLevel = 4;
    scene.onBeforeRenderObservable.notifyObservers(scene);
    expect(texture.anisotropicFilteringLevel).toBe(4);
  });

  it("keeps distinct authored finishes and does not darken the same material twice", () => {
    const scene = makeScene();
    const cloth = new PBRMaterial("M_wet_cloth", scene);
    cloth.roughness = 0.9;
    const bark = new PBRMaterial("M_wet_bark", scene);
    bark.roughness = 0.6;
    const paper = new PBRMaterial("paper", scene);
    paper.roughness = 0.8;
    applyRainWetness(cloth);
    applyRainWetness(bark);
    applyRainWetness(paper);
    expect(cloth.roughness).toBeGreaterThan(bark.roughness);
    expect(paper.roughness).toBe(0.8);
    const color = cloth.albedoColor.clone();
    const roughness = cloth.roughness;
    applyRainWetness(cloth);
    expect(cloth.albedoColor.equals(color)).toBe(true);
    expect(cloth.roughness).toBe(roughness);
  });
});
