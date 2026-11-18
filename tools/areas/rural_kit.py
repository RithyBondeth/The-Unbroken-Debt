"""Building kit for the village expansion's old farm buildings (Episode 1, November
2026): round posts cut from the forest, adze-hewn timbers, thick grey thatch with
ragged eaves and rotted holes, rattan lashings, split-bamboo walls, and library
scans set down on the ground. Geometry goes into shrine_craft.Batch, one mesh per
material. Textures are the CC0 Poly Haven photographs in art-source/library.

Blender axes: X east, Y north, Z up; metres. Run inside Blender.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

import khmer
from kit import LIB, library_material, plain

# ------------------------------------------------------------------ materials

_MATS = {}


def _lib(key, tex, tint=None, tile=None, backface=True):
    name = f"M_rk_{key}"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = library_material(tex, name, tint=tint, tile=tile)
    mat.use_backface_culling = backface
    return mat


def _plain(key, colour, **kw):
    """A plain material made once: reused by name (or its .001 copy) on re-runs."""
    name = f"M_rk_{key}"
    mat = bpy.data.materials.get(name)
    if mat is None:
        dup = next((m for m in bpy.data.materials if m.name.startswith(name + ".")), None)
        if dup is not None:
            dup.name = name
            return dup
        mat = plain(name, colour, **kw)
    return mat


def materials():
    """The kit's materials, made once per file (names start M_rk_)."""
    if _MATS:
        return _MATS
    _MATS.update({
        # Old grey thatch, gone dark with years of rain; the straw stack's newer straw.
        "thatch": _lib("thatch", "thatch_roof_angled", tint=(.78, .76, .70), tile=1.3, backface=False),
        "thatch_dark": _lib("thatch_dark", "thatch_roof_angled", tint=(.48, .47, .42), tile=1.1, backface=False),
        "straw": _lib("straw", "reed_roof_04", tint=(.42, .39, .33), tile=1.6, backface=False),
        # Timber: silver-grey weathered boards, older brown planks, rough bark.
        "planks": _lib("planks", "weathered_planks", tint=(.9, .88, .85), tile=2.0),
        "boards": _lib("boards", "old_planks_02", tile=2.0),
        "hewn": _lib("hewn", "weathered_brown_planks", tint=(.8, .76, .72), tile=1.4),
        "bark": _lib("bark", "bark_brown_02", tint=(.75, .72, .68), tile=1.0),
        "bamboo": _lib("bamboo", "bamboo_wall", tint=(.72, .66, .58), tile=1.6, backface=False),
        "mud": _lib("mud", "mud_forest", tile=2.0),
        "rope": _plain("rope", (.21, .17, .11), rough=.95),
        "rattan": _plain("rattan", (.30, .23, .14), rough=.85),
        "iron": _plain("iron", (.11, .08, .06), rough=.7, metal=.6),
        "dung": _plain("dung", (.07, .055, .035), rough=.75),
        "ash": _plain("ash", (.16, .15, .14), rough=1.0),
        "void": _plain("void", (.004, .004, .004), rough=1.0),
    })
    return _MATS


def tile_of(mat):
    return float(mat.get("tile", 1.0))


# ------------------------------------------------------------------ framing


def _axes(a, b, up=(0, 0, 1)):
    a, b = Vector(a), Vector(b)
    x = (b - a)
    length = x.length
    x.normalize()
    ref = Vector(up)
    if abs(x.dot(ref)) > .97:
        ref = Vector((1, 0, 0))
    y = ref.cross(x).normalized()
    z = x.cross(y).normalized()
    return a, x, y, z, length


# Library photos whose boards run up the image (grain along v), not across it.
GRAIN_V = {"M_rk_planks", "M_rk_boards", "M_rk_bamboo", "M_rk_bark", "M_rk_moss_wood"}


def timber(b, mat, a, c, w, d, rng, chamfer=.012, jitter=.004, twist=0.0, up=(0, 0, 1)):
    """A squared, adze-hewn timber from a to c, `w` wide (local y) and `d` deep
    (local z). The photo's grain runs along it, each timber cut from a different
    part of the texture; edges chamfered, faces a little out of true."""
    o, x, y, z, length = _axes(a, c, up)
    if twist:
        q = Matrix.Rotation(twist, 3, x)
        y, z = q @ y, q @ z
    tile = tile_of(mat)
    along_v = mat.name in GRAIN_V
    ou, ov = rng.uniform(0, 8), rng.uniform(0, 8)
    ch = min(chamfer, w * .3, d * .3)
    # Cross-section with chamfered corners (8 points), swept from end to end.
    hw, hd = w / 2, d / 2
    sec = [(hw - ch, -hd), (hw, -hd + ch), (hw, hd - ch), (hw - ch, hd), (-hw + ch, hd), (-hw, hd - ch), (-hw, -hd + ch), (-hw + ch, -hd)]
    rows = max(2, int(length / .5) + 1)
    verts, faces, uvs = [], [], []
    perim = [0.0]
    for p0, p1 in zip(sec, sec[1:] + sec[:1]):
        perim.append(perim[-1] + math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
    for i in range(rows):
        t = i / (rows - 1)
        for k in range(len(sec) + 1):
            sy, sz = sec[k % len(sec)]
            j = Vector(rng.normal(0, jitter, 3)) if jitter and 0 < i < rows - 1 else Vector((0, 0, 0))
            p = o + x * (length * t) + y * sy + z * sz + j
            verts.append(tuple(p))
            a_ = length * t / tile + ou
            c_ = perim[k] / tile + ov
            uvs.append((c_, a_) if along_v else (a_, c_))
    n = len(sec) + 1
    for i in range(rows - 1):
        for k in range(len(sec)):
            a0 = i * n + k
            faces.append((a0, a0 + 1, a0 + n + 1, a0 + n))
    b.add(mat, verts, faces, uvs, smooth=False)
    # End grain caps.
    for t, flip in ((0.0, True), (1.0, False)):
        cap = [tuple(o + x * (length * t) + y * sy + z * sz) for sy, sz in sec]
        cuv = [((sy + hw) / tile + ou, (sz + hd) / tile + ov) for sy, sz in sec]
        if flip:
            cap, cuv = cap[::-1], cuv[::-1]
        b.add(mat, cap, [tuple(range(len(sec)))], cuv, smooth=False)


def log(b, mat, a, c, r0, r1, rng, sides=9, bow=0.03, knots=.1, rows=None, tile=None):
    """A round pole or post cut from the forest: tapered, bowed, never quite round."""
    a, c = Vector(a), Vector(c)
    length = (c - a).length
    n = rows or max(3, int(length / .35) + 2)
    o, x, y, z, _ = _axes(a, c)
    phase = rng.uniform(0, 6.28, 3)
    pts, radii = [], []
    for i in range(n):
        t = i / (n - 1)
        off = y * math.sin(t * math.pi) * bow * length * math.cos(phase[0]) + z * math.sin(t * math.pi) * bow * length * math.sin(phase[0])
        pts.append(a + (c - a) * t + off)
        k = 1 + knots * (math.sin(t * 17 + phase[1]) * .5 + math.sin(t * 41 + phase[2]) * .3)
        radii.append((r0 + (r1 - r0) * t) * k)
    b.tube(mat, pts, radii, sides=sides, tile=tile or tile_of(mat), cap_end=True)


def lashing(b, mat, at, axis, r, turns=4, width=.05):
    """Rattan bound round a joint: a few flat turns about `axis`."""
    at, axis = Vector(at), Vector(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < .9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    for k in range(turns):
        off = axis * (width * (k / max(1, turns - 1) - .5))
        ring = [at + off + (u * math.cos(t) + v * math.sin(t)) * (r + .006) for t in np.linspace(0, math.tau, 13)]
        b.tube(mat, ring, .0055, sides=4, tile=.2)


# ------------------------------------------------------------------ thatch


def _noise2(u, v, seed):
    return (math.sin(u * 1.7 + seed[0]) * math.sin(v * 2.3 + seed[1]) + .6 * math.sin(u * 4.1 - v * 3.3 + seed[2])
            + .35 * math.sin(u * 9.3 + v * 7.1 + seed[3]))


def thatch(b, mat, ridge0, ridge1, eave0, eave1, rng, thick=.16, sag=.05, hole=None, ragged=.14,
           droop=None, under=None, course=.55, lip=.012, cell=(.13, .1), rot=0.0, strands=1.0, strand_mat=None,
           extent=None):
    """A thick thatch slope from the ridge line (ridge0-ridge1) down to the eave
    (eave0-eave1), laid in overlapping courses: each course's butt end stands
    proud of the one below, so the slope reads in steps of straw. The straw runs
    down the slope; the eave and every hole show the thatch's thickness with
    ragged straw ends. `rot` (0-1) eats organic holes where the thatch has rotted;
    `hole(u, v)` drops more (u along the ridge, v down the slope, 0-1);
    `droop(u, v)` adds a world-space offset (a slumped section); `under` is the
    material seen from inside; `extent(v)` -> (u0, u1) tears the slope off along a
    smooth ragged line instead of cell by cell."""
    r0, r1, e0, e1 = (Vector(p) for p in (ridge0, ridge1, eave0, eave1))
    along = (r1 - r0).length
    down = ((e0 - r0).length + (e1 - r1).length) / 2
    nu = max(4, int(along / cell[0]))
    courses = max(1, round(down / course))
    per = max(2, round(down / courses / cell[1]))
    # Rows: `per` within each course, plus a sliver at each butt for the step.
    vs = []
    for c in range(courses):
        for k in range(per):
            vs.append((c + k / per) / courses)
        vs.append((c + 1 - .015) / courses)
    vs.append(1.0)
    nv = len(vs) - 1
    n = (r1 - r0).cross(e0 - r0).normalized()
    if n.z < 0:
        n = -n
    seed = rng.uniform(0, 100, 8)

    def lift(v):
        """Each course rises towards its butt (sawtooth): the step between courses."""
        f = (v * courses) % 1.0
        return lip * f

    def surf(u, v):
        if extent:
            a0, a1 = extent(v)
            u = a0 + (a1 - a0) * u
        p = (r0 + (r1 - r0) * u) * (1 - v) + (e0 + (e1 - e0) * u) * v
        um, vm = u * along, v * down
        p = p - n * (sag * math.sin(math.pi * v) * (.6 + .4 * math.sin(um * 3.1 + seed[0]) ** 2))
        p = p + n * (.018 * _noise2(um * .9, vm * .9, seed[:4]) + lift(v)
                     + .006 * math.sin(um * 6.3 + math.floor(v * courses) * 2.1)
                     + .008 * math.sin(um * 17.0 + vm * 3 + seed[6]))
        if droop:
            p = p + Vector(droop(u, v))
        return p

    def rotten(u, v):
        if hole and hole(u, v):
            return True
        if not rot:
            return False
        um, vm = u * along, v * down
        # Rot eats round, soft-edged holes (a metre or less), most near the eave.
        n = _noise2(um * .95, vm * .95, seed[4:]) + .12 * math.sin(um * 7 + vm * 5 + seed[5])
        return n + .5 * v > 2.35 - 1.6 * rot

    keep = [[not rotten((i + .5) / nu, (vs[j] + vs[j + 1]) / 2) for i in range(nu)] for j in range(nv)]
    tile = tile_of(mat)
    reach = [ragged * (rng.random() ** 1.5) for _ in range(nu + 1)]
    # Vertices on a hole's edge are nudged in the slope's plane so no edge runs straight.
    du = (r1 - r0).normalized()
    dv = ((e0 + e1) / 2 - (r0 + r1) / 2).normalized()

    def edge_vertex(i, j):
        cells = [(ii, jj) for ii in (i - 1, i) for jj in (j - 1, j) if 0 <= ii < nu and 0 <= jj < nv]
        return any(not keep[jj][ii] for ii, jj in cells) or i in (0, nu) or j == nv

    def grid_pt(i, j, top=True):
        u, v = i / nu, vs[j]
        p = surf(u, v)
        if j == nv:
            p = p + (surf(u, 1.0) - surf(u, vs[nv - 1])).normalized() * reach[i]
        if edge_vertex(i, j) and 0 < j:
            h = hash((i, j)) % 1000 / 1000.0
            p = p + du * (h - .5) * cell[0] * .45 + dv * ((hash((j, i, 7)) % 1000) / 1000.0 - .5) * cell[1] * .5
        if not top:
            p = p - n * thick * (1 - .45 * (j == nv))
        return p

    top = [[grid_pt(i, j) for i in range(nu + 1)] for j in range(nv + 1)]
    bot = [[grid_pt(i, j, False) for i in range(nu + 1)] for j in range(nv + 1)]
    under = under or mat
    jitter_u = [rng.uniform(0, 4) for _ in range(courses + 1)]

    def uv(i, j):
        c = min(courses - 1, int(vs[j] * courses - 1e-6)) if j < nv else courses - 1
        return ((i / nu) * along / tile + jitter_u[c], vs[j] * down / tile)

    for j in range(nv):
        for i in range(nu):
            if not keep[j][i]:
                continue
            b.add(mat, [top[j][i], top[j + 1][i], top[j + 1][i + 1], top[j][i + 1]], [(0, 1, 2, 3)],
                  [uv(i, j), uv(i, j + 1), uv(i + 1, j + 1), uv(i + 1, j)])
            b.add(under, [bot[j][i], bot[j][i + 1], bot[j + 1][i + 1], bot[j + 1][i]], [(0, 1, 2, 3)],
                  [uv(i, j), uv(i + 1, j), uv(i + 1, j + 1), uv(i, j + 1)])
            for di, dj, a, c in ((0, 1, (i, j + 1), (i + 1, j + 1)), (0, -1, (i + 1, j), (i, j)),
                                 (1, 0, (i + 1, j + 1), (i + 1, j)), (-1, 0, (i, j), (i, j + 1))):
                ii, jj = i + di, j + dj
                if 0 <= ii < nu and 0 <= jj < nv and keep[jj][ii]:
                    continue
                ta, tc = top[a[1]][a[0]], top[c[1]][c[0]]
                ba, bc = bot[a[1]][a[0]], bot[c[1]][c[0]]
                el = (tc - ta).length / tile
                # Straw ends: strands run through the thickness.
                b.add(mat, [ta, tc, bc, ba], [(0, 1, 2, 3)],
                      [(0, 0), (el, 0), (el, thick * 3 / tile), (0, thick * 3 / tile)], smooth=False)
                # Loose straws hanging from the cut edge.
                if strands and rng.random() < strands:
                    outward = ((ta + tc) / 2 - (top[j][i] + top[j + 1][i + 1]) / 2)
                    outward = outward - n * outward.dot(n)
                    _straws(b, strand_mat or mat, ta, tc, ba, bc, outward.normalized(), n, rng, tile,
                            hang=dj == 1)
    return n


def _straws(b, mat, ta, tc, ba, bc, outward, n, rng, tile, hang=True, count=None):
    """A few loose straws along a cut edge of thatch, drooping (eave) or splayed (holes)."""
    count = count or int(rng.integers(2, 5))
    for _ in range(count):
        t = rng.random()
        k = rng.uniform(.15, .85)
        root = (ta + (tc - ta) * t) * (1 - k) + (ba + (bc - ba) * t) * k
        length = rng.uniform(.12, .32) if hang else rng.uniform(.06, .16)
        d = outward * rng.uniform(.4, 1.0) - n * rng.uniform(.3, 1.2 if hang else .3) + Vector(rng.normal(0, .25, 3))
        d.normalize()
        side = d.cross(n)
        if side.length < 1e-4:
            side = d.cross(Vector((0, 0, 1)))
        side = side.normalized() * rng.uniform(.004, .009)
        mid = root + d * length * .5 - n * length * .1 * hang
        tip = root + d * length - n * length * .25 * hang
        u0 = rng.uniform(0, 3)
        b.add(mat, [root - side, root + side, mid + side * .7, mid - side * .7], [(0, 1, 2, 3)],
              [(u0, 0), (u0 + .01, 0), (u0 + .01, length / 2 / tile), (u0, length / 2 / tile)], smooth=False)
        b.add(mat, [mid - side * .7, mid + side * .7, tip + side * .2, tip - side * .2], [(0, 1, 2, 3)],
              [(u0, length / 2 / tile), (u0 + .01, length / 2 / tile), (u0 + .01, length / tile), (u0, length / tile)],
              smooth=False)


def ridge_roll(b, mat, a, c, r, rng):
    """The bundled straw roll along a thatched ridge."""
    pts = [Vector(a) + (Vector(c) - Vector(a)) * t + Vector((0, 0, .02 * math.sin(t * 13 + rng.uniform(0, 6))))
           for t in np.linspace(0, 1, 14)]
    b.tube(mat, pts, [r * (1 + .12 * math.sin(i * 1.7)) for i in range(len(pts))], sides=8, tile=tile_of(mat))


# ------------------------------------------------------------------ walls


def slat_panel(b, mat, frame_mat, origin, along, up, width, height, rng, gaps=None, frame=True, sag=0.0):
    """A wall panel of split bamboo slats (vertical) in a light frame: `origin` is
    its lower-left corner, `along`/`up` unit axes. `gaps(t)` -> True drops slats."""
    o, ax, up = Vector(origin), Vector(along).normalized(), Vector(up).normalized()
    nrm = ax.cross(up).normalized()
    m = Matrix.Identity(4)
    for r in range(3):
        m[r][0], m[r][1], m[r][2] = ax[r], up[r], nrm[r]
    tile = tile_of(mat)
    # The slats as one thin sheet with the bamboo texture, broken where slats are gone.
    n = max(2, int(width / .09))
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        if gaps and gaps((t0 + t1) / 2):
            continue
        h = height * (1 - (.25 * rng.random() if gaps and gaps(t0 + .5 / n + .05) else 0))
        x0, x1 = width * t0 + .004, width * t1 - .004
        dz = sag * math.sin(math.pi * (t0 + t1) / 2)
        p = [o + ax * x0 + up * (0 - dz) + nrm * .0, o + ax * x1 + up * (0 - dz), o + ax * x1 + up * h, o + ax * x0 + up * h]
        jit = nrm * rng.normal(0, .006)
        b.add(mat, [q + jit for q in p], [(0, 1, 2, 3)],
              [(x0 / tile, 0), (x1 / tile, 0), (x1 / tile, h / tile), (x0 / tile, h / tile)], smooth=False)
        b.add(mat, [q + jit - nrm * .012 for q in reversed(p)], [(0, 1, 2, 3)],
              [(x0 / tile, h / tile), (x1 / tile, h / tile), (x1 / tile, 0), (x0 / tile, 0)], smooth=False)
    if frame:
        for z in (.05, height * .5, height - .04):
            timber(b, frame_mat, o + up * z + nrm * .02, o + ax * width + up * z + nrm * .02, .04, .025, rng)


# ------------------------------------------------------------------ scans and models


def place_model(coll, model, x, y, ground, rot=0.0, scale=1.0, sink=0.01, scan=False, tilt=(0.0, 0.0), name=None, z=None,
                height=None):
    """A library model or scan, its lowest point set on the ground (or at `z`);
    `height` scales it to that height (m) as it stands."""
    if scan:
        from house_rooms import _scan_proto
        model = _scan_proto(model)
    parent = khmer.place(coll, model, (x, y, 0), math.degrees(rot), scale, name=name)
    parent.rotation_euler = (tilt[0], tilt[1], rot)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in parent.children_recursive if o.type == "MESH" for v in o.data.vertices]
    if height:
        k = height / max(1e-6, max(p.z for p in pts) - min(p.z for p in pts))
        parent.scale = parent.scale * k
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ v.co for o in parent.children_recursive if o.type == "MESH" for v in o.data.vertices]
    low = min(p.z for p in pts)
    base = ground(x, y) if z is None else z
    parent.location.z += base - low - sink
    return parent


def ground_props_scan_ok():
    return os.path.isdir(os.path.join(LIB, "scans"))
