import { expect, it } from "vitest";
import { currentObjective, notebookClues } from "../../src/episodes/ep1/data/notebook";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import { EventBus } from "../../src/core/EventBus";
import type { GameEvents } from "../../src/core/events";
const setup = () => ({ flags: new Flags(), items: new Inventory(new EventBus<GameEvents>()) });
it("names the actual missing studio item and clears it only when it is collected", () => {
  const { flags, items } = setup();
  flags.set("ep1.illustration.inked", true);
  for (const id of ["satchel", "sketchbook", "lamp"]) items.add(id);
  const o = currentObjective(flags, items);
  expect(o.tasks.find((t) => t.text.includes("Matchbox"))?.done).toBe(false);
  items.add("matches", 10);
  expect(currentObjective(flags, items).title).toBe("Answer the telephone");
  flags.set("ep1.phone.answered", true);
  expect(currentObjective(flags, items).title).toBe("Leave for home");
});
it("does not confuse placed tray with collected ingredients and transcribes the discovered arrangement", () => {
  const { flags, items } = setup();
  flags.load({
    "ep1.checkpoint": "CP1",
    "ep1.vigil.started": true,
    "ep1.betel.trayPlaced": true,
    "ep1.betel.drawingSeen": true,
  });
  const o = currentObjective(flags, items);
  expect(o.tasks[0].done).toBe(true);
  expect(o.tasks.slice(1).every((t) => !t.done)).toBe(true);
  expect(o.detail).toContain("lime in the centre");
  const notes = notebookClues(new Set(["SB-03b"]));
  expect(notes[0].text).toContain("back: candle");
});
it("shows the stealth task only for a new opening until the courtyard is reached", () => {
  const { flags, items } = setup();
  flags.load({ "ep1.checkpoint": "CP1", "ep1.early.required": true });
  expect(currentObjective(flags, items).title).toBe("Reach the funeral courtyard");
  flags.set("ep1.early.complete", true);
  expect(currentObjective(flags, items).title).toBe("Find Mak Yey’s instructions");
});
