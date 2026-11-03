import { describe, expect, it } from "vitest";
import { SCARES, facing, type ScareContext } from "../../src/episodes/ep2/PagodaApparition";

const base: ScareContext = {
  stage: "garden",
  feet: { x: 0, z: 0 },
  yaw: 0,
  offerings: 0,
  inKuti: false,
  mirrorsTurned: false,
  nearestPret: 20,
};
const scare = (id: string) => SCARES.find((s) => s.id === id)!;

describe("Episode 2 apparition scares", () => {
  it("has six distinct one-time scares", () => {
    expect(new Set(SCARES.map((s) => s.id)).size).toBe(6);
  });
  it("lunges at the sealed hall only when Sora faces the door", () => {
    const near = { ...base, feet: { x: 22, z: 9 }, yaw: Math.PI };
    expect(scare("hall_door").ready(near)).toBe(true);
    expect(scare("hall_door").ready({ ...near, yaw: 0 })).toBe(false);
    expect(scare("hall_door").ready({ ...near, stage: "arrival" })).toBe(false);
  });
  it("waits for the second offering and keeps clear of a near Pret", () => {
    expect(scare("garden_stare").ready({ ...base, offerings: 1 })).toBe(false);
    expect(scare("garden_stare").ready({ ...base, offerings: 2 })).toBe(true);
    expect(scare("garden_stare").ready({ ...base, offerings: 2, nearestPret: 3 })).toBe(false);
  });
  it("places a behind scare behind the player, so it shows only when they turn", () => {
    const c = { ...base, feet: { x: -18, z: 19.6 }, yaw: 0 };
    expect(scare("kuti_leave").ready(c)).toBe(true);
    const at = scare("kuti_leave").place(c);
    expect(facing(c, at)).toBeLessThan(-0.9);
    expect(facing({ ...c, yaw: Math.PI }, at)).toBeGreaterThan(0.9);
  });
  it("rises from the pond only on the bridge in the library stage", () => {
    const bridge = { ...base, stage: "library" as const, feet: { x: 0, z: -23 } };
    expect(scare("bridge").ready(bridge)).toBe(true);
    expect(scare("bridge").ready({ ...bridge, feet: { x: 4, z: -23 } })).toBe(false);
    expect(scare("bridge").ready({ ...bridge, stage: "garden" })).toBe(false);
  });
});
