# 🕯️ Boon Sop: The Unbroken Debt (បុណ្យសព៖ បំណុលមិនដាច់)

> **A 3D First-Person Atmospheric Survival Horror Game for the Web**  
> *Set in 1932 French-Colonial Cambodia*

![Platform](https://img.shields.io/badge/Platform-Web_Browser-blue)
![Graphics API](https://img.shields.io/badge/Graphics-WebGPU-green)
![Engine](https://img.shields.io/badge/Engine-Babylon.js-orange)
![Genre](https://img.shields.io/badge/Genre-Survival_Horror-red)
![Code License](https://img.shields.io/badge/Code-MIT-lightgrey)
![Content](https://img.shields.io/badge/Content-All_rights_reserved-lightgrey)

---

## 📌 About The Project

**Boon Sop: The Unbroken Debt** is an episodic 3D first-person survival horror game running directly in modern web browsers without installation. Step into the shoes of **Sora**, a 24-year-old illustrator from Phnom Penh, as she returns to rural Cambodia to break an ancient ancestral debt tied to a land guardian spirit (*Neak Ta*).

### 🎮 Core Features
* **Zero Installation:** Play in Chrome, Edge, Safari or Firefox via **WebGPU**, scaling from integrated-graphics laptops (Low) up to gaming PCs (Ultra).
* **Diegetic 3D UI:** No screen HUD. Manage maps, notes, and inventory through Sora's physical 3D satchel and sketchbook.
* **Stealth & Cultural Taboos:** Dodge supernatural entities using spatial audio, visual cones, and traditional cultural rules.
* **Resource Management:** Balance kerosene oil levels, match supplies, and lamp shutter controls to survive the dark.
* **Cross-Episode Persistence:** Save game states locally using native browser `IndexedDB` and portable save codes.

## 🖥️ System Requirements

| | Minimum | Recommended | High-end |
|---|---|---|---|
| GPU | Integrated: Intel Iris Xe / AMD Radeon 680M / Apple M1 / Snapdragon X | NVIDIA RTX 2060 / AMD RX 5700 / Apple M1 Pro | NVIDIA RTX 3070 / AMD RX 6800 / Apple M2 Pro |
| Memory | 8 GB | 16 GB | 16–32 GB |
| Quality | Low, up to 900p with dynamic resolution | Medium, 1080p at 60 fps | High or Ultra, 1440p at 60 fps |
| Browser | WebGPU required: current Chrome or Edge; Safari on macOS 26+; Firefox on Windows or Apple Silicon | | |

The game picks a starting preset from the graphics adapter and lowers the render resolution on the fly when a frame runs over budget. Any laptop or desktop with WebGPU can play; phones and tablets (including iPad) are not supported in Episode 1. The reference test machine is a MacBook Pro M1 Pro.

## 🚀 Getting Started

Requires [Node.js](https://nodejs.org) 20+ and a WebGPU browser. Before adding art or audio files, install [Git LFS](https://git-lfs.com) (`git lfs install`).

```bash
npm install
```

```bash
npm run dev
```

| Command | What it does |
|---|---|
| `npm run dev` | Start the development server at http://localhost:5173 |
| `npm run build` | Type-check and build for production into `dist/` |
| `npm test` | Run the unit tests |
| `npm run typecheck` | Type-check only |
| `npm run lint` | Lint with ESLint |
| `npm run check` | Everything CI runs: type-check, lint, tests, build |
| `npm run format` | Format the code with Prettier |
| `npm run assets` | Optimise Blender exports from `art-export/` into `public/assets/` (needs KTX-Software) |
| `npm run docs` | Rebuild the design PDFs from `docs/src/` (needs Google Chrome) |

## 🗂️ Project Structure

```
.
├── src/                 Game source code (TypeScript, Babylon.js) — see src/README.md
│   ├── main.ts          Boot: device check, engine, game start
│   ├── core/            Game, event bus, flags, loading, localisation
│   ├── player/          Controller, camera, interaction, hands
│   ├── systems/         Inventory, sketchbook, lamp, saves, settings …
│   ├── ai/              Perception, state machines, spirit entities
│   ├── sequences/       Scripted scenes
│   ├── audio/           Audio engine, buses, ambience
│   ├── render/          Engine, device check, quality presets, dynamic resolution, post-processing
│   ├── ui/              Diegetic UI and HTML menus
│   ├── episodes/ep1/    Episode 1 scripts and data
│   ├── data/            Shared definitions and strings (en, km)
│   ├── debug/           Performance overlay (F3) and benchmark
│   └── spikes/          Phase 1 technical spikes (?spike=s1, ?spike=s2)
├── tests/unit/          Unit tests (Vitest)
├── public/              Static files served as-is
│   ├── assets/          Optimised game assets (shared/, ep1/) — Git LFS
│   └── fonts/           Ubuntu and Preah Vihear, with licences
├── art-source/          Editable art: blender/, textures/, audio/ — Git LFS
├── art-export/          Unoptimised Blender exports (not committed)
├── tools/               build-assets.mjs, build-docs.sh
├── .github/workflows/   CI: type-check, lint, test, build on every push
└── docs/                Design documents (pdf/), their sources (src/) and production tracking
```

## 📚 Documentation

| No. | Document |
|---|---|
| 00 | [Project Proposal](docs/pdf/00-Project-Proposal.pdf) |
| 01 | [Episode 1 · The House of Mourning](docs/pdf/01-Episode-1-The-House-of-Mourning.pdf) |
| 02 | [Episode 2 · The Whispering Pagoda](docs/pdf/02-Episode-2-The-Whispering-Pagoda.pdf) |
| 03 | [Episode 3 · The Drowned Village](docs/pdf/03-Episode-3-The-Drowned-Village.pdf) |
| 04 | [Episode 4 · The Rubber Plantation](docs/pdf/04-Episode-4-The-Rubber-Plantation.pdf) |
| 05 | [Episode 5 · The Sunken Sanctuary](docs/pdf/05-Episode-5-The-Sunken-Sanctuary.pdf) |
| 06 | [Development Plan](docs/pdf/06-Development-Plan.pdf) |
| 07 | [Story Bible](docs/pdf/07-Story-Bible.pdf) |
| 08 | [Episode 1 Beat Sheet and Level Layout](docs/pdf/08-Episode-1-Beat-Sheet-and-Level-Layout.pdf) |
| 09 | [Art Bible](docs/pdf/09-Art-Bible.pdf) |
| 10 | [Episode 1 Script and Text](docs/pdf/10-Episode-1-Script.pdf) |
| 11 | [Technical Design Document](docs/pdf/11-Technical-Design-Document.pdf) |
| 12 | [Controls and Interface](docs/pdf/12-Controls-and-Interface.pdf) |
| 13 | [Audio Design Document](docs/pdf/13-Audio-Design-Document.pdf) |
| 14 | [Cultural Guide and Glossary](docs/pdf/14-Cultural-Guide-and-Glossary.pdf) |
| 15 | [Playtest Plan](docs/pdf/15-Playtest-Plan.pdf) |
| — | [Asset tracker](docs/production/asset-tracker.csv) (spreadsheet) |

See [docs/README.md](docs/README.md) for the folder layout and how to rebuild the PDFs.

## ⚖️ License

- **Code** (`src/`, `tests/`, `tools/`, configuration): [MIT License](LICENSE).
- **Content** (story, characters, design documents, art, audio, branding): © 2026 Rithy Bondeth, all rights reserved. See [LICENSE-CONTENT.md](LICENSE-CONTENT.md).
- Fonts and third-party assets keep their own licences.
