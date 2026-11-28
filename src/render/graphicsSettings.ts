import type { DeviceProfile, FormFactor } from "./DeviceProfile";
import { getPreset, isQualityName, type QualityName, type QualityPreset } from "./qualityPresets";

/**
 * The player's graphics settings (title screen and pause menu), saved in the
 * browser. "Auto" picks from the device (DeviceProfile); every other choice
 * overrides it. Pure apart from read/write, so the resolution is unit-tested.
 */

export type PresetChoice = "auto" | QualityName;
/** Frames per second to aim for: "max" renders on every display refresh. */
export type FrameCap = "auto" | "30" | "60" | "max";

/** Effects the player can switch over the preset's own choice. */
export const EFFECT_KEYS = ["ssao", "volumetricFog", "taa"] as const;
export type EffectKey = (typeof EFFECT_KEYS)[number];

export interface GraphicsSettings {
  preset: PresetChoice;
  /** Highest render scale, a share of the preset's render height (0.5–1). */
  renderScale: number;
  /** Lower the resolution under load to hold the frame rate. */
  dynamicResolution: boolean;
  frameCap: FrameCap;
  /** The player's own choice per effect; absent keeps the preset's. Cleared when the preset changes. */
  effects: Partial<Record<EffectKey, boolean>>;
  headBob: boolean;
  /** Dread tremor and full-strength scare jolts; off is reduced camera motion. */
  cameraShake: boolean;
  showFps: boolean;
}

export const DEFAULT_GRAPHICS: Readonly<GraphicsSettings> = Object.freeze({
  preset: "auto",
  renderScale: 1,
  dynamicResolution: true,
  frameCap: "auto",
  effects: {},
  headBob: true,
  cameraShake: true,
  showFps: false,
});

export const RENDER_SCALES = [1, 0.85, 0.75, 0.6, 0.5] as const;
const FRAME_CAPS: readonly FrameCap[] = ["auto", "30", "60", "max"];
const STORAGE_KEY = "boon-sop.graphics";

/** Settings from saved JSON, with anything missing or invalid back at its default. */
export function parseGraphics(raw: unknown): GraphicsSettings {
  const saved = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const bool = (key: keyof GraphicsSettings) =>
    typeof saved[key] === "boolean" ? saved[key] : (DEFAULT_GRAPHICS[key] as boolean);
  const preset =
    saved.preset === "auto" || isQualityName(typeof saved.preset === "string" ? saved.preset : null)
      ? (saved.preset as PresetChoice)
      : DEFAULT_GRAPHICS.preset;
  const scale = Number(saved.renderScale);
  const effects: Partial<Record<EffectKey, boolean>> = {};
  const rawEffects = (saved.effects ?? {}) as Record<string, unknown>;
  for (const key of EFFECT_KEYS)
    if (typeof rawEffects[key] === "boolean") effects[key] = rawEffects[key];
  return {
    preset,
    renderScale: Number.isFinite(scale) ? Math.min(1, Math.max(0.5, scale)) : 1,
    dynamicResolution: bool("dynamicResolution"),
    frameCap: FRAME_CAPS.includes(saved.frameCap as FrameCap)
      ? (saved.frameCap as FrameCap)
      : DEFAULT_GRAPHICS.frameCap,
    effects,
    headBob: bool("headBob"),
    cameraShake: bool("cameraShake"),
    showFps: bool("showFps"),
  };
}

export function readGraphicsSettings(): GraphicsSettings {
  try {
    return parseGraphics(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null"));
  } catch {
    return parseGraphics(null);
  }
}

export function writeGraphicsSettings(settings: GraphicsSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // Private windows and full storage: the settings still apply to this session.
  }
}

/** What the engine runs with, worked out from the settings and the device. */
export interface ResolvedGraphics {
  preset: QualityPreset;
  /** Frames per second to aim for; 0 renders on every display refresh. */
  targetFps: number;
  maxScale: number;
  dynamicResolution: boolean;
}

/**
 * Phones and tablets on "Auto": Low, a lower render height (a phone's 1170
 * native pixels are far more than its GPU can fill in a horror game's fog and
 * shadow), and room for dynamic resolution to go further down under heat.
 */
const AUTO_FORM_FACTOR: Record<FormFactor, Partial<QualityPreset>> = {
  desktop: {},
  tablet: { maxRenderHeight: 900, minRenderScale: 0.5 },
  phone: { maxRenderHeight: 720, minRenderScale: 0.5, lampShadowMapSize: 512 },
};

/** Phones hold 30 fps by default: steady, and they stay cool for a whole episode. */
export function autoFrameRate(formFactor: FormFactor): number {
  return formFactor === "phone" ? 30 : 60;
}

export function resolveGraphics(
  settings: GraphicsSettings,
  device: Pick<DeviceProfile, "quality" | "formFactor">,
): ResolvedGraphics {
  const auto = settings.preset === "auto";
  const name = auto ? device.quality : settings.preset;
  const overrides: Partial<QualityPreset> = auto ? { ...AUTO_FORM_FACTOR[device.formFactor] } : {};
  for (const key of EFFECT_KEYS) {
    const choice = settings.effects[key];
    if (choice !== undefined) overrides[key] = choice;
  }
  return {
    preset: getPreset(name as QualityName, overrides),
    targetFps:
      settings.frameCap === "auto"
        ? autoFrameRate(device.formFactor)
        : settings.frameCap === "max"
          ? 0
          : Number(settings.frameCap),
    maxScale: settings.renderScale,
    dynamicResolution: settings.dynamicResolution,
  };
}

/** Settings that only take effect when the game next loads (they shape loading itself). */
export function needsReload(before: GraphicsSettings, after: GraphicsSettings): boolean {
  if (before.preset !== after.preset) return true;
  return EFFECT_KEYS.some((key) => before.effects[key] !== after.effects[key]);
}
