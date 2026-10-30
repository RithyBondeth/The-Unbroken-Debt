# Krasue kitchen window encounter

The spirit is a repeatable nighttime obstacle outside the kitchen's west window
(the opening beside the hearth and bottle shelf) and its front/south window.
`data/krasue.ts` records their real Blender-to-game opening coordinates.

The Krasue detects an exposed player through the opening after 0.28 s of clear
sight, independently of the player's camera direction or open inventory. At that
moment it screams once and turns toward Sora. A short 0.38 s wind-up (0.26 s with
an exposed lamp) leads into a rush that accelerates from 0.8 to 6.2 m/s. Charging,
searching, reacquiring the same target and lethal contact do not replay the scream.
Moving behind the wall or leaving the kitchen breaks sight and prevents a kill;
a later, rearmed encounter may scream again.

The spirit always remains outside, including during the attack. Its head origin
stops 75 cm beyond the exterior plane; animated geometry never reaches the
wall. A short visible strike at the opening kills an exposed player and invokes
the existing checkpoint retry flow. It does not enter or pursue through the house.
The lamp is not required to encounter it, and missing audio does not disable it.

Sight requires a segment through the 80 × 95 cm aperture, a player in the kitchen,
and a clear Havok ray through the actual room colliders. This avoids both kills
through walls and triangle-by-triangle raycasts against the forest. Wardrobes
conceal Sora. Story cutscenes and other active threats take priority. Hidden tabs
and lost mouse lock suspend encounter progress and stop sound immediately; dawn
stops it completely.

The original synthesized, peak-limited audio uses the threat bus with HRTF panning.
The lament follows the world position, rising as the spirit watches; a rising
breath/shriek follows its attack. Assets are original, with no stock media copied.
The sculpted 3D GLB, 101-bone rig, dense layered hair and source are documented in `art-source/characters/krasue/README.md`.

## Verification

`npm test -- --maxWorkers=2` includes aperture, patrol, warning, cover, attack,
exterior geometry, repeat visit, frame stall and audio tests in `krasue.test.ts`.

Open `/tests/browser/krasue.html?start=act1` for the production village, physics,
night lighting and isolated `boon-sop-krasue-verification` save database:

- Kitchen window / Front window: exterior views through each real opening.
- Creature detail: closer optical view; the creature stays outside.
- 3D turntable: rotate the solid creature to inspect front, sides and back.
- Verify 3D hair and organs: sample actual skinned vertex positions across frames.
- Verify escape behind wall: detect, warn, rush, take solid cover and release gates.
- Face the Krasue: allow the actual attack, death and checkpoint retry flow.
- Play positional sound: opt-in lament followed by the attack shriek.
- Save screenshot: capture the production render in `debug-shots/`.

Add `&automation` when the browser cannot provide native pointer lock. This
fixture alone supplies focused input while its scripted scenario runs; production
visibility, physics, state transitions and death/retry handling are unchanged.
It does not use or overwrite normal player saves.

Full-volume revision on 2026-10-30 replaces the former image relief entirely.
The loaded GLB has a closed sculpted head, inset facial features, tubular hair,
separate lobed organs and intestine meshes, all opaque and skinned. Its exterior
patrol spans 2.1 m sideways, 1.7 m in depth and 44 cm vertically. Flight heading
turns its solid profile into view, while suspicion turns it toward the player.
The standalone Blender front/profile renders prove the skull, nose and organ
volume; the browser fixture verifies real skinned vertices move independently.

`tests/unit/krasueAsset.test.ts` verifies head depth, opaque materials, independent
joint chains, normalized skin weights, organ meshes and a 250,000-triangle ceiling.
The new model retains the existing positional lament, warning, attack, cover and
checkpoint mechanics. Full-suite baseline remains two unrelated courtyard test
fixtures missing their telephone-cord mock; these are outside this revision.

Final verification: TypeScript, scoped ESLint, production build, and 44 focused
tests passed. In the actual WebGPU house fixture, the runtime vertex sampling
check passed for hair and intestines independently. The real window sight ray,
warning, rush, solid-wall cover and release of the threat gates all passed with
the 3D model loaded. The head asset also passes a welded-edge manifold check:
every edge belongs to two triangles. This rules out a two-sided image surface.

Natural-motion revision on 2026-10-30: `KrasueDynamics` supplies damped pendulum
joints driven by actual velocity, acceleration and turn rate. The hair roots stay
anchored; light tips respond first; heavier guts lag and settle after braking.
Small non-uniform gusts provide rest motion. Teleports and background stalls clear
stored energy, and 1/120 s integration substeps keep the motion stable across frame
rates. All bending remains within bounded angles outside the wall.

The rebuilt mesh has smoothly curved fine strands with varied cuts, taper and
flyaways, a curved hairline, coiled intestinal loops, folded mesentery and tracheal
ridges. Linear vertex pigments add tissue mottling; opaque PBR materials include
normal detail and a restrained wet coat. All textures and geometry remain in the
self-contained GLB and editable Blender file.

The browser fixture's encounter buttons now initialize and unlock the production
audio before starting, so the detection scream cannot be missed during audio
setup. `krasueEncounter.test.ts` verifies positional playback at detection, exactly
one scream per sighting, reacquisition without duplicates and stopping on tab
hiding. `krasueDynamics.test.ts` covers inertia, heavier gut response, anchored
roots, braking/settling, frame-rate consistency and teleport/stall resets.

Natural-motion verification: 53 focused tests passed, plus TypeScript, scoped
ESLint and the production build. Both real kitchen windows passed the browser
check for detection, exactly one active positional scream before the accelerating
rush, solid cover and release of the threat gates. The browser's skinned-vertex
check passed for the damped hair and intestines. The fixture also starts audio
when either encounter button is pressed, so no separate sound-preview step is
required.

Facial articulation revision on 2026-10-30: the closed skull now contains a
recessed oral bowl, raised lips/eyelids, deeper sockets, sculpted creases, tongue,
gums and separate dental arches. A `Scream` glTF morph deforms the jaw, cheeks,
chin and lip margins while preserving rigid teeth. `KrasueExpression` follows
the production shriek's 2.4 second timing, using the same detection timestamp
even when audio is unavailable. Mouth opening never re-triggers on reacquisition.

Rush drag is stronger than patrol drift. The joint transform now uses full rest
matrices to preserve the glTF handedness reflection; dropping that reflection
would make strands bend in front of travel. The browser fixture checks actual
deformed hair and intestinal tip coordinates during a westward rush. Measured
trailing displacement was 0.22 m for hair and 0.07 m for the heavier intestine.
The editable source and GLB are rebuilt together; the asset tests cover jaw
displacement, rigid teeth, sealed skull geometry and the 250,000 triangle cap.

Final articulation verification: 56 focused tests, TypeScript, scoped ESLint and
the production build passed. Both live kitchen-window encounters passed the
audio, jaw-opening, accelerating charge, solid-wall cover and threat-release
checks. The actual skinned-tip trailing check passed after the matrix correction.

Fine-strand hair revision: hanging solid lock volumes are removed. The mane is
2,592 individually rooted, tapered geometric fibers, spread through 18 weighted
motion groups. Root angles, lengths, wave phases and thicknesses vary; flyaways
and uneven ends soften the silhouette. A matte fitted root layer covers the
scalp between the fine fibers. Each fiber uses nine rings and a triangular
cross-section, preserving the existing 250,000 triangle budget. Runtime flight
and jaw behavior are unchanged.

Fine-strand verification: the exported asset contains 2,592 fibers, zero hanging
solid hair cores and 244,416 triangles. All 27 Krasue tests and the production
build pass. In the actual WebGPU fixture, the deformed hair tips trailed the rush
by 0.37 m and the intestine by 0.03 m; the browser reported no console errors.
