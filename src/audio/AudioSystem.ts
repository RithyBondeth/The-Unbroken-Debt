import { CreateAudioEngineAsync } from "@babylonjs/core/AudioV2/webAudio/webAudioEngine";
import type { AudioEngineV2 } from "@babylonjs/core/AudioV2/abstractAudio/audioEngineV2";
import type { AudioBus } from "@babylonjs/core/AudioV2/abstractAudio/audioBus";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { StreamingSound } from "@babylonjs/core/AudioV2/abstractAudio/streamingSound";
import type { Node } from "@babylonjs/core/node";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { SPACES, impulseResponse, type AcousticSpace } from "./acoustics";
import { seededRandom } from "./synth";

/**
 * The mix buses (Technical Design Document, section 12; Audio Design Document,
 * section 2). "room" is the ambience of the space the listener is in (rain on
 * the roof overhead, drips through the boards): unlike "ambience", which is
 * the open air outside, walls do not muffle it.
 */
export type BusName = "ambience" | "room" | "sfx" | "threat" | "voice" | "music" | "ui";

/**
 * Threats use HRTF panning: the player must be able to place them by ear
 * alone ("sound tells the truth"). Minor effects use cheaper equal-power
 * panning. Ambience, music and UI are not positioned.
 */
export const PANNING: Record<BusName, "HRTF" | "equalpower" | null> = {
  threat: "HRTF",
  voice: "HRTF",
  sfx: "equalpower",
  ambience: null,
  room: null,
  music: null,
  ui: null,
};

export interface SpatialOptions {
  /** Overrides the bus's panning model (the S4 pointing test compares both). */
  panning?: "HRTF" | "equalpower";
  /** Full volume within this distance, in metres. */
  minDistance?: number;
  maxDistance?: number;
  loop?: boolean;
  volume?: number;
}

/** Buses sent into the space's reverb, and how much (UI, music and the room's own bed stay dry). */
const REVERB_SENDS: Partial<Record<BusName, number>> = {
  sfx: 1,
  threat: 1,
  voice: 0.8,
  ambience: 0.35,
};

/**
 * The master limiter: a fast compressor just under full scale with its automatic
 * make-up gain taken back off, so everything below the threshold passes at
 * exactly the level it had before (Episodes 1 and 3 sound as they did) and only
 * the stacked peaks of a scare are held down, to about -3 dBFS.
 */
export const LIMITER = { threshold: -4, knee: 0, ratio: 20, attack: 0.002, release: 0.12 };

/**
 * The gain, in dB, a DynamicsCompressorNode adds after compressing (Web Audio
 * API 1.1, "Computing the makeup gain"): the curve's output for a full-scale
 * input, inverted and raised to 0.6. Exact for a hard knee.
 */
export function compressorMakeupDb(threshold: number, ratio: number): number {
  const fullRange = threshold + (0 - threshold) / ratio;
  return -0.6 * fullRange;
}

/** The level, dBFS, the limiter lets out for an input `db` dBFS (make-up gain removed). */
export function limiterOutputDb(db: number, limiter = LIMITER): number {
  return db <= limiter.threshold
    ? db
    : limiter.threshold + (db - limiter.threshold) / limiter.ratio;
}

/** The Web Audio nodes behind `setSpace`: reverb sends and the walls' muffling of the outdoors. */
interface Acoustics {
  send: GainNode;
  out: AudioNode;
  occlusion: BiquadFilterNode;
  occlusionGain: GainNode;
}

/**
 * The game's audio: Babylon's Audio Engine v2 with the mix buses, a listener
 * on the camera and helpers for positioned sounds. Browsers start audio only
 * after a click or key press, so call `unlock` from one.
 */
export class AudioSystem {
  private space: AcousticSpace | null = null;
  private reverb: { convolver: ConvolverNode; gain: GainNode } | null = null;
  private readonly impulses = new Map<AcousticSpace, AudioBuffer>();

  private constructor(
    readonly engine: AudioEngineV2,
    readonly buses: Record<BusName, AudioBus>,
    readonly context: BaseAudioContext,
    private readonly acoustics: Acoustics | null,
    /** The last node before the speakers, after the master limiter (for meters). */
    readonly master: AudioNode | null = null,
  ) {}

  /**
   * @param audioContext an `OfflineAudioContext` renders silently to a buffer
   * (S4 uses it to check panning without anyone listening)
   */
  static async create(
    audioContext?: BaseAudioContext,
    { hideUnmuteButton = false } = {},
  ): Promise<AudioSystem> {
    const engine = await CreateAudioEngineAsync({
      ...(audioContext ? { audioContext: audioContext as AudioContext } : {}),
      listenerEnabled: true,
      // The game unlocks sound with its own "Press Enter to begin".
      disableDefaultUI: hideUnmuteButton,
    });
    const names: BusName[] = ["ambience", "room", "sfx", "threat", "voice", "music", "ui"];
    const buses = Object.fromEntries(
      await Promise.all(names.map(async (n) => [n, await engine.createBusAsync(n)] as const)),
    ) as Record<BusName, AudioBus>;
    const context = (engine as unknown as { _audioContext: BaseAudioContext })._audioContext;
    const master = AudioSystem.limit(engine, context);
    const acoustics = AudioSystem.wire(engine, buses, context);
    return new AudioSystem(engine, buses, context, acoustics, master);
  }

  /**
   * Puts the master limiter between Babylon's main output and the speakers. Left
   * out, and the mix runs as before, if the graph is not the plain Web Audio one.
   */
  private static limit(engine: AudioEngineV2, context: BaseAudioContext): AudioNode | null {
    const mainOut = (engine as unknown as { mainOut?: { _inNode?: AudioNode | null } }).mainOut;
    const out = mainOut?._inNode;
    if (!out || typeof context.createDynamicsCompressor !== "function") return null;
    try {
      const limiter = context.createDynamicsCompressor();
      limiter.threshold.value = LIMITER.threshold;
      limiter.knee.value = LIMITER.knee;
      limiter.ratio.value = LIMITER.ratio;
      limiter.attack.value = LIMITER.attack;
      limiter.release.value = LIMITER.release;
      const trim = context.createGain();
      trim.gain.value = 10 ** (-compressorMakeupDb(LIMITER.threshold, LIMITER.ratio) / 20);
      const destination =
        (engine as unknown as { _audioDestination?: AudioNode })._audioDestination ??
        context.destination;
      out.disconnect();
      out.connect(limiter).connect(trim).connect(destination);
      return trim;
    } catch (error) {
      console.warn("[AudioSystem] no master limiter", error);
      return null;
    }
  }

  /**
   * Adds the acoustics to Babylon's bus graph: the ambience bus is re-routed
   * through a low-pass (walls between the listener and the open air), and the
   * buses in REVERB_SENDS feed one reverb send. Null, and the mix stays dry,
   * if the graph is not the plain Web Audio one this expects.
   */
  private static wire(
    engine: AudioEngineV2,
    buses: Record<BusName, AudioBus>,
    context: BaseAudioContext,
  ): Acoustics | null {
    const node = (n: unknown) =>
      (n as { _inNode?: AudioNode | null; _outNode?: AudioNode | null }) ?? {};
    const out = node(engine.defaultMainBus)._inNode;
    const ambience = node(buses.ambience)._outNode;
    if (!out || !ambience) return null;
    try {
      const occlusion = context.createBiquadFilter();
      occlusion.type = "lowpass";
      occlusion.frequency.value = 20000;
      occlusion.Q.value = 0.5;
      const occlusionGain = context.createGain();
      ambience.disconnect(out);
      ambience.connect(occlusion).connect(occlusionGain).connect(out);
      const send = context.createGain();
      for (const [name, level] of Object.entries(REVERB_SENDS) as [BusName, number][]) {
        const tap = context.createGain();
        tap.gain.value = level;
        const from = name === "ambience" ? occlusionGain : node(buses[name])._outNode;
        from?.connect(tap).connect(send);
      }
      return { send, out, occlusion, occlusionGain };
    } catch (error) {
      console.warn("[AudioSystem] no acoustics", error);
      return null;
    }
  }

  /**
   * Moves the listener into `name`: its reverb fades in as the last one fades
   * out, and the walls close round (or open from) the outdoor ambience, over
   * `fade` seconds (the Audio Design Document crossfades zones over 2–3 s).
   */
  setSpace(name: AcousticSpace, fade = 2.5): void {
    const acoustics = this.acoustics;
    if (!acoustics || name === this.space) return;
    this.space = name;
    const space = SPACES[name];
    const context = this.context;
    const now = context.currentTime;
    const tau = Math.max(0.01, fade / 3);
    acoustics.occlusion.frequency.setTargetAtTime(space.occlusion[0], now, tau);
    acoustics.occlusionGain.gain.setTargetAtTime(space.occlusion[1], now, tau);
    let impulse = this.impulses.get(name);
    if (!impulse) {
      const rate = context.sampleRate;
      const [left, right] = impulseResponse(rate, seededRandom(name.length * 7919 + 3), space);
      impulse = context.createBuffer(2, left.length, rate);
      impulse.copyToChannel(left as Float32Array<ArrayBuffer>, 0);
      impulse.copyToChannel(right as Float32Array<ArrayBuffer>, 1);
      this.impulses.set(name, impulse);
    }
    const convolver = context.createConvolver();
    convolver.buffer = impulse;
    const gain = context.createGain();
    gain.gain.value = 0;
    acoustics.send.connect(convolver).connect(gain).connect(acoustics.out);
    gain.gain.setTargetAtTime(space.wet, now, tau);
    const old = this.reverb;
    this.reverb = { convolver, gain };
    if (old) {
      old.gain.gain.setTargetAtTime(0, now, tau);
      setTimeout(() => {
        acoustics.send.disconnect(old.convolver);
        old.gain.disconnect();
      }, fade * 2000);
    }
  }

  /** The space the listener is in, once `setSpace` has been called. */
  get currentSpace(): AcousticSpace | null {
    return this.space;
  }

  async unlock(): Promise<void> {
    await this.engine.unlockAsync();
  }

  /** The listener follows this node (the player's camera): position and turn. */
  attachListener(node: Node): void {
    this.engine.listener.attach(node);
  }

  /** Wraps mono samples (or one array per channel) in an audio buffer for this engine. */
  buffer(samples: Float32Array | Float32Array[], sampleRate: number): AudioBuffer {
    const channels = Array.isArray(samples) ? samples : [samples];
    const buffer = this.context.createBuffer(channels.length, channels[0].length, sampleRate);
    channels.forEach((c, i) => buffer.copyToChannel(c as Float32Array<ArrayBuffer>, i));
    return buffer;
  }

  /**
   * Fetches and decodes the first of `urls` this browser can play (Opus first,
   * AAC as the fallback). Null if none loads.
   */
  async load(urls: string[]): Promise<AudioBuffer | null> {
    for (const url of urls) {
      try {
        const response = await fetch(url);
        if (!response.ok) continue;
        return await this.context.decodeAudioData(await response.arrayBuffer());
      } catch {
        // Not playable here: try the next format.
      }
    }
    return null;
  }

  /** A sound heard from the listener's own position (Sora's feet, her hands). */
  async sound(name: string, buffer: AudioBuffer, bus: BusName, volume = 1): Promise<StaticSound> {
    return this.engine.createSoundAsync(name, buffer, { outBus: this.buses[bus], volume });
  }

  /** A sound placed in the world on `bus`, panned the way that bus requires. */
  async spatialSound(
    name: string,
    buffer: AudioBuffer,
    bus: BusName,
    position: Vector3,
    options: SpatialOptions = {},
  ): Promise<StaticSound> {
    return this.engine.createSoundAsync(name, buffer, this.spatialOptions(bus, position, options));
  }

  /**
   * Like `spatialSound`, but streamed from a file as it plays (long ambience and
   * music, Audio Design Document 10). `urls` lists the formats in order of
   * preference; the browser plays the first it supports.
   */
  async spatialStream(
    name: string,
    urls: string[],
    bus: BusName,
    position: Vector3,
    options: SpatialOptions = {},
  ): Promise<StreamingSound> {
    return this.engine.createStreamingSoundAsync(
      name,
      urls,
      this.spatialOptions(bus, position, options),
    );
  }

  /** A long bed streamed from a file and heard everywhere, not placed (Opus first, AAC after). */
  async stream(
    name: string,
    urls: string[],
    bus: BusName,
    { loop = true, volume = 1 }: { loop?: boolean; volume?: number } = {},
  ): Promise<StreamingSound> {
    return this.engine.createStreamingSoundAsync(name, urls, {
      outBus: this.buses[bus],
      loop,
      volume,
    });
  }

  private spatialOptions(bus: BusName, position: Vector3, options: SpatialOptions) {
    return {
      outBus: this.buses[bus],
      spatialEnabled: true,
      spatialPanningModel: options.panning ?? PANNING[bus] ?? "equalpower",
      spatialPosition: position.clone(),
      spatialDistanceModel: "inverse" as const,
      spatialMinDistance: options.minDistance ?? 1,
      spatialMaxDistance: options.maxDistance ?? 40,
      spatialRolloffFactor: 1,
      loop: options.loop ?? false,
      volume: options.volume ?? 1,
    };
  }
}
