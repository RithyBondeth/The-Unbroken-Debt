import { describe, expect, it } from "vitest";
import { GatedInput } from "../../src/player/InputSource";
describe("wardrobe input", () => {
  it("holds movement and stance while hidden, then releases the underlying controls", () => {
    const gated = new GatedInput({
      readMove: (out) => Object.assign(out, { x: 1, z: 1, hurry: true, crouch: true }),
      consumeLook: (out) => Object.assign(out, { yaw: 0.1, pitch: 0.05 }),
      dispose: () => undefined,
    });
    const move = { x: 0, z: 0, hurry: false, crouch: false };
    gated.hiding = true;
    gated.readMove(move);
    expect(move).toEqual({ x: 0, z: 0, hurry: false, crouch: false });
    gated.hiding = false;
    gated.readMove(move);
    expect(move).toEqual({ x: 1, z: 1, hurry: true, crouch: true });
  });
});
