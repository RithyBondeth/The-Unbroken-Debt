import type { Flags } from "../../../core/Flags";
import type { Inventory } from "../../../systems/inventory/Inventory";
import { EP1_SKETCHBOOK } from "./sketchbook";
import { SLOTS, KANHA_LAYOUT } from "./betel";
import { ITEMS } from "./items";

export interface Objective {
  title: string;
  detail: string;
  tasks: { text: string; done: boolean }[];
}
/** Derived from durable gameplay state; a checkpoint reload cannot retain a stale task. */
export function currentObjective(f: Flags, items: Inventory): Objective {
  const yes = (key: string) => f.get(key, false);
  const objective = (title: string, detail: string, tasks: Objective["tasks"] = []) => ({
    title,
    detail,
    tasks,
  });
  if (yes("ep1.complete"))
    return objective(
      "The first seal is broken",
      "Episode 1 is complete. Your journal choice and discoveries are saved for Episode 2.",
    );
  if (yes("ep1.travel.pending"))
    return objective(
      "Return to the village",
      "Stay in the taxi. Listen to the driver and watch the flooded road.",
    );
  if (f.get("ep1.checkpoint", "CP0") === "CP0") {
    if (!yes("ep1.illustration.inked"))
      return objective(
        "Finish the illustration",
        "Look down at the drawing on the sloping table by the window. Press E to ink the line.",
      );
    const tasks = [
      { text: "Satchel — shelf beside the candle", done: items.has("satchel") },
      { text: "Sketchbook — writing-desk top", done: items.has("sketchbook") },
      { text: "Matchbox — pull open the writing-desk drawer", done: items.has("matches") },
      { text: "Hurricane lamp — hook beside the door", done: items.has("lamp") },
    ];
    if (tasks.some((t) => !t.done))
      return objective(
        "Pack for the journey",
        "Collect all four items. The matchbox and tied letters are separate pickups.",
        tasks,
      );
    if (!yes("ep1.phone.answered"))
      return objective(
        "Answer the telephone",
        "The wall telephone is beside the door. Put away the notebook with Q, look at the phone and press E.",
        tasks,
      );
    return objective(
      "Leave for home",
      "The call has ended. Your progress is saved. Use the studio door to take the taxi.",
      tasks,
    );
  }
  if (yes("ep1.early.required") && !yes("ep1.early.complete"))
    return objective(
      "Reach the funeral courtyard",
      "A figure patrols the path. Crouch with C, stay behind solid cover and put out the lamp with F if it sees the light. Wait for its footsteps to move away.",
    );
  if (yes("ep1.seal1.broken"))
    return objective(
      "Wait for dawn",
      "Return to the pavilion. Vuthy promised to meet you at dawn.",
    );
  if (items.has("bronze_token") || yes("ep1.ritual.tokenPlaced"))
    return objective(
      "Break the first seal",
      "Bring the bronze token to the main burner by the coffin. Use a blessed match, hold your gaze steady and do not turn around.",
    );
  if (items.has("brass_key"))
    return objective(
      "Open Sok’s hidden chest",
      "Return upstairs to Sok’s room. Lift the loose floor planks and use the assembled brass key.",
    );
  if (yes("ep1.thread.broken") || yes("ep1.hunt.started")) {
    const pieces = ["brass_key_bow", "brass_key_shaft", "brass_key_bit"].filter((id) =>
      items.has(id),
    ).length;
    return objective(
      pieces === 3 ? "Assemble the chest key" : "Search the water jars",
      pieces === 3
        ? "Move to safety, open the satchel with Tab and assemble the three brass pieces."
        : "Search beneath the house. Use posts and stored objects as cover. The wandering presence notices your light.",
      [{ text: `Key pieces found: ${pieces} / 3`, done: pieces === 3 }],
    );
  }
  if (yes("ep1.walker.complete"))
    return objective(
      "Investigate Sok’s desk",
      "Find the small key compartment at the base of the upstairs hall altar, then unlock Sok’s desk and read the journal.",
    );
  if (yes("ep1.gramophone.heard"))
    return objective(
      "Survive the hallway presence",
      "Approach the hall carefully. Enter a wardrobe with E, put the lamp out with F, and stay quiet until its footsteps pass.",
    );
  if (yes("ep1.act2.started"))
    return objective(
      "Investigate Sok’s room",
      "The upstairs door has opened. Check the loose wall board beside the desk, read the papers, then tune the gramophone.",
    );
  if (!yes("ep1.arrival.callComplete") && !yes("ep1.vigil.started"))
    return objective(
      "Find Mak Yey’s instructions",
      yes("ep1.arrival.noteRead")
        ? "The note directs you to the ringing telephone in the upstairs hall."
        : "Read the note on the small table beside the funeral pavilion. The family has left for the night.",
    );
  if (!yes("ep1.arrival.matchesTaken") && yes("ep1.arrival.phoneFlow"))
    return objective(
      "Collect the blessed matches",
      "The box tied with red thread waits on the upstairs ancestral altar. These are separate from your ordinary matchbox.",
    );
  if (!yes("ep1.betel.done"))
    return objective(
      "Prepare the offering",
      yes("ep1.betel.drawingSeen")
        ? "Mother’s arrangement: candle at the back, betel leaves left, lime in the centre, areca nuts right and incense at the front. Use each tray position to choose an ingredient."
        : "Collect the tray and ingredients. Inspect Kanha’s drawing beside the altar to learn the arrangement.",
      ["betel_tray", "betel", "areca", "lime", "candle", "incense"].map((id) => ({
        text: ITEMS[id].name,
        done:
          items.has(id) ||
          (id === "betel_tray"
            ? yes("ep1.betel.trayPlaced")
            : SLOTS.some((s) => f.get(`ep1.betel.slot.${s}`, "") === id)),
      })),
    );
  return objective(
    "Keep the vigil",
    "Keep your lamp burning, replace spent incense and inspect the protective thread. Return beneath the pavilion after the vigil cycle.",
  );
}

export function notebookClues(written: ReadonlySet<string>) {
  return EP1_SKETCHBOOK.entries
    .filter((entry) => written.has(entry.id) && entry.text && entry.section !== "people")
    .map((entry) => ({
      id: entry.id,
      title: entry.section === "lore" ? "Found document" : "Sora’s notes",
      text:
        entry.id === "SB-03b"
          ? `Mother’s offering arrangement: ${SLOTS.map((s) => `${s}: ${ITEMS[KANHA_LAYOUT[s]].name.toLowerCase()}`).join("; ")}.`
          : entry.text!,
    }));
}
