"""Production roadside upgrades invoked by tools/travel/build-taxi.py (roadside()) or run standalone.

Builds 7 bespoke, ultra-detailed, architecturally authentic rural Cambodian roadside shops
along the flooded paddy & village-edge stretch (z = 16..140 m), each with its own trade,
visible warmly lit interior (barber chair & mirror, dentist/salon apothecary cabinet,
glowing CRT TV & coffee counter, moto repair petrol-bottle rack & tire stack, wedding band
PA speakers & hanging grocery stall, stilt corner salon, and lonely half-shuttered jungle-edge
outpost), plus 6 gooseneck-lit weathered Khmer 90s roadside poster boards, overhead electrical
drop wires, radial-UV puddle feathering, and optimized shop props using all 16 real hand-painted
1990s Khmer shop signs & posters in T_taxi_khmer_posters_BC.png (zero generated posters!).
"""
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
TEX = ROOT / "art-source/textures/ep1/taxi"
SCANS = ROOT / "art-source/library/scans"
MODELS = ROOT / "art-source/library/models"

# 4x4 atlas grid of 16 REAL Khmer 90s shop signs & posters in T_taxi_khmer_posters_BC.png
#   0: កាត់សក់ (Barber portrait)            1: សត្វមនោហ៍ (90s cinema poster)
#   2: រាំវង់ប្រជាប្រិយ (Ramvong music)      3: កែសម្ផស្ស BEAUTY SALOON
#   4: រចនា អ៊ុតសក់ (Rachana Salon)          5: កាត់សក់ លាបថ្នាំសក់ (Yellow barber)
#   6: គីម ចេង ដាក់ធ្មេញ (Kim Cheng Dentist)  7: ម៉ាលីន អ៊ុតសក់ (Malin Salon)
#   8: កាត់សក់ ជាង លេង (Cheang Leng Barber)  9: ជួសជុលអេឡិចត្រូនិច (TV/Watch Repair)
#  10: ភក្ត្រា កាត់សក់ (Barber 47 06 49)     11: កោះកុង (4 Khmer hairstyles)
#  12: ពន្លឺពេជ្រ ជួសជុលម៉ូតូ (Moto Repair)  13: ក្រុមតន្ត្រីសម័យពន្លឺថ្មី (Wedding Band)
#  14: បញ្ញា កាត់សក់ (Panha Barber)         15: កាត់សក់ចន្ទ្រា (Chantra Barber)
POSTER_COUNT = 16


def _poster_uv_rect(slot_idx):
    idx = slot_idx % POSTER_COUNT
    col = idx % 4
    row = idx // 4
    pad = 6.0 / 2048.0
    u0 = col * 0.25 + pad
    u1 = (col + 1) * 0.25 - pad
    v0 = (3 - row) * 0.25 + pad
    v1 = (4 - row) * 0.25 - pad
    return u0, v0, u1, v1


def _box_bm(bm, center, size, rot=None, bevel=0.0, segs=1):
    sx, sy, sz = size
    M = Matrix.Translation(center)
    if rot is not None:
        M = M @ rot.to_matrix().to_4x4()
    M = M @ Matrix.Diagonal((sx, sy, sz, 1.0))
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    if bevel > 0:
        edges = list({e for v in ret["verts"] for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=segs, affect="EDGES", clamp_overlap=True)
    return ret["verts"]


def _cyl_bm(bm, p0, p1, r0, r1=None, segs=10, cap=True):
    r1 = r0 if r1 is None else r1
    a, b = Vector(p0), Vector(p1)
    d = b - a
    length = d.length
    if length < 1e-6:
        return []
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    M = Matrix.Translation((a + b) * 0.5) @ q.to_matrix().to_4x4()
    ret = bmesh.ops.create_cone(
        bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r0, radius2=r1, depth=length, matrix=M
    )
    return ret["verts"]


def _tube_bm(bm, pts, radius, segs=8):
    vs = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(vs):
        if i == 0:
            tan = (vs[1] - vs[0]).normalized()
        elif i == len(vs) - 1:
            tan = (vs[-1] - vs[-2]).normalized()
        else:
            tan = (vs[i + 1] - vs[i - 1]).normalized()
        up = Vector((0, 0, 1)) if abs(tan.z) < 0.9 else Vector((1, 0, 0))
        u = tan.cross(up).normalized()
        v = tan.cross(u).normalized()
        rings.append([bm.verts.new(p + (u * math.cos(k / segs * math.tau) + v * math.sin(k / segs * math.tau)) * radius) for k in range(segs)])
    for rA, rB in zip(rings, rings[1:]):
        for k in range(segs):
            bm.faces.new((rA[k], rA[(k + 1) % segs], rB[(k + 1) % segs], rB[k]))


def _torus_bm(bm, center, axis, r_maj, r_min, n_maj=18, n_min=8):
    c = Vector(center)
    ax = Vector(axis).normalized()
    up = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    u = ax.cross(up).normalized()
    v = ax.cross(u).normalized()
    rings = []
    for i in range(n_maj):
        a = i / n_maj * math.tau
        rad = u * math.cos(a) + v * math.sin(a)
        pt = c + rad * r_maj
        rings.append([bm.verts.new(pt + (rad * math.cos(j / n_min * math.tau) + ax * math.sin(j / n_min * math.tau)) * r_min) for j in range(n_min)])
    for i in range(n_maj):
        rA, rB = rings[i], rings[(i + 1) % n_maj]
        for j in range(n_min):
            bm.faces.new((rA[j], rA[(j + 1) % n_min], rB[(j + 1) % n_min], rB[j]))


def _corrugated_sheet_bm(bm, x0, x1, y0, y1, z_x0, z_x1, waves=24, amp=0.022, thick=0.012):
    """Build a sculpted wavy corrugated galvanized/rusty zinc roof sheet (top & bottom skin)."""
    nx = 3
    ny = waves * 2
    top, bot = [], []
    for i in range(nx + 1):
        fx = i / nx
        x = x0 + (x1 - x0) * fx
        z_base = z_x0 + (z_x1 - z_x0) * fx
        t_row, b_row = [], []
        for j in range(ny + 1):
            fy = j / ny
            y = y0 + (y1 - y0) * fy
            w_off = math.sin(fy * waves * math.tau) * amp
            t_row.append(bm.verts.new((x, y, z_base + w_off)))
            b_row.append(bm.verts.new((x, y, z_base + w_off - thick)))
        top.append(t_row)
        bot.append(b_row)
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
    # Front and rear corrugated fascia lip edges so sheet looks solid from below!
    for j in range(ny):
        bm.faces.new((top[nx][j], bot[nx][j], bot[nx][j + 1], top[nx][j + 1]))
        bm.faces.new((top[0][j + 1], bot[0][j + 1], bot[0][j], top[0][j]))


def _bm_obj(name, bm, mat, coll, world_uvs_fn=None, smooth=False, M_world=None):
    if len(bm.faces) == 0:
        bm.free()
        return None
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    me.update()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    if mat:
        me.materials.append(mat)
    if M_world is not None:
        o.matrix_world = M_world
    if world_uvs_fn and mat:
        world_uvs_fn(o)
    return o


def _mesh_uv(name, verts, faces, uvs, mat, coll, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    layer = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        for li in p.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]
    me.update()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    if mat:
        me.materials.append(mat)
    return o


def _add_poster_to_lists(verts, faces, uvs, center, right_vec, up_vec, width, height, poster_idx, seed=1):
    """Append a slightly rain-buckled, weathered poster quad referencing slot `poster_idx` in the real Khmer 90s atlas."""
    rng = np.random.default_rng(seed)
    c = Vector(center)
    r = Vector(right_vec).normalized()
    u = Vector(up_vec).normalized()
    n = r.cross(u).normalized()
    u0, v0, u1, v1 = _poster_uv_rect(poster_idx)
    nx, ny = 3, 4
    base = len(verts)
    for j in range(ny + 1):
        vf = j / ny
        for i in range(nx + 1):
            uf = i / nx
            curl = 0.004 * math.sin(uf * math.pi * 2 + seed) * math.sin(vf * math.pi * 2)
            if vf < 0.25 and uf > 0.75:
                curl += 0.015 * (1 - vf / 0.25) * ((uf - 0.75) / 0.25)
            p = c + r * ((uf - 0.5) * width) + u * ((vf - 0.5) * height) + n * (curl + float(rng.normal(0, 0.001)))
            verts.append(tuple(p))
            uvs.append((u0 + uf * (u1 - u0), v0 + vf * (v1 - v0)))
    for j in range(ny):
        for i in range(nx):
            a = base + j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))


def _load_decimated_scan(filename, ratio=0.22, full_gltf_group=None, import_glb=None):
    """Load a local scan GLB cleanly decimated for roadside passing props (keeps triangle & GLB budget tight!)."""
    path = SCANS / filename
    if not path.exists():
        return []
    if full_gltf_group:
        full_gltf_group()
    before_imgs = set(bpy.data.images)
    objs = import_glb(path)
    stem = path.stem
    for idx, img in enumerate(sorted((i for i in bpy.data.images if i not in before_imgs), key=lambda i: i.name)):
        img.name = f"shop_prop_{stem}_{idx}"
    out = []
    for o in objs:
        if "_lod" in o.name.lower():
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        if len(o.data.polygons) > 800 and ratio < 0.99:
            bpy.ops.object.select_all(action="DESELECT")
            o.select_set(True)
            bpy.context.view_layer.objects.active = o
            mod = o.modifiers.new("roadside_prop_lod", "DECIMATE")
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=mod.name)
        o.hide_render = True
        out.append(o)
    return out


def _place_linked(tpls, coll, M_world, prefix):
    out = []
    for src in tpls:
        c = src.copy()
        c.data = src.data
        coll.objects.link(c)
        c.matrix_world = M_world @ src.matrix_world
        c.hide_render = False
        c.name = f"taxi_road_{prefix}"
        out.append(c)
    return out


def _add_gooseneck_lamp(bm_iron, bm_shade, bm_bulb, mount_pt, out_dir, drop_z=-0.16, reach=0.42):
    """Sculpted Cambodian enamel gooseneck conduit lamp illuminating a fascia sign or poster board."""
    p0 = Vector(mount_pt)
    od = Vector(out_dir).normalized()
    p1 = p0 + od * (reach * 0.45) + Vector((0, 0, 0.14))
    p2 = p0 + od * (reach * 0.88) + Vector((0, 0, 0.10))
    p3 = p0 + od * reach + Vector((0, 0, drop_z + 0.08))
    _tube_bm(bm_iron, [p0, p1, p2, p3], 0.011, segs=6)
    _cyl_bm(bm_iron, p0 - od * 0.02, p0 + od * 0.02, 0.036, 0.036, segs=8)
    # Conical dark-green enamel reflector hood & glowing warm tungsten bulb tucked beneath
    _cyl_bm(bm_shade, p3 + Vector((0, 0, 0.03)), p3 + Vector((0, 0, -0.075)), 0.032, 0.145, segs=12, cap=True)
    bmesh.ops.create_uvsphere(
        bm_bulb, u_segments=10, v_segments=6, radius=0.044, matrix=Matrix.Translation(p3 + Vector((0, 0, -0.068)))
    )


def _add_pendant_lamp(bm_iron, bm_shade, bm_bulb, ceiling_pt, drop=0.45):
    """Hanging Cambodian conical enamel shade lamp on twisted cord."""
    c = Vector(ceiling_pt)
    b = c - Vector((0, 0, drop))
    _cyl_bm(bm_iron, c, b + Vector((0, 0, 0.04)), 0.008, 0.008, segs=6)
    _cyl_bm(bm_shade, b + Vector((0, 0, 0.05)), b - Vector((0, 0, 0.045)), 0.032, 0.155, segs=12, cap=True)
    bmesh.ops.create_uvsphere(
        bm_bulb, u_segments=10, v_segments=6, radius=0.048, matrix=Matrix.Translation(b - Vector((0, 0, 0.048)))
    )


def _add_stool(bm_red, bm_wood, pos, red_plastic=True):
    """Classic low Cambodian roadside red plastic or dark-wood noodle/barber stool."""
    x, y, z = pos
    if red_plastic:
        _box_bm(bm_red, (x, y, z + 0.41), (0.28, 0.28, 0.032), bevel=0.008, segs=1)
        for dx in (-0.11, 0.11):
            for dy in (-0.11, 0.11):
                _cyl_bm(bm_red, (x + dx * 1.18, y + dy * 1.18, z), (x + dx * 0.92, y + dy * 0.92, z + 0.40), 0.017, 0.015, segs=6)
        _box_bm(bm_red, (x, y + 0.115, z + 0.15), (0.22, 0.016, 0.022))
        _box_bm(bm_red, (x, y - 0.115, z + 0.15), (0.22, 0.016, 0.022))
    else:
        _box_bm(bm_wood, (x, y, z + 0.42), (0.30, 0.26, 0.036), bevel=0.004, segs=1)
        for dx in (-0.11, 0.11):
            for dy in (-0.09, 0.09):
                _box_bm(bm_wood, (x + dx, y + dy, z + 0.21), (0.036, 0.036, 0.41))


def _add_crate(bm_wood, pos, size=(0.48, 0.36, 0.32), rot_z=0.0):
    """Slatted rural wooden market crate."""
    M = Matrix.Translation(pos) @ Matrix.Rotation(rot_z, 4, "Z")
    sx, sy, sz = size
    for dx in (-sx * 0.46, sx * 0.46):
        for dy in (-sy * 0.46, sy * 0.46):
            p = M @ Vector((dx, dy, sz * 0.5))
            _box_bm(bm_wood, p, (0.035, 0.035, sz), rot=Euler((0, 0, rot_z)))
    for k in range(3):
        zh = sz * (0.18 + k * 0.32)
        for dy in (-sy * 0.49, sy * 0.49):
            _box_bm(bm_wood, M @ Vector((0, dy, zh)), (sx, 0.018, sz * 0.22), rot=Euler((0, 0, rot_z)))
        for dx in (-sx * 0.49, sx * 0.49):
            _box_bm(bm_wood, M @ Vector((dx, 0, zh)), (0.018, sy, sz * 0.22), rot=Euler((0, 0, rot_z)))


def _add_bottles_row(bm_amber, bm_green, bm_red, start_pt, step_vec, count, seed=1):
    """Row of glass soda/tonic/oil bottles and spice jars on a shop shelf or counter."""
    rng = np.random.default_rng(seed)
    s = Vector(start_pt)
    dv = Vector(step_vec)
    for k in range(count):
        p = s + dv * k + Vector((float(rng.uniform(-0.012, 0.012)), float(rng.uniform(-0.012, 0.012)), 0))
        h = float(rng.uniform(0.14, 0.25))
        r = float(rng.uniform(0.028, 0.042))
        bm = [bm_amber, bm_green, bm_red][k % 3]
        _cyl_bm(bm, p, p + Vector((0, 0, h * 0.68)), r, r * 0.94, segs=7)
        _cyl_bm(bm, p + Vector((0, 0, h * 0.68)), p + Vector((0, 0, h)), r * 0.42, r * 0.34, segs=7)


def _add_shelf_unit(bm_wood, bm_amber, bm_green, bm_red, center, width=1.45, height=1.75, depth=0.34, facing_x=True, seed=1):
    """Multi-tier Cambodian wooden shop display shelving stocked with bottles, tins & boxes."""
    cx, cy, cz = center
    # Side uprights & 4 plank shelves
    for sgn in (-1, 1):
        if facing_x:
            _box_bm(bm_wood, (cx, cy + sgn * width * 0.48, cz + height * 0.5), (depth, 0.045, height))
        else:
            _box_bm(bm_wood, (cx + sgn * width * 0.48, cy, cz + height * 0.5), (0.045, depth, height))
    for k in range(4):
        zh = cz + 0.16 + k * (height - 0.32) / 3.0
        if facing_x:
            _box_bm(bm_wood, (cx, cy, zh), (depth, width, 0.032))
            _add_bottles_row(bm_amber, bm_green, bm_red, (cx + 0.03, cy - width * 0.40, zh + 0.018), (0, width * 0.11, 0), 8, seed=seed + k * 7)
        else:
            _box_bm(bm_wood, (cx, cy, zh), (width, depth, 0.032))
            _add_bottles_row(bm_amber, bm_green, bm_red, (cx - width * 0.40, cy + 0.03, zh + 0.018), (width * 0.11, 0, 0), 8, seed=seed + k * 7)


def _add_bicycle(bm_iron, bm_rubber, bm_bamboo, origin, yaw=0.0):
    """Weathered 1930s-90s Cambodian roadside utility bicycle with front basket leaning against a shop post."""
    M = Matrix.Translation(origin) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(math.radians(10), 4, "X")
    def pt(p):
        return M @ Vector(p)
    # Front & rear spoked wheels
    for wx in (-0.54, 0.54):
        _torus_bm(bm_rubber, pt((wx, 0, 0.34)), (M.to_3x3() @ Vector((0, 1, 0))), 0.31, 0.028, n_maj=14, n_min=6)
        _torus_bm(bm_iron, pt((wx, 0, 0.34)), (M.to_3x3() @ Vector((0, 1, 0))), 0.275, 0.011, n_maj=14, n_min=5)
        for sp in range(5):
            a = sp / 5.0 * math.pi
            _cyl_bm(bm_iron, pt((wx - math.cos(a) * 0.27, 0, 0.34 - math.sin(a) * 0.27)),
                    pt((wx + math.cos(a) * 0.27, 0, 0.34 + math.sin(a) * 0.27)), 0.005, 0.005, segs=4)
    # Diamond steel frame, fork, rear rack, saddle & curved handlebars
    for a, b in [
        ((-0.54, 0, 0.34), (-0.08, 0, 0.34)),
        ((-0.08, 0, 0.34), (-0.16, 0, 0.78)),
        ((-0.54, 0, 0.34), (-0.16, 0, 0.74)),
        ((-0.08, 0, 0.34), (0.36, 0, 0.72)),
        ((-0.16, 0, 0.74), (0.36, 0, 0.74)),
        ((0.54, 0, 0.34), (0.35, 0, 0.90)),
        ((0.35, -0.24, 0.92), (0.35, 0.24, 0.92)),
    ]:
        _cyl_bm(bm_iron, pt(a), pt(b), 0.013, 0.013, segs=6)
    _box_bm(bm_rubber, pt((-0.18, 0, 0.82)), (0.22, 0.13, 0.055), rot=Euler((0, 0, yaw)))
    _box_bm(bm_iron, pt((-0.52, 0, 0.70)), (0.38, 0.16, 0.022), rot=Euler((0, 0, yaw)))  # Rear carrier rack
    _box_bm(bm_bamboo, pt((0.52, 0, 0.78)), (0.24, 0.30, 0.22), rot=Euler((0, 0, yaw)))  # Front woven basket


def _add_banana_bunch(bm_green, bm_amber, bm_bamboo, hang_pt, seed=1):
    """Natural hanging Cambodian banana stalk with curved hands of bananas dangling under a shop awning."""
    rng = np.random.default_rng(seed)
    c = Vector(hang_pt)
    _cyl_bm(bm_bamboo, c + Vector((0, 0, 0.16)), c - Vector((0, 0, 0.42)), 0.018, 0.012, segs=6)
    for tier in range(4):
        zt = c.z - 0.06 - tier * 0.095
        n_b = 7 - tier // 2
        bm_b = bm_amber if tier < 2 else bm_green
        for k in range(n_b):
            ang = (k / n_b) * math.tau + tier * 0.45 + float(rng.uniform(-0.15, 0.15))
            r_out = 0.032 + tier * 0.005
            p0 = Vector((c.x + math.cos(ang) * r_out, c.y + math.sin(ang) * r_out, zt))
            p1 = p0 + Vector((math.cos(ang) * 0.095, math.sin(ang) * 0.095, -0.055))
            _cyl_bm(bm_b, p0, p1, 0.017, 0.011, segs=6)


def _add_poster_frame_bm(bm_frame, lp, lr, lu, pw, ph):
    """3D wooden signboard molding border framing a wall-mounted Khmer 90s poster."""
    c = Vector(lp)
    r = Vector(lr).normalized()
    u = Vector(lu).normalized()
    n = r.cross(u).normalized()
    b = 0.036  # molding width
    thick = 0.026
    # Build orthonormal frame matrix so box aligns cleanly along (r, n, u)
    M_rot = Matrix((r, n, u)).transposed().to_4x4()
    for off, sz in [
        (u * (ph * 0.5 + b * 0.35), (pw + b * 1.7, thick, b)),
        (-u * (ph * 0.5 + b * 0.35), (pw + b * 1.7, thick, b)),
        (r * (pw * 0.5 + b * 0.35), (b, thick, ph + b * 0.2)),
        (-r * (pw * 0.5 + b * 0.35), (b, thick, ph + b * 0.2)),
    ]:
        pos = c - n * 0.008 + off
        M = Matrix.Translation(pos) @ M_rot @ Matrix.Diagonal((sz[0], sz[1], sz[2], 1.0))
        bmesh.ops.create_cube(bm_frame, size=1.0, matrix=M)


def _add_realistic_planter(bm_iron, bm_foliage, pos, seed=1):
    """Weathered dark glazed ceramic urn planter with arched dark tropical sword leaves (never toy cubes!)."""
    rng = np.random.default_rng(seed)
    x, y, z = pos
    # Tapered weathered stoneware urn with rolled lip
    _cyl_bm(bm_iron, (x, y, z), (x, y, z + 0.16), 0.11, 0.165, segs=10)
    _cyl_bm(bm_iron, (x, y, z + 0.16), (x, y, z + 0.34), 0.165, 0.145, segs=10)
    _cyl_bm(bm_iron, (x, y, z + 0.33), (x, y, z + 0.38), 0.16, 0.162, segs=10)
    # 10 graceful slender arched Sansevieria/tropical sword blades fanning organically upward & outward
    for k in range(10):
        ang = (k / 10.0) * math.tau + float(rng.uniform(-0.22, 0.22))
        h = float(rng.uniform(0.32, 0.56))
        tilt = float(rng.uniform(0.18, 0.52))
        r0 = float(rng.uniform(0.02, 0.08))
        p_base = Vector((x + math.cos(ang) * r0, y + math.sin(ang) * r0, z + 0.35))
        p_mid = p_base + Vector((math.cos(ang) * h * 0.35 * tilt, math.sin(ang) * h * 0.35 * tilt, h * 0.55))
        p_tip = p_base + Vector((math.cos(ang) * h * 0.85 * tilt, math.sin(ang) * h * 0.85 * tilt, h * 0.92))
        side_v = Vector((-math.sin(ang), math.cos(ang), 0.0))
        v0 = bm_foliage.verts.new(p_base - side_v * 0.022)
        v1 = bm_foliage.verts.new(p_base + side_v * 0.022)
        v2 = bm_foliage.verts.new(p_mid + side_v * 0.032)
        v3 = bm_foliage.verts.new(p_mid - side_v * 0.032)
        v4 = bm_foliage.verts.new(p_tip)
        bm_foliage.faces.new((v0, v1, v2, v3))
        bm_foliage.faces.new((v3, v2, v4))


def _add_plastic_crate(bm_crate, bm_amber, bm_green, pos, rot_z=0.0, filled=True):
    """Authentic Southeast Asian molded openwork soda/beer bottle crate with glass bottles standing inside."""
    M = Matrix.Translation(pos) @ Matrix.Rotation(rot_z, 4, "Z")
    sx, sy, sz = 0.42, 0.32, 0.28
    # Corner posts & top/bottom rims
    for dx in (-sx * 0.47, sx * 0.47):
        for dy in (-sy * 0.47, sy * 0.47):
            _box_bm(bm_crate, M @ Vector((dx, dy, sz * 0.5)), (0.026, 0.026, sz), rot=Euler((0, 0, rot_z)))
    for hz in (0.025, sz * 0.52, sz - 0.022):
        for dy in (-sy * 0.48, sy * 0.48):
            _box_bm(bm_crate, M @ Vector((0, dy, hz)), (sx, 0.018, 0.032), rot=Euler((0, 0, rot_z)))
        for dx in (-sx * 0.48, sx * 0.48):
            _box_bm(bm_crate, M @ Vector((dx, 0, hz)), (0.018, sy, 0.032), rot=Euler((0, 0, rot_z)))
    _box_bm(bm_crate, M @ Vector((0, 0, 0.015)), (sx * 0.96, sy * 0.96, 0.02), rot=Euler((0, 0, rot_z)))
    if filled:
        for ix in (-0.12, 0.0, 0.12):
            for iy in (-0.075, 0.075):
                bp = M @ Vector((ix, iy, 0.03))
                bm_b = bm_amber if (ix + iy) >= 0 else bm_green
                _cyl_bm(bm_b, bp, bp + Vector((0, 0, 0.21)), 0.030, 0.028, segs=6)
                _cyl_bm(bm_b, bp + Vector((0, 0, 0.21)), bp + Vector((0, 0, 0.29)), 0.016, 0.013, segs=6)


def _add_electric_meter(bm_iron, bm_white, post_x, post_y, z_box=1.82, z_top=3.26):
    """Cambodian wooden-post electric meter box, galvanized conduit pipe & dual white porcelain roof insulators."""
    _box_bm(bm_iron, (post_x + 0.09, post_y, z_box), (0.09, 0.18, 0.26), bevel=0.006, segs=1)
    _cyl_bm(bm_white, (post_x + 0.135, post_y, z_box + 0.03), (post_x + 0.148, post_y, z_box + 0.03), 0.048, 0.048, segs=8)
    _cyl_bm(bm_iron, (post_x + 0.085, post_y, z_box + 0.13), (post_x + 0.085, post_y, z_top), 0.012, 0.012, segs=6)
    for dy_i in (-0.09, 0.09):
        _cyl_bm(bm_white, (post_x + 0.06, post_y + dy_i, z_top - 0.02), (post_x + 0.13, post_y + dy_i, z_top - 0.02), 0.024, 0.020, segs=8)


def _add_spirit_shrine(bm_red, bm_amber, bm_shrine_glow, pos):
    """Authentic red-and-gold Khmer doorway spirit shrine shelf (Chumneang Phteah) with tiny glowing red diodes."""
    x, y, z = pos
    _box_bm(bm_red, (x + 0.14, y, z), (0.28, 0.34, 0.03))  # Shelf base
    _box_bm(bm_red, (x + 0.04, y, z + 0.18), (0.04, 0.32, 0.36))  # Lacquered backplate
    for sy_p in (-0.13, 0.13):
        _cyl_bm(bm_amber, (x + 0.24, y + sy_p, z + 0.015), (x + 0.24, y + sy_p, z + 0.32), 0.012, 0.011, segs=6)
    # Tiered traditional curved Khmer/Chinese miniature shrine roof
    _box_bm(bm_red, (x + 0.15, y, z + 0.34), (0.32, 0.40, 0.045), rot=Euler((0, math.radians(10), 0)))
    _box_bm(bm_amber, (x + 0.15, y, z + 0.375), (0.14, 0.44, 0.026))
    # Tiny glowing red shrine altar diodes & incense cup
    for sy_d in (-0.075, 0.075):
        bmesh.ops.create_uvsphere(bm_shrine_glow, u_segments=6, v_segments=4, radius=0.016, matrix=Matrix.Translation((x + 0.18, y + sy_d, z + 0.08)))
    _cyl_bm(bm_amber, (x + 0.18, y, z + 0.015), (x + 0.18, y, z + 0.068), 0.028, 0.032, segs=8)


def _add_accordion_gate(bm_iron, x, y_jamb, z0, z1, side_sgn):
    """Galvanized folding iron scissor/accordion security gate stacked open at the doorway corner."""
    n_bars = 5
    span = 0.34
    for k in range(n_bars):
        by = y_jamb - side_sgn * (0.04 + k * (span / max(1, n_bars - 1)))
        _box_bm(bm_iron, (x + 0.06, by, (z0 + z1) * 0.5), (0.024, 0.020, z1 - z0))
    # Diagonal scissor lattice cross-bars catching headlights!
    for hz in (z0 + 0.38, z0 + 1.05, z0 + 1.72):
        _box_bm(bm_iron, (x + 0.06, y_jamb - side_sgn * (span * 0.52), hz), (0.016, span * 1.15, 0.018), rot=Euler((math.radians(38), 0, 0)))
        _box_bm(bm_iron, (x + 0.06, y_jamb - side_sgn * (span * 0.52), hz), (0.016, span * 1.15, 0.018), rot=Euler((math.radians(-38), 0, 0)))


def _add_tv_antenna(bm_iron, base_pt):
    """Crooked rural rooftop aluminum Yagi TV antenna mast piercing the stormy night sky."""
    p = Vector(base_pt)
    top = p + Vector((0.06, -0.04, 1.85))
    _cyl_bm(bm_iron, p, top, 0.018, 0.014, segs=6)
    # Crossboom & 5 graduated dipole rods
    boom_a = top + Vector((-0.52, 0.12, -0.06))
    boom_b = top + Vector((0.68, -0.16, -0.06))
    _cyl_bm(bm_iron, boom_a, boom_b, 0.011, 0.011, segs=6)
    for f, half_w in [(0.05, 0.46), (0.28, 0.40), (0.52, 0.34), (0.76, 0.28), (0.96, 0.22)]:
        c = boom_a.lerp(boom_b, f)
        _cyl_bm(bm_iron, c + Vector((0.08, half_w, 0)), c + Vector((-0.08, -half_w, 0)), 0.007, 0.007, segs=5)


def _add_motorbike(bm_iron, bm_rubber, bm_blue, bm_white, bm_red, origin, yaw=0.0):
    """Sculpted vintage Cambodian Honda-Cub-style step-through motorbike parked on center stand."""
    M = Matrix.Translation(origin) @ Matrix.Rotation(yaw, 4, "Z")
    R = M.to_3x3()
    def pt(p):
        return M @ Vector(p)
    # Front & rear rubber tires + chrome rims + spokes
    for wx in (-0.62, 0.62):
        _torus_bm(bm_rubber, pt((wx, 0, 0.30)), R @ Vector((0, 1, 0)), 0.25, 0.048, n_maj=14, n_min=6)
        _torus_bm(bm_iron, pt((wx, 0, 0.30)), R @ Vector((0, 1, 0)), 0.195, 0.014, n_maj=12, n_min=5)
        _cyl_bm(bm_iron, pt((wx, -0.06, 0.30)), pt((wx, 0.06, 0.30)), 0.042, 0.042, segs=8)
    # Step-through pressed-steel body, front fender, white plastic leg-shield fairing!
    _box_bm(bm_blue, pt((-0.18, 0, 0.56)), (0.82, 0.20, 0.24), rot=Euler((0, math.radians(-10), yaw)), bevel=0.02, segs=1)
    _box_bm(bm_blue, pt((0.52, 0, 0.54)), (0.34, 0.14, 0.08), rot=Euler((0, math.radians(16), yaw)))  # Front fender
    _box_bm(bm_white, pt((0.32, 0, 0.54)), (0.14, 0.44, 0.54), rot=Euler((0, math.radians(-18), yaw)), bevel=0.015, segs=1)  # Iconic Cub white leg shield!
    # Engine crankcase, chrome exhaust muffler & center stand
    _box_bm(bm_iron, pt((0.02, 0, 0.28)), (0.32, 0.22, 0.22), rot=Euler((0, 0, yaw)))
    _cyl_bm(bm_iron, pt((0.12, -0.14, 0.24)), pt((-0.74, -0.15, 0.34)), 0.022, 0.036, segs=8)
    _cyl_bm(bm_iron, pt((-0.10, -0.14, 0.0)), pt((-0.02, -0.10, 0.22)), 0.012, 0.012, segs=5)
    _cyl_bm(bm_iron, pt((-0.10, 0.14, 0.0)), pt((-0.02, 0.10, 0.22)), 0.012, 0.012, segs=5)
    # Front fork, handlebars, round headlamp cowl & ribbed black bench seat + rear luggage rack & red taillight!
    for fy in (-0.08, 0.08):
        _cyl_bm(bm_iron, pt((0.62, fy, 0.30)), pt((0.40, fy * 0.7, 0.92)), 0.018, 0.018, segs=6)
    _cyl_bm(bm_iron, pt((0.38, -0.32, 0.94)), pt((0.38, 0.32, 0.94)), 0.016, 0.016, segs=6)
    _cyl_bm(bm_white, pt((0.44, 0, 0.92)), pt((0.52, 0, 0.92)), 0.075, 0.068, segs=10)
    _box_bm(bm_rubber, pt((-0.24, 0, 0.74)), (0.66, 0.24, 0.11), rot=Euler((0, 0, yaw)), bevel=0.02, segs=1)
    _box_bm(bm_iron, pt((-0.72, 0, 0.68)), (0.30, 0.22, 0.025), rot=Euler((0, 0, yaw)))
    _box_bm(bm_red, pt((-0.78, 0, 0.60)), (0.05, 0.10, 0.08), rot=Euler((0, 0, yaw)))


def _add_hair_dryer_stand(bm_iron, bm_white, pos):
    """Vintage 1990s Cambodian salon wheeled hooded dome hair-dryer stand."""
    x, y, z = pos
    for a in range(4):
        ang = a * math.pi * 0.5 + 0.4
        _cyl_bm(bm_iron, (x, y, z + 0.06), (x + math.cos(ang) * 0.26, y + math.sin(ang) * 0.26, z + 0.03), 0.014, 0.012, segs=6)
    _cyl_bm(bm_iron, (x, y, z + 0.06), (x, y, z + 1.48), 0.018, 0.015, segs=8)
    _cyl_bm(bm_white, (x + 0.04, y, z + 1.56), (x + 0.22, y, z + 1.32), 0.14, 0.21, segs=12)


def _add_sewing_machine(bm_posts, bm_iron, bm_red, pos):
    """Vintage rural Cambodian treadle sewing machine table with iron wheel & draped silk bolt."""
    x, y, z = pos
    _box_bm(bm_posts, (x, y, z + 0.74), (0.48, 0.92, 0.045))
    for sy_l in (-0.38, 0.38):
        _box_bm(bm_iron, (x, y + sy_l, z + 0.37), (0.42, 0.04, 0.72))
    _box_bm(bm_iron, (x, y, z + 0.18), (0.28, 0.34, 0.025))  # Foot treadle
    # Classic black iron sewing machine arm & handwheel
    _box_bm(bm_iron, (x, y - 0.04, z + 0.78), (0.18, 0.38, 0.04))
    _box_bm(bm_iron, (x, y + 0.12, z + 0.92), (0.07, 0.09, 0.24))
    _box_bm(bm_iron, (x, y - 0.04, z + 1.00), (0.07, 0.34, 0.08))
    _torus_bm(bm_iron, (x, y + 0.18, z + 0.94), (0, 1, 0), 0.065, 0.012, n_maj=10, n_min=5)
    # Draped crimson/maroon Khmer silk cloth folded over table corner
    _box_bm(bm_red, (x + 0.10, y - 0.30, z + 0.78), (0.26, 0.28, 0.045))
    _box_bm(bm_red, (x + 0.23, y - 0.30, z + 0.62), (0.03, 0.26, 0.32))


def _add_galvanized_bucket(bm_iron, pos):
    """Weathered tapered galvanized zinc rain/utility bucket."""
    x, y, z = pos
    _cyl_bm(bm_iron, (x, y, z), (x, y, z + 0.29), 0.115, 0.155, segs=10)


def _add_hanging_brooms(bm_bamboo, bm_posts, pos):
    """Bundle of traditional Cambodian reed brooms & coiled utility rope hanging from a rafter hook."""
    x, y, z = pos
    for k, dy in enumerate((-0.14, 0.0, 0.14)):
        _cyl_bm(bm_bamboo, (x, y + dy, z), (x + 0.04, y + dy * 1.15, z - 0.62), 0.014, 0.012, segs=6)
        _cyl_bm(bm_posts, (x + 0.04, y + dy * 1.15, z - 0.62), (x + 0.06, y + dy * 1.2, z - 0.92), 0.024, 0.085, segs=7)
    _torus_bm(bm_bamboo, (x, y + 0.38, z - 0.26), (1, 0, 0), 0.14, 0.022, n_maj=10, n_min=5)


def _add_ditch_bridge(bm_deck, bm_posts, bm_brick, x_start, y_center, width=1.42, length=1.65):
    """Weathered Cambodian 3-plank timber footbridge with cross-cleats crossing the roadside drainage ditch to shop steps."""
    # Twin longitudinal timber stringers + brick shore abutment
    for dy in (-width * 0.36, width * 0.36):
        _box_bm(bm_posts, (x_start + length * 0.5, y_center + dy, -0.34), (length, 0.09, 0.09))
    _box_bm(bm_brick, (x_start + length - 0.10, y_center, -0.50), (0.28, width * 0.95, 0.42))
    # 5 spaced weathered deck planks + cross grip cleats
    n_slats = 6
    for k in range(n_slats):
        px = x_start + 0.12 + k * ((length - 0.22) / max(1, n_slats - 1))
        _box_bm(bm_deck, (px, y_center, -0.27), (0.22, width, 0.042), bevel=0.004, segs=1)


def _add_catenary_tarp(bm_tarp, bm_bamboo, bm_wire, x0, x1, y0, y1, z_high, z_low):
    """Realistic monsoon vinyl rain tarp with organic curved catenary cloth sag + bamboo props & rope guy-lines."""
    nx, ny = 6, 8
    grid = []
    for i in range(nx + 1):
        fx = i / nx
        row = []
        for j in range(ny + 1):
            fy = j / ny
            x = x0 + (x1 - x0) * fx
            y = y0 + (y1 - y0) * fy
            # Real cloth gravity sag deepest in the middle of the bay + rippled rain-wind edge!
            sag = -0.14 * math.sin(fx * math.pi) * (0.55 + 0.45 * math.sin(fy * math.pi))
            ripple = 0.015 * math.sin(fy * math.pi * 4) * fx
            z = z_high + (z_low - z_high) * fx + sag + ripple
            row.append(bm_tarp.verts.new((x, y, z)))
        grid.append(row)
    for i in range(nx):
        for j in range(ny):
            bm_tarp.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    # Front horizontal bamboo ridge pole + vertical bamboo support poles + diagonal rope guy-lines!
    _cyl_bm(bm_bamboo, (x1, y0 - 0.08, z_low - 0.02), (x1, y1 + 0.08, z_low - 0.02), 0.024, 0.024, segs=6)
    for py in (y0 + 0.06, y1 - 0.06):
        _cyl_bm(bm_bamboo, (x1, py, 0.14), (x1, py, z_low), 0.028, 0.024, segs=6)
        _cyl_bm(bm_wire, (x1, py, z_low - 0.02), (x1 + 0.42, py, -0.28), 0.006, 0.006, segs=4)


def _add_festoon_lights(bm_wire, bm_bulb, p0, p1, n_bulbs=7, sag=0.18):
    """Warm sagging string of miniature Cambodian roadside cafe / wedding-band festoon bulbs across veranda eaves."""
    a, b = Vector(p0), Vector(p1)
    pts = []
    for k in range(n_bulbs * 2 + 1):
        f = k / (n_bulbs * 2)
        p = a.lerp(b, f)
        p.z -= sag * math.sin(f * math.pi)
        pts.append(p)
    _tube_bm(bm_wire, pts, 0.006, segs=5)
    for k in range(n_bulbs):
        f = (k + 0.5) / n_bulbs
        p = a.lerp(b, f)
        p.z -= sag * math.sin(f * math.pi) + 0.036
        _cyl_bm(bm_wire, p + Vector((0, 0, 0.036)), p + Vector((0, 0, 0.012)), 0.007, 0.007, segs=6)
        bmesh.ops.create_uvsphere(bm_bulb, u_segments=8, v_segments=5, radius=0.024, matrix=Matrix.Translation(p))


def _add_air_compressor(bm_red, bm_iron, bm_rubber, pos):
    """Cylindrical red rural garage air compressor tank with top motor, gauge & coiled black air hose."""
    x, y, z = pos
    _cyl_bm(bm_red, (x, y - 0.28, z + 0.24), (x, y + 0.28, z + 0.24), 0.15, 0.15, segs=12)
    for wy in (-0.22, 0.22):
        _torus_bm(bm_rubber, (x + 0.11, y + wy, z + 0.09), (1, 0, 0), 0.075, 0.022, n_maj=10, n_min=5)
        _torus_bm(bm_rubber, (x - 0.11, y + wy, z + 0.09), (1, 0, 0), 0.075, 0.022, n_maj=10, n_min=5)
    _box_bm(bm_iron, (x, y - 0.04, z + 0.44), (0.18, 0.26, 0.16), bevel=0.01, segs=1)
    _cyl_bm(bm_iron, (x, y + 0.18, z + 0.36), (x, y + 0.18, z + 0.48), 0.025, 0.025, segs=8)
    _torus_bm(bm_rubber, (x + 0.14, y, z + 0.32), (1, 0, 0), 0.11, 0.014, n_maj=10, n_min=5)


def _add_dress_form(bm_posts, bm_silk, pos):
    """Tailor's wooden tripod mannequin dress-form draped in traditional Khmer patterned hol silk."""
    x, y, z = pos
    for a in range(3):
        ang = a * math.tau / 3.0
        _cyl_bm(bm_posts, (x + math.cos(ang) * 0.22, y + math.sin(ang) * 0.22, z), (x, y, z + 0.24), 0.016, 0.014, segs=6)
    _cyl_bm(bm_posts, (x, y, z + 0.22), (x, y, z + 0.92), 0.018, 0.016, segs=8)
    # Sculpted cloth torso draped in silk
    _cyl_bm(bm_silk, (x, y, z + 0.88), (x, y, z + 1.12), 0.16, 0.115, segs=12)
    _cyl_bm(bm_silk, (x, y, z + 1.12), (x, y, z + 1.40), 0.115, 0.175, segs=12)
    _cyl_bm(bm_silk, (x, y, z + 1.40), (x, y, z + 1.49), 0.175, 0.055, segs=10)
    _cyl_bm(bm_posts, (x, y, z + 1.49), (x, y, z + 1.56), 0.036, 0.028, segs=8)


def _build_detailed_shop(coll, M_shop, mats, props, p_verts, p_faces, p_uvs, spec, shop_idx):
    """Build ONE hyper-detailed, bespoke rural Cambodian roadside shop matching its specific trade.

    Local shop frame (Blender axes):
      +X faces toward the road (interior back wall at X=-3.3, front doorway wall at X=0.0, veranda extends to X=+1.85)
      Y runs along the road (half-width hw in [2.65..3.25])
      Z=0.16 is veranda plank floor; stilts/footings extend to Z=-1.65 (solidly anchored in flooded paddies!)
    """
    trade = spec["trade"]
    hw = spec.get("hw", 2.75)
    open_front = spec.get("open_front", True)
    has_parapet = spec.get("parapet", False)
    has_tarp = spec.get("tarp", False)
    has_fluoro = spec.get("fluoro", False)
    dim_outpost = spec.get("dim", False)
    door_w = 1.95 if not dim_outpost else 0.72

    # Material-grouped bmeshes -> only ~12 clean meshes per shop, zero bloat, super crisp detail!
    bm_posts = bmesh.new()
    bm_walls = bmesh.new()
    bm_paint = bmesh.new()
    bm_shut = bmesh.new()
    bm_tin = bmesh.new()
    bm_iron = bmesh.new()
    bm_shade = bmesh.new()
    bm_bulb = bmesh.new()
    bm_fluoro = bmesh.new()
    bm_red = bmesh.new()
    bm_blue = bmesh.new()
    bm_amber = bmesh.new()
    bm_green = bmesh.new()
    bm_white = bmesh.new()
    bm_mirror = bmesh.new()
    bm_rubber = bmesh.new()
    bm_crt = bmesh.new()
    bm_bamboo = bmesh.new()
    bm_win_glow = bmesh.new()
    bm_noodle_glow = bmesh.new()
    bm_foliage = bmesh.new()
    bm_shrine_glow = bmesh.new()
    bm_brick = bmesh.new()
    bm_deck = bmesh.new()
    bm_concrete = bmesh.new()
    bm_clay_tile = bmesh.new()
    bm_thatch = bmesh.new()
    bm_bamboo_wall = bmesh.new()
    bm_table_wood = bmesh.new()
    bm_krama = bmesh.new()
    bm_hol_silk = bmesh.new()
    bm_news = bmesh.new()
    bm_kantel = bmesh.new()
    bm_wire_local = bmesh.new()

    def to_w(p):
        return M_shop @ Vector(p)

    def dir_w(v):
        return (M_shop.to_3x3() @ Vector(v)).normalized()

    # 1. RAISED STILT & BRICK-PIER FOUNDATION + INDIVIDUAL TIMBER VERANDA PLANKS + FRONT ENTRY STEPS
    # Heavy brick/concrete pier footings reaching deep beneath flooded paddy water (never floats!)
    stilt_xs = (-3.25, -1.60, 0.0, 1.75)
    stilt_ys = (-hw, -hw * 0.36, hw * 0.36, hw)
    for px in stilt_xs:
        for py in stilt_ys:
            if px == 1.75 and abs(py) < hw * 0.5:
                continue
            # Weathered Cambodian red-brick foundation pier + dark timber stilt post
            _box_bm(bm_brick, (px, py, -1.05), (0.30, 0.30, 1.25))
            h = 3.25 if px == -3.25 else (3.65 if px == 0.0 else (2.52 if px == 1.75 else 3.45))
            if px == -1.60 and abs(py) < hw * 0.5:
                _box_bm(bm_posts, (px, py, -0.35), (0.15, 0.15, 1.05))
            else:
                _box_bm(bm_posts, (px, py, h * 0.5 - 0.25), (0.15, 0.15, h + 0.72))
    # Cross-bracing struts under front veranda stilts (authentic Khmer stilt-house silhouette!)
    for py in (-hw, hw):
        _cyl_bm(bm_posts, (0.0, py, 0.12), (1.75, py, -0.75), 0.045, 0.045, segs=6)
        _cyl_bm(bm_posts, (0.0, py, -0.75), (1.75, py, 0.12), 0.045, 0.045, segs=6)
    # Main longitudinal floor girders + individual spaced weathered brown veranda deck planks!
    for py in stilt_ys:
        _box_bm(bm_posts, (-0.75, py, 0.04), (5.3, 0.13, 0.14))
    _box_bm(bm_deck, (-1.65, 0.0, 0.14), (3.45, hw * 2.02, 0.09))  # Interior plank floor
    n_planks = 12
    for k in range(n_planks):
        px = 0.08 + k * (1.78 / n_planks)
        _box_bm(bm_deck, (px, 0.0, 0.155), (0.132, hw * 2.04, 0.045), bevel=0.004, segs=1)
    # Timber entrance steps + weathered 3-plank ditch-crossing footbridge anchoring shop to muddy roadside!
    step_y = -0.35 if trade != "moto" else 0.0
    if trade == "moto":
        # Worn rain-slick concrete oil-stained moto repair apron bridging out to road shoulder!
        _box_bm(bm_concrete, (1.15, 0.0, 0.165), (1.95, hw * 1.98, 0.06))
        _box_bm(bm_concrete, (2.78, 0.0, -0.14), (1.65, 2.85, 0.24), rot=Euler((0, math.radians(14), 0)))
    else:
        for st in range(3):
            _box_bm(bm_deck, (1.92 + st * 0.24, step_y, 0.04 - st * 0.16), (0.22, 1.35, 0.045))
        for sy_s in (step_y - 0.62, step_y + 0.62):
            _box_bm(bm_posts, (2.15, sy_s, -0.18), (0.95, 0.055, 0.14), rot=Euler((0, math.radians(34), 0)))
        _add_ditch_bridge(bm_deck, bm_posts, bm_brick, 2.52, step_y, width=1.40, length=1.45)

    # 2. EXPOSED TIMBER ROOF RAFTERS, KNEE BRACES, PURLINS & BESPOKE ROOFING (ZINC / CLAY TILES / THATCH!)
    # Horizontal roof wall plates
    for px, pz in [(-3.25, 3.16), (0.0, 3.58), (1.75, 2.52)]:
        _box_bm(bm_posts, (px, 0.0, pz), (0.13, hw * 2.12, 0.15))
    # 45-degree timber knee braces under the front veranda eaves (classic Southeast Asian joinery!)
    for py in (-hw, hw):
        _box_bm(bm_posts, (1.42, py, 2.26), (0.68, 0.08, 0.09), rot=Euler((0, math.radians(-38), 0)))
        _box_bm(bm_posts, (1.75, py + (-0.32 if py > 0 else 0.32), 2.24), (0.08, 0.62, 0.09), rot=Euler((math.radians(38 if py > 0 else -38), 0, 0)))
    # Exposed wooden rafters (7 across roof width!) + horizontal purlins
    for k in range(7):
        ry = -hw * 1.04 + k * (hw * 2.08 / 6.0)
        _box_bm(bm_posts, (-1.62, ry, 3.44), (3.85, 0.075, 0.11), rot=Euler((0, math.radians(-7.5), 0)))
        _box_bm(bm_posts, (0.92, ry, 3.04), (2.42, 0.070, 0.10), rot=Euler((0, math.radians(28.5), 0)))
    for px, pz in [(-2.5, 3.38), (-1.1, 3.55), (0.55, 3.30), (1.45, 2.82)]:
        _box_bm(bm_posts, (px, 0.0, pz), (0.06, hw * 2.16, 0.07))
    # Authentic Cambodian roof variety: aged terracotta clay tiles on Colonial Dentist/Salon,
    # weathered palm thatch veranda on Jungle Outpost, and corrugated rusty zinc sheets on working trades!
    roof_bm = bm_clay_tile if trade == "dentist_salon" else bm_tin
    veranda_roof_bm = bm_thatch if dim_outpost else roof_bm
    _corrugated_sheet_bm(roof_bm, -3.55, 0.10, -hw * 1.08, hw * 1.08, 3.24, 3.74, waves=24, amp=0.022)
    _corrugated_sheet_bm(veranda_roof_bm, -0.05, 2.15, -hw * 1.10, hw * 1.10, 3.70, 2.52, waves=24, amp=0.022)
    _box_bm(roof_bm, (0.0, 0.0, 3.76), (0.34, hw * 2.22, 0.05), bevel=0.01, segs=1)
    # Front decorative scalloped/notched wooden fascia trim board + hanging corrugated metal rain gutter & downspout!
    _box_bm(bm_posts, (2.06, 0.0, 2.48), (0.04, hw * 2.20, 0.17))
    _cyl_bm(bm_iron, (2.16, -hw * 1.10, 2.42), (2.16, hw * 1.10, 2.42), 0.055, 0.055, segs=8, cap=False)
    # Downspout running down front corner post straight into rainwater Ong jar
    ds_y = hw - 0.12
    _cyl_bm(bm_iron, (2.14, ds_y, 2.40), (1.68, ds_y, 2.08), 0.036, 0.036, segs=7)
    _cyl_bm(bm_iron, (1.68, ds_y, 2.08), (1.68, ds_y, 0.88), 0.036, 0.036, segs=7)

    # Optional Cambodian colonial stepped plaster parapet header above the veranda roof (Shop 2 Dentist/Salon!)
    if has_parapet:
        _box_bm(bm_paint, (0.05, 0.0, 3.92), (0.14, hw * 1.98, 0.56), bevel=0.01, segs=1)
        _box_bm(bm_paint, (0.05, 0.0, 4.32), (0.16, hw * 1.25, 0.34), bevel=0.01, segs=1)
        _box_bm(bm_posts, (0.08, 0.0, 4.50), (0.22, hw * 1.32, 0.07))
        _box_bm(bm_posts, (0.08, 0.0, 4.20), (0.20, hw * 2.04, 0.06))

    # 3. EXTERIOR & INTERIOR WALLS (BESPOKE PLASTER / SPLIT-BAMBOO / WEATHERED PLANKS PER SHOP!)
    wall_bm = bm_paint if has_parapet else (bm_bamboo_wall if trade in ("salon", "outpost") else bm_walls)
    _box_bm(wall_bm, (-3.25, 0.0, 1.70), (0.10, hw * 2.0, 3.12))
    for sy in (-hw, hw):
        _box_bm(wall_bm, (-1.62, sy, 1.70), (3.28, 0.10, 3.12))
        # Exterior horizontal wood molding rails breaking up flat walls
        for rz in (0.98, 2.38, 3.15):
            _box_bm(bm_posts, (-1.62, sy + (0.065 if sy > 0 else -0.065), rz), (3.32, 0.04, 0.08))
        # Warm glowing frosted side window with timber security bars & open side shutter (shows cozy interior life on approach!)
        if not dim_outpost:
            out_s = 1.0 if sy > 0 else -1.0
            wx, wz = -2.72, 1.88
            _box_bm(bm_posts, (wx, sy + out_s * 0.055, wz), (0.68, 0.04, 0.86))
            _box_bm(bm_win_glow, (wx, sy + out_s * 0.066, wz), (0.56, 0.025, 0.74))
            for bx_w in (-0.18, 0.0, 0.18):
                _box_bm(bm_posts, (wx + bx_w, sy + out_s * 0.082, wz), (0.028, 0.028, 0.76))
            _box_bm(bm_shut, (wx - 0.52, sy + out_s * 0.12, wz), (0.36, 0.045, 0.78), rot=Euler((0, 0, math.radians(24 * out_s))))
    # Front wall flanks leaving a generous real recessed doorway/shopfront opening!
    flank_w = max(0.75, hw - door_w * 0.5)
    flank_y = door_w * 0.5 + flank_w * 0.5
    # Asymmetric weathered ceramic urn planter with dark arched tropical sword leaves (ONLY select shops, never toy cubes!)
    if trade in ("barber", "dentist_salon", "salon"):
        py_p = step_y - 0.88 if trade != "salon" else step_y + 0.88
        _add_realistic_planter(bm_iron, bm_foliage, (1.84, py_p, 0.17), seed=800 + shop_idx * 17)
    # Wall-mounted Cambodian electric meter box, drop conduit & porcelain roof insulators on active shops!
    if not dim_outpost:
        _add_electric_meter(bm_iron, bm_white, 1.75, -hw + 0.08 if shop_idx % 2 == 0 else hw - 0.08, z_box=1.78, z_top=2.56)
    # Red-and-gold Cambodian Chumneang Phteah house spirit shrine shelf with glowing red diodes at doorway corner!
    if trade in ("noodle", "tv_coffee", "grocery", "barber"):
        _add_spirit_shrine(bm_red, bm_amber, bm_shrine_glow, (0.04, -flank_y * 0.62 if trade != "barber" else flank_y * 0.62, 1.88))
    # Galvanized iron accordion folding security gate pushed open at doorway jambs (barber, dentist & tv shops!)
    if trade in ("barber", "dentist_salon", "tv_coffee"):
        for sgn in (-1, 1):
            _add_accordion_gate(bm_iron, 0.02, sgn * (door_w * 0.50), 0.19, 2.52, sgn)
    for sgn in (-1, 1):
        _box_bm(wall_bm, (0.0, sgn * flank_y, 1.80), (0.10, flank_w, 3.34))
    # Upper wooden-baluster ventilation transom above the shopfront doorway (iconic Khmer shophouse detail!)
    _box_bm(bm_posts, (0.0, 0.0, 2.62), (0.12, door_w + 0.12, 0.10))
    _box_bm(bm_posts, (0.0, 0.0, 3.44), (0.12, door_w + 0.12, 0.14))
    n_bars = max(5, int(door_w / 0.18))
    for kb in range(n_bars):
        by = -door_w * 0.46 + kb * (door_w * 0.92 / max(1, n_bars - 1))
        _box_bm(bm_shut, (0.0, by, 3.03), (0.036, 0.036, 0.78))

    # 4-panel louvered folding Khmer shopfront doors (wide folded open on active shops, nearly shut on outpost!)
    if open_front and not dim_outpost:
        for sgn in (-1, 1):
            hy = sgn * (door_w * 0.5)
            # First leaf angled out 72 deg + second leaf folded accordion-style
            ang1 = math.radians(72 * sgn)
            ang2 = math.radians(108 * sgn)
            _box_bm(bm_shut, (0.22, hy - sgn * 0.06, 1.38), (0.055, 0.46, 2.38), rot=Euler((0, 0, ang1)))
            _box_bm(bm_shut, (0.58, hy + sgn * 0.02, 1.38), (0.055, 0.44, 2.38), rot=Euler((0, 0, ang2)))
            # Louver slats along each door leaf for crisp specular texture in headlights
            for lv in range(8):
                lz = 0.72 + lv * 0.20
                _box_bm(bm_posts, (0.22, hy - sgn * 0.06, lz), (0.07, 0.36, 0.025), rot=Euler((0, 0, ang1)))
    elif dim_outpost:
        # Almost shut storm doors with a haunting warm 34 cm amber crack spilling out into the rain!
        _box_bm(bm_shut, (0.04, -0.56, 1.38), (0.06, 0.78, 2.38))
        _box_bm(bm_shut, (0.12, 0.56, 1.38), (0.06, 0.78, 2.38), rot=Euler((0, 0, math.radians(-18))))
        # Wooden bar across left closed shutter
        _box_bm(bm_posts, (0.10, -0.56, 1.32), (0.05, 0.85, 0.08))
    else:
        # Counter stall (Shop 2 TV/Coffee): lower wood wainscot wall + propped-up overhead wood awning shutter!
        _box_bm(bm_walls, (0.0, 0.0, 0.58), (0.12, door_w, 0.90))
        _box_bm(bm_posts, (0.14, 0.0, 1.04), (0.48, door_w + 0.16, 0.065))  # Wide serving counter!
        _box_bm(bm_shut, (0.64, 0.0, 2.32), (1.38, door_w, 0.055), rot=Euler((0, math.radians(24), 0)))
        for py_p in (-door_w * 0.44, door_w * 0.44):
            _cyl_bm(bm_bamboo, (0.34, py_p, 1.06), (1.22, py_p, 2.04), 0.022, 0.020, segs=6)

    # Rolled woven split-bamboo rain-blind tucked under the veranda eaves + hanging cords
    _cyl_bm(bm_bamboo_wall, (1.80, -hw * 0.95, 2.40), (1.80, hw * 0.95, 2.40), 0.062, 0.062, segs=10)
    if dim_outpost or trade in ("salon", "grocery"):
        # Partially unrolled split-bamboo rain curtain shielding one veranda bay from monsoon rain!
        curt_y = hw * 0.56 if trade != "salon" else -hw * 0.54
        _box_bm(bm_bamboo_wall, (1.76, curt_y, 1.88), (0.022, hw * 0.78, 1.02))
        for sl in range(6):
            _box_bm(bm_posts, (1.77, curt_y, 1.44 + sl * 0.17), (0.032, hw * 0.79, 0.016))

    # Curved catenary-sagging Cambodian blue monsoon vinyl rain tarp with bamboo props & taut guy-ropes!
    if has_tarp:
        _add_catenary_tarp(bm_blue, bm_bamboo, bm_wire_local, 1.72, 2.52, -hw * 0.96, -0.02, 2.46, 2.10)
    # Warm sagging festoon string of miniature glowing café/wedding-band bulbs across eaves of Noodle & Grocery shops!
    if trade in ("noodle", "grocery"):
        _add_festoon_lights(bm_wire_local, bm_bulb, (1.86, -hw * 0.94, 2.38), (1.86, hw * 0.94, 2.38), n_bulbs=7, sag=0.16)

    # 4. DETAILED VISIBLE INTERIOR & TRADE-SPECIFIC REALISM PROPS (EACH SHOP COMPLETELY UNIQUE!)
    # Interior warm wooden ceiling beam & rear workbench/table shared base
    _box_bm(bm_posts, (-1.62, 0.0, 3.12), (0.12, hw * 1.98, 0.14))

    if trade == "noodle":
        # SHOP 0: CAMBODIAN ROADSIDE KUY TEAV NOODLE & ICED COFFEE CART/STALL!
        # Iconic illuminated glass-front Khmer noodle display cart on front veranda edge!
        nx, ny, nz = 1.05, 0.35, 0.17
        # Lower painted steel/wood cart cabinet + wheels
        _box_bm(bm_blue, (nx, ny, nz + 0.46), (0.66, 1.48, 0.76), bevel=0.01, segs=1)
        _box_bm(bm_white, (nx, ny, nz + 0.86), (0.72, 1.54, 0.055))
        for wy in (ny - 0.58, ny + 0.58):
            _torus_bm(bm_rubber, (nx + 0.26, wy, nz + 0.10), (0, 1, 0), 0.10, 0.025, n_maj=10, n_min=5)
        # Glowing warm amber glass-front noodle showcase box with aluminum corner rails & stacked bowls inside!
        _box_bm(bm_noodle_glow, (nx + 0.04, ny - 0.18, nz + 1.26), (0.48, 0.84, 0.74))
        for dx_c in (-0.25, 0.25):
            for dy_c in (-0.43, 0.43):
                _box_bm(bm_iron, (nx + 0.04 + dx_c, ny - 0.18 + dy_c, nz + 1.26), (0.032, 0.032, 0.78))
        _box_bm(bm_iron, (nx + 0.04, ny - 0.18, nz + 1.64), (0.54, 0.90, 0.045))
        # Stacked white ceramic noodle bowls & hanging red BBQ pork strips visible along showcase!
        for bs_i in range(4):
            _cyl_bm(bm_white, (nx + 0.06, ny + 0.45, nz + 0.89 + bs_i * 0.055), (nx + 0.06, ny + 0.45, nz + 0.94 + bs_i * 0.055), 0.075, 0.095, segs=9)
        # Big stainless broth cauldron pot steaming on side burner + galvanized exhaust hood & red gas cylinder!
        _cyl_bm(bm_iron, (nx - 0.02, ny + 0.98, nz + 0.48), (nx - 0.02, ny + 0.98, nz + 0.98), 0.24, 0.25, segs=12)
        _cyl_bm(bm_iron, (nx - 0.02, ny + 0.98, nz + 1.56), (nx - 0.02, ny + 0.98, nz + 1.88), 0.34, 0.10, segs=10)
        _cyl_bm(bm_iron, (nx - 0.02, ny + 0.98, nz + 1.88), (nx - 0.02, ny + 0.98, nz + 2.62), 0.09, 0.09, segs=8)
        _cyl_bm(bm_red, (nx - 0.06, ny + 1.48, nz), (nx - 0.06, ny + 1.48, nz + 0.56), 0.155, 0.155, segs=12)
        _cyl_bm(bm_iron, (nx - 0.06, ny + 1.48, nz + 0.56), (nx - 0.06, ny + 1.48, nz + 0.66), 0.075, 0.065, segs=8)
        # Iconic blue plastic roadside ice cooler chest + stacked red/blue Cambodian soda crates with glass bottles!
        _box_bm(bm_blue, (0.72, 1.88, nz + 0.24), (0.46, 0.68, 0.46), bevel=0.015, segs=1)
        _box_bm(bm_white, (0.72, 1.88, nz + 0.48), (0.48, 0.70, 0.045), bevel=0.008, segs=1)
        _add_plastic_crate(bm_red, bm_amber, bm_green, (1.42, 1.92, nz), rot_z=0.14, filled=True)
        _add_plastic_crate(bm_blue, bm_amber, bm_green, (1.44, 1.90, nz + 0.28), rot_z=-0.08, filled=True)
        # Hanging red-glazed roast duck/pork strips inside showcase + soup ladle in broth cauldron!
        for hy_p in (-0.32, -0.18, -0.04):
            _cyl_bm(bm_red, (nx + 0.04, ny + hy_p, nz + 1.56), (nx + 0.04, ny + hy_p, nz + 1.24), 0.042, 0.032, segs=7)
        _cyl_bm(bm_iron, (nx + 0.02, ny + 0.96, nz + 0.92), (nx + 0.18, ny + 0.88, nz + 1.32), 0.010, 0.008, segs=6)
        # Folding weathered-wood dining table + condiment jars + 3 red plastic stools + interior shelving!
        _box_bm(bm_table_wood, (0.98, -1.42, nz + 0.72), (0.76, 1.02, 0.045))
        for lx in (0.66, 1.30):
            for ly in (-1.86, -0.98):
                _box_bm(bm_posts, (lx, ly, nz + 0.36), (0.05, 0.05, 0.72))
        _add_bottles_row(bm_amber, bm_green, bm_red, (0.98, -1.68, nz + 0.75), (0, 0.13, 0), 5, seed=701)
        for sx_s, sy_s in [(1.46, -1.42), (0.98, -2.06), (0.98, -0.78)]:
            _add_stool(bm_red, bm_posts, (sx_s, sy_s, nz), red_plastic=True)
        _add_banana_bunch(bm_green, bm_amber, bm_bamboo, (1.56, -0.65, 2.24), seed=711)
        _add_shelf_unit(bm_posts, bm_amber, bm_green, bm_red, (-2.85, 0.0, 0.18), width=2.45, height=1.88, depth=0.38, seed=720)

    elif trade == "barber":
        # SHOP 1: CHEANG LENG 1990s KHMER BARBER SHOP!
        # Classic striped red-white-blue Cambodian barber pole on front roadside corner post!
        bp = Vector((1.88, hw - 0.06, 1.56))
        _cyl_bm(bm_iron, bp + Vector((0, 0, -0.44)), bp + Vector((0, 0, -0.37)), 0.072, 0.062, segs=12)
        _cyl_bm(bm_iron, bp + Vector((0, 0, 0.37)), bp + Vector((0, 0, 0.44)), 0.062, 0.072, segs=12)
        _cyl_bm(bm_white, bp + Vector((0, 0, -0.37)), bp + Vector((0, 0, 0.37)), 0.056, 0.056, segs=12)
        for st in range(7):
            sz = -0.32 + st * 0.105
            bm_c = bm_red if st % 2 == 0 else bm_blue
            _cyl_bm(bm_c, bp + Vector((0, 0, sz)), bp + Vector((0, 0, sz + 0.055)), 0.059, 0.059, segs=12)
        # Interior wide framed wall mirror + vanity shelf + folded white barber towels + tonic bottles!
        _box_bm(bm_posts, (-3.14, 0.0, 1.72), (0.06, 2.35, 1.18))
        _box_bm(bm_mirror, (-3.10, 0.0, 1.72), (0.02, 2.18, 1.02))
        _box_bm(bm_posts, (-2.94, 0.0, 1.02), (0.38, 2.48, 0.05))
        _add_bottles_row(bm_amber, bm_green, bm_red, (-2.88, -0.88, 1.05), (0, 0.16, 0), 9, seed=101)
        for tw in range(4):
            _box_bm(bm_white, (-2.86, 0.86, 1.06 + tw * 0.042), (0.24, 0.30, 0.034), bevel=0.006, segs=1)
        # TWO sculpted vintage leather & chrome barber chairs facing the mirror!
        for cx, cy in [(-1.78, -0.52), (-1.78, 0.62)]:
            _cyl_bm(bm_iron, (cx, cy, 0.18), (cx, cy, 0.25), 0.28, 0.22, segs=12)
            _cyl_bm(bm_iron, (cx, cy, 0.25), (cx, cy, 0.62), 0.062, 0.055, segs=10)
            _box_bm(bm_red, (cx, cy, 0.68), (0.50, 0.48, 0.11), bevel=0.02, segs=1)
            _box_bm(bm_red, (cx + 0.22, cy, 1.08), (0.11, 0.46, 0.66), rot=Euler((0, math.radians(-14), 0)), bevel=0.02, segs=1)
            _box_bm(bm_red, (cx + 0.30, cy, 1.48), (0.09, 0.22, 0.15), bevel=0.015, segs=1)
            for ay in (-0.26, 0.26):
                _box_bm(bm_iron, (cx + 0.02, cy + ay, 0.88), (0.46, 0.045, 0.042))
            _box_bm(bm_iron, (cx - 0.32, cy, 0.42), (0.22, 0.34, 0.032))
        # Veranda waiting bench + real aged Khmer newspaper + rooftop Yagi TV antenna + 2 red stools
        _box_bm(bm_table_wood, (1.05, -1.55, 0.52), (0.40, 1.52, 0.055))
        for by in (-2.12, -0.98):
            _box_bm(bm_posts, (1.05, by, 0.33), (0.34, 0.07, 0.38))
        _box_bm(bm_news, (1.05, -1.35, 0.556), (0.26, 0.34, 0.014))  # Real aged newspaper on waiting bench!
        _add_stool(bm_red, bm_posts, (0.95, 1.25, 0.17), red_plastic=True)
        _add_stool(bm_red, bm_posts, (1.28, 1.68, 0.17), red_plastic=True)
        _add_tv_antenna(bm_iron, (-0.22, -hw * 0.72, 3.68))
        # Interior hairstyle chart poster hung right beside the barber mirror!
        _add_poster_to_lists(p_verts, p_faces, p_uvs, to_w((-3.16, 1.56, 1.78)), dir_w((0, 1, 0)), dir_w((0, 0, 1)), 0.86, 0.96, 11, seed=901)

    elif trade == "dentist_salon":
        # SHOP 2: KIM CHENG DENTIST & RACHANA BEAUTY SALON TWIN COLONIAL SHOPHOUSE!
        # Veranda X-braced timber railings + decorative colonial eaves fretwork spindles!
        for sgn in (-1, 1):
            ry = sgn * (hw * 0.64)
            _box_bm(bm_posts, (1.75, ry, 0.92), (0.08, hw * 0.72, 0.07))
            _box_bm(bm_posts, (1.75, ry, 0.30), (0.07, hw * 0.72, 0.06))
            _box_bm(bm_posts, (1.75, ry, 0.61), (0.05, hw * 0.68, 0.05), rot=Euler((math.radians(28), 0, 0)))
            _box_bm(bm_posts, (1.75, ry, 0.61), (0.05, hw * 0.68, 0.05), rot=Euler((math.radians(-28), 0, 0)))
        for sp_k in range(11):
            sy_f = -hw * 0.90 + sp_k * (hw * 1.80 / 10.0)
            _box_bm(bm_posts, (1.75, sy_f, 2.34), (0.036, 0.036, 0.24))
        # Illuminated backlit glass dental/apothecary display vitrine facing front + medicine shelves!
        _box_bm(bm_white, (-1.85, -0.95, 0.56), (0.64, 1.24, 0.78))
        _box_bm(bm_win_glow, (-1.82, -0.95, 1.24), (0.50, 1.12, 0.56))
        for dx_v in (-0.26, 0.26):
            for dy_v in (-0.57, 0.57):
                _box_bm(bm_iron, (-1.82 + dx_v, -0.95 + dy_v, 1.24), (0.028, 0.028, 0.60))
        _add_shelf_unit(bm_posts, bm_amber, bm_green, bm_red, (-2.85, -1.25, 0.18), width=1.55, height=1.88, depth=0.38, seed=201)
        _box_bm(bm_posts, (-3.14, 0.95, 1.72), (0.06, 1.25, 1.10))
        _box_bm(bm_mirror, (-3.10, 0.95, 1.72), (0.02, 1.12, 0.96))
        _add_bottles_row(bm_amber, bm_green, bm_white, (-1.70, -1.42, 1.54), (0, 0.15, 0), 7, seed=209)
        # Vintage salon wheeled hooded hair-dryer + clinical enamel washbasin on tripod stand!
        _add_hair_dryer_stand(bm_iron, bm_white, (-1.45, 1.22, 0.18))
        _cyl_bm(bm_white, (-0.92, -1.55, 0.78), (-0.92, -1.55, 0.92), 0.14, 0.21, segs=10)
        for ta in range(3):
            ang = ta * math.tau / 3.0
            _cyl_bm(bm_iron, (-0.92 + math.cos(ang) * 0.22, -1.55 + math.sin(ang) * 0.22, 0.18),
                    (-0.92 + math.cos(ang) * 0.12, -1.55 + math.sin(ang) * 0.12, 0.84), 0.014, 0.012, segs=6)
        _add_stool(bm_red, bm_posts, (-1.95, 0.82, 0.18), red_plastic=True)
        _add_stool(bm_red, bm_posts, (1.02, -1.65, 0.17), red_plastic=False)
        _add_crate(bm_posts, (1.12, 1.95, 0.17), (0.52, 0.42, 0.36), rot_z=0.22)
        # Authentic woven Khmer checkered krama draped over the colonial veranda rail!
        _box_bm(bm_krama, (1.76, -1.65, 0.82), (0.14, 0.46, 0.34))
        # Hanging decorative bamboo birdcage under the veranda eave
        bc = Vector((1.28, 1.48, 2.02))
        _cyl_bm(bm_bamboo, bc + Vector((0, 0, 0.22)), bc + Vector((0, 0, 0.56)), 0.008, 0.008, segs=6)
        _cyl_bm(bm_bamboo, bc - Vector((0, 0, 0.18)), bc + Vector((0, 0, 0.22)), 0.16, 0.13, segs=10)

    elif trade == "tv_coffee":
        # SHOP 3: CHANTRA ELECTRONICS / CRT TV / WATCH REPAIR & ROADSIDE COFFEE COUNTER!
        # Interior repair workbench with TWO vintage CRT TVs + glowing articulated swing-arm bench lamp!
        _box_bm(bm_posts, (-2.65, 0.0, 0.94), (0.78, 2.55, 0.065))
        for ly in (-1.15, 1.15):
            for lx in (-2.96, -2.34):
                _box_bm(bm_posts, (lx, ly, 0.54), (0.07, 0.07, 0.78))
        # Primary glowing blue-cyan CRT television facing out toward the open road!
        _box_bm(bm_iron, (-2.52, -0.42, 1.24), (0.44, 0.56, 0.46), rot=Euler((0, 0, 0.16)), bevel=0.015, segs=1)
        _box_bm(bm_crt, (-2.29, -0.38, 1.25), (0.04, 0.40, 0.32), rot=Euler((0, 0, 0.16)))
        # Second boxy CRT television stacked slightly askew with open rear service chassis + boombox!
        _box_bm(bm_iron, (-2.58, 0.38, 1.19), (0.38, 0.48, 0.38), rot=Euler((0, 0, -0.22)), bevel=0.012, segs=1)
        _box_bm(bm_amber, (-2.38, 0.34, 1.20), (0.03, 0.32, 0.24), rot=Euler((0, 0, -0.22)))
        # Articulated swing-arm electronics bench lamp glowing over the CRT repair mat
        _cyl_bm(bm_iron, (-2.85, -0.95, 0.96), (-2.62, -0.78, 1.48), 0.011, 0.011, segs=6)
        _cyl_bm(bm_iron, (-2.62, -0.78, 1.48), (-2.42, -0.58, 1.62), 0.010, 0.010, segs=6)
        _cyl_bm(bm_shade, (-2.42, -0.58, 1.62), (-2.36, -0.52, 1.48), 0.025, 0.095, segs=10)
        bmesh.ops.create_uvsphere(bm_bulb, u_segments=8, v_segments=5, radius=0.032, matrix=Matrix.Translation((-2.38, -0.54, 1.50)))
        _box_bm(bm_red, (-2.60, 0.98, 1.08), (0.30, 0.24, 0.18))
        # Open oscilloscope/multimeter test box + coiled black antenna cables on electronics repair bench!
        _box_bm(bm_iron, (-2.54, -1.04, 1.12), (0.26, 0.28, 0.22), rot=Euler((0, 0, 0.28)))
        _box_bm(bm_crt, (-2.40, -1.02, 1.14), (0.02, 0.12, 0.09), rot=Euler((0, 0, 0.28)))
        _torus_bm(bm_wire_local, (-2.42, 0.84, 0.99), (0, 0, 1), 0.095, 0.012, n_maj=10, n_min=5)
        _box_bm(bm_news, (0.16, -1.16, 1.082), (0.24, 0.32, 0.012), rot=Euler((0, 0, 0.15)))
        # Wall-mounted parts shelf behind workbench
        _add_shelf_unit(bm_posts, bm_amber, bm_green, bm_red, (-3.05, 0.10, 1.48), width=2.2, height=1.25, depth=0.28, seed=301)
        # Illuminated glass watchmaker counter showcase right on the front serving counter + coffee tins!
        _box_bm(bm_noodle_glow, (0.14, 0.52, 1.22), (0.38, 0.68, 0.28))
        _box_bm(bm_iron, (0.14, 0.52, 1.37), (0.42, 0.72, 0.025))
        _add_bottles_row(bm_amber, bm_green, bm_white, (0.16, -0.78, 1.08), (0, 0.16, 0), 6, seed=310)
        for sy_s in (-0.68, 0.0, 0.68):
            _add_stool(bm_red, bm_posts, (0.86, sy_s, 0.17), red_plastic=(sy_s != 0.0))
        _add_plastic_crate(bm_blue, bm_amber, bm_green, (1.18, -1.78, 0.17), rot_z=-0.18, filled=True)
        # Tall aluminum Yagi rooftop TV antenna bolted right above the electronics shop!
        _add_tv_antenna(bm_iron, (0.18, hw * 0.78, 3.68))

    elif trade == "moto":
        # SHOP 4: PONLEU PICH MOTORCYCLE REPAIR & ROADSIDE GLASS PETROL-BOTTLE STAND!
        # Iconic Cambodian wooden roadside petrol-bottle rack with 8 tall golden gasoline bottles!
        rx, ry, rz = 1.62, -1.28, 0.17
        _box_bm(bm_posts, (rx, ry, rz + 0.48), (0.28, 1.18, 0.04))
        _box_bm(bm_posts, (rx, ry, rz + 0.90), (0.28, 1.18, 0.04))
        _box_bm(bm_posts, (rx, ry, rz + 1.06), (0.04, 1.18, 0.06))
        for dy in (-0.55, 0.55):
            _box_bm(bm_posts, (rx, ry + dy, rz + 0.56), (0.26, 0.045, 1.12))
        for k in range(8):
            by = ry - 0.455 + k * 0.13
            _cyl_bm(bm_amber, (rx, by, rz + 0.51), (rx, by, rz + 0.74), 0.042, 0.040, segs=8)
            _cyl_bm(bm_white, (rx, by, rz + 0.74), (rx, by, rz + 0.85), 0.019, 0.015, segs=7)
            _cyl_bm(bm_red, (rx, by, rz + 0.85), (rx, by, rz + 0.88), 0.017, 0.017, segs=6)
        # HERO PROP: Sculpted vintage Cambodian Honda-Cub-style motorbike on center stand on the veranda apron!
        _add_motorbike(bm_iron, bm_rubber, bm_blue, bm_white, bm_red, (0.88, 0.35, 0.17), yaw=math.radians(34))
        # Stack of 4 weathered black rubber motorcycle tires leaning at front corner!
        for k in range(4):
            _torus_bm(bm_rubber, (1.15 - k * 0.04, 1.82, 0.25 + k * 0.13), (0.08 * (k % 2), 0.06, 1.0), 0.27, 0.068, n_maj=14, n_min=7)
        # Hanging spoked motorcycle wheel on the front veranda post!
        _torus_bm(bm_rubber, (0.14, 1.85, 1.85), (1.0, 0.0, 0.0), 0.26, 0.045, n_maj=14, n_min=7)
        _torus_bm(bm_iron, (0.14, 1.85, 1.85), (1.0, 0.0, 0.0), 0.21, 0.016, n_maj=14, n_min=6)
        for sp in range(6):
            a = sp / 6.0 * math.pi
            _cyl_bm(bm_iron, (0.14, 1.85 - math.cos(a) * 0.21, 1.85 - math.sin(a) * 0.21),
                    (0.14, 1.85 + math.cos(a) * 0.21, 1.85 + math.sin(a) * 0.21), 0.006, 0.006, segs=5)
        # Twin weathered ribbed 200-liter oil drums (blue & red!) + mechanic workbench & wrench pegboard!
        for dx_d, dy_d, bm_d in [(1.02, -2.12, bm_blue), (0.45, -2.28, bm_red)]:
            _cyl_bm(bm_d, (dx_d, dy_d, 0.17), (dx_d, dy_d, 1.06), 0.28, 0.28, segs=12)
            for hz in (0.44, 0.78):
                _cyl_bm(bm_d, (dx_d, dy_d, hz), (dx_d, dy_d, hz + 0.04), 0.295, 0.295, segs=12)
        _box_bm(bm_posts, (-2.55, 0.0, 0.90), (0.82, 2.85, 0.07))
        _box_bm(bm_red, (-2.35, -0.62, 1.06), (0.34, 0.56, 0.24), bevel=0.01, segs=1)
        _box_bm(bm_blue, (-2.42, 0.65, 1.12), (0.28, 0.20, 0.36))
        # Wall wrench pegboard behind workbench
        _box_bm(bm_posts, (-3.16, 0.0, 1.75), (0.04, 1.55, 0.76))
        for wk in range(8):
            wy = -0.60 + wk * 0.17
            _box_bm(bm_iron, (-3.12, wy, 1.72), (0.02, 0.032, 0.22 + (wk % 3) * 0.09))
        _add_bottles_row(bm_amber, bm_green, bm_red, (-2.38, -0.05, 0.95), (0, 0.12, 0), 5, seed=401)
        _add_stool(bm_red, bm_posts, (-0.95, 0.45, 0.18), red_plastic=True)
        _add_galvanized_bucket(bm_iron, (1.42, 1.25, 0.17))
        # Red cylindrical garage air compressor with coiled black hose + wooden roadside A-frame petrol sign!
        _add_air_compressor(bm_red, bm_iron, bm_rubber, (-1.28, -1.68, 0.18))
        _box_bm(bm_table_wood, (2.22, -1.58, 0.42), (0.04, 0.46, 0.68), rot=Euler((0, math.radians(-14), 0.12)))
        _box_bm(bm_table_wood, (2.42, -1.58, 0.42), (0.04, 0.46, 0.68), rot=Euler((0, math.radians(14), 0.12)))
        # Vertical hand air-pump beside oil drum + weathered vintage bicycle parked at shop corner!
        _cyl_bm(bm_red, (1.35, -1.78, 0.17), (1.35, -1.78, 0.72), 0.024, 0.024, segs=8)
        _cyl_bm(bm_iron, (1.35, -1.90, 0.74), (1.35, -1.66, 0.74), 0.014, 0.014, segs=6)
        _add_bicycle(bm_iron, bm_rubber, bm_bamboo, (2.15, 2.22, -0.25), yaw=math.radians(82))

    elif trade == "grocery":
        # SHOP 5: PONLEU THMEY WEDDING BAND & VILLAGE DRY-GOODS GENERAL STORE!
        # Horizontal bamboo veranda pole with organic hanging banana bunches, reed brooms, coiled rope & natural snack strips!
        _cyl_bm(bm_bamboo, (1.58, -hw * 0.88, 2.26), (1.58, hw * 0.88, 2.26), 0.022, 0.022, segs=6)
        _add_banana_bunch(bm_green, bm_amber, bm_bamboo, (1.58, -1.75, 2.22), seed=511)
        _add_banana_bunch(bm_green, bm_amber, bm_bamboo, (1.58, 1.56, 2.22), seed=512)
        _add_hanging_brooms(bm_bamboo, bm_posts, (1.56, -0.96, 2.24))
        # 4 organic asymmetrical hanging snack sachet clusters (varied lengths & angles, zero grid!)
        for hy, n_t, bm_pkt, tilt in [
            (-0.34, 3, bm_red, 0.24), (0.64, 4, bm_amber, -0.18), (0.94, 3, bm_white, 0.22), (1.20, 2, bm_blue, -0.14),
        ]:
            for tier in range(n_t):
                _box_bm(bm_pkt, (1.58 + 0.02 * (tier % 2), hy, 2.12 - tier * 0.14), (0.03, 0.095, 0.105),
                        rot=Euler((0.06 * tier, 0.08 * (tier % 2), tilt)))
        # TWO tall stacked twin-woofer Cambodian wedding-band PA loudspeaker cabinets + amplifier head!
        for ly, yaw_s in [(-1.38, 0.24), (-0.52, 0.12)]:
            for lz_add in (0.0, 0.76):
                _box_bm(bm_iron, (-1.62, ly, 0.56 + lz_add), (0.52, 0.62, 0.72), rot=Euler((0, 0, yaw_s)), bevel=0.015, segs=1)
                _cyl_bm(bm_rubber, (-1.35, ly + 0.04, 0.56 + lz_add), (-1.33, ly + 0.04, 0.56 + lz_add), 0.21, 0.21, segs=12)
        _box_bm(bm_iron, (-1.62, -0.52, 1.82), (0.44, 0.54, 0.22), rot=Euler((0, 0, 0.12)))  # PA Amp head
        _box_bm(bm_crt, (-1.39, -0.52, 1.84), (0.02, 0.18, 0.06), rot=Euler((0, 0, 0.12)))  # Glowing VU meter!
        # 3-tier stocked village grocery shelving + folding worn-wood veranda tea table + rolled kantel mats + soda crates!
        _add_shelf_unit(bm_posts, bm_amber, bm_green, bm_red, (-2.88, 0.75, 0.18), width=2.35, height=1.95, depth=0.40, seed=501)
        _box_bm(bm_table_wood, (1.05, 1.15, 0.76), (0.62, 0.88, 0.045))
        for k_m in range(3):
            _cyl_bm(bm_kantel, (0.32 + k_m * 0.11, -2.35, 0.18), (0.28 + k_m * 0.11, -2.35, 1.48), 0.055, 0.055, segs=10)
        for lx in (0.78, 1.32):
            for ly in (0.76, 1.54):
                _box_bm(bm_posts, (lx, ly, 0.46), (0.048, 0.048, 0.58))
        _add_bottles_row(bm_amber, bm_green, bm_white, (1.05, 0.90, 0.79), (0, 0.14, 0), 4, seed=530)
        _add_plastic_crate(bm_red, bm_amber, bm_green, (1.08, -1.78, 0.17), rot_z=0.18, filled=True)
        _add_plastic_crate(bm_blue, bm_amber, bm_green, (1.10, -1.74, 0.45), rot_z=-0.12, filled=True)
        _add_galvanized_bucket(bm_iron, (1.52, 2.02, 0.17))
        _add_stool(bm_red, bm_posts, (0.98, 0.45, 0.17), red_plastic=True)
        _add_stool(bm_red, bm_posts, (1.28, 1.72, 0.17), red_plastic=True)

    elif trade == "salon":
        # SHOP 6: MALIN & CHANTRA BRIDAL TAILOR & STILT CORNER SALON!
        _box_bm(bm_posts, (-3.14, 0.0, 1.72), (0.06, 1.48, 1.08))
        _box_bm(bm_mirror, (-3.10, 0.0, 1.72), (0.02, 1.34, 0.94))
        _box_bm(bm_posts, (-2.88, 0.0, 0.96), (0.44, 1.65, 0.05))
        _add_bottles_row(bm_amber, bm_green, bm_red, (-2.82, -0.65, 0.99), (0, 0.17, 0), 8, seed=601)
        _add_shelf_unit(bm_posts, bm_amber, bm_green, bm_red, (-2.75, 1.68, 0.18), width=1.25, height=1.75, depth=0.34, seed=610)
        # Vintage treadle sewing machine draped in real Khmer patterned hol silk + tailor's dress-form + kantel mats!
        _add_sewing_machine(bm_table_wood, bm_iron, bm_hol_silk, (-1.28, -1.42, 0.18))
        _add_dress_form(bm_posts, bm_hol_silk, (-1.12, 1.38, 0.18))
        for sb_k in range(3):
            _cyl_bm(bm_hol_silk, (-2.72, 1.25 + sb_k * 0.16, 1.44), (-2.72, 1.25 + sb_k * 0.16, 1.76), 0.058, 0.058, segs=10)
        _cyl_bm(bm_kantel, (0.48, 2.12, 0.18), (0.44, 2.12, 1.42), 0.056, 0.056, segs=10)
        _add_hair_dryer_stand(bm_iron, bm_white, (-1.75, 0.72, 0.18))
        _box_bm(bm_white, (0.06, 0.74, 1.38), (0.05, 0.42, 2.34), rot=Euler((0, 0, 0.14)))  # Parted cream salon curtain
        _add_stool(bm_red, bm_posts, (-1.85, -0.15, 0.18), red_plastic=True)
        # Carved veranda spindle railing on left half + worn-wood bench + real checkered krama + crate + parked bicycle!
        _box_bm(bm_posts, (1.75, 1.52, 0.88), (0.07, 1.85, 0.06))
        for ks in range(7):
            _box_bm(bm_posts, (1.75, 0.72 + ks * 0.26, 0.52), (0.036, 0.036, 0.68))
        _box_bm(bm_table_wood, (1.02, 1.42, 0.52), (0.38, 1.45, 0.055))
        for by in (0.85, 1.98):
            _box_bm(bm_posts, (1.02, by, 0.33), (0.32, 0.07, 0.38))
        _box_bm(bm_krama, (1.04, 1.55, 0.575), (0.34, 0.44, 0.045))
        _add_crate(bm_posts, (0.92, -1.78, 0.17), (0.46, 0.38, 0.32), rot_z=0.35)
        _add_bicycle(bm_iron, bm_rubber, bm_bamboo, (2.10, -2.05, -0.25), yaw=math.radians(-78))

    else:
        # SHOP 7: LONELY HALF-SHUTTERED JUNGLE-EDGE OUTPOST!
        # Warm glowing amber crack spilling through the slightly ajar storm doors + iron padlock hasp!
        _box_bm(bm_win_glow, (-0.02, 0.06, 1.38), (0.04, 0.28, 2.28))
        _box_bm(bm_iron, (0.12, -0.14, 1.32), (0.06, 0.09, 0.11))
        # Veranda table with upturned red stool stacked for the storm + galvanized rain-drip bucket + leaning bamboo ladder!
        _box_bm(bm_posts, (1.05, 1.35, 0.78), (0.68, 1.05, 0.05))
        for lx in (0.76, 1.34):
            for ly in (0.88, 1.82):
                _box_bm(bm_posts, (lx, ly, 0.47), (0.055, 0.055, 0.62))
        _box_bm(bm_red, (1.05, 1.25, 0.82), (0.28, 0.28, 0.032))
        for dx in (-0.10, 0.10):
            for dy in (-0.10, 0.10):
                _cyl_bm(bm_red, (1.05 + dx, 1.25 + dy, 0.84), (1.05 + dx * 1.15, 1.25 + dy * 1.15, 1.20), 0.015, 0.014, segs=6)
        _add_galvanized_bucket(bm_iron, (1.68, hw - 0.12, 0.17))
        # Weathered bamboo ladder leaning against the shop's side roof eave!
        lad_y = -hw - 0.18
        for dx_l in (-0.22, 0.22):
            _cyl_bm(bm_bamboo, (-1.15 + dx_l, lad_y - 0.55, -0.35), (-1.15 + dx_l, lad_y + 0.08, 3.05), 0.026, 0.024, segs=6)
        for rg in range(8):
            f = (rg + 1) / 9.0
            _cyl_bm(bm_bamboo, (-1.37, lad_y - 0.55 + f * 0.63, -0.35 + f * 3.40), (-0.93, lad_y - 0.55 + f * 0.63, -0.35 + f * 3.40), 0.016, 0.016, segs=6)
        _add_crate(bm_posts, (0.95, -1.65, 0.17), (0.50, 0.40, 0.34), rot_z=-0.28)

    # 5. LIGHTING FIXTURES (VERANDA PENDANT + INTERIOR LAMP/FLUORESCENT + GOOSENECK SIGN LAMP)
    # Main hanging enamel pendant lamp under front veranda awning + runtime PointLight anchor!
    _add_pendant_lamp(bm_iron, bm_shade, bm_bulb, (1.08, 0.10, 3.04), drop=0.62)
    anc_ext = bpy.data.objects.new(f"taxi_road_anchor_shop_lamp_{shop_idx}", None)
    coll.objects.link(anc_ext)
    anc_ext.location = to_w((1.12, 0.10, 2.34))

    # Interior practical lamp (either cool-white fluorescent tube bar or warm hanging tungsten bulb!)
    if has_fluoro:
        _box_bm(bm_iron, (-1.45, 0.0, 2.86), (0.09, 1.28, 0.055))
        _cyl_bm(bm_fluoro, (-1.45, -0.58, 2.81), (-1.45, 0.58, 2.81), 0.022, 0.022, segs=8)
    else:
        _add_pendant_lamp(bm_iron, bm_shade, bm_bulb, (-1.55, 0.0, 3.12), drop=0.58)
    anc_int = bpy.data.objects.new(f"taxi_road_anchor_shop_int_lamp_{shop_idx}", None)
    coll.objects.link(anc_int)
    anc_int.location = to_w((-1.42, 0.0, 2.36))

    # Overhead fascia signboard frame mounted proudly on the front veranda eave + gooseneck lamp!
    _box_bm(bm_posts, (2.12, 0.0, 2.86), (0.08, 2.38, 0.88), bevel=0.01, segs=1)
    _add_gooseneck_lamp(bm_iron, bm_shade, bm_bulb, (2.14, 0.0, 3.30), (1, 0, 0), drop_z=-0.12, reach=0.46)

    # Perpendicular double-sided protruding roadside hanging bracket sign jutting toward the road!
    # Mounted on the approaching corner post so oncoming headlights catch the hand-painted Khmer sign head-on!
    bs_y = hw * 0.96
    _box_bm(bm_iron, (2.36, bs_y, 2.52), (1.18, 0.04, 0.04))  # Top iron cantilever arm
    _cyl_bm(bm_iron, (1.82, bs_y, 2.12), (2.52, bs_y, 2.52), 0.014, 0.014, segs=6)  # Diagonal iron brace
    _box_bm(bm_posts, (2.42, bs_y, 2.02), (1.02, 0.048, 0.82), bevel=0.008, segs=1)

    # Opposite corner secondary framed signboard + wooden framing moldings for all exterior wall posters!
    _box_bm(bm_posts, (1.76, -hw * 0.96, 2.08), (0.06, 1.06, 0.82))

    # 6. CURATED REAL HAND-PAINTED KHMER 90s SHOP SIGNS & POSTERS (ZERO GENERATED POSTERS!)
    p_hero = spec["posters"]["hero"]
    p_front_l, p_front_r = spec["posters"]["front"]
    p_side_a, p_side_b = spec["posters"]["side"]
    p_hang_a, p_hang_b = spec["posters"]["hang"]

    slots = [
        # Prominent overhead veranda fascia signboard (lit by gooseneck lamp!)
        ((2.172, 0.0, 2.86), (0, 1, 0), (0, 0, 1), 2.22, 0.78, p_hero),
        # Front interior-flank walls (facing road +X)
        ((0.068, -flank_y, 1.92), (0, 1, 0), (0, 0, 1), min(1.08, flank_w * 0.82), 1.24, p_front_l),
        ((0.068, flank_y, 1.92), (0, 1, 0), (0, 0, 1), min(1.08, flank_w * 0.82), 1.24, p_front_r),
        # Protruding perpendicular roadside hanging bracket sign (DOUBLE-SIDED for oncoming approach!)
        ((2.42, bs_y + 0.032, 2.02), (-1, 0, 0), (0, 0, 1), 0.94, 0.74, p_hang_a),
        ((2.42, bs_y - 0.032, 2.02), (1, 0, 0), (0, 0, 1), 0.94, 0.74, p_hang_b),
        # Opposite corner post board facing road
        ((1.802, -hw * 0.96, 2.08), (0, 1, 0), (0, 0, 1), 0.98, 0.74, p_side_a),
        # Approach side walls (+Y and -Y so approaching headlights ALWAYS illuminate two big signs!)
        ((-0.82, hw + 0.068, 1.92), (-1, 0, 0), (0, 0, 1), 0.98, 1.26, p_side_a),
        ((-2.02, hw + 0.068, 1.88), (-1, 0, 0), (0, 0, 1), 0.98, 1.26, p_side_b),
        ((-0.82, -hw - 0.068, 1.92), (1, 0, 0), (0, 0, 1), 0.98, 1.26, p_side_a),
        ((-2.02, -hw - 0.068, 1.88), (1, 0, 0), (0, 0, 1), 0.98, 1.26, p_side_b),
    ]
    if has_parapet:
        # Upper colonial parapet banner sign on Shop 1!
        slots.append(((0.14, 0.0, 3.92), (0, 1, 0), (0, 0, 1), 2.15, 0.48, p_hang_b))
    for i, (lp, lr, lu, pw, ph, pidx) in enumerate(slots):
        # Real 3D framed wooden signboard moldings around wall-mounted signs (never bare pasted quads!)
        if i in (1, 2, 6, 7, 8, 9):
            _add_poster_frame_bm(bm_posts, lp, lr, lu, pw, ph)
        _add_poster_to_lists(
            p_verts, p_faces, p_uvs,
            to_w(lp), dir_w(lr), dir_w(lu),
            pw, ph, pidx, seed=400 + shop_idx * 25 + i,
        )

    # Emit grouped meshes cleanly in world space
    parts = [
        ("posts", bm_posts, mats["dark_wood"], False),
        ("walls", bm_walls, mats["planks"], False),
        ("plaster", bm_paint, mats["plaster"], False),
        ("shutters", bm_shut, mats["shutter"], False),
        ("tin", bm_tin, mats["tin"], True),
        ("brick", bm_brick, mats["brick"], False),
        ("deck", bm_deck, mats["deck"], False),
        ("concrete", bm_concrete, mats["concrete"], False),
        ("clay_tile", bm_clay_tile, mats["clay_tile"], False),
        ("thatch", bm_thatch, mats["thatch"], False),
        ("bamboo_wall", bm_bamboo_wall, mats["bamboo_wall"], False),
        ("table_wood", bm_table_wood, mats["table_wood"], False),
        ("krama", bm_krama, mats["krama"], True),
        ("hol_silk", bm_hol_silk, mats["hol_silk"], True),
        ("news", bm_news, mats["news"], False),
        ("kantel", bm_kantel, mats["kantel"], True),
        ("wire_local", bm_wire_local, mats["wire"], True),
        ("iron", bm_iron, mats["iron"], True),
        ("shade", bm_shade, mats["enamel_green"], True),
        ("bulb", bm_bulb, mats["bulb"], True),
        ("fluoro", bm_fluoro, mats["fluoro"], True),
        ("red_props", bm_red, mats["red_plastic"], True),
        ("blue_props", bm_blue, mats["blue_tarp"], True),
        ("amber_glass", bm_amber, mats["amber_glass"], True),
        ("green_glass", bm_green, mats["green_glass"], True),
        ("white_props", bm_white, mats["white_enamel"], True),
        ("mirror", bm_mirror, mats["mirror"], False),
        ("rubber", bm_rubber, mats["rubber"], True),
        ("crt", bm_crt, mats["crt"], False),
        ("bamboo", bm_bamboo, mats["bamboo"], True),
        ("win_glow", bm_win_glow, mats["win_glow"], False),
        ("noodle_glow", bm_noodle_glow, mats["noodle_glow"], False),
        ("foliage", bm_foliage, mats["foliage"], False),
        ("shrine_glow", bm_shrine_glow, mats["shrine_glow"], True),
    ]
    uv_parts = {
        "posts", "walls", "plaster", "shutters", "tin", "brick", "deck", "concrete",
        "clay_tile", "thatch", "bamboo_wall", "table_wood", "krama", "hol_silk", "news", "kantel",
    }
    for suffix, bm_d, mt, sm in parts:
        _bm_obj(
            f"taxi_road_shop_{shop_idx}_{suffix}",
            bm_d, mt, coll,
            world_uvs_fn=mats["world_uvs"] if suffix in uv_parts else None,
            smooth=sm,
            M_world=M_shop,
        )

    # 7. SCANNED RURAL CAMBODIAN PROPS TUCKED NATURALLY ON THE VERANDA, COUNTERS & UNDER THE EAVES
    # Each tuple: (prop_key, local_pos, euler_xyz, uniform_scale)
    prop_layout = [
        ("water_jar", (1.42, hw - 0.34, 0.18), (0.0, 0.0, 0.25), 1.04),  # Rainwater Ong directly under gutter downspout!
    ]
    if trade == "noodle":
        prop_layout += [
            ("cooking_pot", (0.72, -1.26, 0.50), (0.0, 0.0, 0.40), 0.74),  # Broth pot steaming on clay brazier!
            ("clay_stove", (0.72, -1.26, 0.18), (0.0, 0.0, 0.25), 1.02),
            ("jar_handles", (1.46, -hw + 0.42, 0.18), (0.0, 0.0, -0.60), 0.96),
            ("basket_round", (0.48, 1.56, 0.18), (0.0, 0.0, 0.72), 1.08),
            ("winnowing_tray", (0.34, 1.98, 0.44), (0.0, math.radians(74), -0.18), 0.92),  # Leaning beside wall!
        ]
    elif trade == "barber":
        prop_layout += [
            ("rice_sack", (0.58, 1.62, 0.18), (0.0, 0.0, 0.38), 1.08),
            ("basket_deep", (0.52, -1.92, 0.18), (0.0, 0.0, 0.55), 1.24),
            ("clay_stove", (0.62, -0.82, 0.18), (0.0, 0.0, 0.25), 1.02),
            ("kettle", (0.62, -0.82, 0.50), (0.0, 0.0, -0.55), 1.04),
            ("broom", (1.58, hw - 0.56, 0.18), (0.0, 0.0, -0.45), 1.05),
        ]
    elif trade == "dentist_salon":
        prop_layout += [
            ("basket_deep", (0.52, -2.04, 0.18), (0.0, 0.0, 0.55), 1.28),
            ("jar_handles", (1.36, -hw + 0.46, 0.18), (0.0, 0.0, 0.85), 1.02),
            ("broom", (1.55, hw - 0.62, 0.18), (0.0, 0.0, 0.35), 1.02),
        ]
    elif trade == "tv_coffee":
        prop_layout += [
            ("rice_sack", (0.58, 1.62, 0.18), (0.0, 0.0, 0.38), 1.10),
            ("clay_stove", (0.62, -0.82, 0.18), (0.0, 0.0, 0.25), 1.06),
            ("kettle", (0.22, 0.32, 1.07), (0.0, 0.0, -0.55), 1.05),
            ("cooking_pot", (0.62, -0.82, 0.50), (0.0, 0.0, 0.22), 0.72),
            ("basket_round", (0.98, 1.22, 0.18), (0.0, 0.0, -0.45), 1.05),
        ]
    elif trade == "moto":
        prop_layout += [
            ("jar_handles", (1.42, -hw + 0.48, 0.18), (0.0, 0.0, -0.35), 1.04),
            ("broom", (1.58, hw - 0.58, 0.18), (0.0, 0.0, 0.62), 1.08),
            ("basket_round", (0.48, -1.85, 0.18), (0.0, 0.0, 0.28), 1.02),
        ]
    elif trade == "grocery":
        prop_layout += [
            ("rice_sack", (0.58, 1.62, 0.18), (0.0, 0.0, 0.38), 1.14),
            ("basket_deep", (0.52, -1.92, 0.18), (0.0, 0.0, 0.55), 1.32),
            ("clay_stove", (0.62, -0.82, 0.18), (0.0, 0.0, 0.25), 1.06),
            ("cooking_pot", (0.62, -0.82, 0.50), (0.0, 0.0, -0.30), 0.76),
            ("basket_round", (1.16, 1.35, 0.18), (0.0, 0.0, 0.50), 1.12),
            ("winnowing_tray", (0.36, -1.32, 0.44), (0.0, math.radians(72), 0.16), 0.96),
            ("jar_handles", (1.44, -hw + 0.44, 0.18), (0.0, 0.0, 0.48), 0.98),
        ]
    elif trade == "salon":
        prop_layout += [
            ("basket_deep", (0.52, -1.92, 0.18), (0.0, 0.0, 0.55), 1.28),
            ("basket_round", (0.64, 1.48, 0.18), (0.0, 0.0, -0.32), 1.08),
            ("broom", (1.54, hw - 0.56, 0.18), (0.0, 0.0, 0.18), 1.04),
        ]
    elif trade == "outpost":
        prop_layout += [
            ("clay_stove", (0.62, -0.82, 0.18), (0.0, 0.0, 0.25), 1.04),
            ("kettle", (0.62, -0.82, 0.50), (0.0, 0.0, -0.55), 1.04),
            ("jar_handles", (1.38, -hw + 0.44, 0.18), (0.0, 0.0, 0.65), 1.00),
            ("winnowing_tray", (0.34, 1.56, 0.44), (0.0, math.radians(76), -0.22), 0.94),
        ]

    for pkey, lp, prot, psc in prop_layout:
        if props.get(pkey):
            M_p = M_shop @ Matrix.Translation(lp) @ Euler(prot, "XYZ").to_matrix().to_4x4() @ Matrix.Scale(psc, 4)
            _place_linked(props[pkey], coll, M_p, f"shop_{shop_idx}_{pkey}")

    # Return ceramic insulator position at roof corner for overhead electrical drop wire!
    return to_w((1.75, 0.0, 3.32))


def _upgrade_puddles_and_median_grass():
    """Ensure every road puddle has radial UVs for smooth feathered mud shorelines, split
    ditch water onto its own material, and refine median grass so blades look slender & natural."""
    puddle_mat = bpy.data.materials.get("M_puddle")
    ditch_mat = bpy.data.materials.get("M_ditch_water")
    if puddle_mat and ditch_mat is None:
        ditch_mat = puddle_mat.copy()
        ditch_mat.name = "M_ditch_water"
    # Keep M_puddle (BLEND) and M_ditch_water (OPAQUE) distinct in PBR parameters so gltf-transform
    # dedup NEVER merges M_puddle into M_ditch_water!
    if puddle_mat:
        puddle_mat.blend_method = "BLEND"
        if puddle_mat.node_tree and "Principled BSDF" in puddle_mat.node_tree.nodes:
            pbs = puddle_mat.node_tree.nodes["Principled BSDF"]
            pbs.inputs["Base Color"].default_value = (0.011, 0.014, 0.017, 1.0)
            pbs.inputs["Roughness"].default_value = 0.036
            pbs.inputs["Alpha"].default_value = 0.92
    if ditch_mat:
        ditch_mat.blend_method = "OPAQUE"
        if ditch_mat.node_tree and "Principled BSDF" in ditch_mat.node_tree.nodes:
            dbs = ditch_mat.node_tree.nodes["Principled BSDF"]
            dbs.inputs["Base Color"].default_value = (0.018, 0.021, 0.024, 1.0)
            dbs.inputs["Roughness"].default_value = 0.055
            dbs.inputs["Alpha"].default_value = 1.0

    puddle_count = 0
    ditch_count = 0
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if o.name.startswith("taxi_rut_water"):
            me = o.data
            if len(me.vertices) >= 4:
                c = me.vertices[0].co
                uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
                for p in me.polygons:
                    for li in p.loop_indices:
                        vi = me.loops[li].vertex_index
                        if vi == 0:
                            uvl.data[li].uv = (0.5, 0.5)
                        else:
                            d = me.vertices[vi].co - c
                            a = math.atan2(d.y, d.x)
                            uvl.data[li].uv = (0.5 + 0.49 * math.cos(a), 0.5 + 0.49 * math.sin(a))
                me.update()
                puddle_count += 1
        elif o.name.startswith("taxi_ditch_water") and ditch_mat:
            if o.data.materials:
                o.data.materials[0] = ditch_mat
            else:
                o.data.materials.append(ditch_mat)
            ditch_count += 1

    # Make median grass blades slender and slightly lower so zero bright fat cones poke out of puddles!
    mg = bpy.data.objects.get("taxi_median_grass")
    if mg and mg.type == "MESH":
        me = mg.data
        if not me.get("refined_slender"):
            verts = me.vertices
            for poly in me.polygons:
                if len(poly.vertices) == 3:
                    v0, v1, v2 = [verts[i].co for i in poly.vertices]
                    mid = (v0 + v1) * 0.5
                    # Narrow base width by 52% and lower blade height by 36%
                    verts[poly.vertices[0]].co = mid + (v0 - mid) * 0.48
                    verts[poly.vertices[1]].co = mid + (v1 - mid) * 0.48
                    verts[poly.vertices[2]].co = mid + (v2 - mid) * 0.64 - Vector((0, 0, 0.008))
            me["refined_slender"] = True
            me.update()

    # Repair legacy M_forest_leaf if its color texture collapsed to a 4x4 placeholder ("Image")!
    fl_mat = bpy.data.materials.get("M_forest_leaf")
    leaf_bc = ROOT / "art-source/textures/ep1/T_ep1_forest_leaf_BC.png"
    leaf_n = ROOT / "art-source/textures/ep1/T_ep1_forest_leaf_N.png"
    if fl_mat and fl_mat.node_tree and leaf_bc.exists():
        nt = fl_mat.node_tree
        bs = nt.nodes.get("Principled BSDF")
        if bs:
            for n in list(nt.nodes):
                if n.type == "TEX_IMAGE" and n.image and (n.image.size[0] <= 16 or n.image.name == "Image"):
                    nt.nodes.remove(n)
            # Rebuild crisp veined broadleaf cutout links from T_ep1_forest_leaf_BC/N
            has_bc = any(n.type == "TEX_IMAGE" and n.image and "forest_leaf_BC" in n.image.name for n in nt.nodes)
            if not has_bc:
                for l in list(bs.inputs["Base Color"].links) + list(bs.inputs["Alpha"].links):
                    nt.links.remove(l)
                t_bc = nt.nodes.new("ShaderNodeTexImage")
                t_bc.image = bpy.data.images.load(str(leaf_bc), check_existing=True)
                t_bc.image.alpha_mode = "STRAIGHT"
                nt.links.new(t_bc.outputs["Color"], bs.inputs["Base Color"])
                rnd = nt.nodes.new("ShaderNodeMath")
                rnd.operation = "ROUND"
                nt.links.new(t_bc.outputs["Alpha"], rnd.inputs[0])
                nt.links.new(rnd.outputs[0], bs.inputs["Alpha"])
                if leaf_n.exists():
                    t_n = nt.nodes.new("ShaderNodeTexImage")
                    t_n.image = bpy.data.images.load(str(leaf_n), check_existing=True)
                    t_n.image.colorspace_settings.name = "Non-Color"
                    nmap = nt.nodes.new("ShaderNodeNormalMap")
                    nmap.inputs["Strength"].default_value = 0.7
                    nt.links.new(t_n.outputs["Color"], nmap.inputs["Color"])
                    nt.links.new(nmap.outputs["Normal"], bs.inputs["Normal"])
                fl_mat.use_backface_culling = False
                print("TAXI_FOREST_LEAF_TEXTURE_REPAIRED")
    print("TAXI_PUDDLES_AND_GRASS_UPGRADED", "puddles=", puddle_count, "ditches=", ditch_count)


def _image_tex_material(name, path, rough=0.72, tile=0.6, cutout=False, tint=None, double_sided=False):
    """Build a crisp Principled material from a single color texture (Khmer fabrics, paper, or alpha-cutout rice)."""
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = not (cutout or double_sided)
    nt = mat.node_tree
    bs = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    if cutout:
        tex.image.alpha_mode = "STRAIGHT"
        rnd = nt.nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        nt.links.new(tex.outputs["Alpha"], rnd.inputs[0])
        nt.links.new(rnd.outputs[0], bs.inputs["Alpha"])
    if tint:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1.0)
        nt.links.new(tex.outputs["Color"], mix.inputs[6])
        nt.links.new(mix.outputs[2], bs.inputs["Base Color"])
    else:
        nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = 0.0
    mat["tile"] = tile
    return mat


def _road_lateral_from_blender(bx, by):
    """Exact lateral distance from the winding road centerline (matching tests/unit/taxiAssets.test.ts)."""
    x, z = -bx, -by
    t = z
    for _ in range(5):
        c = 3.8 * math.sin(t * 0.018) + 2.2 * math.sin(t * 0.037)
        s = 3.8 * 0.018 * math.cos(t * 0.018) + 2.2 * 0.037 * math.cos(t * 0.037)
        t += ((x - c) * s + z - t) / (1.0 + s * s)
    ang = math.atan(3.8 * 0.018 * math.cos(t * 0.018) + 2.2 * 0.037 * math.cos(t * 0.037))
    return (x - 3.8 * math.sin(t * 0.018) - 2.2 * math.sin(t * 0.037)) * math.cos(ang) - (z - t) * math.sin(ang)


def _mesh_clears_road(mesh_verts_np, M_world, min_lat=3.55, max_y=2.8):
    """Fast vectorized check that no vertex below y = max_y comes within min_lat of the road centerline."""
    m = np.array(M_world, dtype=np.float64)
    wpts = mesh_verts_np @ m[:3, :3].T + m[:3, 3]
    low = wpts[wpts[:, 2] < max_y]
    if len(low) == 0:
        return True
    step = max(1, len(low) // 96)
    for p in low[::step]:
        if abs(_road_lateral_from_blender(float(p[0]), float(p[1]))) < min_lat:
            return False
    return True


def _upgrade_ep1_refine_jungle_and_paddies(
    coll,
    rng,
    w,
    road_point,
    road_heading,
    PADDY_WATER,
    shop_specs,
    board_specs,
    full_gltf_group,
    import_glb,
):
    """Match bondeth/ep1-refine's lush Cambodian countryside & monsoon jungle look:
    - Real transplanted ep1-refine flooded rice hills (T_ep1_rice_hills_green/ripe_BC.png) swaying in the storm
    - Soaring ep1-refine scanned sugar palms (sugar_palm.glb) singly & in pairs along paddy dikes and skyline
    - Abundant ep1-refine scanned banana groves (banana_clump.glb) beside shops, paddy bunds & jungle margins
    - Gnarled old-growth ep1-refine broadleaf giants + bare dead snags (forest_tree_gn.glb) closing in the jungle
    - Zero bamboo (matching ep1-refine's removal of bamboo in favor of bananas and palms).
    """
    import re

    # Remove legacy bamboo clumps so the corridor matches ep1-refine ("no bamboo: bananas & palms").
    removed_bamboo = 0
    for o in list(bpy.data.objects):
        if o.name.startswith("taxi_road_bamboo"):
            bpy.data.objects.remove(o, do_unlink=True)
            removed_bamboo += 1

    # 1. IMPORT ep1-refine FLORA SCANS (KEEP ONLY LOD1 & LOD2 SO UNIQUE TRIS STAY LEAN ~36K!)
    flora_tpls = {}
    flora_verts = {}
    cleanup_objs = []
    for key in ("forest_tree_gn", "banana_clump", "sugar_palm"):
        path = SCANS / f"{key}.glb"
        if not path.exists():
            continue
        if full_gltf_group:
            full_gltf_group()
        before_imgs = set(bpy.data.images)
        objs = import_glb(path)
        for idx, img in enumerate(sorted((i for i in bpy.data.images if i not in before_imgs), key=lambda i: i.name)):
            img.name = f"ep1_flora_{key}_{idx}"
        lod1 = lod2 = None
        for o in objs:
            n = o.name.split(".")[0]
            if n == f"{key}_lod1":
                lod1 = o
            elif n == f"{key}_lod2":
                lod2 = o
            else:
                bpy.data.objects.remove(o, do_unlink=True)
                continue
            for slot in o.material_slots:
                m = slot.material
                if m and not m.name.startswith("M_flora_"):
                    base_m = m.name.split(".")[0]
                    m.name = f"M_flora_{key}_{base_m}"
                    if re.search(r"Cluster|Vines|Leaf|Material_5\d", base_m):
                        m.use_backface_culling = False
            o.hide_render = True
            cleanup_objs.append(o)
        if lod1 or lod2:
            flora_tpls[key] = (lod1 or lod2, lod2 or lod1)
            for tag, obj in ((f"{key}_1", lod1 or lod2), (f"{key}_2", lod2 or lod1)):
                co = np.empty(len(obj.data.vertices) * 3, dtype=np.float64)
                obj.data.vertices.foreach_get("co", co)
                flora_verts[tag] = co.reshape(-1, 3)

    # Create bare-wood dead snag template from forest_tree_gn_lod2 (stripping Cluster/Vines leaves!)
    if "forest_tree_gn" in flora_tpls:
        src_gn = flora_tpls["forest_tree_gn"][1]
        dead = src_gn.copy()
        dead.data = src_gn.data.copy()
        dead.name = dead.data.name = "ep1_forest_tree_gn_dead_tpl"
        coll.objects.link(dead)
        bm_d = bmesh.new()
        bm_d.from_mesh(dead.data)
        leafy = [i for i, m in enumerate(dead.data.materials) if m and re.search(r"Cluster|Vines", m.name)]
        bmesh.ops.delete(bm_d, geom=[f for f in bm_d.faces if f.material_index in leafy], context="FACES")
        bm_d.to_mesh(dead.data)
        bm_d.free()
        dead.hide_render = True
        cleanup_objs.append(dead)
        flora_tpls["dead"] = (dead, dead)
        co = np.empty(len(dead.data.vertices) * 3, dtype=np.float64)
        dead.data.vertices.foreach_get("co", co)
        flora_verts["dead_2"] = co.reshape(-1, 3)

    def _spawn(key, lod_idx, name, M_world, min_lat=3.55):
        if key not in flora_tpls:
            return None
        src = flora_tpls[key][lod_idx]
        vtag = f"{key}_{lod_idx + 1}" if key != "dead" else "dead_2"
        if not _mesh_clears_road(flora_verts[vtag], M_world, min_lat=min_lat):
            return None
        c = bpy.data.objects.new(name, src.data)
        coll.objects.link(c)
        c.matrix_world = M_world
        return c

    # 2. EP1-REFINE TRANSPLANTED FLOODED RICE FIELDS (z = -18..144 m, green & ripening golden plots!)
    rice_mats = {}
    for crop, fname in (("green", "T_ep1_rice_hills_green_BC.png"), ("ripe", "T_ep1_rice_hills_ripe_BC.png")):
        rpath = TEX / fname
        if rpath.exists():
            rice_mats[crop] = _image_tex_material(
                f"M_paddy_rice_{crop}", rpath, rough=0.66, tile=0.0, cutout=True, double_sided=True
            )
    rice_chunks_built = 0
    if rice_mats:
        chunk_data = {}
        z_cur = -18.0
        while z_cur < 144.0:
            z_chunk = int((z_cur + 24.0) // 22.0)
            for side in (-1, 1):
                # Keep a natural open mirror-water pocket around z=18..28 right & z=94..102 left so storm reflections shimmer!
                if (side > 0 and 19.0 < z_cur < 25.0) or (side < 0 and 92.0 < z_cur < 99.0):
                    continue
                is_ripe = (side < 0 and 50.0 < z_cur < 78.0) or (side > 0 and 106.0 < z_cur < 132.0)
                crop = "ripe" if (is_ripe and "ripe" in rice_mats) else "green"
                lat_d = 4.9
                while lat_d < 36.0:
                    lat = side * lat_d
                    near_shop = any(abs(z_cur - sp["z"]) < 5.6 and (sp["lat"] * side > 0) and lat_d < 12.6 for sp in shop_specs)
                    near_board = any(abs(z_cur - bz) < 2.2 and (blat * side > 0) and lat_d < 6.0 for blat, bz, *_ in board_specs)
                    if not near_shop and not near_board and rng.random() > 0.08:
                        hx_z = z_cur + float(rng.normal(0, 0.14))
                        hl = lat + float(rng.normal(0, 0.14))
                        base = w(road_point(hl, PADDY_WATER - 0.06, hx_z))
                        k = float(rng.uniform(0.90, 1.16))
                        cell = int(rng.integers(4))
                        yaw = float(rng.uniform(0, math.pi))
                        lean = (float(rng.normal(0, 0.07)), float(rng.normal(0, 0.07)))
                        chunk_data.setdefault((z_chunk, side, crop), []).append((base, k, cell, yaw, lean))
                    lat_d += 0.78 if lat_d < 15.0 else 1.25
            z_cur += 0.85

        width, height = 0.70, 1.42
        for (z_chunk, side, crop), hills in chunk_data.items():
            verts, faces, uvs, normals = [], [], [], []
            for base, k, cell, yaw, lean in hills:
                u0, u1 = cell * 0.25, (cell + 1) * 0.25
                for turn in (0.0, math.pi * 0.5):
                    a = yaw + turn
                    ax = Vector((math.cos(a), math.sin(a), 0.0)) * (width * k * 0.5)
                    up = Vector((lean[0], lean[1], 1.0)).normalized() * (height * k)
                    b = len(verts)
                    verts += [base - ax, base + ax, base + ax + up, base - ax + up]
                    faces.append((b, b + 1, b + 2, b + 3))
                    uvs += [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)]
                    ax_n = ax.normalized()
                    for t_v, sx_v in ((0, -1), (0, 1), (1, 1), (1, -1)):
                        normals.append((Vector((0.0, 0.0, 0.48 + 0.48 * t_v)) + ax_n * (0.44 * sx_v)).normalized())
            me = bpy.data.meshes.new(f"taxi_road_ep1_rice_{crop}_{'r' if side > 0 else 'l'}_{z_chunk}")
            me.from_pydata([v[:] for v in verts], [], faces)
            uv = me.uv_layers.new(name="UVMap")
            for poly in me.polygons:
                for li in poly.loop_indices:
                    uv.data[li].uv = uvs[me.loops[li].vertex_index]
            me.materials.append(rice_mats[crop])
            me.normals_split_custom_set([normals[me.loops[li].vertex_index][:] for li in range(len(me.loops))])
            me.update()
            obj = bpy.data.objects.new(me.name, me)
            coll.objects.link(obj)
            rice_chunks_built += 1

    # 3. SUGAR PALMS (Thnot) OVER THE FLOODED RICE FIELDS & BEHIND SHOPS (z = -14..148 m)
    palm_count = 0
    palm_spots = [
        # Hero roadside Thnot sugar palm silhouettes framing open flooded rice paddies between shops!
        (9.2, 41.0), (12.8, 44.5), (-9.6, 26.5), (10.4, 52.0),
        (-10.2, 62.5), (9.8, 76.0), (-11.0, 96.0), (10.5, 114.0),
    ]
    for side in (-1, 1):
        z_p = -12.0 if side < 0 else -4.0
        while z_p < 148.0:
            # Singly or authentic Cambodian pair along paddy dikes & village yards!
            lat_base = side * float(rng.uniform(10.2, 32.0))
            pair = 2 if rng.random() < 0.36 else 1
            for k_p in range(pair):
                dz_p = 0.0 if k_p == 0 else float(rng.uniform(2.6, 4.4))
                dl_p = 0.0 if k_p == 0 else side * float(rng.uniform(-1.2, 2.2))
                palm_spots.append((lat_base + dl_p, z_p + dz_p))
            z_p += float(rng.uniform(10.5, 16.5))
    for i_p, (lat, zp) in enumerate(palm_spots):
        side = 1 if lat > 0 else -1
        # Keep clear of shop roofs
        if any(abs(zp - sp["z"]) < 4.5 and (sp["lat"] * side > 0) and abs(lat) < 11.4 for sp in shop_specs):
            lat = side * 12.6
        lod_i = 0 if abs(lat) < 18.5 else 1
        sc = float(rng.uniform(0.92, 1.36))
        pos = w(road_point(lat, PADDY_WATER + 0.06, zp))
        M_p = (
            Matrix.Translation(pos)
            @ Matrix.Rotation(float(rng.uniform(0, math.tau)), 4, "Z")
            @ Matrix.Rotation(float(rng.uniform(-0.06, 0.06)), 4, "X")
            @ Matrix.Rotation(float(rng.uniform(-0.06, 0.06)), 4, "Y")
            @ Matrix.Scale(sc, 4)
        )
        if _spawn("sugar_palm", lod_i, f"taxi_road_ep1_palm_field_{i_p}", M_p, min_lat=4.5):
            palm_count += 1

    # 4. LUSH BANANA GROVES BESIDE EVERY SHOP & ALONG PADDY EMBANKMENT (z = -10..146 m)
    banana_count = 0
    for idx, sp in enumerate(shop_specs):
        lat, z_pos = sp["lat"], sp["z"]
        side = 1 if lat > 0 else -1
        for k_b, (dz, dlat, sc_b) in enumerate([(-4.6, 1.8, 0.92), (4.8, 1.6, 0.88), (0.8, 4.4, 1.04)]):
            pos = w(road_point(lat + side * dlat, PADDY_WATER + 0.14, z_pos + dz))
            M_b = (
                Matrix.Translation(pos)
                @ Matrix.Rotation(float(rng.uniform(0, math.tau)), 4, "Z")
                @ Matrix.Scale(sc_b * float(rng.uniform(0.90, 1.10)), 4)
            )
            if _spawn("banana_clump", 0 if k_b < 2 else 1, f"taxi_road_ep1_banana_shop_{idx}_{k_b}", M_b, min_lat=4.6):
                banana_count += 1
    for side in (-1, 1):
        z_b = -6.0 if side < 0 else 4.0
        while z_b < 144.0:
            near_shop = any(abs(z_b - sp["z"]) < 7.0 and (sp["lat"] * side > 0) for sp in shop_specs)
            near_board = any(abs(z_b - bz) < 4.5 and (blat * side > 0) for blat, bz, *_ in board_specs)
            if not near_shop and not near_board:
                lat = side * float(rng.uniform(7.2, 14.5))
                pos = w(road_point(lat, PADDY_WATER + 0.12, z_b))
                M_b = (
                    Matrix.Translation(pos)
                    @ Matrix.Rotation(float(rng.uniform(0, math.tau)), 4, "Z")
                    @ Matrix.Scale(float(rng.uniform(0.82, 1.14)), 4)
                )
                if _spawn("banana_clump", 1, f"taxi_road_ep1_banana_paddy_{banana_count}", M_b, min_lat=4.5):
                    banana_count += 1
            z_b += float(rng.uniform(16.0, 24.0))

    # 5. EP1-REFINE MONSOON JUNGLE CORRIDOR (z = 144..505 m):
    # Abundant broad-leaf banana_clump groves + gnarled forest_tree_gn old-growth wall + dead snags + sugar palms!
    jungle_trees = 0
    jungle_bananas = 0
    jungle_palms = 0
    jungle_dead = 0

    # 5a. Dense banana_clump groves hugging BOTH sides of the wet jungle track right behind the swaying tall grass!
    for side in (-1, 1):
        z_j = 144.5 if side < 0 else 148.5
        while z_j < 502.0:
            clump_n = 2 if rng.random() < 0.38 else 1
            for k_c in range(clump_n):
                lat = side * float(rng.uniform(5.6, 9.8 if k_c == 0 else 12.8))
                z_p = z_j + (0.0 if k_c == 0 else float(rng.uniform(-2.2, 2.2)))
                pos = w(road_point(lat, -0.14, z_p))
                sc = float(rng.uniform(0.76, 1.12))
                M_b = (
                    Matrix.Translation(pos)
                    @ Matrix.Rotation(float(rng.uniform(0, math.tau)), 4, "Z")
                    @ Matrix.Rotation(float(rng.uniform(-0.05, 0.05)), 4, "X")
                    @ Matrix.Scale(sc, 4)
                )
                lod_i = 0 if abs(lat) < 8.4 and k_c == 0 else 1
                if _spawn("banana_clump", lod_i, f"taxi_road_ep1_banana_j_{jungle_bananas}", M_b, min_lat=3.55):
                    jungle_bananas += 1
            z_j += float(rng.uniform(7.5, 11.8))

    # 5b. Gnarled ep1-refine old-growth forest_tree_gn giants & occasional bare dead snags framing the road!
    for side in (-1, 1):
        z_t = 146.0 if side < 0 else 151.0
        while z_t < 504.0:
            lat = side * float(rng.uniform(8.2, 16.5))
            pos = w(road_point(lat, -0.16, z_t))
            sc = float(rng.uniform(0.78, 1.24))
            M_t = (
                Matrix.Translation(pos)
                @ Matrix.Rotation(float(rng.uniform(0, math.tau)), 4, "Z")
                @ Matrix.Rotation(float(rng.uniform(-0.05, 0.05)), 4, "X")
                @ Matrix.Rotation(float(rng.uniform(-0.05, 0.05)), 4, "Y")
                @ Matrix.Scale(sc, 4)
            )
            if rng.random() < 0.16 and "dead" in flora_tpls:
                if _spawn("dead", 1, f"taxi_road_ep1_dead_{jungle_dead}", M_t, min_lat=3.8):
                    jungle_dead += 1
            else:
                lod_i = 0 if abs(lat) < 11.5 else 1
                if _spawn("forest_tree_gn", lod_i, f"taxi_road_ep1_tree_{jungle_trees}", M_t, min_lat=3.8):
                    jungle_trees += 1
            z_t += float(rng.uniform(8.5, 13.0))

    # 5c. Towering ep1-refine sugar_palm silhouettes breaking above the misty jungle treeline!
    for side in (-1, 1):
        z_sp = 152.0 if side < 0 else 160.0
        while z_sp < 498.0:
            lat = side * float(rng.uniform(9.5, 20.5))
            pos = w(road_point(lat, -0.14, z_sp))
            sc = float(rng.uniform(0.95, 1.32))
            M_sp = (
                Matrix.Translation(pos)
                @ Matrix.Rotation(float(rng.uniform(0, math.tau)), 4, "Z")
                @ Matrix.Rotation(float(rng.uniform(-0.06, 0.06)), 4, "X")
                @ Matrix.Scale(sc, 4)
            )
            if _spawn("sugar_palm", 1, f"taxi_road_ep1_palm_j_{jungle_palms}", M_sp, min_lat=4.5):
                jungle_palms += 1
            z_sp += float(rng.uniform(22.0, 34.0))

    # Remove temporary template objects so only placed linked instances export
    for o in cleanup_objs:
        bpy.data.objects.remove(o, do_unlink=True)

    print(
        "TAXI_EP1_REFINE_NATURE_UPGRADED",
        "rice_chunks=", rice_chunks_built,
        "field_palms=", palm_count,
        "paddy_bananas=", banana_count,
        "jungle_bananas=", jungle_bananas,
        "jungle_trees=", jungle_trees,
        "jungle_dead=", jungle_dead,
        "jungle_palms=", jungle_palms,
        "removed_bamboo=", removed_bamboo,
    )


def apply_roadside_details(
    mats_village,
    rng,
    w,
    road_point,
    road_heading,
    PADDY_WATER,
    library_material,
    plain,
    world_uvs_fn,
    full_gltf_group,
    import_glb,
    plant_fn,
):
    """Build 8 bespoke ultra-detailed Cambodian roadside shops, 7 gooseneck-lit Khmer 90s poster boards,
    overhead electrical drop wires, scarecrows, radial puddle UVs, and ep1-refine rice fields, palms & jungle."""
    coll = bpy.context.scene.collection

    _upgrade_puddles_and_median_grass()

    # Shared shop & real Khmer 90s poster atlas materials (1 draw call for all posters!)
    poster_path = TEX / "T_taxi_khmer_posters_BC.png"
    poster_mat = plain("M_taxi_khmer_posters", (1, 1, 1), 0.48, 0.0)
    nt = poster_mat.node_tree
    bs = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(poster_path), check_existing=True)
    nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
    poster_mat.use_backface_culling = False

    shop_mats = {
        "planks": library_material("weathered_planks", "M_taxi_shop_planks", tint=(0.36, 0.28, 0.21), tile=1.4),
        "dark_wood": library_material("dark_wood", "M_taxi_shop_posts", tint=(0.24, 0.18, 0.14), tile=1.2),
        "shutter": library_material("wood_shutter", "M_taxi_shop_shutters", tint=(0.18, 0.34, 0.30), tile=1.0),
        "tin": library_material("rusty_metal", "M_taxi_shop_tin", tint=(0.44, 0.36, 0.30), tile=1.2),
        "plaster": library_material("yellow_plaster", "M_taxi_shop_plaster", tint=(0.64, 0.56, 0.42), tile=2.0),
        "brick": library_material("red_brick", "M_taxi_shop_brick", tint=(0.48, 0.32, 0.24), tile=1.4),
        "deck": library_material("weathered_brown_planks", "M_taxi_shop_deck", tint=(0.34, 0.26, 0.19), tile=1.6),
        "concrete": library_material("concrete_floor_worn_001", "M_taxi_shop_concrete", tint=(0.46, 0.44, 0.40), tile=2.0),
        "clay_tile": library_material("clay_roof_tiles_02", "M_taxi_shop_clay_tile", tint=(0.56, 0.34, 0.22), tile=2.2),
        "thatch": library_material("thatch_roof_angled", "M_taxi_shop_thatch", tint=(0.42, 0.34, 0.22), tile=1.2),
        "bamboo_wall": library_material("bamboo_wall", "M_taxi_shop_bamboo_wall", tint=(0.46, 0.36, 0.22), tile=1.8),
        "table_wood": library_material("wood_table_worn", "M_taxi_shop_table_wood", tint=(0.42, 0.30, 0.20), tile=0.65),
        "krama": _image_tex_material("M_taxi_shop_krama", TEX / "T_ep1_krama_check_BC.png", rough=0.86, tile=0.52, double_sided=True),
        "hol_silk": _image_tex_material("M_taxi_shop_hol_silk", TEX / "T_ep1_hol_silk_BC.png", rough=0.62, tile=0.48, double_sided=True),
        "news": _image_tex_material("M_taxi_shop_news", TEX / "T_ep1_paper_news_BC.png", rough=0.82, tile=0.36, double_sided=True),
        "kantel": _image_tex_material("M_taxi_shop_kantel", TEX / "T_ep1_kantel_mat_BC.png", rough=0.78, tile=0.85, double_sided=True),
        "iron": plain("M_taxi_shop_iron", (0.06, 0.06, 0.065), 0.52, 0.78),
        "enamel_green": plain("M_taxi_shop_enamel_green", (0.05, 0.16, 0.09), 0.28, 0.18),
        "bulb": plain("M_taxi_shop_bulb", (1.0, 0.76, 0.38), 0.18, 0.0, emission=(1.0, 0.68, 0.28), strength=5.5),
        "fluoro": plain("M_taxi_shop_fluoro", (0.86, 0.94, 1.0), 0.15, 0.0, emission=(0.76, 0.90, 1.0), strength=4.2),
        "crt": plain("M_taxi_shop_crt", (0.35, 0.62, 0.78), 0.12, 0.0, emission=(0.36, 0.66, 0.88), strength=3.4),
        "red_plastic": plain("M_taxi_shop_red_prop", (0.42, 0.055, 0.04), 0.36, 0.04),
        "blue_tarp": plain("M_taxi_shop_blue_prop", (0.06, 0.18, 0.42), 0.42, 0.05),
        "amber_glass": plain("M_taxi_shop_amber_glass", (0.68, 0.39, 0.06), 0.14, 0.06),
        "green_glass": plain("M_taxi_shop_green_glass", (0.05, 0.22, 0.08), 0.16, 0.06),
        "foliage": plain("M_taxi_shop_foliage", (0.032, 0.075, 0.028), 0.62, 0.0),
        "white_enamel": plain("M_taxi_shop_white_enamel", (0.66, 0.64, 0.58), 0.34, 0.08),
        "mirror": plain("M_taxi_shop_mirror", (0.78, 0.82, 0.84), 0.05, 0.96),
        "rubber": plain("M_taxi_shop_rubber", (0.024, 0.024, 0.026), 0.76, 0.0),
        "bamboo": plain("M_taxi_shop_bamboo", (0.38, 0.29, 0.15), 0.74, 0.0),
        "wire": plain("M_taxi_shop_wire", (0.02, 0.02, 0.022), 0.68, 0.15),
        "win_glow": plain("M_taxi_shop_window_glow", (0.95, 0.68, 0.30), 0.22, 0.0, emission=(1.0, 0.64, 0.24), strength=2.6),
        "noodle_glow": plain("M_taxi_shop_noodle_glow", (0.98, 0.80, 0.44), 0.14, 0.0, emission=(1.0, 0.74, 0.34), strength=3.4),
        "shrine_glow": plain("M_taxi_shop_shrine_glow", (1.0, 0.16, 0.08), 0.20, 0.0, emission=(1.0, 0.12, 0.05), strength=6.5),
        "world_uvs": world_uvs_fn,
    }
    shop_mats["foliage"].use_backface_culling = False
    shop_mats["blue_tarp"].use_backface_culling = False

    # Tightly decimated rural shop props + roadside scarecrow (shared linked copies -> tiny triangle & byte budget!)
    props = {
        "rice_sack": _load_decimated_scan("rice_sack.glb", 0.20, full_gltf_group, import_glb),
        "water_jar": _load_decimated_scan("water_jar.glb", 0.10, full_gltf_group, import_glb),
        "basket_deep": _load_decimated_scan("basket_deep.glb", 0.22, full_gltf_group, import_glb),
        "clay_stove": _load_decimated_scan("clay_stove.glb", 0.14, full_gltf_group, import_glb),
        "kettle": _load_decimated_scan("kettle.glb", 0.22, full_gltf_group, import_glb),
        "cooking_pot": _load_decimated_scan("cooking_pot.glb", 0.26, full_gltf_group, import_glb),
        "broom": _load_decimated_scan("broom.glb", 0.85, full_gltf_group, import_glb),
        "jar_handles": _load_decimated_scan("jar_handles.glb", 0.85, full_gltf_group, import_glb),
        "basket_round": _load_decimated_scan("basket_round.glb", 0.85, full_gltf_group, import_glb),
        "winnowing_tray": _load_decimated_scan("winnowing_tray.glb", 0.18, full_gltf_group, import_glb),
    }
    scarecrow = _load_decimated_scan("scarecrow.glb", 0.38, full_gltf_group, import_glb)

    p_verts, p_faces, p_uvs = [], [], []

    # 8 BESPOKE ULTRA-DETAILED RURAL CAMBODIAN ROADSIDE SHOPS (alternating left & right along z = 12.5..136 m!)
    shop_specs = [
        {
            "trade": "noodle", "lat": -6.9, "z": 12.5, "eyaw": -0.14, "hw": 2.75,
            "open_front": True, "parapet": False, "tarp": True, "fluoro": False, "dim": False,
            "posters": {"hero": 2, "front": (1, 13), "side": (0, 2), "hang": (1, 2)},
        },
        {
            "trade": "barber", "lat": 6.9, "z": 26.0, "eyaw": 0.14, "hw": 2.75,
            "open_front": True, "parapet": False, "tarp": True, "fluoro": True, "dim": False,
            "posters": {"hero": 8, "front": (0, 5), "side": (10, 14), "hang": (0, 15)},
        },
        {
            "trade": "dentist_salon", "lat": -7.1, "z": 44.0, "eyaw": -0.12, "hw": 3.15,
            "open_front": True, "parapet": True, "tarp": False, "fluoro": True, "dim": False,
            "posters": {"hero": 6, "front": (4, 3), "side": (7, 11), "hang": (6, 4)},
        },
        {
            "trade": "tv_coffee", "lat": 6.8, "z": 64.0, "eyaw": 0.12, "hw": 2.60,
            "open_front": False, "parapet": False, "tarp": True, "fluoro": False, "dim": False,
            "posters": {"hero": 9, "front": (2, 1), "side": (9, 2), "hang": (9, 1)},
        },
        {
            "trade": "moto", "lat": -7.0, "z": 82.0, "eyaw": -0.14, "hw": 2.85,
            "open_front": True, "parapet": False, "tarp": False, "fluoro": True, "dim": False,
            "posters": {"hero": 12, "front": (13, 15), "side": (12, 14), "hang": (12, 14)},
        },
        {
            "trade": "grocery", "lat": 6.9, "z": 100.0, "eyaw": 0.15, "hw": 2.95,
            "open_front": True, "parapet": False, "tarp": False, "fluoro": False, "dim": False,
            "posters": {"hero": 13, "front": (1, 2), "side": (7, 3), "hang": (13, 1)},
        },
        {
            "trade": "salon", "lat": -7.1, "z": 118.0, "eyaw": -0.10, "hw": 2.65,
            "open_front": True, "parapet": False, "tarp": True, "fluoro": False, "dim": False,
            "posters": {"hero": 7, "front": (15, 3), "side": (4, 11), "hang": (7, 3)},
        },
        {
            "trade": "outpost", "lat": 7.1, "z": 136.0, "eyaw": 0.12, "hw": 2.60,
            "open_front": False, "parapet": False, "tarp": False, "fluoro": False, "dim": True,
            "posters": {"hero": 5, "front": (10, 14), "side": (6, 8), "hang": (5, 8)},
        },
    ]

    bm_wires = bmesh.new()
    for idx, sp in enumerate(shop_specs):
        lat, z_pos, eyaw = sp["lat"], sp["z"], sp["eyaw"]
        pos_bl = w(road_point(lat, -0.16, z_pos))
        base_yaw = -road_heading(z_pos) if lat > 0 else (math.pi - road_heading(z_pos))
        M_shop = Matrix.Translation(pos_bl) @ Matrix.Rotation(base_yaw + eyaw, 4, "Z")
        insulator = _build_detailed_shop(coll, M_shop, shop_mats, props, p_verts, p_faces, p_uvs, sp, idx)

        # Overhead sagging black electrical power drop cable from left-side telegraph line to each shop!
        pole_pt = w(road_point(-4.1, 5.2, z_pos - 2.0))
        sag_pts = []
        for s in range(9):
            f = s / 8.0
            pt = pole_pt.lerp(insulator, f)
            pt.z -= 0.48 * math.sin(f * math.pi)
            sag_pts.append(pt)
        _tube_bm(bm_wires, sag_pts, 0.011, segs=5)
    _bm_obj("taxi_road_shop_power_wires", bm_wires, shop_mats["wire"], coll, smooth=True)

    # 7 ULTRA-DETAILED GOOSENECK-LIT ROADSIDE KHMER 90s POSTER BOARDS (alternating left/right at |lat|=4.35 m!)
    board_specs = [
        (4.35, 17.5, 0, 8),     # Right verge: កាត់សក់ + កាត់សក់ ជាង លេង (cleanly opposite Noodle shop!)
        (-4.35, 35.0, 4, 6),    # Left verge: រចនា អ៊ុតសក់ + គីម ចេង ដាក់ធ្មេញ
        (4.35, 54.0, 9, 2),     # Right verge: ជួសជុលអេឡិចត្រូនិច + រាំវង់ប្រជាប្រិយ
        (-4.35, 73.0, 12, 13),  # Left verge: ពន្លឺពេជ្រ ម៉ូតូ + ក្រុមតន្ត្រីពន្លឺថ្មី
        (4.35, 91.0, 1, 7),     # Right verge: សត្វមនោហ៍ + ម៉ាលីន អ៊ុតសក់
        (-4.35, 109.0, 3, 11),  # Left verge: BEAUTY SALOON + កោះកុង hairstyles
        (4.35, 127.0, 15, 14),  # Right verge: កាត់សក់ចន្ទ្រា + បញ្ញា កាត់សក់
    ]
    for b_idx, (lat, z_pos, p_a, p_b) in enumerate(board_specs):
        pos_bl = w(road_point(lat, -0.22, z_pos))
        ang = -road_heading(z_pos) + (-0.18 if lat < 0 else 0.18)
        lean = math.radians(1.4 if b_idx % 2 == 0 else -1.2)
        M_b = Matrix.Translation(pos_bl) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(lean, 4, "Y")

        bm_b = bmesh.new()
        bm_btin = bmesh.new()
        bm_biron = bmesh.new()
        bm_bconc = bmesh.new()
        bm_bsh = bmesh.new()
        bm_bbulb = bmesh.new()

        # Sturdy timber posts anchored into weathered concrete footings + diagonal rear timber support struts + iron L-brackets!
        for px_b in (-0.70, 0.70):
            _box_bm(bm_bconc, (px_b, 0.0, 0.08), (0.24, 0.24, 0.46), bevel=0.014, segs=1)
            _box_bm(bm_b, (px_b, 0.0, 1.05), (0.10, 0.10, 2.55))
            _box_bm(bm_b, (px_b, -0.34, 0.72), (0.075, 0.075, 1.55), rot=Euler((math.radians(-24), 0, 0)))
            # Rusted steel corner reinforcement brackets & bolt heads
            for bz_k in (1.02, 2.14):
                _box_bm(bm_biron, (px_b, 0.056, bz_k), (0.12, 0.018, 0.065))
        # Plank backing panel + mitered outer picture frame border + lower directional timber slat & notice stub!
        _box_bm(bm_b, (0.0, 0.0, 1.58), (1.56, 0.055, 1.16))
        _box_bm(bm_b, (0.0, 0.036, 2.16), (1.64, 0.044, 0.068))
        _box_bm(bm_b, (0.0, 0.036, 1.00), (1.64, 0.044, 0.068))
        _box_bm(bm_b, (-0.79, 0.036, 1.58), (0.065, 0.044, 1.22))
        _box_bm(bm_b, (0.79, 0.036, 1.58), (0.065, 0.044, 1.22))
        _box_bm(bm_b, (0.0, 0.036, 1.58), (0.045, 0.038, 1.12))  # Center vertical divider
        _box_bm(bm_b, (0.0, 0.03, 0.74), (1.28, 0.035, 0.14), rot=Euler((0, 0.025 if b_idx % 2 == 0 else -0.025, 0)))
        # Sculpted corrugated rusty tin rain-hood overhang + side timber bargeboards & iron brackets!
        _corrugated_sheet_bm(bm_btin, -0.86, 0.86, -0.08, 0.44, 2.25, 2.12, waves=12, amp=0.014, thick=0.010)
        for bx_s in (-0.84, 0.84):
            _box_bm(bm_b, (bx_s, 0.18, 2.16), (0.032, 0.50, 0.065), rot=Euler((math.radians(-14), 0, 0)))
        for bx_s in (-0.72, 0.72):
            _box_bm(bm_biron, (bx_s, 0.20, 2.10), (0.025, 0.40, 0.03), rot=Euler((math.radians(-16), 0, 0)))
        # Curved black conduit gooseneck lamp with green enamel reflector shade shining down on posters!
        _add_gooseneck_lamp(bm_biron, bm_bsh, bm_bbulb, (0.0, 0.05, 2.26), (0, 1, 0), drop_z=-0.10, reach=0.44)
        # Conduit wire running neatly down back of left post
        _cyl_bm(bm_biron, (-0.64, -0.05, 0.35), (-0.64, -0.05, 2.24), 0.011, 0.011, segs=5)

        _bm_obj(f"taxi_road_poster_board_{b_idx}", bm_b, shop_mats["dark_wood"], coll, world_uvs_fn=world_uvs_fn, smooth=False, M_world=M_b)
        _bm_obj(f"taxi_road_poster_board_{b_idx}_conc", bm_bconc, shop_mats["concrete"], coll, world_uvs_fn=world_uvs_fn, smooth=False, M_world=M_b)
        _bm_obj(f"taxi_road_poster_board_{b_idx}_tin", bm_btin, shop_mats["tin"], coll, world_uvs_fn=world_uvs_fn, smooth=True, M_world=M_b)
        _bm_obj(f"taxi_road_poster_board_{b_idx}_iron", bm_biron, shop_mats["iron"], coll, smooth=True, M_world=M_b)
        _bm_obj(f"taxi_road_poster_board_{b_idx}_shade", bm_bsh, shop_mats["enamel_green"], coll, smooth=True, M_world=M_b)
        _bm_obj(f"taxi_road_poster_board_{b_idx}_bulb", bm_bbulb, shop_mats["bulb"], coll, smooth=True, M_world=M_b)

        def bw(p):
            return M_b @ Vector(p)

        def bdir(v):
            return (M_b.to_3x3() @ Vector(v)).normalized()

        # Front face (+Y in local -> faces back toward approaching car!): viewer's right is (-1, 0, 0)
        _add_poster_to_lists(p_verts, p_faces, p_uvs, bw((0.37, 0.042, 1.58)), bdir((-1, 0, 0)), bdir((0, 0, 1)), 0.68, 1.00, p_a, seed=700 + b_idx * 4)
        _add_poster_to_lists(p_verts, p_faces, p_uvs, bw((-0.37, 0.042, 1.58)), bdir((-1, 0, 0)), bdir((0, 0, 1)), 0.68, 1.00, p_b, seed=701 + b_idx * 4)

        # Anchor for calibrated warm signboard bulb right beneath the gooseneck shade!
        anc = bpy.data.objects.new(f"taxi_road_anchor_poster_lamp_{b_idx}", None)
        coll.objects.link(anc)
        anc.location = bw((0.0, 0.56, 2.06))

    # Build ONE combined mesh for all real Khmer 90s color posters (1 draw call, UV-mapped to T_taxi_khmer_posters_BC.png!)
    if p_verts:
        _mesh_uv("taxi_road_khmer_posters", p_verts, p_faces, p_uvs, poster_mat, coll, smooth=True)

    # Eerie rural scarecrows standing out in the flooded rice paddies
    if scarecrow:
        for lat, z_pos, syaw in [(-12.0, 31.0, 0.4), (12.8, 112.0, -0.7)]:
            M_sc = Matrix.Translation(w(road_point(lat, PADDY_WATER + 0.08, z_pos))) @ Matrix.Rotation(syaw, 4, "Z") @ Matrix.Scale(1.08, 4)
            _place_linked(scarecrow, coll, M_sc, f"scarecrow_{int(z_pos)}")

    # Enrich paddy embankment shoulders (-15..142) with tangled wet ferns & verge grass (strictly respecting clearance > 3.5 m!)
    if plant_fn is not None:
        for side in (-1, 1):
            z_cur = -10.0
            while z_cur < 142.0:
                near_shop = any(abs(z_cur - sp["z"]) < 7.2 and (sp["lat"] * side > 0) for sp in shop_specs)
                near_board = any(abs(z_cur - bz) < 4.0 and (blat * side > 0) for blat, bz, *_ in board_specs)
                if not near_shop and not near_board:
                    kind = "fern_02_b" if rng.random() < 0.55 else "shrub_02_b"
                    plant_fn(kind, side * float(rng.uniform(4.1, 5.2)), z_cur, float(rng.uniform(0.65, 1.10)), lift=-0.42, anywhere=True, label="paddy_verge_flora")
                z_cur += float(rng.uniform(2.8, 4.6))
    else:
        ferns = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("taxi_road_fern_02")][:3]
        shrubs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("taxi_road_shrub_02")][:3]
        flora_pool = ferns + shrubs
        if flora_pool:
            for side in (-1, 1):
                z_cur = -8.0
                while z_cur < 140.0:
                    near_shop = any(abs(z_cur - sp["z"]) < 7.8 and (sp["lat"] * side > 0) for sp in shop_specs)
                    near_board = any(abs(z_cur - bz) < 4.2 and (blat * side > 0) for blat, bz, *_ in board_specs)
                    if not near_shop and not near_board:
                        src = flora_pool[int(rng.integers(len(flora_pool)))]
                        c = src.copy()
                        c.data = src.data
                        coll.objects.link(c)
                        c.parent = None
                        c.name = "taxi_road_paddy_verge_flora"
                        lat = side * float(rng.uniform(4.4, 5.6))
                        sc = float(rng.uniform(0.65, 1.05))
                        c.matrix_world = (
                            Matrix.Translation(w(road_point(lat, -0.52, z_cur)))
                            @ Matrix.Rotation(float(rng.uniform(0, math.tau)), 4, "Z")
                            @ Matrix.Scale(sc, 4)
                        )
                    z_cur += float(rng.uniform(2.8, 4.8))

    # Upgrade flooded rice fields, soaring sugar palms, abundant banana groves & monsoon jungle to match ep1-refine!
    _upgrade_ep1_refine_jungle_and_paddies(
        coll,
        rng,
        w,
        road_point,
        road_heading,
        PADDY_WATER,
        shop_specs,
        board_specs,
        full_gltf_group,
        import_glb,
    )

    # Clean up hidden prop template meshes before export
    for grp in [*props.values(), scarecrow]:
        for o in grp:
            bpy.data.objects.remove(o, do_unlink=True)
    print("TAXI_ROADSIDE_DETAILS_APPLIED", "shops=", len(shop_specs), "boards=", len(board_specs), "poster_tris=", len(p_faces) * 2)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT / "tools/areas"))
    from kit import library_material, plain, world_uvs

    ROAD_DROP = -0.27
    PADDY_WATER = -0.88

    def w(p):
        return Vector((-p[0], -p[2], p[1]))

    def road_x(z):
        return 3.8 * math.sin(z * 0.018) + 2.2 * math.sin(z * 0.037)

    def road_heading(z):
        return math.atan(3.8 * 0.018 * math.cos(z * 0.018) + 2.2 * 0.037 * math.cos(z * 0.037))

    def road_point(x, y, z):
        a = road_heading(z)
        return (road_x(z) + x * math.cos(a), y + ROAD_DROP, z - x * math.sin(a))

    def full_gltf_group():
        from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
        name = get_gltf_node_name()
        group = bpy.data.node_groups.get(name)
        if group is None:
            create_settings_group(name)
            return
        full = create_settings_group("glTF full sockets")
        have = {item.name for item in group.interface.items_tree}
        for item in full.interface.items_tree:
            if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name not in have:
                group.interface.new_socket(item.name, in_out="INPUT", socket_type=item.socket_type)
        bpy.data.node_groups.remove(full)

    def import_glb(path):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == "MESH"]
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        if meshes:
            bpy.context.view_layer.objects.active = meshes[0]
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        for o in new:
            if o.type != "MESH":
                bpy.data.objects.remove(o)
        return meshes

    # Remove previous detail pass objects cleanly so re-runs are 100% idempotent!
    prefixes = (
        "taxi_road_shop_",
        "taxi_road_poster_board_",
        "taxi_road_khmer_posters",
        "taxi_road_anchor_shop_lamp_",
        "taxi_road_anchor_shop_int_lamp_",
        "taxi_road_anchor_poster_lamp_",
        "taxi_road_scarecrow_",
        "taxi_road_paddy_verge_flora",
        "taxi_road_ep1_",
    )
    for o in list(bpy.data.objects):
        if o.name.startswith(prefixes):
            bpy.data.objects.remove(o, do_unlink=True)
    # Purge unused shop materials BEFORE creating fresh ones so zero `.001` duplicate materials accumulate!
    bpy.data.orphans_purge(do_recursive=True)

    rng = np.random.default_rng(2026)
    apply_roadside_details(
        {m.name: m for m in bpy.data.materials},
        rng,
        w,
        road_point,
        road_heading,
        PADDY_WATER,
        library_material,
        plain,
        world_uvs,
        full_gltf_group,
        import_glb,
        None,
    )
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.context.scene.objects:
        if o.type in {"MESH", "EMPTY", "CURVE"}:
            o.select_set(True)
    art = ROOT / "art-source/blender/ep1/ep1_taxi_roadside.blend"
    out = ROOT / "art-export/ep1/ep1_taxi_roadside.glb"
    bpy.ops.wm.save_as_mainfile(filepath=str(art))
    bpy.ops.export_scene.gltf(
        filepath=str(out),
        export_format="GLB",
        use_selection=True,
        export_extras=True,
        export_yup=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
    )
    print("TAXI_ROADSIDE_EXPORTED_OK", len(bpy.context.scene.objects))
