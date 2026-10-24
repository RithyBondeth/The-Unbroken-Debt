import { drawHousePlan, drawNightCircles, drawSketch, INK, seeded, type Pen } from "./drawings";
import {
  layoutPages,
  type FontRole,
  type LayoutEntry,
  type Measure,
  type PageLayout,
  type PageSpec,
} from "./pageLayout";
import {
  SECTIONS,
  type NightMark,
  type SectionId,
  type SketchbookData,
  type SketchEntry,
} from "./sketchbookContent";

/** A5 portrait page, in millimetres. */
export const PAGE_MM = { width: 148, height: 210 };

const PAPER = "#e8dfcb";
const TEXT_INK = "#1f1b18";
const TAB_ROW = 12; // height of the tab row at the bottom of right pages, mm

/** Font sizes in mm of paper; `scale` is the "large text" setting. */
function fontSizes(scale: number): Record<FontRole, { size: number; line: number }> {
  return {
    body: { size: 8.4 * scale, line: 11.4 * scale },
    khmer: { size: 8.8 * scale, line: 14 * scale },
    heading: { size: 9 * scale, line: 12 * scale },
    small: { size: 5.5 * scale, line: 7.5 * scale },
  };
}

function fontFamily(role: FontRole): string {
  // Khmer in Sora's Khmer hand; English in her English hand, falling back to Khmer.
  return role === "khmer" ? '"Freehand"' : '"Patrick Hand", "Freehand"';
}

export function canvasFont(role: FontRole, px: number): string {
  return `${px}px ${fontFamily(role)}`;
}

export type PageKind = "content" | "map" | "lore" | "blank";

export interface BookPage {
  section: SectionId;
  kind: PageKind;
  layout: PageLayout;
  /** First page of its section (gets the section heading). */
  first: boolean;
}

export interface RevealState {
  entryId: string;
  /** 0–1: how much of the entry Sora has written so far. */
  progress: number;
}

/**
 * Lays out the sketchbook and paints its pages onto canvases. Each section
 * starts on a left-hand page; the book is read as spreads of two pages.
 */
export class PagePainter {
  pages: BookPage[] = [];
  nights: NightMark[] = Array<NightMark>(7).fill("empty");
  private paper: HTMLCanvasElement | null = null;
  private readonly measureCtx: CanvasRenderingContext2D;
  private readonly measure: Measure;

  constructor(
    private readonly data: SketchbookData,
    /** Texture height in pixels; width follows the page's proportions. */
    readonly textureHeight: number,
    public textScale = 1,
  ) {
    const scratch = document.createElement("canvas");
    this.measureCtx = scratch.getContext("2d") as CanvasRenderingContext2D;
    // Measure at a fixed 10 px per mm, then convert back to millimetres.
    this.measure = (text, role) => {
      this.measureCtx.font = canvasFont(role, fontSizes(this.textScale)[role].size * 10);
      return this.measureCtx.measureText(text).width / 10;
    };
  }

  get textureWidth(): number {
    return Math.round((this.textureHeight * PAGE_MM.width) / PAGE_MM.height);
  }

  /** Pixels per millimetre of paper on the page texture. */
  get mm(): number {
    return this.textureHeight / PAGE_MM.height;
  }

  get bodyFontMm(): number {
    return fontSizes(this.textScale).body.size;
  }

  get spreadCount(): number {
    return this.pages.length / 2;
  }

  /** Rebuilds every page from the entries written so far. */
  layout(written: ReadonlySet<string>): void {
    const sizes = fontSizes(this.textScale);
    const spec: PageSpec = {
      ...PAGE_MM,
      margin: { top: 24, right: 14, bottom: 14 + TAB_ROW, left: 16 },
      lineHeight: {
        body: sizes.body.line,
        khmer: sizes.khmer.line,
        heading: sizes.heading.line,
        small: sizes.small.line,
      },
      gap: 9,
    };
    const entries = this.data.entries.filter((e) => written.has(e.id));
    this.nights = Array<NightMark>(7).fill("empty");
    for (const e of entries) if (e.nights) this.nights = [...e.nights];

    const pages: BookPage[] = [];
    for (const { id: section } of SECTIONS) {
      const own = entries.filter((e) => e.section === section).map(toLayoutEntry);
      const start = pages.length;
      if (section === "map") {
        // The map page leads the section; notes about the nights follow it.
        pages.push({ section, kind: "map", layout: { blocks: [] }, first: true });
      }
      if (section === "lore") {
        pages.push({ section, kind: "lore", layout: { blocks: [] }, first: true });
      } else if (own.length > 0 || section !== "map") {
        const layouts = own.length > 0 ? layoutPages(own, spec, this.measure) : [{ blocks: [] }];
        for (const layout of layouts)
          pages.push({ section, kind: "content", layout, first: pages.length === start });
      }
      if ((pages.length - start) % 2 === 1)
        pages.push({ section, kind: "blank", layout: { blocks: [] }, first: false });
    }
    this.pages = pages;
  }

  /** Spread showing `entryId`, or the last spread with writing on it. */
  spreadOf(entryId: string | null): number {
    const index = this.pages.findIndex((p) => p.layout.blocks.some((b) => b.entryId === entryId));
    return Math.max(0, Math.floor(index / 2));
  }

  /** First spread of a section (the ribbon tab). */
  sectionSpread(section: SectionId): number {
    return Math.floor(this.pages.findIndex((p) => p.section === section) / 2);
  }

  /** Paints page `index` (any page; `null` paints blank paper). */
  paint(
    ctx: CanvasRenderingContext2D,
    index: number | null,
    reveal: RevealState | null = null,
  ): void {
    const mm = this.mm;
    const page = index === null ? null : this.pages[index];
    const right = index !== null && index % 2 === 1;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(this.paperCanvas(), 0, 0);

    // Shade towards the spine so the two pages read as a bound book.
    const spineX = right ? 0 : this.textureWidth;
    const gradient = ctx.createLinearGradient(
      spineX,
      0,
      right ? 14 * mm : this.textureWidth - 14 * mm,
      0,
    );
    gradient.addColorStop(0, "rgba(60,40,20,0.28)");
    gradient.addColorStop(1, "rgba(60,40,20,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, this.textureWidth, this.textureHeight);

    if (page) {
      const pen: Pen = { ctx, mm, rand: seeded(`${page.section}${index}`) };
      if (page.first) {
        const label = SECTIONS.find((s) => s.id === page.section)?.label ?? "";
        ctx.font = canvasFont("heading", fontSizes(this.textScale).heading.size * mm);
        ctx.fillStyle = TEXT_INK;
        ctx.fillText(label, 16 * mm, 16 * mm);
      }
      if (page.kind === "map") this.paintMap(pen);
      if (page.kind === "lore") this.paintLore(pen);
      for (const placed of page.layout.blocks) {
        const entry = this.data.entries.find((e) => e.id === placed.entryId);
        const amount =
          reveal && reveal.entryId === placed.entryId
            ? this.revealFor(entry, placed, reveal.progress)
            : 1;
        if (amount <= 0) continue;
        if (placed.block.kind === "drawing") {
          ctx.save();
          ctx.globalAlpha = amount;
          const pageWidth = PAGE_MM.width - 30;
          drawSketch(
            { ...pen, rand: seeded(placed.entryId) },
            placed.block.id,
            placed.x,
            placed.y,
            pageWidth,
            placed.height,
          );
          ctx.restore();
        } else {
          this.paintLines(
            ctx,
            placed.entryId,
            placed.block.font,
            placed.lines,
            placed.x,
            placed.y,
            amount,
          );
        }
      }
    }
    ctx.restore();
  }

  /** Lines in Sora's hand: each a little rotated and off the baseline. */
  private paintLines(
    ctx: CanvasRenderingContext2D,
    entryId: string,
    role: FontRole,
    lines: string[],
    x: number,
    y: number,
    amount: number,
  ): void {
    const mm = this.mm;
    const { size, line } = fontSizes(this.textScale)[role];
    const graphemes = new Intl.Segmenter("km", { granularity: "grapheme" });
    const total = lines.reduce((n, l) => n + [...graphemes.segment(l)].length, 0);
    let budget = Math.ceil(total * amount);
    ctx.font = canvasFont(role, size * mm);
    ctx.fillStyle = TEXT_INK;
    lines.forEach((text, i) => {
      if (budget <= 0) return;
      const parts = Array.from(graphemes.segment(text), (s) => s.segment);
      const shown = parts.slice(0, budget).join("");
      budget -= parts.length;
      const rand = seeded(`${entryId}:${role}:${i}`);
      const baseline = y + i * line + line * 0.74 + (rand() - 0.5) * 0.5;
      ctx.save();
      ctx.translate((x + (rand() - 0.5) * 0.8) * mm, baseline * mm);
      ctx.rotate(((rand() - 0.5) * 0.8 * Math.PI) / 180);
      ctx.fillText(shown, 0, 0);
      ctx.restore();
    });
  }

  /** How much of one block is visible while its entry is being written. */
  private revealFor(
    entry: SketchEntry | undefined,
    placed: { block: { kind: string; font?: FontRole } },
    progress: number,
  ): number {
    if (!entry) return 1;
    // Text first (English, then Khmer), then the drawing.
    const order: string[] = [];
    if (entry.text) order.push("body");
    if (entry.khmer) order.push("khmer");
    if (entry.drawing) order.push("drawing");
    const key = placed.block.kind === "drawing" ? "drawing" : (placed.block.font ?? "body");
    const i = order.indexOf(key);
    const share = 1 / order.length;
    return Math.min(1, Math.max(0, (progress - i * share) / share));
  }

  private paintMap(pen: Pen): void {
    const { ctx, mm } = pen;
    drawNightCircles(pen, this.nights, 20, 24, 108);
    drawHousePlan(pen, 22, 56, 104, 92);
    for (const label of this.data.mapLabels) {
      ctx.font = canvasFont("small", fontSizes(this.textScale).small.size * mm);
      ctx.fillStyle = TEXT_INK;
      ctx.fillText(label.text, label.x * mm, label.y * mm);
      if (label.khmer) {
        ctx.font = canvasFont("khmer", fontSizes(this.textScale).small.size * 1.15 * mm);
        ctx.fillText(label.khmer, label.x * mm, (label.y + 8 * this.textScale) * mm);
      }
    }
  }

  private paintLore(pen: Pen): void {
    const { ctx, mm } = pen;
    ctx.save();
    ctx.setLineDash([2 * mm, 1.6 * mm]);
    ctx.lineWidth = 0.35 * mm;
    ctx.strokeStyle = INK;
    ctx.globalAlpha = 0.55;
    for (let i = 0; i < this.data.loreCount; i++) {
      const x = 18 + (i % 2) * 58;
      const y = 28 + Math.floor(i / 2) * 62;
      ctx.strokeRect(x * mm, y * mm, 50 * mm, 52 * mm);
      ctx.font = canvasFont("heading", 14 * mm);
      ctx.fillStyle = INK;
      ctx.fillText("?", (x + 21) * mm, (y + 31) * mm);
    }
    ctx.restore();
  }

  /** Cream paper with fibres, foxing and darker edges, made once per size. */
  private paperCanvas(): HTMLCanvasElement {
    if (this.paper) return this.paper;
    const w = this.textureWidth;
    const h = this.textureHeight;
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d") as CanvasRenderingContext2D;
    ctx.fillStyle = PAPER;
    ctx.fillRect(0, 0, w, h);
    const image = ctx.getImageData(0, 0, w, h);
    const rand = seeded("paper");
    for (let i = 0; i < image.data.length; i += 4) {
      const n = (rand() - 0.5) * 6;
      image.data[i] += n;
      image.data[i + 1] += n;
      image.data[i + 2] += n * 0.8;
    }
    ctx.putImageData(image, 0, 0);
    // Foxing: small brown spots, mostly near the edges.
    for (let i = 0; i < 40; i++) {
      const edge = rand() < 0.8;
      const x = edge ? (rand() < 0.5 ? rand() * 0.12 : 0.88 + rand() * 0.12) * w : rand() * w;
      const y = rand() * h;
      const r = (1 + rand() * 5) * this.mm;
      const spot = ctx.createRadialGradient(x, y, 0, x, y, r);
      spot.addColorStop(0, "rgba(150,100,50,0.12)");
      spot.addColorStop(1, "rgba(150,100,50,0)");
      ctx.fillStyle = spot;
      ctx.fillRect(x - r, y - r, r * 2, r * 2);
    }
    const edges = ctx.createRadialGradient(
      w / 2,
      h / 2,
      Math.min(w, h) * 0.45,
      w / 2,
      h / 2,
      Math.max(w, h) * 0.75,
    );
    edges.addColorStop(0, "rgba(120,90,50,0)");
    edges.addColorStop(1, "rgba(120,90,50,0.14)");
    ctx.fillStyle = edges;
    ctx.fillRect(0, 0, w, h);
    this.paper = canvas;
    return canvas;
  }
}

function toLayoutEntry(entry: SketchEntry): LayoutEntry {
  const text = entry.text
    ? [{ kind: "text" as const, font: "body" as const, text: entry.text }]
    : [];
  const khmer = entry.khmer
    ? [{ kind: "text" as const, font: "khmer" as const, text: entry.khmer }]
    : [];
  const drawing = entry.drawing ? [{ kind: "drawing" as const, ...entry.drawing }] : [];
  // Portraits come first on the People page; elsewhere the note comes first.
  const blocks =
    entry.section === "people" ? [...drawing, ...text, ...khmer] : [...text, ...khmer, ...drawing];
  return { id: entry.id, blocks };
}
