# Sora’s first-person hands

The camera hands use a continuous anatomical hand and forearm derived from the
CC0 MakeHuman core assets, shaped with young Asian female macro targets. The
mesh includes connected finger webs, thumb base, knuckles, nail beds and wrist.
A cropped photographic skin atlas is supplemented with anatomy-anchored pores,
fine furrows, knuckle folds, palm/wrist creases and subtle dorsal veins. Albedo,
tangent normal and linear roughness bakes supply the non-emissive PBR material.
Nails have a smoother finish, and the veins use restrained pigmentation and
shallow relief rather than dark painted lines. The editable detail material is
in `tools/characters/sora_skin.py`; it runs only during asset authoring.

The editable Blender source, portable GLB, exact source hashes, licence and
rebuild commands are in `art-source/characters/sora/README.md`. Normal game builds
use the checked-in runtime assets and do not need Blender or source downloads.
The reference image is visual direction only, not a distributed game texture.

## Runtime and animation

`FirstPersonHands.load()` loads the versioned mesh and textures before the world
registers light masks. `HandAsset.ts` validates the mesh header, counts, pose
order, buffer length and indices. `HandRig.ts` mirrors the left mesh for the right
hand, reversing triangle winding and normal X to preserve lighting.

The authoring rig uses the MakeHuman skeleton and skin weights. Six complete
poses are baked after subdivision: relaxed, lamp, phone, journal, pinch and
reach. Runtime GPU morph targets blend positions and normals with exponential
interpolation. Each hand has 33,104 UV-split vertices and 58,144 triangles; posing
does not rebuild geometry or create meshes per frame. Sleeves are separate
cloth surfaces fitted to the forearm. The hand-only fill has priority so nearby
world lights cannot displace it; night-sight excludes the held hands.

Connected presentations:

- The lamp and carrying hand start stowed while the wick is out. F brings them
  out during a successful lighting attempt; F again extinguishes and stows them.
  Missing matches or oil leave the lamp stowed. Visibility follows restored lamp
  state and also clears when oil runs out. An incense strike does not bring out
  an unlit lamp. The left hand follows the handle while carrying and raising it,
  with a lower carry position and angled wrist. Raising requires a burning wick.
- Ordinary lamp/incense strikes and the final ritual strike use the match pinch.
- Interactions use a reach, and oil refills use a tilt gesture.
- The arrival call replaces the wall receiver with a receiver held in the right
  hand. The phone rises into place and has a small breathing movement.
- Both hands support the sketchbook while the lamp is stowed. Closing it restores
  the lamp grip.
- Hiding, document overlays, the satchel and cutscenes stow the hands and lamp.
  The phone remains visible during its conversation.

Hands are presentation only. They do not own save flags, spend inventory or
complete puzzles. Existing lamp timing, inventory, ritual and checkpoint logic
remain responsible for gameplay. Bespoke writing and individual object-transfer
animations remain separate art work; reach and refill use generic gestures.

## Verification — 2026-10-24

`npm run check` passed: lint, typecheck, 242 tests across 43 files and production
build. Tests cover decoded geometry, GPU pose blending, stable mesh counts,
normal/winding alignment, camera transforms, visibility, strike completion and
phone transitions.

The isolated WebGPU/Havok fixture at
`/tests/browser/hands.html?start=act1` passed all presentation assertions: lamp
grip, F-key draw/lighting/stowing, failed lighting with no matches, strike match cost,
hiding, receiver replacement, phone
grip, journal support and restoration. Lowered/raised lamp, strike, phone and
journal captures were inspected in the actual night scene. No console errors
were reported. Existing scene asset-container/light-count and pointer-lock
warnings remain outside the hand asset.

Captures are `debug-shots/sora_hands_{lamp,lamp_raised,strike,phone,book}.png`.
`tools/characters/render-sora-hands.py` renders a neutral anatomical preview from
the saved Blender source; append `-- --detail` for the skin close-up in
`debug-shots/sora_hand_skin_detail.png`. The final skin-material pass passed the
browser fixture with no console errors, including restoration after closing the
journal. The fixture waits for the phone call's queued entries to finish before
closing the journal, and for rendered closure rather than a fixed wall-clock
delay, which could fail in a throttled background tab.
The scripted fixture does not certify free mouse
navigation or every cinematic pose.

The lamp pose was rebuilt around the handle crown after close-up review found
splayed fingers and an outward-pointing thumb. `sora_grip.py` aligns each
phalanx individually and opposes the thumb across the closed fingers. The hand
anchor is now centred over the bail wire. Runtime orientation subtracts the
lamp model's gauge-facing half turn, while preserving raising and swing. Tests
guard the closed grip's reduced span and this orientation correction; the
updated in-game lamp/phone/journal fixture passed with no console errors.
