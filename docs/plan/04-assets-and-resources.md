# 4. Assets and Resources

## 4.1 Tools to install (Phase 0)

| Purpose | Tool | Cost | Notes |
|---|---|---|---|
| Code editor | VS Code | Free | TypeScript support built in |
| Runtime | Node.js (already installed: v26) | Free | |
| 3D modelling, UVs, baking, level layout | **Blender** (latest LTS) | Free | Not installed yet. Exports glTF natively |
| Asset compression | **glTF-Transform** CLI (`@gltf-transform/cli`) | Free | Draco/meshopt geometry compression, KTX2 textures, resizing, deduplication |
| KTX2 encoder | KTX-Software (`toktx`), from Khronos | Free | Needed by glTF-Transform for KTX2/Basis |
| Texture painting | Krita (free) or Substance 3D Painter (paid) | Free / paid | ArmorPaint or Material Maker are open-source alternatives |
| Image editing | GIMP or Photopea | Free | |
| Audio editing | Audacity (simple) or Reaper (cheap licence, much more capable) | Free / ~US$60 | |
| Audio recording | Any decent USB mic + quiet room | — | Foley (wood creaks, cloth, matches) is easy and cheap to record yourself |
| Version control for binaries | Git LFS | Free | Not installed yet |
| Babylon tools (browser) | Playground, Sandbox (glTF viewer), Node Material Editor, Inspector | Free | Sandbox is the quickest way to check exported models |

## 4.2 Episode 1 asset list

**Source key:** **C** = custom (make in Blender), **L** = library asset, retextured to match the palette, **K** = kitbash (library parts assembled into something custom), **R** = record yourself.

### Environments

| Asset | Source | Priority | Notes |
|---|---|---|---|
| Phnom Penh studio interior (prologue) | K | High | Small room; reuse its furniture later |
| Village path + banana grove (journey end) | K | Medium | Banana plants as instanced cards; mostly darkness and rain |
| Courtyard ground, mud, puddles | C | High | Wet mud material is a key visual |
| Teak stilt house: exterior, upper hall, Uncle Sok's room | **C** | **Critical** | Hero asset. Modular kit: floor planks (with 1 cm gaps), walls, posts, stairs, roof tiles, shutters |
| Under-house area (Krom Phteah) + storage shed | C | High | Reuses the house's pillars |
| White funeral tent (Rong Sop) | **C** | **Critical** | Bamboo frame + cloth with wind animation (vertex shader) |

### Props

| Asset | Source | Notes |
|---|---|---|
| Teak coffin (decorated) + stage | C | Hero prop; also used in the bad ending |
| Altar, Uncle Sok portrait frame, brass candle holders | C / L | Portrait texture swaps for the "eyes open" scare |
| 4 tall brass incense burners | C | Incense sticks as separate meshes with a burn-down shader |
| Sai Sin white thread | C | Simple tube or line along the bamboo frame; snaps (two halves + animation) |
| Hanging glass oil lamps (Chhenglang), wax candles | C / L | Flame = emissive card + flicker light |
| Clay water jars (Pheon), woven bamboo benches, mats (Kanteal) | C / L | Make 2–3 variants and instance them |
| Gramophone (brass horn), with speed dial | L + edits | Library gramophones exist; adjust to period |
| Desk, fountain pens, palm-leaf manuscripts (Sleok Rith) | L / C | Manuscripts are simple custom meshes |
| Iron-bound chest, loose wall planks | C | |
| Wardrobes (hide spots) | L | |
| Firewood, ox-cart wheels, tools | L | |
| Brass wall telephone, wall clock, drafting table, ink bottles | L | |
| **Player items:** hurricane lamp (with oil gauge), matchbox, satchel, sketchbook, key fragments, Bronze Token | **C** | Seen up close all game, so give them the most detail |
| First-person hands (Sora) | C or L | Hands only; no full body needed |

### Characters

| Character | Source | Notes |
|---|---|---|
| Yay Mey (grandmother) | L base + custom clothing | White mourning chong kben and sbai. Few animations: standing, sitting, gesturing |
| Uncle Sok's corpse | C / L | Lying pose only; position swaps when unwatched |
| Neak Ta entity | C | Mostly silhouette and shadow (shader + fog), plus a detailed brass mask. Cheap, scary, culturally sensitive, so review it with your advisor |
| Shadow roamer (under-house) | C | Can share the entity's shader with a different shape |

### Audio

| Category | Items | Source |
|---|---|---|
| Ambience beds | Heavy rain, thunder, night insects, bullfrogs, wind in banana leaves, rain on roof tiles, studio room tone | Libraries + R |
| Foley | Footsteps on teak, dirt, mud; cloth; satchel; book pages; match strike; lamp; door and drawer creaks; jar lids | **R** (cheap and distinctive) |
| Horror cues | Backward chant on the gramophone, clock chime/stop, thread snap, dragging steps, whispers, entity screech, phone static | R + design in Audacity/Reaper |
| Music | Sparse Pinpeat-inspired tones (roneat, sralai, skor) and drones | Commission or license from Cambodian musicians where possible (see 4.6) |
| Voice | Yay Mey's phone call and dialogue, Sora's few lines | Khmer-speaking voice actors; English subtitles |

## 4.3 Asset sources

Always check the **licence of each individual asset** and keep a `CREDITS.md` with source, author, licence and link for every third-party asset.

| Source | What | Licence notes |
|---|---|---|
| Poly Haven | Textures, HDRIs, some models | CC0 (free for any use) |
| ambientCG | PBR textures (wood, mud, stone, fabric) | CC0 |
| Sketchfab | Models of everything, including some Khmer/SE Asian items | Mixed: filter by CC-BY or CC0 and credit authors; also paid store |
| Fab (Epic) | Megascans scans + marketplace | Megascans stopped being free after 2024; check the current Fab licence before using it outside Unreal |
| Freesound | Sound effects | Mixed CC licences per sound; CC0 and CC-BY are easiest |
| Sonniss "GameAudioGDC" bundles | Large royalty-free SFX packs, released yearly | Free; check the included licence |
| Mixamo (Adobe) | Character rigging and animations | Free with an Adobe account; check current terms |
| Google Fonts | Khmer fonts: Noto Serif Khmer, Battambang, Moul, Koulen | Open Font License |

**Rule of thumb:** library assets for generic objects (furniture, tools, barrels, textures); custom work for anything that makes the game *Cambodian* (architecture, ritual objects, clothing, the entity). Players notice the second category.

## 4.4 Asset pipeline (spike S3 turns this into a script)

```
Blender (.blend, Git LFS)
   │  export glTF 2.0 (.glb), +Y up, apply transforms, custom properties → extras
   ▼
art-export/*.glb
   │  tools/build-assets.ts → glTF-Transform:
   │    dedup, prune, weld, resize textures (2K hero / 1K props / 512 small),
   │    KTX2 (ETC1S for colour, UASTC for normal maps), Draco or meshopt
   ▼
public/assets/ep1/*.glb   → loaded by Babylon
```

Naming convention: `ep1_house_wall_a.glb`, `shared_lamp.glb`, `trigger_*`, `spawn_*`, `patrol_*`, `hide_*`, `audio_zone_*` for Blender empties that become game objects.

## 4.5 Learning resources

| Topic | Where |
|---|---|
| Babylon.js fundamentals | doc.babylonjs.com (Getting Started, then Features), playground.babylonjs.com examples |
| Babylon.js help | forum.babylonjs.com (very active; core team answers) |
| WebGPU in Babylon | doc.babylonjs.com → WebGPU section |
| Physics (Havok) | doc.babylonjs.com → Physics V2, including the character controller page |
| Audio Engine v2 | doc.babylonjs.com → Audio |
| Node Material (shaders without writing GLSL/WGSL) | nme.babylonjs.com + docs |
| glTF optimisation | gltf-transform.dev documentation |
| Blender for game assets | Blender manual, plus any modular environment / trim-sheet tutorial series |
| Horror design | Study and play: *Amnesia: The Dark Descent*, *Fatal Frame*, *Home Sweet Home* (Thai folk horror; close in spirit), *Pamali* (Indonesian folklore), *DreadOut*; GDC talks on horror pacing and audio |
| Web game performance | Babylon docs → "Optimizing your scene"; browser DevTools performance panel |

## 4.6 Cultural and historical research

The proposal lists cultural misrepresentation as Risk 3. Treat research as a real task with time in the schedule, not an afterthought.

| Topic | Sources to start with |
|---|---|
| Neak Ta and Khmer supernatural beings | Ang Choulean, *Les êtres surnaturels dans la religion populaire khmère* (Paris, CEDORECK, 1986), the foundational study. Note that Neak Ta are usually protective guardians often represented by stones, so the story should frame this one as a guardian bound by a broken contract, not as a generic demon |
| Colonial-era Cambodia, economy, plantations | Margaret Slocomb, *An Economic History of Cambodia in the Twentieth Century* (NUS Press, 2010; open access via OAPEN); Michitake Aso, "Rubber and Race in Rural Colonial Cambodia (1920s–1954)" |
| Historical photographs (1900s–1930s) | Gallica (Bibliothèque nationale de France), Archives nationales d'outre-mer (ANOM), École française d'Extrême-Orient (EFEO) photo collections, Bophana Audiovisual Resource Center (Phnom Penh) |
| Funerals, Pchum Ben, Sai Sin, Bay Ben | Ethnographic literature plus **interviews with elders and monks**; ideally record (with permission) a real description of a 1930s-style village funeral |
| Pinpeat music | Cambodian Living Arts and Cambodian musicians; commission or license original recordings instead of imitating them |
| Language | A native Khmer speaker to check every Khmer term in the design docs and translate in-game text |

**Advisor plan:** find 1–2 Cambodian advisors in Phase 0 (a family elder, a university contact or a cultural organisation). Book reviews at three points: the story outline, the Episode 1 greybox, and the Episode 1 release candidate. Credit them in the game.

## 4.7 Rough budget (solo, Episode 1)

| Item | Low | Comfortable |
|---|---|---|
| Software | US$0 (all free tools) | ~US$300 (Reaper, Substance subscription for a few months) |
| Paid assets | US$0–100 | ~US$400 |
| Sound and music (commission or licence) | US$0 (self + CC) | US$500–1,500 |
| Voice acting (a few Khmer lines) | US$0 (friends/family) | US$200–600 |
| Cultural advisor honorarium | — | US$200–500 |
| Test laptop with integrated GPU (if you don't have one) | — | US$300–500 used |
| Hosting | US$0 (static hosting free tiers) | US$0–20/month |
