import { CreateAudioEngineAsync } from "@babylonjs/core/AudioV2/webAudio/webAudioEngine";
import type { AudioEngineV2 } from "@babylonjs/core/AudioV2/abstractAudio/audioEngineV2";
import type { AudioBus } from "@babylonjs/core/AudioV2/abstractAudio/audioBus";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { Node } from "@babylonjs/core/node";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";

/** The mix buses (Technical Design Document, section 12; Audio Design Document, section 2). */
export type BusName = "ambience" | "sfx" | "threat" | "voice" | "music" | "ui";

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

/**
 * The game's audio: Babylon's Audio Engine v2 with the mix buses, a listener
 * on the camera and helpers for positioned sounds. Browsers start audio only
 * after a click or key press, so call `unlock` from one.
 */
export class AudioSystem {
  private constructor(
    readonly engine: AudioEngineV2,
    readonly buses: Record<BusName, AudioBus>,
    readonly context: BaseAudioContext,
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
      // The game unlocks sound with its own "Click to begin".
      disableDefaultUI: hideUnmuteButton,
    });
    const names: BusName[] = ["ambience", "sfx", "threat", "voice", "music", "ui"];
    const buses = Object.fromEntries(
      await Promise.all(names.map(async (n) => [n, await engine.createBusAsync(n)] as const)),
    ) as Record<BusName, AudioBus>;
    const context = (engine as unknown as { _audioContext: BaseAudioContext })._audioContext;
    return new AudioSystem(engine, buses, context);
  }

  async unlock(): Promise<void> {
    await this.engine.unlockAsync();
  }

  /** The listener follows this node (the player's camera): position and turn. */
  attachListener(node: Node): void {
    this.engine.listener.attach(node);
  }

  /** Wraps mono samples in an audio buffer for this engine. */
  buffer(samples: Float32Array, sampleRate: number): AudioBuffer {
    const buffer = this.context.createBuffer(1, samples.length, sampleRate);
    buffer.copyToChannel(samples as Float32Array<ArrayBuffer>, 0);
    return buffer;
  }

  /** A sound placed in the world on `bus`, panned the way that bus requires. */
  async spatialSound(
    name: string,
    buffer: AudioBuffer,
    bus: BusName,
    position: Vector3,
    options: SpatialOptions = {},
  ): Promise<StaticSound> {
    const panning = options.panning ?? PANNING[bus] ?? "equalpower";
    const sound = await this.engine.createSoundAsync(name, buffer, {
      outBus: this.buses[bus],
      spatialEnabled: true,
      spatialPanningModel: panning,
      spatialPosition: position.clone(),
      spatialDistanceModel: "inverse",
      spatialMinDistance: options.minDistance ?? 1,
      spatialMaxDistance: options.maxDistance ?? 40,
      spatialRolloffFactor: 1,
      loop: options.loop ?? false,
      volume: options.volume ?? 1,
    });
    return sound;
  }
}
