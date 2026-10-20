import type { MoveIntent } from "./movement";

/** Where the player's intent comes from: keyboard and mouse, a gamepad, or a test bot. */
export interface InputSource {
  /** Movement intent for this frame. */
  readMove(out: MoveIntent): MoveIntent;
  /** Look change since the last call, in radians (positive yaw turns right, positive pitch looks down). */
  consumeLook(out: { yaw: number; pitch: number }): void;
  dispose(): void;
}

/**
 * Keyboard and mouse. Bindings use physical key codes so they work on any
 * layout (Controls and Interface, section 10). Mouse look needs pointer lock,
 * requested when the canvas is clicked.
 */
export class KeyboardMouseInput implements InputSource {
  sensitivity: number;
  invertY = false;
  /** Crouch as a toggle instead of hold (a setting in the Controls doc). */
  crouchToggle = false;

  private readonly held = new Set<string>();
  private crouchLatched = false;
  private lookX = 0;
  private lookY = 0;
  private readonly abort = new AbortController();

  constructor(
    private readonly canvas: HTMLCanvasElement,
    sensitivity: number,
  ) {
    this.sensitivity = sensitivity;
    const signal = this.abort.signal;

    window.addEventListener("keydown", (e) => this.onKey(e, true), { signal });
    window.addEventListener("keyup", (e) => this.onKey(e, false), { signal });
    window.addEventListener("blur", () => this.held.clear(), { signal });
    canvas.addEventListener("click", () => void this.requestPointerLock(), { signal });
    document.addEventListener(
      "mousemove",
      (e) => {
        if (document.pointerLockElement !== canvas) return;
        this.lookX += e.movementX;
        this.lookY += e.movementY;
      },
      { signal },
    );
  }

  get pointerLocked(): boolean {
    return document.pointerLockElement === this.canvas;
  }

  readMove(out: MoveIntent): MoveIntent {
    const h = this.held;
    out.x = (h.has("KeyD") ? 1 : 0) - (h.has("KeyA") ? 1 : 0);
    out.z = (h.has("KeyW") ? 1 : 0) - (h.has("KeyS") ? 1 : 0);
    out.hurry = h.has("ShiftLeft") || h.has("ShiftRight");
    const crouchHeld = h.has("KeyC") || h.has("ControlLeft");
    out.crouch = this.crouchToggle ? this.crouchLatched : crouchHeld;
    return out;
  }

  consumeLook(out: { yaw: number; pitch: number }): void {
    out.yaw = this.lookX * this.sensitivity;
    out.pitch = this.lookY * this.sensitivity * (this.invertY ? -1 : 1);
    this.lookX = 0;
    this.lookY = 0;
  }

  dispose(): void {
    this.abort.abort();
  }

  private onKey(e: KeyboardEvent, down: boolean): void {
    if (e.repeat) return;
    if (down) this.held.add(e.code);
    else this.held.delete(e.code);
    if (down && (e.code === "KeyC" || e.code === "ControlLeft")) {
      this.crouchLatched = !this.crouchLatched;
    }
    // Stop the page scrolling or the browser acting on game keys while playing.
    if (this.pointerLocked && e.code !== "Escape") e.preventDefault();
  }

  private async requestPointerLock(): Promise<void> {
    if (this.pointerLocked) return;
    try {
      await this.canvas.requestPointerLock({ unadjustedMovement: true });
    } catch {
      // Some platforms reject raw input; fall back to accelerated movement.
      await this.canvas.requestPointerLock();
    }
  }
}
