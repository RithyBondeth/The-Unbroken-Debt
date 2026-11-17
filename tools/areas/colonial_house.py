"""Episode 1's family house rebuilt as a well-off colonial-era teak house gone to
ruin (1932): square teak posts on lime-plastered brick plinths, painted lapped
weatherboards outside and pale distempered tongue-and-groove inside, louvred
shutters over iron-barred windows, sunburst fanlights over every door and window,
panelled doors, a turned-baluster veranda with carved brackets, and a steep roof of
real Marseille tiles with half-round ridge tiles and carved bargeboards.

The room plan, every opening, every collider, the eave drip points and the two
doors the game opens (interact_door_sok, interact_door_yaymey) keep the size and
place they had, so the acts play exactly as before. The room-side face of every
wall stays where it was, so what hangs on the walls stays flush with them.

Built into the village by tools/areas/rebuild-house-colonial.py.
Blender axes: X east, Y north, Z up; metres. Run inside Blender.
"""
import json
import math
import os

import bpy
import numpy as np

from kit import ROOT, box, collider, image_material, lathe, mesh_object, tube
from khmer import join
from colonial_parts import (_marseille_mesh, _uv_box, fretwork, hang, louvred_leaf, panelled_door, plinth_post,
                            tiled_slope, tongue_groove, valance, wall_print, weatherboards, window_bars)
from cobwebs import corner_cobweb, web_materials, _sheet, _thread

FLOOR = 2.5
WALL_H = 2.6
ZW = FLOOR + WALL_H
H = {"x0": -6.0, "x1": 6.0, "y0": 10.0, "y1": 22.0}
T = 0.06
FRONT = 11.5
DOOR = FLOOR + 2.05
SILL, HEAD = FLOOR + 0.8, FLOOR + 1.75
VENT_W = HEAD + 0.08, HEAD + 0.45  # fanlight over a window
VENT_D = DOOR + 0.08, DOOR + 0.43  # fanlight over a door
PITCH = math.radians(42)
OVER, GX = 0.9, 0.9  # eave and gable overhangs (the eave drip markers sit on them)
YM = (H["y0"] + H["y1"]) / 2
ZP = ZW + 0.05
RIDGE = ZP + 0.12 + (YM - H["y0"]) * math.tan(PITCH)
YE_S, YE_N = H["y0"] - OVER, H["y1"] + OVER
ZE = ZP + 0.12 - OVER * math.tan(PITCH)

# (name, along_x, slab low, slab high, a0, a1, door gaps [(a, b)], window gaps [(a, b)], outside sign or 0)
WALLS = [
    ("wall_front", True, FRONT - T, FRONT, H["x0"], H["x1"], [(-0.5, 0.5)], [(-4.6, -3.8), (3.9, 4.7)], -1),
    ("wall_back", True, H["y1"] - T, H["y1"], H["x0"], H["x1"], [(1.9, 2.8)], [(-4.8, -4.0), (-1.0, -0.2), (4.0, 4.8)], 1),
    ("wall_west", False, H["x0"], H["x0"] + T, FRONT, H["y1"], [], [(12.6, 13.4), (16.0, 16.8), (20.0, 20.8)], -1),
    ("wall_east", False, H["x1"] - T, H["x1"], FRONT, H["y1"], [], [(14.0, 14.8), (16.7, 17.5), (19.6, 20.4)], 1),
    ("wall_kitchen_hall", False, -3.0, -3.0 + T, FRONT, 14.5, [(12.5, 13.4)], [], 0),
    ("wall_yaymey_hall", False, -3.0, -3.0 + T, 14.5, H["y1"], [(15.6, 16.5)], [], 0),
    ("wall_kitchen_yaymey", True, 14.5 - T / 2, 14.5 + T / 2, H["x0"], -3.0, [], [], 0),
    ("wall_sok_hall", False, 3.0 - T, 3.0, FRONT, 18.0, [(13.0, 13.9)], [], 0),
    ("wall_vuthy_hall", False, 3.0 - T, 3.0, 18.0, H["y1"], [(19.0, 19.9)], [], 0),
    ("wall_sok_vuthy", True, 18.0 - T / 2, 18.0 + T / 2, 3.0, H["x1"], [], [], 0),
]
# Windows: (name, wall, a, b, swing in radians: 0 shut).
WINDOWS = [
    ("win_kitchen_s", "wall_front", -4.6, -3.8, 1.2), ("win_sok_s", "wall_front", 3.9, 4.7, 0.0),
    ("win_yaymey_n", "wall_back", -4.8, -4.0, 0.3), ("win_hall_n", "wall_back", -1.0, -0.2, 1.0),
    ("win_vuthy_n", "wall_back", 4.0, 4.8, 0.5),
    ("win_kitchen_w", "wall_west", 12.6, 13.4, 1.3), ("win_yaymey_w", "wall_west", 16.0, 16.8, 0.0),
    ("win_yaymey_w2", "wall_west", 20.0, 20.8, 0.0),
    ("win_sok_e", "wall_east", 14.0, 14.8, 0.0), ("win_sok_e2", "wall_east", 16.7, 17.5, 0.15),
    ("win_vuthy_e", "wall_east", 19.6, 20.4, 0.0),
]
DOORS = [
    ("front", "wall_front", -0.5, 0.5), ("back", "wall_back", 1.9, 2.8), ("kitchen", "wall_kitchen_hall", 12.5, 13.4),
    ("yaymey", "wall_yaymey_hall", 15.6, 16.5), ("sok", "wall_sok_hall", 13.0, 13.9), ("vuthy", "wall_vuthy_hall", 19.0, 19.9),
]
POSTS = [(x, y) for x in (-6.0, -3.0, 0.0, 3.0, 6.0) for y in (10.0, 14.0, 18.0, 22.0)]


def _wall(name):
    return next(w for w in WALLS if w[0] == name)


def _at(along_x, fixed, a, z):
    return (a, fixed, z) if along_x else (fixed, a, z)


def _box_on(name, coll, along_x, f0, f1, a0, a1, z0, z1, mat, **kw):
    """A box given along-wall (a) and across-wall (f) ranges."""
    if along_x:
        return box(name, coll, a0, a1, min(f0, f1), max(f0, f1), z0, z1, mat, **kw)
    return box(name, coll, min(f0, f1), max(f0, f1), a0, a1, z0, z1, mat, **kw)


def _leaf_outward(rotation, out_axis_x, out):
    """+1 when a louvred leaf turned `rotation` shows its outer (-Y) face outdoors."""
    dx, dy = math.sin(rotation), -math.cos(rotation)
    d = dx if out_axis_x else dy
    return 1 if d * out > 0 else -1


def walls(coll, m):
    """Linings, weatherboards, sill beams, plates and colliders for every wall."""
    for name, along_x, lo, hi, a0, a1, doors, windows, out in WALLS:
        vis = [(a, b, VENT_D[1], FLOOR) for a, b in doors] + [(a, b, VENT_W[1], SILL) for a, b in windows]
        # Colliders as before: doorways and window openings up to their heads.
        pieces, at = [], a0
        for (g0, g1, top, sill) in sorted([(a, b, DOOR, FLOOR) for a, b in doors] + [(a, b, HEAD, SILL) for a, b in windows]):
            pieces += [(at, g0, FLOOR, ZW), (g0, g1, top, ZW), (g0, g1, FLOOR, sill)]
            at = g1
        pieces.append((at, a1, FLOOR, ZW))
        for k, (p0, p1, z0, z1) in enumerate(pieces):
            if p1 - p0 > 1e-3 and z1 - z0 > 1e-3:
                if along_x:
                    collider(f"{name}_{k}", coll, p0, p1, lo, hi, z0, z1)
                else:
                    collider(f"{name}_{k}", coll, lo, hi, p0, p1, z0, z1)
        if out == 0:
            # A partition: lined on both faces, inside its own thickness.
            tongue_groove(f"{name}_lining_lo", coll, along_x, lo, a0, a1, FLOOR, ZW, 1, m["cl_room_boards"], openings=vis)
            tongue_groove(f"{name}_lining_hi", coll, along_x, hi, a0, a1, FLOOR, ZW, -1, m["cl_room_boards"], openings=vis)
            continue
        outer, inner = (lo, hi) if out < 0 else (hi, lo)
        tongue_groove(f"{name}_lining", coll, along_x, inner - (-out) * 0.0 + out * 0.015, a0, a1, FLOOR, ZW, -out,
                      m["cl_room_boards"], openings=vis)
        # Outside: lapped boards over the whole face, the wall ends included.
        e0, e1 = (a0 - (0.04 if along_x else 0.06), a1 + (0.04 if along_x else 0.0)) if along_x else (FRONT - T - 0.03, a1 + 0.03)
        weatherboards(f"{name}_boards", coll, along_x, outer, e0, e1, FLOOR + 0.12, ZW, out, m["cl_weatherboard"], openings=vis)
        # The sill beam the boards start from; at a doorway it drops to a threshold.
        at = e0
        for k, (a, b) in enumerate(sorted(doors) + [(e1, e1)]):
            if a - at > 0.01:
                _box_on(f"{name}_sill_beam_{k}", coll, along_x, outer + out * 0.05, inner, at, a, FLOOR - 0.06, FLOOR + 0.12,
                        m["cl_trim"], edge=0.006)
            if b > a:
                _box_on(f"{name}_threshold_{k}", coll, along_x, outer + out * 0.05, inner, a, b, FLOOR - 0.06, FLOOR + 0.008,
                        m["cl_trim"], edge=0.004)
            at = b
        # Corner boards where two outside walls meet.
        if not along_x:
            for y in (FRONT - T, H["y1"]):
                sx = outer
                box(f"{name}_corner_{y:.0f}", coll, min(sx, sx + out * 0.05), max(sx, sx + out * 0.05),
                    y - 0.05 if y > 12 else y - 0.045, y + 0.05 if y > 12 else y + 0.005, FLOOR - 0.06, ZW, m["cl_shutter"])
    # Skirting and cornice along every room face, broken at the doorways.
    for name, along_x, lo, hi, a0, a1, doors, windows, out in WALLS:
        faces = [(lo, -1), (hi, 1)] if out == 0 else [((hi, 1) if out < 0 else (lo, -1))]
        for face, into in faces:
            spans, at = [], a0 + 0.02
            for a, b in sorted(doors):
                spans.append((at, a - 0.07))
                at = b + 0.07
            spans.append((at, a1 - 0.02))
            for k, (s0, s1) in enumerate(spans):
                if s1 - s0 > 0.05:
                    _box_on(f"{name}_skirting_{face:.2f}_{k}", coll, along_x, face, face + into * 0.02, s0, s1, FLOOR,
                            FLOOR + 0.16, m["cl_trim"], edge=0.004)
            _box_on(f"{name}_cornice_{face:.2f}", coll, along_x, face, face + into * 0.045, a0 + 0.02, a1 - 0.02, ZW - 0.07,
                    ZW - 0.02, m["cl_trim"], edge=0.004)


def ceiling(coll, m):
    """Tongue-and-groove ceilings over the rooms, the boards running east-west."""
    c = box("house_ceiling", coll, H["x0"] + T, H["x1"] - T, FRONT, H["y1"] - T, ZW - 0.02, ZW, m["cl_ceiling"])
    c.data.uv_layers.remove(c.data.uv_layers[0])
    _uv_box(c, m["cl_ceiling"], 2.0, 0, 1)
    # The joists the ceiling hangs from, seen at its edges above the cornice: none; the
    # plate and tie beams carry it.
    return c


def posts(coll, m):
    """Square teak posts on plastered brick plinths, with the old colliders' names."""
    made = []
    for x, y in POSTS:
        top = FLOOR if (x, y) in ((0.0, 14.0), (0.0, 18.0)) else ZW
        post, pl, cap = plinth_post(f"pillar_{x:.0f}_{y:.0f}", coll, x, y, top, m["cl_trim"], m["cl_plinth"],
                                    size=0.24, plinth=0.46, plinth_h=0.42)
        collider(f"pillar_{x:.0f}_{y:.0f}", coll, x - 0.2, x + 0.2, y - 0.2, y + 0.2, 0, top)
        made.append((x, y, top))
    # Tie beams over the side walls, plates over the veranda posts and the back wall.
    for x in (H["x0"], H["x1"]):
        box(f"tie_beam_{x:.0f}", coll, x - 0.1, x + 0.1, H["y0"] - 0.12, H["y1"] + 0.12, ZW, ZW + 0.2, m["cl_trim"], edge=0.008)
    for y in (H["y0"], H["y1"]):
        box(f"roof_plate_{y:.0f}", coll, H["x0"] - 0.3, H["x1"] + 0.3, y - 0.12, y + 0.12, ZW, ZW + 0.2, m["cl_trim"], edge=0.008)
    return made


def window_unit(coll, m, name, wall_name, a, b, swing):
    """Frame, sills, iron bars, fanlight, louvred shutters and inside casing."""
    _, along_x, lo, hi, *_rest, out = _wall(wall_name)
    outer, inner = (lo, hi) if out < 0 else (hi, lo)
    mid = (lo + hi) / 2
    f_out, f_in = outer + out * 0.035, inner - out * 0.02
    for k, (p0, p1) in enumerate(((a - 0.06, a), (b, b + 0.06))):
        _box_on(f"{name}_jamb_{k}", coll, along_x, f_out, f_in, p0, p1, SILL - 0.02, VENT_W[1] + 0.06, m["cl_shutter"])
    _box_on(f"{name}_head", coll, along_x, f_out, f_in, a - 0.06, b + 0.06, HEAD, VENT_W[0], m["cl_shutter"])
    _box_on(f"{name}_vent_head", coll, along_x, f_out - out * 0.0, f_in, a - 0.1, b + 0.1, VENT_W[1], VENT_W[1] + 0.07,
            m["cl_shutter"], edge=0.004)
    _box_on(f"{name}_sill", coll, along_x, outer + out * 0.11, inner - out * 0.05, a - 0.11, b + 0.11, SILL - 0.06, SILL,
            m["cl_trim"], edge=0.006)
    window_bars(f"{name}_bars", coll, along_x, mid, a, b, SILL, HEAD, m["iron"])
    fretwork(f"{name}_fanlight", coll, along_x, mid, a, b, VENT_W[0], VENT_W[1], m["cl_shutter"], depth=0.03)
    # Inside casing round the opening.
    for k, (p0, p1) in enumerate(((a - 0.13, a - 0.06), (b + 0.06, b + 0.13))):
        _box_on(f"{name}_casing_{k}", coll, along_x, inner, inner - out * 0.018, p0, p1, SILL - 0.05, VENT_W[1] + 0.13,
                m["cl_trim"], edge=0.003)
    # Shutters hung outside the frame.
    w = (b - a) / 2 + 0.06
    fixed = outer + out * 0.06
    for k, (hinge_a, closed) in enumerate(((a - 0.06, 0.0 if along_x else math.pi / 2),
                                            (b + 0.06, math.pi if along_x else -math.pi / 2))):
        if along_x:
            rot = closed - out * swing if k == 1 else closed + out * swing
        else:
            rot = closed - out * swing if k == 0 else closed + out * swing
        leaf = louvred_leaf(f"{name}_shutter_{k}", coll, w, HEAD - SILL - 0.01, m["cl_shutter"], m["iron"],
                            outward=_leaf_outward(closed, not along_x, out))
        hinge = _at(along_x, fixed, hinge_a, SILL + 0.005)
        hang(leaf, hinge, rot)
        # A rusted hinge pin into the jamb, so the leaf hangs on something.
        for z in (SILL + 0.12, HEAD - 0.14):
            p = _at(along_x, fixed - out * 0.02, hinge_a, z)
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.008, depth=0.07, location=p,
                                                rotation=(math.pi / 2, 0, 0) if along_x else (0, math.pi / 2, 0))
            pin = bpy.context.active_object
            pin.name = f"{name}_pin"
            for c_ in pin.users_collection:
                c_.objects.unlink(pin)
            coll.objects.link(pin)
            pin.data.materials.append(m["iron"])


def door_unit(coll, m, name, wall_name, a, b):
    """Jambs, head, fanlight, architraves on both faces."""
    _, along_x, lo, hi, *_rest, out = _wall(wall_name)
    mid = (lo + hi) / 2
    f0, f1 = (lo - 0.035, hi + 0.035)
    for k, (p0, p1) in enumerate(((a - 0.07, a), (b, b + 0.07))):
        _box_on(f"door_frame_{name}_{k}", coll, along_x, f0, f1, p0, p1, FLOOR, VENT_D[1] + 0.06, m["cl_trim"])
    _box_on(f"door_head_{name}", coll, along_x, f0, f1, a - 0.07, b + 0.07, DOOR, VENT_D[0], m["cl_trim"])
    _box_on(f"door_vent_head_{name}", coll, along_x, f0, f1, a - 0.12, b + 0.12, VENT_D[1], VENT_D[1] + 0.07, m["cl_trim"],
            edge=0.004)
    fretwork(f"door_fanlight_{name}", coll, along_x, mid, a, b, VENT_D[0], VENT_D[1], m["cl_shutter"], depth=0.03)
    for face, into in ((lo, -1), (hi, 1)):
        base = face + into * 0.032 if out == into else face
        for k, (p0, p1) in enumerate(((a - 0.15, a - 0.07), (b + 0.07, b + 0.15))):
            _box_on(f"door_casing_{name}_{face:.2f}_{k}", coll, along_x, base, base + into * 0.02, p0, p1, FLOOR,
                    VENT_D[1] + 0.15, m["cl_trim"], edge=0.003)


def doors(coll, m, interact_props):
    for name, wall_name, a, b in DOORS:
        door_unit(coll, m, name, wall_name, a, b)
    leaf_h = DOOR - FLOOR - 0.015
    # The front doors stand open into the hall, as do the back door and Vuthy's.
    for nm, hinge, ang, w in (("door_front_leaf_l", (-0.5, FRONT - 0.02), math.radians(100), 0.49),
                              ("door_front_leaf_r", (0.5, FRONT - 0.02), math.radians(80), 0.49)):
        leaf = panelled_door(nm, coll, w, leaf_h, m["cl_shutter"], m["iron"])
        hang(leaf, (*hinge, FLOOR + 0.008), ang)
    leaf = panelled_door("door_back_leaf", coll, 0.88, leaf_h, m["cl_shutter"], m["iron"])
    hang(leaf, (2.8, H["y1"] - 0.04, FLOOR + 0.008), math.radians(-120))
    leaf = panelled_door("door_vuthy_leaf", coll, 0.88, leaf_h, m["cl_shutter"], m["iron"])
    hang(leaf, (3.0, 19.9, FLOOR + 0.008), math.radians(-90 + 65))
    # The two doors the game opens or knocks on: shut, one mesh each, same place and size.
    for nm, (x0, x1, y0, y1) in (("interact_door_yaymey", (-3.04, -2.98, 15.6, 16.5)),
                                 ("interact_door_sok", (2.96, 3.02, 13.0, 13.9))):
        leaf = panelled_door(nm + "_leaf", coll, y1 - y0, DOOR - FLOOR, m["cl_shutter"])
        hang(leaf, ((x0 + x1) / 2, y0, FLOOR), math.pi / 2)
        bpy.context.view_layer.update()
        leaf.data.transform(leaf.matrix_world)
        leaf.matrix_world.identity()
        straps = []
        for k, z in enumerate((FLOOR + 0.25, DOOR - 0.3)):
            straps.append(box(f"{nm}_strap_{k}", coll, x0 - 0.004, x1 + 0.004, y0 - 0.01, y0 + 0.3, z - 0.02, z + 0.02, m["iron"]))
        door = join([leaf] + straps, nm)
        for key, value in interact_props.get(nm, {}).items():
            door[key] = value


def veranda(coll, m):
    """Balusters between the front posts, carved brackets, a valance frieze."""
    rz0, rz1 = FLOOR + 0.1, FLOOR + 0.92
    profile = [(0.022, 0.0), (0.022, 0.06), (0.016, 0.08), (0.026, 0.2), (0.014, 0.33), (0.02, 0.38), (0.026, 0.45),
               (0.02, 0.52), (0.014, 0.58), (0.024, 0.7), (0.016, 0.76), (0.022, 0.78), (0.022, rz1 - rz0)]
    proto = lathe("baluster_proto", coll, profile, 0, 0, 0, m["cl_trim"], segments=10)
    bal = []
    for k in range(4):
        a, b = H["x0"] + 3 * k, H["x0"] + 3 * (k + 1)
        n = int((b - a - 0.24) / 0.13)
        for j in range(n):
            x = a + 0.12 + (j + 0.5) * (b - a - 0.24) / n
            o = proto.copy()
            o.location = (x, H["y0"], rz0)
            coll.objects.link(o)
            bal.append(o)
    for j in range(int((FRONT - T - H["y0"] - 0.24) / 0.13)):
        o = proto.copy()
        o.location = (H["x0"], H["y0"] + 0.12 + (j + 0.5) * 0.13, rz0)
        coll.objects.link(o)
        bal.append(o)
    bpy.data.objects.remove(proto)
    join(bal, "veranda_balusters")
    box("rail_top", coll, H["x0"], H["x1"], H["y0"] - 0.07, H["y0"] + 0.07, rz1, rz1 + 0.06, m["cl_trim"], edge=0.012)
    box("rail_bottom", coll, H["x0"], H["x1"], H["y0"] - 0.05, H["y0"] + 0.05, rz0 - 0.07, rz0, m["cl_trim"], edge=0.006)
    box("rail_west_top", coll, H["x0"] - 0.07, H["x0"] + 0.07, H["y0"], FRONT - T, rz1, rz1 + 0.06, m["cl_trim"], edge=0.012)
    box("rail_west_bottom", coll, H["x0"] - 0.05, H["x0"] + 0.05, H["y0"], FRONT - T, rz0 - 0.07, rz0, m["cl_trim"])
    collider("veranda_rail", coll, H["x0"], H["x1"], 9.95, 10.1, FLOOR, FLOOR + 0.98)
    collider("veranda_rail_w", coll, H["x0"] - 0.08, H["x0"] + 0.08, 10.0, 11.5, FLOOR, FLOOR + 0.98)
    # Carved brackets: a curved knee from each post to the plate, both sides of the post.
    pts = [(0, 0)] + [(0.42 - 0.42 * math.cos(t), -0.42 + 0.42 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 9)][::-1] + [(0, -0.42)]
    pts = [(0.0, 0.0), (0.42, 0.0)] + [(0.42 - 0.36 * math.sin(t), -0.36 * (1 - math.cos(t)) - 0.06 * math.sin(t))
                                        for t in np.linspace(0.15, math.pi / 2, 8)] + [(0.0, -0.42)]
    for x in (-6.0, -3.0, 0.0, 3.0, 6.0):
        for side in (-1, 1):
            if (x == -6.0 and side < 0) or (x == 6.0 and side > 0):
                continue
            verts = []
            for d in (-0.025, 0.025):
                for (u, v) in pts:
                    verts.append((x + side * (0.12 + u), H["y0"] + d, ZW + v))
            n = len(pts)
            faces = [tuple(range(n))[::-1] if side > 0 else tuple(range(n)), tuple(range(n, 2 * n)) if side > 0 else tuple(range(n, 2 * n))[::-1]]
            for i in range(n):
                j = (i + 1) % n
                faces.append((i, j, n + j, n + i) if side > 0 else (j, i, n + i, n + j))
            br = mesh_object(f"veranda_bracket_{x:.0f}_{side}", coll, verts, faces, m["cl_trim"])
            _uv_box(br, m["cl_trim"], 1.0, 0, 2)
    for k in range(4):
        a = H["x0"] + 3 * k
        valance(f"veranda_frieze_{k}", coll, True, H["y0"] - 0.13, a + 0.12, a + 3 - 0.12, ZW, m["cl_shutter"], drop=0.2)


def _slope_frame(side, ye):
    """Unit vectors up the slope and out of it, and the eave point of the tile plane."""
    run_y = YM - ye
    length = math.hypot(run_y, RIDGE - ZE)
    up = np.array((0.0, run_y / length, (RIDGE - ZE) / length))
    n = np.array((0.0, -up[2], up[1]))
    if n[2] < 0:
        n = -n
    return up, n, np.array((0.0, ye, ZE)), length


def _solid_half_pipe(name, coll, x0, x1, centre_y, centre_z, radius, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=radius, depth=x1 - x0, end_fill_type="NOTHING",
                                        location=((x0 + x1) / 2, centre_y, centre_z), rotation=(0, math.pi / 2, 0))
    o = bpy.context.active_object
    o.name = name
    for c_ in o.users_collection:
        c_.objects.unlink(o)
    coll.objects.link(o)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    # Rotated 90 degrees about Y, local -X is world up... keep the upper half in world space.
    mw = o.matrix_world
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if (mw @ v.co).z < centre_z - 0.002], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    sol = o.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.016
    sol.offset = -1
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="solid")
    o.data.materials.append(mat)
    _uv_box(o, mat, 1.0, 0, 1)
    return o


def roof(coll, m, rng):
    """Rafters, battens, Marseille tiles, ridge tiles, fascias, valances, gables."""
    for side, ye in ((-1, YE_S), (1, YE_N)):
        up, n, e, length = _slope_frame(side, ye)
        tilt = -side * PITCH
        # Rafters every 0.6 m: their tops 5 cm under the tile plane, where the battens sit.
        rafters = []
        # They run 10 cm past the eave line into the fascia.
        mid = e + up * (length - 0.1) / 2 - n * (0.05 + 0.065)
        for k, x in enumerate(np.arange(H["x0"] - GX + 0.15, H["x1"] + GX, 0.6)):
            r = box(f"rafter_{side}_{k}", coll, x - 0.035, x + 0.035, -(length + 0.1) / 2, (length + 0.1) / 2, -0.065, 0.065,
                    m["cl_trim"])
            r.rotation_euler.x = tilt
            r.location = (x, mid[1], mid[2])
            rafters.append(r)
        join(rafters, f"rafters_{'s' if side < 0 else 'n'}")
        # Battens on the rafters, one under the head of each tile course.
        battens = []
        for k in range(int(length / 0.34) + 1):
            c = e + up * (0.4 + k * 0.34) - n * 0.025
            if np.dot(c - e, up) > length - 0.1:
                break
            bt = box(f"batten_{side}_{k}", coll, H["x0"] - GX, H["x1"] + GX, -0.025, 0.025, -0.025, 0.025, m["cl_trim"])
            bt.rotation_euler.x = tilt
            bt.location = (0.0, c[1], c[2])
            battens.append(bt)
        join(battens, f"roof_battens_{'s' if side < 0 else 'n'}")
        # Only the courses over the veranda (south) and the back eave (north) are seen from below.
        seen = int((FRONT - ye) / math.cos(PITCH) / 0.34) + 2 if side < 0 else int(OVER / math.cos(PITCH) / 0.34) + 2
        tiled_slope(f"roof_tiles_{'s' if side < 0 else 'n'}", coll, H["x0"] - GX, H["x1"] + GX, (ye, ZE), (YM, RIDGE),
                    m["cl_terracotta"], rng, missing=0.012, seen_below=seen)
        # Fascia on the rafter ends, its scalloped valance, and the first course's fillet.
        f0, f1 = sorted((ye - side * 0.0, ye + side * 0.04))
        box(f"fascia_{side}", coll, H["x0"] - GX, H["x1"] + GX, f0, f1, ZE - 0.22, ZE + 0.02, m["cl_shutter"])
        vy = f0 - 0.022 if side < 0 else f1
        valance(f"eave_valance_{side}", coll, True, vy, H["x0"] - GX, H["x1"] + GX, ZE - 0.2, m["cl_shutter"], drop=0.2)
    # Ridge: beam, mortar bed and overlapping half-round ridge tiles.
    box("ridge_beam", coll, H["x0"] - GX, H["x1"] + GX, YM - 0.08, YM + 0.08, RIDGE - 0.45, RIDGE - 0.12, m["cl_trim"])
    box("ridge_mortar", coll, H["x0"] - GX, H["x1"] + GX, YM - 0.13, YM + 0.13, RIDGE - 0.12, RIDGE + 0.01, m["cl_plinth"])
    caps = []
    x = H["x0"] - GX
    k = 0
    while x < H["x1"] + GX - 0.05:
        caps.append(_solid_half_pipe(f"ridge_tile_{k}", coll, x, min(x + 0.42, H["x1"] + GX), YM, RIDGE - 0.005,
                                     0.135 + 0.006 * (k % 2), m["cl_terracotta"]))
        x += 0.38
        k += 1
    join(caps, "ridge_tiles")
    # Gables: boards, a sunburst, a carved bargeboard each side, a finial.
    for x, out in ((H["x0"], -1), (H["x1"], 1)):
        zb = ZW + 0.2
        g = mesh_object(f"gable_{x:.0f}", coll, [(x + out * 0.01, H["y0"], zb), (x + out * 0.01, H["y1"], zb),
                                                  (x + out * 0.01, YM, RIDGE - 0.15)],
                        [(0, 1, 2) if out > 0 else (0, 2, 1)], m["cl_weatherboard"])
        g.data.uv_layers.remove(g.data.uv_layers[0])
        _uv_box(g, m["cl_weatherboard"], 2.0, 2, 1)
        mesh_object(f"gable_{x:.0f}_in", coll, [(x - out * 0.02, H["y0"], zb), (x - out * 0.02, H["y1"], zb),
                                                (x - out * 0.02, YM, RIDGE - 0.15)],
                    [(0, 2, 1) if out > 0 else (0, 1, 2)], m["cl_trim"])
        hub = (x + out * 0.03, YM, zb + 0.35)
        rays = []
        for k in range(11):
            a = math.radians(10 + 160 * k / 10)
            reach = (RIDGE - zb - 0.5) / max(0.35, math.sin(a) + abs(math.cos(a)) * math.tan(PITCH))
            end = (hub[0], YM + math.cos(a) * reach, hub[2] + math.sin(a) * reach)
            rays.append(tube(f"gable_ray_{k}", coll, [hub, end], 0.024, m["cl_trim"], sides=4, metres_per_v=2.0))
        join(rays, f"gable_rays_{x:.0f}")
        bx = x + out * GX
        for side, ye in ((-1, YE_S), (1, YE_N)):
            up, n, e, length = _slope_frame(side, ye)
            c = e + up * length / 2 - n * 0.06
            b = box(f"bargeboard_{x:.0f}_{side}", coll, bx - 0.035, bx + 0.035, -length / 2, length / 2, -0.17, 0.17, m["cl_shutter"])
            b.rotation_euler.x = -side * PITCH
            b.location = (bx, c[1], c[2])
            tube(f"barge_hook_{x:.0f}_{side}", coll, [(bx, ye, ZE - 0.15), (bx, ye + side * 0.18, ZE - 0.02),
                                                      (bx, ye + side * 0.12, ZE + 0.22), (bx, ye - side * 0.02, ZE + 0.3)],
                 0.04, m["cl_shutter"], sides=6, radius_end=0.015)
        tube(f"gable_finial_{x:.0f}", coll, [(bx, YM, RIDGE - 0.05), (bx, YM, RIDGE + 0.4), (bx + out * 0.08, YM, RIDGE + 0.75)],
             0.05, m["cl_shutter"], sides=6, radius_end=0.008)


def post_decay(coll, m, rng):
    """Termite tubes up two posts and cloth tied round three veranda posts."""
    half = 0.12
    for k, (x, y) in enumerate(((-6.0, 22.0), (3.0, 10.0))):
        for j in range(3):
            face = rng.integers(0, 4)
            nx, ny = ((1, 0), (-1, 0), (0, 1), (0, -1))[face]
            off = rng.uniform(-0.07, 0.07)
            pts = []
            for i in range(12):
                z = 0.47 + i * (FLOOR - 0.5) / 11
                off += rng.normal(0, 0.008)
                px = x + nx * (half + 0.006) + (0 if nx else off)
                py = y + ny * (half + 0.006) + (0 if ny else off)
                pts.append((px, py, z))
            tube(f"house_decay_termite_{k}_{j}", coll, pts, 0.011, m["termite"], sides=5, radius_end=0.007)
    for k, x in enumerate((6.0, 3.0, -3.0)):
        z0 = FLOOR + rng.uniform(0.45, 0.6)
        band = box(f"house_detail_tied_rag_{k}", coll, x - half - 0.008, x + half + 0.008, 10.0 - half - 0.008, 10.0 + half + 0.008,
                   z0, z0 + 0.06, m["rag"])
        tail = mesh_object(f"house_detail_tied_rag_tail_{k}", coll,
                           [(x + half + 0.008, 10.0 - 0.03, z0 + 0.03), (x + half + 0.008, 10.0 + 0.03, z0 + 0.03),
                            (x + half + 0.03, 10.0 + 0.05, z0 - 0.38), (x + half + 0.03, 10.0 - 0.02, z0 - 0.42)],
                           [(0, 1, 2, 3)], m["rag"])
        tail.data.materials[0].use_backface_culling = False


PRINTS_SPEC = json.load(open(os.path.join(os.path.dirname(__file__), "studio_prints.json")))["atlases"]
TEXTURES = os.path.join(ROOT, "art-source", "textures", "ep1")


def prints(coll, m):
    """Colour prints pinned to the walls, the same real public-domain sheets as the studio's."""
    mats = {k: image_material(f"M_house_print_{k}", os.path.join(TEXTURES, PRINTS_SPEC[k]["file"] + ".png"), rough=0.9)
            for k in ("posters", "colour", "cards")}
    lift = 0.0016
    # (name, atlas, item, centre, normal into the room, width).
    sheets = [
        # The hall: the Cambodian dance poster by the door to Yay Mey's room, the journal by the front door.
        ("house_print_dance", "posters", "PD1906", (-2.94 + lift, 19.4, FLOOR + 1.45), (1, 0, 0), 0.5),
        ("house_print_journal", "posters", "PJ1906", (-1.75, FRONT + lift, FLOOR + 1.45), (0, 1, 0), 0.36),
        # Sok's room: the map and postcards over his desk.
        ("house_print_siam", "colour", "SIAM1893", (5.94 - lift, 15.75, FLOOR + 1.42), (-1, 0, 0), 0.42),
        ("house_card_dancers", "cards", "DIEU1658", (5.94 - lift, 16.35, FLOOR + 1.12), (-1, 0, 0), 0.15),
        ("house_card_palace", "cards", "THRONE1910", (5.94 - lift, 15.2, FLOOR + 1.05), (-1, 0, 0), 0.15),
        ("house_print_vatphnom", "posters", "A35914", (4.55, 18.0 - T / 2 - lift, FLOOR + 1.5), (0, -1, 0), 0.4),
        # Vuthy's room: the travel poster of a young man who wants the town.
        ("house_print_kuling", "colour", "KULING", (5.94 - lift, 21.2, FLOOR + 1.45), (-1, 0, 0), 0.42),
        # Yay Mey's room: a royal dancer, mounted.
        ("house_print_nymph", "posters", "A36113", (-3.0 - lift, 20.2, FLOOR + 1.5), (-1, 0, 0), 0.34),
    ]
    for k, (name, atlas, item, centre, normal, width) in enumerate(sheets):
        right = tuple(np.cross((0, 0, 1), np.array(normal, float)))
        wall_print(name, coll, PRINTS_SPEC[atlas], item, mats[atlas], centre, right, (0, 0, 1), width,
                   curl=0.012 if width > 0.2 else 0.004, pins=m["brass"], seed=k)


def cobwebs(coll, m, rng):
    """Dusty webs in ceiling corners, and between posts and girders under the house."""
    sheet, thread = web_materials()
    c = ZW - 0.02
    corners = [
        ((-2.94 + 0.0, H["y1"] - T, c), (0, -1, 0), (1, 0, 0), 0.5), ((2.94, FRONT, c), (0, 1, 0), (-1, 0, 0), 0.4),
        ((H["x0"] + T, FRONT, c), (0, 1, 0), (1, 0, 0), 0.55), ((-3.0, 14.5 - T / 2, c), (0, -1, 0), (-1, 0, 0), 0.35),
        ((H["x0"] + T, H["y1"] - T, c), (0, -1, 0), (1, 0, 0), 0.6), ((H["x1"] - T, FRONT, c), (0, 1, 0), (-1, 0, 0), 0.45),
        ((H["x1"] - T, H["y1"] - T, c), (0, -1, 0), (-1, 0, 0), 0.5), ((3.0, 18.0 - T / 2, c), (0, -1, 0), (1, 0, 0), 0.3),
    ]
    for k, (p, da, db, size) in enumerate(corners):
        corner_cobweb(f"house_cobweb_{k}", coll, p, da, db, size, sheet, thread, seed=40 + k)
    # Under the house: webs in the angle of a post and the girder it carries.
    gz = FLOOR - 0.42
    for k, (x, y, sx) in enumerate(((-3.0, 14.0, 1), (3.0, 18.0, -1), (-6.0, 18.0, 1), (6.0, 14.0, -1), (0.0, 18.0, 1))):
        p = np.array((x + sx * 0.12, y + 0.11, gz))
        a = p + np.array((sx * rng.uniform(0.35, 0.6), 0, 0))
        b = p + np.array((0, 0, -rng.uniform(0.35, 0.6)))
        _sheet(f"house_beam_web_{k}", coll, a, b, p, 0.0, sheet, rng, n=8)
        for j in range(4):
            s = p + (a - p) * rng.uniform(0.2, 1.0)
            e = p + (b - p) * rng.uniform(0.2, 1.0)
            pts = [tuple(s * (1 - f) + e * f + np.array((0, 0, -0.05 * math.sin(math.pi * f)))) for f in np.linspace(0, 1, 7)]
            _thread(f"house_beam_thread_{k}_{j}", coll, pts, 0.0007, thread)


def build(coll, m, interact_props, seed=1932):
    rng = np.random.default_rng(seed)
    posts(coll, m)
    walls(coll, m)
    ceiling(coll, m)
    for name, wall_name, a, b, swing in WINDOWS:
        window_unit(coll, m, name, wall_name, a, b, swing)
    doors(coll, m, interact_props)
    veranda(coll, m)
    roof(coll, m, rng)
    post_decay(coll, m, rng)
    prints(coll, m)
    cobwebs(coll, m, rng)
