import { afterEach, describe, expect, it, vi } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "@/core/Game";
import type { Vigil } from "@/episodes/ep1/act1/Vigil";

vi.mock("@/shared/entities/KrasueModel", () => ({
  KrasueModel: class {
    ready = true;
    root = { setEnabled: vi.fn() };
    pose = vi.fn();
  },
}));
import { KrasueEncounter } from "@/episodes/ep1/entities/KrasueEncounter";

async function rig() {
  const doc = Object.assign(new EventTarget(), {
    hidden: false,
    body: { append: vi.fn() },
    createElement: () => ({
      setAttribute: vi.fn(),
      replaceChildren: vi.fn(),
      remove: vi.fn(),
      hidden: true,
      className: "",
    }),
  });
  vi.stubGlobal("document", doc);
  const sounds: {
    name: string;
    play: ReturnType<typeof vi.fn>;
    stop: ReturnType<typeof vi.fn>;
    volume: number;
    spatial: { position: Vector3 };
  }[] = [];
  const game = {
    camera: {
      globalPosition: new Vector3(4.8, 4.08, -13),
      getDirectionToRef: (_axis: Vector3, to: Vector3) => to.set(1, 0, 0),
    },
    input: { pointerLocked: true },
    gated: {},
    flags: { get: () => false },
    satchel: { close: vi.fn() },
    sketchbook: { close: vi.fn() },
    stopInspecting: vi.fn(),
    bus: { emit: vi.fn() },
    scene: { onDisposeObservable: { addOnce: vi.fn() } },
    audio: {
      context: { sampleRate: 16000 },
      buffer: (samples: Float32Array) => samples,
      spatialSound: vi.fn((name: string) => {
        const sound = {
          name,
          play: vi.fn(),
          stop: vi.fn(),
          volume: 0,
          spatial: { position: Vector3.Zero() },
        };
        sounds.push(sound);
        return Promise.resolve(sound);
      }),
    },
    cutscene: false,
    threatActive: false,
  };
  const encounter = new KrasueEncounter(
    game as unknown as Game,
    { lamp: { state: "closed" } } as unknown as Vigil,
    vi.fn(),
  );
  let seen = true;
  vi.spyOn(encounter, "canSeePlayer").mockImplementation(() => seen);
  await encounter.makeSounds();
  const tick = (seconds: number) => {
    for (let i = 0; i < Math.ceil(seconds * 60); i++) encounter.update(1 / 60);
  };
  /** Sora keeps to the side of the window until it has swooped in and stopped. */
  const arrive = () => {
    const was = seen;
    seen = false;
    for (let i = 0; i < 60 * 30 && encounter.brain.state !== "patrol"; i++)
      encounter.update(1 / 60);
    seen = was;
    expect(encounter.brain.state).toBe("patrol");
  };
  return {
    encounter,
    game,
    sounds,
    doc,
    tick,
    arrive,
    see: (value: boolean) => {
      seen = value;
    },
  };
}

describe("Krasue scream and rush integration", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("stays hidden and silent far away until Sora lingers, then stings as it swoops in", async () => {
    const r = await rig();
    const sting = r.sounds.find((s) => s.name === "krasue_sting")!;
    const root = r.encounter.model.root as unknown as { setEnabled: ReturnType<typeof vi.fn> };
    const enable = root.setEnabled;
    r.tick(1);
    expect(r.encounter.brain.hidden).toBe(true);
    expect(enable.mock.lastCall?.[0]).toBe(false);
    expect(sting.play).not.toHaveBeenCalled();
    r.arrive();
    expect(sting.play).toHaveBeenCalledOnce();
    expect(enable.mock.lastCall?.[0]).toBe(true);
    r.encounter.stop();
  });
  it("screams once on detection, before moving, with no duplicate at the rush", async () => {
    const r = await rig();
    const scream = r.sounds.find((s) => s.name === "krasue_shriek")!;
    const pose = vi.spyOn(r.encounter.model, "pose");
    r.arrive();
    r.tick(0.2);
    expect(scream.play).not.toHaveBeenCalled();
    r.tick(0.1);
    expect(r.encounter.brain.state).toBe("watching");
    expect(scream.play).toHaveBeenCalledOnce();
    expect(pose.mock.lastCall?.[6]).toBeLessThan(0.03);
    r.tick(0.1);
    expect(pose.mock.lastCall?.[6]).toBeGreaterThan(0.09);
    expect(Vector3.Distance(scream.spatial.position, r.encounter.brain.position)).toBeLessThan(
      0.001,
    );
    r.tick(0.4);
    expect(r.encounter.brain.state).toBe("charging");
    expect(scream.play).toHaveBeenCalledOnce();
    r.see(false);
    r.tick(0.3);
    expect(r.encounter.brain.state).toBe("searching");
    expect(scream.play).toHaveBeenCalledOnce();
    r.see(true);
    r.tick(0.05);
    expect(r.encounter.brain.state).toBe("charging");
    expect(scream.play).toHaveBeenCalledOnce();
    r.encounter.stop();
  });
  it("allows a new scream after escape and rearming, while tab hiding stops audio", async () => {
    const r = await rig();
    const scream = r.sounds.find((s) => s.name === "krasue_shriek")!;
    r.arrive();
    r.tick(0.3);
    r.see(false);
    r.tick(8);
    expect(r.encounter.brain.state).toBe("away");
    r.arrive();
    r.see(true);
    r.tick(0.3);
    expect(scream.play).toHaveBeenCalledTimes(2);
    r.doc.hidden = true;
    r.doc.dispatchEvent(new Event("visibilitychange"));
    expect(scream.stop).toHaveBeenCalled();
    expect(r.sounds.every((s) => s.stop.mock.calls.length > 0)).toBe(true);
    r.encounter.stop();
  });
});
