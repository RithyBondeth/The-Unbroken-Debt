import { expect, it } from "vitest";
import { currentObjective, notebookClues } from "@/episodes/ep1/data/notebook";
import { Flags } from "@/core/Flags";
import { Inventory } from "@/systems/inventory/Inventory";
import { EventBus } from "@/core/EventBus";
import type { GameEvents } from "@/core/events";
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
it("tracks the new village puzzle chain from sealed gate through well, wards, and stopped clock", () => {
  const { flags, items } = setup();
  flags.load({ "ep1.checkpoint": "CP1", "ep1.village.puzzlesActive": true });
  expect(currentObjective(flags, items).title).toBe("Open the sealed farm gate");
  flags.set("ep1.puzzle.gate.open", true);
  expect(currentObjective(flags, items).title).toBe("Find Mak Yey’s instructions");
  flags.set("ep1.vigil.started", true);
  flags.set("ep1.betel.done", true);
  expect(currentObjective(flags, items).title).toBe("Haul the brick village well");
  flags.set("ep1.puzzle.well.complete", true);
  expect(currentObjective(flags, items).title).toBe("Restore the three compound wards");
  flags.set("ep1.puzzle.ward.neakta", true);
  flags.set("ep1.puzzle.ward.stupas", true);
  flags.set("ep1.puzzle.ward.ruin", true);
  expect(currentObjective(flags, items).title).toBe("Set the stopped hall clock");
  flags.set("ep1.puzzle.clock.solved", true);
  expect(currentObjective(flags, items).title).toBe("Keep the vigil");
});
