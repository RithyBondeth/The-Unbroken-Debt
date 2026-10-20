import { describe, expect, it, vi } from "vitest";
import { EventBus } from "../../src/core/EventBus";
import { Flags } from "../../src/core/Flags";
import type { GameEvents } from "../../src/core/events";

describe("Flags", () => {
  it("returns the fallback for unknown keys", () => {
    const flags = new Flags();
    expect(flags.get("ep1.betel.done", false)).toBe(false);
    expect(flags.has("ep1.betel.done")).toBe(false);
  });

  it("emits flag:changed only when a value actually changes", () => {
    const bus = new EventBus<GameEvents>();
    const changed = vi.fn();
    bus.on("flag:changed", changed);
    const flags = new Flags(bus);

    flags.set("ep1.betel.done", true);
    flags.set("ep1.betel.done", true);

    expect(changed).toHaveBeenCalledOnce();
    expect(changed).toHaveBeenCalledWith({ key: "ep1.betel.done", value: true });
  });

  it("increments numeric counters", () => {
    const flags = new Flags();
    flags.increment("series.respect");
    flags.increment("series.respect", 2);
    expect(flags.get("series.respect", 0)).toBe(3);
  });

  it("round-trips through toJSON and load", () => {
    const flags = new Flags();
    flags.set("ep1.journal.shared", true);
    flags.set("series.respect", 4);

    const restored = new Flags();
    restored.load(flags.toJSON());

    expect(restored.get("ep1.journal.shared", false)).toBe(true);
    expect(restored.get("series.respect", 0)).toBe(4);
  });
});
