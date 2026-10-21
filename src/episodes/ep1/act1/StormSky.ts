import type { Scene } from "@babylonjs/core/scene";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";

/**
 * How bright the clouds are by themselves, and with a lightning flash behind them.
 * The painted colours are used as linear light, so a night sky needs a small factor.
 */
const GLOW = 0.16;
const FLASH = 1.2;

/**
 * The storm over the village (Art Bible 3): low cloud lit from behind by a
 * hidden moon, and the far treeline along the horizon, painted on a dome that
 * stays centred on Sora (tools/drawings/village.mjs, "sky"). Lightning lights
 * the clouds from within.
 */
export class StormSky {
  readonly dome: Mesh;
  private readonly material: StandardMaterial;

  constructor(scene: Scene) {
    // Inside the camera's far plane (60 m), drawn at the same distance wherever Sora stands.
    this.dome = CreateSphere(
      "sky_dome",
      { diameter: 100, segments: 32, sideOrientation: Mesh.BACKSIDE },
      scene,
    );
    this.dome.infiniteDistance = true;
    this.dome.isPickable = false;
    this.dome.receiveShadows = false;
    const material = new StandardMaterial("M_sky_storm", scene);
    const texture = new Texture(`${import.meta.env.BASE_URL}assets/ep1/T_ep1_sky_storm.jpg`, scene);
    texture.wrapU = Texture.WRAP_ADDRESSMODE;
    // The sphere's V runs the other way from the painted map's rows.
    texture.vScale = -1;
    material.emissiveTexture = texture;
    material.emissiveColor = new Color3(GLOW, GLOW, GLOW);
    material.diffuseColor = Color3.Black();
    material.specularColor = Color3.Black();
    material.disableLighting = true;
    material.backFaceCulling = false;
    material.fogEnabled = false;
    this.dome.material = material;
    this.material = material;
  }

  /** `flash` is the lightning's brightness, 0 to 1. */
  update(flash: number): void {
    this.material.emissiveColor.setAll(GLOW + flash * FLASH);
  }
}
