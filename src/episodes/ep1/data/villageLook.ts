import { NIGHT_LOOK, type Look } from "@/render/nightLook";

/**
 * Episode 1's farmstead night (the user, Nov 21, 2026, after the playtest: "the whole
 * scene is too bright ... darker"): darker than the Nov 19 village's, a step brighter
 * than the forest's NIGHT_LOOK. Past the lamp's pool the yard is black until the
 * lightning (every 8-20 s here) shows it all at once; the mist stands a grey-blue bank
 * 20-30 m out; the funeral's candles under the house and the kitchen's embers carry the
 * scene. Other episodes keep the shared NIGHT_LOOK.
 */
export const VILLAGE_NIGHT: Look = {
  ...NIGHT_LOOK,
  baseExposure: 1.65,
  maxExposure: 2.4,
  fogDensity: 0.036,
  // A dark blue-grey the trees and the sky fade into, as the previews' mist (not black).
  fogAmbient: [0.016, 0.021, 0.03],
  clearColor: [0.008, 0.011, 0.015],
  skyIntensity: 0.27,
  moonIntensity: 0.17,
};
