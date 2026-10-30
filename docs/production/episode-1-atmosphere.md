# Episode 1 mist and sound — 30 October 2026

The dark lighting calibration is retained. This pass adds local, low mist and
occasional environmental suspense without changing encounters, inventory or saves.

## Mist

Eight soft-edged pockets sit in trail-side vegetation, beside the flooded fields
and beneath the house. Their tops are below one metre; under-house volumes stay
below 0.5 m. The walking route has only thin edge spill, and nearby working space
around the camera remains clear.

On Medium and above, the existing reduced-resolution volumetric pass integrates
the pockets. A small cool sky-bounce contribution makes the wet air legible only
inside those pockets. The sky, exposure and distant rain haze are unchanged.
The slow drift is computed once per sample, shared by all eight regions.

Low uses one particle system capped at 40 flattened, softly fading wisps, with
one generated 128 px alpha texture. It adds no depth pass or extra scene capture.
Neither version changes geometry or colliders. Dawn removes the local mist.

## Sound and pacing

During unscripted forest exploration, the first eligible sequence waits 22–38 s:

1. Insects, frogs and canopy wind gradually subside for 3.2 s.
2. One of three wet-foliage takes plays from a fixed off-screen bush, 4–13 m away,
   with HRTF positioning. No enemy is spawned and no fake attack/footstep cue is used.
3. Turning within 36° of that source fades the rustle in about 0.3 s; otherwise
   the take ends after 4.6 s. The source never follows the camera.
4. A 2.6 s listening interval leads into a slow ambience recovery. Another sequence
   waits 75–140 eligible seconds, so the cue does not become a constant loop.

The director cancels for dialogue, readers, inspection, inventory, hiding,
cutscenes, released pointer lock, hidden tabs, leaving the forest and authored
presences/threats. A cancellation gives a fresh cooldown. Visibility and pointer
listeners stop an active sound even if the render loop no longer produces frames.
The original shrine/gate approaches and Act II's authored silence take priority.
Rain and ceremonial recitation are not ducked.

Quiet stereo canopy gusts distinguish the outdoors; soft cloth movement sits
under the pavilion recitation. Existing roof rain, shutters and under-house drips
retain their zones. All new takes are procedural, wordless stand-ins and require
no download, external audio service or API key. Dawn stops these layers.

## Review and checks

Open `/tests/browser/atmosphere.html`. It starts with graphics only and isolated
`boon-sop-atmosphere-review` saves. **Enable atmosphere sound** starts the actual
production AudioSystem, NightLife, ForestAtmosphere and Soundscape layers after
a click, without loading unrelated recorded footsteps. Embedded controls emulate
pointer-lock look input, as the ritual test does; normal game input is unchanged.

Views cover the trail, a mist pocket, pavilion, under-house area and paddy edge.
**Toggle mist** provides a comparison. **Verify turn response** uses the real
cue director and then scripts a turn toward its world source; the onscreen trace
records every transition. Dialogue and paused-input controls test preemption.
Use `?quality=low` for the particle fallback. Captures go to `debug-shots/`.

- All 13 new layout, timing, synthesis and runtime-audio tests pass, including
  fixed source placement, turn response, dialogue/encounter priority and tab hiding.
- All 38 focused atmosphere, existing night and house audio tests pass.
- Type checking, ESLint and production build pass.
- Live production-audio review recorded hush → movement → listening immediately
  after turning → recovery → waiting, with no authored presence active. Dialogue
  and paused input cancelled the hush and returned the director to waiting.
- Medium mist and Low fallback loaded without new browser errors. Existing loader
  warnings about `hide_` nodes and asset-container hierarchy remain.
- The full 416-test run had 412 passes and four failures in other in-progress work:
  two courtyard mocks lack the newly added telephone-cord model, and two rural
  asset checks fail on board spacing/UVs. This pass does not edit those assets or
  the phone flow. These failures are not reported as a passing full suite.

This is a focused atmosphere verification, not a fresh full-episode playthrough
or a cross-device performance certification. Image and trace evidence is under
`evidence/2026-10-30-atmosphere/`.
