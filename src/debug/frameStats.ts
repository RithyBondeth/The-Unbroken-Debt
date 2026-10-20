export interface FrameSummary {
  frames: number;
  avgMs: number;
  avgFps: number;
  /** Frame time that 99% of frames beat. */
  p99Ms: number;
  /** "1% low": the average fps of the slowest 1% of frames. */
  low1Fps: number;
  maxMs: number;
}

/** Summarises a list of frame times (milliseconds). Pure, so it can be unit-tested. */
export function summarizeFrames(frameMs: readonly number[]): FrameSummary {
  const n = frameMs.length;
  if (n === 0) return { frames: 0, avgMs: 0, avgFps: 0, p99Ms: 0, low1Fps: 0, maxMs: 0 };

  const sorted = [...frameMs].sort((a, b) => a - b);
  const total = sorted.reduce((sum, ms) => sum + ms, 0);
  const avgMs = total / n;

  const p99Index = Math.min(n - 1, Math.ceil(n * 0.99) - 1);
  const slowestCount = Math.max(1, Math.floor(n * 0.01));
  const slowest = sorted.slice(n - slowestCount);
  const slowestAvg = slowest.reduce((sum, ms) => sum + ms, 0) / slowestCount;

  return {
    frames: n,
    avgMs,
    avgFps: 1000 / avgMs,
    p99Ms: sorted[p99Index],
    low1Fps: 1000 / slowestAvg,
    maxMs: sorted[n - 1],
  };
}

export interface BudgetResult {
  pass: boolean;
  reasons: string[];
}

/**
 * Checks a run against the 60 fps target (Development Plan, Spike S2).
 * The browser caps frame rate at the display refresh, so GPU time is the
 * main measure when it is available; frame time catches CPU-bound stalls.
 */
export function checkSixtyFps(summary: FrameSummary, gpuAvgMs: number | null): BudgetResult {
  const reasons: string[] = [];
  if (summary.avgFps < 58) reasons.push(`average ${summary.avgFps.toFixed(1)} fps is below 58`);
  if (summary.low1Fps < 45) reasons.push(`1% low ${summary.low1Fps.toFixed(1)} fps is below 45`);
  if (gpuAvgMs !== null && gpuAvgMs > 16.6) {
    reasons.push(`GPU time ${gpuAvgMs.toFixed(2)} ms is over the 16.6 ms budget`);
  }
  return { pass: reasons.length === 0, reasons };
}
