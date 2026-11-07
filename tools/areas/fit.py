"""Fits dressing to the geometry it belongs on (run inside Blender).

Generators place cords, roots, cloth and offerings from nominal sizes (a trunk "about .6 m"
across, a plinth edge "at y -25"), but trunks are buttressed, stupas lean and scans are not
cylinders, so dressing ends up floating beside its support or sunk in it. Fitting must only
ever look at the thing the dressing belongs to: measured against everything nearby, a root
reaching for a stupa catches a tree branch two metres off and is dragged out into the air.

- `Support(objs)`: the masonry or trunk a piece belongs to, measured while it is built. Roots
  and cloth trace its real outline (`radius`, `drape`) and start on its real top (`top`).
- `wrap(obj, cx, cy, r)`: for a cord laid round a trunk that is planted later. After the
  build, each vertex is moved out or in along its bearing to keep its offset from the real
  surface instead of from `r`, measured only against what stands on that axis.
- `rest(objs)`: the objects form one prop that must sit on what is under it (a pot and its
  sticks, a candle cluster). The group is lowered or raised onto its support, and slid back
  onto it if it overhangs an edge.

Call `fit_dressing(coll)` once, after everything in the area exists.
"""

import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WRAP, REST = "fit_wrap", "fit_rest"
_groups = 0
_scope = []

# Grass, understory and leaf cards are not something a pot or a cord rests on.
_SOFT = ("grass", "understory", "leaves", "leaf", "canopy", "spray", "fern", "moss_", "litter_leaves", "hair", "flame")


def _world(o):
    """The object's world matrix now, without a depsgraph update (generators move objects
    by their basis many times while building)."""
    if o.parent is None:
        return o.matrix_basis.copy()
    return _world(o.parent) @ o.matrix_parent_inverse @ o.matrix_basis


class Support:
    """A world-space BVH of the given objects only: what a piece of dressing belongs to."""

    def __init__(self, objs):
        verts, polys = [], []
        for o in objs:
            if o is None or o.type != 'MESH':
                continue
            mw = _world(o)
            base = len(verts)
            verts += [mw @ v.co for v in o.data.vertices]
            polys += [[base + i for i in p.vertices] for p in o.data.polygons]
        self.tree = BVHTree.FromPolygons(verts, polys, epsilon=0.0) if polys else None

    @classmethod
    def standing(cls, coll, x, y, margin=.05):
        """Whatever stands on the ground at (x, y): the trunk or masonry whose footprint holds it."""
        return cls(_standing(list(coll.all_objects), x, y, margin))

    def __bool__(self):
        return self.tree is not None

    def radius(self, cx, cy, z, a, reach=3.0):
        """Distance from the axis (cx, cy) to the outside of the support along bearing `a`."""
        if self.tree is None:
            return None
        d = Vector((math.cos(a), math.sin(a), 0))
        hit = self.tree.ray_cast(Vector((cx, cy, z)) + d * reach, -d, reach)
        return None if hit[0] is None else reach - hit[3]

    def drape(self, cx, cy, z, a, above=.12, reach=3.0):
        """The outline as cloth or a root hanging down it sees it: the widest point from `z` up
        to `above` higher, so it bridges under a ledge instead of tucking into it."""
        best = None
        for k in range(4):
            r = self.radius(cx, cy, z + above * k / 3, a, reach)
            if r is not None and (best is None or r > best):
                best = r
        return best

    def top(self, cx, cy, start=30.0):
        """Height of the support's top on the axis."""
        if self.tree is None:
            return None
        hit = self.tree.ray_cast(Vector((cx, cy, start)), Vector((0, 0, -1)), start + 2)
        return None if hit[0] is None else hit[0].z


def outward(radii):
    """Smooths a run of radii outward only: a path traced over masonry loses its sawtooth
    without ever cutting into what it lies on."""
    r = list(radii)
    for _ in range(3):
        r = [r[0]] + [max(r[i], (r[i - 1] + r[i + 1]) / 2) for i in range(1, len(r) - 1)] + [r[-1]]
    return r


def wrap(obj, cx, cy, r):
    """`r` is the nominal radius the generator laid the cord at."""
    obj[WRAP] = (cx, cy)
    obj["fit_r"] = float(r)
    return obj


def rest(objs):
    global _groups
    _groups += 1
    for o in objs:
        o[REST] = _groups
    return objs


def _solid(o):
    if o.type != "MESH" or o.hide_render or o.name.startswith("col_"):
        return False
    if any(k in o.name.lower() for k in _SOFT):
        return False
    return not any(k in o for k in (WRAP, REST))


def _bbox(o):
    corners = [_world(o) @ Vector(c) for c in o.bound_box]
    return (min(c.x for c in corners), max(c.x for c in corners), min(c.y for c in corners),
            max(c.y for c in corners), min(c.z for c in corners))


def _standing(objs, x, y, margin=.05):
    out = []
    for o in objs:
        if not _solid(o):
            continue
        x0, x1, y0, y1, z0 = _bbox(o)
        # Standing here: its footprint holds the axis and it reaches down to the ground. A
        # branch or a canopy arching over the axis does not.
        if x0 - margin < x < x1 + margin and y0 - margin < y < y1 + margin and z0 < .5:
            out.append(o)
    return out


_boxes = {}
_grid = {}
CELL = 4.0


def _box(o):
    if o.name not in _boxes:
        _boxes[o.name] = _bbox(o)
    return _boxes[o.name]


def _index(solids):
    """Buckets solids by the 4 m cells their footprints cover, for quick neighbour lookups."""
    _grid.clear()
    for o in solids:
        x0, x1, y0, y1, _ = _box(o)
        for i in range(math.floor(x0 / CELL), math.floor(x1 / CELL) + 1):
            for j in range(math.floor(y0 / CELL), math.floor(y1 / CELL) + 1):
                _grid.setdefault((i, j), []).append(o)


def _near(x, y, reach):
    seen, out = set(), []
    for i in range(math.floor((x - reach) / CELL), math.floor((x + reach) / CELL) + 1):
        for j in range(math.floor((y - reach) / CELL), math.floor((y + reach) / CELL) + 1):
            for o in _grid.get((i, j), ()):
                if o.name in seen:
                    continue
                seen.add(o.name)
                x0, x1, y0, y1, _ = _box(o)
                if x0 - reach < x < x1 + reach and y0 - reach < y < y1 + reach:
                    out.append(o)
    return out


def _fit_wrapped():
    for o in [o for o in _scope if WRAP in o]:
        cx, cy = o[WRAP]
        nominal = o["fit_r"]
        support = Support(_standing(_near(cx, cy, 1.0), cx, cy))
        if not support:
            continue
        reach = max(.5, nominal * 2)
        mw, mwi = o.matrix_world, o.matrix_world.inverted()
        for v in o.data.vertices:
            p = mw @ v.co
            a = math.atan2(p.y - cy, p.x - cx)
            r = math.hypot(p.x - cx, p.y - cy)
            real = support.radius(cx, cy, p.z, a, reach)
            if real is None:
                continue
            r2 = max(real + .004, real + (r - nominal))
            v.co = mwi @ Vector((cx + math.cos(a) * r2, cy + math.sin(a) * r2, p.z))
        o.data.update()


def _fit_rests():
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
        tree = Support(_near(c.x, c.y, 1.0)).tree
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
    import time
    bpy.context.view_layer.update()
    _scope = list(coll.all_objects)
    solids = [o for o in _scope if _solid(o)]
    _boxes.clear()
    _index(solids)
    t = time.time()
    _fit_wrapped()
    _fit_rests()
    print("FIT: %d solids, %d tagged, %.1fs" % (len(solids), sum(1 for o in _scope if WRAP in o or REST in o), time.time() - t))
    # The tags were only for this pass: keep them out of the exported glTF extras.
    for o in _scope:
        for key in (WRAP, REST, "fit_r"):
            if key in o:
                del o[key]
    bpy.context.view_layer.update()
