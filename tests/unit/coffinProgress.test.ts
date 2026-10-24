import { describe, it, expect } from "vitest";
import { Flags } from "../../src/core/Flags";
import { CoffinProgress } from "../../src/episodes/ep1/act3/CoffinProgress";
function tick(p: CoffinProgress, seconds: number, hold = false, visible = true, paused = false) {
  for (let i = 0; i < Math.ceil(seconds * 10); i++)
    p.update(0.1, true, true, visible, hold, paused);
}
describe("coffin reveal and closure", () => {
  it("requires the token, proximity and a view; triggers once and restores open without replaying the bang", () => {
    const f = new Flags(),
      p = new CoffinProgress(f);
    expect(p.update(0.1, false, true, true, false, false)).toBeNull();
    expect(p.update(0.1, true, false, true, false, false)).toBeNull();
    expect(p.update(0.1, true, true, false, false, false)).toBeNull();
    expect(p.update(0.1, true, true, true, false, false)).toBe("rattle");
    const next = new CoffinProgress(f);
    expect(next.phase).toBe("open");
    expect(next.update(0.1, true, true, true, false, false)).toBeNull();
    tick(p, 2);
    expect(p.phase).toBe("open");
  });
  it("requires seeing the body before holding E for three seconds; releasing yields the lid; menus pause", () => {
    const f = new Flags();
    f.set("ep1.coffin.triggered", true);
    const p = new CoffinProgress(f);
    tick(p, 4, true, false);
    expect(p.closing).toBe(0);
    tick(p, 2, false);
    tick(p, 1, true);
    expect(p.closing).toBeCloseTo(1);
    tick(p, 20, true, true, true);
    expect(p.closing).toBeCloseTo(1);
    tick(p, 1, false);
    expect(p.openness).toBe(1);
    tick(p, 3, true);
    expect(p.phase).toBe("closed");
    expect(f.get("ep1.coffin.closed", false)).toBe(true);
    expect(new CoffinProgress(f).phase).toBe("closed");
    tick(p, 20);
    expect(p.phase).toBe("closed");
  });
  it("reopens an interrupted close safely without losing the seen-body milestone", () => {
    const f = new Flags();
    f.set("ep1.coffin.triggered", true);
    const p = new CoffinProgress(f);
    tick(p, 2);
    tick(p, 1, true);
    const restored = new CoffinProgress(f);
    expect(restored.phase).toBe("open");
    expect(restored.seenSeconds).toBe(2);
  });
});
