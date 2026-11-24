"""Episode 1's farm, the user's environment pass of November 24, 2026: "make all the rice
fields feel more realistic and very detailed along with the palm trees ... expand it
more ... more palm trees, big trees and bananas ... in front of the house left too much
space". Picked from the plan map the same day: ripe rice in drained paddies (no water, as
asked on Nov 21), the paddies across the south half of the farm on both sides of the cart
track, and in the yard before the house rice drying with a straw stack, a rice pounder
under a lean-to and a kre (a low bamboo platform) under a big tree by the track; the
crocodile flag was already at the gate.

Runs after farmstead.build (rebuild-farmstead.py), from its own random generator, so the
rest of the farm's plants keep their places:
- clears the paddy ground (the two small dry fields, their paths, the yard plants and
  litter standing where the plots go);
- lays the plots: dried mud between low earth dikes, transplanted rice ripe and golden
  hill by hill (rice_field.render_hills' atlas), a patch or two lodged by the storms; two
  plots already cut, stubble in rows, sheaves laid out and a straw stack round its pole;
- sugar palms along the dikes and the cart track, big trees at the fields' corners and by
  the track, banana clumps framing the yard and the field edges, each tree with a trunk
  collider;
- the yard before the house.

Blender metres, X east, Y north, Z up. `build(coll, ground, rng, game)`.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

import farmstead as FS
import rural_kit as RK
import village_nature as VN
from kit import ROOT, collider, image_material, import_model, library_material, mesh_object, plain
from shrine_craft import Batch, place

TEX = os.path.join(ROOT, "art-source", "textures", "ep1")


def _grid(xs, ys, skip=()):
    out = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if (i, j) in skip:
                continue
            out.append((xs[i], xs[i + 1], ys[j], ys[j + 1]))
    return out


# The plots between the dikes' centre lines (the dikes are 0.8 m wide on them). West of
# the track: four columns from the west fence's tree line to the banana grove at the track
# (and, north of it, a fifth up to the track's verge); east: three columns east of the
# grove and the old well, a plot north of the grove, two north-east under the palms.
WEST = _grid([-41.0, -34.0, -27.2, -20.4, -13.2], [-36.0, -29.5, -23.5, -18.5]) + \
    _grid([-41.0, -34.0, -27.2, -20.4, -13.2, -6.8], [-18.5, -14.0, -10.0])
EAST = _grid([16.2, 24.2, 32.2, 40.6], [-36.0, -29.5, -23.0, -16.5]) + \
    [(6.8, 15.0, -15.0, -10.0), (24.2, 32.2, -16.5, -12.5), (32.2, 40.6, -16.5, -12.5)]
CUT = {(-27.2, -20.4, -29.5, -23.5), (24.2, 32.2, -23.0, -16.5)}       # already harvested
BUND_HALF = 0.4
PLOTS = [(x0 + BUND_HALF, x1 - BUND_HALF, y0 + BUND_HALF, y1 - BUND_HALF, "cut" if (x0, x1, y0, y1) in CUT else "ripe")
         for (x0, x1, y0, y1) in WEST + EAST]
ZONES = [(-41.4, -6.4, -36.4, -9.6), (6.4, 41.0, -36.4, -10.0)]      # everything the paddies take

# The yard before the house (Blender): what stands where, kept off the way from the yard
# gate (0, 3) to the front stairs (7.5, 10) and the walker's way from the stairs' foot to
# the east fence (data/walker.ts).
DRYING = [(-9.6, 6.15, 0.08), (-6.45, 5.05, -0.05)]           # mats: centre, turn
STRAW_STACK = (-11.0, 9.0)
POUNDER = (10.0, 5.5)
KRE = (-6.6, -1.0)
KRE_TREE = (-9.2, -2.8)
FIREWOOD = (-12.05, 4.2, 6.6)                                  # x, y0, y1 along the west fence
BENCH = (3.6, 8.75)
BIG_TREES = [KRE_TREE, (-21.0, -3.6), (-42.6, -11.8), (41.8, -12.2), (-42.4, -30.0), (42.2, -33.0)]
BANANAS = [(-14.3, 4.6), (14.3, 5.6), (-14.2, 9.6), (-43.1, -23.0), (-43.4, -15.6), (42.9, -21.0), (43.0, -27.5),
           (5.4, -12.6), (16.0, -38.2), (-17.0, -38.4), (-13.9, -11.6), (22.0, -11.3)]


# ------------------------------------------------------------------ helpers


def in_plot(x, y, pad=0.0):
    return any(x0 - pad <= x <= x1 + pad and y0 - pad <= y <= y1 + pad for x0, x1, y0, y1, _k in PLOTS)


def in_zone(x, y, pad=0.0):
    return any(x0 - pad <= x <= x1 + pad and y0 - pad <= y <= y1 + pad for x0, x1, y0, y1 in ZONES)


def _centre(o):
    objs = [o] + list(o.children_recursive)
    pts = [c.matrix_world @ Vector(v) for c in objs if c.type == "MESH" for v in c.bound_box]
    if not pts:
        return o.matrix_world.translation.copy()
    return sum(pts, Vector()) / len(pts)


def _delete(objs):
    names = set()
    for o in objs:
        names.add(o.name)
        names.update(c.name for c in o.children_recursive)
    for n in names:
        o = bpy.data.objects.get(n)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    return len(names)


def grain_texture():
    """Paddy spread on a mat to dry: thousands of golden husked grains, raked into furrows."""
    path = os.path.join(TEX, "T_ep1_paddy_grain_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(1124)
    n = 1024
    img = np.zeros((n, n, 3), np.float32)
    img[:] = (0.42, 0.3, 0.13)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    for k in range(26000):
        cx, cy = rng.uniform(0, n), rng.uniform(0, n)
        a = rng.uniform(0, math.pi)
        L, W = rng.uniform(7, 10), rng.uniform(2.4, 3.4)
        x0, x1 = int(max(0, cx - L)), int(min(n, cx + L + 1))
        y0, y1 = int(max(0, cy - L)), int(min(n, cy + L + 1))
        if x1 <= x0 or y1 <= y0:
            continue
        sx, sy = xx[y0:y1, x0:x1] - cx, yy[y0:y1, x0:x1] - cy
        u = sx * math.cos(a) + sy * math.sin(a)
        v = -sx * math.sin(a) + sy * math.cos(a)
        d = (u / L) ** 2 + (v / W) ** 2
        mask = d < 1
        tone = rng.uniform(0.75, 1.1)
        col = np.array((0.78, 0.58, 0.26)) * tone
        shade = (1 - 0.45 * np.clip(v / W, 0, 1))[..., None]
        patch = img[y0:y1, x0:x1]
        patch[mask] = (col * shade)[mask]
    furrow = 0.85 + 0.15 * np.sin(yy / n * math.tau * 18 + np.sin(xx / n * math.tau * 2) * 1.5)
    img *= furrow[..., None]
    img = np.clip(img, 0, 1)
    out = bpy.data.images.new("T_ep1_paddy_grain_BC", n, n)
    out.pixels.foreach_set(np.concatenate([img[::-1], np.ones((n, n, 1), np.float32)], axis=-1).ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    return path


def straw_texture():
    """Dry rice straw packed in a stack: thousands of thin stalks, mostly running down,
    pale gold to grey-brown, darker in the gaps; tiles both ways."""
    path = os.path.join(TEX, "T_ep1_straw_stack_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(1125)
    n = 1024
    img = np.zeros((n, n, 3), np.float32)
    img[:] = (0.16, 0.12, 0.07)
    for k in range(9000):
        x0, y0 = rng.uniform(0, n), rng.uniform(0, n)
        L = rng.uniform(40, 160)
        a = math.pi / 2 + rng.normal(0, 0.18)
        w = rng.uniform(1.2, 2.6)
        tone = rng.uniform(0.55, 1.05)
        col = np.array((0.74, 0.6, 0.36)) * tone if rng.random() < 0.8 else np.array((0.5, 0.45, 0.38)) * tone
        steps = int(L)
        t = np.arange(steps)
        xs = (x0 + np.cos(a) * t + 3 * np.sin(t / 40 + k)).astype(int) % n
        ys = (y0 + np.sin(a) * t).astype(int) % n
        for d in range(int(math.ceil(w))):
            shade = 1.0 - 0.35 * d / max(1, w)
            img[ys, (xs + d) % n] = col * shade
    img = np.clip(img, 0, 1)
    out = bpy.data.images.new("T_ep1_straw_stack_BC", n, n)
    out.pixels.foreach_set(np.concatenate([img, np.ones((n, n, 1), np.float32)], axis=-1).ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    return path


def materials():
    """The farm kit's own (rural_kit) where they fit, so the export gains few new ones."""
    m = dict(RK.materials())
    m["stubble"] = m["straw"]
    m["post"] = m["hewn"]
    m["clay"] = bpy.data.materials.get("M_fs_clay") or library_material("clay_plaster", "M_fs_clay", tint=(0.55, 0.36, 0.24), tile=0.6)
    m["floor"] = VN.library_material("brown_mud_03", "M_paddy_floor", tile=2.2, tint=(0.62, 0.54, 0.45))
    m["bund"] = VN.library_material("brown_mud_03", "M_paddy_bund_mud", tile=2.0, tint=(0.7, 0.62, 0.55))
    m["rice"] = VN.rice_material("M_paddy_rice_ripe", os.path.join(TEX, "T_ep1_rice_hills_ripe_BC.png"))
    m["straw_stack"] = image_material("M_vf_straw_stack", straw_texture(), rough=0.9)
    m["grain"] = image_material("M_vf_paddy_grain", grain_texture(), rough=0.8)
    m["mat"] = library_material("bamboo_wall", "M_vf_drying_mat", tint=(0.7, 0.6, 0.45), tile=0.5)
    m["hardwood"] = library_material("dark_wood", "M_vf_hardwood", tint=(0.55, 0.45, 0.38), tile=0.6)
    m["sheaf_grain"] = plain("M_paddy_sheaf_grain", (0.5, 0.36, 0.12), rough=0.75)
    m["stalk"] = plain("M_paddy_straw_stalk", (0.42, 0.33, 0.17), rough=0.8)
    m["straw_wisp"] = plain("M_paddy_straw_wisp", (0.38, 0.31, 0.18), rough=0.85)
    m["lacquer"] = plain("M_vf_red_lacquer", (0.2, 0.03, 0.02), rough=0.5)
    m["leaf"] = plain("M_vf_betel_leaf", (0.07, 0.13, 0.03), rough=0.45)
    return m


# ------------------------------------------------------------------ clearing the ground


def clear(coll_names=("farmstead", "village_nature", "ep1_area_village")):
    """The two old dry fields, their two paths and what grows or lies where the plots go."""
    gone = [o for o in bpy.data.objects if o.parent is None and o.name.startswith(("fs_field_0", "fs_field_1"))]
    for k in (8, 9):
        gone += [o for o in bpy.data.objects if o.parent is None and o.name.startswith(f"fs_path_{k}")]
    for name in coll_names:
        coll = bpy.data.collections.get(name)
        if coll is None:
            continue
        for o in list(coll.objects):
            if o.parent is not None or o.name.startswith(("col_", "marker_", "spawn_", "patrol_", "light_", "interact_", "tingmong")):
                continue
            c = _centre(o)
            size = max(o.dimensions)
            # Plants and litter in a plot or on its dikes; never a building or the ground.
            if size < 12 and in_plot(c.x, c.y, 0.6):
                gone.append(o)
    n = _delete(gone)
    print("[fields] cleared", n, flush=True)


# ------------------------------------------------------------------ the paddies


def floors(coll, m, ground):
    for k, (x0, x1, y0, y1, kind) in enumerate(PLOTS):
        step = 0.5
        nx, ny = int(math.ceil((x1 - x0 + 0.6) / step)) + 1, int(math.ceil((y1 - y0 + 0.6) / step)) + 1
        verts, faces, uvs = [], [], []
        for j in range(ny):
            for i in range(nx):
                x, y = x0 - 0.3 + (x1 - x0 + 0.6) * i / (nx - 1), y0 - 0.3 + (y1 - y0 + 0.6) * j / (ny - 1)
                verts.append((x, y, ground(x, y) + 0.012))
                uvs.append((x / 2.2, y / 2.2))
        for j in range(ny - 1):
            for i in range(nx - 1):
                a = j * nx + i
                faces.append((a, a + 1, a + nx + 1, a + nx))
        mesh_object(f"paddy_floor_{k}", coll, verts, faces, m["floor"], uvs=[uvs[i] for f in faces for i in f], smooth=True)


def bunds(coll, m, ground, rng):
    """The dikes: low banks of earth along every plot line, crowned, slumped, a little
    crooked, worn into a footpath along their tops."""
    lines = set()
    for (x0, x1, y0, y1) in WEST + EAST:
        lines.update({((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))})
    profile = [(-0.46, -0.03), (-0.3, 0.1), (-0.14, 0.19), (0.0, 0.21), (0.14, 0.19), (0.3, 0.1), (0.46, -0.03)]
    for k, (a, b) in enumerate(sorted(lines)):
        a, b = Vector((*a, 0)), Vector((*b, 0))
        L = (b - a).length
        along = (b - a).normalized()
        side = Vector((-along.y, along.x, 0))
        n = max(2, int(L / 0.35))
        ph = rng.uniform(0, 9, 3)
        verts, faces, uvs = [], [], []
        for i in range(n + 1):
            t = i / n
            p = a + along * (L * t + (-0.4 if i == 0 else 0.4 if i == n else 0))
            wob = 0.07 * math.sin(L * t * 0.6 + ph[0]) + 0.03 * math.sin(L * t * 2.1 + ph[1])
            for s, h in profile:
                q = p + side * (s * (1 + 0.12 * math.sin(L * t * 1.7 + s * 5 + ph[2])) + wob)
                verts.append((q.x, q.y, ground(q.x, q.y) + h * (0.9 + 0.1 * math.sin(L * t * 0.9 + ph[1]))))
                uvs.append((q.x / 2.0, q.y / 2.0))
        mm = len(profile)
        for i in range(n):
            for j in range(mm - 1):
                c = i * mm + j
                faces.append((c, c + 1, c + mm + 1, c + mm))
        mesh_object(f"paddy_bund_{k}", coll, verts, faces, m["bund"], uvs=[uvs[i] for f in faces for i in f], smooth=True)
    return sorted(lines)


def rice(coll, m, ground, rng, spacing=0.3, cells=4, width=0.6, height=1.16):
    """Ripe rice hill by hill as it was transplanted: a hill every `spacing` m in rough
    rows, a few missing, each two crossed cards of one rendered hill at its own turn, height
    and lean; a patch or two per plot lodged flat by the storms. One mesh per 12 m cell."""
    meshes = {}
    for x0, x1, y0, y1, kind in PLOTS:
        if kind != "ripe":
            continue
        lodged = [(rng.uniform(x0 + 1, x1 - 1), rng.uniform(y0 + 1, y1 - 1), rng.uniform(0.7, 1.6), rng.uniform(0, math.tau))
                  for _ in range(int(rng.integers(0, 3)))]
        y = y0 + rng.uniform(0.05, spacing)
        while y < y1:
            start, end = x0 + rng.uniform(0, 0.25), x1 - rng.uniform(0, 0.25)
            x = start
            while x < end:
                if rng.random() > 0.035:
                    hx, hy = x + rng.normal(0, 0.03), y + rng.normal(0, 0.03)
                    k = rng.uniform(0.84, 1.06)
                    lean = (rng.normal(0, 0.07), rng.normal(0, 0.07))
                    for lx, ly, lr, la in lodged:
                        d = math.hypot(hx - lx, hy - ly)
                        if d < lr:
                            f = 1 - d / lr
                            lean = (lean[0] + math.cos(la) * 1.6 * f, lean[1] + math.sin(la) * 1.6 * f)
                    key = (int(hx // 12), int(hy // 12))
                    meshes.setdefault(key, []).append((hx, hy, ground(hx, hy), k, int(rng.integers(cells)), rng.uniform(0, math.pi), lean))
                x += spacing
            y += spacing
    n = 0
    for (i, j), hills in meshes.items():
        verts, faces, uvs, normals = [], [], [], []
        for hx, hy, gz, k, cell, yaw, lean in hills:
            u0, u1 = cell / cells, (cell + 1) / cells
            up = Vector((lean[0], lean[1], 1)).normalized() * (height * k)
            for turn in (0.0, math.pi / 2):
                a = yaw + turn
                ax = Vector((math.cos(a), math.sin(a), 0)) * (width * k / 2)
                base = Vector((hx, hy, gz - 0.04))
                b = len(verts)
                verts += [base - ax, base + ax, base + ax + up, base - ax + up]
                faces.append((b, b + 1, b + 2, b + 3))
                uvs += [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
                for t, sx in ((0, -1), (0, 1), (1, 1), (1, -1)):
                    normals.append((Vector((0, 0, 0.45 + 0.5 * t)) + ax.normalized() * 0.45 * sx).normalized())
            n += 1
        me = bpy.data.meshes.new(f"paddy_rice_ripe_{i}_{j}")
        me.from_pydata([v[:] for v in verts], [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(m["rice"])
        me.normals_split_custom_set([normals[me.loops[li].vertex_index][:] for li in range(len(me.loops))])
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
    print("[fields] rice hills", n, "cells", len(meshes), flush=True)


def _sheaf(b, m, x, y, z, yaw, rng, lying=True):
    """A sheaf of cut rice: two dozen stalks bound at the waist with a twist of straw,
    the cut butts square at one end, the heavy heads drooping and fanned at the other."""
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z")
    if lying:
        M = M @ Matrix.Translation((0, 0, 0.05)) @ Matrix.Rotation(math.pi / 2 - 0.08, 4, "Y")
    L = rng.uniform(0.68, 0.82)
    for k in range(24):
        a = rng.uniform(0, math.tau)
        r0 = 0.05 * math.sqrt(rng.random())
        base = Vector((math.cos(a) * r0 * 1.2, math.sin(a) * r0 * 1.2, 0.0))
        waist = Vector((math.cos(a) * r0 * 0.6, math.sin(a) * r0 * 0.6, 0.3))
        fan = 0.07 + 0.08 * rng.random()
        top = Vector((math.cos(a) * fan, math.sin(a) * fan, L * rng.uniform(0.9, 1.02)))
        pts = [M @ base, M @ waist, M @ ((waist + top) / 2), M @ top]
        b.tube(m["stalk"], [tuple(p) for p in pts], [0.0022, 0.002, 0.0019, 0.0016], sides=3)
        # The head: a drooping panicle off the stalk's tip.
        tip = M @ top
        droop = M.to_3x3() @ Vector((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.03))
        g = Vector((0, 0, -0.06)) if not lying else Vector((0, 0, -0.03))
        b.tube(m["sheaf_grain"], [tuple(tip), tuple(tip + droop), tuple(tip + droop * 1.6 + g)], [0.006, 0.007, 0.003], sides=4)
    for k in range(3):              # the band round its waist
        b.lathe(m["stalk"], [(0.034, 0.29 + 0.012 * k), (0.038, 0.296 + 0.012 * k), (0.034, 0.302 + 0.012 * k)], xf=M, segments=10,
                tile=0.1, cap=False)


def straw_stack(coll, m, ground, x, y, rng, name, r=1.35, h=2.7):
    """Rice straw stacked round a pole, as Khmer farmers keep it for the cattle: a fat,
    lumpy stack settled to one side, its straw running down its sides, wisps hanging off
    it, its pole out of the top and loose straw round its foot."""
    z = ground(x, y)
    b = Batch(name)
    prof = [(r * 0.9, 0.0), (r * 0.98, 0.25), (r * 1.02, 0.7), (r, h * 0.5), (r * 0.94, h * 0.58), (r * 0.62, h * 0.74),
            (r * 0.3, h * 0.88), (r * 0.08, h * 0.98), (0.03, h)]
    ph = rng.uniform(0, 6, 5)
    lean = Vector((rng.normal(0, 0.06), rng.normal(0, 0.06)))
    na, nh = 56, 22
    verts, faces, uvs = [], [], []
    for j in range(nh + 1):
        hh = h * j / nh
        rr = float(np.interp(hh, [pp[1] for pp in prof], [pp[0] for pp in prof]))
        for i in range(na + 1):
            ang = math.tau * i / na
            k = 1 + 0.06 * math.sin(ang * 3 + ph[0] + hh) + 0.035 * math.sin(ang * 9 + hh * 3 + ph[1]) \
                + 0.02 * math.sin(ang * 21 + hh * 7 + ph[2])
            sag = 0.05 * math.sin(hh * 2.2 + ph[3]) * (hh / h)
            px = x + math.cos(ang) * rr * k + lean.x * hh
            py = y + math.sin(ang) * rr * k + lean.y * hh
            verts.append((px, py, z - 0.05 + hh - sag))
            # The straw runs down the stack: v along the height, u round it.
            uvs.append((ang * r / 1.1, hh / 1.1))
    for j in range(nh):
        for i in range(na):
            c = j * (na + 1) + i
            faces.append((c, c + 1, c + na + 2, c + na + 1))
    b.add(m["straw_stack"], verts, faces, uvs, smooth=True)
    b.tube(m["post"], [(x + lean.x * h, y + lean.y * h, z + h - 0.25), (x + lean.x * h + 0.03, y + lean.y * h - 0.02, z + h + 0.7)],
           [0.05, 0.04], sides=7)
    # Wisps hanging off its skin, longer down the shoulders.
    for k in range(320):
        ang, hh = rng.uniform(0, math.tau), rng.uniform(0.15, h * 0.85)
        rr = float(np.interp(hh, [pp[1] for pp in prof], [pp[0] for pp in prof])) * 1.02
        p0 = Vector((x + math.cos(ang) * rr + lean.x * hh, y + math.sin(ang) * rr + lean.y * hh, z + hh))
        out = Vector((math.cos(ang), math.sin(ang), 0))
        L = rng.uniform(0.12, 0.35)
        p1 = p0 + out * L * 0.35 + Vector((rng.normal(0, 0.03), rng.normal(0, 0.03), -L * rng.uniform(0.6, 0.95)))
        b.tube(m["straw_wisp"], [tuple(p0), tuple((p0 + p1) / 2 + out * 0.03), tuple(p1)], [0.0035, 0.003, 0.002], sides=3)
    for k in range(120):            # loose straw round its foot
        ang = rng.uniform(0, math.tau)
        d = r * rng.uniform(0.95, 1.7)
        p = Vector((x + math.cos(ang) * d, y + math.sin(ang) * d, 0))
        p.z = ground(p.x, p.y) + 0.008
        q = p + Vector((rng.normal(0, 0.2), rng.normal(0, 0.2), 0))
        b.tube(m["straw_wisp"], [tuple(p), tuple(q)], 0.0035, sides=3)
    b.build(coll)
    collider(name, coll, x - r * 0.8, x + r * 0.8, y - r * 0.8, y + r * 0.8, z, z + h, surface="leaves")


def harvested(coll, m, ground, rng):
    """The two plots already cut: stubble in the transplanted rows, sheaves laid in lines
    to dry, a pile of them waiting, and the straw stack in a corner."""
    for k, (x0, x1, y0, y1, kind) in enumerate(PLOTS):
        if kind != "cut":
            continue
        b = Batch(f"paddy_cut_{k}")
        y = y0 + 0.2
        while y < y1 - 0.1:
            x = x0 + 0.2
            while x < x1 - 0.1:
                if rng.random() > 0.08:
                    px, py = x + rng.normal(0, 0.03), y + rng.normal(0, 0.03)
                    gz = ground(px, py)
                    hh = rng.uniform(0.1, 0.2)
                    for s_ in range(6):
                        a = rng.uniform(0, math.tau)
                        r0 = rng.uniform(0.0, 0.025)
                        p0 = Vector((px + math.cos(a) * r0, py + math.sin(a) * r0, gz - 0.01))
                        p1 = p0 + Vector((math.cos(a) * 0.025, math.sin(a) * 0.025, hh * rng.uniform(0.75, 1.05)))
                        b.tube(m["stalk"], [tuple(p0), tuple(p1)], [0.0032, 0.0026], sides=4)
                x += 0.3
            y += 0.3
        # Sheaves laid out across the stubble in lines, heads all one way.
        for row in np.arange(y0 + 1.0, y1 - 0.8, 1.6):
            for x in np.arange(x0 + 0.8, x1 - 0.8, 0.95):
                if rng.random() < 0.25:
                    continue
                px, py = x + rng.normal(0, 0.1), row + rng.normal(0, 0.12)
                _sheaf(b, m, px, py, ground(px, py), rng.normal(0, 0.25), rng)
        # A pile of sheaves by the stack, heads in.
        sx, sy = x1 - 1.9, y1 - 1.9
        for j in range(18):
            a = j * math.tau / 9
            ring = j // 9
            px, py = sx + 2.4 + math.cos(a) * (0.55 - ring * 0.3), sy - 0.2 + math.sin(a) * (0.55 - ring * 0.3)
            _sheaf(b, m, px, py, ground(px, py) + ring * 0.14, a + math.pi, rng)
        b.build(coll)
        straw_stack(coll, m, ground, sx, sy, rng, f"paddy_straw_stack_{k}")


def palms(coll, ground, rng, lines, game):
    """Sugar palms over the paddies as they stand over Khmer fields: alone or in a pair
    on a dike, ten metres and more apart (the first previews' 40 read as a plantation),
    a few along the cart track."""
    lod0, lod1, _ = VN.flora()["sugar_palm"]
    taken = [(o.matrix_world.translation.x, o.matrix_world.translation.y) for o in bpy.data.objects
             if o.name.startswith(("fs_grove_sugar_palm", "palm_"))]
    spots = []
    for (a, b) in lines:
        a, b = Vector((*a, 0)), Vector((*b, 0))
        L = (b - a).length
        if rng.random() < 0.6:
            continue
        t = rng.uniform(0.5, 6.0)
        while t < L - 0.5:
            p = a + (b - a).normalized() * t
            spots.append((p.x + rng.normal(0, 0.08), p.y + rng.normal(0, 0.08)))
            if rng.random() < 0.25:
                q = p + (b - a).normalized() * rng.uniform(2.7, 3.4)
                spots.append((q.x, q.y))
            t += rng.uniform(11.0, 18.0)
    track, _half = FS.TRACK
    for (ax, ay), (bx, by) in zip(track, track[1:]):
        if not -38.0 < ay < -9.0 or rng.random() < 0.82:
            continue
        side = rng.choice([-1, 1])
        d = Vector((bx - ax, by - ay, 0)).normalized()
        n = Vector((-d.y, d.x, 0)) * side * rng.uniform(2.6, 3.4)
        spots.append((ax + n.x, ay + n.y))
    placed = 0
    for x, y in spots:
        near = [math.hypot(x - tx, y - ty) for tx, ty in taken]
        if any(d < 2.6 for d in near) or sum(d < 9 for d in near) > 1:
            continue
        if FS.path_distance(x, y) < 1.4 or in_plot(x, y, -0.2):
            continue
        taken.append((x, y))
        z = VN.ground_under(ground, x, y, 0.3)
        src = lod1 if game and FS.path_distance(x, y) > 8.0 else lod0
        VN.place(coll, src, f"fs_field_palm_{placed}", x, y, z - 0.04, rng.uniform(0, math.tau), rng.uniform(0.95, 1.35),
                 (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05)))
        collider(f"fs_field_palm_{placed}", coll, x - 0.25, x + 0.25, y - 0.25, y + 0.25, z, z + 3.0, surface="mud")
        placed += 1
    print("[fields] palms", placed, flush=True)


def trees_and_bananas(coll, ground, rng, game):
    f = VN.flora()
    for k, (x, y) in enumerate(BIG_TREES):
        z = VN.ground_under(ground, x, y, 0.6)
        s = rng.uniform(0.6, 0.72)
        src = f["forest_tree_gn"][1] if game and k > 0 else f["forest_tree_gn"][0]
        VN.place(coll, src, f"fs_big_tree_{k}", x, y, z - 0.05, rng.uniform(0, math.tau), s)
        collider(f"fs_big_tree_{k}", coll, x - 0.55, x + 0.55, y - 0.55, y + 0.55, z, z + 4.0, surface="mud")
    for k, (x, y) in enumerate(BANANAS):
        z = VN.ground_under(ground, x, y, 0.5)
        VN.place(coll, f["banana_clump"][0], f"fs_banana_more_{k}", x, y, z - 0.03, rng.uniform(0, math.tau), rng.uniform(0.9, 1.2))
    print("[fields] trees", len(BIG_TREES), "bananas", len(BANANAS), flush=True)


def bund_grass(coll, ground, rng, lines):
    """Preview only (the game grows its own tall grass on the dikes, TallGrass.ts): the
    farm's grass clumps along the dikes' crowns."""
    smau = bpy.data.objects.get("tpl_grass_clump")
    if smau is None:
        return 0
    n = 0
    for (a, b) in lines:
        a, b = Vector((*a, 0)), Vector((*b, 0))
        L = (b - a).length
        t = rng.uniform(0, 0.8)
        while t < L:
            p = a + (b - a).normalized() * t
            side = Vector((-(b - a).y, (b - a).x, 0)).normalized() * rng.choice([-0.32, 0.0, 0.32])
            if rng.random() < 0.55:
                q = p + side
                VN.put(coll, smau, q.x + rng.normal(0, 0.06), q.y + rng.normal(0, 0.06), ground, rng.uniform(0, math.tau),
                       rng.uniform(0.55, 0.9))
                n += 1
            t += rng.uniform(0.5, 1.0)
    return n


# ------------------------------------------------------------------ the yard before the house


def drying_mats(coll, m, ground, rng):
    """Paddy spread to dry on two big bamboo mats, raked into furrows; the rake left on
    one, winnowing trays and sacks beside them."""
    for k, (cx, cy, turn) in enumerate(DRYING):
        W, D = 2.0, 3.0
        R = Matrix.Rotation(turn, 4, "Z")
        b = Batch(f"yard_drying_{k}")
        nx, ny = 16, 24

        def pt(u, v, lift):
            p = R @ Vector(((u - 0.5) * W, (v - 0.5) * D, 0))
            curl = 0.035 * (max(0, abs(u - 0.5) - 0.44) + max(0, abs(v - 0.5) - 0.46)) / 0.05
            x, y = cx + p.x, cy + p.y
            return Vector((x, y, ground(x, y) + 0.012 + lift + curl))

        b.grid(m["mat"], lambda u, v: pt(u, v, 0.0), nx, ny, uv=lambda u, v: (u * W / 0.5, v * D / 0.5))

        def grain(u, v):
            uu, vv = 0.07 + u * 0.86, 0.06 + v * 0.88
            edge = min(uu - 0.07, 0.93 - uu, vv - 0.06, 0.94 - vv) / 0.06
            h = 0.022 * min(1.0, edge) + 0.006 * math.sin(vv * D * 26 + math.sin(uu * 7) * 1.2)
            return pt(uu, vv, max(0.002, h))

        b.grid(m["grain"], grain, 28, 42, uv=lambda u, v: (u * W * 0.86 / 0.9, v * D * 0.88 / 0.9))
        b.build(coll)
    # The rake across the second mat, its teeth down in the grain.
    cx, cy, turn = DRYING[1]
    b = Batch("yard_rake")
    R = Matrix.Rotation(turn + 0.5, 4, "Z")
    head = Vector((cx, cy, 0)) + R @ Vector((0.2, 0.6, 0))
    zh = ground(head.x, head.y) + 0.06
    b.box(m["post"], (0.6, 0.05, 0.04), (0, 0, 0), xf=Matrix.Translation((head.x, head.y, zh)) @ R, chamfer=0.006)
    for i in range(9):
        t = Matrix.Translation((head.x, head.y, zh)) @ R @ Matrix.Translation(((i - 4) * 0.065, 0, -0.035))
        b.box(m["post"], (0.015, 0.015, 0.05), (0, 0, 0), xf=t)
    tail = head + R @ Vector((0, -1.55, 0))
    b.tube(m["bamboo"], [(head.x, head.y, zh + 0.01), (tail.x, tail.y, ground(tail.x, tail.y) + 0.03)], 0.016, sides=7)
    b.build(coll)
    # Winnowing trays stacked by the first mat, sacks of paddy by the second.
    tray = VN.import_scan("winnowing_tray").get("winnowing_tray")
    if tray is not None:
        x, y = DRYING[0][0] - 1.3, DRYING[0][1] - 1.05
        for k in range(3):
            o = VN.put(coll, tray, x + rng.normal(0, 0.02), y + rng.normal(0, 0.02), ground, rng.uniform(0, 6), 1.0, sink=-0.035 * k)
            o.name = f"yard_winnowing_tray_{k}"
    sack = VN.import_scan("rice_sack").get("rice_sack")
    if sack is not None:
        for k, (x, y) in enumerate(((-7.65, 3.85), (-8.2, 4.05))):
            o = VN.put(coll, sack, x, y, ground, rng.uniform(0, 6), 1.0, sink=0.01)
            o.name = f"yard_rice_sack_{k}"


def rice_pounder(coll, m, ground, rng):
    """A foot-worked rice pounder (tbal kdeung) under a small thatched lean-to: the long
    beam on its pivot, the pestle over the mortar hollowed from a log, a rail to hold."""
    x, y = POUNDER
    z = ground(x, y)
    b = Batch("yard_pounder")
    W, D = 2.4, 1.8
    for dx, dy, h in ((-W / 2, -D / 2, 1.75), (W / 2, -D / 2, 1.75), (-W / 2, D / 2, 2.15), (W / 2, D / 2, 2.15)):
        b.tube(m["post"], [(x + dx, y + dy, z - 0.1), (x + dx + rng.normal(0, 0.01), y + dy, z + h)], 0.055, sides=7)
    # The roof: purlins and a thatch slope, high to the north.
    for dy, h in ((-D / 2, 1.75), (D / 2, 2.15)):
        b.box(m["post"], (W + 0.4, 0.08, 0.08), (x, y + dy, z + h), chamfer=0.01)
    slope = math.atan2(0.4, D)
    R = Matrix.Translation((x, y, z + 2.04)) @ Matrix.Rotation(slope, 4, "X")
    b.box(m["straw_stack"], (W + 0.7, D + 0.8, 0.2), (0, 0, 0), xf=R, chamfer=0.06, jitter=0.012, rng=rng)
    for k in range(480):          # the fringe: straw hanging off the eaves all round
        side = rng.integers(4)
        u = rng.uniform(-0.5, 0.5)
        ex, ey = (W + 0.7) / 2, (D + 0.8) / 2
        local = [Vector((u * (W + 0.7), -ey, -0.08)), Vector((u * (W + 0.7), ey, -0.08)),
                 Vector((-ex, u * (D + 0.8), -0.08)), Vector((ex, u * (D + 0.8), -0.08))][side]
        p0 = R @ local
        L = rng.uniform(0.06, 0.22)
        p1 = p0 + Vector((rng.normal(0, 0.035), rng.normal(0, 0.035), -L))
        b.tube(m["straw_wisp"], [tuple(p0), tuple((p0 + p1) / 2 + Vector((rng.normal(0, 0.01), 0, 0))), tuple(p1)],
               [0.0022, 0.0018, 0.001], sides=3)
    # The pounder: mortar, beam on its pivot posts, pestle, the treadle end.
    mx, my = x - 0.65, y
    # The mortar: a length of log, its bark still on, the hollow worn smooth and dark.
    b.lathe(m["bark"], [(0.0, 0.0), (0.25, 0.0), (0.27, 0.06), (0.26, 0.37), (0.275, 0.415), (0.0, 0.415)],
            xf=place(mx, my, z - 0.05), segments=28, tile=0.5, radial=lambda a, h: 1 + 0.035 * math.sin(a * 5) + 0.02 * math.sin(a * 13 + h * 9))
    b.lathe(m["hardwood"], [(0.21, 0.417), (0.2, 0.42), (0.15, 0.38), (0.09, 0.27), (0.0, 0.24)],
            xf=place(mx, my, z - 0.05), segments=28, tile=0.3, cap=False)
    for k in range(3):            # husks spilled round its foot
        b.lathe(m["straw_wisp"], [(0.0, 0.0), (0.3 + 0.1 * k, 0.0), (0.0, 0.012)], xf=place(mx + 0.05 * k, my - 0.04 * k, z + 0.004),
                segments=16, tile=0.3, radial=lambda a, h: 1 + 0.25 * math.sin(a * 3 + k))
    px = x + 0.3
    for s in (-1, 1):
        b.box(m["hardwood"], (0.1, 0.08, 0.55), (px, y + s * 0.16, z + 0.22), chamfer=0.01)
    b.tube(m["post"], [(px, y - 0.22, z + 0.42), (px, y + 0.22, z + 0.42)], 0.02, sides=6)
    tilt = math.atan2(0.18, 1.6)
    b.box(m["hardwood"], (2.3, 0.13, 0.14), (0, 0, 0), xf=Matrix.Translation((x - 0.05, y, z + 0.55)) @ Matrix.Rotation(tilt, 4, "Y"),
          chamfer=0.015, jitter=0.002, rng=rng)
    b.tube(m["hardwood"], [(mx, my, z + 0.3), (mx, my, z + 0.74)], [0.065, 0.075], sides=10, cap_end=True)
    b.tube(m["bamboo"], [(x + 0.75, y - 0.5, z + 1.1), (x + 0.75, y + 0.5, z + 1.1)], 0.025, sides=7)
    for s in (-1, 1):
        b.tube(m["bamboo"], [(x + 0.75, y + s * 0.5, z), (x + 0.75, y + s * 0.5, z + 1.12)], 0.03, sides=7)
    # A sieve and a basket of husks by it.
    b.lathe(m["bamboo"], [(0.0, 0.0), (0.24, 0.0), (0.26, 0.05), (0.25, 0.06), (0.0, 0.01)], xf=place(x - 0.6, y + 0.65, z + 0.01), segments=24, tile=0.2)
    b.build(coll)
    collider("yard_pounder", coll, x - W / 2 - 0.1, x + W / 2 + 0.1, y - D / 2 - 0.1, y + D / 2 + 0.1, z, z + 1.0)


def kre(coll, m, ground, rng):
    """A kre under the big tree by the track: a low platform of split bamboo on a pole
    frame where people sit through the heat; a mat, a betel set and a water pot left on it,
    sandals under it."""
    x, y = KRE
    z = ground(x, y)
    W, D, H = 2.1, 1.45, 0.46
    b = Batch("yard_kre")
    for dx in (-W / 2 + 0.06, 0.0, W / 2 - 0.06):
        for dy in (-D / 2 + 0.06, D / 2 - 0.06):
            b.tube(m["bamboo"], [(x + dx, y + dy, z - 0.08), (x + dx, y + dy, z + H - 0.02)], 0.04, sides=8)
    for dy in (-D / 2 + 0.06, D / 2 - 0.06):
        b.tube(m["bamboo"], [(x - W / 2, y + dy, z + H - 0.08), (x + W / 2, y + dy, z + H - 0.08)], 0.045, sides=8)
    for dx in (-W / 2 + 0.06, 0.0, W / 2 - 0.06):
        b.tube(m["bamboo"], [(x + dx, y - D / 2, z + H - 0.045), (x + dx, y + D / 2, z + H - 0.045)], 0.035, sides=8)
    sx = x - W / 2 + 0.03
    while sx < x + W / 2 - 0.03:
        w = rng.uniform(0.045, 0.06)
        b.box(m["bamboo"], (w - 0.006, D, 0.014), (sx + w / 2, y, z + H), chamfer=0.003, jitter=0.0008, rng=rng)
        sx += w
    b.box(m["mat"], (1.2, 0.9, 0.006), (x - 0.25, y + 0.05, z + H + 0.01))
    # The betel set: a red lacquer box, leaves, a little lime pot; a clay water pot and cup.
    b.box(m["lacquer"], (0.24, 0.16, 0.09), (x - 0.35, y + 0.15, z + H + 0.055), chamfer=0.01)
    for k in range(6):
        b.box(m["leaf"], (0.09, 0.06, 0.002), (x - 0.12 + 0.01 * k, y + 0.1 + 0.005 * k, z + H + 0.016 + 0.002 * k),
              xf=None)
    b.lathe(m["clay"], [(0.0, 0.0), (0.09, 0.0), (0.13, 0.08), (0.12, 0.17), (0.06, 0.22), (0.065, 0.25), (0.0, 0.24)],
            xf=place(x + 0.55, y - 0.25, z + H + 0.014), segments=24, tile=0.2)
    b.build(coll)
    collider("yard_kre", coll, x - W / 2, x + W / 2, y - D / 2, y + D / 2, z, z + H)


def firewood(coll, m, ground, rng):
    """Split firewood stacked against the yard fence between two stakes."""
    x, y0, y1 = FIREWOOD
    b = Batch("yard_firewood")
    for yy in (y0, y1):
        b.tube(m["post"], [(x, yy, ground(x, yy) - 0.1), (x + 0.02, yy, ground(x, yy) + 0.95)], 0.04, sides=6)
    for layer in range(7):
        y = y0 + 0.08
        while y < y1 - 0.1:
            L = rng.uniform(0.42, 0.55)
            r = rng.uniform(0.04, 0.065)
            zz = ground(x, y) + 0.06 + layer * 0.115
            p0 = Vector((x - L / 2, y + rng.normal(0, 0.01), zz))
            p1 = Vector((x + L / 2, y + rng.normal(0, 0.01), zz + rng.normal(0, 0.01)))
            b.tube(m["bark"] if "bark" in m else m["post"], [tuple(p0), tuple(p1)], r, sides=5, cap_end=True)
            y += 2 * r + 0.006
    b.build(coll)
    collider("yard_firewood", coll, x - 0.3, x + 0.3, y0, y1, ground(x, (y0 + y1) / 2), ground(x, (y0 + y1) / 2) + 0.9)


def bench(coll, ground):
    x, y = BENCH
    o = import_model(coll, "painted_wooden_bench", (x, y, ground(x, y)), rot_deg=0, name="yard_bench", collide=False)
    bpy.context.view_layer.update()
    pts = [c.matrix_world @ Vector(v) for c in o.children_recursive if c.type == "MESH" for v in c.bound_box]
    if pts:
        collider("yard_bench", coll, min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts),
                 ground(x, y), max(p.z for p in pts))


def yard(coll, m, ground, rng):
    drying_mats(coll, m, ground, rng)
    straw_stack(coll, m, ground, *STRAW_STACK, rng, "yard_straw_stack", r=1.15, h=3.0)
    rice_pounder(coll, m, ground, rng)
    kre(coll, m, ground, rng)
    firewood(coll, m, ground, rng)
    bench(coll, ground)
    print("[fields] yard dressed", flush=True)


def build(coll, ground, rng=None, game=False):
    rng = rng or np.random.default_rng(2411)
    m = materials()
    clear()
    floors(coll, m, ground)
    lines = bunds(coll, m, ground, rng)
    rice(coll, m, ground, rng)
    harvested(coll, m, ground, rng)
    trees_and_bananas(coll, ground, rng, game)
    palms(coll, ground, rng, lines, game)
    if not game:
        print("[fields] dike grass", bund_grass(coll, ground, rng, lines), flush=True)
    yard(coll, m, ground, rng)
    for o in coll.objects:
        if o.name.startswith("col_"):
            o.display_type = "WIRE"
            o.hide_render = True
