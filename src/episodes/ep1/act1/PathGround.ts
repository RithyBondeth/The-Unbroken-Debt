import type { AbstractEngine } from "@babylonjs/core/Engines/abstractEngine";
import type { Scene } from "@babylonjs/core/scene";
import type { SubMesh } from "@babylonjs/core/Meshes/subMesh";
import type { UniformBuffer } from "@babylonjs/core/Materials/uniformBuffer";
import type { BaseTexture } from "@babylonjs/core/Materials/Textures/baseTexture";
import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { Constants } from "@babylonjs/core/Engines/constants";
import type { Color3 } from "@babylonjs/core/Maths/math.color";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import { TERRAIN } from "../data/forestBorder";
import { bakeGroundMask } from "../data/pathGround";

/**
 * Mud and leaf litter in one material, mixed by a world-space mask: the litter's
 * colour and normal map wherever the mask says litter, the mud's (darker where it
 * is wettest) wherever it says mud, and every shade between at the path's edge.
 */
class GroundBlend extends MaterialPluginBase {
  constructor(
    material: PBRMaterial,
    private readonly mask: BaseTexture,
    private readonly litter: BaseTexture,
    private readonly litterBump: BaseTexture | null,
    private readonly litterColor: Color3,
  ) {
    super(material, "GroundBlend", 210, { GROUNDBLEND_BUMP: false });
    this.registerForExtraEvents = true;
    this.doNotSerialize = true;
    this._enable(true);
  }

  override isCompatible(): boolean {
    return true;
  }

  override getClassName(): string {
    return "GroundBlend";
  }

  override isReadyForSubMesh(): boolean {
    return [this.mask, this.litter, this.litterBump].every((t) => !t || t.isReady());
  }

  override prepareDefines(defines: Record<string, unknown>): void {
    defines.GROUNDBLEND_BUMP = !!this.litterBump && !!(this._material as PBRMaterial).bumpTexture;
  }

  override getSamplers(samplers: string[]): void {
    samplers.push("groundMaskSampler", "groundLitterSampler", "groundLitterBumpSampler");
  }

  override getUniforms() {
    return { externalUniforms: ["groundBounds", "groundLitterColor"] };
  }

  override bindForSubMesh(uniformBuffer: UniformBuffer): void {
    uniformBuffer.setTexture("groundMaskSampler", this.mask);
    uniformBuffer.setTexture("groundLitterSampler", this.litter);
    if (this.litterBump) uniformBuffer.setTexture("groundLitterBumpSampler", this.litterBump);
  }

  override hardBindForSubMesh(
    _buffer: UniformBuffer,
    _scene: Scene,
    _engine: AbstractEngine,
    subMesh: SubMesh,
  ): void {
    subMesh.effect?.setFloat4(
      "groundBounds",
      TERRAIN.minX,
      TERRAIN.minZ,
      TERRAIN.maxX - TERRAIN.minX,
      TERRAIN.maxZ - TERRAIN.minZ,
    );
    subMesh.effect?.setColor3("groundLitterColor", this.litterColor);
  }

  override getCustomCode(type: string, language: ShaderLanguage) {
    if (type !== "fragment") return null;
    if (language === ShaderLanguage.WGSL)
      return {
        CUSTOM_FRAGMENT_DEFINITIONS: `
          uniform groundBounds: vec4f;
          uniform groundLitterColor: vec3f;
          var groundMaskSamplerSampler: sampler;
          var groundMaskSampler: texture_2d<f32>;
          var groundLitterSamplerSampler: sampler;
          var groundLitterSampler: texture_2d<f32>;
          #ifdef GROUNDBLEND_BUMP
          var groundLitterBumpSamplerSampler: sampler;
          var groundLitterBumpSampler: texture_2d<f32>;
          #endif
        `,
        CUSTOM_FRAGMENT_UPDATE_ALPHA: `
          let groundMaskUV = (fragmentInputs.vPositionW.xz - uniforms.groundBounds.xy) / uniforms.groundBounds.zw;
          let groundMix = textureSample(groundMaskSampler, groundMaskSamplerSampler, groundMaskUV);
          let groundLitter = toLinearSpaceVec3(textureSample(groundLitterSampler, groundLitterSamplerSampler, fragmentInputs.vAlbedoUV).rgb) * uniforms.groundLitterColor;
          surfaceAlbedo = mix(groundLitter, surfaceAlbedo * (1.0 - 0.38 * groundMix.g), groundMix.r);
          #ifdef GROUNDBLEND_BUMP
          let groundLitterNormal = perturbNormal(TBN, textureSample(groundLitterBumpSampler, groundLitterBumpSamplerSampler, fragmentInputs.vAlbedoUV).xyz, uniforms.vBumpInfos.y);
          normalW = normalize(mix(groundLitterNormal, normalW, groundMix.r));
          #endif
        `,
      };
    return {
      CUSTOM_FRAGMENT_DEFINITIONS: `
        uniform vec4 groundBounds;
        uniform vec3 groundLitterColor;
        uniform sampler2D groundMaskSampler;
        uniform sampler2D groundLitterSampler;
        #ifdef GROUNDBLEND_BUMP
        uniform sampler2D groundLitterBumpSampler;
        #endif
      `,
      CUSTOM_FRAGMENT_UPDATE_ALPHA: `
        vec4 groundMix = texture2D(groundMaskSampler, (vPositionW.xz - groundBounds.xy) / groundBounds.zw);
        vec3 groundLitter = toLinearSpace(texture2D(groundLitterSampler, vAlbedoUV).rgb) * groundLitterColor;
        surfaceAlbedo = mix(groundLitter, surfaceAlbedo * (1.0 - 0.38 * groundMix.g), groundMix.r);
        #ifdef GROUNDBLEND_BUMP
        vec3 groundLitterNormal = perturbNormal(TBN, texture2D(groundLitterBumpSampler, vAlbedoUV).xyz, vBumpInfos.y);
        normalW = normalize(mix(groundLitterNormal, normalW, groundMix.r));
        #endif
      `,
    };
  }
}

/**
 * Gives the authored terrain one blended ground material in place of its two
 * stepped ones. The forest border keeps the shared mud and litter materials.
 */
export function blendPathGround(scene: Scene): void {
  const mudParts = scene.meshes.filter(
    (m) => /^ground(_primitive\d+)?$/.test(m.name) && m.material?.name === "M_wet_mud",
  );
  const litterParts = scene.meshes.filter(
    (m) => /^ground(_primitive\d+)?$/.test(m.name) && m.material?.name === "M_wet_forest_floor",
  );
  const mud = mudParts[0]?.material;
  const litter = litterParts[0]?.material;
  if (!(mud instanceof PBRMaterial) || !(litter instanceof PBRMaterial) || !litter.albedoTexture) {
    console.warn("[PathGround] the terrain's mud or litter material is missing");
    return;
  }
  const { data, width, height } = bakeGroundMask();
  const mask = RawTexture.CreateRGBATexture(
    data,
    width,
    height,
    scene,
    true,
    false,
    Texture.TRILINEAR_SAMPLINGMODE,
    Constants.TEXTURETYPE_UNSIGNED_BYTE,
  );
  mask.name = "T_ground_mask";
  mask.wrapU = mask.wrapV = Texture.CLAMP_ADDRESSMODE;
  const blended = mud.clone("M_ground_blend");
  new GroundBlend(
    blended,
    mask,
    litter.albedoTexture,
    litter.bumpTexture,
    litter.albedoColor.clone(),
  );
  for (const mesh of [...mudParts, ...litterParts]) mesh.material = blended;
}
