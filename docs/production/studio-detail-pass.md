# Studio detail and pickup pass — 26 October 2026

The matchbox was too small and easy to overlook beneath the desktop. The drawer
now has a pale cedar interior, sides, back, moulded front and brass drop pull.
It opens farther, exposing a larger cardboard matchbox with a printed cream/red
label and striker strips. An invisible pickup volume covers the box. Opening the
drawer leans the view toward it and shows an explicit E prompt; movement keys
leave inspection. The pickup still grants exactly ten ordinary matches.

The wall telephone is rebuilt around its existing interaction anchor: chamfered
walnut board and cabinet, shaped twin brass bells and rolled rims, clapper,
ebonite transmitter and perforated diaphragm, separate receiver, hook, braided
cord, magneto crank, slotted screws, enamel number plate and porcelain terminals.
The receiver disappears from its hook during the call and is shown in Sora's
hand. It returns when the call ends. The old chalk-like outline is disabled for
the phone and drawer so their materials remain readable.

The room pass adds a green curved-glass banker's shade, weighted brass base,
lamp wiring, a porcelain writing sconce and switch, a marked ruler, pen cup,
envelopes, rug fringe and skirting nails. The carried letters have paper edges,
an addressed top envelope and narrow cotton ties. A warmer writing light, cool
window fill and softer close-range light falloff reveal material detail without
turning nearby paper and metal white. The original room layout and colliders
remain in use.

The new geometry and canvas-painted textures are original procedural work in
`src/episodes/ep1/prologue/StudioDetails.ts`; no new external assets or runtime
downloads were introduced. Decorative parts sharing a material are merged,
while the receiver and drawer retain their moving hierarchies. Imported glTF
handedness is handled when parenting the new world-oriented models.

## Verification

A fresh studio run in the desktop WebGPU browser passed:

- Physical illustration and drawer interaction rays.
- Drawer opening focuses the matchbox; a single E key event collects ten matches
  without another aim or teleport to the box.
- Physical rays and E events collect the letters, satchel, sketchbook and lamp.
- The automatic notebook closes for the ringing phone.
- Physical phone interaction lifts the new receiver; the completed call puts it
  back on the hook.
- The door, CP1 save-failure retry and village handoff pass.

`npm run check` passes: typecheck, lint, 320 unit tests across 59 files and the
production build. `git diff --check` passes. This is an affected-section replay;
the later episode was not replayed for this visual pass. Dia itself remains
outside the automation tool's available screen capture.

- [Browser assertion log](evidence/2026-10-26/studio-playtest.txt)
- [Matchbox and drawer](evidence/2026-10-26/studio-matchbox.png)
- [Telephone](evidence/2026-10-26/studio-phone.png)
- [Room overview](evidence/2026-10-26/studio-room.png)

For an isolated visual review, run the dev server and open
`/tests/browser/studio.html`. Click to begin, then use the room, desk, phone,
window, bed and drawer buttons. The preview automatically inks the illustration
to unlock prop interactions and uses its own `boon-sop-studio-review` save
database. The full-journey fixture remains `/tests/browser/episode.html`.
