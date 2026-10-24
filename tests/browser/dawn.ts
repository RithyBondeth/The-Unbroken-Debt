import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { newGameSave } from "../../src/systems/saves/SaveData";
import { encodeSaveCode, decodeSaveCode } from "../../src/systems/saves/saveCode";
import { CHEST_ITEMS } from "../../src/episodes/ep1/act3/ChestProgress";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { saveShot } from "../../src/debug/saveShot";
const output = document.getElementById("results")!;
const report = (s: string) => (output.textContent += `${s}\n`);
const assert = (ok: unknown, s: string) => {
  if (!ok) throw new Error(s);
  report(`PASS ${s}`);
};
const pause = (ms = 100) => new Promise((done) => setTimeout(done, ms));
async function wait(test: () => boolean) {
  const start = performance.now();
  while (!test()) {
    if (performance.now() - start > 60000) throw new Error("Timed out");
    await pause();
  }
}
async function click(label: string) {
  await wait(() =>
    [...document.querySelectorAll<HTMLButtonElement>(".resolution button")].some(
      (b) => b.textContent === label && !b.disabled,
    ),
  );
  const button = [...document.querySelectorAll<HTMLButtonElement>(".resolution button")].find(
    (b) => b.textContent === label && !b.disabled,
  )!;
  button.click();
  await pause();
}
async function verify() {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search),
    which = params.get("case") ?? "entry",
    shared = params.get("choice") !== "keep";
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice()),
    saves = new SaveStore(undefined, `boon-sop-dawn-${shared ? "share" : "keep"}`);
  Object.defineProperty(game, "saves", { value: saves });
  if (which === "entry") {
    const save = newGameSave();
    save.checkpoint = "CP5";
    save.clock = "02:35";
    save.lamp = { oil: 1, state: "open" };
    save.inventory = {
      lamp: 1,
      brass_key: 1,
      satchel: 1,
      sketchbook: 1,
      matches: 20,
      blessed_matches: 3,
      incense: 2,
      sok_journal: 1,
      sok_journal_b: 1,
    };
    for (const flag of [
      "ep1.arrival.road",
      "ep1.arrival.courtyard",
      "ep1.vigil.started",
      "ep1.vuthy.left",
      "ep1.betel.asked",
      "ep1.betel.done",
      "ep1.act1.complete",
      "ep1.act2.started",
      "ep1.sok.unlocked",
      "ep1.journal.plankOpen",
      "ep1.journal.found",
      "ep1.gramophone.started",
      "ep1.gramophone.solved",
      "ep1.gramophone.heard",
      "ep1.walker.armed",
      "ep1.walker.complete",
      "ep1.altar.compartmentOpen",
      "ep1.desk.keyTaken",
      "ep1.desk.open",
      "ep1.journalB.read",
      "ep1.portrait.awake",
      "ep1.portrait.seen",
      "ep1.thread.broken",
      "ep1.act2.complete",
      "ep1.act3.started",
      "ep1.hunt.started",
      "ep1.brassKey.assembled",
      "ep1.fragments.3",
    ])
      save.flags[flag] = true;
    save.flags["ep1.coffin.triggered"] = true;
    save.flags["ep1.clock"] = "02:35";
    save.flags["ep1.checkpoint"] = "CP5";
    save.flags["ep1.incense.remaining"] = 0.75;
    save.flags["sketchbook.written"] =
      "SB-01,SB-04,SB-05,SB-A2-05,SB-A2-06,SB-06,SB-A2-07,SB-A3-01";
    await saves.save("autosave", save);
    for (const id of ["J2", "J4", "J6"]) {
      save.flags[`ep1.jar.${id}.open`] = true;
      save.flags[`ep1.jar.${id}.taken`] = true;
    }
    save.flags["ep1.chest.planksOpen"] = true;
    save.flags["ep1.chest.unlocked"] = true;
    save.flags["ep1.ritual.ready"] = true;
    save.flags["ep1.coffin.closed"] = true;
    save.flags["sketchbook.written"] += ",SB-07,SB-CHEST-MAP,SB-CHEST-SLIP";
    delete save.inventory.brass_key;
    for (const item of CHEST_ITEMS) {
      save.flags[`ep1.chest.${item}.taken`] = true;
      save.inventory[item] = 1;
    }
    save.flags["ep1.slip.unread"] = true;
    save.flags["ep1.seal1.broken"] = true;
    save.flags["ep1.ritual.tokenPlaced"] = true;
    save.flags["ep1.resolution.started"] = true;
    save.flags["ep1.resolution.stage"] = "dawn";
    save.flags["ep1.betel.firstTry"] = true;
    save.flags["series.respect"] = 1;
    save.flags["lore.ep1.L2"] = true;
    save.checkpoint = "CP6";
    save.flags["ep1.checkpoint"] = "CP6";
    delete save.inventory.bronze_token;
    await saves.save("autosave", save);
  }
  report("Click to begin. Dawn verification uses isolated saves.");
  await game.start();
  const act = (window as unknown as { act: ActOne }).act;
  await wait(() => act.resolution.active);
  const flags = game.flags;
  if (which === "entry") {
    await click("Wait for Vuthy");
    await click(shared ? "Show him the journal" : "Keep the journal");
    await wait(() => flags.has("ep1.journal.shared") && !saves.saving);
    assert(flags.get("ep1.journal.shared", !shared) === shared, "journal choice committed");
    assert(!flags.get("ep1.slip.read", false), "slip reveal has not happened early");
    const a = document.createElement("a");
    a.href = `?continue&case=choice-reload&choice=${shared ? "share" : "keep"}`;
    a.textContent = "Reload journal choice";
    a.style.cssText =
      "position:fixed;bottom:10px;left:10px;z-index:3000;background:white;padding:15px";
    document.body.append(a);
    return;
  }
  assert(
    flags.get("ep1.journal.shared", !shared) === shared,
    "saved choice restored without asking again",
  );
  if (which !== "complete") {
    await click("Let him return to Grandmother");
    await click("Unfold the map");
    assert(flags.get("ep1.slip.read", false), "fourth name revealed");
    await click("Close the map");
    assert(
      flags.get<number>("series.night", 0) === 3 && flags.get("ep1.map.pagoda", false),
      "pagoda and night 3 saved",
    );
    // One transient write failure must expose an explicit retry, with no duplicate reward.
    const original = saves.save.bind(saves);
    let failed = false;
    saves.save = async (slot, data) => {
      if (!failed && data.flags["ep1.complete"]) {
        failed = true;
        throw new Error("simulated quota failure");
      }
      return original(slot, data);
    };
    await click("Open the sketchbook");
    await click("Retry save");
    await click("View credits");
    assert(failed, "completion save failure recovered through retry");
  }
  await wait(() => flags.get("ep1.complete", false) && !saves.saving);
  const completed = (await saves.load("episode1")).save;
  assert(completed?.flags["ep1.complete"] === true, "separate Episode 1 completion slot exists");
  assert(completed?.flags["series.nextEpisode"] === 2, "Episode 2 handoff is marked");
  assert(flags.get<number>("series.respect", 0) === 3, "respect awarded exactly once");
  assert(
    completed?.inventory.seal_map === 1 && completed.inventory.folded_slip === 1,
    "story inventory preserved",
  );
  const decoded = await decodeSaveCode(await encodeSaveCode(completed!));
  assert(
    decoded.flags["ep1.journal.shared"] === shared,
    "portable completion save keeps journal branch",
  );
  await click("Episode summary");
  await click("View credits");
  assert(flags.get<number>("series.respect", 0) === 3, "revisiting summary cannot award again");
  report("DAWN → CHOICE → RELOAD → REVEALS → SAVE RETRY → SUMMARY → CREDITS PASSED");
  const a = document.createElement("a");
  a.href = `?continue&case=complete&choice=${shared ? "share" : "keep"}`;
  a.textContent = "Reload completed episode";
  a.style.cssText =
    "position:fixed;bottom:10px;left:10px;z-index:3000;background:white;padding:15px";
  document.body.append(a);
  await saveShot(engine, game.camera, `dawn_complete_${shared ? "share" : "keep"}`);
}
void verify().catch((error) => report(`FAIL ${String(error)}`));
