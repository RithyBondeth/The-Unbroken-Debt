/** macOS scratch VO for A2-05; replace with the approved Khmer performance before release. */
import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

const source = readFileSync("src/episodes/ep1/data/investigation.ts", "utf8");
const block = source.split("export const SOK_RECORDING = [")[1].split("] as const")[0];
const lines = [...block.matchAll(/^\s*(".+"),$/gm)].map((m) => JSON.parse(m[1]));
const temporary = mkdtempSync(join(tmpdir(), "sok-voice-"));
try {
  for (const [index, line] of lines.entries()) {
    const input = join(temporary, `${index}.aiff`);
    execFileSync("say", ["-v", "Daniel", "-r", "172", "-o", input, line]);
    const base = `public/assets/ep1/audio/vo_sok_scratch_${index + 1}`;
    for (const [extension, codec] of [
      ["ogg", "libopus"],
      ["m4a", "aac"],
    ])
      execFileSync("ffmpeg", [
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        input,
        "-af",
        "highpass=f=280,lowpass=f=3200,acompressor=threshold=0.1:ratio=3:makeup=1.8,alimiter=limit=0.85",
        "-ac",
        "1",
        "-ar",
        "24000",
        "-c:a",
        codec,
        "-b:a",
        "64k",
        `${base}.${extension}`,
      ]);
  }
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
