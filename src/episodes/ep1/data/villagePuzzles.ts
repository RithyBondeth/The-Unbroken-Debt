import type { Flags } from "@/core/Flags";

/**
 * Pure data & deduction logic for Episode 1 Village's 4 interconnected puzzles & obstacles.
 * Coordinates are in Babylon world space (x = -Blender x, y = Blender z, z = -Blender y).
 */

/** Puzzle 1: Sealed Compound Gate 3-dial brass padlock code (Noodle 7 · Barber 4 · Moto 2). */
export const GATE_CODE = [7, 4, 2] as const;

/** Puzzle 4: Hall Pendulum Clock target time (deduced from village mourning + 20:12 motif). */
export const CLOCK_TARGET = { hour: 1, minute: 12 } as const;

/** Cursed times on the hall clock that chime 13× and unleash a Preay house haunt. */
export const CLOCK_CURSED_TIMES: readonly { hour: number; minute: number }[] = [
  { hour: 0, minute: 0 },
  { hour: 3, minute: 0 },
  { hour: 20, minute: 12 },
];

export type WardStationId = "neakta" | "stupas" | "ruin";
export type WardOfferingId = "well_water" | "sacred_thread" | "ward_marigold";
export type IncenseCount = 1 | 2 | 3;

export interface WardStationSpec {
  readonly id: WardStationId;
  readonly name: string;
  readonly hint: string;
  readonly expectedOffering: WardOfferingId;
  readonly expectedIncense: IncenseCount;
  readonly position: readonly [number, number];
}

/**
 * Puzzle 3: Three folklore ward stations around the compound.
 * Real Khmer cultural grounding:
 * - 3 incense sticks honour sacred guardians (Neak Ta) and family ancestors (Stupas).
 * - 1 incense stick is offered only to unquiet wandering dead (the burnt hearth of the ruin).
 * Confusing the sacred and unquiet counts provokes Preay.
 */
export const WARD_STATIONS: readonly WardStationSpec[] = [
  {
    id: "neakta",
    name: "Neak Ta Wayside Shrine",
    hint: "Stone inscription weathered by rain: “Cool water from the family well, three sticks for the land guardian.”",
    expectedOffering: "well_water",
    expectedIncense: 3,
    position: [2.55, 34.9],
  },
  {
    id: "stupas",
    name: "North Garden Ancestral Stupas",
    hint: "Faded lacquer tablet: “White cotton thread binds the bloodline; three sticks for the elders.”",
    expectedOffering: "sacred_thread",
    expectedIncense: 3,
    position: [25.0, -46.85],
  },
  {
    id: "ruin",
    name: "Ruined First House Hearth",
    hint: "Charred scratch on the fallen beam: “Marigolds for the nameless one left outside—never three sticks, only one.”",
    expectedOffering: "ward_marigold",
    expectedIncense: 1,
    position: [8.9, -47.8],
  },
];

/** Exact Babylon (x, z) placements for village puzzle props & obstacles (verified via Blender raycasts). */
export const PUZZLE_SPOTS = {
  /** Main farm gate barred by a chained 3-dial padlock across the cart track. */
  gate: [0, 40.0] as const,
  /** Side fence loose planks bound with red ward cord (risky crowbar bypass). */
  sideFence: [-7.5, 40.0] as const,
  /** Roadside Noodle Stall wooden veranda table (`Y = 1.45`) beside the oil lamp: Clue 1 calendar (7). */
  noodleClue: [-1.92, 57.56] as const,
  /** Roadside Barber Shop wooden veranda bench (`Y = 0.91`) beside the oil lamp: vintage valve radio -> 4 knocks. */
  barberRadio: [13.3, 46.15] as const,
  /** Roadside Barber Shop walkable interior between the two red barber chairs where Headless Ghost appears. */
  barberGhost: [11.7, 44.1] as const,
  /** Roadside Moto Shop walkable interior workbench (`Y = 0.48`): open kerosene ledger (Lot 2) & crowbar. */
  motoLedger: [12.45, 60.85] as const,
  motoCrowbar: [13.02, 60.82] as const,
  /** Detailed brick village well inside the south gate (village_well.py). */
  well: [-9.5, 33.0] as const,
  /** Behind the brick well curb where Headless Ghost peeks during a failed tug. */
  wellGhost: [-9.5, 31.6] as const,
  /** Counterweight laterite stone near the yard-to-byre track. */
  wellWeight: [-24.5, -2.2] as const,
  /** Iron grapple hook & rope on the servants' hut plank floor (`Y = 1.205`). */
  wellHook: [37.4, -36.6] as const,
  /** Torn right half of Kanha's betel drawing on the servants' hut floor crate (`Y = 1.205`). */
  tornDrawing: [38.2, -37.2] as const,
  /** White cotton thread bundle on the kitchen house floor (`Y = 2.505`). */
  sacredThread: [22.2, -17.5] as const,
  /** Fresh marigold offering dish beside the front yard entrance. */
  wardMarigold: [-3.4, -3.5] as const,
  /** 1930s colonial wall pendulum clock mounted flush on parlour wainscoting wall (`X = -3.00`). */
  hallClock: [-3.09, -13.5] as const,
} as const;

export type WellPhase = "broken" | "rigged" | "pull1" | "tug_danger" | "pull3" | "complete";

export interface GateCheckResult {
  solved: boolean;
  matchedCount: number;
}

export function checkGateCode(digits: readonly [number, number, number]): GateCheckResult {
  let matchedCount = 0;
  for (let i = 0; i < 3; i++) if (digits[i] === GATE_CODE[i]) matchedCount++;
  return { solved: matchedCount === 3, matchedCount };
}

export function checkWardStation(
  stationId: WardStationId,
  offering: WardOfferingId,
  incense: IncenseCount,
): "correct" | "wrong_incense" | "wrong_offering" {
  const spec = WARD_STATIONS.find((s) => s.id === stationId);
  if (!spec) return "wrong_offering";
  if (offering === spec.expectedOffering && incense === spec.expectedIncense) return "correct";
  if (offering === spec.expectedOffering) return "wrong_incense";
  return "wrong_offering";
}

export type ClockDialResult = "solved" | "cursed" | "wrong";

export function checkClockDial(hour: number, minute: number): ClockDialResult {
  const h = ((hour % 24) + 24) % 24;
  const m = ((minute % 60) + 60) % 60;
  if (h === CLOCK_TARGET.hour && m === CLOCK_TARGET.minute) return "solved";
  if (CLOCK_CURSED_TIMES.some((c) => c.hour === h && c.minute === m)) return "cursed";
  return "wrong";
}

/**
 * Pure state machine for the Brick Well 4-stage risk haul (Puzzle 2).
 * Pulling during `tug_danger` (or with an open lamp shining down the shaft) causes the
 * unseen hand below to yank the bucket back down. Waiting still with lamp out releases it.
 */
export class WellMechanism {
  phase: WellPhase = "broken";
  tugRemaining = 0;
  hasWeight = false;
  hasHook = false;
  tugFailures = 0;

  restore(flags: Flags): void {
    this.hasWeight = flags.get("ep1.puzzle.well.weightAttached", false);
    this.hasHook = flags.get("ep1.puzzle.well.hookAttached", false);
    if (flags.get("ep1.puzzle.well.complete", false)) {
      this.phase = "complete";
    } else if (this.hasWeight && this.hasHook) {
      this.phase = "rigged";
    } else {
      this.phase = "broken";
    }
  }

  attachParts(
    haveWeight: boolean,
    haveHook: boolean,
  ): "need_both" | "need_weight" | "need_hook" | "rigged" {
    if (haveWeight) this.hasWeight = true;
    if (haveHook) this.hasHook = true;
    if (this.hasWeight && this.hasHook) {
      if (this.phase === "broken") this.phase = "rigged";
      return "rigged";
    }
    if (!this.hasWeight && !this.hasHook) return "need_both";
    return this.hasWeight ? "need_hook" : "need_weight";
  }

  /** Called when Sora pulls the bamboo sweep (`E`). */
  pull(lampOpen: boolean): "not_ready" | "rising" | "tug_started" | "yanked_back" | "hauled" {
    if (this.phase === "broken") return "not_ready";
    if (this.phase === "complete") return "hauled";
    if (this.phase === "rigged") {
      this.phase = "pull1";
      return "rising";
    }
    if (this.phase === "pull1") {
      // Mid-shaft: water goes quiet and something grabs the bucket
      this.phase = "tug_danger";
      this.tugRemaining = 4.2;
      return "tug_started";
    }
    if (this.phase === "tug_danger") {
      // Pulling while something is holding the rope yanks it back down!
      this.tugFailures++;
      this.phase = "rigged";
      this.tugRemaining = 0;
      return "yanked_back";
    }
    if (this.phase === "pull3") {
      if (lampOpen) {
        // Shining the open flame straight down before clearing the rim still startles it once
        this.tugFailures++;
        this.phase = "tug_danger";
        this.tugRemaining = 3.2;
        return "yanked_back";
      }
      this.phase = "complete";
      return "hauled";
    }
    return "rising";
  }

  /** Ticks the tension window; only drains while Sora keeps her lamp out and holds still. */
  update(dt: number, lampOpen: boolean, movingFast: boolean): "none" | "released" {
    if (this.phase !== "tug_danger") return "none";
    if (!lampOpen && !movingFast) {
      this.tugRemaining -= dt;
      if (this.tugRemaining <= 0) {
        this.tugRemaining = 0;
        this.phase = "pull3";
        return "released";
      }
    }
    return "none";
  }
}

/** Counts how many of the 3 ancestral ward stations are solved. */
export function solvedWardCount(flags: Flags): number {
  let n = 0;
  for (const s of WARD_STATIONS) if (flags.get(`ep1.puzzle.ward.${s.id}`, false)) n++;
  return n;
}
