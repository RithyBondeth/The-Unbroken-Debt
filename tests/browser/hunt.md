# Under-house hunt verification

Run `npm run dev`, open `/tests/browser/hunt.html?continue&case=entry`, and click to begin. This uses the real village, WebGPU renderer, Havok player, interaction rays, sounds and save code. It seeds a CP4 fixture in the separate `boon-sop-hunt-verification` IndexedDB database; player autosaves are untouched.

Follow the reload links through `finish` and `assembled`. The assertions cover CP5 entry, rendered post/floor occlusion, jar noise reaching the roamer, physical jar access, immediate pickup retention on catch, safe restart controls, partial save restoration, the satchel recipe, and restoration of the assembled key without duplicate fragments. Contact and sight use controlled scene positions; searches and assembly use the ordinary interaction/UI paths. AI hearing distances, patrol routes, blocked goals and frame timing are also covered by `tests/unit/hunt.test.ts`.

The **View jar** and **View roamer** buttons pause the encounter in inspection poses for visual checks. They save actual rendered frames under ignored `debug-shots/`. Reload before resuming behavioral verification after using either view.

New hunt dialogue uses subtitles only. Spatial dragging and jar scrapes are nonverbal effects.
