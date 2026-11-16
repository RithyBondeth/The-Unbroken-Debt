import { describe, expect, it } from "vitest";
import {
  TAXI_PASSES,
  TAXI_MIRROR,
  TAXI_STANDER,
  TAXI_WINDOW,
  taxiMirrorRiderAt,
  taxiElectrics,
  taxiMistLevel,
  taxiSpiritAt,
  taxiLightning,
  SPIRIT_WALK_SPEED,
  taxiPass,
  taxiFlinch,
  taxiPassBeat,
  taxiSwerve,
} from "@/episodes/ep1/travel/taxiApparitions";
import { taxiNightLevels, taxiThrottle } from "@/episodes/ep1/travel/TaxiSoundscape";
import { taxiDistance, taxiRoadX } from "@/episodes/ep1/travel/taxiMotion";
import { TAXI_CONVERSATION } from "@/episodes/ep1/travel/taxiConversation";

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

describe("the Neak Ta's two passes", () => {
  it("runs two passes that never overlap", () => {
    expect(TAXI_PASSES.map((p) => p.kind)).toEqual(["crossing", "overtake"]);
    for (const [a, b] of TAXI_PASSES.slice(0, -1).map((p, i) => [p, TAXI_PASSES[i + 1]] as const))
      expect(a.start + a.seconds).toBeLessThan(b.start);
    for (const pass of TAXI_PASSES) {
      // Every pass finishes before the car starts to brake at the drop-off.
      expect(pass.start + pass.seconds).toBeLessThan(62);
    }
  });

  it("drags itself across the road ahead at a person's pace, and is gone when the lamps come back", () => {
    const pass = taxiPass("crossing"),
      beat = taxiPassBeat(pass);
    const start = taxiSpiritAt(pass.start + 0.001)!,
      level = taxiSpiritAt(beat)!,
      end = taxiSpiritAt(pass.start + pass.seconds - 0.001)!;
    expect(start.kind).toBe("crossing");
    expect(start.clip).toBe("walk");
    // From the left of the track towards Sora's side, no faster than the performer walked.
    expect(lateral(start.x, start.z)).toBeLessThan(-0.5);
    expect(lateral(end.x, end.z)).toBeGreaterThan(lateral(start.x, start.z));
    const covered = Math.hypot(end.x - start.x, end.z - start.z);
    expect(covered / pass.seconds).toBeLessThanOrEqual(SPIRIT_WALK_SPEED + 0.01);
    // In the lamps, nine metres off the bonnet, when the lightning shows it.
    const ahead = level.z - taxiDistance(beat);
    expect(ahead).toBeGreaterThan(6);
    expect(ahead).toBeLessThan(12);
    expect(taxiLightning(beat)).toBeCloseTo(1, 5);
    // The lamps blink as he brakes; when they come back, nothing.
    expect(taxiElectrics(beat + 0.5)).toBe(0);
    expect(taxiSpiritAt(beat + 0.7)).toBeNull();
  });

  it("is caught by four flickers in the trees on Sora's side, nearer each time, then at her glass", () => {
    const pass = taxiPass("overtake"),
      beat = taxiPassBeat(pass);
    const seen: { t: number; lateral: number; ahead: number }[] = [];
    for (let t = pass.start - 0.1; t <= pass.start + pass.seconds; t += 0.005) {
      const pose = taxiSpiritAt(t);
      if (!pose?.visible) continue;
      expect(taxiLightning(t)).toBeGreaterThan(0);
      const last = seen.at(-1);
      if (!last || t - last.t > 0.05)
        seen.push({ t, lateral: lateral(pose.x, pose.z), ahead: pose.z - taxiDistance(t) });
      else last.t = t;
    }
    expect(seen.length).toBe(4);
    for (let i = 1; i < 4; i++) expect(seen[i].lateral).toBeLessThan(seen[i - 1].lateral);
    expect(seen[0].lateral).toBeGreaterThan(5.5);
    // The last flicker is the slap: at the glass, level with her window, reaching.
    const slap = taxiSpiritAt(beat)!;
    expect(slap.visible).toBe(true);
    expect(slap.clip).toBe("reach");
    expect(Math.abs(slap.z - taxiDistance(beat))).toBeLessThan(1);
    expect(lateral(slap.x, slap.z)).toBeGreaterThan(1.1);
    expect(lateral(slap.x, slap.z)).toBeLessThan(1.9);
    // Never seen between the flickers.
    expect(taxiSpiritAt(seen[0].t + 0.03)!.visible).toBe(false);
    expect(taxiSpiritAt(pass.start + pass.seconds + 0.01)).toBeNull();
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
});

describe("what the road shows besides the passes", () => {
  it("stands among the first trunks on Sora's side, only breathing and turning its head", () => {
    expect(taxiSpiritAt(TAXI_STANDER.from - 0.1)).toBeNull();
    const far = taxiSpiritAt(TAXI_STANDER.from + 1)!,
      near = taxiSpiritAt(TAXI_STANDER.level)!;
    expect(far.kind).toBe("stander");
    expect(far.clip).toBe("stand");
    // It never moves from its place beyond the track's edge.
    expect([far.x, far.z]).toEqual([near.x, near.z]);
    expect(lateral(near.x, near.z)).toBeGreaterThan(4.2);
    expect(near.z - taxiDistance(TAXI_STANDER.level)).toBeCloseTo(0, 1);
    // Its head comes round to follow the car.
    expect(near.look).toBeGreaterThan(far.look);
    expect(taxiSpiritAt(TAXI_STANDER.until + 0.1)).toBeNull();
  });

  it("runs level with Sora's window in the dark after the slap, before the car brakes", () => {
    const slap = taxiPassBeat(taxiPass("overtake"));
    expect(TAXI_WINDOW.start).toBeGreaterThan(slap + 1.5);
    expect(TAXI_WINDOW.end).toBeLessThan(62);
    for (const t of [TAXI_WINDOW.start + 0.01, TAXI_WINDOW.beat, TAXI_WINDOW.end - 0.01]) {
      const pose = taxiSpiritAt(t)!;
      expect(pose.kind).toBe("window");
      expect(Math.abs(pose.z - taxiDistance(t))).toBeLessThan(0.6);
      // Outside the door (the body is about 0.85 m from the centreline), within reach of the glass.
      expect(lateral(pose.x, pose.z)).toBeGreaterThan(1.1);
      expect(lateral(pose.x, pose.z)).toBeLessThan(1.9);
    }
    expect(taxiSpiritAt(TAXI_WINDOW.end + 0.05)).toBeNull();
    for (const line of TAXI_CONVERSATION)
      expect(TAXI_WINDOW.beat < line.at || TAXI_WINDOW.beat > line.at + 1).toBe(true);
  });

  it("kills the lamps just before the crossing and the face, and nowhere else", () => {
    const cross = taxiPassBeat(taxiPass("crossing"));
    for (const t of [5, 20, 30, 45, 57.9, 65, 71]) expect(taxiElectrics(t)).toBe(1);
    expect(taxiElectrics(cross - 0.3)).toBe(0);
    // Back on as the lightning shows it in the road.
    expect(taxiElectrics(cross)).toBe(1);
    expect(taxiElectrics(TAXI_WINDOW.beat)).toBe(0);
    expect(taxiElectrics(TAXI_WINDOW.beat + 1.05)).toBe(1);
  });

  it("thickens the haze only a little round each of them, never into a wall", () => {
    expect(taxiMistLevel(5)).toBeCloseTo(1, 1);
    expect(taxiMistLevel(36)).toBeGreaterThan(1.15);
    expect(taxiMistLevel(59.5)).toBeGreaterThan(1.1);
    for (let t = 0; t <= 72; t += 0.5) expect(taxiMistLevel(t)).toBeLessThan(1.3);
  });
});

describe("the back seat in the rear-view mirror", () => {
  it("sits behind Sora while the driver warns her, and leans in after she says nobody is there", () => {
    expect(taxiMirrorRiderAt(TAXI_MIRROR.seated.from - 0.05)).toBeNull();
    const seated = taxiMirrorRiderAt((TAXI_MIRROR.seated.from + TAXI_MIRROR.seated.to) / 2)!;
    expect(seated.kind).toBe("seated");
    // Behind her seat (she sits at x 0.39, z -0.24), on the rear bench.
    expect(seated.x).toBeGreaterThan(0.1);
    expect(seated.z).toBeLessThan(-1);
    const nobody = TAXI_CONVERSATION.find((line) => line.text.startsWith("There's nobody"))!;
    expect(TAXI_MIRROR.seated.to).toBeLessThan(nobody.at);
    expect(TAXI_MIRROR.lean.from).toBeGreaterThanOrEqual(nobody.at + nobody.seconds - 0.1);
    const lean = taxiMirrorRiderAt(TAXI_MIRROR.lean.beat)!;
    expect(lean.kind).toBe("lean");
    // Closer to her than it sat, and still behind the front seats.
    expect(lean.z).toBeGreaterThan(seated.z + 0.4);
    expect(lean.z).toBeLessThan(-0.5);
    expect(taxiMirrorRiderAt(TAXI_MIRROR.lean.to + 0.05)).toBeNull();
  });

  it("stays clear of the runners, the face at the window and the driver's lines", () => {
    for (const beat of [TAXI_MIRROR.seated.from, TAXI_MIRROR.lean.beat]) {
      for (const pass of TAXI_PASSES)
        expect(Math.abs(beat - taxiPassBeat(pass))).toBeGreaterThan(3);
      expect(Math.abs(beat - TAXI_WINDOW.beat)).toBeGreaterThan(3);
    }
    for (const line of TAXI_CONVERSATION.filter((l) => l.speaker === "Driver"))
      expect(
        TAXI_MIRROR.lean.beat < line.at || TAXI_MIRROR.lean.beat > line.at + line.seconds,
      ).toBe(true);
  });

  it("dims the dash as it leans in", () => {
    expect(taxiElectrics(TAXI_MIRROR.lean.beat + 0.1)).toBeLessThan(0.5);
    expect(taxiElectrics(TAXI_MIRROR.lean.beat + 0.6)).toBe(1);
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
