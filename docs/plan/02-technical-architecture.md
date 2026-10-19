# 2. Technical Architecture

## 2.1 Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | TypeScript (strict mode) | Catches errors early. Babylon.js is written in TypeScript |
| Build | Vite | Fast dev server, simple static build output |
| Engine | `@babylonjs/core` (ES modules, tree-shaken) | Import only what you use to keep the bundle small |
| Loaders | `@babylonjs/loaders` (glTF 2.0) | Draco/meshopt and KTX2 decoders loaded on demand |
| Rendering | WebGPU with automatic WebGL2 fallback | Detect support at startup, then create `WebGPUEngine` or `Engine` |
| Physics | Havok (`@babylonjs/havok`) | Character controller, collisions, triggers. WASM file loaded at startup |
| Audio | Babylon.js Audio Engine v2 (Web Audio API) | Spatial sound, buses, reverb sends. Unlocked on first click (browser autoplay rule) |
| UI | Babylon GUI on meshes (`AdvancedDynamicTexture.CreateForMesh`) + `DynamicTexture` | Diegetic sketchbook pages, lamp gauge. HTML only for menus/settings and loading screens |
| Navigation | Babylon navigation plugin (Recast navmesh) | Enemy pathing. Check the current docs for the recommended package |
| Storage | IndexedDB (small wrapper such as `idb-keyval`) | Save slots and settings |
| Tests | Vitest for game logic; Playwright for a smoke test that the game boots | No rendering tests; test state machines, inventory, save |
| Assets | Blender → glTF (`.glb`) → glTF-Transform (Draco or meshopt, KTX2/Basis) | Script this so one command rebuilds all assets |
| Hosting | Any static host (Cloudflare Pages, Netlify, GitHub Pages, itch.io) | Check each host's per-file size limit against your largest `.glb` |
| Source control | Git + Git LFS for binary sources (`.blend`, `.wav`, `.psd`) | Exported, compressed assets can live in normal Git or be built in CI |

## 2.2 Repository layout

```
/
├── docs/                    Design docs (PDFs), plan, beat sheets, art bible
├── art-source/              .blend, .kra, raw audio  (Git LFS)
├── tools/
│   └── build-assets.ts      glb optimisation + KTX2 conversion script
├── public/
│   └── assets/
│       ├── shared/          Lamp, hands, satchel, sketchbook, common sounds
│       └── ep1/             Episode 1 compressed .glb, .ktx2, .ogg/.mp3
├── src/
│   ├── main.ts              Boot: detect WebGPU, create engine, load menu
│   ├── core/                Engine wrapper, scene manager, asset loader, event bus, time
│   ├── player/              Controller, camera, head-bob, interaction raycast, hands
│   ├── systems/             Inventory, sketchbook, lamp, resources, stealth, save, settings
│   ├── ai/                  Perception (sight/hearing), state machines, entity types
│   ├── audio/               Audio engine setup, buses, ambience zones, cue library
│   ├── render/              Post-processing pipeline, materials, quality presets
│   ├── ui/                  Diegetic UI widgets, HTML menus
│   ├── episodes/
│   │   ├── ep1/             Ep1 scene setup, scripted events, puzzles, data (items, notes)
│   │   └── ...
│   └── data/                Shared item, note and dialogue definitions (JSON/TS)
└── tests/
```

## 2.3 Core architecture

**Principle: systems are generic; episodes are data plus a few scripts.**

```
          ┌──────────────────────────────┐
          │          Game (main)         │
          │  engine, scene manager, loop │
          └───────────────┬──────────────┘
                          │ event bus (typed events)
   ┌──────────┬───────────┼────────────┬─────────────┬───────────┐
   ▼          ▼           ▼            ▼             ▼           ▼
 Player   Inventory   Sketchbook   Lamp/Resources  Stealth/AI   Save
   │          │           │            │             │           │
   └──────────┴───────────┴─────┬──────┴─────────────┴───────────┘
                                ▼
                     Episode script (ep1/…)
            triggers, puzzles, scripted sequences, flags
```

- **Event bus:** Systems never call each other directly. The lamp emits `lamp:extinguished`; the AI system listens and lowers visibility. This keeps systems reusable across episodes.
- **Game flags:** One key-value store (`flags.set('ep1.gramophone.solved', true)`) holds all story progress. The save system serialises it. Endings in Episode 5 read flags set in Episodes 1–4.
- **Scripted sequences:** Write them as `async` functions (`await walkTo(...); await playSound(...); await waitForLook(...)`). This is readable and easy to change, so no visual scripting tool is needed.
- **State machines:** Entities and puzzles use small explicit state machines (`idle → patrol → investigate → chase → lose-track`). Plain TypeScript is enough; avoid adding a framework until it hurts.
- **Blender as level editor:** Mark triggers, spawn points, patrol nodes, interactables and audio zones with empties and custom properties in Blender. They export into glTF `extras`, and a loader turns them into game objects. Level changes then never touch code.

## 2.4 Scene and memory management

- Each episode is split into **areas** (for Ep1: studio, courtyard, house, under-house). Load each with `LoadAssetContainerAsync` and add or remove it from the scene as the player moves.
- Shared assets (lamp, hands, satchel, common sounds) stay loaded for the whole session.
- On area unload, dispose meshes, materials and textures explicitly. Check the Babylon Inspector's statistics panel for leaks during QA.
- Stream long audio (ambience, music) rather than decoding it fully into memory.

## 2.5 Rendering plan

| Feature | Approach |
|---|---|
| Lamp light | One point light with shadows (the player's lamp). The only dynamic shadow caster most of the time |
| Candles, oil lamps, incense | Unshadowed point lights with flicker, plus emissive meshes and glow. Babylon 9's clustered lighting is meant for many small lights; test it in spike S2 |
| Static lighting | Bake lightmaps or ambient occlusion in Blender for architecture. Cheap at runtime and looks better |
| Moonlight (Ep2) | One directional light with cascaded shadows, only where needed |
| Fog | Scene fog for distance; animated fog cards or particles near the player; a volumetric fog shader only if spike S7 shows it fits the budget (critical for Ep4) |
| Post-processing | `DefaultRenderingPipeline`: grain, chromatic aberration, vignette, bloom, colour grading (sepia LUT for Ep1) |
| Materials | PBR from glTF. Node Material Editor for special effects (entity shadow, wet surfaces, blood-on-map, glowing runes) |
| Quality presets | Low / Medium / High: shadow map size, post effects, render scale, light count. Auto-pick on first launch from a quick benchmark |

## 2.6 Performance budgets (from the proposal, made measurable)

| Budget | Target | How to check |
|---|---|---|
| Frame rate | 60 fps @ 1080p (discrete GPU); 30 fps @ 720p (integrated laptop GPU) | Babylon Inspector FPS; test on a real integrated-GPU laptop |
| Draw calls | ≤ 120 per frame | Inspector → Statistics. Use instancing and merged static meshes |
| Visible polygons | ≤ 150k | Inspector. Use LODs on large props |
| Initial download per episode | ≤ 85 MB | Network tab, cache disabled. First area must load in under 20 MB so the game starts quickly |
| Texture memory | Budget per area, for example ≤ 256 MB | KTX2 everywhere; 2K max for hero assets, 1K or 512 for props |
| JavaScript bundle | ≤ 3 MB gzipped | `vite build` report |

Define **two reference machines** on day one (for example, your main computer and a cheap integrated-GPU laptop) and test on both every week.

## 2.7 Save system

| Part | Design |
|---|---|
| What is saved | Episode, area, checkpoint ID, flags, inventory, sketchbook entries, resource levels, settings, ending-related counters (taboos broken, lore notes found) |
| When | Checkpoints at fixed safe moments (no free saving; it suits horror) plus on episode completion |
| Where | IndexedDB, 3 slots, versioned (`saveVersion: 1`) with migration functions for future changes |
| Save codes | JSON → compress → base64url, plus a checksum. Lets players carry progress between devices and browsers and into the next episode |
| Security note | Browser-side "encryption" cannot stop a determined player, because the key ships in the code. Treat save codes as **tamper-evident** (checksum), not secret. That is fine for a single-player game |

## 2.8 Browser and platform support

| Browser | Expected path |
|---|---|
| Chrome, Edge (Windows, macOS) | WebGPU |
| Safari (macOS 26+) | WebGPU; older macOS falls back to WebGL2 |
| Firefox | WebGPU on Windows and Apple Silicon Macs; WebGL2 elsewhere (Linux, Intel Mac) |
| Mobile | Not supported. Show a friendly message. The proposal targets desktop |

Always keep the WebGL2 path working. Run spike S8 again before release.

## 2.9 Input and accessibility (plan now, cheap to build early)

- Keyboard and mouse first; gamepad support through the Gamepad API (Babylon has a gamepad manager).
- Rebindable keys, mouse sensitivity, invert Y, field of view slider.
- Subtitles and captions for important sounds, which matters because the game relies heavily on audio cues. Add a visual cue option for players who are deaf or hard of hearing.
- Toggle options for head-bob, film grain and chromatic aberration (motion sickness and visual comfort).
- Brightness calibration screen.
- English plus Khmer text from the start (store all strings in data files; Khmer fonts need testing for correct shaping).
