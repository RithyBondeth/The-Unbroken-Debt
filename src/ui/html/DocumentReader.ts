import "./document.css";

/** A readable translation alongside the physical journal, with keyboard and button controls. */
export class DocumentReader {
  private readonly panel = document.createElement("article");
  private readonly title = document.createElement("h2");
  private readonly body = document.createElement("p");
  private readonly count = document.createElement("span");
  private readonly next = document.createElement("button");
  private page = 0;
  private closeAction: (() => void) | null = null;
  private pageAction: ((page: number) => void) | null = null;
  private previousFocus: HTMLElement | null = null;

  constructor(
    private readonly pages: readonly { title: string; text: string }[],
    label = "Sok’s journal · Translation",
  ) {
    this.panel.className = "document-reader";
    this.panel.hidden = true;
    this.panel.setAttribute("aria-label", label);
    this.panel.setAttribute("role", "dialog");
    this.panel.setAttribute("aria-modal", "true");
    const byline = document.createElement("small");
    byline.textContent = label;
    const controls = document.createElement("footer");
    const previous = document.createElement("button");
    previous.textContent = "← Previous";
    previous.onclick = () => this.turn(-1);
    this.next.onclick = () => this.turn(1);
    const close = document.createElement("button");
    close.textContent = "Close · Esc";
    close.onclick = () => this.close();
    controls.append(previous, this.count, this.next, close);
    this.panel.append(byline, this.title, this.body, controls);
    document.body.append(this.panel);
    window.addEventListener(
      "keydown",
      (event) => {
        if (!this.open) return;
        if (event.code === "Tab") {
          event.preventDefault();
          event.stopImmediatePropagation();
          const buttons = [...this.panel.querySelectorAll("button")];
          const current = buttons.indexOf(document.activeElement as HTMLButtonElement);
          buttons[(current + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length].focus();
          return;
        }
        if (["Escape", "ArrowLeft", "ArrowRight", "KeyE", "Enter"].includes(event.code)) {
          event.preventDefault();
          event.stopImmediatePropagation();
          if (event.repeat) return;
          if (event.code === "Escape") this.close();
          else if (
            event.code === "Enter" &&
            document.activeElement instanceof HTMLButtonElement &&
            this.panel.contains(document.activeElement)
          )
            document.activeElement.click();
          else this.turn(event.code === "ArrowLeft" ? -1 : 1);
        }
      },
      { capture: true },
    );
  }

  get open(): boolean {
    return !this.panel.hidden;
  }

  get pageIndex(): number {
    return this.page;
  }

  show(page: number, onClose: () => void, onPage?: (page: number) => void): void {
    this.page = Math.max(0, Math.min(this.pages.length - 1, page));
    this.closeAction = onClose;
    this.pageAction = onPage ?? null;
    this.previousFocus =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    this.panel.hidden = false;
    this.paint();
    this.next.focus({ preventScroll: true });
  }

  close(): void {
    if (!this.open) return;
    this.panel.hidden = true;
    this.previousFocus?.focus({ preventScroll: true });
    this.closeAction?.();
    this.closeAction = null;
    this.pageAction = null;
  }

  private turn(direction: number): void {
    if (direction > 0 && this.page === this.pages.length - 1) return this.close();
    this.page = Math.max(0, Math.min(this.pages.length - 1, this.page + direction));
    this.paint();
  }

  private paint(): void {
    this.title.textContent = this.pages[this.page].title;
    this.body.textContent = this.pages[this.page].text;
    this.count.textContent = `${this.page + 1} / ${this.pages.length}`;
    this.next.textContent = this.page === this.pages.length - 1 ? "Finish · E" : "Next · E →";
    this.pageAction?.(this.page);
  }
}
