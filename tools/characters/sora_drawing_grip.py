"""Reference-matched writing grasp: arched index, opposing thumb, middle support.
The two distal phalanges keep a controlled bend; unconstrained fingertip IK can
fold fingers backwards or leave them hanging under the shaft.
"""
import bpy
import math
from mathutils import Vector, Matrix

CONTACT = Vector((.025, .095, .028))
NIB_DIRECTION = Vector((.1, .65, .75)).normalized()


def drawing_grip(rig, ax, ay, az):
    wrist = rig.data.bones['wrist.L'].head_local
    origin = wrist + ay * .32
    scale = .108

    def local(v):
        d = v - origin
        return Vector((d.dot(ax) * scale, d.dot(ay) * scale, d.dot(az) * scale))

    def point(bone, direction):
        target = (ax * direction.x + ay * direction.y + az * direction.z).normalized()
        current = (bone.tail - bone.head).normalized()
        rotation = current.rotation_difference(target) @ bone.matrix.to_quaternion()
        bone.matrix = Matrix.LocRotScale(bone.head, rotation, bone.matrix.to_scale())
        bpy.context.view_layer.update()

    def arch(digit, target, bend, pole):
        bones = [rig.pose.bones[f'finger{digit}-{p}.L'] for p in range(1, 4)]
        base = local(bones[0].head)
        a, b, c = [(bone.tail-bone.head).length*scale for bone in bones]
        # Fix the DIP bend, then solve the MCP/PIP arch in its anatomical plane.
        distal = math.sqrt(b*b+c*c+2*b*c*math.cos(math.radians(bend)))
        delta = target-base
        distance = delta.length
        assert abs(a-distal) < distance < a+distal, (digit,distance,a+distal)
        direction = delta.normalized()
        outward = (pole-direction*pole.dot(direction)).normalized()
        along = (a*a-distal*distal+distance*distance)/(2*distance)
        pip = base+direction*along+outward*math.sqrt(max(0,a*a-along*along))
        normal = direction.cross(outward).normalized()
        second = (target-pip).normalized()
        offset = (b*b-c*c+distal*distal)/(2*distal)
        dip = pip+second*offset+normal.cross(second).normalized()*math.sqrt(max(0,b*b-offset*offset))
        for bone, end in zip(bones,[pip,dip,target]):
            point(bone,end-local(bone.head))
        return list(local(bones[-1].tail))

    tips = {}
    # Thumb pad opposes the index from the side; the longer index arches forwards.
    tips[1] = arch(1,CONTACT-NIB_DIRECTION*.024+Vector((.007,0,.001)),20,Vector((1,0,.35)))
    tips[2] = arch(2,CONTACT+Vector((-.003,.002,-.006)),22,Vector((0,1,-.45)))
    tips[3] = arch(3,CONTACT+Vector((-.007,-.002,.007)),38,Vector((0,1,-.35)))
    # Supporting fingers form a compact, staggered curl below the palm.
    for digit, inward, angles in [(4,.12,[60,125,165]),(5,.2,[62,120,158])]:
        for part,angle in enumerate(angles,1):
            radians=math.radians(angle)
            direction=Vector((inward,math.cos(radians),math.sin(radians)))
            point(rig.pose.bones[f'finger{digit}-{part}.L'],direction)
        tips[digit]=list(local(rig.pose.bones[f'finger{digit}-3.L'].tail))
    return tips
