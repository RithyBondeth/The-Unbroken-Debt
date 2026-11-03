import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import type { UniformBuffer } from "@babylonjs/core/Materials/uniformBuffer";
import { RawTexture } from "@babylonjs/core/Materials/Textures/rawTexture";
import { DynamicTexture } from "@babylonjs/core/Materials/Textures/dynamicTexture";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";
import { MirrorTexture } from "@babylonjs/core/Materials/Textures/mirrorTexture";
import { Constants } from "@babylonjs/core/Engines/constants";
import { CreateGround } from "@babylonjs/core/Meshes/Builders/groundBuilder";
import { Mesh } from "@babylonjs/core/Meshes/mesh";
import { CreateTorus } from "@babylonjs/core/Meshes/Builders/torusBuilder";
import { Plane } from "@babylonjs/core/Maths/math.plane";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import type { Game } from "../../core/Game";
import { seededRandom } from "../../audio/synth";

class LakeWaves extends MaterialPluginBase {
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
/** Specular water, original tiled normals, GPU waves and a readable expanding threat wake. */
export class VillageWater {
  readonly material: PBRMaterial;
  readonly wards;
  readonly cellar;
  readonly wake;
  private readonly waves: LakeWaves;
  private readonly normal: RawTexture;
  private readonly mirror: MirrorTexture | null;
  private readonly floodWaves: LakeWaves;
  private readonly scum: Mesh;
  private readonly game: Game;
  private time = 0;
  constructor(game: Game) {
    this.game = game;
    const scene = game.scene;
    const material = (this.material = new PBRMaterial("M_ep3_lake_water", scene));
    material.albedoColor = Color3.FromHexString("#25312c").toLinearSpace();
    material.metallic = 0;
    material.roughness = 0.15;
    material.metallicF0Factor = 1;
    material.indexOfRefraction = 1.333;
    material.maxSimultaneousLights = 8;
    material.backFaceCulling = false;
    const size = 512,
      pixels = new Uint8Array(size * size * 4);
    const random = seededRandom(730114);
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
    this.normal = new RawTexture(
      pixels,
      size,
      size,
      Constants.TEXTUREFORMAT_RGBA,
      scene,
      true,
      false,
      Texture.TRILINEAR_SAMPLINGMODE,
    );
    this.normal.gammaSpace = false;
    this.normal.uScale = this.normal.vScale = 90;
    material.bumpTexture = this.normal;
    this.normal.level = 0.38;
    this.waves = new LakeWaves(material);
    // Openings beneath wards and cellar let pumping reveal the lower floor.
    const patches = [
      [-208, -12, -150, 150],
      [12, 132, -150, 150],
      [-12, 12, -150, -27.5],
      [-12, 12, 10, 150],
      [-12, 12, -18.5, -11],
      [-12, -7, -27.5, -18.5],
      [7, 12, -27.5, -18.5],
      [-1068, -208, -1000, 1000],
      [132, 1032, -1000, 1000],
      [-208, 132, -1000, -150],
      [-208, 132, 150, 1000],
    ].map(([x0, x1, z0, z1], i) => {
      const patch = CreateGround(
        "lake_patch_" + i,
        {
          width: x1 - x0,
          height: z1 - z0,
          subdivisions: Math.max(4, Math.min(80, Math.ceil(Math.max(x1 - x0, z1 - z0) / 2))),
        },
        scene,
      );
      patch.position.set((x0 + x1) / 2, 0, (z0 + z1) / 2);
      return patch;
    });
    const lake = Mesh.MergeMeshes(patches, true, true)!;
    lake.name = "tonle_sap_surface";
    lake.position.y = -0.08;
    lake.material = material;
    lake.isPickable = false;
    const inner = material.clone("M_ep3_flood_water");
    inner.roughness = 0.21;
    inner.metallicF0Factor = 1;
    inner.albedoColor = Color3.FromHexString("#253029").toLinearSpace();
    this.floodWaves = new LakeWaves(inner);
    this.wards = CreateGround(
      "ward_flood_water",
      { width: 23.7, height: 20.7, subdivisions: 24 },
      scene,
    );
    this.wards.position.set(0, 0.26, -0.5);
    this.wards.material = inner;
    this.wards.isPickable = false;
    this.cellar = CreateGround(
      "cellar_flood_water",
      { width: 13.8, height: 8.8, subdivisions: 12 },
      scene,
    );
    this.cellar.position.set(0, 0.35, -23);
    this.cellar.material = inner;
    this.cellar.isPickable = false;
    this.scum = CreateGround(
      "clinic_water_silt",
      { width: 23.7, height: 20.7, subdivisions: 1 },
      scene,
    );
    this.scum.position.set(0, 0.269, -0.5);
    this.scum.isPickable = false;
    const scumMat = new PBRMaterial("M_ep3_water_silt", scene);
    const scumTex = new DynamicTexture(
      "T_ep3_water_silt",
      { width: 1024, height: 1024 },
      scene,
      false,
    );
    const ctx = scumTex.getContext() as CanvasRenderingContext2D,
      rand = seededRandom(192033);
    ctx.clearRect(0, 0, 1024, 1024);
    for (let i = 0; i < 460; i++) {
      const x = rand() * 1024,
        y = rand() * 1024,
        edge = Math.min(x, 1024 - x, y, 1024 - y);
      if (edge > 140 && rand() > 0.13) continue;
      const radius = 2 + rand() * 22;
      const glow = ctx.createRadialGradient(x, y, 0, x, y, radius);
      glow.addColorStop(0, `rgba(73,66,37,${0.1 + rand() * 0.14})`);
      glow.addColorStop(1, "rgba(52,51,31,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
      ctx.fillStyle = rand() > 0.5 ? "rgba(62,46,25,.55)" : "rgba(107,93,57,.42)";
      ctx.beginPath();
      ctx.ellipse(x, y, 0.8 + rand() * 2.1, 0.3 + rand() * 0.8, rand() * 6.28, 0, 6.28);
      ctx.fill();
    }
    scumTex.hasAlpha = true;
    scumTex.update();
    scumMat.albedoTexture = scumTex;
    scumMat.useAlphaFromAlbedoTexture = true;
    scumMat.transparencyMode = PBRMaterial.PBRMATERIAL_ALPHABLEND;
    scumMat.metallic = 0;
    scumMat.roughness = 0.94;
    scumMat.maxSimultaneousLights = 8;
    this.scum.material = scumMat;
    this.wake = [0, 1, 2].map((i) => {
      const ring = CreateTorus(
        "kanha_wake_" + i,
        { diameter: 1, thickness: 0.012, tessellation: 48 },
        scene,
      );
      const mat = new PBRMaterial("M_wake_" + i, scene);
      mat.albedoColor.set(0.3, 0.33, 0.28);
      mat.emissiveColor.set(0, 0, 0);
      mat.roughness = 0.55;
      mat.alpha = 0.5;
      ring.material = mat;
      ring.isPickable = false;
      ring.setEnabled(false);
      return ring;
    });
    this.mirror =
      game.preset.name !== "low"
        ? new MirrorTexture(
            "lake_reflection",
            game.preset.name === "ultra" ? 768 : game.preset.name === "medium" ? 256 : 512,
            scene,
            true,
          )
        : null;
    if (this.mirror) {
      this.mirror.mirrorPlane = new Plane(0, -1, 0, -0.08);
      this.mirror.renderList = scene.meshes.filter(
        (mesh) =>
          mesh !== lake &&
          mesh !== this.wards &&
          mesh !== this.cellar &&
          !this.wake.includes(mesh as typeof lake) &&
          mesh !== this.scum &&
          mesh.renderingGroupId === 0 &&
          !mesh.name.startsWith("col_"),
      );
      this.mirror.refreshRate = game.preset.name === "medium" ? 12 : 6;
      this.mirror.level = 1;
      material.reflectionTexture = this.mirror;
      inner.reflectionTexture = this.mirror;
    }
    scene.onDisposeObservable.addOnce(() => this.mirror?.dispose());
  }
  update(dt: number, target: number, wake: { x: number; z: number } | null, storm: boolean): void {
    this.time += dt;
    this.waves.seconds = this.time;
    this.floodWaves.seconds = this.time;
    this.floodWaves.amplitude = 0.006;
    this.waves.amplitude = storm ? 0.025 : 0.008;
    this.normal.uOffset = this.time * 0.0018;
    this.normal.vOffset = this.time * 0.001;
    this.cellar.position.y += (target - this.cellar.position.y) * Math.min(1, dt * 0.6);
    this.scum.position.y = this.wards.position.y + 0.009;
    if (this.mirror) {
      const feet = this.game.player.feet;
      const inside = Math.abs(feet.x) < 12 && feet.z < 10 && feet.z > -28;
      this.mirror.mirrorPlane.d = inside
        ? feet.z < -18.5
          ? this.cellar.position.y
          : this.wards.position.y
        : -0.08;
    }
    this.wake.forEach((ring, i) => {
      ring.setEnabled(wake !== null);
      if (!wake) return;
      const phase = (this.time * 0.35 + i / 3) % 1;
      ring.position.set(wake.x, 0.31, wake.z);
      ring.scaling.setAll(0.6 + phase * 2.4);
      (ring.material as PBRMaterial).alpha = (1 - phase) * 0.6;
    });
  }
}
