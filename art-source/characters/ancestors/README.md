# Ancestral guardian forms

Original forms guided by the four village-shrine photographs supplied by the user: aged seated human figures, faded green mineral paint, charcoal facial details, saffron cotton and accumulated weathering. The standing apparition shares the same sculpted face and material treatment as the seated shrine figures. The primary face has a contracted lower brow, firm jaw and downturned mouth; it is an angry, still effigy.

- Editable source: `ancestor-forms.blend`, with packed maps and three named collections.
- Runtime standing form: `public/assets/ep1/neakta_shadow.glb`, foot origin, facing +Z in Babylon, height 2.5 metres. The encounter scales it to 2.3 / 1.87 metres where required.
- Seated forms: appended from this source by `tools/areas/shrine.py` into the authored village. The larger statue retains `neakta_stone_watch` and its offscreen turning behaviour.
- Anatomical face, ears, hands and fingers are modelled geometry. The eyes are inset behind eyelids. Mineral paint and fine surface relief are image-backed. Lap cloth is settled against anatomical collision geometry and a stone-seat support, then baked; the game runs no cloth or skeleton simulation.
- Three encounters share one loaded asset and its GPU geometry/materials. All forms remain non-pickable.
- The standing apparition is the **black Neak Ta** (user direction, 26 October 2026). `ShadowFigure.prepare`
  multiplies the shared mineral paint down to soot-black lacquer, keeping its mottling and relief, with a dull
  sheen so the lamp still finds the face. The chalk eyes and the cotton are unchanged. The seated shrine
  statues in the village keep their pale paint, because only the encounter asset is darkened.

## Rebuild

Run from the repository root:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b -P tools/characters/build-ancestor-forms.py
npm run assets -- ep1/neakta_shadow.glb
/Applications/Blender.app/Contents/MacOS/Blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/areas/rebuild-shrine.py -- /tmp/ancestral-shrine.glb
node tools/areas/update-shrine-glb.mjs public/assets/ep1/ep1_area_village.glb /tmp/ancestral-shrine.glb public/assets/ep1/ep1_area_village.glb
```

For a production asset pass, compress the focused shrine export before merging, using the same KTX2/meshopt steps as `tools/build-assets.mjs`. The merge preserves unrelated village geometry and compressed materials. The full village builder calls the same shrine functions.

Paint maps are cached in this directory. Delete `effigy-painted-BC.png` and `effigy-painted-N.png` before rebuilding if editing the spatial paint recipe. The build writes neutral inspection renders to `/tmp/ancestor-standing-inspection.png` and `/tmp/ancestor-seated-inspection.png`.

## Provenance

Anatomy, ethnic/age/muscle morphs, pose weights and aged skin input use the project's existing CC0 MakeHuman sources, described in [Sok's source notes](../sok/README.md). The aged skin supplies subtle facial surface variation underneath authored mineral paint; these are separate original ancestral characters. Woven normal relief uses the existing CC0 Poly Haven `rough_linen` library material. The pose, angry facial sculpt, cotton geometry, painted weathering and shrine composition are authored for this project.

The user's photographs are study references; they are not shipped as textures or exact copies of a sacred sculpture. The earlier Dementor study is superseded for the character's identity by these village references.
