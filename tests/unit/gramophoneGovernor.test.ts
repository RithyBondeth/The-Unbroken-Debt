import { describe, expect, it } from "vitest";
import { Flags } from "../../src/core/Flags";
import { GramophoneGovernor } from "../../src/episodes/ep1/act2/GramophoneGovernor";
import { GOVERNOR } from "../../src/episodes/ep1/data/investigation";

describe("Sok’s gramophone governor", () => {
  it("requires sustained active listening and resets when Sora steps away", () => {
    const flags = new Flags();
    const governor = new GramophoneGovernor(flags);
    governor.adjust(78 - governor.rpm);
    expect(governor.update(1, true)).toBe(false);
    expect(governor.update(10, false)).toBe(false);
    expect(governor.update(1, true)).toBe(false);
    expect(governor.update(0.9, true)).toBe(true);
    expect(flags.get("ep1.gramophone.solved", false)).toBe(true);
    expect(flags.get("ep1.gramophone.heard", false)).toBe(false);
    expect(governor.update(10, true)).toBe(false);
  });

  it("does not solve at the wrong speed or when sweeping past the correct setting", () => {
    const governor = new GramophoneGovernor(new Flags());
    governor.adjust(13);
    expect(governor.rpm).toBe(77);
    expect(governor.update(90, true)).toBe(false);
    governor.adjust(1);
    expect(governor.update(0.8, true)).toBe(false);
    governor.adjust(1);
    governor.adjust(-1);
    expect(governor.update(1.2, true)).toBe(false);
    expect(governor.update(0.7, true)).toBe(true);
  });

  it("restores partial tuning, clamps damaged values and locks a solved record", () => {
    const flags = new Flags();
    const first = new GramophoneGovernor(flags);
    first.adjust(5);
    const restored = new Flags();
    restored.load(flags.toJSON());
    expect(new GramophoneGovernor(restored).rpm).toBe(69);
    restored.set("ep1.gramophone.rpm", -500);
    expect(new GramophoneGovernor(restored).rpm).toBe(GOVERNOR.min);
    restored.set("ep1.gramophone.rpm", NaN);
    expect(new GramophoneGovernor(restored).rpm).toBe(GOVERNOR.initial);
    restored.set("ep1.gramophone.solved", true);
    const solved = new GramophoneGovernor(restored);
    solved.adjust(-20);
    expect(solved.rpm).toBe(GOVERNOR.correct);
  });
});
