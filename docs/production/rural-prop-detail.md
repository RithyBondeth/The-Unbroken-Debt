# Rural prop construction and placement

The October 30 pass covers the storage shed's woven bamboo walls, both house
stair flights, stone post footings, spade, stored boards, hanging and grounded
fish traps, mourning ties and folded umbrellas. The materials remain modest,
weathered and appropriate to the family's early-twentieth-century household.

The shed panels now have actual interlaced split cane, a dark backing, framing
rails and rattan bindings. The stairs have separate tread boards bearing on
notched stringers, underside cleats, recessed nail heads and hand-worn rails.
Original gameplay ramps and collision volumes are preserved.

Grounded objects are positioned from their final mesh bounds after rotation,
with 2 mm ground clearance. This replaces origin-based placement for the
spade, umbrellas and three stored traps. Every plank in the stack touches the
one below it. Footing tops stay at 10 cm to meet the unchanged house posts;
photographed porous surfaces replace the flat pale stone material.

Hanging traps have bound cane ribs, hoops, inward funnels, neck harnesses and
rope loops around the actual overhead girders. The stored buffalo yoke has two
load-bearing slings. Mourning cloth is folded and knotted around the actual
rail; the previous stair tie was about 60 cm below its support. Umbrellas have
pleated oiled fabric, continuous bamboo shafts, ferrules touching the soil,
curved handles and closing ties. Their post restraint fits the 65 mm bamboo
post rather than hanging loosely in space.

`tools/areas/rural_detail.py` is shared by the full village build and the focused
rebuild. The focused pass checks geometry, ground contacts and its face budget,
and stages its changes so other art can be preserved when merging.

```sh
blender -b art-source/blender/ep1/ep1_area_village.blend \
  -P tools/areas/rebuild-rural-details.py -- art-export/ep1/rural-details.glb
npm run assets -- ep1/rural-details.glb
node tools/areas/update-house-details-glb.mjs \
  public/assets/ep1/ep1_area_village.glb public/assets/ep1/rural-details.glb \
  art-export/ep1/rural-details.glb.json public/assets/ep1/ep1_area_village.glb
blender -b art-source/blender/ep1/ep1_area_village.blend \
  -P tools/areas/apply-house-details.py -- /tmp/rural-details-source.blend \
  art-export/ep1/rural-details.glb.json
```

The temporary `public/assets/ep1/rural-details.glb` is an intermediate; the game
loads the merged village. Existing library materials and their attribution
records are reused: split bamboo, weathered timber, worn wood, rough linen and
clay plaster. Strand UVs follow the bamboo fibres; the geometry alternates
over and under across both panel faces.

`tests/unit/ruralPropsAsset.test.ts` checks the actual shipped GLB for ground
contacts, stacked board contact, hanging attachment height, woven relief,
complete surface maps and preserved stair/shed colliders. Review views are in
`tests/browser/house.html?start=act1&landscape&view=storage-wall`, with buttons
for the wall, stairs, spade, hanging traps, stored traps and umbrella bundle.
The review uses the production renderer and an isolated save database.

Validation: the focused rebuild contains 44 objects and 61,799 faces, below its
65,000-face budget. The merge preserved all 4,700 unrelated runtime nodes. The
three shipped-asset placement/construction tests, TypeScript check, ESLint and
production build pass. All six rural review views were inspected in the game;
captures are in `debug-shots/house-{storage-wall,stairs,spade,traps,ground-traps,umbrellas}.png`.
