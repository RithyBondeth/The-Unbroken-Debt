import { describe, expect, it } from "vitest";
import {
  layoutPages,
  wrapText,
  type Measure,
  type PageSpec,
} from "../../src/ui/diegetic/pageLayout";

// One millimetre per character (grapheme cluster for Khmer), whatever the font.
const graphemes = new Intl.Segmenter("km", { granularity: "grapheme" });
const measure: Measure = (text) => Array.from(graphemes.segment(text)).length;

describe("wrapText", () => {
  it("breaks English between words", () => {
    expect(
      wrapText("Keep the lamp burning. Keep the incense alight.", 16, "body", measure),
    ).toEqual(["Keep the lamp", "burning. Keep", "the incense", "alight."]);
  });

  it("keeps explicit line breaks", () => {
    expect(wrapText("Four nights.\nThe jars below.", 40, "body", measure)).toEqual([
      "Four nights.",
      "The jars below.",
    ]);
  });

  it("breaks Khmer between words although it has no spaces", () => {
    // "Funeral tent" + "under the house": two words with no space between them.
    const lines = wrapText("រោងបុណ្យក្រោមផ្ទះ", 6, "khmer", measure);
    expect(lines.length).toBe(2);
    expect(lines.join("")).toBe("រោងបុណ្យក្រោមផ្ទះ");
  });

  it("never splits a Khmer consonant cluster", () => {
    // Narrower than one word: it must break, but only between grapheme clusters.
    const lines = wrapText("ផ្ទះរោងដឿង", 2, "khmer", measure);
    const clusters = Array.from(graphemes.segment("ផ្ទះរោងដឿង"), (s) => s.segment);
    expect(lines.join("")).toBe("ផ្ទះរោងដឿង");
    for (const line of lines) {
      const parts = Array.from(graphemes.segment(line), (s) => s.segment);
      for (const part of parts) expect(clusters).toContain(part);
    }
  });
});

describe("layoutPages", () => {
  const spec: PageSpec = {
    width: 30,
    height: 40,
    margin: { top: 5, right: 5, bottom: 5, left: 5 },
    lineHeight: { body: 5, khmer: 6, heading: 6, small: 4 },
    gap: 3,
  };

  it("keeps an entry together and moves it to the next page when it does not fit", () => {
    const pages = layoutPages(
      [
        { id: "a", blocks: [{ kind: "drawing", id: "lamp", height: 20 }] },
        { id: "b", blocks: [{ kind: "text", font: "body", text: "one two three four five six" }] },
      ],
      spec,
      measure,
    );
    expect(pages.length).toBe(2);
    expect(pages[0].blocks.map((b) => b.entryId)).toEqual(["a"]);
    expect(pages[1].blocks[0]).toMatchObject({ entryId: "b", y: 5 });
  });

  it("continues text longer than a page on the next page", () => {
    const long = Array.from({ length: 30 }, (_, i) => `word${i}`).join(" ");
    const pages = layoutPages(
      [{ id: "c", blocks: [{ kind: "text", font: "body", text: long }] }],
      spec,
      measure,
    );
    expect(pages.length).toBe(2);
    const lines = pages.flatMap((p) => p.blocks.flatMap((b) => b.lines));
    expect(lines.join(" ")).toBe(long);
    for (const page of pages) {
      for (const block of page.blocks) expect(block.y + block.height).toBeLessThanOrEqual(35);
    }
  });
});
