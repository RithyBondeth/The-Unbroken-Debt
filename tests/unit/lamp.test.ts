import { describe, expect, it } from "vitest";
import { EventBus } from "../../src/core/EventBus";
import type { GameEvents } from "../../src/core/events";
import { FULL_TANK_SECONDS, Lamp } from "../../src/systems/lamp/Lamp";
import { Upkeep } from "../../src/systems/upkeep/Upkeep";

describe("Lamp", () => {
  it("burns a full tank in twelve minutes, then goes out", () => {
    const bus = new EventBus<GameEvents>();
    const states: string[] = [];
    bus.on("lamp:state", ({ state }) => states.push(state));
    const lamp = new Lamp(bus);
    expect(lamp.light()).toBe(true);
    lamp.update(FULL_TANK_SECONDS / 2);
    expect(lamp.oil).toBeCloseTo(0.5);
    lamp.update(FULL_TANK_SECONDS);
    expect(lamp.oil).toBe(0);
    expect(lamp.state).toBe("out");
    expect(states).toEqual(["open", "out"]);
  });

  it("doesn't burn oil while out, and won't light dry", () => {
    const lamp = new Lamp(undefined, 0.4);
    lamp.update(100);
    expect(lamp.oil).toBeCloseTo(0.4);
    const dry = new Lamp(undefined, 0);
    expect(dry.light()).toBe(false);
  });

  it("burns at full strength above a quarter tank and weaker below", () => {
    const lamp = new Lamp(undefined, 1, "open");
    expect(lamp.flame(1)).toBe(1);
    lamp.update(FULL_TANK_SECONDS * 0.9);
    const low = lamp.flame(1);
    expect(low).toBeGreaterThan(0);
    expect(low).toBeLessThan(0.5);
    lamp.putOut();
    expect(lamp.flame(1)).toBe(0);
  });

  it("refills to full and restores at least half at a checkpoint", () => {
    const lamp = new Lamp(undefined, 0.1);
    lamp.restoreAtLeast(0.5);
    expect(lamp.oil).toBeCloseTo(0.5);
    lamp.refill(1);
    expect(lamp.oil).toBe(1);
    expect(lamp.toJSON()).toEqual({ oil: 1, state: "out" });
  });

  it("reports oil in steps of one percent", () => {
    const bus = new EventBus<GameEvents>();
    let reports = 0;
    bus.on("lamp:oil", () => reports++);
    const lamp = new Lamp(bus, 1, "open");
    for (let i = 0; i < 100; i++) lamp.update(FULL_TANK_SECONDS / 1000);
    expect(reports).toBe(10);
  });
});

describe("Upkeep", () => {
  it("warns twice, expires once and counts the time out", () => {
    const bus = new EventBus<GameEvents>();
    const seen: string[] = [];
    bus.on("upkeep:warning", ({ stage }) => seen.push(`warn${stage}`));
    bus.on("upkeep:expired", () => seen.push("out"));
    const incense = new Upkeep("incense", { duration: 100, warnings: [0.25, 0.1] }, bus);
    incense.update(80);
    expect(incense.warning).toBe(1);
    incense.update(15);
    incense.update(10);
    incense.update(30);
    expect(seen).toEqual(["warn1", "warn2", "out"]);
    expect(incense.alive).toBe(false);
    expect(incense.outFor).toBe(30);
  });

  it("starts again from full when renewed", () => {
    const incense = new Upkeep("incense", { duration: 100, warnings: [0.25, 0.1] });
    incense.extinguish();
    expect(incense.alive).toBe(false);
    incense.renew();
    expect(incense.alive).toBe(true);
    expect(incense.fraction).toBe(1);
    expect(incense.warning).toBe(0);
  });
});
