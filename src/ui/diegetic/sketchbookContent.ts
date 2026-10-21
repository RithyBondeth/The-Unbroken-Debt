/**
 * What can be written in Sora's sketchbook (Controls and Interface, section 5).
 * Episodes provide the entries as data; the sketchbook draws them.
 */

export type SectionId = "map" | "now" | "notes" | "people" | "lore";

/** The ribbon tabs, in order. */
export const SECTIONS: readonly { id: SectionId; label: string }[] = [
  { id: "map", label: "Map" },
  { id: "now", label: "Now" },
  { id: "notes", label: "Notes" },
  { id: "people", label: "People" },
  { id: "lore", label: "Lore" },
];

/** The seven night circles on the map page (Art Bible, section 10). */
export type NightMark = "empty" | "pencil" | "ink";

export interface SketchEntry {
  /** Script ID, e.g. "SB-02" (Episode 1 Script, section 8). */
  id: string;
  /** Beat that writes it, e.g. "A1-05". */
  beat: string;
  section: SectionId;
  /** Sora's note in English (the master text). */
  text?: string;
  /** A line in Khmer script, written by a native speaker. */
  khmer?: string;
  /** A small drawing beside the note, drawn by `drawings.ts`. */
  drawing?: { id: string; height: number };
  /** Writing this entry updates the night circles on the map. */
  nights?: NightMark[];
}

/** A labelled place on the map page, in millimetres from the page's top-left. */
export interface MapLabel {
  text: string;
  khmer?: string;
  x: number;
  y: number;
}

export interface SketchbookData {
  entries: SketchEntry[];
  mapLabels: MapLabel[];
  /** Lore notes in the episode; missing ones show as empty outlines. */
  loreCount: number;
}
