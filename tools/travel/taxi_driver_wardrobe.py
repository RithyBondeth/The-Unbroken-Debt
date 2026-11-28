"""Real scanned wardrobe for Episode 1's taxi driver (cap, hands, krama, collar).

Replaces the generated pieces in taxi_people_refine.py with photoscans and cloth simulation:
- `build_scanned_flat_cap`: "Flat Cap" by kevjumba (CC BY 4.0), a photoscan of a real wool
  flat cap, welded, reduced and warped onto the driver's head so its opening follows his hat line.
- `tuck_head_under_cap`: pulls the scalp (and the head scan's old cap) in under the new cap.
- `ScanHand`: "Hand Scan Rigged And Animated" by Dakta.Grower.Nzl (CC BY 4.0), rigged from its own
  geometry (geodesic finger centre lines, joints at tip-to-web fractions, centre-of-rotation skinning);
  mirrored for the left hand.
- `solve_grip`: places a hand on the steering-wheel rim and curls each finger's three joints together
  (a power grip) until its skin meets the bakelite; `hand_material` re-tones the scan's photo skin to the driver's.
- `build_rolled_krama`: a krama rolled round the base of the neck, its two ends unrolling down the
  chest (cloth-simulated); `bind_to_body` gives it the body's breathing and leaning shapes.
- `regrade_skin` / `skin_patch_from_face` / `heal_uv_seams` / `smooth_neck`: one natural skin for
  face, neck and hands, real skin detail on the neck, and a face scan without seam scratches or facets.

Every function works in the frame its caller documents; nothing here is run on its own.
"""
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
SCANS = ROOT / "art-source/library/scans"
CAP_SCAN = SCANS / "taxi_driver_flatcap.glb"
HAND_SCAN = SCANS / "taxi_driver_hand.glb"

CAP_CREDIT = {
    "title": "Flat Cap",
    "author": "kevjumba (kevinmullin99)",
    "source": "https://sketchfab.com/3d-models/flat-cap-c2901aa86de9457fb241f7da8b1e691e",
    "license": "CC BY 4.0",
}
HAND_CREDIT = {
    "title": "Hand Scan Rigged And Animated",
    "author": "Dakta.Grower.Nzl",
    "source": "https://sketchfab.com/3d-models/hand-scan-rigged-and-animated-2ceff81e5d8c48849ad86e7330c54344",
    "license": "CC BY 4.0",
}


def _sstep(e0, e1, x):
    if e1 > e0:
        t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    else:
        t = max(0.0, min(1.0, (e0 - x) / (e0 - e1)))
    return t * t * (3.0 - 2.0 * t)


def _import_meshes(path):
    """Import a GLB and return its mesh objects joined into one, transforms applied."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    others = [o.name for o in new if o.type != "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for name in others:
        o = bpy.data.objects.get(name)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    if obj.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    return obj


def _decimate(obj, target_tris):
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tris <= target_tris:
        return
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = target_tris / tris
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def _cap_band(ang):
    """The driver's hat line (head-local metres): just above the brows, over the ear tops, low at the back."""
    c_side = abs(math.sin(ang))
    c_back = max(0.0, -math.cos(ang))
    ear_arch = math.exp(-(((abs(ang) - math.pi * 0.47) / 0.25) ** 2))
    return 2.004 - 0.034 * (c_side ** 1.45) + 0.020 * ear_arch - 0.070 * (c_back ** 1.15)


def _head_band_radii(head_bvh, ax, ay, segs=72):
    """Skull radius at the hat line every 5 degrees, bounded so the old scanned cap never inflates it."""
    radii = np.zeros(segs, np.float64)
    for k in range(segs):
        ang = k / segs * math.tau
        dx, dy = math.sin(ang), -math.cos(ang)
        z = max(1.915, _cap_band(ang) - 0.008)
        hit = head_bvh.ray_cast(Vector((ax, ay, z)), Vector((dx, dy, 0.0)), 0.16)
        r = math.hypot(hit[0].x - ax, hit[0].y - ay) if hit[0] is not None else 0.088
        r_anat = 0.084 * abs(math.sin(ang)) + 0.095 * abs(math.cos(ang))
        radii[k] = max(0.078, min(0.100, min(r, r_anat)))
    for _ in range(6):
        radii = 0.25 * np.roll(radii, -1) + 0.5 * radii + 0.25 * np.roll(radii, 1)
    return radii


def _sample_ring(radii, ang):
    segs = len(radii)
    f = (ang % math.tau) / math.tau * segs
    k0 = int(f) % segs
    t = f - math.floor(f)
    return radii[k0] * (1.0 - t) + radii[(k0 + 1) % segs] * t


def build_scanned_flat_cap(head_bvh, axis_xy, coll, target_tris=16000):
    """Return `taxi_driver_cap` built from the wool flat cap scan, in the pristine head frame
    (metres, facing -Y, crown +Z) so the caller's head morphs and seat transform apply unchanged."""
    for stale in ("T_cab_driver_cap_BC", "T_cab_driver_cap_N"):
        img = bpy.data.images.get(stale)
        if img:
            bpy.data.images.remove(img)
    obj = _import_meshes(CAP_SCAN)
    me = obj.data

    # The scan is in millimetres and split into 65k-vertex chunks: weld the chunk and UV seams.
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.06)
    bm.to_mesh(me)
    bm.free()
    me.transform(Matrix.Scale(0.001, 4))
    _decimate(obj, target_tris)

    co = np.array([v.co[:] for v in me.vertices], np.float64)

    # Which end is the peak: the crown is highest at the back and slopes down onto the peak.
    y_lo, y_hi = co[:, 1].min(), co[:, 1].max()
    span = y_hi - y_lo
    lo_end = co[co[:, 1] < y_lo + span * 0.2, 2].max()
    hi_end = co[co[:, 1] > y_hi - span * 0.2, 2].max()
    if hi_end < lo_end:
        # Peak lies at +Y: turn the cap round so it faces -Y like the head.
        co[:, 0] *= -1.0
        co[:, 1] *= -1.0

    # Opening (the sweatband): the lowest edge of the cap body round the back and sides; the
    # front of it hides behind the peak, so an ellipse fitted to the rest gives it.
    segs = 72
    c0 = np.array([float(co[:, 0].mean()), float(co[:, 1].max()) - 0.10])
    rel0 = co[:, :2] - c0
    ang0 = np.arctan2(rel0[:, 0], -rel0[:, 1]) % math.tau
    rad0 = np.hypot(rel0[:, 0], rel0[:, 1])
    ring = []
    for k in range(segs):
        a0 = k / segs * math.tau
        if math.cos(a0) > 0.30:  # the front arc hides under the peak: keep back and sides
            continue
        da = np.abs((ang0 - a0 + math.pi) % math.tau - math.pi)
        sec = da < math.tau / segs
        if not sec.any():
            continue
        zb = co[sec, 2].min()
        bottom = sec & (co[:, 2] < zb + 0.006)
        j = np.argmax(np.where(bottom, rad0, -1.0))
        ring.append(co[j])
    ring = np.array(ring)
    cx = float(ring[:, 0].mean())
    u = ring[:, 0] - cx
    yv = ring[:, 1]
    # A u^2 + B y^2 + C y = 1  ->  centre cy = -C / 2B, semi-axes from completing the square.
    M = np.stack([u * u, yv * yv, yv], axis=1)
    A, B, C = np.linalg.lstsq(M, np.ones(len(ring)), rcond=None)[0]
    cy = -C / (2.0 * B)
    rhs = 1.0 + C * C / (4.0 * B)
    semi_x, semi_y = math.sqrt(rhs / A), math.sqrt(rhs / B)
    # Opening plane through the ring: z = z0 + gy (y - cy)  (sides and back only; the front is extrapolated)
    G = np.stack([np.ones(len(ring)), ring[:, 1] - cy], axis=1)
    z0, gy = np.linalg.lstsq(G, ring[:, 2], rcond=None)[0]
    cap_tilt = math.atan(gy)  # slope of the opening along Y (the peak is at -Y)

    # Level the opening: centre it, rotate about X so its plane is z = 0.
    p = co - np.array([cx, cy, z0])
    c_l, s_l = math.cos(-cap_tilt), math.sin(-cap_tilt)
    y_l = p[:, 1] * c_l - p[:, 2] * s_l
    z_l = p[:, 1] * s_l + p[:, 2] * c_l
    p[:, 1], p[:, 2] = y_l, z_l

    ax, ay = float(axis_xy[0]), float(axis_xy[1])
    head_r = _head_band_radii(head_bvh, ax, ay, segs) + 0.0045  # felt and lining over the hair
    cap_r = np.array([
        1.0 / math.sqrt((math.sin(k / segs * math.tau) / semi_x) ** 2 + (math.cos(k / segs * math.tau) / semi_y) ** 2)
        for k in range(segs)
    ])
    k_ang = head_r / cap_r
    s = float(np.mean(k_ang))
    k_rel = k_ang / s
    co = p
    cx = cy = 0.0
    open_z = 0.0

    # Opening plane of the head's hat line: front and back heights give its tilt.
    band = np.array([_cap_band(k / segs * math.tau) for k in range(segs)])
    z_front, z_back = band[0], band[segs // 2]
    r_front, r_back = head_r[0], head_r[segs // 2]
    tilt = math.atan2(z_front - z_back, r_front + r_back)  # front higher than back
    z_ctr = z_back + (z_front - z_back) * r_back / (r_front + r_back)

    # Similarity: scale about the opening centre, tilt the opening, sit it on the head.
    p = (co - np.array([cx, cy, open_z])) * s
    height = p[:, 2].copy()
    a_v = np.arctan2(p[:, 0], -p[:, 1]) % math.tau
    # Per-angle fit, strongest at the opening and easing off up the crown.
    w_fit = np.clip(1.0 - height / 0.060, 0.25, 1.0)
    k_fit = np.array([_sample_ring(k_rel, a) for a in a_v])
    radial = 1.0 + (k_fit - 1.0) * w_fit
    p[:, 0] *= radial
    p[:, 1] *= radial
    c_t, s_t = math.cos(tilt), math.sin(tilt)
    # Rotate about X by -tilt so the front (-Y) of the opening rises and the back drops.
    y_r = p[:, 1] * c_t + p[:, 2] * s_t
    z_r = -p[:, 1] * s_t + p[:, 2] * c_t
    p[:, 1], p[:, 2] = y_r, z_r
    p += np.array([ax, ay, z_ctr])
    # Follow the hat line's dip over the temples and arch over the ears near the opening.
    plane_z = z_ctr + (-(p[:, 1] - ay)) * math.tan(tilt)
    a_new = np.arctan2(p[:, 0] - ax, -(p[:, 1] - ay)) % math.tau
    band_v = np.array([_cap_band(a) for a in a_new])
    w_band = np.clip(1.0 - np.maximum(height, 0.0) / 0.045, 0.0, 1.0)
    p[:, 2] += (band_v - plane_z) * w_band

    # The stiff peak hinges at the brow: lift it so its edge clears his eye line (eyes at z 1.970)
    # and he can still be seen looking out from under it.
    hinge_y = ay - head_r[0]
    hinge_z = _cap_band(0.0)
    fwd = hinge_y - p[:, 1]
    in_front = fwd > 0.0
    eye_clear = 1.986
    low_peak = p[in_front & (fwd > 0.012), 2]
    beta = 0.0
    if low_peak.size:
        reach = max(1e-3, float(fwd[in_front].max()))
        drop = max(0.0, eye_clear - float(low_peak.min()))
        beta = min(math.radians(16.0), math.atan2(drop, reach * 0.85))
    if beta > 0.0:
        w_h = np.clip(fwd / 0.012, 0.0, 1.0)
        w_h = w_h * w_h * (3.0 - 2.0 * w_h)
        dy, dz = p[:, 1] - hinge_y, p[:, 2] - hinge_z
        cb, sb = math.cos(beta), math.sin(beta)
        ry = dy * cb + dz * sb
        rz = -dy * sb + dz * cb
        sel = in_front
        p[sel, 1] += (hinge_y + ry[sel] - p[sel, 1]) * w_h[sel]
        p[sel, 2] += (hinge_z + rz[sel] - p[sel, 2]) * w_h[sel]
    print("TAXI_CAP_PEAK", "hinge_y=", round(hinge_y, 4), "lift_deg=", round(math.degrees(beta), 2),
          "peak_min_z=", round(float(p[fwd > 0.012, 2].min()) if (fwd > 0.012).any() else -1, 4),
          "crown_top=", round(float(p[:, 2].max()), 4))

    me.vertices.foreach_set("co", p.astype(np.float32).ravel())
    me.update()

    # Material: the scan's own photo texture at 2048 px, matte wool.
    mat = me.materials[0] if me.materials else bpy.data.materials.new("M_cab_driver_cap")
    old = bpy.data.materials.get("M_cab_driver_cap")
    if old and old != mat:
        bpy.data.materials.remove(old)
    mat.name = "M_cab_driver_cap"
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.93
    bsdf.inputs["Metallic"].default_value = 0.0
    for n in nt.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            n.image.name = "T_cab_driver_cap_BC"
            if n.image.size[0] > 2048:
                n.image.scale(2048, 2048)
            n.image.pack()
    mat.use_backface_culling = False

    obj.name = me.name = "taxi_driver_cap"
    for c_old in list(obj.users_collection):
        c_old.objects.unlink(obj)
    coll.objects.link(obj)
    for poly in me.polygons:
        poly.use_smooth = True
    me["credit"] = str(CAP_CREDIT)
    print("TAXI_SCANNED_CAP", "verts=", len(me.vertices), "tris=", sum(len(q.vertices) - 2 for q in me.polygons),
          "scale=", round(s, 4), "tilt_deg=", round(math.degrees(tilt), 2))
    return obj


def tuck_head_under_cap(head, cap, axis_xy, clearance=0.0028):
    """Pull every scalp vertex the cap covers to sit `clearance` inside the cap's inner surface,
    fading over the last centimetre above the cap edge so the hair line stays natural."""
    cap_bvh = BVHTree.FromPolygons([v.co.copy() for v in cap.data.vertices], [list(p.vertices) for p in cap.data.polygons])
    ax, ay = float(axis_xy[0]), float(axis_xy[1])
    centre = Vector((ax, ay, 1.955))
    moved = 0
    for v in head.data.vertices:
        p = v.co
        ang = math.atan2(p.x - ax, -(p.y - ay))
        edge = _cap_band(ang)
        if p.z < edge - 0.004:
            continue
        d = p - centre
        dist = d.length
        if dist < 1e-6:
            continue
        hit = cap_bvh.ray_cast(centre, d / dist, 0.25)
        if hit[0] is None:
            continue
        limit = (hit[0] - centre).length - clearance
        if dist > limit:
            w = _sstep(edge - 0.004, edge + 0.006, p.z)
            v.co = centre + d / dist * (dist + (limit - dist) * w)
            moved += 1
    head.data.update()
    print("TAXI_HEAD_TUCKED_UNDER_CAP", moved)
    return moved


# --------------------------------------------------------------------------- scanned hands

# Fingertips and the geodesic tip-to-web length of each digit, measured on the welded scan
# (right hand, metres, its import frame: fingers point -X, palm faces -Z, thumb at -Y).
HAND_TIPS = {
    "index": (-0.2317, -0.2777, 0.0894),
    "middle": (-0.2432, -0.2493, 0.0915),
    "ring": (-0.2285, -0.2271, 0.0927),
    "pinky": (-0.2156, -0.2025, 0.1100),
    "thumb": (-0.1638, -0.2988, 0.0636),
}
HAND_WEB = {"index": 0.075, "middle": 0.078, "ring": 0.070, "pinky": 0.065, "thumb": 0.061}
# Joints as multiples of the tip-to-web length: (DIP, PIP, MCP) for fingers, (IP, MCP, CMC) for the thumb.
HAND_JOINTS = {
    "index": (0.31, 0.66, 1.28),
    "middle": (0.31, 0.67, 1.28),
    "ring": (0.32, 0.68, 1.27),
    "pinky": (0.31, 0.64, 1.26),
    "thumb": (0.41, 0.96, 1.68),
}
FINGERS = ("index", "middle", "ring", "pinky")
DIGITS = FINGERS + ("thumb",)
BONES = ["forearm", "hand"] + [f"{d}_{k}" for d in DIGITS for k in (1, 2, 3)]
B_IDX = {n: i for i, n in enumerate(BONES)}
RIM_TUBE = 0.0127  # the cabin rim mesh's own tube radius (measured)
THUMB_WEB_R = 0.017  # skin within this of the thumb's metacarpal follows it
THUMB_SWING_MAX = 38.0  # degrees the thumb swings across to wrap the rim


def _geodesic(co, adj, src, limit=0.2):
    import heapq
    d = np.full(len(co), np.inf)
    d[src] = 0.0
    h = [(0.0, src)]
    while h:
        x, v = heapq.heappop(h)
        if x > d[v] or x > limit:
            continue
        for u in adj[v]:
            nd = x + float(np.linalg.norm(co[u] - co[v]))
            if nd < d[u]:
                d[u] = nd
                heapq.heappush(h, (nd, u))
    return d


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _rot(axis, angle):
    """3x3 rotation matrix about a unit axis (numpy)."""
    a = _unit(np.asarray(axis, np.float64))
    x, y, z = a
    c, s = math.cos(angle), math.sin(angle)
    C = 1.0 - c
    return np.array([
        [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
        [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
        [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
    ])


def _about(point, R):
    """4x4 rotating by R about `point`."""
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = point - R @ point
    return M


def _rot_between(a, b):
    a, b = _unit(a), _unit(b)
    ax = np.cross(a, b)
    s = np.linalg.norm(ax)
    c = float(np.dot(a, b))
    if s < 1e-9:
        if c > 0:
            return np.eye(3)
        perp = _unit(np.cross(a, [1.0, 0.0, 0.0] if abs(a[0]) < 0.9 else [0.0, 1.0, 0.0]))
        return _rot(perp, math.pi)
    return _rot(ax / s, math.atan2(s, c))


def _mat_to_dq(M):
    q = Matrix(M[:3, :3].tolist()).to_quaternion()
    qr = np.array([q.w, q.x, q.y, q.z])
    t = M[:3, 3]
    # qd = 0.5 * (0, t) * qr
    w0, x0, y0, z0 = 0.0, t[0], t[1], t[2]
    w1, x1, y1, z1 = qr
    qd = 0.5 * np.array([
        w0 * w1 - x0 * x1 - y0 * y1 - z0 * z1,
        w0 * x1 + x0 * w1 + y0 * z1 - z0 * y1,
        w0 * y1 - x0 * z1 + y0 * w1 + z0 * x1,
        w0 * z1 + x0 * y1 - y0 * x1 + z0 * w1,
    ])
    return np.concatenate([qr, qd])


def _dq_skin(co, weights, mats):
    """Dual-quaternion skinning of rest positions `co` (N,3) with bone matrices `mats` (B,4,4)."""
    dqs = np.array([_mat_to_dq(M) for M in mats])
    ref = dqs[B_IDX["hand"], :4]
    flip = np.sign(dqs[:, :4] @ ref)
    flip[flip == 0] = 1.0
    dqs = dqs * flip[:, None]
    b = weights @ dqs
    nr = np.linalg.norm(b[:, :4], axis=1, keepdims=True)
    b = b / np.maximum(nr, 1e-9)
    w, v = b[:, 0:1], b[:, 1:4]
    wd, vd = b[:, 4:5], b[:, 5:8]
    t = 2.0 * (w * vd - wd * v + np.cross(v, vd))
    out = co + 2.0 * w * np.cross(v, co) + 2.0 * np.cross(v, np.cross(v, co)) + t
    return out


def _cor_centres(co, tris, W, sigma=0.1, eps=0.01):
    """Centres of rotation for optimised centre-of-rotation skinning (Le & Hodgins 2016): each blended
    vertex turns about the area-weighted centroid of the skin whose bone weights resemble its own,
    a point on the joint's axis. Dual quaternions swelled every knuckle of the fist into a ball;
    plain linear blending would pinch it flat. Returns (centres, has_centre)."""
    Wt = np.where(W > eps, W, 0.0)
    a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    cen = (a + b + c) / 3.0
    Wf = (Wt[tris[:, 0]] + Wt[tris[:, 1]] + Wt[tris[:, 2]]) / 3.0
    num = np.zeros((len(co), 3))
    den = np.zeros(len(co))
    n_b = W.shape[1]
    for j in range(n_b):
        for k in range(j + 1, n_b):
            vi = np.where((Wt[:, j] > 0.0) & (Wt[:, k] > 0.0))[0]
            if not len(vi):
                continue
            ti = np.where((Wf[:, j] > 0.0) & (Wf[:, k] > 0.0))[0]
            if not len(ti):
                continue
            bj, bk = Wf[ti, j][None, :], Wf[ti, k][None, :]
            ar, ce = area[ti][None, :], cen[ti]
            for s in range(0, len(vi), 1024):
                v = vi[s:s + 1024]
                aj, ak = Wt[v, j][:, None], Wt[v, k][:, None]
                term = 2.0 * aj * ak * bj * bk * np.exp(-((aj * bk - ak * bj) ** 2) / (sigma * sigma)) * ar
                num[v] += term @ ce
                den[v] += term.sum(1)
    has = den > 1e-14
    cor = co.copy()
    cor[has] = num[has] / den[has][:, None]
    return cor, has


def _quat_rows(q):
    """(N,4) unit quaternions (w,x,y,z) -> (N,3,3) rotation matrices."""
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], -1),
        np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], -1),
        np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], -1),
    ], 1)


def _cor_skin(co, weights, mats, cor, has):
    """Centre-of-rotation skinning: blended rotation (quaternion average) about each vertex's centre,
    which itself moves by linear blending. Rigid parts are plain linear blending."""
    qs = np.array([_mat_to_dq(M)[:4] for M in mats])
    ref = qs[B_IDX["hand"]]
    flip = np.sign(qs @ ref)
    flip[flip == 0] = 1.0
    q = weights @ (qs * flip[:, None])
    q /= np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-12)
    R = _quat_rows(q)
    lin = lambda w, p: np.einsum("nb,bij,nj->ni", w, mats[:, :3, :3], p) + w @ mats[:, :3, 3]
    out = np.einsum("nij,nj->ni", R, co - cor) + lin(weights, cor)
    if not has.all():
        out[~has] = lin(weights[~has], co[~has])
    return out


def _torus_dist(p, C, F, R):
    """Distance of points p (N,3) from the centre line of a rim of radius R (centre C, normal F)."""
    rel = p - C
    z = rel @ F
    inpl = rel - np.outer(z, F)
    r = np.linalg.norm(inpl, axis=1)
    return np.sqrt((r - R) ** 2 + z * z)


class ScanHand:
    """The photoscanned hand, rigged from its own geometry (landmarks + geodesic skin weights)."""

    def __init__(self, mirror=False, keep_len=0.060):
        obj = _import_meshes(HAND_SCAN)
        me = obj.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002)
        bm.to_mesh(me)
        bm.free()
        self.src_obj = obj
        co = np.array([v.co[:] for v in me.vertices], np.float64)
        from collections import defaultdict

        adj = defaultdict(set)
        edge_n = defaultdict(int)
        for p in me.polygons:
            vs = list(p.vertices)
            for i in range(len(vs)):
                a, b = vs[i], vs[(i + 1) % len(vs)]
                adj[a].add(b)
                adj[b].add(a)
                edge_n[(min(a, b), max(a, b))] += 1
        bverts = {v for e, n in edge_n.items() if n == 1 for v in e}
        elbow_c = co[list(bverts)].mean(0)

        tipv = {k: int(np.argmin(np.linalg.norm(co - np.array(t), axis=1))) for k, t in HAND_TIPS.items()}
        D = {k: _geodesic(co, adj, v, 0.16) for k, v in tipv.items()}
        Dmin_other = {k: np.min(np.stack([D[j] for j in DIGITS if j != k]), axis=0) for k in DIGITS}

        # Centre line of each digit: centroids of geodesic rings from the tip to the web.
        lines = {}
        for k in DIGITS:
            pts = []
            for s in np.arange(0.004, HAND_WEB[k] + 1e-6, 0.002):
                ring = (np.abs(D[k] - s) < 0.0014) & (D[k] < Dmin_other[k] - 0.002)
                if ring.sum() >= 4:
                    pts.append((s, co[ring].mean(0)))
            lines[k] = pts

        def along(k, s):
            pts = lines[k]
            ss = np.array([p[0] for p in pts])
            cs = np.array([p[1] for p in pts])
            if s <= ss[-1]:
                return np.array([np.interp(s, ss, cs[:, i]) for i in range(3)])
            tail = cs[ss >= ss[-1] - 0.02]
            d = _unit(tail[-1] - tail[0])
            return cs[-1] + d * (s - ss[-1])

        chains = {}
        for k in DIGITS:
            L = HAND_WEB[k]
            r1, r2, r3 = HAND_JOINTS[k]
            tip = co[tipv[k]]
            chains[k] = [along(k, r3 * L), along(k, r2 * L), along(k, r1 * L), tip]

        mcp_mid = chains["middle"][0]
        fa0 = _unit(elbow_c - mcp_mid)
        w_guess = mcp_mid + fa0 * 0.080
        band = np.abs((co - w_guess) @ fa0) < 0.003
        wrist = co[band].mean(0)
        fa_dir = _unit(elbow_c - wrist)
        fwd = _unit(mcp_mid - wrist)
        across = chains["index"][0] - chains["pinky"][0]
        across = _unit(across - fwd * (across @ fwd))
        n = _unit(np.cross(across, fwd))
        tips_mean = np.mean([chains[k][3] for k in FINGERS], axis=0)
        mcps_mean = np.mean([chains[k][0] for k in FINGERS], axis=0)
        if n @ (tips_mean - mcps_mean) < 0:
            n = -n
        self.handed_right = bool(np.cross(across, fwd) @ n > 0)

        # ---- skin weights
        N, B = len(co), len(BONES)
        W = np.zeros((N, B))
        in_digit = np.full(N, -1)
        for i, k in enumerate(DIGITS):
            mine = (D[k] < HAND_WEB[k] + 0.004) & (D[k] < Dmin_other[k] - 0.001)
            in_digit[mine] = i
        for i, k in enumerate(DIGITS):
            L = HAND_WEB[k]
            s1, s2 = HAND_JOINTS[k][0] * L, HAND_JOINTS[k][1] * L
            sel = in_digit == i
            s = D[k][sel]
            w_dist = 1.0 - np.clip((s - (s1 - 0.004)) / 0.008, 0.0, 1.0)
            w_mid_full = 1.0 - np.clip((s - (s2 - 0.005)) / 0.010, 0.0, 1.0)
            w_mid = w_mid_full - w_dist
            w_prox = 1.0 - w_mid_full
            W[sel, B_IDX[f"{k}_3"]] = w_dist
            W[sel, B_IDX[f"{k}_2"]] = np.clip(w_mid, 0.0, 1.0)
            W[sel, B_IDX[f"{k}_1"]] = w_prox
        # Palm round the knuckles follows the proximal phalanges; the thenar pad follows the thumb.
        palm = in_digit < 0
        pidx = np.where(palm)[0]
        P = co[pidx]
        best = np.full(len(pidx), np.inf)
        best_k = np.full(len(pidx), -1)
        best_t = np.zeros(len(pidx))
        for i, k in enumerate(FINGERS):
            m, pip = chains[k][0], chains[k][1]
            d = _unit(pip - m)
            rel = P - m
            t = rel @ d
            lat = np.linalg.norm(rel - np.outer(t, d), axis=1)
            closer = lat < best
            best[closer], best_k[closer], best_t[closer] = lat[closer], i, t[closer]
        for i, k in enumerate(FINGERS):
            sel = (best_k == i) & (best < 0.016)
            wk = np.clip((best_t[sel] + 0.012) / 0.018, 0.0, 1.0)
            wk = wk * wk * (3.0 - 2.0 * wk) * np.clip((0.016 - best[sel]) / 0.006, 0.0, 1.0)
            W[pidx[sel], B_IDX[f"{k}_1"]] = wk
        cmc, tmcp = chains["thumb"][0], chains["thumb"][1]
        seg = tmcp - cmc
        tt = np.clip(((P - cmc) @ seg) / (seg @ seg), 0.0, 1.0)
        dseg = np.linalg.norm(P - (cmc + np.outer(tt, seg)), axis=1)
        # Only the thumb's own metacarpal and its pad: a wider patch dragged the web and the back of the
        # hand along with the thumb and swelled them into a mound.
        wt = np.clip((THUMB_WEB_R - dseg) / (THUMB_WEB_R * 0.5), 0.0, 1.0) * np.clip(tt / 0.35, 0.0, 1.0)
        W[pidx, B_IDX["thumb_1"]] = np.maximum(W[pidx, B_IDX["thumb_1"]], wt)
        rest = 1.0 - W.sum(1)
        tw = (co - wrist) @ fa_dir  # >0 toward the elbow
        w_fa = np.clip((tw + 0.010) / 0.024, 0.0, 1.0)
        w_fa = w_fa * w_fa * (3.0 - 2.0 * w_fa)
        W[:, B_IDX["forearm"]] = np.clip(rest, 0.0, 1.0) * w_fa
        W[:, B_IDX["hand"]] = np.clip(rest, 0.0, 1.0) * (1.0 - w_fa)
        W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
        # Diffuse the weights over the skin so every joint bends in a soft gradient: hard weight
        # edges left lumps and creases over the knuckles. (Fingers only touch through the palm.)
        nbr_i = np.array([u for v in range(len(co)) for u in adj[v]], np.int64)
        nbr_v = np.array([v for v in range(len(co)) for u in adj[v]], np.int64)
        deg = np.bincount(nbr_v, minlength=len(co)).astype(np.float64)
        tip_guard = np.zeros(len(co), bool)
        for k in DIGITS:
            tip_guard |= D[k] < 0.006
        for _ in range(6):
            avg = np.zeros_like(W)
            np.add.at(avg, nbr_v, W[nbr_i])
            avg /= np.maximum(deg, 1.0)[:, None]
            W = np.where(tip_guard[:, None], W, W * 0.5 + avg * 0.5)
        W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
        self.adj_i, self.adj_v, self.deg = nbr_i, nbr_v, deg
        tris = np.array([(p.vertices[0], p.vertices[i], p.vertices[i + 1])
                         for p in me.polygons for i in range(1, len(p.vertices) - 1)], np.int64)
        self.cor, self.has_cor = _cor_centres(co, tris, W)

        # Keep this much forearm past the wrist (6 cm under a shirt cuff, more below a rolled sleeve).
        self.keep = tw < keep_len
        faces = [list(p.vertices) for p in me.polygons]
        uv_layer = me.uv_layers.active.data
        loops = []
        for p in me.polygons:
            loops.append([tuple(uv_layer[li].uv) for li in p.loop_indices])
        self.faces, self.face_uvs = faces, loops
        self.material = me.materials[0] if me.materials else None

        self.co, self.W, self.D, self.in_digit = co, W, D, in_digit
        self.chains, self.wrist, self.fa_dir, self.fwd, self.across, self.n = chains, wrist, fa_dir, fwd, across, n
        self.mirrored = False
        if mirror:
            self._mirror()

    def _mirror(self):
        """Left hand: reflect across the plane through the wrist normal to `across`."""
        a = self.across.copy()
        S = np.eye(3) - 2.0 * np.outer(a, a)
        o = self.wrist.copy()
        ref = lambda p: (np.asarray(p) - o) @ S.T + o
        self.co = ref(self.co)
        self.cor = ref(self.cor)
        self.chains = {k: [ref(j) for j in v] for k, v in self.chains.items()}
        self.fa_dir, self.fwd = self.fa_dir @ S.T, self.fwd @ S.T
        self.across = self.across @ S.T
        self.n = self.n @ S.T
        self.faces = [f[::-1] for f in self.faces]
        self.face_uvs = [u[::-1] for u in self.face_uvs]
        self.mirrored = True

    # ---- posing
    def flex_axis(self, k, j, locals_):
        """Axis that curls joint j of digit k toward the palm, in the posed rest frame."""
        ch = self.chains[k]
        d = _unit(ch[j + 1] - ch[j])
        if k == "thumb":
            target = np.mean([self.chains[f][0] for f in ("middle", "ring")], axis=0) + self.n * 0.02
            toward = _unit(target - ch[j])
        else:
            toward = self.n
        ax = np.cross(d, toward)
        return _unit(ax)

    def bone_mats(self, G, G_fa, locals_):
        """World matrices for every bone. `locals_[(k, j)]` is a 3x3 rotation about joint j."""
        mats = np.zeros((len(BONES), 4, 4))
        mats[B_IDX["forearm"]] = G_fa
        mats[B_IDX["hand"]] = G
        for k in DIGITS:
            M = np.eye(4)
            for j in range(3):
                R = locals_.get((k, j), np.eye(3))
                M = M @ _about(self.chains[k][j], R)
                mats[B_IDX[f"{k}_{j + 1}"]] = G @ M
        return mats

    def skin(self, mats, idx=None):
        if idx is None:
            return _cor_skin(self.co, self.W, mats, self.cor, self.has_cor)
        return _cor_skin(self.co[idx], self.W[idx], mats, self.cor[idx], self.has_cor[idx])


# --------------------------------------------------------------------------- steering-wheel grip

class Rim:
    """The Rosalie's bakelite rim: centre, normal toward the driver, radius, tube radius."""

    def __init__(self, centre, normal, radius, tube=RIM_TUBE):
        self.C = np.asarray(centre, np.float64)
        self.F = _unit(np.asarray(normal, np.float64))
        self.R = float(radius)
        self.r = float(tube)
        r0 = np.array([1.0, 0.0, 0.0])
        self.R0 = _unit(r0 - self.F * (r0 @ self.F))
        u0 = _unit(np.cross(self.F, self.R0))
        self.U0 = u0 if u0[2] > 0 else -u0

    def frame(self, side, clock_deg, turn=0.0):
        """Outward radial, upward tangent and tube centre at a hand position.
        `clock_deg`: degrees above the horizontal (left hand at 9 o'clock = 0, 10 o'clock = 30)."""
        sign = 1.0 if side == "l" else -1.0
        a = math.radians(clock_deg)
        R = self.R0 * math.cos(turn) + self.U0 * math.sin(turn)
        U = -self.R0 * math.sin(turn) + self.U0 * math.cos(turn)
        rad = _unit(R * sign * math.cos(a) + U * math.sin(a))
        tan = _unit(-R * sign * math.sin(a) + U * math.cos(a))
        return rad, tan, self.C + rad * self.R

    def dist(self, p):
        return _torus_dist(p, self.C, self.F, self.R)

    def push_out(self, p, skin=0.0006):
        """Soft tissue: nothing passes inside the bakelite."""
        rel = p - self.C
        z = rel @ self.F
        inpl = rel - np.outer(z, self.F)
        rr = np.linalg.norm(inpl, axis=1)
        ctr = self.C + inpl * (self.R / np.maximum(rr, 1e-9))[:, None]
        v = p - ctr
        d = np.linalg.norm(v, axis=1)
        lim = self.r + skin
        bad = d < lim
        p = p.copy()
        p[bad] = ctr[bad] + v[bad] / np.maximum(d[bad], 1e-9)[:, None] * lim
        return p


def _palm_point(hand):
    """Palm skin under the knuckle row, a little toward the wrist: where the rim presses."""
    row = np.mean([hand.chains[k][0] for k in FINGERS], axis=0) - hand.fwd * 0.010
    bvh = BVHTree.FromPolygons([Vector(c) for c in hand.co], hand.faces)
    hit = bvh.ray_cast(Vector(row), Vector(hand.n), 0.06)
    if hit[0] is None:
        return row + hand.n * 0.012
    return np.array(hit[0][:])


def grip_placement(hand, rim, side, clock_deg, elbow_hint, turn=0.0, palm_psi=None, slant_deg=16.0):
    """Rigid 4x4 placing the rest hand on the rim: the rim runs across the distal palm, slanting
    toward the wrist on the little-finger side, index uppermost; the palm rolls round the tube so
    the wrist points back toward the elbow."""
    rad, tan, ctr = rim.frame(side, clock_deg, turn)
    s = math.radians(slant_deg)
    g = _unit(hand.across * math.cos(s) + hand.fwd * math.sin(s))
    n = hand.n
    m = _unit(np.cross(g, n))
    P_palm = _palm_point(hand)
    best = None
    psis = [palm_psi] if palm_psi is not None else [math.radians(x) for x in range(-10, 111, 5)]
    for psi in psis:
        out = _unit(rad * math.cos(psi) + rim.F * math.sin(psi))
        n_w = -out
        m_w = _unit(np.cross(tan, n_w))
        Rm = np.stack([tan, n_w, m_w], 1) @ np.stack([g, n, m], 1).T
        t = ctr + out * (rim.r + 0.0012) - Rm @ P_palm
        G = np.eye(4)
        G[:3, :3], G[:3, 3] = Rm, t
        wrist_w = Rm @ hand.wrist + t
        score = float(np.dot(_unit(wrist_w - ctr), _unit(np.asarray(elbow_hint) - ctr)))
        if best is None or score > best[0]:
            best = (score, G, psi)
    return best[1], best[2]


def _contact_angle(hand, rim, G, locals_, k, j, axis, start, stop, thresh, step=math.radians(3.0)):
    """Smallest flex angle at joint j of digit k at which the digit beyond the joint touches the rim."""
    bones = [B_IDX[f"{k}_{jj + 1}"] for jj in range(j, 3)]
    # Only the digit's own skin beyond the web: the palm under the knuckles touches the rim by design.
    idx = np.where((hand.W[:, bones].sum(1) > 0.35) & (hand.in_digit == DIGITS.index(k)))[0]

    def touching(theta):
        loc = dict(locals_)
        loc[(k, j)] = _rot(axis, theta) @ locals_.get((k, j), np.eye(3))
        mats = hand.bone_mats(G, G, loc)
        p = hand.skin(mats, idx)
        return float(rim.dist(p).min()) < thresh

    lo = start
    if touching(lo):
        return lo
    th = lo
    while th < stop:
        nxt = min(stop, th + step)
        if touching(nxt):
            a, b = th, nxt
            for _ in range(5):
                mid = 0.5 * (a + b)
                if touching(mid):
                    b = mid
                else:
                    a = mid
            return a
        th = nxt
    return stop


# A power grip curls a finger's three joints together (MCP : PIP : DIP); one angle per finger.
CURL_RATIO = (0.62, 1.0, 0.66)


def _finger_curl(hand, rim, G, locals_, k, axes, thresh, stop=math.radians(118.0), step=math.radians(3.0)):
    """Smallest coupled curl at which the finger's middle and end phalanges meet the rim (the proximal
    phalanx lies along it by design)."""
    bones = [B_IDX[f"{k}_2"], B_IDX[f"{k}_3"]]
    idx = np.where((hand.W[:, bones].sum(1) > 0.35) & (hand.in_digit == DIGITS.index(k)))[0]

    def touching(theta):
        loc = dict(locals_)
        for j in range(3):
            loc[(k, j)] = _rot(axes[j], CURL_RATIO[j] * theta)
        p = hand.skin(hand.bone_mats(G, G, loc), idx)
        return float(rim.dist(p).min()) < thresh

    th = 0.0
    while th < stop:
        nxt = min(stop, th + step)
        if touching(nxt):
            a, b = th, nxt
            for _ in range(6):
                mid = 0.5 * (a + b)
                if touching(mid):
                    b = mid
                else:
                    a = mid
            return a
        th = nxt
    return stop


def solve_grip(hand, rim, side, clock_deg, elbow_hint, turn=0.0, tense=0.0, tap=0.0, looseness=0.0):
    """Hand placement plus finger and thumb rotations wrapping the rim (dict keyed (digit, joint))."""
    G, psi = grip_placement(hand, rim, side, clock_deg, elbow_hint, turn)
    locals_ = {}
    press = math.radians(1.0 + 8.0 * tense)  # resting fingers just meet the rim; fear squeezes
    thresh = rim.r + 0.0007 - 0.0012 * tense
    for order, k in enumerate(FINGERS):
        axes = [hand.flex_axis(k, j, locals_) for j in range(3)]
        theta = _finger_curl(hand, rim, G, locals_, k, axes, thresh)
        # The ring and little fingers of a relaxed hand lie a touch looser on the rim.
        theta += press - math.radians(7.0) * looseness * (0.3 + 0.35 * order)
        for j in range(3):
            locals_[(k, j)] = _rot(axes[j], CURL_RATIO[j] * theta)
    # Thumb: swing across to the driver's side of the rim, over the index finger, then curl.
    rad, tan, ctr = rim.frame(side, clock_deg, turn)
    psi_t = psi + math.radians(85.0)
    target = ctr + (rad * math.cos(psi_t) + rim.F * math.sin(psi_t)) * (rim.r + 0.009) + tan * 0.010
    Rg = G[:3, :3]
    ch = hand.chains["thumb"]
    cmc_w = Rg @ ch[0] + G[:3, 3]
    tip_w = Rg @ ch[3] + G[:3, 3]
    R_w = _rot_between(tip_w - cmc_w, target - cmc_w)
    ang_w = math.acos(max(-1.0, min(1.0, (np.trace(R_w) - 1.0) / 2.0)))
    if ang_w > math.radians(THUMB_SWING_MAX):
        axis_w = _unit(np.array([R_w[2, 1] - R_w[1, 2], R_w[0, 2] - R_w[2, 0], R_w[1, 0] - R_w[0, 1]]))
        R_w = _rot(axis_w, math.radians(THUMB_SWING_MAX))
    locals_[("thumb", 0)] = Rg.T @ R_w @ Rg
    for j in (1, 2):
        ax = hand.flex_axis("thumb", j, locals_)  # rest frame, like every local rotation
        ang = _contact_angle(hand, rim, G, locals_, "thumb", j, ax, -math.radians(25), math.radians(70), thresh + 0.0004)
        locals_[("thumb", j)] = _rot(ax, ang + press * 0.5)
    # Two fingers lift off the rim (the runtime taps them while he talks).
    if tap > 0.0:
        for k, a1, a2 in (("index", 26.0, 20.0), ("middle", 15.0, 12.0)):
            for j, a in ((0, a1), (1, a2)):
                ax = hand.flex_axis(k, j, locals_)
                locals_[(k, j)] = _rot(ax, -math.radians(a) * tap) @ locals_[(k, j)]
    return G, locals_, psi


def place_forearm(hand, G, eric_fa_dir):
    """The forearm stub turns about the wrist to lie along the sleeve's forearm."""
    Rg = G[:3, :3]
    w = Rg @ hand.wrist + G[:3, 3]
    R = _rot_between(Rg @ hand.fa_dir, np.asarray(eric_fa_dir))
    return _about(w, R) @ G


def posed_hand(hand, rim, G, G_fa, locals_):
    mats = hand.bone_mats(G, G_fa, locals_)
    p = hand.skin(mats)
    # Soft tissue: push skin out of the bakelite, then let the push spread to its neighbours so the
    # pads flatten against the rim instead of dimpling vertex by vertex.
    q = rim.push_out(p)
    d = q - p
    for _ in range(4):
        avg = np.zeros_like(d)
        np.add.at(avg, hand.adj_v, d[hand.adj_i])
        avg /= np.maximum(hand.deg, 1.0)[:, None]
        d = d * 0.5 + avg * 0.5
    return rim.push_out(p + d)


def hand_mesh(hand, positions, name, mat, coll):
    """Mesh object of the kept part of the hand (fingers, palm, 6 cm of forearm)."""
    keep = hand.keep
    remap = -np.ones(len(keep), np.int64)
    remap[keep] = np.arange(int(keep.sum()))
    faces, uvs = [], []
    for f, fu in zip(hand.faces, hand.face_uvs):
        if all(keep[v] for v in f):
            faces.append([int(remap[v]) for v in f])
            uvs.append(fu)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(c) for c in positions[keep]], [], faces)
    layer = me.uv_layers.new(name="UVMap")
    li = 0
    for poly, fu in zip(me.polygons, uvs):
        for k, loop_index in enumerate(poly.loop_indices):
            layer.data[loop_index].uv = fu[k]
    for poly in me.polygons:
        poly.use_smooth = True
    me.update()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    if mat:
        me.materials.append(mat)
    return obj


# Where each hand holds the rim: degrees above the horizontal, a hint toward the elbow (chooses the
# palm's roll), and how loose the grip is. Left hand high, about twenty to ten, the right (Sora's side)
# lower and easier, as a driver sits on a long night road.
DRIVER_GRIP = {
    "l": (20.0, (0.50, -0.02, 0.62), 0.25),
    "r": (-6.0, (0.04, -0.02, 0.62), 0.6),
}
DRIVER_SKIN_SRGB = None  # set below from SKIN_CHROMA (one skin for face, neck and hands)


def wrist_frame(hand, G):
    """World wrist joint, wrist->knuckles direction and palm normal of a placed hand."""
    Rg = G[:3, :3]
    return Rg @ hand.wrist + G[:3, 3], _unit(Rg @ hand.fwd), _unit(Rg @ hand.n)


def _box_blur(a, r):
    if r <= 0:
        return a.copy()
    c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode="edge"), 0)
    a = (c[2 * r + 1:] - c[: -2 * r - 1]) / (2 * r + 1)
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)), mode="edge"), 1)
    return (c[:, 2 * r + 1:] - c[:, : -2 * r - 1]) / (2 * r + 1)


def _image_np(img, size):
    im = img.copy()
    im.scale(size, size)
    px = np.empty(size * size * 4, np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(size, size, 4)


def _pack(name, arr, srgb):
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    rgba = arr if arr.shape[-1] == 4 else np.concatenate([arr, np.ones((h, w, 1), np.float32)], -1)
    img.pixels.foreach_set(np.clip(rgba, 0.0, 1.0).astype(np.float32).ravel())
    img.pack()
    return img


def _uv_mask(face_uvs, size, grow=2):
    """Texels of a UV atlas that the mesh actually covers (the rest is padding), grown a little."""
    m = np.zeros((size, size), bool)
    for fu in face_uvs:
        pts = np.asarray(fu, np.float64) * size - 0.5
        for i in range(1, len(pts) - 1):
            a, b, c = pts[0], pts[i], pts[i + 1]
            x0, x1 = int(max(0, np.floor(min(a[0], b[0], c[0])))), int(min(size - 1, np.ceil(max(a[0], b[0], c[0]))))
            y0, y1 = int(max(0, np.floor(min(a[1], b[1], c[1])))), int(min(size - 1, np.ceil(max(a[1], b[1], c[1]))))
            if x1 < x0 or y1 < y0:
                continue
            yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / d
            l2 = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / d
            inside = (l1 >= -0.02) & (l2 >= -0.02) & (1.0 - l1 - l2 >= -0.02)
            m[y0:y1 + 1, x0:x1 + 1] |= inside
    if grow:
        m = _box_blur(m.astype(np.float64), grow) > 0.0
    return m


def _masked_blur(a, mask, r):
    """Box blur of `a` over the masked texels only (padding never bleeds in)."""
    w = _box_blur(mask.astype(np.float64), r)
    return _box_blur(a * mask, r) / np.maximum(w, 1e-6)


def hand_material(src_mat, name="M_taxi_driver_hands_scan", face_uvs=None):
    """The scan's own photo skin, re-toned to the driver's weathered brown and with the forearm hair
    softened; its scanned normal map keeps knuckle creases, veins and nail edges."""
    links = src_mat.node_tree.links
    bc_src = next(l.from_node.image for l in links if l.to_node.type == "BSDF_PRINCIPLED" and l.to_socket.name == "Base Color")
    n_src = next(l.from_node.image for l in links if l.to_node.type == "NORMAL_MAP" and l.from_node.type == "TEX_IMAGE")
    rgba = _image_np(bc_src, 2048)
    rgb = rgba[..., :3].astype(np.float64)
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    hp = lum - _box_blur(lum, 4)
    # The atlas is padded with smeared edge colour: judge the skin by its own texels (pores, hairs
    # and creases give them fine detail), never by the padding.
    detail = _box_blur(np.abs(hp), 6)
    covered = _uv_mask(face_uvs, 2048) if face_uvs is not None else np.ones(lum.shape, bool)
    valid = covered & (lum > 0.12) & (detail > np.percentile(detail[covered], 45))
    med_l = float(np.median(lum[valid]))
    chroma = rgb / np.maximum(lum, 1e-3)[..., None]
    med_c = np.median(chroma[valid], axis=0)
    # His arm hair is fine and dark, not the scan's pale glinting hairs: lift out every bright fleck
    # (a wider look than the pores), keep the dark creases a little softened.
    hp_wide = lum - _box_blur(lum, 7)
    lum2 = lum - np.minimum(hp, 0.0) * 0.35 - np.maximum(hp_wide, 0.0) * 0.92
    # Even out broad patches (a pale knuckle, a hairy wrist) while keeping creases, pores and nails;
    # measured over covered skin only, so no island edge picks up a band of the padding's tone.
    low = np.maximum(_masked_blur(lum2, covered, 48), 1e-3)
    flat = lum2 / low * med_l * (low / med_l) ** 0.2
    shade = np.clip(flat / med_l, 0.3, 1.5) ** 0.95
    dev = np.clip((chroma - med_c) / med_c, -0.5, 0.5)
    out = DRIVER_SKIN_SRGB * shade[..., None] * (1.0 + 0.2 * dev)
    # Padding takes the colour of the skin beside it, so filtering at a seam stays skin.
    pad = np.stack([_masked_blur(out[..., i], covered, 10) for i in range(3)], -1)
    out = np.where(covered[..., None], out, pad)
    bc = _pack("T_taxi_driver_hands_BC", out.astype(np.float32), True)
    # The scan's relief carries every forearm hair and pore: under the cabin's camera-side light they
    # sparkled white. Blur away the hairs, keep knuckles, creases, tendons and nail edges.
    n_vec = _image_np(n_src, 1024)[..., :3].astype(np.float64) * 2.0 - 1.0
    n_vec = np.stack([_box_blur(n_vec[..., i], 3) for i in range(3)], -1)
    n_vec[..., 2] = np.maximum(n_vec[..., 2], 0.2)
    n_vec /= np.linalg.norm(n_vec, axis=-1, keepdims=True)
    nrm = _pack("T_taxi_driver_hands_N", (n_vec * 0.5 + 0.5).astype(np.float32), False)

    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out_n = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.66
    bs.inputs["Metallic"].default_value = 0.0
    t_bc = nt.nodes.new("ShaderNodeTexImage")
    t_bc.image = bc
    t_n = nt.nodes.new("ShaderNodeTexImage")
    t_n.image = nrm
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.55
    nt.links.new(t_bc.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(t_n.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out_n.inputs["Surface"])
    mat["credit"] = str(HAND_CREDIT)
    return mat


# --------------------------------------------------------------------------- cloth-simulated krama

KRAMA_W = 0.26  # metres: a man's cotton krama, folded once lengthwise
KRAMA_TILE = 0.096  # metres: one seamless tile = 6 x 6 checks of 16 mm
ROLL_R = 0.019  # outer radius of the krama rolled round his neck
ROLL_GAP = 0.003  # cotton layers in the roll
KRAMA_LIFT = True  # lift any hanging cloth the simulation left under his clothes


def _wrap_blur(a, r):
    """Box blur that wraps round the edges, so a tile stays seamless."""
    out = a.copy()
    for axis in (0, 1):
        acc = np.zeros_like(out)
        for k in range(-r, r + 1):
            acc += np.roll(out, k, axis=axis)
        out = acc / (2 * r + 1)
    return out


def _krama_textures(size=512):
    """One seamless tile of an old hand-loomed red-and-white krama: 16 mm checks of madder red and
    unbleached cotton whose bands vary a little in width (a hand loom), a thin dark line in each red
    band, the red-by-white squares woven half and half, yarns of uneven dye and thickness, sun-faded.
    Tiled along the cloth it stays crisp up close; the plain-weave relief goes in the normal map."""
    rng = np.random.default_rng(1933)
    n_threads = size // 2  # two texels per yarn (about 0.4 mm)
    yarn = np.arange(size) // 2

    def bands():
        # 6 bands (red, white, red, ...) a hand's-breadth unequal, summing to one tile.
        w = 1.0 + rng.normal(0.0, 0.08, 6)
        edges = np.concatenate([[0.0], np.cumsum(w / w.sum())])
        t = (np.arange(n_threads) + 0.5) / n_threads
        band = np.searchsorted(edges, t, side="right") - 1
        frac = (t - edges[band]) / (edges[band + 1] - edges[band])
        return band % 2 == 0, np.abs(frac - 0.5) < 0.06

    red = np.array([0.40, 0.078, 0.062])
    deep = np.array([0.19, 0.042, 0.046])
    white = np.array([0.66, 0.615, 0.52])

    def threads(is_red, pin):
        col = np.where(is_red[:, None], red, white)
        col = np.where((is_red & pin)[:, None], deep, col)
        col = col * (1.0 + rng.normal(0.0, 0.07, (n_threads, 1)))  # uneven dye lots
        return col[yarn]

    warp_red, warp_pin = bands()
    weft_red, weft_pin = bands()
    warp_col = threads(warp_red, warp_pin)  # rows (v): runs along the krama's width
    weft_col = threads(weft_red, weft_pin)  # columns (u)
    yy, xx = np.mgrid[0:size, 0:size]
    over = (((xx // 2) + (yy // 2)) % 2 == 0)[..., None]
    rgb = np.where(over, warp_col[:, None, :], weft_col[None, :, :]) * 0.7 + (warp_col[:, None, :] + weft_col[None, :, :]) * 0.15
    # Slubs (thick, bright yarn runs) along both thread directions, then broad sun fading.
    slub_w = np.repeat(_wrap_blur(rng.normal(0.0, 1.0, (n_threads, size)), 3)[:, :], 2, 0)[:size] * 0.07
    slub_f = np.repeat(_wrap_blur(rng.normal(0.0, 1.0, (size, n_threads)), 3), 2, 1)[:, :size] * 0.07
    slub = np.where(over[..., 0], slub_w, slub_f)
    fade = 1.0 + _wrap_blur(rng.normal(0.0, 1.0, (size, size)), 20) * 0.7
    rgb = rgb * (1.0 + slub)[..., None] * np.clip(fade, 0.9, 1.08)[..., None]
    rgb = rgb * 0.9 + rgb.mean(-1, keepdims=True) * 0.1  # a little washed out
    bc = _pack("T_taxi_driver_krama_BC", np.clip(rgb, 0.02, 0.9).astype(np.float32), True)
    # Yarn crowns: each yarn a rounded ridge, over/under alternating, the gaps between them dark.
    u_ph = (xx % 2 + 0.5) / 2.0
    v_ph = (yy % 2 + 0.5) / 2.0
    crown = np.where(over[..., 0], np.sin(v_ph * math.pi), np.sin(u_ph * math.pi))
    hgt = crown * 0.7 + slub * 3.0
    gx = np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)
    gy = np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)
    nrm = np.stack([-gx * 0.5, -gy * 0.5, np.ones_like(gx)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    n_img = _pack("T_taxi_driver_krama_N", (nrm * 0.5 + 0.5).astype(np.float32), False)
    return bc, n_img


def _krama_material():
    bc, n_img = _krama_textures()
    old = bpy.data.materials.get("M_cab_driver_krama")
    if old:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new("M_cab_driver_krama")
    mat.use_nodes = True
    mat.use_backface_culling = False
    nt = mat.node_tree
    nt.nodes.clear()
    out_n = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.92
    bs.inputs["Metallic"].default_value = 0.0
    t_bc = nt.nodes.new("ShaderNodeTexImage")
    t_bc.image = bc
    t_n = nt.nodes.new("ShaderNodeTexImage")
    t_n.image = n_img
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.5
    nt.links.new(t_bc.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(t_n.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out_n.inputs["Surface"])
    return mat


def _catmull(ctrl, per=6):
    out = []
    n = len(ctrl)
    for i in range(n - 1):
        p0, p1, p2, p3 = ctrl[max(0, i - 1)], ctrl[i], ctrl[i + 1], ctrl[min(n - 1, i + 2)]
        for s in range(per):
            t = s / per
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(ctrl[-1])
    return np.array(out)


def _resample(path, n):
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(t, s, path[:, i]) for i in range(3)], 1), s[-1]


def _surface_bvh(objs):
    bm = bmesh.new()
    for o in objs:
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        tmp.transform(o.matrix_world)
        me = bpy.data.meshes.new("_tmp_surface")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


def _noise1(rng, n, scale):
    """Smooth 1-D noise over n samples (blurred random walk), unit-ish amplitude."""
    x = rng.normal(0.0, 1.0, n + 2 * scale)
    k = np.hanning(2 * scale + 1)
    k /= k.sum()
    y = np.convolve(x, k, mode="same")[scale:scale + n]
    return y / max(1e-6, np.abs(y).max())


def _neck_opening(body, near_xy):
    """The body mesh's collar opening: centre (x, y), height, and its radius by angle (degrees, 0 =
    toward his front, 90 = his left)."""
    bm = bmesh.new()
    bm.from_mesh(body.data)
    from collections import defaultdict

    adj = defaultdict(list)
    for e in bm.edges:
        if e.is_boundary:
            a, b = e.verts
            adj[a.index].append(b.index)
            adj[b.index].append(a.index)
    bm.verts.ensure_lookup_table()
    seen, best = set(), None
    for s0 in adj:
        if s0 in seen:
            continue
        loop, cur = [s0], s0
        seen.add(s0)
        while True:
            nxt = [n for n in adj[cur] if n not in seen]
            if not nxt:
                break
            cur = nxt[0]
            seen.add(cur)
            loop.append(cur)
        co = np.array([bm.verts[i].co[:] for i in loop])
        c = co.mean(0)
        d = math.hypot(c[0] - near_xy[0], c[1] - near_xy[1])
        if c[2] > 0.78 and d < 0.08 and (best is None or d < best[0]):
            best = (d, co, c)
    bm.free()
    _, co, c = best
    ang = np.degrees(np.arctan2(co[:, 0] - c[0], -(co[:, 1] - c[1])))
    rad = np.hypot(co[:, 0] - c[0], co[:, 1] - c[1])
    order = np.argsort(ang)
    return (float(c[0]), float(c[1])), float(co[:, 2].max()), (ang[order], rad[order])


def build_rolled_krama(coll, body, colliders, neck_xy, frames=48):
    """A krama as Khmer men wear one: folded lengthwise, rolled into a soft twisted roll that lies round
    the base of the neck on the shoulders, and unrolling at the collarbones into two ends that hang down
    his chest (the left one longer). The roll keeps its shape; the ends are cloth-simulated onto his
    chest and belly. Returns the mesh object (its shape keys come later from `bind_to_body`)."""
    nx, ny = float(neck_xy[0]) - 0.005, float(neck_xy[1]) - 0.02
    ring_c, ring_z, ring_r = _neck_opening(body, (nx, ny))

    def on_ring(deg, out=0.004, up=0.013):
        a_ = math.radians(deg)
        r = float(np.interp(deg, ring_r[0], ring_r[1], period=360.0)) + out
        return (ring_c[0] + math.sin(a_) * r, ring_c[1] - math.cos(a_) * r, ring_z + up)

    # Centre line (cabin metres): the left end up his chest to the left collarbone, the roll lying over
    # the collar opening round the back of the neck, then the right collarbone and the right end down.
    lx, rx = ring_c[0] + 0.080, ring_c[0] - 0.074
    ctrl = np.array([
        (lx + 0.006, -0.072, 0.545), (lx + 0.004, -0.068, 0.610), (lx + 0.002, -0.060, 0.680),
        (lx, -0.046, 0.745), (lx - 0.006, -0.022, 0.805), on_ring(78, 0.010, 0.006),
        on_ring(100, 0.0), on_ring(125, -0.004), on_ring(150, -0.006), on_ring(180, -0.006, 0.015),
        on_ring(-150, -0.006), on_ring(-125, -0.004), on_ring(-100, 0.0), on_ring(-78, 0.010, 0.006),
        (rx + 0.004, -0.022, 0.803), (rx, -0.044, 0.742), (rx - 0.002, -0.056, 0.675),
        (rx - 0.004, -0.062, 0.615),
    ])
    bvh = _surface_bvh([o for o in colliders if o is not None])
    rolled_of_z = lambda z: _sstep(ring_z - 0.010, ring_z - 0.085, z)  # 0 in the roll, 1 down the chest
    snapped = []
    for c in ctrl:
        t = rolled_of_z(c[2])
        if t < 0.25:
            snapped.append(np.array(c))  # the roll lies where it is put, on the collar
            continue
        hit = bvh.find_nearest(Vector(c), 0.3)
        nrm = np.array(hit[1][:])
        q = np.array(hit[0][:])
        # Outward = away from the vertical axis through his neck and chest.
        if nrm @ (q - np.array([ring_c[0], ring_c[1] - 0.02, q[2]])) < 0.0:
            nrm = -nrm
        off = (1.0 - t) * (ROLL_R * 0.8 + 0.0015) + t * 0.0055
        snapped.append(q + nrm * off)
    path, _ = _resample(_catmull(np.array(snapped), 10), 600)
    n_len, n_wid = 190, 56
    centre, L = _resample(path, n_len + 1)
    tng = np.array([_unit(centre[min(n_len, i + 1)] - centre[max(0, i - 1)]) for i in range(n_len + 1)])
    outs = []
    for c in centre:
        hit = bvh.find_nearest(Vector(c), 0.3)
        o = np.array(hit[1][:])
        q = np.array(hit[0][:])
        outs.append(-o if o @ (q - np.array([ring_c[0], ring_c[1] - 0.02, q[2]])) < 0.0 else o)
    outs = np.array(outs)
    for _ in range(12):
        outs[1:-1] = (outs[:-2] + outs[1:-1] * 2.0 + outs[2:]) * 0.25
    for i in range(n_len + 1):
        outs[i] = _unit(outs[i] - tng[i] * (outs[i] @ tng[i]))
        if i and outs[i] @ outs[i - 1] < 0.0:
            outs[i] = -outs[i]
    across = np.array([_unit(np.cross(tng[i], outs[i])) for i in range(n_len + 1)])

    rng = np.random.default_rng(1936)
    u_arc = np.linspace(0.0, L, n_len + 1)
    unroll = np.array([rolled_of_z(c[2]) for c in centre])
    unroll = unroll * unroll * (3.0 - 2.0 * unroll)
    # The roll's outer edge winds round it about once every 24 cm, unevenly, as a hand twists cloth.
    twist = u_arc * (math.tau / 0.24) + 1.2 * _noise1(rng, n_len + 1, 14)
    swell = 1.0 + 0.14 * _noise1(rng, n_len + 1, 6)
    k_sp = ROLL_GAP / math.tau
    v_s = np.linspace(0.0, KRAMA_W, n_wid + 1)
    # Arc length from the outer edge inward along the spiral r = R - k*theta.
    disc = np.maximum(ROLL_R * ROLL_R - 2.0 * k_sp * v_s, 1e-9)
    theta = (ROLL_R - np.sqrt(disc)) / k_sp
    r_sp = ROLL_R - k_sp * theta
    # Hanging ends: the folded cloth gathers to ~70% width in three soft vertical folds.
    fold_ph = rng.uniform(0.0, math.tau, 3)
    verts, uvs, rolled_w = [], [], []
    for i in range(n_len + 1):
        t = unroll[i]
        sp_a = r_sp * swell[i] * np.cos(theta + twist[i])
        sp_o = r_sp * swell[i] * np.sin(theta + twist[i]) * 0.78
        fl_a = (v_s - KRAMA_W * 0.5) * 0.50
        fl_o = 0.0070 * np.sin(v_s / KRAMA_W * math.tau * 2.0 + fold_ph[0] + u_arc[i] * 3.0) \
            + 0.0030 * np.sin(v_s / KRAMA_W * math.tau * 3.5 + fold_ph[1])
        a_ = sp_a * (1.0 - t) + fl_a * t
        o_ = sp_o * (1.0 - t) + fl_o * t
        for j in range(n_wid + 1):
            verts.append(centre[i] + across[i] * a_[j] + outs[i] * o_[j])
            uvs.append((u_arc[i] / KRAMA_TILE, v_s[j] / KRAMA_TILE))
            rolled_w.append(1.0 - t)
    # The hanging ends must start in front of his outermost layer: one straddling the waistcoat's open
    # front edge started half behind it, and the simulation dragged the whole end under the waistcoat.
    # (Looking straight back from in front of his chest: the ends hang over his front.)
    fwd = Vector((0.0, -1.0, 0.0))
    for i in range(n_len + 1):
        if unroll[i] < 0.4:
            continue
        for j in range(n_wid + 1):
            k = i * (n_wid + 1) + j
            p = Vector(verts[k])
            hit = bvh.ray_cast(p + fwd * 0.15, -fwd, 0.3)
            if hit[0] is not None:
                depth = (hit[0] - p).dot(fwd)  # > 0: the vertex lies behind the frontmost surface
                if depth > -0.004:
                    verts[k] = np.array((p + fwd * (depth + 0.004))[:])
    faces = []
    for i in range(n_len):
        for j in range(n_wid):
            q = i * (n_wid + 1) + j
            faces.append((q, q + 1, q + n_wid + 2, q + n_wid + 1))
    me = bpy.data.meshes.new("taxi_driver_krama")
    me.from_pydata([tuple(p) for p in verts], [], faces)
    layer = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]
    obj = bpy.data.objects.new("taxi_driver_krama", me)
    coll.objects.link(obj)
    pin = obj.vertex_groups.new(name="roll")
    for vi, wgt in enumerate(rolled_w):
        pin.add([vi], float(min(1.0, wgt * 1.6)), "REPLACE")

    # Cloth: the roll holds its shape (pinned), the ends fall and settle on his chest. Only the body
    # collides: the roll rests against the neck, and a pinned roll inside the head's collider threw the
    # ends through his chest.
    added = []
    for c_obj in (body,):
        if c_obj is None:
            continue
        m = c_obj.modifiers.new("krama_collision", "COLLISION")
        c_obj.collision.thickness_outer = 0.003
        c_obj.collision.cloth_friction = 10.0
        # Double-sided: the scanned clothes are open shells whose normals are not all outward, and a
        # single-sided collider pushed cloth through them.
        c_obj.collision.use_culling = False
        added.append((c_obj, m.name))
    cl = obj.modifiers.new("cloth", "CLOTH")
    st = cl.settings
    st.quality = 7
    st.mass = 0.2
    st.tension_stiffness = 15.0
    st.compression_stiffness = 15.0
    st.shear_stiffness = 5.0
    st.bending_stiffness = 0.6
    st.air_damping = 2.0
    st.vertex_group_mass = "roll"
    st.pin_stiffness = 2.0
    cs = cl.collision_settings
    cs.distance_min = 0.0025
    cs.use_self_collision = False
    cs.collision_quality = 3
    sc = bpy.context.scene
    cl.point_cache.frame_start = 1
    cl.point_cache.frame_end = frames
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear()
    old_me = obj.data
    obj.data = baked
    bpy.data.meshes.remove(old_me)
    baked.name = "taxi_driver_krama"
    sc.frame_set(1)
    for c_obj, name in added:
        c_obj.modifiers.remove(c_obj.modifiers[name])
    obj.vertex_groups.clear()
    # Any of the hanging cloth left under his clothes comes back out (1.5 mm above them), the lift
    # spread over its neighbours so the folds keep their shape.
    body_bvh = _surface_bvh([body])
    me = obj.data
    co = np.array([v.co[:] for v in me.vertices])
    lift = np.zeros_like(co)
    for i, p in enumerate(co):
        if rolled_w[i] >= 0.5:
            continue
        hit = body_bvh.find_nearest(Vector(p), 0.03)
        if hit[0] is None:
            continue
        nrm = np.array(hit[1][:])
        q = np.array(hit[0][:])
        if nrm @ (q - np.array([ring_c[0], ring_c[1] - 0.02, q[2]])) < 0.0:
            nrm = -nrm
        gap = (p - q) @ nrm
        if gap < 0.0:
            lift[i] = nrm * (0.0015 - gap)
    inside = int((np.abs(lift).sum(1) > 0).sum())
    if inside and KRAMA_LIFT:
        ei = np.array([e.vertices[:] for e in me.edges], np.int64)
        for _ in range(4):
            acc = np.zeros_like(lift)
            cnt = np.zeros(len(co))
            np.add.at(acc, ei[:, 0], lift[ei[:, 1]])
            np.add.at(acc, ei[:, 1], lift[ei[:, 0]])
            np.add.at(cnt, ei[:, 0], 1)
            np.add.at(cnt, ei[:, 1], 1)
            lift = np.maximum.reduce([lift, acc / np.maximum(cnt, 1)[:, None]]) if False else np.where(
                (np.linalg.norm(lift, axis=1) >= np.linalg.norm(acc / np.maximum(cnt, 1)[:, None], axis=1))[:, None],
                lift, acc / np.maximum(cnt, 1)[:, None])
        me.vertices.foreach_set("co", (co + lift).astype(np.float32).ravel())
    print("TAXI_KRAMA_LIFTED_OUT", inside)

    _add_fringe_by_uv(obj)
    mat = _krama_material()
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def _add_fringe_by_uv(obj, count=20):
    """Knotted cotton fringe at both ends (found by their UV), 2-3 cm tassels hanging with gravity."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    v_uv = {}
    for f in bm.faces:
        for lp in f.loops:
            v_uv[lp.vert.index] = lp[uv].uv.copy()
    bm.verts.ensure_lookup_table()
    us = np.array([v_uv[v.index].x for v in bm.verts])
    vs = np.array([v_uv[v.index].y for v in bm.verts])
    co = np.array([v.co[:] for v in bm.verts])
    rng = np.random.default_rng(7)
    white_uv = (0.25, 0.25)
    step = 0.012 / KRAMA_TILE
    for u_end, inward in ((us.min(), 1.0), (us.max(), -1.0)):
        edge = np.where(np.abs(us - u_end) < 1e-6)[0]
        edge = edge[np.argsort(vs[edge])]
        inner = np.where(np.abs(us - (u_end + inward * step)) < step * 0.6)[0]
        out_dir = _unit(co[edge].mean(0) - co[inner].mean(0)) if len(inner) else np.array([0.0, 0.0, -1.0])
        e_v = vs[edge]
        for t in range(count):
            fv = e_v[0] + (t + 0.5) / count * (e_v[-1] - e_v[0])
            j = min(len(edge) - 2, int(np.searchsorted(e_v, fv)) - 1)
            j = max(0, j)
            fr = (fv - e_v[j]) / max(1e-9, e_v[j + 1] - e_v[j])
            base = co[edge[j]] * (1 - fr) + co[edge[j + 1]] * fr
            side = _unit(co[edge[j + 1]] - co[edge[j]])
            length = 0.022 + rng.random() * 0.010
            down = _unit(out_dir * 0.35 + np.array([rng.normal(0, 0.08), rng.normal(0, 0.08), -1.0]))
            pts = [base, base + down * 0.004, base + down * 0.0055, base + down * (length * 0.6), base + down * length]
            widths = (0.0022, 0.0026, 0.0018, 0.0014, 0.0008)
            normal_side = _unit(np.cross(down, side))
            ring = []
            for p, wdt in zip(pts, widths):
                a = bm.verts.new(p - side * wdt * 0.5)
                b = bm.verts.new(p + side * wdt * 0.5)
                c = bm.verts.new(p + normal_side * wdt * 0.35)
                ring.append((a, c, b))
            for r0, r1 in zip(ring, ring[1:]):
                for k in range(3):
                    k2 = (k + 1) % 3
                    face = bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
                    for lp in face.loops:
                        lp[uv].uv = white_uv
    bm.to_mesh(me)
    bm.free()


def bind_to_body(obj, body, shape_names):
    """Shape keys on `obj` that follow the body's own shape keys (surface-deform binding)."""
    mod = obj.modifiers.new("follow_body", "SURFACE_DEFORM")
    mod.target = body
    mod.falloff = 4.0
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    with bpy.context.temp_override(object=obj, active_object=obj):
        bpy.ops.object.surfacedeform_bind(modifier=mod.name)
    keys = body.data.shape_keys.key_blocks
    obj.shape_key_add(name="Basis", from_mix=False)
    for name in shape_names:
        if name not in keys:
            continue
        for kb in keys:
            kb.value = 1.0 if kb.name == name else 0.0
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        pts = np.array([v.co[:] for v in ev.data.vertices], np.float32)
        kb_new = obj.shape_key_add(name=name, from_mix=False)
        kb_new.data.foreach_set("co", pts.ravel())
        kb_new.value = 0.0
    for kb in keys:
        kb.value = 0.0
    obj.modifiers.remove(mod)


def smooth_neck(head, passes=16, lam=0.5, mu=-0.53):
    """Ease the photoscan's lower cheek, jaw, under-chin and neck (head frame, below the ear lobes) so
    they read as skin, not polygon facets or the scan's creases. Taubin smoothing (a shrink step, then a swell step) keeps the jaw's
    volume; the lips, chin front, ears and the open bottom edge are left as they are, and the effect
    fades out over the 2 cm below the lobes."""
    bm = bmesh.new()
    bm.from_mesh(head.data)
    weight = {}
    for v in bm.verts:
        c = v.co
        if v.is_boundary or c.z > 1.955:
            continue
        if c.y < -0.055 and c.z > 1.852:  # lips and the front of the chin keep their shape
            continue
        w_low = _sstep(1.937, 1.915, c.z)
        # The lower cheek and the jaw's side up to the ear lobe (the scan creased there), never the ear.
        side = abs(c.x) > 0.03 and c.y > -0.05 and abs(c.x) < 0.07
        w_side = _sstep(1.958, 1.935, c.z) * (1.0 if side else 0.0)
        w = max(w_low, w_side)
        if w > 0.0:
            weight[v] = w
    for _ in range(passes):
        for f in (lam, mu):
            disp = {}
            for v, w in weight.items():
                nbs = [e.other_vert(v) for e in v.link_edges]
                if nbs and w > 0.0:
                    disp[v] = (sum((nb.co for nb in nbs), Vector()) / len(nbs) - v.co) * (f * w)
            for v, d in disp.items():
                v.co += d
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()
    return len(weight)


# --------------------------------------------------------------------------- one natural skin

# A Khmer man's sun-browned skin as a colour direction (sRGB divided by luminance): brown with an olive
# warmth, not the old curve's orange (which ran about 1.36 : 0.86 : 0.58).
SKIN_CHROMA = np.array([1.27, 0.93, 0.70])
DRIVER_SKIN_SRGB = SKIN_CHROMA * 0.37  # his hands, a shade darker than his face


def regrade_skin(rgb, strength=0.92, lum_scale=1.0):
    """Move a photo's skin toward SKIN_CHROMA, keeping each pixel's luminance and its own deviation from
    the skin's median colour (rosier lips, darker creases, stubble). Hair, eyes and cloth stay."""
    rgb = rgb.astype(np.float64)
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    skin = (rgb[..., 0] > rgb[..., 1]) & (rgb[..., 1] > rgb[..., 2] * 0.9) & (lum > 0.07) & (lum < 0.92)
    w = skin * np.clip((sat - 0.10) / 0.14, 0.0, 1.0) * np.clip((lum - 0.06) / 0.08, 0.0, 1.0)
    c = rgb / np.maximum(lum, 1e-3)[..., None]
    core = w > 0.6
    c_med = np.median(c[core], axis=0) if core.any() else SKIN_CHROMA
    new_c = c + (SKIN_CHROMA - c_med)[None, None, :] * (w * strength)[..., None]
    out = new_c * (lum * (1.0 + (lum_scale - 1.0) * w))[..., None]
    return np.clip(out, 0.0, 1.0).astype(np.float32), c_med


def skin_patch_from_face(head, image, centre, radius=0.012, size=256):
    """A seamless tile of the face photo's own skin (pores, fine stubble, creases) around a point of the
    head (head frame), as a luminance detail layer centred on 1.0."""
    me = head.data
    uv = me.uv_layers.active.data
    us, vs = [], []
    for poly in me.polygons:
        if (poly.center - Vector(centre)).length < radius:
            for li in poly.loop_indices:
                us.append(uv[li].uv.x)
                vs.append(uv[li].uv.y)
    w, h = image.size
    px = np.empty(w * h * 4, np.float32)
    image.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[..., :3]
    if not us:
        return np.ones((size, size), np.float32)
    u0, u1 = int(min(us) * w), int(max(us) * w)
    v0, v1 = int(min(vs) * h), int(max(vs) * h)
    crop = px[max(0, v0):max(v0 + 8, v1), max(0, u0):max(u0 + 8, u1)]
    lum = crop @ np.array([0.299, 0.587, 0.114], np.float32)
    detail = lum / np.maximum(_box_blur(lum, 12), 1e-3)
    # resample to size x size, then mirror-blend the edges so it tiles without a seam
    yy = (np.arange(size) * detail.shape[0] / size).astype(np.int64)
    xx = (np.arange(size) * detail.shape[1] / size).astype(np.int64)
    tile = detail[np.ix_(yy, xx)]
    ramp = np.clip(np.minimum(np.arange(size), size - 1 - np.arange(size)) / (size * 0.18), 0.0, 1.0)
    mask = np.minimum(ramp[:, None], ramp[None, :])
    tile = tile * mask + np.roll(np.roll(tile, size // 2, 0), size // 2, 1) * (1.0 - mask)
    return np.clip(tile, 0.75, 1.25).astype(np.float32)


# --------------------------------------------------------------------------- face texture seams

def heal_uv_seams(bm, uv_layer, colour, normal=None, region=None, radius=5, max_diff=0.3):
    """Along every UV seam (an edge whose two faces map it to different places in the atlas), give both
    sides the average of their colours and flatten the relief map right at the seam. The face scan's
    bake left a dark line and a glint along the jaw seam that read as scratches."""
    H, W = colour.shape[:2]
    nh, nw = (normal.shape[:2] if normal is not None else (0, 0))
    yy, xx = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    falloff = np.clip(1.0 - np.hypot(xx, yy) / (radius + 0.5), 0.0, 1.0) ** 1.5 * 0.92
    healed = 0

    def paint(img, u, v, value, fall):
        h, w = img.shape[:2]
        cx, cy = int(u * w), int(v * h)
        x0, x1 = max(0, cx - radius), min(w, cx + radius + 1)
        y0, y1 = max(0, cy - radius), min(h, cy + radius + 1)
        if x0 >= x1 or y0 >= y1:
            return
        f = fall[(y0 - cy + radius):(y1 - cy + radius), (x0 - cx + radius):(x1 - cx + radius)][..., None]
        img[y0:y1, x0:x1, :3] = img[y0:y1, x0:x1, :3] * (1.0 - f) + value * f

    flat = np.array([0.5, 0.5, 1.0], np.float32)
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        if region is not None and not region((e.verts[0].co + e.verts[1].co) * 0.5):
            continue
        fa, fb = e.link_faces
        v0, v1 = e.verts
        uv = {}
        for f in (fa, fb):
            for lp in f.loops:
                if lp.vert in (v0, v1):
                    uv[(f, lp.vert)] = lp[uv_layer].uv.copy()
        try:
            a0, a1, b0, b1 = uv[(fa, v0)], uv[(fa, v1)], uv[(fb, v0)], uv[(fb, v1)]
        except KeyError:
            continue
        if (a0 - b0).length < 1e-5 and (a1 - b1).length < 1e-5:
            continue
        n = max(2, int((a0 - a1).length * W / 2.0))
        for i in range(n + 1):
            t = i / n
            ua, ub = a0.lerp(a1, t), b0.lerp(b1, t)
            ca = colour[min(H - 1, int(ua.y * H)), min(W - 1, int(ua.x * W)), :3]
            cb = colour[min(H - 1, int(ub.y * H)), min(W - 1, int(ub.x * W)), :3]
            if np.abs(ca - cb).max() > max_diff:
                continue
            m = (ca + cb) * 0.5
            paint(colour, ua.x, ua.y, m, falloff)
            paint(colour, ub.x, ub.y, m, falloff)
            if normal is not None:
                paint(normal, ua.x, ua.y, flat, falloff * 0.8)
                paint(normal, ub.x, ub.y, flat, falloff * 0.8)
        healed += 1
    print("TAXI_FACE_SEAMS_HEALED", healed)
    return healed


def repaint_skin_patch(bm, uv_layer, colour, normal, centres, radius, head=None, image=None):
    """Relax the shape round each centre (head frame) and repaint its texels as softened skin with the
    pores of his own clean jaw, flattening the relief there: removes a scan crease for good."""
    near = [f for f in bm.faces if any((f.calc_center_median() - c).length < radius for c in centres)]
    if not near:
        return 0
    # Shape: shrink-free relax of the patch (the edge of the patch fades out).
    verts = {v for f in near for v in f.verts if not v.is_boundary}
    for _ in range(14):
        for fac in (0.5, -0.53):
            disp = {}
            for v in verts:
                w = max(0.0, 1.0 - min((v.co - c).length for c in centres) / radius)
                nbs = [e.other_vert(v) for e in v.link_edges]
                if nbs and w > 0.0:
                    disp[v] = (sum((nb.co for nb in nbs), Vector()) / len(nbs) - v.co) * (fac * w)
            for v, d in disp.items():
                v.co += d
    # Texels: rasterise the patch's UV triangles into a mask.
    H, W = colour.shape[:2]
    mask = np.zeros((H, W), np.float32)
    for f in near:
        w_f = max(0.0, 1.0 - min((f.calc_center_median() - c).length for c in centres) / radius)
        uvs = [lp[uv_layer].uv for lp in f.loops]
        for i in range(1, len(uvs) - 1):
            tri = np.array([[uvs[0].x * W, uvs[0].y * H], [uvs[i].x * W, uvs[i].y * H], [uvs[i + 1].x * W, uvs[i + 1].y * H]])
            x0, y0 = np.floor(tri.min(0)).astype(int)
            x1, y1 = np.ceil(tri.max(0)).astype(int)
            x0, y0, x1, y1 = max(0, x0 - 2), max(0, y0 - 2), min(W, x1 + 3), min(H, y1 + 3)
            if x1 <= x0 or y1 <= y0:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
            (ax_, ay_), (bx_, by_), (cx_, cy_) = tri
            den = (by_ - cy_) * (ax_ - cx_) + (cx_ - bx_) * (ay_ - cy_)
            if abs(den) < 1e-9:
                continue
            l1 = ((by_ - cy_) * (xx - cx_) + (cx_ - bx_) * (yy - cy_)) / den
            l2 = ((cy_ - ay_) * (xx - cx_) + (ax_ - cx_) * (yy - cy_)) / den
            inside = (l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)
            mask[y0:y1, x0:x1] = np.maximum(mask[y0:y1, x0:x1], inside * w_f)
    mask = np.clip(_box_blur(mask, 3) * 1.4, 0.0, 1.0)
    sel = mask > 0.001
    if not sel.any():
        return 0
    ys, xs = np.where(sel)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    sub = colour[y0:y1, x0:x1, :3]
    soft = np.stack([_box_blur(sub[..., i], 14) for i in range(3)], -1)
    pores = np.ones(sub.shape[:2], np.float32)
    if head is not None and image is not None:
        tile = skin_patch_from_face(head, image, (-0.004 + 0.055, -0.035, 1.875), radius=0.014, size=256)
        reps = np.tile(tile, (sub.shape[0] // 256 + 1, sub.shape[1] // 256 + 1))[: sub.shape[0], : sub.shape[1]]
        pores = reps
    m = mask[y0:y1, x0:x1][..., None]
    colour[y0:y1, x0:x1, :3] = sub * (1.0 - m) + soft * pores[..., None] * m
    if normal is not None:
        nh, nw = normal.shape[:2]
        my = (np.arange(nh) * H / nh).astype(int)
        mx = (np.arange(nw) * W / nw).astype(int)
        nm = mask[np.ix_(my, mx)][..., None]
        normal[..., :3] = normal[..., :3] * (1.0 - nm) + np.array([0.5, 0.5, 1.0], np.float32) * nm
    print("TAXI_CHEEK_CREASES_REPAINTED", len(near), int(sel.sum()))
    return len(near)
