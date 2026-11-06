export interface SubtitleCue {
  at: number;
  duration: number;
  speaker: string;
  text: string;
}
export interface CinematicScript {
  id: string;
  title: string;
  duration: number;
  cues: readonly SubtitleCue[];
}
/** A render-clock timeline: pausing and backgrounding do not lose subtitles or animation beats. */
export class CinematicClock {
  elapsed = 0;
  paused = false;
  skipped = false;
  constructor(readonly script: CinematicScript) {}
  update(dt: number, visible = true): void {
    if (this.paused || !visible || this.finished) return;
    this.elapsed = Math.min(this.script.duration, this.elapsed + Math.max(0, Math.min(dt, 0.1)));
  }
  skip(): void {
    this.skipped = true;
    this.elapsed = this.script.duration;
  }
  get finished(): boolean {
    return this.elapsed >= this.script.duration;
  }
  get cue(): SubtitleCue | null {
    if (this.finished) return null;
    return (
      this.script.cues.find((c) => this.elapsed >= c.at && this.elapsed < c.at + c.duration) ?? null
    );
  }
}
/** Reading speed is authored in English; no runtime speech service or subtitle language switching. */
export function dialogueScript(
  id: string,
  title: string,
  lines: readonly [string, string][],
  gap = 0.6,
): CinematicScript {
  let at = 0.5;
  const cues = lines.map(([speaker, text]) => {
    const duration = Math.max(3.5, text.split(/\s+/).length / 2.6 + 0.6),
      cue = { at, duration, speaker, text };
    at += duration + gap;
    return cue;
  });
  return { id, title, cues, duration: at + 0.5 };
}
