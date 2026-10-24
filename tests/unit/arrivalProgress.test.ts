import { describe, expect, it } from "vitest";
import { Flags } from "../../src/core/Flags";
import { ArrivalProgress } from "../../src/episodes/ep1/act1/ArrivalProgress";
import { VigilProgress } from "../../src/episodes/ep1/act1/VigilProgress";

const reload = (flags: Flags) => {
  const restored = new Flags();
  restored.load(structuredClone(flags.toJSON()));
  return restored;
};
describe("phone arrival", () => {
  it("keeps Vuthy present when reloading his dawn journal conversation", () => {
    const flags = new Flags();
    flags.set("ep1.vigil.started", true);
    flags.set("ep1.resolution.started", true);
    flags.set("ep1.vuthy.left", false);
    new ArrivalProgress(flags);
    expect(flags.get("ep1.vuthy.left", true)).toBe(false);
  });
  it("keeps the vigil stopped until the whole phone call finishes", () => {
    const flags = new Flags();
    const arrival = new ArrivalProgress(flags);
    expect(flags.get("ep1.vuthy.left", false)).toBe(true);
    flags.set("ep1.arrival.noteRead", true);
    flags.set("ep1.betel.asked", true); // interrupted during the call
    const saved = reload(flags);
    const resumed = new ArrivalProgress(saved);
    expect(resumed.called).toBe(false);
    const vigil = new VigilProgress(saved, 660);
    vigil.update(1000);
    expect(saved.get("ep1.incense.cyclePassed", false)).toBe(false);
    resumed.finishCall();
    expect(new ArrivalProgress(reload(saved)).called).toBe(true);
    expect(arrival.called).toBe(false);
  });
  it("never replenishes collected or spent prepared matches on reload", () => {
    const flags = new Flags();
    const arrival = new ArrivalProgress(flags);
    expect(arrival.takeMatches()).toBe(true);
    expect(arrival.takeMatches()).toBe(false);
    expect(new ArrivalProgress(reload(flags)).takeMatches()).toBe(false);
  });
  it("waits for the prepared matchbox before the Act II handover", () => {
    const flags = new Flags();
    const arrival = new ArrivalProgress(flags);
    arrival.finishCall();
    flags.set("ep1.betel.done", true);
    const vigil = new VigilProgress(flags, 660);
    vigil.update(660);
    expect(vigil.ready(true, true)).toBe(false);
    arrival.takeMatches();
    expect(vigil.ready(true, true)).toBe(true);
  });
  it("preserves older completed-offering saves without duplicate matches or a new phone gate", () => {
    const flags = new Flags();
    flags.set("ep1.vigil.started", true);
    flags.set("ep1.betel.done", true);
    const arrival = new ArrivalProgress(flags);
    expect(arrival.called).toBe(true);
    expect(arrival.taken).toBe(true);
    expect(arrival.takeMatches()).toBe(false);
    const vigil = new VigilProgress(flags, 660);
    vigil.update(660);
    expect(vigil.ready(true, true)).toBe(true);
  });
});
