import type { AbstractEngine } from "@babylonjs/core/Engines/abstractEngine";
import type { AbstractMesh } from "@babylonjs/core/Meshes/abstractMesh";
import type { SubMesh } from "@babylonjs/core/Meshes/subMesh";
import type { Scene } from "@babylonjs/core/scene";
import type { Material } from "@babylonjs/core/Materials/material";
import type { UniformBuffer } from "@babylonjs/core/Materials/uniformBuffer";
import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";

/**
 * A warm grazing light inside the object's own material pass. This respects
 * occlusion, alpha cutouts and the WebGPU pre-pass without stencil buffers or
 * extra render targets. Per-draw uniforms keep shared materials from lighting
 * up unrelated scenery, including frozen materials and consecutive submeshes.
 */
export class InteractionHint extends MaterialPluginBase {
  constructor(
    material: Material,
    private readonly strength: (mesh: AbstractMesh) => number,
  ) {
    super(material, "InteractionHint", 200, {});
    this.registerForExtraEvents = true;
    this.doNotSerialize = true;
    this._enable(true);
  }

  override isCompatible(): boolean {
    return true;
  }

  override getClassName(): string {
    return "InteractionHint";
  }

  override getUniforms() {
    return {
      externalUniforms: ["interactionHint"],
    };
  }

  override hardBindForSubMesh(
    _buffer: UniformBuffer,
    _scene: Scene,
    _engine: AbstractEngine,
    subMesh: SubMesh,
  ): void {
    subMesh.effect?.setFloat("interactionHint", this.strength(subMesh.getRenderingMesh()));
  }

  override getCustomCode(type: string, language: ShaderLanguage) {
    if (type !== "fragment") return null;
    const color = this._material.getClassName().startsWith("PBR") ? "finalColor" : "color";
    return {
      CUSTOM_FRAGMENT_DEFINITIONS:
        language === ShaderLanguage.WGSL
          ? "uniform interactionHint: f32;"
          : "uniform float interactionHint;",
      CUSTOM_FRAGMENT_BEFORE_FOG:
        language === ShaderLanguage.WGSL
          ? `
            let hintRim = pow(1.0 - abs(dot(normalW, viewDirectionW)), 2.5);
            ${color} = vec4f(${color}.rgb + vec3f(0.42, 0.35, 0.24)
              * uniforms.interactionHint * (0.12 + 0.88 * hintRim), ${color}.a);
          `
          : `
            float hintRim = pow(1.0 - abs(dot(normalW, viewDirectionW)), 2.5);
            ${color}.rgb += vec3(0.42, 0.35, 0.24)
              * interactionHint * (0.12 + 0.88 * hintRim);
          `,
    };
  }
}
