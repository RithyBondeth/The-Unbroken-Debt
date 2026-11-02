# Episode 2 authored scenes

- `ep2_area_pagoda.blend`: independent chapter environment, from `tools/areas/ep2_area_pagoda.py`.
- `ep2_cinematics.blend`: living villagers with weighted poses baked to morph targets, seated Sophal with a separate draped robe, harvest huts, rice and fire logs; from `tools/ep2/build-cinematics.py`.
- `clinic_photo.blend`: the staged floating-clinic contact print, from `tools/ep2/render-clinic-photo.py`.

Buildings and surfaces reuse Episode 1's `tools/areas/kit.py`/`khmer.py` and the CC0 library in `art-source/library/polyhaven.json`. Human anatomy, weights, macro targets and photographic skin come from the official CC0 MakeHuman sources recorded in `art-source/characters/sora` and `art-source/characters/sok`; the same source licences and contributors apply to these adapted characters. Project-authored poses, garments, scene composition and props are editable in these packed sources.

Both world scenes have an X-reflecting authoring parent to compensate Babylon's glTF import. Runtime coordinates match the gameplay data. Do not add a second reflection. See `docs/production/episode-2-implementation.md` for exact rebuild and review commands.
