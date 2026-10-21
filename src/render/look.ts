/**
 * The moving parts of the 1930s look (Art Bible, section 4), as pure functions:
 * slow eye adaptation, and the vignette, grain and aberration that follow
 * Sora's fear and the player's settings. `Atmosphere` applies them each frame.
 */

/**
 * Simulated eye adjustment (Art Bible: "slow auto-exposure, 2–3 s adaptation").
 * Exposure moves in stops, so a doubling feels the same at any level. Eyes
 * recover from glare faster than they adjust to darkness.
 */
export class EyeAdaptation {
  exposure: number;

  constructor(
    initial: number,
    /** Seconds to cover 90% of the way when it gets darker (exposure rises). */
    private readonly toDarkSeconds = 2.5,
    /** Seconds to cover 90% of the way when it gets brighter. */
    private readonly toBrightSeconds = 0.8,
  ) {
    this.exposure = initial;
  }

  update(dt: number, target: number): number {
    const seconds = target > this.exposure ? this.toDarkSeconds : this.toBrightSeconds;
    // 90% of the way in `seconds`: e^(-seconds / tau) = 0.1.
    const k = 1 - Math.exp((-dt * Math.LN10) / seconds);
    const log = Math.log(this.exposure);
    this.exposure = Math.exp(log + (Math.log(target) - log) * k);
    return this.exposure;
  }
}

/**
 * Exposure the eye wants for a given amount of light reaching it (1 = Sora's
 * lamp, open, at arm's length). The eye only partly makes up for lost light:
 * with `strength` 0.25 it wins back a quarter of the stops (Spike S7: full
 * compensation made the hall brighter with the lamp out, so darkness felt
 * safe). Capped at `max` so the dark never becomes readable.
 */
export function targetExposure(light: number, base: number, max: number, strength = 0.25): number {
  const level = Math.max(light, 1e-4);
  return Math.min(max, Math.max(base * 0.6, base * Math.pow(1 / level, strength)));
}

export interface LookSettings {
  /** Settings toggles (Controls and Interface, section 9). */
  grain: boolean;
  aberration: boolean;
  /** Brightness calibration, in stops (-1 to 1). */
  brightness: number;
}

export interface Mood {
  /** 0 calm to 1 terrified (hidden, threat nearby, hurt). */
  fear: number;
  /** A scare's jolt, 1 at the moment of the scare and fading to 0. */
  scare: number;
  /** Memories and flashbacks: stronger grain. */
  memory: boolean;
}

export interface LookValues {
  vignetteWeight: number;
  grain: number;
  aberration: number;
}

/** Art Bible defaults: grain 8–12, vignette 1.5, aberration small and at the edges only. */
export const LOOK = {
  grain: 9,
  memoryGrain: 14,
  vignette: 1.5,
  fearVignette: 2.5,
  aberration: 8,
  scareAberration: 3,
};

export function lookValues(mood: Mood, settings: LookSettings): LookValues {
  const fear = Math.min(1, Math.max(0, mood.fear));
  const scare = Math.min(1, Math.max(0, mood.scare));
  return {
    vignetteWeight: LOOK.vignette + LOOK.fearVignette * fear,
    grain: settings.grain ? (mood.memory ? LOOK.memoryGrain : LOOK.grain) : 0,
    aberration: settings.aberration ? LOOK.aberration * (1 + LOOK.scareAberration * scare) : 0,
  };
}

/** A scare's jolt fades quickly: about a quarter of a second. */
export function decayScare(scare: number, dt: number): number {
  return scare * Math.exp(-dt / 0.25);
}
