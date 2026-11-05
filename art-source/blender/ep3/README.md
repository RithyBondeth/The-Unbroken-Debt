# Episode 3 · The Drowned Village

`ep3_area_village.blend` is the editable, metre-scale production environment.
The scene uses the Episode 1 material library and Episode 2 MakeHuman anatomy,
clothing and first-person hand assets. Their existing CC0 source credits apply.
The lake shaders, teal plaster, corrosion, micro-normal maps and scenery are
original procedural work. No reference photograph is shipped as a texture.

The realism revision uses the shared CC0 scanned iron bed frames, furniture,
oil lamps and household props, together with original shaped bedding, gathered
muslin, medical dressing, joinery, flood damage and boat construction. Separate
base color, tangent-normal and ORM maps are in `textures/ep3/realism`.

The floating market and abandoned clinic share one streamed area, with separate
day/storm lighting. The scene includes the market, boats and raft, clinic wards,
raised dry routes, doctor’s quarters and stove, diesel pump, cellar, safe,
purification veranda and the three connected roof bridges to the last stilt.

Rebuild from the repository root:

```sh
python3 tools/ep3/fetch-character-source.py
blender -b --factory-startup -P tools/ep3/build-village.py
npm run export -- ep3
npm run assets -- ep3
node tools/ep3/finish-village.mjs
```

To refresh this detail layer on the existing scene, use
`blender -b art-source/blender/ep3/ep3_area_village.blend -P tools/ep3/rebuild-realism.py`,
then repeat export and asset optimization. The full builder includes the same
detail pass. See `docs/production/episode-3-realism.md` for art direction and
reference sources.

`src/episodes/ep3/data/village-layout.json` supplies gameplay coordinates to both
Blender and the game. Builder helpers convert X/Y-up/Z into Blender coordinates;
the authored axes root compensates the same Babylon glTF import convention as
the pagoda. Do not mirror the exported area again. Lettering has its own reflected
local X to read correctly from its intended approach; the finishing tool is
idempotent and handles older exports.

`col_` geometry defines Havok footing and walls. `interact_` roots retain the
production interaction targets, `light_flame_` markers place fixed safe lamps,
and the named `kanha`, `pich`, `npc_`, `collapse_beam_` and repair meshes stay out
of static batching so their authored parts can move. Thin roofing, ramp boards
and curtains render on both sides. Font curves are converted into mesh lettering
before export.

The runtime adds GPU water, weather, the rowboat, worked safe dials, first-person
equipment and memory tools. Water deliberately leaves openings under the wards
and cellar so the pump can expose the lower floor.

The composition layer is in `tools/ep3/cinematic_scene.py` and is included in the
same rebuild. The CC0 cloud environment is recorded in `sky-source.json`. See
`docs/production/episode-3-composition.md` for rendering details and author credits.
Blender sources save with lossless file compression.

The forest/contact/anatomy revision is documented in
`docs/production/episode-3-dread-revision.md`. `human_anatomy.py` reconstructs all
nine actors with fitted eyes, including child-specific MakeHuman targets for
Pich. `human_finish.py` adds loose clothing, hair and blinking. `dread_scene.py`
plants the measured forest, dresses the market and checks prop/boat contact.
