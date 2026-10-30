# Episode 1 phone arrival

Sora arrives after Mak Yey and Vuthy have left for their relatives’ house, where
Mak Yey can rest. A note on the small table beside the pavilion directs Sora to
the ringing telephone in the upstairs hall. Both relatives speak on that call;
Vuthy promises to return at dawn. The call gives the vigil duties and offering
request. The vigil timer starts only when the call finishes.

Three matches, blessed before the family left, wait in a box tied with red
thread on the ancestral altar. The note includes their instructions. Picking up
the box adds three blessed matches once. Completing the offering no longer
creates matches or produces a voice from Mak Yey’s empty bedroom. Sora checks
the tray against Kanha’s drawing. New games require the matchbox to have been
collected before the Act II handover; older completed-offering saves keep their
existing progression and receive no duplicate box.

The note, finished call and match pickup autosave at the current checkpoint.
An interrupted call can restart. Pending sketchbook notes and partial offering
slots are included in captures, so collecting matches during the offering does
not lose ingredients after reload. Mistakes survive reload too.

Vuthy returns physically at dawn for the existing share/keep journal choice.
Afterward he returns to Mak Yey. The closing reveals, summary, credits and
Episode 2 completion archive retain their existing progression.

The hall telephone uses the same moving cloth-lead implementation as the Phnom
Penh studio. Its cable connects the wall terminal to the receiver socket on the
hook, follows Sora’s held receiver during the call, and returns to the hook
after hanging up. The separate wall line remains in place. The moving lead is
not pickable and is kept separate from the hidden receiver and static geometry.
`src/player/TelephoneCord.ts` supplies the shared sag and mesh updates.

## Verification

- `tests/browser/house.html?start=act1&view=phone`: **Preview receiver** toggles
  the real held-phone presentation without advancing story flags. The report
  checks both cable endpoints while lifted and after returning to the hook.
- `tests/unit/telephoneCord.test.ts`: transformed endpoints, lifted/hidden
  receiver, hang-up, reused geometry and non-pickable cable.

- `tests/browser/arrival.html?start=act1`: physical interaction rays for note,
  telephone and matchbox; follow each reload and click to begin. Uses the
  isolated `boon-sop-phone-arrival-verification` database. Covers interruption,
  finished call, partial offering, notes, collected matches and spent matches.
- `tests/browser/act1.html?start=act1`, then `?continue`: offering, incense
  handover, physical door opening and CP2 reload without duplicate matches.
- `tests/browser/dawn.html?continue&case=entry&choice=share` (or `choice=keep`):
  journal choice, reload, reveals, completion save retry and credits. Follow the
  reload links; uses isolated databases.
- `npm run check`: typecheck, lint, unit tests and production build.

These browser fixtures use scripted movement and accelerated subtitles. They
verify integration and persistence; free navigation, real mouse capture and
subjective phone/audio pacing still need a human playtest.

Verified on 2026-10-23: arrival interruption/replay and every reload stage passed,
including partial-tray ingredient recovery and pending phone notes. Act I reached
CP2 and restored without duplicate matches. Both dawn journal branches reached
credits, retained their portable Episode 2 handoff and recovered a simulated
completion-save failure. The completed share branch also passed its final reload.
`npm run check` passed: 231 tests across 42 files, lint, typecheck and build.
