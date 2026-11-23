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
    m = {}
    m["bakelite"] = plain("M_cab_bakelite", (0.015, 0.013, 0.012), 0.24, 0.0)
    m["bakelite_matte"] = plain("M_cab_bakelite_matte", (0.02, 0.018, 0.016), 0.45, 0.0)
    m["chrome"] = plain("M_cab_aged_chrome", (0.64, 0.62, 0.56), 0.24, 0.94)
    m["brass"] = plain("M_cab_aged_brass", (0.48, 0.36, 0.16), 0.32, 0.90)
    m["dark_iron"] = plain("M_cab_dark_iron", (0.04, 0.038, 0.036), 0.52, 0.78)
    m["wrinkle_enamel"] = plain("M_cab_wrinkle_enamel", (0.022, 0.022, 0.024), 0.62, 0.15)
    m["red_enamel"] = plain("M_cab_red_enamel", (0.34, 0.035, 0.025), 0.35, 0.08)
    m["rubber"] = plain("M_cab_rubber", (0.016, 0.016, 0.017), 0.78, 0.0)
    m["pillar_trim"] = plain("M_cab_pillar_leatherette", (0.016, 0.015, 0.014), 0.86, 0.0)
    m["walnut"] = bpy.data.materials.get("M_taxi_dashboard_walnut") or library_material(
        "rosewood_veneer1", "M_cab_walnut_polished", tint=(0.30, 0.19, 0.12), tile=0.26
    )
    m["leather_door"] = library_material("brown_leather", "M_cab_door_leather", tint=(0.24, 0.11, 0.09), tile=0.35)
    m["leather_strap"] = library_material("brown_leather", "M_cab_leather_strap", tint=(0.34, 0.21, 0.12), tile=0.22)
    m["satchel_leather"] = library_material("brown_leather", "M_cab_satchel", tint=(0.28, 0.17, 0.10), tile=0.28)
    m["mud"] = library_material("red_dirt_mud_01", "M_cab_tracked_mud", tint=(0.42, 0.28, 0.20), tile=0.5)
    m["mud"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.14
    m["rosewood_bead"] = library_material("dark_wood", "M_cab_prayer_bead", tint=(0.42, 0.20, 0.10), tile=0.06)
    m["rosewood_bead"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.30

    # Printed textures (radio dial & taximeter face; the 5 main gauges stay live-animated on taxi_instrument_face inside our 3D chrome bezels!)
    m["radio_dial"] = _image_mat("M_cab_radio_dial", TEX / "T_taxi_radio_dial_BC.png", plain, rough=0.3, emission=0.85)
    m["meter_face"] = _image_mat("M_cab_meter_face", TEX / "T_taxi_meter_face_BC.png", plain, rough=0.4, emission=0.08)
    m["cord_white"] = plain("M_cab_sacred_white_cord", (0.50, 0.45, 0.36), 0.94, 0.0)
    m["cord_red"] = plain("M_cab_sacred_red_cord", (0.24, 0.024, 0.020), 0.90, 0.0)
    m["aged_bronze"] = plain("M_cab_takrut_bronze", (0.36, 0.25, 0.11), 0.34, 0.90)
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

    # Ribbed bakelite rim with back-side finger grips
    bm_rim = bmesh.new()
    n_maj, n_min = 48, 16
    r_tube = 0.0155
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

    stalk_base = col_start - N * 0.035 + R_ax * 0.024
    stalk_tip = stalk_base + R_ax * 0.115 + U_ax * 0.035
    _tube_obj("taxi_indicator_stalk", [stalk_base, stalk_tip], 0.0035, m["chrome"], coll, segs=8)
    bm_tip = bmesh.new()
    bmesh.ops.create_uvsphere(bm_tip, u_segments=10, v_segments=8, radius=0.0085, matrix=Matrix.Translation(stalk_tip))
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
    """Authentic woven red-and-white checkered Cambodian krama texture saved for KTX2 pipeline."""
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

    mat = plain("M_cab_driver_krama", (1, 1, 1), 0.90, 0.0)
    nt = mat.node_tree
    bs = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
    linen_n = ROOT / "art-source/library/materials/rough_linen/rough_linen_N.jpg"
    if linen_n.exists():
        ntex = nt.nodes.new("ShaderNodeTexImage")
        ntex.image = bpy.data.images.load(str(linen_n), check_existing=True)
        ntex.image.colorspace_settings.name = "Non-Color"
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 0.55
        nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bs.inputs["Normal"])
    mat.use_backface_culling = False
    return mat


def _add_driver_krama(coll, neck_pos, plain):
    """Draped woven Cambodian krama wrapped around scanned driver's collar with both tails down chest."""
    body_obj = bpy.data.objects.get("taxi_driver_body_scan")
    if not body_obj or neck_pos is None:
        return
    pts = [(body_obj.matrix_world @ v.co, (body_obj.matrix_world.to_3x3() @ v.normal).normalized()) for v in body_obj.data.vertices]
    tree = KDTree(len(pts))
    for i, (co, _) in enumerate(pts):
        tree.insert(co, i)
    tree.balance()

    def lift_surface(p, offset=0.012):
        co, idx, _ = tree.find(p)
        nrm = pts[idx][1]
        return co + nrm * offset, nrm

    c = neck_pos + Vector((0.0, -0.012, -0.028))
    ring = []
    steps = 32
    for s in range(steps):
        a = s / steps * math.tau
        raw = c + Vector((math.sin(a) * 0.095, -math.cos(a) * 0.105, -0.025 * max(0.0, math.cos(a))))
        q, _ = lift_surface(raw, 0.013)
        q.z = max(q.z, raw.z)
        ring.append(q)
    for _ in range(4):
        ring = [(ring[i - 1] + ring[i] * 2 + ring[(i + 1) % steps]) * 0.25 for i in range(steps)]

    verts, faces, uvs = [], [], []

    def sweep(path, closed, half_w, thick, u0):
        start = len(verts)
        sides = 10
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
            for k in range(sides):
                b = k / sides * math.tau
                verts.append(p + out * (math.cos(b) * thick) + across * (math.sin(b) * half_w))
                uvs.append((u0 + s / max(1, len(path)) * 4.5, k / sides * 1.4))
        rows = len(path) if closed else len(path) - 1
        for s in range(rows):
            for k in range(sides):
                a = start + s * sides + k
                b = start + ((s + 1) % len(path)) * sides + k
                faces.append((a, start + s * sides + (k + 1) % sides, start + ((s + 1) % len(path)) * sides + (k + 1) % sides, b))

    sweep(ring, True, 0.028, 0.011, 0.0)
    for side, length in [(-1, 8), (1, 6)]:
        tail = []
        for s in range(length):
            raw = c + Vector((side * (0.032 + 0.005 * s), -0.145 - 0.006 * s, -0.025 - 0.032 * s))
            q, _ = lift_surface(raw, 0.014)
            tail.append(q)
        for _ in range(2):
            tail = [tail[0]] + [(tail[i - 1] + tail[i] * 2 + tail[i + 1]) * 0.25 for i in range(1, len(tail) - 1)] + [tail[-1]]
        sweep(tail, False, 0.036, 0.0045, 0.4 + side * 0.2)

    _make_mesh("taxi_driver_krama", verts, faces, _krama_texture(plain), coll, uvs=uvs, smooth=True)


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
    """Sculpted 3D interior A-pillar leatherette moldings, full-width walnut cowl cap,
    inner windscreen rubber seal, and header-mounted vacuum wiper motor bosses.

    Cleanly conceals raw scan seams between the windscreen surround, A-pillars, door jambs,
    and walnut fascia so there are zero sawtooth polygon edges or bright steel slivers.
    """
    bm_trim = bmesh.new()
    rake = Euler((-0.166, 0.0, 0.0), "XYZ")
    for side in (-1.0, 1.0):
        # Molded dark leatherette A-pillar cover tucked cleanly into the roof headliner above & cowl below
        _box_bm(
            bm_trim,
            (side * 0.534, -0.464, 0.945),
            (0.068, 0.072, 0.62),
            rot=rake,
            bevel=0.010,
            segs=3,
        )
        # Inner cowl kick-panel finisher below dashboard right where pillar meets door jamb
        _box_bm(
            bm_trim,
            (side * 0.548, -0.475, 0.675),
            (0.054, 0.095, 0.24),
            bevel=0.008,
            segs=2,
        )
        # Matte rubber windscreen vertical inner gasket hiding bright door-steel slivers
        _box_bm(
            bm_trim,
            (side * 0.494, -0.470, 0.995),
            (0.018, 0.028, 0.275),
            rot=rake,
            bevel=0.004,
            segs=2,
        )
    # Upper windscreen header trim rail bridging cleanly between both A-pillars
    _box_bm(
        bm_trim,
        (0.0, -0.445, 1.148),
        (1.09, 0.056, 0.042),
        bevel=0.008,
        segs=2,
    )
    _bm_obj("taxi_interior_apillar_trim", bm_trim, m["pillar_trim"], coll, smooth=True)

    # Full-width beveled walnut dashboard top cowl molding tying cleanly into both A-pillars
    bm_cap = bmesh.new()
    _box_bm(
        bm_cap,
        (0.0, -0.486, 0.858),
        (1.08, 0.052, 0.028),
        bevel=0.006,
        segs=2,
    )
    # Subtle lower fascia return edge
    _box_bm(
        bm_cap,
        (0.0, -0.492, 0.612),
        (1.06, 0.036, 0.018),
        bevel=0.004,
        segs=2,
    )
    _bm_obj("taxi_dash_top_rail", bm_cap, m["walnut"], coll, world_uvs_fn, smooth=True)

    # Exterior/header-mounted nickel vacuum wiper motor housings at x = +/-0.23
    bm_wiper_boss = bmesh.new()
    for side in (-1.0, 1.0):
        # Interior vacuum motor casing mounted cleanly on header above windscreen
        _box_bm(
            bm_wiper_boss,
            (side * 0.23, -0.432, 1.148),
            (0.044, 0.030, 0.024),
            bevel=0.005,
            segs=2,
        )
        # Exterior shaft grommet & pivot nut right on the top windscreen rubber rail
        _cyl_bm(
            bm_wiper_boss,
            (side * 0.23, -0.450, 1.146),
            (side * 0.23, -0.472, 1.142),
            0.0085,
            0.0068,
            segs=16,
        )
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

    # 3. Clean molded B-pillars, C-pillars, roof headliner bows, silk rear blind & hanging assist straps
    bm_pil = bmesh.new()
    for side in (-1.0, 1.0):
        # B-pillars cleanly dividing front and rear side windows
        _box_bm(bm_pil, (side * 0.606, 0.392, 0.68), (0.056, 0.072, 1.12), bevel=0.010, segs=2)
        # C-pillars framing rear quarter panels into the rear window
        _box_bm(bm_pil, (side * 0.612, 1.38, 0.96), (0.072, 0.34, 0.62), bevel=0.012, segs=2)
        # Upper side roof cantrails bridging A -> B -> C pillars
        _box_bm(bm_pil, (side * 0.585, 0.54, 1.195), (0.054, 1.88, 0.056), bevel=0.010, segs=2)
    # 4 transverse arched stitched fabric headliner roof bows across the cabin ceiling
    for by, bz in [(-0.02, 1.195), (0.42, 1.225), (0.86, 1.258), (1.30, 1.268)]:
        pts = []
        for s in range(13):
            u = (s / 12.0) * 2.0 - 1.0
            px = u * 0.56
            pz = bz - (u * u) * 0.048
            pts.append((px, by, pz))
        _tube_obj(f"taxi_headliner_bow_{by:.2f}", pts, 0.011, m_trim, coll, segs=8)
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
    bm_dchrome, bm_dglass = bmesh.new(), bmesh.new()
    dome_pos = Vector((0.0, 0.54, 1.224))
    _cyl_bm(bm_dchrome, dome_pos + Vector((0, 0, 0.012)), dome_pos + Vector((0, 0, -0.006)), 0.068, 0.064, segs=24)
    _cyl_bm(bm_dchrome, dome_pos + Vector((0, 0, -0.005)), dome_pos + Vector((0, 0, -0.016)), 0.062, 0.056, segs=24)
    bmesh.ops.create_uvsphere(
        bm_dglass,
        u_segments=20,
        v_segments=10,
        radius=1.0,
        matrix=Matrix.Translation(dome_pos + Vector((0, 0, -0.012))) @ Matrix.Diagonal((0.052, 0.066, 0.022, 1.0)),
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
    _add_driver_krama(coll, neck_pos, plain)
    _upgrade_rear_cabin(coll, m, plain, world_uvs_fn)
    _repair_driver_head_normal()
    print("TAXI_CABIN_DETAILS_APPLIED")
