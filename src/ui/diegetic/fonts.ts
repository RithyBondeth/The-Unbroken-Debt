/**
 * Sora's handwriting (Art Bible, section 10): Patrick Hand for English and
 * Freehand for Khmer, both SIL Open Font Licence (public/fonts/). Canvas text
 * only uses a font once it has loaded, so pages wait for this.
 */
const HANDS = [
  { family: "Patrick Hand", file: "PatrickHand-Regular.ttf" },
  { family: "Freehand", file: "Freehand-Regular.ttf" },
];

export async function loadSketchbookFonts(): Promise<void> {
  await Promise.all(
    HANDS.map(async ({ family, file }) => {
      const face = new FontFace(family, `url(${import.meta.env.BASE_URL}fonts/${file})`);
      document.fonts.add(await face.load());
    }),
  );
}
