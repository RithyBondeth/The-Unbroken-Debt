/**
 * Touch controls preview (no WebGPU needed): the real controls on the real input,
 * with a log of the keys, clicks, movement and look they produce, and the pause
 * menu's settings panel. Open /tests/browser/touch.html in a phone or tablet
 * browser, or with touch emulation in the desktop browser's device toolbar.
 */
import { KeyboardMouseInput } from "@/player/InputSource";
import { DEFAULT_GRAPHICS } from "@/render/graphicsSettings";
import { PauseMenu } from "@/ui/html/PauseMenu";
import { TouchControls, type TouchState } from "@/ui/html/TouchControls";

const canvas = document.getElementById("game") as HTMLCanvasElement;
const log = document.querySelector<HTMLElement>(".touch-log")!;
const input = new KeyboardMouseInput(canvas, 0.0022);
input.enableTouch();
const controls = new TouchControls(input);
const state: TouchState = { playing: true, bookRaised: false, episode: 1 };
const events: string[] = [];
const look = { yaw: 0, pitch: 0 };
const move = { x: 0, z: 0, hurry: false, crouch: false };
let yaw = 0;
let pitch = 0;

const note = (line: string) => {
  events.unshift(line);
  events.length = Math.min(events.length, 6);
};
window.addEventListener("keydown", (e) => note(`keydown ${e.code}`));
window.addEventListener("keyup", (e) => note(`keyup   ${e.code}`));
window.addEventListener("mousedown", (e) => note(`mousedown button ${e.button}`));
window.addEventListener("mouseup", (e) => note(`mouseup   button ${e.button}`));

const pause = new PauseMenu();
const settings = structuredClone(DEFAULT_GRAPHICS);

document.querySelector(".touch-preview-bar")!.addEventListener("click", (event) => {
  const button = (event.target as HTMLElement).closest("button");
  if (!button) return;
  if (button.dataset.episode) state.episode = Number(button.dataset.episode);
  if (button.hasAttribute("data-book")) state.bookRaised = !state.bookRaised;
  if (button.hasAttribute("data-pause"))
    pause.open({
      resume: () => pause.close(),
      restart: null,
      quit: () => pause.close(),
      settings: {
        graphics: settings,
        loaded: structuredClone(DEFAULT_GRAPHICS),
        device: { quality: "low", formFactor: "phone" },
        sensitivity: input.sensitivity,
        invertY: input.invertY,
        touch: true,
        onGraphics: (next) => Object.assign(settings, next),
        onLook: (sensitivity, invertY) => {
          input.sensitivity = sensitivity;
          input.invertY = invertY;
        },
      },
    });
});
window.addEventListener("keydown", (e) => {
  if (e.code === "Escape" && pause.isOpen) pause.back();
  else if (e.code === "Escape") note("(game would pause)");
});

const frame = () => {
  controls.update(state);
  input.readMove(move);
  input.consumeLook(look);
  yaw += look.yaw;
  pitch += look.pitch;
  log.textContent = [
    `engaged ${input.pointerLocked} · episode ${state.episode} · book ${state.bookRaised}`,
    `move x ${move.x.toFixed(2)} z ${move.z.toFixed(2)} hurry ${move.hurry} crouch ${move.crouch}`,
    `look yaw ${yaw.toFixed(2)} pitch ${pitch.toFixed(2)}`,
    ...events,
  ].join("\n");
  requestAnimationFrame(frame);
};
frame();
(window as unknown as { touchPreview: unknown }).touchPreview = { input, state, events };
