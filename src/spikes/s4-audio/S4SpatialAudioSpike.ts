import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { Color3 } from "@babylonjs/core/Maths/math.color";
import { CreateCapsule } from "@babylonjs/core/Meshes/Builders/capsuleBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { KeyboardMouseInput, type InputSource } from "../../player/InputSource";
import type { MoveIntent } from "../../player/movement";
import { PlayerController } from "../../player/PlayerController";
import { PerfOverlay } from "../../debug/PerfOverlay";
import { getPreset, isQualityName, type QualityName } from "../../render/QualityPresets";
import type { DeviceProfile } from "../../render/DeviceProfile";
import { AudioSystem, PANNING } from "../../audio/AudioSystem";
import { boardCreak, rattlingBreath, seededRandom, wetStep } from "../../audio/synth";
import {
  makeTrials,
  relativeAzimuth,
  summarize,
  wrapAngle,
  type Panning,
  type Summary,
  type Trial,
  type TrialResult,
} from "../../audio/localization";
import { SpikeHud } from "../SpikeHud";
import { createHallEnvironment } from "../hallEnvironment";
import { renderEars, type EarLevels } from "./offlineCheck";
import { runRenderLoop } from "../../render/renderLoop";
import { renderStallNotice } from "../../ui/html/RenderStallNotice";

/** Results exposed for automated checks (`window.spikeResult`). */
export interface S4Result {
  ears: EarLevels[];
  trials: TrialResult[];
  summary: Partial<Record<Panning, Summary>>;
  listenerError?: number;
  steps: string[];
}

const RATE = 48000;
const TRIALS = 10;
/** Pass conditions for the pointing test with HRTF. */
const MAX_MEDIAN_ERROR_DEG = 30;
const MAX_FRONT_BACK_RATE = 0.2;
const STEP_INTERVAL = 0.62;

/** Turning only, while a trial runs: the player answers by facing the sound. */
class TurnOnlyInput implements InputSource {
  frozen = false;
  constructor(private readonly inner: InputSource) {}
  readMove(out: MoveIntent): MoveIntent {
    this.inner.readMove(out);
    if (this.frozen) {
      out.x = 0;
      out.z = 0;
      out.crouch = false;
      out.hurry = false;
    }
    return out;
  }
  consumeLook(out: { yaw: number; pitch: number }): void {
    this.inner.consumeLook(out);
  }
  dispose(): void {
    this.inner.dispose();
  }
}

/**
 * Spike S4 (Development Plan, section 2.2): can players locate an unseen enemy
 * by sound? An invisible Neak Ta shadow form walks the S2 hall with wet,
 * dragging steps and breath (synthesised stand-ins), on the HRTF threat bus.
 * The pointing test blacks out the screen and plays steps from hidden places:
 * turn to face them and press Space. The panning itself is checked silently
 * by rendering through the engine offline.
 * URL: `?spike=s4` (headphones; click once to start the sound).
 */
export async function runS4(
  engine: WebGPUEngine,
  params: URLSearchParams,
  device: DeviceProfile,
): Promise<void> {
  const canvas = engine.getRenderingCanvas() as HTMLCanvasElement;
  const qualityParam = params.get("quality");
  const quality: QualityName = isQualityName(qualityParam) ? qualityParam : device.quality;
  const { scene, camera, hall } = await createHallEnvironment(engine, getPreset(quality));
  const input = new TurnOnlyInput(new KeyboardMouseInput(canvas, 0.0022));
  const player = new PlayerController(scene, camera, input, hall.spawn);

  const hud = new SpikeHud(
    "Spike S4 · Spatial audio",
    "Can players locate an unseen enemy by sound? Headphones on.",
    [
      "Click to start sound and look",
      "WASD move",
      "T pointing test",
      "Space answer",
      "V show the walker",
      "P walker on/off",
      "F2 hide panel",
      "F3 stats",
    ],
  );
  hud.addCheck("ears", "Panning is honest: each of 8 directions in the right ear (offline render)");
  hud.addCheck(
    "hrtf",
    "HRTF gives a real head's cues: 0.5–0.8 ms delay at the far ear, front ≠ back",
  );
  hud.addCheck("distance", "Closer is louder: 2 m about 12 dB louder than 8 m");
  hud.addCheck("listener", "The listener follows the camera");
  hud.addCheck(
    "aim",
    `Pointing test with HRTF: median error ≤ ${MAX_MEDIAN_ERROR_DEG}° (you, eyes closed)`,
  );
  hud.addCheck(
    "frontBack",
    `Front/back mix-ups with HRTF in ≤ ${MAX_FRONT_BACK_RATE * 100}% of trials`,
  );
  new PerfOverlay(engine, scene);

  const result: S4Result = { ears: [], trials: [], summary: {}, steps: [] };
  (window as unknown as { spikeResult: S4Result }).spikeResult = result;
  const step = (name: string) => {
    result.steps.push(name);
    console.info(`[S4] ${name}`);
  };

  // Silent checks through the real engine, before anything is heard.
  void (async () => {
    const deg = (d: number) => (d * Math.PI) / 180;
    for (const panning of ["HRTF", "equalpower"] as const) {
      for (const d of [0, 45, 90, 135, 180, -135, -90, -45]) {
        result.ears.push(await renderEars(deg(d), 3, panning));
      }
    }
    const sideOk = result.ears.every((e) => {
      const side = Math.round(Math.sin(e.azimuth) * 1000);
      return side === 0 ? Math.abs(e.ildDb) < 0.5 : Math.sign(e.ildDb) === Math.sign(side);
    });
    hud.check("ears", sideOk);
    const hrtf = result.ears.filter((e) => e.panning === "HRTF");
    const right = hrtf.find((e) => Math.abs(e.azimuth - deg(90)) < 1e-6);
    const front = hrtf.find((e) => e.azimuth === 0);
    const back = hrtf.find((e) => Math.abs(Math.abs(e.azimuth) - Math.PI) < 1e-6);
    const frontBackDb = front && back ? Math.abs(20 * Math.log10(back.left / front.left)) : 0;
    hud.check("hrtf", !!right && right.itdMs >= 0.5 && right.itdMs <= 0.8 && frontBackDb > 0.5);
    const near = await renderEars(0, 2, "HRTF");
    const far = await renderEars(0, 8, "HRTF");
    const dropDb = 20 * Math.log10(near.left / far.left);
    hud.check("distance", dropDb > 10 && dropDb < 14);
    step(
      `offline: sides ${sideOk ? "ok" : "WRONG"}, ITD at 90° ${right?.itdMs.toFixed(2)} ms, front/back ${frontBackDb.toFixed(1)} dB, 2→8 m ${dropDb.toFixed(1)} dB`,
    );
  })();

  // The walker: an invisible shadow form on a slow patrol round the coffin.
  const walker = CreateCapsule("walker", { height: 1.9, radius: 0.28 }, scene);
  const walkerMat = new StandardMaterial("M_walker", scene);
  walkerMat.emissiveColor = new Color3(0.6, 0.1, 0.05);
  walker.material = walkerMat;
  walker.isVisible = false;
  walker.isPickable = false;
  let walkerOn = true;
  let walkerAngle = 0;

  let audio: AudioSystem | null = null;
  let steps: StaticSound[] = [];
  const trialSteps: Record<Panning, StaticSound[]> = { HRTF: [], equalpower: [] };
  let breath: StaticSound | null = null;
  let creak: StaticSound | null = null;
  let stepClock = 0;
  let stepIndex = 0;

  const start = async () => {
    if (audio) return;
    audio = await AudioSystem.create();
    await audio.unlock();
    audio.attachListener(camera);
    const rand = seededRandom(1932);
    const takes = Array.from({ length: 6 }, () => audio!.buffer(wetStep(RATE, rand), RATE));
    const origin = walker.position;
    steps = await Promise.all(
      takes.map((b, i) => audio!.spatialSound(`step_${i}`, b, "threat", origin)),
    );
    for (const panning of ["HRTF", "equalpower"] as const) {
      trialSteps[panning] = await Promise.all(
        takes.map((b, i) =>
          audio!.spatialSound(`trial_${panning}_${i}`, b, "threat", origin, { panning }),
        ),
      );
    }
    breath = await audio.spatialSound(
      "breath",
      audio.buffer(rattlingBreath(RATE, rand), RATE),
      "threat",
      origin,
      {
        loop: true,
        volume: 0.5,
      },
    );
    breath.spatial.attach(walker);
    creak = await audio.spatialSound(
      "creak",
      audio.buffer(boardCreak(RATE, rand), RATE),
      "sfx",
      origin,
      {
        volume: 0.6,
      },
    );
    if (walkerOn) breath.play();
    step("audio started");
  };
  canvas.addEventListener("click", () => void start());

  // The pointing test.
  let trials: Trial[] = [];
  let trial: { index: number; startYaw: number; source: Vector3; time: number } | null = null;
  const blackout = document.createElement("div");
  blackout.style.cssText =
    "position:fixed;inset:0;background:#000;color:#8a8070;display:none;align-items:flex-end;justify-content:center;padding:40px;font:16px Ubuntu,sans-serif;z-index:5;pointer-events:none";
  document.body.appendChild(blackout);

  const beginTrial = (index: number) => {
    const t = trials[index];
    const eye = camera.globalPosition;
    const yaw = player.yaw;
    const source = new Vector3(
      eye.x + Math.sin(yaw + t.azimuth) * t.distance,
      eye.y - 1.2,
      eye.z + Math.cos(yaw + t.azimuth) * t.distance,
    );
    trial = { index, startYaw: yaw, source, time: 0 };
    stepClock = 0;
    blackout.textContent = `Trial ${index + 1} of ${trials.length}: turn to face the footsteps, then press Space`;
  };

  const finishTrials = () => {
    trial = null;
    input.frozen = false;
    blackout.style.display = "none";
    for (const panning of ["HRTF", "equalpower"] as const) {
      result.summary[panning] = summarize(result.trials.filter((r) => r.panning === panning));
    }
    const h = result.summary.HRTF as Summary;
    const e = result.summary.equalpower as Summary;
    const degrees = (r: number) => ((r * 180) / Math.PI).toFixed(0);
    hud.check("aim", (h.medianError * 180) / Math.PI <= MAX_MEDIAN_ERROR_DEG);
    hud.check("frontBack", h.frontBackRate <= MAX_FRONT_BACK_RATE);
    const text = [
      `HRTF: median error ${degrees(h.medianError)}°, front/back mix-ups ${(h.frontBackRate * 100).toFixed(0)}%`,
      `Equal-power: median error ${degrees(e.medianError)}°, front/back mix-ups ${(e.frontBackRate * 100).toFixed(0)}%`,
    ].join("\n");
    hud.showReport(text, (h.medianError * 180) / Math.PI <= MAX_MEDIAN_ERROR_DEG);
    step(text.replace(/\n/g, " | "));
    if (walkerOn) breath?.play();
  };

  const answer = () => {
    if (!trial) return;
    const t = trials[trial.index];
    result.trials.push({
      ...t,
      response: wrapAngle(player.yaw - trial.startYaw),
      seconds: trial.time,
    });
    if (trial.index + 1 < trials.length) beginTrial(trial.index + 1);
    else finishTrials();
  };

  const startTrials = () => {
    if (!audio) return;
    trials = makeTrials(TRIALS, seededRandom(Date.now() & 0xffff));
    result.trials = [];
    input.frozen = true;
    breath?.stop();
    blackout.style.display = "flex";
    beginTrial(0);
  };

  window.addEventListener("keydown", (e) => {
    if (e.code === "KeyT") void start().then(startTrials);
    if (e.code === "Space") answer();
    if (e.code === "KeyV") walker.isVisible = !walker.isVisible;
    if (e.code === "KeyP") {
      walkerOn = !walkerOn;
      if (walkerOn) breath?.play();
      else breath?.stop();
    }
  });

  const playStep = (pool: StaticSound[], at: Vector3) => {
    if (pool.length === 0) return;
    const sound = pool[stepIndex++ % pool.length];
    sound.spatial.position.copyFrom(at);
    sound.play();
  };

  scene.onBeforeRenderObservable.add(() => {
    const dt = Math.min(engine.getDeltaTime() / 1000, 0.1);
    stepClock += dt;
    if (trial) {
      trial.time += dt;
      // Steps where they are, pacing on the spot; the sound tells the truth.
      if (stepClock >= STEP_INTERVAL) {
        stepClock = 0;
        playStep(trialSteps[trials[trial.index].panning], trial.source);
      }
    } else if (walkerOn) {
      walkerAngle += dt * 0.18;
      walker.position.set(Math.cos(walkerAngle) * 3.6, 0.95, Math.sin(walkerAngle) * 2.8);
      if (stepClock >= STEP_INTERVAL) {
        stepClock = 0;
        const feet = walker.position.subtract(new Vector3(0, 0.9, 0));
        playStep(steps, feet);
        if (creak && Math.random() < 0.15) {
          creak.spatial.position.copyFrom(feet);
          creak.play();
        }
      }
    }

    if (audio) {
      const listener = audio.engine.listener.position;
      result.listenerError = Vector3.Distance(listener, camera.globalPosition);
      hud.check("listener", result.listenerError < 0.01);
    }
    const eye = camera.globalPosition;
    const az = relativeAzimuth(eye.x, eye.z, player.yaw, walker.position.x, walker.position.z);
    hud.setReadout([
      audio
        ? `sound on · threat bus ${PANNING.threat} · effects ${PANNING.sfx}`
        : "click the view to start the sound",
      trial
        ? `trial ${trial.index + 1}/${trials.length}`
        : `walker ${walkerOn ? "walking" : "stopped"} ${walker.isVisible ? "(visible)" : "(hidden)"} · ${((az * 180) / Math.PI).toFixed(0)}° from where you face, ${Vector3.Distance(eye, walker.position).toFixed(1)} m`,
      result.ears.length
        ? `offline HRTF at 90°: ${result.ears.find((e) => e.panning === "HRTF" && Math.abs(e.azimuth - Math.PI / 2) < 1e-6)?.itdMs.toFixed(2) ?? "–"} ms later at the far ear`
        : "offline checks running…",
      `listener ${result.listenerError === undefined ? "–" : `${(result.listenerError * 100).toFixed(1)} cm from the camera`}`,
    ]);
  });

  if (import.meta.env.DEV)
    (window as unknown as { spike: unknown }).spike = {
      scene,
      player,
      walker,
      start,
      startTrials,
      answer,
      // For checking the test itself: the current trial and where the player faced at its start.
      current: () => (trial ? { ...trials[trial.index], startYaw: trial.startYaw } : null),
    };
  runRenderLoop(engine, () => scene.render(), renderStallNotice);
}
