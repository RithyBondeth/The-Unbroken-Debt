import type { ResolutionProgress } from "./ResolutionProgress";
import "../../../ui/html/resolution.css";
import { setControlText } from "../../../ui/html/controlText";
/** Accessible paper overlays: translated slip, seal map, and Sora's closing spread. */
export class ResolutionView {
  private static nextId = 0;
  readonly panel = document.createElement("section");
  private readonly content = document.createElement("div");
  private previousFocus: HTMLElement | null = null;
  constructor() {
    this.panel.className = "resolution";
    this.panel.hidden = true;
    this.panel.setAttribute("aria-label", "Episode 1 resolution");
    this.panel.setAttribute("role", "dialog");
    this.panel.setAttribute("aria-modal", "true");
    this.content.className = "resolution-content";
    this.content.tabIndex = 0;
    document.body.append(this.panel);
    this.panel.addEventListener("keydown", (event) => {
      if (event.key !== "Tab") return;
      const focusable: HTMLElement[] = [
        ...(this.content.scrollHeight > this.content.clientHeight ? [this.content] : []),
        ...this.panel.querySelectorAll<HTMLButtonElement>("button:not(:disabled)"),
      ];
      if (!focusable.length) return;
      event.preventDefault();
      const current = focusable.indexOf(document.activeElement as HTMLElement);
      const index =
        current < 0
          ? event.shiftKey
            ? focusable.length - 1
            : 0
          : (current + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length;
      focusable[index].focus();
    });
  }
  async show(title: string, paragraphs: string[], buttons: string[]): Promise<number> {
    if (this.panel.hidden)
      this.previousFocus =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
    this.panel.replaceChildren();
    this.panel.hidden = false;
    const paper = document.createElement("article");
    paper.className = "resolution-paper";
    const heading = document.createElement("h1");
    heading.id = `resolution-title-${ResolutionView.nextId++}`;
    this.panel.setAttribute("aria-labelledby", heading.id);
    heading.textContent = title;
    this.content.replaceChildren(heading);
    for (const text of paragraphs) {
      const p = document.createElement("p");
      p.textContent = text;
      this.content.append(p);
    }
    const nav = document.createElement("nav");
    nav.setAttribute("aria-label", "Story actions");
    paper.append(this.content, nav);
    this.panel.append(paper);
    this.content.scrollTop = 0;
    return new Promise((resolve) =>
      buttons.forEach((label, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = index === 0 ? "ui-button ui-button-primary" : "ui-button";
        setControlText(button, label);
        button.onclick = () => {
          nav.querySelectorAll("button").forEach((b) => (b.disabled = true));
          resolve(index);
        };
        nav.append(button);
        if (index === 0) button.focus();
      }),
    );
  }
  async slip(): Promise<void> {
    const action = this.show(
      "The fourth name",
      [
        "Sok’s folded slip. Three names crossed out. A fourth scraped away until the paper is thin.",
      ],
      ["Unfold the map"],
    );
    const names = document.createElement("div");
    names.className = "resolution-names";
    for (const name of ["Chea", "Chhun", "Kanha"]) {
      const line = document.createElement("s");
      line.textContent = name;
      names.append(line);
    }
    const sora = document.createElement("strong");
    sora.textContent = "Sora";
    names.append(sora);
    this.content.append(names);
    await action;
  }
  async map(): Promise<void> {
    const action = this.show(
      "The village pagoda",
      [
        "Blood seeps across the map. The first faint mark darkens: the village pagoda.",
        "Sora fills the third circle. Four nights remain.",
      ],
      ["Close the map"],
    );
    const map = document.createElement("div");
    map.className = "resolution-map";
    map.innerHTML =
      '<svg viewBox="0 0 400 160" role="img" aria-label="River map with the village pagoda marked in blood"><path d="M20 140 Q100 20 160 90 T380 20" fill="none" stroke="#697b79" stroke-width="12"/><path d="M95 55 L120 30 L145 55 M100 55 H140 V85 H100 Z" fill="none" stroke="currentColor" stroke-width="3"/><circle cx="120" cy="65" r="32" fill="#842a27" opacity=".35"/><text x="165" y="60" fill="currentColor" font-size="18">Village pagoda</text><g fill="none" stroke="currentColor" stroke-width="2"><circle cx="220" cy="125" r="7"/><circle cx="270" cy="100" r="7"/><circle cx="305" cy="65" r="7"/><circle cx="360" cy="85" r="7"/></g></svg>';
    const nights = document.createElement("p");
    nights.setAttribute("aria-label", "Night 3 of 7");
    nights.textContent = "● ● ● ○ ○ ○ ○";
    map.append(nights);
    this.content.append(map);
    await action;
  }
  /** The end credits under the game's logo: the painted title from the welcome screen. */
  credits(paragraphs: string[], buttons: string[]): Promise<number> {
    const title = "Boon Sop: The Unbroken Debt";
    const action = this.show(title, paragraphs, buttons);
    const heading = this.content.querySelector("h1")!;
    heading.className = "resolution-logo";
    heading.setAttribute("aria-label", title);
    const mark = document.createElement("span");
    mark.lang = "km";
    mark.textContent = "បុណ្យសព";
    const logo = document.createElement("img");
    logo.src = `${import.meta.env.BASE_URL}assets/ui/welcome-title.webp`;
    logo.alt = "";
    logo.width = 1600;
    logo.height = 855;
    heading.replaceChildren(mark, logo);
    return action;
  }
  summary(progress: ResolutionProgress): Promise<number> {
    this.panel.classList.add("resolution-book");
    return this.show(
      "The House of Mourning",
      [
        "Episode 1 · Sora’s sketchbook",
        "First seal broken · Night 3 of 7",
        `Lore found: ${progress.lore.length} / 5${progress.lore.length ? ` · ${progress.lore.join(", ")}` : ""}`,
        `Respect: ${progress.flags.get("ep1.betel.firstTry", false) ? "●" : "○"} First offering · ${progress.flags.get("ep1.incense.neglected", false) ? "○" : "●"} Vigil kept`,
        `Journal: ${progress.flags.get("ep1.journal.shared", false) ? "shown to Vuthy" : "kept from Vuthy"}`,
      ],
      ["View credits"],
    );
  }
  hide(): void {
    this.panel.hidden = true;
    this.previousFocus?.focus({ preventScroll: true });
  }
}
