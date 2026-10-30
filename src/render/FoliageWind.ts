import { MaterialPluginBase } from "@babylonjs/core/Materials/materialPluginBase";
import type { Material } from "@babylonjs/core/Materials/material";
import type { MaterialDefines } from "@babylonjs/core/Materials/materialDefines";
import { PBRMaterial } from "@babylonjs/core/Materials/PBR/pbrMaterial";
import type { UniformBuffer } from "@babylonjs/core/Materials/uniformBuffer";
import { ShaderLanguage } from "@babylonjs/core/Materials/shaderLanguage";
import { FRONT_SPEED, GUST_RISE, type WindState } from "./wind";

/**
 * How a material moves in the wind. Trunks and crowns bend alike, so a tree
 * never comes apart; leaves add their flutter on top, fronds flap, grass and
 * hanging thread lean from the root and part round Sora's feet.
 */
export type FoliageKind = "leaf" | "frond" | "bark" | "grass" | "card" | "cloth" | "hanging";

/** [Trunk bend (∝ h²), stem lean (∝ h), branch sway, flutter, push]. */
const SHAPES: Record<FoliageKind, readonly [number, number, number, number, number]> = {
  leaf: [1, 0, 1, 1, 0],
  frond: [1, 0, 1.4, 1.7, 0],
  bark: [1, 0, 0.25, 0, 0],
  grass: [0.5, 0.11, 0.3, 0.7, 1],
  card: [0.6, 0, 0.35, 0, 0],
  cloth: [0, 0.32, 0.7, 2.4, 0.6],
  /** Aerial roots and vines: long, heavy strands that swing slowly from where they hang. */
  hanging: [0, 0.1, 0.5, 0.3, 0.4],
};

/**
 * Plant materials of the village, the forest border and the taxi's roadside,
 * by kind. Props that merely share a word (the sketchbook's leaves, folded
 * banana-leaf offerings, funeral garlands) stay rigid.
 */
const PLANTS: [RegExp, FoliageKind][] = [
  [/^M_forest_far_cards$/, "card"],
  [/^(M_forest_grass|grass_medium_\d+)$/, "grass"],
  [/^(M_banana_leaf|M_palm_fan(_dead)?|M_coconut_leaf)$/, "frond"],
  [
    /^(M_forest_leaf|M_bamboo_leaves|fern_\d+|shrub_\d+|pachira_aquatica_\d+_leaves|island_tree_\d+_leaves)$/,
    "leaf",
  ],
  [
    /^(M_wet_bark(_dead)?|M_forest_moss|M_palm_trunk|M_bamboo(_dead)?|M_coconut|M_banana_stem|pachira_aquatica_\d+_bark|island_tree_\d+(_branches)?)$/,
    "bark",
  ],
];

/** The kind of plant material this is, or null for everything that stays still. */
export function foliageKind(materialName: string): FoliageKind | null {
  const name = materialName.replace(/\.\d+$/, "");
  for (const [pattern, kind] of PLANTS) if (pattern.test(name)) return kind;
  return null;
}

/** Puts every plant material in `materials` into `wind`. */
export function applyFoliageWind(materials: readonly Material[], wind: WindState): FoliageWind[] {
  const plugins: FoliageWind[] = [];
  for (const material of materials) {
    const kind = foliageKind(material.name);
    if (
      kind &&
      material instanceof PBRMaterial &&
      !material.pluginManager?.getPlugin("FoliageWind")
    )
      plugins.push(new FoliageWind(material, wind, kind));
  }
  return plugins;
}

/**
 * The vertex code, written once as GLSL and translated for WGSL. Height above
 * the plant's foot and its phase come from uv6 where the mesh carries them
 * (plants.ts bakes them), from the local position for single-plant meshes
 * (grass clumps), and otherwise from world height.
 */
export function foliageWindCode(wgsl: boolean): string {
  const gust = (g: string) => {
    const u = `(fw_t - ${g}.x - (fw_along - ${g}.w) / ${FRONT_SPEED.toFixed(1)}) / max(${g}.y, 0.001)`;
    return `${g}.z * smoothstep(0.0, ${GUST_RISE}, ${u}) * (1.0 - smoothstep(${GUST_RISE}, 1.0, ${u}))`;
  };
  const glsl = `{
    vec4 fw_main = U.windMain;
    vec4 fw_shape = U.windShape;
    vec4 fw_extra = U.windExtra;
    vec4 fw_push = U.windPush;
    vec4 fw_gustA = U.windGustA;
    vec4 fw_gustB = U.windGustB;
    float fw_t = fw_main.x;
    vec2 fw_dir = vec2(fw_main.y, fw_main.z);
    vec3 fw_p = worldPos.xyz;
    float fw_h = max(0.0, fw_p.y - fw_extra.y);
    float fw_phase = dot(fw_p.xz, vec2(0.05, 0.035));
    #ifdef UV6
    fw_h = A.uv6.x;
    fw_phase = A.uv6.y;
    #endif
    #ifdef FOLIAGE_WIND_LOCAL
    fw_h = max(0.0, positionUpdated.y);
    #endif
    float fw_along = dot(fw_p.xz, fw_dir);
    float fw_across = dot(fw_p.xz, vec2(-fw_dir.y, fw_dir.x));
    float fw_roll = 0.5 + 0.5 * sin(fw_along * 0.12 - fw_t * 1.3 + fw_across * 0.05);
    float fw_amount = fw_main.w * (0.65 + 0.35 * fw_roll) + ${gust("fw_gustA")} + ${gust("fw_gustB")};
    float fw_reach = fw_shape.x * 0.0021 * fw_h * fw_h + fw_shape.y * fw_h;
    float fw_sway = sin(fw_t * (1.05 + 0.15 * sin(fw_phase * 3.1)) + fw_phase);
    // A tip leans at most a tenth of its height (about 6°), however hard it blows.
    float fw_lean = min(fw_reach * (fw_amount + fw_sway * (0.12 + 0.3 * fw_amount)), 0.1 * fw_h + fw_shape.y * fw_h);
    float fw_side = fw_reach * 0.3 * fw_amount * sin(fw_t * 0.83 + fw_phase * 1.7);
    vec3 fw_d = vec3(fw_dir.x * fw_lean - fw_dir.y * fw_side, 0.0, fw_dir.y * fw_lean + fw_dir.x * fw_side);
    float fw_branch = fw_shape.z * min(fw_h, 8.0) * 0.011 * fw_amount * sin(fw_t * (2.2 + fw_amount) + dot(fw_p, vec3(0.31, 0.17, 0.23)) + fw_phase);
    fw_d = fw_d + vec3(fw_dir.x, 0.3, fw_dir.y) * fw_branch;
    float fw_flutter = fw_shape.w * 0.016 * min(fw_h * 2.0, 1.0) * (0.25 + fw_amount) * sin(fw_t * (8.0 + 5.0 * fw_amount) + dot(fw_p, vec3(2.7, 3.1, 2.3)));
    fw_d = fw_d + vec3(-fw_dir.y * 0.6, 1.0, fw_dir.x * 0.6) * fw_flutter;
    vec2 fw_away = fw_p.xz - fw_push.xy;
    float fw_dist = length(fw_away);
    float fw_press = fw_extra.x * fw_push.w * (1.0 - smoothstep(fw_push.z * 0.35, fw_push.z, fw_dist)) * min(fw_h, 1.2);
    fw_away = fw_away / max(fw_dist, 0.001);
    fw_d = fw_d + vec3(fw_away.x * 0.55, -0.4, fw_away.y * 0.55) * fw_press;
    fw_d.y = fw_d.y - (fw_d.x * fw_d.x + fw_d.z * fw_d.z) * 0.5 / max(fw_h, 0.5);
    worldPos = vec4(worldPos.xyz + fw_d, worldPos.w);
    O.vPositionW = worldPos.xyz;
  }`;
  // The preprocessor reads directives only at the start of a line.
  const code = glsl.replace(/^\s+#/gm, "#");
  if (!wgsl) return code.replace(/\bU\.|\bA\.|\bO\./g, "");
  return code
    .replace(
      /^(\s*)(float|vec2|vec3|vec4) (\w+) =/gm,
      (_, indent: string, type: string, name: string) => {
        const t = type === "float" ? "f32" : `${type}f`;
        return `${indent}var ${name}: ${t} =`;
      },
    )
    .replace(/\bvec([234])\(/g, "vec$1f(")
    .replace(/\bU\./g, "uniforms.")
    .replace(/\bA\./g, "vertexInputs.")
    .replace(/\bO\./g, "vertexOutputs.");
}

/**
 * Wind in the vertex shader of a plant material, driven by a shared
 * `WindState`: one set of uniforms per material per frame, nothing per vertex
 * on the CPU, so a whole forest moves on the Low preset.
 */
export class FoliageWind extends MaterialPluginBase {
  private readonly shape: readonly [number, number, number, number, number];
  /** World height of the ground, for meshes that carry no height of their own. */
  ground = 0;

  constructor(
    material: Material,
    readonly wind: WindState,
    readonly kind: FoliageKind,
    /** Heights from the mesh's own vertical axis: one plant per mesh, foot at its origin. */
    private readonly local = false,
  ) {
    super(material, "FoliageWind", 180, { FOLIAGE_WIND_LOCAL: false }, true, true);
    this.doNotSerialize = true;
    this.shape = SHAPES[kind];
  }

  override isCompatible(): boolean {
    return true;
  }

  override prepareDefines(defines: MaterialDefines): void {
    defines["FOLIAGE_WIND_LOCAL"] = this.local;
  }

  override getUniforms() {
    const names = ["windMain", "windGustA", "windGustB", "windPush", "windShape", "windExtra"];
    return {
      ubo: names.map((name) => ({ name, size: 4, type: "vec4" })),
      vertex: names.map((name) => `uniform vec4 ${name};`).join("\n"),
    };
  }

  override bindForSubMesh(buffer: UniformBuffer): void {
    const u = this.wind.uniforms;
    const s = this.shape;
    buffer.updateFloat4("windMain", u[0], u[1], u[2], u[3]);
    buffer.updateFloat4("windGustA", u[4], u[5], u[6], u[7]);
    buffer.updateFloat4("windGustB", u[8], u[9], u[10], u[11]);
    buffer.updateFloat4("windPush", u[12], u[13], u[14], u[15]);
    buffer.updateFloat4("windShape", s[0], s[1], s[2], s[3]);
    buffer.updateFloat4("windExtra", s[4], this.ground, 0, 0);
  }

  override getCustomCode(type: string, language: ShaderLanguage) {
    if (type !== "vertex") return null;
    return { CUSTOM_VERTEX_UPDATE_WORLDPOS: foliageWindCode(language === ShaderLanguage.WGSL) };
  }
}
