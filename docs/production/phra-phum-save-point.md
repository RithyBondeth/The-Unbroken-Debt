# Spirit house outside the compound

28 October 2026. The Phra Phum stands beyond the compound's front-right fence
corner, at `(-15.2, 0, 10.5)`. Both its footprint and approach are outside the
fence (x = -13, z = 3). Reach it through the main gate, following the outside
of the front fence to the right. The former courtyard desk and shrine are gone.

The current direction is a modest early-1900s family spirit house, built from
reclaimed timber. One plain pitched plank roof covers a rectangular doorway;
three simple gable boards close its front. A single hewn post, two braces and
a reused stone support a plank offering tray. Small replacement boards and
repair cleats suggest the household maintains it with available materials.
The ornate roof tiers, wings, spire, floral carving, ochre trim, balustrades
and hanging flower chains have been removed.

The wood retains photographed grain, worn surfaces, seasoning cracks, sparse
joint lichen and one corner cobweb. A small clay bowl holds three incense
sticks; two candles stand in plain clay dishes. Soot-stained individual back
boards keep the chamber recessed. Static pieces still merge by material.

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

`ShrineAgeing.ts` maps the wood grain along each separate timber's longest
axis before static merging. Three shared 1K maps provide colour, tangent-space
normals, occlusion and roughness (about 0.9 MB total). Sources and attribution
are recorded in the prop README; the effigy's independent baked atlas stays
unchanged.

Two candle lights sit at the actual wicks and flicker out of phase. The left
candle casts a shrine-only shadow cube on medium and higher presets, capped
at 512px and cached while idle. The map refreshes as the rigid head turns.
Low retains both candle lights without a shadow map. Both dim and recover
with the existing response; neither changes the player's lamp or the global
night lighting. The visual interaction hint stays on the clay offering vessels
while the whole shrine remains selectable, preventing the wooden shelter
from turning into a bright outline at close range.

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

The October 29 browser fixture also checks that all timber maps load, shadow
casters are restricted to the shrine, the focused hint leaves wood visible,
and both candle lights dim and recover during a successful save. Full and
close-up captures use the production renderer, not the generated reference.

The household version passes the production build, type checking and all 398
unit tests (`npx vitest run --maxWorkers=2`). Shrine files pass ESLint; full
project lint currently reports `require-await` at `tests/browser/text-system.ts:175`.
The browser route, interaction ray, save writes, both candles dimming/restoring,
danger blocking and failed-write recovery all pass without console errors.
The current full view is `debug-shots/phra-phum-household.png`.
