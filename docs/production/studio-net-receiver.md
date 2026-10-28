# Gathered mosquito net and telephone receiver

The studio's closed cone and cylindrical knot are replaced by open gauze with smooth gathered folds, a cinched waist, an uneven stitched hem, an edge seam, a cotton tie and a ceiling hook. `tools/areas/ep1_area_studio.py` generates the geometry and the repeating alpha weave texture at `art-source/textures/ep1/T_studio_net_weave_BC.png`. Rebuild/export/optimize the studio using the commands in `studio-hook-shelf-fix.md`.

`src/player/TelephoneReceiver.ts` creates a single-ear magneto receiver shared by the wall phone and first-person hand. It has a turned ebonite grip, shaped ear shell, perforations, rolled metal rim, grip collars and cord socket. The former unrelated three-sphere handset is removed. Sora's phone pose places the grip across the curled fingers and keeps the earcup inside the view. Parts merge to two material meshes per receiver.

The world cord follows the held receiver's socket during calls, using an updatable tube with sag. When the call ends it reconnects to the receiver on its hook. The same production `holdPhone` presentation and prologue update drive the isolated fixture's Preview receiver toggle. Story flags and dialogue are not changed by that fixture toggle.

Validation: 19 targeted hand/phone tests pass across two files. TypeScript, targeted ESLint and the production build pass. The isolated studio fixture supplies Gathered net and Telephone views, Preview receiver and native renderer screenshots. Evidence: `docs/evidence/studio-net-receiver/`.
