import { expect, it, vi } from "vitest";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import { ActOneBeats } from "../../src/episodes/ep1/act1/ActOneBeats";
import { Prologue } from "../../src/episodes/ep1/prologue/Prologue";
it("captures Act I as CP1 at 23:30 and Act II as CP2 at 01:00 when old saves lack metadata flags", () => {
  const flags = new Flags();
  const state = {
    game: { flags, inventory: new Inventory(), sketchbook: null, resumedSave: null },
    progress: { save: vi.fn() },
    vigil: { saveState: vi.fn(), toJSON: () => ({ oil: 1, state: "out" }) },
    entries: [],
    playTime: 0,
  };
  const capture = () => ActOneBeats.prototype.captureProgress.call(state as unknown as ActOneBeats);
  expect(capture()).toMatchObject({ checkpoint: "CP1", clock: "23:30" });
  flags.set("ep1.act2.started", true);
  expect(capture()).toMatchObject({ checkpoint: "CP2", clock: "01:00" });
  flags.set("ep1.checkpoint", "CP5");
  flags.set("ep1.clock", "02:35");
  expect(capture()).toMatchObject({ checkpoint: "CP5", clock: "02:35" });
});
it("retries the departure checkpoint before navigating into the taxi journey", async () => {
  const writes: string[] = [];
  const save = vi
    .fn()
    .mockImplementationOnce(() => {
      writes.push("failed");
      return Promise.reject(new Error("quota"));
    })
    .mockImplementationOnce(() => {
      writes.push("saved");
      return Promise.resolve();
    });
  const replace = vi.fn();
  vi.stubGlobal("location", { pathname: "/", replace });
  const state = {
    game: {
      cutscene: false,
      gated: { holdStill: false, holdLook: false },
      camera: { globalPosition: {} },
      fade: { to: vi.fn(), show: vi.fn() },
      flags: new Flags(),
      sketchbook: { written: new Set(["SB-01"]) },
      inventory: new Inventory(),
      checkpoints: { mark: save },
      bus: { emit: vi.fn(() => writes.push("event")) },
    },
    play: vi.fn(),
    wait: vi.fn(),
    loops: [],
    playTime: 15,
  };
  try {
    const leave = Reflect.get(Prologue.prototype, "leave", state) as (
      this: typeof state,
    ) => Promise<void>;
    await leave.call(state);
    expect(save).toHaveBeenCalledTimes(2);
    expect(writes).toEqual(["failed", "saved", "event"]);
    expect(state.game.fade.show).toHaveBeenCalledWith(
      expect.objectContaining({ button: "Retry save" }),
    );
    expect(save.mock.calls[1][0]).toMatchObject({
      checkpoint: "CP0",
      clock: "20:12",
      flags: { "ep1.checkpoint": "CP0", "ep1.travel.pending": true },
    });
    expect(replace).toHaveBeenCalledWith("/?continue");
  } finally {
    vi.unstubAllGlobals();
  }
});
