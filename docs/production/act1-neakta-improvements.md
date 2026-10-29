# Episode 1 · Act I Neak Ta and pacing

28 October 2026

The road from the taxi to the funeral courtyard is clear of the former cart
slalom and forced stealth chase. Shrine and gate apparitions remain atmospheric
glimpses. The shrine form now lasts long enough for a deliberate head turn and
laboured breath to register before it recedes.

The later obstacle, A1-11b, is **Keep the vigil in darkness**. It starts beneath
the pavilion after the offering, prepared-match pickup and full incense cycle.
The player has five seconds to read the warning and extinguish the lamp before
the listening presence begins its patrol across the approach to the gate.
Staying dark and quiet lets it pass. Light, running and sustained exposure can
draw its attention; the player must break its view and wait for it to search.
The passage lasts at least 34 seconds and cannot end during a chase. Act II's
gust and upstairs footsteps follow its completion.

The pre-encounter checkpoint preserves offering and incense progress and
restarts beneath the pavilion. Completion is checkpointed before the Act II
handover. Incense upkeep pauses during this forced wait. Existing saves that
already completed the old road encounter retain their completion; Act II saves
do not repeat it. The `ep1.early.*` flags and class name remain for compatibility.

The standing asset has a dedicated aged-skin texture and normal bake, hollowed
cheeks and temples, muted inset eyes, and darker damp cloth. Five morphs create
breathing, a delayed head turn, opposed arm/foot motion and a half-finished
hand gesture. The gate form eases turns and decelerates its pose when it stops;
footsteps are driven by distance travelled. Each clone owns its morph weights.
Seated shrine statues retain their materials and geometry.

Audio combines spatial breathing, foot drags and irregular brass strain with
a quiet beating drone. Intensity follows distance and suspicion; entry and
exit fade the breath and drone. Wildlife falls quiet over 2.4 seconds during
threats and returns gradually afterwards. Ceremonial chanting is unchanged.
All added sounds are wordless procedural effects and obey the existing threat
bus and user volume settings.

Verification entry points:

- `npm run check`: TypeScript, ESLint, unit suite and production build.
- `/tests/browser/act1.html?start=act1`: real offering, delayed encounter,
  survival, checkpoint and Act II transition. Its `?continue` branch checks CP2.
- `/tests/browser/shadows.html?start=act1&landscape`: production lamp, skin,
  profile and animated facial/body poses.
- `/tests/browser/opening.html?stage=road`: quiet arrival; the **Keep the vigil**
  button stages the later obstacle for listening and catch/retry checks.

Browser fixtures use separate IndexedDB databases. The long incense clock and
dialogue are accelerated in the Act I scenario; the passage and Act II cues run
at production speed. Sound design still needs subjective headphone playtesting.

Verified locally on 28 October: `npm run check` passed all 376 tests across
72 files, type checking, lint and the production build. The real WebGPU/Havok
Act I scenario reported `TRANSITION PASSED`, including the calm arrival, removed
carts, later passage, committed checkpoint, paused incense upkeep, extinguished
pavilion lights and open upstairs doorway.
The CP2 reload then reported `RESTORE PASSED`: spawn, opened door, extinguished
lamps, matches, collected lore and the Act II objective all persisted.
