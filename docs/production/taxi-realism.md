# Taxi scene visual pass

The Studio → Village ride uses authored cabin and landscape assets in the same Babylon scene renderer as Act I. The journey lasts 72 seconds, with eight-second autosaves, resume and an atomic CP1 arrival checkpoint.

## Art and motion

- The roadside uses the village's actual trees, coconut and banana palms, bamboo, ferns, shrubs, bark, leaf, forest-floor and mud materials. A single 540-metre curved route covers the whole ride and visible horizon, without recycling scenery. The car follows its centreline and tangent so bends and near/far parallax stay coherent. Trees are scattered in irregular groves, and leaf materials have small, unsynchronized wind motion. A crowned mud track, wheel ruts and standing water replace the flat strip of road.
- The cabin has a curved headliner and dashboard, textured worn vinyl with normal/roughness maps, teak veneer, padded seats with piping and pleats, cranks, trim, glovebox, radio, analogue instruments, sunvisors and a reflected rear-view mirror. An opaque floorpan, firewall, rear bulkhead, lower body and overlapping lining seal the footwell. The padded dashboard shell sits behind the wood fascia, keeping the gauges and controls visible; an occlusion regression protects this placement. Grooved rubber mats, pedals, heater grille, door pockets, sill fasteners, pull switches and engraved labels add close-up detail.
- The seated driver derives from the same CC0 MakeHuman source library already used for Sok, with a neutral expression, a different age blend, anatomical eyes, cotton clothing and a baked steering pose. The driver has photo-derived skin relief, a fitted cloth cap, sewn cuffs, collar leaves, a shirt placket and chest pocket, and a small wristwatch. No runtime skeleton is required.
- Sora’s visible seated lower body uses her existing female MakeHuman source. Cotton travel trousers and leather flats remain visible when looking down; a small blouse hem seals the waist without covering the legs. Both feet rest on the passenger mat; the model stays attached to the seat as Sora looks around.
- The full route now has 494 broadleaf trees plus palms, bamboo and undergrowth. A decimated outer canopy closes gaps behind the near trees; distant batches receive lighting but do not add headlight shadow draws. Route chunks more than 80 metres ahead or behind are disabled, beyond both the forward and rearward viewing ranges.
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

Validation: `npm run check` passes TypeScript, ESLint, 355 unit tests and the production build. The final regenerated landscape also passes all eleven asset regressions. A fresh 72-second browser ride completed without skipping, reloaded into CP1 at Village · Flooded road with ten matches intact, and enabled the early-encounter requirement. No console errors were recorded. Browser captures and the arrival report are in `docs/evidence/taxi-realism/`.

The cabin/continuous-route/monsoon follow-up is captured in `docs/evidence/taxi-cabin-storm/`.

## Passenger and conversation follow-up

The ride contains a 14-line, subtitle-only conversation: seven lines for Sora and seven for the driver. It connects Yay Mey’s call, Sok’s funeral and the roadside presence, then explains the flooded-road stop. Lines have reading time and do not overlap; the apparition has a quiet gap. Selection uses the ride clock, so reloads and timing jumps show the current reply rather than queuing old lines. Subtitle timeline updates cancel stale timed subtitle work.

Tests cover speaker balance, reading time, line selection after resume, stale subtitle cancellation, feet resting on the floor, unobstructed views of both shoes and forest density. Sources remain in `tools/travel/build-taxi.py`; conversation text is in `src/episodes/ep1/travel/taxiConversation.ts`. Evidence for this pass is in `docs/evidence/taxi-passengers/`.
