import { describe, expect, it } from "vitest";
import { parseVoiceManifest } from "../../src/episodes/ep1/data/voiceManifest";
describe("recorded dialogue selection", () => {
  const take = {
    language: "km-KH",
    paragraphs: Array.from({ length: 4 }, (_, k) => [`assets/ep1/audio/vo_sok_km_KH_${k + 1}.ogg`]),
  };
  it("accepts a complete Khmer take independently of subtitle language", () => {
    expect(parseVoiceManifest(take, 4)?.language).toBe("km-KH");
  });
  it("rejects incomplete takes rather than mixing spoken languages", () => {
    expect(parseVoiceManifest({ ...take, paragraphs: take.paragraphs.slice(1) }, 4)).toBeNull();
  });
  it("limits recordings to project audio assets", () => {
    for (const path of [
      "https://example.com/voice.ogg",
      "assets/ep1/audio/../secret.wav",
      "assets/ep1/audio/x.js",
    ])
      expect(
        parseVoiceManifest({ ...take, paragraphs: [[path], ...take.paragraphs.slice(1)] }, 4),
      ).toBeNull();
  });
});
