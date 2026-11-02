import { describe, expect, it, vi } from "vitest";
import { EntryAmbience, WHISPER_SECONDS } from "../../src/audio/EntryAmbience";
import { BED_SECONDS, entryBed, entryBreath, entryThud } from "../../src/audio/entryDread";

function audioFixture() {
  const param = () => ({
    value: 0,
    cancelScheduledValues: vi.fn(),
    setValueAtTime: vi.fn(),
    setTargetAtTime: vi.fn(),
    linearRampToValueAtTime: vi.fn(),
  });
  const node = () => ({
    gain: param(),
    pan: param(),
    connect: vi.fn((target: unknown) => target),
    start: vi.fn(),
    stop: vi.fn(),
    loop: false,
  });
  const context = {
    state: "suspended",
    currentTime: 3,
    sampleRate: 8000,
    destination: {},
    createGain: vi.fn(node),
    createStereoPanner: vi.fn(node),
    createBufferSource: vi.fn(node),
    createBuffer: vi.fn((_channels: number, length: number, rate: number) => ({
      duration: length / rate,
      getChannelData: () => new Float32Array(length),
    })),
    resume: vi.fn(() => Promise.resolve()),
    close: vi.fn(() => Promise.resolve()),
  };
  return { context, factory: vi.fn(() => context as unknown as AudioContext) };
}

describe("listening screen sound", () => {
  it("stays silent without an earlier gesture, or with sound off", () => {
    const { factory } = audioFixture();
    new EntryAmbience(undefined, factory, () => false).start(true);
    new EntryAmbience(undefined, factory, () => true).start(false);
    expect(factory).not.toHaveBeenCalled();
  });

  it("loops the bed, sends whispers across the head and cuts off on Enter", () => {
    vi.useFakeTimers();
    const { context, factory } = audioFixture();
    const whispers: number[] = [];
    const sound = new EntryAmbience(
      (s) => whispers.push(s),
      factory,
      () => true,
    );
    sound.start(true);
    expect(sound.started).toBe(true);
    const bed = context.createBufferSource.mock.results[0].value as { loop: boolean };
    expect(bed.loop).toBe(true);
    vi.advanceTimersByTime(2300);
    expect(whispers).toEqual([WHISPER_SECONDS]);
    const panner = context.createStereoPanner.mock.results[0].value as ReturnType<
      typeof context.createStereoPanner
    >;
    expect(panner.pan.setValueAtTime.mock.calls[0][0]).toBe(-1);
    expect(panner.pan.linearRampToValueAtTime.mock.calls[0][0]).toBe(1);
    sound.enter();
    vi.advanceTimersByTime(2400);
    expect(sound.started).toBe(false);
    expect(context.close).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("synthesises a finite, seamless bed and a breath and thud that fade out", () => {
    const rate = 8000;
    const [left, right] = entryBed(rate);
    expect(left.length).toBe(BED_SECONDS * rate);
    expect(left.every(Number.isFinite) && right.every(Number.isFinite)).toBe(true);
    expect(Math.abs(left[left.length - 1] - left[0])).toBeLessThan(0.05);
    for (const part of [entryBreath(rate), entryThud(rate)]) {
      expect(part.every(Number.isFinite)).toBe(true);
      expect(Math.abs(part[part.length - 1])).toBeLessThan(0.02);
    }
  });
});
