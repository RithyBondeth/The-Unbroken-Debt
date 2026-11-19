"""Episode 1's funeral moves from the tent in the yard into the house's central hall
(the user, Nov 19, 2026: "I want the whole funeral, cuffin, etc inside the house with
incense, candle, offering things along with the smoke with scary environment", then:
"adjust it or remove unnecessary thing make the house feel scary and pressure").

What moves, as one piece: the coffin on its dais, the portrait altar facing the front
door (candles, incense pot, offerings, the folded-leaf baysei), the four incense corners
the vigil tends, the main burner, the step candles and lotus buds, the coffin lamp, the
four hanging lanterns, the betel set, the mourners' tea things, petals and rice, and
every game marker that belonged to the tent (incense corners, burner, flames, flies,
oil, the family's places). It is set down on the hall floor (FLOOR, 2.5 m), the altar a
few steps in from the front door, and pulled in to fit a 6 m room: the dais narrower,
the corner burners and lanterns closer, everything 0.25 m west of centre so the Act 2
walker's way down the east side stays open (src/episodes/ep1/data/walker.ts).

What goes: the tent itself (posts, roof, drapes, valances, floor, lashings), the white
canopy over the portrait, the standing wreaths, the flower urns, the streamers, the
monks' seat and cushions, the tent's mats, the banners, the umbrella and the drums: a
small dark room crowded with only what the dead man needs.

The white cotton thread (sai sin) that ran round the tent now runs round the dais, tied
from burner to burner. Mourners' sandals wait at the foot of the front stairs.

Blender axes: X east, Y north, Z up. The game reads Babylon x = -x, z = -y; its side of
the move is src/episodes/ep1/data/funeral.ts (FUNERAL_SHIFT).
"""
import math
import re

import bmesh
import bpy
from mathutils import Matrix, Vector

FLOOR = 2.5
SHIFT = Vector((-0.25, 10.0, FLOOR))
DAIS_SQUEEZE = 0.85                 # the dais's width across the hall
CORNER_IN = 0.35                    # the corner burners towards the coffin
LANTERN_IN = 0.8                    # the hanging lanterns in from the tent's posts
TENT = (-5.5, 5.5, -0.5, 8.8)       # the tent's ground, x0 x1 y0 y1

MOVE = re.compile(
    r"^(coffin_|dais_|altar_|portrait_|incense_burner|interact_incense|main_burner|marker_main_burner|"
    r"light_flame_(altar|coffin|tent)|lantern_(cord|flame)|funeral_prop_0[0-46-9]_|step_candle|step_lotus|"
    r"baysei_|betel_(box|pot|tray)|candle_stub|folded_cloth|tea_|teapot|scattered_|bangskol|"
    r"marker_(vuthy|yay_mey|flies_tent)|interact_(oil_tent|portrait)|oil_tent|"
    r"col_(altar_table|coffin|dais|incense_burner|main_burner))")
GONE = re.compile(
    r"^((col_)?tent_|funeral_canopy|funeral_wreath|funeral_basket|funeral_prop_(05|10)_|streamer|monk_|"
    r"col_monk_seat|(col_)?banner|umbrella|(col_)?skor|marker_eave_[01]_)")
SANDALS = re.compile(r"^sandal")


def centre(o):
    if o.type == "MESH" and o.data.vertices:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        return sum(bb, Vector()) / 8
    return o.matrix_world.translation.copy()


def in_tent(c):
    return TENT[0] < c.x < TENT[1] and TENT[2] < c.y < TENT[3] and c.z < 6


def indoors():
    """Has the funeral already been moved?"""
    body = bpy.data.objects.get("coffin_body")
    return body is not None and centre(body).y > 11


def thread_round_dais(coll, corners, z):
    """The sai sin: one cotton thread tied round the four corner burners' necks, sagging
    between them, a loose end hanging from the last knot."""
    old = bpy.data.objects.get("thread_mesh")
    parent = old.parent if old else bpy.data.objects.get("interact_thread")
    material = old.data.materials[0] if old and old.data.materials else None
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    pts = []
    loop = corners + corners[:1]
    for a, b in zip(loop, loop[1:]):
        for i in range(12):
            t = i / 12
            p = a.lerp(b, t)
            p.z = z - 0.07 * math.sin(math.pi * t)
            pts.append(p)
    end = loop[-1]
    for i in range(1, 6):
        pts.append(end + Vector((0.02 * i, -0.01 * i, -0.09 * i)))
    bm = bmesh.new()
    r, sides = 0.0018, 4
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = d.cross(Vector((0, 0, 1))).normalized() if abs(d.z) < 0.9 else Vector((1, 0, 0))
        bn = d.cross(n)
        rings.append([bm.verts.new(p + (n * math.cos(a) + bn * math.sin(a)) * r)
                      for a in (k * math.tau / sides for k in range(sides))])
    for ra, rb in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k]))
    me = bpy.data.meshes.new("thread_mesh")
    bm.to_mesh(me)
    bm.free()
    if material:
        me.materials.append(material)
    obj = bpy.data.objects.new("thread_mesh", me)
    coll.objects.link(obj)
    if parent:
        parent.location = corners[0] + Vector((0, 0, z - corners[0].z))
        bpy.context.view_layer.update()
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_world = world
    return obj


def move_indoors():
    """Moves the funeral into the hall. Returns counts for the log, or None if done before."""
    if indoors():
        return None
    roots = [o for o in bpy.data.objects if o.parent is None and o.users_collection
             and o.users_collection[0].name not in ("_protos", "nature_templates")]
    gone, moved, sandals = [], [], []
    for o in roots:
        c = centre(o)
        if not in_tent(c):
            continue
        if GONE.match(o.name):
            gone.append(o.name)
        elif MOVE.match(o.name):
            moved.append(o)
        elif SANDALS.match(o.name):
            sandals.append(o)
    for name in gone:
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        for child in list(o.children_recursive):
            bpy.data.objects.remove(child, do_unlink=True)
        bpy.data.objects.remove(o, do_unlink=True)
    for o in moved:
        o.location += SHIFT
    for o in sandals:                           # left at the foot of the front stairs
        o.location.y += 7.4
    bpy.context.view_layer.update()
    axis_x = SHIFT.x                            # the coffin's long axis, after the move
    corners = []
    for o in moved:
        c = centre(o)
        if re.match(r"^(dais_|col_dais)", o.name):
            # Squeeze about the coffin's axis: scale the object's world matrix in x.
            m = (Matrix.Translation((axis_x, 0, 0)) @ Matrix.Diagonal((DAIS_SQUEEZE, 1, 1, 1))
                 @ Matrix.Translation((-axis_x, 0, 0)))
            o.matrix_world = m @ o.matrix_world
        elif re.match(r"^(incense_burner|interact_incense|col_incense_burner)", o.name):
            o.location.x -= math.copysign(CORNER_IN, c.x - axis_x)
        elif re.match(r"^(funeral_prop_0[0-3]_|lantern_(cord|flame)|light_flame_tent)", o.name):
            o.location.x -= math.copysign(LANTERN_IN, c.x - axis_x)
        elif o.name == "interact_oil_tent":     # off the east wall, on the floor beside it
            o.location.x -= 0.45
    bpy.context.view_layer.update()
    for i in range(4):
        e = bpy.data.objects.get(f"interact_incense_{i}")
        if e:
            corners.append(e.matrix_world.translation.copy())
    if len(corners) == 4:
        mid = sum(corners, Vector()) / 4
        corners.sort(key=lambda p: math.atan2(p.y - mid.y, p.x - mid.x))
        thread_round_dais(bpy.data.collections["ep1_area_village"], corners, FLOOR + 0.92)
    # The lanterns hang lower in a room than under a tent's ridge, and dimmer: the hall
    # is lit by its candles, its lanterns a dull glow under the ceiling.
    for o in bpy.data.objects:
        if o.name.startswith("light_flame_tent_"):
            o["intensity"] = 1.4
            o["radius"] = 4.5
    return {"moved": len(moved), "removed": len(gone), "sandals": len(sandals), "thread corners": len(corners)}
