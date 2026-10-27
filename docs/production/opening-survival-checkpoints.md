# Opening, checkpoints and readable notebook

The new opening runs Studio → rainy taxi → flooded road → stealth approach → funeral courtyard → existing Episode 1 story.

## Saving and recovery

- Studio milestones and pickups save CP0, including collected props, the open drawer, the illustration and the telephone call. Reloading restores the room to that state.
- Leaving the studio records the pending taxi journey. The 72-second ride records elapsed time every eight seconds; reloading resumes the ride. Completing the ride records CP1 before entering the village. A completed journey can be skipped on later playthroughs.
- The flooded road is the first survival checkpoint. Entering the funeral courtyard records a new safe CP1, with the road encounter completed. A death on the approach returns to the road, without replaying the taxi.
- E on the physical writing folios in the studio and courtyard records progress. The courtyard folio records Sora’s position and facing as well as the story, inventory and lamp.
- Entering CP2–CP6 records a new safe chapter snapshot. Puzzle autosaves within that chapter remain separate from the death checkpoint. New-opening deaths in the hallway and beneath the house use the shared checkpoint retry flow.
- `save.autosave` and `save.checkpoint` commit together in one IndexedDB transaction when a safe checkpoint is recorded. The immutable in-memory checkpoint changes only after that transaction succeeds. Failed writes show a failure message rather than claiming progress was saved.
- New games have a run identifier, so a checkpoint from a previous playthrough cannot be adopted accidentally. The v1 save schema remains compatible. Existing saves skip the added journey/road encounter and retain their existing local encounter recovery.

Saves are local to the browser and origin. A checkpoint recorded in one browser is not automatically available in another.

## Notebook

Q opens a readable paper view with four sections: Current objective, Map, Clues & notes, and People. Objectives and checklists come from live story flags and inventory. The discovered offering drawing also has a text transcription. Maps use the actual studio/village coordinates, show Sora’s position and identify the safe desk; the approach map labels the three solid carts. It does not reveal the spirit’s position. Q or Escape closes the notebook. Focus stays inside the notebook, movement/look are gated and held movement keys are cleared on opening/closing.

## Taxi and first encounter

The seated taxi has mouse look, an authored textured cabin and seated driver, a reflected rear-view mirror, animated wipers, rain on the windshield, moving trees/puddles, headlights, thunder, engine/tyre/wiper ambience and a 14-line driver/Sora subtitle conversation. Dialogue is subtitled; the audio beds and effects are procedural. See [the taxi visual pass](taxi-realism.md) for the shared Act I assets, source rebuilds and visual verification.

The approach presence patrols the cleared path. Sustained unobstructed sight builds suspicion, a lit lamp increases visibility, and footsteps can attract it. Crouching lowers Sora behind the solid carts. The presence navigates around the same cover bounds and cannot catch through an occluder. Breaking sight lets it search and return to patrol. The tutorial area at the taxi is safe; the funeral courtyard ends the encounter and unlocks the normal arrival story.

## Verification

`npm run check`: TypeScript, ESLint, all 355 unit tests, and production build pass.

Browser fixtures use separate QA databases and never modify the normal `boon-sop` save:

- `/tests/browser/opening.html?stage=taxi` — taxi and arrival; `?stage=stealth` — road encounter; default — studio. The fixture supplies setup/views while interaction, saving, detection and retry use production handlers.
- `/tests/browser/episode.html` — earned story progression from a fresh studio through the episode. Movement is scripted, the eleven-minute vigil is advanced, and subtitle-only exchanges are shortened. Sok’s recording, the taxi, threats and ritual use their gameplay timelines.

Browser checks completed: actual drawer/phone rays; departure save-failure retry; taxi-to-CP1 transition; road catch/retry restores inventory and flags without replaying taxi; crouching behind the cart blocks the actual sight ray; courtyard completion; E on the save folio; saved position and completed encounter survive reload; Act I offering/phone → CP2; CP2 journal/gramophone → CP3; hallway catch/retry and wardrobe survival → CP4; under-house catch/retry removes post-checkpoint loot, recollection and chest → CP6; ritual turn failures, spare matches and interrupted-hold recovery → credits; completion archive and ending choice persist. The recording-to-credits report is saved as `docs/evidence/opening-upgrade/episode-regression.txt`.

Evidence: `docs/evidence/opening-upgrade/notebook-approach.png`, `notebook-house.png`, `notebook-notes.png`, `courtyard-save.png`, `rainy-taxi.png`, `checkpoint-retry.png`, `restored-road.png`, and `episode-credits.png`.
