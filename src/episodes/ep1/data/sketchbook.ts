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
    {
      id: "SB-01",
      beat: "P05",
      section: "notes",
      text: "20:12 · Phnom Penh studio. Ink spread across the illustration without my touching it. The candle went out and the clock stopped. Then the telephone rang.",
    },
    {
      id: "SB-02",
      beat: "A1-05",
      section: "now",
      text: "Mak Yey called from our relatives’ house. I’m alone until Vuthy returns at dawn. Keep the lamp burning, the incense alight, and the thread whole.",
      drawing: { id: "duties", height: 40 },
    },
    {
      id: "SB-03",
      beat: "A1-06",
      section: "notes",
      text: "“As your mother used to.” Her drawing is by the altar, beside the three matches Mak Yey blessed before leaving.",
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
      id: "SB-A2-01",
      beat: "A2-01",
      section: "now",
      text: "The lamps went out. Footsteps upstairs. Sok's door is open.",
    },
    {
      id: "L4",
      beat: "A1-11",
      section: "lore",
      text: "Résidence de Battambang, March 1911. Certificate of ownership: Chea and his descendants, rice land east of the village. A fortune, a year after the famine.",
    },
    {
      id: "L5",
      beat: "A1-11",
      section: "lore",
      text: "Mother, at the village house. Her hands are stained with ink. She drew too. I had forgotten her hands.",
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
      id: "SB-A2-05",
      beat: "A2-05",
      section: "now",
      text: "Sok’s desk key: ‘where the ancestors keep watch.’ Look at the base of the hall altar.",
    },
    {
      id: "SB-06",
      beat: "A2-07",
      section: "now",
      text: "Key in three pieces. The jars below.",
      drawing: { id: "jars", height: 36 },
    },
    {
      id: "SB-A2-06",
      beat: "A2-06",
      section: "notes",
      text: "It passed. Quiet, a closed wardrobe, and the lamp put out. Now, Sok’s desk key: the base of the hall altar.",
    },
    {
      id: "SB-A2-07",
      beat: "A2-07",
      section: "notes",
      text: "The bronze token is in the iron chest behind Sok’s floor planks. Its key is broken into three pieces, hidden in the water jars below. Burn the token at the coffin with the blessed matches before three. Do not turn around.",
    },
    {
      id: "SB-A3-01",
      beat: "A3-01",
      section: "now",
      text: "The thread snapped. The lamps are dying. Find the three key pieces in the jars beneath the house.",
      drawing: { id: "jars", height: 36 },
    },
    {
      id: "L2",
      beat: "A3-03",
      section: "lore",
      text: "Pages hidden in a jar: ‘He follows the wick. A foot in the mud. Wood scraping clay. Leave the light behind the posts. Wait for the dragging to pass.’",
    },
    {
      id: "SB-A3-04",
      beat: "A3-04",
      section: "now",
      text: "Three broken brass pieces. Get clear of the house, then fit them together in the satchel.",
    },
    {
      id: "SB-A3-05",
      beat: "A3-04",
      section: "now",
      text: "The chest key is whole. Sok hid the iron chest behind the loose planks in his room.",
    },
    {
      id: "SB-CHEST-MAP",
      beat: "A3-05",
      section: "notes",
      text: "A folded map in Sok’s chest. Five faint marks along a river. First, the token.",
    },
    {
      id: "SB-CHEST-SLIP",
      beat: "A3-05",
      section: "notes",
      text: "A small sealed slip from the chest. Leave it folded until this is over.",
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
