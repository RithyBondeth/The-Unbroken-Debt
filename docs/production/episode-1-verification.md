# Episode 1 verification — 23 October 2026

Latest: [fresh current-version journey, 26 October 2026](episode-1-verification-2026-10-26.md)
passed from the studio through the revised phone arrival to credits.

## Result

A scripted fresh-prologue-to-credits journey passed in the desktop in-app WebGPU
browser, using the real Babylon.js scene, Havok player, interaction handlers,
story controllers, audio progression and IndexedDB saves. The journey earned its
inventory and story state; it did not begin from a seeded late-game save. After
fixes, affected sections were replayed from their organically earned saves.

The final journey reached the journal choice, fourth-name reveal, pagoda map,
night 3 of 7, summary and credits, and wrote the separate Episode 1 completion
archive with `ep1.complete`, `series.nextEpisode = 2`, journal choice and inventory.
Player saves in the normal `boon-sop` database were untouched.

## Defects fixed

1. **CP0 resumed in the village.** The section loader treated every resumed save
   as a village checkpoint. CP0 now selects the prologue. Its isolated browser
   check restored the studio with an empty inventory.
2. **A failed CP1 write stranded the prologue on the title card.** A simulated
   storage rejection reproduced an unhandled promise rejection and blocked the
   journey. The prologue now retains its captured checkpoint, offers Retry save,
   and emits checkpoint completion and navigates only after a successful write.
   Both the browser journey and a regression test verified recovery.
3. **Act I autosaves used CP2 metadata before Act II.** Early saves now use CP1;
   the opening explicitly advances the checkpoint to CP2. CP1 retains 23:30, and
   restored story clocks are synchronized with the checkpoint clock. Regression
   tests also cover old saves that lack the redundant metadata flags.
4. **A reachable gramophone rejected governor input.** Tuning measured the eye's
   distance from the prop's floor root. The real test reproduced a distance of
   approximately 2.1045 m while inspecting a reachable control. Reach now measures
   at inspection height. Arrow input, the sustained tuning hold and all four
   recorded-message paragraphs then passed, followed by CP3.
5. **F could not extinguish the lamp during hiding.** The general threat gate
   blocked the escape action itself. Extinguishing now works during a threat;
   relighting/refilling remain gated. The live H1 and H2 encounters and a lamp
   regression test passed.

## Checkpoints and recovery evidence

| Check | Observed result |
| --- | --- |
| CP0 | Canonical fresh checkpoint resumes studio, not village. |
| CP1 | Studio illustration, drawer, phone and exit rays work; letters and ten matches carry into village. Injected write failure recovers through Retry save. First lamp light consumes one ordinary match. |
| CP2 | Earned after offering and Act II opening; reload retains open Sok doorway and extinguished tent. Partial wall-plank discovery survives reload. Journal, tuning and complete recorded warning lead to CP3. |
| CP3 | Reload spawns in Sok's room with minimum half a tank. Deliberate catch restores inventory and respect flags. Retry survives H1; completed CP3 reload does not replay walker. Independent H2 check passes the full route, collision stability, menu gating, exit and persistent completion. |
| CP4 | Altar key, desk drawer and journal work. Scripted ash, relighting and thread snap earn CP4; reload restores the clear tent aisle and completed walker. |
| CP5 | Under-house entry earns CP5; reload restores the safe entrance. A catch immediately after J6 pickup keeps that fragment. Retry collects J2/J4, assembles the key, opens the chest and collects all three discoveries. |
| CP6 | Token placement earns CP6. Reload retains it. Three turn failures consume blessed matches without burning the seal. An altar spare permits another attempt. Reload during that attempt keeps the spare spent and resets hold progress. Another spare and a full 25-second hold break the seal and lead to dawn. |
| Coffin | Releasing E interrupts closing; holding again closes it. Hidden head turn persists, and reload restores the closed coffin without replaying its scare. |
| Completion | Earned journey reaches credits and writes the Episode 2 completion archive with journal choice and night count. |

Final `npm run check`: type-check, lint, **226 tests across 41 files**, and
production build passed. `git diff --check` passed. The added browser loading
diagnostic was also checked with the final TypeScript/lint pass.

## Reproduction

Run `npm run dev`, then open `/tests/browser/episode.html` and click to begin.
Click again after each actual checkpoint reload. Test saves use
`boon-sop-full-journey`; earned checkpoint snapshots use
`boon-sop-journey-CP1` through `boon-sop-journey-CP6`. A regression can replay an
existing earned snapshot with, for example,
`/tests/browser/episode.html?continue&step=walker&restore=CP3`.

The fixture records assertions in its results panel. `step=desk` resumes a
completed CP3 investigation without repeating the walker. It does not seed the
walker's completion flag. CP0 is checked separately at
`/tests/browser/cp0.html?continue`. The existing `walker.html?start=act1&case=h2`
and `chest.html?continue&case=coffin` fixtures cover alternate recovery paths in
separate databases; follow their reload links.

## Scope limits

This was a scripted integration playthrough, not an uninterrupted human
keyboard-and-mouse playtest. It teleports between locations, uses a mixture of
real interaction rays and direct interaction-bus inputs, accelerates subtitle-only
dialogue and advances the long vigil timer. The recorded message, walker patrol,
jar/catch recovery, key assembly and final ritual use production timing.

The embedded browser rejects pointer lock. The ritual fixture simulates that
input capability and scripted yaw/pitch; the interrupted attempt explicitly
removes it before reloading. Real mouse capture/resume, freeform navigation,
subjective audio/pacing, minimum-spec performance and a cross-browser matrix
remain separate manual validation. No claim of release certification is made.

## Arrival revision

The later phone-arrival revision replaces the in-person greetings and bedroom
blessing. Its current flow and targeted regression fixtures are documented in
[arrival-phone-flow.md](arrival-phone-flow.md). The original full-journey results
above describe the earlier arrival; they are not a claim that the entire journey
was replayed after that narrative change.
