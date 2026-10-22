import { describe, expect, it } from "vitest";
import {
  checkTray,
  KANHA_LAYOUT,
  nextOffering,
  OFFERINGS,
  SLOTS,
  type Offering,
  type Tray,
} from "../../src/episodes/ep1/data/betel";
import { ITEMS } from "../../src/episodes/ep1/data/items";
import { EP1_SKETCHBOOK } from "../../src/episodes/ep1/data/sketchbook";
import strings from "../../src/data/strings/en.json";

const all = () => true;

describe("betel offering", () => {
  it("takes each offering once, in Kanha's five places", () => {
    expect(new Set(Object.values(KANHA_LAYOUT)).size).toBe(OFFERINGS.length);
    expect(Object.keys(KANHA_LAYOUT).sort()).toEqual([...SLOTS].sort());
  });

  it("judges only a full tray, and names the places that are wrong", () => {
    expect(checkTray({})).toEqual({ complete: false, wrong: [] });
    expect(checkTray({ ...KANHA_LAYOUT })).toEqual({ complete: true, wrong: [] });
    const swapped: Tray = { ...KANHA_LAYOUT, left: "areca", right: "betel" };
    expect(checkTray(swapped)).toEqual({ complete: true, wrong: ["left", "right"] });
    expect(checkTray({ back: "lime" }).wrong).toEqual(["back"]);
  });

  it("cycles a place through what Sora has, then clears it", () => {
    const tray: Tray = {};
    const seen: (Offering | null)[] = [];
    for (let i = 0; i <= OFFERINGS.length; i++) {
      const next = nextOffering(tray, "centre", all);
      seen.push(next);
      if (next) tray.centre = next;
      else delete tray.centre;
    }
    expect(seen).toEqual([...OFFERINGS, null]);
  });

  it("never offers what is on another place or not in the satchel", () => {
    const tray: Tray = { back: "betel" };
    const held = (o: Offering) => o !== "areca";
    expect(nextOffering(tray, "left", held)).toBe("lime");
    expect(nextOffering({}, "left", () => false)).toBeNull();
  });

  it("has an item, a note and a pickup line for every offering", () => {
    for (const o of OFFERINGS) {
      expect(ITEMS[o]).toBeDefined();
      expect(strings).toHaveProperty(`note.${o}`);
    }
    expect(ITEMS.blessed_matches).toBeDefined();
    expect(EP1_SKETCHBOOK.entries.some((e) => e.id === "SB-03b")).toBe(true);
  });
});
