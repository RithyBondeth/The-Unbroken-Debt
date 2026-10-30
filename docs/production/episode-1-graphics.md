# Episode 1 graphics pass — 29 October 2026

This pass improves the existing Episode 1 assets through lighting, surface shading
and rendering. It covers the studio, taxi and the shared village used by Acts I–III.
It does not replace the environment meshes or claim photographic asset quality.

## Rendering and clarity

- SSAO and TAA now use half-float render targets before exposure and ACES tone
  mapping. Their default 8-bit targets discarded dark color differences and
  clamped bright values before the HDR pipeline could process them.
- Smaller, softer contact occlusion replaces the broad darkening of foliage.
- Grain is subtle and stable; ordinary color aberration is below a pixel, with
  a brief increase on scares. Vignette and bloom no longer obscure the periphery.
- The episode LUT retains warm highlights and cool shadows but reduces split
  toning and lowers its black cutoff from 2% to 0.4%, preserving dark texture.
- Textures use 4× / 8× / 16× anisotropic filtering on Low / Medium / High–Ultra.
  PBR materials use specular antialiasing and two-sided normals on thin surfaces.
  New resources are handled once, including models loaded after initial setup.

## Lantern, weather and materials

The lantern has a warm-white globe rather than saturated orange illumination,
22 units at its calibrated distance instead of 10, and an 11.5 m cutoff instead
of 9 m. Existing soft falloff and close-inspection shading remain in place.
Oil, shutter, match and encounter rules are unchanged.

The sky fill and exposure lift modestly, while the fog is less dense. The lamp-out
view remains substantially dimmer than the lit view. Low's inexpensive material
fog now receives the same night/dawn settings as the volumetric presets. Dawn
restores its exposure cap and disables the night-sight fill.

Fog clears around the eye over 0.6–2.8 m. Camera-carried light contributes less
scattered glare, while practical flames retain halos. Depth-aware four-tap
upsampling keeps low-resolution fog from bleeding over foreground silhouettes.
Stable spatial dithering avoids crawling fog noise while TAA pauses on turns.

Rain dressing preserves each material's authored roughness factor and maps
instead of assigning the same finish to cloth, wood and mud. Its slight darkening
is applied once per material. The taxi and village share this treatment.

The taxi's existing GPU foliage wind is now shared with the village. Leaves and
grass sway subtly without rebuilding geometry, animating trunks, or changing
colliders. No textures or environment triangles are added by this pass. Half-float
post-process targets use more render-target memory than the old 8-bit targets.

## Review

Open `/tests/browser/tour.html` for the production scene tour, or add
`?area=studio` for the prologue. The tour now supports:

- `quality=low|medium|high|ultra` to choose a graphics preset.
- `view=01-forest-path` (or another named view), a player-lamp toggle and a capture button.
- `capture=graphics-final&run` to capture all views with a distinct filename prefix.
- `fixed` to hold full preset resolution for image comparisons. Omit it when
  measuring ordinary dynamic-resolution behavior.

Unlit manual captures receive an `-unlit` suffix. The tour uses isolated saves.
The forest inspection fixture also offers an optional overcast fill; all evidence
for this pass uses production lighting with that fill off.

## Verification

- All 395 tests in 77 files pass (`npm test -- --maxWorkers=4`). Unbounded workers
  timed out in the existing large taxi bounds test while competing with live
  WebGPU review; limiting concurrency passed the same assertions unchanged.
- Type checking, ESLint, formatting checks and the production build pass.
- The Medium village tour captured all 18 views, including forest, pavilion,
  house, investigations, under-house area and ritual burner. No browser rendering
  errors were reported during the tour.
- Low-preset forest rendering and the lantern-off view were checked separately.
  The studio tour captured all four views without rendering errors. Taxi road
  and fixed lightning views were also rendered and captured without errors.
- Evidence images are in `evidence/2026-10-29-graphics/`. The original forest
  capture was made with a temporary Vite source override serving the previous
  graphics modules from Git HEAD; the current working files were not reverted.
- Existing loader warnings about `hide_` nodes and asset-container hierarchy
  remain. They also occur with the original graphics modules.

These checks cover rendering and unit regressions; they are not a fresh
prologue-to-credits gameplay completion or a benchmark across different GPUs.

## Brightness refinement

Following the user's review, night exposure is reduced from 1.65 to 1.55, with
the dark-adaptation cap reduced from 2.45 to 2.3. Sky fill drops from 0.32 to
0.28, moonlight from 0.26 to 0.24, and night sight from 2.0 to 1.8. Fog ambient
light is reduced slightly too. The lantern's useful illumination, HDR precision,
texture detail, fog clarity and dawn settings are retained. The updated forest
capture is `evidence/2026-10-29-graphics/forest-refined.png`.

The second requested reduction sets exposure to 1.45 (adaptation cap 2.1), sky
fill to 0.22 and moonlight to 0.20. Night sight is reduced to 1.4 over 2.6 m,
with dimmer fog and background light, retaining the lantern's illumination and
the improved rendering. Type checking and all 18 lighting/cloud tests pass.
A fresh capture was unavailable after the local preview connection failed;
the earlier evidence images show the previous tuning.
