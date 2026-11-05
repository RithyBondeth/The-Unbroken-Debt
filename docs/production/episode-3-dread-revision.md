# Episode 3 · forest, contact and human anatomy revision

This pass replaces the exposed, lightly dressed lake setting with an enclosing
flooded forest and a colder storm look. It remains on
`bondeth/episode-3-drowned-village`. Episode 1 supplies the shared storm, rain,
lamp falloff and material references; Episode 2 supplies the CC0 MakeHuman source
anatomy. Shared Episode 1 code is unchanged.

## Environment and physical contact

- 143 trees enclose the market and clinic, with submerged roots, reeds, broken
  trunks and a separate distant belt. Tree height is measured from the imported
  mesh rather than inferred from its object scale. The boat channel and playable
  roof routes remain clear.
- The market has broken overhead timber, torn side screens, hanging nets,
  supported fish traps and small oil lamps. Its opening uses cool overcast light,
  rain and fewer birds rather than a bright afternoon wash.
- 337 imported props are placed using their actual lower bounds and explicit
  support heights. Books and vessels use their furniture's measured top surface.
  `ep3-support-audit.json` records this authoring check; it is not a claim that
  every handmade mesh has undergone a physics simulation.
- All six story documents now sit on measured table surfaces. The letter,
  return note and reception key have small timber stands where the original
  scene supplied no support. Ink follows its page and interaction owner.
- All seven moored boats now have keels at −0.22 m against the lake's −0.08 m
  surface. The playable rowboat also sits lower. Oars and boat dressing follow
  the adjusted hulls.
- Rain continues outside clinic windows while Sora shelters indoors. Water uses
  irregular noise gradients over the existing physical reflection/refraction
  material, with larger storm waves. Wet timber catches restrained highlights.

## People

All nine actors are rebuilt from the shared source anatomy. They now have real
sclera, iris and pupil geometry fitted to the original eye bones, photo-based
skin, fitted hairlines and layered wet hair. Pich uses MakeHuman child targets
instead of a scaled adult woman. Loose shirts, folded lower garments and child
shorts replace the painted, skin-tight clothing silhouette. Blink and pose
targets retain their neutral default weights; whole-root idle tilting is removed
so feet stay planted.

The child targets' official URLs and SHA-256 values are recorded in
`art-source/characters/ep3/sources.json`. No third-party ghost models from the
workspace's untracked directories are included in this revision.

## Rebuild

Run from the repository root with the existing shared CC0 library available:

```sh
python3 tools/ep3/fetch-character-source.py
blender -b --factory-startup -P tools/ep3/build-village.py
npm run export -- ep3
npm run assets -- ep3
node tools/ep3/finish-village.mjs
```

For an existing source, substitute the full Blender build with:

```sh
blender -b art-source/blender/ep3/ep3_area_village.blend -P tools/ep3/rebuild-realism.py
```

Both paths rebuild the anatomy, garment, forest and support layers. The saved
Blender source contains the final canopy transforms. `finalize-dread.py` and
`sync-forest-transforms.mjs` support an incremental canopy-only update without
recompressing the texture payload; normal exports do not require that repair.

The optimized area is approximately 65.2 MB, plus the existing 4.3 MB cloud HDR.
Editable source geometry and textures remain available. This is still a web-game
asset set; the captures document its actual detail rather than promising film
photorealism or a cross-device frame rate.

## Checks

`villageAssets.test.ts` checks exported prop contact, planted forest crowns,
submerged boat keels, all nine actors' eye assemblies and neutral morph weights,
lamp support, shirt coverage and story-document footprints.
The review fixture's **Inspect rendered assets** button verifies the loaded eye
assemblies, forest roots and compiled water plugin. Actual browser captures from
this pass are in `evidence/2026-11-03-dread/`; route and story results are recorded
in `episode-3-verification.md`.

The final close-up check removed a cloth copy of hands held in front of the
torso, rounded the shirt fit, lowered Pa Lok's lamp onto the measured stool top,
and removed an obsolete second curtain of Kanha's hair. `refine-people.py` applies
the actor/support changes to an existing source; the normal build includes them.
`refit-clothing.py` reconstructs garment topology on the existing indexed poses,
using the anatomical chest, shoulder and arm regions. Higher waist wraps overlap
the shirts. Shape coordinates are written in bulk to avoid a scene-wide Blender
update for every vertex.
`fix-document-supports.py` applies the paper/support pass to an existing source.
