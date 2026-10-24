import type { Line } from "./prologue";

/**
 * The betel offering (Episode 1, section 6.1; Beat Sheet A1-06 to A1-09): Kanha's
 * drawing shows where each offering sits on the round tray; Sora gathers them,
 * sets the tray before the ancestral altar and arranges it. The contents and the
 * layout are to confirm with the cultural advisor (Cultural Guide: Betel).
 */

/** What goes on the tray, each one an item in the satchel. */
export const OFFERINGS = ["betel", "areca", "lime", "candle", "incense"] as const;
export type Offering = (typeof OFFERINGS)[number];

/** Places on the tray, as seen from in front of the altar. */
export const SLOTS = ["back", "left", "centre", "right", "front"] as const;
export type Slot = (typeof SLOTS)[number];

/** Kanha's layout, as in her drawing (tools/drawings/village.mjs, kanha_drawing). */
export const KANHA_LAYOUT: Record<Slot, Offering> = {
  back: "candle",
  left: "betel",
  centre: "lime",
  right: "areca",
  front: "incense",
};

/** Where each slot sits from the tray's centre, in Blender metres (x east, y north). */
export const SLOT_OFFSETS: Record<Slot, [number, number]> = {
  back: [0, 0.11],
  left: [-0.11, 0],
  centre: [0, 0],
  right: [0.11, 0],
  front: [0, -0.11],
};

export type Tray = Partial<Record<Slot, Offering>>;

/** Whether every slot is filled, and which hold the wrong offering. */
export function checkTray(tray: Tray): { complete: boolean; wrong: Slot[] } {
  const complete = SLOTS.every((slot) => tray[slot] !== undefined);
  const wrong = SLOTS.filter(
    (slot) => tray[slot] !== undefined && tray[slot] !== KANHA_LAYOUT[slot],
  );
  return { complete, wrong };
}

/**
 * What a slot holds after Sora uses it again: the next offering she has with her
 * that isn't already on the tray, in a fixed order, and after the last of them
 * the slot is cleared (the offering goes back in her satchel).
 */
export function nextOffering(
  tray: Tray,
  slot: Slot,
  held: (o: Offering) => boolean,
): Offering | null {
  const current = tray[slot];
  const free = OFFERINGS.filter(
    (o) => o === current || (held(o) && !SLOTS.some((s) => s !== slot && tray[s] === o)),
  );
  const start = current ? free.indexOf(current) + 1 : 0;
  return free.slice(start).find((o) => o !== current) ?? null;
}

/** Matches Yay Mey has left blessed (Beat Sheet A1-09: "sanctified matches ×3"). */
export const BLESSED_MATCHES = 3;

/**
 * Seconds after the last change before Sora checks a full tray, so trying
 * each offering in a slot isn't judged on the way.
 */
export const JUDGE_DELAY = 2.5;

/** Script lines, by their id in the Episode 1 Script. Phone request and Sora’s responses to the drawing. */
export const BETEL_LINES = {
  request: {
    id: "E1-A1-06-1",
    speaker: "Mak Yey · Phone",
    text: "One more thing. Make the betel offering for the ancestors. Do it as your mother used to. Her drawing is still by the altar.",
    seconds: 7.5,
  },
  wrong: {
    id: "E1-A1-09-1",
    speaker: "Sora",
    text: "That doesn’t match Mother’s drawing. I should look again.",
    seconds: 3.2,
  },
  right: {
    id: "E1-A1-09-2",
    speaker: "Sora",
    text: "There. Just as Mother drew it.",
    seconds: 3.4,
  },
  preparedMatches: {
    id: "E1-A1-09-3",
    speaker: "Sora",
    text: "The offering is ready. Mak Yey’s blessed matches are beside the altar. I should keep them with me.",
    seconds: 6,
  },
} satisfies Record<string, Line>;

/** Sketchbook entries: the request (A1-06) and Sora's copy of the drawing (A1-08). */
export const BETEL_ENTRIES = { duties: "SB-02", request: "SB-03", drawing: "SB-03b" };
