import { afterEach, describe, expect, it, vi } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { Game } from "@/core/Game";
import type { Vigil } from "@/episodes/ep1/act1/Vigil";
import type { VillageAudio } from "@/episodes/ep1/audio/VillageAudio";

vi.mock("@/episodes/ep1/entities/KrasueFlyer", () => ({
  KrasueFlyer: class {
    ready = true;
    meshes = [];
    redness = 0;
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
      textContent: "",
    }),
  });
  vi.stubGlobal("document", doc);

  const humSound = {
    play: vi.fn(),
    stop: vi.fn(),
    dispose: vi.fn(),
    volume: 0,
    spatial: { position: Vector3.Zero() },
  };
  const villageAudio = {
    play: vi.fn(),
    createSpatialLoop: vi.fn(() => Promise.resolve(humSound)),
  };

  const lamp = {
    state: "open" as "open" | "closed" | "out",
    burning: true,
    putOut: vi.fn(() => {
      lamp.state = "out";
      lamp.burning = false;
    }),
  };

  const eye = new Vector3(28, 1.58, 36);
  const game = {
    camera: {
      globalPosition: eye,
      // Look east (+X) directly toward waypoint 0 (38, 3.6, 36)
      getDirectionToRef: (_axis: Vector3, to: Vector3) => to.set(1, 0.1, 0).normalize(),
    },
    player: { feet: new Vector3(28, 0, 36) },
    input: { pointerLocked: true },
    flags: { get: () => false },
    atmosphere: { scare: vi.fn() },
    subtitles: { say: vi.fn(() => Promise.resolve()) },
    scene: { onDisposeObservable: { addOnce: vi.fn() } },
    cutscene: false,
    threatActive: false,
  };

  const encounter = new KrasueEncounter(
    game as unknown as Game,
    { lamp } as unknown as Vigil,
    villageAudio as unknown as VillageAudio,
  );
  await encounter.makeSounds();

  const tick = (seconds: number) => {
    for (let i = 0; i < Math.ceil(seconds * 60); i++) encounter.update(1 / 60);
  };

  return { encounter, game, lamp, villageAudio, humSound, doc, tick };
}

describe("Rice-Field KrasueEncounter integration", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("activates hum over the paddies, alerts on open lamp, and snuffs lamp on a close pass", async () => {
    const r = await rig();
    r.encounter.summon(0);
    r.tick(0.2);
    expect(r.humSound.play).toHaveBeenCalled();

    // Keep open lamp shining toward Krasue until blood-red alert
    r.tick(2.4);
    expect(r.encounter.brain.state).toBe("alert");
    expect(r.encounter.model.redness).toBeGreaterThan(0.5);
    expect(r.villageAudio.play).toHaveBeenCalledWith(
      "krasueAlert",
      expect.any(Vector3),
      expect.any(Number),
      expect.any(Number),
    );

    // Ignore warning -> approaching -> close fly-by pass blows out Sora's lamp
    r.tick(6.5);
    expect(r.encounter.brain.passes).toBe(1);
    expect(r.lamp.putOut).toHaveBeenCalled();
    expect(r.game.atmosphere.scare).toHaveBeenCalled();
    r.encounter.stop();
  });

  it("silences spatial hum immediately when tab is hidden", async () => {
    const r = await rig();
    r.encounter.summon(0);
    r.tick(0.2);
    expect(r.humSound.play).toHaveBeenCalled();

    r.doc.hidden = true;
    r.doc.dispatchEvent(new Event("visibilitychange"));
    expect(r.humSound.stop).toHaveBeenCalled();
    r.encounter.stop();
  });
});
