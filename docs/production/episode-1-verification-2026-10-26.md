# Fresh Episode 1 journey — 26 October 2026

## Result

**Follow-up correction:** a player reported hearing the studio phone but being
unable to interact. The original fixture's `free()` helper hid a normal-play
blocker: the automatic ink-blot sketchbook stayed open and disabled interaction.
The phone now puts the sketchbook and satchel away when ringing begins. The
fixture leaves the automatic book untouched before answering, and a fresh
prologue replay passed the phone ray, exit, CP1 retry and village handoff.
[Before](evidence/2026-10-26/prologue-phone-before.txt) and
[after](evidence/2026-10-26/prologue-phone-after.txt) logs capture the regression.
The regression unit test failed before the fix and passed afterward. Final
`npm run check` passed with 316 tests across 59 files. The full route below was
run before this follow-up; the affected studio section was replayed afterward.

Passed a fresh studio-to-credits run of the current episode in the desktop
in-app WebGPU browser. This includes the revised phone arrival and current
Khmer Sok recording. Started `/tests/browser/episode.html` without `continue`;
all progression and inventory were earned, with actual checkpoint reloads.
Test saves used `boon-sop-full-journey` and the fixture's separate checkpoint
snapshot databases. Normal player saves were not used.

The credits were visibly displayed. The fixture read back the `episode1`
completion archive and verified `ep1.complete = true`, `series.nextEpisode = 2`,
`ep1.journal.shared = true` and `series.night = 3`.

## Verified route

- Studio illustration, drawer, letters, kit, phone and exit; CP1 storage rejection
  and successful retry before the village handoff.
- CP1 inventory restoration, first lamp match consumption, arrival note, upstairs
  phone duties, prepared blessed matches and offering; CP1 metadata remains until
  the Act II opening writes CP2.
- CP2 reload restores the extinguished tent and open Sok doorway. Wall plank,
  journal, reachable governor tuning and all four Sok paragraphs lead to CP3.
- CP3 catch restores inventory and respect flags. Retry through H1 hiding,
  lamp extinguishing, menu gating and full patrol releases the encounter gates.
- Altar key compartment, desk key, drawer and journal lead through scripted ash,
  incense relighting and thread snap to CP4.
- CP4 reload preserves walker completion. Under-house entry writes CP5, whose
  reload restores the safe entrance. A catch immediately after J6 retains its
  fragment. J2/J4, key assembly and all three chest discoveries lead to CP6.
- CP6 token restoration, three turn failures, spent matches, altar spare and
  interrupted-attempt reload all pass. The successful full hold consumes the
  token and leads to dawn, the share-journal branch, map, summary and credits.

## Fix

The first full-journey attempt failed its studio telephone ray assertion: after a scripted
teleport, fixed millisecond delays had not guaranteed a rendered camera update.
The journey fixture now waits for two actual rendered frames after teleporting
and aiming, including its notebook-close retry. A new fresh run then passed
through every checkpoint and credits. That initial run required no production
change; the subsequent player-reported notebook blocker is corrected above.

## Evidence and checks

- [Complete assertion log](evidence/2026-10-26/episode1-journey.txt)
- [Credits screenshot](evidence/2026-10-26/episode1-credits.png)
- `npm run check`: typecheck, lint, 315 tests across 58 files and production build
  passed. `git diff --check` passed.

## Dia / packing follow-up

The player's diagnostic screenshot showed `last use: interact_telephone`, with
`active=true`, all menu gates clear and `ringing=false waiting=false answered=false`.
This confirms the phone use reached the story handler before the call was armed;
it does not demonstrate that Dia lost the keyboard event. The original fixture
granted the studio pickups through direct interaction-bus events, so it did not
establish their accessibility during normal play.

The phone and exit now give a specific hint for the first missing kit item,
including where to find it. The development panel also lists missing kit items.
The hurricane lamp has an invisible pickup volume covering its silhouette so
looking through its open centre still selects it; that volume draws no outline.
The fixture now picks up the letters, matches, satchel, sketchbook and lamp using
actual rays and keyboard events. It waits for the player to settle after a
teleport and approaches the lamp outside the console-table collider. The fresh
studio replay then reaches the phone, exit and CP1 handoff.

Four additional regression cases cover each missing item's phone hint. Final
checks pass with 320 tests across 59 files. Native Dia playback is still verified
by the player; the automation tool cannot capture Dia's screen in this session.

## Playthrough limits

This is a scripted integration playthrough, using the real scene, physics,
story controllers, audio, interaction rays and saves. The fixture teleports
between locations, uses some direct interaction-bus inputs, accelerates
subtitle-only dialogue and the long vigil cycle, and substitutes pointer-lock
capability for the ritual. The recording, patrol, catch/recovery and successful
ritual hold retain production timing. This run follows H1 and the share-journal
ending; it does not reverify H2, the optional coffin sequence or the keep-journal
branch. Free navigation, actual mouse capture, subjective pacing and cross-browser
coverage remain separate playtest work.
