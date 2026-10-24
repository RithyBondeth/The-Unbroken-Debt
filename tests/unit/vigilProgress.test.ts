import { describe, expect, it } from "vitest";
import { Flags } from "../../src/core/Flags";
import { VigilProgress } from "../../src/episodes/ep1/act1/VigilProgress";
import { Upkeep } from "../../src/systems/upkeep/Upkeep";

describe("Act I handover", () => {
  it("requires the offering, a vigil cycle, the tent and free hands", () => {
    const flags = new Flags();
    const progress = new VigilProgress(flags, 660);
    progress.update(1000); // Loading, the carriage and greetings do not use the vigil timer.
    expect(flags.get("ep1.incense.cyclePassed", false)).toBe(false);
    flags.set("ep1.vigil.started", true);
    progress.update(660);
    expect(progress.ready(true, true)).toBe(false);
    flags.set("ep1.betel.done", true);
    expect(progress.ready(false, true)).toBe(false);
    expect(progress.ready(true, false)).toBe(false);
    expect(progress.ready(true, true)).toBe(true);
    flags.set("ep1.act2.started", true);
    expect(progress.ready(true, true)).toBe(false);
  });

  it("counts a full cycle even when the sticks are renewed early", () => {
    const flags = new Flags();
    flags.set("ep1.vigil.started", true);
    flags.set("ep1.betel.done", true);
    const progress = new VigilProgress(flags, 660);
    const incense = new Upkeep("incense", { duration: 660, warnings: [0.25, 0.1] });
    for (let k = 0; k < 3; k++) {
      incense.update(220);
      progress.update(220);
      incense.renew();
    }
    expect(incense.alive).toBe(true);
    expect(progress.ready(true, true)).toBe(true);
    expect(flags.get("ep1.incense.neglected", false)).toBe(false);
  });

  it("restores elapsed vigil time and doesn't restart after Act II begins", () => {
    const flags = new Flags();
    flags.set("ep1.vigil.started", true);
    const first = new VigilProgress(flags, 660);
    first.update(600);
    first.save();
    const restored = new Flags();
    restored.load(flags.toJSON());
    const progress = new VigilProgress(restored, 660);
    progress.update(59);
    expect(restored.get("ep1.incense.cyclePassed", false)).toBe(false);
    progress.update(1);
    expect(restored.get("ep1.incense.cyclePassed", false)).toBe(true);
    restored.set("ep1.act2.started", true);
    progress.update(900);
    progress.save();
    expect(restored.get("ep1.vigil.seconds", 0)).toBe(660);
  });

  it("restores expired incense with its neglect grace period intact", () => {
    const incense = new Upkeep("incense", { duration: 660, warnings: [0.25, 0.1] });
    incense.restore(0, 18);
    expect(incense.alive).toBe(false);
    incense.update(10);
    expect(incense.outFor).toBe(28);
    incense.restore(0.2, 60);
    expect(incense.alive).toBe(true);
    expect(incense.warning).toBe(1);
    expect(incense.outFor).toBe(0);
    incense.update(66);
    expect(incense.fraction).toBeCloseTo(0.1);
    expect(incense.warning).toBe(2);
  });
});
