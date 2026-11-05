# Episode 3 · The Drowned Village

Implementation and review · 3 November 2026 · `bondeth/episode-3-drowned-village`.

## Source continuity

Episode 1’s reference is local `main` (`1d71477`, also the remote main at the
start of this task). The existing workspace held the uncommitted Episode 2
implementation on `bondeth/episode-2-whispering-pagoda`; no local or remote branch
named `bondeth/whisper-pagoda` was present. Those existing edits and assets were
retained when the new branch was created.

The chapter shares the Episode 1 HDR post-processing, grade, calibrated lantern
falloff, physical lantern and Sora’s hands, paper interface, typography, notebook,
footsteps and material library. Episode 2 supplies the actual aged hand meshes,
MakeHuman anatomy, expedition equipment and the cinematic playback lifecycle.
Episode 1's cloud renderer is unchanged from `main`. Episode 3 adds its own
photographed daylight environment and uses the shared storm dome at night.

## Playable chapter

- Afternoon floating market, noodle seller, Vuthy’s inherited journal-dependent
  dialogue and Pa Lok’s account of Kanha’s death. Conversations have English
  subtitles, subtle anatomical morphs, pause, skip and a paper transcript.
- Alternating left/right oar input drives a guided storm crossing with a visible
  hull, moving oars, wave movement and stroke audio. Arrival checkpoints at the
  clinic’s landing lamp.
- Flooded wards: two sealable windows, three dry fuses, raised dry boardwalks,
  fixed lamp refuges, an attic stove, supplies and optional records. Repair and
  collection states reconstruct from saves.
- A drainage pump reveals the cellar. Four physical brass dials display Khmer
  numerals; accessible paper controls operate the same saved combination. Both
  the admission register and a reception calendar key give the necessary clue.
- The jar opens the playable memory as Sok. His aged hands, stylus and two
  separate interactions let the player scrape Vuthy’s name and write Sora’s.
- Three purification candles and a separate fourth-candle choice. Freeing Kanha
  and Pich awards Respect +2 once and records `series.kanha.freed` for Episode 5.
  Completing only the seal retains the sorrow consequence.
- Cut mooring, rising water, creaking and moving broken beams, a timed roof route,
  the last-stilt rescue, compass, burnt rubber, fifth night mark and Episode 4 clue.
- Episode 2 credits can continue directly into Episode 3. Production entry
  requires real Episode 2 completion. Episode 1/2 archives are kept separately;
  autosaves, immutable retry checkpoints and an Episode 3 completion archive
  use the existing save format and export/import code.

## Art and horror

The editable Blender scene has more than 4,300 authored objects before runtime batching:
real timber piles and braces, raised decks, torn window bays, rusty corrugated
metal sheets and fixings, algae and tide marks, framing, iron beds and muslin,
medical glass, instruments, paper records, mosquito nets, charcoal, woven traps,
vegetables, market awnings, sampans, a raft, nets, rope and storm debris. Kanha
uses anatomical geometry with separate wet hair strands; Pich uses the same
character construction at child scale. The realism revision adds scanned iron
beds and furniture, shaped bedding, gathered fabric, supported oil lamps, market
cladding, boat construction and medical dressing. Original maps up to 1024px
combine shared photographic grain with paint loss, damp, corrosion and textile
damage, using separate base color, linear normal and ORM maps. The optimized
area is approximately 63.4 MB, plus a 4.3 MB HDR sky. See
`episode-3-realism.md` and `episode-3-composition.md` for references and details.

GPU waves, tiled animated water normals, wake rings, rain, shared storm clouds,
lightning and calibrated amber lamps establish the wet clinic. Medium, High and
Ultra use 256px, 512px and 768px planar lake/floodwater reflections respectively.
Low omits the shadow map and reflection. Materials retain their wood, cloth and
metal distinctions.

The spirit approaches only when the player is in water, with widening rings
before rising. Raised boards and fixed lamp zones prevent contact. Exposure
tracks wetness and warmth; the stove and safe lamps recover them. Reading,
cinematics, absent pointer capture and background tabs pause threats, survival
and the escape clock. Reduced-motion settings suppress cinematic sways and
the cold-edge pulse.

Sound uses the existing series buses and spatial attenuation: water, oar strokes,
tin rain, bird calls, submerged breathing, timber creaks and snaps, a diesel loop,
an original wordless lullaby fragment and the existing pressure score. Dialogue
is presented through English subtitles; these are not newly recorded voice actors.

## Review

Run `npm run dev`, then open:

- `/?start=ep3&profile=ep3-play` for a new isolated development playthrough.
- `/?episode=3` to continue from a completed Episode 2 production save.
- `/tests/browser/drowned-village.html` for the isolated production-scene review.
  `stage=market|clinic|vault|memory|purification|escape` selects a review state;
  `view=market|lok|clinic|ward|attic|vault|kanha|ritual|escape|rescue` selects a view.
  `quality=low|medium|high|ultra` selects a preset; `audio` enables production audio.

The review’s story button scripts dialogue decisions but uses the production
progression methods, alternating-oar key listener, safe dial operations and save
payloads. The physical-routes button uses the real Havok controller, with threats
paused, on separate named routes; it also checks actual interaction ray reach.
These are development fixtures and cannot replace the player’s IndexedDB saves.

## Remaining production review

The source narrative requests a historically checked Khmer lunar-date conversion.
The current puzzle uses Sok’s legible copied marks with an explicit numeral key;
the damaged lunar annotation is not presented as a verified historical conversion.
The name/folklore of the water spirit, Pich’s portrayal and the ritual verse retain
the cultural-advisor review requested by the original episode specification.

The chapter loop is implemented; its specification’s 1.5–2 hour playtime and
difficulty pacing have not been established by a full human playtest. The lake
crossing uses the specification’s guided-path fallback rather than a buoyancy
simulation. Collapse is staged through flooding, moving broken beams, sound
and the roof route; there is no whole-building rigid-body destruction simulation.
