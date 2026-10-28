import { PORTRAIT_ATLAS, PORTRAIT_CELLS } from "../notebook/NotebookPortraits";
import type { Game } from "../../core/Game";
import { SECTIONS, type SectionId } from "../diegetic/sketchbookContent";
import { mapSvg } from "../notebook/NotebookMap";
import "./notebook.css";
import { setControlText } from "./controlText";

/** Optional readable presentation of the physical sketchbook, using identical content. */
export class NotebookReader {
  private readonly panel = document.createElement("section");
  private readonly content = document.createElement("div");
  private readonly controls = document.createElement("nav");
  private readonly status = document.createElement("span");
  private tab: SectionId = "now";
  private wasRaised = false;
  private lastSignature = "";
  private refreshAge = 0;
  constructor(private readonly game: Game) {
    this.panel.className = "notebook-reader";
    this.panel.hidden = true;
    this.panel.setAttribute("role", "dialog");
    this.panel.setAttribute("aria-modal", "true");
    this.panel.setAttribute("aria-label", "Sora’s notebook · Read clearly");
    const book = document.createElement("article"),
      header = document.createElement("header"),
      nav = document.createElement("nav");
    header.innerHTML =
      "<div><small>SORA’S NOTEBOOK · READ CLEARLY</small><h1>A record of this night</h1></div>";
    const actions = document.createElement("div");
    actions.className = "notebook-reader-actions";
    actions.append(
      this.button("Back to sketchbook · R", () => this.back(true)),
      this.button("Close · Q / Esc", () => game.closeSketchbook(true)),
    );
    header.append(actions);
    nav.setAttribute("aria-label", "Notebook sections");
    SECTIONS.forEach(({ id, label }) => {
      const b = this.button(label, () => this.select(id));
      b.dataset.tab = id;
      nav.append(b);
    });
    this.content.className = "notebook-content";
    this.content.tabIndex = 0;
    book.append(header, nav, this.content);
    this.panel.append(book);
    document.body.append(this.panel);
    this.controls.className = "notebook-controls";
    this.controls.setAttribute("aria-label", "Sketchbook controls");
    this.controls.hidden = true;
    const sections = document.createElement("div");
    sections.className = "notebook-section-controls";
    SECTIONS.forEach(({ id, label }, index) => {
      const b = this.button(`${index + 1} · ${label}`, () => this.select(id));
      b.dataset.section = id;
      sections.append(b);
    });
    const tools = document.createElement("div");
    tools.className = "notebook-page-controls";
    tools.append(
      this.button("← Previous · A", () => game.sketchbook?.turn(-1)),
      this.status,
      this.button("Next · D →", () => game.sketchbook?.turn(1)),
      this.button("Read clearly · R", () => this.show()),
      this.button("Close · Q / Esc", () => game.closeSketchbook(true)),
    );
    this.status.setAttribute("aria-live", "polite");
    this.status.className = "notebook-page-status";
    this.controls.append(sections, tools);
    document.body.append(this.controls);
    const fitControls = () => {
      if (this.controls.hidden) return;
      const top = sections.getBoundingClientRect().bottom + 12;
      const bottom = window.innerHeight - tools.getBoundingClientRect().top + 12;
      game.sketchbook?.setViewportInsets(top, bottom);
    };
    const resize = new ResizeObserver(fitControls);
    resize.observe(sections);
    resize.observe(tools);
    resize.observe(this.controls);
    window.addEventListener("resize", fitControls);
    window.addEventListener(
      "keydown",
      (e) => {
        if (!this.isOpen) {
          if (game.sketchbook?.isRaised && e.code === "Tab") {
            e.preventDefault();
            e.stopImmediatePropagation();
            const buttons = [...this.controls.querySelectorAll<HTMLButtonElement>("button")];
            const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
            buttons[(index + (e.shiftKey ? -1 : 1) + buttons.length) % buttons.length]?.focus();
          }
          return;
        }
        e.stopImmediatePropagation();
        if (e.code === "Tab") {
          e.preventDefault();
          const focusable = [...this.panel.querySelectorAll<HTMLElement>("button, [tabindex='0']")];
          const index = focusable.indexOf(document.activeElement as HTMLElement);
          focusable[(index + (e.shiftKey ? -1 : 1) + focusable.length) % focusable.length].focus();
        } else if (!e.repeat && ["KeyQ", "Escape"].includes(e.code)) {
          e.preventDefault();
          game.closeSketchbook(true);
        } else if (!e.repeat && e.code === "KeyR") {
          e.preventDefault();
          this.back(true);
        } else if (!e.repeat && /^Digit[1-5]$/.test(e.code)) {
          e.preventDefault();
          this.select(SECTIONS[Number(e.code.slice(-1)) - 1].id);
        }
      },
      { capture: true },
    );
  }
  private button(label: string, action: () => void): HTMLButtonElement {
    const b = document.createElement("button");
    b.type = "button";
    setControlText(b, label);
    b.onclick = action;
    return b;
  }
  get isOpen(): boolean {
    return !this.panel.hidden;
  }

  show(): void {
    const g = this.game,
      book = g.sketchbook;
    if (!book?.isRaised || g.cutscene || g.threatActive || g.hiding) return;
    g.input.clear();
    book.refreshContent();
    this.tab = book.section;
    this.panel.hidden = false;
    this.controls.hidden = true;
    book.setPresentationHidden(true);
    g.gated.notebook = true;
    g.stopInspecting();
    g.satchel.close();
    document.exitPointerLock();
    this.paint();
    this.panel.querySelector<HTMLButtonElement>("button")?.focus();
  }
  /** Hide the reading overlay without closing the notebook. */
  back(focus = false): void {
    if (!this.isOpen) return;
    this.panel.hidden = true;
    this.game.sketchbook?.showSection(this.tab);
    this.game.sketchbook?.setPresentationHidden(false);
    this.game.input.clear();
    this.controls.hidden = !this.game.sketchbook?.isRaised;
    if (focus)
      this.controls.querySelector<HTMLButtonElement>(`[data-section="${this.tab}"]`)?.focus();
  }
  /** Compatibility for callers closing all menus. */
  close(relock = false): void {
    if (this.isOpen || this.game.sketchbook?.isVisible) this.game.closeSketchbook(relock);
  }

  select(section: SectionId): void {
    const book = this.game.sketchbook;
    if (!book?.isRaised) return;
    book.goToSection(section);
    if (this.isOpen) {
      this.tab = section;
      this.paint();
    }
  }

  /** Covers manual openings and automatic story discoveries. No permanent reading preference. */
  update(dt: number): void {
    const g = this.game,
      book = g.sketchbook;
    const raised = book?.isRaised ?? false;
    if (!raised && this.isOpen) this.back();
    g.gated.notebook = book?.isVisible ?? false;
    const available = raised && !g.cutscene && !g.threatActive && !g.hiding && !g.satchel.isOpen;
    this.controls.hidden = !available || this.isOpen;
    if (raised && !this.wasRaised) g.input.clear();
    this.wasRaised = raised;
    this.refreshAge += dt;
    if (raised && this.refreshAge >= 0.25) {
      this.refreshAge = 0;
      book?.refreshContent();
      if (this.isOpen) {
        const signature = g.notebookContent().signature;
        if (signature !== this.lastSignature) this.paint(false);
      }
    }
    if (!book || !raised) return;
    for (const b of this.controls.querySelectorAll<HTMLButtonElement>("[data-section]"))
      b.setAttribute("aria-pressed", String(b.dataset.section === book.section));
    const label = SECTIONS.find((s) => s.id === book.section)?.label ?? "Notebook";
    const next = `${label} · ${book.spread + 1} / ${book.painter.spreadCount}`;
    if (next !== this.status.textContent) this.status.textContent = next;
  }
  private paint(resetScroll = true): void {
    const scrollTop = resetScroll ? 0 : this.content.scrollTop;
    const model = this.game.notebookContent();
    this.lastSignature = model.signature;
    this.content.replaceChildren();
    for (const b of this.panel.querySelectorAll<HTMLButtonElement>("nav button"))
      b.setAttribute("aria-pressed", String(b.dataset.tab === this.tab));
    if (this.tab === "map") {
      const title = document.createElement("h2");
      title.textContent = model.map.title;
      this.content.append(title);
      const holder = document.createElement("div");
      holder.className = "notebook-map";
      holder.innerHTML = mapSvg(model.map);
      this.content.append(holder);
      const nights = document.createElement("p");
      nights.textContent = `Night circles: ${model.nights.map((mark, i) => `${i + 1} ${mark === "empty" ? "unmarked" : mark === "pencil" ? "pencilled" : "inked"}`).join("; ")}.`;
      this.content.append(nights);
    }
    for (const entry of model.entries.filter((e) => e.section === this.tab)) {
      const article = document.createElement("article");
      if (entry.heading && !(this.tab === "map" && entry.id === "live:map")) {
        const h = document.createElement("h2");
        h.textContent = entry.heading;
        article.append(h);
      }
      if (entry.section === "people" && PORTRAIT_CELLS[entry.id]) {
        const [column, row] = PORTRAIT_CELLS[entry.id];
        const portrait = document.createElement("div");
        portrait.className = "notebook-portrait";
        portrait.setAttribute("role", "img");
        portrait.setAttribute("aria-label", `Graphite portrait of ${entry.heading}`);
        portrait.style.backgroundImage = `url("${PORTRAIT_ATLAS}")`;
        portrait.style.backgroundPosition = `${column * 100}% ${row * 100}%`;
        article.append(portrait);
      }
      for (const text of [entry.text, entry.smallText, entry.khmer]) {
        if (!text) continue;
        const p = document.createElement("p");
        p.textContent = text;
        if (text.startsWith("✓")) p.className = "notebook-task-done";
        article.append(p);
      }
      this.content.append(article);
    }
    this.content.scrollTop = scrollTop;
  }
}
