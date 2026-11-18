// Written by tools/characters/build-preay.py: the Preay's clips (seconds), her walking
// pace at 1x (m/s) and the walk's heel strikes (seconds into the cycle).
export const PREAY_CLIPS = {
  stand: { seconds: 4.333 },
  walk: { seconds: 2.467, speed: 0.808, strikes: [0.067, 0.667, 1.3, 1.933] },
  hurry: { seconds: 2.033, speed: 1.084, strikes: [0.0, 0.367, 0.767, 1.067, 1.4, 1.633, 1.867] },
  reach: { seconds: 2.0 },
} as const;
