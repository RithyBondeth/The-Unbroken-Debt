# Studio: Sora draws on the first E press

The illustration interaction now performs a 3.6-second drawing action. Sora's
anatomical right hand uses its dedicated authored tripod pose, attached to a split-nib dip
pen in the illustration's coordinate space. The pen approaches, follows four
pressure-varied roof/cornice strokes, lifts between marks, and withdraws.
The scratch sound follows the same stroke timing. Movement and look are held
for the action; the prior view and input gates are restored afterward.

The paper uses the existing authored illustration at full resolution on a thin
curved sheet with a subtle cotton normal texture. Transparent ink overlays are
excluded from the desk lamp's shadow casters to avoid rectangular shadows.
Checkpoint restoration paints the completed ink immediately without replaying
the hand animation.

## Verification

Open `/tests/browser/studio.html?drawing`, click to begin, aim at the illustration
and press E. This query keeps the first interaction available; the ordinary
studio review still auto-completes it. The Drawing table view and slower Preview
drawing button permit close visual inspection. Save screenshot captures only
the rendered game, without review overlays. The review uses isolated saves.

Targeted tests cover the drawing grip during cutscenes, hand ownership and lamp
restoration, input/view restoration on completion and failure, and prologue
sound synthesis. Browser verification checked actual E input, visible hand/pen
motion, completion of the illustration flag, and return to normal interaction.

The drawing pose is the seventh hand morph. `tools/characters/sora_drawing_grip.py`
fits the thumb, index and middle finger to separate pad contacts around the shaft;
the ring/little fingers curl toward the palm. The pencil axis and contact are
aligned geometrically in `FirstPersonHands.holdDrawing`. Rebuild only this morph
with Blender and `tools/characters/update-sora-drawing.py`; it preserves the six
existing runtime poses and textures. The full hand builder includes the same pose.

The supplied writing-hand references guide the revised pose: the index arches
forward, the thumb opposes the barrel, and the middle finger supports it.
Controlled distal-joint bends replace unconstrained fingertip IK. A shared
paper-space frame keeps the palm down and cancels the imported studio's mirror
for the drawing hand. The camera radius is 0.29 m for a tighter view. Short,
raised repositioning arcs connect strokes, with eased speed and small wrist
pivots. The pen shares the hand's depth pass to avoid detached oversized shadows.

The close view now targets the roof stroke area, offset from the plate centre,
so the pencil's top remains inside the frame. The existing hand-only fill light
eases from 0.32 to 0.85 intensity during drawing and returns afterward, keeping
finger contact and knuckle detail visible under the studio's nighttime lighting.
