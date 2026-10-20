import { assertSave, SAVE_VERSION, SaveError, type SaveData } from "./SaveData";

/**
 * `MIGRATIONS[n]` turns a version-n save into version n + 1 (Technical Design
 * Document, section 13). Version 1 is the first, so the list starts empty; add
 * an entry whenever `SAVE_VERSION` goes up, and never change an old one.
 */
export const MIGRATIONS: Record<
  number,
  (save: Record<string, unknown>) => Record<string, unknown>
> = {};

/**
 * Upgrades any older save to the current version and checks it. Saves from a
 * newer game (played on another device with a later build) are refused rather
 * than guessed at.
 */
export function migrate(raw: unknown, migrations = MIGRATIONS, current = SAVE_VERSION): SaveData {
  if (typeof raw !== "object" || raw === null)
    throw new SaveError("data", "Save data is damaged: not an object");
  let save = { ...(raw as Record<string, unknown>) };
  let version = save.saveVersion;
  if (!Number.isInteger(version)) throw new SaveError("data", "Save data is damaged: no version");
  if ((version as number) > current) {
    throw new SaveError(
      "version",
      `This save comes from a newer version of the game (save format ${String(version)})`,
    );
  }
  while ((version as number) < current) {
    const step = migrations[version as number];
    if (!step) throw new SaveError("version", `No upgrade from save format ${String(version)}`);
    save = step(save);
    version = (version as number) + 1;
    save.saveVersion = version;
  }
  assertSave(save);
  return save;
}
