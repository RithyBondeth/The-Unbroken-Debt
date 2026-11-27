import { describe, expect, it } from "vitest";
import { Flags } from "@/core/Flags";
import {
  CLOCK_CURSED_TIMES,
  CLOCK_TARGET,
  GATE_CODE,
  WARD_STATIONS,
  WellMechanism,
  checkClockDial,
  checkGateCode,
  checkWardStation,
  solvedWardCount,
} from "@/episodes/ep1/data/villagePuzzles";

describe("Village Puzzle 1 — Sealed Compound Gate Padlock", () => {
  it("accepts the deduced 7-4-2 code and counts partial matches accurately", () => {
    expect(checkGateCode(GATE_CODE)).toEqual({ solved: true, matchedCount: 3 });
    expect(checkGateCode([7, 4, 9])).toEqual({ solved: false, matchedCount: 2 });
    expect(checkGateCode([7, 0, 0])).toEqual({ solved: false, matchedCount: 1 });
    expect(checkGateCode([0, 0, 0])).toEqual({ solved: false, matchedCount: 0 });
  });
});

describe("Village Puzzle 2 — Brick Well 4-Stage Risk Haul", () => {
  it("requires both counterweight stone and grapple hook before hauling", () => {
    const well = new WellMechanism();
    expect(well.pull(false)).toBe("not_ready");
    expect(well.attachParts(false, false)).toBe("need_both");
    expect(well.attachParts(true, false)).toBe("need_hook");
    expect(well.pull(false)).toBe("not_ready");
    expect(well.attachParts(false, true)).toBe("rigged");
    expect(well.phase).toBe("rigged");
  });

  it("yanks the rope back when pulling during the mid-shaft tug or shining an open lamp at the rim", () => {
    const well = new WellMechanism();
    well.attachParts(true, true);
    expect(well.pull(false)).toBe("rising");
    expect(well.pull(false)).toBe("tug_started");
    expect(well.phase).toBe("tug_danger");
    // Pulling while held yanks the bucket back down
    expect(well.pull(false)).toBe("yanked_back");
    expect(well.tugFailures).toBe(1);
    expect(well.phase).toBe("rigged");

    // Second attempt: wait still with lamp out until released
    expect(well.pull(false)).toBe("rising");
    expect(well.pull(false)).toBe("tug_started");
    // Moving fast or keeping lamp open prevents release
    expect(well.update(3, true, false)).toBe("none");
    expect(well.update(3, false, true)).toBe("none");
    expect(well.phase).toBe("tug_danger");
    // Still and dark releases the grip
    expect(well.update(2.2, false, false)).toBe("none");
    expect(well.update(2.5, false, false)).toBe("released");
    expect(well.phase).toBe("pull3");
    // Shining an open lamp on the final haul triggers a scare yank
    expect(well.pull(true)).toBe("yanked_back");
    expect(well.phase).toBe("tug_danger");
    expect(well.update(3.5, false, false)).toBe("released");
    // Final haul in darkness succeeds
    expect(well.pull(false)).toBe("hauled");
    expect(well.phase).toBe("complete");
  });

  it("restores attached parts and completion cleanly from Flags", () => {
    const flags = new Flags();
    flags.set("ep1.puzzle.well.weightAttached", true);
    flags.set("ep1.puzzle.well.hookAttached", true);
    const well = new WellMechanism();
    well.restore(flags);
    expect(well.phase).toBe("rigged");
    flags.set("ep1.puzzle.well.complete", true);
    well.restore(flags);
    expect(well.phase).toBe("complete");
  });
});

describe("Village Puzzle 3 — Compound Folklore Wards", () => {
  it("distinguishes 3 sticks for sacred/ancestral wards from 1 stick for the unquiet ruin", () => {
    expect(checkWardStation("neakta", "well_water", 3)).toBe("correct");
    expect(checkWardStation("neakta", "well_water", 1)).toBe("wrong_incense");
    expect(checkWardStation("neakta", "ward_marigold", 3)).toBe("wrong_offering");

    expect(checkWardStation("stupas", "sacred_thread", 3)).toBe("correct");
    expect(checkWardStation("stupas", "sacred_thread", 2)).toBe("wrong_incense");

    expect(checkWardStation("ruin", "ward_marigold", 1)).toBe("correct");
    expect(checkWardStation("ruin", "ward_marigold", 3)).toBe("wrong_incense");
  });

  it("counts solved wards accurately across Flags", () => {
    const flags = new Flags();
    expect(solvedWardCount(flags)).toBe(0);
    for (let i = 0; i < WARD_STATIONS.length; i++) {
      flags.set(`ep1.puzzle.ward.${WARD_STATIONS[i].id}`, true);
      expect(solvedWardCount(flags)).toBe(i + 1);
    }
  });
});

describe("Village Puzzle 4 — Stopped 20:12 Hall Pendulum Clock", () => {
  it("solves at 01:12, curses 00:00 / 03:00 / 20:12, and rejects unrelated times", () => {
    expect(checkClockDial(CLOCK_TARGET.hour, CLOCK_TARGET.minute)).toBe("solved");
    for (const c of CLOCK_CURSED_TIMES) {
      expect(checkClockDial(c.hour, c.minute)).toBe("cursed");
    }
    expect(checkClockDial(2, 30)).toBe("wrong");
    expect(checkClockDial(14, 45)).toBe("wrong");
  });
});
