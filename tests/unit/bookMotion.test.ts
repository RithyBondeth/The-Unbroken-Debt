import { expect, it } from "vitest";
import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { bookTurnFrame, readingFrame } from "../../src/ui/diegetic/BookMotion";
import { BOOK } from "../../src/ui/diegetic/bookGeometry";

it("reaches and pinches before lifting, then releases before returning to the grip", () => {
  for (const direction of [-1, 1] as const) {
    const rest = bookTurnFrame({ progress: 0, direction });
    const contact = bookTurnFrame({ progress: 0.2, direction });
    const carry = bookTurnFrame({ progress: 0.48, direction });
    const done = bookTurnFrame({ progress: 1, direction });
    expect(rest.carry).toBe(0);
    expect(contact.pageProgress).toBe(direction > 0 ? 0 : 1);
    expect(contact.pinch).toBeGreaterThan(0.6);
    expect(carry.wrist[1]).toBeGreaterThan(0.08);
    expect(carry.carry).toBe(1);
    expect(done.pinch).toBe(0);
    expect(done.carry).toBe(0);
    expect(done.pageProgress).toBe(direction > 0 ? 1 : 0);
    for (let i = 0; i <= 100; i++) {
      const frame = bookTurnFrame({ progress: i / 100, direction });
      expect(frame.wrist.every(Number.isFinite)).toBe(true);
      expect(frame.pinch).toBeLessThanOrEqual(frame.carry + 0.0001);
    }
  }
});

it("keeps the cover and page footer inside the real UI clearance at narrow and ultrawide aspects", () => {
  const fov = (75 * Math.PI) / 180;
  const rotation = Matrix.RotationYawPitchRoll(-0.025, -Math.PI / 2 + 0.29, 0.025);
  for (const [width, height, top, bottom] of [
    [1920, 1080, 72, 72],
    [2560, 1080, 72, 72],
    [878, 1080, 72, 96],
    [390, 700, 120, 140],
  ]) {
    const aspect = width / height;
    const pose = readingFrame(aspect, fov, true, top / height, bottom / height);
    const tanH = Math.tan(fov / 2),
      tanV = tanH / aspect;
    for (const x of [-BOOK.width - 0.012, BOOK.width + 0.012])
      for (const z of [-BOOK.height / 2 - 0.012, BOOK.height / 2 + 0.012]) {
        const point = Vector3.TransformCoordinates(new Vector3(x, 0.005, z), rotation);
        const px = 0.5 + (point.x - 0.006) / (2 * (pose.z + point.z) * tanH);
        const py = 0.5 - (point.y + pose.y) / (2 * (pose.z + point.z) * tanV);
        expect(px).toBeGreaterThanOrEqual(0.03 - 1e-6);
        expect(px).toBeLessThanOrEqual(0.97 + 1e-6);
        expect(py * height).toBeGreaterThanOrEqual(top - 1e-5);
        expect(py * height).toBeLessThanOrEqual(height - bottom + 1e-5);
      }
  }
});
