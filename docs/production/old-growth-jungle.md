# Old-growth jungle (31 October 2026)

The user asked for the whole forest restyled as a dark, old-growth lowland jungle
(Home Sweet Home 2 mood, Khmer setting): oppressive and enclosed, thick dark
trunks, lianas and hanging roots, ferns and litter on the floor, cold
green-black colour, with the red thread and cords as the only accents.

## Village forest (Blender)

`tools/areas/rebuild-jungle.py` is a focused rebuild of the village .blend, in
the same way as `rebuild-forest.py`. It changes the forest and preserves every
prop, the sacred cloth, the gameplay nodes and the other colliders.

- **Giant trees.** `forest.py` `tropical_tree` builds old-growth giants half
  again as tall as before (to 26 m): a straight bole on buttress fins 1.8–3.2 m
  high, mossed and wound with four to seven lianas. The limbs spread wide with
  lianas looping between them, cables hang towards the ground and bird's-nest
  ferns sit in the crotches.
- **Bananas.** The banana plants that filled the forest are cleared (377 of
  435). Bananas stay only round the houses, the yard and the paddy bank.
- **Forest floor.** Grass grows only in the clearings: the path verges, round
  the yard and on the road bank. Ferns and litter cover the floor where the
  bananas stood and under the giants near the walk.
- **Palette.** `forest_detail.py` repaints leaves, grass and moss in cold, deep
  blue-greens.
- **Budget.** Crowns use ten leaves per spray (Low preset budget), giving
  1.15 M faces in the rebuilt forest.

Run it with the commands in the script's docstring. It needs the
`art-source/library` assets (`npm run fetch-library`). Without them the bark
exports untextured, its UVs are pruned, and the batcher refuses to merge
meshes that differ in attributes.

## Generated forest and grade (code)

- **Forest border** (`data/forestBorder.ts`): mostly broadleaf giants, with
  bamboo, dead trees and a few sugar palms. Saplings, pachira and shrubs fill
  the middle layer and ferns the floor. Bananas appear only in the belt by the
  houses. The far cards are taller and colder.
- **Library plants** (`jungleGrade.ts`): shrubs, ferns, pachira, bananas and
  palms are tinted cold and dark to match. The taxi roadside, which was never
  repainted, gets the full grade.
- **Tall grass:** only a thin fringe along the forest path; it stays thick on
  the road bank, the bunds and round the yard.
- **Night look:** thicker, colder fog (density 0.024) and a green-black
  distance.

## Cost on Low

Measured at 1280×720 in a background tab, so the absolute numbers are inflated:

| View | Before | After |
| --- | --- | --- |
| Forest walk | 35.0 ms | 38.3 ms |
| Spawn | 17.1 ms | 16.7 ms |
| House | 25.2 ms | 25.9 ms |

The "after" column also includes the wind, tall grass and omens. Triangles
drawn on the walk went from 4.06 M to 4.28 M. Low's dynamic resolution absorbs
the difference.

Evidence: `evidence/2026-10-30-wind/low-jungle-before-after.jpg` (left before,
right after, gamma lifted for viewing).
