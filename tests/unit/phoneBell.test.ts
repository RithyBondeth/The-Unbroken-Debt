import { describe, expect, it } from "vitest";
import { PhoneBell, RING_CYCLE } from "../../src/episodes/ep1/audio/PhoneBell";

const fakeSound = () => {
  const log: string[] = [];
  return { log, play: () => log.push("play"), stop: () => log.push("stop") };
};

describe("unanswered telephone", () => {
  it("rings in bursts with long quiet between them", () => {
    const sound = fakeSound();
    const bell = new PhoneBell(sound, 5, 35);
    bell.start();
    expect(sound.log).toEqual(["play"]);
    expect(bell.burst).toBeLessThan(5 * RING_CYCLE);
    for (let t = 0; t < bell.burst - 0.1; t += 0.1) bell.update(0.1);
    expect(sound.log).toEqual(["play"]);
    bell.update(0.2);
    expect(sound.log).toEqual(["play", "stop"]);
    for (let t = 0; t < 34.8; t += 0.1) bell.update(0.1);
    expect(sound.log).toEqual(["play", "stop"]);
    bell.update(0.3);
    expect(sound.log).toEqual(["play", "stop", "play"]);
  });
  it("falls silent for good once answered, even mid-quiet", () => {
    const sound = fakeSound();
    const bell = new PhoneBell(sound, 2, 10);
    bell.start();
    bell.start();
    bell.update(bell.burst + 0.1);
    bell.stop();
    expect(bell.active).toBe(false);
    bell.update(60);
    expect(sound.log).toEqual(["play", "stop"]);
  });
});
