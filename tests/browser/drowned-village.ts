/** Real production area, Havok, UI and interactions. Review saves never touch the player database. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { isQualityName } from "../../src/render/QualityPresets";
import type { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import { encodeSaveCode, decodeSaveCode } from "../../src/systems/saves/saveCode";
import { saveShot } from "../../src/debug/saveShot";
import { FUSE_IDS, LEAK_IDS, SAFE_CODE, VILLAGE } from "../../src/episodes/ep3/data/village";
import { VillageProgress } from "../../src/episodes/ep3/VillageProgress";
import { Flags } from "../../src/core/Flags";
import { Inventory } from "../../src/systems/inventory/Inventory";
import type { DrownedVillage } from "../../src/episodes/ep3/DrownedVillage";

const VIEWS: Record<string, [number[], number[]]> = {
  water: [
    [-68, 0.78, 11.8],
    [-75, 0.2, 15],
  ],
  market: [
    [-64, 0.78, 8],
    [-64, 2, -9],
  ],
  lok: [
    [-69, 0.78, 13],
    [-72, 1.9, 12],
  ],
  clinic: [
    [0, 0.74, 14],
    [0, 3, -1],
  ],
  ward: [
    [3.8, 0.08, 1.8],
    [5, 0.85, -1],
  ],
  attic: [
    [-6, 3.43, -3],
    [-6.3, 4, -8],
  ],
  vault: [
    [1, -1.52, -22],
    [0, -0.75, -25.5],
  ],
  kanha: [
    [-12, 3.43, 6.4],
    [-12.8, 4.7, 2.8],
  ],
  portrait: [
    [-12, 3.43, 4.5],
    [-13.05, 4.72, 2.7],
  ],
  ritual: [
    [-12, 3.43, 8],
    [-12.3, 4.15, 4.2],
  ],
  escape: [
    [-14, 3.9, -6],
    [-22, 5.9, -18],
  ],
  rescue: [
    [-22, 5.56, -18],
    [0, 3, 0],
  ],
};
const output = document.getElementById("results")!;
const log = (s: string) => {
  output.textContent += "\n" + s;
};
const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
async function wait(test: () => boolean, label: string, timeout = 30000): Promise<void> {
  const deadline = performance.now() + timeout;
  while (!test()) {
    if (performance.now() > deadline) throw new Error("Timeout: " + label);
    await sleep(50);
  }
}
function check(ok: boolean, label: string): void {
  if (!ok) throw new Error(label);
  log("PASS " + label);
}

async function boot(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const url = new URL(location.href);
  url.searchParams.set("start", "ep3");
  history.replaceState(null, "", url);
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const device = await detectDevice(),
    quality = url.searchParams.get("quality");
  if (isQualityName(quality)) device.quality = quality;
  // Independent review tabs must not clear each other's initialization save
  // during HMR or while the user explores another stage.
  const reviewKey = "ep3-review-session";
  const reviewSession = sessionStorage.getItem(reviewKey) ?? crypto.randomUUID();
  sessionStorage.setItem(reviewKey, reviewSession);
  const game = new Game(engine, device, `boon-sop-ep3-review-${reviewSession}`);
  const saves: SaveStore = game.saves;
  await saves.clear("autosave");
  await saves.clear("checkpoint");
  const save = newGameSave();
  save.episode = 3;
  save.inventory = { satchel: 1, sketchbook: 1, lamp: 1, matches: 12, oil: 3 };
  save.lamp = { oil: 1, state: "open" };
  save.flags = { "ep3.started": true, "ep3.preview": true };
  const stage = url.searchParams.get("stage") ?? "market";
  if (stage !== "market")
    Object.assign(save.flags, {
      "ep3.met.lok": true,
      "ep3.met.vuthy": true,
      "ep3.boat.borrowed": true,
      "ep3.docked": true,
    });
  if (stage !== "market") Object.assign(save.inventory, { clinic_supplies: 2, yellow_candle: 4 });
  if (["vault", "memory", "purification", "escape"].includes(stage))
    Object.assign(save.flags, {
      "ep3.pump.running": true,
      ...Object.fromEntries(FUSE_IDS.map((id) => ["ep3.fuse." + id, true])),
      ...Object.fromEntries(LEAK_IDS.map((id) => ["ep3.sealed." + id, true])),
    });
  if (["memory", "purification", "escape"].includes(stage))
    Object.assign(save.flags, { "ep3.safe.open": true, "ep3.jar.taken": true });
  if (["purification", "escape"].includes(stage))
    Object.assign(save.flags, { "ep3.memory.scraped": true, "ep3.memory.written": true });
  if (stage === "purification" && url.searchParams.get("candles") === "3")
    Object.assign(save.flags, {
      "ep3.ritual.water": true,
      "ep3.candle.0": true,
      "ep3.candle.1": true,
      "ep3.candle.2": true,
    });
  if (stage === "escape")
    Object.assign(save.flags, { "ep3.mother.freed": true, "ep3.seal3.broken": true });
  await saves.save("autosave", save);
  game.fade.waitForEnter = () => Promise.resolve();
  await game.start({ audio: url.searchParams.has("audio") });
  await wait(
    () => !!(window as unknown as { village?: DrownedVillage }).village?.active,
    "episode initialization",
    90000,
  );
  const act = (window as unknown as { village: DrownedVillage }).village;
  await wait(() => !game.cutscene, "begin");
  await game.fade.to(0, 0);
  game.hints.hide();
  game.subtitles.hide();
  const look = (name: string) => {
    current = name;
    const [from, to] = VIEWS[name],
      at = Vector3.FromArray(from),
      target = Vector3.FromArray(to);
    game.fallGuard.bounds = null;
    game.player.teleport(at, Math.atan2(target.x - at.x, target.z - at.z));
    game.player.pitch = Math.atan2(
      at.y + 1.58 - target.y,
      Math.hypot(target.x - at.x, target.z - at.z),
    );
    game.fallGuard.reset(at);
    game.input.clear();
    log("View: " + name);
  };
  let current =
    url.searchParams.get("view") ??
    (stage === "market"
      ? "market"
      : stage === "vault" || stage === "memory"
        ? "vault"
        : stage === "purification"
          ? "kanha"
          : "clinic");
  output.textContent = `Production Episode 3 · ${device.quality} · ${act.area.level.colliders.length} colliders · ${act.area.level.interactables.length} interactions\nIsolated review database; survival and threats pause without pointer capture.`;
  look(current);
  for (const button of document.querySelectorAll<HTMLButtonElement>("[data-view]"))
    button.onclick = () => look(button.dataset.view!);
  document.getElementById("capture")!.onclick = () => {
    void saveShot(engine, game.camera, "ep3-" + current).then(() => log("Saved ep3-" + current));
  };
  document.getElementById("clean")!.onclick = () => {
    document.getElementById("review")!.hidden = true;
    output.hidden = true;
  };
  document.getElementById("journey")!.onclick = () => {
    void journey(game, act).catch((e) => {
      log("FAIL " + String(e));
      console.error(e);
    });
  };
  document.getElementById("traversal")!.onclick = () => {
    void traversal(game, act).catch((e) => {
      log("FAIL " + String(e));
      console.error(e);
    });
  };
  if (url.searchParams.has("capture")) {
    await sleep(1800);
    await saveShot(engine, game.camera, "ep3-" + current);
    log("Saved ep3-" + current);
  }
  if (url.searchParams.has("run")) await journey(game, act);
}

async function journey(game: Game, act: DrownedVillage): Promise<void> {
  output.textContent =
    "Production story inputs + real saved payloads. Dialog choices scripted; physical routes are a separate check.";
  (document.getElementById("journey") as HTMLButtonElement).disabled = true;
  const originalShow = act.view.show.bind(act.view),
    originalFade = game.fade.show.bind(game.fade);
  // Explicit test inputs, including the safe's real dial actions; no production state gate is bypassed.
  act.view.show = (title, _paragraphs, buttons) => {
    // Hold credits after the archive write; do not navigate or download during a test.
    if (title === "The Unbroken Debt") return new Promise<number>(() => undefined);
    if (buttons.some((b) => b.startsWith("Turn dial"))) {
      const at = act.progress.dials.findIndex((v, i) => v !== SAFE_CODE[i]);
      return Promise.resolve(at < 0 ? 4 : at);
    }
    return Promise.resolve(0);
  };
  game.fade.show = () => Promise.resolve();
  const skip = setInterval(() => {
    for (const button of document.querySelectorAll<HTMLButtonElement>(
      ".cinematic-controls:not([hidden]) button",
    ))
      if (button.textContent === "Skip scene") button.click();
  }, 60);
  try {
    check(act.progress.stage === "market", "fresh market state");
    await act.use("interact_seller");
    await act.use("interact_vuthy");
    await act.use("interact_lok");
    await act.use("interact_boat");
    check(act.progress.stage === "crossing", "boat requires both conversations");
    // Test the actual alternating-oar listener and frame-driven arrival with controlled pointer ownership.
    Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => true });
    let stroke = 0;
    while (act.progress.stage === "crossing") {
      window.dispatchEvent(new KeyboardEvent("keydown", { code: stroke++ % 2 ? "KeyD" : "KeyA" }));
      await sleep(280);
      if (stroke > 45) throw new Error("Oar crossing did not dock");
    }
    await wait(() => !game.cutscene && !game.saves.saving, "landing checkpoint");
    delete (game.input as unknown as { pointerLocked?: boolean }).pointerLocked;
    check(act.progress.stage === "clinic", "alternating oars dock through production update");
    for (const id of LEAK_IDS) await act.use("interact_seal_" + id);
    for (const id of FUSE_IDS) await act.use("interact_fuse_" + id);
    await act.use("interact_note_admission");
    await act.use("interact_calendar_key");
    await act.use("interact_stove");
    await act.use("interact_generator");
    check(act.progress.stage === "vault", "both seals and all fuses power the pump");
    await act.use("interact_safe");
    check(game.flags.get("ep3.safe.open", false), "four Khmer dials open the safe");
    await act.use("interact_note_letter");
    await act.use("interact_jar");
    await act.use("interact_scrape");
    await act.use("interact_write");
    check(act.progress.stage === "purification", "playable memory preserves the renamed debt");
    await act.use("interact_purify");
    for (let i = 0; i < 3; i++) await act.use("interact_candle_" + i);
    await act.use("interact_mother_choice");
    check(
      act.progress.stage === "escape" && game.flags.get("ep3.mother.freed", false),
      "three candles and fourth light free Kanha and Pich",
    );
    const current = act.capture();
    check(
      (await decodeSaveCode(await encodeSaveCode(current))).flags["series.kanha.freed"] === true,
      "export and import keep the Episode 5 consequence",
    );
    const f = new Flags(),
      inventory = new Inventory();
    f.load(current.flags);
    inventory.load(current.inventory);
    const restored = new VillageProgress(f, inventory);
    check(
      restored.stage === "escape" && !restored.release(true),
      "reload cannot duplicate the respect reward",
    );
    const respect = game.flags.get("series.respect", 0);
    check(restored.escape() && restored.finish(), "rescue completes the episode");
    check(
      restored.inventory.count("brass_compass") === 1 &&
        restored.flags.get<number>("series.nextEpisode", 0) === 4,
      "compass, rubber clue and next episode persist",
    );
    check(
      game.flags.get("series.respect", 0) === respect,
      "continuation copy leaves live save intact",
    );
    void act.use("interact_rescue").catch((error) => {
      log("FAIL " + String(error));
    });
    await wait(
      () => act.progress.stage === "complete" && !game.saves.saving,
      "production rescue and completion archive",
    );
    const archived = (await game.saves.load("episode3")).save;
    check(
      archived?.episode === 3 &&
        archived.flags["ep3.complete"] === true &&
        archived.inventory.brass_compass === 1,
      "actual rescue writes the Episode 3 completion archive",
    );
    log("PASS EPISODE 3 STORY, ROWING, SAFE, MEMORY, CHOICE AND SAVE JOURNEY COMPLETE");
  } finally {
    clearInterval(skip);
    act.view.show = originalShow;
    game.fade.show = originalFade;
    delete (game.input as unknown as { pointerLocked?: boolean }).pointerLocked;
  }
}

async function traversal(game: Game, _act: DrownedVillage): Promise<void> {
  output.textContent =
    "Real Havok controller. Threat simulation paused. Each separate architectural route starts at its named footing.";
  (document.getElementById("traversal") as HTMLButtonElement).disabled = true;
  const read = game.input.readMove.bind(game.input);
  let moving = false;
  game.input.readMove = (out) => {
    out.x = 0;
    out.z = moving ? 1 : 0;
    out.hurry = false;
    out.crouch = false;
    return out;
  };
  const walk = async (name: string, from: number[], to: number[]) => {
    game.cutscene = true;
    game.gated.holdStill = false;
    const a = Vector3.FromArray(from),
      b = Vector3.FromArray(to);
    game.player.teleport(a, Math.atan2(b.x - a.x, b.z - a.z));
    game.fallGuard.reset(a);
    game.fallGuard.bounds = null;
    const deadline = performance.now() + Math.hypot(b.x - a.x, b.z - a.z) * 1300 + 5000;
    moving = true;
    try {
      while (Math.hypot(game.player.feet.x - b.x, game.player.feet.z - b.z) > 0.25) {
        if (performance.now() > deadline)
          throw new Error(name + " blocked at " + game.player.feet.toString());
        game.player.yaw = Math.atan2(b.x - game.player.feet.x, b.z - game.player.feet.z);
        await sleep(40);
      }
    } finally {
      moving = false;
    }
    await sleep(200);
    check(
      game.player.supported && Math.abs(game.player.feet.y - b.y) < 0.3,
      name + " · " + game.player.feet.toString(),
    );
  };
  try {
    await walk("Market main dock", [-64, 0.78, 8], [-64, 0.7, -7]);
    await walk("Pa Lok’s raft link", [-64, 0.78, 11], [-72, 0.7, 12]);
    await walk("Clinic landing slope", [0, 0.72, 13], [0, 0, 7.5]);
    await walk("West stair to attic", [-10, 0.08, 8], [-10, 3.35, -3.4]);
    await walk("Attic doorway to veranda", [-10, 3.43, -3.4], [-12, 3.35, -3.4]);
    await walk("Cellar descent", [7.7, 0.08, -10], [7.7, -1.6, -21]);
    for (let i = 0; i < VILLAGE.escape.length - 1; i++)
      await walk(
        "Roof bridge " + (i + 1),
        VILLAGE.escape[i].map((v, n) => (n === 1 ? v + 0.08 : v)),
        VILLAGE.escape[i + 1],
      );
    game.cutscene = false;
    const allow = game.interaction.allow;
    game.interaction.allow = () => true;
    try {
      for (const [id, from, to] of [
        ["interact_fuse_reception", [-5, 0.08, 6.1], [-5, 0.96, 5]],
        ["interact_generator", [7, 0.08, -6.6], [7, 0.9, -7.6]],
        ["interact_safe", [0, -1.52, -24.2], [0, -0.7, -25.4]],
        ["interact_purify", [-12, 3.43, 5.55], [-12, 3.37, 5]],
        ["interact_candle_0", [-12.45, 3.43, 5.1], [-12.45, 3.46, 4.5]],
        ["interact_mother_choice", [-12, 3.43, 4.4], [-12, 3.5, 3.8]],
      ] as [string, number[], number[]][]) {
        const a = Vector3.FromArray(from),
          b = Vector3.FromArray(to);
        game.player.teleport(a, Math.atan2(b.x - a.x, b.z - a.z));
        game.player.pitch = Math.atan2(a.y + 1.58 - b.y, Math.hypot(b.x - a.x, b.z - a.z));
        game.fallGuard.reset(a);
        await sleep(250);
        game.interaction.update();
        check(
          game.interaction.focus === id,
          "interaction ray: " + id + " (actual " + game.interaction.focus + ")",
        );
      }
    } finally {
      game.interaction.allow = allow;
    }
    log("PASS EPISODE 3 PHYSICAL TRAVERSAL AND INTERACTION REACH COMPLETE");
  } finally {
    moving = false;
    game.input.readMove = read;
    game.cutscene = false;
  }
}
void boot().catch((error) => {
  log("FAIL " + String(error));
  console.error(error);
});
