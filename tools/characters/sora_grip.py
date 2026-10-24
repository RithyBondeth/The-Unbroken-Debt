"""Anatomical lamp grip authored in hand space, not a shared curl axis.
Align each phalanx separately so the fingers adduct and the thumb opposes them.
The open MakeHuman hand has splayed digits; flexion alone preserves that splay.
"""
import bpy
from mathutils import Vector, Matrix


def lamp_grip(rig, ax, ay, az):
    def point(digit, part, direction):
        bone = rig.pose.bones[f'finger{digit}-{part}.L']
        target = (ax*direction[0] + ay*direction[1] + az*direction[2]).normalized()
        bpy.context.view_layer.update()
        current = (bone.tail-bone.head).normalized()
        rotation = current.rotation_difference(target) @ bone.matrix.to_quaternion()
        bone.matrix = Matrix.LocRotScale(bone.head, rotation, bone.matrix.to_scale())
        bpy.context.view_layer.update()

    # MCPs come together; the PIP/DIP arc folds back toward the palm around
    # the thin bail wire. Shorter outer fingers have a softer, staggered curl.
    for digit, inward, lift in [(2,-.14,.18),(3,-.02,.15),(4,.10,.20),(5,.22,.29)]:
        point(digit,1,(inward,lift,.98))
        point(digit,2,(inward*.25,-.88,.48))
        point(digit,3,(0,-.76,-.65))
    # The thumb's saddle joint opposes; its own hinge axes differ from the
    # four fingers. The tip crosses the index/middle fingers instead of splaying.
    point(1,1,(.07,.78,.62))
    point(1,2,(-.78,.55,.30))
    point(1,3,(-.91,-.15,-.38))
