import { tintFromHex, type GradeParams } from "../../../render/grade";

/**
 * Episode 1 night grade (Art Bible, sections 2 and 4): "a 1930s photograph come
 * to life" with warm sepia mid-tones, lamp-amber highlights, blue-grey shadows
 * and deep blacks at night. Baked into the episode's lookup table at load.
 */
export const EP1_GRADE: GradeParams = {
  saturation: -0.2,
  // Moonlit shadows in cold blue-teal against amber flames, as in the horror games
  // the night is measured against; the sepia stays in the mid-tones.
  shadows: { tint: tintFromHex("#5F7C99"), strength: 0.55 },
  midtones: { tint: tintFromHex("#C2A57A"), strength: 0.3 },
  highlights: { tint: tintFromHex("#FFB15E"), strength: 0.3 },
  blackPoint: 0.02,
};
