import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import type { AudioSystem } from "@/audio/AudioSystem";
import { rattlingBreath, seededRandom, wetStep } from "@/audio/synth";
import { sniff } from "./houseSounds";
import { ep1AudioUrls } from "./VillageAudio";

const HEAD = 1.62;

/**
 * Preay's intimate, spatialized vocal & movement presence (Acts II–III & village stalks):
 * backed by real mastered CC0 wet throat-rattle, close-mic breath, neck-crack, and wet drag
 * recordings (replacing the old metallic synth buzz), with procedural fallback offline.
 */
export class StalkerVoice {
  private readonly drags: StaticSound[] = [];
  private breath: StaticSound | null = null;
  private rattle: StaticSound | null = null;
  private sniffSound: StaticSound | null = null;
  private breathing = false;
  private next = 0;
  private rattleCooldown = 0;

  constructor(private readonly volume = 0.62) {}

  async load(audio: AudioSystem | null, name: string, seed: number): Promise<void> {
    if (!audio) return;
    const rate = audio.context.sampleRate;
    const at = Vector3.Zero();

    const [recBreath, recRattle, recWhisper, recSplash] = await Promise.all([
      audio.load(ep1AudioUrls("sfx_ep1_preay_breath_1")),
      audio.load(ep1AudioUrls("sfx_ep1_preay_rattle")),
      audio.load(ep1AudioUrls("sfx_ep1_preay_whisper_1")),
      audio.load(ep1AudioUrls("sfx_ep1_taxi_mud_splash_1")),
    ]);

    for (let k = 0; k < 3; k++) {
      const drag = await audio.spatialSound(
        `${name}_drag_${k}`,
        recSplash ?? audio.buffer(wetStep(rate, seededRandom(seed + k)), rate),
        "threat",
        at,
        { panning: "HRTF", minDistance: 2, maxDistance: 28, volume: this.volume * 0.62 },
      );
      drag.playbackRate = 0.78 + k * 0.06;
      this.drags.push(drag);
    }

    this.breath = await audio.spatialSound(
      `${name}_breath`,
      recBreath ?? audio.buffer(rattlingBreath(rate, seededRandom(seed + 10)), rate),
      "threat",
      at,
      { panning: "HRTF", loop: true, minDistance: 1.4, maxDistance: 22, volume: 0 },
    );

    if (recRattle) {
      this.rattle = await audio.spatialSound(`${name}_rattle`, recRattle, "threat", at, {
        panning: "HRTF",
        minDistance: 1.5,
        maxDistance: 24,
        volume: this.volume * 0.9,
      });
    }

    this.sniffSound = await audio.spatialSound(
      `${name}_sniff`,
      recWhisper ?? audio.buffer(sniff(rate, seededRandom(seed + 12)), rate),
      "threat",
      at,
      { panning: "HRTF", minDistance: 1.6, maxDistance: 22, volume: this.volume * 0.85 },
    );
  }

  step(feet: Vector3): void {
    const drag = this.drags[this.next++ % Math.max(1, this.drags.length)];
    if (!drag) return;
    drag.spatial.position = feet.add(new Vector3(0, 0.05, 0));
    drag.play();
  }

  breathe(feet: Vector3 | null, urgency = 0, presence = 1): void {
    const breath = this.breath;
    if (!breath) return;
    if (!feet) {
      if (this.breathing) breath.stop();
      this.breathing = false;
      return;
    }
    const headPos = feet.add(new Vector3(0, HEAD, 0));
    breath.spatial.position = headPos;
    breath.volume = this.volume * (0.55 + 0.55 * urgency) * Math.max(0, Math.min(1, presence));
    breath.playbackRate = 0.92 + 0.36 * urgency;
    if (!this.breathing) breath.play();
    this.breathing = true;
    this.rattleCooldown -= 0.016;
    if (this.rattle && urgency > 0.35 && this.rattleCooldown <= 0) {
      this.rattleCooldown = 4.2 + Math.random() * 3.5;
      this.rattle.spatial.position = headPos.clone();
      this.rattle.volume = this.volume * (0.7 + 0.3 * urgency) * presence;
      this.rattle.play();
    }
  }

  sniffAt(feet: Vector3): void {
    const pos = feet.add(new Vector3(0, HEAD - 0.1, 0));
    if (this.rattle) {
      this.rattle.spatial.position = pos.clone();
      this.rattle.play();
    }
    if (this.sniffSound) {
      this.sniffSound.spatial.position = pos;
      this.sniffSound.play();
    }
  }

  stop(): void {
    this.breathe(null);
    for (const drag of this.drags) drag.stop();
    this.rattle?.stop();
    this.sniffSound?.stop();
  }
}
