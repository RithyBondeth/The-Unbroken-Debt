import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import type { UniformBuffer } from "@babylonjs/core/Materials/uniformBuffer";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { Constants } from "@babylonjs/core/Engines/constants";
import type { Scene } from "@babylonjs/core/scene";
import { seededRandom } from "@/audio/synth";

/**
 * Still or wind-stirred open water, shared by the episodes' lakes, ponds and tanks: slow GPU
 * swell in the vertices (needs a subdivided surface), drifting ripple slopes in the normals
 * (world position, no UVs needed), and the surface normal fed into a mirror's projection so
 * reflections break up on the ripples. Set `seconds` each frame and `amplitude` to taste.
 */
export class LakeWaves extends MaterialPluginBase {
  seconds = 0;
  amplitude = 0.025;
  constructor(material: PBRMaterial) {
    super(material, "LakeWaves", 180, {}, true, true);
    this.doNotSerialize = true;
  }
  override isCompatible(): boolean {
    return true;
  }
  override getUniforms() {
    return {
      ubo: [
        { name: "lakeTime", size: 1, type: "float" },
        { name: "lakeAmplitude", size: 1, type: "float" },
      ],
      vertex: "uniform float lakeTime; uniform float lakeAmplitude;",
      fragment: "uniform float lakeTime; uniform float lakeAmplitude;",
    };
  }
  override bindForSubMesh(buffer: UniformBuffer): void {
    buffer.updateFloat("lakeTime", this.seconds);
    buffer.updateFloat("lakeAmplitude", this.amplitude);
  }
  override getCustomCode(type: string, language: ShaderLanguage): Record<string, string> | null {
    const u = language === ShaderLanguage.WGSL ? "uniforms." : "";
    if (type === "fragment") {
      const p = language === ShaderLanguage.WGSL ? "fragmentInputs.vPositionW" : "vPositionW";
      const decl = language === ShaderLanguage.WGSL ? "var lakeSlope: vec2f" : "vec2 lakeSlope";
      const vec = language === ShaderLanguage.WGSL ? "vec3f" : "vec3";
      const scalar = language === ShaderLanguage.WGSL ? "let" : "float";
      const mutableVec =
        language === ShaderLanguage.WGSL ? "var lakeReflection: vec3f" : "vec3 lakeReflection";
      const vec4 = language === ShaderLanguage.WGSL ? "vec4f" : "vec4";
      const vector4Declaration = language === ShaderLanguage.WGSL ? "let" : "vec4";
      return {
        CUSTOM_FRAGMENT_DEFINITIONS:
          language === ShaderLanguage.WGSL
            ? `
          fn lakeGradientNoise(p: vec2f) -> vec2f {
            let cell = floor(p); let f = fract(p);
            let a = fract(sin(dot(cell, vec2f(127.1,311.7)))*43758.5453);
            let b = fract(sin(dot(cell+vec2f(1.0,0.0), vec2f(127.1,311.7)))*43758.5453);
            let c = fract(sin(dot(cell+vec2f(0.0,1.0), vec2f(127.1,311.7)))*43758.5453);
            let d = fract(sin(dot(cell+vec2f(1.0,1.0), vec2f(127.1,311.7)))*43758.5453);
            let blend = f*f*(vec2f(3.0)-2.0*f);
            let derivative = 6.0*f*(vec2f(1.0)-f);
            return derivative*vec2f((b-a)+(a-b-c+d)*blend.y, (c-a)+(a-b-c+d)*blend.x);
          }
        `
            : `
          vec2 lakeGradientNoise(vec2 p) {
            vec2 cell=floor(p), f=fract(p);
            float a=fract(sin(dot(cell,vec2(127.1,311.7)))*43758.5453);
            float b=fract(sin(dot(cell+vec2(1.0,0.0),vec2(127.1,311.7)))*43758.5453);
            float c=fract(sin(dot(cell+vec2(0.0,1.0),vec2(127.1,311.7)))*43758.5453);
            float d=fract(sin(dot(cell+vec2(1.0,1.0),vec2(127.1,311.7)))*43758.5453);
            vec2 blend=f*f*(vec2(3.0)-2.0*f), derivative=6.0*f*(vec2(1.0)-f);
            return derivative*vec2((b-a)+(a-b-c+d)*blend.y,(c-a)+(a-b-c+d)*blend.x);
          }
        `,
        // Babylon 9.31's projected mirror ignores the surface normal. Disturb
        // that projection with the same normal used for the water's highlights.
        "!return computeProjectionCoords\\(worldPos,([^;]+)\\);": `
          ${mutableVec} = computeProjectionCoords(worldPos,$1);
          ${vector4Declaration} lakeViewSlope = ${language === ShaderLanguage.WGSL ? "scene.view" : "view"} * ${vec4}(worldNormal.x, 0.0, worldNormal.z, 0.0);
          lakeReflection.x += lakeViewSlope.x * 0.035 * lakeReflection.z;
          lakeReflection.y += lakeViewSlope.z * 0.025 * lakeReflection.z;
          return lakeReflection;
        `,
        CUSTOM_FRAGMENT_BEFORE_LIGHTS: `
          ${scalar} lakeA = ${p}.x * 2.7 + ${p}.z * 1.9 + sin(${p}.x * 0.31 - ${p}.z * 0.28 + ${u}lakeTime * 0.14) * 1.8 + ${u}lakeTime * 0.95;
          ${scalar} lakeB = -${p}.x * 4.1 + ${p}.z * 3.3 + sin(${p}.x * 0.41 + ${p}.z * 0.32 - ${u}lakeTime * 0.1) * 1.2 - ${u}lakeTime * 1.2;
          ${scalar} lakeC = ${p}.x * 11.5 - ${p}.z * 7.2 + sin(${p}.x * 1.1 + ${p}.z * 0.7 + ${u}lakeTime * 0.2) * 0.8 + ${u}lakeTime * 1.8;
          ${decl} = ${language === ShaderLanguage.WGSL ? "vec2f" : "vec2"}(
            cos(lakeA) * 0.105 - cos(lakeB) * 0.08 + cos(lakeC) * 0.03,
            cos(lakeA) * 0.074 + cos(lakeB) * 0.064 - cos(lakeC) * 0.019
          );
          lakeSlope += lakeGradientNoise(${language === ShaderLanguage.WGSL ? "vec2f" : "vec2"}(${p}.x*1.3+${p}.z*0.4+${u}lakeTime*0.43, ${p}.z*3.7-${p}.x*0.7-${u}lakeTime*0.17))*0.16;
          lakeSlope += lakeGradientNoise(${p}.xz*7.1-${language === ShaderLanguage.WGSL ? "vec2f" : "vec2"}(${u}lakeTime*0.61))*0.045;
          normalW = normalize(normalW + ${vec}(lakeSlope.x, 0.0, lakeSlope.y));
        `,
      };
    }
    if (type !== "vertex") return null;
    const scalar = language === ShaderLanguage.WGSL ? "let" : "float";
    return {
      CUSTOM_VERTEX_UPDATE_POSITION: `
        ${scalar} lakeVertexA = positionUpdated.x * 0.54 + positionUpdated.z * 0.36 + ${u}lakeTime * 0.8 + sin(positionUpdated.z * 0.13 - positionUpdated.x * 0.11) * 0.7;
        ${scalar} lakeVertexB = -positionUpdated.x * 0.39 + positionUpdated.z * 0.71 - ${u}lakeTime * 0.64 + sin(positionUpdated.z * 0.17 + positionUpdated.x * 0.09) * 1.1;
        ${scalar} lakeVertexC = positionUpdated.x * 0.91 - positionUpdated.z * 0.67 + ${u}lakeTime * 0.9;
        positionUpdated.y += (sin(lakeVertexA) + sin(lakeVertexB) * 0.65 + sin(lakeVertexC) * 0.28) * ${u}lakeAmplitude;
      `,
      CUSTOM_VERTEX_UPDATE_NORMAL: `normalUpdated = normalize(normalUpdated + ${language === ShaderLanguage.WGSL ? "vec3f" : "vec3"}(-(cos(lakeVertexA) * 0.54 - cos(lakeVertexB) * 0.2535 + cos(lakeVertexC) * 0.2548) * ${u}lakeAmplitude, 0.0, -(cos(lakeVertexA) * 0.36 + cos(lakeVertexB) * 0.4615 - cos(lakeVertexC) * 0.1876) * ${u}lakeAmplitude));`,
    };
  }
}
/**
 * A tiling ripple normal map: a periodic spectrum of crossed, phase-warped waves, so it
 * mip-filters cleanly without parallel sine bands. Needs UVs on the surface it is put on.
 */
export function rippleNormals(scene: Scene, seed = 730114, size = 512): RawTexture {
  const pixels = new Uint8Array(size * size * 4);
  const random = seededRandom(seed);
  // A periodic spectrum preserves mip filtering without the old parallel
  // sine bands. Crossed, phase-warped travelling waves supply the larger swell.
  const spectrum = Array.from({ length: 24 }, () => {
    const x = Math.floor(random() * 25) - 12,
      z = Math.floor(random() * 25) - 12,
      length = Math.hypot(x, z) || 1;
    const weight = 0.06 / Math.sqrt(length);
    return {
      x,
      z,
      phase: random() * Math.PI * 2,
      dx: (weight * x) / length,
      dy: (weight * z) / length,
    };
  });
  for (let y = 0; y < size; y++)
    for (let x = 0; x < size; x++) {
      const u = (x / size) * Math.PI * 2,
        v = (y / size) * Math.PI * 2,
        n = (y * size + x) * 4;
      let dx = 0,
        dy = 0;
      for (const wave of spectrum) {
        const slope = Math.cos(u * wave.x + v * wave.z + wave.phase);
        dx += slope * wave.dx;
        dy += slope * wave.dy;
      }
      const nz = 1 / Math.sqrt(1 + dx * dx + dy * dy);
      pixels[n] = 128 + dx * nz * 127;
      pixels[n + 1] = 128 + dy * nz * 127;
      pixels[n + 2] = nz * 255;
      pixels[n + 3] = 255;
    }
  const texture = new RawTexture(
    pixels,
    size,
    size,
    Constants.TEXTUREFORMAT_RGBA,
    scene,
    true,
    false,
    Texture.TRILINEAR_SAMPLINGMODE,
  );
  texture.gammaSpace = false;
  return texture;
}
