import { afterEach, describe, expect, it, vi } from "vitest";
import { WelcomeAmbience } from "../../src/audio/WelcomeAmbience";

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
    expect(sources).toHaveLength(5);
    for (const source of sources) expect(source.stop).toHaveBeenCalledExactlyOnceWith(10.24);
    expect(context.close).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(300);
    expect(context.close).toHaveBeenCalledTimes(1);
    expect(factory).toHaveBeenCalledTimes(1);
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
