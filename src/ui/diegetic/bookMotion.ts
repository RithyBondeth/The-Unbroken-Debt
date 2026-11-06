import { Matrix, Vector3 } from "@babylonjs/core/Maths/math.vector";
import { BOOK } from "./bookGeometry";
import { leafProfile } from "./leafCurve";

export interface BookTurnState {
  progress: number;
  direction: -1 | 1;
}
const ease = (a: number, b: number, t: number) => {
  const x = Math.min(1, Math.max(0, (t - a) / (b - a)));
  return x * x * (3 - 2 * x);
};

/** Reach and pinch before the leaf moves; let go before the hand returns. */
export function bookTurnFrame(turn: BookTurnState) {
  const t = Math.min(1, Math.max(0, turn.progress));
  const page = ease(0.22, 0.82, t);
  const reach = ease(0, 0.2, t);
  const release = ease(0.62, 0.86, t);
  const carry = reach * (1 - release);
  const pinch = ease(0.12, 0.25, t) * (1 - ease(0.6, 0.75, t));
  const pageProgress = turn.direction > 0 ? page : 1 - page;
  const [edgeX, edgeY] = leafProfile(pageProgress, BOOK.width, 28).at(-1)!;
  return {
    pageProgress,
    carry,
    pinch,
    // Wrist remains outside the fingertip contact on the moving lower corner.
    wrist: [edgeX + turn.direction * 0.035, edgeY + 0.012, -0.123] as const,
    contact: [edgeX, edgeY + BOOK.pageY + 0.001, -0.075] as const,
    curl: Math.sin(page * Math.PI),
    settle: Math.sin(t * Math.PI),
  };
}

/** Fit every cover corner between the real UI bounds, including wide horizontal-FOV views. */
export function readingFrame(
  aspect: number,
  fov: number,
  horizontal: boolean,
  top: number,
  bottom: number,
) {
  const tanH = Math.tan(fov / 2) * (horizontal ? 1 : aspect);
  const tanV = Math.tan(fov / 2) / (horizontal ? aspect : 1);
  const room = Math.max(0.2, 1 - top - bottom);
  const rotation = Matrix.RotationYawPitchRoll(-0.025, -Math.PI / 2 + 0.29, 0.025);
  let distance = 0.25;
  for (const x of [-BOOK.width - 0.012, BOOK.width + 0.012])
    for (const z of [-BOOK.height / 2 - 0.012, BOOK.height / 2 + 0.012]) {
      const point = Vector3.TransformCoordinates(new Vector3(x, 0.005, z), rotation);
      distance = Math.max(
        distance,
        Math.abs(point.x - 0.006) / (0.94 * tanH) - point.z,
        (point.y / tanV - (1 - 2 * top) * point.z) / room,
        (-point.y / tanV + (-1 + 2 * bottom) * point.z) / room,
      );
    }
  return { y: (bottom - top) * distance * tanV, z: distance };
}
