import type { Flags } from "../../../core/Flags";

/** A1-11b: the obstruction is a listening presence after the offering and vigil. */
export const PASSAGE_WARNING_SECONDS = 5;
export const PASSAGE_SECONDS = 34;

export function passageRequired(flags: Flags): boolean {
  return !flags.get("ep1.early.complete", false) && !flags.get("ep1.act2.started", false);
}

export function passageReady(flags: Flags, underTent: boolean, handsFree: boolean): boolean {
  return (
    passageRequired(flags) &&
    underTent &&
    handsFree &&
    flags.get("ep1.vigil.started", false) &&
    flags.get("ep1.betel.done", false) &&
    flags.get("ep1.incense.cyclePassed", false) &&
    (!flags.get("ep1.arrival.phoneFlow", false) || flags.get("ep1.arrival.matchesTaken", false))
  );
}
