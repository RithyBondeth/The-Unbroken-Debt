import { describe, expect, it } from "vitest";
import { subtitleChunks } from "../../src/ui/html/StoryUi";

describe("subtitleChunks", () => {
  it("keeps a short line whole", () => {
    const line = "Grandma's letters… I can't read them tonight.";
    expect(subtitleChunks(line)).toEqual([line]);
  });

  it("splits a long line at its pauses, keeping every word", () => {
    const line = "You must come home. Right now. Uncle Sok… he broke it… it's inside the house—";
    const chunks = subtitleChunks(line);
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.every((c) => c.length <= 60)).toBe(true);
    expect(chunks.join(" ")).toBe(line);
  });
});
