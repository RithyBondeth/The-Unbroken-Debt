# src

Game source code, organised as in the Technical Design Document (sections 2–3). Systems are generic; episodes are data plus a few sequence scripts.

| Folder       | Responsibility                                                                                         |
| ------------ | ------------------------------------------------------------------------------------------------------ |
| `main.ts`    | Boot: WebGPU check, engine, game start                                                                 |
| `core/`      | Game, event bus, flags, area loading, level building from glTF extras, time, localisation              |
| `player/`    | Character controller, camera rig, interaction ray, first-person hands                                  |
| `systems/`   | Inventory, sketchbook, lamp, matches, upkeep timers, hiding, checkpoints, saves, settings, night count |
| `ai/`        | Perception, noise, state machines; `entities/` holds one file per spirit type                          |
| `sequences/` | Sequencer runtime and shared helper actions for scripted scenes                                        |
| `audio/`     | Audio engine, buses, ambience zones, cue library                                                       |
| `render/`    | Engine creation, post-processing, quality presets; `materials/` for node materials                     |
| `ui/`        | `diegetic/` (sketchbook pages, gauges) and `html/` (menus, requirements page, base styles)             |
| `episodes/`  | One folder per episode: `index.ts`, `sequences.ts` and `data/` (items, notes, entities)                |
| `data/`      | Shared definitions and `strings/` (en.json, km.json)                                                   |

Rules: no imports between systems (use the event bus and flags); beat IDs in comments next to the code that implements them (`// A2-06`).
