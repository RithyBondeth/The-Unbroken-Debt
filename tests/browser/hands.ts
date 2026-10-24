import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { saveShot } from "../../src/debug/saveShot";
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
const wait = async (test: () => boolean) => {
  const start = performance.now();
  while (!test()) {
    if (performance.now() - start > 120000) throw new Error("Timed out");
    await pause(100);
  }
};
async function run() {
  if (!import.meta.env.DEV) throw new Error("Development only");
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-hands-verification"),
  });
  const say = game.subtitles.say.bind(game.subtitles);
  game.subtitles.say = (speaker, text, seconds) => say(speaker, text, seconds * 0.05);
  report("Click to begin");
  await game.start();
  const act = (window as unknown as { act: ActOne }).act;
  await wait(() => game.flags.get("ep1.arrival.road", false) && !game.cutscene);
  await pause(3200);
  const heldLamp = game.scene.getTransformNodeByName("held_lamp")!;
  const pressF = () => window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyF" }));
  check(
    !heldLamp.isEnabled() && !game.hands.left.isEnabled(),
    "unlit lamp and carrying hand start stowed",
  );
  await saveShot(engine, game.camera, "sora_lamp_stowed");
  const count = game.inventory.count("matches");
  pressF();
  await pause(300);
  check(game.hands.right.isEnabled(), "ordinary match strike animates right hand");
  check(
    heldLamp.isEnabled() && game.hands.left.isEnabled(),
    "F brings out the lamp while lighting",
  );
  await saveShot(engine, game.camera, "sora_hands_strike");
  await wait(() => act.vigil.lamp.burning);
  await pause(700);
  check(game.inventory.count("matches") === count - 1, "F consumes exactly one match");
  await saveShot(engine, game.camera, "sora_hands_lamp");
  check(game.hands.leftRig.grip === "lamp", "lamp uses a closed handle grip");
  Reflect.set(act.vigil, "raising", true);
  await pause(600);
  await saveShot(engine, game.camera, "sora_hands_lamp_raised");
  Reflect.set(act.vigil, "raising", false);
  pressF();
  await wait(() => !heldLamp.isEnabled() && !game.hands.left.isEnabled());
  check(!act.vigil.lamp.burning, "F extinguishes and stows the lamp");
  // An empty matchbox must not bring out an unlit lamp or consume blessed matches.
  game.inventory.remove("matches", count - 1);
  pressF();
  await pause(100);
  check(
    !heldLamp.isEnabled() && !game.hands.left.isEnabled(),
    "failed lighting leaves lamp stowed",
  );
  game.inventory.add("matches", count - 1);
  pressF();
  await wait(() => act.vigil.lamp.burning && heldLamp.isEnabled());
  await pause(700);
  game.hiding = true;
  await pause(100);
  check(!game.hands.left.isEnabled() && !game.hands.right.isEnabled(), "hiding stows both hands");
  game.hiding = false;
  game.bus.emit("interact:use", { id: "interact_arrival_phone" });
  await pause(550);
  check(
    game.cutscene && game.hands.right.isEnabled(),
    "phone hand remains visible during the call",
  );
  check(
    !game.scene.getTransformNodeByName("arrival_receiver")!.isEnabled(),
    "world receiver is replaced by the held receiver",
  );
  check(game.hands.rightRig.grip === "phone", "receiver uses its own finger wrap");
  await saveShot(engine, game.camera, "sora_hands_phone");
  await wait(() => game.flags.get("ep1.arrival.callComplete", false) && !game.cutscene);
  await wait(() => act.betel.pendingEntries.length === 0 && !game.sketchbook?.isBusy);
  if (!game.sketchbook?.isOpen) game.sketchbook?.toggle();
  await pause(1100);
  check(
    game.hands.left.isEnabled() && game.hands.right.isEnabled(),
    "both hands support the sketchbook",
  );
  check(
    game.hands.leftRig.grip === "journal" && game.hands.rightRig.grip === "journal",
    "journal uses two supporting grips",
  );
  await saveShot(engine, game.camera, "sora_hands_book");
  game.sketchbook?.close();
  // Wait for rendered state: a background browser can advance less than one
  // second of animation during a one-second wall-clock pause.
  await wait(() => !game.sketchbook?.isBusy && !game.hands.right.isEnabled());
  check(
    game.hands.left.isEnabled() && !game.hands.right.isEnabled(),
    "closing book restores lamp grip",
  );
  report("HANDS VERIFICATION PASSED");
}
void run().catch((e: unknown) => {
  report(`FAIL ${String(e)}`);
  console.error(e);
});
