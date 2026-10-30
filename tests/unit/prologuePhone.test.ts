import { Matrix } from "@babylonjs/core/Maths/math.vector";
import { expect, it, vi } from "vitest";
import { Prologue } from "../../src/episodes/ep1/prologue/Prologue";
import { DreadScore } from "../../src/episodes/ep1/audio/DreadScore";
import { Flags } from "../../src/core/Flags";

it.each([
  ["satchel", "hint.packSatchel"],
  ["sketchbook", "hint.packSketchbook"],
  ["matches", "hint.packMatches"],
  ["lamp", "hint.packLamp"],
])("explains the missing %s when the phone is used before the call is armed", (missing, hint) => {
  const state = {
    game: {
      flags: new Flags(),
      inventory: { has: (item: string) => item !== missing },
      hints: { show: vi.fn() },
    },
    ringing: false,
    waiting: new Map(),
  };
  const use = Reflect.get(Prologue.prototype, "onUse") as (this: typeof state, id: string) => void;
  use.call(state, "interact_telephone");
  expect(state.game.hints.show).toHaveBeenCalledWith(hint, 8);
  expect(state.game.flags.get("ep1.phone.answered", false)).toBe(false);
});

it("puts the automatic notebook away before waiting for the ringing phone", async () => {
  let bookOpen = false;
  let satchelOpen = true;
  const order: string[] = [];
  const state = {
    game: {
      cutscene: false,
      input: { lockPointer: vi.fn() },
      audio: null,
      fade: { to: vi.fn(), waitForEnter: vi.fn() },
      interaction: { allow: () => true },
      flags: new Flags(),
      inventory: { has: () => true },
      satchel: {
        close: () => {
          satchelOpen = false;
        },
      },
      sketchbook: {
        write: () => {
          bookOpen = true;
          order.push("write");
        },
        close: () => {
          bookOpen = false;
          order.push("close");
        },
      },
      hints: { show: vi.fn() },
    },
    lights: { strike: vi.fn(), snuffCandle: vi.fn() },
    ink: { inkLine: vi.fn(), spill: vi.fn() },
    sfx: new Map(),
    score: new DreadScore(null),
    ringing: false,
    makeSounds: vi.fn(),
    idleHints: vi.fn(),
    play: vi.fn(),
    wait: vi.fn(),
    until: vi.fn(),
    drawIllustration: vi.fn(),
    phoneCall: vi.fn(),
    leave: vi.fn(),
    saveProgress: vi.fn(),
    used: vi.fn((id: string) => {
      if (id === "interact_telephone") {
        expect(state.ringing).toBe(true);
        expect(bookOpen).toBe(false);
        expect(satchelOpen).toBe(false);
        order.push("phone");
      }
      return Promise.resolve();
    }),
  };
  vi.useFakeTimers();
  try {
    const run = Reflect.get(Prologue.prototype, "run") as (this: typeof state) => Promise<void>;
    await run.call(state);
    expect(order).toEqual(["write", "close", "phone"]);
    expect(state.phoneCall).toHaveBeenCalledOnce();
    expect(state.leave).toHaveBeenCalledOnce();
  } finally {
    vi.clearAllTimers();
    vi.useRealTimers();
  }
});

it.each([false, true])(
  "releases drawing input and restores the view after completion or failure (failure=%s)",
  async (fail) => {
    const game = {
      player: { yaw: 1.2, pitch: 0.6 },
      gated: { holdStill: false, holdLook: false },
      inspectObject: vi.fn(),
      stopInspecting: vi.fn(),
    };
    const state = {
      game,
      mesh: () => ({
        scaling: { x: 1 },
        computeWorldMatrix: () => Matrix.Translation(-3, 0.914, -0.72),
      }),
      play: vi.fn(),
      ink: {
        inkLine: vi.fn(() => {
          expect(game.gated.holdStill && game.gated.holdLook).toBe(true);
          game.player.yaw = 3;
          return fail ? Promise.reject(new Error("drawing failed")) : Promise.resolve();
        }),
      },
    };
    const draw = Reflect.get(Prologue.prototype, "drawIllustration") as (
      this: typeof state,
    ) => Promise<void>;
    if (fail) await expect(draw.call(state)).rejects.toThrow("drawing failed");
    else await draw.call(state);
    expect(state.ink.inkLine).toHaveBeenCalledWith(3.6);
    expect(game.stopInspecting).toHaveBeenCalledOnce();
    expect(game.player).toEqual({ yaw: 1.2, pitch: 0.6 });
    expect(game.gated).toEqual({ holdStill: false, holdLook: false });
  },
);
