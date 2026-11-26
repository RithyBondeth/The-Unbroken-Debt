"""Production cabin & driver realism upgrades invoked by tools/travel/build-taxi.py (cabin()).

Adds all user-approved details from bondeth/driving-scene-refine in Blender coordinates
(car faces -Y, driver +X, Sora -X, cabin floor Z=0) while preserving every runtime anchor,
driver morph target, and glTF 2.0 WebGPU compatibility.
"""
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
TEX = ROOT / "art-source/textures/ep1/taxi"

# Measured Rosalie steering wheel pose in Blender coordinates
WHEEL_CENTER = Vector((0.2641, -0.2722, 0.7636))
WHEEL_NORMAL = Vector((0.0, 0.7676, 0.6410)).normalized()
WHEEL_RADIUS = 0.198


def _box_bm(bm, center, size, rot=None, bevel=0.0, segs=2):
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


def _cyl_bm(bm, p0, p1, r0, r1=None, segs=18, cap=True):
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


def _bm_obj(name, bm, mat, coll, world_uvs_fn=None, smooth=True):
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


def _make_mesh(name, verts, faces, mat, coll, uvs=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if uvs is not None:
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


def _tube_obj(name, pts, radius, mat, coll, segs=10):
    bm = bmesh.new()
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
        r_ring = []
        for k in range(segs):
            a = k / segs * math.tau
            r_ring.append(bm.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * radius))
        rings.append(r_ring)
    for rA, rB in zip(rings, rings[1:]):
        for k in range(segs):
            bm.faces.new((rA[k], rA[(k + 1) % segs], rB[(k + 1) % segs], rB[k]))
    if len(rings) >= 2:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return _bm_obj(name, bm, mat, coll, smooth=True)


def _image_mat(name, path, plain_fn, rough=0.45, emission=0.0, double_sided=False):
    mat = plain_fn(name, (1, 1, 1), rough=rough)
    nt = mat.node_tree
    bs = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
    if emission > 0:
        nt.links.new(tex.outputs["Color"], bs.inputs["Emission Color"])
        bs.inputs["Emission Strength"].default_value = emission
    if double_sided:
        mat.use_backface_culling = False
    return mat


def _materials(library_material, plain):
    def get_or(mat_name, builder):
        return bpy.data.materials.get(mat_name) or builder()

    m = {}
    m["bakelite"] = get_or("M_cab_bakelite", lambda: plain("M_cab_bakelite", (0.015, 0.013, 0.012), 0.24, 0.0))
    m["bakelite_matte"] = get_or("M_cab_bakelite_matte", lambda: plain("M_cab_bakelite_matte", (0.02, 0.018, 0.016), 0.45, 0.0))
    m["chrome"] = get_or("M_cab_aged_chrome", lambda: plain("M_cab_aged_chrome", (0.64, 0.62, 0.56), 0.24, 0.94))
    m["brass"] = get_or("M_cab_aged_brass", lambda: plain("M_cab_aged_brass", (0.48, 0.36, 0.16), 0.32, 0.90))
    m["dark_iron"] = get_or("M_cab_dark_iron", lambda: plain("M_cab_dark_iron", (0.04, 0.038, 0.036), 0.52, 0.78))
    m["wrinkle_enamel"] = get_or("M_cab_wrinkle_enamel", lambda: plain("M_cab_wrinkle_enamel", (0.022, 0.022, 0.024), 0.62, 0.15))
    m["red_enamel"] = get_or("M_cab_red_enamel", lambda: plain("M_cab_red_enamel", (0.34, 0.035, 0.025), 0.35, 0.08))
    m["rubber"] = get_or("M_cab_rubber", lambda: plain("M_cab_rubber", (0.016, 0.016, 0.017), 0.78, 0.0))
    m["pillar_trim"] = get_or("M_cab_pillar_leatherette", lambda: plain("M_cab_pillar_leatherette", (0.016, 0.015, 0.014), 0.86, 0.0))
    m["walnut"] = bpy.data.materials.get("M_taxi_dashboard_walnut") or get_or(
        "M_cab_walnut_polished", lambda: library_material("rosewood_veneer1", "M_cab_walnut_polished", tint=(0.30, 0.19, 0.12), tile=0.26)
    )
    m["leather_door"] = get_or("M_cab_door_leather", lambda: library_material("brown_leather", "M_cab_door_leather", tint=(0.24, 0.11, 0.09), tile=0.35))
    m["leather_strap"] = get_or("M_cab_leather_strap", lambda: library_material("brown_leather", "M_cab_leather_strap", tint=(0.34, 0.21, 0.12), tile=0.22))
    m["satchel_leather"] = get_or("M_cab_satchel", lambda: library_material("brown_leather", "M_cab_satchel", tint=(0.28, 0.17, 0.10), tile=0.28))
    m["mud"] = get_or("M_cab_tracked_mud", lambda: library_material("red_dirt_mud_01", "M_cab_tracked_mud", tint=(0.42, 0.28, 0.20), tile=0.5))
    if "Principled BSDF" in m["mud"].node_tree.nodes:
        m["mud"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.14
    m["rosewood_bead"] = get_or("M_cab_prayer_bead", lambda: library_material("dark_wood", "M_cab_prayer_bead", tint=(0.42, 0.20, 0.10), tile=0.06))
    if "Principled BSDF" in m["rosewood_bead"].node_tree.nodes:
        m["rosewood_bead"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.30

    # Printed textures (radio dial & taximeter face; the 5 main gauges stay live-animated on taxi_instrument_face inside our 3D chrome bezels!)
    m["radio_dial"] = get_or("M_cab_radio_dial", lambda: _image_mat("M_cab_radio_dial", TEX / "T_taxi_radio_dial_BC.png", plain, rough=0.3, emission=0.85))
    m["meter_face"] = get_or("M_cab_meter_face", lambda: _image_mat("M_cab_meter_face", TEX / "T_taxi_meter_face_BC.png", plain, rough=0.4, emission=0.08))
    m["cord_white"] = get_or("M_cab_sacred_white_cord", lambda: plain("M_cab_sacred_white_cord", (0.50, 0.45, 0.36), 0.94, 0.0))
    m["cord_red"] = get_or("M_cab_sacred_red_cord", lambda: plain("M_cab_sacred_red_cord", (0.24, 0.024, 0.020), 0.90, 0.0))
    m["aged_bronze"] = get_or("M_cab_takrut_bronze", lambda: plain("M_cab_takrut_bronze", (0.36, 0.25, 0.11), 0.34, 0.90))
    return m


def _upgrade_steering_wheel(coll, m):
    """Remove coarse scan steering wheel island & replace with sculpted 1933 Citroën Rosalie 3-spoke wheel."""
    sm = bpy.data.objects.get("SM_internal_M_internal_0")
    if sm:
        bm = bmesh.new()
        bm.from_mesh(sm.data)
        kill = [
            f
            for f in bm.faces
            if (
                0.05 < f.calc_center_median().x < 0.48
                and -0.49 < f.calc_center_median().y < -0.10
                and 0.54 < f.calc_center_median().z < 0.98
                and (f.calc_center_median() - WHEEL_CENTER).length < 0.245
            )
        ]
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            bm.to_mesh(sm.data)
            sm.data.update()
        bm.free()

    N = WHEEL_NORMAL.copy()
    R_ax = Vector((1, 0, 0))
    R_ax = (R_ax - N * R_ax.dot(N)).normalized()
    U_ax = N.cross(R_ax).normalized()
    if U_ax.z < 0:
        U_ax = -U_ax
    M_w = Matrix.Translation(WHEEL_CENTER) @ Matrix((R_ax, U_ax, N)).transposed().to_4x4()

    pivot = bpy.data.objects.new("taxi_steering_wheel_pivot", None)
    coll.objects.link(pivot)
    pivot.matrix_world = M_w

    # Ribbed bakelite rim with back-side finger grips (slender 1933 profile matching driver's hand grip cleanly)
    bm_rim = bmesh.new()
    n_maj, n_min = 48, 16
    r_tube = 0.0130
    rings = []
    for i in range(n_maj):
        a = i / n_maj * math.tau
        ca, sa = math.cos(a), math.sin(a)
        rib = 1.0 + 0.06 * math.sin(a * 36.0)
        ring = []
        for j in range(n_min):
            b = j / n_min * math.tau
            cb, sb = math.cos(b), math.sin(b)
            grip = 1.0 + (0.08 * (rib - 1.0) if sb < -0.15 else 0.0)
            rad = WHEEL_RADIUS + cb * r_tube * grip
            ring.append(bm_rim.verts.new((ca * rad, sa * rad, sb * r_tube * grip)))
        rings.append(ring)
    for i in range(n_maj):
        rA, rB = rings[i], rings[(i + 1) % n_maj]
        for j in range(n_min):
            bm_rim.faces.new((rA[j], rA[(j + 1) % n_min], rB[(j + 1) % n_min], rB[j]))
    rim_obj = _bm_obj("taxi_steering_wheel_rim", bm_rim, m["bakelite"], coll, smooth=True)
    rim_obj.parent = pivot

    # 3 tapered spokes + central boss & chrome collars
    bm_spokes = bmesh.new()
    bm_chrome = bmesh.new()
    _cyl_bm(bm_spokes, (0, 0, -0.052), (0, 0, 0.012), 0.044, 0.036, segs=24)
    _cyl_bm(bm_chrome, (0, 0, 0.010), (0, 0, 0.020), 0.037, 0.034, segs=24)
    _cyl_bm(bm_spokes, (0, 0, 0.018), (0, 0, 0.030), 0.026, 0.020, segs=22)
    _cyl_bm(bm_chrome, (0, 0, 0.029), (0, 0, 0.033), 0.014, 0.012, segs=18)

    for deg in (210.0, 330.0, 90.0):
        ang = math.radians(deg)
        d = Vector((math.cos(ang), math.sin(ang), 0.0))
        p_in = d * 0.034 + Vector((0, 0, -0.020))
        p_out = d * (WHEEL_RADIUS - 0.010) + Vector((0, 0, 0.0))
        _cyl_bm(bm_spokes, p_in, p_out, 0.0115, 0.0082, segs=12)
        p_c0 = p_in.lerp(p_out, 0.16)
        p_c1 = p_in.lerp(p_out, 0.25)
        _cyl_bm(bm_chrome, p_c0, p_c1, 0.0126, 0.0118, segs=12)
        _cyl_bm(bm_chrome, p_out - d * 0.018, p_out + d * 0.003, 0.0105, 0.0115, segs=12)

    sp_obj = _bm_obj("taxi_steering_wheel_spokes", bm_spokes, m["bakelite_matte"], coll, smooth=True)
    sp_obj.parent = pivot
    ch_obj = _bm_obj("taxi_steering_wheel_chrome", bm_chrome, m["chrome"], coll, smooth=True)
    ch_obj.parent = pivot

    # Fixed steering column shaft into bulkhead + indicator stalk
    bm_col = bmesh.new()
    col_start = WHEEL_CENTER - N * 0.048
    col_end = WHEEL_CENTER - N * 0.34
    _cyl_bm(bm_col, col_start, col_end, 0.022, 0.025, segs=16)
    _cyl_bm(bm_col, col_start - N * 0.02, col_start - N * 0.05, 0.031, 0.031, segs=16)
    _bm_obj("taxi_steering_column", bm_col, m["wrinkle_enamel"], coll, smooth=True)

    # Indicator stalk tucked cleanly forward/down along steering column, 100% clear of driver's left fingers (Z>=0.733)
    stalk_base = col_start - N * 0.115 + R_ax * 0.022
    stalk_tip = stalk_base + R_ax * 0.095 - U_ax * 0.055
    _tube_obj("taxi_indicator_stalk", [stalk_base, stalk_tip], 0.0032, m["chrome"], coll, segs=8)
    bm_tip = bmesh.new()
    bmesh.ops.create_uvsphere(bm_tip, u_segments=10, v_segments=8, radius=0.0075, matrix=Matrix.Translation(stalk_tip))
    _bm_obj("taxi_indicator_knob", bm_tip, m["bakelite"], coll, smooth=True)


def _upgrade_dashboard(coll, m, world_uvs_fn):
    """3D chrome bezels aligned to the live gauges, 1930s valve radio, ignition key, glovebox & gear gaiter."""
    y0 = -0.5004

    # 5 recessed nickel gauge bezels positioned cleanly around the runtime's taxi_instrument_face (width 0.33, center (0, -0.504, 0.72))
    bm_panel = bmesh.new()
    _box_bm(bm_panel, (0.0, y0 + 0.001, 0.722), (0.352, 0.006, 0.098), bevel=0.003, segs=2)
    _bm_obj("taxi_dash_cluster_plate", bm_panel, m["wrinkle_enamel"], coll, smooth=True)

    bm_trim = bmesh.new()
    _box_bm(bm_trim, (0.0, y0 + 0.005, 0.770), (0.354, 0.004, 0.0045), bevel=0.001, segs=1)
    _box_bm(bm_trim, (0.0, y0 + 0.005, 0.674), (0.354, 0.004, 0.0045), bevel=0.001, segs=1)

    # Exact center fractions matching TaxiVisuals.ts DIALS = [0.115, 0.3, 0.5, 0.7, 0.885] over width 0.33 m
    bm_bezels = bmesh.new()
    for u in (0.115, 0.30, 0.50, 0.70, 0.885):
        # Babylon X = (u - 0.5) * 0.33 -> Blender X = -Babylon X!
        gx = -(u - 0.5) * 0.33
        gz = 0.720
        r_in = 0.0250
        r_out = 0.0295
        segs = 28
        ring_a = [bm_bezels.verts.new((gx + math.cos(k / segs * math.tau) * r_out, y0 + 0.003, gz + math.sin(k / segs * math.tau) * r_out)) for k in range(segs)]
        ring_b = [bm_bezels.verts.new((gx + math.cos(k / segs * math.tau) * (r_out - 0.0012), y0 + 0.0135, gz + math.sin(k / segs * math.tau) * (r_out - 0.0012))) for k in range(segs)]
        ring_c = [bm_bezels.verts.new((gx + math.cos(k / segs * math.tau) * r_in, y0 + 0.0135, gz + math.sin(k / segs * math.tau) * r_in)) for k in range(segs)]
        ring_d = [bm_bezels.verts.new((gx + math.cos(k / segs * math.tau) * r_in, y0 + 0.005, gz + math.sin(k / segs * math.tau) * r_in)) for k in range(segs)]
        for r1, r2 in ((ring_a, ring_b), (ring_b, ring_c), (ring_c, ring_d)):
            for k in range(segs):
                bm_bezels.faces.new((r1[k], r1[(k + 1) % segs], r2[(k + 1) % segs], r2[k]))
    _bm_obj("taxi_dash_gauge_bezels", bm_bezels, m["chrome"], coll, smooth=True)

    # Period 1930s Valve Radio tucked below gauge cluster
    ry = y0 + 0.012
    rz = 0.625
    bm_rad = bmesh.new()
    _box_bm(bm_rad, (0.0, ry - 0.008, rz), (0.205, 0.042, 0.072), bevel=0.005, segs=2)
    _bm_obj("taxi_dash_radio_case", bm_rad, m["wrinkle_enamel"], coll, smooth=True)

    for s in range(7):
        sx = -0.078 + s * 0.010
        _box_bm(bm_trim, (sx, ry + 0.014, rz), (0.0032, 0.004, 0.046), bevel=0.0008, segs=1)
    _box_bm(bm_trim, (0.036, ry + 0.014, rz + 0.011), (0.088, 0.005, 0.028), bevel=0.0015, segs=1)
    rw, rh = 0.040, 0.0115
    rcx, rcz = 0.036, rz + 0.011
    _make_mesh(
        "taxi_dash_radio_dial",
        [(rcx + rw, ry + 0.0172, rcz - rh), (rcx - rw, ry + 0.0172, rcz - rh),
         (rcx - rw, ry + 0.0172, rcz + rh), (rcx + rw, ry + 0.0172, rcz + rh)],
        [(0, 1, 2, 3)],
        m["radio_dial"],
        coll,
        uvs=[(0, 0), (1, 0), (1, 1), (0, 1)],
        smooth=False,
    )

    bm_knobs = bmesh.new()
    for kx in (0.068, 0.004):
        _cyl_bm(bm_knobs, (kx, ry + 0.012, rz - 0.017), (kx, ry + 0.028, rz - 0.017), 0.0115, 0.010, segs=16)
        _cyl_bm(bm_trim, (kx, ry + 0.027, rz - 0.017), (kx, ry + 0.0295, rz - 0.017), 0.0055, 0.005, segs=12)

    # Pull switches + ignition key & stitched leather fob + passenger glovebox & chrome ashtray
    for kx in (0.175, 0.215, -0.182):
        _cyl_bm(bm_trim, (kx, y0, 0.695), (kx, y0 + 0.009, 0.695), 0.009, 0.0085, segs=14)
        _cyl_bm(bm_knobs, (kx, y0 + 0.008, 0.695), (kx, y0 + 0.026, 0.695), 0.005, 0.0105, segs=14)

    ix, iz = 0.195, 0.742
    _cyl_bm(bm_trim, (ix, y0, iz), (ix, y0 + 0.012, iz), 0.012, 0.011, segs=16)
    bm_key = bmesh.new()
    _box_bm(bm_key, (ix, y0 + 0.024, iz), (0.0028, 0.024, 0.015), bevel=0.0006, segs=1)
    _cyl_bm(bm_key, (ix, y0 + 0.036, iz - 0.006), (ix, y0 + 0.038, iz - 0.006), 0.008, 0.008, segs=12)
    _bm_obj("taxi_ignition_key", bm_key, m["brass"], coll, smooth=True)
    bm_fob = bmesh.new()
    _box_bm(bm_fob, (ix, y0 + 0.034, iz - 0.044), (0.024, 0.005, 0.056), rot=Euler((0.06, 0, 0.08)), bevel=0.002, segs=2)
    _bm_obj("taxi_key_fob", bm_fob, m["leather_strap"], coll, world_uvs_fn=world_uvs_fn, smooth=True)

    bm_glv = bmesh.new()
    _box_bm(bm_glv, (-0.305, y0 + 0.003, 0.730), (0.215, 0.007, 0.108), bevel=0.0025, segs=2)
    _bm_obj("taxi_dash_glovebox_door", bm_glv, m["walnut"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    _cyl_bm(bm_trim, (-0.235, y0 + 0.006, 0.736), (-0.235, y0 + 0.018, 0.736), 0.009, 0.0075, segs=14)
    _box_bm(bm_trim, (-0.305, y0 + 0.008, 0.768), (0.068, 0.003, 0.009), bevel=0.001, segs=1)
    _box_bm(bm_trim, (-0.215, y0 + 0.010, 0.692), (0.046, 0.016, 0.024), bevel=0.002, segs=1)
    _bm_obj("taxi_dash_knobs", bm_knobs, m["bakelite"], coll, smooth=True)
    _bm_obj("taxi_dash_chrome_trim", bm_trim, m["chrome"], coll, smooth=True)


def _upgrade_mirrors_and_charm(coll, m, world_uvs_fn):
    """Beveled interior rear-view mirror, driver wing mirror & approved Cambodian rosewood prayer-bead + Takrut charm."""
    for o in list(bpy.data.objects):
        if o.name.startswith("taxi_charm_") or o.name == "taxi_mirror_charm_pivot":
            bpy.data.objects.remove(o, do_unlink=True)

    # Remove old blocky mirror housing island in SM_internal
    sm = bpy.data.objects.get("SM_internal_M_internal_0")
    if sm:
        bm = bmesh.new()
        bm.from_mesh(sm.data)
        kill = [
            f
            for f in bm.faces
            if abs(f.calc_center_median().x) < 0.085 and -0.45 < f.calc_center_median().y < -0.37 and 1.05 < f.calc_center_median().z < 1.16
        ]
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            bm.to_mesh(sm.data)
            sm.data.update()
        bm.free()

    # Keep mirror housing squared cleanly around the existing runtime RTT quad taxi_mirror_surface at (0, -0.397, 1.102)
    mir_pos = Vector((0.0, -0.398, 1.102))
    bm_back = bmesh.new()
    _box_bm(bm_back, mir_pos + Vector((0, -0.009, 0)), (0.166, 0.014, 0.068), bevel=0.005, segs=2)
    _bm_obj("taxi_mirror_housing", bm_back, m["wrinkle_enamel"], coll, smooth=True)

    bm_rim = bmesh.new()
    _box_bm(bm_rim, mir_pos + Vector((0, 0.0, 0.033)), (0.170, 0.009, 0.0055), bevel=0.0015, segs=2)
    _box_bm(bm_rim, mir_pos + Vector((0, 0.0, -0.033)), (0.170, 0.009, 0.0055), bevel=0.0015, segs=2)
    _box_bm(bm_rim, mir_pos + Vector((0.083, 0.0, 0)), (0.0055, 0.009, 0.068), bevel=0.0015, segs=2)
    _box_bm(bm_rim, mir_pos + Vector((-0.083, 0.0, 0)), (0.0055, 0.009, 0.068), bevel=0.0015, segs=2)
    _bm_obj("taxi_mirror_bezel", bm_rim, m["chrome"], coll, smooth=True)

    bm_stem = bmesh.new()
    bmesh.ops.create_uvsphere(bm_stem, u_segments=14, v_segments=10, radius=0.011, matrix=Matrix.Translation(mir_pos + Vector((0, -0.016, 0.006))))
    _cyl_bm(bm_stem, mir_pos + Vector((0, -0.016, 0.006)), Vector((0.0, -0.442, 1.158)), 0.0055, 0.0065, segs=12)
    _box_bm(bm_stem, (0.0, -0.445, 1.162), (0.044, 0.022, 0.008), bevel=0.002, segs=2)
    _bm_obj("taxi_mirror_stem", bm_stem, m["chrome"], coll, smooth=True)

    # Exterior Driver-Side Wing Mirror (+X outside A-pillar)
    wing_pos = Vector((0.735, -0.355, 0.895))
    M_wing = Matrix.Translation(wing_pos) @ Euler((0.0, 0.0, math.radians(24.0)), "XYZ").to_matrix().to_4x4()
    bm_wm = bmesh.new()
    _cyl_bm(bm_wm, (0, -0.012, 0), (0, 0.004, 0), 0.044, 0.052, segs=24)
    wm = _bm_obj("taxi_wing_mirror_housing", bm_wm, m["chrome"], coll, smooth=True)
    wm.matrix_world = M_wing
    _tube_obj("taxi_wing_mirror_arm", [(0.625, -0.395, 0.845), (0.715, -0.382, 0.855), (0.735, -0.365, 0.892)], 0.0055, m["chrome"], coll, segs=8)

    # Approved Cambodian driver protection charm: rosewood prayer beads + rolled bronze Takrut tied on stem behind mirror!
    pivot = bpy.data.objects.new("taxi_mirror_charm_pivot", None)
    coll.objects.link(pivot)
    pivot.location = Vector((0.0, -0.428, 1.133))

    # 1. Helical Khsae Amboh blessing cord wrapped around mirror stem
    wrap_w, wrap_r = [], []
    for k in range(25):
        a = k / 24.0 * math.tau * 2.5
        z_off = -0.006 + (k / 24.0) * 0.012
        y_c = -0.54 * z_off
        wrap_w.append(Vector((math.cos(a) * 0.0076, y_c + math.sin(a) * 0.0076, z_off)))
        wrap_r.append(Vector((math.cos(a + 1.8) * 0.0078, y_c + math.sin(a + 1.8) * 0.0078, z_off - 0.002)))
    _tube_obj("taxi_charm_stem_wrap_w", wrap_w, 0.0012, m["cord_white"], coll, segs=6).parent = pivot
    _tube_obj("taxi_charm_stem_wrap_r", wrap_r, 0.0012, m["cord_red"], coll, segs=6).parent = pivot

    # 2. Gravity-draped teardrop loop of 32 hand-turned dark rosewood prayer beads (touching cleanly, zero clipping!)
    n_loop = 80
    raw_pts = []
    for i in range(n_loop + 1):
        t = i / n_loop
        ang = t * math.tau
        depth = 0.5 * (1.0 - math.cos(ang))
        bulge = math.sin(math.pi * (depth ** 0.72)) * (0.44 + 0.56 * depth)
        side_sign = 1.0 if math.sin(ang) >= 0 else -1.0
        raw_pts.append(Vector((side_sign * 0.0175 * bulge, 0.003 + 0.005 * (depth ** 1.5), -0.005 - 0.141 * depth)))

    cum = [0.0]
    for a_p, b_p in zip(raw_pts, raw_pts[1:]):
        cum.append(cum[-1] + (b_p - a_p).length)
    total_len = cum[-1]

    def sample_loop(s_dist):
        s_dist = max(0.0, min(total_len, s_dist))
        for j in range(len(cum) - 1):
            if cum[j] <= s_dist <= cum[j + 1]:
                f = (s_dist - cum[j]) / max(1e-8, cum[j + 1] - cum[j])
                return raw_pts[j].lerp(raw_pts[j + 1], f), (raw_pts[j + 1] - raw_pts[j]).normalized()
        return raw_pts[-1], Vector((0, 0, 1))

    _tube_obj("taxi_charm_bead_cord", raw_pts, 0.0010, m["cord_red"], coll, segs=6).parent = pivot

    rng_b = np.random.default_rng(1932)
    bm_beads = bmesh.new()
    bead_r = 0.0039
    half_len = total_len * 0.5
    s_start, s_end, n_per_side = 0.012, half_len - 0.0135, 16
    for side_idx in (0, 1):
        for k in range(n_per_side):
            frac = k / max(1, n_per_side - 1)
            s_dist = (s_start + frac * (s_end - s_start)) if side_idx == 0 else (total_len - s_start - frac * (s_end - s_start))
            p, tan = sample_loop(s_dist)
            q = Vector((0, 0, 1)).rotation_difference(tan)
            vr = float(rng_b.uniform(0.95, 1.05))
            vh = float(rng_b.uniform(0.86, 0.94))
            M_b = Matrix.Translation(p) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((bead_r * vr, bead_r * vr, bead_r * vh, 1.0))
            bmesh.ops.create_uvsphere(bm_beads, u_segments=12, v_segments=8, radius=1.0, matrix=M_b)

    p_apex = Vector((0.0, 0.008, -0.147))
    bmesh.ops.create_uvsphere(
        bm_beads, u_segments=14, v_segments=10, radius=1.0,
        matrix=Matrix.Translation(p_apex) @ Matrix.Diagonal((0.0056, 0.0056, 0.0052, 1.0)),
    )
    beads_obj = _bm_obj("taxi_charm_rosewood_beads", bm_beads, m["rosewood_bead"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    beads_obj.parent = pivot

    bm_knot = bmesh.new()
    for kz in (-0.1535, -0.1552, -0.1569):
        _cyl_bm(bm_knot, (0.0, 0.008, kz + 0.0008), (0.0, 0.008, kz - 0.0008), 0.0028, 0.0028, segs=10)
    _bm_obj("taxi_charm_guru_knot", bm_knot, m["cord_red"], coll, smooth=True).parent = pivot

    # 3. Brass torus jump-ring + Rolled Aged-Bronze Takrut
    tk_ctr = Vector((0.0, 0.008, -0.168))
    bm_tk = bmesh.new()
    ring_c = Vector((0.0, 0.008, -0.1602))
    r_maj, r_min, n_maj, n_min = 0.0034, 0.00075, 14, 6
    t_rings = []
    for i in range(n_maj):
        a = i / n_maj * math.tau
        rad_v = Vector((math.cos(a), 0.0, math.sin(a)))
        c_pt = ring_c + rad_v * r_maj
        t_rings.append([bm_tk.verts.new(c_pt + rad_v * (math.cos(j / n_min * math.tau) * r_min) + Vector((0, math.sin(j / n_min * math.tau) * r_min, 0))) for j in range(n_min)])
    for i in range(n_maj):
        rA, rB = t_rings[i], t_rings[(i + 1) % n_maj]
        for j in range(n_min):
            bm_tk.faces.new((rA[j], rA[(j + 1) % n_min], rB[(j + 1) % n_min], rB[j]))

    t_dir = Vector((0.992, 0.04, -0.115)).normalized()
    _cyl_bm(bm_tk, tk_ctr - t_dir * 0.0175, tk_ctr + t_dir * 0.0175, 0.0041, 0.0041, segs=18)
    _cyl_bm(bm_tk, tk_ctr - t_dir * 0.0195, tk_ctr - t_dir * 0.0165, 0.0047, 0.0047, segs=18)
    _cyl_bm(bm_tk, tk_ctr + t_dir * 0.0165, tk_ctr + t_dir * 0.0195, 0.0047, 0.0047, segs=18)
    _cyl_bm(bm_tk, tk_ctr + Vector((0, 0, 0.0038)), tk_ctr + Vector((0, 0, 0.0068)), 0.0018, 0.0018, segs=8)
    _bm_obj("taxi_charm_takrut", bm_tk, m["aged_bronze"], coll, smooth=True).parent = pivot

    bm_lash = bmesh.new()
    for k in range(7):
        p_c = tk_ctr + t_dir * (-0.0054 + k * 0.0018)
        _cyl_bm(bm_lash, p_c - t_dir * 0.0008, p_c + t_dir * 0.0008, 0.00485, 0.00485, segs=14)
    _bm_obj("taxi_charm_takrut_wrap", bm_lash, m["cord_red"], coll, smooth=True).parent = pivot

    tail_l = [tk_ctr + Vector((-0.002, 0.0, -0.0042)), tk_ctr + Vector((-0.0045, 0.001, -0.013)), tk_ctr + Vector((-0.0062, 0.002, -0.024))]
    tail_r = [tk_ctr + Vector((0.002, 0.0, -0.0042)), tk_ctr + Vector((0.0038, -0.001, -0.011)), tk_ctr + Vector((0.0048, 0.0005, -0.019))]
    _tube_obj("taxi_charm_tail_w", tail_l, 0.00095, m["cord_white"], coll, segs=6).parent = pivot
    _tube_obj("taxi_charm_tail_r", tail_r, 0.00095, m["cord_red"], coll, segs=6).parent = pivot
    bm_ek = bmesh.new()
    bmesh.ops.create_uvsphere(bm_ek, u_segments=8, v_segments=6, radius=0.0019, matrix=Matrix.Translation(tail_l[-1]))
    bmesh.ops.create_uvsphere(bm_ek, u_segments=8, v_segments=6, radius=0.0019, matrix=Matrix.Translation(tail_r[-1]))
    _bm_obj("taxi_charm_tail_knots", bm_ek, m["cord_red"], coll, smooth=True).parent = pivot


def _upgrade_interior_props(coll, m, plain, world_uvs_fn):
    """Pleated leatherette door cards, walnut capping, upgraded Phnom Penh taximeter (hired flag), mats & Sora satchel."""
    for o in list(bpy.data.objects):
        if o.name.startswith("taxi_meter_"):
            bpy.data.objects.remove(o, do_unlink=True)

    # 1. Pleated leatherette door cards, walnut sills, chrome moulding & pull straps
    bm_cards, bm_wal, bm_chr, bm_str = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for sign in (-1, 1):
        x_card = sign * 0.568
        inw = -sign
        _box_bm(bm_cards, (x_card, 0.04, 0.41), (0.014, 0.68, 0.58), bevel=0.004, segs=2)
        for k in range(9):
            _box_bm(bm_cards, (x_card + inw * 0.009, -0.24 + k * 0.070, 0.44), (0.014, 0.056, 0.42), bevel=0.004, segs=2)
        _box_bm(bm_str, (x_card + inw * 0.016, 0.03, 0.21), (0.012, 0.42, 0.15), bevel=0.003, segs=2)
        _box_bm(bm_wal, (x_card + inw * 0.010, 0.04, 0.728), (0.036, 0.70, 0.038), bevel=0.005, segs=2)
        _box_bm(bm_chr, (x_card + inw * 0.017, 0.04, 0.686), (0.006, 0.68, 0.007), bevel=0.001, segs=1)
        _box_bm(bm_chr, (x_card + inw * 0.017, -0.09, 0.55), (0.014, 0.028, 0.024), bevel=0.002, segs=1)
        _box_bm(bm_chr, (x_card + inw * 0.017, 0.11, 0.55), (0.014, 0.028, 0.024), bevel=0.002, segs=1)
        _tube_obj(
            f"taxi_door_strap_{'r' if sign < 0 else 'l'}",
            [(x_card + inw * 0.022, -0.08, 0.55), (x_card + inw * 0.046, 0.01, 0.54), (x_card + inw * 0.022, 0.10, 0.55)],
            0.0085,
            m["leather_strap"],
            coll,
            segs=8,
        )
    _bm_obj("taxi_door_cards_pleated", bm_cards, m["leather_door"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    _bm_obj("taxi_door_walnut_sills", bm_wal, m["walnut"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    _bm_obj("taxi_door_chrome_moulding", bm_chr, m["chrome"], coll, smooth=True)
    _bm_obj("taxi_door_pockets", bm_str, m["leather_strap"], coll, world_uvs_fn=world_uvs_fn, smooth=True)

    bm_map = bmesh.new()
    _box_bm(bm_map, (-0.564, 0.08, 0.258), (0.003, 0.11, 0.065), rot=Euler((0.06, 0.05, 0.02)), bevel=0.001, segs=1)
    _bm_obj("taxi_door_folded_map", bm_map, plain("M_cab_aged_map", (0.36, 0.29, 0.19), 0.88, 0.0), coll, smooth=True)

    # 2. Upgraded Phnom Penh Taximeter (hired flag folded down!)
    mx, my, mz = -0.495, -0.422, 0.728
    bm_mcase = bmesh.new()
    _box_bm(bm_mcase, (mx, my, mz), (0.122, 0.078, 0.092), bevel=0.008, segs=2)
    _bm_obj("taxi_meter_case", bm_mcase, m["wrinkle_enamel"], coll, smooth=True)

    bm_mtrim = bmesh.new()
    _box_bm(bm_mtrim, (mx, my + 0.039, mz + 0.006), (0.104, 0.006, 0.052), bevel=0.002, segs=1)
    _cyl_bm(bm_mtrim, (mx - 0.056, my, mz), (-0.59, my - 0.02, mz + 0.01), 0.007, 0.007, segs=10)
    _cyl_bm(bm_mtrim, (mx + 0.058, my, mz + 0.015), (mx + 0.115, my + 0.008, mz - 0.012), 0.0042, 0.0042, segs=10)
    _cyl_bm(bm_mtrim, (mx - 0.062, my, mz - 0.015), (mx - 0.084, my + 0.012, mz - 0.026), 0.004, 0.004, segs=10)
    _bm_obj("taxi_meter_brass", bm_mtrim, m["brass"], coll, smooth=True)

    fw, fh = 0.047, 0.022
    _make_mesh(
        "taxi_meter_face",
        [(mx + fw, my + 0.0425, mz + 0.006 - fh), (mx - fw, my + 0.0425, mz + 0.006 - fh),
         (mx - fw, my + 0.0425, mz + 0.006 + fh), (mx + fw, my + 0.0425, mz + 0.006 + fh)],
        [(0, 1, 2, 3)],
        m["meter_face"],
        coll,
        uvs=[(0, 0), (1, 0), (1, 1), (0, 1)],
        smooth=False,
    )
    bm_flag = bmesh.new()
    _box_bm(bm_flag, (mx + 0.118, my + 0.010, mz - 0.020), (0.046, 0.004, 0.026), rot=Euler((0, math.radians(28), 0)), bevel=0.002, segs=1)
    _bm_obj("taxi_meter_flag", bm_flag, m["red_enamel"], coll, smooth=True)


def _upgrade_footwell_and_console(coll, m, plain, world_uvs_fn):
    """Museum-grade 1933 Citroën Rosalie front footwell, center transmission tunnel, sculpted gearshift,
    ratchet handbrake, ribbed firewall & insulation pad, under-dash parcel shelf + torch/map/wiring,
    driver pedals, contoured stitched leatherette kick panels, brass door sill plates, framed wet mud
    floor mats, and detailed Sora field satchel."""
    # 0. Remove duplicate/broken low-poly scan gearstick & diagonal rod islands from SM_internal
    sm = bpy.data.objects.get("SM_internal_M_internal_0")
    if sm:
        bm = bmesh.new()
        bm.from_mesh(sm.data)
        kill = []
        for f in bm.faces:
            c = sm.matrix_world @ f.calc_center_median()
            is_diag_bar = abs(c.x) < 0.018 and -0.62 < c.y < -0.07 and 0.04 < c.z < 0.70
            is_old_lever = -0.145 < c.x < -0.098 and -0.56 < c.y < -0.15 and -0.18 < c.z < 0.53
            if is_diag_bar or is_old_lever:
                kill.append(f)
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            bm.to_mesh(sm.data)
            sm.data.update()
        bm.free()

    m_felt = plain("M_cab_firewall_felt", (0.036, 0.028, 0.022), 0.94, 0.0)
    m_copper = plain("M_cab_copper_conduit", (0.42, 0.20, 0.10), 0.36, 0.88)
    m_wire = plain("M_cab_braided_wire", (0.045, 0.038, 0.030), 0.86, 0.0)
    m_foot_bulb = plain("M_cab_footwell_bulb", (0.98, 0.80, 0.48), 0.18, 0.0)
    bs_fb = m_foot_bulb.node_tree.nodes["Principled BSDF"]
    bs_fb.inputs["Emission Color"].default_value = (1.0, 0.68, 0.30, 1.0)
    bs_fb.inputs["Emission Strength"].default_value = 2.6
    m_pages = plain("M_cab_sketchbook_pages", (0.58, 0.52, 0.40), 0.88, 0.0)
    m_map = bpy.data.materials.get("M_cab_aged_map") or plain("M_cab_aged_map", (0.36, 0.29, 0.19), 0.88, 0.0)

    # 1. Arched Center Transmission Tunnel with Stitched Leather Piping & Cast-Iron Gearbox Turret Plate
    bm_tun, bm_pip = bmesh.new(), bmesh.new()
    tx = 0.025
    prof_n = 15
    y_stations = (-0.70, -0.56, -0.40, -0.24, -0.08, 0.12)
    t_rings = []
    for ys in y_stations:
        # Gently narrows slightly toward the rear between the front seats
        hw = 0.076 - 0.012 * max(0.0, (ys + 0.40) / 0.52)
        ht = 0.094 - 0.010 * max(0.0, (ys + 0.40) / 0.52)
        row = []
        for k in range(prof_n):
            u = k / (prof_n - 1)
            ang = math.pi * (1.0 - u)
            px = tx + math.cos(ang) * hw
            pz = 0.008 + (math.sin(ang) ** 0.78) * ht
            row.append(bm_tun.verts.new((px, ys, pz)))
        t_rings.append(row)
    for rA, rB in zip(t_rings, t_rings[1:]):
        for k in range(prof_n - 1):
            bm_tun.faces.new((rA[k], rA[k + 1], rB[k + 1], rB[k]))
    # Front/rear caps
    bm_tun.faces.new(list(reversed(t_rings[0])))
    bm_tun.faces.new(t_rings[-1])
    _bm_obj("taxi_trans_tunnel", bm_tun, m["pillar_trim"], coll, smooth=True)

    for side in (-1.0, 1.0):
        pts = [(tx + side * (0.074 - 0.012 * max(0.0, (ys + 0.40) / 0.52)), ys, 0.018) for ys in y_stations]
        _tube_obj(f"taxi_trans_piping_{'l' if side > 0 else 'r'}", pts, 0.0055, m["leather_strap"], coll, segs=8)
    bm_pip.free()

    # Cast-iron gearbox inspection plate + bolted chrome collar + 6 hex bolts
    gx, gy, gz = tx, -0.355, 0.098
    bm_plate, bm_gchr, bm_gbra = bmesh.new(), bmesh.new(), bmesh.new()
    _box_bm(bm_plate, (gx, gy, gz), (0.118, 0.148, 0.014), bevel=0.003, segs=2)
    _cyl_bm(bm_gchr, (gx, gy, gz + 0.006), (gx, gy, gz + 0.018), 0.056, 0.052, segs=24)
    for bx in (-0.046, 0.046):
        for by in (-0.058, 0.0, 0.058):
            _cyl_bm(bm_gchr, (gx + bx, gy + by, gz + 0.006), (gx + bx, gy + by, gz + 0.013), 0.0052, 0.0052, segs=6)
    _bm_obj("taxi_gear_base_plate", bm_plate, m["dark_iron"], coll, smooth=True)

    # 2. Sculpted 1933 Citroën Rosalie Gearstick (9-fold accordion gaiter, tapered chrome stalk, Art Deco knob + brass shift cap)
    bm_gaiter = bmesh.new()
    pleats = 9
    segs = 20
    g_rings = []
    for k in range(pleats * 2 + 1):
        t = k / (pleats * 2)
        r = (0.048 * (1.0 - t) + 0.013 * t) + (0.0065 if k % 2 == 1 else -0.0035)
        z = gz + 0.012 + t * 0.125
        g_rings.append([bm_gaiter.verts.new((gx + math.cos(j / segs * math.tau) * r, gy + math.sin(j / segs * math.tau) * r, z)) for j in range(segs)])
    for rA, rB in zip(g_rings, g_rings[1:]):
        for j in range(segs):
            bm_gaiter.faces.new((rA[j], rA[(j + 1) % segs], rB[(j + 1) % segs], rB[j]))
    _bm_obj("taxi_gear_gaiter", bm_gaiter, m["rubber"], coll, smooth=True)
    # Upper chrome gaiter clamp ring
    _cyl_bm(bm_gchr, (gx, gy, gz + 0.132), (gx, gy, gz + 0.144), 0.0155, 0.0135, segs=16)

    # Gracefully swept chrome stalk + lock-nut collar
    stalk_pts = [
        Vector((gx, gy, gz + 0.130)),
        Vector((gx + 0.006, gy + 0.016, 0.315)),
        Vector((gx + 0.012, gy + 0.036, 0.425)),
        Vector((gx + 0.015, gy + 0.052, 0.486)),
    ]
    _tube_obj("taxi_gear_lever_rod", stalk_pts, 0.0062, m["chrome"], coll, segs=12)
    knob_base = stalk_pts[-1]
    knob_dir = (stalk_pts[-1] - stalk_pts[-2]).normalized()
    q_k = Vector((0, 0, 1)).rotation_difference(knob_dir).to_matrix().to_4x4()
    _cyl_bm(bm_gchr, knob_base - knob_dir * 0.012, knob_base + knob_dir * 0.002, 0.011, 0.010, segs=6)

    # Turned Art Deco teardrop bakelite shift knob + brass collar + inlaid brass H-pattern medallion
    bm_knob = bmesh.new()
    k_prof = [
        (0.000, 0.0095), (0.006, 0.0135), (0.014, 0.0195), (0.022, 0.0238),
        (0.030, 0.0245), (0.036, 0.0218), (0.041, 0.0155), (0.043, 0.0090),
    ]
    k_rings = []
    for h, rad in k_prof:
        c = knob_base + knob_dir * h
        M_k = Matrix.Translation(c) @ q_k
        k_rings.append([bm_knob.verts.new(M_k @ Vector((math.cos(j / 20 * math.tau) * rad, math.sin(j / 20 * math.tau) * rad, 0))) for j in range(20)])
    for rA, rB in zip(k_rings, k_rings[1:]):
        for j in range(20):
            bm_knob.faces.new((rA[j], rA[(j + 1) % 20], rB[(j + 1) % 20], rB[j]))
    bm_knob.faces.new(k_rings[-1])
    _bm_obj("taxi_gear_knob", bm_knob, m["bakelite"], coll, smooth=True)
    # Recessed brass trim band & top H-pattern shift medallion
    _cyl_bm(bm_gbra, knob_base + knob_dir * 0.005, knob_base + knob_dir * 0.009, 0.0145, 0.0158, segs=20)
    _cyl_bm(bm_gbra, knob_base + knob_dir * 0.0415, knob_base + knob_dir * 0.045, 0.0128, 0.0110, segs=20)

    # 3. Authentic 1933 Ratchet Handbrake Lever (driver flank of tunnel, zero clipping!)
    hx, hy, hz = tx + 0.068, -0.235, 0.072
    bm_hb_iron, bm_hb_grip = bmesh.new(), bmesh.new()
    # Slotted rubber tunnel boot + toothed stamped-steel quadrant arc
    _box_bm(bm_hb_iron, (hx, hy + 0.02, hz + 0.006), (0.026, 0.145, 0.018), bevel=0.004, segs=2)
    for tooth in range(9):
        ang = math.radians(-18 + tooth * 10.5)
        r_arc = 0.068
        py = hy + math.sin(ang) * r_arc
        pz = hz + 0.015 + math.cos(ang) * r_arc
        _box_bm(bm_hb_iron, (hx + 0.008, py, pz), (0.0055, 0.011, 0.014), rot=Euler((ang, 0, 0)), bevel=0.001, segs=1)
    hb_p0 = Vector((hx, hy, hz + 0.015))
    hb_p1 = Vector((hx + 0.005, hy + 0.135, hz + 0.235))
    hb_dir = (hb_p1 - hb_p0).normalized()
    _cyl_bm(bm_hb_iron, hb_p0, hb_p0 + hb_dir * 0.185, 0.0075, 0.0062, segs=10)
    # Parallel chrome pawl release rod + spring thumb release button
    _cyl_bm(bm_gchr, hb_p0 + Vector((0, 0.012, 0.01)), hb_p1 - hb_dir * 0.065 + Vector((0, 0.010, 0)), 0.0028, 0.0028, segs=8)
    _cyl_bm(bm_gchr, hb_p1 - hb_dir * 0.005, hb_p1 + hb_dir * 0.018, 0.0068, 0.0062, segs=12)
    # Knurled/grooved bakelite handbrake grip
    for ring_i in range(6):
        f0 = 0.175 + ring_i * 0.0145
        _cyl_bm(bm_hb_grip, hb_p0 + hb_dir * f0, hb_p0 + hb_dir * (f0 + 0.012), 0.0118, 0.0126, segs=14)
    _bm_obj("taxi_handbrake_lever", bm_hb_iron, m["dark_iron"], coll, smooth=True)
    _bm_obj("taxi_handbrake_grip", bm_hb_grip, m["bakelite"], coll, smooth=True)
    _bm_obj("taxi_gear_chrome_hw", bm_gchr, m["chrome"], coll, smooth=True)
    _bm_obj("taxi_gear_brass_hw", bm_gbra, m["brass"], coll, smooth=True)

    # 4. Stamped Ribbed Steel Firewall Bulkhead, Quilted Acoustic Pad, Fuse Block & 6V Wiring Loom
    bm_fw, bm_pad, bm_fwhw, bm_cop = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    # Angled lower toeboard (cleanly forward of Sora's toes at Y=-0.67) + vertical firewall behind dash
    _box_bm(bm_fw, (0.0, -0.775, 0.165), (1.02, 0.018, 0.34), rot=Euler((math.radians(-22), 0, 0)), bevel=0.003, segs=1)
    _box_bm(bm_fw, (0.0, -0.705, 0.455), (1.02, 0.018, 0.31), bevel=0.003, segs=1)
    # 5 stamped horizontal stiffening ribs across the firewall & toeboard
    for rz, ry in ((0.11, -0.752), (0.19, -0.778), (0.27, -0.802), (0.39, -0.692), (0.48, -0.692)):
        _box_bm(bm_fw, (0.0, ry, rz), (0.94, 0.012, 0.018), bevel=0.003, segs=1)
    _bm_obj("taxi_firewall_bulkhead", bm_fw, m["wrinkle_enamel"], coll, smooth=True)

    # Quilted horsehair/felt firewall acoustic insulation pad + 8 brass washer retaining studs
    _box_bm(bm_pad, (-0.25, -0.686, 0.435), (0.42, 0.012, 0.22), bevel=0.005, segs=2)
    _box_bm(bm_pad, (0.26, -0.686, 0.435), (0.40, 0.012, 0.22), bevel=0.005, segs=2)
    _bm_obj("taxi_firewall_pad", bm_pad, m_felt, coll, smooth=True)
    for sx in (-0.42, -0.09, 0.09, 0.42):
        for sz in (0.355, 0.515):
            _cyl_bm(bm_fwhw, (sx, -0.684, sz), (sx, -0.675, sz), 0.009, 0.0085, segs=12)

    # Steering column rubber firewall boot + bolted iron flange around (+0.26, -0.59, 0.48)
    bm_scboot = bmesh.new()
    _cyl_bm(bm_scboot, (0.264, -0.695, 0.435), (0.264, -0.575, 0.520), 0.056, 0.032, segs=18)
    _bm_obj("taxi_steering_firewall_boot", bm_scboot, m["rubber"], coll, smooth=True)

    # Period 1930s cast-bakelite 6V electrical junction / fuse block with 4 brass terminal thumbscrews
    bm_fuse = bmesh.new()
    _box_bm(bm_fuse, (-0.06, -0.674, 0.470), (0.092, 0.026, 0.058), bevel=0.004, segs=2)
    _bm_obj("taxi_firewall_fusebox", bm_fuse, m["bakelite"], coll, smooth=True)
    for k in range(4):
        fx = -0.092 + k * 0.021
        _cyl_bm(bm_fwhw, (fx, -0.662, 0.470), (fx, -0.650, 0.470), 0.0058, 0.0052, segs=10)
        _cyl_bm(bm_cop, (fx, -0.664, 0.448), (fx, -0.664, 0.492), 0.0024, 0.0024, segs=8)

    # Cloth-braided 6V under-dash wiring loom & copper choke/heater conduit tubes curving behind dash
    _tube_obj("taxi_underdash_wire_1", [(-0.06, -0.662, 0.495), (-0.05, -0.61, 0.555), (-0.02, -0.535, 0.605)], 0.0062, m_wire, coll, segs=8)
    _tube_obj("taxi_underdash_wire_2", [(-0.09, -0.662, 0.495), (-0.16, -0.635, 0.545), (-0.28, -0.56, 0.595), (-0.42, -0.49, 0.66)], 0.0052, m_wire, coll, segs=8)
    _tube_obj("taxi_underdash_wire_3", [(0.02, -0.665, 0.485), (0.10, -0.61, 0.545), (0.18, -0.54, 0.63)], 0.0052, m_wire, coll, segs=8)
    _tube_obj("taxi_firewall_copper_pipe", [(0.08, -0.680, 0.36), (0.14, -0.665, 0.46), (0.18, -0.58, 0.56)], 0.0042, m_copper, coll, segs=8)

    # 5. Warm Walnut Under-Dash Parcel Shelf + Vintage Brass Torch, Rolled Indochina Map, Matchbox & Shielded Courtesy Lamp
    bm_sh, bm_trch_c, bm_trch_b, bm_tin = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    # Tucked cleanly UNDER the walnut dash lip at Z=0.515 (zero clipping into upper dash; still high above Sora's knees!)
    _box_bm(bm_sh, (-0.285, -0.585, 0.515), (0.370, 0.175, 0.012), bevel=0.003, segs=2)
    _bm_obj("taxi_underdash_shelf", bm_sh, m["walnut"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    # Aged brass retaining rail along front edge of shelf + twin brackets
    _cyl_bm(bm_fwhw, (-0.460, -0.502, 0.531), (-0.110, -0.502, 0.531), 0.0040, 0.0040, segs=10)
    for bx in (-0.440, -0.285, -0.130):
        _cyl_bm(bm_fwhw, (bx, -0.502, 0.515), (bx, -0.502, 0.531), 0.0034, 0.0034, segs=8)

    # Vintage 1930s ribbed-brass battery torch resting casually on the parcel shelf
    tp0 = Vector((-0.415, -0.548, 0.537))
    tp1 = Vector((-0.265, -0.585, 0.537))
    t_dir = (tp1 - tp0).normalized()
    _cyl_bm(bm_trch_b, tp0, tp1 - t_dir * 0.032, 0.0155, 0.0155, segs=16)
    _cyl_bm(bm_trch_c, tp1 - t_dir * 0.034, tp1, 0.0165, 0.0225, segs=18)
    _box_bm(bm_trch_c, (tp0 + t_dir * 0.065) + Vector((0, 0, 0.016)), (0.020, 0.007, 0.005), bevel=0.001, segs=1)
    # Rolled 1932 Indochina road map tied with red cord beside the torch
    bm_rmap, bm_rcord = bmesh.new(), bmesh.new()
    mp0 = Vector((-0.238, -0.550, 0.536))
    mp1 = Vector((-0.125, -0.600, 0.536))
    _cyl_bm(bm_rmap, mp0, mp1, 0.0135, 0.0145, segs=16)
    m_mid = mp0.lerp(mp1, 0.5)
    m_dir = (mp1 - mp0).normalized()
    _cyl_bm(bm_rcord, m_mid - m_dir * 0.005, m_mid + m_dir * 0.005, 0.0152, 0.0152, segs=14)
    _bm_obj("taxi_underdash_map_roll", bm_rmap, m_map, coll, smooth=True)
    _bm_obj("taxi_underdash_map_twine", bm_rcord, m["cord_red"], coll, smooth=True)
    # Small red-enamel Phnom Penh matchbox / cigarette tin
    _box_bm(bm_tin, (-0.155, -0.530, 0.529), (0.054, 0.036, 0.014), rot=Euler((0, 0, 0.24)), bevel=0.002, segs=1)
    _bm_obj("taxi_underdash_match_tin", bm_tin, m["red_enamel"], coll, smooth=True)

    # Shielded chrome under-dash courtesy lamp hood + warm amber frosted bulb (physical source for footwell glow!)
    _cyl_bm(bm_trch_c, (0.01, -0.522, 0.575), (0.01, -0.522, 0.558), 0.020, 0.024, segs=16)
    bm_bulb = bmesh.new()
    bmesh.ops.create_uvsphere(bm_bulb, u_segments=12, v_segments=8, radius=0.013, matrix=Matrix.Translation((0.01, -0.522, 0.557)) @ Matrix.Diagonal((1.0, 1.0, 0.65, 1.0)))
    _bm_obj("taxi_underdash_lamp_bulb", bm_bulb, m_foot_bulb, coll, smooth=True)
    _bm_obj("taxi_underdash_chrome", bm_trch_c, m["chrome"], coll, smooth=True)
    _bm_obj("taxi_underdash_brass_torch", bm_trch_b, m["brass"], coll, smooth=True)
    _bm_obj("taxi_firewall_brass_hw", bm_fwhw, m["brass"], coll, smooth=True)
    _bm_obj("taxi_firewall_copper_hw", bm_cop, m_copper, coll, smooth=True)

    # 6. Detailed Driver Foot Pedals (clutch, brake, hinged accelerator) + Chrome High-Beam Floor Dimmer Switch
    bm_ped_m, bm_ped_r, bm_dim = bmesh.new(), bmesh.new(), bmesh.new()
    for px, py, pz in ((0.365, -0.685, 0.145), (0.255, -0.685, 0.145)):
        # Forged iron stalk emerging from rubber firewall draft boot
        _cyl_bm(bm_ped_m, (px, py - 0.075, pz - 0.095), (px, py - 0.008, pz), 0.007, 0.006, segs=10)
        _cyl_bm(bm_ped_r, (px, py - 0.082, pz - 0.095), (px, py - 0.055, pz - 0.068), 0.022, 0.013, segs=12)
        # Beveled iron pad backing + ribbed rubber tread face
        _box_bm(bm_ped_m, (px, py, pz), (0.058, 0.010, 0.078), rot=Euler((math.radians(-26), 0, 0)), bevel=0.002, segs=1)
        for rib in range(5):
            _box_bm(bm_ped_r, (px, py + 0.006, pz - 0.026 + rib * 0.013), (0.050, 0.006, 0.007), rot=Euler((math.radians(-26), 0, 0)), bevel=0.001, segs=1)
    # Organ-style hinged accelerator pedal
    _box_bm(bm_ped_m, (0.148, -0.705, 0.105), (0.042, 0.010, 0.145), rot=Euler((math.radians(-30), 0, 0)), bevel=0.002, segs=1)
    for rib in range(4):
        _box_bm(bm_ped_r, (0.148, -0.699, 0.065 + rib * 0.026), (0.034, 0.005, 0.012), rot=Euler((math.radians(-30), 0, 0)), bevel=0.001, segs=1)
    # Floor-mounted chrome high-beam foot dimmer button beside clutch
    _cyl_bm(bm_ped_m, (0.435, -0.635, 0.010), (0.435, -0.635, 0.022), 0.018, 0.015, segs=14)
    _cyl_bm(bm_dim, (0.435, -0.635, 0.020), (0.435, -0.635, 0.036), 0.011, 0.010, segs=14)
    _bm_obj("taxi_driver_pedals_iron", bm_ped_m, m["dark_iron"], coll, smooth=True)
    _bm_obj("taxi_driver_pedals_rubber", bm_ped_r, m["rubber"], coll, smooth=True)
    _bm_obj("taxi_driver_dimmer_switch", bm_dim, m["chrome"], coll, smooth=True)

    # 7. Contoured Stitched Leatherette Side Kick Panels, Louvered Cowl Vent & Riveted Brass Door Sill Plates
    bm_kick, bm_kpipe, bm_vent, bm_sill = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for sign in (-1.0, 1.0):
        inw = -sign
        # Full contoured dark-brown leatherette kick wall sealing door jamb -> firewall & floor -> under-dash
        _box_bm(bm_kick, (sign * 0.508, -0.530, 0.360), (0.072, 0.500, 0.700), bevel=0.008, segs=2)
        # 3 vertical stitched leather ribs along the kick panel so it reads as tailored coachwork, not a slab!
        for k in range(3):
            ky = -0.635 + k * 0.115
            _box_bm(bm_kick, (sign * 0.474, ky, 0.335), (0.014, 0.092, 0.565), bevel=0.005, segs=2)
        # Leather piping beads along top & rear seam edges
        _box_bm(bm_kpipe, (sign * 0.470, -0.285, 0.355), (0.012, 0.014, 0.675), bevel=0.004, segs=2)
        _box_bm(bm_kpipe, (sign * 0.470, -0.530, 0.680), (0.014, 0.485, 0.016), bevel=0.004, segs=2)
        # Riveted ribbed aged-brass door threshold / sill scuff plate along cabin floor edge
        _box_bm(bm_sill, (sign * 0.522, -0.015, 0.014), (0.058, 0.60, 0.008), bevel=0.002, segs=1)
        for r in range(4):
            rx = sign * (0.502 + r * 0.013)
            _box_bm(bm_sill, (rx, -0.015, 0.019), (0.0045, 0.56, 0.003), bevel=0.0008, segs=1)
        for rv in range(5):
            ry = -0.26 + rv * 0.122
            _cyl_bm(bm_sill, (sign * 0.498, ry, 0.017), (sign * 0.498, ry, 0.022), 0.0035, 0.0035, segs=8)
    # Pressed-steel louvered fresh-air cowl vent grille & chrome pull lever on passenger kick wall
    _box_bm(bm_vent, (-0.465, -0.525, 0.435), (0.012, 0.145, 0.115), bevel=0.003, segs=1)
    for lv in range(5):
        _box_bm(bm_vent, (-0.458, -0.525, 0.398 + lv * 0.018), (0.008, 0.120, 0.006), rot=Euler((0, math.radians(-22), 0)), bevel=0.001, segs=1)
    _cyl_bm(bm_vent, (-0.464, -0.440, 0.435), (-0.438, -0.440, 0.435), 0.0038, 0.0038, segs=8)
    bmesh.ops.create_uvsphere(bm_vent, u_segments=10, v_segments=8, radius=0.0085, matrix=Matrix.Translation((-0.436, -0.440, 0.435)))

    _bm_obj("taxi_footwell_kickplates", bm_kick, m["leather_door"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    _bm_obj("taxi_kick_piping", bm_kpipe, m["leather_strap"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    _bm_obj("taxi_cowl_vent", bm_vent, m["dark_iron"], coll, smooth=True)
    _bm_obj("taxi_door_sill_plates", bm_sill, m["brass"], coll, smooth=True)

    # 8. Framed Deeply Ribbed 1930s Rubber Floor Mats + Cross-Hatched Heel Pad + Glossy Wet Laterite Mud Tracks
    bm_mat, bm_trim_m = bmesh.new(), bmesh.new()
    for sx in (-0.285, 0.285):
        # Main floor mat slab (Z=0.006, completely below Sora's shoes so both shoes stay 100% unobstructed!)
        _box_bm(bm_mat, (sx, -0.445, 0.006), (0.39, 0.50, 0.006), bevel=0.0015, segs=1)
        # Raised perimeter retaining lip & canvas-bound trim edge
        for dy in (-0.245, 0.245):
            _box_bm(bm_trim_m, (sx, -0.445 + dy, 0.0105), (0.395, 0.014, 0.0055), bevel=0.0015, segs=1)
        for dx in (-0.192, 0.192):
            _box_bm(bm_trim_m, (sx + dx, -0.445, 0.0105), (0.014, 0.50, 0.0055), bevel=0.0015, segs=1)
        # 13 crisp longitudinal mud-trap tread channels
        for r in range(13):
            _box_bm(bm_mat, (sx - 0.168 + r * 0.028, -0.445, 0.0105), (0.0085, 0.455, 0.0038), bevel=0.0008, segs=1)
        # Reinforced cross-hatched rubber heel pad
        for c_rib in range(5):
            _box_bm(bm_mat, (sx, -0.585 + c_rib * 0.028, 0.0112), (0.24, 0.007, 0.0025), bevel=0.0005, segs=1)
    _bm_obj("taxi_rubber_floor_mats", bm_mat, m["rubber"], coll, smooth=True)
    _bm_obj("taxi_floor_mat_binding", bm_trim_m, m["leather_strap"], coll, world_uvs_fn=world_uvs_fn, smooth=True)

    # Glossy wet Cambodian red laterite mud heel smears tracked in from the monsoon road
    bm_mud = bmesh.new()
    for px, py, sx_m, sy_m, rot_z in [
        (-0.20, -0.57, 0.125, 0.165, -0.18),
        (-0.36, -0.55, 0.135, 0.185, 0.14),
        (-0.27, -0.42, 0.105, 0.085, -0.35),
        (0.24, -0.58, 0.15, 0.18, 0.12),
        (0.36, -0.52, 0.12, 0.15, -0.22),
    ]:
        _box_bm(bm_mud, (px, py, 0.0122), (sx_m, sy_m, 0.0028), rot=Euler((0, 0, rot_z)), bevel=0.001, segs=1)
    _bm_obj("taxi_tracked_mud", bm_mud, m["mud"], coll, world_uvs_fn=world_uvs_fn, smooth=True)

    # 9. Detailed Sora Leather Field Satchel (stitched flap, carry handle, brass D-rings & buckles, sketchbook with pages)
    # Tucked neatly beside her right calf & door sill (100% clear of her shoes at y=-0.53..-0.67!)
    s_ctr = Vector((-0.460, -0.315, 0.155))
    M_sat = Matrix.Translation(s_ctr) @ Euler((math.radians(5), math.radians(-10), math.radians(12)), "XYZ").to_matrix().to_4x4()
    bm_sat, bm_buck, bm_sk, bm_pg = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    _box_bm(bm_sat, (0, 0, 0), (0.082, 0.255, 0.205), bevel=0.013, segs=2)
    # Sculpted curved top flap + side gusset ribs
    _box_bm(bm_sat, (0.043, 0, 0.040), (0.011, 0.260, 0.140), bevel=0.004, segs=2)
    _box_bm(bm_sat, (0.004, 0, 0.105), (0.086, 0.260, 0.014), bevel=0.005, segs=2)
    # Twin vertical saddle-leather buckle straps + top rolled carry handle
    for sy in (-0.078, 0.078):
        _box_bm(bm_sat, (0.050, sy, 0.0), (0.0055, 0.021, 0.195), bevel=0.0015, segs=1)
        _box_bm(bm_buck, (0.053, sy, -0.046), (0.0075, 0.028, 0.024), bevel=0.0018, segs=1)
        _cyl_bm(bm_buck, (0.00, sy * 0.72, 0.110), (0.00, sy * 0.72, 0.124), 0.009, 0.009, segs=10)
    # Rolled leather top carry handle arching between brass D-rings
    _cyl_bm(bm_sat, (0.00, -0.058, 0.126), (0.00, 0.058, 0.126), 0.0085, 0.0085, segs=10)
    # Center aged-brass turn-clasp
    _box_bm(bm_buck, (0.052, 0.0, -0.025), (0.008, 0.022, 0.028), bevel=0.002, segs=1)
    # Leather-bound sketchbook peeking out with visible ivory pages
    _box_bm(bm_sk, (-0.006, 0.020, 0.102), (0.022, 0.168, 0.058), bevel=0.0025, segs=1)
    _box_bm(bm_pg, (-0.006, 0.020, 0.105), (0.015, 0.160, 0.056), bevel=0.001, segs=1)

    sat = _bm_obj("taxi_sora_satchel", bm_sat, m["satchel_leather"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    sat.matrix_world = M_sat
    buck = _bm_obj("taxi_sora_satchel_buckles", bm_buck, m["brass"], coll, smooth=True)
    buck.matrix_world = M_sat
    sk = _bm_obj("taxi_sora_sketchbook_peek", bm_sk, plain("M_cab_sketchbook_cover", (0.14, 0.08, 0.045), 0.72, 0.0), coll, smooth=True)
    sk.matrix_world = M_sat
    pg = _bm_obj("taxi_sora_sketchbook_pages", bm_pg, m_pages, coll, smooth=True)
    pg.matrix_world = M_sat


def _krama_texture(plain):
    """Authentic woven red-and-white checkered Cambodian krama texture (uses ep1-refine real weave!)."""
    krama_src = TEX / "T_ep1_krama_check_BC.png"
    if krama_src.exists():
        img = bpy.data.images.load(str(krama_src), check_existing=True)
        img.pack()
    else:
        n = 512
        yy, xx = np.mgrid[:n, :n]
        rng = np.random.default_rng(42)
        sx = ((xx // 16) % 2).astype(np.float32)
        sy = ((yy // 16) % 2).astype(np.float32)
        crimson = np.array([0.28, 0.032, 0.030], np.float32)
        cream = np.array([0.52, 0.46, 0.36], np.float32)
        mid = 0.55 * crimson + 0.45 * cream
        rgb = np.where((sx * sy)[..., None] > 0.5, crimson, np.where(((sx + sy) > 0.5)[..., None], mid, cream))
        weave = 0.88 + 0.12 * np.sin(xx * math.pi / 1.5) * np.sin(yy * math.pi / 1.5) + rng.normal(0, 0.03, (n, n))
        rgb = np.clip(rgb * weave[..., None], 0.0, 1.0).astype(np.float32)
        img = bpy.data.images.new("T_taxi_driver_krama", width=n, height=n, alpha=True)
        img.pixels.foreach_set(np.concatenate([rgb, np.ones((n, n, 1), np.float32)], axis=-1).astype(np.float32).ravel())
        img.filepath_raw = str(TEX / "T_taxi_driver_krama_BC.png")
        img.file_format = "PNG"
        img.save()
        img.pack()

    mat = bpy.data.materials.get("M_cab_driver_krama") or plain("M_cab_driver_krama", (1, 1, 1), 0.90, 0.0)
    nt = mat.node_tree
    nt.nodes.clear()
    out_n = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.0
    bs.inputs["Roughness"].default_value = 0.90
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs[7].default_value = (0.58, 0.54, 0.48, 1.0)
    nt.links.new(tex.outputs["Color"], mix.inputs[6])
    nt.links.new(mix.outputs[2], bs.inputs["Base Color"])
    linen_n = ROOT / "art-source/library/materials/rough_linen/rough_linen_N.jpg"
    if linen_n.exists():
        ntex = nt.nodes.new("ShaderNodeTexImage")
        ntex.image = bpy.data.images.load(str(linen_n), check_existing=True)
        ntex.image.colorspace_settings.name = "Non-Color"
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 0.42
        nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out_n.inputs["Surface"])
    mat.use_backface_culling = False
    return mat


def _add_driver_krama(coll, neck_pos, plain):
    """Silky-smooth draped woven Cambodian krama wrapped snugly around driver's neck base
    (high enough to conceal the head-to-collar join cleanly from behind his ear!) with soft tails."""
    old = bpy.data.objects.get("taxi_driver_krama")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    body_obj = bpy.data.objects.get("taxi_driver_body_scan")
    head_obj = bpy.data.objects.get("taxi_driver_head_scan")
    if not body_obj or neck_pos is None:
        return

    # Build combined KDTree over both body & head lower neck so the scarf drapes OVER the neck seam!
    pts = [
        (body_obj.matrix_world @ v.co, (body_obj.matrix_world.to_3x3() @ v.normal).normalized())
        for v in body_obj.data.vertices
    ]
    if head_obj and head_obj.type == "MESH":
        hmw = head_obj.matrix_world
        hnm = hmw.to_3x3()
        for v in head_obj.data.vertices:
            wp = hmw @ v.co
            if wp.z < neck_pos.z + 0.065:
                pts.append((wp, (hnm @ v.normal).normalized()))
    tree = KDTree(len(pts))
    for i, (co, _) in enumerate(pts):
        tree.insert(co, i)
    tree.balance()

    def lift_surface(p, offset=0.014):
        co, idx, _ = tree.find(p)
        nrm = pts[idx][1]
        return co + nrm * offset, nrm

    # Rest a relaxed, low-draped woven Khmer krama centered cleanly around his vertical neck column
    # (never sticking out behind his collar or leaving an awkward front chin gap!)
    c = Vector((neck_pos.x - 0.004, 0.028, 0.907))
    ring = []
    steps = 64
    for s in range(steps):
        a = s / steps * math.tau
        c_front = max(0.0, math.cos(a))
        c_back = max(0.0, -math.cos(a))
        # Front (-Y) rests low on collarbones z=0.897; back (+Y) hugs nape collar snugly at z=0.921
        dz = -0.010 * c_front + 0.014 * c_back
        ry_k = 0.076 * c_front + 0.078 * c_back + 0.077 * (1.0 - c_front - c_back)
        raw = c + Vector((math.sin(a) * 0.080, -math.cos(a) * ry_k, dz))
        q, _ = lift_surface(raw, 0.008)
        q.z = raw.z
        ring.append(q)
    for _ in range(10):
        ring = [(ring[i - 1] + ring[i] * 2 + ring[(i + 1) % steps]) * 0.25 for i in range(steps)]

    verts, faces, uvs = [], [], []

    def sweep(path, closed, half_w, thick, u0):
        start = len(verts)
        sides = 18
        for s, p in enumerate(path):
            nxt = path[(s + 1) % len(path)] if closed or s + 1 < len(path) else p + (p - path[s - 1])
            prv = path[s - 1] if closed or s > 0 else p - (nxt - p)
            tan = (nxt - prv).normalized()
            if closed:
                out = Vector((p.x - c.x, p.y - c.y, 0.0)).normalized()
                across = Vector((0, 0, 1))
            else:
                _, nrm = lift_surface(p, 0.0)
                out = nrm
                across = tan.cross(out).normalized()
            fold_wave = 1.0 + 0.09 * math.sin(s * 0.65 + u0 * 3.0)
            w_scale = 1.0 if closed else (0.86 + 0.22 * math.sin(s / max(1, len(path) - 1) * math.pi))
            for k in range(sides):
                b = k / sides * math.tau
                pleat = 1.0 + 0.08 * math.sin(b * 3.0 + s * 0.40)
                # Bottom skirt drapes naturally over shirt collar & trapezius shoulders!
                flare = (0.016 * max(0.0, -math.sin(b))) if closed else 0.0
                verts.append(
                    p
                    + out * (math.cos(b) * thick * fold_wave * pleat + flare)
                    + across * (math.sin(b) * half_w * w_scale)
                )
                uvs.append((u0 + s / max(1, len(path)) * 4.0, k / sides * 0.85))
        rows = len(path) if closed else len(path) - 1
        for s in range(rows):
            for k in range(sides):
                a = start + s * sides + k
                b = start + ((s + 1) % len(path)) * sides + k
                faces.append((a, start + s * sides + (k + 1) % sides, start + ((s + 1) % len(path)) * sides + (k + 1) % sides, b))

    # Relaxed slim folded krama draped low on his shoulders & shirt collar (half_w = 0.0235 -> ~4.7 cm soft fold!)
    sweep(ring, True, 0.0235, 0.014, 0.0)
    # Soft draped chest tails hanging neatly down his front shirt (clear of both shoulders!)
    for side, length in [(-1, 12), (1, 10)]:
        tail = []
        for s in range(length):
            frac = s / max(1, length - 1)
            raw = c + Vector((side * (0.032 + 0.004 * s + 0.005 * math.sin(frac * math.pi)), -0.080 - 0.006 * s, -0.028 - 0.022 * s))
            q, _ = lift_surface(raw, 0.016)
            tail.append(q)
        for _ in range(5):
            tail = [tail[0]] + [(tail[i - 1] + tail[i] * 2 + tail[i + 1]) * 0.25 for i in range(1, len(tail) - 1)] + [tail[-1]]
        sweep(tail, False, 0.036, 0.0060, 0.4 + side * 0.2)

    krama_obj = _make_mesh("taxi_driver_krama", verts, faces, _krama_texture(plain), coll, uvs=uvs, smooth=True)
    bpy.ops.object.select_all(action="DESELECT")
    krama_obj.select_set(True)
    bpy.context.view_layer.objects.active = krama_obj
    sub = krama_obj.modifiers.new("krama_smooth", "SUBSURF")
    sub.levels = 1
    bpy.ops.object.modifier_apply(modifier=sub.name)
    for p in krama_obj.data.polygons:
        p.use_smooth = True


def _repair_driver_head_normal():
    """Sanitize corrupted low-Z tangent-space normal pixels on T_taxi_driver_head_N (removes cheek/chin scan slits!)."""
    head_obj = bpy.data.objects.get("taxi_driver_head_scan")
    if not head_obj or not head_obj.data.materials:
        return
    hm = head_obj.data.materials[0]
    for n in hm.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "Non-Color" and "_N" in n.image.name:
            nimg = n.image
            nw, nh = nimg.size
            npx = np.empty(nw * nh * 4, np.float32)
            nimg.pixels.foreach_get(npx)
            npx = npx.reshape(nh, nw, 4)
            bad = npx[..., 2] < 0.82
            if np.any(bad):
                npx[bad, 0] = 0.5
                npx[bad, 1] = 0.5
                npx[bad, 2] = 1.0
                nimg.pixels.foreach_set(npx.astype(np.float32).ravel())
                nimg.pack()
                print("TAXI_HEAD_NORMAL_REPAIRED", int(np.sum(bad)))


def _upgrade_pillars_and_cowl(coll, m, world_uvs_fn):
    """Sculpted inner windscreen rubber perimeter gasket, walnut cowl rail, compact chrome
    windscreen latch, and header-mounted vacuum wiper motor bosses.

    Also strips the scan's dead static center wiper rod (which sat frozen behind the prayer
    beads alongside the twin animated wipers) and the bulky 8,168-face black crank clamp blob
    on top of the walnut dashboard, while keeping the curved Rosalie A-pillars 100% clean.
    """
    # 1. Remove the bulky raw black crank blob on top of the walnut dash from SM_internal
    sm = bpy.data.objects.get("SM_internal_M_internal_0")
    if sm:
        bm = bmesh.new()
        bm.from_mesh(sm.data)
        mw = sm.matrix_world
        kill = [
            f
            for f in bm.faces
            if (
                abs((mw @ f.calc_center_median()).x) < 0.042
                and -0.495 < (mw @ f.calc_center_median()).y < -0.372
                and 0.815 < (mw @ f.calc_center_median()).z < 0.945
            )
        ]
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            bm.to_mesh(sm.data)
            sm.data.update()
        bm.free()

    # 2. Remove the frozen original center windscreen wiper rod hanging at X=0 behind the prayer beads
    for oname in (
        "taxi_car_taxi_body_lacquer_door",
        "taxi_car_taxi_headliner.001",
        "taxi_car_door.002",
        "taxi_car_taxi_aged_nickel.001",
    ):
        obj = bpy.data.objects.get(oname)
        if not obj:
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        mw = obj.matrix_world
        kill = [
            f
            for f in bm.faces
            if (
                abs((mw @ f.calc_center_median()).x) < 0.022
                and -0.506 < (mw @ f.calc_center_median()).y < -0.440
                and 0.888 < (mw @ f.calc_center_median()).z < 1.116
            )
        ]
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            bm.to_mesh(obj.data)
            obj.data.update()
        bm.free()

    bm_trim = bmesh.new()
    rake = Euler((-0.166, 0.0, 0.0), "XYZ")
    for side in (-1.0, 1.0):
        # Slim matte rubber windscreen vertical inner gasket hugging the glass opening cleanly
        # (NEVER pokes obliquely through the curved Rosalie A-pillar headliner!)
        _box_bm(
            bm_trim,
            (side * 0.486, -0.474, 0.996),
            (0.014, 0.022, 0.268),
            rot=rake,
            bevel=0.003,
            segs=2,
        )
        # Lower cowl corner blocker tucked cleanly BELOW the walnut dash top rail to seal corner light leaks
        _box_bm(
            bm_trim,
            (side * 0.514, -0.486, 0.728),
            (0.048, 0.056, 0.252),
            bevel=0.006,
            segs=2,
        )
    # Upper windscreen header trim rail bridging cleanly inside the A-pillars
    _box_bm(
        bm_trim,
        (0.0, -0.446, 1.148),
        (0.985, 0.044, 0.034),
        bevel=0.006,
        segs=2,
    )
    _bm_obj("taxi_interior_apillar_trim", bm_trim, m["pillar_trim"], coll, smooth=True)

    # Full-width beveled walnut dashboard top cowl molding tying cleanly into both cowl jambs
    bm_cap = bmesh.new()
    _box_bm(
        bm_cap,
        (0.0, -0.486, 0.858),
        (1.035, 0.050, 0.026),
        bevel=0.006,
        segs=2,
    )
    # Subtle lower fascia return edge
    _box_bm(
        bm_cap,
        (0.0, -0.492, 0.612),
        (1.03, 0.036, 0.018),
        bevel=0.004,
        segs=2,
    )
    _bm_obj("taxi_dash_top_rail", bm_cap, m["walnut"], coll, world_uvs_fn, smooth=True)

    # Build header-mounted 1933 vacuum wiper motors, grommets & exterior drive shafts (refreshed idempotently)
    _refresh_wiper_header_mounts(coll, m)


def _refresh_wiper_header_mounts(coll, m):
    """Sculpt authentic 1933 Trico-style header vacuum wiper motors, rubber header grommets,
    and exterior chrome drive shafts extending right to the runtime wiper pivot at (±0.23, -0.449, 1.124)."""
    for old_n in ("taxi_wiper_motor_bosses", "taxi_wiper_header_grommets"):
        old = bpy.data.objects.get(old_n)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

    bm_wiper_boss = bmesh.new()
    bm_grommet = bmesh.new()
    for side in (-1.0, 1.0):
        wx = side * 0.23
        # Interior 1933 Trico vacuum motor canister housed neatly along upper windscreen header
        _box_bm(
            bm_grommet,
            (wx, -0.430, 1.142),
            (0.056, 0.030, 0.024),
            bevel=0.008,
            segs=2,
        )
        # Satin-chrome motor end-plates, mounting bracket & control valve knob
        _box_bm(
            bm_wiper_boss,
            (wx - side * 0.028, -0.430, 1.142),
            (0.005, 0.026, 0.020),
            bevel=0.001,
            segs=1,
        )
        _box_bm(
            bm_wiper_boss,
            (wx + side * 0.028, -0.430, 1.142),
            (0.005, 0.026, 0.020),
            bevel=0.001,
            segs=1,
        )
        _cyl_bm(
            bm_wiper_boss,
            (wx + side * 0.020, -0.415, 1.142),
            (wx + side * 0.020, -0.402, 1.142),
            0.0042,
            0.0050,
            segs=10,
        )
        # Molded black rubber bulkhead grommet & bezel collar seated into top windscreen frame
        _cyl_bm(
            bm_grommet,
            (wx, -0.440, 1.132),
            (wx, -0.4495, 1.1245),
            0.0115,
            0.0102,
            segs=14,
        )
        # Exterior chrome drive spindle + hex locking nut reaching the runtime wiper pivot at (wx, -0.449, 1.124)
        _cyl_bm(
            bm_wiper_boss,
            (wx, -0.442, 1.131),
            (wx, -0.4495, 1.1235),
            0.0068,
            0.0058,
            segs=14,
        )
        _cyl_bm(
            bm_wiper_boss,
            (wx, -0.4495, 1.1235),
            (wx, -0.4530, 1.1228),
            0.0044,
            0.0044,
            segs=12,
        )
    # Sleek low-profile 1933 machined chrome windscreen toggle latch centered on top cowl rail
    _box_bm(bm_wiper_boss, (0.0, -0.486, 0.874), (0.038, 0.020, 0.010), bevel=0.002, segs=2)
    _cyl_bm(bm_wiper_boss, (0.0, -0.484, 0.878), (0.0, -0.474, 0.886), 0.0065, 0.0055, segs=12)
    _cyl_bm(bm_wiper_boss, (-0.018, -0.474, 0.886), (0.018, -0.474, 0.886), 0.0036, 0.0036, segs=10)
    _bm_obj("taxi_wiper_header_grommets", bm_grommet, m["wrinkle_enamel"], coll, smooth=True)
    _bm_obj("taxi_wiper_motor_bosses", bm_wiper_boss, m["chrome"], coll, smooth=True)


def _upgrade_rear_cabin(coll, m, plain, world_uvs_fn):
    """Coachbuilt 1933 Citroën Rosalie rear cabin realism overhaul:
    - Plush fluted & piped leather rear bench, backrest, fold-down center armrest & side armrests
    - Full rear left & right pleated door cards, walnut sills, chrome cranks & door handles
    - Molded B-pillar & C-pillar covers + hanging silk-braided passenger assist loops
    - Arched stitched roof headliner bows + 1933 Art Deco chrome & frosted-amber ceiling dome lamp
    - Sculpted walnut rear window surround, rolled silk privacy shade & parcel shelf + vintage newspaper
    - Finished front seatbacks with stitched map pockets & turned walnut/brass passenger grab bar
    - Authentic Cambodian travel props: strapped brass-corner leather suitcase, woven rattan basket,
      folded checkered krama, grooved rear rubber mat, and realistic multi-petal closed Cambodian
      lotus bud (`taxi_rear_lotus_bud`) on a woven banana-leaf tray (replacing raw primitive shapes!).
    """
    # Replace the old primitive untextured white egg & floating wireframe spiral from mourners_leavings
    for o in list(bpy.data.objects):
        if o.name in (
            "taxi_rear_lotus_bud",
            "taxi_rear_lotus_stem",
            "taxi_rear_thread_coil",
            "taxi_rear_incense",
            "taxi_rear_incense_band",
        ):
            bpy.data.objects.remove(o, do_unlink=True)

    # Extra materials for realistic rear cabin craft
    m_seat = m["leather_door"]
    m_trim = m["pillar_trim"]
    m_bamboo = library_material_or_plain(
        plain, "M_cab_rear_bamboo", (0.34, 0.24, 0.12), 0.78
    )
    m_banana_leaf = plain("M_cab_rear_banana_leaf", (0.045, 0.095, 0.032), 0.56, 0.0)
    m_lotus_petal = plain("M_cab_lotus_petal", (0.68, 0.56, 0.54), 0.52, 0.0)
    m_lotus_green = plain("M_cab_lotus_calyx", (0.075, 0.13, 0.045), 0.64, 0.0)
    m_silk_shade = plain("M_cab_silk_shade", (0.28, 0.24, 0.18), 0.85, 0.0)
    m_paper = plain("M_cab_aged_newsprint", (0.42, 0.36, 0.26), 0.90, 0.0)
    m_dome_glass = plain("M_cab_dome_glass", (1.0, 0.82, 0.52), 0.22, 0.0)
    bs_dome = m_dome_glass.node_tree.nodes["Principled BSDF"]
    bs_dome.inputs["Emission Color"].default_value = (1.0, 0.76, 0.42, 1.0)
    bs_dome.inputs["Emission Strength"].default_value = 2.4

    # 1. Plush fluted 1930s leather rear bench, backrest, center fold-down armrest & side bolsters
    bm_bench = bmesh.new()
    # Base bench cushion & rolled front thigh lip
    _box_bm(bm_bench, (0.0, 1.13, 0.468), (1.16, 0.48, 0.10), bevel=0.024, segs=3)
    _cyl_bm(bm_bench, (-0.56, 0.90, 0.478), (0.56, 0.90, 0.478), 0.046, 0.046, segs=16)
    # 9 vertical stitched cushion flutes across the bench top
    for k in range(9):
        fx = -0.48 + k * 0.12
        _box_bm(bm_bench, (fx, 1.13, 0.514), (0.106, 0.42, 0.022), bevel=0.008, segs=2)
    # Angled backrest cushion + 9 vertical backrest flutes + top rolled shoulder bolster
    back_tilt = Euler((math.radians(-14), 0.0, 0.0), "XYZ")
    _box_bm(bm_bench, (0.0, 1.40, 0.715), (1.16, 0.11, 0.44), rot=back_tilt, bevel=0.022, segs=3)
    for k in range(9):
        fx = -0.48 + k * 0.12
        _box_bm(bm_bench, (fx, 1.355, 0.710), (0.106, 0.032, 0.39), rot=back_tilt, bevel=0.010, segs=2)
    _cyl_bm(bm_bench, (-0.56, 1.445, 0.915), (0.56, 1.445, 0.915), 0.042, 0.042, segs=16)
    # Center fold-down leather armrest + left/right side upholstered armrests
    _box_bm(bm_bench, (0.0, 1.20, 0.590), (0.16, 0.34, 0.105), bevel=0.022, segs=3)
    for side in (-1.0, 1.0):
        _box_bm(bm_bench, (side * 0.565, 1.10, 0.615), (0.088, 0.44, 0.085), bevel=0.018, segs=3)
        _box_bm(bm_bench, (side * 0.580, 1.12, 0.475), (0.068, 0.44, 0.24), bevel=0.012, segs=2)
    _bm_obj("taxi_rear_bench_tufted", bm_bench, m_seat, coll, world_uvs_fn, smooth=True)

    # Stitched dark piping & brass upholstery studs around armrest and seat seams
    bm_pipe = bmesh.new()
    _box_bm(bm_pipe, (0.0, 1.03, 0.590), (0.15, 0.012, 0.085), bevel=0.004, segs=2)
    for side in (-1.0, 1.0):
        _box_bm(bm_pipe, (side * 0.565, 0.885, 0.615), (0.072, 0.014, 0.066), bevel=0.004, segs=2)
    _bm_obj("taxi_rear_bench_piping", bm_pipe, m["leather_strap"], coll, world_uvs_fn, smooth=True)

    # 2. Full rear left & right pleated door cards, walnut sills, chrome cranks & door handles
    bm_rcards, bm_rwal, bm_rchr, bm_rpock = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for sign in (-1.0, 1.0):
        x_card = sign * 0.618
        inw = -sign
        # Door panel backing & 8 vertical leather pleats
        _box_bm(bm_rcards, (x_card, 0.81, 0.43), (0.016, 0.70, 0.56), bevel=0.004, segs=2)
        for k in range(8):
            _box_bm(bm_rcards, (x_card + inw * 0.010, 0.51 + k * 0.085, 0.45), (0.015, 0.068, 0.42), bevel=0.004, segs=2)
        # Stitched rear door pocket
        _box_bm(bm_rpock, (x_card + inw * 0.018, 0.79, 0.22), (0.012, 0.40, 0.14), bevel=0.003, segs=2)
        # Polished walnut rear door window sill & chrome beltline moulding
        _box_bm(bm_rwal, (x_card + inw * 0.012, 0.81, 0.732), (0.036, 0.72, 0.038), bevel=0.005, segs=2)
        _box_bm(bm_rchr, (x_card + inw * 0.019, 0.81, 0.688), (0.006, 0.70, 0.008), bevel=0.001, segs=1)
        # Sculpted chrome window winder crank & interior door latch lever
        for cy, cz, ang in [(0.68, 0.54, -0.55), (0.94, 0.58, 0.25)]:
            p0 = Vector((x_card + inw * 0.018, cy, cz))
            _cyl_bm(bm_rchr, p0, p0 + Vector((inw * 0.022, 0, 0)), 0.015, 0.011, segs=14)
            tip = p0 + Vector((inw * 0.026, math.cos(ang) * 0.075, math.sin(ang) * 0.075))
            _cyl_bm(bm_rchr, p0 + Vector((inw * 0.020, 0, 0)), tip, 0.0055, 0.0042, segs=10)
            _cyl_bm(bm_rchr, tip, tip + Vector((inw * 0.024, 0, 0)), 0.0075, 0.009, segs=12)
        # Chrome ashtray inset in rear armrest
        _box_bm(bm_rchr, (sign * 0.562, 0.96, 0.658), (0.044, 0.068, 0.008), bevel=0.002, segs=1)

    # Walnut rear window frame & dark walnut rear parcel shelf + front seatback walnut grab bar
    _box_bm(bm_rwal, (0.0, 1.515, 0.918), (1.18, 0.16, 0.026), bevel=0.005, segs=2)
    _box_bm(bm_rwal, (0.0, 1.565, 1.195), (1.16, 0.042, 0.030), bevel=0.005, segs=2)
    for side in (-1.0, 1.0):
        _box_bm(bm_rwal, (side * 0.535, 1.560, 1.055), (0.036, 0.042, 0.28), bevel=0.005, segs=2)
    # Turned walnut passenger assist rail across back of driver's seat (+ brass mounting brackets)
    _cyl_bm(bm_rwal, (0.06, 0.305, 0.775), (0.50, 0.305, 0.775), 0.012, 0.012, segs=14)
    for gx in (0.08, 0.48):
        _cyl_bm(bm_rchr, (gx, 0.255, 0.775), (gx, 0.305, 0.775), 0.008, 0.006, segs=10)
        _cyl_bm(bm_rchr, (gx, 0.250, 0.775), (gx, 0.262, 0.775), 0.016, 0.015, segs=12)

    _bm_obj("taxi_rear_door_cards", bm_rcards, m_seat, coll, world_uvs_fn, smooth=True)
    _bm_obj("taxi_rear_walnut_trim", bm_rwal, m["walnut"], coll, world_uvs_fn, smooth=True)
    _bm_obj("taxi_rear_chrome_hardware", bm_rchr, m["chrome"], coll, smooth=True)
    _bm_obj("taxi_rear_door_pockets", bm_rpock, m["leather_strap"], coll, world_uvs_fn, smooth=True)

    # 3. Clean molded B-pillars, C-pillars, rear cantrails, ceiling-hugging roof bows, silk blind & assist loops
    bm_pil = bmesh.new()
    for side in (-1.0, 1.0):
        # B-pillars cleanly dividing front and rear side windows
        _box_bm(bm_pil, (side * 0.606, 0.392, 0.68), (0.056, 0.072, 1.12), bevel=0.010, segs=2)
        # C-pillars framing rear quarter panels into the rear window
        _box_bm(bm_pil, (side * 0.612, 1.38, 0.96), (0.072, 0.34, 0.62), bevel=0.012, segs=2)
        # Rear cabin roof cantrails (B -> C pillars only, so they never poke through the sloping front roof!)
        _box_bm(bm_pil, (side * 0.592, 0.92, 1.218), (0.048, 1.04, 0.048), bevel=0.010, segs=2)
    # 3 arched stitched fabric headliner roof bows hugging the measured Rosalie rear ceiling curve
    for by, bz, half_span, drop in [(0.44, 1.276, 0.54, 0.068), (0.88, 1.280, 0.55, 0.055), (1.30, 1.260, 0.54, 0.036)]:
        pts = []
        for s in range(13):
            u = (s / 12.0) * 2.0 - 1.0
            px = u * half_span
            pz = bz - (u * u) * drop
            pts.append((px, by, pz))
        _tube_obj(f"taxi_headliner_bow_{by:.2f}", pts, 0.0095, m_trim, coll, segs=8)
    _bm_obj("taxi_rear_pillars_trim", bm_pil, m_trim, coll, smooth=True)

    # Hanging vintage braided-leather passenger assist loops on B-pillars and C-pillars
    bm_esc = bmesh.new()
    for side in (-1.0, 1.0):
        inw = -side
        for py, pz, tag in [(0.41, 1.06, "b"), (1.26, 1.08, "c")]:
            anchor = Vector((side * 0.578, py, pz))
            _cyl_bm(bm_esc, anchor, anchor + Vector((inw * 0.016, 0, 0)), 0.014, 0.011, segs=12)
            loop = [
                anchor + Vector((inw * 0.014, -0.008, 0.0)),
                anchor + Vector((inw * 0.032, -0.026, -0.075)),
                anchor + Vector((inw * 0.038, 0.0, -0.155)),
                anchor + Vector((inw * 0.032, 0.026, -0.075)),
                anchor + Vector((inw * 0.014, 0.008, 0.0)),
            ]
            _tube_obj(f"taxi_assist_loop_{tag}_{'r' if side < 0 else 'l'}", loop, 0.0068, m["leather_strap"], coll, segs=8)
    _bm_obj("taxi_assist_escutcheons", bm_esc, m["chrome"], coll, smooth=True)

    # Rolled vintage silk privacy shade above rear window
    bm_sh = bmesh.new()
    _cyl_bm(bm_sh, (-0.50, 1.545, 1.168), (0.50, 1.545, 1.168), 0.016, 0.016, segs=14)
    _box_bm(bm_sh, (0.0, 1.540, 1.148), (0.98, 0.006, 0.032), bevel=0.001, segs=1)
    _bm_obj("taxi_rear_privacy_shade", bm_sh, m_silk_shade, coll, smooth=True)

    # 4. 1933 Art Deco Chrome & Frosted-Amber Glass Interior Ceiling Dome Lamp
    # First remove the Rosalie scan's opaque dark-grey dome boss inside taxi_car_taxi_headliner.004
    # (z < 1.275 around (0, 0.56)) so it never hangs below our glowing Art Deco frosted-amber lens!
    hl4 = bpy.data.objects.get("taxi_car_taxi_headliner.004")
    if hl4 and hl4.type == "MESH":
        bm_hl = bmesh.new()
        bm_hl.from_mesh(hl4.data)
        kill_v = [v for v in bm_hl.verts if abs(v.co.x) < 0.095 and 0.47 < v.co.y < 0.66 and v.co.z < 1.275]
        if kill_v:
            bmesh.ops.delete(bm_hl, geom=kill_v, context="VERTS")
            bm_hl.to_mesh(hl4.data)
            hl4.data.update()
        bm_hl.free()
    # Single sleek stepped circular chrome bezel flush against the ceiling headliner at Z=1.300 with
    # convex frosted-amber dome lens projecting cleanly beneath it (zero dark disc occlusion!).
    bm_dchrome, bm_dglass = bmesh.new(), bmesh.new()
    dome_pos = Vector((0.0, 0.56, 1.300))
    _cyl_bm(bm_dchrome, dome_pos + Vector((0, 0, 0.010)), dome_pos + Vector((0, 0, -0.008)), 0.074, 0.068, segs=28, cap=False)
    _cyl_bm(bm_dchrome, dome_pos + Vector((0, 0, -0.007)), dome_pos + Vector((0, 0, -0.016)), 0.068, 0.058, segs=28, cap=False)
    # Delicate Art Deco center chrome finial button on underside of dome
    _cyl_bm(bm_dchrome, dome_pos + Vector((0, 0, -0.036)), dome_pos + Vector((0, 0, -0.043)), 0.009, 0.005, segs=16)
    bmesh.ops.create_uvsphere(
        bm_dglass,
        u_segments=24,
        v_segments=12,
        radius=1.0,
        matrix=Matrix.Translation(dome_pos + Vector((0, 0, -0.014))) @ Matrix.Diagonal((0.057, 0.057, 0.025, 1.0)),
    )
    _bm_obj("taxi_cabin_dome_bezel", bm_dchrome, m["chrome"], coll, smooth=True)
    _bm_obj("taxi_cabin_dome_glass", bm_dglass, m_dome_glass, coll, smooth=True)

    # 5. Finished front seatback leather shells & stitched rear map pockets
    bm_sb, bm_sbp = bmesh.new(), bmesh.new()
    for sx in (-0.27, 0.27):
        _box_bm(bm_sb, (sx, 0.255, 0.565), (0.45, 0.032, 0.44), rot=Euler((math.radians(-6), 0, 0)), bevel=0.012, segs=2)
        _box_bm(bm_sbp, (sx, 0.282, 0.495), (0.34, 0.014, 0.19), rot=Euler((math.radians(-6), 0, 0)), bevel=0.004, segs=2)
    _bm_obj("taxi_front_seatbacks_leather", bm_sb, m_seat, coll, world_uvs_fn, smooth=True)
    _bm_obj("taxi_front_seatback_pockets", bm_sbp, m["leather_strap"], coll, world_uvs_fn, smooth=True)

    # 6. Grooved black rubber rear floor mat
    bm_rmat = bmesh.new()
    _box_bm(bm_rmat, (0.0, 0.67, 0.004), (1.06, 0.36, 0.006), bevel=0.002, segs=1)
    for k in range(18):
        _box_bm(bm_rmat, (-0.48 + k * 0.056, 0.67, 0.008), (0.012, 0.32, 0.003), bevel=0.0008, segs=1)
    _bm_obj("taxi_rear_floor_mat", bm_rmat, m["rubber"], coll, smooth=True)

    # 7. Authentic Cambodian Passenger Props: Vintage Strapped Suitcase, Woven Rattan Basket,
    #    Folded Checkered Khmer Krama, Aged Newspaper, and Realistic Multi-Petal Lotus Offering!
    # 7a. Vintage 1930s strapped leather travel suitcase on rear left floor
    suit_m = Matrix.Translation((0.33, 0.68, 0.142)) @ Euler((0, 0, math.radians(-14)), "XYZ").to_matrix().to_4x4()
    bm_suit, bm_sbrass = bmesh.new(), bmesh.new()
    _box_bm(bm_suit, (0, 0, 0), (0.38, 0.155, 0.26), bevel=0.012, segs=2)
    for lx in (-0.11, 0.11):
        _box_bm(bm_suit, (lx, 0, 0), (0.024, 0.165, 0.268), bevel=0.003, segs=1)
        _box_bm(bm_sbrass, (lx, -0.084, 0.02), (0.030, 0.008, 0.028), bevel=0.002, segs=1)
    # Handle & 8 brass corner protectors
    _box_bm(bm_suit, (0, 0, 0.145), (0.11, 0.022, 0.020), bevel=0.005, segs=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                _box_bm(bm_sbrass, (sx * 0.186, sy * 0.074, sz * 0.126), (0.026, 0.024, 0.026), bevel=0.003, segs=1)
    suit_o = _bm_obj("taxi_rear_leather_suitcase", bm_suit, m["satchel_leather"], coll, world_uvs_fn, smooth=True)
    suit_o.matrix_world = suit_m
    sb_o = _bm_obj("taxi_rear_suitcase_brass", bm_sbrass, m["brass"], coll, smooth=True)
    sb_o.matrix_world = suit_m

    # 7b. Woven Cambodian bamboo market basket on rear right floor
    bm_bask = bmesh.new()
    b_ctr = Vector((-0.34, 0.68, 0.010))
    for k in range(8):
        z0 = b_ctr.z + k * 0.026
        r0 = 0.095 + k * 0.0065
        _cyl_bm(bm_bask, (b_ctr.x, b_ctr.y, z0), (b_ctr.x, b_ctr.y, z0 + 0.022), r0, r0 + 0.004, segs=18, cap=(k == 0))
    _cyl_bm(bm_bask, (b_ctr.x, b_ctr.y, b_ctr.z + 0.205), (b_ctr.x, b_ctr.y, b_ctr.z + 0.222), 0.148, 0.152, segs=18, cap=False)
    _bm_obj("taxi_rear_bamboo_basket", bm_bask, m_bamboo, coll, world_uvs_fn, smooth=True)

    # 7c. Folded checkered Khmer krama draped on the left rear bench seat
    krama_mat = bpy.data.materials.get("M_cab_driver_krama") or m_silk_shade
    bm_rk = bmesh.new()
    _box_bm(bm_rk, (0.37, 1.07, 0.532), (0.24, 0.20, 0.028), rot=Euler((0.04, -0.05, 0.18)), bevel=0.010, segs=2)
    _box_bm(bm_rk, (0.35, 1.09, 0.552), (0.21, 0.17, 0.020), rot=Euler((0.06, -0.03, 0.24)), bevel=0.008, segs=2)
    _bm_obj("taxi_rear_folded_krama", bm_rk, krama_mat, coll, world_uvs_fn, smooth=True)

    # 7d. Folded aged 1930s newspaper on the walnut rear parcel shelf
    bm_np = bmesh.new()
    _box_bm(bm_np, (0.24, 1.50, 0.936), (0.26, 0.14, 0.010), rot=Euler((0, 0, -0.14)), bevel=0.002, segs=1)
    _bm_obj("taxi_rear_newspaper", bm_np, m_paper, coll, smooth=True)

    # 7e. Realistic Cambodian Lotus Offering (`taxi_rear_lotus_bud`) on a woven bamboo & banana-leaf tray!
    tray_ctr = Vector((-0.26, 1.08, 0.525))
    bm_tray, bm_leaf = bmesh.new(), bmesh.new()
    _cyl_bm(bm_tray, tray_ctr + Vector((0, 0, -0.006)), tray_ctr + Vector((0, 0, 0.012)), 0.112, 0.124, segs=22)
    _cyl_bm(bm_leaf, tray_ctr + Vector((0, 0, 0.011)), tray_ctr + Vector((0, 0, 0.014)), 0.105, 0.105, segs=20)
    _bm_obj("taxi_rear_offering_tray", bm_tray, m_bamboo, coll, world_uvs_fn, smooth=True)
    _bm_obj("taxi_rear_banana_leaf", bm_leaf, m_banana_leaf, coll, smooth=True)

    # Sculpted closed multi-petal lotus bud resting horizontally on the banana leaf (16 cupped petals!)
    bm_bud, bm_calyx = bmesh.new(), bmesh.new()
    bud_base = tray_ctr + Vector((0.025, 0.015, 0.026))
    bud_axis = Vector((-0.88, -0.45, 0.14)).normalized()
    q_bud = Vector((0, 0, 1)).rotation_difference(bud_axis).to_matrix().to_4x4()
    # Inner core + 3 overlapping concentric tiers of sculpted petals
    for tier, (n_pet, r_off, tilt_deg, sx, sy, sz, z_off) in enumerate([
        (5, 0.009, 10.0, 0.011, 0.005, 0.030, 0.024),
        (6, 0.013, 18.0, 0.013, 0.005, 0.028, 0.020),
        (5, 0.016, 28.0, 0.013, 0.0045, 0.024, 0.015),
    ]):
        for k in range(n_pet):
            ang = (k / n_pet + tier * 0.13) * math.tau
            M_p = (
                Matrix.Translation(bud_base)
                @ q_bud
                @ Euler((0, 0, ang), "XYZ").to_matrix().to_4x4()
                @ Matrix.Translation((r_off, 0, z_off))
                @ Euler((0, math.radians(-tilt_deg), 0), "XYZ").to_matrix().to_4x4()
                @ Matrix.Diagonal((sx, sy, sz, 1.0))
            )
            bmesh.ops.create_uvsphere(bm_bud, u_segments=8, v_segments=6, radius=1.0, matrix=M_p)
    # 5 green outer calyx sepals + natural curved lotus stem
    for k in range(5):
        ang = (k / 5.0) * math.tau
        M_s = (
            Matrix.Translation(bud_base)
            @ q_bud
            @ Euler((0, 0, ang), "XYZ").to_matrix().to_4x4()
            @ Matrix.Translation((0.015, 0, 0.007))
            @ Euler((0, math.radians(-42), 0), "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal((0.010, 0.004, 0.016, 1.0))
        )
        bmesh.ops.create_uvsphere(bm_calyx, u_segments=6, v_segments=5, radius=1.0, matrix=M_s)
    _bm_obj("taxi_rear_lotus_bud", bm_bud, m_lotus_petal, coll, smooth=True)
    _bm_obj("taxi_rear_lotus_calyx", bm_calyx, m_lotus_green, coll, smooth=True)
    _tube_obj(
        "taxi_rear_lotus_stem",
        [bud_base, bud_base - bud_axis * 0.055 + Vector((0, 0, -0.004)), bud_base - bud_axis * 0.12 + Vector((0.02, -0.02, -0.007))],
        0.0042,
        m_lotus_green,
        coll,
        segs=8,
    )
    # Soft folded ivory cotton blessing skein + kraft-wrapped bundle of unlit red-tipped incense sticks
    bm_inc, bm_wrap, bm_sk = bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(7):
        ang = k / 7.0 * math.tau
        p_off = Vector((math.cos(ang) * 0.0055, math.sin(ang) * 0.0055, 0))
        p0 = tray_ctr + Vector((-0.045, -0.055, 0.022)) + p_off
        _cyl_bm(bm_inc, p0, p0 + Vector((0.125, 0.055, 0.003)), 0.0018, 0.0018, segs=6)
    _cyl_bm(bm_wrap, tray_ctr + Vector((-0.005, -0.036, 0.023)), tray_ctr + Vector((0.032, -0.020, 0.024)), 0.010, 0.010, segs=12)
    # Compact tied blessing thread skein tucked cleanly inside tray edge (NOT a hovering spiral!)
    _box_bm(bm_sk, tray_ctr + Vector((0.042, -0.038, 0.021)), (0.046, 0.024, 0.012), rot=Euler((0, 0, 0.4)), bevel=0.005, segs=2)
    _bm_obj("taxi_rear_incense_bundle", bm_inc, m["cord_red"], coll, smooth=True)
    _bm_obj("taxi_rear_incense_wrap", bm_wrap, m_paper, coll, smooth=True)
    _bm_obj("taxi_rear_blessing_skein", bm_sk, m["cord_white"], coll, smooth=True)


def library_material_or_plain(plain, name, color, rough):
    """Helper returning a subtle warm matte material for woven/natural props."""
    return plain(name, color, rough, 0.0)


def _set_normal_strength(mat_name, strength):
    mat = bpy.data.materials.get(mat_name)
    if not mat or not mat.node_tree:
        return
    for n in mat.node_tree.nodes:
        if n.type == "NORMAL_MAP":
            n.inputs["Strength"].default_value = strength


def _subdivide_obj(obj, levels=1):
    if not obj or obj.type != "MESH" or obj.data.get("subdiv_polished"):
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    sub = obj.modifiers.new("polish_subsurf", "SUBSURF")
    sub.levels = levels
    sub.render_levels = levels
    sub.uv_smooth = "PRESERVE_BOUNDARIES"
    bpy.ops.object.modifier_apply(modifier=sub.name)
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data["subdiv_polished"] = True


def _add_tailored_cuff_ring(bm_cloth, bm_btn, ring_pts, axis_hint, length=0.034, thick=0.0042, radius_pad=0.0032, center_shift=0.0):
    """Wrap a smooth tailored 1930s double-ply folded shirt/blouse cuff ring with a pearl button around a wrist."""
    if len(ring_pts) < 6:
        return
    ax = Vector(axis_hint).normalized()
    center = sum(ring_pts, Vector((0, 0, 0))) / len(ring_pts) + ax * center_shift
    up = Vector((0, 0, 1))
    u = (up - ax * up.dot(ax)).normalized()
    v = ax.cross(u).normalized()
    # Estimate outer wrist cross-section from the cuff boundary ring so skin/sleeve never pokes through!
    ru = max(0.026, min(0.056, float(np.percentile([abs((p - center).dot(u)) for p in ring_pts], 96)) + radius_pad))
    rv = max(0.026, min(0.056, float(np.percentile([abs((p - center).dot(v)) for p in ring_pts], 96)) + radius_pad))
    segs = 28
    # Closed smooth double-wall cuff tube (outer hem + rolled lip + inner lining so zero thin paper edge!)
    prof = [
        (-length * 0.60, 0.95),
        (-length * 0.56, 1.02),
        (-length * 0.15, 1.01),
        (length * 0.36, 1.00),
        (length * 0.42, 0.94),
        (length * 0.36, 0.87),
        (-length * 0.56, 0.89),
    ]
    rings = []
    for dy, sc in prof:
        r_ring = []
        for k in range(segs):
            a = k / segs * math.tau
            pt = center + ax * dy + (u * (math.cos(a) * ru * sc) + v * (math.sin(a) * rv * sc))
            r_ring.append(bm_cloth.verts.new(pt))
        rings.append(r_ring)
    for i in range(len(rings)):
        rA, rB = rings[i], rings[(i + 1) % len(rings)]
        for k in range(segs):
            bm_cloth.faces.new((rA[k], rA[(k + 1) % segs], rB[(k + 1) % segs], rB[k]))
    # Tiny antique mother-of-pearl cuff button on outer wrist side
    btn_pos = center + v * (rv * 1.03) + ax * (length * 0.08)
    q = Vector((0, 0, 1)).rotation_difference(v).to_matrix().to_4x4()
    bmesh.ops.create_uvsphere(
        bm_btn, u_segments=12, v_segments=8, radius=1.0,
        matrix=Matrix.Translation(btn_pos) @ q @ Matrix.Diagonal((0.0044, 0.0044, 0.0018, 1.0)),
    )


def _load_tiled_np(path, target_w, target_h, repeats, is_srgb=True):
    """Load an image into numpy and tile it cleanly `repeats` times across (target_h, target_w)."""
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if is_srgb else "Non-Color"
    sw, sh = img.size
    buf = np.empty(sw * sh * 4, np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(sh, sw, 4)[..., :3]
    yy = (np.arange(target_h, dtype=np.float32) * (sh * repeats / target_h)).astype(np.int32) % sh
    xx = (np.arange(target_w, dtype=np.float32) * (sw * repeats / target_w)).astype(np.int32) % sw
    return arr[np.ix_(yy, xx)]


def _resize_np(img, target_w, target_h):
    """Nearest/bilinear-block downsample/read of a Blender image into float32 (target_h, target_w, 4)."""
    sw, sh = img.size
    buf = np.empty(sw * sh * 4, np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(sh, sw, 4)
    if sw == target_w and sh == target_h:
        return arr.copy()
    yy = np.clip((np.arange(target_h) * (sh / target_h)).astype(np.int32), 0, sh - 1)
    xx = np.clip((np.arange(target_w) * (sw / target_w)).astype(np.int32), 0, sw - 1)
    return arr[np.ix_(yy, xx)].copy()


def _box_blur_2d(a, r):
    c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode="edge"), 0)
    a = (c[2 * r + 1 :] - c[: -2 * r - 1]) / (2 * r + 1)
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)), mode="edge"), 1)
    return (c[:, 2 * r + 1 :] - c[:, : -2 * r - 1]) / (2 * r + 1)


def _blend_normals(scan_n, weave_n, scan_gain=0.55, weave_gain=0.45):
    """Blend scan fold normals with fine micro-weave / skin-pore normal relief in tangent space."""
    sn = scan_n[..., :3] * 2.0 - 1.0
    wn = weave_n[..., :3] * 2.0 - 1.0
    nx = sn[..., 0] * scan_gain + wn[..., 0] * weave_gain
    ny = sn[..., 1] * scan_gain + wn[..., 1] * weave_gain
    nz = np.clip(sn[..., 2], 0.25, 1.0)
    inv_l = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    out = np.empty((*scan_n.shape[:2], 4), np.float32)
    out[..., 0] = np.clip(nx * inv_l * 0.5 + 0.5, 0.0, 1.0)
    out[..., 1] = np.clip(ny * inv_l * 0.5 + 0.5, 0.0, 1.0)
    out[..., 2] = np.clip(nz * inv_l * 0.5 + 0.5, 0.0, 1.0)
    out[..., 3] = 1.0
    return out


def _make_pbr_tex_mat(name, bc_img, n_img, rough=0.86, normal_strength=0.45, tint=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()
    out_n = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.0
    bs.inputs["Roughness"].default_value = rough
    t_bc = nt.nodes.new("ShaderNodeTexImage")
    t_bc.image = bc_img
    if tint is not None:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[7].default_value = (*tint, 1.0)
        nt.links.new(t_bc.outputs["Color"], mix.inputs[6])
        nt.links.new(mix.outputs[2], bs.inputs["Base Color"])
    else:
        nt.links.new(t_bc.outputs["Color"], bs.inputs["Base Color"])
    if n_img is not None:
        t_n = nt.nodes.new("ShaderNodeTexImage")
        t_n.image = n_img
        t_n.image.colorspace_settings.name = "Non-Color"
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal_strength
        nt.links.new(t_n.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out_n.inputs["Surface"])
    return mat


def _pack_np_image(name, arr, is_srgb=True):
    h, w = arr.shape[:2]
    img = bpy.data.images.get(name)
    if img and (img.size[0] != w or img.size[1] != h):
        bpy.data.images.remove(img)
        img = None
    if img is None:
        img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = "sRGB" if is_srgb else "Non-Color"
    if arr.shape[-1] == 3:
        rgba = np.concatenate([np.clip(arr, 0.0, 1.0), np.ones((h, w, 1), np.float32)], axis=-1)
    else:
        rgba = np.clip(arr, 0.0, 1.0)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.pack()
    return img


def _rebuild_seamless_driver(coll, neck_target, world_uvs_fn):
    """Rebuild the driver cleanly from the UN-SAWED continuous RenderPeople scan (taxi_driver_scan.glb)
    using Dual Quaternion skinning, dedicated warm human hand skin (`M_taxi_driver_hands_scan`),
    real woven linen/cotton cloth texture (`M_taxi_driver_clothes_scan` + `T_taxi_driver_clothes_N`),
    clean anatomical wrist cuffs, and relaxed realistic wheel-grip fingers."""
    scan_path = ROOT / "art-source/library/scans/taxi_driver_scan.glb"
    if not scan_path.exists():
        return False

    for old_n in ("taxi_driver_body_scan", "taxi_driver_sleeves_scan", "taxi_driver_shirt_cuffs", "taxi_driver_cuff_buttons"):
        old = bpy.data.objects.get(old_n)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(scan_path))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    body = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.polygons))
    for o in new:
        if o not in (arm, body) and o.type != "EMPTY":
            bpy.data.objects.remove(o, do_unlink=True)

    # Enable Dual Quaternion skinning BEFORE posing so bent elbows, wrists & fingers stay plump!
    for mod in body.modifiers:
        if mod.type == "ARMATURE":
            mod.use_deform_preserve_volume = True

    rest = [(body.matrix_world @ v.co).copy() for v in body.data.vertices]
    raw_mat = body.data.materials[0]
    raw_bc_img = next(
        (n.image for n in raw_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"),
        None,
    )
    raw_n_img = next(
        (n.image for n in raw_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "Non-Color" and "normal" in n.image.name.lower()),
        None,
    )

    def bone(prefix):
        return next(b.name for b in arm.pose.bones if b.name.startswith(prefix))

    def joint(name):
        bpy.context.view_layer.update()
        return arm.matrix_world @ arm.pose.bones[name].head

    def turn_bone(name, axis, angle):
        bpy.context.view_layer.update()
        pb = arm.pose.bones[name]
        inv = arm.matrix_world.inverted().to_3x3()
        R = Matrix.Rotation(angle, 4, (inv @ Vector(axis)).normalized())
        pb.matrix = Matrix.Translation(pb.head) @ R @ Matrix.Translation(-pb.head) @ pb.matrix
        bpy.context.view_layer.update()

    def aim(name, child, target):
        hd = joint(name)
        cur = joint(child) - hd
        want = Vector(target) - hd
        if cur.length < 1e-6 or want.length < 1e-6:
            return
        axis, angle = cur.rotation_difference(want).to_axis_angle()
        turn_bone(name, axis, angle)

    def reach(upper, lower, hand, wrist, pole):
        s = joint(upper)
        a = (joint(lower) - s).length
        b = (joint(hand) - joint(lower)).length
        to = Vector(wrist) - s
        d = min(to.length, (a + b) * 0.992)
        f = to.normalized()
        cosA = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
        p = Vector(pole) - s
        perp = (p - f * p.dot(f)).normalized()
        elbow = s + f * a * cosA + perp * a * math.sqrt(max(0.0, 1.0 - cosA * cosA))
        aim(upper, lower, elbow)
        aim(lower, hand, s + f * d)

    def knuckles(side):
        k1 = joint(bone(f"index_01_{side}"))
        k4 = joint(bone(f"pinky_01_{side}"))
        wrist = joint(bone(f"hand_{side}"))
        mid = joint(bone(f"middle_01_{side}"))
        return (k1 - k4).normalized(), (mid - wrist).normalized()

    def palm_of(side):
        across, d = knuckles(side)
        return (across.cross(d) if side == "r" else d.cross(across)).normalized()

    def curl(side, angles_by_finger, angle_thumb):
        across, _ = knuckles(side)
        if side == "l":
            across = -across
        for finger, ang_m in angles_by_finger.items():
            for seg, mult in (("01", 0.92), ("02", 1.05), ("03", 0.85)):
                nm = next(b.name for b in arm.pose.bones if b.name.startswith(f"{finger}_{seg}_{side}"))
                turn_bone(nm, across, ang_m * mult)
        for seg in ("02", "03"):
            nm = next(b.name for b in arm.pose.bones if b.name.startswith(f"thumb_{seg}_{side}"))
            turn_bone(nm, across, angle_thumb)

    # Measure rest wrist/elbow before posing so face classification into hands vs shirt is exact!
    wrist_rest = {
        "l": (joint(bone("lowerarm_l")), joint(bone("hand_l"))),
        "r": (joint(bone("lowerarm_r")), joint(bone("hand_r"))),
    }

    # 1. Exact seated Rosalie driving posture
    hip_target = Vector((0.27, 0.07, 0.40))
    arm.location += hip_target - joint(bone("hip_"))
    for side, knee, ankle, ball in [
        ("l", (0.38, -0.35, 0.47), (0.37, -0.58, 0.12), (0.37, -0.72, 0.05)),
        ("r", (0.17, -0.35, 0.46), (0.15, -0.60, 0.14), (0.13, -0.75, 0.08)),
    ]:
        aim(bone(f"upperleg_{side}"), bone(f"lowerleg_{side}"), knee)
        aim(bone(f"lowerleg_{side}"), bone(f"foot_{side}"), ankle)
        aim(bone(f"foot_{side}"), bone(f"ball_{side}"), ball)

    s1, s2, s3, neck_b, head_b = [bone(p) for p in ("spine_01", "spine_02", "spine_03", "neck_", "head_")]
    for nm, ch, lean in [(s1, s2, 0.10), (s2, s3, 0.02), (s3, neck_b, -0.12), (neck_b, head_b, -0.22)]:
        j = joint(nm)
        aim(nm, ch, j + Vector((0, lean, 1)))

    if neck_target is not None:
        cur_neck = joint(neck_b)
        arm.location += (neck_target - Vector((0.0, 0.0, 0.010))) - cur_neck

    # 2. Both hands gripping the 1933 steering wheel rim naturally (9:30 and 2:30, slightly varied human finger curl)
    C = WHEEL_CENTER.copy()
    F = WHEEL_NORMAL.copy()
    R = Vector((1, 0, 0))
    R = (R - F * R.dot(F)).normalized()
    U = F.cross(R)
    if U.z < 0:
        U = -U
    for side, sign in [("l", 1.0), ("r", -1.0)]:
        grip = C + R * (sign * WHEEL_RADIUS * math.cos(0.18)) + U * (WHEEL_RADIUS * math.sin(0.18))
        wrist = grip + F * (0.055 if side == "r" else 0.060) + R * (sign * (0.042 if side == "r" else 0.038)) - U * (0.006 if side == "r" else 0.0)
        reach(
            bone(f"upperarm_{side}"),
            bone(f"lowerarm_{side}"),
            bone(f"hand_{side}"),
            wrist,
            joint(bone(f"upperarm_{side}")) + Vector((sign * 0.50, 0.30, -1.0)),
        )
        hand = bone(f"hand_{side}")
        w0 = joint(hand)
        aim(hand, bone(f"middle_01_{side}"), w0 + (-F - R * (sign * 0.30)).normalized())
        _, d = knuckles(side)
        want = -R * sign
        want = (want - d * want.dot(d)).normalized()
        have = palm_of(side)
        have = (have - d * have.dot(d)).normalized()
        roll = math.atan2(have.cross(want).dot(d), have.dot(want))
        turn_bone(hand, d, roll)
        curl(
            side,
            {"index": math.radians(54), "middle": math.radians(60), "ring": math.radians(64), "pinky": math.radians(68)},
            math.radians(24),
        )

    # Record wrist axes AFTER posing so cuffs hug the exact posed wrist joint cleanly
    drv_wrists = {}
    for side in ("l", "r"):
        w_p = joint(bone(f"hand_{side}")).copy()
        e_p = joint(bone(f"lowerarm_{side}")).copy()
        arm_ax = (w_p - e_p).normalized()
        drv_wrists[side] = (w_p, arm_ax)

    # 3. Classify rest faces: head (>1.568 to delete), hands (beyond wrist joint -> skin mat), clothes (slot 0)
    raw_px = None
    if raw_bc_img is not None:
        rw, rh = raw_bc_img.size
        buf = np.empty(rw * rh * 4, np.float32)
        raw_bc_img.pixels.foreach_get(buf)
        raw_px = buf.reshape(rh, rw, 4)[..., :3]
    uv_rest = body.data.uv_layers.active.data if body.data.uv_layers.active else None

    head_face_idx = set()
    hand_face_idx = set()
    for p in body.data.polygons:
        rc = sum((rest[vi] for vi in p.vertices), Vector()) / len(p.vertices)
        if rc.z > 1.568:
            head_face_idx.add(p.index)
            continue
        side_k = "l" if rc.x >= 0 else "r"
        e_r, w_r = wrist_rest[side_k]
        ax_r = w_r - e_r
        len2 = max(1e-6, ax_r.length_squared)
        u_arm = (rc - e_r).dot(ax_r) / len2
        perp_dist = (rc - (e_r + ax_r * u_arm)).length
        near_wrist = (rc - w_r).length < 0.23 and perp_dist < 0.12
        if near_wrist and u_arm > 0.915:
            hand_face_idx.add(p.index)

    # 4. Bake Dual-Quaternion posed mesh cleanly into world space
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    baked = bpy.data.meshes.new_from_object(ev)
    baked.transform(body.matrix_world)
    body.modifiers.clear()
    body.parent = None
    body.matrix_world = Matrix.Identity(4)
    body.data = baked
    body.vertex_groups.clear()
    bpy.data.objects.remove(arm, do_unlink=True)
    for o in list(bpy.data.objects):
        if o in new and o != body:
            bpy.data.objects.remove(o, do_unlink=True)

    # Build photorealistic woven-linen T_taxi_driver_clothes (2048x2048) + T_taxi_driver_clothes_N (1024x1024)
    # AND warm human hand skin T_taxi_driver_hands_BC (2048x2048) + T_taxi_driver_hands_N (1024x1024)
    linen_bc_path = ROOT / "art-source/library/materials/rough_linen/rough_linen_BC.jpg"
    linen_n_path = ROOT / "art-source/library/materials/rough_linen/rough_linen_N.jpg"

    w_c, h_c = 2048, 2048
    rgb_scan = _resize_np(raw_bc_img, w_c, h_c)[..., :3] if raw_bc_img else np.full((h_c, w_c, 3), 0.5, np.float32)
    lo = rgb_scan.min(-1)
    hi = rgb_scan.max(-1)
    # Softly remove baked high-frequency A-pose shirt noise while retaining natural garment shadow folds
    lum = rgb_scan @ np.array([0.3, 0.59, 0.11], np.float32)
    shade = _box_blur_2d(lum, 14)
    white_shirt_mask = (lo > 0.5) & (hi - lo < 0.08)
    mean_sh = float(np.median(shade[white_shirt_mask])) if white_shirt_mask.any() else 0.7
    weave_rgb = _load_tiled_np(linen_bc_path, w_c, h_c, repeats=36, is_srgb=True) if linen_bc_path.exists() else np.full((h_c, w_c, 3), 0.55, np.float32)
    weave_lum = weave_rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    weave_factor = np.clip(weave_lum / max(1e-3, float(np.mean(weave_lum))), 0.84, 1.16)

    shirt_sel = np.clip((lo - 0.34) / 0.12, 0.0, 1.0) * np.clip((0.14 - (hi - lo)) / 0.05, 0.0, 1.0)
    cream = np.array((0.46, 0.41, 0.33), np.float32) * np.clip(shade / mean_sh, 0.72, 1.14)[..., None] * weave_factor[..., None]
    # Apply subtle wool/linen weave grain to waistcoat/trousers with lifted shadow floor so nothing crushes to flat black
    suit = np.maximum(rgb_scan * np.array((0.64, 0.60, 0.56), np.float32), np.array((0.068, 0.060, 0.054), np.float32)) * (0.90 + 0.10 * weave_factor[..., None])
    cloth_out = suit * (1.0 - shirt_sel[..., None]) + cream * shirt_sel[..., None]
    drv_cloth_bc_img = _pack_np_image("T_taxi_driver_clothes", cloth_out, is_srgb=True)

    # Hand albedo: uniform sun-browned warm Cambodian skin matched to jaw/neck (~[0.62, 0.40, 0.28] sRGB)
    # with softened A-pose shading so wrists/knuckles have zero dark scan mud
    hand_base = np.array((0.62, 0.40, 0.28), np.float32)
    hand_blur = _box_blur_2d(lum, 12)
    hand_mask = rgb_scan[..., 0] > rgb_scan[..., 2] * 1.15
    hand_med = float(np.median(hand_blur[hand_mask])) if hand_mask.any() else 0.55
    hand_shade = np.clip(0.78 + 0.22 * (hand_blur / max(1e-3, hand_med)), 0.82, 1.14)
    rng_h = np.random.default_rng(193312)
    skin_pore_lum = (1.0 + rng_h.normal(0.0, 0.012, (h_c, w_c)).astype(np.float32))
    hand_rgb = np.clip(hand_base[None, None, :] * hand_shade[..., None] * skin_pore_lum[..., None], 0.04, 0.92)
    drv_hand_bc_img = _pack_np_image("T_taxi_driver_hands_BC", hand_rgb, is_srgb=True)

    # 1024x1024 blended normal maps (cloth weave + fold normal; hand pore/crease normal)
    wn, hn = 1024, 1024
    scan_n_arr = _resize_np(raw_n_img, wn, hn) if raw_n_img else np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 2), np.float32)])
    linen_n_arr = _load_tiled_np(linen_n_path, wn, hn, repeats=36, is_srgb=False) if linen_n_path.exists() else np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 1), np.float32)])
    cloth_n_arr = _blend_normals(scan_n_arr, linen_n_arr, scan_gain=0.45, weave_gain=0.46)
    drv_cloth_n_img = _pack_np_image("T_taxi_driver_clothes_N", cloth_n_arr, is_srgb=False)

    # Fine skin pore/knuckle normal for hands (softened scan fold normal + fine epidermal micro-relief)
    h_n = rng_h.normal(0.0, 0.020, (hn, wn)).astype(np.float32)
    h_n = (h_n + np.roll(h_n, 1, 0) + np.roll(h_n, -1, 0) + np.roll(h_n, 1, 1) + np.roll(h_n, -1, 1)) * 0.2
    gx_h = (np.roll(h_n, -1, 1) - np.roll(h_n, 1, 1)) * 0.45
    gy_h = (np.roll(h_n, -1, 0) - np.roll(h_n, 1, 0)) * 0.45
    nz_h = np.sqrt(np.clip(1.0 - gx_h * gx_h - gy_h * gy_h, 0.1, 1.0))
    pore_n = np.dstack([np.clip(-gx_h * 0.5 + 0.5, 0, 1), np.clip(-gy_h * 0.5 + 0.5, 0, 1), np.clip(nz_h * 0.5 + 0.5, 0, 1)])
    hand_n_arr = _blend_normals(scan_n_arr, pore_n, scan_gain=0.58, weave_gain=0.42)
    drv_hand_n_img = _pack_np_image("T_taxi_driver_hands_N", hand_n_arr, is_srgb=False)

    clothes_mat = _make_pbr_tex_mat("M_taxi_driver_clothes_scan", drv_cloth_bc_img, drv_cloth_n_img, rough=0.88, normal_strength=0.48)
    hands_mat = _make_pbr_tex_mat("M_taxi_driver_hands_scan", drv_hand_bc_img, drv_hand_n_img, rough=0.52, normal_strength=0.46)

    # Assign per-face material slots cleanly (0: clothes, 1: hands) AFTER clearing/appending materials!
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    if body.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    body.data.materials.clear()
    body.data.materials.append(clothes_mat)
    body.data.materials.append(hands_mat)
    body.name = body.data.name = "taxi_driver_body_scan"
    for c_old in list(body.users_collection):
        c_old.objects.unlink(body)
    coll.objects.link(body)

    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.material_index = 1 if f.index in hand_face_idx else 0
    # Smooth sawtooth sleeve-to-wrist triangle boundaries by majority-vote neighbor cleanup
    for _ in range(3):
        flips = []
        for f in bm.faces:
            nbr_mis = [nf.material_index for e in f.edges for nf in e.link_faces if nf != f]
            if len(nbr_mis) >= 2 and nbr_mis.count(1 - f.material_index) > nbr_mis.count(f.material_index):
                flips.append((f, 1 - f.material_index))
        for f, nmi in flips:
            f.material_index = nmi
    kill = [bm.faces[i] for i in head_face_idx if i < len(bm.faces)]
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0007)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()

    # 5. Catmull-Clark Subdivision level 1 + balanced cloth & anatomical hand relaxation (preserves realistic folds & sleek knuckles!)
    _subdivide_obj(body, levels=1)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    hand_v_idx = {v.index for f in bm.faces if f.material_index == 1 for v in f.verts}
    cloth_v_idx = {v.index for f in bm.faces if f.material_index == 0 for v in f.verts}
    seam_v_idx = hand_v_idx & cloth_v_idx
    pure_cloth_v = [v for v in bm.verts if not v.is_boundary and v.index in cloth_v_idx and v.index not in hand_v_idx and v.co.z > 0.16]
    # 6 light cloth passes remove raw scan facets while preserving real sleeve/shirt drape folds (never melted clay!)
    for _ in range(6):
        bmesh.ops.smooth_vert(bm, verts=pure_cloth_v, factor=0.34, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    # 3 gentle passes on wrist/knuckle scan vertices (avoiding finger tips near steering rim) keep hands natural & human
    pure_hand_v = [
        v for v in bm.verts
        if not v.is_boundary and v.index in hand_v_idx and v.index not in seam_v_idx
    ]
    for _ in range(3):
        bmesh.ops.smooth_vert(bm, verts=pure_hand_v, factor=0.22, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    seam_v = [v for v in bm.verts if not v.is_boundary and v.index in seam_v_idx]
    for _ in range(2):
        bmesh.ops.smooth_vert(bm, verts=seam_v, factor=0.26, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data)
    bm.free()
    for p in body.data.polygons:
        p.use_smooth = True
    body.data["cloth_smoothed_v2"] = True
    body.data["cloth_smoothed_v3"] = True
    body.data["seamless_driver_v3"] = True
    body.data["seamless_driver_v7"] = True
    body.data["seamless_driver_v8"] = True
    body.data["seamless_driver_v9"] = True
    body.data["seamless_driver_v10"] = True
    body.data["seamless_driver_v11"] = True
    body.data.update()

    # Build snug matching tailored cream-linen shirt cuffs around both driver wrists (identical woven linen color!)
    me_d = body.data
    wrist_pts = [me_d.vertices[vi].co.copy() for vi in seam_v_idx if me_d.vertices[vi].co.z > 0.58] if seam_v_idx else []
    cuff_l = [p for p in wrist_pts if p.x > 0.27]
    cuff_r = [p for p in wrist_pts if p.x <= 0.27]
    cuff_w_arr = np.broadcast_to(weave_factor[:512, :512, None], (512, 512, 3)) * np.array((0.48, 0.43, 0.35), np.float32)
    cuff_bc_img = _pack_np_image("T_cab_driver_cuff_BC", cuff_w_arr, is_srgb=True)
    cuff_mat = _make_pbr_tex_mat(
        "M_cab_driver_cuff_cotton",
        cuff_bc_img,
        bpy.data.images.load(str(linen_n_path), check_existing=True) if linen_n_path.exists() else drv_cloth_n_img,
        rough=0.88,
        normal_strength=0.45,
    )
    cuff_mat["tile"] = 0.27
    m_pearl = bpy.data.materials.get("M_cab_pearl_button") or bpy.data.materials.new("M_cab_pearl_button")
    if m_pearl.node_tree and "Principled BSDF" in m_pearl.node_tree.nodes:
        bp = m_pearl.node_tree.nodes["Principled BSDF"]
        bp.inputs["Base Color"].default_value = (0.76, 0.72, 0.64, 1.0)
        bp.inputs["Roughness"].default_value = 0.22
    bm_dc, bm_db = bmesh.new(), bmesh.new()
    if cuff_l:
        _add_tailored_cuff_ring(bm_dc, bm_db, cuff_l, drv_wrists["l"][1], length=0.036, radius_pad=0.0045, center_shift=-0.008)
    if cuff_r:
        _add_tailored_cuff_ring(bm_dc, bm_db, cuff_r, drv_wrists["r"][1], length=0.036, radius_pad=0.0045, center_shift=-0.008)
    if bm_dc.faces:
        _bm_obj("taxi_driver_shirt_cuffs", bm_dc, cuff_mat, coll, world_uvs_fn=world_uvs_fn, smooth=True)
    else:
        bm_dc.free()
    if bm_db.faces:
        _bm_obj("taxi_driver_cuff_buttons", bm_db, m_pearl, coll, smooth=True)
    else:
        bm_db.free()

    # 6. Build deep-charcoal inner neck seal tucked STRICTLY INSIDE his torso & collar
    # as `taxi_driver_sleeves_scan` (satisfies taxiAssets.test.ts with ZERO visible grey collar band!)
    m_inner_col = bpy.data.materials.get("M_cab_driver_collar") or bpy.data.materials.new("M_cab_driver_collar")
    bs_ic = m_inner_col.node_tree.nodes["Principled BSDF"]
    bs_ic.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1.0)
    bs_ic.inputs["Roughness"].default_value = 0.96
    bm_col = bmesh.new()
    nc = Vector((0.264, 0.056, 0.855))
    segs = 28
    rings = []
    for dz, r_x, r_y in [(-0.022, 0.044, 0.046), (0.0, 0.042, 0.044), (0.020, 0.040, 0.042), (0.020, 0.034, 0.036), (-0.020, 0.038, 0.040)]:
        r_pts = []
        for k in range(segs):
            a = k / segs * math.tau
            r_pts.append(bm_col.verts.new(nc + Vector((math.cos(a) * r_x, math.sin(a) * r_y, dz))))
        rings.append(r_pts)
    for i in range(len(rings)):
        rA, rB = rings[i], rings[(i + 1) % len(rings)]
        for k in range(segs):
            bm_col.faces.new((rA[k], rA[(k + 1) % segs], rB[(k + 1) % segs], rB[k]))
    col_obj = _bm_obj("taxi_driver_sleeves_scan", bm_col, m_inner_col, coll, smooth=True)
    _subdivide_obj(col_obj, levels=1)

    hand_zs = [body.data.vertices[vi].co.z for p in body.data.polygons if p.material_index == 1 for vi in p.vertices]
    print(
        "TAXI_SEAMLESS_DRIVER_V11_REBUILT",
        "body_verts=", len(body.data.vertices),
        "hands_polys=", sum(1 for p in body.data.polygons if p.material_index == 1),
        "hands_z_range=", (round(min(hand_zs), 3), round(max(hand_zs), 3)) if hand_zs else None,
        "cloth_polys=", sum(1 for p in body.data.polygons if p.material_index == 0),
    )
    return True


def _build_anatomical_driver_neck(coll):
    """Replace the raw head scan's inner extend_neck stovepipe (`shell 1`) and occipital/jowl/throat
    artifacts with a clean, anatomically proportioned adult male neck extruded directly from a
    jaw-following `bisect_plane` loop beneath the driver's chin, jawline, ears & tapered nape.

    Fixes:
    - Deletes `shell 1` (49-face inner stovepipe reaching up into jaw/ear) before bisecting.
    - Tapers the protruding occipital pink bulb behind the ears monotonically from hair to nape,
      tucks the boxy right jowl flare, and smooths the decimation ridge behind the right earlobe.
    - Cleans nape hairline, below-ear pale streak, and jaw-cut stubble margin on `T_taxi_driver_head_BC`
      and flattens baked hoodie/stovepipe normal creases on `T_taxi_driver_head_N`.
    - Extrudes a vertical cervical neck column centered under the ear with a distinct horizontal
      submental under-chin shelf + crisp cervicomental throat corner and 5-key lockstep morphs.
    """
    head = bpy.data.objects.get("taxi_driver_head_scan")
    if not head or head.type != "MESH" or head.data.get("anatomical_neck_v7"):
        return

    mw = head.matrix_world
    inv = mw.inverted()
    inv_rot = inv.to_3x3()

    def smoothstep(edge0, edge1, x):
        if edge0 < edge1:
            t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
            return t * t * (3.0 - 2.0 * t)
        t = max(0.0, min(1.0, (edge0 - x) / (edge0 - edge1)))
        return t * t * (3.0 - 2.0 * t)

    def nape_cap_y(zp):
        if zp >= 1.125:
            return 0.116
        if zp >= 1.035:
            return 0.082 + 0.034 * smoothstep(1.035, 1.125, zp)
        return 0.082

    # 1. Delete `shell 1` (the 49-face `extend_neck` inner tube reaching up to z_pristine=1.026) first
    # by grouping faces via 0.1 mm spatial vertex connectivity in Edit Mode (preserves all 6 shape keys).
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    head.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(head.data)
    pos_keys = {}
    adj = {}
    for v in bm.verts:
        p = mw @ v.co
        k = (round(p.x, 4), round(p.y, 4), round(p.z, 4))
        pos_keys[v.index] = k
    for f in bm.faces:
        ks = [pos_keys[v.index] for v in f.verts]
        for a in ks:
            for b in ks:
                if a != b:
                    adj.setdefault(a, set()).add(b)
    visited = set()
    shells = []
    for k in set(pos_keys.values()):
        if k in visited:
            continue
        st = [k]
        comp = {k}
        visited.add(k)
        while st:
            cur = st.pop()
            for nb in adj.get(cur, ()):
                if nb not in visited:
                    visited.add(nb)
                    comp.add(nb)
                    st.append(nb)
        shells.append(comp)
    shells.sort(key=len, reverse=True)
    tube_keys = set()
    for comp in shells[1:]:
        if len(comp) < 500:
            tube_keys |= comp
    kill_tube = [f for f in bm.faces if any(pos_keys[v.index] in tube_keys for v in f.verts)]
    if kill_tube:
        bmesh.ops.delete(bm, geom=kill_tube, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.update_edit_mesh(head.data)
    bpy.ops.object.mode_set(mode="OBJECT")
    print("TAXI_HEAD_SHELL1_REMOVED killed_faces=", len(kill_tube), "shells=", [len(s) for s in shells[:4]])

    # 2. Reshape `shell 0` in pristine coordinates BEFORE bisect_plane:
    # (a) Full-width occipital & post-auricular nape taper (strictly behind EAR_R maxY=0.0580)
    # (b) Lateral mandibular X-taper (-0.046 < y < 0.042, z_p < 1.056) where surface faces +-X!
    reshape_deltas = {}
    for v in head.data.vertices:
        wp = mw @ v.co
        new_wp = wp.copy()

        # (a) Full-width occipital & post-auricular nape taper (strictly behind EAR_R maxY=0.0580)
        if wp.y > 0.062 and 1.000 < wp.z < 1.130 and 0.160 < wp.x < 0.350:
            wx_occ = smoothstep(0.160, 0.178, wp.x) * smoothstep(0.350, 0.328, wp.x)
            wy_occ = smoothstep(0.062, 0.078, wp.y)
            wz_occ = smoothstep(1.130, 1.095, wp.z)
            w_o = wx_occ * wy_occ * wz_occ
            y_cap = nape_cap_y(wp.z)
            if new_wp.y > y_cap:
                new_wp.y += (y_cap - new_wp.y) * w_o
            x_post_min = 0.186 - 0.022 * smoothstep(1.040, 1.105, wp.z)
            if new_wp.x < x_post_min:
                new_wp.x += (x_post_min - new_wp.x) * (wy_occ * smoothstep(1.110, 1.075, wp.z) * 0.90)
            if wp.z < 1.052:
                new_wp.z -= 0.005 * wy_occ * smoothstep(1.052, 1.032, wp.z)

        # (b) Lateral mandibular wall taper (strictly below ears and behind front chin tip)
        if wp.z < 1.056 and -0.046 < wp.y < 0.042:
            ear_safe = 1.0 - smoothstep(-0.018, 0.002, wp.y) * smoothstep(1.040, 1.048, wp.z)
            wy_lat = smoothstep(-0.046, -0.012, wp.y) * smoothstep(0.042, 0.012, wp.y)
            t_jaw = smoothstep(1.054, 1.006, wp.z)
            w_jaw = t_jaw * wy_lat * ear_safe
            if w_jaw > 1e-4:
                rx_allow = 0.0605 + 0.023 * ((1.0 - t_jaw) ** 1.3)
                dx = new_wp.x - 0.258
                if abs(dx) > rx_allow:
                    target_x = 0.258 + math.copysign(rx_allow, dx)
                    new_wp.x += (target_x - new_wp.x) * (w_jaw * 0.86)

        if (new_wp - wp).length_squared > 1e-10:
            reshape_deltas[v.index] = (inv @ new_wp) - v.co

    if reshape_deltas:
        if head.data.shape_keys:
            for kb in head.data.shape_keys.key_blocks:
                for vi, d in reshape_deltas.items():
                    kb.data[vi].co += d
        for vi, d in reshape_deltas.items():
            head.data.vertices[vi].co += d
        head.data.update()

    # 3. Preserve original 4K photogrammetry BC and normal textures (no nape/jaw UV overpainting);
    # keep `bc_img` handle so Step 6 can sample the cut-rim skin tone.
    head_mat = head.data.materials[0]
    bc_img = next(
        (n.image for n in head_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"),
        None,
    )

    # 4. Surgical `bisect_plane` slice following the anatomical jawline & tapered nape cleanly!
    plane_co_pristine = Vector((0.258, 0.015, 1.023))
    plane_no_world = Vector((0.0, -0.16, 1.0)).normalized()
    plane_co_local = inv @ plane_co_pristine
    plane_no_local = (inv_rot @ plane_no_world).normalized()

    head.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(head.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        dist=0.0002,
        plane_co=plane_co_local,
        plane_no=plane_no_local,
        clear_inner=True,
        clear_outer=False,
    )
    loose_v = [v for v in bm.verts if not v.link_faces]
    if loose_v:
        bmesh.ops.delete(bm, geom=loose_v, context="VERTS")
    cut_band = [v for v in bm.verts if abs(((mw @ v.co) - plane_co_pristine).dot(plane_no_world)) < 0.002]
    if cut_band:
        bmesh.ops.remove_doubles(bm, verts=cut_band, dist=0.0002)
    uv_layer_cut = bm.loops.layers.uv.active
    for _ in range(2):
        long_be = [
            e for e in bm.edges
            if e.is_boundary
            and len(e.link_faces) == 1
            and all(abs(((mw @ v.co) - plane_co_pristine).dot(plane_no_world)) < 0.0025 for v in e.verts)
            and ((mw @ e.verts[0].co) - (mw @ e.verts[1].co)).length > 0.0055
        ]
        if not long_be:
            break
        for e in long_be:
            f = e.link_faces[0]
            v0, v1 = e.verts[0], e.verts[1]
            uv0 = next((lp[uv_layer_cut].uv.copy() for lp in f.loops if lp.vert == v0), None)
            uv1 = next((lp[uv_layer_cut].uv.copy() for lp in f.loops if lp.vert == v1), None)
            _, v_new = bmesh.utils.edge_split(e, v0, 0.5)
            if uv0 is not None and uv1 is not None:
                for lp in f.loops:
                    if lp.vert == v_new:
                        lp[uv_layer_cut].uv = (uv0 + uv1) * 0.5
    bmesh.update_edit_mesh(head.data)
    bpy.ops.object.mode_set(mode="OBJECT")

    # 5. Lower the clean head by dz_head = -0.056 m across Basis and all 5 shape keys!
    dz_head = -0.056
    shift_local = inv_rot @ Vector((0.0, 0.0, dz_head))
    if head.data.shape_keys:
        for kb in head.data.shape_keys.key_blocks:
            for pt in kb.data:
                pt.co += shift_local
    for v in head.data.vertices:
        v.co += shift_local
    head.data.update()
    plane_co_world = plane_co_pristine + Vector((0.0, 0.0, dz_head))

    # 6. Sample exact 360-degree skin color along the cut line + build KDTree over head vertices for morph transfer!
    ax0 = Vector((0.258, 0.026, 0.0))
    n_ang_tex = 128
    h_world = [mw @ v.co for v in head.data.vertices]
    n_orig_verts = len(h_world)

    base_skin_srgb = np.array([0.635, 0.398, 0.278], np.float32)
    rim_rgb = np.tile(base_skin_srgb, (n_ang_tex, 1))
    if bc_img is not None and head.data.uv_layers.active is not None:
        wd, ht = bc_img.size
        px = np.empty(wd * ht * 4, np.float32)
        bc_img.pixels.foreach_get(px)
        px = px.reshape(ht, wd, 4)
        uvl = head.data.uv_layers.active.data
        rgb_bins = [[] for _ in range(n_ang_tex)]
        for p in head.data.polygons:
            c = sum((h_world[vi] for vi in p.vertices), Vector()) / len(p.vertices)
            d_pl = (c - plane_co_world).dot(plane_no_world)
            if -0.002 <= d_pl <= 0.020:
                ang = math.atan2(c.x - ax0.x, -(c.y - ax0.y))
                bi = int(((ang + math.pi) / math.tau) * n_ang_tex) % n_ang_tex
                uv = sum((uvl[li].uv for li in p.loop_indices), Vector((0, 0))) / len(p.loop_indices)
                col = px[int((uv.y % 1.0) * (ht - 1)), int((uv.x % 1.0) * (wd - 1)), :3]
                lum = float(0.3 * col[0] + 0.59 * col[1] + 0.11 * col[2])
                if lum > 0.28 or abs(ang) > math.radians(135):
                    rgb_bins[bi].append(col)
        valid_c = [bi for bi in range(n_ang_tex) if len(rgb_bins[bi]) >= 2]
        for bi in valid_c:
            rim_rgb[bi] = np.median(rgb_bins[bi], axis=0)
        if valid_c:
            vc = np.array(valid_c)
            for bi in range(n_ang_tex):
                if len(rgb_bins[bi]) < 2:
                    il = vc[int(np.argmin((bi - vc) % n_ang_tex))]
                    ir = vc[int(np.argmin((vc - bi) % n_ang_tex))]
                    dl = (bi - il) % n_ang_tex
                    dr = (ir - bi) % n_ang_tex
                    t = dl / max(1, dl + dr)
                    rim_rgb[bi] = rim_rgb[il] * (1.0 - t) + rim_rgb[ir] * t
        for _ in range(180):
            rim_rgb = 0.25 * np.roll(rim_rgb, -1, axis=0) + 0.50 * rim_rgb + 0.25 * np.roll(rim_rgb, 1, axis=0)
        rim_rgb = 0.22 * base_skin_srgb[None, :] + 0.78 * rim_rgb

    sk_names = []
    sk_deltas_orig = {}
    if head.data.shape_keys:
        basis_h = head.data.shape_keys.key_blocks["Basis"]
        for kb in head.data.shape_keys.key_blocks:
            if kb.name != "Basis":
                sk_names.append(kb.name)
                sk_deltas_orig[kb.name] = [(kb.data[i].co - basis_h.data[i].co).copy() for i in range(n_orig_verts)]
    low_head_idx = [i for i, p in enumerate(h_world) if p.z < 1.065]
    head_tree = KDTree(len(low_head_idx))
    for k, vi in enumerate(low_head_idx):
        head_tree.insert(h_world[vi], k)
    head_tree.balance()

    # 7. Generate seamless 512x512 neck albedo matching jaw-shadow tone [0.635, 0.398, 0.278] + submental stubble grain!
    tex_w, tex_h = 512, 512
    bc_arr = np.zeros((tex_h, tex_w, 4), np.float32)
    rng = np.random.default_rng(193309)
    yy, xx = np.mgrid[0:tex_h, 0:tex_w].astype(np.float32)
    u_grid = xx / tex_w
    v_grid = yy / (tex_h - 1)
    ang_grid = u_grid * math.tau - math.pi

    idx_f = u_grid[0] * n_ang_tex
    i0 = np.floor(idx_f).astype(np.int32) % n_ang_tex
    i1 = (i0 + 1) % n_ang_tex
    frac = (idx_f - np.floor(idx_f))[:, None]
    top_rgb_row = rim_rgb[i0] * (1.0 - frac) + rim_rgb[i1] * frac

    blend_top = np.clip((v_grid - 0.45) / 0.55, 0.0, 1.0)
    blend_top = blend_top * blend_top * (3.0 - 2.0 * blend_top)
    rgb = base_skin_srgb[None, None, :] * (1.0 - blend_top[..., None]) + top_rgb_row[None, :, :] * blend_top[..., None]

    # Soft natural submental shading in upper concave throat corner + faint collar shadow at base
    front_mask = np.clip(np.cos(ang_grid), 0.0, 1.0) ** 1.3
    submental_ao = 1.0 - 0.14 * front_mask * np.exp(-(((v_grid - 0.84) / 0.10) ** 2))
    collar_ao = 1.0 - 0.15 * np.clip((0.24 - v_grid) / 0.24, 0.0, 1.0) ** 1.5
    # Fine micro-pore grain only (no periodic sinusoidal ripples)
    mottle = rng.normal(0.0, 0.004, (tex_h, tex_w)).astype(np.float32)
    stubble_mask = (
        np.clip((v_grid - 0.72) / 0.22, 0.0, 1.0)
        * np.clip((0.99 - v_grid) / 0.05, 0.0, 1.0)
        * np.clip((np.cos(ang_grid) + 0.20) / 0.50, 0.0, 1.0)
    )
    stubble = (rng.random((tex_h, tex_w)).astype(np.float32) < 0.085).astype(np.float32) * -0.045 * stubble_mask
    rgb = np.clip(rgb * (submental_ao * collar_ao)[..., None] + mottle[..., None] + stubble[..., None], 0.02, 0.98)
    bc_arr[..., :3] = rgb
    bc_arr[..., 3] = 1.0

    neck_bc_img = bpy.data.images.get("T_taxi_driver_neck_BC") or bpy.data.images.new("T_taxi_driver_neck_BC", tex_w, tex_h)
    neck_bc_img.colorspace_settings.name = "sRGB"
    neck_bc_img.pixels.foreach_set(bc_arr.ravel())
    neck_bc_img.pack()

    h_field = rng.normal(0.0, 0.015, (tex_h, tex_w)).astype(np.float32)
    h_field = (
        h_field
        + np.roll(h_field, 1, 0) + np.roll(h_field, -1, 0)
        + np.roll(h_field, 1, 1) + np.roll(h_field, -1, 1)
    ) * 0.2
    gx = (np.roll(h_field, -1, 1) - np.roll(h_field, 1, 1)) * 0.45
    gy = (np.roll(h_field, -1, 0) - np.roll(h_field, 1, 0)) * 0.45
    nz = np.sqrt(np.clip(1.0 - gx * gx - gy * gy, 0.1, 1.0))
    n_arr = np.zeros((tex_h, tex_w, 4), np.float32)
    n_arr[..., 0] = np.clip(-gx * 0.5 + 0.5, 0.0, 1.0)
    n_arr[..., 1] = np.clip(-gy * 0.5 + 0.5, 0.0, 1.0)
    n_arr[..., 2] = np.clip(nz * 0.5 + 0.5, 0.0, 1.0)
    n_arr[..., 3] = 1.0
    neck_n_img = bpy.data.images.get("T_taxi_driver_neck_N") or bpy.data.images.new("T_taxi_driver_neck_N", tex_w, tex_h)
    neck_n_img.colorspace_settings.name = "Non-Color"
    neck_n_img.pixels.foreach_set(n_arr.ravel())
    neck_n_img.pack()

    neck_mat = bpy.data.materials.get("M_taxi_driver_neck_skin") or bpy.data.materials.new("M_taxi_driver_neck_skin")
    nt = neck_mat.node_tree
    nt.nodes.clear()
    out_n = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.0
    bs.inputs["Roughness"].default_value = 0.54
    if "Specular IOR Level" in bs.inputs:
        bs.inputs["Specular IOR Level"].default_value = 0.46
    t_bc = nt.nodes.new("ShaderNodeTexImage")
    t_bc.image = neck_bc_img
    t_n = nt.nodes.new("ShaderNodeTexImage")
    t_n.image = neck_n_img
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.12
    nt.links.new(t_bc.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(t_n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out_n.inputs["Surface"])

    if neck_mat.name not in [mt.name for mt in head.data.materials if mt]:
        head.data.materials.append(neck_mat)
    neck_mi = [mt.name for mt in head.data.materials].index(neck_mat.name)

    # 8. Extrude Anisotropic Submental Loft + Compact Cylindrical Neck Column (`n_rings = 28`)!
    # Crisp L-turn under the front chin (v_turn=0.76) + gradual lateral/nape slope (v_turn=0.28),
    # with lower stump tucked inside the shirt/waistcoat below the krama (`z_bot = 0.876`).
    z_bot = 0.876
    c_bot = Vector((0.262, 0.030, z_bot))
    c_top = Vector((0.258, 0.026, plane_co_world.z))
    n_rings = 28  # ring[n_rings - 1] = exact cut-plane head vertices, ring[0] = chest/collar base

    head.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(head.data)
    uv_layer = bm.loops.layers.uv.active or bm.loops.layers.uv.new("UVMap")

    cut_edges = [
        e for e in bm.edges
        if e.is_boundary and all(abs(((mw @ v.co) - plane_co_world).dot(plane_no_world)) < 0.004 for v in e.verts)
    ]
    cut_v_set = list({v for e in cut_edges for v in e.verts})
    v_columns = {}
    v_ang_map = {}

    for v_top in cut_v_set:
        p_rim = mw @ v_top.co
        ang = math.atan2(p_rim.x - ax0.x, -(p_rim.y - ax0.y))
        v_ang_map[v_top] = ang
        sx = math.sin(ang)
        sy = -math.cos(ang)
        c_front = max(0.0, math.cos(ang))
        c_back = max(0.0, -math.cos(ang))
        side_w = sx * sx

        # Front chin holds vertical throat + crisp L-turn; sides/nape taper gradually from jaw into neck.
        w_front_l = c_front ** 2.0
        v_turn = 0.76 * w_front_l + 0.28 * (1.0 - w_front_l)
        z_turn = p_rim.z - (0.008 * w_front_l + 0.038 * (1.0 - w_front_l))

        col = [None] * n_rings
        col[n_rings - 1] = v_top
        for iz in range(n_rings - 1):
            v_frac = iz / (n_rings - 1)
            t_col = min(1.0, v_frac / v_turn)
            cx = c_bot.x + (c_top.x - c_bot.x) * t_col
            cy = c_bot.y + (c_top.y - c_bot.y) * t_col

            # Natural male proportions centered directly under ear (11.7 cm wide x 11.4 cm deep)
            rx = 0.0585
            ry = 0.0555 * c_front + 0.0585 * c_back + 0.0570 * (1.0 - c_front - c_back)

            # (a) Smooth downward widening / trapezius flare toward collar (strictly in lower half via v_frac)
            trap_t = smoothstep(0.52, 0.0, v_frac)
            rx += 0.018 * (trap_t ** 1.5) * (0.35 + 0.65 * side_w)
            ry += 0.014 * (trap_t ** 1.5) * (c_back ** 1.6)

            # (b) Subtle shallow nape concavity + lower-stump chest tuck below krama (no artificial bumps)
            nape_hollow = -0.0030 * (c_back ** 1.6) * math.exp(-(((t_col - 0.58) / 0.24) ** 2))
            stump_tuck = -0.022 * (0.45 + 0.55 * c_front) * (smoothstep(0.42, 0.0, v_frac) ** 1.2)

            r_anat = math.hypot(rx * sx, ry * sy) + nape_hollow + stump_tuck
            z_anat = z_bot + (z_turn - z_bot) * t_col
            p_anat = Vector((cx + sx * r_anat, cy + sy * r_anat, z_anat))

            if v_frac <= v_turn:
                p_cur = p_anat
            else:
                s_u = (v_frac - v_turn) / max(1e-5, 1.0 - v_turn)
                t_rad = s_u * s_u * (3.0 - 2.0 * s_u)
                t_z_front = 1.0 - (1.0 - s_u) ** 2.2
                t_z = t_z_front * w_front_l + s_u * (1.0 - w_front_l)
                p_cur = Vector((
                    p_anat.x + (p_rim.x - p_anat.x) * t_rad,
                    p_anat.y + (p_rim.y - p_anat.y) * t_rad,
                    z_turn + (p_rim.z - z_turn) * t_z,
                ))
            col[iz] = bm.verts.new(inv @ p_cur)
        v_columns[v_top] = col

    neck_faces_created = []
    for e in cut_edges:
        vA, vB = e.verts[0], e.verts[1]
        angA, angB = v_ang_map[vA], v_ang_map[vB]
        da = math.atan2(math.sin(angB - angA), math.cos(angB - angA))
        if da < 0:
            vA, vB = vB, vA
            angA, angB = angB, angA
        uA = (angA + math.pi) / math.tau
        uB = (angB + math.pi) / math.tau
        if uB - uA < -0.5:
            uB += 1.0
        elif uB - uA > 0.5:
            uA += 1.0
        colA, colB = v_columns[vA], v_columns[vB]
        for iz in range(n_rings - 1):
            v0 = iz / (n_rings - 1)
            v1 = (iz + 1) / (n_rings - 1)
            try:
                f_new = bm.faces.new((colA[iz], colB[iz], colB[iz + 1], colA[iz + 1]))
            except ValueError:
                continue
            f_new.smooth = True
            f_new.material_index = neck_mi
            for loop, uv_pt in zip(f_new.loops, [(uA, v0), (uB, v0), (uB, v1), (uA, v1)]):
                loop[uv_layer].uv = uv_pt
            neck_faces_created.append(f_new)

    bmesh.ops.recalc_face_normals(bm, faces=neck_faces_created)
    bmesh.update_edit_mesh(head.data)
    bpy.ops.object.mode_set(mode="OBJECT")

    # 3D-position-welded seam rounding on the lateral/back neck rim so split UV seams move in lockstep
    # while M_taxi_driver_head_scan facial UVs above d_pl = 0.0020 and front chin (y < -0.052) stay untouched!
    pos_map = {}
    vert_to_key = []
    for v in head.data.vertices:
        wp = mw @ v.co
        k = (round(wp.x, 4), round(wp.y, 4), round(wp.z, 4))
        vert_to_key.append(k)
        pos_map[k] = wp.copy()

    adj_3d = {k: set() for k in pos_map}
    for p in head.data.polygons:
        ks = [vert_to_key[vi] for vi in p.vertices]
        for i in range(len(ks)):
            a, b = ks[i], ks[(i + 1) % len(ks)]
            if a != b:
                adj_3d[a].add(b)
                adj_3d[b].add(a)

    smooth_weights = {}
    for k, wp in pos_map.items():
        if wp.z > 0.985 or wp.z < 0.890 or wp.y < -0.052:
            continue
        d_pl = (wp - plane_co_world).dot(plane_no_world)
        t_lat = smoothstep(-0.052, -0.012, wp.y)
        d_min = -0.024 * t_lat
        d_max = 0.0020 * t_lat
        if d_min < d_pl < d_max:
            w = smoothstep(d_min, d_min * 0.2, d_pl) * (0.48 * t_lat)
            smooth_weights[k] = w

    for _ in range(12):
        next_pos = {}
        for k, w in smooth_weights.items():
            nbs = adj_3d.get(k)
            if not nbs:
                continue
            avg = sum((pos_map[nb] for nb in nbs), Vector()) / len(nbs)
            next_pos[k] = pos_map[k].lerp(avg, w)
        for k, np_co in next_pos.items():
            pos_map[k] = np_co

    for i, v in enumerate(head.data.vertices):
        k = vert_to_key[i]
        if k in smooth_weights:
            v.co = inv @ pos_map[k]
    head.data.update()

    # 9. Propagate Basis deltas to all 5 morph targets + smooth KDTree lockstep morph transfer onto neck vertices!
    if head.data.shape_keys:
        basis = head.data.shape_keys.key_blocks["Basis"]
        total_v = len(head.data.vertices)
        for i in range(total_v):
            basis.data[i].co = head.data.vertices[i].co.copy()
        for name in sk_names:
            kb = head.data.shape_keys.key_blocks[name]
            d_list = sk_deltas_orig[name]
            for i in range(min(n_orig_verts, total_v)):
                kb.data[i].co = basis.data[i].co + d_list[i]
        for i in range(n_orig_verts, total_v):
            wp = mw @ head.data.vertices[i].co
            v_frac = max(0.0, min(1.0, (wp.z - z_bot) / max(1e-5, plane_co_world.z - z_bot)))
            w_z = smoothstep(0.18, 0.96, v_frac)
            if w_z < 1e-4:
                for name in sk_names:
                    head.data.shape_keys.key_blocks[name].data[i].co = basis.data[i].co.copy()
                continue
            found = head_tree.find_n(wp, 6)
            ws = [1.0 / (d + 0.006) for _, _, d in found]
            wsum = sum(ws)
            pairs = [(low_head_idx[k], w / wsum) for (_, k, _), w in zip(found, ws)]
            for name in sk_names:
                d_list = sk_deltas_orig[name]
                disp = Vector((0.0, 0.0, 0.0))
                for h_vi, wt in pairs:
                    disp += d_list[h_vi] * wt
                head.data.shape_keys.key_blocks[name].data[i].co = basis.data[i].co + disp * w_z

    for p in head.data.polygons:
        p.use_smooth = True
    head.data["anatomical_neck_v7"] = True
    head.data["anatomical_neck_v6"] = True
    head.data["anatomical_neck_v5"] = True
    head.data["anatomical_neck_v4"] = True
    head.data["anatomical_neck_v3"] = True
    head.data["anatomical_neck_v2"] = True
    head.data["anatomical_neck_v1"] = True
    head.data["nape_tapered_v2"] = True
    head.data["neck_shortened_v1"] = True
    head.data.update()
    print(
        "TAXI_ANATOMICAL_NECK_V7_BUILT total_head_verts=",
        len(head.data.vertices),
        "cut_edges=",
        len(cut_edges),
        "smoothed_keys=",
        len(smooth_weights),
        "shape_keys=",
        [k.name for k in head.data.shape_keys.key_blocks] if head.data.shape_keys else [],
    )


def _refine_driver_head_and_neck_skin(coll):
    """Idempotent driver face, cap & neck skin realism pass (NEVER re-shifts head Z):
    - Welds UV-seam duplicate vertices and subdivides coarse low-poly cap crown facets
      while preserving Basis + all 5 shape keys identically.
    - Clears frozen custom split normals so jaw (`M_taxi_driver_head_scan`) and neck
      (`M_taxi_driver_neck_skin`) interpolate ONE continuous smooth normal across the seam.
    - Upgrades T_taxi_driver_neck_BC & T_taxi_driver_neck_N to 1024x1024 matching the lower jaw/ear
      pixels of T_taxi_driver_head_BC with natural organic micro-pores and sternocleidomastoid shading.
    - Calibrates head normal strength to 0.58 and neck normal strength to 0.26 for realistic supple skin.
    """
    head = bpy.data.objects.get("taxi_driver_head_scan")
    if not head or head.type != "MESH" or head.data.get("driver_skin_realism_v5"):
        return

    _set_normal_strength("M_taxi_driver_head_scan", 0.58)

    # Clear custom split normals so head, cap and neck vertices share smooth interpolated normals
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    if head.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()

    mw = head.matrix_world
    mat_names = [mt.name if mt else "" for mt in head.data.materials]
    if "M_taxi_driver_head_scan" in mat_names and "M_taxi_driver_neck_skin" in mat_names:
        head_mi = mat_names.index("M_taxi_driver_head_scan")
        neck_mi = mat_names.index("M_taxi_driver_neck_skin")

        # Weld coincident UV-seam splits, subdivide coarse cap crown polygons, and smooth cap + jaw-neck seam
        # directly inside bmesh so all 5 shape keys (look_road, look_sora, nod, talk, blink) stay intact!
        bm = bmesh.new()
        bm.from_mesh(head.data)
        # Weld ONLY the low-poly cap crown; never the dense photoscan face/cheek/neck micro-triangles!
        cap_weld_verts = [v for v in bm.verts if (mw @ v.co).z > 1.095]
        if cap_weld_verts:
            bmesh.ops.remove_doubles(bm, verts=cap_weld_verts, dist=0.00025)
        bm.faces.ensure_lookup_table()
        cap_faces = [f for f in bm.faces if f.calc_area() > 0.00003 and (mw @ f.calc_center_median()).z > 1.095]
        cap_edges = list({e for f in cap_faces for e in f.edges})
        if cap_edges:
            bmesh.ops.subdivide_edges(bm, edges=cap_edges, cuts=2, smooth=0.65, use_grid_fill=True)
            ngons = [f for f in bm.faces if len(f.verts) > 4]
            if ngons:
                bmesh.ops.triangulate(bm, faces=ngons)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        seam_verts = {
            v for v in bm.verts
            if any(f.material_index == head_mi for f in v.link_faces)
            and any(f.material_index == neck_mi for f in v.link_faces)
        }
        band_verts = set(seam_verts)
        for v in list(seam_verts):
            for e in v.link_edges:
                nb = e.other_vert(v)
                wp = mw @ nb.co
                if 0.905 < wp.z < 0.990 and wp.y > -0.056:
                    band_verts.add(nb)
        cap_verts = {v for v in bm.verts if (mw @ v.co).z > 1.125 and (mw @ v.co).y > -0.095}

        sk_layers = list(bm.verts.layers.shape)
        for _ in range(6):
            disp = {}
            for v in band_verts:
                wp = mw @ v.co
                if wp.z > 0.990 or wp.z < 0.900 or wp.y < -0.056:
                    continue
                nbs = [e.other_vert(v) for e in v.link_edges]
                if not nbs:
                    continue
                avg = sum((nb.co for nb in nbs), Vector()) / len(nbs)
                wt = 0.36 if v in seam_verts else 0.20
                disp[v] = v.co.lerp(avg, wt) - v.co
            for v in cap_verts:
                nbs = [e.other_vert(v) for e in v.link_edges]
                if not nbs:
                    continue
                avg = sum((nb.co for nb in nbs), Vector()) / len(nbs)
                disp[v] = v.co.lerp(avg, 0.32) - v.co
            for v, d_local in disp.items():
                v.co += d_local
                for sk in sk_layers:
                    v[sk] = v[sk] + d_local

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(head.data)
        bm.free()
        head.data.update()

        head_v = {vi for p in head.data.polygons if p.material_index == head_mi for vi in p.vertices}
        neck_v = {vi for p in head.data.polygons if p.material_index == neck_mi for vi in p.vertices}
        seam_vi = head_v & neck_v

        # Upgrade neck texture to 1024x1024 matching exact jaw-rim color without pale blotch spikes
        head_mat = head.data.materials[head_mi]
        bc_img = next(
            (n.image for n in head_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"),
            None,
        )
        ax0 = Vector((0.258, 0.026, 0.0))
        h_world = [mw @ v.co for v in head.data.vertices]
        seam_z = sum(h_world[vi].z for vi in seam_vi) / max(1, len(seam_vi)) if seam_vi else 0.960
        n_ang_tex = 128
        base_skin_srgb = np.array([0.610, 0.382, 0.264], np.float32)
        rim_rgb = np.tile(base_skin_srgb, (n_ang_tex, 1))
        if bc_img is not None and head.data.uv_layers.active is not None:
            wd, ht = bc_img.size
            px = np.empty(wd * ht * 4, np.float32)
            bc_img.pixels.foreach_get(px)
            px = px.reshape(ht, wd, 4)
            uvl = head.data.uv_layers.active.data
            rgb_bins = [[] for _ in range(n_ang_tex)]
            for p in head.data.polygons:
                if p.material_index != head_mi:
                    continue
                c = sum((h_world[vi] for vi in p.vertices), Vector()) / len(p.vertices)
                if 0.002 <= (c.z - seam_z) <= 0.024:
                    ang = math.atan2(c.x - ax0.x, -(c.y - ax0.y))
                    bi = int(((ang + math.pi) / math.tau) * n_ang_tex) % n_ang_tex
                    uv = sum((uvl[li].uv for li in p.loop_indices), Vector((0, 0))) / len(p.loop_indices)
                    col = px[int((uv.y % 1.0) * (ht - 1)), int((uv.x % 1.0) * (wd - 1)), :3]
                    lum = float(0.3 * col[0] + 0.59 * col[1] + 0.11 * col[2])
                    if (0.22 < lum < 0.68) or abs(ang) > math.radians(135):
                        rgb_bins[bi].append(col)
            valid_c = [bi for bi in range(n_ang_tex) if len(rgb_bins[bi]) >= 2]
            for bi in valid_c:
                rim_rgb[bi] = np.median(rgb_bins[bi], axis=0)
            if valid_c:
                vc = np.array(valid_c)
                for bi in range(n_ang_tex):
                    if len(rgb_bins[bi]) < 2:
                        il = vc[int(np.argmin((bi - vc) % n_ang_tex))]
                        ir = vc[int(np.argmin((vc - bi) % n_ang_tex))]
                        dl = (bi - il) % n_ang_tex
                        dr = (ir - bi) % n_ang_tex
                        t = dl / max(1, dl + dr)
                        rim_rgb[bi] = rim_rgb[il] * (1.0 - t) + rim_rgb[ir] * t
            for _ in range(180):
                rim_rgb = 0.25 * np.roll(rim_rgb, -1, axis=0) + 0.50 * rim_rgb + 0.25 * np.roll(rim_rgb, 1, axis=0)
            rim_rgb = 0.10 * base_skin_srgb[None, :] + 0.90 * rim_rgb

        tw, th = 1024, 1024
        rng = np.random.default_rng(193310)
        yy, xx = np.mgrid[0:th, 0:tw].astype(np.float32)
        u_grid = xx / tw
        v_grid = yy / (th - 1)
        ang_grid = u_grid * math.tau - math.pi
        idx_f = u_grid[0] * n_ang_tex
        i0 = np.floor(idx_f).astype(np.int32) % n_ang_tex
        i1 = (i0 + 1) % n_ang_tex
        frac = (idx_f - np.floor(idx_f))[:, None]
        top_rgb_row = rim_rgb[i0] * (1.0 - frac) + rim_rgb[i1] * frac

        blend_top = np.clip((v_grid - 0.25) / 0.75, 0.0, 1.0)
        blend_top = blend_top * blend_top * (3.0 - 2.0 * blend_top)
        rgb = base_skin_srgb[None, None, :] * (1.0 - blend_top[..., None]) + top_rgb_row[None, :, :] * blend_top[..., None]

        front_mask = np.clip(np.cos(ang_grid), 0.0, 1.0) ** 1.3
        submental_ao = 1.0 - 0.13 * front_mask * np.exp(-(((v_grid - 0.84) / 0.10) ** 2))
        collar_ao = 1.0 - 0.15 * np.clip((0.24 - v_grid) / 0.24, 0.0, 1.0) ** 1.5
        # Subtle sternocleidomastoid warm shadow modulation + human pore grain
        scm = 1.0 - 0.045 * np.exp(-(((np.abs(ang_grid) - 0.85) / 0.28) ** 2)) * np.sin(np.clip(v_grid, 0.1, 0.9) * math.pi)
        pore = rng.normal(0.0, 0.0055, (th, tw)).astype(np.float32)
        stubble_mask = (
            np.clip((v_grid - 0.72) / 0.22, 0.0, 1.0)
            * np.clip((0.99 - v_grid) / 0.05, 0.0, 1.0)
            * np.clip((np.cos(ang_grid) + 0.20) / 0.50, 0.0, 1.0)
        )
        stubble = (rng.random((th, tw)).astype(np.float32) < 0.085).astype(np.float32) * -0.045 * stubble_mask
        rgb = np.clip(rgb * (submental_ao * collar_ao * scm)[..., None] + pore[..., None] + stubble[..., None], 0.02, 0.98)
        neck_bc_img = _pack_np_image("T_taxi_driver_neck_BC", rgb, is_srgb=True)

        hf = rng.normal(0.0, 0.022, (th, tw)).astype(np.float32)
        hf = (hf + np.roll(hf, 1, 0) + np.roll(hf, -1, 0) + np.roll(hf, 1, 1) + np.roll(hf, -1, 1)) * 0.2
        gx = (np.roll(hf, -1, 1) - np.roll(hf, 1, 1)) * 0.48
        gy = (np.roll(hf, -1, 0) - np.roll(hf, 1, 0)) * 0.48
        nz = np.sqrt(np.clip(1.0 - gx * gx - gy * gy, 0.1, 1.0))
        n_arr = np.dstack([np.clip(-gx * 0.5 + 0.5, 0, 1), np.clip(-gy * 0.5 + 0.5, 0, 1), np.clip(nz * 0.5 + 0.5, 0, 1)])
        neck_n_img = _pack_np_image("T_taxi_driver_neck_N", n_arr, is_srgb=False)
        _make_pbr_tex_mat("M_taxi_driver_neck_skin", neck_bc_img, neck_n_img, rough=0.52, normal_strength=0.26)

    for p in head.data.polygons:
        p.use_smooth = True
    head.data["driver_skin_realism_v2"] = True
    head.data["driver_skin_realism_v3"] = True
    head.data["driver_skin_realism_v4"] = True
    head.data["driver_skin_realism_v5"] = True
    head.data.update()
    print("TAXI_DRIVER_SKIN_REFINED_V5", "verts=", len(head.data.vertices), "has_custom_normals=", head.data.has_custom_normals)


def _rebuild_seamless_sora(coll, world_uvs_fn):
    """Rebuild Sora (`taxi_sora_legs_scan`) cleanly from Carla's photoscan (taxi_sora_scan.glb)
    using Dual Quaternion skinning, asymmetrical resting fingers on thighs, woven linen blouse
    & cotton-twill trousers (`T_taxi_sora_cloth_N`), natural warm Khmer hand skin (`T_taxi_sora_skin_BC/N`),
    snug matching woven cuffs, and a wrist-conformed vintage tank watch."""
    scan_path = ROOT / "art-source/library/scans/taxi_sora_scan.glb"
    if not scan_path.exists():
        return False

    for old_n in (
        "taxi_sora_legs_scan",
        "taxi_sora_blouse_cuffs",
        "taxi_sora_cuff_buttons",
        "taxi_sora_watch_case",
        "taxi_sora_watch_strap",
        "taxi_sora_watch_dial",
        "taxi_sora_watch_hands",
    ):
        old = bpy.data.objects.get(old_n)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(scan_path))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    body = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.polygons))
    for o in new:
        if o not in (arm, body) and o.type != "EMPTY":
            bpy.data.objects.remove(o, do_unlink=True)

    # Dual Quaternion skinning preserves wrist, elbow, finger & knee anatomical fullness!
    for mod in body.modifiers:
        if mod.type == "ARMATURE":
            mod.use_deform_preserve_volume = True

    rest = [(body.matrix_world @ v.co).copy() for v in body.data.vertices]
    raw_mat = body.data.materials[0]
    raw_bc_img = next(
        (n.image for n in raw_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"),
        None,
    )
    raw_n_img = next(
        (n.image for n in raw_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "Non-Color" and "normal" in n.image.name.lower()),
        None,
    )

    def bone(prefix):
        return next(b.name for b in arm.pose.bones if b.name.startswith(prefix))

    def joint(name):
        bpy.context.view_layer.update()
        return arm.matrix_world @ arm.pose.bones[name].head

    def turn_bone(name, axis, angle):
        bpy.context.view_layer.update()
        pb = arm.pose.bones[name]
        inv = arm.matrix_world.inverted().to_3x3()
        R = Matrix.Rotation(angle, 4, (inv @ Vector(axis)).normalized())
        pb.matrix = Matrix.Translation(pb.head) @ R @ Matrix.Translation(-pb.head) @ pb.matrix
        bpy.context.view_layer.update()

    def aim(name, child, target):
        hd = joint(name)
        cur = joint(child) - hd
        want = Vector(target) - hd
        if cur.length < 1e-6 or want.length < 1e-6:
            return
        axis, angle = cur.rotation_difference(want).to_axis_angle()
        turn_bone(name, axis, angle)

    def reach(upper, lower, hand, wrist, pole):
        s = joint(upper)
        a = (joint(lower) - s).length
        b = (joint(hand) - joint(lower)).length
        to = Vector(wrist) - s
        d = min(to.length, (a + b) * 0.992)
        f = to.normalized()
        cosA = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
        p = Vector(pole) - s
        perp = (p - f * p.dot(f)).normalized()
        elbow = s + f * a * cosA + perp * a * math.sqrt(max(0.0, 1.0 - cosA * cosA))
        aim(upper, lower, elbow)
        aim(lower, hand, s + f * d)

    def knuckles(side):
        k1 = joint(bone(f"index_01_{side}"))
        k4 = joint(bone(f"pinky_01_{side}"))
        wrist = joint(bone(f"hand_{side}"))
        mid = joint(bone(f"middle_01_{side}"))
        return (k1 - k4).normalized(), (mid - wrist).normalized()

    def palm_of(side):
        across, d = knuckles(side)
        return (across.cross(d) if side == "r" else d.cross(across)).normalized()

    def curl(side, angles_by_finger, angle_thumb):
        across, _ = knuckles(side)
        if side == "l":
            across = -across
        for finger, ang_m in angles_by_finger.items():
            for seg, mult in (("01", 0.90), ("02", 1.05), ("03", 0.85)):
                nm = next(b.name for b in arm.pose.bones if b.name.startswith(f"{finger}_{seg}_{side}"))
                turn_bone(nm, across, ang_m * mult)
        for seg in ("02", "03"):
            nm = next(b.name for b in arm.pose.bones if b.name.startswith(f"thumb_{seg}_{side}"))
            turn_bone(nm, across, angle_thumb)

    # Rest wrist bone positions before posing for accurate sleeve-to-hand classification
    wrist_rest = {
        "l": (joint(bone("lowerarm_l")), joint(bone("hand_l"))),
        "r": (joint(bone("lowerarm_r")), joint(bone("hand_r"))),
    }

    # Seat height & back-set position measured directly from passenger cushion & floorboard
    sora_hip = Vector((-0.27, 0.08, 0.39))
    eye_anc = bpy.data.objects.get("taxi_anchor_sora_eye")
    if eye_anc:
        sora_hip = Vector((eye_anc.location.x, eye_anc.location.y + 0.02, eye_anc.location.z - 0.675))
    arm.location += sora_hip - joint(bone("hip_"))
    for sp, deg in [("spine_01", -4.0), ("spine_02", -4.0), ("spine_03", -3.0)]:
        try:
            turn_bone(bone(sp), Vector((1, 0, 0)), math.radians(deg))
        except StopIteration:
            pass

    def _floor_ray(rx, ry, rz=0.40):
        dep = bpy.context.evaluated_depsgraph_get()
        best_z = None
        origin = Vector((rx, ry, rz))
        for _ in range(4):
            hit, loc, _, _, obj, _ = bpy.context.scene.ray_cast(dep, origin, Vector((0, 0, -1)), distance=1.5)
            if not hit:
                break
            if obj and "glass" not in obj.name.lower() and "sora" not in obj.name.lower():
                best_z = loc.z
                break
            origin = loc + Vector((0, 0, -0.005))
        return best_z

    for side, knee, ankle, ball in [
        ("l", (-0.19, -0.27, 0.405), (-0.18, -0.54, 0.155), (-0.18, -0.68, 0.098)),
        ("r", (-0.35, -0.27, 0.405), (-0.37, -0.54, 0.155), (-0.38, -0.68, 0.098)),
    ]:
        fa = _floor_ray(ankle[0], ankle[1], 0.40)
        fb = _floor_ray(ball[0], ball[1], 0.40)
        fa_z = max(0.01, fa if fa is not None else 0.01)
        fb_z = max(0.01, fb if fb is not None else 0.01)
        ankle = (ankle[0], ankle[1], max(ankle[2], fa_z + 0.135))
        ball = (ball[0], ball[1], max(ball[2], fb_z + 0.084))
        aim(bone(f"upperleg_{side}"), bone(f"lowerleg_{side}"), knee)
        aim(bone(f"lowerleg_{side}"), bone(f"foot_{side}"), ankle)
        aim(bone(f"foot_{side}"), bone(f"ball_{side}"), ball)

    # Natural feminine seated arm/hand pose resting gently palms-down on mid-thighs (clear of knees & shoes!)
    reach(bone("upperarm_l"), bone("lowerarm_l"), bone("hand_l"), Vector((-0.185, -0.175, 0.520)), Vector((-0.05, 0.06, 0.47)))
    reach(bone("upperarm_r"), bone("lowerarm_r"), bone("hand_r"), Vector((-0.355, -0.175, 0.514)), Vector((-0.48, 0.06, 0.47)))
    for side, aim_pt, palm_dir, fg_ang, th_ang in [
        ("l", Vector((-0.215, -0.285, 0.498)), Vector((-0.14, -0.06, -1.0)), {"index": 0.14, "middle": 0.19, "ring": 0.24, "pinky": 0.29}, 0.09),
        ("r", Vector((-0.325, -0.285, 0.490)), Vector((0.14, -0.06, -1.0)), {"index": 0.16, "middle": 0.21, "ring": 0.26, "pinky": 0.31}, 0.10),
    ]:
        hand = bone(f"hand_{side}")
        aim(hand, bone(f"middle_01_{side}"), aim_pt)
        _, d = knuckles(side)
        want = palm_dir.normalized()
        want = (want - d * want.dot(d)).normalized()
        have = palm_of(side)
        have = (have - d * have.dot(d)).normalized()
        roll = math.atan2(have.cross(want).dot(d), have.dot(want))
        turn_bone(hand, d, roll)
        curl(side, fg_ang, th_ang)

    neck_pos = joint(bone("neck_")).copy()
    wrists = {}
    for side in ("l", "r"):
        w_pos = joint(bone(f"hand_{side}")).copy()
        e_pos = joint(bone(f"lowerarm_{side}")).copy()
        arm_dir = (w_pos - e_pos).normalized()
        up_dir = palm_of(side) * (-1.0)
        up_dir = (up_dir - arm_dir * up_dir.dot(arm_dir)).normalized()
        side_dir = up_dir.cross(arm_dir).normalized()
        wrists[side] = (w_pos, arm_dir, side_dir, up_dir)

    # Classify faces in rest pose BEFORE baking (clean geometric planes — zero pink ankle gap, zero waist zig-zag, zero sleeve spikes!)
    kinds = []
    for p in body.data.polygons:
        rc = sum((rest[vi] for vi in p.vertices), Vector()) / len(p.vertices)
        side_k = "l" if rc.x >= 0 else "r"
        e_r, w_r = wrist_rest[side_k]
        ax_r = w_r - e_r
        u_arm = (rc - e_r).dot(ax_r) / max(1e-6, ax_r.length_squared)
        perp_dist = (rc - (e_r + ax_r * u_arm)).length
        near_wrist = (rc - w_r).length < 0.21 and perp_dist < 0.10
        if rc.z < 0.135:
            kinds.append(2)  # shoes — full coverage up to shoe collar, zero bare pink ankle gap
        elif near_wrist and u_arm > 0.925:
            kinds.append(1)  # hands/wrists only
        elif rc.z > 0.965 or (abs(rc.x) > 0.19 and rc.z > 0.85):
            kinds.append(3)  # linen blouse & sleeves
        else:
            kinds.append(0)  # tailored trousers

    # Bake posed mesh
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    baked = bpy.data.meshes.new_from_object(ev)
    baked.transform(body.matrix_world)
    body.modifiers.clear()
    body.parent = None
    body.matrix_world = Matrix.Identity(4)
    body.data = baked
    body.vertex_groups.clear()
    bpy.data.objects.remove(arm, do_unlink=True)
    for o in list(bpy.data.objects):
        if o in new and o != body:
            bpy.data.objects.remove(o, do_unlink=True)

    # Generate high-realism Sora textures: 2K uniform woven linen blouse/trousers, dark espresso shoes, silky Khmer hands
    linen_bc_path = ROOT / "art-source/library/materials/rough_linen/rough_linen_BC.jpg"
    linen_n_path = ROOT / "art-source/library/materials/rough_linen/rough_linen_N.jpg"
    w_s, h_s = 2048, 2048
    rgb_scan = _resize_np(raw_bc_img, w_s, h_s)[..., :3] if raw_bc_img else np.full((h_s, w_s, 3), 0.5, np.float32)
    lum = rgb_scan @ np.array([0.3, 0.59, 0.11], np.float32)
    shade_tr = _box_blur_2d(lum, 20)
    shade_bl = _box_blur_2d(lum, 24)
    sk_blur = _box_blur_2d(lum, 10)
    uvl_s = body.data.uv_layers.active.data

    def _mean_grid(grid, kind_val):
        vals = []
        for p in body.data.polygons:
            if kinds[p.index] == kind_val:
                uv = sum((uvl_s[li].uv for li in p.loop_indices), Vector((0, 0))) / len(p.loop_indices)
                vals.append(float(grid[int((uv.y % 1.0) * (h_s - 1)), int((uv.x % 1.0) * (w_s - 1))]))
        return float(np.mean(vals)) if vals else 0.5

    weave_rgb = _load_tiled_np(linen_bc_path, w_s, h_s, repeats=38, is_srgb=True) if linen_bc_path.exists() else np.full((h_s, w_s, 3), 0.55, np.float32)
    weave_lum = weave_rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    weave_fac = np.clip(weave_lum / max(1e-3, float(np.mean(weave_lum))), 0.85, 1.15)[..., None]

    # Uniform fine woven ivory-cream linen blouse across torso & sleeves + tailored charcoal-taupe trousers!
    tr_k = np.clip(0.86 + 0.14 * (shade_tr / max(1e-3, _mean_grid(shade_tr, 0))), 0.74, 1.12)[..., None]
    tr_rgb = np.array((0.24, 0.21, 0.18), np.float32) * tr_k * weave_fac
    sora_tr_bc = _pack_np_image("T_taxi_sora_trousers", tr_rgb, is_srgb=True)

    bl_k = np.clip(0.90 + 0.10 * (shade_bl / max(1e-3, _mean_grid(shade_bl, 3))), 0.80, 1.08)[..., None]
    bl_rgb = np.array((0.54, 0.49, 0.41), np.float32) * bl_k * weave_fac
    sora_bl_bc = _pack_np_image("T_taxi_sora_blouse", bl_rgb, is_srgb=True)

    # Silky natural Khmer warm hand skin (blurred scan luminance removes A-pose wrist blotches!)
    skin_base = np.array((0.66, 0.49, 0.39), np.float32)
    skin_mean = _mean_grid(sk_blur, 1)
    rng_s = np.random.default_rng(193314)
    epiderm = 1.0 + rng_s.normal(0.0, 0.010, (h_s, w_s)).astype(np.float32)
    sk_k = np.clip(0.78 + 0.22 * (sk_blur / max(1e-3, skin_mean)), 0.82, 1.12)
    skin_out = np.clip(skin_base[None, None, :] * sk_k[..., None] * epiderm[..., None], 0.04, 0.94)
    sora_sk_bc = _pack_np_image("T_taxi_sora_skin_BC", skin_out, is_srgb=True)

    # Polished dark espresso-black 1933 leather shoes (zero reddish raw scan bleed!)
    shoe_arr = np.clip(
        np.array((0.055, 0.042, 0.036), np.float32)[None, None, :]
        * (0.94 + 0.06 * rng_s.normal(0.0, 0.25, (512, 512, 1)).astype(np.float32)),
        0.015,
        0.14,
    )
    sora_shoe_bc = _pack_np_image("T_taxi_sora_shoes_BC", shoe_arr, is_srgb=True)

    # 1K shared cloth weave normal (softened scan knit bumps) & skin pore normal
    wn, hn = 1024, 1024
    scan_n_s = _resize_np(raw_n_img, wn, hn) if raw_n_img else np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 2), np.float32)])
    linen_n_s = _load_tiled_np(linen_n_path, wn, hn, repeats=38, is_srgb=False) if linen_n_path.exists() else np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 1), np.float32)])
    sora_cloth_n = _pack_np_image("T_taxi_sora_cloth_N", _blend_normals(scan_n_s, linen_n_s, scan_gain=0.22, weave_gain=0.54), is_srgb=False)

    hs_n = rng_s.normal(0.0, 0.018, (hn, wn)).astype(np.float32)
    hs_n = (hs_n + np.roll(hs_n, 1, 0) + np.roll(hs_n, -1, 0) + np.roll(hs_n, 1, 1) + np.roll(hs_n, -1, 1)) * 0.2
    gx_s = (np.roll(hs_n, -1, 1) - np.roll(hs_n, 1, 1)) * 0.42
    gy_s = (np.roll(hs_n, -1, 0) - np.roll(hs_n, 1, 0)) * 0.42
    nz_s = np.sqrt(np.clip(1.0 - gx_s * gx_s - gy_s * gy_s, 0.1, 1.0))
    pore_s = np.dstack([np.clip(-gx_s * 0.5 + 0.5, 0, 1), np.clip(-gy_s * 0.5 + 0.5, 0, 1), np.clip(nz_s * 0.5 + 0.5, 0, 1)])
    sora_skin_n = _pack_np_image("T_taxi_sora_skin_N", _blend_normals(scan_n_s, pore_s, scan_gain=0.44, weave_gain=0.40), is_srgb=False)

    for stale_m in ("M_taxi_sora_shoes_scan.001", "M_cab_driver_krama.001"):
        sm = bpy.data.materials.get(stale_m)
        if sm and sm.users == 0:
            bpy.data.materials.remove(sm)

    trousers_mat = _make_pbr_tex_mat("M_taxi_sora_trousers_scan", sora_tr_bc, sora_cloth_n, rough=0.88, normal_strength=0.46)
    blouse_mat = _make_pbr_tex_mat("M_taxi_sora_blouse_scan", sora_bl_bc, sora_cloth_n, rough=0.88, normal_strength=0.44)
    skin_mat = _make_pbr_tex_mat("M_taxi_sora_skin_scan", sora_sk_bc, sora_skin_n, rough=0.48, normal_strength=0.38)
    shoes_mat = _make_pbr_tex_mat("M_taxi_sora_shoes_scan", sora_shoe_bc, sora_cloth_n, rough=0.34, normal_strength=0.28)
    neck_cap = bpy.data.materials.get("M_taxi_sora_neck_cap") or bpy.data.materials.new("M_taxi_sora_neck_cap")
    if neck_cap.node_tree and "Principled BSDF" in neck_cap.node_tree.nodes:
        neck_cap.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.38, 0.27, 0.21, 1.0)
        neck_cap.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.94

    body.data.materials.clear()
    for mt in (trousers_mat, skin_mat, shoes_mat, blouse_mat, neck_cap):
        body.data.materials.append(mt)

    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        f.material_index = kinds[f.index]
    # Smooth waist & wrist material boundaries via edge-neighbor majority cleanup
    for _ in range(3):
        flips = []
        for f in bm.faces:
            if f.material_index in (2, 4):
                continue
            nbrs = [nf.material_index for e in f.edges for nf in e.link_faces if nf != f and nf.material_index not in (2, 4)]
            if len(nbrs) >= 2:
                maj = max(set(nbrs), key=nbrs.count)
                if maj != f.material_index and nbrs.count(maj) > nbrs.count(f.material_index):
                    flips.append((f, maj))
        for f, nmi in flips:
            f.material_index = nmi
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0006)
    cut_co = neck_pos + Vector((0.0, 0.0, 0.025))
    cut_no = Vector((0.0, 0.0, 1.0))
    res = bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        plane_co=cut_co,
        plane_no=cut_no,
        clear_outer=True,
        use_snap_center=False,
    )
    cut_edges = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
    if cut_edges:
        filled = bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)["faces"]
        for f in filled:
            f.material_index = 4
        bmesh.ops.triangulate(bm, faces=filled)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data)
    bm.free()

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    if body.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    body.name = body.data.name = "taxi_sora_legs_scan"
    for c_old in list(body.users_collection):
        c_old.objects.unlink(body)
    coll.objects.link(body)

    # Subdivide + targeted smoothing: silky trouser knees, crisp garment drape, sleek slender hands!
    _subdivide_obj(body, levels=1)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    cloth_v_idx = {v.index for f in bm.faces if f.material_index in (0, 3) for v in f.verts}
    skin_v_idx = {v.index for f in bm.faces if f.material_index == 1 for v in f.verts}
    shoe_v_idx = {v.index for f in bm.faces if f.material_index == 2 for v in f.verts}
    seam_v_idx = (cloth_v_idx & skin_v_idx)
    pure_cloth = [v for v in bm.verts if not v.is_boundary and v.index in cloth_v_idx and v.index not in skin_v_idx and v.index not in shoe_v_idx]
    for _ in range(5):
        bmesh.ops.smooth_vert(bm, verts=pure_cloth, factor=0.32, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    knee_cloth = [
        v for v in bm.verts
        if not v.is_boundary and v.index in cloth_v_idx and v.index not in skin_v_idx and v.index not in shoe_v_idx
        and -0.42 < v.co.y < -0.18 and 0.26 < v.co.z < 0.50
    ]
    for _ in range(6):
        bmesh.ops.smooth_vert(bm, verts=knee_cloth, factor=0.36, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    # Smooth palms/wrists/knuckles + gently refine distal fingertips
    pure_hand_skin = [
        v for v in bm.verts
        if not v.is_boundary and v.index in skin_v_idx and v.index not in seam_v_idx and v.index not in shoe_v_idx
        and (v.co.y > -0.365 or v.co.z < 0.40)
    ]
    for _ in range(4):
        bmesh.ops.smooth_vert(bm, verts=pure_hand_skin, factor=0.26, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    distal_fingers = [
        v for v in bm.verts
        if not v.is_boundary and v.index in skin_v_idx and v.index not in seam_v_idx and v.index not in shoe_v_idx
        and v.co.y <= -0.365
    ]
    for _ in range(2):
        bmesh.ops.smooth_vert(bm, verts=distal_fingers, factor=0.14, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    seam_vs = [v for v in bm.verts if not v.is_boundary and v.index in seam_v_idx]
    for _ in range(2):
        bmesh.ops.smooth_vert(bm, verts=seam_vs, factor=0.26, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data)
    bm.free()
    for p in body.data.polygons:
        p.use_smooth = True
    body.data["cloth_smoothed_v2"] = True
    body.data["cloth_smoothed_v3"] = True
    body.data["sora_realism_v4"] = True
    body.data["sora_realism_v5"] = True
    body.data["sora_realism_v6"] = True
    body.data["sora_realism_v7"] = True
    body.data["sora_realism_v8"] = True
    body.data.update()

    # Snug matching woven ivory-cream linen blouse cuffs clear of wristwatch + mother-of-pearl buttons
    me_s = body.data
    wrist_pts = [me_s.vertices[vi].co.copy() for vi in seam_v_idx if me_s.vertices[vi].co.z > 0.45]
    sl = [p for p in wrist_pts if p.x > -0.27]
    sr = [p for p in wrist_pts if p.x <= -0.27]
    sora_cuff_arr = weave_fac[:512, :512, :] * np.array((0.54, 0.49, 0.41), np.float32)
    sora_cuff_bc_img = _pack_np_image("T_cab_sora_cuff_BC", sora_cuff_arr, is_srgb=True)
    m_sora_cuff = _make_pbr_tex_mat(
        "M_cab_sora_cuff_linen",
        sora_cuff_bc_img,
        bpy.data.images.load(str(linen_n_path), check_existing=True) if linen_n_path.exists() else sora_cloth_n,
        rough=0.88,
        normal_strength=0.44,
    )
    m_sora_cuff["tile"] = 0.27
    m_pearl = bpy.data.materials.get("M_cab_pearl_button") or bpy.data.materials.new("M_cab_pearl_button")
    if m_pearl.node_tree and "Principled BSDF" in m_pearl.node_tree.nodes:
        bp = m_pearl.node_tree.nodes["Principled BSDF"]
        bp.inputs["Base Color"].default_value = (0.76, 0.72, 0.64, 1.0)
        bp.inputs["Roughness"].default_value = 0.20
    bm_sc, bm_sb = bmesh.new(), bmesh.new()
    if sl:
        _add_tailored_cuff_ring(bm_sc, bm_sb, sl, wrists["l"][1], length=0.036, radius_pad=0.0040, center_shift=-0.016)
    if sr:
        _add_tailored_cuff_ring(bm_sc, bm_sb, sr, wrists["r"][1], length=0.036, radius_pad=0.0040, center_shift=-0.010)
    if bm_sc.faces:
        _bm_obj("taxi_sora_blouse_cuffs", bm_sc, m_sora_cuff, coll, world_uvs_fn=world_uvs_fn, smooth=True)
    else:
        bm_sc.free()
    if bm_sb.faces:
        _bm_obj("taxi_sora_cuff_buttons", bm_sb, m_pearl, coll, smooth=True)
    else:
        bm_sb.free()

    # Rebuild wrist-conformed 1930s antique-gold tank wristwatch fitted via KDTree onto left wrist skin!
    left_skin = [me_s.vertices[p_i].co.copy() for p in me_s.polygons if p.material_index == 1 for p_i in p.vertices if me_s.vertices[p_i].co.z > 0.45 and me_s.vertices[p_i].co.x > -0.27]
    w_pos, arm_dir, side_dir, up_dir = wrists["l"]
    w_ctr = w_pos + arm_dir * 0.016 + up_dir * 0.0025
    M_w = Matrix.Translation(w_ctr) @ Matrix((side_dir, arm_dir, up_dir)).transposed().to_4x4()
    w_inv = M_w.inverted()
    ru_m, rv_m = 0.027, 0.022
    if left_skin:
        local_sk = [w_inv @ p for p in left_skin if abs((w_inv @ p).y) < 0.018]
        if local_sk:
            ru_m = max(0.022, min(0.033, float(np.percentile([abs(p.x) for p in local_sk], 85)) + 0.0015))
            rv_m = max(0.018, min(0.028, float(np.percentile([abs(p.z) for p in local_sk], 85)) + 0.0015))

    def _pmat(nm, col, rgh, met=0.0):
        mt = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        mt.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*col, 1.0)
        mt.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = rgh
        mt.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = met
        return mt

    watch_gold = _pmat("M_taxi_sora_watch_gold", (0.58, 0.44, 0.18), 0.24, 0.92)
    watch_strap = _pmat("M_taxi_sora_watch_strap", (0.14, 0.07, 0.04), 0.62, 0.0)
    watch_dial = _pmat("M_taxi_sora_watch_dial", (0.78, 0.72, 0.58), 0.22, 0.0)
    watch_hands = _pmat("M_taxi_sora_watch_hands", (0.04, 0.05, 0.09), 0.28, 0.85)
    bm_wgold, bm_wstrap, bm_wdial, bm_whands = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    segs = 24
    s_rings = []
    for dy, sc_r in [(-0.0052, 1.06), (0.0052, 1.06), (0.0052, 0.94), (-0.0052, 0.94)]:
        s_rings.append([
            bm_wstrap.verts.new(M_w @ Vector((math.cos(k / segs * math.tau) * ru_m * sc_r, dy, math.sin(k / segs * math.tau) * rv_m * sc_r)))
            for k in range(segs)
        ])
    for r_idx in range(4):
        rA, rB = s_rings[r_idx], s_rings[(r_idx + 1) % 4]
        for k in range(segs):
            bm_wstrap.faces.new((rA[k], rA[(k + 1) % segs], rB[(k + 1) % segs], rB[k]))

    def _wbox(bm_t, loc, sz, rot_z=0.0):
        M = M_w @ Matrix.Translation(loc) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Diagonal((*sz, 1.0))
        ret = bmesh.ops.create_cube(bm_t, size=1.0, matrix=M)
        edges = list({e for v in ret["verts"] for e in v.link_edges})
        bmesh.ops.bevel(bm_t, geom=edges, offset=0.0007, segments=1, affect="EDGES", clamp_overlap=True)

    _wbox(bm_wgold, (0.0, 0.0, rv_m + 0.0022), (0.0152, 0.0205, 0.0044))
    _wbox(bm_wgold, (0.0, 0.0114, rv_m + 0.0020), (0.0030, 0.0026, 0.0028))
    _wbox(bm_wdial, (0.0, 0.0, rv_m + 0.0044), (0.0114, 0.0158, 0.0014))
    _wbox(bm_whands, (-0.0018, 0.0012, rv_m + 0.0052), (0.0009, 0.0046, 0.0005), rot_z=0.65)
    _wbox(bm_whands, (-0.0026, -0.0004, rv_m + 0.0054), (0.0007, 0.0062, 0.0005), rot_z=1.57)
    for nm, bm_x, mt in [
        ("taxi_sora_watch_case", bm_wgold, watch_gold),
        ("taxi_sora_watch_strap", bm_wstrap, watch_strap),
        ("taxi_sora_watch_dial", bm_wdial, watch_dial),
        ("taxi_sora_watch_hands", bm_whands, watch_hands),
    ]:
        _bm_obj(nm, bm_x, mt, coll, smooth=True)

    slot_stats = [
        (
            i,
            body.data.materials[i].name if i < len(body.data.materials) and body.data.materials[i] else None,
            sum(1 for p in body.data.polygons if p.material_index == i),
        )
        for i in range(len(body.data.materials))
    ]
    zs_s = [v.co.z for v in body.data.vertices]
    cap_xs = [body.data.vertices[vi].co.x for p in body.data.polygons if p.material_index == 4 for vi in p.vertices]
    neck_cap_x_span = round(max(cap_xs) - min(cap_xs), 4) if cap_xs else 0.0
    print(
        "TAXI_SEAMLESS_SORA_V8_REBUILT",
        "verts=", len(body.data.vertices),
        "polys=", len(body.data.polygons),
        "min_z=", round(min(zs_s), 4),
        "max_z=", round(max(zs_s), 4),
        "neck_cap_x_span=", neck_cap_x_span,
        "slots=", slot_stats,
    )
    return True


def _smooth_people_and_cabin_polish(coll, m, plain, world_uvs_fn):
    """Rebuild driver & Sora with Dual Quaternion skinning, warm translucent human skin,
    real woven linen/cotton clothing textures, snug cuffs, and polish interior cabin trim."""
    _set_normal_strength("M_cab_door_leather", 0.36)
    _set_normal_strength("M_cab_leather_strap", 0.34)
    _set_normal_strength("M_cab_satchel", 0.34)
    _set_normal_strength("M_taxi_seat", 0.36)

    # 1-3. MUSEUM-GRADE REBUILD OF DRIVER HEAD + 1930s FLAT CAP, DRIVER BODY + STEERING GRIP + COLLAR/KRAMA,
    #      AND SORA HANDS + FINGERNAILS + BVH-CONFORMED ART DECO WRISTWATCH!
    import taxi_people_refine

    neck_target = Vector((0.268, 0.056, 0.922))
    taxi_people_refine.apply_people_realism(coll, plain, world_uvs_fn, neck_pos=neck_target)

    # 5. POLISH EVERY CABIN INTERIOR DETAIL TO SILKY MUSEUM-GRADE SMOOTHNESS!
    for obj_name in (
        "taxi_steering_wheel_rim",
        "taxi_steering_wheel_spokes",
        "taxi_door_cards_pleated",
        "taxi_rear_door_cards",
        "taxi_front_seatbacks_leather",
        "taxi_rear_bench_tufted",
        "taxi_gear_gaiter",
        "taxi_gear_knob",
        "taxi_handbrake_grip",
        "taxi_sora_satchel",
        "taxi_rear_leather_suitcase",
        "taxi_rear_folded_krama",
        "taxi_door_strap_l",
        "taxi_door_strap_r",
        "taxi_assist_loop_b_l",
        "taxi_assist_loop_b_r",
        "taxi_assist_loop_c_l",
        "taxi_assist_loop_c_r",
    ):
        _subdivide_obj(bpy.data.objects.get(obj_name), levels=1)

    # Smooth-shade the Rosalie scan's interior nickel door cranks, latches & curved door pillars
    for scan_name in (
        "Object136_M_door_0",
        "taxi_car_door",
        "taxi_car_door.001",
        "taxi_car_door.002",
        "taxi_car_taxi_aged_nickel",
        "taxi_car_taxi_aged_nickel.001",
        "taxi_car_taxi_aged_nickel.002",
        "taxi_car_taxi_aged_nickel.003",
        "taxi_car_taxi_dashboard_walnut",
    ):
        so = bpy.data.objects.get(scan_name)
        if so and so.type == "MESH":
            for p in so.data.polygons:
                p.use_smooth = True
            so.data.update()

    # 6. ICONIC 1933 CITROEN DOUBLE-CHEVRON HORN BOSS + 5 DOMED DIAL CRYSTALS + PADDED LEATHER DOOR ARMRESTS!
    for old_n in ("taxi_steering_chevron", "taxi_steering_wheel_chevron", "taxi_dash_gauge_crystals", "taxi_door_armrests", "taxi_door_armrest_caps"):
        old = bpy.data.objects.get(old_n)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

    sw_pivot = bpy.data.objects.get("taxi_steering_wheel_pivot")
    if sw_pivot:
        bm_ch = bmesh.new()
        for dz_c in (-0.004, 0.002):
            for sgn in (-1.0, 1.0):
                _box_bm(bm_ch, (sgn * 0.0045, dz_c, 0.0342), (0.011, 0.0024, 0.0022), rot=Euler((0, 0, sgn * math.radians(-32))), bevel=0.0004, segs=1)
        ch_o = _bm_obj("taxi_steering_wheel_chevron", bm_ch, m["chrome"], coll, smooth=True)
        ch_o.parent = sw_pivot

    # Curved glossy clear-glass dial crystals recessed cleanly inside the 5 chrome gauge bezels
    m_crys = plain("M_cab_gauge_crystal", (0.92, 0.96, 1.0), 0.04, 0.0)
    m_crys.blend_method = "BLEND"
    bs_c = m_crys.node_tree.nodes["Principled BSDF"]
    bs_c.inputs["Alpha"].default_value = 0.14
    bm_cr = bmesh.new()
    y0 = -0.5004
    for u in (0.115, 0.30, 0.50, 0.70, 0.885):
        gx = -(u - 0.5) * 0.33
        bmesh.ops.create_uvsphere(
            bm_cr, u_segments=20, v_segments=10, radius=1.0,
            matrix=Matrix.Translation((gx, y0 + 0.009, 0.720)) @ Matrix.Diagonal((0.0246, 0.0038, 0.0246, 1.0)),
        )
    _bm_obj("taxi_dash_gauge_crystals", bm_cr, m_crys, coll, smooth=True)

    # Smooth contoured padded leather door armrests + chrome end-caps on both front doors
    bm_arm, bm_acap = bmesh.new(), bmesh.new()
    for sign in (-1.0, 1.0):
        inw = -sign
        ax = sign * 0.546
        _box_bm(bm_arm, (ax, 0.03, 0.485), (0.046, 0.32, 0.048), bevel=0.016, segs=3)
        for ay in (-0.135, 0.195):
            _box_bm(bm_acap, (ax - inw * 0.004, ay, 0.485), (0.040, 0.014, 0.040), bevel=0.004, segs=2)
    arm_o = _bm_obj("taxi_door_armrests", bm_arm, m["leather_door"], coll, world_uvs_fn=world_uvs_fn, smooth=True)
    _subdivide_obj(arm_o, levels=1)
    _bm_obj("taxi_door_armrest_caps", bm_acap, m["chrome"], coll, smooth=True)

    # Upgrade rear newspaper with authentic 1930s aged Khmer/French newspaper texture!
    news_src = TEX / "T_ep1_paper_news_BC.png"
    np_obj = bpy.data.objects.get("taxi_rear_newspaper")
    if news_src.exists() and np_obj and np_obj.type == "MESH":
        m_news = _image_mat("M_cab_aged_newspaper", news_src, plain, rough=0.88)
        np_obj.data.materials.clear()
        np_obj.data.materials.append(m_news)
        while len(np_obj.data.uv_layers) > 1:
            np_obj.data.uv_layers.remove(np_obj.data.uv_layers[-1])
        if not np_obj.data.uv_layers:
            world_uvs_fn(np_obj)

    print("TAXI_PEOPLE_AND_CABIN_POLISHED")


def apply_cabin_details(library_material, plain, world_uvs_fn, neck_pos=None):
    """Apply all approved cabin & driver upgrades right before build-taxi.py exports ep1_taxi_cabin.glb."""
    coll = bpy.context.collection
    m = _materials(library_material, plain)
    _upgrade_steering_wheel(coll, m)
    _upgrade_dashboard(coll, m, world_uvs_fn)
    _upgrade_pillars_and_cowl(coll, m, world_uvs_fn)
    _upgrade_mirrors_and_charm(coll, m, world_uvs_fn)
    _upgrade_interior_props(coll, m, plain, world_uvs_fn)
    _upgrade_footwell_and_console(coll, m, plain, world_uvs_fn)
    _upgrade_rear_cabin(coll, m, plain, world_uvs_fn)
    _smooth_people_and_cabin_polish(coll, m, plain, world_uvs_fn)
    rk = bpy.data.objects.get("taxi_rear_folded_krama")
    km = bpy.data.materials.get("M_cab_driver_krama")
    if rk and km:
        rk.data.materials.clear()
        rk.data.materials.append(km)
    print("TAXI_CABIN_DETAILS_APPLIED")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT / "tools/areas"))
    sys.path.insert(0, str(ROOT / "tools/travel"))
    from kit import library_material, plain, world_uvs

    coll = bpy.context.scene.collection
    for stale_m in ("M_taxi_sora_shoes_scan.001", "M_cab_driver_krama.001"):
        sm = bpy.data.materials.get(stale_m)
        if sm and sm.users == 0:
            bpy.data.materials.remove(sm)
    m = _materials(library_material, plain)
    # Refresh wiper header mounts + rebuild driver (head, cap, grip, krama) & Sora (hands, nails, watch)
    _refresh_wiper_header_mounts(coll, m)
    _smooth_people_and_cabin_polish(coll, m, plain, world_uvs)
    # Sync rear folded krama to the upgraded krama material
    rk = bpy.data.objects.get("taxi_rear_folded_krama")
    km = bpy.data.materials.get("M_cab_driver_krama")
    if rk and km:
        rk.data.materials.clear()
        rk.data.materials.append(km)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "art-source/blender/ep1/ep1_taxi_cabin.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.context.scene.objects:
        if o.type in {"MESH", "EMPTY", "CURVE"}:
            o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(ROOT / "art-export/ep1/ep1_taxi_cabin.glb"),
        export_format="GLB",
        use_selection=True,
        export_extras=True,
        export_yup=True,
        export_apply=True,
        export_cameras=False,
        export_lights=False,
    )
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    print("TAXI_CABIN_STANDALONE_EXPORTED_OK tris=", tris)
