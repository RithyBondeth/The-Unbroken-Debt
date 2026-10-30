import { afterEach, describe, expect, it, vi } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { ForestUnease } from "../../src/episodes/ep1/act1/ForestUnease";
import { ForestAtmosphere } from "../../src/episodes/ep1/act1/ForestAtmosphere";
import {
  forestSource,
  FOREST_SOURCES,
  GROUND_MIST,
  inUneaseForest,
} from "../../src/episodes/ep1/data/forestAtmosphere";
import { mistDensityAt, MAX_MIST_POCKETS } from "../../src/render/mist";
import {
  canopyWind,
  foliageMovement,
  pavilionCloth,
} from "../../src/episodes/ep1/audio/atmosphereSounds";
import { seededRandom, rms } from "../../src/audio/synth";
import type { Game } from "../../src/core/Game";

const advance = (state: ForestUnease, seconds: number, allowed = true, looking = false) => {
  for (let i = 0; i < Math.ceil(seconds * 60); i++) state.update(1 / 60, allowed, looking);
};

describe("forest suspense pacing", () => {
  it("hushes before movement, stops on a turn, and restores ambience slowly", () => {
    const state = new ForestUnease(() => 0.5);
    state.scheduleSoon();
    advance(state, 2);
    expect(state.phase).toBe("hush");
    expect(state.silence).toBeGreaterThan(0.75);
    advance(state, 1.3);
    expect(state.phase).toBe("movement");
    state.update(1 / 60, true, true);
    expect(state.phase).toBe("listening");
    advance(state, 2);
    expect(state.silence).toBeGreaterThan(0.8);
    advance(state, 6);
    expect(state.phase).toBe("waiting");
    expect(state.silence).toBeLessThan(0.03);
    advance(state, 60);
    expect(state.phase).toBe("waiting");
  });

  it("never plays into a gaze already on the bush", () => {
    const state = new ForestUnease(() => 0.5);
    state.scheduleSoon();
    advance(state, 3.4, true, true);
    expect(state.phase).toBe("listening");
  });

  it("cancels on interruptions without queuing a scare for re-entry", () => {
    const state = new ForestUnease(() => 0.5);
    state.scheduleSoon();
    advance(state, 3.4);
    state.update(0.1, false, false);
    expect(state.phase).toBe("waiting");
    advance(state, 40);
    expect(state.phase).toBe("waiting");
    advance(state, 2, false);
    expect(state.silence).toBeLessThan(0.1);
  });

  it("does not advance a whole sequence after a background stall", () => {
    const state = new ForestUnease(() => 0.5);
    state.scheduleSoon();
    state.update(120, true, false);
    expect(state.phase).toBe("hush");
    expect(state.silence).toBeLessThan(0.2);
  });
});

describe("forest placement and ground mist", () => {
  it("chooses an off-screen world source at a plausible audible distance", () => {
    for (const [x, z] of [
      [0, 34],
      [-1, 53],
      [0, 13],
      [0, -27],
    ]) {
      const p = forestSource(x, z, 0, -1);
      expect(p).not.toBeNull();
      const dx = p![0] - x,
        dz = p![1] - z,
        distance = Math.hypot(dx, dz);
      expect(distance).toBeGreaterThanOrEqual(4);
      expect(distance).toBeLessThanOrEqual(13);
      expect(-dz / distance).toBeLessThan(0.15);
      expect(FOREST_SOURCES).toContain(p);
    }
    expect(forestSource(0, 0, 0, 0)).toBeNull();
  });

  it("keeps the pavilion, upper rooms and under-house hunt outside false-alarm zones", () => {
    expect(inUneaseForest(0, 0, 34)).toBe(true);
    expect(inUneaseForest(0, 0, -4)).toBe(false);
    expect(inUneaseForest(0, 2.5, -14)).toBe(false);
    expect(inUneaseForest(0, 0, -14)).toBe(false);
  });

  it("stays below eye level, fades at boundaries and leaves the path center thin", () => {
    expect(GROUND_MIST.length).toBeLessThanOrEqual(MAX_MIST_POCKETS);
    for (const p of GROUND_MIST) {
      expect(p.baseY + p.height).toBeLessThan(1);
      expect(mistDensityAt(p, p.x, p.baseY + 0.2, p.z)).toBeGreaterThan(0);
      expect(mistDensityAt(p, p.x, 1.3, p.z)).toBe(0);
      expect(mistDensityAt(p, p.x, p.baseY - 0.1, p.z)).toBe(0);
      expect(mistDensityAt(p, p.x + p.radiusX * 2, 0.2, p.z)).toBe(0);
    }
    const path = [
      [-2.5, 50],
      [-0.5, 40],
      [2.5, 30],
      [2, 20],
      [-0.5, 10],
    ];
    for (const [x, z] of path)
      expect(GROUND_MIST.reduce((sum, p) => sum + mistDensityAt(p, x, 0.3, z), 0)).toBeLessThan(
        0.08,
      );
  });
});

describe("atmosphere sound takes", () => {
  for (const make of [foliageMovement, canopyWind, pavilionCloth]) {
    it(`${make.name} stays finite, audible and below its peak ceiling`, () => {
      const take = make(16000, seededRandom(9));
      expect(take.every(Number.isFinite)).toBe(true);
      expect(rms(take)).toBeGreaterThan(0.01);
      let peak = 0,
        step = 0;
      for (let i = 0; i < take.length; i++) {
        peak = Math.max(peak, Math.abs(take[i]));
        if (i) step = Math.max(step, Math.abs(take[i] - take[i - 1]));
      }
      expect(peak).toBeLessThanOrEqual(0.600001);
      if (make === foliageMovement) {
        expect(take[0]).toBe(0);
        expect(take[take.length - 1]).toBe(0);
        expect(take).not.toEqual(make(16000, seededRandom(10)));
      } else expect(Math.abs(take[0] - take[take.length - 1])).toBeLessThanOrEqual(step);
    });
  }
});

describe("forest audio integration", () => {
  afterEach(() => vi.unstubAllGlobals());
  const rig = async () => {
    const doc = Object.assign(new EventTarget(), { hidden: false, querySelector: () => null });
    vi.stubGlobal("document", doc);
    const sounds: {
      play: ReturnType<typeof vi.fn>;
      stop: ReturnType<typeof vi.fn>;
      volume: number;
      spatial: { position: Vector3 };
    }[] = [];
    const direction = new Vector3(0, 0, -1);
    const game = {
      player: { feet: new Vector3(0, 0, 34) },
      camera: {
        globalPosition: new Vector3(0, 1.58, 34),
        getDirectionToRef: (_axis: Vector3, to: Vector3) => to.copyFrom(direction),
      },
      input: { pointerLocked: true },
      gated: {},
      notebook: { isOpen: false },
      satchel: { isOpen: false },
      subtitles: { active: false },
      flags: { get: () => true },
      scene: { onDisposeObservable: { add: vi.fn() } },
      audio: {
        context: { sampleRate: 16000 },
        buffer: (samples: Float32Array) => samples,
        spatialSound: vi.fn(() => {
          const sound = {
            play: vi.fn(),
            stop: vi.fn(),
            volume: 0,
            spatial: { position: Vector3.Zero() },
          };
          sounds.push(sound);
          return Promise.resolve(sound);
        }),
      },
    };
    const forest = new ForestAtmosphere(game as unknown as Game);
    await forest.makeSounds();
    forest.director.scheduleSoon();
    const tick = (seconds: number, protectedMoment = false) => {
      for (let i = 0; i < Math.ceil(seconds * 60); i++) forest.update(1 / 60, protectedMoment);
    };
    return { forest, game, direction, doc, sounds, tick };
  };

  it("uses a fixed bush, fades on turning, and resumes the natural bed", async () => {
    const r = await rig();
    r.tick(3.5);
    expect(r.sounds[0].play).toHaveBeenCalledOnce();
    const source = r.forest.source!.clone();
    r.direction.copyFrom(source.subtract(r.game.camera.globalPosition).normalize());
    r.tick(0.5);
    expect(r.forest.director.phase).toBe("listening");
    expect(r.sounds[0].stop).toHaveBeenCalledOnce();
    expect(r.sounds[0].spatial.position.equals(source)).toBe(true);
    r.forest.stop();
  });

  it("gives dialogue and encounters priority over the new cue", async () => {
    const r = await rig();
    r.game.subtitles.active = true;
    r.tick(5);
    expect(r.sounds.every((s) => s.play.mock.calls.length === 0)).toBe(true);
    r.game.subtitles.active = false;
    r.tick(3.5);
    expect(r.sounds[0].play).toHaveBeenCalledOnce();
    r.tick(0.5, true);
    expect(r.forest.director.phase).toBe("waiting");
    expect(r.sounds[0].stop).toHaveBeenCalledOnce();
    r.forest.stop();
  });

  it("stops immediately on tab hiding even when no more frames arrive", async () => {
    const r = await rig();
    r.tick(3.5);
    r.doc.hidden = true;
    r.doc.dispatchEvent(new Event("visibilitychange"));
    expect(r.sounds[0].stop).toHaveBeenCalledOnce();
    expect(r.forest.director.phase).toBe("waiting");
    r.doc.hidden = false;
    r.tick(2);
    expect(r.sounds[0].play).toHaveBeenCalledTimes(1);
    r.forest.stop();
  });
});
