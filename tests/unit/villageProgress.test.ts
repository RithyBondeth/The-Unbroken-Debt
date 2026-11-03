import { describe, expect, it } from "vitest";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import { VillageProgress, enterVillage } from "../../src/episodes/ep3/VillageProgress";
import { FUSE_IDS, LEAK_IDS, SAFE_CODE } from "../../src/episodes/ep3/data/village";
import { villageNotebook } from "../../src/episodes/ep3/data/notebook";
import { newGameSave, assertSave } from "../../src/systems/saves/SaveData";
import { encodeSaveCode, decodeSaveCode } from "../../src/systems/saves/saveCode";

function fresh() {
  return new VillageProgress(new Flags(), new Inventory());
}
function clinic(p: VillageProgress) {
  p.meet("vuthy");
  p.meet("lok");
  p.borrowBoat();
  p.dock();
}
function vault(p: VillageProgress) {
  clinic(p);
  for (const id of FUSE_IDS) p.collectFuse(id);
  for (const id of LEAK_IDS) p.seal(id);
  p.startPump();
}
function ritual(p: VillageProgress) {
  vault(p);
  SAFE_CODE.forEach((n, i) => {
    for (let k = 0; k < n; k++) p.turnDial(i);
  });
  p.openSafe();
  p.takeJar();
  p.scrapeName();
  p.writeName();
  p.pourWater();
  for (let i = 0; i < 3; i++) p.lightCandle(i);
}

describe("Episode 3 chapter and inherited decisions", () => {
  it("requires Episode 2 completion, clones its archive and retains both earlier episodes", async () => {
    const save = newGameSave();
    expect(() => enterVillage(save)).toThrow("Complete Episode 2");
    save.episode = 2;
    Object.assign(save.flags, {
      "ep2.complete": true,
      "ep1.journal.shared": false,
      "series.respect": 7,
      "series.night": 4,
      "ep2.memory.choice": 2,
      "game.run": "inherited",
      "checkpoint.spawn.x": 10,
    });
    save.inventory = {
      lamp: 1,
      sketchbook: 1,
      satchel: 1,
      silver_inlay: 1,
      blessed_thread: 1,
      clinic_photo: 1,
    };
    const original = structuredClone(save),
      next = enterVillage(save);
    assertSave(next);
    expect(save).toEqual(original);
    expect(next.episode).toBe(3);
    expect(next.clock).toBe("16:30");
    expect(next.flags["series.respect"]).toBe(7);
    expect(next.flags["ep1.journal.shared"]).toBe(false);
    expect(next.flags["checkpoint.spawn.x"]).toBeUndefined();
    expect(next.inventory.silver_inlay).toBe(1);
    expect(await decodeSaveCode(await encodeSaveCode(next))).toEqual(next);
  });
  it("cannot leave without both conversations or receive duplicate supplies", () => {
    const p = fresh();
    expect(p.borrowBoat()).toBe(false);
    p.meet("lok");
    expect(p.borrowBoat()).toBe(false);
    p.meet("vuthy");
    expect(p.borrowBoat()).toBe(true);
    expect(p.borrowBoat()).toBe(false);
    expect(p.inventory.count("yellow_candle")).toBe(4);
  });
  it("cannot drain an unsealed room or install fewer than three fuses", () => {
    const p = fresh();
    clinic(p);
    for (const id of FUSE_IDS) expect(p.collectFuse(id)).toBe(true);
    expect(p.collectFuse("ward")).toBe(false);
    expect(p.startPump()).toBe(false);
    p.seal("west");
    expect(p.startPump()).toBe(false);
    expect(p.inventory.count("brass_fuse")).toBe(3);
    p.seal("east");
    expect(p.startPump()).toBe(true);
    expect(p.inventory.count("brass_fuse")).toBe(0);
    expect(p.startPump()).toBe(false);
    expect(p.stage).toBe("vault");
  });
  it("preserves dial values across reload and rejects incorrect combinations without consumption", () => {
    const p = fresh();
    vault(p);
    expect(p.openSafe()).toBe(false);
    expect(p.takeJar()).toBe(false);
    expect(p.turnDial(-1)).toBe(-1);
    expect(p.turnDial(0.5)).toBe(-1);
    SAFE_CODE.forEach((n, i) => {
      for (let k = 0; k < n; k++) p.turnDial(i);
    });
    const flags = new Flags();
    flags.load(p.flags.toJSON());
    const restored = new VillageProgress(flags, p.inventory);
    expect(restored.dials).toEqual(SAFE_CODE);
    expect(restored.openSafe()).toBe(true);
    expect(restored.takeJar()).toBe(true);
    expect(restored.takeJar()).toBe(false);
    expect(restored.inventory.count("terracotta_jar")).toBe(1);
    expect(restored.writeName()).toBe(false);
    expect(restored.scrapeName()).toBe(true);
    expect(restored.writeName()).toBe(true);
  });
  it.each([true, false])(
    "finishes the %s mother choice once and retains its Episode 5 consequence",
    (free) => {
      const p = fresh();
      ritual(p);
      p.flags.set("series.respect", 3);
      expect(p.release(free)).toBe(true);
      expect(p.release(free)).toBe(false);
      expect(p.flags.get("series.respect", 0)).toBe(free ? 5 : 3);
      expect(p.flags.get("series.kanha.freed", !free)).toBe(free);
      expect(p.inventory.count("yellow_candle")).toBe(free ? 0 : 1);
      expect(p.inventory.count("shrine_soil")).toBe(1);
      expect(p.finish()).toBe(false);
      expect(p.escape()).toBe(true);
      expect(p.finish()).toBe(true);
      expect(p.finish()).toBe(false);
      expect(p.inventory.count("brass_compass")).toBe(1);
      expect(p.flags.get("series.nextEpisode", 0)).toBe(4);
      expect(p.flags.get("series.night", 0)).toBe(5);
    },
  );
  it("keeps the safe clue available outside the optional attic and hides unread lore", () => {
    const p = fresh();
    clinic(p);
    expect(p.read("letter")).toBe(false);
    p.read("admission");
    const n = villageNotebook(p, { x: 0, z: 7 }, "Landing");
    expect(n.loreFound).toBe(1);
    expect(n.entries.some((e) => e.text?.includes("១ · ៥ · ០ · ៧"))).toBe(true);
    expect(n.entries.some((e) => e.heading === "Unsent letter to Vuthy · 1931")).toBe(false);
  });
});
