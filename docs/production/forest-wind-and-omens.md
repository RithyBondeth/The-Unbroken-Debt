# Forest wind, tall grass and omens

One wind now blows through every outdoor scene of Episode 1. The trees, the
grass and the thread tied in them move with it, and the same state drives what
is heard. The forest beside the path has been marked by the villagers: thread,
a boundary cord, blood, and a strangler fig wrapped as a spirit tree.

## Wind (`src/render/wind.ts`)

- `Game.wind` (`WindState`) holds a heading that wanders ±0.35 rad round the
  monsoon's own, a strength, and gust fronts that roll downwind at 11 m/s. A
  gust bends the trees upwind about 1.5 s before it reaches Sora.
- Sections set `base`: 0.62 on the taxi road, 0.55 for the village night,
  0.16 for the dawn after the storm.
- The story sets `calm` and `tension`. When NightLife, the forest's unease or
  the spirit house fall silent for a threat, the wind drops within about a
  second and the gusts die. Rising dread brings gusts more often and harder.
- Every `DreadScore.sting` sends a gust timed so its height lands on the
  sting's hit (`stingGust`).

## Foliage (`src/render/FoliageWind.ts`)

- The plugin runs in the vertex shader, written once and translated for WGSL.
  It combines a trunk bend that grows with the square of height, branch sway,
  leaf flutter and the two gust fronts. A tip never leans further than a tenth
  of its height. Grass and hanging thread part round Sora's feet.
- `plantHeights.ts` bakes each authored plant's height above its foot, scaled by
  species flexibility, and its phase into uv6 before the area batcher merges
  plants. Trunk and crown therefore bend as one tree. The forest border, the far
  tree cards and the taxi roadside carry the same data.
- Materials are chosen by name (`foliageKind`). Props that only share a word,
  such as the sketchbook's leaves, folded banana-leaf offerings and funeral
  garlands, stay rigid.
- Rain streaks slant with the wind at Sora.

## Tall grass (`act1/TallGrass.ts`, `data/grass.ts`)

- Smau (tall grass) grows thick on the path and road verges, along the paddy
  bunds and at the edge of the swept yard. It is thinner in the forest belt.
  The trodden path, the road, the yard, the shrine clearing, the pond and the
  wells stay bare.
- Each 16-blade clump is drawn with thin instances, one draw per 12 m cell, and
  culled beyond 24 m on Low (34 m on Medium, 44 m on High and Ultra). About
  1,950 clumps on Low.

## Wind sound (`audio/WindAudio.ts`, `audio/windSounds.ts`)

- **Beds:** a stereo roar and a leaf hiss, raised and lowered with the wind
  where Sora stands.
- **Gusts:** a swell with a thin howl, timed to the front reaching her. It
  sweeps from upwind, over her and on downwind.
- **Trees:** crowns rustle, bamboo knocks and squeals, palm fronds clatter, and
  trunks groan under hard gusts. These come from real trees 5 to 24 m away,
  mostly the ones the gust is hitting. Two voices play at once on Low, four on
  the other presets.
- **Indoors:** all of this is on the ambience bus, so the house and the space
  under it hear it muffled. The shutter, draught and cloth layers of the
  Soundscape follow the same gusts.
- **Taxi:** the beds are behind the body and glass, and each gust buffets the
  car.
- Every sound plays on its own at `/tests/browser/sound-audition.html`
  (Wind group).

## Omens (`act1/TreeOmens.ts`, `data/treeOmens.ts`)

Grounded in rural Khmer practice; **advisor review pending**. There is no Khmer
text, so nothing was added to the `KHMER` list.

- **Thread.** Red and faded-white cotton thread is wound round five real trunks
  between the road and the compound, measured from their bark, as a kru binds
  what lives in a tree. The knotted ends hang loose and flutter.
- **Cord web.** As on the title screen: four bamboo poles either side of the
  path a few steps from where Sora arrives, eight dark-red cords sagging between
  them overhead, black hair tassels and red and white ties along them, and three
  cloth effigies with raised arms. The first hangs just above her head over the
  path. A bloody hand is pressed to the first pole.
- **Blood.** A dragged handprint (z ≈ 15) and a smear (z ≈ 37) are pressed into
  the bark, with rain-thinned runs below and spatter round them.
- **Strangler fig (chrey).** At (8.5, 29), 18 roots wind both ways round a pale
  dead host. They crawl half-buried along the ground before rising. About 110
  aerial roots hang like hair and swing slowly. Faded red and white cloth bands
  and red thread are tied round the trunk. At its roots are a clay pot,
  burnt-down incense, old betel-juice stains and a handprint. Red cords with hair
  tassels and two more effigies hang from its branches.

## Verification

- Unit tests cover the wind state and envelope (`wind.test.ts`), sound synthesis
  and audio scheduling (`windAudio.test.ts`), and plant heights, trunk
  measurement, grass layout, tubes and placement (`forestDressing.test.ts`).
- Frame time on Low (Apple M1 Pro, Act 1 path): 28.8 ms average with the new
  work disabled and 28.9 ms with it enabled, over four alternating runs. Both
  were measured in a background tab, so the absolute numbers are inflated; the
  difference is within noise.
- Browser evidence in `evidence/2026-10-30-wind/` (gamma lifted for viewing):
  the fig, its roots and the bloodied trunks; one path view with the wind still,
  blowing and in a gust; and the taxi roadside.
