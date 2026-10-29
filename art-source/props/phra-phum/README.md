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
