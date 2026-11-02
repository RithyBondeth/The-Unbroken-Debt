import "./pause.css";
import { t } from "../../data/strings";
import { EntryAmbience } from "../../audio/EntryAmbience";
import { readWelcomeSettings } from "./WelcomeScreen";

export interface PauseActions {
  resume(): void;
  /** Back to the last checkpoint; absent when there is none yet. */
  restart: (() => void) | null;
  quit(): void;
}

/** Lines the dark says while the game waits. */
const WHISPERS = ["pause.whisper1", "pause.whisper2", "pause.whisper3", "pause.whisper4"] as const;

/**
 * Escape freezes the night under a stained veil: the frame drained of colour
 * behind a blood-dark vignette and grain, the title menu's red smears, whispers
 * crossing the ears, and now and then a pair of eyes opening in the dark at
 * the edge of the screen. Escape again, or Resume, goes back.
 */
export class PauseMenu {
  private readonly node = document.createElement("div");
  private readonly menu = document.createElement("nav");
  private readonly controls = document.createElement("dl");
  private readonly confirm = document.createElement("div");
  private readonly whisper = document.createElement("p");
  private readonly eyes = document.createElement("div");
  private sound: EntryAmbience | null = null;
  private eyeTimer: ReturnType<typeof setTimeout> | undefined;
  private actions: PauseActions | null = null;
  private returnFocus: HTMLElement | null = null;

  constructor() {
    const node = this.node;
    node.className = "pause";
    node.hidden = true;
    node.setAttribute("role", "dialog");
    node.setAttribute("aria-modal", "true");
    node.setAttribute("aria-labelledby", "pause-title");
    const veil = document.createElement("div");
    veil.className = "pause-veil";
    veil.setAttribute("aria-hidden", "true");
    veil.innerHTML = '<div class="pause-grain"></div><div class="pause-drip"></div>';
    this.eyes.className = "pause-eyes";
    this.eyes.setAttribute("aria-hidden", "true");
    this.eyes.innerHTML = "<i></i><i></i>";

    const panel = document.createElement("div");
    panel.className = "pause-panel";
    const eyebrow = document.createElement("p");
    eyebrow.className = "pause-eyebrow";
    eyebrow.lang = "km";
    eyebrow.textContent = "បុណ្យសព";
    const title = document.createElement("h1");
    title.id = "pause-title";
    title.className = "pause-title";
    title.textContent = t("pause.title");
    title.dataset.text = title.textContent;
    this.whisper.className = "pause-whisper";

    this.menu.className = "pause-menu";
    this.menu.setAttribute("aria-label", t("pause.title"));
    this.controls.className = "pause-controls";
    this.controls.hidden = true;
    this.controls.innerHTML = [
      ["W A S D", "Move"],
      ["Mouse", "Look"],
      ["E", "Use, take, open; save at a spirit house or writing desk"],
      ["Shift", "Hurry"],
      ["C / Ctrl", "Crouch"],
      ["F", "Light or put out the lamp"],
      ["Q", "Notebook: objective, map, clues and people"],
      ["Tab", "Satchel"],
      ["Esc", "Pause"],
    ]
      .map(([key, what]) => `<dt>${key}</dt><dd>${what}</dd>`)
      .join("");
    this.confirm.className = "pause-confirm";
    this.confirm.hidden = true;

    panel.append(eyebrow, title, this.whisper, this.menu, this.controls, this.confirm);
    const hint = document.createElement("p");
    hint.className = "pause-hint";
    hint.innerHTML = `<kbd>Esc</kbd> ${t("pause.resumeHint")}`;
    node.append(veil, this.eyes, panel, hint);
    document.body.append(node);

    node.addEventListener("keydown", (event) => {
      if (event.code !== "Tab") return;
      // Keep keyboard focus inside the menu while it is open.
      const focusable = [
        ...node.querySelectorAll<HTMLButtonElement>("button:not([hidden])"),
      ].filter((b) => b.offsetParent !== null);
      if (!focusable.length) return;
      const at = focusable.indexOf(document.activeElement as HTMLButtonElement);
      const next = event.shiftKey
        ? (at <= 0 ? focusable.length : at) - 1
        : (at + 1) % focusable.length;
      event.preventDefault();
      focusable[next].focus();
    });
  }

  get isOpen(): boolean {
    return !this.node.hidden;
  }

  open(actions: PauseActions): void {
    if (this.isOpen) return;
    this.actions = actions;
    this.returnFocus = document.activeElement as HTMLElement | null;
    const key = WHISPERS[Math.floor(Math.random() * WHISPERS.length)];
    this.whisper.textContent = t(key);
    this.showMenu();
    this.node.hidden = false;
    // Restart the entrance each time the menu opens.
    this.node.classList.remove("shown");
    void this.node.offsetWidth;
    this.node.classList.add("shown");
    this.menu.querySelector("button")?.focus({ preventScroll: true });
    this.sound = new EntryAmbience();
    this.sound.start(readWelcomeSettings().sound);
    this.scheduleEyes(2.5);
  }

  close(): void {
    if (!this.isOpen) return;
    this.node.hidden = true;
    this.node.classList.remove("shown");
    this.sound?.dispose();
    this.sound = null;
    clearTimeout(this.eyeTimer);
    this.eyes.classList.remove("open");
    this.actions = null;
    this.returnFocus?.focus?.({ preventScroll: true });
  }

  /** Escape inside the menu: back out of a sub-panel first, then resume. */
  back(): void {
    if (!this.controls.hidden || !this.confirm.hidden) this.showMenu();
    else this.actions?.resume();
  }

  private showMenu(): void {
    const actions = this.actions;
    this.controls.hidden = true;
    this.confirm.hidden = true;
    this.menu.hidden = false;
    this.menu.replaceChildren();
    const item = (label: string, run: () => void) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", run);
      this.menu.append(button);
      return button;
    };
    item(t("pause.resume"), () => this.actions?.resume());
    item(t("pause.controls"), () => {
      this.menu.hidden = true;
      this.controls.hidden = false;
      this.backButton(this.controls);
    });
    const restart = actions?.restart;
    if (restart) item(t("pause.restart"), () => this.ask(t("pause.restartConfirm"), restart));
    item(t("pause.quit"), () => this.ask(t("pause.quitConfirm"), () => this.actions?.quit()));
    this.menu.querySelector("button")?.focus({ preventScroll: true });
  }

  private backButton(panel: HTMLElement): void {
    panel.querySelector(".pause-back")?.remove();
    const back = document.createElement("button");
    back.type = "button";
    back.className = "pause-back";
    back.textContent = t("pause.back");
    back.addEventListener("click", () => this.showMenu());
    panel.append(back);
    back.focus({ preventScroll: true });
  }

  /** A second step before anything that loses progress. */
  private ask(question: string, yes: () => void): void {
    this.menu.hidden = true;
    this.confirm.hidden = false;
    this.confirm.replaceChildren();
    const text = document.createElement("p");
    text.textContent = question;
    const go = document.createElement("button");
    go.type = "button";
    go.className = "pause-danger";
    go.textContent = t("pause.confirm");
    go.addEventListener("click", yes);
    this.confirm.append(text, go);
    this.backButton(this.confirm);
    go.focus({ preventScroll: true });
  }

  /** Every so often a pair of eyes opens somewhere at the edge of the dark, and closes. */
  private scheduleEyes(delay: number): void {
    this.eyeTimer = setTimeout(() => {
      if (!this.isOpen) return;
      const left = Math.random() < 0.5;
      this.eyes.style.setProperty(
        "--x",
        `${left ? 4 + Math.random() * 14 : 82 + Math.random() * 12}%`,
      );
      this.eyes.style.setProperty("--y", `${18 + Math.random() * 62}%`);
      this.eyes.style.setProperty("--tilt", `${(Math.random() - 0.5) * 16}deg`);
      this.eyes.classList.add("open");
      this.eyeTimer = setTimeout(
        () => {
          this.eyes.classList.remove("open");
          this.scheduleEyes(5 + Math.random() * 7);
        },
        1600 + Math.random() * 1400,
      );
    }, delay * 1000);
  }
}
