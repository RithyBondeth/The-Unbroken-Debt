# Modern Khmer funeral ensemble reference study

Updated 24 October 2026. The user selected **modern photographic styling**,
including richer flowers and decorative draping, for the funeral ensemble.
The surrounding village and the story's characters retain their existing assets.

## Evidence and scope

This is a modeled interpretation of documented Cambodian Buddhist funerals, not
a claim that every Khmer family uses one identical arrangement. Family practice,
means, location and ceremony stage affect the objects and their placement.

| Source | Evidence used | Limits |
| --- | --- | --- |
| [Keo Mony, Death in Cambodian Buddhist Culture, EthnoMed](https://ethnomed.org/resource/death-in-cambodian-buddhist-culture/) | Home funeral, coffin, family vigil, monks and white mourning clothing; cultural context for the existing scene. | Cultural account reviewed in 2008; not a modern equipment specification. |
| [Fresh News, Battambang funeral report, 29 August 2025](https://freshnews.com.kh/localnews/400369-2025-08-29-13-56-09) | Photographed flower-framed portrait, abundant white/yellow flowers and greenery, ceremonial furniture and offerings at a Cambodian home funeral. | One family's contemporary arrangement, not a universal template. |
| [Setarra, Cambodian Funeral Ceremony, 2017](https://www.setarra.com/cambodian-funeral-ceremony/) | Firsthand family ceremony, food offerings, gathering, monks and coffin procession. | Diaspora setting; corroborates functions rather than exact local styling. |
| User's two supplied photographs | Dense floral portrait border, white canopy and gathered curtains, paired lamps, low flower baskets, carved altar and layered offerings. | The watermarked first image is Alamy E1M57N. Its precise location was not independently established. These are styling references, not proof of national provenance. |

Reference photographs are retained only in ignored `art-source/reference/funeral/`
for study. They are not shipped as game textures. The game's original Sok portrait
is retained. No relative's photograph or watermarked reference was imported into
the playable scene. The later condolence ribbons use the sourced Khmer wording
listed below; no donor names or institutional identities were invented.

## Modeled components

| Component | Implemented detail |
| --- | --- |
| Funeral shelter | Existing bamboo frame and thatch shelter; visible slat floor, rattan lashings, cloth-lined roof, gathered side/back panels, four entrance swags, narrow gold hems and curtain bows. |
| Portrait canopy | Separate white draped canopy above the memorial, supported posts, curved parted curtains, gathered top swag, hems and hanging ribbon tails. |
| Memorial portrait | Original Sok image, timber frame, narrow gilt bead, rear stand, dense irregular white/cream floral border and foliage. The face stays visible. |
| Flowers | Cupped multi-whorl petals, tiny flower centers, folded leaves, palm sprays, paired standing wreaths and low urn arrangements with bows. Variation in bloom radius, angle and spacing avoids identical flower discs. |
| Altar | Beveled timber top, turned legs, stretcher bars, gilt feet and modeled scroll relief, cloth front and raised portrait support. |
| Offerings | Open water cups, water surfaces, food dishes, bananas, individual elongated rice grains, paired vases and bouquets, a hollow incense pot and individual sticks. |
| Memorial lamps | Paired turned brass stands and frosted warm globes outside the altar corners, supported by actual practical lights. |
| Candles | Shaped wax, irregular drips, dark wicks, holders and separately controlled flame cards. |
| Coffin | Actual hollow timber shell and bed, interior linen, plinth, layered gilt mouldings, raised scroll details, side handles, end panels, crowned solid lid, narrow soft cloth and flowers attached to the moving lid. |
| Dais | Existing two-level platform, white covers and skirt, preserved walking and collision volumes. |
| Incense stations | Hollow cast-brass vessels, ringed feet/stems/rims, visible ash, uneven sticks and pale spent tips at the four existing ritual corners. |
| Main ritual burner | Hollow turned bowl, cast rings, ash and incense; original token-burning anchor retained. |
| Folded-leaf offerings | Bowls supporting actual folded banana-leaf clusters in three scaled tiers, replacing smooth stacked cone shapes. |
| Monks' seating | Existing raised platform and cushions, added sewn piping and a soft linen runner; white ceremonial cord retained. |
| Mourners' objects | Open porcelain cups including the upset cup, shaped teapot with lid/spout/handle, softened folded cloth, bounded woven mats with reed fringe, petals and individual scattered rice. |
| Drums and perimeter | Finer drum bodies, membranes and rope geometry; existing flags, banners, umbrella bundle, lanterns, water jars and sandals retained in their functional positions. |

The canopy dimensions, exact decorative scrolls, lamp design and flower mix are
art direction informed by those references. They are not presented as mandatory
ritual prescriptions. The richer memorial arrangement is the user's deliberate
departure from the project's earlier sparse period styling.

## Runtime and authoring

`tools/areas/funeral.py` is the shared craft builder. `khmer.py` and the village
builder call it, so subsequent full exports keep the funeral improvements.
`rebuild-funeral.py` updates only this domain in the current Blender scene and
checks the transforms and data of unrelated objects before saving. Its focused
export and manifest are merged by `update-funeral-glb.mjs`; unrelated runtime
nodes and existing compressed materials remain intact.

The hollow-shell metadata makes `CorpseModels` retain the authored coffin rather
than cover it with the older box replacement. All lid ornament follows the same
production hinge. Portrait examination, the four incense stations, protective
thread, oil pickup and ritual-burner markers preserve their gameplay identities.
New globe meshes participate in the pavilion's existing snuff/relight behavior.
`DeskModels` retains the authored floral frame and stand while replacing only
the photograph for the eye animation. Its plane matches the authored size and
tilt. Standing wreaths sit outside the coffin approach, leaving the reveal and
near-rim grip clear.

Use `tests/browser/funeral.html?start=act1` for the six review views under the
actual game lighting. Use `tests/browser/chest.html?continue&case=coffin` for the
production reveal, hold/release, closing and saved restoration checks.

## Verification on 24 October 2026

- Focused Blender rebuild verified unchanged data and transforms of unrelated
  scene objects. The runtime merge preserved 3,681 unrelated nodes.
- Asset checks verified the hollow shell metadata, four incense-corner IDs,
  independent candle/globe meshes, corrected lamp intensities and double-sided
  textured petal/foliage materials. Floor slats remain below the woven mats.
- TypeScript build, scoped ESLint, formatting and all 242 tests passed.
- The production coffin browser case passed the initial shut state, body below
  the rim, reachable handle, hold/release behavior, head change only behind the
  lid, and saved closed-coffin restoration without repeating the scare.
- Six visual-review views use the actual game, materials, lamp and colour grade.
  Review screenshots are saved in ignored `debug-shots/funeral-*.png`.

## Fuller flowers, 25 October 2026

`tools/areas/floristry.py` now authors the floral geometry used by the portrait,
wreaths, baskets, vase bouquets and coffin garland. The arrangements combine
layered chrysanthemums, ruffled carnations, raised-center daisies and six-petal
lilies. Curved petal surfaces, curled tips, calyces, connected stems and fine
filler sprays give the flowers depth from oblique views.

The portrait border contains 164 blooms, with unequal corner clusters and blush
accents. The wreaths have variable band widths and different foliage rhythms;
the vase and basket bouquets have rounded volumes and uneven heights. Leaves
vary in width, twist, curvature and growth direction, with modeled midribs and
the existing vein maps. Flowers remain clear of the portrait's face and the
standing wreaths keep their clearance from the coffin approach.
Warm shading at the petal attachments and pale tips make the overlapping layers
read under the practical lamps. The candles sit farther forward and outboard,
with reduced spill, so they remain separate from the wider floral border.

The focused rebuild preserved 3,865 unrelated Blender objects, and its runtime
merge preserved 3,681 unrelated nodes. Asset inspection verified increased floral
geometry, several bloom species, finite bounds and the four incense anchors.
The production build passed after integration.

## Filled floral tributes and Khmer banners

The user corrected both standing arrangements to have solid flower-filled
centres rather than open rings. The head of each stand now has 110 additional
overlapping blooms on a shallow domed backing. The two arrangements keep their
individual irregular foliage and their existing positions outside the coffin
approach.

[The Cambodian Ministry of Information / AKP funeral report of 27 April 2021](https://www.information.gov.kh/articles/41212)
shows a dense white floral tribute with a black horizontal Khmer-lettered band
across its front. The photograph was inspected for this correction and is kept
only as an ignored reference image, credited to AKP / Khem Sovannara.

Each modeled band reads **សូមចូលរួមរំលែកទុក្ខ** ("With condolences") from left to
right. This wording also appears in the funeral-flower description of
[1st Blossom's Cambodian florist post](https://www.facebook.com/100070183750679/posts/1036704135345702/).
The florist search excerpt was used for wording; its social-media image was not
accessible. The inscription is recorded in `tools/drawings/ep1.mjs`'s `KHMER`
inventory. `tools/drawings/funeral.mjs` renders it with the existing OFL
Preahvihear font so consonant stacks and vowel signs are shaped correctly.

The band is an original cloth texture on a softly sagging three-dimensional
strip, with folded-back ends and stitched hems. Its lettering uses UASTC
compression. `rebuild-floral-tributes.py` updates just the two stands, while the
runtime merge's `--reuse-materials` option keeps the existing compressed craft
materials and all unrelated village art.

## Black and white mourning cloth (26 October 2026)

The user supplied a photograph of a present-day Cambodian funeral pavilion (Together
Studio watermark). It was used only as a colour and arrangement reference and is not
shipped or copied. The pavilion keeps its 1930s bamboo frame and palm thatch. Its
cloth now follows the black-and-white Khmer funeral scheme:

- The ceiling lining alternates white and black bays between the rafters.
- A white band with a scalloped black valance runs round the eaves.
- Black swags are hung over deeper white ones across the entrance, with the gold
  hems kept. A garland of white chrysanthemums and yellow daisies, in alternating
  groups of three, runs along their hem.
- Gathered black curtains hang at every post of the white back and side walls.
  They are tied at shoulder height with white bows (back) or white cords (sides).
- The front tie-back curtains and the portrait canopy's top swag are black.

These are made by `mourning_cloth()` and `pavilion()` in `tools/areas/funeral.py`,
using the new `M_funeral_black_cloth` (rough linen at near-black). The focused rebuild
now does two things it didn't before. It remakes village materials the saved scene
has pruned (`M_jasmine` had blocked every run), and it leaves the house pass's silk
tent cobwebs alone. The run rebuilt 597 funeral nodes, preserved 4,361 unrelated
Blender objects and 4,161 unrelated exported nodes, and grew the village GLB by
2.4 MB. Captures: `debug-shots/before-tent-*` and `after-tent-*`.
