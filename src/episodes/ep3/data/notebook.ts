import type { NotebookSnapshot } from "../../../ui/notebook/notebookContent";
import type { NotebookMap, MapShape } from "../../../ui/notebook/NotebookMap";
import type {
  SketchbookData,
  SketchEntry,
  NightMark,
} from "../../../ui/diegetic/sketchbookContent";
import type { VillageProgress, VillageStage } from "../VillageProgress";
import { VILLAGE, NOTES, KHMER_DIGITS } from "./village";

export const EP3_SKETCHBOOK: SketchbookData = { entries: [], mapLabels: [], loreCount: 5 };
export const OBJECTIVES: Record<VillageStage, readonly [string, string]> = {
  market: [
    "The last afternoon",
    "Ask the noodle seller about Pa Lok. Speak to Vuthy on the main walkway, then find Pa Lok on his raft to the south-west. Borrow his boat.",
  ],
  crossing: [
    "Row toward the clinic",
    "Alternate A and D to pull the oars. The clinic’s amber landing lamp is ahead. Keep rowing through the black water.",
  ],
  clinic: [
    "Keep above the water",
    "Seal both broken ward windows, collect three dry fuses and start the generator in the north-east ward. The child’s footsteps lead upstairs to a dry fuse. Wall lamps and the attic stove restore warmth.",
  ],
  vault: [
    "The letter in the safe",
    "The pump has drained the cellar. Take the descending ramp at the north-east corner. Match the safe’s four dials to the copied Khmer marks in the admission register or calendar key.",
  ],
  memory: [
    "Sok · 1931",
    "I am in his hands. Scrape Vuthy’s name from the wet earth on the low table, then take the stylus and write the name he chose instead.",
  ],
  purification: [
    "Call her by her name",
    "Go up the west stair to the sheltered upper deck. Pour Pa Lok’s sanctified water over the jar. Light the three candles, then decide whether to stay for Kanha and Pich.",
  ],
  escape: [
    "The rope has been cut",
    "The boat is gone. Follow the sloping boards from the north end of the upper west veranda, across three roof bridges to the last stilt. Ring the hanging rescue bell.",
  ],
  dawn: [
    "Pa Lok’s raft",
    "The lake is quiet. Pa Lok has come back. Hear what he knows about the man who asked after your boat.",
  ],
  complete: [
    "Two nights remain",
    "Third seal broken. Pa Lok’s compass points east. The burnt rubber bears the stamp of the Kampong Cham estate, 1928.",
  ],
};
export function villageNotebook(
  p: VillageProgress,
  at: { x: number; z: number },
  checkpoint: string,
): NotebookSnapshot {
  const [heading, text] = OBJECTIVES[p.stage];
  const entries: SketchEntry[] = [
    { id: "live:objective", beat: "live", section: "now", heading, text },
    { id: "live:checkpoint", beat: "live", section: "now", smallText: checkpoint },
  ];
  if (["clinic", "vault"].includes(p.stage))
    entries.push({
      id: "ep3:checklist",
      beat: "live",
      section: "now",
      heading: "The flooded clinic",
      text: `Windows sealed: ${p.sealed} / 2\nDry fuses found: ${p.fuses} / 3\nPump: ${p.flags.get("ep3.pump.running", false) ? "running" : "without power"}`,
      pageBreakBefore: true,
    });
  entries.push({
    id: "ep3:rules",
    beat: "live",
    section: "notes",
    heading: "Pa Lok’s warning",
    text: "The water carries her. Stay on raised boards, beds and the upper walkways. Listen for a wet breath and watch the widening rings before she rises. Fixed lamps keep her away. Warm up at the attic stove; dry matches and oil are kept there. F lights the lamp, X closes its shutter, R refills it.",
  });
  entries.push({
    id: "ep3:numerals",
    beat: "live",
    section: "notes",
    heading: "The safe’s numeral key",
    text: `${[...KHMER_DIGITS].map((n, i) => `${n} = ${i}`).join("   ")}\nThe four copied marks read from left to right. The same key is pinned to the reception desk.`,
  });
  if (p.flags.get("lore.ep3.admission", false) || p.flags.get("lore.ep3.calendar", false))
    entries.push({
      id: "ep3:combination",
      beat: "live",
      section: "notes",
      heading: "Sok’s copied marks",
      text: "១ · ៥ · ០ · ៧. Each dial turns forward through ten numerals.",
    });
  if (p.flags.get("ep3.memory.written", false))
    entries.push({
      id: "ep3:revelation",
      beat: "live",
      section: "notes",
      heading: "The fourth name",
      text: "Sok erased Vuthy and wrote me into the debt. Kanha is my mother. Pich is my brother. The journal was an apology, and a trap.",
    });
  for (const [id, name, description] of [
    ["lok", "Pa Lok", "He rowed Kanha here in 1920. His raft is south-west of the market."],
    [
      "vuthy",
      "Vuthy",
      "Grandmother told him whose name was written first. He wants me to leave the seals alone.",
    ],
    ["pich", "Pich", "Small footsteps on dry boards. He is leading me away from the water."],
  ])
    entries.push({
      id: "ep3:person:" + id,
      beat: "live",
      section: "people",
      heading: name,
      text: description,
    });
  for (const id of p.lore)
    entries.push({
      id: "ep3:lore:" + id,
      beat: "live",
      section: "lore",
      heading: NOTES[id].title,
      text: NOTES[id].text,
      pageBreakBefore: true,
    });
  if (!p.lore.length)
    entries.push({
      id: "ep3:no-lore",
      beat: "live",
      section: "lore",
      text: "Five records remain in the wards, doctor’s quarters and vault.",
    });
  const market = at.x < -40;
  const shapes: MapShape[] = market
    ? [
        { kind: "rect", x: -67.5, y: -9, w: 7, h: 22, walls: true },
        { kind: "rect", x: -75, y: 10.5, w: 6, h: 5 },
        { kind: "label", x: -75, y: 16.5, text: "Pa Lok" },
        { kind: "label", x: -63, y: -3, text: "Vuthy" },
        { kind: "label", x: -76, y: 4, text: "Noodle seller" },
      ]
    : [
        { kind: "rect", x: -12, y: -11, w: 24, h: 21, walls: true },
        { kind: "rect", x: -14, y: -4.5, w: 4, h: 15 },
        { kind: "rect", x: -7, y: -27.5, w: 14, h: 9, walls: true },
        { kind: "rect", x: -11.8, y: -10.8, w: 9.4, h: 13.8 },
        { kind: "path", points: VILLAGE.escape.map((p) => [p[0], p[2]]) },
        { kind: "label", x: -10, y: 8, text: "West stair ↑" },
        { kind: "label", x: -9, y: -8, text: "Doctor / stove" },
        { kind: "label", x: 3, y: -8, text: "Generator" },
        { kind: "label", x: -4, y: -25, text: "Safe / cellar ↓" },
        { kind: "label", x: -22, y: -18, text: "Last stilt" },
        { kind: "label", x: -14, y: 5, text: "Upper deck" },
        { kind: "label", x: -2, y: 13, text: "Landing" },
      ];
  shapes.push({ kind: "you", x: at.x, y: at.z, r: 0.7 });
  const map: NotebookMap = {
    title: market ? "Tonle Sap · Market" : "The clinic · dry routes",
    bounds: market ? [-82, -18, -48, 20] : [-27, -30, 18, 19],
    labelSize: 0.9,
    bindingOffset: 0,
    shapes,
    description:
      "Hand-copied from Sok’s notes. Upper routes lie above the water; the cellar is down the north-east ramp.",
  };
  entries.push({
    id: "live:map",
    beat: "live",
    section: "map",
    heading: map.title,
    text: map.description,
  });
  const nights: NightMark[] = [
    "ink",
    "ink",
    "ink",
    "ink",
    p.stage === "complete" ? "ink" : "pencil",
    "empty",
    "empty",
  ];
  return {
    signature: JSON.stringify([entries, map, checkpoint]),
    entries,
    map,
    checkpoint,
    loreFound: p.lore.length,
    loreTotal: 5,
    nights,
  };
}
