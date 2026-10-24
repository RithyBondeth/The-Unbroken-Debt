import { expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { SokInvestigation } from "../../src/episodes/ep1/act2/SokInvestigation";
it("permits tuning a reachable record above its floor root, while preserving distance and book gates", () => {
  const state = {
    available: true,
    started: true,
    governor: { solved: false },
    game: {
      inspecting: true,
      cutscene: false,
      sketchbook: { isOpen: false, isBusy: false },
      camera: { globalPosition: new Vector3(0.85, 4.08, 1.1) },
    },
    models: { gramophone: { position: new Vector3(0, 2.5, 0) } },
  };
  expect(Reflect.get(SokInvestigation.prototype, "tuning", state)).toBe(true);
  state.game.sketchbook.isBusy = true;
  expect(Reflect.get(SokInvestigation.prototype, "tuning", state)).toBe(false);
  state.game.sketchbook.isBusy = false;
  state.game.camera.globalPosition.set(5, 4.08, 1.1);
  expect(Reflect.get(SokInvestigation.prototype, "tuning", state)).toBe(false);
});
