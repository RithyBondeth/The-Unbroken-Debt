# Spirit house outside the compound

28 October 2026. The Phra Phum stands beyond the compound's front-right fence
corner, at `(-15.2, 0, 10.5)`. Both its footprint and approach are outside the
fence (x = -13, z = 3). Reach it through the main gate, following the outside
of the front fence to the right. The former courtyard desk and shrine are gone.

The supplied reference guides the architectural silhouette: three steep,
stepped gables, two lateral roof wings, curved flame-shaped finials, a tall
ringed spire, and richly worked pediments. Closed wooden gable panels carry
raised flame branches, curling stems, leaves, beads and scalloped cornices.
The bargeboards and tapering finials are solid bevelled geometry. Overlapping
shingles have chipped ends; separate ridge caps and exposed rafters remain.
Faded red lacquer, tarnished gilding, dark timber, laterite brick, lime mortar,
cotton ribbons and withered flowers retain the requested old-house atmosphere.
Static architectural pieces, including the wings, merge by material.

The entrance has a shorter pointed arch, a carved rectangular lintel, recessed
jambs, layered floral relief and pierced scrolls. Both mirrored arch fronts
have outward-facing normals. Soot-stained individual boards and their joints
give the chamber depth without a featureless black backing.

`ShrineEffigy.ts` loads an original wooden statue, replacing the miniature human
ancestor. Its broad mask-like face, hollow eye sockets, incised mouth, fingers,
folded robes and seated body are carved timber. A single rough wood material
carries continuous upright grain, baked normal detail and real splits in the
forehead, cheek and chest. There are no skin, separate clothing or eyeball
materials. The head turns as a rigid wooden piece on a neck joint; the body
remains still. The preserved parent joint survives mesh quantization.

Editable source, maps, rebuild instructions and attribution are under
`art-source/props/phra-phum/`. The original geometry builder is
`tools/characters/build-shrine-effigy.py`; the 1K, meshopt-compressed runtime
asset is `public/assets/ep1/phra_phum_effigy.glb`, about 2.5 MB. The existing
forest ancestors are unchanged.

The maintained clearing keeps plants out of the shrine and its approach.
Generated plants respect the clearing; authored low plants whose crowns
intersect it are hidden before batching. Large trees and story props remain.

Press E within reach to pay respects and save. The write commits immediately;
then a 6.2-second response dims the candles, gives three spatial wooden knocks,
turns the carved mask towards the player, releases a cavity breath, and leaves
a low brass tail. Wildlife recedes temporarily. The hollow sockets remain
empty. Player movement, lamp and inventory do not change. Repeated input cannot
stack the response. Failed storage writes preserve the previous save and do
not perform a success response. Threats and cutscenes cancel the effect.

The isolated browser fixture `tests/browser/save-shrine.html?start=act1` offers
full views, an elevated roof inspection, doorway inspection, a real-controller
walk from the gate, actual interaction-ray saving, danger blocking, rejected-write
recovery and checkpoint reload. Roof inspection raises only the review camera;
walking, interaction and saves use the normal player height. The fixture uses
`boon-sop-phra-phum-review`, never player save storage. Add `&listen` for sound.

Validation covers roof geometry, finite normals and draw-call budgets, the
statue's physical size and pivot, complete wood maps, save concurrency, threat
blocking and storage-failure recovery. `npm run check` runs type checking,
ESLint, unit tests and the production build. Browser verification and captures
use the actual game renderer and its night lighting.

Verified for this revision: all 386 tests in 75 files, type checking, ESLint and
production build pass. In the browser, the real outside-gate route, interaction
ray, checkpoint write, danger block and failed-write recovery passed with the
new roof and wooden asset loaded. Roof and statue captures are saved under
`debug-shots/phra-phum-reference-roof.png` and `debug-shots/phra-phum-wooden-statue.png`.
