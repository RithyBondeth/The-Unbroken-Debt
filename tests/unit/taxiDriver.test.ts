import { expect, it } from "vitest";
import { taxiDriverBody, taxiDriverFace, taxiSoraBody } from "@/episodes/ep1/travel/taxiDriver";
import { TAXI_CONVERSATION } from "@/episodes/ep1/travel/taxiConversation";
import { TAXI_WINDOW, taxiPass, taxiPassBeat } from "@/episodes/ep1/travel/taxiApparitions";

it("moves his jaw only while he speaks, opening and closing on syllables", () => {
  for (const line of TAXI_CONVERSATION) {
    const samples: number[] = [];
    for (let t = line.at + 0.3; t < line.at + line.seconds - 0.4; t += 0.02)
      samples.push(taxiDriverFace(t).talk);
    if (line.speaker === "Driver") {
      expect(Math.max(...samples)).toBeGreaterThan(0.12);
      expect(Math.max(...samples)).toBeLessThan(0.3);
      expect(Math.min(...samples)).toBeLessThan(0.05);
    } else expect(Math.max(...samples)).toBe(0);
    expect(taxiDriverFace(line.at + line.seconds + 0.05).talk).toBeLessThan(0.01);
  }
});

it("glances round to Sora as he starts a line, then back to the road", () => {
  const line = TAXI_CONVERSATION.find((l) => l.speaker === "Driver" && l.seconds > 4)!;
  expect(taxiDriverFace(line.at + 0.8).look_sora).toBeGreaterThan(0.5);
  expect(taxiDriverFace(line.at + line.seconds - 0.6).look_sora).toBeLessThan(0.2);
});

it("watches the trees while Sora asks why, and snaps forward at the crossing", () => {
  expect(taxiDriverFace(30).look_road).toBeLessThan(0.15);
  expect(taxiDriverFace(12.5).look_road + taxiDriverFace(12.5).look_sora).toBeGreaterThan(0.6);
  expect(taxiDriverFace(taxiPassBeat(taxiPass("crossing")) + 0.3).look_road).toBeGreaterThan(0.6);
});

it("keeps every weight within 0–1 for the whole ride", () => {
  for (let t = 0; t <= 72; t += 0.05) {
    for (const value of Object.values(taxiDriverFace(t))) {
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThanOrEqual(1);
    }
    for (const value of Object.values(taxiDriverBody(t, Math.sin(t) * 0.25))) {
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThanOrEqual(1);
    }
    for (const value of Object.values(taxiSoraBody(t))) {
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThanOrEqual(1);
    }
  }
});

it("drives driver steering-wheel morphs with wheel angle and tenses Sora's hands on scares", () => {
  expect(taxiDriverBody(10, 0.25).steer_left).toBeGreaterThan(0.8);
  expect(taxiDriverBody(10, 0.25).steer_right).toBe(0);
  expect(taxiDriverBody(10, -0.25).steer_right).toBeGreaterThan(0.8);
  expect(taxiDriverBody(10, -0.25).steer_left).toBe(0);
  expect(taxiDriverBody(TAXI_WINDOW.beat + 0.15, 0).grip_tense).toBeGreaterThan(0.7);

  // Sora fidgets subtly while calm, and clenches her knees tightly on Beat 4b's window scare!
  expect(taxiSoraBody(7).fidget).toBeGreaterThan(0.4);
  expect(taxiSoraBody(7).tense_grip).toBeLessThan(0.2);
  expect(taxiSoraBody(TAXI_WINDOW.beat + 0.15).tense_grip).toBeGreaterThan(0.75);
  expect(taxiSoraBody(TAXI_WINDOW.beat + 0.15).fidget).toBe(0);
});
