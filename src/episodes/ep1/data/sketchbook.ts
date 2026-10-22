import type { NightMark, SketchbookData } from "../../../ui/diegetic/sketchbookContent";

/** Night circles from a pattern: "p" pencil, "i" ink, anything else empty. */
const night = (marks: string): NightMark[] =>
  [...marks].map((m) => (m === "i" ? "ink" : m === "p" ? "pencil" : "empty"));

/**
 * Episode 1 sketchbook entries, from the Episode 1 Script (section 8), in the
 * order the beats write them. English is the master text.
 *
 * Khmer lines are glossary terms only (Cultural Guide, section 3), still marked
 * Draft or Query there: they need the advisor's review before release.
 */
export const EP1_SKETCHBOOK: SketchbookData = {
  entries: [
    { id: "SB-01", beat: "P05", section: "notes", drawing: { id: "inkBlot", height: 62 } },
    {
      id: "SB-02",
      beat: "A1-05",
      section: "now",
      text: "Keep the lamp burning. Keep the incense alight. Keep the thread whole.",
      drawing: { id: "duties", height: 40 },
    },
    {
      id: "SB-03",
      beat: "A1-06",
      section: "notes",
      text: "“As your mother used to.” Her drawing is by the altar.",
      drawing: { id: "altar", height: 42 },
    },
    {
      id: "SB-03b",
      beat: "A1-08",
      section: "notes",
      text: "Her tray, as she drew it.",
      drawing: { id: "betelTray", height: 44 },
    },
    {
      id: "SB-04",
      beat: "A2-03",
      section: "notes",
      text: "1910. Great-grandfather Chea. A bargain. Four lives. Five seals.",
      drawing: { id: "names", height: 38 },
    },
    {
      id: "SB-05",
      beat: "A2-05",
      section: "map",
      text: "The seventh night after his death.",
      nights: night("pp....."),
    },
    {
      id: "SB-06",
      beat: "A2-07",
      section: "now",
      text: "Key in three pieces. The jars below.",
      drawing: { id: "jars", height: 36 },
    },
    {
      id: "SB-07",
      beat: "A3-06",
      section: "now",
      text: "Before three. The burner. The blessed matches. Don’t turn around.",
      drawing: { id: "burner", height: 44 },
    },
    { id: "SB-08", beat: "R04", section: "map", text: "Four nights.", nights: night("ppi....") },
    // Spike S5 test content for the People page: names from the glossary.
    {
      id: "P-SORA",
      beat: "S5-test",
      section: "people",
      text: "Sora",
      khmer: "សូរ៉ា",
      drawing: { id: "portrait", height: 34 },
    },
    {
      id: "P-YAYMEY",
      beat: "S5-test",
      section: "people",
      text: "Yay Mey",
      khmer: "យាយម៉ី",
      drawing: { id: "portrait", height: 34 },
    },
    {
      id: "P-VUTHY",
      beat: "S5-test",
      section: "people",
      text: "Vuthy",
      khmer: "វុទ្ធី",
      drawing: { id: "portrait", height: 34 },
    },
    {
      id: "P-SOK",
      beat: "S5-test",
      section: "people",
      text: "Uncle Sok",
      khmer: "សុខ",
      drawing: { id: "portrait", height: 34 },
    },
  ],
  mapLabels: [
    { text: "House", khmer: "ផ្ទះរោងដឿង", x: 30, y: 74 },
    { text: "Funeral tent", khmer: "រោងបុណ្យ", x: 76, y: 128 },
    { text: "Under the house", khmer: "ក្រោមផ្ទះ", x: 22, y: 118 },
  ],
  loreCount: 4,
};
