# Episode 1 studio: shophouse rebuild (November 2026)

The prologue studio was rebuilt from scratch on branch `episode1/improvement`. The
user rejected the old 6 × 5 m room ("I don't want current map and design") and
asked for:

- more room, realistic detail and real posters instead of drawings;
- better shadows;
- a clean but old room;
- no opening "Press E to draw";
- a detailed telephone;
- smooth play without judder.

## Layout

Sora rents the top floor of a 1932 Sino-Khmer shophouse: 4.6 × 14 m between masonry
party walls. Blender's (x, y, z) is the game's (−x, z, −y).

| Zone | Blender y | Contents |
| --- | --- | --- |
| Balcony | −1.25 … −0.3 | Cement slab, cast-iron railing, the street and the shophouse opposite |
| Front studio | 0 … 6 | Two French doors, the drafting table and banker's lamp, the writing desk and drawer (same place as before, so the prologue code is unchanged), plan chest, bookcase, tea corner, the candle shelf and satchel on the partition |
| Hall | 6.12 … 9.12 | Indoor hall: the stairs down behind a child gate (`interact_door`, the way out), the wall telephone and lantern hook, dining table, food safe, water jar, cooking corner |
| Back room | 9.27 … 14 | Bed under its gathered mosquito net, wardrobe, washstand and mirror, the family altar shelf with an oil lamp, a lacquered screen |

Built by `tools/areas/ep1_area_studio.py`. Library models are CC0 Poly Haven assets,
decimated to a polygon budget each (some arrive with 200k faces). The encaustic
cement floor tiles are generated in the script.

### The hall (third playtest)

The user turned down both the plain open airwell and the detailed courtyard that
replaced it: "I actually want indoor just like others". The middle of the floor is now
an indoor hall, ceilinged and tiled like the other rooms:

- the stairs down, still the way out, behind their gate;
- the telephone and lantern on the partition;
- a dining table under a green enamel hanging lamp (the hall's baked light), with a wire
  food cover, rice bowls and chopsticks, and stools;
- a screened food safe whose legs stand in tins of water against the ants;
- the big water jar with its dipper;
- the cooking corner on the west wall (brazier, kettle, jars, firewood, chillies and
  garlic), with soot on the wall above;
- washing drying in the rains on a line across the stairwell, lit from below by the glow up the stairs;
- pegs with a krama and a bag, a rolled sleeping mat, a rice sack, and the earth-god shrine.

It is old: cracks from the door head, a brick patch, soot over the fire, a ceiling stain
with a rusty basin catching the drip, damp behind the water jar, and cobwebs in the high
corners.

### The hall, fourth playtest: scanned props

The user found the hall "still not detail". Its props were primitives with flat colours,
so they were replaced by photo-scanned models:

- Poly Haven CC0, fetched by `npm run fetch-library` (V1-162 to V1-180):
  - the table, three stools and the cook's squat stool;
  - the painted kitchen shelves, the rice chest, the enamelled hanging lamp;
  - the brass wok, crocks, bowls, jug, oil tin and wooden spoon;
  - a carved plate of limes and lychees, onions and sweet potatoes, a hatchet.
- Sketchfab CC BY 4.0 (V1-181 to V1-192), prepared by `tools/areas/studio_scans.py`
  into `art-source/library/scans/` (LFS):
  - the big glazed water jar (a real Martaban-type storage jar), a smaller jar with
    handles, glazed jars on the shelves;
  - the clay cooking pot on its clay stove, the brazier with the aluminium kettle;
  - the burlap rice sack, the bamboo winnowing tray and two baskets on the wall;
  - the rolled sleeping mat hanging by its ropes, the straw broom.

  Scans are reduced once, when prepared, and not again in the build: re-decimating a
  photo scan tears its texture layout apart. `scan()` leaves a scan out, or uses a
  stand-in, when its file is missing. Three approved downloads were not used: the
  cupboard (1.5 m wide) and the work table (1.9 m long) are too big for the hall, and
  the fruit basket holds apples, unlikely in 1932 Phnom Penh.
- The firewood, shelves and food safe are now photo-textured (bark, weathered planks).

Soot over the cooking fire and the roof-leak stains are no longer flat polygons. They are
part of the bake's grime pass (`MARKS` in `bake_studio_lightmap.py`): soft, broken-edged
blobs with a tide line, multiplied into the lightmap.

Collision boxes are kept to the real shapes so that every route stays walkable (player
radius 0.25 m). Routes are checked by walking them with key presses.

**Cultural advisor:** please check the earth-god shrine too.

## Prints

All prints are real public-domain printed matter from 1932 or earlier. The 1960s–2020s
references the user sent are out of period and under copyright. Sources and licences
are listed under `art-source/library/polyhaven.json` → `archive`, and in the asset
tracker (V1-159, V1-160):

- *Exposition coloniale de Marseille 1906 · Cambodge · Danses cambodgiennes*
  (Charles-Henri Beauvais, colour lithograph);
- *Le Petit Journal*, illustrated supplement of 24 June 1906 (colour cover of King
  Sisowath's dancers in Marseille);
- four 1921 autochromes by Léon Busy (CC0, Musée Albert-Kahn): Wat Phnom, a Royal
  Ballet dancer, the Throne Hall, the Emerald Buddha (over the altar);
- five Pierre Dieulefils postcards of Phnom Penh.
- colour, added after the first playtest: a 1920s *Try Kuling* travel poster, *Le Petit
  Journal*'s colour map of Siam and Cambodia (1893), René Piot's gold *Danseuse
  cambodgienne*, and three more Busy autochromes of dancers in costume (Hanuman, a Yaksa,
  a princess). These are in the third atlas, `T_studio_print_colour_BC`.

`tools/drawings/studio.mjs` paints them into three atlases with paper toning, foxing,
folds, tack holes and tide marks (`npm run drawings -- ep1 studio_posters`, and the same
for `studio_cards` and `studio_colour`). Layout: `tools/areas/studio_prints.json`.

**Cultural advisor:** please check the dancers, the Royal Palace and the Emerald
Buddha print on the family altar.

## Light

Static light is baked; it is no longer drawn every frame:

- `tools/areas/bake_studio_lightmap.py` bakes these with Cycles into one 4096 px
  lightmap: the banker's lamp, the writing sconce, the hall lamp, the altar lamp,
  the glow up the stairs and the night sky. The bake has soft shadows and bounce
  light, and is multiplied by a grime pass: contact darkness, water stains running
  down from the ceiling, scuffs above the skirting.
- Receivers get a second UV map (`TEXCOORD_1`) and `_LM` material copies.
- `src/episodes/ep1/prologue/Studio.ts` gives `_LM` materials the lightmap as
  `lightmapTexture`. One light in Babylon's `LIGHTMAP_SPECULAR` mode
  (`desk_lamp_highlight`) turns that into diffuse light × albedo, and adds the lamp's
  highlight on varnish, brass and tile.
- Runtime lights reach only the props that are not baked, and only within their range.
  The shelf candle goes out in P05, so it stays a runtime light with a shadow map drawn
  once and redrawn when something nearby is taken. The lightning's shadow map is drawn
  only during a flash.

Before: 1,775 draw calls and 8.2 M triangles a frame, with the desk lamp's cube shadow
redrawn every frame.

## Frame pacing

`FramePacer` (`src/render/renderLoop.ts`) renders on every second refresh on
120–165 Hz displays. Without it, frames alternated between 8.3 and 16.7 ms, and the
view shook while turning. `?fps=max` turns it off.

## Rebuild

```bash
npm run fetch-library
npm run drawings -- ep1 studio_posters && npm run drawings -- ep1 studio_cards && npm run drawings -- ep1 studio_colour
blender -b --factory-startup -P tools/areas/ep1_area_studio.py
blender -b art-source/blender/ep1/ep1_area_studio.blend -P tools/areas/bake_studio_lightmap.py
npm run export -- ep1/ep1_area_studio && npm run assets -- ep1/ep1_area_studio
```

Preview renders without baking:
`blender -b art-source/blender/ep1/ep1_area_studio.blend -P tools/areas/bake_studio_lightmap.py -- preview OUTDIR`.

### Fixes after the fifth playtest

- **Drying line (studio):** the three sheets were blank and glowed. They now carry Sora's
  ink studies (boats, palm trees, a stilt house; `T_studio_study_*`), pegged up with a
  slight curl. They are baked like the walls, so they no longer glow.
- **Hall pegs:** the krama and a hessian bag cut through each other. Now a krama and a
  blue cotton cloth hang gathered from separate pegs (`peg_cloth`).
- **Back-room washstand:** the towel hung in mid-air in front of the cabinet. It now
  hangs over a wooden rail on the cabinet front, under a brass basin and the jug. The
  enamel pot, whose painted flames looked like fire, is gone from there as well.
