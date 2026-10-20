import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { AudioSystem } from "../../audio/AudioSystem";
import { rms, seededRandom, wetStep } from "../../audio/synth";
import type { Panning } from "../../audio/localization";

export interface EarLevels {
  azimuth: number;
  distance: number;
  panning: Panning;
  left: number;
  right: number;
  /** Interaural level difference, right minus left, in dB. */
  ildDb: number;
  /** The same above 3 kHz, where the head's shadow is strongest. */
  ildHighDb: number;
  /** Interaural time difference: how much later the left ear hears it, ms (negative = right later). */
  itdMs: number;
}

const RATE = 48000;

/**
 * Renders one footstep through the real audio engine into an offline buffer,
 * with the listener at the origin facing +z (Babylon's forward), and measures
 * each ear. No one has to listen: a source on the right must come out louder
 * on the right. WebAudio is right-handed and Babylon left-handed, so this
 * catches a mirrored world.
 */
export async function renderEars(
  azimuth: number,
  distance: number,
  panning: Panning,
): Promise<EarLevels> {
  const context = new OfflineAudioContext(2, RATE * 0.6, RATE);
  const audio = await AudioSystem.create(context);
  const position = new Vector3(Math.sin(azimuth) * distance, 0, Math.cos(azimuth) * distance);
  const step = audio.buffer(wetStep(RATE, seededRandom(7)), RATE);
  const sound = await audio.spatialSound("probe", step, "threat", position, { panning });
  sound.play();
  const out = await context.startRendering();
  audio.engine.dispose();
  const l = out.getChannelData(0);
  const r = out.getChannelData(1);
  const left = rms(l);
  const right = rms(r);
  const highL = rms(highPass(l, 3000));
  const highR = rms(highPass(r, 3000));
  return {
    azimuth,
    distance,
    panning,
    left,
    right,
    ildDb: 20 * Math.log10((right + 1e-9) / (left + 1e-9)),
    ildHighDb: 20 * Math.log10((highR + 1e-9) / (highL + 1e-9)),
    itdMs: (lagOf(l, r, Math.round(RATE * 0.0012)) / RATE) * 1000,
  };
}

/** One-pole high-pass, for a rough look at the head-shadow band. */
function highPass(samples: Float32Array, cutoff: number): Float32Array {
  const a = 1 / (1 + (2 * Math.PI * cutoff) / RATE);
  const out = new Float32Array(samples.length);
  for (let i = 1; i < samples.length; i++) out[i] = a * (out[i - 1] + samples[i] - samples[i - 1]);
  return out;
}

/** Lag (samples) that best lines the left channel up with the right: positive = left is later. */
function lagOf(left: Float32Array, right: Float32Array, maxLag: number): number {
  let best = 0;
  let bestScore = -Infinity;
  for (let lag = -maxLag; lag <= maxLag; lag++) {
    let score = 0;
    for (let i = maxLag; i < left.length - maxLag; i++) score += right[i] * left[i + lag];
    if (score > bestScore) {
      bestScore = score;
      best = lag;
    }
  }
  return best;
}
