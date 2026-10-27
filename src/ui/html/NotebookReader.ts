import type { Game } from "../../core/Game";
import { currentObjective, notebookClues } from "../../episodes/ep1/data/notebook";
import "./notebook.css";
import { PATH } from "../../episodes/ep1/data/forestBorder";
import { ROAD_COVER } from "../../episodes/ep1/act1/EarlyStealthBrain";

type Tab = "now" | "map" | "notes" | "people";
const TABS: [Tab, string][] = [
  ["now", "Current objective"],
  ["map", "Map"],
  ["notes", "Clues & notes"],
  ["people", "People"],
];

/** A close reading view of the notebook, with selectable text and a genuine location plan. */
export class NotebookReader {
  private readonly panel = document.createElement("section");
  private readonly content = document.createElement("div");
  private tab: Tab = "now";
  private previousFocus: HTMLElement | null = null;
  constructor(private readonly game: Game) {
    this.panel.className = "notebook-reader";
    this.panel.hidden = true;
    this.panel.setAttribute("role", "dialog");
    this.panel.setAttribute("aria-modal", "true");
    this.panel.setAttribute("aria-label", "Sora’s notebook");
    const book = document.createElement("article"),
      header = document.createElement("header"),
      nav = document.createElement("nav");
    header.innerHTML = "<div><small>SORA’S NOTEBOOK</small><h1>A record of this night</h1></div>";
    const close = document.createElement("button");
    close.textContent = "Close · Q / Esc";
    close.onclick = () => this.close(true);
    header.append(close);
    nav.setAttribute("aria-label", "Notebook sections");
    for (const [id, name] of TABS) {
      const b = document.createElement("button");
      b.textContent = name;
      b.dataset.tab = id;
      b.onclick = () => {
        this.tab = id;
        this.paint();
      };
      nav.append(b);
    }
    this.content.className = "notebook-content";
    book.append(header, nav, this.content);
    this.panel.append(book);
    document.body.append(this.panel);
    window.addEventListener(
      "keydown",
      (e) => {
        if (!this.isOpen) return;
        e.stopImmediatePropagation();
        if (e.code === "Tab") {
          e.preventDefault();
          const buttons = [...this.panel.querySelectorAll<HTMLButtonElement>("button")];
          const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
          buttons[(index + (e.shiftKey ? -1 : 1) + buttons.length) % buttons.length].focus();
          return;
        }
        if (["KeyQ", "Escape"].includes(e.code)) {
          e.preventDefault();
          if (!e.repeat) this.close(true);
        }
        const index = Number(e.code.replace("Digit", "")) - 1;
        if (!e.repeat && index >= 0 && index < TABS.length) {
          this.tab = TABS[index][0];
          this.paint();
        }
      },
      { capture: true },
    );
  }
  get isOpen(): boolean {
    return !this.panel.hidden;
  }
  show(): void {
    this.game.input.clear();
    this.previousFocus =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    this.panel.hidden = false;
    this.tab = "now";
    this.game.gated.notebook = true;
    this.game.stopInspecting();
    this.game.satchel.close();
    document.exitPointerLock();
    this.paint();
    this.panel.querySelector<HTMLButtonElement>("button")?.focus();
  }
  close(relock = false): void {
    if (!this.isOpen) return;
    this.panel.hidden = true;
    this.game.gated.notebook = false;
    this.game.input.clear();
    this.game.sketchbook?.close();
    this.previousFocus?.focus({ preventScroll: true });
    if (relock && !this.game.cutscene && !this.game.satchel.isOpen)
      void this.game.input.lockPointer();
  }
  private paragraph(text: string, parent: HTMLElement = this.content): void {
    const p = document.createElement("p");
    p.textContent = text;
    parent.append(p);
  }
  private heading(text: string): void {
    const h = document.createElement("h2");
    h.textContent = text;
    this.content.append(h);
  }
  private paint(): void {
    this.content.replaceChildren();
    for (const b of this.panel.querySelectorAll<HTMLButtonElement>("nav button"))
      b.setAttribute("aria-pressed", String(b.dataset.tab === this.tab));
    const g = this.game,
      f = g.flags;
    if (this.tab === "now") {
      const o = currentObjective(f, g.inventory);
      this.heading(o.title);
      this.paragraph(o.detail);
      const list = document.createElement("ul");
      list.className = "notebook-tasks";
      for (const task of o.tasks) {
        const li = document.createElement("li");
        li.textContent = `${task.done ? "✓" : "○"} ${task.text}`;
        li.classList.toggle("done", task.done);
        list.append(li);
      }
      this.content.append(list);
      const last = g.checkpoints.last;
      this.paragraph(
        last
          ? `Last checkpoint: ${String(last.flags["checkpoint.location"] ?? last.checkpoint)} · ${last.clock}`
          : "Your first checkpoint will be recorded at the writing desk.",
      );
    } else if (this.tab === "map") this.map();
    else if (this.tab === "notes") {
      this.heading("What I know");
      const clues = notebookClues(g.sketchbook?.written ?? new Set());
      if (!clues.length)
        this.paragraph(
          "No clues recorded yet. Documents and discoveries will be written here when you find them.",
        );
      for (const clue of clues) {
        const article = document.createElement("article");
        const h = document.createElement("h3");
        h.textContent = clue.title;
        article.append(h);
        this.paragraph(clue.text, article);
        this.content.append(article);
      }
    } else {
      this.heading("People I know");
      for (const [name, description] of [
        ["Sora", "An illustrator returning to her family’s village."],
        [
          "Yay Mey / Mak Yey",
          "My grandmother. She called from home; she knows the funeral duties.",
        ],
        ["Uncle Sok", "His death brought me home. His house is the centre of tonight’s vigil."],
        [
          "Vuthy",
          "My cousin. He has taken Grandmother somewhere she can rest and promises to return at dawn.",
        ],
      ]) {
        if (name === "Vuthy" && !f.get("ep1.arrival.callComplete", false)) continue;
        const h = document.createElement("h3");
        h.textContent = name;
        this.content.append(h);
        this.paragraph(description);
      }
    }
  }
  private map(): void {
    const g = this.game,
      studio = g.flags.get("ep1.checkpoint", "CP0") === "CP0";
    this.heading(studio ? "Studio · Phnom Penh" : "Village · House of mourning");
    const holder = document.createElement("div");
    holder.className = "notebook-map";
    const at = g.player.feet;
    if (!studio && at.z > 15) {
      holder.classList.add("approach-map");
      // Rotate the long approach into landscape so labels remain readable.
      holder.innerHTML = `<svg viewBox="-9 -10 80 22" role="img" aria-label="Approach path: funeral courtyard on the left, three solid carts for cover, taxi on the right"><path d="${PATH.map(([x, z], i) => `${i ? "L" : "M"}${z} ${-x}`).join(" ")}" class="path"/><rect x="-1" y="-4" width="7" height="8" class="walls"/><text x="3" y="-7.5">Funeral courtyard</text><text x="3" y="8">Safe checkpoint</text>${ROAD_COVER.map((r, i) => `<rect x="${r.minZ}" y="${-r.maxX}" width="${r.maxZ - r.minZ}" height="${r.maxX - r.minX}"/><text x="${(r.minZ + r.maxZ) / 2}" y="-6">Cover ${3 - i}</text>`).join("")}<text x="60" y="-6">Taxi</text><text x="58" y="8">Flooded road</text><circle cx="${at.z}" cy="${-at.x}" r=".55" class="you"/></svg>`;
      this.content.append(holder);
      this.paragraph(
        "● You · Solid rectangles are carts you can crouch behind. Follow the path left toward the funeral courtyard. The map does not show the presence’s position.",
      );
      return;
    }
    // The plans use the actual Babylon world x/z coordinates and preserve their scale.
    const base = studio
      ? `<svg viewBox="-6.5 -5.5 7 6" role="img" aria-label="Studio floor plan: drawing table by south window, writing desk east, door and phone west"><rect x="-6" y="-5" width="6" height="5" class="walls"/><path d="M-6 -3 L-6 -2" class="door"/><rect x="-3.65" y="-1.1" width="1.3" height=".76"/><text x="-3" y="-.65">Drawing table</text><rect x="-.68" y="-3.25" width=".66" height="1.5"/><text x="-1.12" y="-2.5">Desk / drawer</text><rect x="-5.9" y="-4.88" width="1.9" height=".86"/><text x="-4.95" y="-4.45">Bed</text><text x="-5.1" y="-3.55">Phone</text><text x="-5.15" y="-2.5">Exit →</text><text x="-2.9" y="-4.75">Shelf / satchel</text><path d="M-3.75 0 H-2.25" class="window"/>`
      : `<svg viewBox="-11 -24 22 40" role="img" aria-label="Village floor plan with house, stairs, funeral tent and courtyard save point"><rect x="-6" y="-19" width="12" height="8" class="walls"/><text x="0" y="-20">HOUSE · upper floor</text><path d="M-1 -19 V-11 M-6 -13.5 H6"/><text x="2.4" y="-16.6">Hall</text><text x="2.4" y="-15.2">Phone</text><text x="-3.5" y="-16.6">${g.flags.get("ep1.act2.started", false) ? "Sok’s" : "Locked"}</text><text x="-3.5" y="-15.2">room</text><text x="0" y="-11.6">Stairs ↓</text><rect x="-4" y="-7" width="8" height="6" class="walls"/><text x="0" y="-5.4">FUNERAL TENT</text><text x="0" y="-3.4">Coffin / burner</text><text x="-5.1" y="1.4">✦ Safe desk</text><text x="0" y="5">Courtyard</text><path d="M0 6 L0 15" class="path"/><text x="0" y="12">Path to taxi ↓</text>`;
    const marker =
      studio || (at.z <= 15 && at.z >= -23)
        ? `<circle cx="${at.x}" cy="${at.z}" r="${studio ? 0.1 : 0.3}" class="you"/>`
        : "";
    holder.innerHTML = `${base}${marker}</svg>`;
    this.content.append(holder);
    this.paragraph(
      "● You     ✦ Safe place     Blue line: window / entrance. Labels describe the real room layout.",
    );
    if (!studio && at.z > 15)
      this.paragraph(
        `You are on the approach path. The courtyard is approximately ${Math.round(at.z)} metres ahead, toward the house.`,
      );
    if (!studio && at.y < 1.5)
      this.paragraph(
        "The house plan shows the upper floor. Its stairs are on the courtyard side; storage and water jars are beneath it.",
      );
  }
}
