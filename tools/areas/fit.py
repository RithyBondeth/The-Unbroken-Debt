"""Fits dressing to the geometry it belongs on, after an area is built (run inside Blender).

Generators place cords, roots and offerings from nominal sizes (a trunk "about .6 m"
across, a plinth edge "at y -25"), but trunks are squeezed and buttressed, stupas lean
and scans are not cylinders, so dressing ends up floating beside its support or sunk in
it. Tag dressing while building it, then call `fit_dressing(coll)` once at the end:

- `wrap(obj, cx, cy, r)`: the object was laid round a vertical axis at nominal radius
  `r(z)` (cord round a trunk, roots down a stupa). Each vertex is moved out or in along
  its bearing so it keeps its offset from the real surface instead of from `r`.
- `rest(objs)`: the objects form one prop that must sit on what is under it (a pot and
  its sticks, a candle cluster). The group is lowered or raised onto its support, and
  slid back onto it if it overhangs an edge.
- `crown(obj, cx, cy)`: a fig trunk that grows out of a monument's top: it is moved
  down or up so its foot meets the masonry at the axis.
"""

import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WRAP, REST, CROWN = "fit_wrap", "fit_rest", "fit_crown"
_GROUP = "fit_group"
_groups = 0
_scope = []


def wrap(obj, cx, cy, r, top=None):
    """`r` is the nominal radius the generator used: a number or a function of z. With
    `top` (the nominal height of the monument's top), the object is also stretched or
    squashed in height so it starts on the real top."""
    obj[WRAP] = (cx, cy)
    if top is not None:
        obj["fit_top"] = float(top)
    obj["fit_r"] = [float(r(z / 20)) if callable(r) else float(r) for z in range(0, 121)]
    return obj


def rest(objs):
    global _groups
    _groups += 1
    for o in objs:
        o[REST] = _groups
    return objs


def crown(objs, cx, cy, top):
    """A fig's trunk, leaves and aerial roots, grown from a nominal `top`: they move
    together so the trunk's foot meets the monument's real top."""
    for o in objs:
        o[CROWN] = (cx, cy)
        o["fit_top"] = float(top)
    return objs


def _nominal(obj, z):
    table = obj["fit_r"]
    i = min(len(table) - 1, max(0, int(round(z * 20))))
    return table[i]


# Grass, understory and leaf cards are not something a pot or a cord rests on.
_SOFT = ("grass", "understory", "leaves", "leaf", "canopy", "spray", "fern", "moss_", "litter_leaves", "hair", "flame")


def _solid(o):
    if o.type != "MESH" or o.hide_render or o.name.startswith("col_"):
        return False
    if any(k in o.name.lower() for k in _SOFT):
        return False
    return not any(k in o for k in (WRAP, REST, CROWN))


_boxes = {}
_trees = {}
_grid = {}
CELL = 4.0


def _bbox(o):
    if o.name not in _boxes:
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        _boxes[o.name] = (min(c.x for c in corners), max(c.x for c in corners),
                          min(c.y for c in corners), max(c.y for c in corners))
    return _boxes[o.name]


def _index(solids):
    """Buckets solids by the 4 m cells their footprints cover, for quick neighbour lookups."""
    _grid.clear()
    for o in solids:
        x0, x1, y0, y1 = _bbox(o)
        for i in range(math.floor(x0 / CELL), math.floor(x1 / CELL) + 1):
            for j in range(math.floor(y0 / CELL), math.floor(y1 / CELL) + 1):
                _grid.setdefault((i, j), []).append(o)


def _tree(o):
    """A world-space BVH of one object, built once."""
    if o.name not in _trees:
        dg = bpy.context.evaluated_depsgraph_get()
        me = o.evaluated_get(dg).to_mesh()
        mw = o.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [list(p.vertices) for p in me.polygons]
        o.evaluated_get(dg).to_mesh_clear()
        _trees[o.name] = BVHTree.FromPolygons(verts, polys, epsilon=0.0) if polys else None
    return _trees[o.name]


class _Trees:
    """Several BVHs answering a ray as one: the nearest hit wins."""

    def __init__(self, trees):
        self.trees = trees

    def ray_cast(self, origin, direction, distance):
        best = (None, None, None, None)
        for t in self.trees:
            hit = t.ray_cast(origin, direction, distance)
            if hit[0] is not None and (best[3] is None or hit[3] < best[3]):
                best = hit
        return best


def _bvh(objs):
    trees = [t for t in (_tree(o) for o in objs) if t is not None]
    return _Trees(trees) if trees else None


def _near(objs, x, y, reach):
    """Solids whose footprint comes within `reach` of (x, y). `objs` is ignored in favour of
    the grid built from the same solids."""
    seen, out = set(), []
    for i in range(math.floor((x - reach) / CELL), math.floor((x + reach) / CELL) + 1):
        for j in range(math.floor((y - reach) / CELL), math.floor((y + reach) / CELL) + 1):
            for o in _grid.get((i, j), ()):
                if o.name in seen:
                    continue
                seen.add(o.name)
                x0, x1, y0, y1 = _bbox(o)
                if x0 - reach < x < x1 + reach and y0 - reach < y < y1 + reach:
                    out.append(o)
    return out


def _on_axis(objs, x, y, margin=.05):
    """Objects standing on the axis (x, y): the trunk or monument a dressing wraps."""
    out = []
    for o in objs:
        x0, x1, y0, y1 = _bbox(o)
        if x0 - margin < x < x1 + margin and y0 - margin < y < y1 + margin:
            out.append(o)
    return out


def _surface_radius(tree, cx, cy, z, a, guess):
    """Distance from the axis to the outside of whatever stands on it, along bearing `a`."""
    if tree is None:
        return None
    d = Vector((math.cos(a), math.sin(a), 0))
    far = max(3.0, guess * 3)
    origin = Vector((cx, cy, z)) + d * far
    hit = tree.ray_cast(origin, -d, far)
    if hit[0] is None:
        return None
    return (hit[0] - Vector((cx, cy, z))).length


def _fit_wrapped(solids):
    for o in [o for o in _scope if WRAP in o]:
        cx, cy = o[WRAP]
        tree = _bvh(_on_axis(_near(solids, cx, cy, 1.5), cx, cy))
        mw, mwi = o.matrix_world, o.matrix_world.inverted()
        scale = 1.0
        if "fit_top" in o:
            top = _real_top(solids, cx, cy, o["fit_top"])
            if top is not None and o["fit_top"] > .2:
                scale = top / o["fit_top"]
        for v in o.data.vertices:
            p = mw @ v.co
            if p.z < .08:
                continue  # the part already in the ground stays where it grips
            z0 = p.z
            p.z = .08 + (p.z - .08) * scale
            a = math.atan2(p.y - cy, p.x - cx)
            r = math.hypot(p.x - cx, p.y - cy)
            nominal = _nominal(o, z0)
            real = _surface_radius(tree, cx, cy, p.z, a, nominal)
            if real is None:
                v.co = mwi @ p  # nothing there at this height (root tips on the ground)
                continue
            r2 = max(real + .004, real + (r - nominal))
            p2 = Vector((cx + math.cos(a) * r2, cy + math.sin(a) * r2, p.z))
            v.co = mwi @ p2
        o.data.update()


_tops = {}


def _real_top(solids, cx, cy, nominal):
    """Height of the masonry's top on the axis (cached per axis). The ray starts a little above
    the nominal top and only meets things standing on the ground there, so the canopy of a
    tree arching over a stupa is never taken for its top."""
    key = (round(cx, 3), round(cy, 3))
    if key not in _tops:
        standing = [o for o in _on_axis(_near(solids, cx, cy, .8), cx, cy) if _zmin(o) < .3]
        tree = _bvh(standing)
        start = nominal * 1.8 + 1.0  # above any spire, below the canopies
        hit = None if tree is None else tree.ray_cast(Vector((cx, cy, start)), Vector((0, 0, -1)), start + 1)
        _tops[key] = None if hit is None or hit[0] is None else hit[0].z
    return _tops[key]


_zmins = {}


def _zmin(o):
    if o.name not in _zmins:
        _zmins[o.name] = min((o.matrix_world @ Vector(c)).z for c in o.bound_box)
    return _zmins[o.name]


def _fit_crowns(solids):
    for o in [o for o in _scope if CROWN in o]:
        cx, cy = o[CROWN]
        top = _real_top(solids, cx, cy, o["fit_top"])
        if top is not None:
            o.location.z += top - o["fit_top"]


def _fit_rests(solids):
    groups = {}
    for o in _scope:
        if REST in o:
            groups.setdefault(o[REST], []).append(o)
    for objs in groups.values():
        pts = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
        base = min(p.z for p in pts)
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts)))
        c = (lo + hi) / 2
        tree = _bvh(_near(solids, c.x, c.y, 1.0))
        if tree is None:
            continue

        def support(x, y):
            hit = tree.ray_cast(Vector((x, y, base + .25)), Vector((0, 0, -1)), 3)
            return None if hit[0] is None else hit[0].z

        def footprint(off):
            hx, hy = (hi.x - lo.x) * .35, (hi.y - lo.y) * .35
            return [support(c.x + off.x + dx, c.y + off.y + dy) for dx in (-hx, 0, hx) for dy in (-hy, 0, hy)]

        # Slide back onto the support if the centre overhangs an edge, toward whichever
        # side holds; then sit on the highest point under the footprint.
        off = Vector((0, 0))
        heights = footprint(off)
        if heights[4] is None or heights[4] < base - .05:
            best = None
            for k in range(16):
                a = k * math.tau / 16
                for step in (.04, .08, .12, .16, .22, .3):
                    o2 = Vector((math.cos(a) * step, math.sin(a) * step))
                    h = footprint(o2)
                    if h[4] is not None and abs(h[4] - base) < .06 and all(x is not None and x > base - .06 for x in h):
                        if best is None or step < best[0]:
                            best = (step, o2)
                        break
            if best:
                off = best[1]
                heights = footprint(off)
        known = [h for h in heights if h is not None]
        if not known:
            continue
        target = max(known)
        if base > -.05 and target < -.05:
            # Authored at ground level over ground the game adds at runtime (the far forest
            # floor): it stays at ground level rather than falling onto a buried root.
            target = 0.0
        dz = target - base
        for o in objs:
            o.location.x += off.x
            o.location.y += off.y
            o.location.z += dz


def fit_dressing(coll):
    """Call once, after everything in the area's collection `coll` exists."""
    global _scope
    bpy.context.view_layer.update()
    _scope = list(coll.all_objects)
    solids = [o for o in _scope if _solid(o)]
    _boxes.clear()
    _tops.clear()
    _zmins.clear()
    _trees.clear()
    _index(solids)
    import time
    t = time.time()
    _fit_crowns(solids)
    _fit_wrapped(solids)
    _fit_rests(solids)
    print("FIT: %d solids, %d tagged, %.1fs" % (len(solids), sum(1 for o in _scope if any(k in o for k in (WRAP, REST, CROWN))), time.time() - t))
    # The tags were only for this pass: keep them out of the exported glTF extras.
    for o in _scope:
        for key in (WRAP, REST, CROWN, "fit_r", "fit_top"):
            if key in o:
                del o[key]
    bpy.context.view_layer.update()
