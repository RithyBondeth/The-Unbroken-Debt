export interface ItemInfo {
  name: string;
  /** Shown under the name in the satchel; `{n}` is replaced by the count. */
  note?: string;
}

/** Items in the satchel. The satchel itself holds the rest, so it is not listed. */
export const ITEMS: Record<string, ItemInfo> = {
  letters: { name: "Yay Mey's letters", note: "Tied with red string. Unopened." },
  matches: { name: "Matchbox", note: "{n} matches" },
  sketchbook: { name: "Sketchbook" },
  lamp: { name: "Hurricane lamp", note: "Raise it to read the gauge." },
  oil: { name: "Lamp oil", note: "{n} bottles of kerosene" },
  incense: { name: "Incense", note: "A bundle of four sticks" },
  // The betel offering (A1-08).
  betel_tray: { name: "Betel tray", note: "Lacquered, and empty." },
  betel: { name: "Betel leaves", note: "Fresh from the vine." },
  areca: { name: "Areca nuts" },
  lime: { name: "Lime pot", note: "White lime paste." },
  candle: { name: "Candle" },
  blessed_matches: {
    name: "Blessed matches",
    note: "{n}, blessed by Yay Mey. Keep them for when I need them most.",
  },
};
