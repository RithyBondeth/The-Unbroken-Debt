import { describe, it, expect } from "vitest";
import { Flags } from "../../src/core/Flags";
import { ResolutionProgress } from "../../src/episodes/ep1/resolution/ResolutionProgress";
import { newGameSave } from "../../src/systems/saves/SaveData";
import { encodeSaveCode, decodeSaveCode } from "../../src/systems/saves/saveCode";
function setup() {
  const flags = new Flags();
  return { flags, p: new ResolutionProgress(flags) };
}
describe("dawn resolution and Episode 2 completion", () => {
  it("requires the seal and an explicit journal choice, including false", () => {
    const { flags, p } = setup();
    expect(p.begin()).toBe(false);
    expect(p.advance()).toBe(false);
    flags.set("ep1.seal1.broken", true);
    expect(p.begin()).toBe(true);
    p.advance();
    expect(p.stage).toBe("choice");
    expect(p.advance()).toBe(false);
    expect(p.choose(false)).toBe(true);
    expect(p.choose(true)).toBe(false);
    expect(p.advance()).toBe(true);
    expect(p.stage).toBe("slip");
    expect(flags.get("ep1.slip.read", false)).toBe(true);
    expect(flags.get("ep1.slip.unread", true)).toBe(false);
    expect(flags.get("ep1.journal.shared", true)).toBe(false);
  });
  for (const shared of [true, false])
    it(`round trips the ${shared ? "shared" : "kept"} choice at every reveal and awards respect once`, async () => {
      const { flags, p } = setup();
      flags.set("ep1.seal1.broken", true);
      flags.set("ep1.betel.firstTry", true);
      flags.set("series.respect", 3);
      flags.set("lore.ep1.L2", true);
      p.begin();
      p.advance();
      p.choose(shared);
      for (let i = 0; i < 5; i++) {
        p.advance();
        const save = {
          ...newGameSave(),
          checkpoint: "CP6",
          clock: flags.get("ep1.clock", "05:30"),
          flags: flags.toJSON(),
          inventory: { seal_map: 1, folded_slip: 1, sok_journal: 1 },
        };
        const restored = await decodeSaveCode(await encodeSaveCode(save));
        flags.load(restored.flags);
        const next = new ResolutionProgress(flags);
        next.begin();
        expect(next.stage).toBe(p.stage);
        expect(flags.get("ep1.journal.shared", !shared)).toBe(shared);
      }
      expect(p.stage).toBe("credits");
      expect(p.advance()).toBe(false);
      expect(flags.get("ep1.complete", false)).toBe(true);
      expect(flags.get("series.nextEpisode", 0)).toBe(2);
      expect(flags.get("series.night", 0)).toBe(3);
      expect(flags.get("series.respect", 0)).toBe(5);
      expect(flags.get("ep1.respect.earned", 0)).toBe(2);
      expect(p.lore).toEqual(["L2"]);
      expect(flags.get("sketchbook.written", "").split(",")).toContain("SB-08");
      // A resumed summary cannot award again, even when revisited from credits.
      flags.set("ep1.resolution.stage", "title");
      p.advance();
      expect(flags.get("series.respect", 0)).toBe(5);
    });
  it("does not award offering or vigil respect when their conditions failed", () => {
    const { flags, p } = setup();
    flags.set("ep1.seal1.broken", true);
    flags.set("ep1.incense.neglected", true);
    flags.set("series.respect", 2);
    p.begin();
    p.advance();
    p.choose(true);
    while (p.stage !== "credits") p.advance();
    expect(flags.get("ep1.respect.earned", -1)).toBe(0);
    expect(flags.get("series.respect", 0)).toBe(2);
  });
});
