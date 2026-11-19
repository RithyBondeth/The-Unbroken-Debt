import { NIGHT_LOOK, type Look } from "@/render/nightLook";

/**
 * Episode 1's village night: the monsoon night of the Art Bible lifted a step (the
 * user, Nov 19: "Make the whole environment a bit more brighter"). The paddies, the
 * palms and the tree line read in the cloud light past the lamp's pool, as in the
 * preview the user chose; the mist glows a little; the dark under the trees and in
 * the house stays dark. Other episodes keep the shared NIGHT_LOOK.
 */
export const VILLAGE_NIGHT: Look = {
  ...NIGHT_LOOK,
  baseExposure: 2.2,
  maxExposure: 3.1,
  fogDensity: 0.019,
  fogAmbient: [0.011, 0.016, 0.021],
  clearColor: [0.011, 0.014, 0.018],
  skyIntensity: 0.5,
  moonIntensity: 0.42,
};
