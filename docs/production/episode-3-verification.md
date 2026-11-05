# Episode 3 verification · 3 November 2026

Branch: `bondeth/episode-3-drowned-village`.

## Automated checks

- `npm test -- --maxWorkers=1`: all 487 tests in 91 files pass, including 10
  new chapter-state, continuation, numeral-puzzle, choice, warmth and water-spirit
  checks. An earlier run with active rendering and asset builds timed out in an
  unchanged audio-synthesis assertion; the quiet rerun passed without changing
  its timeout or assertions.
- `npm run typecheck`, `npm run lint`, `npm run build` and `git diff --check` pass.
- Prettier passes for every changed Episode 3 source, fixture and finishing tool.
  The repository-wide formatting command also includes concurrent Episode 2 work;
  its unrelated `tools/drawings/ep2.mjs` was left untouched.
- Blender generation, export and texture/mesh optimization complete. The shipped
  area after the composition revision is approximately 63.4 MB, with the actual `.blend`
  source and texture maps retained.
  The lettering finishing tool reports zero changes when rerun.

## Real browser and physics

The Medium production scene loads with 193 colliders and 27 interaction roots.
The separate review database leaves player saves untouched. The following routes
pass with the real Havok character, including supported footing at their ends:

1. Market main walkway.
2. Pa Lok’s raft connection.
3. Clinic landing and descending entrance slope.
4. West stair to the doctor’s quarters.
5. Attic doorway onto the upper veranda.
6. North-east ramp into the cellar.
7. First rising roof bridge.
8. Second rising roof bridge.
9. Final bridge to the last standing stilt.

Actual production rays reach the reception fuse, generator, iron safe and
purification bowl. The bowl is measured from within the shared 1.8 m reach;
none of the interaction ranges were enlarged for the test.

The first physical pass identified a stair obstructed by a partition and an upper
floor edge. The final scene has a real stair opening and a clear attic doorway.
The roof pass identified flat platforms forming lips across the sloped bridges;
four matching sloped hip joints replace those platforms. The final full route
and ray fixture passes.

The scripted journey verifies progression separately from those physical routes.
The final journey passes through the actual rescue interaction and verifies the
stored Episode 3 completion archive, compass and inherited Water-trial choice.
Dialogue decisions and cinematic skipping are controlled test inputs. Rowing uses
the actual alternating-oar key listener and production frame-driven docking.
The safe uses actual dial operations; export/import uses the real save codec.
These checks do not establish the specification’s intended 1.5–2 hour human
playtime or replace a full difficulty/balance playtest with live threats.

High-preset water/reflection and Kanha/Pich staging were rendered and inspected;
the Low-preset flooded ward also rendered without shader errors. Captures are in
`evidence/2026-11-03-ep3/`. These observations cover this machine, not a
cross-device frame-rate benchmark.

## Realism revision

The revised High-preset scene passes the same nine physical routes and four
interaction-ray checks. It retains 193 colliders and 27 interaction roots.
Indoor reflections, cloth, scanned beds, roof undersides and lamp dressing were
checked in the production renderer. At the settled ward view, the diagnostic
reported approximately 176 draw calls and 0.51 million triangles across passes;
this is a view-specific observation on this machine, not a performance guarantee.
New captures and the previous ward baseline are in
`evidence/2026-11-03-realism/`.

The final art export also passes the production story journey, including actual
row inputs and the Episode 3 completion archive. The market was inspected at
Medium and the clinic/spirit views at High. Desktop and narrow panel views retain
the same geometry and equipment; the temporary desktop viewport test was reset.

## Composition and final continuation

The composition pass also verifies all nine routes and six production rays:
reception fuse, generator, safe, purification vessel, first candle and mother
choice. The replacement scanned vessel is parented to `interact_purify` before
static batching; the first ray pass exposed its missing interaction ownership.

The final continuation corrects the detail boxes' rotation pivots in both the
editable Blender file and the optimized area. It also fixes flame rendering,
preserves the ritual mat's weave under candlelight, expands the sky beyond the
lake, and checks water shaders at High and Low. Updated production captures are
in `evidence/2026-11-03-composition/`.

`npm test -- --maxWorkers=1` passes all 487 tests in 91 files again (35.22s).
An earlier loaded-machine run timed out in the unchanged taxi asset bounds check;
the rerun uses the original timeout and assertions. Vite now scans review fixtures
at startup to avoid duplicate Babylon modules; each review tab has an independent
session database to avoid setup-save races on simultaneous reloads.

After the final pivot, sky, water and character-material changes, the High-preset
fixture passes all nine physical routes and all six rays again. The final
production build, typecheck, ESLint, changed-source Prettier and `git diff --check`
also pass. Episode 1's `StormSky.ts` still matches `main` byte for byte; only the
Episode 3 instance is enlarged to enclose its open lake.

## Forest, contact and anatomy revision

The current optimized area is 65,223,012 bytes (approximately 65.2 MB), plus the
existing cloud HDR. All nine actors use the reconstructed anatomy and complete
eyes; the forest contains 143 measured mature trees. The source and shipped area
include the final garment/hand and lamp-support corrections. The obsolete second
hair curtain is removed from both.

- `npm test -- --maxWorkers=1`: **494 tests in 92 files pass** (50.99s), including
  seven exported-asset checks for support contact, canopy placement, boat draft,
  lamp/stool contact, actor eyes/neutral morphs, shirt coverage and six story
  documents' height and footprint against their supporting surfaces.
- ESLint and the final production build pass; the build also runs TypeScript's
  no-emit check. Changed-source Prettier, Python compilation and `git diff --check`
  pass.
- The High fixture passes all nine real Havok routes and all six production rays
  after the forest and boat changes. The scripted production story journey also
  passes rowing, repairs, safe dials, memory, ritual, rescue and completion saves.
  The final subsequent art correction changes clothing, redundant hair and the
  supported lamp; it does not change colliders or interaction roots.
- The loaded High renderer reports all 18 eye assemblies, 89 near-forest roots
  and the compiled lake wave plugin. The other 54 trees form the distant belt.
- The final Low ward also loads all 18 eye assemblies and the compiled water
  plugin without console warnings or errors. The cellar letter's timber support
  is visibly present in `vault-supported-low.png`.

Fresh browser evidence is in `evidence/2026-11-03-dread/`. Wide ward, attic and
market environment captures precede the final hand/lamp correction; the final
character and water captures follow it. The final ritual captures also include
the complete shirt coverage and waist overlap. These are visual checks on this machine,
not a cross-device performance or historical-authenticity certification. A human
balance playtest with active threats is still separate from the scripted checks.
See `episode-3-dread-revision.md` for the art changes and rebuild instructions.
