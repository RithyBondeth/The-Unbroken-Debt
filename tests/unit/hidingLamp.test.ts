import { expect, it, vi } from "vitest";
import { Lamp } from "../../src/systems/lamp/Lamp";
import { Vigil } from "../../src/episodes/ep1/act1/Vigil";
it("can put out a burning lamp during a threat, without permitting a new match", () => {
  const state = {
    game: { cutscene: false, satchel: { isOpen: false }, sketchbook: { isOpen: false } },
    handsFree: false,
    lamp: new Lamp(undefined, 1, "open"),
    play: vi.fn(),
    lightLamp: vi.fn(),
  };
  const press = Reflect.get(Vigil.prototype, "onKey", state) as (
    this: typeof state,
    e: { code: string; repeat: boolean },
  ) => void;
  press.call(state, { code: "KeyF", repeat: false });
  expect(state.lamp.burning).toBe(false);
  press.call(state, { code: "KeyF", repeat: false });
  expect(state.lightLamp).not.toHaveBeenCalled();
});
