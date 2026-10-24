import { describe, expect, it } from "vitest";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import { ChestProgress, CHEST_ITEMS } from "../../src/episodes/ep1/act3/ChestProgress";
import {
  RitualProgress,
  RITUAL_SECONDS,
  RITUAL_TURN_LIMIT,
} from "../../src/episodes/ep1/act3/RitualProgress";
import { newGameSave } from "../../src/systems/saves/SaveData";
import { encodeSaveCode, decodeSaveCode } from "../../src/systems/saves/saveCode";
function setup() {
  const flags = new Flags(),
    inventory = new Inventory();
  const chest = new ChestProgress(flags, inventory);
  const ritual = new RitualProgress(flags, inventory);
  const discover = () => {
    flags.set("ep1.act3.started", true);
    inventory.add("brass_key");
    inventory.add("blessed_matches", 3);
    chest.liftPlanks();
    chest.unlock();
    for (const item of CHEST_ITEMS) chest.take(item);
  };
  return { flags, inventory, ritual, discover };
}
describe("chest through CP6 and first seal", () => {
  it("requires all chest discoveries, places once and preserves the unread slip", () => {
    const { ritual: p, inventory, flags, discover } = setup();
    inventory.add("bronze_token");
    expect(p.place()).toBe(false);
    expect(p.start()).toBe(false);
    expect(p.spare()).toBe(false);
    discover();
    expect(p.place()).toBe(true);
    expect(p.place()).toBe(false);
    expect(flags.get("ep1.checkpoint", "")).toBe("CP6");
    expect(flags.get("ep1.clock", "")).toBe("02:50");
    expect(flags.get("ep1.slip.unread", false)).toBe(true);
  });
  it("fails beyond 100 degrees before awarding success, consumes one match per attempt and retries", () => {
    const { ritual: p, inventory, discover } = setup();
    discover();
    p.place();
    expect(p.start()).toBe(true);
    expect(p.start()).toBe(false);
    expect(inventory.count("blessed_matches")).toBe(2);
    expect(p.update(24, 0)).toBe(null);
    expect(p.update(1, RITUAL_TURN_LIMIT + 0.01)).toBe("failed");
    expect(p.broken).toBe(false);
    expect(inventory.has("bronze_token")).toBe(true);
    expect(p.start()).toBe(true);
    expect(p.update(25, RITUAL_TURN_LIMIT)).toBe("broken");
    expect(inventory.count("blessed_matches")).toBe(1);
    expect(inventory.has("bronze_token")).toBe(false);
    expect(p.start()).toBe(false);
    expect(p.update(25, 0)).toBe(null);
  });
  it("offers one spare only when empty, including repeated exhaustion", () => {
    const { ritual: p, inventory, discover } = setup();
    discover();
    p.place();
    expect(p.spare()).toBe(false);
    for (let i = 0; i < 3; i++) {
      p.start();
      p.update(0.1, Math.PI);
    }
    expect(inventory.count("blessed_matches")).toBe(0);
    expect(p.start()).toBe(false);
    expect(p.spare()).toBe(true);
    expect(p.spare()).toBe(false);
    p.start();
    expect(p.spare()).toBe(false);
    p.update(0.1, -Math.PI);
    expect(p.spare()).toBe(true);
    p.start();
    p.update(25, 0);
    expect(p.spare()).toBe(false);
  });
  it("pauses without progress or failure and rejects negative elapsed time", () => {
    const { ritual: p, discover } = setup();
    discover();
    p.place();
    p.start();
    p.update(30, Math.PI, true);
    expect(p.elapsed).toBe(0);
    p.update(-10, 0);
    expect(p.elapsed).toBe(0);
    expect(p.update(RITUAL_SECONDS - 0.1, 0)).toBe(null);
    expect(p.update(0.1, 0)).toBe("broken");
  });
  it("round-trips an interrupted CP6 with spent matches and zero hold progress, then saves success", async () => {
    const { ritual: p, flags, inventory, discover } = setup();
    discover();
    p.place();
    p.start();
    p.update(12, 0);
    const save = {
      ...newGameSave(),
      checkpoint: "CP6",
      clock: "02:50",
      flags: flags.toJSON(),
      inventory: inventory.toJSON(),
    };
    const restored = await decodeSaveCode(await encodeSaveCode(save));
    const nextFlags = new Flags(),
      nextInventory = new Inventory();
    nextFlags.load(restored.flags);
    nextInventory.load(restored.inventory);
    const next = new RitualProgress(nextFlags, nextInventory);
    expect(next.placed).toBe(true);
    expect(next.active).toBe(false);
    expect(next.elapsed).toBe(0);
    expect(nextInventory.count("blessed_matches")).toBe(2);
    expect(nextInventory.has("bronze_token")).toBe(true);
    next.start();
    expect(next.update(25, 0)).toBe("broken");
    const final = await decodeSaveCode(
      await encodeSaveCode({
        ...restored,
        flags: nextFlags.toJSON(),
        inventory: nextInventory.toJSON(),
        clock: "03:00",
      }),
    );
    nextFlags.load(final.flags);
    nextInventory.load(final.inventory);
    const finished = new RitualProgress(nextFlags, nextInventory);
    expect(finished.broken).toBe(true);
    expect(finished.start()).toBe(false);
    expect(final.inventory.bronze_token).toBeUndefined();
    expect(final.flags["ep1.slip.unread"]).toBe(true);
  });
});
