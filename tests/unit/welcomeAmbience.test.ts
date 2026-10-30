import { afterEach, describe, expect, it, vi } from "vitest";
import { welcomeTheme } from "../../src/audio/welcomeTheme";
import { WelcomeAmbience } from "../../src/audio/WelcomeAmbience";
import { STINGER_HIT, funeralChant, stinger, whisperBed } from "../../src/audio/welcomeDread";

type FakeNode = ReturnType<typeof audioFixture>["nodes"][number];

function audioFixture() {
  const param = () => ({
    value: 0,
    cancelScheduledValues: vi.fn(),
    setValueAtTime: vi.fn(),
    setTargetAtTime: vi.fn(),
    linearRampToValueAtTime: vi.fn(),
  });
  const makeNode = () => ({
    gain: param(),
    frequency: param(),
    Q: param(),
    connect: vi.fn((target: unknown) => target),
    start: vi.fn(),
    stop: vi.fn(),
  });
  const nodes: ReturnType<typeof makeNode>[] = [];
  function node() {
    const result = makeNode();
    nodes.push(result);
    return result;
  }
  const context = {
    state: "suspended",
    currentTime: 10,
    sampleRate: 8000,
    destination: {},
    createGain: vi.fn(node),
    createBiquadFilter: vi.fn(node),
    createBufferSource: vi.fn(node),
    createOscillator: vi.fn(node),
    createBuffer: vi.fn((_channels: number, length: number) => ({
      getChannelData: () => new Float32Array(length),
    })),
    resume: vi.fn((): Promise<void> => {
      context.state = "running";
      return Promise.resolve();
    }),
    close: vi.fn((): Promise<void> => {
      context.state = "closed";
      return Promise.resolve();
    }),
  };
  const factory = vi.fn(() => context as unknown as AudioContext);
  return { context, factory, nodes };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("welcome ambience lifecycle", () => {
  it("creates no audio before a gesture, or while sound is disabled", async () => {
    const { factory } = audioFixture();
    const sound = new WelcomeAmbience(false, factory);
    expect(factory).not.toHaveBeenCalled();
    expect(await sound.unlock()).toBe(false);
    sound.setEnabled(true);
    expect(await sound.unlock()).toBe(true);
    await sound.unlock();
    expect(factory).toHaveBeenCalledTimes(1);
    sound.dispose();
  });

  it("mutes on hiding and on the sound toggle, and fades back in", async () => {
    const { context, factory } = audioFixture();
    const sound = new WelcomeAmbience(true, factory);
    await sound.unlock();
    const master = (context.createGain.mock.results[0].value as FakeNode).gain;
    sound.setVisible(false);
    expect(master.setValueAtTime).toHaveBeenLastCalledWith(0, 10);
    sound.setVisible(true);
    expect(master.setTargetAtTime).toHaveBeenLastCalledWith(0.32, 10, 0.8);
    sound.setEnabled(false);
    expect(master.setValueAtTime).toHaveBeenLastCalledWith(0, 10);
    sound.dispose();
  });

  it("fades, stops every source and closes its context exactly once", async () => {
    vi.useFakeTimers();
    const { context, factory, nodes } = audioFixture();
    const sound = new WelcomeAmbience(true, factory);
    await sound.unlock();
    sound.dispose();
    sound.dispose();
    expect(sound.started).toBe(false);
    expect(await sound.unlock()).toBe(false);
    const sources = nodes.filter((node) => node.start.mock.calls.length);
    expect(sources).toHaveLength(8);
    for (const source of sources) expect(source.stop).toHaveBeenCalledExactlyOnceWith(10.24);
    expect(context.close).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(300);
    expect(context.close).toHaveBeenCalledTimes(1);
    expect(factory).toHaveBeenCalledTimes(1);
  });

  it("plays stingers only once unlocked and stops them on disposal", async () => {
    const { factory, nodes } = audioFixture();
    const sound = new WelcomeAmbience(true, factory);
    sound.cue("near");
    expect(factory).not.toHaveBeenCalled();
    await sound.unlock();
    const before = nodes.length;
    sound.cue("near");
    sound.cue("appear");
    const cues = nodes.slice(before).filter((node) => node.start.mock.calls.length);
    expect(cues).toHaveLength(2);
    sound.setEnabled(false);
    sound.cue("vanish");
    expect(nodes.slice(before).filter((node) => node.start.mock.calls.length)).toHaveLength(2);
    sound.dispose();
    for (const cue of cues) expect(cue.stop).toHaveBeenCalledExactlyOnceWith(10.24);
  });

  it("cannot restart after disposal while the browser is resuming audio", async () => {
    vi.useFakeTimers();
    const { context, factory } = audioFixture();
    let finish!: () => void;
    context.resume.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    const sound = new WelcomeAmbience(true, factory);
    const pending = sound.unlock();
    sound.dispose();
    finish();
    expect(await pending).toBe(false);
    await vi.advanceTimersByTimeAsync(300);
    expect(context.close).toHaveBeenCalledTimes(1);
  });

  it("tolerates browsers denying audio", async () => {
    const sound = new WelcomeAmbience(true, () => {
      throw new Error("Audio unavailable");
    });
    expect(await sound.unlock()).toBe(false);
    expect(sound.started).toBe(false);
    sound.dispose();
  });
});

it("keeps the original title motif quiet, finite and silent at the loop boundary", () => {
  const data = welcomeTheme(8000);
  let peak = 0,
    energy = 0,
    finite = true;
  for (const value of data) {
    finite &&= Number.isFinite(value);
    peak = Math.max(peak, Math.abs(value));
    energy += value * value;
  }
  expect(finite).toBe(true);
  expect(peak).toBeLessThan(0.14);
  expect(Math.sqrt(energy / data.length)).toBeGreaterThan(0.005);
  expect(data[0]).toBe(0);
  expect(data[data.length - 1]).toBe(0);
});

function stats(data: Float32Array) {
  let peak = 0,
    finite = true;
  for (const value of data) {
    finite &&= Number.isFinite(value);
    peak = Math.max(peak, Math.abs(value));
  }
  return { peak, finite };
}

it("keeps the chant and whisper beds quiet, finite and click-free at the loop", () => {
  for (const [left, right] of [funeralChant(8000), whisperBed(8000)]) {
    expect(left.length).toBe(right.length);
    for (const side of [left, right]) {
      const { peak, finite } = stats(side);
      expect(finite).toBe(true);
      expect(peak).toBeLessThanOrEqual(0.3001);
      expect(peak).toBeGreaterThan(0.05);
      // The loop seam is no bigger a step than the bed's own movement.
      expect(Math.abs(side[side.length - 1] - side[0])).toBeLessThan(0.08);
    }
  }
});

it("lands every stinger on its hit and fades it out", () => {
  const rate = 8000;
  for (const kind of ["appear", "near", "vanish"] as const) {
    const [left, right] = stinger(rate, kind);
    const { peak, finite } = stats(left);
    expect(finite).toBe(true);
    expect(Math.max(peak, stats(right).peak)).toBeLessThanOrEqual(0.951);
    const hit = Math.round(STINGER_HIT * rate);
    const energy = (from: number, to: number) => {
      let sum = 0;
      for (let i = from; i < to; i++) sum += left[i] * left[i];
      return sum / (to - from);
    };
    // The 100 ms after the hit are much louder than the start of the swell.
    expect(energy(hit, hit + 800)).toBeGreaterThan(energy(hit - 5600, hit - 4800) * 4);
    expect(Math.abs(left[left.length - 1])).toBe(0);
    expect(Math.abs(right[right.length - 1])).toBe(0);
  }
});
