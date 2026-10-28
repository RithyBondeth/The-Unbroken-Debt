"""Anatomical lamp grip authored in hand space, not a shared curl axis.
Align each phalanx separately so the fingers adduct and the thumb opposes them.
The open MakeHuman hand has splayed digits; flexion alone preserves that splay.
"""
import bpy
import math
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


def phone_grip(rig, ax, ay, az):
    """Fit each finger's three phalanges around the actual 26 mm receiver grip.
    Joint lengths stay anatomical; distinct arcs close the outer fingers and thumb.
    The receiver centreline in authored hand space is y=.060+.15*x, z=.020.
    """
    wrist=rig.data.bones['wrist.L'].head_local
    origin=wrist+ay*.32
    scale=.108
    def local(v):
        d=v-origin
        return Vector((d.dot(ax)*scale,d.dot(ay)*scale,d.dot(az)*scale))
    def point(digit, part, direction):
        bone=rig.pose.bones[f'finger{digit}-{part}.L']
        target=(ax*direction[0]+ay*direction[1]+az*direction[2]).normalized()
        bpy.context.view_layer.update()
        current=(bone.tail-bone.head).normalized()
        rotation=current.rotation_difference(target) @ bone.matrix.to_quaternion()
        bone.matrix=Matrix.LocRotScale(bone.head,rotation,bone.matrix.to_scale())
        bpy.context.view_layer.update()
    for digit in range(2,6):
        bones=[rig.pose.bones[f'finger{digit}-{p}.L'] for p in range(1,4)]
        base=local(bones[0].head)
        lengths=[(b.tail-b.head).length*scale for b in bones]
        cy=.060+.15*base.x
        cz=.020
        radius=.0235 if digit<5 else .021
        dy,dz=cy-base.y,cz-base.z
        distance=math.hypot(dy,dz)
        along=(lengths[0]**2-radius**2+distance**2)/(2*distance)
        height=math.sqrt(max(0,lengths[0]**2-along**2))
        # Distal intersection of the knuckle-reach and grip-clearance circles.
        py=base.y+dy*along/distance+dz*height/distance
        pz=base.z+dz*along/distance-dy*height/distance
        angle=math.atan2(pz-cz,py-cy)
        targets=[Vector((base.x*.96,py,pz))]
        for length in lengths[1:]:
            angle+=2*math.asin(min(.99,length/(2*radius)))
            targets.append(Vector((base.x*.94,cy+radius*math.cos(angle),cz+radius*math.sin(angle))))
        for part,target in enumerate(targets,1):
            direction=target-local(bones[part-1].head)
            point(digit,part,direction)
    # The thumb pad lies lengthwise against the receiver's neck, above the
    # curled index finger. It must not fold underneath the fist like a hook.
    point(1,1,(.50,.70,.50))
    point(1,2,(.20,.93,.30))
    point(1,3,(.95,.15,-.10))
