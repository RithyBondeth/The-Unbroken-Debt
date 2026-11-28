/**
 * Development only: places to start Act I for testing, chosen by the URL
 * (`?start=act1&at=hall`). Game coordinates (Blender x, y → -x, -y), on the house's floor
 * (2.5 m); `yaw` faces Sora the way given.
 */
export const DEV_SPOTS: Readonly<Record<string, { feet: [number, number, number]; yaw: number }>> =
  {
    /** The front doors, looking into the hall. */
    front: { feet: [0, 2.5, -11.0], yaw: Math.PI },
    /** The hall, facing the altar and its two narrow doors. */
    hall: { feet: [0, 2.5, -13.0], yaw: Math.PI },
    /** The washing room behind the altar, facing its cord of cloths. */
    washing: { feet: [-1.4, 2.5, -18.6], yaw: 2.39 },
    /** Yay Mey's room, facing the Krasue's west window. */
    yaymey: { feet: [4.4, 2.5, -13.0], yaw: Math.PI / 2 },
    /** The loom room, facing the silk on its pole. */
    loom: { feet: [4.6, 2.5, -18.9], yaw: 0.62 },
    /** The long corridor, looking north past Sok's study to the nailed back door. */
    corridor: { feet: [0, 2.5, -24.0], yaw: Math.PI },
    /** Sok's study, facing the photograph over his cabinet. */
    study: { feet: [4.2, 2.5, -25.6], yaw: 0.47 },
    /** South compound gate, directly facing the chained 3-dial brass padlock. */
    gate: { feet: [0, 0, 41.3], yaw: Math.PI },
    /** Roadside laterite street facing the Noodle, Barber, and Moto shops. */
    shops: { feet: [0, 0.1, 52.0], yaw: 0 },
    /** Detailed brick village well inside the south gate. */
    well: { feet: [-7.9, 0, 33.4], yaw: -Math.PI / 2 },
    /** Track overlook facing west across the flooded rice paddies (Krasue flight path). */
    paddies: { feet: [4.0, 0, 30.0], yaw: 1.2 },
    /** Upstairs hall directly facing the stopped 20:12 wall pendulum clock. */
    clock: { feet: [-2.4, 2.5, -13.5], yaw: -Math.PI / 2 },
  };
