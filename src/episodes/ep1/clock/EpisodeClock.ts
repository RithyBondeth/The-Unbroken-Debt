import "@/ui/html/clockCard.css";
import type { Flags } from "@/core/Flags";

/** The cursed stopped-clock motif shared by Studio (P05), Taxi, and the Hall Wall Clock. */
export const CURSED_CLOCK_TIME = "20:12";

const LABELS: Record<string, string> = {
  "20:00": "Phnom Penh · Studio",
  "20:12": "The Clock Stopped",
  "22:45": "Road Out of Town",
  "23:30": "Village · Flooded Road",
  "23:45": "The Farmstead",
  "00:00": "Midnight Watch",
  "00:30": "The Three Wards",
  "01:00": "The First Watch",
  "02:00": "Beneath the Stilts",
  "02:05": "Beneath the Stilts",
  "03:00": "Before Three",
  "05:30": "Dawn",
};

/**
 * Pure Episode 1 Night Clock state: tracks story-paced time (`ep1.clock`),
 * detects hour/milestone transitions for Fatal Frame-style cards, and supports
 * haunted `20:12` glitch windows during peak supernatural anomalies.
 */
export class EpisodeClockState {
  private glitchRemaining = 0;
  private lastAnnounced = "";

  constructor(private readonly flags: Flags) {
    this.lastAnnounced = this.rawTime;
  }

  get rawTime(): string {
    return this.flags.get("ep1.clock", "23:30");
  }

  get glitched(): boolean {
    return this.glitchRemaining > 0;
  }

  /** Time shown on Sora's watch / Pause / Sketchbook: flickers to 20:12 during anomalies. */
  get displayTime(): string {
    return this.glitched ? CURSED_CLOCK_TIME : this.rawTime;
  }

  get label(): string {
    if (this.glitched) return "It stopped again…";
    return LABELS[this.rawTime] ?? "The House of Mourning";
  }

  /** Advances the story clock and returns the announcement if it changed meaningfully. */
  advance(time: string, customLabel?: string): { time: string; label: string } | null {
    this.flags.set("ep1.clock", time);
    if (time === this.lastAnnounced) return null;
    this.lastAnnounced = time;
    return { time, label: customLabel ?? LABELS[time] ?? "The House of Mourning" };
  }

  /** Checks if another subsystem updated `ep1.clock` to a new major timestamp. */
  pollMilestone(): { time: string; label: string } | null {
    const now = this.rawTime;
    if (now === this.lastAnnounced) return null;
    this.lastAnnounced = now;
    // Show subtle hour-transition cards on clean milestone jumps
    if (now in LABELS) return { time: now, label: LABELS[now] };
    return null;
  }

  triggerGlitch(seconds: number): void {
    this.glitchRemaining = Math.max(this.glitchRemaining, seconds);
  }

  update(dt: number): void {
    if (this.glitchRemaining > 0) this.glitchRemaining = Math.max(0, this.glitchRemaining - dt);
  }
}

/**
 * Episode 1 Diegetic Night Clock UI:
 * - Zero permanent HUD clutter (strictly honours DESIGN.md).
 * - Brief 3.2-second atmospheric serif timestamp cards on night transitions (`23:30`, `00:00`, `01:00`...).
 * - Quick-glance vintage watch (`T` key) showing current time for 2.6 s — glitching to `20:12` during haunts!
 */
export class EpisodeClockUi {
  readonly state: EpisodeClockState;
  private readonly card = document.createElement("div");
  private readonly cardTime = document.createElement("p");
  private readonly cardLabel = document.createElement("p");
  private readonly watch = document.createElement("div");
  private readonly watchTime = document.createElement("p");
  private readonly watchSub = document.createElement("p");
  private cardTimer: ReturnType<typeof setTimeout> | undefined;
  private watchTimer: ReturnType<typeof setTimeout> | undefined;
  private readonly abort = new AbortController();

  constructor(
    flags: Flags,
    private readonly canGlance: () => boolean,
    private readonly onChime?: (glitched: boolean) => void,
    private readonly onWatchClick?: () => void,
  ) {
    this.state = new EpisodeClockState(flags);

    this.card.className = "ep1-clock-card";
    this.card.setAttribute("aria-live", "polite");
    this.cardTime.className = "ep1-clock-time";
    this.cardLabel.className = "ep1-clock-label";
    this.card.append(this.cardTime, this.cardLabel);
    document.body.append(this.card);

    this.watch.className = "ep1-watch-glance";
    this.watch.setAttribute("aria-live", "polite");
    this.watchTime.className = "ep1-clock-time";
    this.watchSub.className = "ep1-watch-sub";
    this.watch.append(this.watchTime, this.watchSub);
    document.body.append(this.watch);

    window.addEventListener(
      "keydown",
      (e) => {
        if (e.repeat || e.code !== "KeyT" || !this.canGlance()) return;
        this.glanceWatch();
      },
      { signal: this.abort.signal },
    );
  }

  /** Shows a brief 3.2-second Fatal Frame-style hour transition card. */
  announce(time: string, label?: string, playChime = true): void {
    const entry = this.state.advance(time, label) ?? {
      time,
      label: label ?? this.state.label,
    };
    this.showCard(entry.time, entry.label, false);
    if (playChime) this.onChime?.(false);
  }

  /** Triggers the haunted `20:12` clock anomaly for `seconds`. */
  glitch(seconds = 8): void {
    this.state.triggerGlitch(seconds);
  }

  /** `T` key: quick 2.6-second glance at Sora's vintage wristwatch / pocket watch. */
  glanceWatch(): void {
    const glitched = this.state.glitched;
    this.watchTime.textContent = this.state.displayTime;
    this.watchSub.textContent = glitched ? "Stopped · 20:12" : `${this.state.label} · Until Dawn`;
    this.watch.classList.toggle("glitched", glitched);
    this.watch.classList.add("shown");
    this.onWatchClick?.();
    clearTimeout(this.watchTimer);
    this.watchTimer = setTimeout(() => this.watch.classList.remove("shown"), 2600);
  }

  update(dt: number): void {
    this.state.update(dt);
    const next = this.state.pollMilestone();
    if (next) {
      this.showCard(next.time, next.label, false);
      this.onChime?.(false);
    }
  }

  private showCard(time: string, label: string, glitched: boolean): void {
    this.cardTime.textContent = time;
    this.cardLabel.textContent = label;
    this.card.classList.toggle("glitched", glitched);
    this.card.classList.add("shown");
    clearTimeout(this.cardTimer);
    this.cardTimer = setTimeout(() => this.card.classList.remove("shown"), 3400);
  }

  dispose(): void {
    this.abort.abort();
    clearTimeout(this.cardTimer);
    clearTimeout(this.watchTimer);
    this.card.remove();
    this.watch.remove();
  }
}
