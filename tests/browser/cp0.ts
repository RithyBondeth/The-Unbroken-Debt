import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
async function verify() {
  if (!import.meta.env.DEV) return;
  const output = document.getElementById("results")!;
  try {
    const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
    if (!engine) throw new Error("WebGPU required");
    useLocalDecoders();
    const game = new Game(engine, await detectDevice());
    const saves = new SaveStore(undefined, "boon-sop-cp0-verification");
    Object.defineProperty(game, "saves", { value: saves });
    await saves.save("autosave", newGameSave());
    await game.start();
    if (
      !game.scene.getMeshByName("interact_illustration") ||
      game.flags.get("ep1.act2.started", false) ||
      game.inventory.list().length
    )
      throw new Error("CP0 did not restore a fresh studio");
    output.textContent =
      "PASS CP0 loads the studio with an empty inventory, rather than the village.";
  } catch (error) {
    output.textContent = `FAIL ${String(error)}`;
  }
}
void verify();
