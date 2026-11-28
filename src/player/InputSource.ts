import type { MoveIntent } from "./movement";

/** Where the player's intent comes from: keyboard and mouse, a gamepad, or a test bot. */
export interface InputSource {
  /** Movement intent for this frame. */
  readMove(out: MoveIntent): MoveIntent;
  /** Look change since the last call, in radians (positive yaw turns right, positive pitch looks down). */
  consumeLook(out: { yaw: number; pitch: number }): void;
  dispose(): void;
}

/** Touch-drag look is this much faster than the same distance of mouse movement. */
export const TOUCH_LOOK_SCALE = 1.6;

/**
 * Keyboard and mouse, and the on-screen touch controls on phones and tablets.
 * Bindings use physical key codes so they work on any layout (Controls and
 * Interface, section 10). Mouse look needs pointer lock, requested when the
 * canvas is clicked.
 *
 * Touch has no pointer lock. With touch enabled, "locked" means engaged: the
 * player has touched the controls since the game last let go of the pointer
 * (opening the sketchbook, a reader or a cutscene calls exitPointerLock), so
 * every system that waits for the pointer to be captured works the same way.
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
  private touch = false;
  private touchEngaged = false;
  private touchMoveX = 0;
  private touchMoveZ = 0;
  private touchHurry = false;
  private touchCrouch = false;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    sensitivity: number,
  ) {
    this.sensitivity = sensitivity;
    const signal = this.abort.signal;

    window.addEventListener("keydown", (e) => this.onKey(e, true), { signal });
    window.addEventListener("keyup", (e) => this.onKey(e, false), { signal });
    window.addEventListener("blur", () => this.held.clear(), { signal });
    canvas.addEventListener("click", () => void this.lockPointer(), { signal });
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

  isHeld(code: string): boolean {
    return this.held.has(code);
  }

  /** Menus must not retain movement keys pressed before they took focus. */
  clear(): void {
    this.held.clear();
    this.lookX = 0;
    this.lookY = 0;
    this.touchMoveX = 0;
    this.touchMoveZ = 0;
    this.touchHurry = false;
  }

  get pointerLocked(): boolean {
    return document.pointerLockElement === this.canvas || (this.touch && this.touchEngaged);
  }

  /** Whether the on-screen touch controls drive Sora. */
  get touchEnabled(): boolean {
    return this.touch;
  }

  /**
   * Turns touch play on. Every place that lets go of the pointer for a menu or a
   * cutscene calls `document.exitPointerLock()`; with touch that also ends the
   * engagement, until the player touches the controls again.
   */
  enableTouch(): void {
    if (this.touch) return;
    this.touch = true;
    const exit = document.exitPointerLock?.bind(document);
    document.exitPointerLock = () => {
      this.touchEngaged = false;
      exit?.();
    };
  }

  /** The virtual stick: x strafes, z walks (-1 to 1 each); `hurry` when pushed to the rim. */
  setTouchMove(x: number, z: number, hurry: boolean): void {
    this.touchMoveX = x;
    this.touchMoveZ = z;
    this.touchHurry = hurry;
  }

  /** A drag on the look area, in CSS pixels. */
  addTouchLook(dx: number, dy: number): void {
    this.lookX += dx * TOUCH_LOOK_SCALE;
    this.lookY += dy * TOUCH_LOOK_SCALE;
  }

  /** The crouch button is a toggle: holding a thumb on it while walking is awkward. */
  toggleTouchCrouch(): boolean {
    this.touchCrouch = !this.touchCrouch;
    return this.touchCrouch;
  }

  get touchCrouched(): boolean {
    return this.touchCrouch;
  }

  readMove(out: MoveIntent): MoveIntent {
    const h = this.held;
    const keyX = (h.has("KeyD") ? 1 : 0) - (h.has("KeyA") ? 1 : 0);
    const keyZ = (h.has("KeyW") ? 1 : 0) - (h.has("KeyS") ? 1 : 0);
    out.x = Math.max(-1, Math.min(1, keyX + this.touchMoveX));
    out.z = Math.max(-1, Math.min(1, keyZ + this.touchMoveZ));
    out.hurry = h.has("ShiftLeft") || h.has("ShiftRight") || this.touchHurry;
    const crouchHeld = h.has("KeyC") || h.has("ControlLeft");
    out.crouch = (this.crouchToggle ? this.crouchLatched : crouchHeld) || this.touchCrouch;
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

  /** Mouse look needs pointer lock, requested from a player activation gesture. */
  async lockPointer(): Promise<void> {
    if (this.touch) {
      // Touch play has nothing to capture: being asked is enough to engage.
      this.touchEngaged = true;
      return;
    }
    if (this.pointerLocked) return;
    try {
      await this.canvas.requestPointerLock({ unadjustedMovement: true });
    } catch {
      // Some platforms reject raw input; fall back to accelerated movement.
      await this.canvas.requestPointerLock().catch((error: unknown) => {
        console.warn("[Input] pointer lock refused", error);
      });
    }
  }
}

/**
 * Movement and look as the story allows: while the sketchbook is open its page
 * keys (A/D) take over strafing (S5), and a scripted moment (a phone call, a
 * fade) can hold Sora still or stop the camera too.
 */
export class GatedInput implements InputSource {
  notebook = false;
  hiding = false;
  inspecting = false;
  reading = false;
  holdStill = false;
  holdLook = false;

  constructor(private readonly inner: InputSource) {}

  readMove(out: MoveIntent): MoveIntent {
    this.inner.readMove(out);
    if (this.reading) out.x = 0;
    if (this.holdStill || this.inspecting || this.hiding || this.notebook) {
      out.x = 0;
      out.z = 0;
      out.hurry = false;
      if (this.hiding) out.crouch = false;
    }
    return out;
  }

  consumeLook(out: { yaw: number; pitch: number }): void {
    this.inner.consumeLook(out);
    if (this.holdLook || this.notebook) {
      out.yaw = 0;
      out.pitch = 0;
    }
  }

  dispose(): void {
    this.inner.dispose();
  }
}
