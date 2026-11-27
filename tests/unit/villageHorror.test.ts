import { describe, expect, it } from "vitest";
import { Flags } from "@/core/Flags";
import {
  HAUNT_COOLDOWN_SEC,
  ROADSIDE_PEEK_RETREAT,
  ROADSIDE_PEEK_SPOT,
  SHOP_CROSSING_PATH,
  VillageHauntPacer,
} from "@/episodes/ep1/data/villageHaunts";
import { CURSED_CLOCK_TIME, EpisodeClockState } from "@/episodes/ep1/clock/EpisodeClock";

describe("VillageHauntPacer", () => {
  it("enforces breathing room cooldowns and one-shot memory for autonomous scares", () => {
    const pacer = new VillageHauntPacer();
    expect(pacer.canTriggerAutonomous("roadsidePeeker", false)).toBe(false);
    // Cooldown does not drain while busy
    pacer.tick(20, true);
    expect(pacer.canTriggerAutonomous("roadsidePeeker", false)).toBe(false);
    // Drains once free
    pacer.tick(11, false);
    expect(pacer.canTriggerAutonomous("roadsidePeeker", false)).toBe(true);
    pacer.markTriggered("roadsidePeeker");
    expect(pacer.hasDone("roadsidePeeker")).toBe(true);
    // Blocked during cooldown and permanently marked done
    expect(pacer.canTriggerAutonomous("strobeCloser", false)).toBe(false);
    pacer.tick(HAUNT_COOLDOWN_SEC + 1, false);
    expect(pacer.canTriggerAutonomous("roadsidePeeker", false)).toBe(false);
    expect(pacer.canTriggerAutonomous("strobeCloser", false)).toBe(true);
  });

  it("supports repeatable beats and tightens cooldown modestly under aggravation", () => {
    const pacer = new VillageHauntPacer();
    pacer.tick(15, false);
    pacer.aggravate(4);
    pacer.markTriggered("extraFootstep", true);
    expect(pacer.hasDone("extraFootstep")).toBe(false);
    // Even at max aggravation (4), cooldown never drops below 12 seconds
    pacer.tick(11, false);
    expect(pacer.canTriggerAutonomous("extraFootstep", false)).toBe(false);
    pacer.tick(2, false);
    expect(pacer.canTriggerAutonomous("extraFootstep", false)).toBe(true);
  });

  it("tracks cover retreat and shop doorway crossing choreography cleanly", () => {
    const pacer = new VillageHauntPacer();
    pacer.tick(12, false);
    expect(pacer.canTriggerAutonomous("shopDoorCrossing", false)).toBe(true);
    pacer.markTriggered("shopDoorCrossing");
    expect(pacer.hasDone("shopDoorCrossing")).toBe(true);
    // Cover retreat moves physically behind the west shop wall from the roadside peek spot
    expect(ROADSIDE_PEEK_RETREAT.x).toBeLessThan(ROADSIDE_PEEK_SPOT.x - 4);
    expect(SHOP_CROSSING_PATH.to.x).toBeGreaterThan(SHOP_CROSSING_PATH.from.x + 2.5);
  });
});

describe("EpisodeClockState", () => {
  it("tracks story time, polls milestones once, and glitches to 20:12 cleanly", () => {
    const flags = new Flags();
    flags.set("ep1.clock", "23:30");
    const clock = new EpisodeClockState(flags);
    expect(clock.rawTime).toBe("23:30");
    expect(clock.displayTime).toBe("23:30");
    expect(clock.pollMilestone()).toBeNull();

    // Another subsystem advances ep1.clock to a major milestone
    flags.set("ep1.clock", "01:00");
    const m = clock.pollMilestone();
    expect(m).toEqual({ time: "01:00", label: "The First Watch" });
    expect(clock.pollMilestone()).toBeNull();

    // Direct advance avoids duplicate announcements
    expect(clock.advance("02:00")).toEqual({ time: "02:00", label: "Beneath the Stilts" });
    expect(clock.advance("02:00")).toBeNull();

    // Peak haunt glitch temporarily freezes display to 20:12
    clock.triggerGlitch(5);
    expect(clock.glitched).toBe(true);
    expect(clock.displayTime).toBe(CURSED_CLOCK_TIME);
    expect(clock.label).toContain("stopped");
    clock.update(3);
    expect(clock.glitched).toBe(true);
    clock.update(3);
    expect(clock.glitched).toBe(false);
    expect(clock.displayTime).toBe("02:00");
  });
});
