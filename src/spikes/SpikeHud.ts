export interface ChecklistItem {
  id: string;
  label: string;
  done: boolean;
}

/**
 * The text panel shown during a spike: title, controls, pass checklist and
 * live readouts. Plain HTML over the canvas; not part of the game's interface.
 */
export class SpikeHud {
  private readonly root: HTMLElement;
  private readonly checklistEl: HTMLUListElement;
  private readonly readoutEl: HTMLPreElement;
  private readonly reportEl: HTMLPreElement;
  private readonly items = new Map<string, ChecklistItem>();

  constructor(title: string, question: string, controls: string[]) {
    this.root = document.createElement("section");
    this.root.className = "spike-hud";

    const h = document.createElement("h1");
    h.textContent = title;
    const q = document.createElement("p");
    q.textContent = question;
    const c = document.createElement("p");
    c.className = "spike-controls";
    c.textContent = controls.join(" · ");

    this.checklistEl = document.createElement("ul");
    this.readoutEl = document.createElement("pre");
    this.reportEl = document.createElement("pre");
    this.reportEl.className = "spike-report";
    this.reportEl.hidden = true;

    this.root.append(h, q, c, this.checklistEl, this.readoutEl, this.reportEl);
    document.body.appendChild(this.root);
    // F2 hides the panel to look at the scene (F3 toggles the stats).
    window.addEventListener("keydown", (e) => {
      if (e.code === "F2") {
        e.preventDefault();
        this.root.hidden = !this.root.hidden;
      }
    });
  }

  addCheck(id: string, label: string): void {
    this.items.set(id, { id, label, done: false });
    this.renderChecklist();
  }

  check(id: string, done = true): void {
    const item = this.items.get(id);
    if (!item || item.done === done) return;
    item.done = done;
    this.renderChecklist();
  }

  isChecked(id: string): boolean {
    return this.items.get(id)?.done ?? false;
  }

  setReadout(lines: string[]): void {
    this.readoutEl.textContent = lines.join("\n");
  }

  showReport(text: string, pass: boolean): void {
    this.reportEl.hidden = false;
    this.reportEl.textContent = text;
    this.reportEl.classList.toggle("pass", pass);
    this.reportEl.classList.toggle("fail", !pass);
  }

  private renderChecklist(): void {
    this.checklistEl.replaceChildren(
      ...[...this.items.values()].map((item) => {
        const li = document.createElement("li");
        li.textContent = `${item.done ? "✔" : "○"} ${item.label}`;
        li.classList.toggle("done", item.done);
        return li;
      }),
    );
  }
}
