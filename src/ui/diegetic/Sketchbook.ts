import type { Scene } from "@babylonjs/core/scene";
import type { Node } from "@babylonjs/core/node";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { BookModel, type PageSlot } from "./BookModel";
import { PagePainter } from "./PagePainter";
import type { SectionId, SketchbookData } from "./sketchbookContent";

const OPEN_SECONDS = 0.6;
const FLIP_SECONDS = 0.55;
const WRITE_SECONDS = 1.6;

/** Held pose relative to the camera: lowered at the hip (closed) and raised to read (open). */
const POSE = {
  closed: { position: new Vector3(0.07, -0.42, 0.34), tilt: 1.1 },
  open: { position: new Vector3(-0.006, -0.045, 0.33), tilt: 0.29 },
};

const smooth = (x: number) => {
  const c = Math.min(1, Math.max(0, x));
  return c * c * (3 - 2 * c);
};

interface Flip {
  from: number;
  to: number;
  t: number;
}

/**
 * Sora's sketchbook in her hands (Controls and Interface, section 5): opens at
 * the newest entry, turns pages, jumps to a section by its ribbon tab, and
 * writes new entries in as the player watches. The game keeps running.
 */
export class Sketchbook {
  readonly book: BookModel;
  readonly painter: PagePainter;
  readonly written = new Set<string>();
  spread = 0;
  /** Milliseconds spent painting each page texture (for the spike's budget check). */
  readonly paintMs: number[] = [];
  /** Painting cost of the last page turn, all textures together. */
  lastTurnMs = 0;

  private opening = 0;
  private wantOpen = false;
  private flip: Flip | null = null;
  private readonly queue: number[] = [];
  private writing: { entryId: string; t: number } | null = null;
  private newest: string | null = null;

  constructor(
    scene: Scene,
    private readonly data: SketchbookData,
    textureHeight: number,
    holder: Node,
  ) {
    this.painter = new PagePainter(data, textureHeight);
    this.book = new BookModel(scene, this.painter.textureWidth, textureHeight);
    this.book.root.parent = holder;
    this.painter.layout(this.written);
    this.applyPose();
  }

  get isOpen(): boolean {
    return this.wantOpen && this.opening >= 1;
  }

  get isBusy(): boolean {
    return this.flip !== null || this.writing !== null || (this.opening > 0 && this.opening < 1);
  }

  get section(): SectionId {
    return this.painter.pages[this.spread * 2]?.section ?? "map";
  }

  /** Forgets paint timings, e.g. after the first paints that make the paper and load fonts. */
  resetStats(): void {
    this.paintMs.length = 0;
    this.lastTurnMs = 0;
  }

  /** Writes entries without animation (state at load or a checkpoint). */
  restore(ids: readonly string[]): void {
    for (const id of ids) this.written.add(id);
    this.newest = ids.at(-1) ?? null;
    this.painter.layout(this.written);
    this.spread = this.painter.spreadOf(this.newest);
    this.paintSpread();
  }

  /** Q: opens at the newest entry, or closes. */
  toggle(): void {
    this.wantOpen = !this.wantOpen;
    // Closing midway through writing or a page turn must not leave a hidden,
    // permanently busy book blocking world interaction and object inspection.
    if (!this.wantOpen && (this.writing || this.flip || this.queue.length)) {
      this.writing = null;
      this.flip = null;
      this.queue.length = 0;
      this.book.setFlip(null);
      this.spread = this.painter.spreadOf(this.newest);
      this.paintSpread();
    }
    if (this.wantOpen && !this.flip) {
      this.spread = this.painter.spreadOf(this.newest);
      this.paintSpread();
    }
  }

  /** Close safely even during an opening or a queued writing animation. */
  close(): void {
    if (this.wantOpen) this.toggle();
  }

  /** A / D: one spread back or forward. */
  turn(direction: -1 | 1): void {
    const last = this.queue.at(-1) ?? this.flip?.to ?? this.spread;
    const to = Math.min(this.painter.spreadCount - 1, Math.max(0, last + direction));
    if (to !== last) this.queue.push(to);
  }

  /** A ribbon tab: straight to the first spread of a section. */
  goToSection(section: SectionId): void {
    const to = this.painter.sectionSpread(section);
    if (to !== (this.queue.at(-1) ?? this.flip?.to ?? this.spread)) this.queue.push(to);
  }

  /** Writes a new entry: the book turns to it and Sora's hand writes it in. */
  write(entryId: string): void {
    if (this.written.has(entryId)) return;
    this.written.add(entryId);
    this.newest = entryId;
    this.relayout();
    this.wantOpen = true;
    const to = this.painter.spreadOf(entryId);
    if (to !== this.spread) this.queue.push(to);
    this.writing = { entryId, t: -1 };
  }

  /** The "large text" setting: lays the pages out again at a bigger size. */
  setTextScale(scale: number): void {
    const section = this.section;
    this.painter.textScale = scale;
    this.relayout();
    this.spread = this.painter.sectionSpread(section);
    this.paintSpread();
  }

  /** Next entry from the episode data that is not written yet. */
  nextUnwritten(): string | null {
    return this.data.entries.find((e) => !this.written.has(e.id))?.id ?? null;
  }

  update(dt: number): void {
    this.opening = Math.min(
      1,
      Math.max(0, this.opening + (this.wantOpen ? dt : -dt) / OPEN_SECONDS),
    );
    this.applyPose();

    if (!this.flip && this.queue.length > 0 && this.opening >= 1)
      this.startFlip(this.queue.shift() as number);
    if (this.flip) {
      this.flip.t = Math.min(1, this.flip.t + dt / FLIP_SECONDS);
      const forward = this.flip.to > this.flip.from;
      this.book.setFlip(forward ? this.flip.t : 1 - this.flip.t);
      if (this.flip.t >= 1) {
        this.spread = this.flip.to;
        this.flip = null;
        this.book.setFlip(null);
        this.paintSpread();
      }
    }

    // Writing starts once the book is open on the right spread.
    if (this.writing && !this.flip && this.queue.length === 0 && this.opening >= 1) {
      if (this.writing.t < 0) this.writing.t = 0;
      this.writing.t = Math.min(1, this.writing.t + dt / WRITE_SECONDS);
      const page = this.painter.pages.findIndex((p) =>
        p.layout.blocks.some((b) => b.entryId === this.writing?.entryId),
      );
      this.paint(page % 2 === 0 ? "left" : "right", page, {
        entryId: this.writing.entryId,
        progress: this.writing.t,
      });
      if (this.writing.t >= 1) this.writing = null;
    }
  }

  private relayout(): void {
    const section = this.section;
    this.painter.layout(this.written);
    this.spread = Math.min(this.painter.sectionSpread(section), this.painter.spreadCount - 1);
    this.paintSpread();
  }

  private startFlip(to: number): void {
    const from = this.spread;
    const started = performance.now();
    if (to > from) {
      // The right page lifts and lands as the new left page.
      this.paint("leafFront", from * 2 + 1);
      this.paint("leafBack", to * 2);
      this.paint("right", to * 2 + 1);
    } else {
      this.paint("leafBack", from * 2);
      this.paint("leafFront", to * 2 + 1);
      this.paint("left", to * 2);
    }
    this.lastTurnMs = performance.now() - started;
    this.flip = { from, to, t: 0 };
    this.book.setFlip(to > from ? 0 : 1);
  }

  private paintSpread(): void {
    this.paint("left", this.spread * 2);
    this.paint("right", this.spread * 2 + 1);
  }

  private paint(
    slot: PageSlot,
    page: number,
    reveal: { entryId: string; progress: number } | null = null,
  ): void {
    const started = performance.now();
    const texture = this.book.textures[slot];
    const ctx = texture.getContext() as unknown as CanvasRenderingContext2D;
    this.painter.paint(ctx, page >= 0 && page < this.painter.pages.length ? page : null, reveal);
    texture.update();
    this.paintMs.push(performance.now() - started);
    if (this.paintMs.length > 200) this.paintMs.shift();
  }

  private applyPose(): void {
    const raise = smooth(this.opening / 0.55);
    const hinge = smooth((this.opening - 0.2) / 0.6);
    const root = this.book.root;
    Vector3.LerpToRef(POSE.closed.position, POSE.open.position, raise, root.position);
    // A narrow game pane needs the book closer; landscape framing keeps the S5 pose.
    const engine = root.getScene().getEngine();
    const aspect = engine.getRenderWidth() / engine.getRenderHeight();
    const readingZ = POSE.open.position.z * Math.max(0.78, Math.min(1, aspect / 1.4));
    root.position.z = POSE.closed.position.z + (readingZ - POSE.closed.position.z) * raise;
    const tilt = POSE.closed.tilt + (POSE.open.tilt - POSE.closed.tilt) * raise;
    // Page normal (local +y) towards the eye, the top of the page tipped away.
    root.rotation.set(-Math.PI / 2 + tilt, -0.025 * raise, 0.025 * raise);
    this.book.setOpen(hinge);
    root.setEnabled(this.opening > 0);
  }
}
