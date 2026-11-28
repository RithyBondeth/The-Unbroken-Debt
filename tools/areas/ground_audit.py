"""Finds things that float: every loose part of every visible mesh must rest on
something below it or touch something beside it (a wall, a hook, a cord).

Run on any area file:
    blender -b --factory-startup art-source/blender/ep1/ep1_area_village.blend \
        -P tools/areas/ground_audit.py -- [report.json] [--tol 0.015] [--box x0 y0 x1 y1]

A part passes when a ray cast straight down from one of its lowest points meets a
surface within `tol`, or when any of its sampled points lies within `tol` of
another part (its own object's other parts count). Plants, colliders and the
sky are skipped: leaves hang from branches by design and are checked at runtime.
The report lists each failure with the height of its gap, worst first.
"""

import json
import math
import re
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TOL = 0.015
OUT = None
REGION = None  # (x0, y0, x1, y1): only report parts whose centre lies inside
i = 0
while i < len(argv):
    if argv[i] == "--tol":
        TOL = float(argv[i + 1])
        i += 2
        continue
    if argv[i] == "--box":
        REGION = tuple(float(v) for v in argv[i + 1:i + 5])
        i += 5
        continue
    if argv[i].startswith("--"):
        i += 1
        continue
    OUT = argv[i]
    i += 1

# Objects that are meant to hang in the air, or are not solid things at all.
SKIP_OBJECT = re.compile(
    r"^(col_|sky|storm|rain|light_|marker_|spawn_|proto_|tpl_|terrain_far|fog|mist|paddy_rice_)"
    r"|^(banana|palm|coconut|shrub|fern|pachira|grass|moss|island_tree|jungle|forest_leaf|forest_canopy|vine|liana|leaf)",
    re.I,
)
SKIP_MATERIAL = re.compile(
    r"^M_(banana_leaf|palm_fan|coconut_leaf|tree_leaves|bamboo_leaves|grass|forest_|leaf|flame|lamp_window|cobweb"
    # The scanned plants (village_nature.py): leaves, fronds and vines hang from their own
    # wood by design; their trunks stand on their origin, checked in the game (groundSnap).
    r"|flora_(forest_tree_gn|forest_banyan|sugar_palm|bamboo_clump|banana_clump|scarecrow|anthurium|calathea"
    r"|fern|shrub|nettle|weed|periwinkle|grass)|paddy_rice)", re.I
)


def islands(faces_flat, loop_start, loop_total, nverts):
    """Connected parts of a mesh: a label per vertex (pointer-jumping union)."""
    labels = np.arange(nverts, dtype=np.int64)
    # Each polygon's vertices belong together: link each to the polygon's first vertex.
    first = np.repeat(faces_flat[loop_start], loop_total)
    a, b = first, faces_flat
    for _ in range(200):
        la, lb = labels[a], labels[b]
        m = np.minimum(la, lb)
        changed = np.any(la != lb)
        np.minimum.at(labels, a, m)
        np.minimum.at(labels, b, m)
        labels = labels[labels]
        labels = labels[labels]
        if not changed:
            break
    return labels


def audit():
    deps = bpy.context.evaluated_depsgraph_get()
    parts = []  # (object name, material, island verts world (N,3))
    all_verts, all_tris, tri_part = [], [], []
    offset = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or SKIP_OBJECT.search(obj.name) or obj.hide_render:
            continue
        ev = obj.evaluated_get(deps)
        mesh = ev.to_mesh()
        n = len(mesh.vertices)
        if n == 0:
            ev.to_mesh_clear()
            continue
        co = np.empty(n * 3, np.float64)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(obj.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        np_ = len(mesh.polygons)
        ls = np.empty(np_, np.int64)
        lt = np.empty(np_, np.int64)
        mesh.polygons.foreach_get("loop_start", ls)
        mesh.polygons.foreach_get("loop_total", lt)
        mi = np.empty(np_, np.int64)
        mesh.polygons.foreach_get("material_index", mi)
        lv = np.empty(len(mesh.loops), np.int64)
        mesh.loops.foreach_get("vertex_index", lv)
        mats = [s.material.name if s.material else "" for s in obj.material_slots]
        ev.to_mesh_clear()
        if np_ == 0:
            continue
        labels = islands(lv, ls, lt, n)
        # Triangulate as fans for the BVH.
        tris = []
        for k in range(np_):
            s, t = ls[k], lt[k]
            for j in range(1, t - 1):
                tris.append((lv[s], lv[s + j], lv[s + j + 1]))
        tris = np.array(tris, np.int64)
        face_of_tri = np.repeat(np.arange(np_), np.maximum(lt - 2, 0))
        uniq, part_index = np.unique(labels, return_inverse=True)
        base = len(parts)
        tri_isl = part_index[tris[:, 0]] if len(tris) else np.zeros(0, np.int64)
        order = np.argsort(tri_isl, kind="stable")
        bounds = np.searchsorted(tri_isl[order], np.arange(len(uniq) + 1))
        vorder = np.argsort(part_index, kind="stable")
        vbounds = np.searchsorted(part_index[vorder], np.arange(len(uniq) + 1))
        poly_isl = part_index[lv[ls]]
        first_poly = np.full(len(uniq), -1, np.int64)
        first_poly[poly_isl[::-1]] = np.arange(np_)[::-1]
        for u_i in range(len(uniq)):
            vsel = vorder[vbounds[u_i]:vbounds[u_i + 1]]
            fp = first_poly[u_i]
            mat = mats[mi[fp]] if fp >= 0 and mats and mi[fp] < len(mats) else ""
            ptris = tris[order[bounds[u_i]:bounds[u_i + 1]]]
            parts.append((obj.name, mat, co[vsel], co[ptris] if len(ptris) else None, vsel))
        all_verts.append(co)
        all_tris.append(tris + offset)
        tri_part.append(base + part_index[tris[:, 0]])
        offset += n
    verts = np.concatenate(all_verts)
    tris = np.concatenate(all_tris)
    tri_part = np.concatenate(tri_part)
    print(f"[audit] {len(parts)} parts, {len(tris)} triangles; building BVH", flush=True)
    bvh = BVHTree.FromPolygons([Vector(v) for v in verts], tris.tolist(), all_triangles=True, epsilon=0.0)
    failures = []
    down = Vector((0, 0, -1))
    up = Vector((0, 0, 1))
    for p_i, (name, mat, pts, ptri, vsel) in enumerate(parts):
        if SKIP_MATERIAL.search(mat or "") or len(pts) < 3:
            continue
        if REGION:
            cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
            if not (REGION[0] <= cx <= REGION[2] and REGION[1] <= cy <= REGION[3]):
                continue
        zmin = pts[:, 2].min()
        if zmin < -0.5 and name.startswith(("terrain", "ground", "road", "paddy", "flood", "pond", "well")):
            continue
        # Below: the lowest points (within 2 cm of the bottom), up to 12 of them.
        low = pts[pts[:, 2] < zmin + 0.02]
        if len(low) > 12:
            low = low[np.linspace(0, len(low) - 1, 12).astype(int)]
        best = math.inf
        for v in low:
            hit = bvh.ray_cast(Vector((v[0], v[1], v[2] - 0.0005)), down, 50.0)
            if hit[0] is not None and tri_part[hit[2]] != p_i:
                best = min(best, hit[3])
            if best <= TOL:
                break
        if best <= TOL:
            continue
        # Sunk into something (a post in the ground): a ray up from its foot meets that surface.
        sunk = False
        for v in low[:4]:
            hit = bvh.ray_cast(Vector((v[0], v[1], v[2] + 0.0005)), up, float(pts[:, 2].max() - v[2]))
            if hit[0] is not None and tri_part[hit[2]] != p_i:
                sunk = True
                break
        if sunk:
            continue
        # Passing into something (a beam into a wall, a wall inside a beam): its
        # triangles intersect another part's.
        crossing = False
        if ptri is not None:
            flat = ptri.reshape(-1, 3)
            local = BVHTree.FromPolygons([Vector(v) for v in flat], [(3 * k, 3 * k + 1, 3 * k + 2) for k in range(len(ptri))],
                                         all_triangles=True)
            crossing = any(tri_part[j] != p_i for _i, j in local.overlap(bvh))
        if crossing:
            continue
        # Beside: any sampled point touching another part.
        sample = pts if len(pts) <= 160 else pts[np.linspace(0, len(pts) - 1, 160).astype(int)]
        touching = False
        for v in sample:
            for _co, _n, idx, _d in bvh.find_nearest_range(Vector(v), TOL):
                if tri_part[idx] != p_i:
                    touching = True
                    break
            if touching:
                break
        if touching:
            continue
        lo, hi = pts.min(0), pts.max(0)
        failures.append({
            "object": name, "material": mat, "gap": None if best == math.inf else round(best, 3), "part": p_i,
            "min": [round(x, 2) for x in lo], "max": [round(x, 2) for x in hi], "verts": len(pts),
        })
    failures.sort(key=lambda f: -(f["gap"] if f["gap"] is not None else 99))
    print(f"[audit] {len(failures)} floating parts (tolerance {TOL} m)")
    for f in failures[:80]:
        print(f"  gap {f['gap']}  {f['object']}  [{f['material']}]  min {f['min']}  verts {f['verts']}")
    if OUT:
        with open(OUT, "w") as stream:
            json.dump(failures, stream, indent=1)
    return failures, {"bvh": bvh, "tri_part": tri_part, "parts": parts}


if __name__ == "__main__" and not globals().get("AUDIT_AS_MODULE"):
    audit()
