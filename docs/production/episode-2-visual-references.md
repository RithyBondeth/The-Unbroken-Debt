# Episode 2 environment rebuild

The user's nine reference photographs establish the visual target: old Khmer vihara architecture, broad overlapping terracotta roofs, carved dark timber pediments, cream plaster and red dado, heavy patterned columns, faded blue/red ceiling paintings, and densely grouped memorial stupas. These are composition and construction references, not shipped textures.

## Internet research

- [Cambodian Ministry of Culture and Fine Arts: Wat Roka Kandal](https://mcfa.gov.kh/ministry-of-culture-and-fine-arts-successfully-completes-restoration-of-the-ancient-vihara-of-wat-roka-kandal/): Khmer architectural reference, specifically its paintings and carved woodwork.
- [Hello Angkor: Wat Rokar Kandal](https://helloangkor.com/attractions/wat-rokar-kandal/): reference photographs and descriptions of carved pediments, timber pillars, cross beams, roof supports, tiled roof and old stupas.
- [Chiang Mai World Heritage: Wat Umong](https://chiangmaipao.go.th/ChiangMaiWorldHeritage/en/?p=87): forest enclosure, masonry passages and the relationship between the chedi and its surrounding landscape. Search-index text was available; the page itself returned 403. Used for spatial inspiration, not a literal reconstruction or a claim that the site is haunted.

## Authored interpretation

`tools/areas/pagoda_architecture.py` builds original geometry and texture maps. The existing Episode 1 CC0 library supplies timber, clay tiles, bark and ground surfaces. No watermarked photograph is used as an asset.

- Recessed memorial chambers with separate corner piers, pointed layered arch mouldings, convex lotus bands, stepped bases and three ringed pinnacle profiles. Four aged surface palettes vary the cemetery.
- Fifty-two memorials and four canopy-tree islands replace the identical 56-monument grid. Staggered interior placements break long sightlines; the four family locations remain stable for story and saved progress.
- `src/episodes/ep2/data/garden-layout.json` is the common source for Blender, collision placement, ghost navigation, hearing occlusion and notebook plotting.
- Roof tiles have curved cross-sections and overlapping lips. Exposed rafters, purlins, carved pediments, edge teeth and high finials replace simple roof planes.
- Recessed windows, red plaster dado, decorated timber columns, painted ceiling panels, altar cloth, mats and vessels give the prayer hall an inhabited history.
- Layered tropical canopy and understory reuse Episode 1's detailed forest builders. Tree islands, vines, roots, bamboo, fern rosettes and fallen boughs create enclosure while leaving offering approaches clear.
- Episode 1's grade, lamp, foliage motion and ground mist remain the visual baseline. New architecture and foliage participate in moon shadows at supported quality settings.

English subtitles remain the narrative presentation. The horror is fictional atmosphere and environmental neglect, rather than a statement about the real reference temples.

## Rebuild validation

- Full `npm run check`: 477 tests in 89 files, TypeScript, lint, formatting and production build pass.
- Optimized area GLB: 52.76 MB. The additional geometry increases the download from the prior environment.
- Real renderer review: gate, memorial and hall interior inspected; hall preview approximately 60–70 fps on the current machine at Medium (not a cross-device performance guarantee).
- Physical collapse/escape fixture: passes with 56.0 active seconds remaining through the actual library, bridge and west garden aisle.
- Initial generic traversal fixture reached the locked bridge in its default story state; the unlocked collapse fixture verifies the full bridge/exit route. Full live-ghost offering balance remains a separate manual playtest.

## Ceremonial entrance correction

The user's subsequent gate photograph supersedes the earlier tiled-roof entrance. `pagoda_gateway.py` now authors a three-portal red stucco gateway: tall main piers, lower pedestrian wings, projecting layered cornices, curved solid pediments, curling floral relief, central lotus medallions and slender crown ornaments. Actual raised mouldings cast shadows; plaster normal maps, subdued gold paint, dark recessed bands and individual mineral drips provide age without using the reference photograph as a texture. The central opening remains clear. The small existing naga approach balustrades remain part of the compound design.

`tools/ep2/rebuild-gateway.py` updates this part of the editable Blender scene without rebuilding unrelated scenery. The full area builder calls the same gateway function.

## Horror ruin pass · 2 November 2026

The user asked for an older, scarier, more detailed compound and a forest as thick as Episode 1's. Further reference research:

- Strangler figs gripping Angkorian masonry: [Ta Prohm (Insight Guides)](https://www.insightguides.com/inspire-me/blog/visual/tree-roots-envelop-some-of-the-temples-in-mysterious-angkor-cambodia), [Preah Khan (Photo12)](https://p12.photo12.com/en/image/brk19i99_139), and Beng Mealea as the most overgrown site ([Trip.com](https://ph.trip.com/moments/poi-koh-ker-temple-50649076)).
- Wat Mahathat, Ayutthaya, burnt in 1767: stripped brick chedi, rows of headless Buddha images, the head held in fig roots ([Benjie Layug](https://benjielayug.com/2011/04/ayutthaya-wat-mahathat.html), [Thaïlande et Asie](https://thailande-et-asie.com/en/guide-voyage/thailande/ayutthaya/wat-mahathat)). Used for condition and atmosphere; the famous head is not reproduced.
- Retired spirit houses left under large trees or on temple grounds ([Must Share News](https://mustsharenews.com/thai-spirit-houses/amp/), [The Thailand Life](https://thethailandlife.com/thai-spirit-houses)); accounts differ on how common this is.
- Sema boundary stones around an ordination hall and the hall's enclosing wall ([Wat Pho: Kampaengkaew](https://watpho.com/en/architecture/detail/306)).

Construction (all original geometry and procedural maps; no photograph is a texture):

- `tools/areas/weathering.py`: tileable lime plaster with clustered black mould runs, algae, lichen, hairline cracks and spalls to brick; exposed Khmer brick; eroded sandstone.
- `tools/areas/pagoda_stupa.py`: the 52 memorials keep their footprints but gain four crowns (Khmer ringed spire, Thai bell, lotus bud, stepped prang), lean, snapped tips lying on the pedestal, brick scabs, chipped petals, fig saplings, cloth sashes, incense, candle stubs and dead garlands. The family stupas stay upright with clear fronts and white cloth.
- `tools/areas/pagoda_ruin.py`: strangler-fig root nets, a burnt bell chedi with fallen plaster and a fig in its crown (south-east yard), a terrace of damaged seated images inside the gate wall and a cloister gallery, ten retired spirit houses under the old banyan, sema stones round the prayer hall, guardians at the gate, and lotus-crested enclosure walls with leaning bays, scabbed plaster, three fallen bays and creepers.
- `tools/areas/pagoda_forest.py`: Episode 1's old-growth giants (synchronised `forest.py`/`forest_detail.py` from main), three ranks outside the walls, a tree-lined approach track with a rag tree and roadside stupas, dead trees, termite mounds, fallen logs, banyans whose roots pour over the walls, and a fern and litter floor. Trees beside walks keep their buttresses inside the collision footprint.
- 22 forgotten memorials in the north-west and north-east yards and on the approach lean hard; a third carry figs.

All additions sit outside the ghosts' garden navigation domain or inside the existing stupa footprints, so `garden-layout.json`, Pret navigation, hearing occlusion and the notebook are unchanged. Advisor review: the image terrace, cloister images, spirit houses, sema stones and guardians.

## Hall and props pass after the user's vihara photographs · 2 November 2026

The user's second reference set (old Khmer vihara exterior and interiors) drives `tools/areas/pagoda_props.py` and the reworked `temple_interior`/`temple_roof`:

- Interior: black-lacquer columns with a gold stencilled lozenge lattice rising to the ceiling; gold-on-black frames round faded blue ceiling boards with a central red mandala, corner roundels and star flowers, tide-marked by water; wall-top bands in red, green and yellow; webs, fallen tiles and torn banners.
- Altar: a stepped painted altar, a painted-plaster Buddha (ivory skin, saffron robe, bare right arm calling the earth to witness) on a carved red lotus throne, gilded bodhi trees, small images, lamps and a crimson curtain swag with side drapes. Advisor review.
- Roofs: dark brown tiles, dark saw-tooth edges, tall curving horn finials, upturned corner hooks and a carved praying deva in each hall and library pediment.
- Props: a sculpted five-headed naga balustrade on a stone rail, the family flower as a tarnished silver medallion with a worn inscription tablet (no invented Khmer), low lacquered offering tables with footed trays, lumpy rice on banana leaf, water cups, solid sema stones, and floorboards with their grain along each board.
- Fix: voxel sculpts now cap open tubes before remeshing; earlier guardians, images and the naga lost their tube parts.

## Hungry ghosts, leaf beds and Sophal · 2 November 2026

- Pret (`hungry_ghost` in `pagoda_props.py`): hunched, starved anatomy after mural preta: caved ribcage, vertebrae, sagging belly, needle neck and pinhole mouth, arms past the knees with clawed fingers, knobbed joints, lank hair, dim milky eyes instead of glowing ones. The `pret_<n>` roots and their movement are unchanged.
- Leaf beds keep their invisible `leaves` sound surfaces; the visible rectangles are replaced by feathered leaf-mould drifts with loose curled leaves and twigs (`leaf_litter`).
- Sophal (`tools/ep2/build-cinematics.py`): the cone drape that hid an unposed body is gone. He now sits cross-legged on a reed mat in a saffron robe assigned by body position, covering the body and left arm with the right shoulder bare, smoothed off the skin in every baked pose, with a folded robe edge. Fixed a long-standing bug that lifted each garment vertex once per adjoining face (blistered cloth). His sutra table is a low lacquered table with a palm-leaf manuscript, betel box and water bowl.

## Hall entrance and kuti · 2 November 2026

- The hall's `hall_chain` barrier is now a group: rusted chains crossed over the doorway, a padlock, a white cotton cord and an inked yantra-style cloth (abstract geometry only; advisor review). The runtime still hides it by name when the hall opens. Carved red-and-teak door leaves stand ajar inside.
- The bell verse is a yellowed sheet on a black lacquered board, moved beside the hall steps so it no longer stands in the walk; it keeps the `interact_bell_verse` name.
- The bells hang on ropes from a small tiled timber pavilion on stone footings, with a striker and webs.
- Sophal's kuti: altar shelf with a small gilded image, candles, dried flowers and red backdrop; a mosquito net over the sleeping mat; robes drying on a pole; lidded alms bowl; water jar and ladle; manuscript shelf; sandals at the door; webs in the rafters. The supplies and record tables are low lacquered tables carrying a reel of white cotton thread, oil bottles and a matchbox, and loose written sheets with an inkpot and pen.

## Yantra cloths · 3 November 2026

After the user's yantra (យ័ន្ត) references, `tools/drawings/ep2.mjs` (`npm run drawings -- ep2`) hand-inks two original yantra on aged cotton with headless Chrome so Khmer clusters shape correctly:

- `T_ep2_yantra_circle_BC`: a double ring of the itipiso verse, an inner ring of the Dhamma and Sangha verses, namo buddhāya and ma-a-u at the centre, eight cartouches of the Triple Gem and the five syllables, circled syllables and radiating unalom strokes with numerals. Nailed over the chained hall door.
- `T_ep2_yantra_square_BC`: namo buddhāya above, a square with diagonals and diamond, looped corners and midpoints, a Lo Shu numeral square in Khmer numerals in the outer triangles, syllables in the inner ones, ma-a-u and the five syllables in side columns, the itipiso opening and the Triple Gem below. Above the kuti altar.

All Khmer strings are standard Pali formulas listed in the file's `KHMER` inventory, pending native-speaker and cultural-advisor review.
