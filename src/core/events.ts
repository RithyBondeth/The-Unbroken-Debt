import type { FlagValue } from "./Flags";

export type LampState = "open" | "shuttered" | "out";

export interface Position {
  x: number;
  y: number;
  z: number;
}

/** Every event in the game. See the Technical Design Document, section 5. */
export type GameEvents = {
  "flag:changed": { key: string; value: FlagValue };
  "area:loaded": { areaId: string };
  "area:unloaded": { areaId: string };
  "interact:focus": { id: string };
  "interact:use": { id: string };
  "inventory:changed": { itemId: string; count: number };
  "lamp:state": { state: LampState };
  "lamp:oil": { level: number };
  "upkeep:warning": { id: string; stage: 1 | 2 };
  "upkeep:expired": { id: string };
  "player:step": { surface: string; loudness: number };
  "noise:made": { position: Position; loudness: number; source: string };
  "entity:state": { id: string; state: string };
  "player:caught": { by: string };
  "checkpoint:reached": { id: string };
  "sequence:start": { id: string };
  "sequence:end": { id: string };
  "choice:made": { id: string; option: string };
  "settings:changed": { key: string };
};
