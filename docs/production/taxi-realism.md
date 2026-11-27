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

## Horror pass, 10 Nov 2026: driver, car nose, swaying forest, the back seat

**Driver.** The body uses MakeHuman's old Asian proportions in full and is leaner (0.6 minimum-weight). The skin is generated by `khmer_driver_skin` in `build-taxi.py`: the old Asian and old dark-skinned photos are blended to a sun-browned Khmer tone, and the photo's own creases are deepened. It adds grey two-day stubble along the jaw and upper lip (masked from where each face sits on the head) and sweat in the folds beside the mouth. The pore relief strength is 0.6. Other changes:
- Hair is MakeHuman `short04`, combed back and greying.
- The shirt carries sweat tide-marks and grime.
- A slim faded red-and-white chequered krama is wound once round his neck, both ends down his shirt front. It is weighted from the nearest skin or shirt, so his glances carry it.
- **Review note:** this reverses the earlier "krama removed at review" decision. It is one line in `driver()` to take it out again.
- New sources (pinned in `art-source/characters/taxi-driver/sources.json`): `old_darkskinned_male_diffuse.png`, `old_lightskinned_male_diffuse2.png` and `short04`.

**Car nose.** `car_nose()` replaces the low bonnet, which never showed through the windscreen. It adds:
- a lofted, hinged bonnet in black-green lacquer, high enough to be seen over the scuttle, with louvres, catches and seams
- a nickel radiator shell with slats
- the filler cap with a motor thermometer
- the lamp bar with two nickel lamp bowls, and the crowns of the wings

At runtime the lacquer gets a wet clear coat with rain beads running back at road speed, and the headlamps sit in the bowls. The cabin GLB is 6.27 MB against its 6 MiB (6.29 MB) budget.

**Forest.** The two far ranks from `taxiForestDepth.ts` now have six rows of vertices each and sway with the shared wind (`FoliageWind` "leaf"), so the whole wall of crowns heaves with each gust.

**The back seat (46.6 s and 52.3 s).** The rear-view mirror is now a fixed camera at the glass, aimed down at the back seat and drawn mirrored. The old `MirrorTexture` plane faced the wrong way and only ever showed the dashboard. A form sits behind Sora while the driver says "Don't call to it": only its pale eyes and the dim shape of its head show in the glass, with a breath behind her shoulder. After she says "There's nobody behind us", the lightning shows it leaning in between the front seats, with whispering at her ear, the shock sting and the dash dimming. It is on a layer only the mirror camera draws, so turning round finds the seat empty.

**The window, after.** When the face at Sora's window strikes the glass, two long-fingered greasy palm prints stay on it, with rain runs from them, for the rest of the ride. They wash slowly and stand out in each flash. Breath fogs the glass where its mouth was, then clears.

Advisor review: the mirror rider and the window prints extend the black Neak Ta's presence in the taxi.

## Review pass, 11 Nov 2026: no rite, thin haze, old growth, a real Neak Ta

**Rite removed.** The sending-away rite at 212 m is gone from `build-taxi.py` (`roadside_rite`, `RITUAL_Z` and the clearing around it) and from the runtime: its candlelight, the whispers and flags placed at it, and the verge kept clear for it. The small omens (flags, threads, incense at trunk feet, the Ting Mong at the village approach, milestones) remain. The insects still fall silent from 22 s, now around the still form at the verge.

**Haze, not a wall of mist.** `TaxiMist` follows Episode 2's forest: a thin grey-teal haze (density 0.024, height falloff 0.15, marched to 75 m) a shade lighter than the trees, so trunk after trunk stands dark against it. Mist banks are four low skeins between the trunks, knee to waist high; the humps round each scare add at most a quarter. The far fog used to be twice the night look's density and up to 75 % thicker at the scares.

**Old growth, not bamboo.** The roadside is replanted as rank after rank of the village's broadleaf giants: the near rank (4.2–9 m) is 60 % the tallest half of them at 0.85–1.3 scale, a second rank of full giants stands at 9.5–14 m, and lighter crowns at 14–21, 21–29 and 29–37 m grow taller towards the back. Bamboo is 2 % of the young growth (it was in the near rank and a sixth of the young growth, and was planted twice again at runtime). Under the headlamps the village's pale leaf tint is graded to a deep cold green for this scene.

**Endless forest, as Episode 2 does it.** The painted cut-out ranks are replaced by Episode 2's far forest: crossed painted tree cards (`src/render/farTreeCards.ts`, shared, painted by `forestCards.ts`) in a belt from 33 to 125 m either side, densest near the modelled trees, about one per 18 m², crowns as wide as tall, with emergents above the canopy line, over a dark forest floor that carries on from the road's ground. The camera now sees to 140 m.

**The Neak Ta moves like a person (advisor review).** The rigid shrine effigy slid along the road is replaced by `neakta_roadside.glb` (`tools/characters/build-neakta-roadside.py`): the same sculpted anatomy, aged face, sarong and sash, kept on MakeHuman's skeleton and weights and driven by CMU motion capture through Episode 2's retargeter: `stand` (79_73, arms hanging dead), `walk` (91_25, one leg dragged, arms dead, 0.64 m/s) and `reach` (104_41). `MocapFigure` (shared) poses it from the ride clock and turns its head to keep Sora in view. It is soot-black and dry-skinned so the lamps show a dark gaunt man, not a pale one. It is never seen moving faster than a person:
- **17.4–24.5 s:** it stands among the first trunks on Sora's side, breathing and shifting its weight, its head following the car.
- **Crossing (36.8–38.15 s):** as the lamps stutter it is already in the road, dragging itself towards Sora's side; the lightning shows it nine metres off the bonnet; the lamps blink as he brakes and the road is empty when they return. The rush of air is gone. Sora now says "Wait—there was someone in the road!"
- **Overtake (57.3–57.93 s):** one stroke of lightning flickers four times; each flicker finds it standing nearer in the trees on her side, level with the car; the last is its hands on her glass (the slap). Between flickers only its feet in the mud are heard.
- **Window (60.18–61.02 s):** with the lamps dead, the lightning shows its face at the glass, looking down at her; a faint cold fill stands for lightning through the windscreen.

The back-seat rider in the mirror still uses the shrine effigy (`ShadowFigure`).

## Redesign, 17 Nov 2026: a real 1933 taxi, paddies, and real people

**The taxi.** The cabin is a photoscanned 1933 Citroën Rosalie (RolloT, CC BY 4.0), prepared by `tools/travel/taxi_scans.py` and relined by region in `build-taxi.py` with Poly Haven photo textures. The runtime finds lamps, glass, wipers, mirror, dials and seats from `taxi_anchor_*` empties. The wipers hang from the top, the cluster has five dials, and the mirror shows the paddies.

**The road.** The first 140 m run between flooded paddies: dikes, instanced rows of rice, a palm far card, three scanned stilt houses with a lit lamp, and a laterite embankment. The forest starts at 150 m, with a shrine and candle at 157.5 m and scanned mud ruts in the track.

**The driver is a photoscan.**
- **Face and head:** a real 8K photoscan of a man ("A-Pose - Male Full Body 3D Scan", OverseerThuror, CC BY 4.0), prepared by `tools/travel/taxi_driver_head.py`. From the 2.6-million-face scan it keeps the head and the bare neck. The hoodie comes off, and a fitted neck tube runs down into the collar. The baseball cap becomes a 1930s cloth cap: its brim is cut back to a short peak and its embroidered letters are smoothed away. Logos, eyelets and the strap are re-dyed as worn dark cotton twill, sweat-darkened at the band.
- **Skin:** browned to a sun-dark Sino-Khmer tone with an RGB curve. The photo's pores, stubble and creases stay.
- **Bake:** a 46,000-triangle game mesh is baked in Cycles from the full scan: 4096 px colour, 2048 relief, 1024 roughness. The roughness has wet eyes, lips, an oily nose and brow, matte hair and cotton. Ears, eyes, nose and lips are protected from decimation, so the thin ear bakes clean. UV islands are weighted so the face gets about five times the texture of the cap. Missed texels and island borders are filled from their neighbours, so no seam darkens in the mips.
- **Shapes:** `build-taxi.py` (`scanned_head`) sets the head on the scanned body's collar and bakes his shapes: `look_road`, `look_sora` and `nod` (neck-weighted turns), `talk` (the jaw on its hinge) and `blink` (the lids). Sources and credits are in the asset tracker (V1-209 to V1-217).
- **Body:** Renderpeople's "Eric" (CC BY 4.0), posed seated with two-bone IK, his hands curled round the rim. One recoloured copy of the scan's photo dresses all of him (`driver_photo`), decided pixel by pixel so every edge follows the photo rather than the mesh. His skin takes the same sun-browned curve as his face. The white shirt becomes a plain, washed, old cream that keeps only its soft large folds: the studio shadows of the scan's A-pose are gone. The waistcoat, trousers and shoes stay as photographed. The whole collar stays, up to its sewn edge; only his own neck, head and hair are cut away.
- **Sleeves (`simulate_sleeves`):** split off, then cloth-simulated as cotton while the arms move from the A-pose to the wheel, over a collider 1 cm inside them. The cloth is simulated coarse (about 2 cm) with stiff bending, so it falls in broad, heavy folds: at the elbow, and hanging from the forearm. After it settles it is lightly smoothed and subdivided. A fine, soft simulation had crumpled like paper, and self-collision cost twenty minutes for no visible gain. The simulation adds about a minute to `build-taxi.py -- cabin`.
- **No tangents in the GLB:** they push the instanced trim past WebGPU's eight vertex buffers and break the face's blend shapes. The face's relief reads well with the renderer's own tangents.

**Sora's legs.** Renderpeople's "Carla" (CC BY 4.0), posed into the footwell, her heels and the balls of her feet set on the Rosalie's floorboards by a ray to the floor. The glen-check trousers are re-dyed plain dark cotton and keep the scan's folds. Her top becomes a cream blouse tucked in at the waist, and the cut above it is closed with blouse, so the old flat cloth over her lap is gone. Her black leather pumps rest on the mat.

**The Neak Ta's skin is real.** The roadside figure keeps its photoscanned body (LaPresse3D, CC BY 4.0) and gets its own baked skin (`soot_skin` in `build-neakta-roadside.py`):
- **Colour:** the scan's photo graded to deep soot-brown, so its pores, veins and old faded markings still show. Ash is dusted on in patches, and mud has dried in runs down the shins and feet.
- **Roughness:** rain runs wet in streaks; the ash is dry.
- **Relief:** baked in the body's own space. A relief taken from the photo creased along each of its hundreds of UV islands.

The rebuilt right side's copied split normals are cleared. (Smoothing the arms' scan noise was tried: it shrank them to spikes.) The runtime no longer multiplies the skin by near-black (0.009), which had left only a chrome-like sheen. It dims the baked colour to about a quarter, so under the lightning it reads as a soot-dark man with skin, not black plastic. The sash is soaked nearly black. The hair is finer and sparser, with wet strands gathered into clumps that pinch together at the tips.

**Budgets and tests.** The people keep 2K maps, with the face in UASTC, and the cabin GLB is now about 22 MB (budget 26 MiB). The roadside is 15.9 MB (budget 17 MiB) and the Neak Ta 6.3 MB. `taxiAssets.test.ts` now checks the Rosalie (its own linings, its roof height, a floor sealed below Sora's eyes, the walnut fascia and dials) and the scanned people (shapes and maps on the face, shoes visible from Sora's eyes, no lap cloth). `optimise-taxi.mjs` caps everything else at 1024 px through the gltf-transform API, because the CLI's `--pattern` cannot exclude names.

## Wardrobe pass, 26 Nov 2026: a real cap, real hands, a cloth krama

The user's playtest screenshot showed the driver's cap, krama, clothes and grip all reading as generated. Each is now a scan or a simulation, built by `tools/travel/taxi_driver_wardrobe.py` and called from `taxi_people_refine.py`:
- **Cap:** "Flat Cap" (kevjumba, CC BY 4.0, V1-240), a photoscan of a real wool flat cap. Its five 65k-vertex chunks are welded and reduced to 16,000 triangles. An ellipse is fitted to the opening's back and sides (the front hides under the peak), and the cap is warped onto his hat line: just above the brows, over the ear tops, low at the back. The stiff peak hinges up 14° at the brow so his eyes show beneath it, and the scalp under the cap tucks 2.8 mm inside it. It rides the head's five shapes as before.
- **Hands:** "Hand Scan Rigged And Animated" (Dakta.Grower.Nzl, CC BY 4.0, V1-241). The download has no skeleton, so it is rigged from its own geometry. Geodesic rings from each fingertip give every digit's centre line, and its joints sit at fixed fractions of the tip-to-web length. Skin weights come from the same geodesics, and dual-quaternion skinning keeps the knuckles full. The left hand is the right one mirrored.
- **Grip (`solve_grip`):** the rim runs across the distal palm, slanting toward the wrist on the little-finger side, index uppermost. The palm rolls round the 25 mm bakelite tube until the wrist points back to the elbow. Each finger joint (base, middle, tip) then curls until its own skin touches the tube. The thumb swings across to the driver's side of the rim and curls on. Nothing passes inside the bakelite. The left hand holds near ten o'clock; the right, on Sora's side, near three and a little looser.
- **Arms:** reach to each solved wrist, and the hand bone turns the same way so the sleeve's forearm twist follows. Eric's hands are cut away at the cuff plane, along with any loose finger left past it. The sleeve end gets a folded 3.5 mm hem and a lining 2.5 cm up the sleeve.
- **Shapes:** every arm shape (`steer_left`, `steer_right`, `grip_tense`, `breathe`, `lean_peer`) re-solves the grip, so the hands move with the rim and clench into it. The near hand adds `grip`: its index and middle fingers lift off the rim. `taxiDriverFace` already drives `grip` as he talks, and before this pass nothing played it.
- **Skin:** the scan's photo colour is re-toned to his weathered brown (luminance and a little of its own redness kept, broad patches evened out, forearm hair softened). Its scanned normal map keeps the creases, veins and nail edges.
- **Krama:** a 1.3 × 0.26 m krama (a man's krama folded once lengthwise) is laid round the nape in loose pleats. It is cloth-simulated for 90 frames onto his body, neck and collar, then subdivided and relaxed. It follows his breathing and leaning through a surface-deform binding to the body's shapes. The weave is generated: red-and-cream gingham with 12 mm checks, per-yarn dye variation, a striped border and a plain heading at each end, and eleven knotted tassels per end.
- **Collar:** a 2.6 cm cotton stand collar, open 3 cm at the throat, replaces the old lofted ring.
- **Clothes:** the linen weave squeezed into the whole-body atlas, and the drawn twill on the waistcoat, only aliased into a fuzzy "felt". They are gone, and the scan's own folds and seams carry the cloth.

The cultural advisor should review the krama's pattern and how it is worn (V1-242).

**Smoothing pass, same day.** After the first look the user said it still was not smooth. Close-ups from Sora's seat found:
- **Jaw and neck:** the photoscan's jaw, under-chin and neck were coarse polygon facets. A Taubin smoothing (shrink, then swell, so the jaw keeps its volume) eases everything below the ear lobes, leaving the lips, chin front and ears as scanned. The face's relief map drops from 0.55 to 0.40, because it lit the jaw's UV seam as a bright scratch.
- **Collar:** the stand collar had been aimed from a centre that drifted toward the turned jaw and flared into a plate. It is now sewn onto the shirt's own neck opening, which is smoothed as one loop. An older step had pulled only the opening's edge vertices in, which left shards.
- **Krama:** it starts flatter and untwisted, as stiffer cotton, settles for 120 frames and is relaxed more, so it drapes instead of crumpling.
- **Cuffs:** the old cuff lip came out as a zigzag on the cut's uneven vertices, so it is off for the scanned hands. Wherever the posed scanned wrist would cut through the sleeve's last 6.5 cm, the sleeve is let out to 5 mm clear of it, and the hem is grown only after the forearms are tailored.
- **Hands:** skin weights are diffused over the skin (no lumps at the knuckles), the rim-contact push spreads over the pad instead of dimpling single vertices, and the relief is blurred so the forearm hairs stop glinting under the cabin light.

**Elbow and krama pass, same day.** The user flagged the far arm and the krama in a crop from Sora's seat:
- **Elbows:** the wheel sits close, so his elbows fold to about 70°. Plain skinning collapsed the inside of each sleeve: the forearm pushed through the upper arm in a hard edge and a balloon. A corrective smooth against the scan's rest shape (`ElbowRelax`, weighted 7–17 cm round each elbow) now relaxes the elbows in every pose.
- **Sleeves:** eased toward the arm bones to a real shirt sleeve's width (5.6 cm round the upper arm to 4.4 cm at the forearm), in each shape with that shape's own arm.
- **Cuff hem:** it folds toward the opening's own centre, because folding toward the wrist joint turned part of it out as a flap.
- **Left hand:** rides a little lower, at about twenty to ten.
- **Krama:** its weave is now one seamless 7.2 cm tile (6 × 6 checks) repeated along the cloth, about 7 texels per millimetre, shipped as UASTC. The single stretched image had gone soft in game. The fringe is 22 knotted, three-sided tassels per end.

**One real man, same day.** The user said he still did not read as a real person (face and skin, body and clothes, hands), and chose to rebuild from the existing scans:
- **Skin:** the old head bake's curve had left him spray-tan orange (about 1.36 : 0.86 : 0.58). Face, neck and hands now share one Khmer brown (`SKIN_CHROMA`, 1.27 : 0.93 : 0.70). Each texture keeps its own variation: rosier lips, darker creases, stubble. At runtime the translucency tint is blood-red rather than orange.
- **Head:** scaled to 93% about the neck base, because the scanned head read large, doll-like, on Eric's shoulders.
- **Neck:** carries his own jaw skin (pores, fine stubble) tiled round it, with stronger neck muscles and Adam's apple.
- **Cheek creases:** two diagonal creases on each cheek (from the scan's hoodie strings) are relaxed in shape and repainted as softened skin with his jaw's pores, and the relief there is flattened.
- **Collar:** the generated stand collar is gone. The scan's own shirt, tie and waistcoat show in the V, and the krama covers the neck opening.
- **Clothes:** at runtime a cotton-drill detail map (`makeClothWeave`) gives the shirt, waistcoat and cuffs a woven surface up close.
- **Grip:** resting fingers only meet the rim, and fear squeezes; the left hand is a little looser too.

## Hands and krama rebuild, 27 Nov 2026

The user said the driver was "still not good at all" and named the krama and the hands as the weak parts.

**Hands.** The raw scan was never the problem: rendered on its own it is a real, finely detailed hand. The posing was.
- **Skinning:** dual-quaternion skinning swells every joint it bends far, so at 90° each knuckle of the fist ballooned and the back of the hand read as one swollen bulb. The hand now uses optimised centre-of-rotation skinning (Le & Hodgins 2016). Each blended vertex turns about the centroid of the skin whose weights resemble its own, a point on the joint's axis, so the knuckles, tendons and the back of the hand keep their scanned shape.
- **Grip:** each joint used to curl in turn until it touched the rim, so the index and little fingers stayed straight at the knuckle and bent 80–90° at the middle joint, a claw. A finger now curls as a real power grip does: its three joints move together (base : middle : tip = 0.62 : 1 : 0.66) until the middle and end phalanges meet the bakelite. The ring and little fingers of the looser right hand lie a touch open.
- **Skin:** the scan's pale forearm hairs glinted as white specks. Every bright fleck is now lifted out of the colour map, and the relief is blurred a little more. The broad tone-evening measures covered skin only (the UV atlas is rasterised to find it). It used to bleed the padding's tone into each island edge, which drew a lighter band across the left hand's fingers.

**Krama** (`build_rolled_krama`). It used to lie on his shoulders as a flat, stiff sheet, like a bib. Now it is worn as Khmer men wear one: folded lengthwise and rolled into a soft, uneven, twisted roll.
- The roll lies over the shirt's collar opening round the back of the neck. Its path follows the body mesh's own opening ring, so it also hides the neck seal.
- At the collarbones it unrolls into two ends that hang down his chest in loose vertical folds, the left one longer.
- The roll is built as a real spiral of cloth (4–5 turns of the 26 cm folded width), its outer edge winding round about every 24 cm, unevenly. It holds its shape (pinned in the simulation), while the ends are cloth-simulated onto his chest and belly.
- The weave is old hand-loomed cotton: 16 mm checks of faded madder red and unbleached cotton. The bands differ slightly in width as on a hand loom, with a thin dark line in each red band, uneven dye lots, slubs and sun-fading. One seamless 9.6 cm tile repeats along the cloth.
- Twenty knotted tassels finish each end, found from the cloth's UVs.
- It still follows his breathing and leaning through the body's shape keys.

The cultural advisor should still review the pattern and how it is worn (V1-242).

**Sleeves, same day.** His sleeves are rolled up to mid-forearm, as a driver's would be in Phnom Penh heat. The stiff cuff at the wrist had read as paper, so now 12.8 cm of the scanned forearm shows, tendons and all. Each sleeve is cut square to the forearm 9.3 cm above the wrist. Its edge is rolled outward and back up the arm into a soft cotton band, about 4 cm wide and 1 cm proud, uneven round the arm. The band wears the cuff cotton, toned to the shirt's own colour at the sleeves.

**Fixes found in the game.**
- **Inside-out body:** recalculating normals guesses "outside" for an open shell, and the rolled bands tipped the guess, so the whole body shell came out inside-out (hollow shoulders). Each connected piece is now checked against his torso and turned outward. `taxiAssets.test.ts` fails if less than 80% of his torso faces outward.
- **Krama ends:** the hanging ends start in front of his outermost layer, since one started straddling the waistcoat's open edge and the simulation dragged it under. They collide double-sided with the body only.
- **Rim size:** the grip uses the rim mesh's measured size (centre line 0.1974 m, tube 12.7 mm).
- **Steering wheel:** the driver's left forearm lies along the lower-left rim and crosses a spoke, and posing the arm clear of it read worse. At the user's call, only that part of the wheel is hidden (`cut_wheel_inside_driver`): on his left, every rim, spoke and spoke-cap face his clothes pass through in any of his shapes, each shape tested with the wheel turned as that shape holds it. The rim cut becomes one arc, from under his sleeve into the middle of his left fist (`_rim_cut_into_fists`), so neither end shows as he moves. The left spoke keeps its length up to where his sleeve covers it at rest: it is sliced 4 mm inside the sleeve and capped (`_trim_spokes_at_sleeve`), so the wheel still shows all three spokes. His right cuff only grazes the rim in a few shapes, so that side stays whole. From Sora's seat the wheel reads whole, the rim running into his fist and behind his forearm. Each wheel part keeps an untouched copy in the blend (`<name>__full`) and is cut from it afresh on every build.
