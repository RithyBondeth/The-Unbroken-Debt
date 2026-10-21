/**
 * Graphics presets (Technical Design Document, section 11). Low was added in
 * October 2026 so integrated graphics can play: it looks plainer but plays the
 * same, because darkness, the lamp's shadow and fog are gameplay.
 */
export type QualityName = "low" | "medium" | "high" | "ultra";

export const QUALITY_ORDER: readonly QualityName[] = ["low", "medium", "high", "ultra"];

export interface QualityPreset {
  name: QualityName;
  /** Hardware this preset is tuned for. */
  target: string;
  /** Highest internal render height; taller screens are upscaled. */
  maxRenderHeight: number;
  /** Lowest render scale dynamic resolution may drop to (fraction of maxRenderHeight). */
  minRenderScale: number;
  /** Largest texture size loaded (the asset pipeline writes 1K, 2K and 4K tiers). */
  textureSize: number;
  lampShadowMapSize: number;
  /** Flame lights (candles, braziers) that cast live shadows; the rest are baked. */
  shadowedFlames: number;
  flameShadowMapSize: number;
  /** Small unshadowed lights handled by clustered lighting. */
  clusteredLights: number;
  ssao: boolean;
  /** SSAO render scale (0.5 = half resolution). */
  ssaoRatio: number;
  ssaoSamples: number;
  /** Ray-marched fog lit by the lamp and flames; otherwise cheap exponential height fog. */
  volumetricFog: boolean;
  fogRatio: number;
  fogSteps: number;
  ssr: boolean;
  /** Temporal anti-aliasing; FXAA otherwise. */
  taa: boolean;
}

export const QUALITY_PRESETS: Record<QualityName, QualityPreset> = {
  low: {
    name: "low",
    target: "Integrated graphics · Intel Iris Xe, base Apple M1, Snapdragon X",
    maxRenderHeight: 900,
    minRenderScale: 0.6,
    textureSize: 1024,
    lampShadowMapSize: 1024,
    shadowedFlames: 0,
    flameShadowMapSize: 256,
    clusteredLights: 16,
    ssao: false,
    ssaoRatio: 0.5,
    ssaoSamples: 8,
    volumetricFog: false,
    fogRatio: 0.5,
    fogSteps: 8,
    ssr: false,
    taa: false,
  },
  medium: {
    name: "medium",
    target: "1080p · RTX 2060 / Apple M1 Pro",
    maxRenderHeight: 1080,
    minRenderScale: 0.75,
    textureSize: 2048,
    lampShadowMapSize: 2048,
    shadowedFlames: 2,
    flameShadowMapSize: 512,
    clusteredLights: 32,
    ssao: true,
    ssaoRatio: 0.5,
    ssaoSamples: 8,
    volumetricFog: true,
    fogRatio: 0.5,
    fogSteps: 12,
    ssr: false,
    taa: true,
  },
  high: {
    name: "high",
    target: "1440p · RTX 3060 Ti",
    maxRenderHeight: 1440,
    minRenderScale: 0.75,
    textureSize: 4096,
    lampShadowMapSize: 4096,
    shadowedFlames: 4,
    flameShadowMapSize: 1024,
    clusteredLights: 64,
    ssao: true,
    ssaoRatio: 1,
    ssaoSamples: 16,
    volumetricFog: true,
    fogRatio: 0.5,
    fogSteps: 24,
    ssr: true,
    taa: true,
  },
  ultra: {
    name: "ultra",
    target: "1440p–4K · RTX 3070+",
    maxRenderHeight: 2160,
    minRenderScale: 0.75,
    textureSize: 4096,
    lampShadowMapSize: 4096,
    shadowedFlames: 4,
    flameShadowMapSize: 1024,
    clusteredLights: 128,
    ssao: true,
    ssaoRatio: 1,
    ssaoSamples: 32,
    volumetricFog: true,
    fogRatio: 0.75,
    fogSteps: 32,
    ssr: true,
    taa: true,
  },
};

export function isQualityName(value: string | null): value is QualityName {
  return value !== null && value in QUALITY_PRESETS;
}

/** Returns a preset, with optional overrides (used by spikes to test harder loads). */
export function getPreset(
  name: QualityName,
  overrides: Partial<QualityPreset> = {},
): QualityPreset {
  return { ...QUALITY_PRESETS[name], ...overrides };
}
