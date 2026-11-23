import {
  biquad,
  brown,
  bubble,
  formant,
  mix,
  modal,
  mudSuction,
  noise,
  normalise,
  softClip,
  stickSlip,
  sweep,
  wetStep,
  wrapLoop,
} from "@/audio/synth";

/**
 * Physically modelled horror & storm sound synthesis for Episode 1's 1933 Citroën
 * Rosalie night drive (Audio Design Document, section 9). Every cue is organic,
 * wordless, and bounded at any sample rate; no sacred chants or temple bells are
 * ever used as scares. Stereo is [left, right].
 */

export type Stereo = [Float32Array, Float32Array];

const cap = (f: number, rate: number) => Math.min(f, rate * 0.42);

/** Random impulses at `perSecond`, sizes skewed small, signs random. */
function crackles(n: number, rate: number, random: () => number, perSecond: number) {
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++)
    if (random() < perSecond / rate) out[i] = (random() < 0.5 ? -1 : 1) * random() ** 3;
  return out;
}

/**
 * The dash radio left on between stations, an 8 s loop: band-limited hiss, the
 * storm's static crackling in it, a heterodyne whistle drifting, and under it all
 * something like a far voice that never makes a word. The soundscape rides it up
 * when something is near.
 */
export function radioStatic(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 8.4),
    out = new Float32Array(n);
  const hiss = biquad(noise(n, random), rate, "bandpass", cap(2400, rate), 0.6);
  const crackle = modal(crackles(n, rate, random, 28), rate, [
    [cap(1900, rate), 0.0015, 1],
    [cap(3100, rate), 0.0008, 0.6],
  ]);
  const voice = formant(noise(n, random), rate, [
    [cap(620, rate), 90, 1],
    [cap(1180, rate), 140, 0.7],
    [cap(2450, rate), 220, 0.3],
  ]);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    phase += (880 + 260 * Math.sin((2 * Math.PI * t) / 8.4)) / rate;
    const whistle = Math.sin(2 * Math.PI * phase) * (0.5 + 0.5 * Math.sin((2 * Math.PI * t) / 4.2));
    const murmur = Math.max(0, Math.sin((2 * Math.PI * t) / 2.8 + 1)) ** 2;
    out[i] = hiss[i] * 0.5 + crackle[i] * 0.9 + whistle * 0.025 + voice[i] * 0.22 * murmur;
  }
  biquad(out, rate, "highpass", 300, 0.7);
  biquad(out, rate, "lowpass", cap(3200, rate), 0.7);
  return normalise(wrapLoop(out, rate, 0.4), 0.6);
}

/** Equal-power gains for a pan position from -1 (left) to 1 (right). */
function pan(position: number): [number, number] {
  const a = ((Math.max(-1, Math.min(1, position)) + 1) * Math.PI) / 4;
  return [Math.cos(a), Math.sin(a)];
}

/**
 * Something sprinting past at inhuman speed, 1.6 s with its nearest point at 0.6 s:
 * a violent tearing air-shear sweep, Doppler-bending hollow breath/howl, and frantic
 * bare feet slapping flooded mud 13 times a second across the headlights. Panned from `from` to `to`.
 */
export function ghostRush(rate: number, random: () => number, from = -1, to = 1): Stereo {
  const n = Math.round(rate * 1.6),
    closest = 0.6;
  const air = sweep(
    noise(n, random),
    rate,
    "bandpass",
    (t) => cap(420 + 2900 * Math.exp(-(((t - closest) / 0.14) ** 2)), rate),
    1.5,
  );
  const sub = biquad(brown(n, random, 0.99), rate, "lowpass", 140, 0.8);
  const mono = new Float32Array(n);
  let phase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      near = Math.exp(-(((t - closest) / 0.19) ** 2));
    phase += (470 * (1 + 0.28 * Math.tanh((closest - t) / 0.06))) / rate;
    const howl = Math.sin(2 * Math.PI * phase) * (0.55 + 0.45 * random());
    mono[i] = air[i] * near * 1.45 + sub[i] * near * 1.2 + howl * near * 0.12;
  }
  for (let t = 0.18; t < 1.06; t += 0.072 + random() * 0.015) {
    const step = wetStep(rate, random),
      at = Math.round(t * rate),
      gain = 0.62 * Math.exp(-(((t - closest) / 0.28) ** 2));
    for (let j = 0; j < step.length && at + j < n; j++) mono[at + j] += step[j] * gain;
  }
  const left = new Float32Array(n),
    right = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      p = Math.max(0, Math.min(1, (t - 0.24) / 0.68)),
      [l, r] = pan(from + (to - from) * p * p * (3 - 2 * p));
    left[i] = mono[i] * l;
    right[i] = mono[i] * r;
  }
  const peak = Math.max(
    ...[left, right].map((c) => c.reduce((m, v) => Math.max(m, Math.abs(v)), 0)),
  );
  for (const c of [left, right]) for (let i = 0; i < n; i++) c[i] *= 0.92 / (peak || 1);
  return [left, right];
}

/**
 * Ferocious bare-footed sprint through flooded mud ruts, 1.35 s, accelerating from
 * 11 to 15 steps/second as it hurtles straight onto Sora's side glass: violent wet
 * slaps, thick mud suction, splash spray, and jagged ragged panting overhead.
 */
export function mudSprint(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.35),
    out = new Float32Array(n);
  let t = 0.015;
  while (t < 1.18) {
    const progress = t / 1.18;
    const at = Math.round(t * rate),
      slap = wetStep(rate, random),
      suck = mudSuction(rate, random),
      gain = 0.65 + 0.45 * progress;
    for (let j = 0; j < slap.length && at + j < n; j++) out[at + j] += slap[j] * gain;
    const later = at + Math.round(0.032 * rate);
    for (let j = 0; j < suck.length && later + j < n; j++) out[later + j] += suck[j] * 0.3 * gain;
    // Accelerating stride cadence as it closes on the car door!
    t += 0.092 - 0.026 * progress + random() * 0.012;
  }
  const breath = formant(noise(n, random), rate, [
    [cap(540, rate), 150, 1],
    [cap(1620, rate), 240, 0.65],
    [cap(2950, rate), 420, 0.35],
  ]);
  for (let i = 0; i < n; i++) {
    const s = i / rate;
    const env = 0.35 + 0.65 * Math.min(1, s / 1.1);
    out[i] += breath[i] * 0.42 * env * Math.max(0, Math.sin(s * Math.PI * 2 * 3.8)) ** 2.4;
  }
  return normalise(out, 0.9);
}

/**
 * Visceral palm & body slam against Sora's side glass from outside:
 * 1) 62 Hz cabin air-pressure thud (door panel flexing inward),
 * 2) laminated glass impact ring + loose 1930s steel frame rattle,
 * 3) chilling wet palm & fingernail-on-wet-glass drag squeal sliding down the pane!
 */
export function windowSlap(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.35),
    hit = new Float32Array(n);
  const onset = Math.round(0.008 * rate);
  hit[onset] = 1;
  hit[onset + 2] = -0.6;
  // Cabin pressure thump + heavy door cavity resonance
  const pressure = modal(hit, rate, [
    [62, 0.11, 1.4],
    [104, 0.07, 0.95],
    [186, 0.045, 0.65],
    [340, 0.022, 0.4],
  ]);
  // Laminated glass plate modes
  const ring = modal(hit, rate, [
    [cap(1180, rate), 0.095, 0.3],
    [cap(2410, rate), 0.055, 0.18],
    [cap(3650, rate), 0.032, 0.11],
  ]);
  // Loose vintage door-frame metallic rattle
  const rattle = modal(
    stickSlip(
      n,
      rate,
      random,
      () => 38,
      (t) => (t < 0.36 ? Math.exp(-t * 8.5) : 0),
      0.35,
    ),
    rate,
    [
      [cap(420, rate), 0.009, 0.7],
      [cap(780, rate), 0.006, 1],
    ],
  );
  // Wet palm & fingernail dragging across soaked glass
  const drag = modal(
    stickSlip(
      n,
      rate,
      random,
      (t) => 310 + 680 * Math.max(0, t - 0.24),
      (t) => (t > 0.24 && t < 0.96 ? Math.sin(((t - 0.24) / 0.72) * Math.PI) ** 0.85 : 0),
      0.22,
    ),
    rate,
    [
      [cap(1950, rate), 0.004, 1],
      [cap(3100, rate), 0.0025, 0.65],
    ],
  );
  // Wet flesh splash transient at impact
  const slapBurst = biquad(
    noise(Math.round(0.045 * rate), random),
    rate,
    "bandpass",
    cap(2200, rate),
    0.9,
  );
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++)
    out[i] = pressure[i] * 1.25 + ring[i] + rattle[i] * 0.28 + drag[i] * 0.22;
  mix(out, slapBurst, rate, 0.006, 0.65, (t) => Math.exp(-t / 0.01));
  return normalise(softClip(out, 1.35), 0.94);
}

/**
 * The driver's breath caught short: a sharp inhale through the teeth, held, then
 * let out unsteadily, shaking.
 */
export function driverGasp(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.9),
    out = new Float32Array(n);
  const inhale = formant(noise(n, random), rate, [
    [380, 180, 0.6],
    [cap(2100, rate), 380, 1],
    [cap(3000, rate), 520, 0.6],
  ]);
  const exhale = formant(noise(n, random), rate, [
    [560, 200, 1],
    [cap(1250, rate), 260, 0.6],
  ]);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const drawIn = t < 0.32 ? (1 - Math.exp(-t / 0.02)) * Math.exp(-(((t - 0.18) / 0.14) ** 2)) : 0;
    const letGo =
      t > 0.95
        ? Math.sin(Math.min(1, (t - 0.95) / 0.85) * Math.PI) *
          (0.65 + 0.35 * Math.sin(t * 2 * Math.PI * 8.5))
        : 0;
    out[i] = inhale[i] * drawIn * 1.4 + exhale[i] * letGo * 0.6;
  }
  return normalise(out, 0.85);
}

/**
 * Emergency lockup on flooded laterite: hydroplaning mud & fender spray, 1930s wet
 * drum-brake metallic squeal, and the Rosalie's leaf springs dipping hard.
 */
export function brakeSlither(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.35),
    out = new Float32Array(n);
  const mud = sweep(
    noise(n, random),
    rate,
    "bandpass",
    (t) => cap(1250 - 700 * Math.min(1, t / 0.85), rate),
    1.1,
  );
  const spray = biquad(noise(n, random), rate, "highpass", cap(3000, rate), 0.7);
  // Wet 1930s steel drum brake squeal bending downward as wheels lock
  const squeal = modal(
    stickSlip(
      n,
      rate,
      random,
      (t) => 1450 - 520 * Math.min(1, t / 0.75),
      (t) => (t > 0.04 && t < 0.72 ? Math.sin(((t - 0.04) / 0.68) * Math.PI) : 0),
      0.14,
    ),
    rate,
    [
      [cap(1620, rate), 0.012, 0.6],
      [cap(2840, rate), 0.008, 0.35],
    ],
  );
  const dip = new Float32Array(n);
  dip[Math.round(0.04 * rate)] = 1;
  const body = modal(dip, rate, [
    [54, 0.14, 1.2],
    [108, 0.075, 0.55],
    [195, 0.04, 0.25],
  ]);
  for (let i = 0; i < n; i++) {
    const t = i / rate,
      env = (1 - Math.exp(-t / 0.025)) * Math.exp(-t / 0.48);
    out[i] = mud[i] * env * 1.15 + spray[i] * env * 0.4 + squeal[i] * 0.2 + body[i] * 0.95;
  }
  return normalise(out, 0.88);
}

/**
 * Physically modelled chest-cavity heartbeat ("lub-dub"), 1.0 s exact seamless cycle
 * (60 BPM base — modulated dynamically via StaticSound.playbackRate from 0.9x up to 1.8x
 * racing panic inside pre-scare silence vacuums!).
 */
export function anxiousHeartbeat(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.0),
    out = new Float32Array(n);
  const pulse = (atSec: number, fStart: number, fEnd: number, decaySec: number, amp: number) => {
    const start = Math.round(atSec * rate);
    const len = Math.round(decaySec * 5 * rate);
    let phase = 0;
    for (let j = 0; j < len && start + j < n; j++) {
      const t = j / rate;
      const f = fEnd + (fStart - fEnd) * Math.exp(-t / 0.025);
      phase += f / rate;
      const env = (1 - Math.exp(-t / 0.008)) * Math.exp(-t / decaySec);
      out[start + j] +=
        (Math.sin(2 * Math.PI * phase) + 0.32 * Math.sin(4 * Math.PI * phase)) * env * amp;
    }
  };
  // S1 ("lub"): heavy low mitral/tricuspid closure
  pulse(0.06, 64, 36, 0.068, 1.0);
  // S2 ("dub"): tighter higher aortic/pulmonary snap
  pulse(0.31, 82, 48, 0.048, 0.72);
  // Subtle muffled arterial blood rush beneath each beat
  const rush = biquad(brown(n, random, 0.985), rate, "lowpass", 150, 0.7);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const whoosh = Math.exp(-(((t - 0.18) / 0.14) ** 2)) * 0.26;
    out[i] += rush[i] * whoosh;
  }
  biquad(out, rate, "lowpass", 220, 0.65);
  return normalise(out, 0.88);
}

/**
 * Infrasonic psychological anxiety drone (8.0 s seamless loop): detuned 36.5 / 38.2 Hz
 * sub-harmonics beating slowly in the chest + ghostly bowed rusted-wire overtones that
 * creep into every silence vacuum before a haunt strikes.
 */
export function subTensionDrone(rate: number, random: () => number): Float32Array {
  const duration = 8.4,
    n = Math.round(rate * duration),
    out = new Float32Array(n);
  const air = sweep(
    noise(n, random),
    rate,
    "bandpass",
    (t) => cap(340 + 180 * Math.sin((2 * Math.PI * t) / 8.0), rate),
    5.5,
  );
  const wire = formant(noise(n, random), rate, [
    [cap(296, rate), 24, 0.7],
    [cap(443, rate), 32, 0.5],
    [cap(624, rate), 48, 0.3],
  ]);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const subA = Math.sin(2 * Math.PI * 36.5 * t);
    const subB = Math.sin(2 * Math.PI * 38.2 * t);
    const fifth =
      Math.sin(2 * Math.PI * 55.0 * t) * (0.45 + 0.35 * Math.sin(2 * Math.PI * 0.375 * t));
    const swell = 0.55 + 0.45 * Math.sin(2 * Math.PI * 0.25 * t + 0.8);
    out[i] = subA * 0.55 + subB * 0.5 + fifth * 0.32 + (air[i] * 0.22 + wire[i] * 0.32) * swell;
  }
  biquad(out, rate, "lowpass", cap(950, rate), 0.7);
  return normalise(wrapLoop(out, rate, 0.4), 0.72);
}

/**
 * Ultra-close binaural breath & wordless raspy whisper right behind Sora's right ear
 * (Beat 3 rear-view mirror snap-lunge): moist throat inhale → sudden icy, trembling
 * ragged exhale with faint wet vocal-fry clicks. Completely wordless and organic.
 */
export function neckBreathWhisper(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.15),
    out = new Float32Array(n);
  const src = noise(n, random);
  const hiss = formant(src, rate, [
    [cap(480, rate), 120, 0.85],
    [cap(1180, rate), 210, 0.9],
    [cap(2650, rate), 360, 0.85],
    [cap(4100, rate), 620, 0.55],
  ]);
  // Wet vocal-fry tremor under the close exhale
  const fry = formant(
    stickSlip(
      n,
      rate,
      random,
      (t) => 38 + 16 * Math.sin(t * 9),
      (t) => (t > 0.22 && t < 1.05 ? Math.sin(((t - 0.22) / 0.83) * Math.PI) : 0),
      0.48,
    ),
    rate,
    [
      [cap(420, rate), 110, 1],
      [cap(980, rate), 190, 0.65],
    ],
  );
  // Subtle moist throat crackles right against the ear
  const wetClicks = modal(crackles(n, rate, random, 48), rate, [
    [cap(860, rate), 0.004, 0.8],
    [cap(1850, rate), 0.0025, 0.5],
  ]);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    // Quick cold intake 0.0..0.18 s, explosive close exhale 0.18..1.12 s
    const inEnv = t < 0.18 ? Math.sin((t / 0.18) * Math.PI) * 0.42 : 0;
    const outEnv =
      t >= 0.18
        ? (1 - Math.exp(-(t - 0.18) / 0.025)) *
          Math.exp(-(t - 0.18) / 0.34) *
          (0.82 + 0.18 * Math.sin(t * 28))
        : 0;
    out[i] = hiss[i] * (inEnv + outEnv * 1.35) + fry[i] * 1.1 + wetClicks[i] * outEnv * 0.45;
  }
  biquad(out, rate, "highpass", 180, 0.7);
  return normalise(out, 0.9);
}

/**
 * Cinema-grade organic horror sting (1.45 s):
 * 1) 46 → 28 Hz sub-bass chest drop,
 * 2) waterphone / bowed rusted-iron inharmonic shriek,
 * 3) hollow inhuman breathy gasp-shriek via shifting throat formants.
 * Zero cheesy synth beeps; raw, chilling, and punchy.
 */
export function ghostScreechSting(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 1.45),
    out = new Float32Array(n);
  // 1) Sub-bass adrenaline chest drop
  let subPhase = 0;
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const f = 28 + 20 * Math.exp(-t / 0.18);
    subPhase += f / rate;
    const env = (1 - Math.exp(-t / 0.006)) * Math.exp(-t / 0.42);
    out[i] += Math.sin(2 * Math.PI * subPhase) * env * 1.15;
  }
  // 2) Bowed rusted-iron / waterphone inharmonic metal shriek
  const bow = stickSlip(
    n,
    rate,
    random,
    (t) => 110 + 180 * Math.exp(-t / 0.35),
    (t) => (1 - Math.exp(-t / 0.015)) * Math.exp(-t / 0.48),
    0.26,
  );
  const metal = modal(bow, rate, [
    [cap(685, rate), 0.24, 0.9],
    [cap(1142, rate), 0.2, 0.85],
    [cap(1796, rate), 0.15, 0.7],
    [cap(2680, rate), 0.1, 0.48],
  ]);
  // 3) Hollow inhuman breathy gasp-shriek (glottal friction + sweeping vocal cavity)
  const rawBreath = noise(n, random);
  const shriekBand = sweep(
    rawBreath,
    rate,
    "bandpass",
    (t) => cap(720 + 1480 * Math.exp(-t / 0.16) + 220 * Math.sin(t * 26), rate),
    3.6,
  );
  const throat = formant(softClip(shriekBand.slice(), 2.2), rate, [
    [cap(620, rate), 140, 0.9],
    [cap(1520, rate), 240, 1.0],
    [cap(2780, rate), 380, 0.65],
  ]);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const voiceEnv = (1 - Math.exp(-t / 0.012)) * Math.exp(-t / 0.36);
    out[i] += metal[i] * 0.62 + throat[i] * voiceEnv * 1.25;
  }
  return normalise(softClip(out, 1.25), 0.94);
}

/**
 * 1930s 6-volt automotive relay chatter & tungsten filament sputter (0.55 s):
 * sharp mechanical clicks, 100/200 Hz coil hum, and crackling arc sparks inside the dash
 * whenever the headlights & valve radio short out right before a haunt!
 */
export function electricalArcZap(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 0.55),
    out = new Float32Array(n);
  const sparks = crackles(n, rate, random, 140);
  // 3 distinct mechanical relay clacks as voltage collapses
  for (const atSec of [0.02, 0.14, 0.29]) {
    const idx = Math.round(atSec * rate);
    if (idx < n) sparks[idx] = 2.2;
  }
  const clickRing = modal(sparks, rate, [
    [cap(1650, rate), 0.004, 1.0],
    [cap(3100, rate), 0.0025, 0.85],
    [cap(4400, rate), 0.0015, 0.6],
  ]);
  const arcNoise = biquad(noise(n, random), rate, "highpass", cap(2400, rate), 0.7);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const gate =
      Math.exp(-(((t - 0.05) / 0.04) ** 2)) +
      Math.exp(-(((t - 0.18) / 0.05) ** 2)) * 0.85 +
      Math.exp(-(((t - 0.34) / 0.07) ** 2)) * 0.7;
    const buzz = (Math.sin(2 * Math.PI * 100 * t) + 0.6 * Math.sin(2 * Math.PI * 200 * t)) * 0.25;
    out[i] = clickRing[i] * 0.9 + (arcNoise[i] * 0.55 + buzz) * gate;
  }
  return normalise(out, 0.82);
}

/**
 * Sharp wet-wood branch crack right off the jungle verge (0.45 s) — snaps when Beat 1's
 * verge watcher lurches 2.1 m closer in the lightning blink!
 */
export function branchSnap(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 0.45),
    imp = new Float32Array(n);
  for (const [atSec, amp] of [
    [0.005, 1.0],
    [0.018, -0.75],
    [0.042, 0.55],
    [0.078, -0.32],
  ] as const) {
    const idx = Math.round(atSec * rate);
    if (idx < n) imp[idx] = amp;
  }
  const snap = modal(imp, rate, [
    [cap(740, rate), 0.016, 0.9],
    [cap(1480, rate), 0.012, 1.0],
    [cap(2650, rate), 0.007, 0.8],
    [cap(3900, rate), 0.004, 0.5],
  ]);
  const rustle = biquad(noise(n, random), rate, "bandpass", cap(1800, rate), 0.8);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    out[i] = snap[i] * 1.1 + rustle[i] * 0.35 * Math.exp(-t / 0.12);
  }
  return normalise(out, 0.88);
}

/**
 * Inside a 1933 steel-roofed sedan driving through a Cambodian monsoon (8.6 s seamless loop):
 * heavy fat raindrops drumming directly onto the tin roof & bonnet, gale wind whistling
 * softly through old rubber door seals, and flooded sheet-water splashing in the wheel arches.
 */
export function cabinStormBed(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 9.0),
    out = new Float32Array(n);
  // Dense fat droplets hammering thin painted steel roof panels
  const drops = crackles(n, rate, random, 190);
  const tinRoof = modal(drops, rate, [
    [cap(310, rate), 0.012, 0.7],
    [cap(580, rate), 0.008, 0.95],
    [cap(1040, rate), 0.005, 0.75],
    [cap(2150, rate), 0.003, 0.45],
  ]);
  // Sheet-water spray rushing through front mudguards / flooded ruts
  const spray = biquad(noise(n, random), rate, "bandpass", cap(1250, rate), 0.65);
  // Low cabin resonance from heavy downpour outside
  const cabinRumble = biquad(brown(n, random, 0.992), rate, "lowpass", 180, 0.7);
  // Subtle eerie gale whistling through aged door seals
  const sealWhistle = sweep(
    noise(n, random),
    rate,
    "bandpass",
    (t) => cap(640 + 260 * Math.sin((2 * Math.PI * t) / 4.3 + 0.5), rate),
    7.5,
  );
  // Occasional heavier puddle splash drops under the floorboard
  for (let k = 0; k < 24; k++) {
    const drop = bubble(rate, cap(750 + random() * 1400, rate), 0.006 + random() * 0.006, 0.75);
    mix(out, drop, rate, random() * 8.4, 0.08 + random() * 0.08, () => 1);
  }
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const surge = 0.78 + 0.22 * Math.sin((2 * Math.PI * t) / 3.0);
    const gust = Math.max(0, Math.sin((2 * Math.PI * t) / 4.3)) ** 2;
    out[i] +=
      tinRoof[i] * 0.82 * surge +
      spray[i] * 0.26 * surge +
      cabinRumble[i] * 0.45 +
      sealWhistle[i] * 0.22 * gust;
  }
  biquad(out, rate, "lowpass", cap(3600, rate), 0.7);
  return normalise(wrapLoop(out, rate, 0.4), 0.75);
}

/**
 * Close-range monsoon lightning strike (3.8 s): starts with an explosive supersonic
 * air-tear whip-crack that immediately detonates into chest-shaking sub-bass thunder
 * echoing across the flooded jungle canopy!
 */
export function thunderCrack(rate: number, random: () => number): Float32Array {
  const n = Math.round(rate * 3.8),
    out = new Float32Array(n);
  // 1) Initial lightning air-tear whip-crack (0.0..0.18 s)
  const snapSrc = noise(Math.round(0.24 * rate), random);
  const crackHigh = biquad(snapSrc.slice(), rate, "bandpass", cap(2200, rate), 0.75);
  const crackMid = biquad(snapSrc.slice(), rate, "bandpass", cap(680, rate), 0.9);
  mix(out, crackHigh, rate, 0.002, 1.3, (t) => Math.exp(-t / 0.028));
  mix(out, crackMid, rate, 0.004, 1.1, (t) => Math.exp(-t / 0.055));
  // Secondary forked crackle at 0.07 s
  const fork = biquad(
    noise(Math.round(0.12 * rate), random),
    rate,
    "highpass",
    cap(1400, rate),
    0.7,
  );
  mix(out, fork, rate, 0.068, 0.75, (t) => Math.exp(-t / 0.022));
  // 2) Massive rolling sub-bass detonation + canopy reflections
  const subBoom = biquad(brown(n, random, 0.996), rate, "lowpass", 130, 0.75);
  const midRoll = biquad(brown(n, random, 0.985), rate, "bandpass", 260, 0.7);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    const attack = 1 - Math.exp(-t / 0.018);
    // Primary blast + two echoing cloud reflections at 0.65 s and 1.45 s
    const roll =
      Math.exp(-t / 1.05) +
      0.42 * Math.exp(-(((t - 0.65) / 0.34) ** 2)) +
      0.26 * Math.exp(-(((t - 1.48) / 0.55) ** 2));
    out[i] += subBoom[i] * attack * roll * 2.4 + midRoll[i] * attack * Math.exp(-t / 0.75) * 0.9;
  }
  return normalise(softClip(out, 1.4), 0.94);
}
