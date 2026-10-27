import { expect, it, vi } from "vitest";
import { Prologue } from "../../src/episodes/ep1/prologue/Prologue";
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
      fade: { to: vi.fn(), waitForClick: vi.fn() },
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
    ringing: false,
    makeSounds: vi.fn(),
    idleHints: vi.fn(),
    play: vi.fn(),
    wait: vi.fn(),
    until: vi.fn(),
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
