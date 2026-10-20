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

/** Lights that scatter in the fog: the lamp plus the shadowed flames. */
export const FOG_MAX_LIGHTS = 5;

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
uniform frame: f32;
uniform density: f32;
uniform heightFalloff: f32;
uniform fogBaseY: f32;
uniform maxDistance: f32;
uniform steps: f32;
uniform ambient: vec3f;
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

// Henyey-Greenstein phase: light scatters mostly forwards, so flames glow when you look towards them.
fn phase(cosTheta: f32) -> f32 {
  let g = 0.35;
  let g2 = g * g;
  return (1.0 - g2) / (12.566 * pow(1.0 + g2 - 2.0 * g * cosTheta, 1.5));
}

fn pointLight(p: vec3f, dir: vec3f, light: vec4f, color: vec3f) -> vec3f {
  let v = light.xyz - p;
  // Clamp close to the light: the held lamp is half a metre from the eye and an
  // unclamped 1/d² would fill the screen with glare.
  let d2 = max(dot(v, v), 0.6);
  let r = light.w;
  if (d2 > r * r) {
    return vec3f(0.0);
  }
  var att = clamp(1.0 - d2 / (r * r), 0.0, 1.0);
  att = att * att / d2;
  // Light travels L→p then scatters back along -dir: cos θ = dot(v̂, dir).
  return color * att * phase(dot(normalize(v), dir));
}

#define CUSTOM_FRAGMENT_DEFINITIONS
@fragment
fn main(input: FragmentInputs) -> FragmentOutputs {
  let dims = vec2f(textureDimensions(depthSampler, 0));
  let depth = textureLoad(depthSampler, vec2i(input.vUV * dims), 0).r;
  let viewZ = select(uniforms.maxDistance, min(depth, uniforms.maxDistance), depth > 0.0);

  let ndc = input.vUV * 2.0 - 1.0;
  let viewRay = vec3f(ndc.x * uniforms.tanFov.x, ndc.y * uniforms.tanFov.y, 1.0);
  let rayLength = viewZ * length(viewRay);
  let dir = normalize((uniforms.invView * vec4f(viewRay, 0.0)).xyz);

  // Interleaved gradient noise, changed every frame: TAA smooths the banding away.
  let pixel = input.position.xy + vec2f(uniforms.frame * 5.588);
  let jitter = fract(52.9829189 * fract(dot(pixel, vec2f(0.06711056, 0.00583715))));

  let stepCount = i32(uniforms.steps);
  let stepLength = rayLength / uniforms.steps;
  var t = stepLength * jitter;
  var transmittance = 1.0;
  var scattered = vec3f(0.0);

  for (var i = 0; i < stepCount; i++) {
    let p = uniforms.cameraPos + dir * t;
    let heightFog = exp(-max(p.y - uniforms.fogBaseY, 0.0) * uniforms.heightFalloff);
    let sigma = uniforms.density * heightFog * (0.4 + 1.2 * density3(p, uniforms.time));

    var light = uniforms.ambient;
    light += pointLight(p, dir, uniforms.light0, uniforms.color0);
    light += pointLight(p, dir, uniforms.light1, uniforms.color1);
    light += pointLight(p, dir, uniforms.light2, uniforms.color2);
    light += pointLight(p, dir, uniforms.light3, uniforms.color3);
    light += pointLight(p, dir, uniforms.light4, uniforms.color4);

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

#define CUSTOM_FRAGMENT_DEFINITIONS
@fragment
fn main(input: FragmentInputs) -> FragmentOutputs {
  let fog = textureSample(textureSampler, textureSamplerSampler, input.vUV);
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

  private readonly march: PostProcess;
  private readonly fallbackDepth: RawTexture;
  private readonly composite: PostProcess;
  private readonly invView = new Matrix();
  private readonly tmpColor = new Color3();
  private readonly tmpPos = new Vector3();
  private frame = 0;

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
        "frame",
        "density",
        "heightFalloff",
        "fogBaseY",
        "maxDistance",
        "steps",
        "ambient",
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
    config.postProcess = this.march;
    this.march._prePassEffectConfiguration = config;

    this.composite = new PostProcess("fogComposite", "volumetricFogComposite", {
      samplers: ["sceneColor"],
      size: 1,
      camera,
      textureType: Constants.TEXTURETYPE_HALF_FLOAT,
      shaderLanguage: ShaderLanguage.WGSL,
    });
    // The march pass ignores its input; the composite reads that input (the scene) back.
    this.composite.onApply = (effect) => effect.setTextureFromPostProcess("sceneColor", this.march);
  }

  dispose(): void {
    this.march.dispose(this.camera);
    this.composite.dispose(this.camera);
    this.fallbackDepth.dispose();
  }

  private applyMarch(effect: Effect): void {
    const prePass = this.scene.prePassRenderer;
    if (prePass) {
      const index = prePass.getIndex(Constants.PREPASS_DEPTH_TEXTURE_TYPE);
      const depth = index >= 0 ? prePass.getRenderTarget().textures[index] : undefined;
      effect.setTexture("depthSampler", depth ?? this.fallbackDepth);
    } else {
      effect.setTexture("depthSampler", this.fallbackDepth);
    }

    const camera = this.camera;
    camera.getViewMatrix().invertToRef(this.invView);
    effect.setMatrix("invView", this.invView);
    const aspect = this.scene.getEngine().getAspectRatio(camera);
    const tanY =
      camera.fovMode === 0 ? Math.tan(camera.fov / 2) : Math.tan(camera.fov / 2) / aspect;
    effect.setFloat2("tanFov", tanY * aspect, tanY);
    effect.setVector3("cameraPos", camera.globalPosition);
    effect.setFloat("time", performance.now() / 1000);
    effect.setFloat("frame", (this.frame = (this.frame + 1) % 64));
    effect.setFloat("density", this.density);
    effect.setFloat("heightFalloff", this.heightFalloff);
    effect.setFloat("fogBaseY", this.fogBaseY);
    effect.setFloat("maxDistance", this.maxDistance);
    effect.setFloat("steps", this.steps);
    effect.setColor3("ambient", this.ambient);

    for (let i = 0; i < FOG_MAX_LIGHTS; i++) {
      const light = this.lights[i];
      if (light && light.isEnabled()) {
        this.tmpPos.copyFrom(light.getAbsolutePosition());
        effect.setFloat4(`light${i}`, this.tmpPos.x, this.tmpPos.y, this.tmpPos.z, light.range);
        light.diffuse.scaleToRef(light.intensity, this.tmpColor);
        effect.setColor3(`color${i}`, this.tmpColor);
      } else {
        effect.setFloat4(`light${i}`, 0, -1000, 0, 0.01);
        effect.setColor3(`color${i}`, Color3.BlackReadOnly);
      }
    }
  }
}
