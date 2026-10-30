import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import type { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { UniformBuffer } from "@babylonjs/core/Materials/uniformBuffer";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";

/** Small, unsynchronized leaf movement. Trunks and the road stay rigid. */
export class FoliageWind extends MaterialPluginBase {
  seconds = 0;
  constructor(material: PBRMaterial) {
    super(material, "FoliageWind", 180, {}, true, true);
    this.doNotSerialize = true;
  }
  override isCompatible(): boolean {
    return true;
  }
  override getUniforms() {
    return {
      ubo: [{ name: "foliageWindTime", size: 1, type: "float" }],
      vertex: "uniform float foliageWindTime;",
    };
  }
  override bindForSubMesh(buffer: UniformBuffer): void {
    buffer.updateFloat("foliageWindTime", this.seconds);
  }
  override getCustomCode(type: string, language: ShaderLanguage) {
    if (type !== "vertex") return null;
    const time = language === ShaderLanguage.WGSL ? "uniforms.foliageWindTime" : "foliageWindTime";
    const strength = "min(0.065, max(0.0, (positionUpdated.y - 0.4) * 0.009))";
    return {
      CUSTOM_VERTEX_UPDATE_POSITION: `
      positionUpdated.x += sin(positionUpdated.z * 0.37 + positionUpdated.x * 0.63 + ${time} * 1.6) * ${strength};
      positionUpdated.z += sin(positionUpdated.z * 0.21 - positionUpdated.x * 0.41 + ${time} * 1.13) * ${strength} * 0.45;
    `,
    };
  }
}
