import { afterEach, expect, it, vi } from "vitest";
import { NullEngine } from "@babylonjs/core/Engines/nullEngine";
import { Scene } from "@babylonjs/core/scene";
import { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { SavePoint } from "../../src/systems/saves/SavePoint";
import { EventBus } from "../../src/core/EventBus";
import type { GameEvents } from "../../src/core/events";
import type { Game } from "../../src/core/Game";

const engines: NullEngine[] = [];
afterEach(() => {
  for (const engine of engines.splice(0)) engine.dispose();
});
const flush = async () => {
  for (let k = 0; k < 10; k++) await Promise.resolve();
};
const setup = (save: () => Promise<unknown>) => {
  const engine = new NullEngine();
  engines.push(engine);
  const scene = new Scene(engine),
    bus = new EventBus<GameEvents>();
  const appearance = {
    root: new TransformNode("phra_phum", scene),
    hint: "hint.saveShrine" as const,
    interacting: false,
    saving: vi.fn(),
    settled: vi.fn(),
  };
  const state = {
    scene,
    bus,
    cutscene: false,
    threatActive: false,
    hints: { show: vi.fn() },
    interaction: { add: vi.fn() },
  };
  let available = true;
  new SavePoint(
    state as unknown as Game,
    "save",
    Vector3.Zero(),
    "COURTYARD",
    save,
    () => available,
    appearance,
  );
  return {
    state,
    bus,
    appearance,
    block: () => {
      available = false;
    },
    use: () => bus.emit("interact:use", { id: "save" }),
  };
};

it("uses the shrine's real geometry and affordance, and confirms only a completed write", async () => {
  let finish!: () => void;
  const save = vi.fn(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
  );
  const { state, appearance, bus, use } = setup(save);
  expect(state.interaction.add).toHaveBeenCalledWith("save", appearance.root, { outline: false });
  bus.emit("interact:focus", { id: "save" });
  expect(state.hints.show).toHaveBeenCalledWith("hint.saveShrine", 8);
  use();
  use();
  await flush();
  expect(save).toHaveBeenCalledTimes(1);
  expect(appearance.saving).toHaveBeenCalledTimes(1);
  expect(appearance.settled).not.toHaveBeenCalled();
  expect(state.hints.show).not.toHaveBeenCalledWith("note.checkpointSaved", 5);
  finish();
  await flush();
  expect(appearance.settled).toHaveBeenCalledWith(true);
  expect(state.hints.show).toHaveBeenCalledWith("note.checkpointSaved", 5);
});

it("blocks saving during danger, cutscenes and unavailable story states", async () => {
  const save = vi.fn().mockResolvedValue(undefined);
  const { state, appearance, block, use } = setup(save);
  state.threatActive = true;
  use();
  state.threatActive = false;
  state.cutscene = true;
  use();
  state.cutscene = false;
  block();
  use();
  await flush();
  expect(save).not.toHaveBeenCalled();
  expect(appearance.saving).not.toHaveBeenCalled();
});

it("does not restart a shrine performance or write again until its response ends", async () => {
  const save = vi.fn().mockResolvedValue(undefined);
  const { appearance, use } = setup(save);
  use();
  await flush();
  appearance.interacting = true;
  use();
  await flush();
  expect(save).toHaveBeenCalledTimes(1);
  appearance.interacting = false;
  use();
  await flush();
  expect(save).toHaveBeenCalledTimes(2);
});

it("reports storage failure without a success response and permits retry, including synchronous errors", async () => {
  const save = vi
    .fn<() => Promise<unknown>>()
    .mockRejectedValueOnce(new Error("quota"))
    .mockImplementationOnce(() => {
      throw new Error("unavailable");
    })
    .mockResolvedValueOnce(undefined);
  const { state, appearance, use } = setup(save);
  use();
  await flush();
  expect(appearance.settled).toHaveBeenLastCalledWith(false);
  expect(state.hints.show).toHaveBeenLastCalledWith("note.saveFailed", 8);
  use();
  await flush();
  expect(appearance.settled).toHaveBeenLastCalledWith(false);
  use();
  await flush();
  expect(save).toHaveBeenCalledTimes(3);
  expect(appearance.settled).toHaveBeenLastCalledWith(true);
  expect(state.hints.show).toHaveBeenLastCalledWith("note.checkpointSaved", 5);
});
