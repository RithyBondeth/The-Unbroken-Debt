import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import type { AudioSystem } from "../../../audio/AudioSystem";
import type { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { seededRandom } from "../../../audio/synth";
import { chantDrone } from "./nightSounds";
import { shellacNoise } from "./houseSounds";
import { SOK_RECORDING } from "../data/investigation";
import voiceManifest from "../data/sokVoice.json";
import { parseVoiceManifest } from "../data/voiceManifest";

/** Positioned shellac noise, speed-controlled reversed drone and Sok's recorded performance. */
export class GramophoneAudio {
  private wrong: StaticSound | null = null;
  private preview: StaticSound | null = null;
  private crackle: StaticSound | null = null;
  private readonly voice: (StaticSound | null)[] = [];
  readonly durations: number[] = [];
  private running = false;
  private message = false;
  /** The voice can be Khmer while the current subtitle translation stays English. */
  language = "en-GB";

  async load(audio: AudioSystem | null, at: Vector3): Promise<void> {
    if (!audio) {
      this.durations.push(...SOK_RECORDING.map((text) => text.split(" ").length / 2.8));
      return;
    }
    const rate = audio.context.sampleRate;
    // Use the wordless stand-in, never reverse the licensed ceremonial recording.
    const reversed = chantDrone(rate, seededRandom(810)).reverse();
    this.wrong = await audio.spatialSound(
      "gramophone_reverse",
      audio.buffer(reversed, rate),
      "sfx",
      at,
      { loop: true, minDistance: 1.3, volume: 0.28 },
    );
    this.crackle = await audio.spatialSound(
      "gramophone_crackle",
      audio.buffer(shellacNoise(rate, seededRandom(811)), rate),
      "sfx",
      at,
      { loop: true, minDistance: 1.2, volume: 0.05 },
    );
    const manifest = parseVoiceManifest(voiceManifest, SOK_RECORDING.length);
    let buffers = manifest
      ? await Promise.all(
          manifest.paragraphs.map((files) =>
            audio.load(files.map((path) => `${import.meta.env.BASE_URL}${path}`)),
          ),
        )
      : [];
    if (!manifest || buffers.some((buffer) => !buffer)) {
      console.warn("[Sok voice] incomplete recording; using the complete English scratch take");
      buffers = await Promise.all(
        SOK_RECORDING.map((_, i) => {
          const base = `${import.meta.env.BASE_URL}assets/ep1/audio/vo_sok_scratch_${i + 1}`;
          return audio.load([`${base}.ogg`, `${base}.m4a`]);
        }),
      );
    } else this.language = manifest.language;
    for (let i = 0; i < SOK_RECORDING.length; i++) {
      const buffer = buffers[i];
      this.voice.push(
        buffer
          ? await audio.spatialSound(`sok_recording_${i}`, buffer, "voice", at, {
              minDistance: 1.6,
              volume: 0.85,
            })
          : null,
      );
      this.durations.push(buffer?.duration ?? SOK_RECORDING[i].split(" ").length / 2.8);
      if (i === 0 && buffer)
        this.preview = await audio.spatialSound("gramophone_voice_preview", buffer, "voice", at, {
          loop: true,
          minDistance: 1.3,
          volume: 0,
        });
    }
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    this.wrong?.play();
    this.preview?.play();
    this.crackle?.play();
  }

  tune(rpm: number, clarity: number): void {
    if (this.wrong) {
      this.wrong.playbackRate = rpm / 78;
      this.wrong.volume = this.message ? 0 : 0.3 * (1 - clarity * 0.85);
    }
    if (this.preview) {
      this.preview.playbackRate = rpm / 78;
      this.preview.volume = this.message ? 0 : 0.55 * clarity ** 4;
    }
  }

  beginMessage(): void {
    this.message = true;
    this.wrong?.stop();
    this.preview?.stop();
  }

  playParagraph(index: number): void {
    this.voice[index]?.play();
  }
  endMessage(): void {
    this.message = false;
    this.crackle?.stop();
    this.running = false;
  }
}
