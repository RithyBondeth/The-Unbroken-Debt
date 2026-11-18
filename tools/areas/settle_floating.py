"""Sets down everything that floats in an area file. Uses ground_audit.py to find
each loose part that rests on nothing and touches nothing, then moves that part
(only that part) the shortest sensible way onto what should hold it:

  * down onto the ground, a floor, a table or a shelf;
  * back against the nearest wall, for thin upright things (prints, frames,
    stains, cloths pinned flat);
  * up to its support, for things that hang (cords, cloths, streamers, flags,
    lanterns);
  * broken-off pieces of dead branches hanging in mid-air are removed.

Parts that would have to move further than a short reach are left and listed.

    blender -b --factory-startup art-source/blender/ep1/ep1_area_village.blend \\
        -P tools/areas/settle_floating.py -- [report.json] [--box x0 y0 x1 y1] [--dry]
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
AUDIT_AS_MODULE = True
import ground_audit  # noqa: E402

DRY = "--dry" in sys.argv
HANGS = re.compile(r"(streamer|flag|cloth|rope|cord|thread|web|lantern|tieback|curtain|valance|banner|net|hung|tassel|tie|"
                   r"string|garland|rag|sarong|krama)", re.I)
BARK = re.compile(r"^M_wet_bark|bark", re.I)
REACH = {"down": 2.5, "up": 0.8, "side": 0.35}


def _rays(bvh, tri_part, part_index, starts, direction, limit):
    best = math.inf
    d = Vector(direction)
    for v in starts:
        hit = bvh.ray_cast(Vector(v) + d * -0.0005, d, limit)
        if hit[0] is not None and tri_part[hit[2]] != part_index:
            best = min(best, hit[3])
    return best


def _extreme(pts, axis, sign, n=12):
    vals = pts[:, axis] * sign
    edge = vals.max()
    sel = pts[vals > edge - 0.02]
    if len(sel) > n:
        sel = sel[np.linspace(0, len(sel) - 1, n).astype(int)]
    return sel


def plan_moves(failures, ctx):
    bvh, tri_part, parts = ctx["bvh"], ctx["tri_part"], ctx["parts"]
    moves, deletes, left = [], [], []
    for f in failures:
        p_i = f["part"]
        name, mat, pts, _tri, vsel = parts[p_i]
        ext = pts.max(0) - pts.min(0)
        options = {}
        down = _rays(bvh, tri_part, p_i, _extreme(pts, 2, -1), (0, 0, -1), REACH["down"])
        if down < math.inf:
            options["down"] = (down, (0, 0, -1))
        up = _rays(bvh, tri_part, p_i, _extreme(pts, 2, 1), (0, 0, 1), REACH["up"])
        if up < math.inf:
            options["up"] = (up, (0, 0, 1))
        # Buried: the ground lies above the whole part.
        bury = _rays(bvh, tri_part, p_i, _extreme(pts, 2, -1), (0, 0, 1), 3.0)
        for axis, label in ((0, "x"), (1, "y")):
            for sign in (1, -1):
                g = _rays(bvh, tri_part, p_i, _extreme(pts, axis, sign), tuple(sign if i == axis else 0 for i in range(3)),
                          REACH["side"])
                if g < math.inf:
                    options[f"side{label}{sign:+d}"] = (g, tuple(sign if i == axis else 0 for i in range(3)))
        thin_upright = min(ext[0], ext[1]) < 0.03 and ext[2] > 0.06
        hangs = bool(HANGS.search(name) or HANGS.search(mat or ""))
        if BARK.search(mat or "") and (down == math.inf or down > 0.3) and not any(k.startswith("side") and v[0] < 0.05
                                                                                for k, v in options.items()):
            deletes.append((name, vsel, f))
            continue
        choice = None
        if thin_upright:
            sides = [(v, k) for k, v in options.items() if k.startswith("side")]
            if sides:
                choice = min(sides, key=lambda s: s[0][0])
        if choice is None and hangs and "up" in options:
            choice = (options["up"], "up")
        if choice is None and "down" in options:
            choice = (options["down"], "down")
        if choice is None and options:
            k = min(options, key=lambda key: options[key][0])
            choice = (options[k], k)
        if choice is None and bury < math.inf:
            choice = ((bury + 0.004, (0, 0, 1)), "unbury")
        if choice is None:
            left.append(f)
            continue
        (gap, direction), label = choice
        moves.append((name, vsel, np.array(direction) * (gap + 0.002), label, f))
    return moves, deletes, left


def _single_user_mesh(obj):
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    if obj.modifiers:
        bpy.context.view_layer.objects.active = obj
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)


def apply(moves, deletes):
    import bmesh
    by_obj = {}
    for name, vsel, delta, label, f in moves:
        by_obj.setdefault(name, []).append(("move", vsel, delta))
    for name, vsel, f in deletes:
        by_obj.setdefault(name, []).append(("delete", vsel, None))
    for name, ops in by_obj.items():
        obj = bpy.data.objects[name]
        n_verts = len(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
        whole = len(ops) == 1 and ops[0][0] == "move" and len(ops[0][1]) == n_verts
        if whole:
            # The whole object floats: move the object, in its parent's space.
            delta = Vector(ops[0][2])
            mw = obj.matrix_world.copy()
            mw.translation += delta
            obj.matrix_world = mw
            continue
        _single_user_mesh(obj)
        if len(obj.data.vertices) != n_verts:
            print(f"[settle] {name}: vertex count changed applying modifiers; skipped")
            continue
        inv = obj.matrix_world.inverted().to_3x3()
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        doomed = []
        for kind, vsel, delta in ops:
            if kind == "move":
                local = inv @ Vector(delta)
                for i in vsel:
                    bm.verts[int(i)].co += local
            else:
                doomed += [bm.verts[int(i)] for i in vsel]
        if doomed:
            bmesh.ops.delete(bm, geom=list(set(doomed)), context="VERTS")
        bm.to_mesh(obj.data)
        bm.free()


def main():
    # Objects with modifiers must have them applied for the audit's vertex indices to match.
    failures, ctx = ground_audit.audit()
    names = {f["object"] for f in failures}
    if not DRY:
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj and obj.type == "MESH" and obj.modifiers:
                _single_user_mesh(obj)
        failures, ctx = ground_audit.audit()
    moves, deletes, left = plan_moves(failures, ctx)
    for name, _v, delta, label, f in moves:
        print(f"[settle] {label:>8} {np.linalg.norm(delta):.3f} m  {name} [{f['material']}] at {f['min']}")
    for name, _v, f in deletes:
        print(f"[settle]   delete  {name} [{f['material']}] at {f['min']}")
    for f in left:
        print(f"[settle]     LEFT  {f['object']} [{f['material']}] at {f['min']}")
    print(f"[settle] {len(moves)} moved, {len(deletes)} removed, {len(left)} left")
    if DRY:
        return
    apply(moves, deletes)
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    after, _ = ground_audit.audit()
    print(f"[settle] after: {len(after)} floating parts")


main()
