import { describe, expect, it, vi } from "vitest";
import { Flags } from "../../src/core/Flags";
import { GatedInput, type InputSource } from "../../src/player/InputSource";
import { ActOneBeats } from "../../src/episodes/ep1/act1/ActOneBeats";

function courtyard() {
  const flags = new Flags();
  flags.set("ep1.vigil.started", true);
  const input: InputSource = {
    readMove: (out) => Object.assign(out, { x: 0, z: 1, hurry: false, crouch: false }),
    consumeLook: () => {},
    dispose: () => {},
  };
  const gated = new GatedInput(input);
  const game = {
    flags,
    gated,
    cutscene: false,
    player: { feet: { z: 8 } },
    bus: { emit: vi.fn() },
    sketchbook: null,
    satchel: { isOpen: false },
  };
  // Exercise the actual arrival update without constructing its doors, audio or DOM readers.
  const beats = Object.assign(Object.create(ActOneBeats.prototype), {
    game,
    started: true,
    busy: false,
    opening: -1,
    playTime: 0,
    courtyardBeatRemaining: 0,
    entries: [],
    sok: { update: vi.fn() },
    shed: { update: vi.fn() },
    progress: { update: vi.fn(), ready: () => false },
  }) as ActOneBeats;
  return { beats, game, gated };
}

describe("first courtyard view", () => {
  it("keeps walking through the reveal and emits its story beat only once", () => {
    const { beats, game, gated } = courtyard();
    for (let i = 0; i < 240; i++) {
      beats.update(1 / 60);
      expect(gated.readMove({ x: 0, z: 0, hurry: false, crouch: false }).z).toBe(1);
    }
    expect(game.flags.get("ep1.arrival.courtyard", false)).toBe(true);
    expect(game.bus.emit.mock.calls).toEqual([
      ["sequence:start", { id: "A1-02" }],
      ["sequence:end", { id: "A1-02" }],
    ]);
  });
  it("does not release another interaction's movement lock when the reveal ends", () => {
    const { beats, game, gated } = courtyard();
    beats.update(0.1);
    game.cutscene = true;
    gated.holdStill = true;
    beats.update(3);
    expect(gated.holdStill).toBe(true);
  });
});
