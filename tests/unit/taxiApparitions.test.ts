import { describe, expect, it } from "vitest";
import {
  TAXI_PASSES,
  TAXI_RITUAL_ALONG,
  taxiPass,
  taxiFlinch,
  taxiPassBeat,
  taxiRunnerAt,
  taxiSwerve,
} from "../../src/episodes/ep1/travel/taxiApparitions";
import { taxiNightLevels, taxiThrottle } from "../../src/episodes/ep1/travel/TaxiSoundscape";
import { taxiDistance, taxiRoadPoint, taxiRoadX } from "../../src/episodes/ep1/travel/taxiMotion";
import { TAXI_CONVERSATION } from "../../src/episodes/ep1/travel/taxiConversation";

/** Signed metres right of the centreline, the inverse of taxiRoadPoint near `along`. */
function lateral(x: number, z: number): number {
  let best = Infinity,
    side = 0;
  for (let along = z - 8; along <= z + 8; along += 0.01) {
    const d = Math.hypot(x - taxiRoadX(along), z - along);
    if (d < best) {
      best = d;
      side = Math.sign(x - taxiRoadX(along));
    }
  }
  return best * side;
}

describe("the forms that run past the taxi", () => {
  it("runs two passes that never overlap", () => {
    expect(TAXI_PASSES.map((p) => p.kind)).toEqual(["crossing", "overtake"]);
    for (const [a, b] of TAXI_PASSES.slice(0, -1).map((p, i) => [p, TAXI_PASSES[i + 1]] as const))
      expect(a.start + a.seconds).toBeLessThan(b.start);
    for (const pass of TAXI_PASSES) {
      // Every pass finishes before the car starts to brake at the drop-off.
      expect(pass.start + pass.seconds).toBeLessThan(62);
    }
  });

  it("crosses the whole road ahead of the car faster than a person can run", () => {
    const pass = taxiPass("crossing");
    const start = taxiRunnerAt(pass.start + 0.001)!,
      end = taxiRunnerAt(pass.start + pass.seconds - 0.001)!;
    expect(lateral(start.x, start.z)).toBeLessThan(-4.5);
    expect(lateral(end.x, end.z)).toBeGreaterThan(4.5);
    const ahead = start.z - taxiDistance(pass.start);
    expect(ahead).toBeGreaterThan(6);
    expect(ahead).toBeLessThan(12);
    expect(10 / pass.seconds).toBeGreaterThan(12);
  });

  it("overtakes up Sora's side, level with her window at the slap, then leaves into the trees", () => {
    const pass = taxiPass("overtake"),
      beat = taxiPassBeat(pass),
      level = taxiRunnerAt(beat)!;
    expect(Math.abs(level.z - taxiDistance(beat))).toBeLessThan(1.5);
    expect(lateral(level.x, level.z)).toBeGreaterThan(1.8);
    expect(lateral(level.x, level.z)).toBeLessThan(2.8);
    const gone = taxiRunnerAt(pass.start + pass.seconds - 0.001)!;
    expect(lateral(gone.x, gone.z)).toBeGreaterThan(5.5);
    expect(taxiRunnerAt(pass.start - 0.01)).toBeNull();
    expect(taxiRunnerAt(pass.start + pass.seconds + 0.01)).toBeNull();
  });

  it("trails copies a beat behind the lead for the smear", () => {
    const beat = taxiPassBeat(taxiPass("crossing")),
      lead = taxiRunnerAt(beat)!,
      trail = taxiRunnerAt(beat, 0.045)!;
    expect(lateral(trail.x, trail.z)).toBeLessThan(lateral(lead.x, lead.z));
  });

  it("swerves and flinches briefly after the crossing, then settles", () => {
    const beat = taxiPassBeat(taxiPass("crossing"));
    expect(taxiSwerve(beat - 0.1)).toBe(0);
    let peak = 0;
    for (let t = beat; t < beat + 3; t += 0.01) peak = Math.max(peak, Math.abs(taxiSwerve(t)));
    expect(peak).toBeGreaterThan(0.03);
    expect(peak).toBeLessThan(0.1);
    expect(taxiSwerve(beat + 3)).toBe(0);
    expect(taxiFlinch(beat + 0.3)).toBeGreaterThan(0.5);
    expect(taxiFlinch(20)).toBe(0);
  });

  it("places the rite on Sora's side of the road", () => {
    const at = taxiRoadPoint(5.4, TAXI_RITUAL_ALONG);
    expect(lateral(at.x, at.z)).toBeCloseTo(5.4, 1);
  });
});

describe("the ride's night and radio", () => {
  it("silences the forest around the rite and the watcher, and again before the overtake", () => {
    expect(taxiNightLevels(10).forest).toBe(1);
    for (const t of [28, 37.8, 47]) expect(taxiNightLevels(t).forest).toBe(0);
    expect(taxiNightLevels(55).forest).toBeGreaterThan(0.8);
    expect(taxiNightLevels(58).forest).toBe(0);
    expect(taxiNightLevels(70).forest).toBe(1);
  });

  it("surges the radio static only when something is near", () => {
    const quiet = taxiNightLevels(12).radio;
    expect(quiet).toBeLessThan(0.15);
    for (const pass of TAXI_PASSES.slice(1))
      expect(taxiNightLevels(taxiPassBeat(pass)).radio).toBeGreaterThan(0.7);
    expect(taxiNightLevels(37.8).radio).toBeGreaterThan(0.5);
  });

  it("lifts off the throttle on the crossing only", () => {
    const beat = taxiPassBeat(taxiPass("crossing"));
    expect(taxiThrottle(beat - 0.1)).toBe(1);
    expect(taxiThrottle(beat + 0.4)).toBeLessThan(0.7);
    expect(taxiThrottle(beat + 3.1)).toBe(1);
  });

  it("keeps the scares out of the spoken lines' first words", () => {
    // A beat lands mid-line at most, never on a line's opening second.
    for (const pass of TAXI_PASSES) {
      const beat = taxiPassBeat(pass);
      for (const line of TAXI_CONVERSATION) expect(beat < line.at || beat > line.at + 1).toBe(true);
    }
  });
});
