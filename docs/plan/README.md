# Development Plan — Boon Sop: The Unbroken Debt

This folder turns the proposal and the five episode design documents (`docs/*.pdf`) into a plan a **solo developer** can execute. Read the files in order.

| # | Document | What it answers |
|---|---|---|
| 1 | [01-scope-and-roadmap.md](01-scope-and-roadmap.md) | What to build first, in what order, how long it realistically takes, and what to cut |
| 2 | [02-technical-architecture.md](02-technical-architecture.md) | Stack, project structure, engine systems, performance budgets, save system |
| 3 | [03-game-systems.md](03-game-systems.md) | Every gameplay system across all 5 episodes, which episode introduces it, and how it is built once and reused |
| 4 | [04-assets-and-resources.md](04-assets-and-resources.md) | Episode 1 asset list, where each asset comes from, tools to install, learning and cultural research sources |
| 5 | [05-open-questions.md](05-open-questions.md) | Story and design gaps that must be decided before or during Episode 1 |

## Decisions already made

| Decision | Choice | Why |
|---|---|---|
| Team | Solo developer | Plan is sized for one person; art and audio come from libraries plus targeted custom work |
| Engine | **Babylon.js** (code-first, TypeScript) | Mature WebGPU + WebGL2 fallback from one codebase, built-in Havok physics, spatial audio engine, inspector, no editor lock-in |
| Assets | Mix of libraries + custom Blender work | Generic props from CC0/paid libraries; Khmer-specific hero assets (stilt house, funeral tent, coffin, stupas) made custom |
| Plan format | Markdown in this repo | Versioned next to the code |
| First milestone | **Episode 1 vertical slice**, released on its own | Proves the tech, the tone and the pipeline before committing to four more episodes |

## Versions checked (October 2026)

| Package | Version |
|---|---|
| `@babylonjs/core`, `@babylonjs/loaders` | 9.31.0 |
| `@babylonjs/havok` | 1.3.14 |
| `vite` | 8.3.4 |
| `typescript` | 7.0.2 |
| Node.js (installed locally) | 26.8.2 |

Pin exact versions in `package.json` when the project is scaffolded and upgrade deliberately, not automatically.
