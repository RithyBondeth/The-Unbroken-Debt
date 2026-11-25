"""Episode 1's house after the user's third review, November 25, 2026 (four game
screenshots), the parts that are not the store room (house_review.store_room), the
prints' atlas (colonial_parts.wall_print) or the webs (cobwebs.refit):

- The hall's east wall: the framed certificate hung half behind the wall post at y 14
  (the post stands 6 cm proud of the boards): taken down. Anything else hung on a wall
  behind a post is reported (none was, Nov 25).
- Kanha's room: her mosquito net knotted up over the bed read as a white paper lamp
  ("this is just a cartoon"); the user chose a real lamp there. A kerosene hurricane lamp
  (Poly Haven's Lantern_01 scan) hangs on a forged chain from an eye screwed into a turned
  block on the ceiling boards, an S hook through its bail. (A soot stain over it read as a
  black bat on the ceiling: left off.)
- The hall's lamp hung from a square iron bar standing in for a chain, its glass at head
  height: the same chain and hook now, the lamp raised to clear Sora's head.

Blender metres, X east, Y north, Z up. Called at the end of rebuild-farmstead.py.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import review_kit as RK
import stilt_house as SH
from kit import import_model
from shrine_craft import Batch, place

F, T, ZW = SH.FLOOR, SH.T, SH.ZW
CEILING = ZW - 0.02                 # the underside of the tongue-and-groove ceilings
POSTS = SH.FRONT_POSTS + SH.BACK_POSTS
HUNG = ("print", "frame", "calendar", "certificate", "photo", "poster", "drawing", "_vj", "card", "clock", "mirror", "map")


# ------------------------------------------------------------------ the hall's certificate


def wall_posts():
    """The certificate behind the hall's post comes down; anything else hung on a wall where
    a post stands in front of it is reported."""
    gone = RK.delete(o for o in bpy.data.objects if o.name.startswith("hall_certificate"))
    print("[polish] hall certificate down:", gone, flush=True)
    RK.vl()
    for o in bpy.data.objects:
        if o.type != "MESH" or not any(k in o.name.lower() for k in HUNG) or o.name.startswith(("col_", "door_frame")):
            continue
        if any(c.name.startswith("_") for c in o.users_collection):
            continue
        bb = RK.box_of([o])
        if bb is None or not (F + 0.3 < bb[1].z < ZW) or (bb[1] - bb[0]).length > 2.0:
            continue
        for x, y in POSTS:
            if bb[0].x < x + 0.12 and bb[1].x > x - 0.12 and bb[0].y < y + 0.12 and bb[1].y > y - 0.12:
                print("[polish] WARNING hung behind the post at", (x, y), o.name, flush=True)


# ------------------------------------------------------------------ hanging lamps


def _link(b, mat, centre, length, width, wire, turn):
    """One oval link of forged wire, standing in the vertical plane turned `turn` about Z."""
    rr = width / 2 - wire
    half = length / 2 - wire - rr
    c, s = math.cos(turn), math.sin(turn)
    pts = []
    for k in range(24):
        a = k / 24 * math.tau
        u = rr * math.cos(a)
        z = rr * math.sin(a) + (half if math.sin(a) >= 0 else -half)
        pts.append((centre.x + c * u, centre.y + s * u, centre.z + z))
    pts.append(pts[0])
    b.tube(mat, pts, wire, sides=7)


def hanging_lamp(coll, m, name, x, y, bottom, rng):
    """A hurricane lamp hung under the ceiling: a turned block on the boards, a screw eye, a
    forged chain, an S hook through the lamp's bail. Returns the lamp's root."""
    iron = m.get("cast_iron") or m["iron"]
    wood = m.get("cl_trim") or m.get("bed_wood")
    b = Batch(f"{name}_hanger")
    # The block (a pattress), screwed to the ceiling boards.
    b.lathe(wood, [(0, 0), (0.036, 0), (0.038, 0.004), (0.034, 0.011), (0.026, 0.014), (0, 0.014)],
            xf=Matrix.Translation((x, y, CEILING)) @ Matrix.Rotation(math.pi, 4, "X"), segments=24, tile=0.08)
    # The screw eye: its shank up into the block, its ring under it.
    eye_r, wire = 0.011, 0.0028
    ring_c = Vector((x, y, CEILING - 0.014 - 0.006 - eye_r))
    b.tube(iron, [(x, y, CEILING - 0.006), (x, y, ring_c.z + eye_r)], 0.0026, sides=7)
    _link(b, iron, ring_c, 2 * eye_r + 2 * wire, 2 * eye_r + 2 * wire, wire, 0.0)
    # The lamp, its bail's top where the S hook will hold it.
    lamp = import_model(coll, "Lantern_01", (x, y, bottom), rot_deg=float(rng.uniform(0, 360)), name=name, collide=False)
    RK.vl()
    lb = RK.box_of(RK.tree(lamp))
    lamp.location.z += bottom - lb[0].z
    RK.vl()
    lb = RK.box_of(RK.tree(lamp))
    bail = lb[1].z - 0.004
    # The S hook: its lower bowl through the bail, its upper bowl holding the chain's last
    # link (two 12 mm bowls, point-symmetric about their joint).
    r, mid = 0.012, bail + 0.024
    s_pts = [(x + r * math.cos(a), y, mid + r + r * math.sin(a)) for a in np.linspace(math.pi, -math.pi / 2, 13)]
    s_pts += [(x + r * math.cos(a), y, mid - r + r * math.sin(a)) for a in np.linspace(math.pi / 2, 2 * math.pi, 13)[1:]]
    b.tube(iron, s_pts, 0.0022, sides=6)
    hook_top = mid + 2 * r
    # The chain: interlocked oval links, each turned a quarter to the last, from the eye's
    # ring down to the hook.
    length, width, wire = 0.034, 0.02, 0.0031
    first = ring_c.z - eye_r - length / 2 + 2 * wire          # hangs in the eye's ring
    last = hook_top + length / 2 - 2 * wire                    # sits in the hook's bowl
    n = max(2, int(round((first - last) / (length - 4 * wire))) + 1)
    pitch = (first - last) / (n - 1)
    for k in range(n):
        _link(b, iron, Vector((x, y, first - pitch * k)), length, width, wire, math.pi / 2 if k % 2 == 0 else 0.0)
    b.build(coll)
    print(f"[polish] {name} hung at", (round(x, 2), round(y, 2)), "bottom", round(bottom - F, 2), "links", n, flush=True)
    return lamp


def lamps(coll, m, rng):
    # Kanha's room: by her bed, where the knotted net hung over it; out of her way when
    # she sat up, high enough to walk under.
    bed = next((o for o in bpy.data.objects if o.name.startswith("house_old_bed_frame") and o.parent is None), None)
    bb = RK.box_of(RK.tree(bed)) if bed else None
    kx, ky = (bb[0].x - 0.42, (bb[0].y + bb[1].y) / 2) if bb else (5.5, 24.9)
    hanging_lamp(coll, m, "kanha_lamp", kx, ky, F + 1.98, rng)
    # The hall: its lamp off the bar and onto a chain, its glass above head height.
    RK.delete([o for o in (bpy.data.objects.get("hall_lamp_chain"), bpy.data.objects.get("hall_lamp")) if o])
    hanging_lamp(coll, m, "hall_lamp", 0.0, 14.6, F + 1.98, rng)


def polish(coll, m):
    rng = np.random.default_rng(2511)
    wall_posts()
    lamps(coll, m, rng)
