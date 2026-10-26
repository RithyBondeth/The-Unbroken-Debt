import type { Line } from "./prologue";

/** English master lines from Episode 1 Script, A1-01 through A1-05. */
export const ARRIVAL: Record<"road" | "greeting" | "vuthy" | "duties", Line[]> = {
  road: [
    {
      id: "E1-A1-01-1",
      speaker: "Driver",
      text: "No further, miss. The road is under water. And not to that house, not tonight.",
      seconds: 6,
    },
    {
      id: "E1-A1-01-2",
      speaker: "Sora",
      text: "It's all right. I used to know the way.",
      seconds: 3,
    },
  ],
  greeting: [
    {
      id: "E1-A1-03-1",
      speaker: "Mak Yey · Phone",
      text: "Sora. Child. You made it. Vuthy brought me to our relatives’ house to rest. You are alone there tonight.",
      seconds: 8,
    },
    {
      id: "E1-A1-03-2",
      speaker: "Mak Yey · Phone",
      text: "You did not come for your mother's memorial. Three years, Sora.",
      seconds: 5,
    },
    { id: "E1-A1-03-3", speaker: "Sora", text: "I know, Yay. I'm here now.", seconds: 3 },
  ],
  vuthy: [
    {
      id: "E1-A1-04-1",
      speaker: "Vuthy · Phone",
      text: "Cousin. It's been a long time.",
      seconds: 3,
    },
    {
      id: "E1-A1-04-2",
      speaker: "Vuthy · Phone",
      text: "Grandmother hasn't slept in two days. All this incense and thread… it's what the old people need, I suppose.",
      seconds: 7,
    },
    {
      id: "E1-A1-04-3",
      speaker: "Vuthy · Phone",
      text: "I brought Grandmother here before you arrived. I’ll come back at dawn, before the office. Don’t let her frighten you with stories.",
      seconds: 7,
    },
  ],
  duties: [
    {
      id: "E1-A1-05-1",
      speaker: "Mak Yey · Phone",
      text: "I left three blessed matches beside the upstairs altar. Keep them for when you need them most. Tonight you keep his watch. Three things.",
      seconds: 9,
    },
    {
      id: "E1-A1-05-2",
      speaker: "Mak Yey · Phone",
      text: "Keep your lamp burning. A soul should not be left in the dark.",
      seconds: 4,
    },
    {
      id: "E1-A1-05-3",
      speaker: "Mak Yey · Phone",
      text: "Keep the four incense sticks alight, one at each corner of him.",
      seconds: 4,
    },
    {
      id: "E1-A1-05-4",
      speaker: "Mak Yey · Phone",
      text: "And the thread around the tent. It must not break. Whatever you hear.",
      seconds: 5,
    },
  ],
};

/** A2-01: insects die away, the gust snuffs the flames, then weight crosses the hall. */
export const ACT_TWO_OPENING = {
  quietSeconds: 4,
  snuffSeconds: 1.2,
  stepTimes: [6, 7.15, 8.35, 9.6, 10.9],
  endSeconds: 13,
};

/** Flames in the pavilion must remain separate from static batches so they can go out. */
export const TENT_FLAME_MESH =
  /^(lantern_flame_\d+|altar_candle_\d+_flame|altar_globe_\d+|coffin_lamp_flame|step_candle_\d+_flame)$/;

export const ARRIVAL_NOTE = [
  {
    title: "Sora — from Mak Yey",
    text: "Vuthy has taken me to our relatives’ house to rest. We left before you arrived. Answer the telephone in the upstairs hall; I will call until you pick up. Vuthy will return at dawn.\n\nI blessed three matches and tied the box with red thread. It is beside the upstairs altar. Keep them for when you need them most. Arrange the ancestors’ offering as your mother did; her drawing is beside the tray. Keep your lamp burning, tend the four corner incense sticks, and keep the thread around the tent whole. Whatever you hear, do not break it.",
  },
];
