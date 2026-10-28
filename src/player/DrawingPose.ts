import type { TransformNode } from "@babylonjs/core/Meshes/transformNode";
import { Matrix, Quaternion, Vector3 } from "@babylonjs/core/Maths/math.vector";
import authored from "../../art-source/characters/sora/sora-hands.drawing.json";

export const DRAWING_VIEW_RADIUS = 0.29;

/** Frame the roof strokes and grip, leaving space above the pencil. */
export function drawingFocus(paper: TransformNode): Vector3 {
  const m = 1 / Math.abs(paper.scaling.x || 1);
  return Vector3.TransformCoordinates(
    new Vector3(-0.025, 0.002, 0.09).scale(m),
    paper.computeWorldMatrix(true),
  );
}

/** Shared anatomical frame: palm faces the paper and the forearm leads back to Sora. */
export function drawingFrame(): {
  pen: Quaternion;
  hand: Quaternion;
  contact: Vector3;
} {
  const inclination = (15 * Math.PI) / 180;
  const fingerDirection = new Vector3(
    0.8 * Math.cos(inclination),
    -Math.sin(inclination),
    0.6 * Math.cos(inclination),
  );
  const palm = new Vector3(0, -1, 0);
  palm.subtractInPlace(fingerDirection.scale(Vector3.Dot(palm, fingerDirection))).normalize();
  const thumbAxis = Vector3.Cross(fingerDirection, palm).normalize();
  const basis = Matrix.Identity();
  Matrix.FromXYZAxesToRef(thumbAxis, fingerDirection, palm, basis);
  const handInPaper = Quaternion.FromRotationMatrix(basis);
  const nib = Vector3.FromArray(authored.nibDirection);
  // The imported studio has a mirrored root. The drawing hand compensates
  // that reflection, so contacts here use the original authored coordinates.
  const tailInPaper = Vector3.TransformNormal(nib.negate(), basis).normalize();
  const pen = Quaternion.Identity();
  Quaternion.FromUnitVectorsToRef(Vector3.Up(), tailInPaper, pen);
  const hand = Quaternion.Inverse(pen).multiply(handInPaper);
  const relative = Matrix.Identity();
  hand.toRotationMatrix(relative);
  const point = Vector3.FromArray(authored.contact);
  return { pen, hand, contact: Vector3.TransformNormal(point.scale(0.85), relative) };
}
