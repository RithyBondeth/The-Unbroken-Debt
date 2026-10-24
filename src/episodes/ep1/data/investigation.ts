/** Episode 1 Script, A2-03–05. The English text is the translation of Sok's papers. */
export const JOURNAL_A = [
  {
    title: "To whoever keeps my vigil",
    text: "My grandfather Chea went to the guardian’s shrine in the forest in the famine year, with our family’s silver betel box in his hands. The village was dying. His children were dying. He came home with the box full of earth and a promise.",
  },
  {
    title: "The payments",
    text: "We were saved. We were given land, and rice, and this house. And every so often the guardian comes for one of us. Grandfather first, within days. My father the next year. My sister, Kanha, in 1920, in the water, while I held her hand and could do nothing.",
  },
  {
    title: "Five seals",
    text: "The pact is bound by five seals. Break all five, and the one who is named may end it. That is what the old men told me, and the monks, and the manuscripts. I believe them. I have to.",
  },
] as const;

/** English subtitles; each paragraph follows the duration of its Khmer voice recording. */
export const SOK_RECORDING = [
  "If this is playing, then I am dead, and you are the one keeping my vigil. Listen to me.",
  "In 1910 my grandfather, Chea, made a bargain with the guardian of the land. Our lives, and a fortune, for a price: one of us from each generation. Four lives. Three have been paid. My father. My sister.",
  "On the seventh night after my death, it will come to collect what is owed. Break the seals before then. There are five. The first is in my chest. Its key I gave to the water jars below the house. The key to my desk is where the ancestors keep watch.",
  "I tried to begin. If you are hearing this, I failed. Forgive me. Forgive me for all of it.",
] as const;

export const GOVERNOR = { min: 60, max: 90, correct: 78, initial: 64, holdSeconds: 1.8 } as const;
