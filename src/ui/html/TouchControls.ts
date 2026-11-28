import "./touch.css";
import type { KeyboardMouseInput } from "@/player/InputSource";

/** What the controls need to know about the game each frame. */
export interface TouchState {
  /** Sora can be steered (no cutscene); otherwise only the menus show. */
  playing: boolean;
  /** The sketchbook is up: its page buttons replace the action buttons. */
  bookRaised: boolean;
  episode: number;
}

/** The stick knob travels this far (CSS px); pushing a thumb past the rim hurries. */
const STICK_RADIUS = 56;
const STICK_DEAD_ZONE = 0.12;
const HURRY_PAST_RIM = 1.15;

interface Button {
  label: string;
  /** Keyboard code sent while held (keydown on press, keyup on release). */
  key?: string;
  /** Mouse button sent while held (right mouse raises the lamp, left pours oil). */
  mouse?: 0 | 2;
  action?: "crouch" | "row" | "keys";
  /** Episodes that show it (all when absent). */
  episodes?: number[];
  hint?: string;
  className?: string;
}

const TOP: Button[] = [
  { label: "Pause", key: "Escape", hint: "Esc" },
  { label: "Notebook", key: "KeyQ", hint: "Q" },
  { label: "Satchel", key: "Tab", hint: "Tab" },
  { label: "Watch", key: "KeyT", hint: "T", episodes: [1] },
];

const ACTIONS: Button[] = [
  { label: "Use", key: "KeyE", hint: "E", className: "touch-primary" },
  { label: "Lamp", key: "KeyF", hint: "F" },
  { label: "Crouch", action: "crouch", hint: "C" },
  { label: "Raise", mouse: 2, hint: "R-click" },
];

const EXTRAS: Button[] = [
  { label: "Breath", key: "Space", hint: "Space", episodes: [2] },
  { label: "Shutter", key: "KeyX", hint: "X", episodes: [2, 3] },
  { label: "Throw", key: "KeyG", hint: "G", episodes: [2] },
  { label: "Refill", key: "KeyR", hint: "R", episodes: [2, 3] },
  { label: "Row", action: "row", hint: "A / D", episodes: [3] },
];

const BOOK: Button[] = [
  { label: "◀", key: "KeyA", hint: "A" },
  { label: "Read", key: "KeyR", hint: "R" },
  { label: "▶", key: "KeyD", hint: "D" },
  { label: "Close", key: "KeyQ", hint: "Q" },
];

/**
 * Every key and click the game listens for, for moments the main buttons don't
 * cover: four rows of six.
 */
const KEYPAD: Button[] = [
  ...[
    ["Escape", "Tab", "KeyQ", "KeyE", "KeyR", "KeyT"],
    ["KeyF", "KeyX", "KeyG", "KeyA", "KeyD", "Enter"],
    ["Digit1", "Digit2", "Digit3", "Digit4", "Digit5", "Space"],
    ["ArrowLeft", "ArrowUp", "ArrowDown", "ArrowRight"],
  ]
    .flat()
    .map((key) => ({ label: keyName(key), key })),
  { label: "L-click", mouse: 0 },
  { label: "R-click", mouse: 2 },
];

/**
 * On-screen controls for phones and tablets: a stick that appears under the
 * left thumb, drag-to-look on the rest of the screen, and buttons that stand in
 * for the keys and mouse buttons. Buttons send the same keyboard and mouse
 * events a keyboard would, so every system in every episode answers them as it
 * already answers the keyboard, holds included (hold E, hold breath).
 *
 * The layer sits under the game's panels and menus (they take their own taps);
 * the keypad, for the rare keyboard-only moment, sits above everything.
 */
export class TouchControls {
  private readonly root = document.createElement("div");
  private readonly stick = document.createElement("div");
  private readonly knob = document.createElement("div");
  private readonly keypad = document.createElement("div");
  private readonly keypadToggle = document.createElement("button");
  private readonly crouchButtons: HTMLButtonElement[] = [];
  private readonly abort = new AbortController();
  private stickId: number | null = null;
  private stickX = 0;
  private stickY = 0;
  private lookId: number | null = null;
  private lookX = 0;
  private lookY = 0;
  private rowNext: "KeyA" | "KeyD" = "KeyA";
  private shown = "";

  constructor(private readonly input: KeyboardMouseInput) {
    const root = this.root;
    root.className = "touch";
    root.setAttribute("aria-hidden", "true");
    this.stick.className = "touch-stick";
    this.stick.hidden = true;
    this.knob.className = "touch-stick-knob";
    this.stick.append(this.knob);

    const rotate = document.createElement("p");
    rotate.className = "touch-rotate";
    rotate.textContent = "Turn your phone sideways to play";

    root.append(
      this.stick,
      rotate,
      this.group("touch-top", TOP),
      this.group("touch-extras", EXTRAS),
      this.group("touch-actions", ACTIONS),
      this.group("touch-book", BOOK),
    );

    this.keypad.className = "touch-keypad";
    this.keypad.hidden = true;
    for (const button of KEYPAD) this.keypad.append(this.button(button));
    this.keypad.addEventListener("touchstart", (e) => e.preventDefault(), {
      passive: false,
      signal: this.abort.signal,
    });
    this.keypadToggle.type = "button";
    this.keypadToggle.className = "touch-keypad-toggle";
    this.keypadToggle.textContent = "Keys";
    this.keypadToggle.setAttribute("aria-expanded", "false");
    this.keypadToggle.tabIndex = -1;
    this.listen(this.keypadToggle, { label: "Keys", action: "keys" });

    document.body.append(root, this.keypad, this.keypadToggle);
    this.watchSurface();
  }

  /** Shows the buttons that fit the moment; cheap enough to call every frame. */
  update(state: TouchState): void {
    const key = `${state.playing}|${state.bookRaised}|${state.episode}`;
    if (key === this.shown) return;
    this.shown = key;
    this.root.dataset.playing = String(state.playing);
    this.root.dataset.book = String(state.bookRaised);
    for (const node of this.root.querySelectorAll<HTMLElement>("[data-episodes]"))
      node.hidden = !node.dataset.episodes!.split(",").includes(String(state.episode));
    if (!state.playing) this.releaseStick();
  }

  dispose(): void {
    this.abort.abort();
    this.root.remove();
    this.keypad.remove();
    this.keypadToggle.remove();
  }

  private group(className: string, buttons: Button[]): HTMLElement {
    const group = document.createElement("div");
    group.className = `touch-group ${className}`;
    for (const button of buttons) group.append(this.button(button));
    return group;
  }

  private button(spec: Button): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button";
    button.tabIndex = -1;
    button.className = `touch-button ${spec.className ?? ""}`.trim();
    button.textContent = spec.label;
    if (spec.hint) {
      const hint = document.createElement("kbd");
      hint.textContent = spec.hint;
      button.append(hint);
    }
    if (spec.episodes) button.dataset.episodes = spec.episodes.join(",");
    if (spec.action === "crouch") {
      button.setAttribute("aria-pressed", "false");
      this.crouchButtons.push(button);
    }
    this.listen(button, spec);
    return button;
  }

  /** A button press: hold semantics for keys and mouse buttons, taps for the rest. */
  private listen(button: HTMLButtonElement, spec: Button): void {
    const signal = this.abort.signal;
    let held: number | null = null;
    // Some buttons (the keypad) live outside the play surface: cancel their touches
    // too, or the browser follows each tap with a left click the game would hear.
    button.addEventListener("touchstart", (e) => e.preventDefault(), { passive: false, signal });
    const release = () => {
      if (held === null) return;
      held = null;
      button.classList.remove("pressed");
      if (spec.key) sendKey("keyup", spec.key);
      if (spec.mouse !== undefined) sendMouse("mouseup", spec.mouse);
    };
    button.addEventListener(
      "pointerdown",
      (event) => {
        // Not stopped: the window still hears it (sound unlocks on a gesture); the
        // play surface ignores presses that land on a button.
        event.preventDefault();
        if (held !== null) return;
        held = event.pointerId;
        button.setPointerCapture?.(event.pointerId);
        button.classList.add("pressed");
        // Touching the controls is the touch version of clicking into the game.
        if (spec.action !== "keys" && spec.key !== "Escape") void this.input.lockPointer();
        if (spec.key) sendKey("keydown", spec.key);
        if (spec.mouse !== undefined) sendMouse("mousedown", spec.mouse);
        if (spec.action === "crouch") this.setCrouch(this.input.toggleTouchCrouch());
        if (spec.action === "row") {
          sendKey("keydown", this.rowNext);
          sendKey("keyup", this.rowNext);
          this.rowNext = this.rowNext === "KeyA" ? "KeyD" : "KeyA";
        }
        if (spec.action === "keys") this.toggleKeypad();
      },
      { signal },
    );
    button.addEventListener("pointerup", release, { signal });
    button.addEventListener("pointercancel", release, { signal });
    button.addEventListener("lostpointercapture", release, { signal });
  }

  private setCrouch(crouched: boolean): void {
    for (const button of this.crouchButtons) button.setAttribute("aria-pressed", String(crouched));
  }

  private toggleKeypad(): void {
    const open = this.keypad.hidden;
    this.keypad.hidden = !open;
    this.keypadToggle.setAttribute("aria-expanded", String(open));
  }

  /** Stick on the left of the screen, look on the right (and anywhere a stick is already down). */
  private watchSurface(): void {
    const root = this.root;
    const signal = this.abort.signal;
    // No compatibility mouse events, double-tap zoom or long-press menus from the
    // play surface: a tap must not reach the game as a left click (pour oil).
    root.addEventListener("touchstart", (e) => e.preventDefault(), { passive: false, signal });
    root.addEventListener("contextmenu", (e) => e.preventDefault(), { signal });
    root.addEventListener(
      "pointerdown",
      (event) => {
        if (event.target !== root) return;
        event.preventDefault();
        void this.input.lockPointer();
        if (this.stickId === null && event.clientX < window.innerWidth * 0.42) {
          this.stickId = event.pointerId;
          this.stickX = event.clientX;
          this.stickY = event.clientY;
          this.stick.style.translate = `${this.stickX}px ${this.stickY}px`;
          this.knob.style.translate = "0 0";
          this.stick.hidden = false;
        } else if (this.lookId === null) {
          this.lookId = event.pointerId;
          this.lookX = event.clientX;
          this.lookY = event.clientY;
        } else return;
        root.setPointerCapture?.(event.pointerId);
      },
      { signal },
    );
    root.addEventListener(
      "pointermove",
      (event) => {
        if (event.pointerId === this.stickId) this.moveStick(event.clientX, event.clientY);
        else if (event.pointerId === this.lookId) {
          this.input.addTouchLook(event.clientX - this.lookX, event.clientY - this.lookY);
          this.lookX = event.clientX;
          this.lookY = event.clientY;
        }
      },
      { signal },
    );
    const end = (event: PointerEvent) => {
      if (event.pointerId === this.stickId) this.releaseStick();
      if (event.pointerId === this.lookId) this.lookId = null;
    };
    root.addEventListener("pointerup", end, { signal });
    root.addEventListener("pointercancel", end, { signal });
    window.addEventListener("blur", () => this.releaseStick(), { signal });
  }

  private moveStick(x: number, y: number): void {
    const {
      x: mx,
      z: mz,
      hurry,
      knobX,
      knobY,
    } = stickVector(x - this.stickX, y - this.stickY, STICK_RADIUS);
    this.knob.style.translate = `${knobX}px ${knobY}px`;
    this.knob.classList.toggle("hurry", hurry);
    this.input.setTouchMove(mx, mz, hurry);
  }

  private releaseStick(): void {
    this.stickId = null;
    this.stick.hidden = true;
    this.knob.classList.remove("hurry");
    this.input.setTouchMove(0, 0, false);
  }
}

/**
 * Stick offset (CSS px, screen down = +y) to movement intent: x strafes right,
 * z walks forward; a dead zone in the middle, and hurry once the thumb is
 * pushed past the rim. Pure, for tests.
 */
export function stickVector(
  dx: number,
  dy: number,
  radius: number,
): { x: number; z: number; hurry: boolean; knobX: number; knobY: number } {
  const distance = Math.hypot(dx, dy);
  const reach = distance / radius;
  const clamped = Math.min(1, reach);
  const scale = distance > 0 ? (clamped * radius) / distance : 0;
  const knobX = dx * scale;
  const knobY = dy * scale;
  if (reach < STICK_DEAD_ZONE) return { x: 0, z: 0, hurry: false, knobX, knobY };
  // Rescale past the dead zone so walking starts gently instead of with a jump.
  const strength = (clamped - STICK_DEAD_ZONE) / (1 - STICK_DEAD_ZONE);
  return {
    x: (dx / distance) * strength,
    z: (-dy / distance) * strength,
    hurry: reach > HURRY_PAST_RIM,
    knobX,
    knobY,
  };
}

/** The `key` value a keyboard would send with a code. */
export function keyFor(code: string): string {
  if (code.startsWith("Key")) return code.slice(3).toLowerCase();
  if (code.startsWith("Digit")) return code.slice(5);
  if (code === "Space") return " ";
  return code;
}

function keyName(code: string): string {
  const names: Record<string, string> = {
    Escape: "Esc",
    Space: "Space",
    Tab: "Tab",
    Enter: "Enter",
    ArrowLeft: "←",
    ArrowRight: "→",
    ArrowUp: "↑",
    ArrowDown: "↓",
  };
  return names[code] ?? keyFor(code).toUpperCase();
}

/** Keys go where the keyboard's would: the focused element, bubbling up to the window. */
function sendKey(type: "keydown" | "keyup", code: string): void {
  const target = (document.activeElement as HTMLElement | null) ?? document.body;
  target.dispatchEvent(
    new KeyboardEvent(type, { code, key: keyFor(code), bubbles: true, cancelable: true }),
  );
}

function sendMouse(type: "mousedown" | "mouseup", button: 0 | 2): void {
  window.dispatchEvent(
    new MouseEvent(type, { button, buttons: type === "mousedown" ? 1 << button : 0 }),
  );
}
