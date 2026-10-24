# Episode 1 browser verification

Run `npm run dev`, then open
`http://localhost:5173/tests/browser/act1.html?start=act1` in a WebGPU browser and
click to begin. The page uses a separate IndexedDB database (`boon-sop-act1-verification`),
so it does not overwrite player saves.

The scenario uses the actual village GLB, sound cues, puzzle handlers and Havok
physics. Dialogue is accelerated, the character is moved between test locations,
and the eleven-minute vigil clock is advanced; the thirteen-second Act II opening
plays at normal speed. Assertions appear over the game:

- The vigil starts after the arrival dialogue and duties.
- Sok's door is initially blocked and the shed requires its unique key.
- The shed lore can be collected and the offering awards three blessed matches.
- The offering alone cannot advance the act; a cycle and a return beneath the tent are required.
- The pavilion's lights and flame meshes go out and the opening writes CP2.
- A Havok ray passes through Sok's opened doorway.
- The transition does not add an incense-neglect penalty.

After `TRANSITION PASSED`, use **Verify checkpoint restoration** and click to begin
again. The second scenario checks the CP2 spawn, opened door, extinguished lamps,
collected lore, sketchbook objective and unchanged blessed-match count.

NPC performances and the gust/footsteps are greybox stand-ins. Listening for the
footsteps above the player and walking through the door are useful manual checks
in the normal game (`/?start=act1`).

For a visual check, open `/tests/browser/visual-review.html?start=act1`. The toolbar
opens the actual sketchbook, turns its pages, and assembles the offering with the
same models used during play. After the blessing, **Inspect offering** opens the
completed tray again. Escape or a movement key leaves the close-up. This preview
does not write checkpoints.

## Sok’s room investigation

Open `/tests/browser/act2.html?start=act1`, then click to begin. This scenario
starts at the Act II handover and uses the separate database
`boon-sop-act2-verification`. It checks actual interaction rays for the wall board
and exposed papers, journal reading, and partial governor tuning. Follow the
three reload links to verify partial tuning, an interrupted recording, and the
completed investigation. The full warning plays at normal speed. Completed and
queued sketchbook objectives must survive every reload without duplicate items.

The toolbar can revisit the journal and gramophone for visual inspection. Add
`&visual` to the starting URL to explore without running the scripted assertions.
Normal controls: E opens the plank, reads the journal or inspects the gramophone;
left/right arrows adjust the governor; Escape or a movement key leaves inspection.

The gramophone model is procedural source in `SokRoomModels.ts`; it replaces the
render children of the existing anchor while retaining the original collider.
The journal wall board is separate from the floor planks reserved for the chest.
Investigation autosaves update CP2 until CP3 is armed for the hallway encounter.

`vo_sok_scratch_*` contains filtered English scratch VO made with the macOS Daniel
voice using `node tools/audio/make-sok-recording.mjs`. It is a timing and gameplay
stand-in for the approved Khmer performance. The reversed puzzle audio uses the
wordless generated drone, not the ceremonial smot recording. Missing voice files
fall back to the full timed subtitles, so audio failure cannot block progress.

## Hallway walker and CP3

Open `/tests/browser/walker.html?start=act1`. The page uses the isolated database
`boon-sop-walker-verification`. After CP3 is saved, follow the reload link to check
the caught path and H1 hiding. It checks the stored checkpoint, room spawn,
inventory and respect restoration, minimum lamp oil, movement/menu gates, the
actual wardrobe interaction ray and Havok stability inside the cabinet. The
walker traverses the real stairs and hall at its production speed, including the
four-second pause at Sok’s door. A second link checks completed CP3 restoration;
its H2 link runs a fresh encounter with the hall wardrobe.

The encounter starts after the recording is heard, with the notebook closed, as
Sora approaches the hall. E enters a wardrobe, F puts out the lamp, and E or Escape
leaves. Books, inventory menus and unrelated interactables cannot bypass the
active threat. Catching Sora restores an immutable in-memory copy of CP3 after
the scare and fade. Reloading the browser uses the same stored CP3, inside Sok’s
room, with the journal and gramophone already complete. Completion is saved so
the walker does not repeat. Even when browser storage fails, the in-session
checkpoint copy remains usable for a restart.

## Khmer voice recordings

Sok’s spoken language is selected by `src/episodes/ep1/data/sokVoice.json`,
independently of the subtitles. The current files are still the English scratch
performance. To use recorded Khmer dialogue, record the four paragraphs of
`SOK_RECORDING` in `src/episodes/ep1/data/investigation.ts` in the same order, using
a reviewed Khmer translation, and run:

```sh
node tools/audio/import-sok-voice.mjs km-KH part1.wav part2.wav part3.wav part4.wav
```

The importer applies the gramophone filter, writes Opus and AAC versions, and
switches the manifest after all four clips are converted. Playback and subtitle
durations follow the decoded Khmer files; the English text remains available as
subtitles. An incomplete take falls back to the complete English scratch take,
rather than mixing languages. No API key or speech service runs in the game.

For generated scratch dialogue, Azure Speech documents `km-KH-PisethNeural`
(male) and `km-KH-SreymomNeural` (female):
[official voice support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=text-to-speech).
Generation needs a Speech account/key and a Khmer script; neither is supplied by
this repository. Local actor recordings work with the same importer.

## Final ritual and CP6

Open `/tests/browser/ritual.html?continue` in a WebGPU browser. This starts from the completed chest with its three discoveries
and uses `boon-sop-ritual-verification`, never the player save database. Click to
begin each stage and follow the reload links:

1. Place the token through the actual main-burner interaction; save CP6.
2. Reload the placed token; turn around during three attempts and exhaust matches.
3. Reload with no matches; take one spare through the house altar interaction,
   start again, then reload during the hold.
4. Verify the spent spare is not refunded and hold progress resets. Take another
   spare, complete the full 25 seconds, and wait for the lamps to relight.
5. Reload the broken seal; verify the token stays consumed, chest discoveries and
   unread slip survive, controls are released and lamps stay lit.

In production the ritual pauses while the document is hidden or pointer lock is
released. The fixture drives yaw/pitch and simulates the pointer-lock input
capability so embedded automation can run the hold; hidden documents still pause.
Verify Escape and click-to-resume manually in the normal game. Ritual sound effects and the wordless
mantra layer are procedural stand-ins; the pavilion's existing smot continues.
No new ceremonial text or spoken Presence recording is introduced.

## Dawn, journal choice and Episode 2 completion

Open `/tests/browser/dawn.html?continue&choice=share` (or `choice=keep`) and click
begin. Each branch has a separate verification database. The fixture starts with
the broken seal and checks the real ending UI. Follow **Reload journal choice**
to verify the saved branch resumes its response without asking again. The next
stage checks the slip, pagoda map and third night, injects one failed completion
write and retries it, then verifies the separate `episode1` slot and portable save
code. **Reload completed episode** confirms credits and summary can be revisited
without awarding respect again. Player saves are untouched.

The completion payload remains `episode: 1`, `CP6`; `ep1.complete` and
`series.nextEpisode = 2` identify the handoff. `series.night = 3`,
`ep1.journal.shared`, `series.respect`, all lore flags, inventory and sketchbook
entries survive. The `episode1` archive is independent of the next autosave.
Episode 2 itself is not loaded by this ending. Credits offer a portable completion
save download. Vuthy's returning figure and dawn birds use procedural stand-ins.

## Fresh prologue-to-credits journey

Open `/tests/browser/episode.html` without `continue` to start a clean test run.
This uses `boon-sop-full-journey`, earns the story state from the prologue and
reloads the actual checkpoint saves. Click to begin after each reload. It tests
CP1 storage rejection/retry, CP3 catch/restore and H1, the altar/desk/CP4 flow,
CP5 immediate-loot retention on catch, chest discoveries, and CP6 failures,
spares, interrupted hold and completion through credits. Scripted movement,
interaction-bus inputs and a pointer-lock test substitute are explicit in the
source. Dialogue and the long vigil cycle are accelerated; encounter timings
are retained. `/tests/browser/cp0.html?continue` checks CP0 section selection.

The latest run and its limits are recorded in
`docs/production/episode-1-verification.md`.
