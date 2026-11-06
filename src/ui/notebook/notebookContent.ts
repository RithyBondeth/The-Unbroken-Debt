import type { Flags } from "../../core/Flags";
import type { Inventory } from "../../systems/inventory/Inventory";
import { currentObjective, notebookClues } from "../../episodes/ep1/data/notebook";
import { EP1_SKETCHBOOK } from "../../episodes/ep1/data/sketchbook";
import type { NightMark, SectionId, SketchEntry } from "../diegetic/sketchbookContent";
import { notebookMap, type NotebookMap } from "./NotebookMap";

export interface NotebookSnapshot {
  signature: string;
  entries: SketchEntry[];
  map: NotebookMap;
  checkpoint: string;
  loreFound: number;
  loreTotal: number;
  nights: NightMark[];
}

/** Read-only projection of durable state; live pages never become saved discoveries. */
export function notebookContent(
  flags: Flags,
  inventory: Inventory,
  written: ReadonlySet<string>,
  at: { x: number; y: number; z: number },
  checkpoint: string,
): NotebookSnapshot {
  const objective = currentObjective(flags, inventory);
  const clues = new Map(notebookClues(written).map((c) => [c.id, c.text]));
  const entries: SketchEntry[] = [];
  const live = (
    id: string,
    section: SectionId,
    heading?: string,
    text?: string,
    smallText?: string,
  ) => entries.push({ id: `live:${id}`, beat: "live", section, heading, text, smallText });
  live("objective", "now", objective.title, objective.detail);
  live("checkpoint", "now", undefined, undefined, checkpoint);
  for (const [i, task] of objective.tasks.entries()) {
    live(
      `task:${i}`,
      "now",
      i === 0 ? "Checklist" : undefined,
      `${task.done ? "✓" : "○"} ${task.text}`,
    );
    if (i === 0) entries[entries.length - 1].pageBreakBefore = true;
  }
  const map = notebookMap(
    flags.get("ep1.checkpoint", "CP0") === "CP0",
    { x: Math.round(at.x * 10) / 10, y: at.y, z: Math.round(at.z * 10) / 10 },
    flags.get("ep1.act2.started", false),
  );
  live("map", "map", map.title, map.description);
  for (const entry of EP1_SKETCHBOOK.entries) {
    if (!written.has(entry.id) || entry.section === "people") continue;
    entries.push({
      ...entry,
      section: entry.section === "now" ? "notes" : entry.section,
      text: clues.get(entry.id) ?? entry.text,
    });
  }
  const people: [string, string, string][] = [
    ["P-SORA", "Sora", "An illustrator returning to her family’s village."],
    [
      "P-YAYMEY",
      "Yay Mey / Mak Yey",
      flags.get("ep1.phone.answered", false)
        ? "My grandmother. She called from home; she knows the funeral duties."
        : "My grandmother, back in our family’s village.",
    ],
    [
      "P-SOK",
      "Uncle Sok",
      "His death brought me home. His house is the centre of tonight’s vigil.",
    ],
  ];
  if (flags.get("ep1.arrival.callComplete", false) || written.has("P-VUTHY"))
    people.push([
      "P-VUTHY",
      "Vuthy",
      "My cousin. He has taken Grandmother somewhere she can rest and promises to return at dawn.",
    ]);
  for (const [id, name, description] of people) {
    const source = EP1_SKETCHBOOK.entries.find((e) => e.id === id);
    entries.push({
      id,
      beat: "live",
      section: "people",
      heading: name,
      text: description,
      khmer: source?.khmer,
      drawing: { id: "portrait", height: 102 },
      pageBreakBefore: true,
    });
  }
  if (!entries.some((e) => e.section === "notes"))
    live(
      "empty-notes",
      "notes",
      undefined,
      "No clues recorded yet. Discoveries will be written here when you find them.",
    );
  const loreFound = entries.filter((e) => e.section === "lore").length;
  const loreTotal = EP1_SKETCHBOOK.loreCount;
  if (!loreFound)
    live(
      "empty-lore",
      "lore",
      undefined,
      "No documents found yet. Look for letters, records and hidden pages during your journey.",
    );
  live("lore-count", "lore", undefined, undefined, `${loreFound} of ${loreTotal} documents found.`);
  let nights: NightMark[] = Array<NightMark>(7).fill("empty");
  for (const entry of entries) if (entry.nights) nights = [...entry.nights];
  return {
    nights,
    signature: JSON.stringify([entries, map, checkpoint]),
    entries,
    map,
    checkpoint,
    loreFound,
    loreTotal,
  };
}
