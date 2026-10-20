/**
 * Text wrapping and page layout for the sketchbook (Controls and Interface,
 * section 5). Pure functions over a `measure` callback, so they can be tested
 * without a canvas. All sizes are in millimetres of paper.
 */

/** Width of `text` set in `font` (a role name), in millimetres. */
export type Measure = (text: string, font: FontRole) => number;

export type FontRole = "body" | "khmer" | "heading" | "small";

/** A page of Sora's sketchbook: A5 portrait, as in the Art Bible. */
export interface PageSpec {
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
  /** Line height per font role. */
  lineHeight: Record<FontRole, number>;
  /** Space between entries. */
  gap: number;
}

export type Block =
  { kind: "text"; font: FontRole; text: string } | { kind: "drawing"; id: string; height: number };

/** An entry's blocks stay together on one page unless they cannot fit any page. */
export interface LayoutEntry {
  id: string;
  blocks: Block[];
}

export interface PlacedBlock {
  entryId: string;
  block: Block;
  /** Top-left of the block on the page. */
  x: number;
  y: number;
  height: number;
  /** Wrapped lines (text blocks only). */
  lines: string[];
}

export interface PageLayout {
  blocks: PlacedBlock[];
}

/** Line breaks: word boundaries where the script has them, never inside a cluster. */
function segments(text: string, granularity: "word" | "grapheme"): string[] {
  // Khmer has no spaces between words; the word segmenter finds the breaks.
  const segmenter = new Intl.Segmenter("km", { granularity });
  return Array.from(segmenter.segment(text), (s) => s.segment);
}

/**
 * Greedy line wrapping. Breaks at word boundaries (including between Khmer
 * words, which have no spaces), and only splits a word that is wider than the
 * line, between grapheme clusters so stacked consonants stay whole.
 */
export function wrapText(
  text: string,
  maxWidth: number,
  font: FontRole,
  measure: Measure,
): string[] {
  const fits = (s: string) => measure(s.trimEnd(), font) <= maxWidth;
  const lines: string[] = [];
  for (const paragraph of text.split("\n")) {
    let line = "";
    for (const word of segments(paragraph, "word")) {
      if (line !== "" && !fits(line + word)) {
        lines.push(line.trimEnd());
        line = word.trimStart();
      } else {
        line += word;
      }
      if (fits(line)) continue;
      // A word wider than the line: split it between grapheme clusters.
      let part = "";
      for (const grapheme of segments(line, "grapheme")) {
        if (part !== "" && !fits(part + grapheme)) {
          lines.push(part);
          part = "";
        }
        part += grapheme;
      }
      line = part;
    }
    lines.push(line.trimEnd());
  }
  return lines;
}

/**
 * Flows entries onto pages. Each entry starts on the page where it fits whole;
 * an entry taller than a whole page starts on a fresh page and continues.
 */
export function layoutPages(
  entries: LayoutEntry[],
  spec: PageSpec,
  measure: Measure,
): PageLayout[] {
  const { margin } = spec;
  const width = spec.width - margin.left - margin.right;
  const bottom = spec.height - margin.bottom;
  const pages: PageLayout[] = [{ blocks: [] }];
  let y = margin.top;

  const placed = (entry: LayoutEntry) =>
    entry.blocks.map((block) => {
      const lines = block.kind === "text" ? wrapText(block.text, width, block.font, measure) : [];
      const height =
        block.kind === "text" ? lines.length * spec.lineHeight[block.font] : block.height;
      return { block, lines, height };
    });

  for (const entry of entries) {
    const parts = placed(entry);
    const total = parts.reduce((sum, p) => sum + p.height, 0);
    const page = () => pages[pages.length - 1];
    if (page().blocks.length > 0 && y + spec.gap + total > bottom) {
      pages.push({ blocks: [] });
      y = margin.top;
    } else if (page().blocks.length > 0) {
      y += spec.gap;
    }
    for (const part of parts) {
      if (part.block.kind === "text") {
        // Split long text across pages line by line.
        let lines = part.lines;
        const lineHeight = spec.lineHeight[part.block.font];
        while (lines.length > 0) {
          const room = Math.max(1, Math.floor((bottom - y) / lineHeight));
          if (y + lineHeight > bottom && page().blocks.length > 0) {
            pages.push({ blocks: [] });
            y = margin.top;
            continue;
          }
          const chunk = lines.slice(0, room);
          page().blocks.push({
            entryId: entry.id,
            block: part.block,
            x: margin.left,
            y,
            height: chunk.length * lineHeight,
            lines: chunk,
          });
          y += chunk.length * lineHeight;
          lines = lines.slice(room);
        }
      } else {
        if (y + part.height > bottom && page().blocks.length > 0) {
          pages.push({ blocks: [] });
          y = margin.top;
        }
        page().blocks.push({
          entryId: entry.id,
          block: part.block,
          x: margin.left,
          y,
          height: part.height,
          lines: [],
        });
        y += part.height;
      }
    }
  }
  return pages;
}
