export interface TaxiLine {
  at: number;
  speaker: "Sora" | "Driver";
  text: string;
  seconds: number;
  /** The speaker's Khmer take number and its duration in seconds. */
  voice: number;
  clip: number;
}

/**
 * The exchange on the way to the village; leave silence around the roadside
 * glimpse. Both speakers have Khmer dialogue under the English subtitles.
 */
export const TAXI_CONVERSATION: readonly TaxiLine[] = [
  {
    at: 2,
    speaker: "Driver",
    text: "The road is flooded. Is someone expecting you?",
    seconds: 4.5,
    voice: 1,
    clip: 3.91,
  },
  {
    at: 6.5,
    speaker: "Sora",
    text: "My grandmother called. I'm going to Uncle Sok's house.",
    seconds: 4.8,
    voice: 1,
    clip: 3.41,
  },
  {
    at: 12,
    speaker: "Driver",
    text: "I took mourners there this morning.",
    seconds: 3.7,
    voice: 2,
    clip: 2.89,
  },
  {
    at: 16,
    speaker: "Sora",
    text: "I haven't been home in years. It looks different.",
    seconds: 4.3,
    voice: 2,
    clip: 3.91,
  },
  {
    at: 21,
    speaker: "Driver",
    text: "The trees have grown. The road hasn't changed.",
    seconds: 4,
    voice: 3,
    clip: 3.21,
  },
  {
    at: 25.6,
    speaker: "Sora",
    text: "You keep looking into the forest.",
    seconds: 3,
    voice: 3,
    clip: 2.25,
  },
  {
    at: 29.2,
    speaker: "Driver",
    text: "People don't wait beside this road. Not in this weather.",
    seconds: 5.4,
    voice: 4,
    clip: 4.51,
  },
  {
    at: 34.7,
    speaker: "Sora",
    text: "Then who are you looking for?",
    seconds: 2.8,
    voice: 4,
    clip: 1.93,
  },
  {
    at: 40,
    speaker: "Sora",
    text: "Wait—there was someone in the road! Did you see that?",
    seconds: 4.3,
    voice: 5,
    clip: 4.01,
  },
  {
    at: 44.8,
    speaker: "Driver",
    text: "Keep your eyes forward. Don't call to it.",
    seconds: 4,
    voice: 5,
    clip: 3.71,
  },
  {
    at: 49.5,
    speaker: "Sora",
    text: "There's nobody behind us.",
    seconds: 2.5,
    voice: 6,
    clip: 1.93,
  },
  {
    at: 53,
    speaker: "Driver",
    text: "Good. Keep your lamp covered until you're out.",
    seconds: 4.3,
    voice: 6,
    clip: 4.21,
  },
  {
    at: 58,
    speaker: "Sora",
    text: "Can't you take me to the house?",
    seconds: 3.3,
    voice: 7,
    clip: 2.41,
  },
  {
    at: 62,
    speaker: "Driver",
    text: "This is as far as I go. Follow the path to the house. Stay quiet.",
    seconds: 7,
    voice: 7,
    clip: 5.81,
  },
];

/** Select from the ride clock, including on resume, without replaying missed lines. */
export function taxiConversationAt(seconds: number): (TaxiLine & { index: number }) | null {
  const index = TAXI_CONVERSATION.findIndex(
    (line) => seconds >= line.at && seconds < line.at + line.seconds,
  );
  return index < 0 ? null : { ...TAXI_CONVERSATION[index], index };
}

/** The speaker's recorded Khmer line, Opus first, AAC for Safari. */
export function taxiVoiceUrls(speaker: TaxiLine["speaker"], voice: number): string[] {
  const base = `assets/ep1/audio/vo_taxi_${speaker.toLowerCase()}_km_${voice}`;
  return [`${base}.ogg`, `${base}.m4a`];
}
