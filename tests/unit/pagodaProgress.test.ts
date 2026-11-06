import { describe, expect, it } from "vitest";
import { Flags } from "@/core/Flags";
import { Inventory } from "@/systems/inventory/Inventory";
import { assertSave, newGameSave } from "@/systems/saves/SaveData";
import { decodeSaveCode, encodeSaveCode } from "@/systems/saves/saveCode";
import { enterPagoda, PagodaProgress } from "@/episodes/ep2/PagodaProgress";
import { ANCESTORS, MIRROR_TARGETS } from "@/episodes/ep2/data/pagoda";
import { pagodaNotebook } from "@/episodes/ep2/data/notebook";

function state() {
  return new PagodaProgress(new Flags(), new Inventory());
}
function garden(p: PagodaProgress) {
  p.meetMonk();
  for (const item of ["rice", "lotus", "water"] as const) p.collect(item);
  for (const a of ANCESTORS) p.offer(a.id, a.item);
}
function archive(p: PagodaProgress) {
  garden(p);
  p.openBridge();
  MIRROR_TARGETS.forEach((n, i) => {
    for (let k = 0; k < n; k++) p.rotateMirror(i);
  });
  p.openArchive();
}

describe("Episode 2 state and series continuity", () => {
  it("requires a completed Episode 1 and retains its decisions, lore and remnant", async () => {
    const old = newGameSave();
    expect(() => enterPagoda(old)).toThrow("Complete Episode 1");
    Object.assign(old, {
      checkpoint: "CP6",
      inventory: { satchel: 1, sketchbook: 1, lamp: 1, matches: 2, seal_map: 1, sok_journal: 1 },
    });
    Object.assign(old.flags, {
      "ep1.complete": true,
      "ep1.journal.shared": false,
      "lore.ep1.L2": true,
      "series.respect": 2,
      "series.night": 3,
      "game.run": "same-run",
      "checkpoint.spawn.x": 5,
    });
    const before = structuredClone(old),
      next = enterPagoda(old);
    expect(old).toEqual(before);
    assertSave(next);
    expect(next).toMatchObject({
      episode: 2,
      checkpoint: "CP0",
      clock: "23:45",
      inventory: { matches: 10, oil: 2, seal_map: 1, sok_journal: 1 },
    });
    expect(next.flags).toMatchObject({
      "ep1.journal.shared": false,
      "lore.ep1.L2": true,
      "series.respect": 2,
      "game.run": "same-run",
    });
    expect(next.flags["checkpoint.spawn.x"]).toBeUndefined();
    expect(await decodeSaveCode(await encodeSaveCode(next))).toEqual(next);
  });
  it("never consumes an incorrect offering or duplicates a reward on reload", () => {
    const p = state();
    expect(p.collect("rice")).toBe(false);
    p.meetMonk();
    p.meetMonk();
    expect(p.inventory.count("blessed_thread")).toBe(1);
    expect(p.inventory.count("clay_bowl")).toBe(4);
    p.collect("rice");
    p.collect("lotus");
    expect(p.collect("rice")).toBe(false);
    expect(p.offer("chea", "lotus")).toBe("wrong");
    expect(p.inventory.count("lotus")).toBe(1);
    expect(p.offer("chhun", "water")).toBe("missing");
    expect(p.openBridge()).toBe(false);
    expect(p.offer("chea", "rice")).toBe("placed");
    expect(p.offer("chea", "rice")).toBe("done");
    expect(p.inventory.count("rice")).toBe(1);
    expect(p.pretCount).toBe(3);
    const restored = new PagodaProgress(new Flags(), new Inventory());
    restored.flags.load(p.flags.toJSON());
    restored.inventory.load(p.inventory.toJSON());
    expect(restored.offered("chea")).toBe(true);
    expect(restored.offer("chea", "rice")).toBe("done");
  });
  it("guards the optional hall and cabinet and recovers after wrong bell sequences", () => {
    const p = state();
    expect(p.read("hall_0")).toBe(false);
    expect(p.read("library_0")).toBe(false);
    expect(p.openArchive()).toBe(false);
    expect(p.rotateMirror(0)).toBe(-1);
    p.meetMonk();
    for (const bell of [2, 0, 0, 2, 0, 1]) p.ring(bell);
    expect(p.flags.get("ep2.hall.open", false)).toBe(true);
    expect(p.read("hall_0")).toBe(true);
    expect(p.openArchive()).toBe(false);
  });
  it("completes all acts, persists the truthful choice once, and carries the second seal forward", () => {
    const p = state();
    p.flags.set("series.respect", 2);
    archive(p);
    expect(p.stage).toBe("memory");
    expect(p.inventory.count("silver_betel_box")).toBe(1);
    expect(p.openArchive()).toBe(false);
    expect(p.remember(2)).toBe(true);
    expect(p.remember(2)).toBe(false);
    expect(p.flags.get("series.respect", 0)).toBe(3);
    expect(p.escape()).toBe(true);
    expect(p.finish(ANCESTORS.map((a) => a.id))).toBe(true);
    expect(p.stage).toBe("complete");
    expect(p.flags.get("series.respect", 0)).toBe(5);
    expect(p.inventory.has("silver_betel_box")).toBe(false);
    expect(p.inventory.has("silver_inlay")).toBe(true);
    expect(p.inventory.has("clinic_photo")).toBe(true);
    expect(p.flags.get("series.nextEpisode", 0)).toBe(3);
    expect(p.flags.get("series.night", 0)).toBe(4);
    expect(p.finish(ANCESTORS.map((a) => a.id))).toBe(false);
    expect(p.flags.get("series.respect", 0)).toBe(5);
  });
  it("allows recovery from a wrong dawn order without awarding the first-try point", () => {
    const p = state();
    archive(p);
    p.remember(0);
    p.escape();
    expect(p.finish(["kanha", "wife", "chhun", "chea"])).toBe(false);
    expect(p.stage).toBe("dawn");
    expect(p.inventory.has("silver_betel_box")).toBe(true);
    expect(p.finish(ANCESTORS.map((a) => a.id))).toBe(true);
    expect(p.flags.get("series.respect", 0)).toBe(1);
  });
  it("writes the actual episode objectives, clues, lore and physical map", () => {
    const p = state();
    garden(p);
    p.read("monk");
    const n = pagodaNotebook(p, { x: -18, z: 15 }, "Kuti");
    expect(n.entries.some((e) => e.text?.includes("Four family stupas"))).toBe(true);
    expect(n.map.title).toBe("The Whispering Pagoda");
    expect(n.loreFound).toBe(1);
    expect(n.entries.some((e) => e.heading === "Sophal’s letter · 1912")).toBe(true);
    expect(n.map.shapes.filter((s) => s.kind === "you")).toEqual([
      { kind: "you", x: -18, y: 15, r: 1.2 },
    ]);
  });
});
