/** Physical route with live hearing/catches. Only the initial CP1 spawn is teleported. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import type { WhisperingPagoda } from "../../src/episodes/ep2/WhisperingPagoda";
const output = document.getElementById("results")!;
const log = (s: string) => {
  output.textContent += "\n" + s;
};
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
async function wait(test: () => boolean, label: string, timeout = 30000): Promise<void> {
  const until = performance.now() + timeout;
  while (!test()) {
    if (performance.now() > until) throw new Error(label);
    await sleep(50);
  }
}
async function boot(): Promise<void> {
  if (!import.meta.env.DEV) return;
  history.replaceState(null, "", "?start=ep2");
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  const saves = new SaveStore(undefined, "boon-sop-ep2-balance");
  Object.defineProperty(game, "saves", { value: saves });
  await saves.clear("autosave");
  await saves.clear("checkpoint");
  const save = newGameSave();
  save.episode = 2;
  save.flags = { "ep2.started": true, "ep2.monk.met": true, "ep2.preview": true };
  save.inventory = {
    satchel: 1,
    sketchbook: 1,
    lamp: 1,
    matches: 10,
    oil: 2,
    blessed_thread: 1,
    clay_bowl: 4,
  };
  save.lamp = { oil: 1, state: "open" };
  await saves.save("autosave", save);
  game.fade.waitForEnter = () => Promise.resolve();
  await game.start({ audio: false });
  await wait(() => !!(window as unknown as { pagoda?: WhisperingPagoda }).pagoda?.active, "start");
  const act = (window as unknown as { pagoda: WhisperingPagoda }).pagoda;
  await wait(() => !game.cutscene, "begin");
  const button = document.getElementById("run") as HTMLButtonElement;
  button.disabled = false;
  button.onclick = () => {
    button.disabled = true;
    void run(game, act).catch((e) => {
      log("FAIL " + String(e));
      console.error(e);
    });
  };
  log(
    "Ready. Real controller, step sounds, live AI and catches. No ghost changes or invulnerability.",
  );
}
async function run(game: Game, act: WhisperingPagoda): Promise<void> {
  const started = performance.now();
  let caught = false,
    moving = false,
    crouch = false,
    hold = false;
  const read = game.input.readMove.bind(game.input),
    held = game.input.isHeld.bind(game.input);
  Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => true });
  game.input.readMove = (out) => {
    out.x = 0;
    out.z = moving ? 1 : 0;
    out.crouch = crouch;
    out.hurry = false;
    return out;
  };
  game.input.isHeld = (code) => (code === "Space" ? hold : held(code));
  game.bus.on("player:caught", () => {
    caught = true;
  });
  game.retryFromCheckpoint = () => {
    caught = true;
    moving = false;
    return Promise.resolve();
  };
  game.player.teleport(new Vector3(-18, 0.22, 14), 0);
  game.fallGuard.reset(game.player.feet);
  const idle = () => wait(() => !game.cutscene && !game.saves.saving, "interaction completion");
  const walk = async (x: number, z: number, quiet = false) => {
    crouch = quiet;
    const distance = Math.hypot(x - game.player.feet.x, z - game.player.feet.z);
    const deadline = performance.now() + (distance / (quiet ? 0.85 : 1.5)) * 1400 + 5000;
    moving = true;
    while (Math.hypot(x - game.player.feet.x, z - game.player.feet.z) > 0.22) {
      if (caught) throw new Error("Caught at " + game.player.feet.toString());
      if (performance.now() > deadline)
        throw new Error("Blocked toward " + x + "," + z + " at " + game.player.feet.toString());
      game.player.yaw = Math.atan2(x - game.player.feet.x, z - game.player.feet.z);
      hold = quiet && act.breath.remaining > 2;
      await sleep(40);
    }
    moving = false;
    hold = false;
    log(
      "Walked " +
        x +
        "," +
        z +
        " · closest Pret " +
        Math.min(
          ...act.ghosts
            .slice(0, act.progress.pretCount)
            .map((g) => Math.hypot(g.position.x - x, g.position.z - z)),
        ).toFixed(1) +
        "m",
    );
  };
  const use = async (id: string, label?: string) => {
    if (caught) throw new Error("Caught before " + id);
    game.bus.emit("interact:use", { id: "interact_" + id });
    if (label) {
      await wait(
        () =>
          [
            ...document.querySelectorAll<HTMLButtonElement>(".resolution:not([hidden]) button"),
          ].some((b) => b.textContent === label),
        "offering reader",
      );
      [...document.querySelectorAll<HTMLButtonElement>(".resolution:not([hidden]) button")]
        .find((b) => b.textContent === label)!
        .click();
    }
    await idle();
    log("Used " + id);
  };
  const throwBowl = async (yaw: number) => {
    game.player.yaw = yaw;
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "KeyG" }));
    await sleep(100);
    await idle();
  };
  try {
    await walk(-18, 17);
    await walk(-14, 17);
    await throwBowl(Math.PI / 2);
    await walk(-14, 7, true);
    await walk(-16, 7);
    await use("pickup_rice");
    await walk(-14, 7);
    await walk(-14, -7);
    await walk(-16, -7);
    await use("pickup_lotus");
    await walk(-14, -7);
    await walk(-14, -16.8);
    await walk(16.5, -16.8);
    await walk(16, -16.8);
    await walk(16, -9);
    await use("pickup_water");
    await walk(16, 6.9);
    await walk(17.3, 6.9);
    await walk(17.3, 8);
    await use("pickup_bowls");
    await walk(14, 8.9);
    await throwBowl(Math.PI);
    await walk(14, 4.75);
    await walk(12, 4.75, true);
    await use("stupa_wife", "Offer a lotus bud");
    await walk(14, 4.75, true);
    await walk(16.5, 4.75);
    await walk(16.5, -9.25);
    await throwBowl(0);
    await walk(14, -9.25);
    await walk(12, -9.25, true);
    await use("stupa_kanha", "Offer rice balls");
    await walk(14, -9.25, true);
    await walk(16.5, -16.8);
    await walk(-18, -16.8);
    await walk(-18, -5.8);
    await throwBowl(0);
    await walk(-14, -5.8);
    await walk(-12, -5.8, true);
    await use("stupa_chhun", "Offer sanctified water");
    await walk(-14, -5.8, true);
    await walk(-14, 8.25);
    await throwBowl(Math.PI);
    await walk(-12, 8.25, true);
    await use("stupa_chea", "Offer rice balls");
    await walk(-14, 8.25, true);
    await walk(-14, 17);
    await walk(-18, 17);
    await walk(-18, 14);
    if (caught || act.progress.offerings !== 4 || act.progress.pretCount !== 5)
      throw new Error("Final garden state");
    log(
      "PASS LIVE STEALTH ROUTE · four offerings, five Pret, no catches · " +
        ((performance.now() - started) / 1000).toFixed(0) +
        "s · bowls remaining " +
        game.inventory.count("clay_bowl"),
    );
  } finally {
    moving = false;
    hold = false;
    game.input.readMove = read;
    game.input.isHeld = held;
    Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => false });
  }
}
void boot().catch((e) => {
  log("FAIL " + String(e));
  console.error(e);
});
