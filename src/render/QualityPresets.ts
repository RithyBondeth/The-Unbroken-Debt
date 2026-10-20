/** Graphics presets from the Technical Design Document, section 11. */
export type QualityName = "medium" | "high" | "ultra";

export interface QualityPreset {
  name: QualityName;
  /** Minimum-spec target this preset is tuned for. */
  target: string;
  lampShadowMapSize: number;
  /** Extra flame lights (candles, braziers) that cast shadows. */
  shadowedFlames: number;
  flameShadowMapSize: number;
  /** Small unshadowed lights handled by clustered lighting. */
  clusteredLights: number;
  /** SSAO render scale (0.5 = half resolution). */
  ssaoRatio: number;
  ssaoSamples: number;
  /** Volumetric fog render scale and ray-march steps. */
  fogRatio: number;
  fogSteps: number;
  ssr: boolean;
  taa: boolean;
}

export const QUALITY_PRESETS: Record<QualityName, QualityPreset> = {
  medium: {
    name: "medium",
    target: "1080p · RTX 2060",
    lampShadowMapSize: 2048,
    shadowedFlames: 2,
    flameShadowMapSize: 512,
    clusteredLights: 32,
    ssaoRatio: 0.5,
    ssaoSamples: 8,
    fogRatio: 0.5,
    fogSteps: 12,
    ssr: false,
    taa: true,
  },
  high: {
    name: "high",
    target: "1440p · RTX 3060 Ti",
    lampShadowMapSize: 4096,
    shadowedFlames: 4,
    flameShadowMapSize: 1024,
    clusteredLights: 64,
    ssaoRatio: 1,
    ssaoSamples: 16,
    fogRatio: 0.5,
    fogSteps: 24,
    ssr: true,
    taa: true,
  },
  ultra: {
    name: "ultra",
    target: "1440p–4K · RTX 3070+",
    lampShadowMapSize: 4096,
    shadowedFlames: 4,
    flameShadowMapSize: 1024,
    clusteredLights: 128,
    ssaoRatio: 1,
    ssaoSamples: 32,
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
