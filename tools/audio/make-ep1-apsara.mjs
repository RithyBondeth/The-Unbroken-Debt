#!/usr/bin/env node
// The music of Episode 1's dancer ghost (November 2026), cut and warped from the
// Apsara dance recording the user supplied (art-source/audio/ep1/apsara_dance_source.mp3,
// 14 min 19 s; rights to be confirmed before release).
//
// - mus_ep1_apsara_ghost: 4 s from a full passage (02:36), played close and as
//   recorded while she dances in the back room; only its last moment runs down to a stop
//   as the house's lights go out (DancerGhost.ts).
// - mus_ep1_apsara_lure: a 24 s loop (12:00), as if through the back room's wall,
//   until she is seen.
//
// Usage: node tools/audio/make-ep1-apsara.mjs   (needs ffmpeg with libopus)
// Writes public/assets/ep1/audio/<name>.ogg (Opus) and .m4a (AAC), mono, 48 kHz.

import { execFileSync } from "node:child_process";
import { join } from "node:path";

const SRC = join("art-source", "audio", "ep1", "apsara_dance_source.mp3");
const OUT = join("public", "assets", "ep1", "audio");
const RATE = 48000;

/** Mono float samples of `seconds` of the source from `start`. */
function decode(start, seconds) {
  const raw = execFileSync(
    "ffmpeg",
    ["-v", "error", "-ss", String(start), "-t", String(seconds), "-i", SRC].concat([
      "-ac",
      "1",
      "-ar",
      String(RATE),
      "-f",
      "f32le",
      "-",
    ]),
    { maxBuffer: 1 << 28 },
  );
  return new Float32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4);
}

/** Reads `src` at a speed that changes over time: `speed(t)` (1 = as recorded). */
function vary(src, seconds, speed) {
  const out = new Float32Array(Math.round(seconds * RATE));
  let pos = 0;
  for (let i = 0; i < out.length; i++) {
    const a = Math.floor(pos);
    if (a + 1 >= src.length) break;
    out[i] = src[a] + (src[a + 1] - src[a]) * (pos - a);
    pos += speed(i / RATE);
  }
  return out;
}

/** Encodes `samples` with an ffmpeg filter chain to .ogg and .m4a. */
function encode(name, samples, filters) {
  const input = Buffer.from(samples.buffer, samples.byteOffset, samples.byteLength);
  const common = ["-v", "error", "-y", "-f", "f32le", "-ar", String(RATE), "-ac", "1", "-i", "-"];
  execFileSync(
    "ffmpeg",
    [...common, "-af", filters, "-c:a", "libopus", "-b:a", "96k", join(OUT, `${name}.ogg`)],
    {
      input,
    },
  );
  execFileSync(
    "ffmpeg",
    [...common, "-af", filters, "-c:a", "aac", "-b:a", "112k", join(OUT, `${name}.m4a`)],
    {
      input,
    },
  );
  console.log(`${name}: ${(samples.length / RATE).toFixed(2)} s`);
}

// A hard little room: echoes off near walls.
const ROOM = "aecho=0.8:0.6:37|71|113|167:0.4|0.32|0.24|0.16";

// ---- The dance, as she is seen: the recording as it is, close, with a short echo; only
// the last moment runs down to a stop, as the lights go.
{
  const length = 4.0;
  const stop = 0.6;
  const src = decode(156, 5);
  const out = vary(src, length, (t) => {
    const left = length - t;
    return left < stop ? Math.max(0.03, (left / stop) ** 1.4) : 1;
  });
  encode(
    "mus_ep1_apsara_ghost",
    out,
    `highpass=f=60,aecho=0.85:0.5:41|83:0.25|0.15,afade=t=in:d=0.02,afade=t=out:st=${length - 0.1}:d=0.1,loudnorm=I=-14:TP=-1:LRA=11,aresample=48000`,
  );
}

// ---- The same music through the back room's wall, before she is seen.
{
  const length = 24;
  const src = decode(720, 30);
  const out = vary(
    src,
    length + 0.6,
    (t) =>
      0.9 * (1 + 0.012 * Math.sin(2 * Math.PI * 0.3 * t) + 0.005 * Math.sin(2 * Math.PI * 2.1 * t)),
  );
  // Loop: the tail crossfaded over the head.
  const fade = Math.round(0.6 * RATE);
  const loop = out.slice(0, out.length - fade);
  for (let i = 0; i < fade; i++) {
    const k = i / fade;
    loop[i] = loop[i] * Math.sqrt(k) + out[out.length - fade + i] * Math.sqrt(1 - k);
  }
  encode(
    "mus_ep1_apsara_lure",
    loop,
    `highpass=f=120,lowpass=f=1600,${ROOM},loudnorm=I=-20:TP=-2:LRA=7,aresample=48000`,
  );
}
