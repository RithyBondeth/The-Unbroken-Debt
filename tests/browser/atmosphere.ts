/** Isolated visual/listening fixture; only look input and cue scheduling are scripted. */
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { isQualityName } from "../../src/render/QualityPresets";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { saveShot } from "../../src/debug/saveShot";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { AudioSystem } from "../../src/audio/AudioSystem";
import { Soundscape } from "../../src/episodes/ep1/act1/Soundscape";

async function review(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const params = new URLSearchParams(location.search);
  params.set("start", "act1");
  history.replaceState(null, "", `${location.pathname}?${params}`);
  const output = document.getElementById("status")!;
  output.textContent = "Loading production village…";
  const nav = document.getElementById("controls")!;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const device = await detectDevice();
  const quality = params.get("quality");
  if (isQualityName(quality)) device.quality = quality;
  const game = new Game(engine, device);
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-atmosphere-review"),
  });
  for (const flag of ["ep1.arrival.road", "ep1.arrival.courtyard", "ep1.vigil.started"])
    game.flags.set(flag, true);
  // Load graphics first. Enable only the relevant production audio layers after
  // a click, avoiding the full episode's unrelated recorded-footstep download.
  game.fade.waitForEnter = async () => {};
  await game.start({ audio: false });
  const act = (window as unknown as { act: ActOne }).act;
  while (game.cutscene) await new Promise((resolve) => setTimeout(resolve, 100));
  let paused = false,
    mist = true,
    view = "forest",
    captured = "",
    lastUpdate = 0;
  let autoTurn = false,
    elapsed = 0,
    lastPhase = "waiting";
  const trace: string[] = [];
  // Controls in the embedded browser substitute for pointer-lock mouse input,
  // as in the ritual fixture. Hidden tabs and the pause button still cancel cues.
  Object.defineProperty(game.input, "pointerLocked", { configurable: true, get: () => !paused });
  const aim = (at: Vector3) => {
    const d = at.subtract(game.camera.globalPosition);
    game.player.yaw = Math.atan2(d.x, d.z);
    game.player.pitch = Math.atan2(-d.y, Math.hypot(d.x, d.z));
  };
  const views: Record<string, [Vector3, Vector3]> = {
    forest: [new Vector3(-0.5, 0, 35.5), new Vector3(-1, 0.8, 26)],
    "mist-detail": [new Vector3(0, 0, 35), new Vector3(-5.4, 0.25, 34)],
    pavilion: [new Vector3(0, 0, -2), new Vector3(0, 1.1, -4.4)],
    "under-house": [new Vector3(-3.6, 0, -16.6), new Vector3(1, 0.6, -12)],
    paddy: [new Vector3(9, 0, 62), new Vector3(17, 0.4, 73)],
  };
  const show = (which: string) => {
    view = which;
    game.stopInspecting();
    game.player.teleport(views[which][0]);
    const d = views[which][1].subtract(views[which][0].add(new Vector3(0, 1.58, 0)));
    game.player.yaw = Math.atan2(d.x, d.z);
    game.player.pitch = Math.atan2(-d.y, Math.hypot(d.x, d.z));
    act.vigil.lamp.light();
    captured = "";
  };
  const button = (name: string, action: () => void) => {
    const b = document.createElement("button");
    b.textContent = name;
    b.onclick = action;
    nav.append(b);
  };
  for (const name of Object.keys(views)) button(name, () => show(name));
  let soundLoading = false;
  button("Enable atmosphere sound", () => {
    if (game.audio || soundLoading) return;
    soundLoading = true;
    void (async () => {
      const audio = await AudioSystem.create(undefined, { hideUnmuteButton: true });
      game.audio = audio;
      audio.attachListener(game.camera);
      await audio.unlock();
      await act.night.makeSounds();
      await act.forest.makeSounds();
      const space = new Soundscape(game, () =>
        Math.max(act.night.threatSilence, act.forest.silence),
      );
      await space.makeSounds();
      game.scene.onBeforeRenderObservable.add(() => space.update(game.deltaSeconds));
      game.scene.onDisposeObservable.add(() => space.stop());
    })().catch((error: unknown) => {
      captured = `Audio setup failed: ${String(error)}`;
      console.error(error);
    });
  });
  button("Toggle mist", () => {
    mist = !mist;
    if (game.pipeline.fog) game.pipeline.fog.mistStrength = mist ? 1 : 0;
    else {
      const system = game.scene.particleSystems.find((p) => p.name === "low_ground_mist");
      if (system) {
        system.stop();
        system.reset();
        if (mist) system.start();
      }
    }
  });
  button("Rehearse forest sequence", () => {
    show("forest");
    act.forest.previewSequence();
  });
  button("Verify turn response", () => {
    autoTurn = true;
    trace.length = 0;
    show("forest");
    act.forest.previewSequence();
  });
  button("Turn toward rustle", () => {
    if (act.forest.source) aim(act.forest.source);
  });
  button("Toggle dialogue interruption", () => {
    if (game.subtitles.active) game.subtitles.hide();
    else game.subtitles.show("Review", "Environmental cues yield while dialogue is active.");
  });
  button("Toggle paused input", () => {
    paused = !paused;
  });
  button("Toggle lantern", () => {
    if (act.vigil.lamp.burning) act.vigil.lamp.putOut();
    else act.vigil.lamp.light();
  });
  button("Save screenshot", () => {
    const name = `atmosphere-${game.preset.name}-${view}-${mist ? "mist" : "clear"}`;
    void saveShot(engine, game.camera, name).then(() => {
      captured = `Saved debug-shots/${name}.png`;
    });
  });
  game.scene.onAfterRenderObservable.add(() => {
    elapsed += game.deltaSeconds;
    const phase = act.forest.director.phase;
    if (phase !== lastPhase) {
      trace.push(
        `${phase}@${elapsed.toFixed(1)}s (presence ${act.apparitions.active}, threat ${game.threatActive}, hidden ${document.hidden})`,
      );
      lastPhase = phase;
    }
    if (autoTurn && phase === "movement" && act.forest.source) {
      aim(act.forest.source);
      autoTurn = false;
    }
    if (performance.now() - lastUpdate < 150) return;
    lastUpdate = performance.now();
    const source = act.forest.source;
    output.textContent =
      `${view} · ${game.preset.name} · mist ${mist ? "on" : "off"} · ${game.audio ? "audio enabled" : "silent visual review"}\n` +
      `sequence ${act.forest.director.phase} · hush ${act.forest.silence.toFixed(2)} · input ${paused ? "paused" : "active"}\n` +
      `source ${source ? `${source.x.toFixed(1)}, ${source.z.toFixed(1)}` : "none"} · dialogue ${game.subtitles.active}\n${trace.slice(-5).join("\n")}\n${captured}`;
  });
  show(params.get("view") && views[params.get("view")!] ? params.get("view")! : "forest");
}

void review().catch((error: unknown) => {
  document.getElementById("status")!.textContent = `FAIL ${String(error)}`;
  console.error(error);
});
