# src

Game source code, organised as in the Technical Design Document (sections 2–3). Systems are generic; episodes are data plus a few sequence scripts.

| Folder      | Responsibility                                                                                                       |
| ----------- | -------------------------------------------------------------------------------------------------------------------- |
| `main.ts`   | Boot: WebGPU check, engine, game start                                                                               |
| `core/`     | Game, event bus, flags, area loading, level building from glTF extras, physics                                       |
| `player/`   | Character controller, camera, first-person hands (Sora's and Chea's), held lamp, telephone                           |
| `systems/`  | Interaction, inventory, lamp and lantern equipment, upkeep timers, checkpoints and saves                             |
| `audio/`    | Audio engine, footsteps, dread score; `sounds/` holds the synthesised sound banks every episode shares               |
| `render/`   | Engine creation, device check, quality presets, post-processing, mist, wind; `weather/` (rain, lightning, storm sky) |
| `shared/`   | Gameplay pieces more than one episode uses: relic crafting, the ancestor shadow figure, `cinematics/`                |
| `ui/`       | `diegetic/` (sketchbook), `html/` (menus, story UI, resolution screen) and `notebook/`                               |
| `episodes/` | One folder per episode (`ep1/`, `ep2/`, `ep3/`): scenes, entities, `data/` and episode-only `audio/`                 |
| `data/`     | Shared definitions and `strings/` (en.json, km.json)                                                                 |
| `debug/`    | Performance overlay (F3) and development screenshots                                                                 |
| `spikes/`   | Phase 1 S4 spatial-audio listening test (`?spike=s4`)                                                                |

Rules:

- No imports between systems (use the event bus and flags). Beat IDs go in comments next to the code that implements them (`// A2-06`).
- An episode may import from any shared folder, never from another episode. When a second episode needs something, move it to `shared/`, `render/`, `audio/` or `player/`.
- Imports: relative inside a folder area (one episode, or one top-level folder); `@/` (for `src/`) across areas, e.g. `import { Game } from "@/core/Game"`.
- File names: `PascalCase.ts` when the file is named after the class or type it exports (`Lamp.ts`, `DeviceProfile.ts`); `camelCase.ts` for modules of functions or data (`physics.ts`, `nightSounds.ts`). Unit tests mirror the module name (`qualityPresets.test.ts`).
