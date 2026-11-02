import layout from "./garden-layout.json";
/** Episode 2 layout. Babylon X east / Y up / Z south, in metres. */
export type Point = { x: number; z: number };
export const ENTRY = { x: 0, y: 0.08, z: 33, yaw: Math.PI };
export const KUTI = { x: -18, y: 0.22, z: 15, yaw: Math.PI };
export const LIBRARY = { x: 0, y: 1.4, z: -29, yaw: Math.PI };
export const DAWN = { x: -12, y: 0.08, z: 8.5, yaw: Math.PI };
export const MEMORY = { x: 80, y: 0.08, z: 10, yaw: Math.PI };
export const BOUNDS = { minX: -29, maxX: 29, minZ: -39, maxZ: 40 };

export const ANCESTORS = [
  {
    id: "chea",
    name: "Chea",
    item: "rice",
    offering: "Rice balls",
    x: -12,
    z: 6.5,
    inscription:
      "Chea · 1840–1910. Even in the hungry season, Father kept a little rice for his children.",
  },
  {
    id: "wife",
    name: "Chea’s wife",
    item: "lotus",
    offering: "Lotus bud",
    x: 12,
    z: 3,
    inscription:
      "Beside Chea rests his wife. She tended the lotus pond; her hands always smelled of its flowers.",
  },
  {
    id: "chhun",
    name: "Chhun",
    item: "water",
    offering: "Sanctified water",
    x: -12,
    z: -7.5,
    inscription:
      "Chhun · 1867–1911. The boatman carried clean water to those too weak to reach the river.",
  },
  {
    id: "kanha",
    name: "Kanha",
    item: "rice",
    offering: "Rice balls",
    x: 12,
    z: -11,
    inscription:
      "Kanha · 1896–1925. She fed the sick before she ate. A bowl of rice waited by every bed.",
  },
] as const;
export type AncestorId = (typeof ANCESTORS)[number]["id"];
export type Offering = "rice" | "lotus" | "water";
/** Deep, small, middle: the verse's three bell sizes. */
export const BELL_ORDER = [2, 0, 1] as const;
/** Four 90-degree detents per mirror; engraved clue points to these orientations. */
export const MIRROR_TARGETS = [1, 3, 2] as const;
export const MIRROR_CLUES = [
  "First: face the open doorway.",
  "Second: face the river wall.",
  "Third: face the family cabinet.",
];
export const NOTES = {
  monk: {
    title: "Sophal’s letter · 1912",
    text: "Yay Mey brought Chea’s silver betel box today. It was filled with earth when the guardian returned it. She asked that it stay here until the one whose name is written comes to claim it. Sok came last year; I refused him. A younger man in a town suit asked about it this evening.",
  },
  hall_0: {
    title: "A villager’s account",
    text: "Chea said he wanted his children spared. But he spoke of land too, of never bowing his head before a rich man again. We heard both wishes beneath that tree. The family remembers the first. The village remembers the second.",
  },
  hall_1: {
    title: "Pchum Ben mural",
    text: "The painted figures offer food to the hungry dead. No one laughs at them or takes their share. The living keep the names of those who came before. Below the painting, a faded hand has drawn four flowers like those on the family stupas.",
  },
  library_0: {
    title: "Chea’s confession",
    text: "I asked that my children live, and that our line never know poverty again. I told myself the second wish was only another way of making the first. But I knew the weight of the silver box before I offered it.",
  },
  library_1: {
    title: "Record of Sok’s visit",
    text: "1931. Sok asked to remove his grandfather’s box. He knew the seal but could not open it. Only the named may break a seal. Before he left, he asked whether a physician could change a name in a birth register. The monk did not answer.",
  },
} as const;
export type NoteId = keyof typeof NOTES;

export const EP2_ITEMS = {
  blessed_thread: {
    name: "Blessed white thread",
    note: "From Venerable Sophal. Keep it for the last night.",
  },
  rice: { name: "Rice balls", note: "{n} portions. For the family stupas." },
  lotus: { name: "Lotus bud", note: "For Chea’s wife." },
  water: { name: "Sanctified water", note: "For Chhun." },
  clay_bowl: {
    name: "Empty clay bowls",
    note: "{n} distractions · G to throw. Keep the rice for the dead.",
  },
  family_record: { name: "Family record", note: "Chea’s plea and the cost of the land." },
  silver_betel_box: {
    name: "Silver Betel Box",
    note: "The second seal. Still filled with old earth.",
  },
  silver_inlay: {
    name: "Silver inlay",
    note: "The second broken seal. Keep it for the final night.",
  },
  clinic_photo: {
    name: "Tonle Sap clinic · 1920",
    note: "Uncle Sok, and my mother. She is pregnant.",
  },
};

/** Shared with Blender authoring; X east / Z south in this manifest. */
export const STUPAS: Point[] = layout.stupas;
export const GARDEN_TREES: Point[] = layout.trees;
export const GARDEN_OBSTACLES: Point[] = [...STUPAS, ...GARDEN_TREES];
export const PATROLS: Point[][] = [
  [
    { x: -14, z: 12 },
    { x: 14, z: 12 },
    { x: 14, z: -14 },
    { x: -14, z: -14 },
  ],
  [
    { x: -10, z: 12 },
    { x: -10, z: -14 },
    { x: 10, z: -14 },
    { x: 10, z: 12 },
  ],
  [
    { x: -14, z: 5 },
    { x: 14, z: 5 },
    { x: 14, z: -5 },
    { x: -14, z: -5 },
  ],
  [
    { x: -6, z: 12 },
    { x: -6, z: -14 },
    { x: 6, z: -14 },
    { x: 6, z: 12 },
  ],
  [
    { x: -14, z: -12 },
    { x: 14, z: -12 },
    { x: 14, z: 9 },
    { x: -14, z: 9 },
  ],
];
