import { HDRCubeTexture } from "@babylonjs/core/Materials/Textures/hdrCubeTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { CreateBox } from "@babylonjs/core/Meshes/Builders/boxBuilder";
import type { Mesh } from "@babylonjs/core/Meshes/mesh";
import type { Scene } from "@babylonjs/core/scene";

/** Photographed cloud illumination; the series' storm sky takes over at night. */
export class VillageEnvironment {
  private readonly sky: Mesh;
  constructor(
    private readonly scene: Scene,
    size = 256,
  ) {
    const env = new HDRCubeTexture(
      `${import.meta.env.BASE_URL}assets/ep3/kloofendal_overcast_puresky_2k.hdr`,
      scene,
      size,
      false,
      true,
      false,
      true,
    );
    env.rotationY = 3.8;
    scene.environmentTexture = env;
    const sky = (this.sky = CreateBox("ep3_photographed_sky", { size: 4000 }, scene));
    sky.infiniteDistance = true;
    sky.isPickable = false;
    sky.applyFog = false;
    const surface = new StandardMaterial("M_ep3_photographed_sky", scene);
    surface.backFaceCulling = false;
    surface.disableLighting = true;
    surface.diffuseColor.set(0, 0, 0);
    surface.specularColor.set(0, 0, 0);
    surface.reflectionTexture = env.clone();
    surface.reflectionTexture.coordinatesMode = Texture.SKYBOX_MODE;
    surface.reflectionTexture.level = 0.65;
    sky.material = surface;
    scene.onDisposeObservable.addOnce(() => env.dispose());
  }
  setStage(day: boolean, dawn: boolean, memory: boolean): void {
    this.sky.setEnabled(day || dawn);
    this.scene.environmentIntensity = day ? 0.48 : dawn ? 0.32 : memory ? 0.18 : 0.028;
  }
}
