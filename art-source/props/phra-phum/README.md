# Wooden household effigy

Original carving for the Phra Phum checkpoint. This replaces the miniature
human ancestor model. The face, fingers, folded robes and seated legs are
carved as rigid timber, with hollow eye sockets and real incised splits.
There are no skin, fabric, eyeball, skeleton or breathing assets.

`shrine-effigy.blend` is the editable source, including the wooden head's neck
pivot, integral plinth and packed 2K colour/normal atlases. The continuous grain
uses the project's existing CC0 `dark_wood` library photograph, projected upright
before baking. See the library's attribution records. All geometry is original.

Rebuild from the project root:

```sh
blender -b --factory-startup -P tools/characters/build-shrine-effigy.py
npx gltf-transform dedup public/assets/ep1/phra_phum_effigy.glb /tmp/phra-effigy-dedup.glb
npx gltf-transform resize /tmp/phra-effigy-dedup.glb /tmp/phra-effigy-resized.glb --width 1024 --height 1024
npx gltf-transform meshopt /tmp/phra-effigy-resized.glb public/assets/ep1/phra_phum_effigy.glb
```

The game wrapper faces the carving toward the +Z doorway. Asset feet are at
Y=0, overall height is about 48 cm, and the rigid head joint is at Y=0.331 m. One rough wood material covers both meshes. The resulting
GLB is about 2.5 MB. Runtime saving turns the carved head while the body remains
still; its hollow sockets never become human eyeballs.

## Aged wooden spirit house

The current shrine follows the modest household direction: one plain pitched
roof, a rectangular doorway, rough reused planks, a hewn support post and small
repair cleats. There are no ceremonial tiers, spire, ornate reliefs, gilded
trim, balustrades or flower chains. The older generated image remains an aged
wood and lighting study; its elaborate silhouette is superseded.

`PhraPhum.ts`, `ShrineWoodwork.ts` and `ShrineAgeing.ts` build the shelter,
physical splits, sparse lichen, a corner cobweb and candle wax. A plain clay
bowl carries three incense sticks; two candles sit in clay dishes. The wooden
effigy and the unsettling save response remain.

The 1K runtime maps under `public/assets/ep1/phra-phum/` come from the existing
Poly Haven `weathered_brown_planks` material: Dimitrios Savva and Rico Cilliers,
CC0 1.0, already recorded as V1-109 in the asset tracker. The source files are
under `art-source/library/materials/weathered_brown_planks/`; `npm run fetch-library`
restores them. BC is sRGB, N is OpenGL tangent-space normal, and ORM packs
occlusion in red, roughness in green and metallic in blue. The three runtime
files total approximately 0.9 MB. Materials share these maps; every individual
piece receives metric UVs along its long axis before merging.

To restore the runtime copies on macOS, from the project root:

```sh
for map in BC N ORM; do
  cp "art-source/library/materials/weathered_brown_planks/weathered_brown_planks_${map}.jpg" \
    "public/assets/ep1/phra-phum/aged-timber-${map}.jpg"
  sips -Z 1024 "public/assets/ep1/phra-phum/aged-timber-${map}.jpg"
done
```

One candle casts a 512px or smaller shadow cube on medium and higher presets,
cached until the carved head moves; low uses the same two flickering candle
lights without a shadow map. The caster list contains only shrine geometry.
The interaction cue is restricted to the clay offering vessels, preserving
the wood and lighting when the whole shrine is focused. Checkpoint reach,
storage and response timing remain the same.
