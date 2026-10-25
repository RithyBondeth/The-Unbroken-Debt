import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** Every .ts file under a folder. */
function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? sources(path) : path.endsWith(".ts") ? [path] : [];
  });
}

describe("material colour space", () => {
  // PBR albedo is linear; a hex string is sRGB. Used as is, #3c2417 dark endgrain
  // renders as a pale tan (scene pass, October 2026). The sketchbook's materials are
  // tuned to its own reading light and stay as authored.
  it("converts hex albedo colours to linear space in the episode's runtime models", () => {
    const offenders = sources("src/episodes").flatMap((file) =>
      readFileSync(file, "utf8")
        .split("\n")
        .map((line, i) => ({ line, at: `${file}:${i + 1}` }))
        .filter(({ line }) => /albedoColor\s*=\s*Color3\.FromHexString\(/.test(line))
        .filter(({ line }) => !line.includes(".toLinearSpace()"))
        .map(({ at }) => at),
    );
    expect(offenders).toEqual([]);
  });
});
