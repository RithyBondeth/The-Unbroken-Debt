# Stable picture, graphics settings, phones and tablets — 28 November 2026

Report: standing still without touching anything, the game kept moving and the
picture shook. Asked for: a steadier, smoother game; graphics settings players
can match to their device; play on phones and tablets.

## Why the picture moved and shook at rest

Three causes, from largest to smallest.

1. **Sora never stopped.** `PlayerController` set the Havok character
   controller's `acceleration` to 14. In Babylon that field is a *gain* (the
   share of the speed difference made up each step; 1 is all of it), and
   `maxAcceleration` (default 50 m/s²) is the limit. With a gain of 14 every step
   overshot the target, was clamped to ±0.83 m/s, and overshot back the other
   way. Walking speed flipped between 0.83 and 1.67 m/s on alternate frames
   (judder while walking), and after the keys were released the capsule settled
   into the same two-frame cycle around zero. Sora crept on at about 0.35 m/s and
   the head-bob restarted. Now the gain is 1 and the configured 14 m/s² is the
   limit: speed ramps to 1.6 m/s in about 0.11 s and stops dead.
   **Gameplay note:** the cycle also made Sora's speed depend on the frame rate.
   Measured on Havok (4 s of steady input, flat floor), in m/s:

   | Mode (configured) | 30 fps before | 60 fps before | 120 fps before | Now, any rate |
   |---|---|---|---|---|
   | Walk (1.6) | 0.90 | 1.29 | 1.48 | 1.60 |
   | Crouch (0.9) | 0.90 | 0.89 | 1.06 | 0.90 |
   | Hurry (3.4) | 3.13 | 3.40 | 3.56 | 3.40 |

   The configured speeds now hold everywhere, so at 60 fps walking is about 24 %
   faster than it was. Chases and stealth were played at the old pace: if they
   now feel too easy, lower `walkSpeed` in `PlayerConfig.ts` (1.3 matches the
   old 60 fps pace) rather than bringing the bug back.
2. **TAA flipped on and off.** Babylon counts the camera as moved when its
   position or rotation differs *at all* from the last frame, and TAA only blends
   its history on frames where it hasn't moved. The eye-height, crouch, head-bob
   and field-of-view smoothing only ever approached their targets, and the
   capsule settles by fractions of a millimetre. So TAA alternated between its
   smooth image and the raw sub-pixel-jittered frame, and every edge shimmered.
   The camera now holds exactly still at rest (`src/player/cameraRest.ts`: a 4 mm
   dead band, and smoothing that lands exactly on its target).
3. **Dynamic resolution kept changing size.** Without GPU timing it probed one
   step up every few seconds; each change rebuilds every render target (a hitch,
   and TAA starts over). It now uses the GPU timer where the browser has one
   (Chromium), drops straight to the scale predicted to fit instead of step by
   step, only steps up when the step is predicted to fit, waits at least 0.6 s
   between changes, starts afresh after loading's shader compiles, and no longer
   reads the canvas size from the page layout every frame.

Frame pacing is now by elapsed time, so a 30 fps cap holds 30 fps even when a
frame overruns a refresh (counting callbacks would have dropped it to 20).

Regression tests: `tests/unit/playerMotion.test.ts` runs the real controller on
Havok in Node (stops where the player lets go; walks at a steady 1.6 m/s; zero
camera-moved frames at rest). All three fail with the old setting.

## Graphics settings

Title screen → Settings, and Pause → Settings (`src/ui/html/graphicsMenu.ts`,
saved in `localStorage` as `boon-sop.graphics`).

| Setting | Choices | Applies |
|---|---|---|
| Quality | Auto (device's pick), Low, Medium, High, Ultra | next load |
| Resolution | 100, 85, 75, 60, 50 % of the preset's render height | at once |
| Dynamic resolution | on / off | at once |
| Frame rate | Auto (30 on phones, 60 elsewhere), 30, 60, Unlimited | at once |
| Ambient occlusion, volumetric fog, TAA | on / off over the preset | next load |
| Head bob; camera shake (fear tremor, scare jolts) | on / off | at once |
| Show frame rate | on / off | at once |

In the pause menu, a note says when a change waits for the next load (from the
last checkpoint). `?quality=` (development builds) and `?fps=max` still work.

## Phones and tablets

- `DeviceProfile` now tells phones and tablets apart (`formFactor`) instead of
  blocking them. Without WebGPU they see the requirements page, which names
  the browsers that have it (Safari on iOS/iPadOS 26+, Chrome on Android).
- On Auto they start on Low with a lower render height (phones 720p, tablets
  900p), dynamic resolution down to 50 %, a 512 lamp shadow on phones, 30 fps on
  phones and no multisampled canvas.
- Touch controls (`src/ui/html/TouchControls.ts`): a stick under the left thumb
  (push past the rim to hurry), drag anywhere else to look, and buttons for Use,
  Lamp, Crouch (a toggle), Raise, Notebook, Satchel, Watch and Pause. Episode 2
  and 3 add Breath, Shutter, Throw, Refill and Row. With the sketchbook up, page
  buttons replace the action buttons. **Keys** (top left) opens every other key
  and both mouse buttons, above every panel. Buttons send the same keyboard and
  mouse events as a keyboard, holds included, so every system answers them
  unchanged. Touch has no pointer lock: touching the controls "engages" play,
  and any `document.exitPointerLock()` call disengages it.
- Starting a game on a phone or tablet asks for full screen and landscape
  (where the browser allows it); switching apps pauses. The title screen puts
  the logo beside the menu on short landscape screens.
- Settings → Touch controls: Auto (phones and tablets), On or Off.

Preview without WebGPU: `/tests/browser/touch.html` (phone emulation in the
browser's device toolbar, or a real phone on the local network).

## Not verified here

The cloud container that made these changes has no GPU (WebGPU device creation
fails even on SwiftShader), so nothing was rendered: the TAA, dynamic resolution
and phone frame rates still need a look on real hardware, in particular an iPhone
and an Android phone on Auto, and the reference M1 Pro at rest in the Act I village.
