import "./story.css";
import { setControlText } from "./controlText";
import "./entry.css";
import { t, type StringKey } from "../../data/strings";

export type { StringKey };

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.className = className;
  document.body.appendChild(node);
  return node;
}

const after = (seconds: number) => new Promise<void>((done) => setTimeout(done, seconds * 1000));

/**
 * Control hints with shared type and keycaps that fade: shown the first time an action
 * is needed, never again once the player has done it (Controls and Interface, 6.3).
 */
export class Hints {
  private readonly node = element("div", "story-hint");
  private readonly performedKeys = new Set<string>();
  private current: StringKey | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;

  show(key: StringKey, seconds = 7): void {
    if (this.performedKeys.has(key)) return;
    this.current = key;
    setControlText(this.node, t(key));
    this.node.classList.add("shown");
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.hide(), seconds * 1000);
  }

  /** The player has done it: hide the hint and never show it again. */
  performed(key: StringKey): void {
    this.performedKeys.add(key);
    if (this.current === key) this.hide();
  }

  hide(): void {
    this.current = null;
    this.node.classList.remove("shown");
  }
}

/** Characters that fit two subtitle lines on a small laptop screen. */
const SUBTITLE_CHARS = 60;

/** Splits a line after sentences or pauses (". ", "… ", "? ") into pieces of two lines at most. */
export function subtitleChunks(text: string, max = SUBTITLE_CHARS): string[] {
  const parts = text.match(/[.?!…—]*[^.?!…—]+[.?!…—]+\s*|[.?!…—]*[^.?!…—]+$/g) ?? [text];
  const chunks: string[] = [];
  for (const part of parts) {
    const last = chunks.at(-1);
    if (last !== undefined && (last + part).trim().length <= max)
      chunks[chunks.length - 1] = last + part;
    else chunks.push(part);
  }
  return chunks.map((c) => c.trim()).filter(Boolean);
}

/** Bottom centre, at most two lines, with the speaker's name (section 6.3). */
export class Subtitles {
  private readonly node = element("div", "story-subtitles");
  private sequence = 0;

  /** Environmental cues yield while a story line is being presented. */
  get active(): boolean {
    return !this.node.hidden;
  }

  constructor() {
    this.node.hidden = true;
    this.node.setAttribute("aria-live", "polite");
    this.node.setAttribute("aria-atomic", "true");
  }

  private render(speaker: string, text: string): void {
    this.node.innerHTML = "";
    const name = document.createElement("b");
    name.textContent = `${speaker}: `;
    this.node.append(name, text);
    this.node.hidden = false;
  }

  /** A timeline owns visibility; stale timed subtitles cannot overwrite it. */
  show(speaker: string, text: string): void {
    this.sequence++;
    this.render(speaker, text);
  }

  hide(): void {
    this.sequence++;
    this.node.hidden = true;
  }

  /** Shows a line; a long one is split at sentence breaks and shown in turn. */
  async say(speaker: string, text: string, seconds: number): Promise<void> {
    const sequence = ++this.sequence;
    const chunks = subtitleChunks(text);
    for (const chunk of chunks) {
      if (sequence !== this.sequence) return;
      this.render(speaker, chunk);
      await after((seconds * chunk.length) / text.length);
    }
    if (sequence === this.sequence) this.node.hidden = true;
  }
}

/** Black fades, the keyboard entry screen, and title cards. */
export class ScreenFade {
  private readonly node = element("div", "story-fade");
  private readonly card = document.createElement("div");

  constructor() {
    this.card.className = "story-card";
    this.node.appendChild(this.card);
  }

  /** Fades the black to `opacity` (1 = black) over `seconds`. */
  async to(opacity: number, seconds: number): Promise<void> {
    this.node.style.transitionDuration = `${seconds}s`;
    this.node.style.opacity = String(opacity);
    await after(seconds);
  }

  /** A card on the black; `button` resolves the promise when clicked. */
  async show(parts: {
    title: string;
    khmer?: string;
    body?: string;
    button?: string;
  }): Promise<void> {
    this.card.innerHTML = "";
    const title = document.createElement("h1");
    title.textContent = parts.title;
    this.card.appendChild(title);
    for (const [text, className] of [
      [parts.khmer, "khmer"],
      [parts.body, ""],
    ] as const) {
      if (!text) continue;
      const p = document.createElement("p");
      p.textContent = text;
      if (className) p.className = className;
      this.card.appendChild(p);
    }
    this.card.classList.add("shown");
    if (!parts.button) return;
    const button = document.createElement("button");
    button.className = "ui-button ui-button-primary";
    setControlText(button, parts.button);
    this.card.appendChild(button);
    button.focus({ preventScroll: true });
    await new Promise<void>((done) =>
      button.addEventListener("click", () => done(), { once: true }),
    );
  }

  hideCard(): void {
    this.card.classList.remove("shown");
  }

  /** Keep audio unlock and pointer capture in the player's activation gesture. */
  async waitForEnter(onEnter: () => void): Promise<void> {
    const previousFocus = document.activeElement as HTMLElement | null;
    this.card.replaceChildren();
    this.card.classList.add("story-entry");
    const atmosphere = document.createElement("div");
    atmosphere.className = "entry-atmosphere";
    atmosphere.setAttribute("aria-hidden", "true");
    atmosphere.innerHTML = '<div class="entry-door"></div><i></i><i></i>';
    this.node.prepend(atmosphere);
    const label = document.createElement("p");
    label.className = "entry-eyebrow";
    label.textContent = t("start.before");
    const icon = document.createElement("div");
    icon.className = "entry-headphones";
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML = `<svg viewBox="0 0 80 80" fill="none"><path d="M16 45v-9a24 24 0 0 1 48 0v9M22 32v-2a18 18 0 0 1 36 0v2"/><rect x="12" y="40" width="14" height="23" rx="5"/><rect x="54" y="40" width="14" height="23" rx="5"/><path d="M19 47v9M61 47v9"/></svg>`;
    const title = document.createElement("h1");
    title.id = "entry-title";
    title.textContent = t("start.listen");
    const recommendation = document.createElement("p");
    recommendation.className = "entry-recommendation";
    recommendation.textContent = t("start.note");
    const detail = document.createElement("p");
    detail.className = "entry-detail";
    detail.id = "entry-detail";
    detail.textContent = t("start.detail");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "entry-begin";
    button.setAttribute("aria-label", t("start.enter"));
    button.setAttribute("aria-keyshortcuts", "Enter");
    const key = document.createElement("kbd");
    key.textContent = "Enter";
    const action = document.createElement("span");
    action.textContent = t("start.begin");
    button.append(key, action);
    this.card.append(label, icon, title, recommendation, detail, button);
    this.card.setAttribute("role", "region");
    this.card.setAttribute("aria-labelledby", title.id);
    this.card.setAttribute("aria-describedby", detail.id);
    this.node.classList.add("waiting");
    this.card.classList.add("shown");
    button.focus({ preventScroll: true });
    const abort = new AbortController();
    let entering = false;
    await new Promise<void>((done) => {
      const begin = () => {
        if (entering) return;
        entering = true;
        button.disabled = true;
        onEnter();
        this.node.classList.add("entering");
        this.hideCard();
        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        setTimeout(done, reducedMotion ? 0 : 650);
      };
      window.addEventListener(
        "keydown",
        (event) => {
          if (
            event.key !== "Enter" ||
            event.isComposing ||
            event.altKey ||
            event.ctrlKey ||
            event.metaKey
          )
            return;
          event.preventDefault();
          event.stopImmediatePropagation();
          if (!event.repeat) begin();
        },
        { capture: true, signal: abort.signal },
      );
      button.addEventListener("click", begin, { signal: abort.signal });
    });
    abort.abort();
    this.node.classList.remove("waiting");
    this.node.classList.remove("entering");
    atmosphere.remove();
    this.card.classList.remove("story-entry");
    this.card.removeAttribute("role");
    this.card.removeAttribute("aria-labelledby");
    this.card.removeAttribute("aria-describedby");
    this.card.replaceChildren();
    const canvas = document.getElementById("game");
    (canvas ?? previousFocus)?.focus({ preventScroll: true });
  }
}

export interface SatchelEntry {
  name: string;
  note?: string;
}

export interface SatchelAction {
  label: string;
  enabled: boolean;
  perform: () => void;
}

/** Carried items and contextual actions beside the held 3D workspace. */
export class SatchelPanel {
  private readonly node = element("div", "story-satchel");
  private action: SatchelAction | null = null;
  private entries: SatchelEntry[] = [];

  setAction(action: SatchelAction | null): void {
    this.action = action;
    this.node.classList.toggle("has-action", !!action);
    if (this.isOpen) this.open(this.entries);
  }

  constructor() {
    this.node.hidden = true;
    window.addEventListener(
      "keydown",
      (event) => {
        if (!this.isOpen || !this.action || !["KeyE", "Enter"].includes(event.code)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!event.repeat && this.action.enabled) this.action.perform();
      },
      true,
    );
  }

  get isOpen(): boolean {
    return !this.node.hidden;
  }

  open(entries: SatchelEntry[]): void {
    this.entries = entries;
    this.node.innerHTML = "";
    const title = document.createElement("h2");
    title.textContent = t("satchel.title");
    const list = document.createElement("ul");
    for (const entry of entries) {
      const item = document.createElement("li");
      item.textContent = entry.name;
      if (entry.note) {
        const note = document.createElement("span");
        note.textContent = entry.note;
        item.appendChild(note);
      }
      list.appendChild(item);
    }
    if (!entries.length) list.textContent = t("satchel.empty");
    const placeholder = document.createElement("small");
    placeholder.textContent = t("satchel.placeholder");
    this.node.append(title, list);
    if (this.action) {
      const button = document.createElement("button");
      button.className = "ui-button ui-button-primary";
      setControlText(button, this.action.label);
      button.disabled = !this.action.enabled;
      button.onclick = () => this.action?.enabled && this.action.perform();
      this.node.append(button);
    } else this.node.append(placeholder);
    this.node.hidden = false;
  }

  close(): void {
    this.node.hidden = true;
  }
}

/** The small save indicator while a checkpoint is written (section 6.3). */
export class SaveIndicator {
  private readonly node = element("div", "story-saving");
  private timer: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    this.node.textContent = t("save.saving");
  }

  set(saving: boolean, result?: "saved" | "failed"): void {
    clearTimeout(this.timer);
    this.node.textContent = saving
      ? t("save.saving")
      : result === "saved"
        ? t("save.saved")
        : t("save.failed");
    this.node.setAttribute("role", "status");
    this.node.classList.toggle("shown", saving || result !== undefined);
    if (!saving) this.timer = setTimeout(() => this.node.classList.remove("shown"), 3500);
  }
}
