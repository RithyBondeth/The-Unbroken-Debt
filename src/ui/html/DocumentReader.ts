import "./document.css";
import { setControlText } from "./controlText";

/** A readable translation alongside the physical journal, with keyboard and button controls. */
export class DocumentReader {
  private static nextId = 0;
  private readonly overlay = document.createElement("div");
  private readonly panel = document.createElement("article");
  private readonly content = document.createElement("div");
  private readonly title = document.createElement("h2");
  private readonly body = document.createElement("p");
  private readonly count = document.createElement("span");
  private readonly next = document.createElement("button");
  private readonly previous = document.createElement("button");
  private page = 0;
  private closeAction: (() => void) | null = null;
  private pageAction: ((page: number) => void) | null = null;
  private previousFocus: HTMLElement | null = null;

  constructor(
    private readonly pages: readonly { title: string; text: string }[],
    label = "Sok’s journal · Translation",
  ) {
    this.overlay.className = "document-reader-overlay";
    this.overlay.hidden = true;
    this.panel.className = "document-reader";
    this.panel.hidden = true;
    this.panel.setAttribute("aria-label", label);
    this.panel.setAttribute("role", "dialog");
    this.panel.setAttribute("aria-modal", "true");
    this.title.id = `document-reader-title-${DocumentReader.nextId++}`;
    this.panel.setAttribute("aria-labelledby", this.title.id);
    this.content.className = "document-reader-content";
    this.content.tabIndex = 0;
    const byline = document.createElement("small");
    byline.textContent = label;
    const controls = document.createElement("footer");
    this.previous.textContent = "← Previous";
    this.previous.onclick = () => this.turn(-1);
    this.previous.hidden = this.count.hidden = this.pages.length === 1;
    this.count.setAttribute("role", "status");
    this.next.className = "ui-button ui-button-primary document-reader-next";
    this.next.onclick = () => this.turn(1);
    const close = document.createElement("button");
    setControlText(close, "Close · Esc");
    close.onclick = () => this.close();
    controls.append(this.previous, this.count, this.next, close);
    this.content.append(byline, this.title, this.body);
    this.panel.append(this.content, controls);
    this.overlay.append(this.panel);
    document.body.append(this.overlay);
    window.addEventListener(
      "keydown",
      (event) => {
        if (!this.open) return;
        if (event.code === "Tab") {
          event.preventDefault();
          event.stopImmediatePropagation();
          const focusable: HTMLElement[] = [
            ...(this.content.scrollHeight > this.content.clientHeight ? [this.content] : []),
            ...this.panel.querySelectorAll<HTMLButtonElement>(
              "button:not(:disabled):not([hidden])",
            ),
          ];
          const current = focusable.indexOf(document.activeElement as HTMLElement);
          const index =
            current < 0
              ? event.shiftKey
                ? focusable.length - 1
                : 0
              : (current + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length;
          focusable[index].focus();
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
    this.overlay.hidden = false;
    this.paint();
    this.next.focus({ preventScroll: true });
  }

  close(): void {
    if (!this.open) return;
    this.panel.hidden = true;
    this.overlay.hidden = true;
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
    this.previous.disabled = this.page === 0;
    if (this.previous.disabled && document.activeElement === this.previous)
      this.next.focus({ preventScroll: true });
    this.content.scrollTop = 0;
    setControlText(this.next, this.page === this.pages.length - 1 ? "Finish · E" : "Next · E →");
    this.pageAction?.(this.page);
  }
}
