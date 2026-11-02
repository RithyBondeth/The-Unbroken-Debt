import { expect, it } from "vitest";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import { notebookContent } from "../../src/ui/notebook/NotebookContent";
import { mapSvg } from "../../src/ui/notebook/NotebookMap";

const at = { x: -3, y: 0, z: -0.7 };
const model = (flags: Flags, inventory: Inventory, ids: string[] = []) =>
  notebookContent(flags, inventory, new Set(ids), at, "Studio checkpoint · 20:00");
it("keeps the objective live while retaining historical instructions as notes", () => {
  const flags = new Flags(),
    inventory = new Inventory();
  flags.load({ "ep1.checkpoint": "CP1", "ep1.act2.started": true });
  const content = model(flags, inventory, ["SB-02"]);
  expect(content.entries.find((e) => e.id === "live:objective")?.heading).toBe(
    "Investigate Sok’s room",
  );
  expect(content.entries.find((e) => e.id === "SB-02")?.section).toBe("notes");
  expect(
    content.entries.filter((e) => e.section === "now").every((e) => e.id.startsWith("live:")),
  ).toBe(true);
});
it("derives checklist progress after state changes and a checkpoint reload, without modifying saves", () => {
  const flags = new Flags(),
    inventory = new Inventory();
  flags.set("ep1.illustration.inked", true);
  inventory.add("sketchbook");
  const stored = { flags: flags.toJSON(), inventory: inventory.toJSON(), written: ["SB-01"] };
  const before = model(flags, inventory, stored.written);
  inventory.add("matches", 10);
  expect(
    model(flags, inventory, stored.written).entries.find((e) => e.id === "live:task:2")?.text,
  ).toMatch(/^✓/);
  flags.load(stored.flags);
  inventory.load(stored.inventory);
  expect(model(flags, inventory, stored.written)).toEqual(before);
  expect(stored.written).toEqual(["SB-01"]);
  expect(flags.toJSON()).toEqual(stored.flags);
});
it("shares discovered clue text, keeps lore separate, and hides undiscovered people", () => {
  const flags = new Flags(),
    inventory = new Inventory();
  const content = model(flags, inventory, ["SB-03b", "L4"]);
  expect(content.entries.find((e) => e.id === "SB-03b")?.text).toContain("back: candle");
  expect(content.entries.find((e) => e.id === "L4")?.section).toBe("lore");
  expect(content.loreFound).toBe(1);
  expect(content.entries.some((e) => e.heading === "Vuthy")).toBe(false);
  expect(content.entries.find((e) => e.id === "P-SORA")?.section).toBe("people");
  flags.set("ep1.arrival.callComplete", true);
  expect(model(flags, inventory).entries.some((e) => e.heading === "Vuthy")).toBe(true);
});
it("renders the same current-position map in the physical and readable views", () => {
  const flags = new Flags(),
    inventory = new Inventory();
  const studio = model(flags, inventory).map;
  expect(studio.shapes.find((s) => s.kind === "you")).toMatchObject({ x: -3, y: -0.7 });
  expect(mapSvg(studio)).toContain('cx="-3" cy="-0.7"');
  flags.set("ep1.checkpoint", "CP1");
  const village = notebookContent(flags, inventory, new Set(), { x: 0, y: 0, z: 35 }, "").map;
  expect(village.title).toContain("Approach");
  expect(village.shapes.find((s) => s.kind === "you")).toMatchObject({ x: 35, y: 0 });
  expect(mapSvg(village)).toContain('cx="35" cy="0"');
});

it("keeps the recorded night circles available to both presentations", () => {
  const content = model(new Flags(), new Inventory(), ["SB-08"]);
  expect(content.nights).toEqual(["pencil", "pencil", "ink", "empty", "empty", "empty", "empty"]);
});

it("keeps the village plan and player in the same landscape coordinate system", () => {
  const flags = new Flags();
  flags.set("ep1.checkpoint", "CP1");
  const map = notebookContent(flags, new Inventory(), new Set(), { x: 4, y: 3, z: -16 }, "").map;
  expect(map.bounds[2]).toBeGreaterThan(map.bounds[3]);
  expect(map.shapes.find((s) => s.kind === "you")).toMatchObject({ x: 16, y: 4 });
  expect(map.shapes.find((s) => s.kind === "rect" && s.walls)).toMatchObject({
    x: 11,
    y: -6,
    w: 12,
    h: 12,
  });
  expect(mapSvg(map)).toContain('cx="16" cy="4"');
});
