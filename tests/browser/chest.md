# Chest, ritual preparation and corpse verification

Run `npm run dev`, open `/tests/browser/chest.html?continue&case=entry`, and click to begin. Follow each reload link: `unlock`, `contents`, `complete`. This seeds a CP5 fixture with the assembled key in the separate `boon-sop-chest-verification` database. Player autosaves are untouched.

The real village, Havok player, interaction rays, models and IndexedDB verify:

- Four seconds looking away changes one corpse pose; watching prevents movement. All five poses fit the conservative visibility guard.
- The loose boards lift independently, expose the floor recess, and stay lifted after reload.
- The assembled key opens the chest once and is consumed. Crouching lets the player reach each object inside.
- Token, map and slip are collected individually, disappear, and stay absent on reload.
- The slip remains sealed and unread. All three discoveries prepare the ritual and save SB-07, without advancing to CP6 or breaking the seal.
- A later catch by the roamer returns to CP5 with every chest item retained and the key still consumed.

`?continue&case=gallery` uses a second isolated database with an open, unlooted chest for visual inspection. It captures actual frames in ignored `debug-shots/`. **View corpse** captures the body in its funeral setting. The ordinary behavioral verification never uses the gallery fixture.

New dialogue is subtitle-only; plank, lid and pickup cues are nonverbal effects. Pure progression and observation timing tests are in `tests/unit/chestProgress.test.ts`.

The gallery also provides **Corpse pose 0–4** controls for the imported anatomical asset. Each button pauses progression, selects one baked morph state, and captures `sok_corpse_pose_N.png`. Asset tests in `tests/unit/corpseAsset.test.ts` check rest weights, skin textures / UVs, surface orientation, the full-length shroud and all five pose bounds. Rebuild instructions and CC0 provenance are in `art-source/characters/sok/README.md`.

`?continue&case=coffin` seeds the Bronze Token discovery with the coffin still shut. It checks the approach reveal, actual body placement below the rim, handle reach, releasing a partial pull, the full three-second hold, and the head turn behind the nearly closed lid. Follow **Reload the closed coffin** to verify the closed lid and head-turn milestone persist without replaying the scare. It captures `coffin_reveal.png`, `coffin_closed.png` and `coffin_closed_reload.png`.

The reveal begins with a timber creak, then a sudden hinged opening and impact. Sok must remain exposed for two seconds before the handle becomes usable. Releasing E lets the lid yield back open; menus pause the encounter. Interrupted opening/closing resumes open, while a completed closure stays shut. No new voice recording is used. State-machine coverage is in `tests/unit/coffinProgress.test.ts`.

Creative reference: Joko Anwar's emphasis on physical presence, practical effects and atmosphere in _Pengabdi Setan_ ([interview](https://www.liputan6.com/showbiz/read/3103009/ini-alasan-joko-anwar-ogah-pakai-cgi-di-pengabdi-setan)). The existing Khmer funeral setting is retained.
