# Welcome screen and title identity

The welcome screen follows the user-selected Home Sweet Home reference for mood only: a realistic, dim interior rendered from the game itself, hand-smeared red title lettering, film grain and a sparse text menu with a red selection mark. The scene, lettering and behaviour are original to The Unbroken Debt. The Cambodian house, Khmer title and Episode I identity are preserved.

Reference: https://www.mobygames.com/game/96548/home-sweet-home/screenshots/windows/960273/

## Assets

The title scene is key art, not the Episode 1 layout: the village house hall seen from the front door, dressed for a binding ritual. The camera's lens shift puts the hall in the right of the frame and leaves the dark left side for the menu. Blood-soaked red cords web the whole room from the family altar, out to both walls and behind the menu, with hanks of black hair knotted to them, cloth effigies hanging from them by the neck and paper charms on both walls. Uncle Sok's coffin lies across the frame in the open floor beside the menu, its long side to the camera, inside a circle of floor candles and a sigil that catches the moonlight like chalk, under incense smoke, something has been dragged from it out of the back door, and paper charms with red brush marks (abstract, not writing) are pinned to the walls. The black Neak Ta has glowing eyes.

The coffin lid is rebuilt for the title: black lacquer gone to craquelure, flaking to dark teak, with worn gilt mouldings and a medallion on the foot. The lid has been shoved round on the rim, leaving a wide wedge of the dark inside facing the camera. The red cords that tied it shut have snapped and their frayed ends hang. Bloody handprints are dragged down its end and across its slope, beside fingernail gouges down to pale wood. Nails torn up along the rim are bent outward, the funeral flowers on it have blackened, and long black hair spills out of the gap and down the front of the coffin.

- `public/assets/ui/welcome-hall.webp`: the empty hall.
- `public/assets/ui/welcome-hall-far.webp` and `welcome-hall-near.webp`: the same frame with the Neak Ta by the back door, and at the far end of the open coffin, against the lit doorway. They are full plates shown over the empty hall.
- `public/assets/ui/welcome-cords.webp`, `welcome-cords-far.webp` and `welcome-cords-near.webp`: the cords, their dolls and hair alone on transparency, with the room (and the Neak Ta, where it stands) cut out of them. The plates leave the cords out but keep their shadows.
- `src/ui/html/welcomeCordPaths.ts`: the cords projected into the frame, for the blood beads.
- `public/assets/ui/welcome-title.webp`: “THE UNBROKEN DEBT” painted as wet red brush strokes. No font is used: each letter is a stroke skeleton dragged with a simulated bristle brush that runs dry, followed by drips and splatter.

Everything is rendered in Blender Cycles from `ep1_area_village.blend` with the game's own geometry, coffin and Neak Ta, at 1920×1080 from one camera and seed, and graded cold and desaturated with only the lamps, candles and red paint keeping their colour.

Rebuild from the repository root (the .blend is never saved):

```sh
B=art-source/blender/ep1/ep1_area_village.blend
for m in empty far near; do
  blender -b $B -P tools/ui/render-title-scene.py -- /tmp/hall-$m.png $m 1920 128
  blender -b -P tools/ui/grade-title-scene.py -- /tmp/hall-$m.png /tmp/hall-$m-graded.png
  blender -b $B -P tools/ui/render-title-scene.py -- /tmp/cords-$m.png threads-$m 1920 128
  blender -b -P tools/ui/grade-title-scene.py -- /tmp/cords-$m.png /tmp/cords-$m-graded.png cords
done
blender -b $B -P tools/ui/render-title-scene.py -- src/ui/html/welcomeCordPaths.ts threads-data
npx prettier --write src/ui/html/welcomeCordPaths.ts
blender -b -P tools/ui/paint-title.py -- /tmp/title.png 31
blender -b -P tools/ui/paint-title.py -- /tmp/listen.png 7 listen
```

Encode with sharp: the three plates at WebP quality 90, the cord layers at 88 with alpha, the title resized to 1600 px wide at 88 with alpha. The entry screen's lettering is resized to 1600 px at 88 with alpha. Its background is the empty hall with the cord layer over it, resized to 960 px, blurred (sigma 10), dimmed to 85 % and saved at WebP quality 80. The script also has an animated `loop` mode and transparent `figure-far|figure-near` layers; they were tried for the title and set aside in favour of the still plates.

## Behavior

The default URL opens the title screen before hardware detection and game initialization. New game starts the prologue; Continue uses the existing IndexedDB autosave and checkpoint loader. Unreadable or unavailable saves receive a visible status message. Restarting with an existing save asks for confirmation inside the game. Settings persist sound, mouse sensitivity and inverted vertical look; changes apply at startup. Settings remain usable for the current session if local storage is unavailable. Arrow keys, Home/End, Tab and Enter support menu navigation. Dialogs use native focus management and Escape dismissal. Fullscreen is requested only when its button is clicked.

Existing `?start=act1`, `?continue` and recognized spike URLs retain their direct entry behavior. The engine's existing requirements page still handles unsupported devices. Game loading failures show a return-to-title action. The in-game listening screen handles pointer capture and audio unlock when the player presses Enter.

## Listening screen

After the scene loads, a dedicated listening screen replaces the old click-to-begin card. It matches the title screen. Behind it is the same ritual hall, cords and all, heavily blurred and slowly drifting, as if the eyes have not adjusted to the dark (`public/assets/ui/entry-hall.webp`), under a dark vignette and the title's film grain. The red បុណ្យសព mark sits above “LISTEN CLOSELY.”, painted with the title's brush tool in ash-white paint (`public/assets/ui/entry-listen.webp`). Below it come the headphones recommendation, the line explaining that directional sound helps locate things in the darkness, and a plain “Press Enter to begin” with the menu's red paint smear breathing beside it. An L–R line under the prompt lights up on the side a whisper is crossing. Enter starts the scene from anywhere on the screen; the focused button also supports pointer activation. Clicking the background does not start play.

While it waits, the screen has its own quiet soundscape (`src/audio/EntryAmbience.ts`, synthesised in `entryDread.ts` and `dread.ts`): a low drone with two tones beating against each other, and rain far off. Every 5.5–7.5 seconds a whisper crosses the head from the left ear to the right, a little closer each time, sometimes followed by knocks behind to the right or boards creaking to the left. It is kept well below the welcome screen, so players can set their volume. Pressing Enter cuts it all off under a sharp breath at the ear and a heavy thud, and the scene fades in on the silence that follows. Browsers allow sound only after a gesture: coming from the title menu it plays, and on a direct link the screen stays silent until Enter. It respects the shared sound setting and mutes in hidden tabs.

Audio unlock and pointer capture run synchronously inside the activation gesture. Repeated, composing and modified Enter presses do not start play, and activation is guarded during the 650 ms departure fade. The listener is removed and focus returns to the canvas before the scene continues. Reduced-motion preferences skip the departure delay. Entry styling is removed before ordinary story cards are displayed.

`/tests/browser/entry.html` previews the real screen without touching saves or loading the game. Press Enter to verify activation, audio unlock, focus restoration, listener removal and ordinary story-card styling; pointer capture is reported separately because embedded browsers may reject it. Preview again repeats the check.

## In-game text

Subtitles, hints, dialogs, story cards and the listening screen share the title screen's look through the tokens in `src/ui/html/design-system.css`: cold black, bone text and blood red used as paint (heading rules, button smears, keycap underlines, speaker marks). Screen headings are spaced Ubuntu capitals, not a serif; letter spacing is dropped for Khmer. Physical paper (documents, the notebook, the ending pages) keeps its own palette and Georgia headings.

## Living atmosphere

The scene fades up from black and creeps slowly inward. Dust turns in the back-door moonlight and animated grain covers the frame. All layers track the image's cover crop.

The cords are alive (`src/ui/html/welcomeCords.ts`). A small WebGL pass draws the cord layer displaced by a slow sway and a fine tremble, held still near the coffin and the frame's left edge, so their ends stay tied. A dull red pulse runs outward from the altar along them, like something feeding. Blood beads slide along each cord to its lowest point, swell there and drip. When the Neak Ta appears beside the coffin, every cord thrashes in travelling waves and the beads run; smaller shudders mark its other moves. The pass runs at about 30 fps and stops in hidden tabs. Without WebGL, or with reduced motion, the static cord layer is shown instead.

The Neak Ta haunts the room in a cycle. It stands by the altar when the menu appears; after 9–14 seconds the lamps gutter to near-black and it is gone. 5–9 seconds later they gutter again and it is suddenly at the far end of the open coffin, close: the frame jolts and the edges bleed red. About two seconds later it is gone, and after another 5–9 seconds it is back by the altar. Every change is timed to a stinger whose hit lands on the darkest frame. Hidden tabs postpone the cycle and pause the visual loops. Reduced-motion preferences show the figure by the altar, with no flicker, jolt, grain or drift.

The welcome screen synthesizes all of its sound with Web Audio (`src/audio/welcomeDread.ts`); nothing is downloaded. The background is a funeral chant gone wrong: six low male voices recite rhythmic, wordless syllables in unison, each phrase ending on a long hum that sags flat, with one voice a semitone low and one an octave below, in a reverberant hall. Under it: the original bell motif far away, a whisper bed with creaking boards and three slow knocks, quiet rain and wind. Stingers mark the Neak Ta: a sub drop and cracked bell as it returns, the same with a shrieking string cluster and a whisper when it is close, and an inhale and thud when it vanishes. Synthesis runs in a worker after the first gesture, so the menu never stalls; rain and wind start at once and the chant fades in a moment later. Audio is created only after a player gesture, respects the shared sound setting, and has a visible ambience toggle in the footer. Hidden tabs are muted. Starting or continuing fades out every source, including stingers, and closes the menu audio context, so the soundscape cannot continue under gameplay.
