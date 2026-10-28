# Sketchbook portrait atlas

`people-graphite.png` is original AI-generated artwork created for The Unbroken
Debt with the built-in imagegen tool on 2026-10-28. No external portrait image
was supplied. Direction follows the character descriptions in the project's
Art Bible: Cambodian people, 1931, graphite life studies on transparent ground.

Atlas quadrants: top left Sora, top right Yay Mey, bottom left Uncle Sok,
bottom right Vuthy. The runtime copy is in `public/assets/ep1/notebook/`.
Canvas multiplication lets the graphite sit on the book's own paper texture.
Keep full transparent RGBA; do not flatten against white.

`sok-funeral-photo.png` was edited with imagegen on 2026-10-28, using the atlas's
bottom-left Sok study as the identity reference and the previous funeral print
as the mount/style reference. It replaces the historical archive man's likeness.
The standalone runtime photo, the village GLB's embedded photo, and the packed
Blender image are updated together. `tools/areas/update-sok-photo.py` updates the
packed source; `tools/replace-glb-image.mjs` replaces just the GLB's image payload
without re-exporting geometry or recompressing unrelated textures.
