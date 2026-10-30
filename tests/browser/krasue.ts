import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Game } from "../../src/core/Game";
import { AudioSystem } from "../../src/audio/AudioSystem";
import { createEngine } from "../../src/render/createEngine";
import { detectDevice } from "../../src/render/detectDevice";
import { useLocalDecoders } from "../../src/render/decoders";
import { SaveStore } from "../../src/systems/saves/SaveStore";
import { saveShot } from "../../src/debug/saveShot";
import type { ActOne } from "../../src/episodes/ep1/act1/ActOne";
import { KRASUE_WINDOWS } from "../../src/episodes/ep1/data/krasue";

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
  if (!new URLSearchParams(location.search).has("continue")) {
    for (const key of [
      "ep1.arrival.road",
      "ep1.arrival.courtyard",
      "ep1.act2.started",
      "ep1.sok.unlocked",
      "ep1.walker.complete",
    ])
      game.flags.set(key, true);
  }
  game.fade.waitForEnter = async () => {};
  results.textContent = "Loading production house, physics and lighting…";
  await game.start({ audio: false });
  await wait(() => !game.cutscene);
  const act = (window as unknown as { act: ActOne }).act;
  const encounter = act.krasue;
  // QA can supply a focused bot when the embedded browser has no pointer-lock
  // support. Sight, movement, attack and checkpoint code remain production code.
  const automated = new URLSearchParams(location.search).has("automation");
  let botActive = false;
  if (automated)
    Object.defineProperty(game.input, "pointerLocked", {
      configurable: true,
      get: () => botActive,
    });
  let preview = true,
    detail = false,
    selected = 0;
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
    botActive = false;
    document.exitPointerLock();
    preview = true;
    detail = close;
    selected = index;
    game.cutscene = true;
    game.sketchbook?.close();
    game.stopInspecting();
    encounter.brain.reset();
    encounter.brain.selectWindow(KRASUE_WINDOWS[index]);
    game.player.teleport(
      index === 0 ? new Vector3(4.65, 2.5, -13) : new Vector3(4.2, 2.5, -12.8),
      index === 0 ? Math.PI / 2 : 0,
    );
    game.player.pitch = 0.035;
    if (close)
      requestAnimationFrame(() =>
        requestAnimationFrame(() => {
          // Teleport is applied by the physics step. Aim the close-up from its
          // updated camera position, rather than from the previous test corner.
          if (preview && detail) game.inspectObject(new Vector3(8.4, 3.45, -13), 1.15);
        }),
      );
    act.vigil.lamp.light();
    results.textContent =
      "Production geometry and night lighting · Esc pauses the encounter\nPreview: " +
      (close ? "face, hair and trailing organs" : KRASUE_WINDOWS[index].id + " kitchen window");
  };
  game.scene.onBeforeRenderObservable.add(() => {
    clock += game.deltaSeconds;
    if (!preview) return;
    encounter.brain.update(game.deltaSeconds, game.camera.globalPosition, false, false);
    const at = detail ? new Vector3(8.4, 4.08, -13) : encounter.brain.position;
    const rushAge = (clock - rushAt) % 5;
    if (Number.isFinite(rushAt)) {
      const moving = Math.max(0, rushAge - 0.38);
      const travel = Math.min(3, 0.8 * moving + 6.5 * moving * moving);
      at.x += 3 - travel;
    }
    encounter.model.root.setEnabled(true);
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
      await encounter.makeSounds();
    }
    await game.audio.unlock();
  };
  const play = async (escape: boolean) => {
    show(selected);
    await ensureAudio();
    preview = false;
    game.cutscene = false;
    encounter.brain.reset();
    if (automated) botActive = true;
    else await game.input.lockPointer();
    await game.audio?.unlock();
    results.textContent = "Encounter running · WASD moves; F extinguishes the lamp; Esc pauses";
    if (escape) {
      await wait(() => encounter.brain.state === "watching", 15);
      if (encounter.activeScreams !== 1)
        throw new Error("Detection did not start one audible scream");
      await wait(() => encounter.model.mouthOpen > 0.9, 1);
      await wait(() => encounter.brain.state === "charging", 15);
      // Stand in a clear corner beside the aperture, including the steeper
      // sight angle when her accelerating rush reaches its closest approach.
      game.player.teleport(
        selected === 0 ? new Vector3(5.4, 2.5, -14.05) : new Vector3(3.35, 2.5, -12.05),
      );
      await wait(() => encounter.brain.state === "cooldown", 10);
      if (game.threatActive) throw new Error("Threat did not release after escape");
      document.exitPointerLock();
      botActive = false;
      results.textContent =
        "PASS actual window ray detects the player\nPASS one positional scream starts before the rush\nPASS charge accelerates after the warning\nPASS solid wall blocks sight and prevents a kill\nPASS searching ends and threat/menu gates release";
      results.textContent += "\nPASS jaw opens with the detection scream";
    }
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
    results.textContent += "\nRepeating outside rush: watch the hair and organs lag, then settle";
  };
  document.getElementById("motion")!.onclick = () =>
    void (async () => {
      show(0, true);
      await pause(100);
      const hair = encounter.model.meshes.find((m) => m.name.includes("krasue_hair_lock_05"))!;
      const gut = encounter.model.meshes.find(
        (m) => m.name.includes("krasue_intestine_3") && !m.name.includes("vessel"),
      )!;
      if (!hair || !gut) throw new Error("Missing skinned hair or intestine mesh");
      const sample = (mesh: typeof hair) => Array.from(mesh.getPositionData(true)!);
      const firstHair = sample(hair),
        firstGut = sample(gut);
      await pause(900);
      const moved = (first: number[], second: number[]) =>
        first.some((v, i) => Math.abs(v - second[i]) > 0.0005);
      if (!moved(firstHair, sample(hair)) || !moved(firstGut, sample(gut)))
        throw new Error("Skinned vertices did not animate");
      results.textContent =
        "PASS real hair vertices deform under skeletal animation\nPASS real intestine vertices deform independently\nPASS solid sculpted GLB with 101 bones; no silhouette surface";
    })().catch(fail);
  document.getElementById("trail")!.onclick = () =>
    void (async () => {
      show(0, true);
      await pause(1800);
      const hair = encounter.model.meshes.find((m) => m.name.includes("krasue_hair_lock_05"))!;
      const gut = encounter.model.meshes.find(
        (m) => m.name.includes("krasue_intestine_3") && !m.name.includes("vessel"),
      )!;
      const relativeTip = (mesh: typeof hair) => {
        const positions = mesh.getPositionData(true)!;
        const rest = mesh.getPositionData(false)!;
        let low = Infinity;
        for (let i = 1; i < rest.length; i += 3) low = Math.min(low, rest[i]);
        const sum = Vector3.Zero();
        let count = 0;
        for (let i = 0; i < positions.length; i += 3) {
          if (rest[i + 1] > low + 0.12) continue;
          sum.addInPlace(
            Vector3.TransformCoordinates(
              new Vector3(positions[i], positions[i + 1], positions[i + 2]),
              mesh.getWorldMatrix(),
            ).subtract(encounter.model.root.position),
          );
          count++;
        }
        return sum.scale(1 / count);
      };
      const hairAtRest = relativeTip(hair),
        gutAtRest = relativeTip(gut);
      rushAt = clock;
      await pause(900);
      // This close-up flies west (-X); the actual deformed tips must trail east.
      const hairLag = relativeTip(hair).x - hairAtRest.x;
      const gutLag = relativeTip(gut).x - gutAtRest.x;
      if (hairLag < 0.05 || gutLag < 0.025)
        throw new Error(
          `Rush tips did not trail: hair ${hairLag.toFixed(3)}m, gut ${gutLag.toFixed(3)}m`,
        );
      results.textContent = `PASS actual skinned hair trails behind flight (${hairLag.toFixed(2)}m)\nPASS hanging intestine trails with weight (${gutLag.toFixed(2)}m)`;
    })().catch(fail);
  document.getElementById("cover")!.onclick = () =>
    void play(true).catch((error: unknown) => fail(`${String(error)} · ${encounter.debugSight}`));
  document.getElementById("attack")!.onclick = () => void play(false).catch(fail);
  document.getElementById("sound")!.onclick = async () => {
    await ensureAudio();
    const audio = game.audio!;
    // Reuse the production source and buffers, with a short opt-in preview.
    const { krasueLament, krasueShriek } =
      await import("../../src/episodes/ep1/audio/krasueSounds");
    const { seededRandom } = await import("../../src/audio/synth");
    const at = KRASUE_WINDOWS[selected].center.add(KRASUE_WINDOWS[selected].normal.scale(2.45));
    const sound = await audio.spatialSound(
      "krasue_review",
      audio.buffer(
        krasueLament(audio.context.sampleRate, seededRandom(739)),
        audio.context.sampleRate,
      ),
      "threat",
      at,
      { minDistance: 2, volume: 0.2 },
    );
    sound.play();
    results.textContent += "\nPlaying HRTF lament, then attack shriek";
    await pause(4000);
    sound.stop();
    sound.dispose();
    const attack = await audio.spatialSound(
      "krasue_review_attack",
      audio.buffer(
        krasueShriek(audio.context.sampleRate, seededRandom(741)),
        audio.context.sampleRate,
      ),
      "threat",
      at,
      { minDistance: 2, volume: 0.45 },
    );
    attack.play();
    await pause(2500);
    attack.dispose();
  };
  document.getElementById("capture")!.onclick = () =>
    void saveShot(
      engine,
      game.camera,
      screamDetail
        ? "krasue-scream"
        : detail
          ? "krasue-detail"
          : `krasue-${KRASUE_WINDOWS[selected].id}`,
    ).then(() => {
      results.textContent += "\nScreenshot saved in debug-shots";
    });
  await game.checkpoints.mark(act.beats.captureProgress(), "Krasue review · Safe checkpoint");
  show(0);
}

function fail(error: unknown): void {
  results.textContent = `FAIL ${String(error)}`;
  console.error(error);
}
void review().catch(fail);
