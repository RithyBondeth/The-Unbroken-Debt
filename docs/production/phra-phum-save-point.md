# Spirit house outside the compound

17 November 2026 redesign. The Preah Phum (ព្រះភូមិ) stands beyond the
compound's front-right fence corner, at `(-15.2, 0, 10.5)`
(`src/episodes/ep1/data/saveShrine.ts`). Both its footprint and approach are
outside the fence. Reach it through the main gate, following the outside of
the front fence to the right. This replaces the October "modest household"
direction (reclaimed boards and a plain roof, built at runtime from boxes) and
the carved wooden effigy that sat inside it.

## The house

A well-off 1930s family's carved teak spirit house, sixty years of rain and
candle smoke on it:

- A single turned teak post, ringed and capped with an inverted lotus of gilt
  petals, on two hand-cut laterite blocks sunk in the earth. A termite tunnel
  of mud climbs the post; a strip of red cloth is tied round it.
- Four scroll brackets carry a balustraded offering tray (top at 1.125 m):
  silver-grey teak planks, one split; red fascia with gilt beads and a cut
  fringe of teeth; turned balusters, one missing.
- A panelled house on a stepped base with a band of gilt lotus petals. Side
  walls have small windows of turned balusters. The doorway faces the path;
  one door leaf is thrown back, the other hangs off a broken hinge.
- Two stacked gables: a narrower porch on two turned columns in front, the main
  roof behind and above. Teak shingles with pointed tips, some missing; carved
  kbach reliefs in the pediments; bargeboards with flame teeth; the gilt naga
  ends are the Cleveland Museum of Art's CC0 bronze naga finial scan; horn
  finials at each apex.
- The red lacquer has faded and flaked along the grain to silver-grey wood; the
  gilt has rubbed through to its red bole. Inside it is black with soot.
- On the porch: two beeswax candles burnt down in clay dishes, their wax run
  down over the fascia; joss sticks old and new in a bowl of ash-grey sand;
  lotus buds in two brass vases; banana-leaf cups of marigolds and betel; cups
  of water; a dead jasmine and marigold garland on the porch beam; cobweb
  veils in the porch corners. Beside the house: a young coconut, a hand of
  bananas on a clay plate, an old leaf cup of rice, spilled rice, dead flowers.
- The chamber is empty but for one candle burning on a dish crusted with the
  wax of every candle before it.

Builders: `tools/areas/phra_phum.py` (with `shrine_craft.py`, `shrine_surfaces.py`
and `offerings_kit.py`); `tools/areas/build-phra-phum.py` writes the editable
`art-source/props/phra-phum/phra-phum.blend` and `art-export/ep1/phra_phum.glb`;
`npm run assets -- ep1/phra_phum.glb` compresses it to
`public/assets/ep1/phra_phum.glb` (≈9.6 MB, 113K triangles, 18 meshes, KTX2
textures, meshopt). Small plain-coloured offerings share one palette material.

## In the game

`PhraPhum.ts` loads the asset (`PhraPhum.prepare` during the act's loading)
and finds the wick markers `phra_phum_wick_left`, `_right` and `_inner`:

- `phra_phum_votive_light` (left porch candle) casts a shrine-only shadow cube
  on medium and higher presets, capped at 512 px and rendered once.
- `phra_phum_right_candle` (right porch candle) has no shadows.
- `phra_phum_inner_candle` lights the inside of the chamber.

Flames are small unlit spheres at the wicks. One invisible box (1.34 × 1.2 ×
1.05 m) is the collider; the clay vessels carry the close-range interaction
hint; cobweb veils never stop the interaction ray.

Press E within reach to pay respects and save. The write commits immediately;
then a 6.2-second response (`ShrineResponse.ts`) dims the porch candles, gives
three spatial wooden knocks from inside, and the chamber's candle leans out of
the doorway toward Sora and drowns to an ember before it rights itself; a
cavity breath and a low brass tail follow. Wildlife recedes. Player movement,
lamp and inventory do not change. Repeated input cannot stack the response.
Failed storage writes preserve the previous save and do not perform a success
response. Threats and cutscenes cancel the effect.

## Checks

- `tests/unit/phraPhumAsset.test.ts`: bounds, the three wicks where the lights
  go, the clay and gilt materials and their maps, draw-call and triangle budgets.
- `tests/unit/shrineDetail.test.ts`: the clearing and route outside the fence,
  the response's cues and its cancelling.
- `tests/unit/savePoint.test.ts`: save concurrency, threat blocking, storage failure.
- Browser fixture `tests/browser/save-shrine.html?start=act1`: views, the
  real-controller walk from the gate, interaction-ray saving, the three candle
  lights sinking and recovering, danger blocking, rejected-write recovery,
  checkpoint reload. It uses `boon-sop-phra-phum-review`, never player saves.
  Add `&listen` for sound.
- `tools/areas/ground_audit.py` on `phra-phum.blend` over a ground plane: no
  floating parts.

Cultural details (offerings, the empty chamber, the response) are advisor-review
items in the Cultural Guide.
