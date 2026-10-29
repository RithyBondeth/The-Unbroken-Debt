import { describe, expect, it } from "vitest";
import { Vector3 } from "@babylonjs/core/Maths/math.vector";
import { EarlyStealthBrain, RoadNavigation } from "../../src/episodes/ep1/act1/EarlyStealthBrain";
describe("listening presence and navigation", () => {
  it("requires both real line of sight and sustained exposure; cover blocks a catch", () => {
    const b = new EarlyStealthBrain(),
      player = b.position.add(new Vector3(0, 0, 3));
    b.update(0.2, player, true, false, true);
    expect(b.state).toBe("patrol");
    for (let i = 0; i < 40; i++) b.update(0.025, player, true, false, false);
    expect(b.state).not.toBe("chase");
    expect(b.suspicion).toBe(0);
    player.set(b.position.x + 1, 0, b.position.z);
    b.direction.copyFrom(player.subtract(b.position).normalize());
    for (let i = 0; i < 24; i++) b.update(0.025, player, true, false, true);
    expect(b.state).toBe("chase");
    b.position.copyFrom(player.add(new Vector3(0, 0, -0.4)));
    b.update(0.02, player, true, false, false);
    expect(b.state).not.toBe("caught");
    b.update(0.02, player, true, false, true);
    expect(b.state).toBe("caught");
  });
  it("uses a forward view cone, shorter crouched sight and longer lamp visibility", () => {
    const b = new EarlyStealthBrain();
    expect(b.sees(b.position.add(new Vector3(0, 0, -3)), true, false, true)).toBe(false);
    expect(b.sees(b.position.add(new Vector3(0, 0, 7)), false, true, true)).toBe(false);
    expect(b.sees(b.position.add(new Vector3(0, 0, 12)), true, true, true)).toBe(true);
  });
  it("hears running beyond crouching range and loses a chase after cover hides the player", () => {
    const b = new EarlyStealthBrain(),
      player = b.position.add(new Vector3(0, 0, 5));
    b.hear(player, 0.12);
    expect(b.state).toBe("patrol");
    b.hear(player, 1);
    expect(b.state).toBe("investigate");
    b.state = "chase";
    b.suspicion = 1;
    b.update(0.1, player, true, false, true);
    for (let i = 0; i < 400; i++) b.update(0.025, player, false, true, false);
    expect(b.state).toBe("patrol");
  });
  it("routes around supplied solid cover bounds", () => {
    const n = new RoadNavigation([{ minX: -3.6, maxX: -1.7, minZ: 48, maxZ: 49.3 }]),
      from = new Vector3(-2.6, 0, 51),
      to = new Vector3(-2.6, 0, 46);
    expect(n.clear(from, to)).toBe(false);
    const path = n.path(from, to);
    expect(path.length).toBeGreaterThan(1);
    let last = from;
    for (const next of path) {
      expect(n.clear(last, next)).toBe(true);
      last = next;
    }
    expect(last.equals(to)).toBe(true);
  });
  it("keeps the later patrol on the open gate path without phantom cart colliders", () => {
    const b = new EarlyStealthBrain();
    for (let i = 0; i < 1500; i++) {
      b.update(0.025, new Vector3(0, 0, -2), false, true, true);
      expect(b.position.z).toBeGreaterThanOrEqual(11.7);
      expect(b.position.z).toBeLessThanOrEqual(24.3);
      expect(b.state).toBe("patrol");
    }
    expect(b.navigation.obstacles).toHaveLength(0);
  });
});
