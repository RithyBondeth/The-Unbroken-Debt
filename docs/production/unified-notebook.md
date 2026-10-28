# One notebook, two presentations

Q opens Sora's physical sketchbook on the live objective. Story discoveries
still open it on the new entry. The flat panel is now an optional “Read clearly”
mode of the same notebook, accessed with R or its control-strip button.
The physical book and hands are hidden while that mode is visible.

Both presentations consume `NotebookContent` and `NotebookMap`: current tasks,
checkpoint details, known people, discovered notes, found documents, and the
actual-position location plan. Historical objective entries remain readable in
Notes, while Objective shows only the current state. The objective's checklist
uses the facing page, with larger text. Missing lore and unrevealed people are
not exposed as discoveries.

Live entries never enter `sketchbook.written`; that set retains only durable
story IDs, so existing save/checkpoint formats are unchanged. The physical pages
refresh while open without changing the active entry, or interrupting a turn or
writing animation. “Read clearly” returns to the selected section.

Controls: Q/Esc closes either presentation; R switches between physical and
clear reading; 1–5 selects Map, Objective, Notes, People, Lore; A/D turns physical
pages. Tab/Shift+Tab navigates notebook controls while it is open. Reading holds
movement/look. The satchel, active threats, and hiding keep their existing gates.

## Verification

`/tests/browser/notebook.html` uses production code and the separate
`boon-sop-unified-notebook-qa` database. “Verify flows” checks physical-only
opening, live objective, clear-mode hiding, section return, closing during page
turns, automatic discovery, rapid Q, input release, forced threat dismissal, and IndexedDB save/load
restoration. The matchbox button permits a visible live-checklist comparison.

The full unit suite passed (372 tests / 71 files, `npm test -- --maxWorkers=1`).
The production build and scoped ESLint checks passed. Browser verification
reported no console errors. Focused coverage includes
live task updates, historical notes, clue/lore/people visibility, map coordinates,
checkpoint-derived content, and facing-page layout.

Forced threat/hiding dismissals lower the book immediately so they cannot hold
movement during the closing animation. Both night-circle state and its readable
text are derived from the same discovered entries. The game canvas regains
keyboard focus on close, and reader refreshes preserve scroll position.

## Portrait and map art revision · 2026-10-28

People now uses four distinct graphite portrait studies, with one person per
physical page. The transparent atlas is decoded once before book construction;
page turns only copy the selected cell. Graphite is multiplied into the existing
paper in both presentations. Vuthy remains hidden until discovered. Asset source
and quadrant order are recorded in `art-source/textures/ep1/notebook/README.md`.

The production map uses both facing pages. Night circles sit below the plan,
leaving the drawing area clear. Larger labels, stronger linework, recognisable
studio furniture, door swing, stairs, coffin and window marks replace anonymous
boxes. The village axis runs horizontally across the spread; its geometry and
player position undergo the same rotation. Physical-only offsets keep key marks
and labels away from the binding. Read clearly retains the same geometry on a
larger, unbroken map. The browser fixture has studio, village and approach map
preview buttons and checks portrait pagination and the two-page map layout.

## Reading clearance and hand motion · 2026-10-28

Sections sit above the book; page actions sit in one bar below it (two balanced
rows on a small screen). A ResizeObserver measures the bars, and the book fits
its full cover between them using the actual camera field of view and aspect.
The seven-night label and map legend are larger. Both thumbs grip below the
page text rather than resting on the night circles.

A page turn takes 1.05 seconds: reach, pinch, carry, release, return. The opposite
hand supports the cover throughout; the active hand follows the same leaf curve
that deforms the paper. Forward turns use the right hand, backward turns the
left. Closing or entering Read clearly cancels the gesture cleanly. A small
weight shift accompanies the turn, with subdued breathing while holding still.

Sok's photographic funeral print now uses his graphite portrait identity in both
the embedded village image and the close inspection photo. Packed Blender source
and the drawing generator retain that identity on rebuild. The independent family
archive prints are unchanged. The tour has a `05b-sok-portrait` close view.
