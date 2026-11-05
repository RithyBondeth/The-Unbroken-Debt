export interface WaterExposure {
  depth: number;
  rain: boolean;
  warm: boolean;
  sheltered: boolean;
}
/** Active seconds only. Reading, lost pointer capture and background tabs freeze survival. */
export class WaterSurvival {
  wetness = 0;
  warmth = 1;
  update(dt: number, exposure: WaterExposure): void {
    dt = Math.max(0, Math.min(0.1, dt));
    const wet = exposure.depth > 0.08;
    this.wetness = Math.max(
      0,
      Math.min(
        1,
        this.wetness +
          dt *
            (exposure.warm
              ? -0.065
              : wet
                ? 0.045
                : exposure.rain && !exposure.sheltered
                  ? 0.012
                  : -0.003),
      ),
    );
    this.warmth = Math.max(
      0,
      Math.min(
        1,
        this.warmth + dt * (exposure.warm ? 0.045 : -this.wetness * (wet ? 0.0035 : 0.0015)),
      ),
    );
  }
  get shivering(): boolean {
    return this.warmth < 0.35;
  }
  get collapsed(): boolean {
    return this.warmth <= 0;
  }
}
