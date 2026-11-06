import type { NotebookSnapshot } from "@/ui/notebook/notebookContent";
import type { NotebookMap, MapShape } from "@/ui/notebook/NotebookMap";
import type { SketchbookData, SketchEntry, NightMark } from "@/ui/diegetic/sketchbookContent";
import type { PagodaProgress } from "../PagodaProgress";
import { ANCESTORS, NOTES, MIRROR_CLUES, STUPAS, GARDEN_TREES } from "./pagoda";

export const EP2_SKETCHBOOK: SketchbookData = { entries: [], mapLabels: [], loreCount: 5 };
export function pagodaNotebook(
  p: PagodaProgress,
  at: { x: number; z: number },
  checkpoint: string,
): NotebookSnapshot {
  const stage = p.stage;
  const titles = {
    arrival: "The gates of Pchum Ben",
    garden: "The hungry garden",
    library: "Moonlight in the archive",
    memory: "Chea · 1910",
    escape: "Leave the library",
    dawn: "The dawn offering",
    complete: "Three nights remain.",
  };
  const details = {
    arrival:
      "Find Venerable Sophal in the warm wooden kuti, west of the processional path. Sok’s map led me here.",
    garden:
      "Four family stupas bear a silver five-petalled flower. Read their inscriptions, gather the offerings, then open the bronze lock at the pond.",
    library:
      "Guide the roof’s moonbeam across three bronze mirrors into the family cabinet. E turns a mirror one quarter turn. The silver line on its rim marks its direction.",
    memory:
      "I am walking in Chea’s memory. The forest shrine is ahead. What did he ask for, beneath that tree?",
    escape:
      "The guardian is pulling the library apart. Cross the bridge and reach Chea’s stupa on the west side of the garden. Keep moving.",
    dawn: "At Chea’s stupa: return the earth, light incense and remember the four ancestors in the order written here.",
    complete:
      "The second seal is broken. The photograph points to the floating clinic on Tonle Sap. Uncle Sok stands beside my mother. She is pregnant.",
  };
  const entries: SketchEntry[] = [
    {
      id: "live:objective",
      beat: "live",
      section: "now",
      heading: titles[stage],
      text: details[stage],
    },
    { id: "live:checkpoint", beat: "live", section: "now", smallText: checkpoint },
  ];
  if (stage === "garden")
    for (const [i, a] of ANCESTORS.entries())
      entries.push({
        id: "live:family:" + a.id,
        beat: "live",
        section: "now",
        heading: i === 0 ? "Family offerings" : undefined,
        text: `${p.offered(a.id) ? "✓" : "○"} ${a.name} · ${a.offering}`,
        pageBreakBefore: i === 0,
      });
  const shapes: MapShape[] = [
    { kind: "rect", x: -28, y: -38, w: 56, h: 65, walls: true },
    { kind: "rect", x: -21.5, y: 8.5, w: 7, h: 7, walls: true },
    { kind: "rect", x: 17.5, y: -8.5, w: 9, h: 15, walls: true },
    { kind: "rect", x: -17.5, y: -38.5, w: 35, h: 21 },
    { kind: "rect", x: -4.5, y: -36, w: 9, h: 8, walls: true },
    {
      kind: "path",
      points: [
        [0, 27],
        [0, 17],
        [-18, 17],
        [0, 17],
        [0, -18],
        [0, -28],
      ],
    },
    { kind: "label", x: -23, y: 19, text: "Kuti · Sophal" },
    { kind: "label", x: 16, y: 10, text: "Prayer hall" },
    { kind: "label", x: -6, y: -39, text: "Scripture library" },
    { kind: "label", x: -22, y: 30, text: "Naga gate" },
    { kind: "label", x: 6, y: -23, text: "Lotus pond" },
  ];
  for (const stupa of STUPAS)
    shapes.push({
      kind: "rect",
      x: stupa.x - 0.6,
      y: stupa.z - 0.6,
      w: 1.2,
      h: 1.2,
    });
  for (const tree of GARDEN_TREES)
    shapes.push({ kind: "rect", x: tree.x - 0.7, y: tree.z - 0.7, w: 1.4, h: 1.4 });
  for (const a of ANCESTORS) {
    shapes.push({
      kind: "label",
      x: a.x < 0 ? -24 : 15,
      y: a.z,
      text: `${p.offered(a.id) ? "✓ " : ""}${a.name}`,
    });
  }
  if (at.x < 40) shapes.push({ kind: "you", x: at.x, y: at.z, r: 1.2 });
  const map: NotebookMap = {
    title: "The Whispering Pagoda",
    bounds: [-30, -42, 30, 35],
    labelSize: 1.1,
    bindingOffset: 0,
    shapes,
    description:
      "The kuti is west of the gate. Four family stupas stand at the outer edges of the ash garden. Beyond them, the library rises over the lotus pond.",
  };
  entries.push({
    id: "live:map",
    beat: "live",
    section: "map",
    heading: map.title,
    text: map.description,
  });
  entries.push({
    id: "ep2:rules",
    beat: "live",
    section: "notes",
    heading: "Sophal’s rules",
    text: "The shrouded dead are blind. Dry leaves carry every step; moss and bare earth are quieter. C to crouch. Hold Space to quiet your breath for six seconds; holding too long ends in a gasp. G throws an empty clay bowl. The rice belongs to the dead. X closes the lamp shutter; it still burns oil. F extinguishes or lights the wick. R refills it.",
  });
  if (p.flags.get("ep2.monk.met", false)) {
    entries.push({
      id: "ep2:family",
      beat: "live",
      section: "notes",
      heading: "The family flower",
      text: ANCESTORS.map((a) => `${a.name}: ${a.offering}. ${a.inscription}`).join("\n\n"),
    });
    entries.push({
      id: "ep2:bells",
      beat: "live",
      section: "notes",
      heading: "Verse at the prayer hall",
      text: "First the deepest voice calls the earth. Then the smallest voice calls the sky. Last the middle voice carries us home. Large → small → middle. The bells carry far.",
    });
    entries.push({
      id: "ep2:mirrors",
      beat: "live",
      section: "notes",
      heading: "The bronze mirrors",
      text: `The silver lines must follow the engraved directions. ${MIRROR_CLUES.join(" ")}\n\nDetents: First 1 quarter turn, second 3, third 2, clockwise from their resting marks.`,
    });
  }
  entries.push({
    id: "ep2:people",
    beat: "live",
    section: "people",
    heading: "Venerable Sophal",
    text: "The blind head monk. Yay Mey entrusted Chea’s box to him in 1912. Only the named may break a seal; the guardian weighs the truth above everything.",
  });
  entries.push({
    id: "ep2:sora",
    beat: "live",
    section: "people",
    heading: "Sora",
    text: "An illustrator from Phnom Penh. My name was the fourth on Sok’s list. I kept the first seal’s map and his journal.",
  });
  for (const id of p.lore)
    entries.push({
      id: "ep2:lore:" + id,
      beat: "live",
      section: "lore",
      heading: NOTES[id].title,
      text: NOTES[id].text,
      pageBreakBefore: true,
    });
  if (!p.lore.length)
    entries.push({
      id: "ep2:no-lore",
      beat: "live",
      section: "lore",
      text: "Five records remain in the kuti, prayer hall and library.",
    });
  const nights: NightMark[] = [
    "ink",
    "ink",
    "ink",
    p.stage === "complete" ? "ink" : "pencil",
    "empty",
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
