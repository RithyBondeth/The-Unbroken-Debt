# Performance pass — 25 October 2026

Measured on the reference MacBook Pro M1 Pro (Apple Metal 3) in the desktop
in-app browser, Act I village (`?start=act1`), standing at the player spawn on
the forest path. Forced presets with the new development-only `?quality=` URL
parameter. Each heading: 1.2 s settle, then 3 s of frames.

## Caveats

- The in-app pane was 676×900 (Low) and 812×1080 (Medium), smaller than a
  1080p window, so GPU cost is understated. Treat GPU numbers as a floor.
- The display runs at 120 Hz: 8.3 ms is the vsync cap, not the frame cost.
- Run-to-run variance was about ±2 ms (the same Medium view measured 15.8 and
  17.4 ms average in two runs).
- No GPU timer on this Mac; "CPU" is time inside `scene.render()`.

## Results

| Preset | Heading | Active meshes | Avg ms | p95 ms | CPU ms |
|---|---|---|---|---|---|
| Low | 0° (into the forest) | 75 | 8.3 (vsync) | 9.1 | 4.7 |
| Low | 90° | 114 | 8.3 (vsync) | 9.0 | 5.2 |
| Low | **180° (down the village)** | **428** | **10.2** | **11.2** | **8.3** |
| Low | −90° | 107 | 8.3 (vsync) | 9.0 | 4.9 |
| Medium | 0° | 75 | 10.4 | 12.4 | 5.7 |
| Medium | 90° | 114 | 11.4 | 13.0 | 6.6 |
| Medium | **180°** | **428** | **15.8** | **20.9** | **12.0** |
| Medium | −90° | 107 | 11.3 | 13.3 | 6.5 |

**Medium misses 60 fps at the 95th percentile looking down the village**
(20.9 ms against 16.7 ms), on the Recommended machine and below 1080p. Low holds
60 fps here, but with 8.3 ms of CPU; an integrated-graphics laptop with a slower
CPU (the Minimum spec) may land near 12–16 ms on the same view, because CPU cost
does not fall with dynamic resolution.

## Where the time goes (Medium, 180°)

Scene instrumentation, averaged over 3 s:

| Part | ms |
|---|---|
| Active mesh evaluation (culling 1,625 enabled meshes) | 2.8 |
| Mesh draw submission (`render`) | 7.5 |
| Camera render total, including the post-processing chain | 14.4 |

- 2,225 meshes in the scene, 1,625 enabled. 752 visible meshes are under 60 cm.
- 428 drawn: 241 merged static batches plus 187 separate meshes (shrine pieces,
  rag trees, island trees, tingmong, offerings, puddles).
- 3.2 million vertices drawn within the 60 m far plane.
- The post chain on Medium has 18 passes: SSAO (5), volumetric fog (2), TAA (2),
  bloom (4), image processing, sharpen, grain, chromatic aberration, FXAA. FXAA
  alongside TAA is deliberate (it covers camera moves, when TAA stands aside).

## Fixed in this pass

- **Light limits overwritten by the glTF loader** (`src/render/lightBudget.ts`).
  Every glTF load raised every material in the scene to the scene's light count
  (18–23), undoing VillageLights' 8 and the sketchbook's 4: 330 materials compiled
  oversized shaders and WebGPU clamped them back with about 50 warnings at load.
  Limits are now restored as each load becomes ready: 333 materials at 8, 25 at
  4, no warnings. Frame time change is within noise; the gain is smaller shaders
  and a clean console.
- **Development-only `?quality=low|medium|high|ultra`** forces a preset in the
  real game, as the spikes already allowed.

## Tried and rejected

- Distance-culling meshes under 1 m beyond 35 m (Babylon LOD to nothing): only 17
  fewer draws (428 → 411), about 1.3 ms CPU, within run variance; most small props
  are already inside merged batches. Not worth the pop-in.

## Options, in order of expected gain (need a visual check)

1. **Pull the far plane in when looking down the village**, or fade it with the
   fog: at density 0.028 the last 20 m of the 60 m far plane are 70–80 % fogged.
   A 45 m far plane removes the most distant batches. Needs your eye on the vista.
2. **Selection octree for static meshes** (`scene.createOrUpdateSelectionOctree`)
   to cut the 2.8 ms of culling. Every mesh the story scripts move must then be
   kept out of the octree or marked dynamic, so it needs a full playthrough.
3. **Batch the 187 separate props** that do not move (shrine pieces, rag trees,
   puddles): check why `batchStatics` leaves them alone (keep list, parenting or
   material) and merge the static ones.
4. **Cheaper post chain on Medium**: SSAO at half its samples, or bloom off
   outdoors, measured with the S7 `&bench=1` costs.

Measure again in a standalone Chrome window at 1920×1080 before and after, as
the Development Plan asks; the in-app pane throttles and is too small.
