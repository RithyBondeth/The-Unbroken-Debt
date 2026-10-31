/** Development-only views of the actual game objects, with no writes to player saves. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { KANHA_LAYOUT, OFFERINGS, SLOTS } from "../../src/episodes/ep1/data/betel";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";

async function review(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU is required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  game.flags.set("ep1.arrival.road", true);
  game.flags.set("ep1.vigil.started", true);
  game.flags.set("ep1.betel.asked", true);
  // The review should stay in the quiet vigil and never write CP2.
  game.flags.set("ep1.act2.started", true);
  await game.start();
  const act = (window as unknown as { act: ActOne }).act;
  const use = (id: string) => game.bus.emit("interact:use", { id });
  const book = () => {
    game.stopInspecting();
    game.player.teleport(new Vector3(0, 0, -2), Math.PI);
    game.player.pitch = 0;
    game.sketchbook?.restore(["SB-01", "SB-02", "SB-03", "SB-03b"]);
    if (!game.sketchbook?.isOpen) game.sketchbook?.toggle();
    game.sketchbook?.goToSection("notes");
  };
  let arranged = false;
  document.getElementById("book")?.addEventListener("click", book);
  document.getElementById("turn")?.addEventListener("click", () => game.sketchbook?.turn(1));
  document.getElementById("tray")?.addEventListener("click", () => {
    if (game.sketchbook?.isOpen) game.sketchbook.toggle();
    game.player.teleport(new Vector3(0, 2.5, -20.25), Math.PI);
    game.player.pitch = 1.0;
    act.vigil.lamp.light();
    if (arranged) return use("interact_altar");
    arranged = true;
    // Populate the same interactive tray the player assembles in Act I.
    for (const id of [
      "interact_betel_tray",
      "interact_betel_leaves",
      "interact_areca_nut",
      "interact_lime_pot",
      "interact_altar_candle",
      "interact_incense_bundle",
    ])
      use(id);
    game.inventory.add("incense");
    use("interact_altar");
    const free = new Set<string>(OFFERINGS);
    for (const slot of SLOTS) {
      const available = OFFERINGS.filter((item) => free.has(item));
      for (let k = 0; k <= available.indexOf(KANHA_LAYOUT[slot]); k++) use(`betel_slot_${slot}`);
      free.delete(KANHA_LAYOUT[slot]);
    }
  });
  await new Promise<void>((resolve) => {
    const tick = () => {
      if (game.cutscene) requestAnimationFrame(tick);
      else resolve();
    };
    tick();
  });
  book();
}
void review().catch(console.error);
