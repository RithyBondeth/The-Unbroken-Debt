# Episode 3 visual revision · 3 November 2026

The first scene used rigid mattress boxes, thin bed poles, flat curtains, sparse
rooms and excessively uniform metal. This pass replaces those close-view props
and extends the weathering treatment through the clinic, market and boats.

## Relationship to main

The visual authority remains the repository's Episode 1 material library,
`tools/areas/kit.py`, `house_decay.py`, `weathering.py`, and the shared rendering
setup. Bed frames, stools, cupboards, baskets, vessels, luggage and oil lamps
come from the existing CC0 library. Original procedural cloth and paint combine
that photographed grain with irregular macro stains and small surface damage.
No external reference photograph is included in the shipped textures.

The new base color, normal and ORM maps connect directly to glTF-supported
material inputs. Rust reduces metal response and increases roughness. Damp
paint, cloth, paper and timber retain distinct surface responses. Corrugated
roofing and textiles render on both sides. Physical grain and room scale matter
more than increasing normal-map contrast.

## Reference study

- [Tonle Sap stilt-village photographs, Monkey's Tale](https://monkeystale.ca/2019/10/02/phnom-penh-and-tonle-saps-stilt-village/):
  pile construction, irregular plank walls, ladders, small boats, baskets and
  belongings around working docks. Used as construction and dressing reference,
  without treating the modern photographs as historical evidence for the story.
- [Abandoned asylum photographs, Roman Robroek](https://romanrobroek.nl/spooky-abandoned-asylums-will-haunt-dreams/):
  empty iron beds, damaged fabric, records and uneven decay. Used to study
  material age and unsettling absence; the clinic retains its existing setting.

## Implemented art

- Six scanned corroded bed frames, shaped mattresses with seams and ties,
  stuffed pillows, sagging torn sheets and gathered muslin with real hangers.
- Supported curtain rails, restrained cloth motion, chipped enamel trays,
  medicine bottles, gauze, instruments, patient tags and waterlogged records.
- Scanned furniture and belongings in the ward and attic; broken paint edges,
  exposed lath, mould roots, timber straps, nails and roof repairs.
- Individual market cladding, stitched sagging awnings, hanging laundry and
  photographed baskets, produce and ceramics.
- Thickened moored boat hulls, bent ribs, caulking and fixings. The playable
  rowing boat also has inner planking, ribs, a keel and rounded gunwales.
- Scanned oil lamps positioned against actual supports. Shared main-branch light
  sorting and material light budgets; cached architectural and ward-lamp shadows.
- Crossing ripple normals, murky floodwater, surface debris and indoor reflections
  using the current water height. Flood reflections previously applied only to
  the outdoor lake material.
- Continuous spirit blouse coverage, a fitted scalp, finer wet hair clumps and
  a desaturated skin map preserving the original face texture. The first close-up
  exposed gaps caused by anatomical bone labels being used as clothing masks.

The 193 collider meshes and 27 story interaction roots remain intact. Art
detail does not change the interaction reach, puzzle gates or route geometry.
The scene remains a real-time web game; this revision does not establish
photorealism, cultural review, historical authenticity or a cross-device frame
rate guarantee.

## Rebuild and evidence

`tools/ep3/realism_scene.py` is invoked by the full builder. To refresh the detail
on the current source scene:

```sh
blender -b art-source/blender/ep3/ep3_area_village.blend -P tools/ep3/rebuild-realism.py
npm run export -- ep3
npm run assets -- ep3
node tools/ep3/finish-village.mjs
```

Runtime captures are stored in `evidence/2026-11-03-realism/`. These are actual
game renders, with the same first-person equipment used by the previous episodes.
