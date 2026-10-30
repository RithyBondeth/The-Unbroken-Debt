/** Matches the 2.4 second shriek: fast jaw opening, strained hold, breath release. */
export function krasueScreamMouth(age: number): number {
  if (!Number.isFinite(age) || age <= 0 || age >= 2.4) return 0;
  const attack = Math.min(1, age / 0.075);
  const release = Math.min(1, (2.4 - age) / 0.45);
  const smooth = (x: number) => x * x * (3 - 2 * x);
  return smooth(attack) * smooth(release) * (0.97 + Math.sin(age * 53) * 0.03);
}
