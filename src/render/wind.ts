import { seededRandom } from "../audio/synth";

/**
 * One wind for an outdoor scene: a direction that veers slowly, a strength
 * the story raises and lowers, and gusts that roll across the world as
 * fronts. The foliage shader (FoliageWind) and the wind's sound (WindAudio)
 * read this same state, so a gust is seen bending the trees upwind a moment
 * before it is heard arriving, and both fall still together when the night
 * holds its breath.
 */

/** How fast a gust front travels downwind (m/s). */
export const FRONT_SPEED = 11;
/** Fraction of a gust's passage spent rising; the rest is its long fall. */
export const GUST_RISE = 0.3;
/** Grass and hanging thread part round Sora within this radius (m). */
export const PUSH_RADIUS = 0.85;
/** Floats `pack` writes: main, two gusts and the push, four each. */
export const WIND_UNIFORMS = 16;

export interface Gust {
  /** Wind time (s) at which the front leaves `origin`. */
  start: number;
  /** Seconds the gust takes to pass any one point. */
  duration: number;
  /** Extra strength at the gust's height. */
  peak: number;
  /** Where the front starts, measured along the wind's heading (m). */
  origin: number;
}

const smooth = (x: number) => x * x * (3 - 2 * x);

/** A gust at one point over its passage `u` (0–1): a quick rise and a long fall. */
export function gustEnvelope(u: number): number {
  if (u <= 0 || u >= 1) return 0;
  return u < GUST_RISE ? smooth(u / GUST_RISE) : 1 - smooth((u - GUST_RISE) / (1 - GUST_RISE));
}

/**
 * Wave crests rolling downwind with the fronts: the slow breathing every
 * stand of trees shows between gusts. FoliageWind evaluates the same function.
 */
export function windRoll(along: number, across: number, time: number): number {
  return 0.5 + 0.5 * Math.sin(along * 0.12 - time * 1.3 + across * 0.05);
}

export class WindState {
  time = 0;
  /** What the scene sets: 0 still air, 0.5 a monsoon night, 1 a storm. */
  base = 0;
  /** 0–1: the story has hushed the night. The air stops and gusts die. */
  calm = 0;
  /** 0–1: dread rising. Gusts come more often and harder. */
  tension = 0;
  /** The strength drawn and heard: `base` eased through calm and tension. */
  strength = 0;
  /** Heading the wind blows towards (radians; 0 is +x, π/2 is +z). */
  heading: number;
  /** Two fronts at most: the foliage shader has two slots. */
  readonly gusts: Gust[] = [];
  /** Where Sora is, for grass and thread parting round her; null when no one stands in the scene. */
  readonly push: { x: number; z: number } | null;
  /** `pack`ed once per update, for every plant material's shader. */
  readonly uniforms = new Float32Array(WIND_UNIFORMS);
  /** Each new gust, and the seconds until its height reaches the listener. */
  onGust: ((gust: Gust, arrivesIn: number) => void) | null = null;
  private nextGust: number;
  private veer = 0;
  private veerTarget = 0;
  private nextVeer = 0;
  private listenerX = 0;
  private listenerZ = 0;

  constructor(
    private readonly random: () => number = seededRandom(7310),
    /** The monsoon's own direction, which the wind wanders either side of. */
    readonly prevailing = -2.25,
    push = true,
  ) {
    this.heading = prevailing;
    this.nextGust = 4 + random() * 4;
    this.push = push ? { x: 0, z: 0 } : null;
  }

  get dirX(): number {
    return Math.cos(this.heading);
  }

  get dirZ(): number {
    return Math.sin(this.heading);
  }

  /** Distance of a point along the heading. */
  along(x: number, z: number): number {
    return x * this.dirX + z * this.dirZ;
  }

  /** Advances the wind; `x`, `z` is the listener, whom gusts are aimed at. */
  update(dt: number, x: number, z: number): void {
    dt = Math.max(0, Math.min(dt, 0.25));
    this.time += dt;
    this.listenerX = x;
    this.listenerZ = z;
    const target = this.base * (1 - 0.92 * this.calm) * (1 + 0.3 * this.tension);
    // The air drops quickly when the night hushes, and returns slowly.
    const tau = target < this.strength ? 1.1 : 3.5;
    this.strength += (target - this.strength) * (1 - Math.exp(-dt / tau));

    this.nextVeer -= dt;
    if (this.nextVeer <= 0) {
      this.nextVeer = 6 + this.random() * 9;
      this.veerTarget = (this.random() - 0.5) * 0.7;
    }
    this.veer += (this.veerTarget - this.veer) * (1 - Math.exp(-dt / 6));
    this.heading = this.prevailing + this.veer;

    for (let i = this.gusts.length - 1; i >= 0; i--)
      if (this.finished(this.gusts[i])) this.gusts.splice(i, 1);
    this.nextGust -= dt;
    if (this.nextGust <= 0) {
      const interval = 14 - 9 * this.tension;
      this.nextGust = interval * (0.6 + 0.8 * this.random());
      // A hushed night has no gusts; neither has still air.
      if (this.calm < 0.4 && this.base > 0.05 && this.gusts.length < 2) {
        const peak =
          (0.35 + 0.45 * this.random()) * (0.6 + 0.6 * this.base) * (1 + 0.5 * this.tension);
        this.launch(peak, 3.5 + 4 * this.random(), 22 + 26 * this.random());
      }
    }
    this.pack(this.uniforms);
  }

  /**
   * A gust now, its front `lead` metres upwind of the listener: what a sting
   * or a reveal brings with it. It takes the oldest slot if both are full.
   */
  surge(peak: number, lead = 9, duration = 4): void {
    if (this.calm > 0.85) return;
    if (this.gusts.length >= 2) this.gusts.shift();
    this.launch(peak, duration, lead);
  }

  /** Gust strength at a point (calm included), at the current time. */
  gustAt(x: number, z: number): number {
    const along = this.along(x, z);
    let sum = 0;
    for (const g of this.gusts)
      sum +=
        g.peak *
        gustEnvelope((this.time - g.start - (along - g.origin) / FRONT_SPEED) / g.duration);
    return sum * (1 - this.calm);
  }

  /** How hard the wind is blowing at a point: what the trees there show. */
  at(x: number, z: number): number {
    const along = this.along(x, z);
    const across = -x * this.dirZ + z * this.dirX;
    return this.strength * (0.65 + 0.35 * windRoll(along, across, this.time)) + this.gustAt(x, z);
  }

  /** The shader's uniforms: [time, dirX, dirZ, strength], gust A, gust B, [pushX, pushZ, radius, on]. */
  pack(out: Float32Array): Float32Array {
    out[0] = this.time;
    out[1] = this.dirX;
    out[2] = this.dirZ;
    out[3] = this.strength;
    for (let k = 0; k < 2; k++) {
      const g = this.gusts[k];
      const o = 4 + k * 4;
      out[o] = g?.start ?? 0;
      out[o + 1] = g?.duration ?? 0;
      out[o + 2] = g ? g.peak * (1 - this.calm) : 0;
      out[o + 3] = g?.origin ?? 0;
    }
    out[12] = this.push?.x ?? 0;
    out[13] = this.push?.z ?? 0;
    out[14] = PUSH_RADIUS;
    out[15] = this.push ? 1 : 0;
    return out;
  }

  private launch(peak: number, duration: number, lead: number): void {
    const gust: Gust = {
      start: this.time,
      duration,
      peak,
      origin: this.along(this.listenerX, this.listenerZ) - lead,
    };
    this.gusts.push(gust);
    this.pack(this.uniforms);
    this.onGust?.(gust, lead / FRONT_SPEED + GUST_RISE * duration);
  }

  /** Past the listener and on into the fog downwind. */
  private finished(g: Gust): boolean {
    const reach = this.along(this.listenerX, this.listenerZ) + 60 - g.origin;
    return this.time > g.start + reach / FRONT_SPEED + g.duration;
  }
}
