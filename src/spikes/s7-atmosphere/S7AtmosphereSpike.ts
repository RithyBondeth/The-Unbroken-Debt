import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { CreateScreenshotAsync } from "@babylonjs/core/Misc/screenshotTools";
import { KeyboardMouseInput } from "../../player/InputSource";
import { PlayerController } from "../../player/PlayerController";
import { PerfOverlay } from "../../debug/PerfOverlay";
import { saveShot } from "../../debug/saveShot";
import { getPreset, isQualityName, type QualityName } from "../../render/QualityPresets";
import type { DeviceProfile } from "../../render/DeviceProfile";
import { Atmosphere, type GradeMode } from "../../render/Atmosphere";
import { targetExposure } from "../../render/look";
import { EP1_GRADE } from "../../episodes/ep1/data/grade";
import { SpikeHud } from "../SpikeHud";
import { createHallEnvironment, lockRenderSize } from "../hallEnvironment";

/** Results exposed for automated checks (`window.spikeResult`). */
export interface S7Result {
  quality: QualityName;
  render: string;
  /** Extra frame time of each effect, ms (A/B against the same frame without it). */
  costs: Record<string, number>;
  /** Seconds for the eye to get 90% of the way after the lamp goes out. */
  adaptSeconds?: number;
  /**
   * Brightness (0–1, sRGB) of the brightest 5% of the middle of the screen after
   * adapting in the dark: the nearest shapes. Most of a dark frame is rightly black.
   */
  darkLuma?: number;
  steps: string[];
}

/** Lamp light at 1 m (intensity 14) counts as 1: the eye's reference. */
const LAMP_REFERENCE = 14;
/**
 * Look effects together must cost less than this at 1080p (ms): about 12% of a
 * 60 fps frame. S2's 60 fps benchmark on Medium already includes all of them.
 */
const LOOK_BUDGET_MS = 2;
/** Darkness rule: the nearest shapes faint, neither black nor lit (sRGB, 95th percentile). */
const DARK_LUMA = { min: 0.04, max: 0.3 };

/**
 * Spike S7 (Development Plan, section 2.2): can the 1930s look be done cheaply?
 * The S2 hall with the episode's lookup-table grade, slow eye adaptation, and
 * vignette, grain and aberration that follow fear, scares and settings. Measures
 * what each effect costs and checks the Art Bible's darkness rule.
 * URL: `?spike=s7` (`&auto=1` scripted checks, `&bench=1` effect costs,
 * `&flames=0` flames and candles out, lit only by the moon, `&res=1080`, `&quality=low|…`).
 */
export async function runS7(
  engine: WebGPUEngine,
  params: URLSearchParams,
  device: DeviceProfile,
): Promise<void> {
  const canvas = engine.getRenderingCanvas() as HTMLCanvasElement;
  const qualityParam = params.get("quality");
  const quality: QualityName = isQualityName(qualityParam) ? qualityParam : device.quality;
  const preset = getPreset(quality);
  const res = Number(params.get("res"));
  if (res >= 360) lockRenderSize(engine, res);

  const { scene, camera, hall, lamp, flames, candles, pipeline } = await createHallEnvironment(
    engine,
    preset,
  );
  const darkHall = params.get("flames") === "0";
  if (darkHall) {
    // Every flame and candle out: only the moon through the gaps.
    for (const flame of flames) flame.setEnabled(false);
    for (const candle of candles.lights) candle.intensity = 0;
  }

  const player = new PlayerController(
    scene,
    camera,
    new KeyboardMouseInput(canvas, 0.0022),
    hall.spawn,
  );
  const atmosphere = new Atmosphere(scene, pipeline.main, EP1_GRADE, camera);
  let lampOn = true;

  /** Light reaching Sora's eyes: her lamp plus the flames, by distance. */
  const lightAtEye = (): number => {
    const eye = camera.globalPosition;
    let light = lampOn ? 1 : 0;
    for (const flame of flames) {
      if (!flame.isEnabled()) continue;
      const d = Math.max(0.5, Vector3.Distance(eye, flame.getAbsolutePosition()));
      light += flame.intensity / (d * d) / LAMP_REFERENCE;
    }
    return light + 0.01; // moonlight through the gaps
  };

  const hud = new SpikeHud("Spike S7 · Atmosphere", "Can the 1930s look be done cheaply?", [
    "Click to look",
    "WASD move",
    "F lamp",
    "T fear",
    "X scare",
    "G grain",
    "C aberration",
    "L grade LUT/curves/off",
    "[ ] brightness",
    "B effect costs",
    "F2 hide panel",
    "F3 stats",
  ]);
  hud.addCheck(
    "cost",
    `The look (grain, aberration, vignette, grade, bloom) under ${LOOK_BUDGET_MS} ms at 1080p`,
  );
  hud.addCheck("lut", "The episode's lookup table costs no more than the colour curves");
  hud.addCheck("adapt", "Lamp out: the eye adjusts 90% of the way in 2–3 s");
  hud.addCheck("dark", "Darkness rule: faint shapes after adapting (run with &flames=0)");
  hud.addCheck("mood", "Fear deepens the vignette; a scare jolts the aberration");
  hud.addCheck("settings", "Settings turn grain and aberration off");
  new PerfOverlay(engine, scene);

  const result: S7Result = {
    quality,
    render: `${engine.getRenderWidth()}×${engine.getRenderHeight()}`,
    costs: {},
    steps: [],
  };
  (window as unknown as { spikeResult: S7Result }).spikeResult = result;
  const step = (name: string) => {
    result.steps.push(name);
    console.info(`[S7] ${name}`);
  };

  // Lamp-out timing: from the moment the lamp goes out to 90% of the way (in stops).
  let adapting: { start: number; from: number; t: number } | null = null;
  let fearTarget = 0;
  let sawFear = false;
  let sawScare = false;
  let grainOff = false;
  let aberrationOff = false;

  scene.onBeforeRenderObservable.add(() => {
    // Eyes adapt in real time whatever the frame rate: a slow or stalled frame must not
    // slow adaptation down (the smoothing is exponential, so long steps are safe).
    const dt = Math.min(engine.getDeltaTime() / 1000, 1);
    const t = performance.now() / 1000;
    const flicker = 0.9 + 0.06 * Math.sin(t * 7.3) + 0.04 * Math.sin(t * 13.1);
    lamp.light.intensity = lampOn ? 14 * flicker : 0;
    const mood = atmosphere.mood;
    mood.fear += (fearTarget - mood.fear) * Math.min(1, dt * 1.5);
    const light = lightAtEye();
    atmosphere.update(dt, light);

    const ip = pipeline.main.imageProcessing;
    if (mood.fear > 0.9 && ip.vignetteWeight > 3.5) sawFear = true;
    if (mood.scare > 0.5 && pipeline.main.chromaticAberration.aberrationAmount > 20)
      sawScare = true;
    hud.check("mood", sawFear && sawScare);
    hud.check("settings", grainOff && aberrationOff);

    if (adapting) {
      adapting.t += dt;
      const target = Math.log(atmosphere.eye.exposure / adapting.from);
      const goal = Math.log(adapting.start / adapting.from);
      if (goal > 0 && target / goal >= 0.9) {
        result.adaptSeconds = adapting.t;
        hud.check("adapt", adapting.t >= 2 && adapting.t <= 3.2);
        step(`eye adapted in ${adapting.t.toFixed(2)} s`);
        adapting = null;
      }
    }

    hud.setReadout([
      `quality ${quality} · render ${engine.getRenderWidth()}×${engine.getRenderHeight()} · ${darkHall ? "flames out" : "flames lit"}`,
      `lamp ${lampOn ? "on" : "off"} · light at eye ${light.toFixed(3)} · exposure ${atmosphere.eye.exposure.toFixed(2)} (brightness ${atmosphere.settings.brightness >= 0 ? "+" : ""}${atmosphere.settings.brightness.toFixed(1)} stops)`,
      `fear ${mood.fear.toFixed(2)} · vignette ${ip.vignetteWeight.toFixed(2)} · grain ${atmosphere.settings.grain ? pipeline.main.grain.intensity : "off"} · aberration ${atmosphere.settings.aberration ? pipeline.main.chromaticAberration.aberrationAmount.toFixed(1) : "off"}`,
      `grade ${atmosphere.gradeMode}`,
      `costs ${
        Object.entries(result.costs)
          .map(([k, v]) => `${k} ${v.toFixed(2)}`)
          .join(" · ") || "press B"
      }`,
      `adapt ${result.adaptSeconds?.toFixed(2) ?? "–"} s · dark luma ${result.darkLuma?.toFixed(3) ?? "–"}`,
    ]);
  });

  const setLamp = (on: boolean) => {
    lampOn = on;
    if (!on) {
      const start = targetExposure(lightAtEye(), atmosphere.baseExposure, atmosphere.maxExposure);
      adapting = { start, from: atmosphere.eye.exposure, t: 0 };
    }
    step(`lamp ${on ? "on" : "off"}`);
  };

  const modes: GradeMode[] = ["lut", "curves", "off"];
  const press = (code: string) => {
    if (code === "KeyF") setLamp(!lampOn);
    if (code === "KeyT") fearTarget = fearTarget > 0 ? 0 : 1;
    if (code === "KeyX") atmosphere.scare();
    if (code === "KeyG") {
      atmosphere.settings.grain = !atmosphere.settings.grain;
      if (!atmosphere.settings.grain) grainOff = true;
    }
    if (code === "KeyC") {
      atmosphere.settings.aberration = !atmosphere.settings.aberration;
      if (!atmosphere.settings.aberration) aberrationOff = true;
    }
    if (code === "KeyL")
      atmosphere.gradeMode = modes[(modes.indexOf(atmosphere.gradeMode) + 1) % modes.length];
    if (code === "BracketLeft" || code === "BracketRight") {
      const b = atmosphere.settings.brightness + (code === "BracketRight" ? 0.25 : -0.25);
      atmosphere.settings.brightness = Math.max(-1, Math.min(1, b));
    }
    if (code === "KeyB") void bench();
  };
  window.addEventListener("keydown", (e) => press(e.code));

  const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
  const meanFrameMs = async (ms: number) => {
    const frames: number[] = [];
    const o = scene.onAfterRenderObservable.add(() => frames.push(engine.getDeltaTime()));
    await wait(ms);
    o.remove();
    return frames.reduce((s, x) => s + x, 0) / Math.max(1, frames.length);
  };

  /**
   * Each effect A/B against the same frame without it, alternating four times so
   * thermal drift cancels out (S5 found single samples drift by ±2 ms).
   */
  const bench = async () => {
    const ip = pipeline.main.imageProcessing;
    const s = atmosphere.settings;
    const look = (on: boolean) => {
      s.grain = on;
      s.aberration = on;
      ip.vignetteEnabled = on;
      pipeline.main.bloomEnabled = on;
      atmosphere.gradeMode = on ? "lut" : "off";
    };
    const effects: [string, (on: boolean) => void][] = [
      ["look", look],
      ["grain", (on) => (s.grain = on)],
      ["aberration", (on) => (s.aberration = on)],
      ["bloom", (on) => (pipeline.main.bloomEnabled = on)],
      ["vignette", (on) => (ip.vignetteEnabled = on)],
      ["lut", (on) => (atmosphere.gradeMode = on ? "lut" : "off")],
      ["curves", (on) => (atmosphere.gradeMode = on ? "curves" : "off")],
    ];
    step("bench start");
    look(true);
    for (const [name, set] of effects) {
      const on: number[] = [];
      const off: number[] = [];
      for (let i = 0; i < 4; i++) {
        set(true);
        await wait(400);
        on.push(await meanFrameMs(1500));
        set(false);
        await wait(400);
        off.push(await meanFrameMs(1500));
      }
      set(true);
      const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;
      result.costs[name] = mean(on) - mean(off);
      step(`cost ${name} ${result.costs[name].toFixed(2)} ms`);
    }
    look(true);
    // Costs scale with pixels: compare against the budget at 1080p.
    const scale = (1920 * 1080) / (engine.getRenderWidth() * engine.getRenderHeight());
    hud.check("cost", result.costs.look * scale < LOOK_BUDGET_MS);
    hud.check("lut", result.costs.lut <= result.costs.curves + 0.2);
    step("bench done");
  };

  /** 95th-percentile sRGB brightness of the middle third of the frame (post-processing included). */
  const middleLuma = async (): Promise<number> => {
    const width = engine.getRenderWidth();
    const height = engine.getRenderHeight();
    const url = await CreateScreenshotAsync(engine, camera, { width, height }, "image/png");
    const image = new Image();
    image.src = url;
    await image.decode();
    const c = document.createElement("canvas");
    c.width = width;
    c.height = height;
    const ctx = c.getContext("2d") as CanvasRenderingContext2D;
    ctx.drawImage(image, 0, 0);
    const data = ctx.getImageData(width / 3, height / 3, width / 3, height / 3).data;
    const values = new Float32Array(data.length / 4);
    for (let i = 0; i < data.length; i += 4) {
      values[i / 4] = (0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2]) / 255;
    }
    values.sort();
    return values[Math.floor(values.length * 0.95)];
  };

  if (import.meta.env.DEV)
    (window as unknown as { spike: unknown }).spike = {
      scene,
      player,
      atmosphere,
      pipeline,
      shot: (name: string) => saveShot(engine, camera, name),
      middleLuma,
    };

  if (params.get("auto") === "1") {
    void (async () => {
      await wait(4000);
      if (import.meta.env.DEV) await saveShot(engine, camera, `s7_${quality}_look`);
      // Stand about 1.5–2 m from the coffin and its stand for the darkness rule.
      if (darkHall) player.teleport(new Vector3(0, 0, -1.9), 0);
      await wait(500);
      setLamp(false);
      await wait(5000);
      if (darkHall) {
        result.darkLuma = await middleLuma();
        hud.check("dark", result.darkLuma >= DARK_LUMA.min && result.darkLuma <= DARK_LUMA.max);
        step(`dark luma ${result.darkLuma.toFixed(3)}`);
      }
      if (import.meta.env.DEV)
        await saveShot(engine, camera, `s7_${quality}_lamp_off${darkHall ? "_dark" : ""}`);
      setLamp(true);
      await wait(1500);
      press("KeyT");
      await wait(3000);
      press("KeyX");
      await wait(100);
      if (import.meta.env.DEV) await saveShot(engine, camera, `s7_${quality}_fear_scare`);
      press("KeyT");
      for (const key of ["KeyG", "KeyC", "KeyG", "KeyC"]) {
        press(key);
        await wait(300);
      }
      if (params.get("bench") === "1") await bench();
      step("auto run done");
    })();
  } else if (params.get("bench") === "1") void wait(4000).then(bench);

  engine.runRenderLoop(() => scene.render());
}
