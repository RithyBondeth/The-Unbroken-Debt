/** Real village interaction rays and interrupted-call reloads in an isolated save database. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";

const results = document.getElementById("results")!;
const report = (text: string) => {
  results.textContent += `\n${text}`;
};
const check = (value: unknown, text: string) => {
  if (!value) throw new Error(text);
  report(`PASS ${text}`);
};
const pause = (ms: number) => new Promise((r) => setTimeout(r, ms));
const wait = async (fn: () => boolean) => {
  const start = performance.now();
  while (!fn()) {
    if (performance.now() - start > 60000) throw new Error("Timed out");
    await pause(100);
  }
};
async function run() {
  if (!import.meta.env.DEV) throw new Error("Development only");
  const stage = new URLSearchParams(location.search).get("stage") ?? "note";
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  const saves = new SaveStore(undefined, "boon-sop-phone-arrival-verification");
  Object.defineProperty(game, "saves", { value: saves });
  const say = game.subtitles.say.bind(game.subtitles);
  game.subtitles.say = (speaker, text, seconds) => say(speaker, text, seconds * 0.08);
  report(`STAGE ${stage}; click to begin`);
  await game.start();
  const act = (window as unknown as { act: ActOne }).act;
  await wait(() => game.flags.get("ep1.arrival.road", false) && !game.cutscene);
  async function ray(id: string, feet: Vector3, at: Vector3) {
    await wait(() => !game.sketchbook?.isBusy);
    game.sketchbook?.close();
    await wait(() => !game.gated.reading);
    game.player.teleport(feet);
    await pause(350);
    game.inspectObject(at, 0.4);
    await pause(500);
    check(
      game.interaction.focus === id,
      `${id} reachable by interaction ray (${game.interaction.focus})`,
    );
    game.interaction.use();
  }
  async function next(stage: string) {
    await act.beats.saveProgress();
    await wait(() => !saves.saving);
    report(`RELOAD → ${stage}`);
    location.replace(`?continue&stage=${stage}`);
  }
  const phone = () =>
    ray("interact_arrival_phone", new Vector3(1.8, 2.5, -17.2), new Vector3(2.65, 3.7, -17.2));
  if (stage === "note") {
    check(!game.flags.get("ep1.vigil.started", false), "empty arrival does not start the vigil");
    await ray("interact_arrival_note", new Vector3(2.7, 0, -1.85), new Vector3(2.7, 0.79, -2.6));
    check(
      !!document.querySelector(".document-reader:not([hidden])"),
      "instructions open as a readable note",
    );
    document
      .querySelector<HTMLButtonElement>(".document-reader:not([hidden]) footer button:last-child")!
      .click();
    await next("interrupt");
  } else if (stage === "interrupt") {
    check(
      game.flags.get("ep1.arrival.noteRead", false) && !act.beats.arrival.called,
      "note reload retains an unanswered phone",
    );
    await phone();
    await pause(200);
    check(
      game.cutscene && !act.beats.arrival.called,
      "call in progress is not committed as complete",
    );
    await next("replay");
  } else if (stage === "replay") {
    check(
      !act.beats.arrival.called && !game.cutscene,
      "interrupted call releases controls and can restart",
    );
    await phone();
    await wait(() => act.beats.arrival.called && !game.cutscene);
    check(
      game.flags.get("ep1.betel.asked", false) && game.flags.get("ep1.vigil.started", false),
      "complete call gives offering request and starts vigil",
    );
    check(
      game.inventory.count("blessed_matches") === 0,
      "call does not manufacture blessed matches",
    );
    await next("pickup");
  } else if (stage === "pickup") {
    check(act.beats.arrival.called, "completed call remains complete after reload");
    for (const id of [
      "interact_betel_tray",
      "interact_betel_leaves",
      "interact_areca_nut",
      "interact_lime_pot",
      "interact_altar_candle",
      "interact_incense_bundle",
    ])
      game.bus.emit("interact:use", { id });
    game.bus.emit("interact:use", { id: "interact_altar" });
    game.bus.emit("interact:use", { id: "betel_slot_left" });
    check(game.inventory.count("betel") === 0, "partial offering consumes its placed leaf");
    await ray(
      "interact_blessed_matches",
      new Vector3(-0.65, 2.5, -16.6),
      new Vector3(-0.65, 3.614, -17.5),
    );
    game.bus.emit("interact:use", { id: "interact_blessed_matches" });
    check(
      game.inventory.count("blessed_matches") === 3,
      "physical matchbox grants exactly three matches once",
    );
    await next("spent");
  } else if (stage === "spent") {
    check(
      game.inventory.count("blessed_matches") === 3 && act.beats.arrival.taken,
      "reload preserves match inventory and collection state",
    );
    check(
      !game.scene.getTransformNodeByName("arrival_blessed_matches")!.isEnabled(),
      "collected matchbox remains hidden",
    );
    check(
      game.flags.get<string>("ep1.betel.slot.left", "") === "betel",
      "partial offering position survives matchbox autosave",
    );
    game.bus.emit("interact:use", { id: "betel_slot_left" });
    check(
      game.inventory.count("betel") === 1,
      "restored slot returns its original ingredient when cycled",
    );
    game.inventory.remove("blessed_matches", 3);
    await next("verify");
  } else {
    game.bus.emit("interact:use", { id: "interact_blessed_matches" });
    check(game.inventory.count("blessed_matches") === 0, "reload does not replenish spent matches");
    check(
      act.beats.arrival.called && game.flags.get("ep1.vuthy.left", false),
      "relatives remain away after reload",
    );
    check(
      game.sketchbook?.written.has("SB-02") && game.sketchbook.written.has("SB-03"),
      "phone duties and offering notes survive immediate reload",
    );
    report("PHONE ARRIVAL RELOADS PASSED");
  }
}
void run().catch((error: unknown) => {
  report(`FAIL ${String(error)}`);
  console.error(error);
});
