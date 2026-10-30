import type { Flags } from "../../../core/Flags";

const RESOLUTION_STAGES = ["dawn", "choice", "slip", "map", "title", "summary", "credits"] as const;
export type ResolutionStage = (typeof RESOLUTION_STAGES)[number];
/** R01–R05: each reveal and the one-time respect award survive reloads. */
export class ResolutionProgress {
  constructor(readonly flags: Flags) {}
  get available(): boolean {
    return this.flags.get("ep1.seal1.broken", false);
  }
  get stage(): ResolutionStage {
    const stage = this.flags.get("ep1.resolution.stage", "dawn");
    return RESOLUTION_STAGES.includes(stage) ? stage : "dawn";
  }
  begin(): boolean {
    if (!this.available) return false;
    this.flags.set("ep1.resolution.started", true);
    this.flags.set("ep1.checkpoint", "CP6");
    if (this.stage === "dawn") this.flags.set("ep1.clock", "05:30");
    return true;
  }
  choose(shared: boolean): boolean {
    if (!this.available || this.stage !== "choice" || this.flags.has("ep1.journal.shared"))
      return false;
    this.flags.set("ep1.journal.shared", shared);
    return true;
  }
  advance(): boolean {
    if (!this.available || (this.stage === "choice" && !this.flags.has("ep1.journal.shared")))
      return false;
    const index = RESOLUTION_STAGES.indexOf(this.stage);
    if (index === RESOLUTION_STAGES.length - 1) return false;
    const next = RESOLUTION_STAGES[index + 1];
    this.flags.set("ep1.resolution.stage", next);
    if (next === "choice") {
      this.flags.set("ep1.clock", "05:35");
      this.flags.set("ep1.vuthy.left", false);
    }
    if (next === "slip") {
      this.flags.set("ep1.vuthy.left", true);
      this.flags.set("ep1.clock", "05:40");
      this.flags.set("ep1.slip.unread", false);
      this.flags.set("ep1.slip.read", true);
    }
    if (next === "map") {
      this.flags.set("ep1.clock", "05:42");
      this.flags.set("ep1.map.pagoda", true);
      this.flags.set("series.night", 3);
      const written = new Set(this.flags.get("sketchbook.written", "").split(",").filter(Boolean));
      written.add("SB-08");
      this.flags.set("sketchbook.written", [...written].join(","));
    }
    if (next === "summary" && !this.flags.get("ep1.complete", false)) {
      const respect =
        Number(this.flags.get("ep1.betel.firstTry", false)) +
        Number(!this.flags.get("ep1.incense.neglected", false));
      this.flags.set("ep1.respect.earned", respect);
      this.flags.set("series.respect", Math.min(9, this.flags.get("series.respect", 0) + respect));
      this.flags.set("ep1.complete", true);
      this.flags.set("series.nextEpisode", 2);
    }
    return true;
  }
  get lore(): string[] {
    return [1, 2, 3, 4, 5]
      .map((n) => `L${n}`)
      .filter((id) => this.flags.get(`lore.ep1.${id}`, false));
  }
}
