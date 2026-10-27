import { describe, expect, it, vi } from "vitest";
import { Checkpoints, checkpointName } from "../../src/systems/saves/Checkpoints";
import { newGameSave } from "../../src/systems/saves/SaveData";
import type { SaveStore } from "../../src/systems/saves/SaveStore";
const setup = () => {
  const store = {
    save: vi.fn().mockResolvedValue(undefined),
    saveCheckpoint: vi.fn().mockResolvedValue(undefined),
    load: vi.fn().mockResolvedValue({ save: null }),
  };
  return { store, checkpoints: new Checkpoints(() => store as unknown as SaveStore) };
};
describe("safe checkpoints", () => {
  it("restores the immutable story, item counts, lamp and position from the last safe write", async () => {
    const { store, checkpoints } = setup(),
      data = newGameSave();
    data.inventory = { matches: 10 };
    data.flags = { "ep1.early.required": true, "checkpoint.spawn.z": 60 };
    data.lamp.oil = 0.7;
    await checkpoints.mark(data, "Village · Flooded road");
    data.inventory.matches = 1;
    data.flags["ep1.early.complete"] = true;
    data.lamp.oil = 0.1;
    const exposed = checkpoints.last!;
    exposed.inventory.matches = 0;
    const retry = await checkpoints.prepareRetry();
    expect(retry.inventory.matches).toBe(10);
    expect(retry.lamp.oil).toBe(0.7);
    expect(retry.flags["ep1.early.complete"]).toBeUndefined();
    expect(retry.flags["checkpoint.spawn.z"]).toBe(60);
    expect(store.save).toHaveBeenCalledWith("autosave", retry);
    expect(checkpointName(retry)).toBe("Village · Flooded road");
  });
  it("keeps the previous safe point when storage rejects a new checkpoint", async () => {
    const { store, checkpoints } = setup();
    await checkpoints.mark(newGameSave(), "Studio");
    store.saveCheckpoint.mockRejectedValueOnce(new Error("quota"));
    await expect(checkpoints.mark(newGameSave(), "Courtyard")).rejects.toThrow("quota");
    expect(checkpointName(checkpoints.last!)).toBe("Studio");
  });
  it("serializes overlapping pickups so disk and memory retain the latest complete snapshot", async () => {
    const { store, checkpoints } = setup();
    let finish!: () => void;
    store.saveCheckpoint.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    const first = checkpoints.mark(newGameSave(), "First");
    await Promise.resolve();
    const second = checkpoints.mark(newGameSave(), "Second");
    expect(store.saveCheckpoint).toHaveBeenCalledTimes(1);
    finish();
    await Promise.all([first, second]);
    expect(checkpointName(checkpoints.last!)).toBe("Second");
  });
  it("loads legacy autosaves without a checkpoint slot and rejects another playthrough’s checkpoint", async () => {
    const { store, checkpoints } = setup(),
      fallback = newGameSave();
    fallback.checkpoint = "CP3";
    await checkpoints.load(fallback);
    expect(checkpoints.last?.checkpoint).toBe("CP3");
    const other = newGameSave();
    other.flags["game.run"] = "previous";
    store.load.mockResolvedValueOnce({ save: other });
    fallback.flags["game.run"] = "current";
    await checkpoints.load(fallback);
    expect(checkpoints.last?.flags["game.run"]).toBe("current");
  });
});
