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

export const NIGHT_LOOK: Look = {
  baseExposure: 1.45,
  maxExposure: 2.1,
  nightSightIntensity: 1.4,
  nightSightRange: 2.6,
  // Old-growth night: thicker, colder air under the canopy, green-black beyond.
  fogDensity: 0.024,
  fogAmbient: [0.005, 0.0095, 0.013],
  clearColor: [0.005, 0.007, 0.009],
  skyIntensity: 0.22,
  moonIntensity: 0.2,
};

export const DAWN_LOOK: Look = {
  baseExposure: 1.1,
  maxExposure: 2.25,
  nightSightIntensity: 0,
  nightSightRange: 2.8,
  fogDensity: 0.018,
  fogAmbient: [0.12, 0.15, 0.18],
  clearColor: [0.26, 0.31, 0.36],
  skyIntensity: 0.65,
  moonIntensity: 0.4,
};
