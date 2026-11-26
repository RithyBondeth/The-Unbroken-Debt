import { setControlText } from "@/ui/html/controlText";
import type { Game } from "@/core/Game";
import type { StaticSound } from "@babylonjs/core/AudioV2/abstractAudio/staticSound";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { newGameSave, type SaveData } from "@/systems/saves/SaveData";
import { seededRandom } from "@/audio/synth";
import { taxiMotor, taxiRoadWash, taxiWiperStroke } from "../audio/taxiSounds";
import { cabinStormBed } from "../audio/taxiDreadSounds";
import { DreadScore } from "@/audio/DreadScore";
import { WindAudio, stingGust } from "../audio/WindAudio";
import { TaxiVisuals } from "./TaxiVisuals";
import { TAXI_CONVERSATION, taxiConversationAt, taxiDriverVoiceUrls } from "./taxiConversation";
import { TaxiSoundscape, taxiAnxietyLevel, taxiThrottle } from "./TaxiSoundscape";
import { taxiElectrics, taxiFlinch, taxiLightning, taxiVacuumDuck } from "./taxiApparitions";
import { taxiSpeed, taxiWiperAngle } from "./taxiMotion";

const TAXI_SECONDS = 72;

function ep1AudioUrls(name: string): string[] {
  const base = `${import.meta.env.BASE_URL}assets/ep1/audio/${name}`;
  return [`${base}.ogg`, `${base}.m4a`];
}

/** The playable journey between CP0 and CP1. Reload resumes the ride, never an empty studio. */
export class TaxiRide {
  elapsed = 0;
  private running = false;
  private ending = false;
  private dialogueIndex = -1;
  private savedBucket = -1;
  private persisting: Promise<void> = Promise.resolve();
  private motorLoop: { sound: StaticSound; base: number } | null = null;
  private roadLoop: { sound: StaticSound; base: number } | null = null;
  private rainLoop: { sound: StaticSound; base: number } | null = null;
  private roofLoop: { sound: StaticSound; base: number } | null = null;
  private wiperStrokes: StaticSound[] = [];
  private lastWiperDir = 0;
  private wiperToggle = 0;
  private lastDuckFactor = 1;
  private visuals!: TaxiVisuals;
  private windAudio!: WindAudio;
  private dread: TaxiSoundscape | null = null;
  /** The driver's Khmer lines, spatialized at his front-left seat by their `voice` number. */
  private readonly driverVoice = new Map<number, StaticSound>();
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
    for (const loop of this.allLoops()) loop.sound.play();
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

  private allLoops(): { sound: StaticSound; base: number }[] {
    return [this.motorLoop, this.roadLoop, this.rainLoop, this.roofLoop].filter(
      (x): x is { sound: StaticSound; base: number } => x !== null,
    );
  }

  private update(dt: number): void {
    if (!this.running || this.ending) return;
    const prevT = this.elapsed;
    this.elapsed = Math.min(TAXI_SECONDS, this.elapsed + dt);
    const t = this.elapsed,
      flash = taxiLightning(t),
      vacuum = taxiVacuumDuck(t),
      speed = taxiSpeed(t),
      speedRatio = speed / 6.8,
      throttle = taxiThrottle(t),
      power = taxiElectrics(t),
      flinch = taxiFlinch(t),
      ambientKeep = 1 - vacuum;
    this.visuals.update(dt, t, flash);
    this.windAudio.update(dt);
    this.dread?.update(t);

    // Smooth Web Audio bus vacuum ducking + subtle post-shock stunned-ear hush!
    const shockHush = flinch > 0.35 ? (flinch - 0.35) * 0.32 : 0;
    const duckTarget = Math.max(0.14, 1 - vacuum * 0.82 - shockHush);
    if (Math.abs(duckTarget - this.lastDuckFactor) > 0.015) {
      this.game.audio?.duckAmbience(duckTarget, vacuum > 0.1 ? 0.24 : 0.45);
      this.lastDuckFactor = duckTarget;
    }

    // Dynamic speed-reactive 1933 4-cylinder RPM (smoothly drops to chugging vintage idle when braking!)
    if (this.motorLoop) {
      const rpm = 0.64 + 0.36 * speedRatio * (0.76 + 0.24 * throttle) + Math.sin(t * 0.85) * 0.015;
      this.motorLoop.sound.playbackRate = rpm;
      this.motorLoop.sound.volume =
        this.motorLoop.base * (0.45 + 0.55 * throttle) * (0.26 + 0.74 * ambientKeep);
    }
    // Speed-scaled flooded laterite tire spray & puddle wash (fades cleanly to zero as car stops!)
    if (this.roadLoop) {
      this.roadLoop.sound.playbackRate = 0.72 + 0.3 * speedRatio;
      this.roadLoop.sound.volume = this.roadLoop.base * speedRatio ** 1.35 * ambientKeep;
    }
    // Real enclosed-cabin heavy monsoon rain + subtle tin-roof droplet body
    if (this.rainLoop) this.rainLoop.sound.volume = this.rainLoop.base * ambientKeep;
    if (this.roofLoop) this.roofLoop.sound.volume = this.roofLoop.base * ambientKeep;

    // Exact visual-synchronized windscreen wiper squeegee sweeps tied to `taxiWiperAngle(t)` reversals!
    if (dt > 0 && this.wiperStrokes.length > 0) {
      const dir = Math.sign(taxiWiperAngle(t) - taxiWiperAngle(Math.max(0, prevT - 0.005)));
      if (dir !== 0 && this.lastWiperDir !== 0 && dir !== this.lastWiperDir && vacuum < 0.75) {
        const stroke = this.wiperStrokes[this.wiperToggle++ % this.wiperStrokes.length];
        stroke.playbackRate = (dir > 0 ? 1.03 : 0.94) * (0.88 + 0.12 * power);
        stroke.volume = 0.32 * ambientKeep * (0.55 + 0.45 * power);
        stroke.play();
      }
      if (dir !== 0) this.lastWiperDir = dir;
    }

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
      const voice = line?.voice ? this.driverVoice.get(line.voice) : undefined;
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
    g.audio?.duckAmbience(1, 0.4);
    this.speaking?.stop();
    for (const loop of this.allLoops()) loop.sound.stop();
    for (const w of this.wiperStrokes) w.stop();
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
    // Tight 1933 steel-and-upholstery sedan cabin acoustics.
    audio.setSpace("cabin", 0.3);
    const rate = audio.context.sampleRate;

    // 1. Speed-reactive vintage 4-cylinder engine + separate speed-reactive flooded-road tire wash
    const motorSound = await audio.sound(
      "taxi_motor",
      audio.buffer(taxiMotor(rate, seededRandom(210)), rate),
      "room",
      0.54,
    );
    motorSound.loop = true;
    this.motorLoop = { sound: motorSound, base: 0.54 };

    const roadSound = await audio.sound(
      "taxi_road_wash",
      audio.buffer(taxiRoadWash(rate, seededRandom(215)), rate),
      "room",
      0.42,
    );
    roadSound.loop = true;
    this.roadLoop = { sound: roadSound, base: 0.42 };

    // 2. Real mastered CC0 closed-cabin heavy monsoon rain + subtle tin-roof droplet body
    const recordedRain = await audio.load(ep1AudioUrls("amb_ep1_taxi_rain_cabin"));
    const rainSound = await audio.sound(
      "taxi_rain_cabin_real",
      recordedRain ?? audio.buffer(cabinStormBed(rate, seededRandom(212)), rate),
      "room",
      recordedRain ? 0.66 : 0.54,
    );
    rainSound.loop = true;
    this.rainLoop = { sound: rainSound, base: recordedRain ? 0.66 : 0.54 };

    const roofSound = await audio.sound(
      "taxi_cabin_roof_drops",
      audio.buffer(cabinStormBed(rate, seededRandom(214)), rate),
      "room",
      recordedRain ? 0.28 : 0.48,
    );
    roofSound.loop = true;
    this.roofLoop = { sound: roofSound, base: recordedRain ? 0.28 : 0.48 };

    // 3. Spatialized windscreen wiper squeegee strokes (alternating pair synced to visual wipers!)
    const wiperPos = new Vector3(0.05, 1.12, 0.58);
    this.wiperStrokes = await Promise.all(
      [216, 217].map((seed, i) =>
        audio.spatialSound(
          `taxi_wiper_stroke_${i}`,
          audio.buffer(taxiWiperStroke(rate, seededRandom(seed)), rate),
          "sfx",
          wiperPos,
          { minDistance: 0.5, maxDistance: 5, volume: 0.32 },
        ),
      ),
    );

    // 4. Driver's recorded Khmer voice, spatialized authentically at the driver's left-seat head!
    const driverHeadPos = new Vector3(-0.48, 1.04, -0.02);
    await Promise.all(
      TAXI_CONVERSATION.filter((line) => line.voice).map(async (line) => {
        const urls = taxiDriverVoiceUrls(line.voice!).map(
          (url) => `${import.meta.env.BASE_URL}${url}`,
        );
        const buffer = await audio.load(urls);
        if (buffer)
          this.driverVoice.set(
            line.voice!,
            await audio.spatialSound(`taxi_driver_${line.voice}`, buffer, "voice", driverHeadPos, {
              minDistance: 0.95,
              maxDistance: 6,
              volume: 0.96,
            }),
          );
      }),
    );

    // 5. Cinematic dread score powered by our mastered real CC0 horror drone bed!
    this.score = new DreadScore(audio);
    this.score.onSting = (kind, volume) =>
      stingGust(this.game.wind, kind, volume, this.score.lead(kind));
    await this.score.load(ep1AudioUrls("amb_ep1_taxi_dread_drone"));
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
