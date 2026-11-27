"""Episode 1's taxi driver from the studio's own sculpt (`art-source/library/scans/taxi_driver_tripo.glb`).

The sculpt (made with Tripo on the studio's paid plan) is one 4.9M-triangle surface of a seated man at
the wheel: a newsboy cap, a work shirt with a collar, placket, chest pocket and cuffed long sleeves, an
open sleeveless vest, a belt, trousers and tall leather boots. It has no UVs and no colour. This module
fits him into the Rosalie and dresses him:

1. **Fit.** He is scaled to a real man (head 22 cm, crown to chin), turned to face the road, sat on the
   driver's cushion with his back on the seatback. His own small wheel is cut away; the cabin's wheel
   takes its place, and each hand is eased out onto its rim (the arm follows, fading out by the shoulder)
   and closed round its thinner tube.
2. **Colour.** Each garment is found on the surface (rough regions, then the boundary snapped to the
   sculpt's own seam groove), painted as vertex colour on the full sculpt with cavity dirt, wear and skin
   variation, and baked with its relief onto a 110k-triangle game mesh with its own UVs.
3. **Life.** Shape keys for the runtime: the hands turn with the wheel, clench, he breathes, leans to
   peer, turns his head to the road and to Sora, nods and talks.

Run from `taxi_people_refine.apply_people_realism` (inside the cabin build).
"""
import heapq
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art-source/library/scans/taxi_driver_tripo.glb"
CREDIT = {
    "title": "Taxi driver at the wheel",
    "author": "The studio (made with Tripo AI on the studio's paid plan)",
    "license": "Studio-owned",
}

# ---------------------------------------------------------------- measured fit (the file's own frame)
SCALE = 1.18  # the file is normalised to 1 unit tall; this makes his head 22 cm, crown to chin
FILE_FWD = (0.765, -0.644)  # the way he faces in the file (horizontal)
FILE_ANCHOR = Vector((-0.20, 0.10, 0.255))  # over his seat, in the file
CABIN_ANCHOR = Vector((0.185, 0.04, 0.31))  # on the driver's cushion, back on the seatback
# His own wheel, fitted to the rim's clear stretches: centre, axis (away from him), radius, tube. The
# sculpted rim is not quite round (up to 7 mm out), so the cut follows a centre line measured every 5°.
OWN_WHEEL_C = Vector((0.0455, 0.0052, 0.6414))
OWN_WHEEL_N = Vector((0.6855, -0.5807, -0.4391)).normalized()
OWN_WHEEL_R = 0.1319
OWN_TUBE = 0.015
OWN_SPOKES = (-158.9, -32.2, 95.9)  # degrees, in the wheel basis below (each axis is refitted)
OWN_SPOKE_R = 0.0135
HAND_ANGLE = {"l": -147.0, "r": -15.0}  # where each hand holds his wheel (his left, his right)
HAND_SECTOR = {"l": (-176.0, -114.0), "r": (-46.0, 16.0)}

# Landmarks picked on the sculpt (file frame): his face, ears and hairline, and his arm joints.
FACE = {
    "eye_r": (-0.1244, 0.1010, 0.9034),
    "eye_l": (-0.1108, 0.1489, 0.9024),
    "brow_r_in": (-0.1109, 0.1113, 0.9121),
    "brow_r_out": (-0.1303, 0.0906, 0.9104),
    "brow_l_in": (-0.1022, 0.1319, 0.9121),
    "brow_l_out": (-0.1085, 0.1625, 0.9098),
    "nose_tip": (-0.0880, 0.1166, 0.8697),
    "mouth_c": (-0.1019, 0.1186, 0.8469),
    "mouth_r": (-0.1197, 0.1051, 0.8464),
    "mouth_l": (-0.1061, 0.1391, 0.8469),
    "lip_top": (-0.0998, 0.1180, 0.8522),
    "lip_bot": (-0.1046, 0.1194, 0.8401),
    "chin": (-0.1139, 0.1222, 0.8183),
    "ear_r": (-0.2011, 0.0946, 0.8837),
    "temple_hair_r": (-0.1811, 0.0846, 0.9168),
    "nape_hair": (-0.2333, 0.1023, 0.8700),
    "sideburn_low_r": (-0.1843, 0.0881, 0.8934),
    "shoulder_r": (-0.3054, 0.0669, 0.7423),
    "elbow_r": (-0.2631, -0.0407, 0.6067),
    "shoulder_l": (-0.0926, 0.3197, 0.7423),
    "elbow_l": (0.0163, 0.2780, 0.6406),
}

# The Rosalie's wheel (Blender cabin frame: the car faces -y, the driver sits at +x).
WHEEL_CENTER = Vector((0.2641, -0.2722, 0.7636))
WHEEL_NORMAL = Vector((0.0, 0.7676, 0.6410)).normalized()  # toward the driver
RIM_R = 0.1974
RIM_TUBE = 0.0127


def placement():
    yaw = -math.pi / 2 - math.atan2(FILE_FWD[1], FILE_FWD[0])
    return (
        Matrix.Translation(CABIN_ANCHOR)
        @ Matrix.Rotation(yaw, 4, "Z")
        @ Matrix.Scale(SCALE, 4)
        @ Matrix.Translation(-FILE_ANCHOR)
    )


def own_wheel():
    """His wheel in the cabin frame: centre, axis (away from him), basis (e1, e2), radius, tube."""
    M = placement()
    C = M @ OWN_WHEEL_C
    N = (M.to_3x3() @ OWN_WHEEL_N).normalized()
    e1 = N.cross(Vector((0, 0, 1))).normalized()
    e2 = N.cross(e1)
    return C, N, e1, e2, OWN_WHEEL_R * SCALE, OWN_TUBE * SCALE


def _arrays(me):
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    return co.reshape(n, 3).astype(np.float64)


def _edges(me):
    ed = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ed)
    return ed.reshape(-1, 2)


def load_sculpt(name="taxi_driver_sculpt"):
    """Import the sculpt and set it in the driver's seat (mesh data in cabin metres)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    new = [o for o in bpy.data.objects if o not in before]
    mesh = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.polygons))
    mesh.data.transform(mesh.matrix_world)
    mesh.parent = None
    mesh.matrix_world = Matrix.Identity(4)
    for o in new:
        if o is not mesh:
            bpy.data.objects.remove(o, do_unlink=True)
    mesh.data.transform(placement())
    mesh.data.update()
    mesh.name = name
    return mesh


def _wheel_coords(co):
    C, N, e1, e2, R, tube = own_wheel()
    C, N, e1, e2 = (np.array(v) for v in (C, N, e1, e2))
    v = co - C
    h = v @ N
    rad = v - np.outer(h, N)
    rl = np.linalg.norm(rad, axis=1)
    ang = np.degrees(np.arctan2(rad @ e2, rad @ e1))
    return h, rl, ang, R, tube


def _in_sector(ang, lo, hi):
    return (ang > lo) & (ang < hi)


def rim_centreline(co, step=5.0):
    """His rim's centre line, measured: for each 5° sector clear of his hands, the middle of the tube's
    cross-section (radius r and height h in the wheel frame); across each grip it is interpolated.
    Returns (angles, r, h) for linear interpolation round the wheel."""
    h, rl, ang, R, tube = _wheel_coords(co)
    near = np.sqrt(h * h + (rl - R) ** 2) < 2.4 * tube
    A, Rs, Hs = [], [], []
    for a0 in np.arange(-180.0, 180.0, step):
        if any(_in_sector(np.array([a0]), lo, hi)[0] for lo, hi in HAND_SECTOR.values()):
            continue
        m = near & (np.abs(((ang - a0 + 180.0) % 360.0) - 180.0) < step / 2)
        if m.sum() < 20:
            continue
        A.append(a0)
        Rs.append((np.percentile(rl[m], 1) + np.percentile(rl[m], 99)) / 2)
        Hs.append((np.percentile(h[m], 1) + np.percentile(h[m], 99)) / 2)
    A = np.array(A)
    order = np.argsort(A)
    A, Rs, Hs = A[order], np.array(Rs)[order], np.array(Hs)[order]
    # wrap for interpolation
    return np.r_[A - 360.0, A, A + 360.0], np.r_[Rs, Rs, Rs], np.r_[Hs, Hs, Hs]


def own_wheel_mask(co, normals):
    """Vertices of his own wheel: rim, spokes, hub and column stub (cabin frame). Inside each grip only
    the rim's own surface goes (its normal points straight out of the tube), never his fingers."""
    C, N, e1, e2, R, tube = own_wheel()
    h, rl, ang, R, tube = _wheel_coords(co)
    A, Rs, Hs = rim_centreline(co)
    rc = np.interp(ang, A, Rs)
    hc = np.interp(ang, A, Hs)
    dr, dh = rl - rc, h - hc
    d = np.sqrt(dr * dr + dh * dh)
    Cn, Nn, e1n, e2n = (np.array(v) for v in (C, N, e1, e2))
    rad_dir = (co - Cn) - np.outer(h, Nn)
    rad_dir /= np.maximum(np.linalg.norm(rad_dir, axis=1), 1e-9)[:, None]
    out = (rad_dir * dr[:, None] + Nn[None, :] * dh[:, None]) / np.maximum(d, 1e-9)[:, None]
    facing = (out * normals).sum(1)
    grip = np.zeros(len(co), bool)
    for lo, hi in HAND_SECTOR.values():
        grip |= _in_sector(ang, lo, hi)
    rim = np.where(grip, (d < 1.22 * tube) | ((d < 1.40 * tube) & (facing > 0.90)), d < 1.47 * tube)
    hub = ((rl < 0.042 * SCALE) & (h > -0.006 * SCALE) & (h < 0.052 * SCALE)) | (
        (rl < 0.033 * SCALE) & (h >= 0.052 * SCALE) & (h < 0.14 * SCALE)
    )
    spoke = np.zeros(len(co), bool)
    for a in OWN_SPOKES:
        # Each spoke's axis, refitted from its own middle stretch (a line through the in-plane points).
        sel = (np.abs(((ang - a + 180.0) % 360.0) - 180.0) < 20.0) & (rl > 0.35 * R) & (rl < 0.72 * R) & (np.abs(h) < 0.03 * SCALE)
        P = co[sel]
        c0 = P.mean(0)
        ax = np.linalg.svd(P - c0, full_matrices=False)[2][0]
        if ax @ (c0 - Cn) < 0:
            ax = -ax
        rel = co - c0
        s = rel @ ax
        s0 = (Cn - c0) @ ax
        dist = np.linalg.norm(rel - np.outer(s, ax), axis=1)
        spoke |= (dist < OWN_SPOKE_R * SCALE * 1.18) & (s > s0) & (rl < rc - 0.6 * tube)
    return rim | hub | spoke


def components(n, edges):
    """Connected-component label per vertex (min-label propagation, vectorised)."""
    lab = np.arange(n)
    for _ in range(4000):
        a = np.minimum(lab[edges[:, 0]], lab[edges[:, 1]])
        new = lab.copy()
        np.minimum.at(new, edges[:, 0], a)
        np.minimum.at(new, edges[:, 1], a)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    return lab


def _delete_verts(obj, kill):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.where(kill)[0]], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def cut_own_wheel(obj):
    """Delete his own wheel; the cabin's wheel takes its place in his hands. Any loose piece left
    (a bit of spoke between the cuts) goes too. Returns where each hand held it (on the rim's
    measured centre line)."""
    me = obj.data
    co = _arrays(me)
    C, N, e1, e2, R, tube = own_wheel()
    A, Rs, Hs = rim_centreline(co)
    grips = {}
    for s_, a in HAND_ANGLE.items():
        d = e1 * math.cos(math.radians(a)) + e2 * math.sin(math.radians(a))
        grips[s_] = np.array(C + d * float(np.interp(a, A, Rs)) + N * float(np.interp(a, A, Hs)))
    nr = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("normal", nr)
    kill = own_wheel_mask(co, nr.reshape(-1, 3).astype(np.float64))
    _delete_verts(obj, kill)
    lab = components(len(obj.data.vertices), _edges(obj.data))
    ids, counts = np.unique(lab, return_counts=True)
    loose = lab != ids[np.argmax(counts)]
    if loose.any():
        _delete_verts(obj, loose)
    print("TAXI_TRIPO_WHEEL_CUT", int(kill.sum()), "verts; loose pieces dropped:", len(ids) - 1, int(loose.sum()))
    return grips


# ---------------------------------------------------------------- landmarks in the cabin

def marks():
    """His landmarks in the cabin frame, plus a head frame: `f` the way his face looks (horizontal),
    `lat` toward his left, `hc` the middle of his head between the ears."""
    M = placement()
    m = {k: np.array(M @ Vector(v)) for k, v in FACE.items()}
    lat = m["eye_l"] - m["eye_r"]
    lat[2] = 0.0
    lat /= np.linalg.norm(lat)
    f = np.cross(lat, (0.0, 0.0, 1.0))
    # his left ear, mirrored across the face's middle plane
    off = (m["ear_r"] - m["nose_tip"]) @ lat
    m["ear_l"] = m["ear_r"] - 2.0 * off * lat
    m["hc"] = (m["ear_r"] + m["ear_l"]) / 2.0
    m["f"], m["lat"] = f, lat
    C, N, e1, e2, R, tube = own_wheel()
    for s, a in HAND_ANGLE.items():
        m[f"grip_{s}"] = np.array(C + (e1 * math.cos(math.radians(a)) + e2 * math.sin(math.radians(a))) * R)
        m[f"wrist_{s}"] = m[f"grip_{s}"] + (m[f"elbow_{s}"] - m[f"grip_{s}"]) / np.linalg.norm(m[f"elbow_{s}"] - m[f"grip_{s}"]) * 0.085
    return m


def _seg_dist(co, a, b):
    ab = b - a
    t = np.clip(((co - a) @ ab) / (ab @ ab), 0.0, 1.0)
    return np.linalg.norm(co - (a + np.outer(t, ab)), axis=1), t


def _sstep(e0, e1, x):
    t = np.clip((np.asarray(x, np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------- garments

SKIN, CAP, SHIRT, VEST, BELT, TROUSERS, BOOTS, HANDS = range(8)
LABELS = ("skin", "cap", "shirt", "vest", "belt", "trousers", "boots", "hands")
COLLAR = 8  # his shirt collar, kept apart only while its edges are found


CUFF_FROM_GRIP = 0.058  # his cuff's open edge, measured along the forearm back from his grip


def cuff_plane(co, m, s):
    """Across the side `s` forearm at his cuff's edge (the seam snap then finds the edge itself).
    Returns (point, direction); the hand lies on the side the direction points to."""
    E, G = m[f"elbow_{s}"], m[f"grip_{s}"]
    d = (G - E) / np.linalg.norm(G - E)
    return G - d * CUFF_FROM_GRIP, d


def rough_labels(co, m, smooth_co=None):
    """A first guess at each garment from where it lies on him (cabin frame). Edges are only
    roughly right here; `snap_labels` moves each onto the sculpt's own seam. `smooth_co` (his body
    with its folds relaxed) places the vest's open front, so a fold never crosses it."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    sx, sy = (smooth_co[:, 0], smooth_co[:, 1]) if smooth_co is not None else (x, y)
    n = len(co)
    rel = co - m["hc"]
    u, v = rel @ m["f"], rel @ m["lat"]
    lab = np.full(n, TROUSERS, np.int8)
    # the belt runs round his waist, higher in front where he sits forward
    zb = 0.547 - 0.327 * (y + 0.0125)
    arms = np.full(n, 9.0)
    upper = np.zeros(n, bool)
    for s in ("l", "r"):
        S, E = m[f"shoulder_{s}"], m[f"elbow_{s}"]
        d1, t1 = _seg_dist(co, S, E)
        d2, _ = _seg_dist(co, E, m[f"wrist_{s}"])
        arms = np.minimum(arms, np.minimum(d1, d2))
        # the sleeve starts at the armhole: across the arm just outside the shoulder joint
        along = (co - S) @ ((E - S) / np.linalg.norm(E - S))
        upper |= (d1 < 0.085) & (along > 0.012)
        upper |= d2 < 0.072
    above = z > zb + 0.022
    lab[(np.abs(z - zb) <= 0.022) & (y > -0.13) & (arms > 0.06)] = BELT
    # the boots, below their folded tops (a plane across both shins)
    bn = np.array((0.0, -0.43, -0.90))
    bn /= np.linalg.norm(bn)
    boots = ((co - np.array((0.0, -0.255, 0.36))) @ bn > 0.0) & (z < 0.47) & (y < -0.10)
    lab[boots & ~above] = BOOTS
    # above the belt: torso (shirt front, vest round the sides and back) and arms (shirt sleeves)
    theta = np.degrees(np.arctan2(sx - 0.270, -(sy - 0.105)))
    torso_shirt = np.abs(theta) < 60.0
    lab[above] = np.where(torso_shirt[above], SHIRT, VEST)
    lab[above & upper] = SHIRT
    neck = np.hypot(x - m["hc"][0], y - (m["hc"][1] - 0.005))
    lab[above & (z > 0.90) & (neck < 0.125)] = COLLAR
    # head: skin above the collar's top edge (highest at his nape, an open V at the throat), the cap
    # above its band
    zc = 0.978 + 0.018 * _sstep(0.0, -0.06, u) - 0.038 * np.exp(-((v / 0.03) ** 2)) * _sstep(0.0, 0.05, u)
    head = (z > zc) & (np.linalg.norm(rel, axis=1) < 0.20)
    lab[head] = SKIN
    cap = head & ((z > 1.097 + 0.15 * u) | ((u > 0.115) & (z > 1.09)))
    lab[cap] = CAP
    # hands: past each cuff's edge, round the grip
    for s in ("l", "r"):
        cp, d = cuff_plane(co, m, s)
        G = m[f"grip_{s}"]
        line = np.linalg.norm((co - cp) - np.outer((co - cp) @ d, d), axis=1)
        lab[((co - cp) @ d > 0.0) & (np.linalg.norm(co - G, axis=1) < 0.13) & (line < 0.10)] = HANDS
    return lab


def _vertex_normals(me):
    nr = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("normal", nr)
    nr = nr.reshape(-1, 3).astype(np.float64)
    return nr / np.maximum(np.linalg.norm(nr, axis=1), 1e-12)[:, None]


def snap_labels(co, nr, edges, lab, rings=14, iters=260, k0=70.0, pairs=None):
    """Move each garment's edge onto the sculpt's seam near it: a random walk inside a band round the
    rough edges, where it crosses easily over smooth cloth or skin and hardly at all over a seam's
    groove or ridge (edge conductance falls with the surface's bend along the edge). `pairs` limits
    it to the edges between those garments."""
    n = len(co)
    a, b = edges[:, 0], edges[:, 1]
    diff = lab[a] != lab[b]
    if pairs is not None:
        lo, hi = np.minimum(lab[a], lab[b]), np.maximum(lab[a], lab[b])
        diff &= np.isin(lo.astype(np.int64) * 16 + hi, [min(p) * 16 + max(p) for p in pairs])
    band = np.zeros(n, bool)
    band[a[diff]] = True
    band[b[diff]] = True
    for _ in range(rings):
        grow = band[a] | band[b]
        nb = band.copy()
        nb[a[grow]] = True
        nb[b[grow]] = True
        band = nb
    L = np.linalg.norm(co[a] - co[b], axis=1)
    bend = np.arccos(np.clip((nr[a] * nr[b]).sum(1), -1.0, 1.0)) / np.maximum(L, 1e-6)
    w = np.exp(-((bend / k0) ** 2)) + 1e-6
    K = int(lab.max()) + 1
    p = np.zeros((n, K))
    p[np.arange(n), lab] = 1.0
    sel = band[a] | band[b]
    ea, eb, ew = a[sel], b[sel], w[sel]
    wsum = np.bincount(ea, ew, n) + np.bincount(eb, ew, n)
    free = band & (wsum > 0)
    for _ in range(iters):
        acc = np.empty_like(p)
        for k in range(K):
            acc[:, k] = np.bincount(ea, ew * p[eb, k], n) + np.bincount(eb, ew * p[ea, k], n)
        p[free] = acc[free] / wsum[free, None]
    out = lab.copy()
    out[free] = np.argmax(p[free], axis=1)
    return out


def clean_labels(edges, lab, min_size=1500):
    """Fold small stray patches of a garment into whatever surrounds them."""
    lab = lab.copy()
    n = len(lab)
    a, b = edges[:, 0], edges[:, 1]
    comp = components(n, edges[lab[a] == lab[b]])
    ids, counts = np.unique(comp, return_counts=True)
    small = np.isin(comp, ids[counts < min_size])
    K = int(lab.max()) + 1
    for _ in range(200):
        if not small.any():
            break
        votes = np.zeros((n, K))
        ok_b, ok_a = ~small[b], ~small[a]
        np.add.at(votes, (a[ok_b], lab[b[ok_b]]), 1.0)
        np.add.at(votes, (b[ok_a], lab[a[ok_a]]), 1.0)
        has = small & (votes.sum(1) > 0)
        lab[has] = votes[has].argmax(1)
        small[has] = False
    # straighten the edges: rounds of majority vote among each vertex and its neighbours
    for _ in range(10):
        votes = np.zeros((n, K))
        np.add.at(votes, (np.arange(n), lab), 1.5)
        np.add.at(votes, (a, lab[b]), 1.0)
        np.add.at(votes, (b, lab[a]), 1.0)
        lab = votes.argmax(1).astype(lab.dtype)
    return lab


def garment_labels(obj):
    """Garment label per vertex of `obj` (a mid-detail copy of the sculpt): rough guess, snapped to
    the seams, stray patches folded in."""
    me = obj.data
    co, nr, ed = _arrays(me), _vertex_normals(me), _edges(me)
    # his body with the cloth's folds relaxed (positions only), to place the vest's open front
    deg = np.maximum(np.bincount(ed[:, 0], minlength=len(co)) + np.bincount(ed[:, 1], minlength=len(co)), 1)
    smooth_co = co.copy()
    for _ in range(60):
        smooth_co = 0.5 * smooth_co + 0.5 * np.stack(
            [(np.bincount(ed[:, 0], smooth_co[ed[:, 1], k], len(co)) + np.bincount(ed[:, 1], smooth_co[ed[:, 0], k], len(co))) / deg for k in range(3)], 1)
    rough = rough_labels(co, marks(), smooth_co)
    # The vest's edge over the shirt front has no seam groove to find (the random walk only frayed
    # it along the creases), so it keeps its rough line: snap with vest, collar and shirt as one...
    merged = np.where(np.isin(rough, (VEST, COLLAR)), SHIRT, rough).astype(np.int8)
    lab = snap_labels(co, nr, ed, merged)
    lab[(lab == SHIRT) & (rough == VEST)] = VEST
    # the vest is one garment: any piece of it cut off from the main body is shirt
    vest = lab == VEST
    comp = components(len(lab), ed[vest[ed[:, 0]] & vest[ed[:, 1]]])
    ids, counts = np.unique(comp[vest], return_counts=True)
    lab[vest & np.isin(comp, ids[counts < 0.15 * counts.max()])] = SHIRT
    lab[(lab == SHIRT) & (rough == COLLAR)] = COLLAR
    # ...then the collar's turned-down edge, which does lie on a groove, against the vest under it.
    lab = snap_labels(co, nr, ed, lab, pairs=((COLLAR, VEST),))
    lab[lab == COLLAR] = SHIRT
    return clean_labels(ed, lab)


def nearest_labels(src_co, src_lab, dst_co):
    kd = KDTree(len(src_co))
    for i, c in enumerate(src_co):
        kd.insert(c, i)
    kd.balance()
    return np.array([src_lab[kd.find(c)[1]] for c in dst_co], np.int8)


# ---------------------------------------------------------------- colour

def _smooth(x, edges, n, k):
    a, b = edges[:, 0], edges[:, 1]
    deg = np.maximum(np.bincount(a, minlength=n) + np.bincount(b, minlength=n), 1)
    for _ in range(k):
        x = 0.5 * x + 0.5 * (np.bincount(a, x[b], n) + np.bincount(b, x[a], n)) / deg
    return x


def vnoise(p, scale, seed=0):
    """Smooth 3-D value noise in [0, 1] (trilinear over hashed lattice values)."""
    q = p / scale
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3.0 - 2.0 * f)

    def h(dx, dy, dz):
        n = (i[:, 0] + dx) * 73856093 ^ (i[:, 1] + dy) * 19349663 ^ (i[:, 2] + dz) * 83492791 ^ (seed * 2654435761)
        n = (n ^ (n >> 13)) * 1274126177
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * h(dx, dy, dz)
    return out


def _srgb_to_linear(c):
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _mix(col, target, amt):
    amt = np.clip(amt, 0.0, 1.0)[:, None]
    return col * (1.0 - amt) + np.asarray(target)[None, :] * amt


PALETTE = {  # sRGB
    SKIN: (0.465, 0.335, 0.255),  # a Khmer man's sun-browned skin
    HANDS: (0.45, 0.32, 0.235),
    CAP: (0.15, 0.137, 0.123),  # dark grey-brown wool
    SHIRT: (0.645, 0.61, 0.535),  # an old off-white cotton shirt, washed many times
    VEST: (0.15, 0.13, 0.11),  # old brown-grey wool
    BELT: (0.165, 0.098, 0.058),
    TROUSERS: (0.42, 0.37, 0.28),  # khaki drill
    BOOTS: (0.235, 0.135, 0.072),  # polished brown leather
}
ROUGH = {SKIN: 0.55, HANDS: 0.6, CAP: 0.93, SHIRT: 0.88, VEST: 0.9, BELT: 0.55, TROUSERS: 0.9, BOOTS: 0.46}
MATERIAL_OF = {SKIN: 0, HANDS: 0, CAP: 1, SHIRT: 1, VEST: 1, TROUSERS: 1, BELT: 2, BOOTS: 2}


def paint(obj, lab):
    """Colour and roughness per vertex of the full sculpt: each garment's own cloth or leather with
    its wear (grime in the seams and folds, dust on the knees, sweat at the collar, scuffed toes), and
    his face: skin with its own warmth, stubble, the hairline under the cap, brows, lips and eyes."""
    me = obj.data
    co, nr, ed = _arrays(me), _vertex_normals(me), _edges(me)
    n = len(co)
    m = marks()
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    # cavity (+ in folds and seams) and edges (+ on ridges), from the surface's own bend
    a, b = ed[:, 0], ed[:, 1]
    deg = np.maximum(np.bincount(a, minlength=n) + np.bincount(b, minlength=n), 1)
    nb_mean = np.stack([(np.bincount(a, co[b, k], n) + np.bincount(b, co[a, k], n)) / deg for k in range(3)], 1)
    elen = (np.bincount(a, np.linalg.norm(co[a] - co[b], axis=1), n) + np.bincount(b, np.linalg.norm(co[a] - co[b], axis=1), n)) / deg
    c = ((nb_mean - co) * nr).sum(1) / np.maximum(elen, 1e-6)
    c1 = _smooth(c, ed, n, 3)
    c2 = _smooth(c, ed, n, 18)
    q1 = np.percentile(np.abs(c1), 96) + 1e-9
    q2 = np.percentile(np.abs(c2), 96) + 1e-9
    cav = 0.55 * np.clip(c2 / q2, 0, 1) + 0.45 * np.clip(c1 / q1, 0, 1)
    ridge = np.clip(-c1 / q1, 0, 1)
    big = vnoise(co, 0.045, 1)
    mid = vnoise(co, 0.012, 2)
    fine = vnoise(co, 0.0022, 3)

    col = np.array([PALETTE[int(k)] for k in range(8)])[lab]
    rough = np.array([ROUGH[int(k)] for k in range(8)])[lab]
    cloth = np.isin(lab, (CAP, SHIRT, VEST, TROUSERS))
    leather = np.isin(lab, (BELT, BOOTS))
    skin = np.isin(lab, (SKIN, HANDS))

    # ---- cloth: dye variation, grime in the folds, wear on the ridges
    col[cloth] *= (0.97 + 0.04 * big[cloth] + 0.02 * mid[cloth])[:, None]
    col[cloth] *= (1.0 - 0.42 * cav[cloth])[:, None]
    col[cloth] = _mix(col[cloth], (0.80, 0.76, 0.66), 0.10 * ridge[cloth])
    cap = lab == CAP
    # herringbone tweed: chevron columns of fine diagonal ribs
    colw = np.floor((x[cap] + y[cap]) / 0.006).astype(np.int64)
    sgn = np.where(colw % 2 == 0, 1.0, -1.0)
    rib = 0.5 + 0.5 * np.sin((z[cap] + sgn * (x[cap] - y[cap]) * 0.7) * (2 * math.pi / 0.0021))
    col[cap] *= (0.92 + 0.14 * rib)[:, None]
    shirt = lab == SHIRT
    neck_d = np.hypot(x - m["hc"][0], y - m["hc"][1])
    collar_sweat = shirt & (z > 0.92) & (neck_d < 0.10)
    col[collar_sweat] = _mix(col[collar_sweat], (0.60, 0.54, 0.42), 0.12 + 0.06 * mid[collar_sweat])
    for s in ("l", "r"):
        d = np.linalg.norm(co - m[f"wrist_{s}"], axis=1)
        cuff = shirt & (d < 0.075)
        col[cuff] = _mix(col[cuff], (0.50, 0.46, 0.39), _sstep(0.075, 0.02, d[cuff]) * 0.14)
    trou = lab == TROUSERS
    knee = trou & (z < 0.50) & (y < -0.12)
    col[knee] = _mix(col[knee], (0.55, 0.50, 0.41), 0.35 * ridge[knee] + 0.12 * big[knee])
    # ---- leather: deep creases, a dull polish, scuffed toes and edges
    col[leather] *= (0.90 + 0.14 * big[leather] + 0.06 * mid[leather])[:, None]
    col[leather] *= (1.0 - 0.50 * cav[leather])[:, None]
    col[leather] = _mix(col[leather], (0.42, 0.30, 0.20), 0.45 * ridge[leather] * mid[leather])
    rough[leather] += 0.18 * cav[leather] + 0.10 * ridge[leather] - 0.05
    boots = lab == BOOTS
    toe = boots & (y < -0.50)
    col[toe] = _mix(col[toe], (0.36, 0.25, 0.17), 0.25 * ridge[toe])
    belt = lab == BELT
    buckle = belt & (np.abs(x - 0.217) < 0.038) & (y < 0.0)
    col[buckle] = (0.30, 0.285, 0.26)
    rough[buckle] = 0.42

    # ---- skin: its own warmth and blemish, darker in creases
    col[skin] *= (0.97 + 0.05 * big[skin] + 0.02 * mid[skin])[:, None]
    col[skin] *= (1.0 - 0.32 * cav[skin])[:, None]
    hands = lab == HANDS
    col[hands] = _mix(col[hands], (0.52, 0.30, 0.22), 0.25 * ridge[hands])  # knuckles
    rough[hands] += 0.06 * cav[hands]

    head = lab == SKIN
    rel = co - m["hc"]
    u, v = rel @ m["f"], rel @ m["lat"]

    def blob(centre, r):
        return np.exp(-(np.linalg.norm(co - centre, axis=1) / r) ** 2)

    red = 0.09 * blob(m["nose_tip"], 0.014)
    for s in ("r", "l"):
        cheek = m[f"eye_{s}"] - np.array((0.0, 0.0, 0.032)) - m["f"] * 0.006
        red += 0.06 * blob(cheek, 0.020) + 0.10 * blob(m[f"ear_{s}"], 0.022)
        under = m[f"eye_{s}"] - np.array((0.0, 0.0, 0.010))
        col[head] = _mix(col[head], (0.34, 0.24, 0.21), 0.16 * blob(under, 0.009)[head])
    col[head] = _mix(col[head], (0.58, 0.30, 0.24), red[head])
    # stubble over the jaw, chin and upper lip
    mz = m["mouth_c"][2]
    stub = head & (z < mz + 0.017) & (z > m["chin"][2] - 0.045) & (u > -0.035)
    stub_amt = _sstep(mz + 0.017, mz + 0.006, z) * _sstep(-0.035, -0.010, u)
    speck = (fine > 0.55).astype(float) * 0.5 + 0.5 * mid
    col[stub] = _mix(col[stub], (0.25, 0.21, 0.19), (0.22 * stub_amt * speck)[stub])
    rough[stub] += 0.05
    # oily forehead and nose
    tz = head & (u > 0.06) & (z > m["nose_tip"][2] - 0.01) & (np.abs(v) < 0.025)
    rough[tz] -= 0.08
    # lips
    dv = (co - m["mouth_c"]) @ m["lat"]
    dz = z - m["mouth_c"][2]
    t = np.clip(np.abs(dv) / 0.0225, 0.0, 1.0)
    up = (m["lip_top"][2] - m["mouth_c"][2] + 0.0006) * np.sqrt(1 - t * t) ** 0.8
    lo = (m["mouth_c"][2] - m["lip_bot"][2] + 0.0008) * np.sqrt(1 - t * t)
    lipd = np.where(dz > 0, dz / np.maximum(up, 1e-4), -dz / np.maximum(lo, 1e-4))
    lips = head & (np.abs(dv) < 0.0225) & (lipd < 1.25) & ((co - m["mouth_c"]) @ m["f"] > -0.012)
    la = _sstep(1.2, 0.8, lipd) * _sstep(1.0, 0.85, t)
    col[lips] = _mix(col[lips], (0.44, 0.26, 0.23), 0.62 * la[lips])
    seam = lips & (np.abs(dz) < 0.0009)
    col[seam] = _mix(col[seam], (0.20, 0.11, 0.09), 0.7 * la[seam])
    rough[lips] -= 0.16 * la[lips]
    # hair: under the cap at the temples, round and behind the ears to the nape
    ear_d = np.minimum(np.linalg.norm(co - m["ear_r"], axis=1), np.linalg.norm(co - m["ear_l"], axis=1))
    ear = _sstep(0.033, 0.026, ear_d) * _sstep(0.040, 0.055, np.abs(v))
    u_front = 0.024 + 0.003 * (mid - 0.5)
    z_low = np.interp(u, (-0.09, -0.035, -0.004, 0.03), (1.022, 1.026, 1.056, 1.056)) + 0.003 * (mid - 0.5)
    hair_amt = _sstep(u_front + 0.003, u_front - 0.003, u) * _sstep(z_low - 0.002, z_low + 0.005, z) * (1.0 - ear)
    hair_amt *= _sstep(0.030, 0.045, np.abs(v)) + _sstep(-0.02, -0.04, u)
    hair_amt = np.clip(hair_amt, 0, 1) * (0.88 + 0.12 * fine)
    col[head] = _mix(col[head], (0.040, 0.034, 0.030), hair_amt[head])
    rough[head] += 0.12 * hair_amt[head]
    # brows
    for s in ("r", "l"):
        d, tt = _seg_dist(co, m[f"brow_{s}_in"] + np.array((0, 0, 0.0015)), m[f"brow_{s}_out"] + np.array((0, 0, 0.0005)))
        w = 0.0043 * (1.0 - 0.45 * tt)
        amt = _sstep(w, w * 0.3, d) * (0.45 + 0.55 * (fine > 0.45)) * ((co - m["hc"]) @ m["f"] > 0.03)
        col[head] = _mix(col[head], (0.07, 0.055, 0.048), 0.72 * amt[head])
    # eyes: the eyeball in the lids' opening, iris, pupil, lash line
    for s in ("r", "l"):
        e = m[f"eye_{s}"]
        ev = (co - e) @ m["lat"]
        ez = z - e[2]
        eu = (co - e) @ m["f"]
        ell = (ev / 0.0106) ** 2 + (ez / 0.0036) ** 2
        ball = head & (ell < 1.0) & (eu < 0.0025) & (eu > -0.012)
        r = np.hypot(ev, ez)
        corner = _sstep(0.006, 0.0105, np.abs(ev))
        sc = _mix(np.tile(np.array((0.62, 0.575, 0.50)), (n, 1)), (0.58, 0.42, 0.37), 0.55 * corner)
        sc *= (0.78 + 0.22 * _sstep(0.0035, -0.001, ez))[:, None]  # the upper lid shades the eyeball
        iris = _mix(np.tile(np.array((0.21, 0.125, 0.065)), (n, 1)), (0.11, 0.065, 0.035), _sstep(0.0036, 0.0057, r))
        eye_col = np.where((r < 0.0058)[:, None], iris, sc)
        eye_col = np.where((r < 0.0019)[:, None], np.array((0.02, 0.016, 0.014)), eye_col)
        col[ball] = eye_col[ball]
        rough[ball] = 0.06
        lash = head & (ell >= 0.85) & (ell < 1.6) & (eu > -0.006)
        col[lash] = _mix(col[lash], (0.12, 0.08, 0.065), 0.55 * _sstep(1.6, 1.0, ell[lash]))

    rough = np.clip(rough + 0.04 * (mid - 0.5), 0.05, 1.0)
    lin = _srgb_to_linear(col)
    stub_full = np.zeros(n)
    stub_full[stub] = np.clip(stub_amt[stub], 0, 1)
    for name, data in (("taxi_col", np.c_[lin, np.ones(n)]), ("taxi_rough", np.c_[rough, rough, rough, np.ones(n)]),
                       ("taxi_stub", np.c_[stub_full, stub_full, stub_full, np.ones(n)])):
        at = me.color_attributes.get(name) or me.color_attributes.new(name, "FLOAT_COLOR", "POINT")
        at.data.foreach_set("color", data.astype(np.float32).ravel())
    me.update()
    print("TAXI_TRIPO_PAINTED", n, "verts; by garment:", dict(zip(LABELS, np.bincount(lab, minlength=8).tolist())))


# ---------------------------------------------------------------- game mesh, UVs and bake

GAME_TRIS = 120000
MID_TRIS = 800000
# material, texture stem, colour size, relief size, roughness size
MATS = (
    ("M_taxi_driver_skin", "T_taxi_driver_skin", 2048, 2048, 1024),
    ("M_taxi_driver_cloth", "T_taxi_driver_cloth", 2048, 1024, 1024),
    ("M_taxi_driver_leather", "T_taxi_driver_leather", 1024, 1024, 512),
)
OLD_DRIVER = (
    "taxi_driver_head_scan", "taxi_driver_cap", "taxi_driver_body_scan", "taxi_driver_hand_l",
    "taxi_driver_hand_r", "taxi_driver_krama", "taxi_driver_sleeves_scan", "taxi_driver_cuff_buttons",
    "taxi_driver_shirt_collar", "taxi_driver_shirt_front", "taxi_driver_shirt_buttons",
)


def _copy(obj, name):
    c = obj.copy()
    c.data = obj.data.copy()
    c.name = c.data.name = name
    for col in obj.users_collection:
        col.objects.link(c)
    return c


def _activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _decimate(obj, tris, keep=None):
    """Collapse to about `tris` triangles; vertices in `keep` (a per-vertex weight) are spared."""
    _activate(obj)
    md = obj.modifiers.new("decimate", "DECIMATE")
    md.ratio = min(1.0, tris / max(1, len(obj.data.polygons)))
    if keep is not None:
        vg = obj.vertex_groups.new(name="_keep")
        for w in np.unique(np.round(keep, 2)):
            if w > 0:
                vg.add(np.where(np.round(keep, 2) == w)[0].tolist(), float(w), "REPLACE")
        # (the modifier decimates where its group is; inverted, the kept vertices are left alone)
        md.vertex_group = vg.name
        md.invert_vertex_group = True
        md.vertex_group_factor = 1.0
    bpy.ops.object.modifier_apply(modifier=md.name)
    if keep is not None:
        obj.vertex_groups.remove(obj.vertex_groups["_keep"])


def _image(name, size, srgb):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    # (with alpha: the bake marks each texel it writes, so the gaps can be filled after)
    img = bpy.data.images.new(name, size, size, alpha=True)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return img


def _material(name, stem, s_bc, s_n, s_r):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = 0.0
    t_bc = nt.nodes.new("ShaderNodeTexImage")
    t_bc.name, t_bc.image = "BC", _image(f"{stem}_BC", s_bc, True)
    t_r = nt.nodes.new("ShaderNodeTexImage")
    t_r.name, t_r.image = "R", _image(f"{stem}_R", s_r, False)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    t_n = nt.nodes.new("ShaderNodeTexImage")
    t_n.name, t_n.image = "N", _image(f"{stem}_N", s_n, False)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(t_bc.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(t_r.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bs.inputs["Roughness"])
    nt.links.new(t_n.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return mat


def game_mesh(mid, mid_lab):
    """The 120k-triangle mesh the game draws: decimated from the mid copy, one material per kind of
    surface (skin, cloth, leather), smooth-shaded. The vertices along each garment's edge are spared,
    so the edge keeps the fine line it was painted with instead of zigzagging along big triangles."""
    L = _copy(mid, "taxi_driver_body_scan")
    for at in list(L.data.color_attributes):
        L.data.color_attributes.remove(at)
    ed = _edges(mid.data)
    edge = np.zeros(len(mid_lab), bool)
    diff = mid_lab[ed[:, 0]] != mid_lab[ed[:, 1]]
    edge[ed[diff, 0]] = True
    edge[ed[diff, 1]] = True
    _decimate(L, GAME_TRIS, keep=edge.astype(float))
    me = L.data
    me.materials.clear()
    for spec in MATS:
        me.materials.append(_material(*spec))
    mid_co = _arrays(mid.data)
    fc = np.empty(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get("center", fc)
    lab_f = nearest_labels(mid_co, mid_lab, fc.reshape(-1, 3))
    me.polygons.foreach_set("material_index", np.array([MATERIAL_OF[int(k)] for k in lab_f], np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    me.update()
    return L


def unwrap(L):
    """Its own UVs, each kind of surface (skin, cloth, leather) filling its own texture: the mesh is
    split by material, each part unwrapped and packed on its own, then joined and welded back."""
    _activate(L)
    me = L.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UVMap")
    before = set(bpy.data.objects)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [L] + [o for o in bpy.data.objects if o not in before]
    for part in parts:
        _activate(part)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(58.0), island_margin=0.003, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = L
    bpy.ops.object.join()
    bm = bmesh.new()
    bm.from_mesh(L.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(L.data)
    bm.free()
    L.data.update()


def _submesh(src, vmask_faces, name, coll):
    """A new object holding only the faces of `src` picked by `vmask_faces` (with their point colour
    attributes), built straight from arrays."""
    me = src.data
    nf = len(me.polygons)
    tris = np.empty(nf * 3, np.int64)
    me.polygons.foreach_get("vertices", tris)
    tris = tris.reshape(-1, 3)[vmask_faces]
    used, inv = np.unique(tris, return_inverse=True)
    co = _arrays(me)[used]
    new = bpy.data.meshes.new(name)
    new.vertices.add(len(used))
    new.vertices.foreach_set("co", co.astype(np.float32).ravel())
    new.loops.add(tris.size)
    new.loops.foreach_set("vertex_index", inv.astype(np.int32).ravel())
    new.polygons.add(len(tris))
    new.polygons.foreach_set("loop_start", (np.arange(len(tris)) * 3).astype(np.int32))
    new.update(calc_edges=True)
    for at in me.color_attributes:
        if at.domain != "POINT":
            continue
        data = np.empty(len(me.vertices) * 4, np.float32)
        at.data.foreach_get("color", data)
        dst = new.color_attributes.new(at.name, "FLOAT_COLOR", "POINT")
        dst.data.foreach_set("color", data.reshape(-1, 4)[used].ravel())
    new.polygons.foreach_set("use_smooth", np.ones(len(tris), bool))
    obj = bpy.data.objects.new(name, new)
    coll.objects.link(obj)
    return obj


def _fill_unbaked(img, rounds=24):
    """Texels no garment wrote (their alpha is still 0) take their neighbours' colour, round after
    round, so island edges and mips never pull in black."""
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    done = px[..., 3] > 0.5
    for _ in range(rounds):
        if done.all():
            break
        acc = np.zeros((h, w, 3), np.float32)
        cnt = np.zeros((h, w), np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sh = np.roll(np.roll(done, dy, 0), dx, 1)
            acc += np.roll(np.roll(px[..., :3], dy, 0), dx, 1) * sh[..., None]
            cnt += sh
        grow = (~done) & (cnt > 0)
        px[grow, :3] = acc[grow] / cnt[grow, None]
        done |= grow
    px[..., 3] = 1.0
    img.pixels.foreach_set(px.ravel())


LIB = ROOT / "art-source/library"
# Photo detail for each garment: (source, crop x, y, size in source pixels with the top row first or
# None for the whole image, repeats per metre): the scanned hand, the photoscanned wool cap, Poly
# Haven's linen and leather. (His face's pores and stubble are generated in the bake shader.)
DETAIL_SOURCES = {
    "hand": ("scans/taxi_driver_hand.glb", 1200, 920, 440, 20.0),
    "wool": ("scans/taxi_driver_flatcap.glb", 1880, 920, 280, 36.0),
    "linen": ("materials/rough_linen/rough_linen_BC.jpg", None, None, None, 8.0),
    "drill": ("materials/rough_linen/rough_linen_BC.jpg", None, None, None, 5.0),
    "leather": ("materials/brown_leather/brown_leather_BC.jpg", None, None, None, 4.0),
}
DETAIL_OF = {SKIN: "hand", HANDS: "hand", CAP: "wool", VEST: "wool", SHIRT: "linen", TROUSERS: "drill",
             BELT: "leather", BOOTS: "leather"}
DETAIL_GAIN = {"hand": 1.5, "wool": 1.0, "linen": 1.6, "drill": 1.8, "leather": 1.2}
DETAIL_BUMP = {SKIN: 0.35, HANDS: 0.35, CAP: 0.25, VEST: 0.25, SHIRT: 0.2, TROUSERS: 0.25, BELT: 0.35, BOOTS: 0.35}


def _source_pixels(rel):
    """RGB pixels (top row first) of a library image, or of the first colour image in a library GLB."""
    path = LIB / rel
    if path.suffix == ".glb":
        before_i, before_o = set(bpy.data.images), set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        new_i = [i for i in bpy.data.images if i not in before_i]
        img = None
        for o in [o for o in bpy.data.objects if o not in before_o and o.type == "MESH"]:
            for mt in o.data.materials:
                bsdf = next((nd for nd in mt.node_tree.nodes if nd.type == "BSDF_PRINCIPLED"), None) if mt and mt.use_nodes else None
                links = bsdf.inputs["Base Color"].links if bsdf else []
                if links and links[0].from_node.type == "TEX_IMAGE":
                    img = links[0].from_node.image
        img = img or max(new_i, key=lambda i: i.size[0])
    else:
        before_i, before_o = set(bpy.data.images), set(bpy.data.objects)
        img = bpy.data.images.load(str(path))
        new_i = [img]
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[::-1, :, :3].copy()
    for o in [o for o in bpy.data.objects if o not in before_o]:
        bpy.data.objects.remove(o, do_unlink=True)
    for i in new_i:
        bpy.data.images.remove(i)
    return px


def _box_blur(a, r):
    out = a
    for axis in (0, 1):
        pad = np.concatenate([np.flip(out.take(range(r), axis), axis), out, np.flip(out.take(range(out.shape[axis] - r, out.shape[axis]), axis), axis)], axis)
        c = np.cumsum(pad, axis, dtype=np.float64)
        c = np.concatenate([np.zeros_like(c.take([0], axis)), c], axis)
        hi = c.take(range(2 * r + 1, c.shape[axis]), axis)
        lo = c.take(range(0, c.shape[axis] - 2 * r - 1), axis)
        out = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return out


def detail_images():
    """Each photo source reduced to its fine detail: the pixel over its blurred surround, so pores,
    stubble, weave and grain stay and the photo's own light and colour go. Tiled mirrored."""
    cache, out = {}, {}
    for key, (rel, x0, y0, size, scale) in DETAIL_SOURCES.items():
        if rel not in cache:
            cache[rel] = _source_pixels(rel)
        px = cache[rel]
        if size is not None:
            px = px[y0:y0 + size, x0:x0 + size]
        if px.shape[0] > 1024:
            step = px.shape[0] // 1024
            px = px[::step, ::step]
        base = _box_blur(px, max(4, px.shape[0] // 10))
        ratio = px / np.maximum(base, 1e-3)
        lum = ratio.mean(-1, keepdims=True)
        g = DETAIL_GAIN[key]
        det = np.clip(1.0 + g * (lum - 1.0), 0.55, 1.5) * np.clip(ratio / np.maximum(lum, 1e-3), 0.85, 1.15) ** 0.5
        hgt, wid = det.shape[:2]
        name = f"_taxi_detail_{key}"
        img = bpy.data.images.get(name)
        if img is not None:
            bpy.data.images.remove(img)
        img = bpy.data.images.new(name, wid, hgt, alpha=False, float_buffer=True)
        img.colorspace_settings.name = "Non-Color"
        img.pixels.foreach_set(np.concatenate([det[::-1], np.ones((hgt, wid, 1), np.float32)], -1).ravel())
        out[key] = (img, scale)
    return out


def bake(H, L, lab_h, lab_l):
    """Colour, roughness and relief from the full sculpt onto the game mesh, one garment at a time:
    each garment's faces only see that garment's part of the sculpt, so a collar never catches the
    vest under its overhang, nor a cuff the wrist."""
    sc = bpy.context.scene
    engine = sc.render.engine
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    bk = sc.render.bake
    bk.use_selected_to_active = True
    bk.use_clear = False
    bk.margin = 0
    details = detail_images()
    src = bpy.data.materials.new("_taxi_driver_bake_src")
    src.use_nodes = True
    nt = src.node_tree
    nt.nodes.clear()
    N_ = nt.nodes.new
    attr = N_("ShaderNodeAttribute")
    attr.attribute_type = "GEOMETRY"
    stub = N_("ShaderNodeAttribute")
    stub.attribute_type, stub.attribute_name = "GEOMETRY", "taxi_stub"
    tc = N_("ShaderNodeTexCoord")
    mp = N_("ShaderNodeMapping")
    tex = N_("ShaderNodeTexImage")
    tex2 = N_("ShaderNodeTexImage")
    for t in (tex, tex2):
        t.projection, t.projection_blend, t.extension = "BOX", 0.25, "MIRROR"
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    mix_d = N_("ShaderNodeMix")
    mix_d.data_type = "RGBA"
    nt.links.new(stub.outputs["Fac"], mix_d.inputs["Factor"])
    nt.links.new(tex.outputs["Color"], mix_d.inputs[6])
    nt.links.new(tex2.outputs["Color"], mix_d.inputs[7])
    mul = N_("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(attr.outputs["Color"], mul.inputs[6])
    em = N_("ShaderNodeEmission")
    bw = N_("ShaderNodeRGBToBW")
    bump = N_("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(bw.outputs["Val"], bump.inputs["Height"])
    # His face: pores, mottling and stubble generated in place (a small scanned patch tiled over a
    # whole face repeats its marks; these never repeat).
    def _math(op, a, b=None, c=None):
        nd = N_("ShaderNodeMath")
        nd.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                nd.inputs[i].default_value = v
            else:
                nt.links.new(v, nd.inputs[i])
        return nd.outputs[0]

    def _dots(scale, lo, hi):
        vor = N_("ShaderNodeTexVoronoi")
        vor.voronoi_dimensions, vor.feature = "3D", "F1"
        vor.inputs["Scale"].default_value = scale
        nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
        mr = N_("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = lo, hi
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0
        nt.links.new(vor.outputs["Distance"], mr.inputs["Value"])
        return mr.outputs["Result"]

    noise = N_("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 260.0
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    pores = _math("MULTIPLY_ADD", _dots(1500.0, 0.05, 0.2), -0.16, 1.0)
    mottle = _math("MULTIPLY_ADD", noise.outputs["Fac"], 0.16, 0.92)
    whisk = _math("MULTIPLY_ADD", _dots(2600.0, 0.04, 0.13), -0.55, 1.0)
    stubbled = _math("ADD", _math("MULTIPLY", _math("SUBTRACT", whisk, 1.0), stub.outputs["Fac"]), 1.0)
    skin_det = _math("MULTIPLY", _math("MULTIPLY", pores, mottle), stubbled)
    bsdf = N_("ShaderNodeBsdfPrincipled")
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    out = N_("ShaderNodeOutputMaterial")

    def wire(g, node_name, attr_name):
        img, scale = details[DETAIL_OF[g]]
        tex.image = img
        tex2.image = img
        mp.inputs["Scale"].default_value = (scale, scale, scale)
        bump.inputs["Strength"].default_value = DETAIL_BUMP[g]
        for lk in list(mul.inputs[7].links) + list(bw.inputs["Color"].links):
            nt.links.remove(lk)
        det = skin_det if g == SKIN else mix_d.outputs[2]
        nt.links.new(det, mul.inputs[7])
        nt.links.new(det, bw.inputs["Color"])
        for lk in list(out.inputs["Surface"].links):
            nt.links.remove(lk)
        for lk in list(em.inputs["Color"].links):
            nt.links.remove(lk)
        if node_name == "N":
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        else:
            attr.attribute_name = attr_name
            nt.links.new((mul.outputs[2] if node_name == "BC" else attr.outputs["Color"]), em.inputs["Color"])
            nt.links.new(em.outputs["Emission"], out.inputs["Surface"])

    for mat in L.data.materials:
        for nm in ("BC", "R", "N"):
            img = mat.node_tree.nodes[nm].image
            img.pixels.foreach_set(np.zeros(img.size[0] * img.size[1] * 4, np.float32))
    coll = L.users_collection[0]
    tri = np.empty(len(H.data.polygons) * 3, np.int64)
    H.data.polygons.foreach_get("vertices", tri)
    face_lab_h = lab_h[tri.reshape(-1, 3)[:, 0]]
    fc = np.empty(len(L.data.polygons) * 3, np.float32)
    L.data.polygons.foreach_get("center", fc)
    face_lab_l = nearest_labels(_arrays(L.data), lab_l, fc.reshape(-1, 3))
    for g in range(len(LABELS)):
        if not (face_lab_l == g).any() or not (face_lab_h == g).any():
            continue
        Hg = _submesh(H, face_lab_h == g, "_bake_hi", coll)
        Hg.data.materials.append(src)
        Lg = _copy(L, "_bake_lo")
        bm = bmesh.new()
        bm.from_mesh(Lg.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.where(face_lab_l != g)[0]], context="FACES")
        bm.to_mesh(Lg.data)
        bm.free()
        for node_name, attr_name, kind in (("BC", "taxi_col", "EMIT"), ("R", "taxi_rough", "EMIT"), ("N", None, "NORMAL")):
            wire(g, node_name, attr_name)
            for mat in Lg.data.materials:
                mat.node_tree.nodes.active = mat.node_tree.nodes[node_name]
            bpy.ops.object.select_all(action="DESELECT")
            Hg.select_set(True)
            Lg.select_set(True)
            bpy.context.view_layer.objects.active = Lg
            bpy.ops.object.bake(type=kind, use_selected_to_active=True, cage_extrusion=0.003,
                                max_ray_distance=0.008, margin=0, use_clear=False, normal_space="TANGENT")
        for o in (Hg, Lg):
            me = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.meshes.remove(me)
        print("TAXI_TRIPO_BAKED", LABELS[g])
    for mat in L.data.materials:
        for nm in ("BC", "R", "N"):
            img = mat.node_tree.nodes[nm].image
            _fill_unbaked(img)
            img.pack()
        mat.node_tree.nodes.active = mat.node_tree.nodes["BC"]
    bpy.data.materials.remove(src)
    for img, _ in details.values():
        if img.name in bpy.data.images:
            bpy.data.images.remove(img)
    sc.render.engine = engine


# ---------------------------------------------------------------- hands onto the cabin's rim, and his shapes

def _geodesic(co, edges, sources, limit=0.6):
    n = len(co)
    order = np.argsort(np.r_[edges[:, 0], edges[:, 1]], kind="stable")
    nbr = np.r_[edges[:, 1], edges[:, 0]][order]
    start = np.searchsorted(np.r_[edges[:, 0], edges[:, 1]][order], np.arange(n + 1))
    dist = np.full(n, np.inf)
    heap = []
    for s in sources:
        dist[s] = 0.0
        heap.append((0.0, int(s)))
    heapq.heapify(heap)
    while heap:
        d, i = heapq.heappop(heap)
        if d > dist[i] or d > limit:
            continue
        for j in nbr[start[i]:start[i + 1]]:
            nd = d + float(np.linalg.norm(co[i] - co[j]))
            if nd < dist[j]:
                dist[j] = nd
                heapq.heappush(heap, (nd, int(j)))
    return dist


def _rot_about(co, pivot, axis, angle):
    R = np.array(Matrix.Rotation(angle, 3, Vector(axis)))
    return (co - pivot) @ R.T + pivot


def fit_hands(L, lab, grips):
    """Each hand moves from his own small rim onto the Rosalie's: a rigid turn and shift taking his
    grip on his rim to the nearest point of the cabin rim (its tube and plane), with the arm following
    and fading out by the shoulder (by distance along his skin). The fist then closes round the
    thinner bakelite tube. Returns each hand's weight per vertex."""
    me = L.data
    co, ed = _arrays(me), _edges(me)
    C, N, e1, e2, R, tube = own_wheel()
    C, N, e1, e2 = (np.array(v) for v in (C, N, e1, e2))
    WC, WN = np.array(WHEEL_CENTER), np.array(WHEEL_NORMAL)
    out = co.copy()
    weights = {}
    for s, a in HAND_ANGLE.items():
        g = grips[s]
        r_o = g - C - N * ((g - C) @ N)
        r_o /= np.linalg.norm(r_o)
        t_o = np.cross(N, r_o)
        v = g - WC
        v -= WN * (v @ WN)
        r_c = v / np.linalg.norm(v)
        target = WC + r_c * RIM_R
        t_c = np.cross(-WN, r_c)
        Rm = np.c_[r_c, t_c, -WN] @ np.c_[r_o, t_o, N].T
        src = np.where((np.linalg.norm(co - g, axis=1) < 0.05) & (lab == HANDS))[0]
        d = _geodesic(co, ed, src)
        w = _sstep(0.46, 0.08, d)
        weights[s] = w
        moved = (co - g) @ Rm.T + target
        out += w[:, None] * (moved - co)
    # close each fist round the cabin's thinner tube
    hand_w = np.maximum(weights["l"], weights["r"])
    rel = out - WC
    h = rel @ WN
    rad = rel - np.outer(h, WN)
    rl = np.linalg.norm(rad, axis=1)
    rdir = rad / np.maximum(rl, 1e-9)[:, None]
    centre = WC + rdir * RIM_R
    off = out - centre
    dc = np.linalg.norm(off, axis=1)
    own_tube = OWN_TUBE * SCALE
    pull = (own_tube - RIM_TUBE - 0.0008) * _sstep(own_tube + 0.012, own_tube + 0.002, dc) * (hand_w > 0.9)
    out -= off / np.maximum(dc, 1e-9)[:, None] * pull[:, None]
    me.vertices.foreach_set("co", out.astype(np.float32).ravel())
    me.update()
    print("TAXI_TRIPO_HANDS_ON_RIM", {s: round(float(np.linalg.norm(grips[s] - (WC + (lambda v: v / np.linalg.norm(v))((grips[s] - WC) - WN * ((grips[s] - WC) @ WN)) * RIM_R))), 4) for s in grips})
    return weights


REST_HEAD_YAW = -18.0  # he faced 23° to his left in the sculpt; this sets his eyes on the road


def _head_frame(co, lab):
    m = marks()
    neck = (lab == SKIN) & (co[:, 2] > 0.955) & (co[:, 2] < 0.975)
    pivot = np.array((co[neck, 0].mean(), co[neck, 1].mean(), 0.975)) if neck.any() else m["hc"] - np.array((0, 0, 0.08))
    w = np.isin(lab, (SKIN, CAP)) * _sstep(0.962, 1.002, co[:, 2])
    return m, pivot, w


def shapes(L, lab, hand_w):
    """His rest head turn, then the runtime's shape keys."""
    me = L.data
    co = _arrays(me)
    m, pivot, wh = _head_frame(co, lab)
    rest = co + wh[:, None] * (_rot_about(co, pivot, (0, 0, 1), math.radians(REST_HEAD_YAW)) - co)
    me.vertices.foreach_set("co", rest.astype(np.float32).ravel())
    me.update()
    co = rest
    f = np.array(Matrix.Rotation(math.radians(REST_HEAD_YAW), 3, "Z") @ Vector(m["f"]))
    lat = np.cross(f, (0.0, 0.0, -1.0))
    lat /= np.linalg.norm(lat)
    WC, WN = np.array(WHEEL_CENTER), np.array(WHEEL_NORMAL)
    hw = np.maximum(hand_w["l"], hand_w["r"])
    z = co[:, 2]

    def head_turn(yaw, pitch=0.0):
        p = _rot_about(co, pivot, (0, 0, 1), math.radians(yaw))
        if pitch:
            p = _rot_about(p, pivot + np.array((0, 0, 0.02)), lat, math.radians(pitch))
        return co + wh[:, None] * (p - co)

    keys = {}
    keys["steer_left"] = co + hw[:, None] * (_rot_about(co, WC, WN, -0.16) - co)
    keys["steer_right"] = co + hw[:, None] * (_rot_about(co, WC, WN, 0.16) - co)
    # clench: the fist tightens onto the bakelite
    rel = co - WC
    hh = rel @ WN
    rad = rel - np.outer(hh, WN)
    centre = WC + rad / np.maximum(np.linalg.norm(rad, axis=1), 1e-9)[:, None] * RIM_R
    off = co - centre
    dc = np.linalg.norm(off, axis=1)
    squeeze = 0.0011 * _sstep(0.034, 0.016, dc) * (hw > 0.9)
    keys["grip_tense"] = co - off / np.maximum(dc, 1e-9)[:, None] * squeeze[:, None]
    # breathing: the chest fills and the shoulders lift; the hands stay on the wheel
    torso = np.isin(lab, (SHIRT, VEST, SKIN, CAP, BELT)) * _sstep(0.56, 0.70, z) * (1.0 - hw)
    chest = np.exp(-((z - 0.76) / 0.09) ** 2) * np.isin(lab, (SHIRT, VEST))
    radial = co - np.array((0.27, 0.105, 0.0))
    radial[:, 2] = 0.0
    radial /= np.maximum(np.linalg.norm(radial, axis=1), 1e-9)[:, None]
    br = co + (radial * (0.0035 * chest)[:, None] + np.array((0.0, 0.0, 0.0016)) * torso[:, None])
    keys["breathe"] = br
    # peering: he leans in from the hips; his hands keep the rim, his arms bend
    lean_w = _sstep(0.50, 0.72, z) * (1.0 - hw) * ~np.isin(lab, (TROUSERS, BOOTS))
    keys["lean_peer"] = co + lean_w[:, None] * (_rot_about(co, np.array((0.27, 0.12, 0.42)), (1, 0, 0), math.radians(5.0)) - co)
    keys["look_road"] = head_turn(4.0)
    keys["look_sora"] = head_turn(-30.0, 4.5)
    keys["nod"] = head_turn(0.0, 8.5)
    # talking: the jaw drops a little from its hinge below the ears
    jaw = (lab == SKIN) * _sstep(m["mouth_c"][2] + 0.002, m["mouth_c"][2] - 0.008, z) * _sstep(m["chin"][2] - 0.03, m["chin"][2] - 0.005, z)
    jaw *= _sstep(-0.035, 0.0, (co - pivot) @ f)
    hinge = (m["ear_r"] + m["ear_l"]) / 2 - np.array((0.0, 0.0, 0.012))
    hinge = np.array(Matrix.Rotation(math.radians(REST_HEAD_YAW), 3, "Z") @ Vector(hinge - pivot)) + pivot
    keys["talk"] = co + jaw[:, None] * (_rot_about(co, hinge, lat, math.radians(5.0)) - co)
    L.shape_key_add(name="Basis", from_mix=False)
    for name, pts in keys.items():
        kb = L.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", pts.astype(np.float32).ravel())
        kb.value = 0.0
    print("TAXI_TRIPO_SHAPES", list(keys))


def build_driver(coll):
    """Replace the old scanned driver with the sculpted one, fitted, coloured and alive."""
    for name in OLD_DRIVER:
        o = bpy.data.objects.get(name)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    H = load_sculpt()
    if H.name not in coll.objects:
        for c in list(H.users_collection):
            c.objects.unlink(H)
        coll.objects.link(H)
    grips = cut_own_wheel(H)
    mid = _copy(H, "_taxi_driver_mid")
    _decimate(mid, MID_TRIS)
    mid_lab = garment_labels(mid)
    lab_h = nearest_labels(_arrays(mid.data), mid_lab, _arrays(H.data))
    paint(H, lab_h)
    L = game_mesh(mid, mid_lab)
    unwrap(L)
    lab = nearest_labels(_arrays(mid.data), mid_lab, _arrays(L.data))
    bake(H, L, lab_h, lab)
    for o in (H, mid):
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)
    hand_w = fit_hands(L, lab, grips)
    shapes(L, lab, hand_w)
    L["credit"] = str(CREDIT)
    L["tripo"] = True
    print("TAXI_TRIPO_DRIVER_BUILT", len(L.data.vertices), "verts", len(L.data.polygons), "faces")
    return L
