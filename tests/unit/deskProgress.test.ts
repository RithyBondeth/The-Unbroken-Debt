import { describe, expect, it } from "vitest";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import { DeskProgress, PORTRAIT_TIMEOUT } from "../../src/episodes/ep1/act2/DeskProgress";

function setup() {
  const flags = new Flags(),
    inventory = new Inventory();
  return { flags, inventory, progress: new DeskProgress(flags, inventory) };
}
function investigate() {
  const state = setup();
  state.flags.set("ep1.walker.complete", true);
  state.progress.openCompartment();
  state.progress.takeKey();
  state.progress.unlockDesk();
  state.progress.readJournal();
  return state;
}

describe("Sok's desk and Act III handover", () => {
  it("gates investigation on surviving the walker and consumes the key exactly once", () => {
    const { flags, inventory, progress: p } = setup();
    expect(p.openCompartment()).toBe(false);
    expect(p.takeKey()).toBe(false);
    expect(p.unlockDesk()).toBe(false);
    flags.set("ep1.walker.complete", true);
    expect(p.unlockDesk()).toBe(false);
    expect(p.readJournal()).toBe(false);
    expect(p.openCompartment()).toBe(true);
    expect(p.openCompartment()).toBe(false);
    expect(p.takeKey()).toBe(true);
    expect(p.takeKey()).toBe(false);
    expect(inventory.count("drawer_key")).toBe(1);
    expect(p.unlockDesk()).toBe(true);
    expect(inventory.has("drawer_key")).toBe(false);
    expect(p.unlockDesk()).toBe(false);
    expect(p.readJournal()).toBe(true);
    expect(p.readJournal()).toBe(false);
    expect(inventory.count("sok_journal_b")).toBe(1);
  });

  it("restores intermediate key / drawer progress without duplicating items", () => {
    const { flags, inventory, progress: p } = setup();
    flags.set("ep1.walker.complete", true);
    p.openCompartment();
    p.takeKey();
    const restored = setup();
    restored.flags.load(flags.toJSON());
    restored.inventory.load(inventory.toJSON());
    expect(restored.progress.compartmentOpen).toBe(true);
    expect(restored.progress.takeKey()).toBe(false);
    expect(restored.inventory.count("drawer_key")).toBe(1);
    expect(restored.progress.unlockDesk()).toBe(true);
    expect(restored.progress.readJournal()).toBe(true);
  });

  it("waits for the journal and the return to the tent before authored ash", () => {
    const { progress: p, flags } = investigate();
    expect(p.update(10, false, true, true)).toBeNull();
    expect(p.update(10, true, false, true)).toBeNull();
    expect(p.update(0, true, true, true)).toBe("portrait");
    expect(flags.get("ep1.incense.scripted", false)).toBe(true);
    expect(flags.get("ep1.thread.broken", false)).toBe(false);
    expect(p.update(2, true, true, true)).toBeNull();
    expect(p.update(1, true, true, false)).toBeNull();
    expect(p.update(0.1, true, true, true)).toBe("snap");
    expect(flags.get("ep1.checkpoint", "")).toBe("CP4");
    expect(flags.get("ep1.clock", "")).toBe("02:00");
    expect(flags.get("ep1.thread.broken", false)).toBe(true);
    expect(flags.get("ep1.act2.complete", false)).toBe(true);
    expect(p.update(1000, true, true, true)).toBeNull();
  });

  it("persists the timeout, pauses for menus, and waits for a safe CP4 position", () => {
    const { flags, inventory, progress: p } = investigate();
    p.update(0, true, true, true);
    p.update(60, false, true, false);
    p.update(500, true, false, false);
    expect(flags.get("ep1.portrait.seconds", 0)).toBe(60);
    const restored = setup();
    restored.flags.load(flags.toJSON());
    restored.inventory.load(inventory.toJSON());
    expect(restored.progress.update(PORTRAIT_TIMEOUT - 60, false, true, false)).toBeNull();
    expect(restored.progress.actThree).toBe(false);
    expect(restored.progress.update(0, true, true, false)).toBe("snap");
    const after = new DeskProgress(restored.flags, restored.inventory);
    expect(after.update(200, true, true, true)).toBeNull();
    expect(restored.inventory.count("sok_journal_b")).toBe(1);
  });
});
