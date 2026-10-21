import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { KeyboardMouseInput } from "../../player/InputSource";
import { PlayerController } from "../../player/PlayerController";
import { PerfOverlay } from "../../debug/PerfOverlay";
import { getPreset, isQualityName, type QualityName } from "../../render/QualityPresets";
import type { DeviceProfile } from "../../render/DeviceProfile";
import { Flags } from "../../core/Flags";
import { newGameSave, SaveError, type SaveData } from "../../systems/saves/SaveData";
import { decodeSaveCode, encodeSaveCode } from "../../systems/saves/saveCode";
import { SaveStore } from "../../systems/saves/SaveStore";
import { endOfEpisodeOne } from "../../systems/saves/sampleSaves";
import { SpikeHud } from "../SpikeHud";
import { createHallEnvironment } from "../hallEnvironment";
import { runRenderLoop } from "../../render/renderLoop";
import { renderStallNotice } from "../../ui/html/RenderStallNotice";

/** Results exposed for automated checks (`window.spikeResult`). */
export interface S6Result {
  saveMs: number[];
  codeLength?: number;
  steps: string[];
}

/** The spike's own database, so it never touches real saves. */
const DATABASE = "boon-sop-spike-s6";
const RELOAD_MARK = "s6.reloadTest";
const MAX_SAVE_MS = 20;

/** The pieces of game state a save holds, live. */
class GameState {
  readonly flags = new Flags();
  inventory: Record<string, number> = {};
  lamp: SaveData["lamp"] = { oil: 1, state: "out" };
  checkpoint = "CP0";
  clock = "20:00";
  playTimeSec = 0;

  snapshot(): SaveData {
    return {
      saveVersion: 1,
      episode: 1,
      checkpoint: this.checkpoint,
      clock: this.clock,
      flags: this.flags.toJSON(),
      inventory: { ...this.inventory },
      lamp: { ...this.lamp },
      playTimeSec: Math.round(this.playTimeSec),
      savedAt: new Date().toISOString(),
    };
  }

  restore(save: SaveData): void {
    this.flags.load(save.flags);
    this.inventory = { ...save.inventory };
    this.lamp = { ...save.lamp };
    this.checkpoint = save.checkpoint;
    this.clock = save.clock;
    this.playTimeSec = save.playTimeSec;
  }
}

/** Compares saves ignoring when they were written. */
const sameGame = (a: SaveData, b: SaveData) =>
  JSON.stringify({ ...a, savedAt: "" }) === JSON.stringify({ ...b, savedAt: "" });

/**
 * Spike S6 (Development Plan, section 2.2): does state survive a refresh and
 * export as a code? Saves go to IndexedDB with a save indicator and the
 * "leave site?" guard; save codes carry a whole save between browsers.
 * URL: `?spike=s6` (add `&auto=1` to run every check, including a page reload).
 */
export async function runS6(
  engine: WebGPUEngine,
  params: URLSearchParams,
  device: DeviceProfile,
): Promise<void> {
  const canvas = engine.getRenderingCanvas() as HTMLCanvasElement;
  const qualityParam = params.get("quality");
  const quality: QualityName = isQualityName(qualityParam) ? qualityParam : device.quality;
  const { scene, camera, hall } = await createHallEnvironment(engine, getPreset(quality));
  const player = new PlayerController(
    scene,
    camera,
    new KeyboardMouseInput(canvas, 0.0022),
    hall.spawn,
  );

  // The save indicator: a small lamp in the top-right corner while saving (Controls, section 6.3).
  const indicator = document.createElement("div");
  indicator.textContent = "🪔";
  indicator.title = "Saving";
  indicator.style.cssText =
    "position:fixed;top:14px;right:18px;font-size:22px;opacity:0;transition:opacity .2s;z-index:6;pointer-events:none";
  document.body.appendChild(indicator);
  let indicatorSeen = false;
  let hideTimer = 0;
  const store = new SaveStore((saving) => {
    if (saving) {
      indicatorSeen = true;
      clearTimeout(hideTimer);
      indicator.style.opacity = "1";
    } else {
      // Keep it up long enough to be seen.
      hideTimer = window.setTimeout(() => (indicator.style.opacity = "0"), 700);
    }
  }, DATABASE);

  const hud = new SpikeHud(
    "Spike S6 · Save and load",
    "Does state survive a refresh and export as a code?",
    [
      "1 betel done",
      "2 pick up a match",
      "3 lamp open/out",
      "C next checkpoint (autosave)",
      "S save",
      "L load",
      "K copy code",
      "I paste code",
      "R reload page",
      "N new game",
      "F2 hide panel",
    ],
  );
  hud.addCheck("reload", "A save survives a page reload (IndexedDB)");
  hud.addCheck("code", "Export a save code and import it: the same game");
  hud.addCheck("tamper", "A changed or mistyped code is refused");
  hud.addCheck("damaged", "Damaged save data falls back to a new game, no crash");
  hud.addCheck("newer", "A save from a newer game is refused politely");
  hud.addCheck(
    "fast",
    `Saving under ${MAX_SAVE_MS} ms, with the save indicator and leave-site guard`,
  );
  new PerfOverlay(engine, scene);

  const result: S6Result = { saveMs: [], steps: [] };
  (window as unknown as { spikeResult: S6Result }).spikeResult = result;
  const step = (name: string) => {
    result.steps.push(name);
    console.info(`[S6] ${name}`);
  };

  const state = new GameState();
  let lastCode = "";
  let message = "";
  let guardSeen = false;

  const save = async (slot: "slot1" | "autosave") => {
    const data = state.snapshot();
    const started = performance.now();
    const writing = store.save(slot, data);
    guardSeen ||= store.saving;
    await writing;
    const ms = performance.now() - started;
    result.saveMs.push(ms);
    hud.check("fast", Math.max(...result.saveMs) < MAX_SAVE_MS && indicatorSeen && guardSeen);
    message = `saved ${slot} in ${ms.toFixed(1)} ms`;
    return data;
  };

  const load = async (slot: "slot1" | "autosave") => {
    const { save: data, problem } = await store.load(slot);
    if (data) {
      state.restore(data);
      message = `loaded ${slot} (${data.checkpoint}, saved ${new Date(data.savedAt).toLocaleTimeString()})`;
    } else {
      message = problem ? `couldn't use ${slot}: ${problem.message}` : `no save in ${slot}`;
    }
    return { data, problem };
  };

  const copyCode = async () => {
    const snapshot = state.snapshot();
    lastCode = await encodeSaveCode(snapshot);
    result.codeLength = lastCode.length;
    try {
      await navigator.clipboard.writeText(lastCode);
      message = `save code copied (${lastCode.length} characters)`;
    } catch {
      message = `save code (${lastCode.length} characters) is in the console`;
      console.info(lastCode);
    }
    return snapshot;
  };

  const pasteCode = async (code: string) => {
    try {
      const data = await decodeSaveCode(code);
      state.restore(data);
      message = `save code accepted (${data.checkpoint})`;
      return data;
    } catch (error) {
      message = error instanceof SaveError ? error.message : String(error);
      return null;
    }
  };

  // "Continue": pick up the checkpoint autosave if there is one.
  const resumed = await load("autosave");
  if (resumed.data) step("continued from autosave");

  scene.onBeforeRenderObservable.add(() => {
    const dt = Math.min(engine.getDeltaTime() / 1000, 0.1);
    state.playTimeSec += dt;
    // The lamp burns oil while open: about a quarter of a bottle every four minutes.
    if (state.lamp.state === "open") {
      state.lamp.oil = Math.max(0, state.lamp.oil - dt / 960);
      if (state.lamp.oil === 0) state.lamp.state = "out";
    }
    const flags = state.flags.toJSON();
    hud.setReadout([
      `checkpoint ${state.checkpoint} · ${state.clock} · played ${Math.floor(state.playTimeSec / 60)}:${String(Math.floor(state.playTimeSec % 60)).padStart(2, "0")}`,
      `lamp ${state.lamp.state}, oil ${(state.lamp.oil * 100).toFixed(1)}% · items ${
        Object.entries(state.inventory)
          .map(([k, v]) => `${k} ${v}`)
          .join(", ") || "none"
      }`,
      `flags ${Object.keys(flags).length}: ${Object.entries(flags)
        .slice(0, 4)
        .map(([k, v]) => `${k}=${String(v)}`)
        .join(", ")}${Object.keys(flags).length > 4 ? " …" : ""}`,
      `save code ${result.codeLength ?? "–"} characters · last save ${result.saveMs.at(-1)?.toFixed(1) ?? "–"} ms`,
      message,
    ]);
  });

  const checkpoints = ["CP0", "CP1", "CP2", "CP3", "CP4", "CP5", "CP6"];
  window.addEventListener("keydown", (e) => {
    if (e.code === "Digit1")
      state.flags.set("ep1.betel.done", !state.flags.get("ep1.betel.done", false));
    if (e.code === "Digit2") state.inventory.matches = (state.inventory.matches ?? 0) + 1;
    if (e.code === "Digit3") state.lamp.state = state.lamp.state === "open" ? "out" : "open";
    if (e.code === "KeyC") {
      state.checkpoint =
        checkpoints[Math.min(checkpoints.length - 1, checkpoints.indexOf(state.checkpoint) + 1)];
      void save("autosave");
    }
    if (e.code === "KeyS") void save("slot1");
    if (e.code === "KeyL") void load("slot1");
    if (e.code === "KeyK") void copyCode();
    if (e.code === "KeyI") {
      const code = window.prompt("Paste a save code");
      if (code) void pasteCode(code);
    }
    if (e.code === "KeyR") window.location.reload();
    if (e.code === "KeyN") state.restore(newGameSave());
  });

  if (import.meta.env.DEV)
    (window as unknown as { spike: unknown }).spike = {
      scene,
      player,
      state,
      store,
      save,
      load,
      copyCode,
      pasteCode,
    };

  // Automated run: part 1 saves and reloads the page; part 2 checks after the reload.
  const auto = params.get("auto") === "1";
  const expected = sessionStorage.getItem(RELOAD_MARK);
  if (auto && expected === null) {
    void (async () => {
      state.restore(endOfEpisodeOne());
      const saved = await save("slot1");
      await save("autosave");
      sessionStorage.setItem(RELOAD_MARK, JSON.stringify(saved));
      step("saved; reloading");
      window.location.reload();
    })();
  } else if (expected !== null) {
    sessionStorage.removeItem(RELOAD_MARK);
    void (async () => {
      const before = JSON.parse(expected) as SaveData;
      const { data } = await load("slot1");
      hud.check("reload", !!data && sameGame(data, before));
      step(`after reload: slot1 ${data && sameGame(data, before) ? "matches" : "DIFFERS"}`);

      // Save code round trip.
      const encoded = await copyCode();
      const decoded = await decodeSaveCode(lastCode);
      // Exact, savedAt included: the code carries the save unchanged.
      const same = JSON.stringify(decoded) === JSON.stringify(encoded);
      hud.check("code", same);
      step(`code ${lastCode.length} characters, round trip ${same ? "ok" : "DIFFERS"}`);

      // A typo in the middle of the code.
      const i = Math.floor(lastCode.length / 2);
      const typo = lastCode.slice(0, i) + (lastCode[i] === "x" ? "y" : "x") + lastCode.slice(i + 1);
      const refused = (await pasteCode(typo)) === null;
      hud.check("tamper", refused);
      step(`typo refused: ${refused} (${message})`);

      // Damaged data in the slot: reported, not thrown, and the game carries on.
      const good = await store.load("slot1");
      await store.writeRaw("slot1", { saveVersion: 1, episode: "one", flags: null });
      const damaged = await store.load("slot1");
      hud.check("damaged", damaged.save === null && damaged.problem?.reason === "data");
      step(`damaged slot: ${damaged.problem?.message ?? "not caught"}`);
      if (good.save) await store.save("slot1", good.save);

      // A save written by a newer build of the game.
      const newer = await encodeSaveCode({
        ...state.snapshot(),
        saveVersion: 2,
      } as unknown as SaveData);
      const newerRefused = (await pasteCode(newer)) === null && message.includes("newer");
      hud.check("newer", newerRefused);
      step(`newer save: ${message}`);

      // Ten saves in a row for timing.
      for (let n = 0; n < 10; n++) await save("slot1");
      step(`save time max ${Math.max(...result.saveMs).toFixed(1)} ms`);
      step("auto run done");
    })();
  }

  runRenderLoop(engine, () => scene.render(), renderStallNotice);
}
