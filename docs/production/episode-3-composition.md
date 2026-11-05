# Episode 3 · market, people, ritual and water revision

This revision addresses the wider composition, character silhouettes and light
response that remained basic after the first detail pass.

The market has a flooded tree belt, submerged roots, vegetation behind the roofs,
hanging fishing nets, overlapping shutters and gables, dock hardware, ladders and
working props. It uses the same photographed library and foliage wind as Episode 1.

Kanha and Pich stand on the upper veranda beside the fourth candle. Their feet
are at deck height instead of floating between the lake and balcony. The release
camera follows their faces at this height. Separate cloth shells carry the same
authored gesture morphs as their bodies. A dark coat, shoulder cloth, indigo wrap
and child's shorts distinguish the figures. Pich's head proportions suit his
small stature. Kanha has layered fine hair cards over the fitted scalp. Wax
pillars have parallel sides, melted crowns, drips and wicks. Vessels, a woven mat,
incense and a hanging oil lamp establish the ritual at floor level. Candle lights
follow the production candle flags. The three small flames use Episode 1's painted
alpha texture on an unlit material, so they remain visible independently of PBR
light selection. Their restrained local light preserves the mat's weave.
The final close-up replaces Kanha's tan blouse with the dark woven coat material
and grades her skin's reflectance to retain facial shape under the held lantern.

## Rendering

- Episode 1's `StormSky.ts` is identical to `main` again. Its night clouds, shared
  tone mapping, paper interface, weather and lantern falloff remain the reference.
- Daylight uses [Kloofendal Overcast (Pure Sky)](https://polyhaven.com/a/kloofendal_overcast_puresky),
  by Greg Zaal / Poly Haven, CC0. The local 2K RGBE file supplies the market sky
  and prefiltered illumination at 256px per cube face (128px on Low). At night the
  storm dome takes over and environment intensity falls to 0.028. Provenance is
  in `art-source/blender/ep3/sky-source.json` and the asset tracker. Play does not
  request the HDR file from an external host.
- Moving people join nearby practical lamps' light lists. Previously those lists
  used the characters' initial, hidden positions. A restrained local flame light
  lets the held lamp and hands catch their own flame. Directional lightning
  preserves surface shape instead of applying a uniform hemispheric flash.
- Water includes the sky in its reflection pass, uses water's index of refraction,
  and combines phase-warped wave slopes with a seeded 24-direction ripple spectrum.
  The ripple spectrum replaces the previous few axis-aligned sinusoids. Vertex
  displacement updates normals too. Planar targets are 256/512/768px on
  Medium/High/Ultra. Low keeps animation and environment lighting without that pass.
  Nearby water keeps a denser mesh while four coarse outer patches carry the
  horizon. Both sky backgrounds enclose the lake instead of hiding water beyond
  the former 50m sky radius. Daylight haze integrates over 240m; the camera's far
  plane is 4000m to contain those backgrounds. The normal also perturbs Babylon's
  projected mirror lookup, so reflected tree edges move with the ripples.

The detail box builder now gives each board, paper and charcoal piece its own
central pivot. Previously, rotating world-coordinate vertices moved some shutters
above the roofs. The existing source and optimized area received the same 288
position corrections; colliders and interaction roots are unchanged.

The optimized area is approximately 63.4 MB plus a 4.3 MB HDR sky. Added texture
and character data increase download and memory use. The editable Blender source
uses lossless file compression; mesh and texture quality are retained.

## Reproduction and review

The full builder calls `realism_scene.py`, which calls `cinematic_scene.py`.
The detail rebuild runs the same code. `finish-composition.py` updates candle
origins and horizon scale in an older detail scene before export.

```sh
blender -b art-source/blender/ep3/ep3_area_village.blend -P tools/ep3/rebuild-realism.py
npm run export -- ep3
npm run assets -- ep3
node tools/ep3/finish-village.mjs
```

The isolated browser fixture adds `view=water`, `view=portrait`, and
`stage=purification&candles=3` for the valid state before the fourth-candle choice.
These use production flags and materials. Desktop and narrow panel views are
checked separately. Captures are in `evidence/2026-11-03-composition/`.

Vite now scans the browser fixtures during initial dependency optimization. This
keeps their lazy Babylon imports in the same module graph as the game and avoids
duplicate scene/physics classes after a fixture triggers dependency discovery.
Each review tab also has its own session database, so simultaneous reloads cannot
clear another tab's chapter setup. Player save storage remains separate.
