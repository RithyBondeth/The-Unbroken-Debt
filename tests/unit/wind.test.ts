import { describe, expect, it } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import {
  FRONT_SPEED,
  GUST_RISE,
  WIND_UNIFORMS,
  WindState,
  gustEnvelope,
} from "../../src/render/wind";
import type { FoliageWind } from "../../src/render/FoliageWind";
import { applyFoliageWind, foliageKind, foliageWindCode } from "../../src/render/FoliageWind";
import { seededRandom } from "../../src/audio/synth";

const run = (wind: WindState, seconds: number, x = 0, z = 0) => {
  for (let i = 0; i < Math.round(seconds * 60); i++) wind.update(1 / 60, x, z);
};

describe("gust envelope", () => {
  it("rises quickly to its height, falls slowly and is still outside its passage", () => {
    expect(gustEnvelope(-0.1)).toBe(0);
    expect(gustEnvelope(0)).toBe(0);
    expect(gustEnvelope(1)).toBe(0);
    expect(gustEnvelope(GUST_RISE)).toBeCloseTo(1);
    for (let u = 0.02; u < GUST_RISE; u += 0.02)
      expect(gustEnvelope(u + 0.02)).toBeGreaterThanOrEqual(gustEnvelope(u));
    for (let u = GUST_RISE; u < 0.98; u += 0.02)
      expect(gustEnvelope(u + 0.02)).toBeLessThanOrEqual(gustEnvelope(u));
  });
});

describe("wind state", () => {
  it("eases up to the scene's strength and stays within reach of the prevailing heading", () => {
    const wind = new WindState(seededRandom(1));
    wind.base = 0.55;
    run(wind, 30);
    expect(wind.strength).toBeGreaterThan(0.5);
    expect(wind.strength).toBeLessThan(0.6);
    let wander = 0;
    for (let i = 0; i < 300; i++) {
      run(wind, 1);
      wander = Math.max(wander, Math.abs(wind.heading - wind.prevailing));
    }
    expect(wander).toBeGreaterThan(0.05);
    expect(wander).toBeLessThanOrEqual(0.36);
  });

  it("drops fast when the night hushes and comes back slowly", () => {
    const wind = new WindState(seededRandom(2));
    wind.base = 0.55;
    run(wind, 30);
    wind.calm = 1;
    run(wind, 3);
    expect(wind.strength).toBeLessThan(0.55 * 0.15);
    expect(wind.gustAt(0, 0)).toBe(0);
    wind.calm = 0;
    run(wind, 3);
    expect(wind.strength).toBeLessThan(0.45);
    run(wind, 20);
    expect(wind.strength).toBeGreaterThan(0.5);
  });

  it("sends no gusts in still air or a hushed night, and more of them as dread climbs", () => {
    const count = (base: number, calm: number, tension: number) => {
      const wind = new WindState(seededRandom(3));
      wind.base = base;
      wind.calm = calm;
      wind.tension = tension;
      let gusts = 0;
      wind.onGust = () => gusts++;
      run(wind, 240);
      return gusts;
    };
    expect(count(0, 0, 0)).toBe(0);
    expect(count(0.55, 0.8, 0)).toBe(0);
    const calm = count(0.55, 0, 0),
      tense = count(0.55, 0, 1);
    expect(calm).toBeGreaterThan(8);
    expect(tense).toBeGreaterThan(calm * 1.3);
  });

  it("reaches trees upwind first and lands its height on the listener when it said it would", () => {
    const wind = new WindState(seededRandom(4));
    wind.base = 0.55;
    run(wind, 5, 3, 7);
    let arrival: number | null = null;
    wind.onGust = (_gust, arrivesIn) => (arrival ??= wind.time + arrivesIn);
    while (arrival === null) run(wind, 0.1, 3, 7);
    const upwind = { x: 3 - wind.dirX * 15, z: 7 - wind.dirZ * 15 };
    let peakHere = { t: 0, v: 0 },
      peakUpwind = { t: 0, v: 0 };
    // The listener stays put: the heading veers slowly, so sample as it is.
    for (let i = 0; i < 60 * 12; i++) {
      wind.update(1 / 60, 3, 7);
      const here = wind.gustAt(3, 7),
        there = wind.gustAt(upwind.x, upwind.z);
      if (here > peakHere.v) peakHere = { t: wind.time, v: here };
      if (there > peakUpwind.v) peakUpwind = { t: wind.time, v: there };
    }
    expect(peakHere.v).toBeGreaterThan(0.2);
    expect(Math.abs(peakHere.t - arrival)).toBeLessThan(0.6);
    expect(peakHere.t - peakUpwind.t).toBeGreaterThan((15 / FRONT_SPEED) * 0.7);
  });

  it("surges a gust in on a scare, taking the oldest slot when both are full", () => {
    const wind = new WindState(seededRandom(5));
    wind.base = 0.5;
    run(wind, 10);
    for (let k = 0; k < 3; k++) wind.surge(1, 5, 3);
    expect(wind.gusts.length).toBe(2);
    run(wind, 5 / FRONT_SPEED + GUST_RISE * 3);
    expect(wind.gustAt(0, 0)).toBeGreaterThan(1.5);
    wind.calm = 0.9;
    wind.surge(1);
    expect(wind.gusts.length).toBe(2);
  });

  it("packs time, heading, strength, both gusts and Sora's position for the shader", () => {
    const wind = new WindState(seededRandom(6));
    wind.base = 0.5;
    run(wind, 4);
    wind.push!.x = 2;
    wind.push!.z = -3;
    wind.surge(0.8, 10, 4);
    const out = wind.pack(new Float32Array(WIND_UNIFORMS));
    expect(out[0]).toBeCloseTo(wind.time);
    expect(Math.hypot(out[1], out[2])).toBeCloseTo(1);
    expect(out[3]).toBeCloseTo(wind.strength);
    expect(out[6] + out[10]).toBeGreaterThan(0.79);
    expect([out[12], out[13], out[15]]).toEqual([2, -3, 1]);
    expect(Array.from(wind.uniforms)).toEqual(Array.from(out));
  });

  it("measures the wind at a point from its strength and gusts", () => {
    const wind = new WindState(seededRandom(7));
    wind.base = 0.6;
    run(wind, 30);
    for (let x = -20; x <= 20; x += 10) {
      const at = wind.at(x, 3);
      expect(at).toBeGreaterThanOrEqual(wind.strength * 0.65 - 1e-6);
      expect(at).toBeLessThanOrEqual(wind.strength + wind.gustAt(x, 3) + 1e-6);
    }
  });
});

describe("foliage wind", () => {
  it("moves plants and leaves props that merely share a word alone", () => {
    expect(foliageKind("M_forest_leaf")).toBe("leaf");
    expect(foliageKind("M_banana_leaf")).toBe("frond");
    expect(foliageKind("M_palm_fan_dead")).toBe("frond");
    expect(foliageKind("M_wet_bark")).toBe("bark");
    expect(foliageKind("pachira_aquatica_01_bark.001")).toBe("bark");
    expect(foliageKind("M_forest_grass")).toBe("grass");
    expect(foliageKind("shrub_03")).toBe("leaf");
    expect(foliageKind("M_forest_far_cards")).toBe("card");
    for (const prop of [
      "M_sketchbook_leaf_front",
      "M_funeral_leaf",
      "M_offering_betel_leaf",
      "M_shrine_folded_banana_leaf.002",
      "M_house_detail_palm_leaf",
      "M_wet_mud",
    ])
      expect(foliageKind(prop)).toBeNull();
  });

  it("writes the same displacement for WGSL and GLSL, directives at line starts", () => {
    const wgsl = foliageWindCode(true),
      glsl = foliageWindCode(false);
    expect(wgsl).toContain("uniforms.windMain");
    expect(wgsl).toContain("vertexInputs.uv6");
    expect(wgsl).toContain("vertexOutputs.vPositionW");
    expect(wgsl).not.toMatch(/\bvec[234]\(/);
    expect(wgsl).not.toMatch(/^\s*(float|vec[234]) /m);
    expect(glsl).not.toMatch(/\b(uniforms|vertexInputs|vertexOutputs)\./);
    expect(glsl).toContain("worldPos = vec4(worldPos.xyz + fw_d, worldPos.w);");
    for (const code of [wgsl, glsl]) {
      for (const line of code.split("\n").filter((l) => l.includes("#")))
        expect(line.startsWith("#")).toBe(true);
      expect(code.split("{").length).toBe(code.split("}").length);
    }
  });

  it("puts each plant material into one shared wind, once", () => {
    const engine = new NullEngine(),
      scene = new Scene(engine);
    try {
      const wind = new WindState();
      const leaf = new PBRMaterial("M_forest_leaf", scene);
      const page = new PBRMaterial("M_sketchbook_leaf_front", scene);
      const plain = new StandardMaterial("M_bamboo", scene);
      const plugins = applyFoliageWind([leaf, page, plain], wind);
      expect(plugins.map((p) => p.kind)).toEqual(["leaf"]);
      expect(applyFoliageWind([leaf], wind)).toEqual([]);
      const plugin = leaf.pluginManager?.getPlugin("FoliageWind") as FoliageWind;
      expect(plugin.wind).toBe(wind);
      expect(plugin.getCustomCode("fragment", ShaderLanguage.WGSL)).toBeNull();
      expect(plugin.getUniforms().ubo.map((u) => u.name)).toContain("windGustB");
    } finally {
      scene.dispose();
      engine.dispose();
    }
  });
});
