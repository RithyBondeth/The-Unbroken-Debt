import { describe, expect, it } from "vitest";
import {
  BEATS,
  SCARES,
  facing,
  ghostPose,
  rushAcross,
  type ScareContext,
} from "@/episodes/ep2/PagodaApparition";

const base: ScareContext = {
  stage: "garden",
  feet: { x: 0, z: 0 },
  yaw: 0,
  offerings: 0,
  inKuti: false,
  mirrorsTurned: false,
  nearestPret: 20,
  zone: null,
  pickedLotus: false,
};
const scare = (id: string) => SCARES.find((s) => s.id === id)!;

describe("Episode 2 apparition scares", () => {
  it("has distinct one-time scares", () => {
    expect(new Set(SCARES.map((s) => s.id)).size).toBe(SCARES.length);
    expect(SCARES.length).toBeGreaterThanOrEqual(11);
  });
  it("carries her across the line of sight, ahead of Sora, from one side to the other", () => {
    for (const yaw of [0, 0.7, Math.PI, -2.2])
      for (const rightward of [true, false]) {
        const c = { ...base, yaw };
        const p = rushAcross(c, 9, 6.5, rightward);
        const right = { x: Math.cos(yaw), z: -Math.sin(yaw) };
        const side = (q: { x: number; z: number }) => q.x * right.x + q.z * right.z;
        expect(Math.sign(side(p))).toBe(rightward ? -1 : 1);
        expect(Math.sign(side(p.to!))).toBe(rightward ? 1 : -1);
        // Both ends in front of her, so she crosses the view and never walks at the camera.
        expect(facing(c, p)).toBeGreaterThan(0.5);
        expect(facing(c, p.to!)).toBeGreaterThan(0.5);
      }
  });
  it("waits for the lost garden's own places", () => {
    expect(scare("court_lanes").ready(base)).toBe(false);
    expect(scare("court_lanes").ready({ ...base, zone: "court" })).toBe(true);
    expect(scare("court_lanes").ready({ ...base, zone: "court", nearestPret: 3 })).toBe(false);
    const landing = { ...base, feet: { x: -53, z: -39 } };
    expect(scare("tank_rise").ready(landing)).toBe(false);
    expect(scare("tank_rise").ready({ ...landing, pickedLotus: true })).toBe(true);
  });
  it("shows her at the far end of the reclining Buddha only from inside the sala's mouth", () => {
    const sala = { ...base, feet: { x: 35, z: 8.7 }, yaw: Math.atan2(40.2 - 35, 12.9 - 8.7) };
    expect(scare("sala").ready(sala)).toBe(true);
    expect(scare("sala").ready({ ...sala, yaw: sala.yaw + Math.PI })).toBe(false);
    expect(scare("sala").ready({ ...sala, feet: { x: 20, z: 8.7 } })).toBe(false);
    expect(scare("sala").ready({ ...sala, stage: "escape" })).toBe(false);
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
    const at = scare("kuti_leave").place(c)!;
    expect(facing(c, at)).toBeLessThan(-0.9);
    expect(facing({ ...c, yaw: Math.PI }, at)).toBeGreaterThan(0.9);
  });
  it("rises from the pond only on the bridge in the library stage", () => {
    const bridge = { ...base, stage: "library" as const, feet: { x: 0, z: -23 } };
    expect(scare("bridge").ready(bridge)).toBe(true);
    expect(scare("bridge").ready({ ...bridge, feet: { x: 4, z: -23 } })).toBe(false);
    expect(scare("bridge").ready({ ...bridge, stage: "garden" })).toBe(false);
  });
  it("flickers in rather than fading: on, off, on, off, on", () => {
    expect([0.01, 0.06, 0.1, 0.15, 0.2].map((t) => ghostPose("lunge", t).visible)).toEqual([
      true,
      false,
      true,
      false,
      true,
    ]);
  });
  it("rolls her head over in a lunge, then across to the other side", () => {
    expect(ghostPose("lunge", 0.2).neck).toBe(0);
    expect(ghostPose("lunge", 0.5).neck).toBe(1);
    expect(ghostPose("lunge", 0.85).neck).toBeLessThan(0);
  });
  it("blinks out mid-stare and comes back a step nearer", () => {
    expect(ghostPose("stare", 0.95).visible).toBe(false);
    expect(ghostPose("stare", 0.5).travel).toBe(0);
    expect(ghostPose("stare", 1.1).travel).toBe(1);
  });
  it("cracks her neck in every appearance she stops for, and laughs when she stares", () => {
    // A pass is too quick to stop for: it has its own whoosh (audio/ghostSounds.ts).
    for (const [kind, beats] of Object.entries(BEATS))
      if (kind !== "rush") expect(beats.some((b) => b.sound === "crack")).toBe(true);
    expect(BEATS.stare.some((b) => b.sound === "laugh")).toBe(true);
  });
});
