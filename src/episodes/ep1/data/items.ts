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
  shed_key: { name: "Storage shed key", note: "From Yay Mey's sewing box." },
  sok_journal: { name: "Sok’s journal pages", note: "A bargain in 1910. Four lives. Five seals." },
  drawer_key: {
    name: "Sok’s desk key",
    note: "A small warded brass key from the ancestral altar.",
  },
  sok_journal_b: {
    name: "Sok’s final instructions",
    note: "Three key pieces. The jars beneath the house. Do not turn around.",
  },
  brass_key_bow: { name: "Brass key · broken bow", note: "A worn ring and the first fracture." },
  brass_key_shaft: {
    name: "Brass key · broken shaft",
    note: "Two jagged ends. It fits between the others.",
  },
  brass_key_bit: {
    name: "Brass key · broken bit",
    note: "Three uneven teeth for an old chest lock.",
  },
  brass_key: {
    name: "Sok’s chest key",
    note: "The three pieces fitted together. Behind his floorboards.",
  },
  bronze_token: {
    name: "Bronze Token",
    note: "Grandfather’s pendant. The first seal; return it to the burner.",
  },
  seal_map: {
    name: "Sok’s folded map",
    note: "A river and five faint marks. Keep it for after the ritual.",
  },
  folded_slip: { name: "Sok’s folded slip", note: "Sealed with red thread and wax. Unread." },
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
