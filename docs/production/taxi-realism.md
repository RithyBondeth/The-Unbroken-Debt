# Taxi scene visual pass

The Studio → Village ride uses authored cabin and landscape assets in the same Babylon scene renderer as Act I. The journey lasts 72 seconds, with eight-second autosaves, resume and an atomic CP1 arrival checkpoint.

## Art and motion

- The roadside uses the village's actual trees, coconut and banana palms, bamboo, ferns, shrubs, bark, leaf, forest-floor and mud materials. A single 540-metre curved route covers the whole ride and visible horizon, without recycling scenery. The car follows its centreline and tangent so bends and near/far parallax stay coherent. Trees are scattered in irregular groves, and leaf materials have small, unsynchronized wind motion. A crowned mud track, wheel ruts and standing water replace the flat strip of road.
- The cabin has a curved headliner and dashboard, textured worn vinyl with normal/roughness maps, teak veneer, padded seats with piping and pleats, cranks, trim, glovebox, radio, analogue instruments, sunvisors and a reflected rear-view mirror. An opaque floorpan, firewall, rear bulkhead, lower body and overlapping lining seal the footwell. The padded dashboard shell sits behind the wood fascia, keeping the gauges and controls visible; an occlusion regression protects this placement. Grooved rubber mats, pedals, heater grille, door pockets, sill fasteners, pull switches and engraved labels add close-up detail.
- The seated driver derives from the same CC0 MakeHuman source library already used for Sok, with a neutral expression, a different age blend, anatomical eyes, cotton clothing and a baked steering pose. The driver has photo-derived skin relief, a fitted cloth cap, sewn cuffs, collar leaves, a shirt placket and chest pocket, and a small wristwatch. No runtime skeleton is required.
- Sora’s visible seated lower body uses her existing female MakeHuman source. Cotton travel trousers and leather flats remain visible when looking down; a small blouse hem seals the waist without covering the legs. Both feet rest on the passenger mat; the model stays attached to the seat as Sora looks around.
- The muddy track is 5.6 metres wide, with clear shoulders and roadside markers beyond its edges. The full route has 572 broadleaf trees plus palms, bamboo and undergrowth. Saplings and ferns enclose the road while their full low geometry stays beyond a 3.4-metre offset from the centreline. A decimated outer canopy closes gaps behind the near trees; distant batches receive lighting but do not add headlight shadow draws. Route chunks more than 80 metres ahead or behind are disabled, beyond both the forward and rearward viewing ranges.
- StormSky, NIGHT_LOOK exposure, moon/cloud bounce, fog and the episode colour grade match Act I. Asymmetric warm headlights cast PCF shadows; a small instrument practical lights the cabin. Standing water reflects the sky and trees.
- The curved windshield carries larger moving water beads and trails; side windows retain unwiped runoff. Two fields use Act I’s RainStreaks: a dense warm-lit field in front of the bonnet and dimmer rain further into the forest. Their velocity combines falling rain, gusts and vehicle speed, with no emission inside the cabin. The physical wiper arms and water-removal mask use the same periodic angle. Wind-driven rain, speed-linked suspension, braking and live speedometer needles support the existing rain/engine/wiper audio.
- The roadside glimpse uses the existing authored ShadowFigure.

## Rebuilding

From the repository root, with Blender, KTX tools and project dependencies installed:

```sh
blender -b --factory-startup -P tools/travel/build-taxi.py
node tools/travel/optimise-taxi.mjs
```

Both commands accept `cabin` or `roadside` to rebuild one asset; Blender arguments follow `--`. Sources are `art-source/blender/ep1/ep1_taxi_{cabin,roadside}.blend`; generated vinyl textures live in `art-source/textures/ep1/taxi/`. The optimizer writes texture-compressed, meshopt GLBs to `public/assets/ep1/` and removes its temporary staging directory.

Materials and human sources reuse the repository's existing CC0 library; no new externally fetched art is introduced. The source script preserves the village Blender file and exports the taxi into separate files.

## Review and verification

`/tests/browser/opening.html?stage=taxi&review` provides Road, Dashboard, Driver, Passenger window and Rear cabin camera presets, Footwell, Sora legs and Lower door checks, and a held lightning-detail view. Review mode loops the middle of the ride; Lightning detail holds the production flash for surface inspection. Omit `review` for the normal journey and arrival. **Save screenshot** captures a 1600 × 1000 render to `debug-shots/taxi-<view>.png`. This fixture uses the isolated `boon-sop-opening-qa` database, separate from player saves.

Asset regression tests check textures, anatomical geometry and outward skin normals, inset eyes, upward road/water normals, download/triangle budgets and complete-route coverage and opaque cabin enclosure. A renderer regression also checks that shared plant instances survive batching and that their culling bounds move with the route. Motion tests check the speed integral, stopping, wiper periodicity and continuous route alignment. Asset rays check 42 floor/lower-body views against the actual exported opaque shell.

Validation: `npm run check` passes TypeScript, ESLint, 356 unit tests and the production build. The final regenerated landscape also passes all twelve asset regressions. A fresh 72-second browser ride completed without skipping, reloaded into CP1 at Village · Flooded road with ten matches intact, and enabled the early-encounter requirement. No console errors were recorded. Browser captures and the arrival report are in `docs/evidence/taxi-realism/`.

The cabin/continuous-route/monsoon follow-up is captured in `docs/evidence/taxi-cabin-storm/`.

## Passenger and conversation follow-up

The ride contains a 14-line, subtitle-only conversation: seven lines for Sora and seven for the driver. It connects Yay Mey’s call, Sok’s funeral and the roadside presence, then explains the flooded-road stop. Lines have reading time and do not overlap; the apparition has a quiet gap. Selection uses the ride clock, so reloads and timing jumps show the current reply rather than queuing old lines. Subtitle timeline updates cancel stale timed subtitle work.

Tests cover speaker balance, reading time, line selection after resume, stale subtitle cancellation, feet resting on the floor, unobstructed views of both shoes and forest density. Sources remain in `tools/travel/build-taxi.py`; conversation text is in `src/episodes/ep1/travel/taxiConversation.ts`. Evidence for this pass is in `docs/evidence/taxi-passengers/`.

## Narrower forest road

The track narrows from 6.8 to 4.4 metres. Trees and saplings sit closer to both verges, with 572 broadleaf trees (previously 494), denser undergrowth and a low fern fringe. Roadside markers move inward with the verge. The cabin, route centreline and ride timeline are unchanged. The rebuilt roadside GLB is 11,501,664 bytes, within the existing 12 MiB limit. All 16 taxi asset, batching and motion checks pass; an exported-geometry measurement confirms a maximum track half-width of 2.217 metres along the bends, including quantization/curve sampling tolerance. Browser inspection of the moving scene recorded no console errors. Evidence: `docs/evidence/taxi-narrow-road/road.png`.

## Clear, flooded carriageway

The latest pass widens the track from 4.4 to 5.6 metres. Plant placement checks every transformed vertex below 2.8 metres against the curved centreline, moving the whole plant outward until its full low footprint clears a 3.4-metre lateral offset. This keeps grass, ferns, shrubs, bamboo and tree trunks beyond the road with room for wind motion. Dense woodland and overhead canopy remain on both sides.

There are 218 shallow water patches, including 48 broad flooded pools across the carriageway. Their surface sits above the mud crown, with a matching reflection plane, subtle drifting surface normals and the existing storm reflections. Markers follow the wider shoulder. The optimized roadside GLB is 11,578,352 bytes, within 12 MiB.

Validation: all 356 unit tests pass with two workers; the 17 taxi asset/batching/motion checks include a regression over exported vegetation footprints, road width and visible water elevation. ESLint, TypeScript and the production build pass. Moving browser inspection recorded no console errors. Evidence: `docs/evidence/taxi-clear-water/road.png`.

## Dread pass: jungle road, roadside rite, running forms and soundscape

**Road.** The laterite cart track has two deep wheel ruts with mud pushed up beside them, a grassy centre hump (11,000 blades in tufts), a crumbling edge into flooded ditches on both sides, 900 pebbles of gravel, and the existing rut pools. A colonial telegraph line follows the left verge: tarred posts every 38–47 m, cross-arms with glass insulators and two sagging wires; some posts lean and one arm hangs broken. Three milestones mark the route. Track and ground use shared smooth normals.

**Forest.** The roadside now uses the village's old-growth jungle (the same `tree_*` giants with lianas, `dead_*` snags, termite mounds, `jungle_understory` and leaf litter, sedge, ferns and shrubs) in four layers: giants at 4–9.5 m, young growth, an unshadowed middle wall of decimated crowns and a far wall. Bananas no longer appear in the forest. Omens line the road: rotting crocodile flags, threads strung through the trees, incense and candles at trunk feet, and two Ting Mong guarding the village approach.

**Roadside rite (advisor review).** At 212 m on Sora's side (passed around 28–31 s, while the driver says people don't wait beside this road): a dead tree bound in white cloth; the spirit house with ground offerings; flags; a Ting Mong facing the road; bamboo poles with long white banners; and a ring of ten stakes and white cord (the lowest cord snapped). Inside lies a banana-stem raft carrying a life-size effigy bound in white cloth, its face covered and a red cloth over its feet, with banana-leaf cones, an incense bowl and fourteen lit candles. A guttering point light and flickering flame emission light it in the rain. It is written as a sending-away rite left at the forest edge. It is not desecrated: the horror is that it is fresh and unattended. The rite, cloth wraps, the effigy, the mirror yantra and the blessing threads all need cultural-advisor review.

**Cabin and driver.** Added a mirror charm (jasmine garland with a red tassel, prayer beads, and a folded yantra cloth with ruled diagrams but no script) on a pivot that swings with bends, bumps and braking; a mechanical taximeter with its flag up; and what the morning's mourners left behind (a white lotus bud and a coil of blessing thread on the rear bench, a bundle of incense on the floor). The driver wears a checked red krama with a knot and tails, white blessing threads at the wrist, and a cap refitted to his head. His head is turned past Sora toward the trees on her side. At runtime he breathes, flinches at the crossing and the slap, and the car swerves.

**Running forms.** `taxiApparitions.ts` times three passes of the black Neak Ta form. Each is a lightless (unlit, near-black) copy of the ShadowFigure with two fainter trailing copies as a speed smear:
- **Glimpse (19.4 s):** it runs between the trunks on the driver's side.
- **Crossing (46.9 s):** it crosses the road 8 m ahead in 0.62 s, silhouetted by a lightning flash, while the driver says not to call to it. He lifts off the throttle, brakes and swerves.
- **Overtake (57.3 s):** it sprints up Sora's side, slaps her window when level with it, and veers into the trees ahead under lightning.

**Sound.** `TaxiSoundscape` adds the following over the engine, wipers, rain, wind and DreadScore:
- Frogs and crickets, muffled by the car body. They fall silent from 22 s around the rite and the watcher, return, then stop again just before the overtake.
- The dash radio hissing between stations. It surges whenever something is near.
- Wordless whispers and flags snapping, placed at the rite as the car passes.
- For the crossing: a stereo rush with Doppler and slapping feet, a shock sting on the beat, the brakes slithering, the driver's gasp, ringing ears and thunder.
- For the overtake: sprinting feet placed on the runner, then the slap on Sora's window with a shock sting.
- Thunder for the other two lightning flashes.

All sounds are synthesised in `taxiDreadSounds.ts`. Like the rest of the score, they contain no chant or bell.

**Budgets.** Roadside textures for set dressing are capped at 512 px, with prop relief maps at 256 px (`optimise-taxi.mjs`). The roadside GLB is 11.1 MB (limit 12 MiB) and the cabin 5.8 MB (limit 6 MiB). In the moving ride the forest draws about 2.8 M triangles in 680 draw calls (previously 2.2 M in 800).

**Fixes found on the way.**
- Primitive spheres carried a second UV map, which broke batching.
- A roadside mesh left alone in its batch cell lost its glTF handedness parent and appeared inside the car. `buildTaxiRoadside` now re-parents with `setParent`.

Tests: `taxiApparitions.test.ts` covers pass timing, the road crossing, overtaking at the window, swerve, forest hush, radio surges and throttle. `taxiSounds.test.ts` checks every new sound and the rush's pan and peak. `taxiAssets.test.ts` checks the telegraph line, gravel, ditches, centre grass, the rite pieces and emissive flames, the charm pivot, the krama and the taximeter.

## Real driver and a working taxi's cabin

**Driver.** The driver was a bare MakeHuman body with sphere eyes and a primitive cap. He is rebuilt from fitted CC0 MakeHuman proxies: short combed hair with grey through it, eyebrows, eyelashes, textured brown eyes, and a button shirt and trousers with real folds, re-dyed to washed cotton. The skin under the clothes is removed. The face blend is an adult man rather than an androgynous one. His head is turned past Sora toward the trees on her side, his eyes turned further still. At runtime:
- he blinks every few seconds (sometimes twice) and screws his eyes half shut at the crossing;
- the skin gets a little translucency and a softer sheen;
- the eyes get a wet clear coat.

Sources and the rebuild steps are in `art-source/characters/taxi-driver/README.md`.

**Cabin.**
- **Seats:** tuck-and-roll front seats with rolled edges, bolsters and piping, and a leather robe rail on their backs. The rear bench has a buttoned back and a centre armrest.
- **Doors:** cards with walnut capping, pleated panels, chrome strips, carpet kick panels, the shut line, leather pull straps, lock knobs, crank rosettes and rear-door handles.
- **Roof:** lining bows and seams, a frosted dome lamp, leather assist straps and coat hooks.
- **Windshield:** a header rail with the vacuum wiper motor and its hose, and a chrome sill.
- **Rear window:** a roller blind drawn down, with its tassel.
- **Dash:** an eight-day clock in the glovebox lid, the ignition key with a leather fob, the passenger's grab bar, an ashtray with two butts, and a fare card tucked behind the windshield.
- **Floor:** a handbrake and gear-lever gaiter, a furled oiled-paper umbrella by Sora's door, and mud and wet leaves tracked onto her mat.

The walnut is darker and varnished (clear coat) instead of glowing. The clockwork meter ticks, and its fare drum turns over (`taxiMeter`), placed at the meter.

**Budgets.** At load the static trim is batched by material, so the cabin now draws in about 120 batches instead of about 620 pieces. The moving ride measured 599 draw calls and 3.1 M triangles, against about 680 before this pass. The cabin GLB is 5.9 MB (limit 6 MiB). The shirt and hair relief maps are capped at 512 and 256 px.

## Grip, krama, a talking driver, endless forest, two runners

**Grip.** Both hands are posed on the rim at nine and three, halfway down the wheel. The rim position is shared with the wheel geometry (`WHEEL_CENTRE`, `WHEEL_FACING`, `WHEEL_RADIUS`). Each palm sits just outside the rim, fingers pointing forward through the wheel and curled back round it, with the thumbs resting up along the inside of the rim. Each hand's IK target is nudged until the hollow of the curled fingers closes on the rim. The wristwatch and wrist threads are removed.

**Krama.** Removed at review, with the wrist threads: he wears only his shirt.

**Talking.** The driver mesh and his hair, brows, lashes, eyes and shirt carry baked shapes: `talk` (MakeHuman mouth-open target), `look_road`, `look_sora`, `nod` and `grip` (two fingers of the near hand lift to tap the rim), plus `blink`. `taxiDriver.ts` turns the conversation clock into weights:
- **While he speaks:** his jaw moves gently on syllables (about three a second) and closes between words and at line ends. He glances round to Sora as he starts, nods on stressed words and taps two fingers on the rim.
- **While Sora speaks:** he half turns to listen.
- **Otherwise:** he watches the road, except while he keeps looking into the trees (20–34 s). The crossing snaps his eyes forward.

`TaxiVisuals` eases each shape towards its weight: the jaw quickly, the head slowly.

**Endless forest.** The roadside adds a sparse row of crowns at 22–31 m and cut-out forest walls of trunks, lianas and canopy at 34 and 44 m on both sides. The ground now runs to 70 m and the camera sees to 85 m, so no horizon opens between the trunks.

**Two runners.** The roadside Neak Ta watcher and the early glimpse are removed. The crossing now lands on the 37.8 s lightning, and Sora's next line refers to it: "Wait—something ran across the road! Did you see that?" The old rising sting is removed so it does not double the crossing's shock. The overtake at Sora's window is unchanged.
