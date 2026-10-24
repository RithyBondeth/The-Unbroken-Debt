import { describe, it, expect } from "vitest";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import { ChestProgress, CHEST_ITEMS } from "../../src/episodes/ep1/act3/ChestProgress";
import { CorpseProgress } from "../../src/episodes/ep1/act3/CorpseProgress";
function setup() {
  const flags = new Flags(),
    inventory = new Inventory();
  return {
    flags,
    inventory,
    p: new ChestProgress(flags, inventory),
    corpse: new CorpseProgress(flags),
  };
}
describe("hidden chest and ritual preparation", () => {
  it("requires Act III, lifted planks and the assembled key; consumes it only once", () => {
    const { flags, inventory, p } = setup();
    inventory.add("brass_key");
    expect(p.liftPlanks()).toBe(false);
    expect(p.unlock()).toBe(false);
    flags.set("ep1.act3.started", true);
    expect(p.unlock()).toBe(false);
    expect(p.liftPlanks()).toBe(true);
    expect(p.liftPlanks()).toBe(false);
    inventory.remove("brass_key");
    expect(p.unlock()).toBe(false);
    inventory.add("brass_key");
    expect(p.unlock()).toBe(true);
    expect(p.unlock()).toBe(false);
    expect(inventory.has("brass_key")).toBe(false);
  });
  it("collects each object independently, never reads the slip, and prepares only with all three", () => {
    const { flags, inventory, p } = setup();
    flags.set("ep1.act3.started", true);
    expect(p.take("bronze_token")).toBe(false);
    p.liftPlanks();
    inventory.add("brass_key");
    p.unlock();
    expect(p.take("unknown")).toBe(false);
    expect(p.take("folded_slip")).toBe(true);
    expect(p.take("folded_slip")).toBe(false);
    expect(flags.get("ep1.slip.unread", false)).toBe(true);
    expect(flags.has("ep1.slip.read")).toBe(false);
    expect(p.ready).toBe(false);
    p.take("seal_map");
    expect(p.ready).toBe(false);
    p.take("bronze_token");
    expect(p.ready).toBe(true);
    expect(flags.get("ep1.clock", "")).toBe("02:45");
    for (const id of CHEST_ITEMS) expect(inventory.count(id)).toBe(1);
    expect(flags.has("ep1.seal1.broken")).toBe(false);
    expect(flags.has("ep1.checkpoint")).toBe(false);
  });
  it("restores partial searches without duplicating contents or requiring another key", () => {
    const first = setup();
    first.flags.set("ep1.act3.started", true);
    first.p.liftPlanks();
    first.inventory.add("brass_key");
    first.p.unlock();
    first.p.take("bronze_token");
    const next = setup();
    next.flags.load(first.flags.toJSON());
    next.inventory.load(first.inventory.toJSON());
    expect(next.p.planksOpen && next.p.unlocked).toBe(true);
    expect(next.p.unlock()).toBe(false);
    expect(next.p.take("bronze_token")).toBe(false);
    expect(next.inventory.count("bronze_token")).toBe(1);
    expect(next.p.take("seal_map")).toBe(true);
    expect(next.p.take("folded_slip")).toBe(true);
    expect(next.p.ready).toBe(true);
    const last = setup();
    last.flags.load(next.flags.toJSON());
    last.inventory.load(next.inventory.toJSON());
    for (const id of CHEST_ITEMS) expect(last.p.take(id)).toBe(false);
    expect(last.p.ready).toBe(true);
    expect(last.inventory.has("brass_key")).toBe(false);
  });
});
describe("Sok moves only when unobserved", () => {
  it("does not move before Act III or while watched; resets the four-second wait on a glance", () => {
    const { flags, corpse: c } = setup();
    c.update(20, true, false);
    expect(c.update(20, false, false)).toBe(false);
    flags.set("ep1.act3.started", true);
    c.update(20, true, false);
    expect(c.pose).toBe(0);
    expect(c.update(3.9, false, false)).toBe(false);
    c.update(0.01, true, false);
    expect(c.update(3.9, false, false)).toBe(false);
    expect(c.update(0.1, false, false)).toBe(true);
    expect(c.pose).toBe(1);
  });
  it("pauses during menus, restores a partial wait, and never skips unseen poses", () => {
    const first = setup();
    first.flags.set("ep1.act3.started", true);
    first.corpse.update(0.1, true, false);
    first.corpse.update(2, false, false);
    first.corpse.update(100, false, true);
    const next = setup();
    next.flags.load(first.flags.toJSON());
    expect(next.corpse.update(1.99, false, false)).toBe(false);
    expect(next.corpse.update(0.01, false, false)).toBe(true);
    expect(next.corpse.update(1000, false, false)).toBe(false);
    expect(next.corpse.pose).toBe(1);
    for (let pose = 2; pose <= 4; pose++) {
      next.corpse.update(0.1, true, false);
      expect(next.corpse.update(4, false, false)).toBe(true);
      expect(next.corpse.pose).toBe(pose);
    }
    next.corpse.update(0.1, true, false);
    expect(next.corpse.update(100, false, false)).toBe(false);
    expect(next.corpse.pose).toBe(4);
  });
  it("stops after the seal is broken", () => {
    const { flags, corpse: c } = setup();
    flags.set("ep1.act3.started", true);
    c.update(0.1, true, false);
    flags.set("ep1.seal1.broken", true);
    expect(c.update(20, false, false)).toBe(false);
    expect(c.pose).toBe(0);
  });
});
