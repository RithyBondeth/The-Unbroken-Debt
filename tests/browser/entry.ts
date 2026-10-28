/** Test the real entry screen without loading assets or touching player saves. */
import { ScreenFade } from "../../src/ui/html/StoryUi";
import { KeyboardMouseInput } from "../../src/player/InputSource";

async function verify(): Promise<void> {
  if (!import.meta.env.DEV) return;
  const canvas = document.getElementById("game") as HTMLCanvasElement;
  const results = document.getElementById("results")!;
  const input = new KeyboardMouseInput(canvas, 0.0022);
  const fade = new ScreenFade();
  const context = new AudioContext();
  let activations = 0;
  let downstreamEnter = 0;
  let activationHadGesture = false;
  window.addEventListener("keydown", (event) => {
    if (event.key === "Enter") downstreamEnter++;
  });
  const waiting = fade.waitForEnter(() => {
    activations++;
    activationHadGesture = navigator.userActivation.isActive;
    void context.resume();
    void input.lockPointer();
    // Neither repeated keys nor a second activation during the fade may start twice.
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", repeat: true }));
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
  });
  for (const options of [
    { key: "a" },
    { key: "Enter", repeat: true },
    { key: "Enter", isComposing: true },
    { key: "Enter", ctrlKey: true },
  ])
    window.dispatchEvent(new KeyboardEvent("keydown", options));
  if (Number(activations) !== 0) throw new Error("Unrelated or held keys started the screen");
  await waiting;
  const focusRestored = document.activeElement === canvas;
  const entryCleared = !document.querySelector(".waiting, .entering, .story-entry");
  const before = downstreamEnter;
  window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
  const listenerRemoved = downstreamEnter === before + 1;
  const passed =
    activations === 1 && activationHadGesture && focusRestored && entryCleared && listenerRemoved;
  const lines = [
    `Activations: ${activations} · real gesture: ${activationHadGesture}`,
    `Focus restored: ${focusRestored} · entry cleared: ${entryCleared}`,
    `Enter listener removed: ${listenerRemoved} · audio: ${context.state}`,
    `Pointer captured: ${input.pointerLocked}`,
  ];
  results.textContent = `${passed ? "PASS" : "FAIL"}\n${lines.join("\n")}`;
  console.info(results.textContent);
  // Ordinary story cards must keep their original styling after entry.
  await fade.show({
    title: passed ? "Entry verified" : "Entry failed",
    body: lines.join(" · "),
    button: "Preview again",
  });
  await context.close();
  input.dispose();
  location.reload();
}

void verify();
