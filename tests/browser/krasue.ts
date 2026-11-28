import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "@/core/Game";
import { AudioSystem } from "@/audio/AudioSystem";
import { createEngine } from "@/render/createEngine";
import { detectDevice } from "@/render/detectDevice";
import { useLocalDecoders } from "@/render/decoders";
import { SaveStore } from "@/systems/saves/SaveStore";
import { saveShot } from "@/debug/saveShot";
import type { ActOne } from "@/episodes/ep1/act1/ActOne";
import { KRASUE_PADDY_PATHS } from "@/episodes/ep1/data/krasue";

const results = document.getElementById("results")!;
const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const wait = async (test: () => boolean, seconds = 120) => {
  const start = performance.now();
  while (!test()) {
    if (performance.now() - start > seconds * 1000)
      throw new Error("Timed out waiting for encounter");
    await pause(50);
  }
};

async function review(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const engine = await createEngine(document.getElementById("game") as HTMLCanvasElement);
  if (!engine) throw new Error("WebGPU required");
  useLocalDecoders();
  const game = new Game(engine, await detectDevice());
  Object.defineProperty(game, "saves", {
    value: new SaveStore(undefined, "boon-sop-krasue-verification"),
  });
  for (const key of ["ep1.arrival.road", "ep1.arrival.courtyard", "ep1.puzzle.gate.open"]) {
    game.flags.set(key, true);
  }
  game.fade.waitForEnter = async () => {};
  results.textContent = "Loading production rice paddies, Krasue GLB and lighting…";
  await game.start({ audio: false });
  await wait(() => !game.cutscene);
  const act = (window as unknown as { act: ActOne }).act;
  const encounter = act.krasue;

  let preview = true;
  let detail = false;
  let selected = 0;
  let clock = 0;
  let turntable = false;
  let screamDetail = false;
  let rushAt = -Infinity;
  const flight = new Vector3();

  const show = (index: number, close = false) => {
    game.input.clear();
    turntable = false;
    screamDetail = false;
    rushAt = -Infinity;
    document.exitPointerLock();
    preview = true;
    detail = close;
    selected = index % KRASUE_PADDY_PATHS.length;
    game.cutscene = true;
    game.sketchbook?.close();
    game.stopInspecting();
    encounter.summon(selected);
    const camPos = close
      ? new Vector3(4.65, 2.5, -13)
      : selected === 0
        ? new Vector3(12, 0.2, 34)
        : new Vector3(-12, 0.2, 32);
    game.player.teleport(camPos, selected === 0 ? 1.15 : -1.15);
    game.player.pitch = 0.02;
    if (close) {
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          if (preview && detail) game.inspectObject(new Vector3(8.4, 3.45, -13), 1.15);
        }),
      );
    }
    act.vigil.lamp.light();
    results.textContent =
      "Rice-Field Krasue (អាប) · Emerald-green ↔ Blood-red organ glow\nPreview: " +
      (close ? "face, hair and trailing organs" : KRASUE_PADDY_PATHS[selected].id);
  };

  game.scene.onBeforeRenderObservable.add(() => {
    clock += game.deltaSeconds;
    if (!preview) return;
    encounter.brain.update(game.deltaSeconds, game.camera.globalPosition, false, false, true);
    const at = detail ? new Vector3(8.4, 4.08, -13) : encounter.brain.position;
    const rushAge = (clock - rushAt) % 5;
    if (Number.isFinite(rushAt)) {
      const moving = Math.max(0, rushAge - 0.38);
      const travel = Math.min(3, 0.8 * moving + 6.5 * moving * moving);
      at.x += 3 - travel;
    }
    encounter.model.root.setEnabled(detail || !encounter.brain.hidden);
    encounter.model.redness = detail ? Math.sin(clock * 0.9) * 0.5 + 0.5 : encounter.brain.redness;
    flight.set(Math.sin(clock * 0.7), 0, Math.cos(clock * 0.7));
    encounter.model.pose(
      at,
      game.camera.globalPosition,
      clock,
      Number.isFinite(rushAt),
      turntable ? flight : detail ? undefined : encounter.brain.direction,
      false,
      screamDetail ? 0.5 : Number.isFinite(rushAt) ? rushAge : -1,
    );
  });

  const ensureAudio = async () => {
    if (!game.audio) {
      game.audio = await AudioSystem.create(undefined, { hideUnmuteButton: true });
      game.audio.attachListener(game.camera);
      await act.villageAudio.load();
      await encounter.makeSounds();
    }
    await game.audio.unlock();
  };

  document.getElementById("west")!.onclick = () => show(0);
  document.getElementById("south")!.onclick = () => show(1);
  document.getElementById("detail")!.onclick = () => show(0, true);
  document.getElementById("turntable")!.onclick = () => {
    show(0, true);
    turntable = true;
  };
  document.getElementById("scream")!.onclick = () => {
    show(0, true);
    screamDetail = true;
    results.textContent += "\nHeld scream pose: inspect jaw, lips and recessed teeth";
  };
  document.getElementById("rush")!.onclick = () => {
    show(0, true);
    rushAt = clock;
    results.textContent += "\nRepeating rush: watch the hair and organs lag, then settle";
  };
  document.getElementById("sound")!.onclick = async () => {
    await ensureAudio();
    act.villageAudio.play("krasueAlert", encounter.brain.position, 0.95);
    results.textContent += "\nPlaying mastered Krasue alert";
  };
  document.getElementById("capture")!.onclick = () =>
    void saveShot(
      engine,
      game.camera,
      screamDetail
        ? "krasue-scream"
        : detail
          ? "krasue-detail"
          : `krasue-${KRASUE_PADDY_PATHS[selected].id}`,
    ).then(() => {
      results.textContent += "\nScreenshot saved in debug-shots";
    });

  show(0);
}

function fail(error: unknown): void {
  results.textContent = `FAIL ${String(error)}`;
  console.error(error);
}
void review().catch(fail);
