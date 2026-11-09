import type { AudioSystem } from "@/audio/AudioSystem";

/**
 * Episode 2's recorded sound: CC0 field recordings and Foley from Freesound, cut
 * and levelled by tools/audio/make-ep2-audio.sh (sources and licences in
 * tools/audio/ep2-freesound.json and docs/production/credits.md).
 */

/** Streamed stereo beds, heard everywhere (each a seamless loop at -20 LUFS). */
export const BEDS = {
  insects: ["amb_ep2_insects_a", "amb_ep2_insects_b", "amb_ep2_insects_c"],
  canopy: ["amb_ep2_wind_canopy"],
  leaves: ["amb_ep2_wind_leaves"],
} as const;

/** Streamed mono beds placed in the world. */
export const PLACED_BEDS = {
  frogsPond: "amb_ep2_frogs_a",
  frogsWest: "amb_ep2_frogs_b",
  pond: "amb_ep2_pond",
} as const;

/** One-shot takes, decoded up front (mono, peak -3 dBFS, whole decays kept). */
export const SHOTS = {
  /** Index 0 is the smallest bell, 2 the largest, as in the hall's rack. */
  bells: ["sfx_ep2_bell_small", "sfx_ep2_bell_middle", "sfx_ep2_bell_large"],
  gong: ["sfx_ep2_gong_1", "sfx_ep2_gong_2"],
  drum: ["sfx_ep2_drum_1", "sfx_ep2_drum_2", "sfx_ep2_drum_3"],
  knock: ["sfx_ep2_knock_1", "sfx_ep2_knock_2", "sfx_ep2_knock_3", "sfx_ep2_knock_4"],
  splinter: [
    "sfx_ep2_splinter_1",
    "sfx_ep2_splinter_2",
    "sfx_ep2_splinter_3",
    "sfx_ep2_splinter_4",
    "sfx_ep2_splinter_5",
  ],
  creakTree: [
    "sfx_ep2_creak_tree_1",
    "sfx_ep2_creak_tree_2",
    "sfx_ep2_creak_tree_3",
    "sfx_ep2_creak_tree_4",
  ],
  creakBamboo: [
    "sfx_ep2_creak_bamboo_1",
    "sfx_ep2_creak_bamboo_2",
    "sfx_ep2_creak_bamboo_3",
    "sfx_ep2_creak_bamboo_4",
  ],
  gust: ["sfx_ep2_gust_1", "sfx_ep2_gust_2", "sfx_ep2_gust_3", "sfx_ep2_gust_4", "sfx_ep2_gust_5"],
  dog: ["sfx_ep2_dog_1", "sfx_ep2_dog_2", "sfx_ep2_dog_3", "sfx_ep2_dog_4"],
  owl: ["sfx_ep2_owl_1", "sfx_ep2_owl_2", "sfx_ep2_owl_3"],
  gecko: ["sfx_ep2_gecko_1", "sfx_ep2_gecko_2"],
  water: ["sfx_ep2_water_1", "sfx_ep2_water_2"],
  clay: ["sfx_ep2_clay_1", "sfx_ep2_clay_2", "sfx_ep2_clay_3", "sfx_ep2_clay_4"],
} as const;

export type ShotKind = keyof typeof SHOTS;

/**
 * Evens out the takes inside a kind (they were levelled by peak, not loudness):
 * the middle bell is a hot close recording, the small one a quiet ring.
 */
export const TAKE_TRIM: Partial<Record<string, number>> = {
  sfx_ep2_bell_small: 0.8,
  sfx_ep2_bell_middle: 0.4,
  sfx_ep2_bell_large: 0.85,
  sfx_ep2_creak_tree_4: 0.6,
  sfx_ep2_gecko_2: 0.7,
};

/**
 * The monks' recitation of the Dharma in Pali, streamed from the hall
 * (recorded for the project at a pagoda; art-source/audio/ep2, S2-032).
 */
export const SMOT = "amb_ep2_chant";

/** Sora's footsteps on leaves (Kenney, CC0), borrowed for steps that follow her. */
export const LEAF_STEPS = [0, 1, 2, 3, 4].map((k) => `assets/shared/audio/sfx_step_leaves_00${k}`);

/** The URLs of an Episode 2 sound by name (or of `path` as given), Opus first, AAC after. */
export function soundUrls(nameOrPath: string, base = import.meta.env.BASE_URL): string[] {
  const path = nameOrPath.includes("/") ? nameOrPath : `assets/ep2/audio/${nameOrPath}`;
  return [`${base}${path}.ogg`, `${base}${path}.m4a`];
}

/** Every recorded Episode 2 file the game asks for, by name. */
export function allRecordings(): string[] {
  return [
    ...Object.values(BEDS).flat(),
    ...Object.values(PLACED_BEDS),
    ...Object.values(SHOTS).flat(),
  ];
}

/** Whether the recording is there: the dev server answers a missing file with the page. */
export async function hasRecording(urls: string[]): Promise<boolean> {
  try {
    const response = await fetch(urls[0], { method: "HEAD" });
    return response.ok && (response.headers.get("content-type") ?? "").startsWith("audio");
  } catch {
    return false;
  }
}

/** Decodes every take of each kind (missing ones are left out). */
export async function loadShots(
  audio: AudioSystem,
): Promise<Map<ShotKind, { name: string; buffer: AudioBuffer }[]>> {
  const kinds = Object.entries(SHOTS) as [ShotKind, readonly string[]][];
  const loaded = await Promise.all(
    kinds.map(async ([kind, names]) => {
      const takes = await Promise.all(
        names.map(async (name) => ({ name, buffer: await audio.load(soundUrls(name)) })),
      );
      return [
        kind,
        takes.filter((t): t is { name: string; buffer: AudioBuffer } => t.buffer !== null),
      ] as const;
    }),
  );
  return new Map(loaded);
}
