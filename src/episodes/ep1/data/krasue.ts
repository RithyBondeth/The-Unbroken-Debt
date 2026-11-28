import { Vector3 } from "@babylonjs/core/Maths/math.vector";

export interface PaddyFlightPath {
  readonly id: string;
  /** Default organ glow bias: 0 = eerie emerald-green, 1 = blood-red. */
  readonly baseRedness: number;
  /** Waypoints drifting over the flooded rice paddy plots (Babylon metres). */
  readonly waypoints: readonly Vector3[];
}

/**
 * Flight routes of the Krasue (អាប) over Episode 1's flooded rice paddies (`farmLayout.FIELDS`)
 * and outer palms. Each route drifts low over the dikes, dips down toward the dark water to feed,
 * and rises back into the monsoon mist.
 */
export const KRASUE_PADDY_PATHS: readonly PaddyFlightPath[] = [
  {
    id: "west_paddies_green",
    baseRedness: 0.0,
    waypoints: [
      new Vector3(38, 3.6, 36),
      new Vector3(28, 2.4, 30),
      new Vector3(19, 1.85, 25),
      new Vector3(13, 2.6, 17),
      new Vector3(22, 2.1, 12),
      new Vector3(34, 3.2, 16),
      new Vector3(41, 4.4, 28),
    ],
  },
  {
    id: "east_paddies_red",
    baseRedness: 0.85,
    waypoints: [
      new Vector3(-39, 3.8, 34),
      new Vector3(-28, 2.3, 27),
      new Vector3(-19, 1.9, 21),
      new Vector3(-13, 2.8, 13),
      new Vector3(-24, 2.0, 14),
      new Vector3(-35, 3.4, 22),
      new Vector3(-42, 4.6, 32),
    ],
  },
  {
    id: "approach_crossing",
    baseRedness: 0.15,
    waypoints: [
      new Vector3(30, 3.4, 29),
      new Vector3(16, 2.4, 26),
      new Vector3(6, 3.2, 23),
      new Vector3(-8, 3.0, 21),
      new Vector3(-21, 2.1, 19),
      new Vector3(-34, 3.5, 25),
    ],
  },
  {
    id: "yard_edge_flyby",
    baseRedness: 0.92,
    waypoints: [
      new Vector3(24, 4.2, 14),
      new Vector3(15, 3.9, 4),
      new Vector3(11, 4.1, -9),
      new Vector3(14, 3.8, -19),
      new Vector3(26, 4.6, -12),
      new Vector3(35, 5.2, 8),
    ],
  },
];

/** Still exported for window sight/framing checks inside Yay Mey's room. */
export const KRASUE_WINDOWS = [
  {
    id: "west",
    center: new Vector3(6, 3.86, -13),
    normal: new Vector3(1, 0, 0),
    tangent: new Vector3(0, 0, 1),
  },
  {
    id: "south",
    center: new Vector3(4.5, 3.86, -11.44),
    normal: new Vector3(0, 0, 1),
    tangent: new Vector3(1, 0, 0),
  },
] as const;
export type KrasueWindow = (typeof KRASUE_WINDOWS)[number];

/** True when Sora is outdoors near the fields, track, or yard (exposed to paddy sky). */
export function exposedToPaddies(feet: { x: number; y: number; z: number }): boolean {
  // Indoors inside main house rooms or beneath roof shelter protects Sora
  const insideMainHouse = Math.abs(feet.x) < 8.4 && feet.z > -34.5 && feet.z < -9.5 && feet.y < 5.2;
  const insideKitchen = feet.x > 19.6 && feet.x < 28.4 && feet.z > -23 && feet.z < -15.2;
  const insideBarn = feet.x > -29.2 && feet.x < -20.8 && feet.z > -25.8 && feet.z < -19.2;
  return !insideMainHouse && !insideKitchen && !insideBarn;
}
