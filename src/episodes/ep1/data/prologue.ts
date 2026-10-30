/**
 * Prologue content (Episode 1 Beat Sheet, section 3.1; Script, section 3.1):
 * the items Sora packs, her lines and Yay Mey's call, and the timing of the
 * scripted beats. English is the master text; Khmer voice and subtitles follow.
 */

/** The starting kit (P04): the door stays shut until Sora has all four. */
export const KIT = ["satchel", "sketchbook", "matches", "lamp"] as const;

/** Matches in the first box (Beat Sheet, section 5: "Start with 10"). */
export const STARTING_MATCHES = 10;

export interface Line {
  id: string;
  speaker: string;
  text: string;
  /** Seconds on screen (and, once recorded, roughly the line's length). */
  seconds: number;
}

/** Script lines, by their id in the Episode 1 Script. */
export const LINES = {
  letters: {
    id: "E1-P03-1",
    speaker: "Sora",
    text: "Grandma's letters… I can't read them tonight.",
    seconds: 4.2,
  },
  call1: {
    id: "E1-P06-1",
    speaker: "Yay Mey",
    text: "Sora? Sora, is that you? Child, can you hear me?",
    seconds: 3.8,
  },
  call2: {
    id: "E1-P06-2",
    speaker: "Sora",
    text: "Yay? What's wrong? It's past eight—",
    seconds: 2.6,
  },
  call3: {
    id: "E1-P06-3",
    speaker: "Yay Mey",
    text: "You must come home. Right now. Uncle Sok… he broke it… it's inside the house—",
    seconds: 4.6,
  },
  call4: { id: "E1-P06-4", speaker: "Sora", text: "Yay? …Yay!", seconds: 2.4 },
} satisfies Record<string, Line>;

/** The title card after the journey (P07). The Khmer needs the advisor's review. */
export const TITLE_CARD = { title: "Night 3", khmer: "យប់ទី ៣" };

/** Seconds between scripted beats. */
export const TIMING = {
  /** P01: pencil hints appear if the player hasn't looked or moved by then. */
  idleHint: 3,
  /** P05 starts this long after the kit is complete. */
  dreadDelay: 2.5,
  /** P06: the telephone rings this long after the ink spills. */
  ringDelay: 5,
  /** Checkpoint CP1: the carriage arrives at the village at 11:30 PM. */
  cp1Clock: "23:30",
};

/** Sketchbook entry the ink blot writes (P05). */
export const INK_BLOT_ENTRY = "SB-01";
