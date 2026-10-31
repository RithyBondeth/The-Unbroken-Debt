# Haunted forest (31 October 2026)

The user asked for a completely different forest from the old-growth jungle
tried earlier the same day: a **dying, haunted forest**, **readable by
moonlight**. Everything is withered and wrong: bare grey trees, dead bamboo,
leaf litter, drifting fog, and no green left. The palette is ash grey, bone
white and rust, with blood red as the only accent (the thread, the cords and
the blood).

## Village forest (Blender)

`tools/areas/rebuild-haunted.py` is a focused rebuild of the village .blend.
It changes the forest and preserves every prop, the sacred cloth, the gameplay
nodes and the other colliders.

- **Dying giants.** `forest.py` `tropical_tree` builds grey, cracked trees (to
  22 m) leaning on their buttresses, and four in ten are snapped off at the top.
  Bare limbs split into clawing twigs. Three in ten still carry a few clusters
  of dead brown leaves. Dead vines loop between the limbs and hang towards the
  ground. Pale lichen replaces moss.
- **Bananas.** The forest's banana plants are cleared (377 of 435). The rest
  stay round the houses, the yard and the paddy bank.
- **Forest floor.** Dry grass grows only in the clearings. Dead ferns and
  litter cover the floor under the trees.
- **Palette.** `forest_detail.py` repaints leaves, grass and moss in dead
  browns, straw and lichen grey.
- **Budget.** The rebuilt forest is 0.91 M faces, fewer than before.

Run it with the commands in the script's docstring. It needs the
`art-source/library` assets (`npm run fetch-library`): without them the bark
exports untextured, its UVs are pruned, and the batcher refuses to merge
meshes that differ in attributes.

## Everything else (code)

- **Withered shader** (`render/Withered.ts`). Every plant material that wasn't
  repainted is drained towards its own luminance: dead brown for leaves and
  fronds, straw for grass, ash grey for bark. This covers the library shrubs,
  ferns and pachira, the bananas and palms by the houses, the bamboo, and the
  whole taxi roadside.
- **Generated forest** (`data/forestBorder.ts`): grey giants and dead trees
  with dead bamboo and a few palms. The far cards are mostly bare dead trees
  in browns and ash.
- **Tall grass** is dead olive-brown and straw.
- **Moonlight** (`data/nightLook.ts`, `VillageLights`): a bone-white moon
  (0.75), cloud bounce (0.5), a cold silver haze in the fog, exposure 1.6 and
  night sight to 4 m. The bare trees read as grey shapes without the lamp, and
  the lamp warms only what is near.
- **Wind sound**: half the leaf hiss, since few leaves are left. The giants
  mostly creak and groan, more as the gusts lean on them.

## Cost on Low

Measured at 1280×720 in a background tab, so the absolute numbers are inflated.
The "after" column includes the wind, tall grass and omens.

| View | Current build | Haunted forest |
| --- | --- | --- |
| Forest walk | 35.0 ms | 31.8 ms |
| Spawn | 17.1 ms | 16.7 ms |
| House | 25.2 ms | 27.1 ms |

## Evidence

In `evidence/2026-10-30-wind/`:

- `low-haunted-before-after.jpg`: before on the left, after on the right, for
  the spawn, the walk, beside the path and deeper in.
- `low-haunted-crowns-fig-house.jpg`: bare crowns against the sky, the fig, and
  the house edge.
