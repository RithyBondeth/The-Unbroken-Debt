import { tintFromHex, type GradeParams } from "../../../render/grade";

/**
 * Episode 1 night grade (Art Bible, sections 2 and 4): "a 1930s photograph come
 * to life" with warm sepia mid-tones, lamp-amber highlights, blue-grey shadows
 * and deep blacks at night. Baked into the episode's lookup table at load.
 */
export const EP1_GRADE: GradeParams = {
  saturation: -0.12,
  // Moonlit shadows in cold blue-teal against amber flames, as in the horror games
  // the night is measured against; the sepia stays in the mid-tones.
  shadows: { tint: tintFromHex("#6C8299"), strength: 0.3 },
  midtones: { tint: tintFromHex("#C2AC8D"), strength: 0.16 },
  highlights: { tint: tintFromHex("#FFD4A0"), strength: 0.16 },
  // Keep the toe above true black: the old 2% cutoff erased bark and grass detail.
  blackPoint: 0.004,
};
