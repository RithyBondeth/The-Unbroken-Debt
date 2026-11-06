import layout from "./village-layout.json";
import type { ItemInfo } from "../../ep1/data/items";

/** Feet planted on the upper veranda, drawn towards the fourth candle. */
export const RITUAL_FIGURES = {
  mother: [-13.05, 3.35, 2.7],
  child: [-12.2, 3.35, 3.1],
} as const;

export const VILLAGE = layout;
export const FUSE_IDS = ["reception", "ward", "attic"] as const;
export type FuseId = (typeof FUSE_IDS)[number];
export const LEAK_IDS = ["west", "east"] as const;
export type LeakId = (typeof LEAK_IDS)[number];
export const SAFE_CODE = [1, 5, 0, 7] as const;
export const KHMER_DIGITS = "០១២៣៤៥៦៧៨៩";
export const BOUNDS = { minX: -85, maxX: 25, minZ: -36, maxZ: 25 };
export const NOTES = {
  admission: {
    title: "Admission register · 1920",
    text: "Kanha. Admitted by boat during the flood. An infant boy delivered alive; both lost before morning. The last line is in another hand: do not send a second name to the water.\n\nA later pencil annotation gives the safe’s four marks: ១ · ៥ · ០ · ៧. The torn calendar key is pinned above the register.",
  },
  mother: {
    title: "Kanha’s folded note",
    text: "Sora, if your uncle brings this home, there is a little brother for you. I have called him Pich. Your grandfather says the lake will be kind this year.\n\nThe ink ends in a line of pale water. On the back is a verse: Kanha, I know your name. Pich, take your mother’s hand. The water has held you long enough.",
  },
  calendar: {
    title: "The doctor’s calendar key",
    text: "A torn printed calendar, its margins covered in Sok’s notes. The copied safe marks read ១ · ៥ · ០ · ៧.\n\nNumeral key: ០ ១ ២ ៣ ៤ ៥ ៦ ៧ ៨ ៩ = 0 1 2 3 4 5 6 7 8 9. Read the copied marks from left to right. The lunar-date annotation is too damaged to read.",
  },
  letter: {
    title: "Unsent letter to Vuthy · 1931",
    text: "My son. Yours was the fourth name. I scraped it from the earth and wrote Sora’s. She was Kanha’s child. She had no one left to ask why.\n\nI told myself that saving you was enough. Then I learned that only the named debtor can undo the seals. I have left her the way out that I denied her mother.",
  },
  return: {
    title: "Sok’s last return",
    text: "The jar still holds earth from the shrine of 1910. The third payment has not left the clinic. At night a child walks above the flooded boards. Wherever he goes, there is still a dry way through.\n\nWhen the jar is clean, call her by her own name. Give her one more light. A seal can break without a soul being freed.",
  },
} as const;
export type NoteId = keyof typeof NOTES;
export const EP3_ITEMS: Record<string, ItemInfo> = {
  clinic_supplies: {
    name: "Planks and folded tarpaulin",
    note: "For the two broken ward windows.",
  },
  brass_fuse: { name: "Dry brass fuse", note: "{n} sealed fuse(s) for the drainage pump." },
  terracotta_jar: {
    name: "Terracotta Water Jar",
    note: "The third seal. Earth from the shrine of 1910.",
  },
  shrine_soil: { name: "Earth from the third seal", note: "Keep it for the last night." },
  brass_compass: { name: "Pa Lok’s brass compass", note: "East, toward Kampong Cham." },
  burnt_rubber: {
    name: "Oilcloth-wrapped rubber",
    note: "Compagnie des Caoutchoucs de Kampong Cham · 1928.",
  },
  yellow_candle: { name: "Yellow candles", note: "{n} candle(s), wrapped dry by Pa Lok." },
};
