/** Local recording import: node tools/audio/import-sok-voice.mjs km-KH part1.wav ... part4.wav */
import { execFileSync } from "node:child_process";
import { mkdtempSync, renameSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { format, resolveConfig } from "prettier";

const args = process.argv.slice(2);
if (args[0] === "--help") {
  console.log(
    "Usage: node tools/audio/import-sok-voice.mjs km-KH part1.wav part2.wav part3.wav part4.wav\nImports four local recordings, applies the gramophone filter, and switches the voice manifest. Subtitles are unchanged.",
  );
  process.exit(0);
}
const [language, ...files] = args;
if (!/^[a-z]{2,3}(?:-[A-Z]{2})?$/.test(language ?? "") || files.length !== 4)
  throw new Error("Supply a language such as km-KH and exactly four recordings. See --help.");
for (const file of files) if (!statSync(file).isFile()) throw new Error(`Not a recording: ${file}`);
const staging = mkdtempSync(join(tmpdir(), "sok-local-voice-"));
const manifest = { language, paragraphs: [] };
try {
  for (const [i, file] of files.entries()) {
    const duration = Number(
      execFileSync(
        "ffprobe",
        [
          "-v",
          "error",
          "-show_entries",
          "format=duration",
          "-of",
          "default=noprint_wrappers=1:nokey=1",
          resolve(file),
        ],
        { encoding: "utf8" },
      ),
    );
    if (!Number.isFinite(duration) || duration < 0.5 || duration > 120)
      throw new Error(`Paragraph ${i + 1} must be 0.5–120 seconds long.`);
    const base = `vo_sok_${language.replaceAll("-", "_")}_${i + 1}`;
    const paths = [];
    for (const [extension, codec] of [
      ["ogg", "libopus"],
      ["m4a", "aac"],
    ]) {
      const name = `${base}.${extension}`;
      execFileSync("ffmpeg", [
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        resolve(file),
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
        join(staging, name),
      ]);
      paths.push(`assets/ep1/audio/${name}`);
    }
    manifest.paragraphs.push(paths);
  }
  for (const paths of manifest.paragraphs)
    for (const path of paths) renameSync(join(staging, path.split("/").at(-1)), `public/${path}`);
  const target = "src/episodes/ep1/data/sokVoice.json";
  writeFileSync(
    target,
    await format(JSON.stringify(manifest), { ...(await resolveConfig(target)), parser: "json" }),
  );
  console.log(`Imported ${language} voice. English subtitles remain available.`);
} finally {
  rmSync(staging, { recursive: true, force: true });
}
