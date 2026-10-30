import { readFileSync } from "node:fs";

/**
 * True when a Git LFS file is only its pointer (as in CI checkouts without LFS), so
 * tests that read the real binary can skip instead of failing.
 */
export function isLfsPointer(path: string): boolean {
  return readFileSync(path).subarray(0, 40).toString().startsWith("version https://git-lfs");
}
