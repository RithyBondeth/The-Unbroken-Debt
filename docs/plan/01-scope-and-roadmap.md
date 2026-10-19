# 1. Scope and Roadmap

## 1.1 The honest size of the project

The proposal budgets **11 months for a five-person team**. That is roughly 55 person-months. A solo developer doing the same scope should expect **2.5–4 years**, depending on hours per week. That is not a reason to stop. It is a reason to:

1. **Ship Episode 1 alone first** as a free or pay-what-you-want release. It validates the idea with real players.
2. **Build every system once** in Episode 1 and reuse it in Episodes 2–5 (see [03-game-systems.md](03-game-systems.md)).
3. **Cut cost, not atmosphere.** Darkness, fog, sound and first-person framing hide a lot. Use them deliberately.

Estimates below assume **about 25 focused hours per week**. Scale them to your real availability.

## 1.2 Roadmap overview

```
Phase 0  Pre-production            3 weeks
Phase 1  Technical spikes          4 weeks
Phase 2  Episode 1 greybox         5 weeks
Phase 3  Core systems complete     7 weeks
Phase 4  Episode 1 art + audio    10 weeks
Phase 5  Polish, test, release     5 weeks
                                  ---------
                                  ~34 weeks (~8 months) to Episode 1 release
Then     Episodes 2–5             ~4–6 months each, reusing systems
```

## 1.3 Phase details and exit criteria

Each phase ends with a checklist. Do not start the next phase until the checklist passes, or until you consciously decide to accept the gap.

### Phase 0 — Pre-production (3 weeks)

| Task | Output |
|---|---|
| Resolve the story gaps in [05-open-questions.md](05-open-questions.md), at least the ones marked **Before Ep1** | Updated design notes |
| Write the Episode 1 beat sheet: every scene, trigger, item, line of dialogue, in order | `docs/design/ep1-beats.md` |
| Define the fail state: what happens when Sora is caught | Short spec (the episode docs never say) |
| Build a visual reference board: 1930s Battambang houses, funeral tents, lamps, clothing | Folder of reference images, with sources noted |
| Write a one-page art bible: palette, lighting rules, post-processing look, texel density | `docs/design/art-bible.md` |
| Install the toolchain (see [04-assets-and-resources.md](04-assets-and-resources.md)) | Working Blender → glb → browser pipeline |
| Work through the Babylon.js getting-started docs and playground examples | Comfort with scene, camera, lights, materials, loaders |

**Exit:** You can describe all of Episode 1 from start to end without opening the PDF.

### Phase 1 — Technical spikes (4 weeks)

Small throwaway prototypes that answer risky technical questions **before** they become expensive. Each spike has a pass condition.

| Spike | Question | Pass condition |
|---|---|---|
| S1 First-person controller | Does movement feel right on raised floors, stairs and ladders? | Walk, crouch, climb stairs; head-bob; no snagging on 1 cm floor gaps |
| S2 Lamp lighting | Can one shadow-casting lamp plus many small flames run on a laptop? | 30 fps at 720p on an integrated GPU with 1 shadowed point light and 20+ unshadowed flame lights |
| S3 Asset pipeline | Can a Blender model reach the browser compressed? | `.blend` → `.glb` → Draco/meshopt + KTX2 via glTF-Transform → loads in Babylon with correct materials |
| S4 Spatial audio | Can players locate an unseen enemy by sound? | Blindfolded test: you can point to a footstep source in 3D |
| S5 Diegetic sketchbook | Can a 3D book show readable, updatable pages? | Open satchel, flip pages, new note appears; text readable at 720p |
| S6 Save/load | Does state survive refresh and export as a code? | Save to IndexedDB, reload, restore; export/import save code |
| S7 Atmosphere | Can the 1930s look be achieved cheaply? | Film grain, vignette, chromatic aberration, sepia grade, fog in one pipeline within budget |
| S8 WebGPU / WebGL2 fallback | Does the same build run on both? | Same scene runs in Chrome (WebGPU) and with WebGPU disabled (WebGL2) |

**Exit:** All spikes pass, or the design is adjusted (for example, fewer shadowed lights).

### Phase 2 — Episode 1 greybox (5 weeks)

Build the **whole episode with grey boxes**: no final art, but every room at the right scale, every trigger, puzzle, enemy path and line of text.

- Prologue studio → journey (consider a fade/cutscene instead of a playable carriage ride) → courtyard and tent → ground floor → upper hall → Uncle Sok's room → shed.
- All puzzles working: incense loop, gramophone dial, key fragments in jars, chest, counter-ritual.
- Entity behaviour: hallway patrol, under-house roamer, corpse that moves when unwatched, final "do not turn around" sequence.

**Exit:** A friend can play Episode 1 start to finish in greybox, and it is scary even with cubes. If it is not, fix the pacing now. Art will not save it.

### Phase 3 — Core systems complete (7 weeks)

Harden the spike code into the reusable systems listed in [03-game-systems.md](03-game-systems.md): interaction, inventory, sketchbook, lamp and resources, stealth perception, entity AI, scripted events, save, settings, accessibility. Add automated tests for game logic (not rendering).

**Exit:** Systems are data-driven. Adding a new item, note or trigger means editing data, not engine code.

### Phase 4 — Episode 1 art and audio (10 weeks)

| Weeks | Focus |
|---|---|
| 1–3 | Hero architecture: stilt house exterior/interior, funeral tent, under-house area |
| 4–5 | Props: library assets retextured to the palette, plus custom Khmer props |
| 6 | Characters: Yay Mey, the corpse, the entity (shadow and mask) |
| 7 | Lighting bake, post-processing tuning, rain and wind effects |
| 8–9 | Sound: ambience beds, foley, horror cues, entity sounds, music stingers |
| 10 | Performance pass: draw calls, polygons, texture memory, load size |

**Exit:** Meets the budgets in [02-technical-architecture.md](02-technical-architecture.md) on both target machines.

### Phase 5 — Polish, test, release (5 weeks)

- 5+ external playtesters; watch them play without helping, and note where they get lost or bored.
- Cultural review of Episode 1 by at least one Cambodian advisor (see section 4.6).
- Cross-browser pass: Chrome, Edge, Firefox, Safari on Windows and macOS.
- Store page / landing page, trailer capture, release.

**Exit:** Episode 1 is public. Collect feedback before starting Episode 2.

## 1.4 Episodes 2–5 (after Ep1 release)

| Episode | New systems to build | Reuse from earlier | Estimate (solo) |
|---|---|---|---|
| 2 Whispering Pagoda | Lamp shutter, noise surfaces, breath-hold, thrown distractions, mirror light beams, timed escape | Everything from Ep1 | 4–5 months |
| 3 Drowned Village | Rowboat, water/wetness, safe-zone lights, water-only enemy pathing | Mirror/beam logic not needed; fuse = key-fragment pattern | 5–6 months (water is hard) |
| 4 Rubber Plantation | Compass, fog navigation loop, "don't look back" taboo detector, furnace sequence | Gear puzzle = inventory + slots | 4–5 months |
| 5 Sunken Sanctuary | Hub, boss ritual, chant choice UI, ending logic | Each trial reuses a previous episode's system | 5–6 months |

## 1.5 Solo cut list (in order of what to cut first)

If time runs short, cut from the top. None of these damages the core experience.

1. Playable carriage/train journey → fade-to-black with sound and a sketchbook entry.
2. Spoken dialogue → written text with Khmer-language voice snippets for key lines only.
3. Full-body characters → Sora is hands-only (first person); NPCs mostly seated, static or shown in silhouette.
4. Many unique props → fewer props, more variation through material tints and decals.
5. Physics-driven debris in escape sequences → scripted animations.
6. Rowboat physics (Ep3) → boat on a spline with limited steering.

## 1.6 Things not to do as a solo developer

- Do not build a level editor. Use Blender as the level editor and export metadata via custom properties.
- Do not write your own engine features that Babylon already has (physics, audio, picking, GUI, post-processing).
- Do not start Episode 2 content before Episode 1 is released.
- Do not polish art in a room whose gameplay is not final.
