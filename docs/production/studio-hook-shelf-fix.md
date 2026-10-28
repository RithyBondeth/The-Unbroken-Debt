# Studio lantern mounting and shelf

The lantern's former block hook was above and behind its handle. The studio builder now measures the actual bail vertices and fits a curved brass hook to them, with a wall plate and fasteners. The lantern retains its original interaction anchor and pickup hierarchy. Source geometry measures less than 0.1 mm between the handle and supporting hook.

The shelf candle previously overlapped the encyclopedia set. Nine separate clothbound study volumes replace that set, with varied heights, coloured covers, page blocks, binding lines and stamped spines. The candlestick moves clear of the books by 20.6 cm, with a wax candle and wick above the holder. The procedural flame now specifies all three dimensions; its former missing depth allowed a metre-deep sphere to appear as a flattened glowing shape. Soft candle falloff and a book-only warm bounce reveal the bindings without bleaching the wall. Both candle lights and the flame switch off together for P05. Imported studio materials allow the room's lights within the eight-light device budget.

Rebuild the studio with:

```sh
blender -b --factory-startup -P tools/areas/ep1_area_studio.py
blender -b art-source/blender/ep1/ep1_area_studio.blend -P tools/export-blend.py -- art-export/ep1/ep1_area_studio.glb
node tools/build-assets.mjs ep1/ep1_area_studio
```

The isolated `/tests/browser/studio.html` fixture includes Lantern hook and Books and candle views, E interaction and native screenshot capture. It waits for the initial checkpoint write before triggering the illustration, then uses the production pickup handler. Browser verification confirmed `interact_lamp` focus and collection with E; no console errors were recorded. The 17 prologue phone/sound tests pass, along with TypeScript, targeted ESLint and the production build. Evidence is in `docs/evidence/studio-hook-shelf/`.
