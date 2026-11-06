import { dialogueScript, type CinematicScript } from "../../../shared/cinematics/timeline";
export const SOPHAL_SCENE = dialogueScript("ep2-sophal", "Sophal’s kuti", [
  ["Sora", "Sok’s map led me here. You kept my great-grandfather’s box."],
  [
    "Venerable Sophal",
    "Yay Mey brought it in 1912. The guardian had returned it, filled with earth.",
  ],
  [
    "Venerable Sophal",
    "That was the sign that the offering was accepted. Sok asked for it last year. I refused him.",
  ],
  ["Sora", "And tonight?"],
  [
    "Venerable Sophal",
    "Tonight it belongs to the one who is named. Only the named can break a seal.",
  ],
  [
    "Venerable Sophal",
    "The guardian weighs the truth above everything. Remember that when the old story returns.",
  ],
  [
    "Venerable Sophal",
    "The hungry have no sight. They listen to the leaves under your feet, and to your breath.",
  ],
  [
    "Venerable Sophal",
    "Crouch on the moss. Hold your breath only a little while. The shutter closes without a match.",
  ],
  [
    "Venerable Sophal",
    "Find the four silver flowers. Feed your family’s dead. Keep the rice for them.",
  ],
  [
    "Venerable Sophal",
    "The empty bowls can draw the hungry away. There is oil at my table. Rest here when you need to.",
  ],
  ["Venerable Sophal", "Take this thread. Keep it. You will need it when the last night comes."],
]);
export const HARVEST_SCENE: CinematicScript = {
  id: "ep2-harvest",
  title: "The harvest · 1909",
  duration: 24,
  cues: [
    { at: 1, duration: 5, speaker: "Chea", text: "Before the hunger, there was this." },
    {
      at: 8,
      duration: 6,
      speaker: "Chea",
      text: "The harvest was in. My children would not come away from the fire.",
    },
    {
      at: 17,
      duration: 5.5,
      speaker: "Chea",
      text: "I thought that a full granary meant we were safe.",
    },
  ],
};
export const FAMINE_SCENE: CinematicScript = {
  id: "ep2-famine",
  title: "The same village · 1910",
  duration: 14,
  cues: [
    { at: 1, duration: 5, speaker: "Chea", text: "One season. That was all it took." },
    {
      at: 7,
      duration: 6,
      speaker: "Chea",
      text: "No grain. No medicine. The coughing did not stop when the sun came up.",
    },
  ],
};
export const BARGAIN_SCENE = dialogueScript("ep2-bargain", "The forest shrine · 1910", [
  ["Chea", "My hands are shaking. The silver is all I have left."],
  ["The guardian", "What do you want, Chea?"],
]);
export const COLLAPSE_SCENE: CinematicScript = {
  id: "ep2-collapse",
  title: "The library",
  duration: 8,
  cues: [
    { at: 0.5, duration: 3, speaker: "Sora", text: "The page… I was inside the page." },
    {
      at: 4,
      duration: 3.6,
      speaker: "Sora",
      text: "The roof is splitting. Across the bridge. Back to Chea’s stupa.",
    },
  ],
};
export const DAWN_SCENE: CinematicScript = {
  id: "ep2-dawn",
  title: "The dawn offering · 4:00 AM",
  duration: 14,
  cues: [
    { at: 1, duration: 4, speaker: "Sora", text: "The earth goes back to you." },
    {
      at: 6,
      duration: 6.5,
      speaker: "Sora",
      text: "I will not leave your names buried with the bargain.",
    },
  ],
};
export const PHOTO_SCENE = dialogueScript("ep2-photograph", "The lining of the box", [
  ["Sora", "Uncle Sok. In a physician’s coat."],
  ["Sora", "Tonle Sap clinic. Nineteen twenty."],
  ["Sora", "Mother? You were…"],
  ["Sora", "The second mark. Three nights remain."],
]);
