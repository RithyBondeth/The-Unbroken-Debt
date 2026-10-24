/** Real area / Havok / WebGPU verification, isolated from the player's IndexedDB. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import voiceManifest from "../../src/episodes/ep1/data/sokVoice.json";
import { SOK_RECORDING } from "../../src/episodes/ep1/data/investigation";

const output = document.getElementById("results")!;
const report = (text: string) => (output.textContent += `${text}\n`);
const assert = (value: unknown, text: string) => {
  if (!value) throw new Error(text);
  report(`PASS ${text}`);
};
const wait = async (test: () => boolean, timeout = 30000) => {
  const start = performance.now();
  while (!test()) {
    if (performance.now() - start > timeout) throw new Error("Timed out waiting for game state");
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
};

async function verify(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search);
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  const saves = new SaveStore(
    undefined,
    params.has("voice") ? "boon-sop-voice-verification" : "boon-sop-act2-verification",
  );
  Object.defineProperty(game, "saves", { value: saves });
  if (!params.has("continue")) {
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
    ])
      game.flags.set(flag, true);
    game.flags.set("ep1.clock", "01:00");
  }
  if (params.has("voice")) {
    for (const flag of [
      "ep1.journal.plankOpen",
      "ep1.journal.found",
      "ep1.gramophone.started",
      "ep1.gramophone.solved",
    ])
      game.flags.set(flag, true);
    game.flags.set("ep1.gramophone.rpm", 78);
    game.inventory.add("sok_journal");
  }
  report("Click to begin. Uses its own verification save database.");
  await game.start();
  const act = (window as unknown as { act: ActOne }).act;
  const investigation = act.investigation;
  const inputStatus = document.getElementById("input-status")!;
  window.addEventListener(
    "keydown",
    (event) => {
      inputStatus.textContent = `${event.code || event.key} · focus: ${game.interaction.focus ?? "none"} · active: ${game.interaction.active}`;
    },
    { capture: true },
  );
  const frame = () => new Promise((resolve) => setTimeout(resolve, 300));
  const closeBook = async () => {
    await wait(() => !game.sketchbook?.isBusy);
    if (game.sketchbook?.isOpen) game.sketchbook.toggle();
    await wait(() => !game.sketchbook?.isBusy && !game.gated.reading);
  };
  const viewJournal = async () => {
    await closeBook();
    const at = investigation.models.journal.position;
    // Keep the capsule in front of the desk, rather than teleporting into its collider.
    game.player.teleport(new Vector3(at.x + 1.45, 2.5, at.z + 0.7), -Math.PI / 2);
    await frame();
    game.inspectObject(at.add(new Vector3(0, -0.05, 0)));
    await frame();
  };
  const viewGramophone = async () => {
    await closeBook();
    const at = investigation.models.gramophone.position;
    game.player.teleport(new Vector3(at.x + 0.85, 2.5, at.z + 1.1), Math.PI);
    await frame();
    game.inspectObject(at.add(new Vector3(0, 1.05, 0.1)), 0.6);
    await frame();
  };
  document.getElementById("journal")!.onclick = () => void viewJournal();
  document.getElementById("gramophone")!.onclick = () => void viewGramophone();
  document.getElementById("results-toggle")!.onclick = () => (output.hidden = !output.hidden);
  const link = (phase: string, text: string) => {
    const a = document.createElement("a");
    a.href = `?continue&phase=${phase}`;
    a.textContent = text;
    a.style.cssText =
      "position:fixed;bottom:12px;left:12px;z-index:1001;background:#e4d6b9;color:#201b14;padding:12px";
    document.body.append(a);
  };
  await wait(() => !game.cutscene, 300000);
  act.vigil.lamp.light();
  assert(investigation.available, "Sok’s room investigation is accessible at CP2");
  assert(
    investigation.audio.language === voiceManifest.language,
    `selected ${voiceManifest.language} recording decoded without scratch fallback`,
  );
  assert(
    investigation.audio.durations.length === 4 &&
      investigation.audio.durations.every((duration) => duration > 0.5),
    "all four voice paragraphs have decoded subtitle timings",
  );
  if (params.has("visual")) {
    await viewGramophone();
    return;
  }
  const phase = params.has("voice") ? "tuned" : params.get("phase");
  if (!params.has("continue") && !params.has("voice")) {
    game.bus.emit("interact:use", { id: "interact_gramophone" });
    assert(!investigation.started, "record cannot bypass journal discovery");
    await viewJournal();
    assert(
      game.interaction.focus === "interact_sok_wall_plank",
      "wall board is reachable through the actual interaction ray",
    );
    game.interaction.use();
    await new Promise((resolve) => setTimeout(resolve, 1000));
    game.inspectObject(
      investigation.models.papers.getAbsolutePosition().add(new Vector3(0.01, -0.05, 0)),
    );
    await frame();
    assert(
      game.interaction.focus === "interact_sok_journal",
      "journal is reachable after the board moves",
    );
    game.interaction.use();
    assert(investigation.reader.open, "journal opens a readable translation");
    // Exercise the actual UI next/finish buttons, preserving normal read timing elsewhere.
    for (let i = 0; i < 3; i++)
      document
        .querySelector<HTMLButtonElement>(".document-reader footer button:nth-of-type(2)")!
        .click();
    await wait(() => investigation.started);
    assert(game.inventory.count("sok_journal") === 1, "journal collection is unique");
    await viewGramophone();
    for (let i = 0; i < 5; i++)
      window.dispatchEvent(new KeyboardEvent("keydown", { code: "ArrowRight" }));
    await wait(() => !game.saves.saving && game.flags.get<number>("ep1.gramophone.rpm", 0) === 69);
    await new Promise((resolve) => setTimeout(resolve, 800));
    const saved = (await saves.load("autosave")).save;
    assert(saved?.flags["ep1.gramophone.rpm"] === 69, "partial dial setting autosaves");
    assert(saved?.flags["ep1.journal.found"] === true, "journal discovery autosaves");
    report("PARTIAL SAVE PASSED");
    link("partial", "Reload partial investigation");
    return;
  }
  assert(game.flags.get("ep1.journal.found", false), "journal discovery restores");
  assert(investigation.models.plank.position.x < -0.3, "wall board stays open");
  assert(game.inventory.count("sok_journal") === 1, "journal is not duplicated");
  // The isolated voice preview seeds puzzle flags without replaying notebook discovery.
  if (!params.has("voice")) assert(game.sketchbook?.written.has("SB-04"), "pact entry restores");
  if (phase === "partial") {
    assert(
      investigation.governor.rpm === 69 && !investigation.governor.solved,
      "partial tuning restores unsolved",
    );
    await viewGramophone();
    for (let i = 0; i < 9; i++)
      window.dispatchEvent(new KeyboardEvent("keydown", { code: "ArrowRight" }));
    await wait(() => investigation.governor.solved);
    await wait(() => !game.saves.saving);
    assert(investigation.playingMessage, "correct sustained speed starts Sok’s recording");
    assert(
      !game.flags.get("ep1.gramophone.heard", false),
      "tuning alone does not prematurely finish the recording",
    );
    report("TUNED SAVE PASSED");
    link("tuned", "Reload before recording finishes");
    return;
  }
  assert(
    investigation.governor.solved && investigation.governor.rpm === 78,
    "solved speed restores",
  );
  if (phase === "tuned") {
    assert(!investigation.playingMessage, "interrupted recording waits for the player on reload");
    await viewGramophone();
    const subtitles = document.querySelector<HTMLElement>(".story-subtitles")!;
    const seen: string[] = [];
    const observer = new MutationObserver(() => {
      const text = subtitles.textContent ?? "";
      if (!subtitles.hidden && text.startsWith("Sok: ")) seen.push(text.slice(5).trim());
    });
    observer.observe(subtitles, { childList: true, subtree: true });
    game.bus.emit("interact:use", { id: "interact_gramophone" });
    await wait(() => game.flags.get("ep1.gramophone.heard", false), 150000);
    observer.disconnect();
    assert(
      seen.join(" ") === SOK_RECORDING.join(" "),
      "all four Khmer voice paragraphs retain the complete English subtitles",
    );
    await wait(() => !game.saves.saving);
    const saved = (await saves.load("autosave")).save;
    assert(saved?.flags["ep1.gramophone.heard"] === true, "completed warning autosaves");
    assert(
      String(saved?.flags["sketchbook.written"]).includes("SB-A2-05"),
      "desk-key objective persists before notebook animations finish",
    );
    report("RECORDING PASSED");
    if (!params.has("voice")) link("complete", "Reload completed investigation");
    return;
  }
  assert(game.flags.get("ep1.gramophone.heard", false), "completed recording restores");
  assert(game.sketchbook?.written.has("SB-A2-05"), "altar-base key clue restores");
  assert(!investigation.playingMessage, "completed warning does not autoplay again");
  report("INVESTIGATION RESTORE PASSED");
  await viewGramophone();
}
void verify().catch((error) => {
  report(`FAIL ${String(error)}`);
  console.error(error);
});
