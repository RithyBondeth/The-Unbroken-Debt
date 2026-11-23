"""Production roadside upgrades invoked by tools/travel/build-taxi.py (roadside()).

Adds weathered rural Cambodian roadside timber shops/stalls, wooden roadside poster boards
plastered with REAL Khmer 90s color posters (packed in T_taxi_khmer_posters_BC.png — zero
generated posters!), lantern anchors for runtime flickering pools, scanned rural shop props,
and denser flooded paddy & jungle verge details along build-taxi.py's exact road_x(z) curve.
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
# (row 0 = top in image -> V in [0.75..1.0], row 3 = bottom -> V in [0.0..0.25])
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


def _bm_obj(name, bm, mat, coll, world_uvs_fn=None, smooth=False):
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
    """Append a slightly rain-buckled, weathered poster quad referencing slot `poster_idx` in the shared real Khmer 90s atlas."""
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
                curl += 0.014 * (1 - vf / 0.25) * ((uf - 0.75) / 0.25)
            p = c + r * ((uf - 0.5) * width) + u * ((vf - 0.5) * height) + n * (curl + float(rng.normal(0, 0.001)))
            verts.append(tuple(p))
            uvs.append((u0 + uf * (u1 - u0), v0 + vf * (v1 - v0)))
    for j in range(ny):
        for i in range(nx):
            a = base + j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))


def _load_decimated_scan(filename, ratio=0.30, full_gltf_group=None, import_glb=None):
    """Load a local scan GLB cleanly decimated for roadside passing props (keeps triangle & GLB budget tight!)."""
    path = SCANS / filename
    if not path.exists():
        return []
    if full_gltf_group:
        full_gltf_group()
    objs = import_glb(path)
    out = []
    for o in objs:
        if "_lod" in o.name.lower():
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        if len(o.data.polygons) > 1200 and ratio < 0.99:
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


def _build_shop(coll, M_shop, mats, props, p_verts, p_faces, p_uvs, poster_offset, shop_idx, lit=True):
    """Build one authentic rural Cambodian timber shop with rusty tin awning, real Khmer 90s posters, props & lantern anchor.

    Local shop frame (Blender axes):
      +X faces toward road (width along Y in [-2.6..+2.6], depth along X in [-3.6..0.0], awning extends to +1.65)
      +Y faces BACK toward oncoming car (for right-side shops) or -Y (for left-side shops) — posters on BOTH side walls!
    """
    bm_posts, bm_walls, bm_shut, bm_tin = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()

    # Raised earth/timber foundation plinth reaching well down into flooded paddy water (never floats!)
    _box_bm(bm_posts, (-1.0, 0.0, -0.58), (5.8, 6.0, 1.32))
    _box_bm(bm_walls, (-1.0, 0.0, 0.12), (5.4, 5.5, 0.14))

    for px in (-3.5, 0.0, 1.60):
        h = 3.20 if px == -3.5 else (3.60 if px == 0.0 else 2.52)
        for py in (-2.55, -0.85, 0.85, 2.55):
            if px == 1.60 and py in (-0.85, 0.85):
                continue
            _box_bm(bm_posts, (px, py, h * 0.5), (0.14, 0.14, h + 0.45))
    for py in (-2.55, 0.0, 2.55):
        _box_bm(bm_posts, (-1.75, py, 3.30), (3.7, 0.12, 0.14))
        _box_bm(bm_posts, (0.80, py, 2.92), (1.85, 0.10, 0.12), rot=Euler((0, math.radians(24), 0)))
    for px, pz in [(0.0, 3.50), (1.60, 2.52), (-3.5, 3.10)]:
        _box_bm(bm_posts, (px, 0.0, pz), (0.12, 5.4, 0.14))

    # Back, side, and front plank walls + half-ajar shutters + counter + bench
    _box_bm(bm_walls, (-3.5, 0.0, 1.65), (0.09, 5.2, 3.05))
    for sy in (-2.55, 2.55):
        _box_bm(bm_walls, (-1.75, sy, 1.65), (3.5, 0.09, 3.05))
    _box_bm(bm_walls, (0.0, -1.72, 1.72), (0.09, 1.68, 3.25))
    _box_bm(bm_walls, (0.0, 1.72, 1.72), (0.09, 1.68, 3.25))
    _box_bm(bm_walls, (0.0, 0.0, 0.55), (0.12, 1.80, 0.94))
    _box_bm(bm_walls, (0.0, 0.0, 3.08), (0.10, 1.80, 0.70))
    _box_bm(bm_shut, (0.16, -0.80, 1.86), (0.05, 0.44, 1.70), rot=Euler((0, 0, math.radians(32))))
    _box_bm(bm_shut, (0.14, 0.82, 1.86), (0.05, 0.44, 1.70), rot=Euler((0, 0, math.radians(-26))))
    _box_bm(bm_walls, (0.18, 0.0, 1.02), (0.40, 1.90, 0.06))
    _box_bm(bm_posts, (0.95, -1.52, 0.52), (0.36, 1.42, 0.06))
    for by in (-2.05, -1.00):
        _box_bm(bm_posts, (0.95, by, 0.30), (0.30, 0.07, 0.44))

    # Sloped corrugated rusty tin roof + veranda awning (14 wide corrugated ribs for crisp silhouette & low tris)
    for k in range(14):
        ry = -2.65 + k * 0.41
        _box_bm(bm_tin, (-1.70, ry, 3.44), (4.0, 0.36, 0.035), rot=Euler((0, math.radians(-6), 0)))
        _box_bm(bm_tin, (0.92, ry, 2.94), (2.30, 0.36, 0.035), rot=Euler((0, math.radians(24), 0)))

    # Corner wooden signboard frames on both +Y and -Y awning posts
    _box_bm(bm_posts, (1.60, 2.50, 2.12), (0.06, 1.12, 0.82))
    _box_bm(bm_posts, (1.60, -2.50, 2.12), (0.06, 1.12, 0.82))

    for suffix, bm_d, mt in [
        ("posts", bm_posts, mats["dark_wood"]),
        ("walls", bm_walls, mats["planks"]),
        ("shutters", bm_shut, mats["shutter"]),
        ("tin", bm_tin, mats["tin"]),
    ]:
        o = _bm_obj(f"taxi_road_shop_{shop_idx}_{suffix}", bm_d, mt, coll, world_uvs_fn=mats["world_uvs"], smooth=False)
        o.matrix_world = M_shop

    # Mount REAL Khmer 90s posters on front wall (+X) and BOTH approach side walls (+Y and -Y)
    def to_w(p):
        return M_shop @ Vector(p)

    def dir_w(v):
        return (M_shop.to_3x3() @ Vector(v)).normalized()

    slots = [
        ((0.065, -1.72, 1.92), (0, 1, 0), (0, 0, 1), 0.78, 1.04),    # Front left wall
        ((0.065, 1.72, 1.92), (0, 1, 0), (0, 0, 1), 0.78, 1.04),     # Front right wall
        ((0.065, 0.0, 3.08), (0, 1, 0), (0, 0, 1), 1.38, 0.62),      # Upper shopfront signboard
        ((-0.78, 2.63, 1.92), (-1, 0, 0), (0, 0, 1), 0.90, 1.18),    # +Y side wall poster 1
        ((-1.88, 2.63, 1.88), (-1, 0, 0), (0, 0, 1), 0.92, 1.18),    # +Y side wall poster 2
        ((-0.78, -2.63, 1.92), (1, 0, 0), (0, 0, 1), 0.90, 1.18),    # -Y side wall poster 1
        ((-1.88, -2.63, 1.88), (1, 0, 0), (0, 0, 1), 0.92, 1.18),    # -Y side wall poster 2
        ((1.65, 2.50, 2.12), (0, 1, 0), (0, 0, 1), 1.04, 0.76),      # Corner post board
    ]
    for i, (lp, lr, lu, pw, ph) in enumerate(slots):
        _add_poster_to_lists(
            p_verts, p_faces, p_uvs,
            to_w(lp), dir_w(lr), dir_w(lu),
            pw, ph, poster_offset + i, seed=400 + shop_idx * 20 + i,
        )

    # Scanned rural Cambodian props tucked neatly under the tin veranda awning
    for pkey, lp, pyaw, psc in [
        ("rice_sack", (0.58, 1.50, 0.19), 0.4, 1.12),
        ("water_jar", (1.20, 2.05, 0.18), 0.2, 1.02),
        ("basket_deep", (0.48, -1.85, 0.19), 0.5, 1.35),
        ("clay_stove", (0.55, -0.68, 0.19), 0.3, 1.08),
        ("kettle", (0.20, 0.28, 1.05), -0.6, 1.08),
    ]:
        if props.get(pkey):
            M_p = M_shop @ Matrix.Translation(lp) @ Matrix.Rotation(pyaw, 4, "Z") @ Matrix.Scale(psc, 4)
            _place_linked(props[pkey], coll, M_p, f"shop_{shop_idx}_{pkey}")

    # Hanging lantern glass & warm flame mesh + empty anchor node for runtime flickering PointLight!
    if lit:
        bm_gl = bmesh.new()
        bmesh.ops.create_uvsphere(bm_gl, u_segments=10, v_segments=8, radius=0.055, matrix=Matrix.Translation((0.88, 0.15, 2.34)))
        gl = _bm_obj(f"taxi_road_shop_{shop_idx}_bulb", bm_gl, mats["bulb"], coll, smooth=True)
        gl.matrix_world = M_shop

        anc = bpy.data.objects.new(f"taxi_road_anchor_shop_lamp_{shop_idx}", None)
        coll.objects.link(anc)
        anc.location = to_w((0.92, 0.15, 2.28))


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
    """Build roadside Cambodian shops with REAL Khmer 90s posters, poster boards, scarecrow & richer verge props."""
    coll = bpy.context.scene.collection

    # Shared shop & real Khmer 90s poster atlas materials (1 draw call for all posters!)
    poster_path = TEX / "T_taxi_khmer_posters_BC.png"
    poster_mat = plain("M_taxi_khmer_posters", (1, 1, 1), 0.42, 0.0)
    nt = poster_mat.node_tree
    bs = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(poster_path), check_existing=True)
    nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
    poster_mat.use_backface_culling = False

    shop_mats = {
        "planks": library_material("weathered_planks", "M_taxi_shop_planks", tint=(0.36, 0.28, 0.22), tile=1.4),
        "dark_wood": library_material("dark_wood", "M_taxi_shop_posts", tint=(0.28, 0.22, 0.17), tile=1.2),
        "shutter": library_material("wood_shutter", "M_taxi_shop_shutters", tint=(0.24, 0.34, 0.28), tile=1.0),
        "tin": library_material("rusty_metal", "M_taxi_shop_tin", tint=(0.44, 0.36, 0.30), tile=1.2),
        "bulb": plain("M_taxi_shop_bulb", (1.0, 0.72, 0.34), 0.2, 0.0, emission=(1.0, 0.65, 0.28), strength=8.0),
        "world_uvs": world_uvs_fn,
    }

    # Decimated rural shop props + roadside scarecrow (shared linked copies -> tiny triangle/byte footprint!)
    props = {
        "rice_sack": _load_decimated_scan("rice_sack.glb", 0.25, full_gltf_group, import_glb),
        "water_jar": _load_decimated_scan("water_jar.glb", 0.22, full_gltf_group, import_glb),
        "basket_deep": _load_decimated_scan("basket_deep.glb", 0.25, full_gltf_group, import_glb),
        "clay_stove": _load_decimated_scan("clay_stove.glb", 0.25, full_gltf_group, import_glb),
        "kettle": _load_decimated_scan("kettle.glb", 0.30, full_gltf_group, import_glb),
    }
    scarecrow = _load_decimated_scan("scarecrow.glb", 0.45, full_gltf_group, import_glb)

    p_verts, p_faces, p_uvs = [], [], []

    # 4 weathered Cambodian roadside timber shops along the paddy road & village approach!
    # In build-taxi.py Babylon coords: +lateral = Sora's right side (Blender -X), -lateral = driver's left side (Blender +X).
    # road_point(lat, y, z) -> w(...) gives Blender world point.
    # For right-side shops (lat > 0, Blender -X): local +X points toward road (+X in Blender), yaw = -road_heading(z) + small angle!
    # For left-side shops (lat < 0, Blender +X): local +X points toward road (-X in Blender), yaw = pi - road_heading(z)!
    shop_specs = [
        # (lateral_babylon, z_along, extra_yaw, poster_offset, lit)
        (6.8, 28.0, 0.14, 0, True),     # Right side (Sora's side) early paddy barber/salon shop!
        (-7.0, 64.0, -0.12, 4, True),   # Left side mid-paddy shop with dentist/watch/salon signs!
        (6.8, 102.0, 0.16, 8, True),    # Right side second village-edge moto/band/barber shop!
        (-7.2, 134.0, -0.10, 12, True), # Last dim shuttered wooden shop before dark jungle begins!
    ]
    for idx, (lat, z_pos, eyaw, poff, lit) in enumerate(shop_specs):
        pos_bl = w(road_point(lat, -0.16, z_pos))
        base_yaw = -road_heading(z_pos) if lat > 0 else (math.pi - road_heading(z_pos))
        M_shop = Matrix.Translation(pos_bl) @ Matrix.Rotation(base_yaw + eyaw, 4, "Z")
        _build_shop(coll, M_shop, shop_mats, props, p_verts, p_faces, p_uvs, poff, idx, lit=lit)

    # 4 weathered roadside wooden poster boards right at the embankment verge catching the oncoming headlights!
    # Placed at |lat| = 4.25 m (cleanly outside PLANT_CLEARANCE = 3.4 m) facing straight back along road tangent!
    board_specs = [
        (-4.35, 19.0, 0, 8),    # Left verge: កាត់សក់ + កាត់សក់ ជាង លេង
        (4.35, 48.0, 4, 6),     # Right verge: រចនា អ៊ុតសក់ + គីម ចេង ដាក់ធ្មេញ
        (-4.35, 84.0, 13, 14),  # Left verge: ក្រុមតន្ត្រីសម័យពន្លឺថ្មី + 90s barber
        (4.35, 118.0, 1, 15),   # Right verge: សត្វមនោហ៍ + កាត់សក់ចន្ទ្រា
    ]
    for b_idx, (lat, z_pos, p_a, p_b) in enumerate(board_specs):
        pos_bl = w(road_point(lat, -0.22, z_pos))
        # Heading in Blender Z-rotation: oncoming car travels along -Y at road_heading(z_pos)
        ang = -road_heading(z_pos) + (-0.18 if lat < 0 else 0.18)
        M_b = Matrix.Translation(pos_bl) @ Matrix.Rotation(ang, 4, "Z")
        bm_b = bmesh.new()
        _box_bm(bm_b, (-0.64, 0.0, 1.08), (0.09, 0.09, 2.45))
        _box_bm(bm_b, (0.64, 0.0, 1.08), (0.09, 0.09, 2.45))
        _box_bm(bm_b, (0.0, 0.0, 1.54), (1.48, 0.06, 1.12))
        # Small rusty tin rain hood above poster board
        _box_bm(bm_b, (0.0, 0.14, 2.14), (1.56, 0.36, 0.03), rot=Euler((math.radians(18), 0, 0)))
        bo = _bm_obj(f"taxi_road_poster_board_{b_idx}", bm_b, shop_mats["dark_wood"], coll, world_uvs_fn=world_uvs_fn, smooth=False)
        bo.matrix_world = M_b

        def bw(p):
            return M_b @ Vector(p)

        def bdir(v):
            return (M_b.to_3x3() @ Vector(v)).normalized()

        # Front face (+Y in local -> faces back toward approaching car!): viewer's right is (-1, 0, 0)
        _add_poster_to_lists(p_verts, p_faces, p_uvs, bw((0.35, 0.044, 1.54)), bdir((-1, 0, 0)), bdir((0, 0, 1)), 0.64, 0.94, p_a, seed=700 + b_idx * 4)
        _add_poster_to_lists(p_verts, p_faces, p_uvs, bw((-0.35, 0.044, 1.54)), bdir((-1, 0, 0)), bdir((0, 0, 1)), 0.64, 0.94, p_b, seed=701 + b_idx * 4)

        # Anchor for dim warm hooded signboard bulb so posters glow vividly through the rain & mist!
        anc = bpy.data.objects.new(f"taxi_road_anchor_poster_lamp_{b_idx}", None)
        coll.objects.link(anc)
        anc.location = bw((0.0, 0.42, 2.02))

    # Build ONE combined mesh for all real Khmer 90s color posters (1 draw call, UV-mapped to T_taxi_khmer_posters_BC.png!)
    if p_verts:
        _mesh_uv("taxi_road_khmer_posters", p_verts, p_faces, p_uvs, poster_mat, coll, smooth=True)

    # Eerie rural scarecrow standing out in the flooded rice paddies
    if scarecrow:
        for lat, z_pos, syaw in [(-11.5, 42.0, 0.4), (12.8, 112.0, -0.7)]:
            M_sc = Matrix.Translation(w(road_point(lat, PADDY_WATER + 0.08, z_pos))) @ Matrix.Rotation(syaw, 4, "Z") @ Matrix.Scale(1.08, 4)
            _place_linked(scarecrow, coll, M_sc, f"scarecrow_{int(z_pos)}")

    # Enrich paddy embankment shoulders (-15..142) with tangled wet ferns & verge grass (strictly respecting clearance > 3.5 m!)
    if plant_fn is not None:
        for side in (-1, 1):
            z_cur = -10.0
            while z_cur < 142.0:
                near_shop = any(abs(z_cur - sz) < 6.5 and (slat * side > 0) for slat, sz, *_ in shop_specs)
                if not near_shop:
                    kind = "fern_02_b" if rng.random() < 0.55 else "shrub_02_b"
                    plant_fn(kind, side * float(rng.uniform(3.9, 5.1)), z_cur, float(rng.uniform(0.65, 1.15)), lift=-0.42, anywhere=True, label="paddy_verge_flora")
                z_cur += float(rng.uniform(2.6, 4.4))
    else:
        # Clone existing fern/shrub meshes directly from ep1_taxi_roadside.blend (zero new textures, linked instances!)
        ferns = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("taxi_road_fern_02")][:3]
        shrubs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("taxi_road_shrub_02")][:3]
        bananas = [o for o in bpy.data.objects if o.type == "MESH" and "banana" in o.name.lower()][:2]
        flora_pool = ferns + shrubs
        if flora_pool:
            for side in (-1, 1):
                z_cur = -8.0
                while z_cur < 140.0:
                    near_shop = any(abs(z_cur - sz) < 7.5 and (slat * side > 0) for slat, sz, *_ in shop_specs)
                    near_board = any(abs(z_cur - bz) < 4.0 and (blat * side > 0) for blat, bz, *_ in board_specs)
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
        # Extra banana clumps beside the roadside shops so every rural stall sits nestled in Cambodian greenery!
        if bananas:
            for idx, (lat, z_pos, *_rest) in enumerate(shop_specs):
                side = 1 if lat > 0 else -1
                for dz, dlat in [(-4.4, 1.4), (4.5, 1.2)]:
                    src = bananas[idx % len(bananas)]
                    c = src.copy()
                    c.data = src.data
                    coll.objects.link(c)
                    c.parent = None
                    c.name = f"taxi_road_shop_banana_{idx}"
                    c.matrix_world = (
                        Matrix.Translation(w(road_point(lat + side * dlat, PADDY_WATER + 0.15, z_pos + dz)))
                        @ Matrix.Rotation(float(rng.uniform(0, math.tau)), 4, "Z")
                        @ Matrix.Scale(float(rng.uniform(0.85, 1.05)), 4)
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
        "taxi_road_anchor_poster_lamp_",
        "taxi_road_scarecrow_",
        "taxi_road_paddy_verge_flora",
    )
    for o in list(bpy.data.objects):
        if o.name.startswith(prefixes):
            bpy.data.objects.remove(o, do_unlink=True)

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
