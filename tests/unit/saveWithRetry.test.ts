import { describe, expect, it, vi } from "vitest";
import { saveWithRetry } from "../../src/systems/saves/saveWithRetry";

describe("saveWithRetry", () => {
  it("writes once when the browser accepts the save", async () => {
    const write = vi.fn(() => Promise.resolve());
    const ask = vi.fn(() => Promise.resolve());
    await saveWithRetry(write, ask);
    expect(write).toHaveBeenCalledTimes(1);
    expect(ask).not.toHaveBeenCalled();
  });

  it("asks the player and tries again until the write succeeds", async () => {
    vi.stubGlobal("document", { exitPointerLock: vi.fn() });
    let attempts = 0;
    const write = vi.fn(() =>
      ++attempts < 3 ? Promise.reject(new Error("full")) : Promise.resolve(),
    );
    const ask = vi.fn(() => Promise.resolve());
    await saveWithRetry(write, ask);
    expect(write).toHaveBeenCalledTimes(3);
    expect(ask).toHaveBeenCalledTimes(2);
    vi.unstubAllGlobals();
  });
});
