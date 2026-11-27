"""Episode 1's well inside the south gate, built for close looks (the user, Nov 26, 2026: "fix
the well for more detailed, and realistic. Not just like a cartoon like this").

A village well (អណ្ដូង) as they are dug in the countryside: a round curb of fired bricks
laid course by course, rendered with lime that has fallen away in patches, a coping of bricks
set on edge along its top; inside, the brick shaft down to dark water. Round it the yard's mud,
trodden and wet, with the old brick paving sunk and half gone in it and bricks edging the
spill's way out. Beside it the well
sweep: a forked tree trunk planted in the ground, a bamboo pole pivoting on a hardwood pin
in its fork, rocks lashed to its butt for a counterweight, and from its tip a slender rod
hanging to the wooden bucket. A clay jar, a wooden bowl on the lip, a low stool.

Blender space, metres. `build(coll, ground)` deletes the old well (well_*, col_well*) and
builds this one; village_review.well calls it in the full rebuild, build-village-well.py
runs it alone on the built village file.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "..", "travel")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

WELL = (9.5, -33.0)          # the curb's centre (village_review.WELL)
R_OUT, R_IN, HEIGHT = 0.8, 0.56, 0.66
SEED = 2611


def materials():
    from kit import library_material, plain

    m = {
        "brick": library_material("red_brick", "M_well_brick", tint=(0.5, 0.4, 0.35), tile=0.7),
        "plaster": library_material("white_plaster_rough_01", "M_well_plaster", tint=(0.58, 0.56, 0.5), tile=0.9),
        "cap": library_material("concrete_floor_worn_001", "M_well_cap", tint=(0.55, 0.52, 0.47), tile=0.6),
        "laterite": library_material("red_laterite_soil_stones", "M_well_laterite", tint=(0.5, 0.38, 0.3), tile=0.4),
        "mud": library_material("muddy_tracks", "M_well_mud", tint=(0.55, 0.49, 0.43), tile=1.6),
        "brick_old": library_material("red_brick", "M_well_brick_old", tint=(0.27, 0.215, 0.19), tile=0.7),
        "bark": library_material("bark_brown_02", "M_well_bark", tint=(0.55, 0.49, 0.43), tile=0.55),
        "wood": library_material("weathered_planks", "M_well_wood", tint=(0.46, 0.38, 0.3), tile=0.6),
        "rope": library_material("rough_linen", "M_well_rope", tint=(0.42, 0.31, 0.19), tile=0.12),
        "moss": library_material("moss_wood", "M_well_moss", tint=(0.3, 0.32, 0.24), tile=0.5),
        "bamboo": library_material("bamboo_wall", "M_well_bamboo", tint=(0.8, 0.72, 0.55), tile=1.8),
        "water": plain("M_well_water", (0.012, 0.016, 0.015), rough=0.02),
        "slime": plain("M_well_slime", (0.05, 0.075, 0.04), rough=0.35),
        "iron": plain("M_well_iron", (0.08, 0.07, 0.06), rough=0.55, metal=0.7),
        "cloth": plain("M_well_cloth_red", (0.42, 0.04, 0.035), rough=0.85),
    }
    for k in ("cloth",):
        m[k].use_backface_culling = False
    import village_road as VR

    VR._vertex_colour_multiply(m["mud"])
    return m


def clear_old():
    gone = [o for o in bpy.data.objects if o.name.startswith(("well_", "col_well"))]
    for o in gone:
        bpy.data.objects.remove(o, do_unlink=True)
    return len(gone)


class Parts:
    """One bmesh per material; `emit` makes one object each (world UVs on the tiled ones,
    the bamboo keeps the UVs laid along its culm)."""

    def __init__(self, m):
        self.m = m
        self.b = {}

    def __getitem__(self, k):
        if k not in self.b:
            self.b[k] = bmesh.new()
            self.b[k].loops.layers.uv.verify()
        return self.b[k]

    def emit(self, coll, own_uv=("bamboo",), smooth=("bamboo", "bark", "rope", "water", "slime", "iron", "cap")):
        from kit import world_uvs

        out = []
        for k, bm in self.b.items():
            if not len(bm.faces):
                continue
            me = bpy.data.meshes.new(f"well_{k}")
            bm.to_mesh(me)
            bm.free()
            if me.uv_layers:
                me.uv_layers[0].name = "UVMap"
            if k in smooth:
                for p in me.polygons:
                    p.use_smooth = True
            me.materials.append(self.m[k])
            o = bpy.data.objects.new(f"well_{k}", me)
            coll.objects.link(o)
            if k not in own_uv and self.m[k].get("tile", 0):
                for l in list(me.uv_layers):
                    me.uv_layers.remove(l)
                world_uvs(o)
            out.append(o)
        return out


def _ring_noise(a, h, seed):
    return 0.012 * math.sin(3 * a + seed) + 0.007 * math.sin(7 * a + 2 * seed) + 0.004 * math.sin(11 * a + 0.7 * h * 9)


def curb(P, x, y, g, rng):
    """Bricks course by course (headers, staggered), the lime render over them with its
    fallen patches, the concrete cap, the shaft, the water."""
    import shop_goods as G

    seed = float(rng.uniform(0, 6.28))
    course_h, n_courses = 0.075, int(HEIGHT / 0.075)
    for c in range(n_courses):
        z = g - 0.05 + c * course_h + course_h / 2
        r_mid = (R_OUT + R_IN) / 2
        n = int(2 * math.pi * r_mid / 0.118)
        for k in range(n):
            a = (k + 0.5 * (c % 2)) / n * math.tau
            jit = rng.normal(0, 0.003)
            M = Matrix.Translation((x + math.cos(a) * (r_mid + jit), y + math.sin(a) * (r_mid + jit), z)) @ Matrix.Rotation(a, 4, "Z")
            G.boxm(P["brick"], M, (0, 0, 0), (R_OUT - R_IN - 0.01 + rng.normal(0, 0.004), 0.104, 0.066), bevel=0.006, segs=1)
    # The render: a skin a centimetre proud of the bricks, gone where the lime has fallen.
    na, nh = 72, 10
    rows = []
    for j in range(nh + 1):
        h = j / nh
        z = g - 0.02 + h * (HEIGHT - 0.04)
        row = []
        for i in range(na):
            a = i / na * math.tau
            r = R_OUT + 0.012 + _ring_noise(a, h, seed)
            row.append(P["plaster"].verts.new((x + math.cos(a) * r, y + math.sin(a) * r, z)))
        rows.append(row)
    for j in range(nh):
        for i in range(na):
            a, h = (i + 0.5) / na * math.tau, (j + 0.5) / nh
            # Fallen away near the ground (rising damp) and in a few big flakes higher up.
            flake = math.sin(a * 3 + seed) * math.sin(h * 5 + seed * 0.7) + 0.6 * math.sin(a * 7 - seed) * math.cos(h * 9)
            if h < 0.18 + 0.12 * math.sin(a * 4 + seed) or flake > 0.95:
                continue
            P["plaster"].faces.new((rows[j][i], rows[j][(i + 1) % na], rows[j + 1][(i + 1) % na], rows[j + 1][i]))
    # Moss in the shade at the foot, where the splash keeps it damp.
    mrows = []
    for j in range(3):
        z = g - 0.03 + j * 0.06
        mrows.append([P["moss"].verts.new((x + math.cos(i / na * math.tau) * (R_OUT + 0.02 - 0.004 * j),
                                            y + math.sin(i / na * math.tau) * (R_OUT + 0.02 - 0.004 * j), z)) for i in range(na)])
    for j in range(2):
        for i in range(na):
            if math.sin(i / na * math.tau * 2 + seed) < -0.3:
                continue
            P["moss"].faces.new((mrows[j][i], mrows[j][(i + 1) % na], mrows[j + 1][(i + 1) % na], mrows[j + 1][i]))
    # The coping: a course of bricks set on edge across the wall's top (a rounded skim of
    # mortar there read as a tyre), the odd one cracked or sunk, mortar between them.
    top = g - 0.05 + n_courses * course_h
    r_mid = (R_OUT + R_IN) / 2
    n = int(2 * math.pi * r_mid / 0.068)
    for k in range(n):
        a = k / n * math.tau
        h = 0.105 - (0.015 if rng.random() < 0.06 else 0.0)
        M = Matrix.Translation((x + math.cos(a) * r_mid, y + math.sin(a) * r_mid, top + h / 2 + 0.006)) @ \
            Matrix.Rotation(a + rng.normal(0, 0.012), 4, "Z") @ Matrix.Rotation(rng.normal(0, 0.02), 4, "X")
        G.boxm(P["brick"], M, (0, 0, 0), (R_OUT - R_IN + 0.02 + rng.normal(0, 0.004), 0.058, h), bevel=0.007, segs=1)
    G.lathe(P["cap"], [(R_OUT + 0.012, top), (R_OUT + 0.012, top + 0.095), (R_IN - 0.012, top + 0.095), (R_IN - 0.012, top)],
            Matrix.Translation((x, y, 0)), segs=64, cap_bottom=False)
    top += 0.105
    # The shaft: bricks inside (the render never reached down here), slime at the waterline.
    G.lathe(P["brick"], [(R_IN, top - 0.11), (R_IN, g - 2.2)], Matrix.Translation((x, y, 0)), segs=48, cap_bottom=False)
    # The water stands high after the rains, just above the yard (the forest floor runs on
    # under the curb, so lower down it would show through as earth).
    G.lathe(P["slime"], [(R_IN - 0.004, g + 0.03), (R_IN - 0.004, g + 0.2)], Matrix.Translation((x, y, 0)), segs=48, cap_bottom=False)
    G.lathe(P["water"], [(R_IN, g + 0.04), (0.0, g + 0.04)], Matrix.Translation((x, y, 0)), segs=48, cap_bottom=False)
    return top


def apron(P, coll, m, x, y, ground, rng):
    """The yard round the well: mud trodden hard and kept dark by every bucket spilled, raised a
    little round the curb and running out under the yard's own earth along a ragged edge (a
    ring of bright laterite slabs here read as toy tiles, the user, Nov 26, 2026). Set in it the
    old brick paving, broken, sunk and half gone; bricks edging the spill's way out to the
    south-east; laterite pebbles trodden in. Returns the yard's height at a point, for what
    stands on it."""
    import shop_goods as G
    import village_road as VR
    from kit import world_uvs

    exact = ground       # the terrain as the game draws it (village_expansion.Ground)
    seed = float(rng.uniform(0, 6.28))
    drain = math.atan2(-0.83, 0.55)

    def gap(a, b):
        return (a - b + math.pi) % math.tau - math.pi

    def edge(a):
        return (1.68 + 0.2 * math.sin(2 * a + seed) + 0.1 * math.sin(5 * a - seed) + 0.05 * math.sin(9 * a + 2 * seed)
                + 0.75 * math.exp(-((gap(a, drain) / 0.32) ** 2)))

    def lift(r, a):
        """Height over the forest floor: 5 cm against the curb, 3.5 cm out to the edge (never
        level with it, where the game can't tell which is in front), then well under it."""
        e = edge(a)
        if r > e:
            return -0.12
        wob = 0.005 * math.sin(r * 23 + a * 7 + seed) * math.sin(a * 13 - r * 9)
        return 0.035 + 0.02 * (1 - VR.smoothstep(R_OUT, R_OUT + 0.7, r)) + wob

    def yard(px, py):
        r, a = math.hypot(px - x, py - y), math.atan2(py - y, px - x)
        return exact(px, py) + max(0.0, lift(r, a))

    na, nr = 96, 22
    verts, cols, faces = [], [], []
    for i in range(na):
        a = i / na * math.tau
        e = edge(a)
        for j in range(nr):
            t = j / (nr - 1)
            r = R_OUT + 0.004 + (e + 0.22 - R_OUT) * (t ** 0.85)
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            verts.append((px, py, exact(px, py) + lift(r, a)))
            # Dark and wet against the curb and down the spill's way, patchy elsewhere.
            k = 0.92 - 0.12 * (0.5 + 0.5 * math.sin(px * 3.1 + py * 2.3) * math.sin(px * 1.3 - py * 4.1))
            k *= 1 - 0.38 * (1 - VR.smoothstep(R_OUT, R_OUT + 0.55, r))
            k *= 1 - 0.32 * math.exp(-((gap(a, drain) / 0.13) ** 2)) * VR.smoothstep(R_OUT, R_OUT + 0.4, r)
            cols.append((k, k * 0.97, k * 0.93))
    for i in range(na):
        for j in range(nr - 1):
            q = (i * nr + j, ((i + 1) % na) * nr + j, ((i + 1) % na) * nr + j + 1, i * nr + j + 1)
            if all(verts[v][2] < exact(verts[v][0], verts[v][1]) - 0.05 for v in q):
                continue
            faces.append(q)
    me = bpy.data.meshes.new("well_apron")
    me.from_pydata(verts, [], faces)
    me.materials.append(m["mud"])
    col = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            col.data[li].color = (*cols[me.loops[li].vertex_index], 1.0)
    me.color_attributes.active_color = col
    me.color_attributes.render_color_index = list(me.color_attributes).index(col)
    me.update()
    o = bpy.data.objects.new("well_apron", me)
    coll.objects.link(o)
    world_uvs(o)

    def brick(cx, cy, yaw, length, proud):
        """A brick laid flat, its top `proud` m above the yard, the rest in the mud."""
        top = yard(cx, cy) + proud
        M = (Matrix.Translation((cx, cy, top - 0.03)) @ Matrix.Rotation(yaw, 4, "Z") @
             Matrix.Rotation(float(rng.normal(0, 0.035)), 4, "X") @ Matrix.Rotation(float(rng.normal(0, 0.035)), 4, "Y"))
        G.boxm(P["brick_old"], M, (0, 0, 0), (length, 0.105 + float(rng.normal(0, 0.003)), 0.06), bevel=0.009, segs=1)

    # The old paving: two courses of bricks round the curb's foot, laid radially; a third are
    # gone, some broken in half, the rest sunk unevenly where the mud has worked under them.
    for ring_r, n, gone in ((R_OUT + 0.13, 30, 0.42), (R_OUT + 0.36, 38, 0.62)):
        for k in range(n):
            if rng.random() < gone:
                continue
            a = (k + 0.5 * (ring_r > R_OUT + 0.2) + rng.normal(0, 0.08)) / n * math.tau
            length = 0.215 if rng.random() > 0.35 else float(rng.uniform(0.07, 0.15))
            r = ring_r + float(rng.normal(0, 0.018))
            brick(x + math.cos(a) * r, y + math.sin(a) * r, a + float(rng.normal(0, 0.09)), length,
                  float(rng.uniform(-0.014, 0.007)))
    # The spill's way: bricks laid lengthwise either side of a dark runnel, half of them gone.
    d = Vector((math.cos(drain), math.sin(drain)))
    nrm = Vector((-d.y, d.x))
    for k in range(8):
        r = R_OUT + 0.62 + k * 0.23
        for side in (-1, 1):
            if rng.random() < 0.45:
                continue
            p = Vector((x, y)) + d * (r + float(rng.normal(0, 0.03))) + nrm * side * (0.15 + float(rng.normal(0, 0.02)))
            brick(p.x, p.y, drain + float(rng.normal(0, 0.1)), 0.215 if rng.random() > 0.3 else float(rng.uniform(0.08, 0.14)),
                  float(rng.uniform(-0.012, 0.006)))
    # Laterite pebbles trodden in.
    for _k in range(70):
        a = float(rng.uniform(0, math.tau))
        r = float(rng.uniform(R_OUT + 0.45, max(R_OUT + 0.5, edge(a) - 0.1)))
        cx, cy = x + math.cos(a) * r, y + math.sin(a) * r
        s_ = float(rng.uniform(0.018, 0.05))
        M = Matrix.Translation((cx, cy, yard(cx, cy) - 0.25 * s_)) @ Matrix.Rotation(float(rng.uniform(0, 6.28)), 4, "Z")
        G.boxm(P["laterite"], M, (0, 0, 0), (s_ * 1.2, s_, s_ * 0.6), bevel=s_ * 0.35, segs=2)
    return yard


def forked_post(P, px, py, pg, rng):
    """A trunk with a natural fork, planted: its bark, a swelling at the root, the two
    limbs cut short above the fork. Returns the fork's height."""
    import shop_goods as G

    fork_z = pg + 2.05
    pts, rad = [], []
    for k in range(9):
        t = k / 8
        pts.append((px + 0.03 * math.sin(t * 2.2) + rng.normal(0, 0.004), py + 0.02 * math.sin(t * 3.1), pg - 0.45 + t * (fork_z - pg + 0.3)))
        rad.append(0.12 - 0.04 * t + (0.025 if t < 0.15 else 0.0) + rng.normal(0, 0.003))
    _tube_var(P["bark"], pts, rad, 12)
    base = Vector(pts[-2])
    for sgn in (-1, 1):
        limb = [tuple(base), tuple(base + Vector((0.02 * sgn, 0.1 * sgn, 0.22))), tuple(base + Vector((0.03 * sgn, 0.16 * sgn, 0.42)))]
        _tube_var(P["bark"], limb, [0.07, 0.06, 0.05], 10)
        G.lathe(P["wood"], [(0.0, 0.0), (0.05, 0.0)], Matrix.Translation(limb[-1]) @ Matrix.Rotation(sgn * 0.35, 4, "X"), segs=10,
                cap_bottom=False)
    return fork_z + 0.18


def _tube_var(bm, pts, rad, segs):
    """A tube through pts with a radius per point (closed ends)."""
    pts = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        u = d.orthogonal().normalized()
        v = d.cross(u)
        rings.append([bm.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * rad[i]) for a in (k / segs * math.tau for k in range(segs))])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs):
            bm.faces.new((a[k], a[(k + 1) % segs], b[(k + 1) % segs], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


def bamboo_culm(bm, p0, p1, r0, r1, sag=0.0, segs=12, strip=0.0):
    """A bamboo culm from p0 (butt) to p1 (tip): tapering, sagging a little, a swelling ring
    at each node; its UVs laid along one cane of the bamboo texture so the grain and the
    nodes run the length of the pole."""
    uv = bm.loops.layers.uv.verify()
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    d = (p1 - p0).normalized()
    side = d.orthogonal().normalized()
    up = Vector((0, 0, 1))
    n = max(8, int(L / 0.05))
    nodes = []
    s = 0.0
    while s < L:
        s += 0.3 + 0.08 * math.sin(s * 3.0)
        nodes.append(s)
    rings, vs = [], []
    for i in range(n + 1):
        t = i / n
        p = p0 + d * L * t - up * sag * math.sin(math.pi * t)
        r = r0 + (r1 - r0) * t
        dist = min((abs(L * t - q) for q in nodes), default=1.0)
        r *= 1.0 + 0.09 * max(0.0, 1.0 - dist / 0.02)
        u_ = d.cross(side).normalized()
        rings.append([bm.verts.new(p + (side * math.cos(a) + u_ * math.sin(a)) * r) for a in (k / segs * math.tau for k in range(segs))])
        vs.append(L * t / 1.8)
    for j in range(n):
        for k in range(segs):
            f = bm.faces.new((rings[j][k], rings[j][(k + 1) % segs], rings[j + 1][(k + 1) % segs], rings[j + 1][k]))
            for loop, (kk, jj) in zip(f.loops, ((k, j), (k + 1, j), (k + 1, j + 1), (k, j + 1))):
                loop[uv].uv = (strip + 0.024 * kk / segs, vs[jj])
    for ring in (rings[0], rings[-1]):
        f = bm.faces.new(ring if ring is rings[-1] else list(reversed(ring)))
        for loop in f.loops:
            loop[uv].uv = (strip + 0.012, 0.0)


def sweep(P, coll, x, y, ground, rng, lip):
    """The well sweep: post, pole on its pin, the counterweight, the rod and the bucket."""
    import shop_goods as G
    import shop_interiors as SI

    px, py = x + 1.55, y - 0.45
    pg = ground(px, py)
    pivot_z = forked_post(P, px, py, pg, rng)
    pivot = Vector((px + 0.03, py, pivot_z))
    # The pole: its tip high over the well (the counterweight holds it up at rest).
    tip = Vector((x + 0.12, y + 0.08, pivot_z + 0.95))
    d = (tip - pivot).normalized()
    butt = pivot - d * 1.6
    bamboo_culm(P["bamboo"], butt, tip, 0.052, 0.03, sag=0.05, segs=14, strip=0.31)
    # The pin through the fork, rattan lashings either side of it.
    G.cylm(P["wood"], Matrix.Identity(4), pivot + Vector((0, -0.16, 0)), pivot + Vector((0, 0.16, 0)), 0.016, segs=8)
    for off in (-0.09, 0.09):
        c = pivot + d * off
        for k in range(6):
            G.torus(P["rope"], Matrix.Identity(4), tuple(c + d * (k * 0.011)), tuple(d), 0.056, 0.0045, n=14, m=4)
    # The counterweight: a rattan basket of stones hung on three coir lines from the butt.
    hang = butt + d * 0.12
    basket = SI.scan("basket_round.glb", 3500)
    bz = hang.z - 0.42
    if basket:
        SI.place(coll, basket, Matrix.Translation((hang.x, hang.y, bz)) @ Matrix.Scale(1.05, 4), "well_counterweight_basket")
    for k in range(3):
        a = k * math.tau / 3 + 0.3
        foot = Vector((hang.x + math.cos(a) * 0.17, hang.y + math.sin(a) * 0.17, bz + 0.15))
        G.cylm(P["rope"], Matrix.Identity(4), tuple(hang - Vector((0, 0, 0.04))), tuple(foot), 0.006, segs=5)
    for k in range(4):
        G.torus(P["rope"], Matrix.Identity(4), tuple(hang + d * (k * 0.012 - 0.02)), tuple(d), 0.058, 0.005, n=14, m=4)
    for k in range(11):
        a, r = rng.uniform(0, 6.28), 0.12 * math.sqrt(rng.uniform(0, 1))
        sz = (rng.uniform(0.07, 0.12), rng.uniform(0.06, 0.1), rng.uniform(0.05, 0.08))
        M = Matrix.Translation((hang.x + math.cos(a) * r, hang.y + math.sin(a) * r, bz + 0.05 + sz[2] / 2 + (0.05 if k > 6 else 0))) @ \
            Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(rng.uniform(-0.3, 0.3), 4, "X")
        G.boxm(P["laterite"], M, (0, 0, 0), sz, bevel=0.022, segs=2)
    # The rod: a thin cane hung from the tip on a coir loop, the bucket's bail on its hook.
    rod_top = tip + Vector((0.0, 0.0, -0.03))
    bucket_rim = lip + 0.38
    rod_bot = Vector((tip.x, tip.y, bucket_rim + 0.32))
    G.torus(P["rope"], Matrix.Identity(4), tuple(tip), tuple(d.cross(Vector((0, 0, 1))).normalized()), 0.04, 0.006, n=12, m=4)
    bamboo_culm(P["bamboo"], rod_top, rod_bot, 0.017, 0.015, segs=8, strip=0.62)
    G.tube(P["iron"], Matrix.Identity(4), [tuple(rod_bot), tuple(rod_bot + Vector((0, 0, -0.08))), tuple(rod_bot + Vector((0.03, 0, -0.11))),
                                           tuple(rod_bot + Vector((0.04, 0, -0.08)))], 0.005, segs=6)
    bucket = SI.ph("wooden_bucket_01", 5000)
    if bucket:
        dims = bucket[0].dimensions
        s = 0.3 / max(dims.x, dims.y)
        SI.place(coll, bucket, Matrix.Translation((tip.x - 0.02, tip.y, rod_bot.z - 0.1 - dims.z * s)) @ Matrix.Rotation(0.5, 4, "Z") @
                 Matrix.Scale(s, 4), "well_bucket")
    # A strip of red cloth knotted round the post, as on any post a spirit is asked to keep.
    for k in range(5):
        zz = pg + 1.05 + k * 0.016
        G.tube(P["cloth"], Matrix.Identity(4), [(px + 0.112 * math.cos(a), py + 0.112 * math.sin(a), zz + 0.003 * a)
                                                for a in np.linspace(0, math.tau, 13)], 0.007, segs=4)
    G.tube(P["cloth"], Matrix.Identity(4), [(px + 0.11, py, pg + 1.09), (px + 0.16, py + 0.03, pg + 0.95), (px + 0.15, py + 0.06, pg + 0.8)],
           0.01, segs=4)
    return px, py, pg, pivot_z


def extras(P, coll, x, y, yard, lip, rng):
    """What stands round a well: a glazed jar for the day's water, a bowl on the lip, a stool
    (on the yard's trodden mud, `yard(x, y)` its height)."""
    import shop_interiors as SI

    jar = SI.scan("jar_handles.glb", 3500)
    jx, jy = x - 1.2, y + 0.75
    if jar:
        SI.place(coll, jar, Matrix.Translation((jx, jy, yard(jx, jy) - 0.02)) @ Matrix.Rotation(1.2, 4, "Z") @ Matrix.Scale(1.35, 4),
                 "well_jar")
    bowl = SI.ph("wooden_bowl_01", 2000)
    if bowl:
        dims = bowl[0].dimensions
        a = 2.4
        SI.place(coll, bowl, Matrix.Translation((x + math.cos(a) * (R_IN + 0.12), y + math.sin(a) * (R_IN + 0.12), lip - 0.005)) @
                 Matrix.Scale(0.17 / max(dims.x, dims.y), 4), "well_bowl")
    stool = SI.ph("wooden_stool_02", 3000)
    sx, sy = x - 0.95, y - 0.85
    if stool:
        dims = stool[0].dimensions
        SI.place(coll, stool, Matrix.Translation((sx, sy, yard(sx, sy) - 0.01)) @ Matrix.Rotation(0.4, 4, "Z") @
                 Matrix.Scale(0.26 / max(dims.z, 0.01), 4), "well_stool")
    return jx, jy


def collider(coll, name, x0, x1, y0, y1, z0, z1, surface="stone"):
    from kit import box

    o = box(f"col_{name}", coll, x0, x1, y0, y1, z0, z1)
    o["surface"] = surface
    o.display_type = "WIRE"
    o.hide_render = True
    return o


def build(coll, ground):
    import shop_interiors as SI

    rng = np.random.default_rng(SEED)
    n = clear_old()
    m = materials()
    P = Parts(m)
    x, y = WELL
    g = ground(x, y)
    lip = curb(P, x, y, g, rng)
    yard = apron(P, coll, m, x, y, ground, rng)
    px, py, pg, pivot_z = sweep(P, coll, x, y, ground, rng, lip)
    jx, jy = extras(P, coll, x, y, yard, lip, rng)
    P.emit(coll)
    SI.drop_templates()
    r = R_OUT + 0.04
    collider(coll, "well", x - r, x + r, y - r, y + r, g - 0.1, lip)
    collider(coll, "well_post", px - 0.13, px + 0.13, py - 0.13, py + 0.13, pg, pivot_z)
    collider(coll, "well_jar", jx - 0.32, jx + 0.32, jy - 0.32, jy + 0.32, yard(jx, jy) - 0.1, yard(jx, jy) + 0.6)
    tris = sum(len(o.data.polygons) for o in coll.objects if o.name.startswith("well_") and o.type == "MESH")
    print(f"[village_well] old parts out {n}; built, {tris} faces", flush=True)
