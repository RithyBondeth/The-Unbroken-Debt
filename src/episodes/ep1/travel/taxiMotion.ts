/** Distance is an integral of speed, so scenery resumes at exactly the same position. */
export function taxiDistance(seconds: number): number {
  const t = Math.max(0, Math.min(72, seconds)),
    braking = Math.max(0, t - 62);
  return 6.8 * Math.min(t, 62) + 6.8 * (braking - (braking * braking) / 10 + braking ** 3 / 300);
}
export function taxiSpeed(seconds: number): number {
  return 6.8 * (1 - Math.max(0, Math.min(10, seconds - 62)) / 10) ** 2;
}
export function taxiWiperAngle(seconds: number): number {
  return -0.07 + Math.sin((seconds * Math.PI * 2) / 1.8) * 0.83;
}
/** Shared with build-taxi.py: metres along the complete curved route. */
export function taxiRoadX(z: number): number {
  return 3.8 * Math.sin(z * 0.018) + 2.2 * Math.sin(z * 0.037);
}
export function taxiRoadHeading(z: number): number {
  return Math.atan(3.8 * 0.018 * Math.cos(z * 0.018) + 2.2 * 0.037 * Math.cos(z * 0.037));
}
/** Inverse vehicle transform keeps the passenger seated while the car follows the road. */
export function taxiRoadPose(distance: number) {
  const x = taxiRoadX(distance),
    yaw = taxiRoadHeading(distance),
    c = Math.cos(yaw),
    s = Math.sin(yaw);
  return { x: -x * c + distance * s, z: -x * s - distance * c, yaw: -yaw };
}

/** Keep both look directions beyond the 60 m far plane; disable only invisible route chunks. */
export function taxiRouteChunkVisible(minZ: number, maxZ: number, distance: number): boolean {
  return maxZ >= distance - 80 && minZ <= distance + 80;
}
