import { describe, expect, it, vi } from "vitest";
import { EventBus } from "../../src/core/EventBus";

type TestEvents = {
  ping: { n: number };
  other: { s: string };
};

describe("EventBus", () => {
  it("delivers payloads to subscribers of that event only", () => {
    const bus = new EventBus<TestEvents>();
    const ping = vi.fn();
    const other = vi.fn();
    bus.on("ping", ping);
    bus.on("other", other);

    bus.emit("ping", { n: 1 });

    expect(ping).toHaveBeenCalledWith({ n: 1 });
    expect(other).not.toHaveBeenCalled();
  });

  it("stops delivering after unsubscribe", () => {
    const bus = new EventBus<TestEvents>();
    const handler = vi.fn();
    const off = bus.on("ping", handler);

    off();
    bus.emit("ping", { n: 2 });

    expect(handler).not.toHaveBeenCalled();
  });

  it("keeps calling other handlers when one throws", () => {
    const bus = new EventBus<TestEvents>();
    const after = vi.fn();
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    bus.on("ping", () => {
      throw new Error("boom");
    });
    bus.on("ping", after);

    bus.emit("ping", { n: 3 });

    expect(after).toHaveBeenCalledWith({ n: 3 });
    expect(consoleError).toHaveBeenCalledOnce();
    consoleError.mockRestore();
  });
});
