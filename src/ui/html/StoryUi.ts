import "./story.css";
import strings from "../../data/strings/en.json";

export type StringKey = keyof typeof strings;

export const t = (key: StringKey): string => strings[key];

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
 * Control hints as faint pencil text that fades: shown the first time an action
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
    this.node.textContent = t(key);
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

  constructor() {
    this.node.hidden = true;
    this.node.setAttribute("aria-live", "polite");
  }

  /** Shows a line; a long one is split at sentence breaks and shown in turn. */
  async say(speaker: string, text: string, seconds: number): Promise<void> {
    const chunks = subtitleChunks(text);
    for (const chunk of chunks) {
      this.node.innerHTML = "";
      const name = document.createElement("b");
      name.textContent = `${speaker}: `;
      this.node.append(name, chunk);
      this.node.hidden = false;
      await after((seconds * chunk.length) / text.length);
    }
    this.node.hidden = true;
  }
}

/** Black fades, the click that starts the game, and title cards. */
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
    button.textContent = parts.button;
    this.card.appendChild(button);
    await new Promise<void>((done) =>
      button.addEventListener("click", () => done(), { once: true }),
    );
  }

  hideCard(): void {
    this.card.classList.remove("shown");
  }

  /** Browsers start sound and pointer lock only from a click: wait for one on the black. */
  async waitForClick(onClick: () => void): Promise<void> {
    this.node.classList.add("waiting");
    void this.show({ title: t("start.click"), body: t("start.note") });
    await new Promise<void>((done) =>
      this.node.addEventListener(
        "click",
        () => {
          onClick();
          done();
        },
        { once: true },
      ),
    );
    this.node.classList.remove("waiting");
    this.hideCard();
  }
}

export interface SatchelEntry {
  name: string;
  note?: string;
}

/**
 * Greybox stand-in for the satchel (Controls and Interface, section 4): a paper
 * list of what Sora carries. The 3D satchel in her hands replaces it in Phase 3.
 */
export class SatchelPanel {
  private readonly node = element("div", "story-satchel");

  constructor() {
    this.node.hidden = true;
  }

  get isOpen(): boolean {
    return !this.node.hidden;
  }

  open(entries: SatchelEntry[]): void {
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
    this.node.append(title, list, placeholder);
    this.node.hidden = false;
  }

  close(): void {
    this.node.hidden = true;
  }
}

/** The small save indicator while a checkpoint is written (section 6.3). */
export class SaveIndicator {
  private readonly node = element("div", "story-saving");

  constructor() {
    this.node.textContent = t("save.saving");
  }

  set(saving: boolean): void {
    this.node.classList.toggle("shown", saving);
  }
}
