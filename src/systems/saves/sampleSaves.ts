import type { SaveData } from "./SaveData";

/**
 * A realistic save at the end of Episode 1, with the flags the Beat Sheet and
 * Story Bible name, every lore note and sketchbook entry. Used to size save
 * codes and to test the round trip (Spike S6).
 */
export function endOfEpisodeOne(): SaveData {
  const flags: SaveData["flags"] = {
    "ep1.act": 3,
    "ep1.letters.taken": true,
    "ep1.betel.done": true,
    "ep1.betel.firstTry": true,
    "ep1.incense.neglected": false,
    "ep1.journal.shared": true,
    "ep1.gramophone.solved": true,
    "ep1.shed.opened": true,
    "ep1.fragments.count": 3,
    "ep1.seal1.broken": true,
    "ep1.vuthy.left": false,
    "ep1.L1.body": true,
    "series.respect": 4,
    "series.chantErrors": 0,
    "series.vuthy.saved": false,
    "series.vuthy.forgiven": false,
    "series.mother.freed": false,
  };
  for (let i = 1; i <= 8; i++) flags[`lore.ep1.L${i}`] = true;
  for (let i = 1; i <= 8; i++) flags[`sb.SB-0${i}`] = true;
  return {
    saveVersion: 1,
    episode: 1,
    checkpoint: "CP6",
    clock: "05:40",
    flags,
    inventory: {
      letters: 1,
      oil_bottle: 1,
      matches: 7,
      sanctified_match: 1,
      key_fragment: 3,
    },
    lamp: { oil: 0.64, state: "open" },
    playTimeSec: 6120,
    savedAt: "2026-10-20T14:03:00.000Z",
  };
}
