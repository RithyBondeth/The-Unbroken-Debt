import { tintFromHex, type GradeParams } from "../../../render/grade";

/**
 * Episode 1 night grade (Art Bible, sections 2 and 4): "a 1930s photograph come
 * to life" with warm sepia mid-tones, lamp-amber highlights, blue-grey shadows
 * and deep blacks at night. Baked into the episode's lookup table at load.
 */
export const EP1_GRADE: GradeParams = {
  saturation: -0.3,
  shadows: { tint: tintFromHex("#7F8A99"), strength: 0.35 },
  midtones: { tint: tintFromHex("#C9A46A"), strength: 0.4 },
  highlights: { tint: tintFromHex("#FFB15E"), strength: 0.2 },
  blackPoint: 0.02,
};
