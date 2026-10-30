import { PostProcess } from "@babylonjs/core/PostProcesses/postProcess";
import { ShaderStore } from "@babylonjs/core/Engines/shaderStore";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import { Constants } from "@babylonjs/core/Engines/constants";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Camera } from "@babylonjs/core/Cameras/camera";
import type { PointLight } from "@babylonjs/core/Lights/pointLight";
import type { Scene } from "@babylonjs/core/scene";
import type { Effect } from "@babylonjs/core/Materials/effect";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import type { PrePassEffectConfiguration } from "@babylonjs/core/Rendering/prePassEffectConfiguration";
import "@babylonjs/core/Rendering/prePassRendererSceneComponent";
import { MAX_MIST_POCKETS, type MistPocket } from "./mist";

/** Lights that scatter in the fog: the lamp plus the shadowed flames. */
const FOG_MAX_LIGHTS = 5;

const MARCH_SHADER = `
varying vUV: vec2f;
var textureSamplerSampler: sampler;
var textureSampler: texture_2d<f32>;
var depthSamplerSampler: sampler;
var depthSampler: texture_2d<f32>;
uniform invView: mat4x4f;
uniform tanFov: vec2f;
uniform cameraPos: vec3f;
uniform time: f32;
uniform density: f32;
uniform heightFalloff: f32;
uniform fogBaseY: f32;
uniform maxDistance: f32;
uniform steps: f32;
uniform ambient: vec3f;
uniform mistStrength: f32;
${Array.from({ length: MAX_MIST_POCKETS }, (_, i) => `uniform mist${i}: vec4f; uniform mistShape${i}: vec4f;`).join("\n")}
uniform light0: vec4f; uniform color0: vec3f;
uniform light1: vec4f; uniform color1: vec3f;
uniform light2: vec4f; uniform color2: vec3f;
uniform light3: vec4f; uniform color3: vec3f;
uniform light4: vec4f; uniform color4: vec3f;

// Cheap drifting density variation: a few sines instead of hashed value noise,
// which cost about half the pass (Spike S2 measurement).
fn density3(p: vec3f, t: f32) -> f32 {
  let a = sin(p.x * 1.7 + t * 0.31) * sin(p.z * 1.3 - t * 0.23);
  let b = sin(p.y * 2.3 + p.x * 0.7 - t * 0.17) * sin(p.z * 0.9 + p.y * 1.1);
  return 0.5 + 0.3 * a + 0.2 * b;
}

fn groundMist(p: vec3f, region: vec4f, shape: vec4f, offset: vec2f) -> f32 {
  let h = (p.y - shape.x) / shape.y;
  if (shape.z <= 0.0 || h <= 0.0 || h >= 1.0) { return 0.0; }
  let q = (p.xz - region.xy + offset) * region.zw;
  let edge = max(0.0, 1.0 - dot(q, q));
  return shape.z * edge * edge * smoothstep(0.0, 0.15, h) * (1.0 - smoothstep(0.35, 1.0, h));
}

// Henyey-Greenstein phase: light scatters mostly forwards, so flames glow when you look towards them.
// Schlick's approximation of Henyey-Greenstein (g = 0.35): same shape, no pow().
fn phase(cosTheta: f32) -> f32 {
  let k = 0.5189; // 1.55 g - 0.55 g³
  let denom = 1.0 - k * cosTheta;
  return (1.0 - k * k) / (12.566 * denom * denom);
}

fn pointLight(p: vec3f, dir: vec3f, light: vec4f, color: vec3f) -> vec3f {
  let v = light.xyz - p;
  // Clamp close to the light: the held lamp is half a metre from the eye and an
  // unclamped 1/d² would fill the screen with glare.
  let d2 = max(dot(v, v), 0.6);
  let r2 = light.w * light.w;
  var att = clamp(1.0 - d2 / r2, 0.0, 1.0);
  att = att * att / d2;
  // Light travels L→p then scatters back along -dir: cos θ = dot(v̂, dir).
  return color * att * phase(dot(v, dir) * inverseSqrt(d2));
}

// Does this light's range reach the ray segment at all? Checked once per pixel,
// so the step loop only pays for lights the ray actually passes near.
fn reaches(origin: vec3f, dir: vec3f, rayLength: f32, light: vec4f) -> bool {
  let t = clamp(dot(light.xyz - origin, dir), 0.0, rayLength);
  let closest = origin + dir * t - light.xyz;
  return dot(closest, closest) < light.w * light.w;
}

#define CUSTOM_FRAGMENT_DEFINITIONS
@fragment
fn main(input: FragmentInputs) -> FragmentOutputs {
  let dims = vec2f(textureDimensions(depthSampler, 0));
  let depth = textureLoad(depthSampler, vec2i(input.vUV * dims), 0).r;
  let viewZ = select(uniforms.maxDistance, min(depth, uniforms.maxDistance), depth > 0.0);

  let ndc = input.vUV * 2.0 - 1.0;
  let viewRay = vec3f(ndc.x * uniforms.tanFov.x, ndc.y * uniforms.tanFov.y, 1.0);
  let rayLength = min(viewZ * length(viewRay), uniforms.maxDistance);
  let dir = normalize((uniforms.invView * vec4f(viewRay, 0.0)).xyz);

  // Stable spatial dithering. TAA pauses while turning, so changing this every
  // frame made the lantern's fog crawl with noise precisely when walking.
  let pixel = input.position.xy;
  let jitter = fract(52.9829189 * fract(dot(pixel, vec2f(0.06711056, 0.00583715))));

  let stepCount = i32(uniforms.steps);
  let stepLength = rayLength / uniforms.steps;
  var t = stepLength * jitter;
  var transmittance = 1.0;
  var scattered = vec3f(0.0);

  let origin = uniforms.cameraPos;
  let use0 = reaches(origin, dir, rayLength, uniforms.light0);
  let use1 = reaches(origin, dir, rayLength, uniforms.light1);
  let use2 = reaches(origin, dir, rayLength, uniforms.light2);
  let use3 = reaches(origin, dir, rayLength, uniforms.light3);
  let use4 = reaches(origin, dir, rayLength, uniforms.light4);

  for (var i = 0; i < stepCount; i++) {
    let p = uniforms.cameraPos + dir * t;
    let heightFog = exp(-max(p.y - uniforms.fogBaseY, 0.0) * uniforms.heightFalloff);
    // Leave a clear working distance round the eye; humid air should separate
    // distant trunks, rather than put a milky screen over the held lantern.
    let nearFade = smoothstep(0.6, 2.8, t);
    var pockets = 0.0;
    // Most sky/eye-level samples skip the local volumes completely.
    if (p.y < 1.0 && uniforms.mistStrength > 0.0) {
      let drift = vec2f(sin(p.z * 0.7 + uniforms.time * 0.09) * 0.25, sin(p.x * 0.6 - uniforms.time * 0.07) * 0.2);
      ${Array.from({ length: MAX_MIST_POCKETS }, (_, i) => `pockets += groundMist(p, uniforms.mist${i}, uniforms.mistShape${i}, drift);`).join("\n")}
    }
    let sigma = (uniforms.density * heightFog + pockets * uniforms.mistStrength) * nearFade * (0.4 + 1.2 * density3(p, uniforms.time));

    // Cool sky bounce makes humid pockets readable at ground level. This never
    // raises the distant haze or puts a bright veil over the camera/lantern.
    var light = uniforms.ambient + vec3f(0.008, 0.01, 0.014) * min(1.0, pockets * 8.0) * uniforms.mistStrength;
    if (use0) { light += pointLight(p, dir, uniforms.light0, uniforms.color0); }
    if (use1) { light += pointLight(p, dir, uniforms.light1, uniforms.color1); }
    if (use2) { light += pointLight(p, dir, uniforms.light2, uniforms.color2); }
    if (use3) { light += pointLight(p, dir, uniforms.light3, uniforms.color3); }
    if (use4) { light += pointLight(p, dir, uniforms.light4, uniforms.color4); }

    let stepTransmittance = exp(-sigma * stepLength);
    // Energy-conserving integration of in-scattered light over the step.
    scattered += transmittance * light * (1.0 - stepTransmittance);
    transmittance *= stepTransmittance;
    t += stepLength;
  }

  fragmentOutputs.color = vec4f(scattered, transmittance);
}
`;

const COMPOSITE_SHADER = `
varying vUV: vec2f;
var textureSamplerSampler: sampler;
var textureSampler: texture_2d<f32>;
var sceneColorSampler: sampler;
var sceneColor: texture_2d<f32>;
var depthSampler: texture_2d<f32>;

#define CUSTOM_FRAGMENT_DEFINITIONS
@fragment
fn main(input: FragmentInputs) -> FragmentOutputs {
  // Depth-aware upsampling keeps the reduced-resolution fog off foreground
  // leaf edges, doorframes and the hands. Four taps retain the half-size march.
  let dims = vec2i(textureDimensions(textureSampler, 0));
  let depthDims = vec2i(textureDimensions(depthSampler, 0));
  let centerDepth = textureLoad(depthSampler, clamp(vec2i(input.vUV * vec2f(depthDims)), vec2i(0), depthDims - vec2i(1)), 0).r;
  let position = input.vUV * vec2f(dims) - vec2f(0.5);
  let base = vec2i(floor(position));
  let blend = fract(position);
  var sum = vec4f(0.0);
  var weights = 0.0;
  for (var y = 0; y < 2; y++) {
    for (var x = 0; x < 2; x++) {
      let coord = clamp(base + vec2i(x, y), vec2i(0), dims - vec2i(1));
      let uv = (vec2f(coord) + vec2f(0.5)) / vec2f(dims);
      let sampleDepth = textureLoad(depthSampler, clamp(vec2i(uv * vec2f(depthDims)), vec2i(0), depthDims - vec2i(1)), 0).r;
      let spatial = select(1.0 - blend.x, blend.x, x == 1) * select(1.0 - blend.y, blend.y, y == 1);
      let weight = max(spatial, 0.001) / (1.0 + abs(sampleDepth - centerDepth) * 8.0);
      sum += textureLoad(textureSampler, coord, 0) * weight;
      weights += weight;
    }
  }
  let fog = sum / weights;
  let color = textureSample(sceneColor, sceneColorSampler, input.vUV);
  fragmentOutputs.color = vec4f(color.rgb * fog.a + fog.rgb, color.a);
}
`;

ShaderStore.ShadersStoreWGSL["volumetricFogMarchPixelShader"] = MARCH_SHADER;
ShaderStore.ShadersStoreWGSL["volumetricFogCompositePixelShader"] = COMPOSITE_SHADER;

export interface VolumetricFogOptions {
  /** Render scale of the ray march (0.5 = half resolution). */
  ratio: number;
  steps: number;
  density?: number;
  heightFalloff?: number;
  fogBaseY?: number;
  maxDistance?: number;
  ambient?: Color3;
}

/**
 * Height fog lit by point lights, ray-marched at reduced resolution and
 * composited over the HDR scene (before tone mapping). Unshadowed in this
 * version: light passes through walls inside the fog. Shadowed scattering is
 * an Ultra-only follow-up if the budget allows (Spike S2 notes).
 */
export class VolumetricFog {
  density: number;
  heightFalloff: number;
  fogBaseY: number;
  maxDistance: number;
  steps: number;
  readonly ambient: Color3;
  readonly lights: PointLight[] = [];
  /** 0 removes only local ground mist, e.g. at dawn or during visual comparisons. */
  mistStrength = 0;
  private mistPockets: readonly MistPocket[] = [];

  private readonly march: PostProcess;
  private readonly fallbackDepth: RawTexture;
  private readonly composite: PostProcess;
  private readonly invView = new Matrix();
  private readonly tmpColor = new Color3();
  private readonly tmpPos = new Vector3();

  constructor(
    private readonly scene: Scene,
    private readonly camera: Camera,
    options: VolumetricFogOptions,
  ) {
    this.density = options.density ?? 0.015;
    this.heightFalloff = options.heightFalloff ?? 0.35;
    this.fogBaseY = options.fogBaseY ?? 0;
    this.maxDistance = options.maxDistance ?? 40;
    this.steps = options.steps;
    this.ambient = options.ambient ?? new Color3(0.004, 0.005, 0.008);

    const prePass = scene.enablePrePassRenderer();
    if (!prePass) throw new Error("Volumetric fog needs the pre-pass renderer (depth)");
    const config: PrePassEffectConfiguration = {
      name: "volumetricFog",
      enabled: true,
      texturesRequired: [Constants.PREPASS_DEPTH_TEXTURE_TYPE],
    };
    // Until the pre-pass has produced depth (first frames), read "no depth": fog to maxDistance.
    this.fallbackDepth = RawTexture.CreateRTexture(
      new Float32Array([0]),
      1,
      1,
      scene,
      false,
      false,
      Texture.NEAREST_SAMPLINGMODE,
      Constants.TEXTURETYPE_FLOAT,
    );

    const lightUniforms = Array.from({ length: FOG_MAX_LIGHTS }, (_, i) => [
      `light${i}`,
      `color${i}`,
    ]).flat();
    this.march = new PostProcess("fogMarch", "volumetricFogMarch", {
      uniforms: [
        "invView",
        "tanFov",
        "cameraPos",
        "time",
        "density",
        "heightFalloff",
        "fogBaseY",
        "maxDistance",
        "steps",
        "ambient",
        "mistStrength",
        ...Array.from({ length: MAX_MIST_POCKETS }, (_, i) => [`mist${i}`, `mistShape${i}`]).flat(),
        ...lightUniforms,
      ],
      samplers: ["depthSampler"],
      size: options.ratio,
      camera,
      textureType: Constants.TEXTURETYPE_HALF_FLOAT,
      shaderLanguage: ShaderLanguage.WGSL,
    });
    this.march.onApply = (effect) => this.applyMarch(effect);
    // Registers the depth requirement the way Babylon's own effects do (SSAO2): the
    // pre-pass renderer re-enables configurations attached to camera post-processes.
    // Don't set config.postProcess: the pre-pass then forces this pass to render at
    // full resolution into its own target, which cost ~6 ms at 1080p (Spike S2).
    this.march._prePassEffectConfiguration = config;

    this.composite = new PostProcess("fogComposite", "volumetricFogComposite", {
      samplers: ["sceneColor", "depthSampler"],
      size: 1,
      camera,
      textureType: Constants.TEXTURETYPE_HALF_FLOAT,
      shaderLanguage: ShaderLanguage.WGSL,
    });
    // The march pass ignores its input; the composite reads that input (the scene) back.
    this.composite.onApply = (effect) => {
      effect.setTextureFromPostProcess("sceneColor", this.march);
      this.bindDepth(effect);
    };
  }

  dispose(): void {
    this.march.dispose(this.camera);
    this.composite.dispose(this.camera);
    this.fallbackDepth.dispose();
  }

  setMistPockets(pockets: readonly MistPocket[]): void {
    this.mistPockets = pockets.slice(0, MAX_MIST_POCKETS);
    this.mistStrength = this.mistPockets.length ? 1 : 0;
  }

  private bindDepth(effect: Effect): void {
    const prePass = this.scene.prePassRenderer;
    if (prePass) {
      const index = prePass.getIndex(Constants.PREPASS_DEPTH_TEXTURE_TYPE);
      const depth = index >= 0 ? prePass.getRenderTarget().textures[index] : undefined;
      effect.setTexture("depthSampler", depth ?? this.fallbackDepth);
    } else {
      effect.setTexture("depthSampler", this.fallbackDepth);
    }
  }

  private applyMarch(effect: Effect): void {
    this.bindDepth(effect);
    const camera = this.camera;
    camera.getViewMatrix().invertToRef(this.invView);
    effect.setMatrix("invView", this.invView);
    const aspect = this.scene.getEngine().getAspectRatio(camera);
    const tanY =
      camera.fovMode === 0 ? Math.tan(camera.fov / 2) : Math.tan(camera.fov / 2) / aspect;
    effect.setFloat2("tanFov", tanY * aspect, tanY);
    effect.setVector3("cameraPos", camera.globalPosition);
    effect.setFloat("time", performance.now() / 1000);
    effect.setFloat("density", this.density);
    effect.setFloat("heightFalloff", this.heightFalloff);
    effect.setFloat("fogBaseY", this.fogBaseY);
    effect.setFloat("maxDistance", this.maxDistance);
    effect.setFloat("steps", this.steps);
    effect.setColor3("ambient", this.ambient);
    effect.setFloat("mistStrength", this.mistStrength);
    for (let i = 0; i < MAX_MIST_POCKETS; i++) {
      const p = this.mistPockets[i];
      effect.setFloat4(
        `mist${i}`,
        p?.x ?? 0,
        p?.z ?? 0,
        p ? 1 / p.radiusX : 1,
        p ? 1 / p.radiusZ : 1,
      );
      effect.setFloat4(`mistShape${i}`, p?.baseY ?? 0, p?.height ?? 1, p?.density ?? 0, 0);
    }

    for (let i = 0; i < FOG_MAX_LIGHTS; i++) {
      const light = this.lights[i];
      if (light && light.isEnabled()) {
        this.tmpPos.copyFrom(light.getAbsolutePosition());
        effect.setFloat4(`light${i}`, this.tmpPos.x, this.tmpPos.y, this.tmpPos.z, light.range);
        // Camera-carried lights illuminate surfaces; only a little of their
        // light returns as mist. Keep distant practical flames' halos intact.
        const scatter = light.parent === this.camera ? 0.18 : 1;
        light.diffuse.scaleToRef(light.intensity * scatter, this.tmpColor);
        effect.setColor3(`color${i}`, this.tmpColor);
      } else {
        effect.setFloat4(`light${i}`, 0, -1000, 0, 0.01);
        effect.setColor3(`color${i}`, Color3.BlackReadOnly);
      }
    }
  }
}
