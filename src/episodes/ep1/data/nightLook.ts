/**
 * The village's light levels at night and at dawn (Art Bible 3, 4). The night is
 * a monsoon night: little reaches Sora but her lamp, the flames and lightning;
 * the forest and roofs survive as silhouettes against a faint cloud and fog.
 * Dawn lifts all of it at the end of the episode.
 */
export interface Look {
  /** Exposure with the lamp lit at arm's length, and the most adapted eyes reach. */
  baseExposure: number;
  maxExposure: number;
  /** Night sight at full adjustment in the dark, and how far it reaches (m). */
  nightSightIntensity: number;
  nightSightRange: number;
  fogDensity: number;
  /** Light the fog scatters by itself (linear RGB). */
  fogAmbient: [number, number, number];
  /** Behind everything, where nothing is drawn (linear RGB). */
  clearColor: [number, number, number];
  /** Cloud bounce (hemispheric) and the moon behind the cloud. */
  skyIntensity: number;
  moonIntensity: number;
}

/**
 * The haunted forest is lit by the moon through thin cloud (31 October 2026):
 * the bare trees stand readable in a cold silver haze without the lamp, the
 * lamp warms only what is near.
 */
export const NIGHT_LOOK: Look = {
  baseExposure: 1.6,
  maxExposure: 2.4,
  nightSightIntensity: 1.6,
  nightSightRange: 4,
  fogDensity: 0.021,
  fogAmbient: [0.028, 0.033, 0.042],
  clearColor: [0.018, 0.021, 0.028],
  skyIntensity: 0.5,
  moonIntensity: 0.75,
};

export const DAWN_LOOK: Look = {
  baseExposure: 1.1,
  maxExposure: 2.25,
  nightSightIntensity: 0,
  nightSightRange: 2.8,
  fogDensity: 0.018,
  fogAmbient: [0.12, 0.15, 0.18],
  clearColor: [0.26, 0.31, 0.36],
  skyIntensity: 1.1,
  moonIntensity: 0.4,
};
