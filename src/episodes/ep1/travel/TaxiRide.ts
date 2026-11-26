import { setControlText } from "@/ui/html/controlText";
import type { Game } from "@/core/Game";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { newGameSave, type SaveData } from "@/systems/saves/SaveData";
import { seededRandom } from "@/audio/synth";
import { villageRain } from "@/audio/sounds/nightSounds";
import { taxiMotor, taxiWipers } from "../audio/taxiSounds";
import { cabinStormBed } from "../audio/taxiDreadSounds";
import { DreadScore } from "@/audio/DreadScore";
import { WindAudio, stingGust } from "../audio/WindAudio";
import { TaxiVisuals } from "./TaxiVisuals";
import { TAXI_CONVERSATION, taxiConversationAt, taxiVoiceUrls } from "./taxiConversation";
import { TaxiSoundscape, taxiAnxietyLevel, taxiThrottle } from "./TaxiSoundscape";
import { taxiLightning, taxiVacuumDuck } from "./taxiApparitions";

const TAXI_SECONDS = 72;
/** The playable journey between CP0 and CP1. Reload resumes the ride, never an empty studio. */
export class TaxiRide {
  elapsed = 0;
  private running = false;
  private ending = false;
  private dialogueIndex = -1;
  private savedBucket = -1;
  private persisting: Promise<void> = Promise.resolve();
  private readonly loops: { sound: StaticSound; base: number }[] = [];
  private visuals!: TaxiVisuals;
  private windAudio!: WindAudio;
  private dread: TaxiSoundscape | null = null;
  /** Both speakers' Khmer lines, in conversation order. */
  private readonly dialogueVoice = new Map<number, StaticSound>();
  private speaking: StaticSound | null = null;
  private score = new DreadScore(null);
  private skip: HTMLButtonElement | null = null;

  constructor(private readonly game: Game) {}

  async load(): Promise<void> {
    const g = this.game;
    this.elapsed = Math.max(0, Math.min(TAXI_SECONDS - 1, g.flags.get("ep1.travel.elapsed", 0)));
    g.flags.set("ep1.travel.resumeAt", this.elapsed);
    g.cutscene = true;
    g.gated.holdStill = true;
    g.interaction.allow = () => false;
    this.visuals = await TaxiVisuals.load(g);
    // The storm the taxi drives into: gusts off the paddies buffet the car.
    g.wind.base = 0.78;
    this.windAudio = new WindAudio(g, g.wind, { vehicle: true });
    if (import.meta.env.DEV) (window as unknown as { taxi: TaxiRide }).taxi = this;
    g.scene.onBeforeRenderObservable.add(() => this.update(g.deltaSeconds));
  }

  async begin(): Promise<void> {
    const g = this.game;
    this.visuals.configure();
    this.visuals.update(0, this.elapsed, 0);
    await g.fade.to(1, 0);
    await g.fade.waitForEnter(() => {
      void g.input.lockPointer();
      void g.audio?.unlock();
    });
    await this.makeSounds();
    for (const loop of this.loops) loop.sound.play();
    this.dread?.begin(this.elapsed);
    await g.fade.to(0, 2);
    this.running = true;
    try {
      if (localStorage.getItem("boon-sop.taxi.seen") === "1") {
        this.skip = document.createElement("button");
        setControlText(this.skip, "Skip journey · Enter");
        this.skip.className = "taxi-skip";
        this.skip.onclick = () => void this.finish();
        document.body.append(this.skip);
        window.addEventListener("keydown", (e) => {
          if (e.code === "Enter" && !e.repeat) void this.finish();
        });
      }
    } catch {
      /* Storage preference is optional; the journey still plays. */
    }
  }

  private update(dt: number): void {
    if (!this.running || this.ending) return;
    this.elapsed = Math.min(TAXI_SECONDS, this.elapsed + dt);
    const t = this.elapsed,
      flash = taxiLightning(t),
      vacuum = taxiVacuumDuck(t),
      ambientKeep = 1 - vacuum;
    this.visuals.update(dt, t, flash);
    this.windAudio.update(dt);
    this.dread?.update(t);
    // Vacuum-silence ducking before major haunt hits pulls engine, wipers, rain and roof drumming
    // into suffocating dead air so each spatial impact detonates with maximum anxiety and surprise.
    if (this.loops[0])
      this.loops[0].sound.volume =
        this.loops[0].base * taxiThrottle(t) * (0.28 + 0.72 * ambientKeep);
    for (let i = 1; i < this.loops.length; i++)
      this.loops[i].sound.volume = this.loops[i].base * ambientKeep;
    // Dread score and storm wind track the full 5-beat psychological anxiety arc.
    const pressure = Math.min(1, taxiAnxietyLevel(t) * 0.85 + (t > 24 && t < 62 ? 0.15 : 0));
    this.score.pressure(pressure);
    const g = this.game;
    g.wind.tension = pressure;
    g.wind.calm = Math.max(
      t > 33.5 && t < 37.6 ? Math.min(1, (t - 33.5) / 2) * 0.85 : 0,
      vacuum * 0.92,
    );
    this.score.update(dt);
    const line = taxiConversationAt(t);
    if ((line?.index ?? -1) !== this.dialogueIndex) {
      this.dialogueIndex = line?.index ?? -1;
      if (line) this.game.subtitles.show(line.speaker, line.text);
      else this.game.subtitles.hide();
      // Spoken from its first word; a ride resumed mid-line shows only the subtitle.
      const voice = line ? this.dialogueVoice.get(line.index) : undefined;
      if (line && voice && t - line.at < 0.5) {
        this.speaking?.stop();
        this.speaking = voice;
        voice.play();
      }
    }
    const bucket = Math.floor(t / 8);
    if (bucket !== this.savedBucket) {
      this.savedBucket = bucket;
      const save = this.capture();
      this.persisting = this.persisting
        .then(() => this.game.saves.save("autosave", save))
        .catch(() => {
          this.game.hints.show("note.saveFailed", 5);
        });
    }
    if (t >= TAXI_SECONDS) void this.finish();
  }

  private capture(): SaveData {
    const g = this.game;
    g.flags.set("ep1.travel.elapsed", Math.floor(this.elapsed));
    return {
      ...newGameSave(),
      checkpoint: "CP0",
      clock: "22:45",
      flags: g.flags.toJSON(),
      inventory: g.inventory.toJSON(),
      lamp: g.savedLamp ?? { oil: 1, state: "out" },
      playTimeSec:
        (g.resumedSave?.playTimeSec ?? 0) +
        Math.floor(this.elapsed - g.flags.get("ep1.travel.resumeAt", 0)),
    };
  }

  private async finish(): Promise<void> {
    if (this.ending) return;
    this.ending = true;
    this.skip?.remove();
    this.game.subtitles.hide();
    const g = this.game;
    await g.fade.to(1, 2);
    this.speaking?.stop();
    for (const loop of this.loops) loop.sound.stop();
    this.score.stop();
    this.windAudio.stop();
    this.dread?.stop();
    await this.persisting;
    const save = this.capture();
    save.checkpoint = "CP1";
    save.clock = "23:30";
    Object.assign(save.flags, {
      "ep1.travel.pending": false,
      "ep1.travel.complete": true,
      "ep1.checkpoint": "CP1",
      "ep1.clock": "23:30",
      "ep1.early.required": true,
      "ep1.arrival.road": true,
    });
    while (true) {
      try {
        await g.checkpoints.mark(save, "Village · Flooded road");
        break;
      } catch {
        await g.fade.show({
          title: "The journey is ready",
          body: "Could not save the arrival checkpoint. Free browser storage and retry.",
          button: "Retry save",
        });
      }
    }
    try {
      localStorage.setItem("boon-sop.taxi.seen", "1");
    } catch {
      /* Optional preference. */
    }
    location.replace(`${location.pathname}?continue`);
  }

  private async makeSounds(): Promise<void> {
    const audio = this.game.audio;
    if (!audio) return;
    // Place the listener inside tight 1933 steel-and-upholstery sedan cabin acoustics.
    audio.setSpace("cabin", 0.3);
    const rate = audio.context.sampleRate;
    for (const [name, samples, volume] of [
      ["taxi_motor", taxiMotor(rate, seededRandom(210)), 0.62],
      ["taxi_wipers", taxiWipers(rate, seededRandom(211)), 0.42],
      ["taxi_rain", villageRain(rate, seededRandom(212)), 0.5],
      ["taxi_cabin_storm", cabinStormBed(rate, seededRandom(214)), 0.64],
    ] as const) {
      const sound = await audio.sound(name, audio.buffer(samples, rate), "room", volume);
      sound.loop = true;
      this.loops.push({ sound, base: volume });
    }
    // Load each take before starting the ride clock.
    await Promise.all(
      TAXI_CONVERSATION.map(async (line, index) => {
        const urls = taxiVoiceUrls(line.speaker, line.voice).map(
          (url) => `${import.meta.env.BASE_URL}${url}`,
        );
        const buffer = await audio.load(urls);
        if (buffer)
          this.dialogueVoice.set(
            index,
            await audio.sound(`taxi_${line.speaker}_${line.voice}`, buffer, "voice", 0.95),
          );
      }),
    );
    this.score = new DreadScore(audio);
    this.score.onSting = (kind, volume) =>
      stingGust(this.game.wind, kind, volume, this.score.lead(kind));
    await this.score.load();
    await this.windAudio.makeSounds();
    this.dread = new TaxiSoundscape(
      audio,
      this.visuals.route,
      this.score,
      this.visuals.meterPosition(),
    );
    await this.dread.load();
  }
}
