import { NIGHT_LOOK, type Look } from "@/render/nightLook";
import { NIGHT_GRADE } from "@/render/nightGrade";
import { tintFromHex, type GradeParams } from "@/render/grade";

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

/**
 * The night grade with warm shadows: candlelit browns where the night has blue-teal.
 * Under the house the approved previews are all candle orange and black.
 */
export const FUNERAL_GRADE: GradeParams = {
  ...NIGHT_GRADE,
  saturation: 0.05,
  shadows: { tint: tintFromHex("#8A5A3A"), strength: 0.3 },
};

/**
 * Under the house at the funeral, as the approved Cycles previews (funeral_wide,
 * funeral_close, coffin_close; measured region by region against the game, Nov 24,
 * 2026): candlelight only, warm, black between the stilts. The cool mist and night
 * sight fall away, the shadows warm, and the eye stays near 1.1 rather than opening
 * to the village's 2.4 (which doubled the mats and lit the jungle beyond).
 */
export const FUNERAL_LOOK = {
  baseExposure: 1.0,
  maxExposure: 1.12,
  /**
   * Of the village's night sight, the share left under the funeral: none. It rides
   * with Sora, so a torn cloth at arm's length glowed grey-blue where the previews
   * have it black against the candles.
   */
  nightSight: 0,
  /** Of the village's blue-grey mist light, the share left (the lightning's stays). */
  mist: 0,
  grade: FUNERAL_GRADE,
} as const;
