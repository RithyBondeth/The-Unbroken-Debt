import { describe, expect, it } from "vitest";
import { EventBus } from "../../src/core/EventBus";
import type { GameEvents } from "../../src/core/events";
import { Inventory } from "../../src/systems/inventory/Inventory";

describe("Inventory", () => {
  it("counts items and emits a change for each one", () => {
    const bus = new EventBus<GameEvents>();
    const seen: string[] = [];
    bus.on("inventory:changed", ({ itemId, count }) => seen.push(`${itemId}=${count}`));
    const inv = new Inventory(bus);
    inv.add("matches", 10);
    inv.add("letters");
    expect(inv.remove("matches", 3)).toBe(true);
    expect(inv.count("matches")).toBe(7);
    expect(seen).toEqual(["matches=10", "letters=1", "matches=7"]);
  });

  it("refuses to take more than it holds", () => {
    const inv = new Inventory();
    inv.add("matches", 2);
    expect(inv.remove("matches", 3)).toBe(false);
    expect(inv.count("matches")).toBe(2);
  });

  it("round-trips through a save without empty entries", () => {
    const inv = new Inventory();
    inv.add("lamp");
    inv.add("letters");
    inv.remove("letters");
    expect(inv.toJSON()).toEqual({ lamp: 1 });
    const copy = new Inventory();
    copy.load({ lamp: 1, matches: 10, ghost: 0 });
    expect(copy.list()).toEqual([
      ["lamp", 1],
      ["matches", 10],
    ]);
  });
});
