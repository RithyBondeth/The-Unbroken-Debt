import type { Scene } from "@babylonjs/core/scene";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateSphere } from "@babylonjs/core/Meshes/Builders/sphereBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { cloudDeck, cloudScud, type CloudMap } from "./stormClouds";

/**
 * How bright the cloud deck is by itself, and with a lightning flash inside it, at
 * the base exposure. Very little: a monsoon night under rain cloud, the moon only
 * a faint lightening somewhere behind it.
 */
const GLOW = 0.075;
const FLASH = 1.5;
/** A little flat fill from a flash: the whole sky goes pale for an instant. */
const FLASH_FILL = new Color3(0.05, 0.055, 0.07);
/** Exposure the sky is painted for: as Sora's eyes adapt, the sky stays night. */
const BASE_EXPOSURE = 1.45;
/** Drift round the dome, in turns per second: the deck crawls, the scud runs under it. */
const DECK_DRIFT = 0.0008;
const SCUD_DRIFT = 0.0032;

/**
 * The storm over the village (Art Bible 3): a heavy rain deck and torn low scud
 * on a dome centred on Sora, both drifting with the wind. The deck carries the
 * light (a faint glow, and lightning from inside the cloud); the scud multiplies
 * it, so the low cloud stands dark against the deck and darker still against a
 * flash. Both maps are generated (stormClouds.ts); nothing is a flat colour.
 */
export class StormSky {
  readonly dome: Mesh;
  private readonly material: StandardMaterial;
  private readonly deck: Texture;
  private readonly scud: Texture;

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
    this.deck = cloudTexture(cloudDeck(), scene, "T_sky_cloud_deck");
    this.scud = cloudTexture(cloudScud(), scene, "T_sky_cloud_scud");
    // Light comes from the deck (emissive); the scud is the base colour it is multiplied by.
    material.emissiveTexture = this.deck;
    material.diffuseTexture = this.scud;
    material.emissiveColor = Color3.Black();
    material.diffuseColor = Color3.White();
    material.specularColor = Color3.Black();
    material.disableLighting = true;
    material.backFaceCulling = false;
    material.fogEnabled = false;
    this.dome.material = material;
    this.material = material;
    this.update(0, BASE_EXPOSURE, 0);
  }

  /**
   * `flash` is the lightning's brightness, 0 to 1; `exposure` the camera's, which
   * the sky cancels out so it doesn't fade up to a dusk as her eyes adjust.
   */
  update(flash: number, exposure = BASE_EXPOSURE, dt = 0): void {
    this.deck.uOffset = (this.deck.uOffset + dt * DECK_DRIFT) % 1;
    this.scud.uOffset = (this.scud.uOffset + dt * SCUD_DRIFT) % 1;
    const k = BASE_EXPOSURE / Math.max(BASE_EXPOSURE, exposure);
    this.deck.level = (GLOW + flash * FLASH) * k;
    FLASH_FILL.scaleToRef(flash * k, this.material.emissiveColor);
  }
}

function cloudTexture(map: CloudMap, scene: Scene, name: string): Texture {
  // Rows run zenith to nadir, as the sphere's V does: uploaded as they are.
  const texture = RawTexture.CreateRGBATexture(
    map.data,
    map.width,
    map.height,
    scene,
    true,
    false,
    Texture.TRILINEAR_SAMPLINGMODE,
  );
  texture.name = name;
  texture.wrapU = Texture.WRAP_ADDRESSMODE;
  texture.wrapV = Texture.CLAMP_ADDRESSMODE;
  return texture;
}
