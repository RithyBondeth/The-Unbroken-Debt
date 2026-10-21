import type { WebGPUEngine } from "@babylonjs/core/Engines/webgpuEngine";
import { PointLight } from "@babylonjs/core/Lights/pointLight";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { KeyboardMouseInput, type InputSource } from "../../player/InputSource";
import type { MoveIntent } from "../../player/movement";
import { PlayerController } from "../../player/PlayerController";
import { PerfOverlay } from "../../debug/PerfOverlay";
import { saveShot } from "../../debug/saveShot";
import { getPreset, isQualityName, type QualityName } from "../../render/QualityPresets";
import type { DeviceProfile } from "../../render/DeviceProfile";
import { FLAME_COLOR } from "../../render/RenderSetup";
import { createHallEnvironment, lockRenderSize } from "../hallEnvironment";
import { SpikeHud } from "../SpikeHud";
import { Sketchbook } from "../../ui/diegetic/Sketchbook";
import { loadSketchbookFonts } from "../../ui/diegetic/fonts";
import { SECTIONS } from "../../ui/diegetic/sketchbookContent";
import { PAGE_MM } from "../../ui/diegetic/PagePainter";
import { EP1_SKETCHBOOK } from "../../episodes/ep1/data/sketchbook";
import { runRenderLoop } from "../../render/renderLoop";
import { renderStallNotice } from "../../ui/html/RenderStallNotice";

/** Results exposed for automated checks (`window.spikeResult`). */
export interface S5Result {
  quality: QualityName;
  textureHeight: number;
  readingLight: number;
  /** Body text height (em) on screen, scaled to a 1080p screen. */
  bodyPx1080: number;
  largeTextPx1080?: number;
  paintMsAvg: number;
  paintMsMax: number;
  turnMsMax: number;
  khmerFont: boolean;
  steps: string[];
}

/** Smallest body text we accept, in pixels at 1080p (common console accessibility guidance). */
const MIN_TEXT_PX = 28;

const TEXTURE_HEIGHT: Record<QualityName, number> = {
  low: 1024,
  medium: 1536,
  high: 2048,
  ultra: 2048,
};

/** Movement with the strafe keys taken over by page turning while the book is open. */
class ReadingInput implements InputSource {
  reading = false;
  constructor(private readonly inner: InputSource) {}
  readMove(out: MoveIntent): MoveIntent {
    this.inner.readMove(out);
    if (this.reading) out.x = 0;
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
 * Spike S5 (Development Plan, section 2.2): can a 3D book show readable,
 * updatable pages? Sora's sketchbook in the dark S2 hall, lit by her lamp,
 * under the full post-processing: open, turn pages, jump by tab, watch a new
 * note being written, and measure the text size on screen.
 * URL: `?spike=s5` (add `&auto=1` for a scripted run, `&quality=low|…`,
 * `&reading=<intensity>` for the book's light, `&res=1080` to render at exactly 1080p).
 */
export async function runS5(
  engine: WebGPUEngine,
  params: URLSearchParams,
  device: DeviceProfile,
): Promise<void> {
  const canvas = engine.getRenderingCanvas() as HTMLCanvasElement;
  const qualityParam = params.get("quality");
  const quality: QualityName = isQualityName(qualityParam) ? qualityParam : device.quality;
  const preset = getPreset(quality);
  const textureHeight = Number(params.get("tex")) || TEXTURE_HEIGHT[quality];

  const res = Number(params.get("res"));
  if (res >= 360) lockRenderSize(engine, res);

  await loadSketchbookFonts();
  const { scene, camera, hall, lamp } = await createHallEnvironment(engine, preset);

  const keyboard = new KeyboardMouseInput(canvas, 0.0022);
  const input = new ReadingInput(keyboard);
  const player = new PlayerController(scene, camera, input, hall.spawn);

  const sketchbook = new Sketchbook(scene, EP1_SKETCHBOOK, textureHeight, camera);
  // Drawn after the room with its own depth, so the book never sinks into a wall.
  sketchbook.book.setRenderingGroup(1);
  scene.setRenderingAutoClearDepthStencil(1, true, true, true);

  // A lamp 30 cm from paper is about 50 times brighter than the room at 2 m, which the
  // fixed exposure clips to white. The book gets its own light from the lamp's side,
  // tuned so the paper reads as lamp-lit cream; the room's lamp no longer reaches it.
  const readingLight = new PointLight("lamp_reading", new Vector3(-0.3, -0.12, 0.12), scene);
  readingLight.parent = camera;
  readingLight.diffuse = FLAME_COLOR.clone();
  readingLight.includedOnlyMeshes = sketchbook.book.meshes;
  lamp.light.excludedMeshes = [...sketchbook.book.meshes];
  let readingIntensity = Number(params.get("reading")) || 0.22;
  // Up to "the seventh night" (A2-05), plus the People test page.
  sketchbook.restore([
    "SB-01",
    "SB-02",
    "SB-03",
    "SB-04",
    "SB-05",
    "P-SORA",
    "P-YAYMEY",
    "P-VUTHY",
    "P-SOK",
  ]);
  // The first paints make the paper texture and warm up the fonts: not part of the budget.
  sketchbook.resetStats();

  const hud = new SpikeHud(
    "Spike S5 · Diegetic sketchbook",
    "Can a 3D book show readable, updatable pages?",
    [
      "Click to look",
      "WS move",
      "Q open/close",
      "A/D turn",
      "1–5 tabs",
      "N new note",
      "L large text",
      "G paper glow",
      "[ ] reading light",
      "F2 hide panel",
      "F3 stats",
    ],
  );
  hud.addCheck("open", "Q opens at the newest entry and closes again");
  hud.addCheck("turn", "A/D turn pages; 1–5 jump to a section by its tab");
  hud.addCheck("write", "N: the book turns to a new note and it is written in");
  hud.addCheck("readable", `Body text at least ${MIN_TEXT_PX} px tall at 1080p`);
  hud.addCheck("khmer", "Khmer names and places in Sora's hand (Freehand)");
  hud.addCheck("cost", "Page painting fits the frame: a turn under 8 ms, one page under 4 ms");
  new PerfOverlay(engine, scene);

  const result: S5Result = {
    quality,
    textureHeight,
    readingLight: readingIntensity,
    bodyPx1080: 0,
    paintMsAvg: 0,
    paintMsMax: 0,
    turnMsMax: 0,
    khmerFont: document.fonts.check('20px "Freehand"', "ផ្ទះ"),
    steps: [],
  };
  (window as unknown as { spikeResult: S5Result }).spikeResult = result;
  if (import.meta.env.DEV)
    (window as unknown as { spike: unknown }).spike = {
      scene,
      player,
      sketchbook,
      camera,
      shot: (name: string) => saveShot(engine, camera, name),
    };
  hud.check("khmer", result.khmerFont);

  let opened = false;
  let turned = false;
  let jumped = false;
  let writing: string | null = null;
  let largeText = false;
  let glow = false;
  const step = (name: string) => {
    result.steps.push(name);
    console.info(`[S5] ${name}`);
  };

  /** Body text height on screen, from the projected page height, scaled to 1080p. */
  const measureText = (): number => {
    const [bottom, top] = sketchbook.book.rightPageEdge();
    const width = engine.getRenderWidth();
    const height = engine.getRenderHeight();
    const viewport = camera.viewport.toGlobal(width, height);
    const transform = camera.getTransformationMatrix();
    const a = Vector3.Project(bottom, Matrix.IdentityReadOnly, transform, viewport);
    const b = Vector3.Project(top, Matrix.IdentityReadOnly, transform, viewport);
    const pagePx = Math.hypot(a.x - b.x, a.y - b.y);
    return ((sketchbook.painter.bodyFontMm * pagePx) / PAGE_MM.height) * (1080 / height);
  };

  scene.onBeforeRenderObservable.add(() => {
    const dt = Math.min(engine.getDeltaTime() / 1000, 1 / 20);
    sketchbook.update(dt);
    input.reading = sketchbook.isOpen;
    // The kerosene flame is never steady (Art Bible); the page flickers with it.
    const t = performance.now() / 1000;
    const flicker = 0.9 + 0.06 * Math.sin(t * 7.3) + 0.04 * Math.sin(t * 13.1);
    lamp.light.intensity = 14 * flicker;
    readingLight.intensity = readingIntensity * flicker;

    if (sketchbook.isOpen && !sketchbook.isBusy) {
      const px = measureText();
      if (largeText) result.largeTextPx1080 = px;
      else result.bodyPx1080 = px;
      hud.check("readable", result.bodyPx1080 >= MIN_TEXT_PX);
    }
    if (writing && !sketchbook.isBusy && sketchbook.isOpen) {
      step(`wrote ${writing}`);
      hud.check("write");
      writing = null;
    }
    const paints = sketchbook.paintMs;
    result.paintMsAvg = paints.reduce((s, x) => s + x, 0) / Math.max(1, paints.length);
    result.paintMsMax = Math.max(0, ...paints);
    result.turnMsMax = Math.max(result.turnMsMax, sketchbook.lastTurnMs);
    hud.check(
      "cost",
      paints.length > 0 && result.turnMsMax > 0 && result.turnMsMax < 8 && result.paintMsAvg < 4,
    );

    const pages = sketchbook.painter.pages.length;
    hud.setReadout([
      `quality ${quality} · page texture ${sketchbook.painter.textureWidth}×${textureHeight} · reading light ${readingIntensity.toFixed(2)} · render ${engine.getRenderWidth()}×${engine.getRenderHeight()}`,
      `book ${sketchbook.isOpen ? "open" : "closed"} · spread ${sketchbook.spread + 1}/${pages / 2} (${sketchbook.section}) · written ${sketchbook.written.size}`,
      `body text ${result.bodyPx1080.toFixed(1)} px at 1080p${result.largeTextPx1080 ? ` · large ${result.largeTextPx1080.toFixed(1)} px` : ""} (target ≥ ${MIN_TEXT_PX})`,
      `painting: page avg ${result.paintMsAvg.toFixed(2)} ms, max ${result.paintMsMax.toFixed(2)} ms · turn ${result.turnMsMax.toFixed(2)} ms`,
      `large text ${largeText ? "on" : "off"} · paper glow ${glow ? "on" : "off"} · Khmer font ${result.khmerFont ? "loaded" : "missing"}`,
    ]);
  });

  const press = (code: string) => {
    if (code === "KeyQ") {
      const wasOpen = sketchbook.isOpen;
      sketchbook.toggle();
      if (!wasOpen) {
        step(`open at spread ${sketchbook.spread + 1}`);
        opened = true;
      } else if (opened) {
        step("close");
        hud.check("open");
      }
    }
    if (!sketchbook.isOpen && code !== "KeyN") return;
    if (code === "KeyA" || code === "KeyD") {
      sketchbook.turn(code === "KeyD" ? 1 : -1);
      turned = true;
    }
    const digit = Number(code.replace("Digit", ""));
    if (code.startsWith("Digit") && digit >= 1 && digit <= SECTIONS.length) {
      sketchbook.goToSection(SECTIONS[digit - 1].id);
      jumped = true;
    }
    if (turned && jumped) hud.check("turn");
    if (code === "KeyN") {
      const next = sketchbook.nextUnwritten();
      if (next) {
        sketchbook.write(next);
        writing = next;
      }
    }
    if (code === "KeyL") {
      largeText = !largeText;
      sketchbook.setTextScale(largeText ? 1.3 : 1);
    }
    if (code === "KeyG") {
      glow = !glow;
      sketchbook.book.setPaperGlow(glow ? 0.07 : 0);
    }
    if (code === "BracketLeft" || code === "BracketRight") {
      readingIntensity = Math.max(0.01, readingIntensity * (code === "BracketRight" ? 1.25 : 0.8));
      result.readingLight = readingIntensity;
    }
  };
  window.addEventListener("keydown", (e) => press(e.code));

  if (params.get("auto") === "1") void autoRun(press, () => sketchbook.isBusy, step);
  runRenderLoop(engine, () => scene.render(), renderStallNotice);
}

/** Scripted run for automated checks: open, turn, jump, write, large text, close. */
async function autoRun(
  press: (code: string) => void,
  busy: () => boolean,
  step: (s: string) => void,
): Promise<void> {
  const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
  const settle = async () => {
    await wait(100);
    while (busy()) await wait(50);
    await wait(250);
  };
  await wait(1500);
  press("KeyQ");
  await settle();
  for (const code of ["KeyA", "KeyA", "KeyD", "KeyD", "KeyD", "Digit1", "Digit4", "Digit2"]) {
    press(code);
    await settle();
  }
  for (let i = 0; i < 3; i++) {
    press("KeyN");
    await settle();
  }
  press("KeyL");
  await settle();
  press("KeyL");
  await settle();
  press("KeyQ");
  await settle();
  step("auto run done");
}
