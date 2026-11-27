"""Upgrades Episode 1's rigged Preay (`art-source/characters/preay/preay.blend`) for photorealistic,
high-detail monsoon survival horror with real skinned lower legs & bare muddy feet, natural
non-plastic wet hair, crisp fabric/skin/blood PBR maps, and polished natural `stand`/`hurry`
arm animations (eliminating stiff A-pose arms and wild overhead flailing).

Features:
  1. Idempotent backup (`preay_untrimmed_backup.blend` & `preay_source_albedo.png`) so re-runs
     never compound trims or grades.
  2. Cleanly trims the ragged wet funeral gown hem to mid-shin (~0.28-0.34 m) with an extruded
     dark inner lining cuff, removing all old melted/spiky foot polygons and zeroing `foot` weights
     on the dress.
  3. Grafts real MakeHuman Southeast Asian female lower legs, calves, ankles, and bare feet
     aligned millimeter-for-millimeter onto `preay_rig`'s leg/foot bones and skinned cleanly
     to `upperleg01.L/R`, `lowerleg01.L/R`, and `foot.L/R` (zero skirt-hem clipping!).
  4. Upgrades 2048x2048 PBR maps with unsharp micro-detail sharpening + 3D world-space vertical
     wet hair strand breakup (eliminating plastic bowling-ball sheen!), weathered linen weave,
     rain-soaked shoulder darkening, deep dark venous blood rivulets, and matching drowned-corpse
     skin + monsoon mud across face, hands, and bare legs/feet.
  5. Polishes `stand` (natural relaxed asymmetric arm drape & organic breathing instead of stiff
     A-pose) and `hurry` (predatory forward stalking arm swing instead of overhead flailing) while
     leaving `walk` and all clip timings/heel strikes 100% intact.

Usage:
    blender -b --factory-startup --python-exit-code 1 -P tools/characters/grade-preay-photoreal.py
    npm run assets -- ep1/preay
"""
import math
import shutil
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hair_cards as HC  # noqa: E402
import photoreal_surfaces as PS  # noqa: E402
BLEND = ROOT / "art-source/characters/preay/preay.blend"
BACKUP_BLEND = ROOT / "art-source/characters/preay/preay_untrimmed_backup.blend"
BACKUP_BC = ROOT / "art-source/characters/preay/preay_source_albedo.png"
MH_DIR = ROOT / "art-source/library/makehuman-sora"
OUT = ROOT / "art-export/ep1/preay.glb"


# ------------------------------------------------------------------ deterministic 2D & 3D noise
def _hash2(ix, iy, seed):
    ux = ix.astype(np.uint64)
    uy = iy.astype(np.uint64)
    n = (ux * np.uint64(374761393) + uy * np.uint64(668265263) + np.uint64(seed * 1442695041)) & np.uint64(0xFFFFFFFF)
    n = ((n ^ (n >> np.uint64(13))) * np.uint64(1274126177)) & np.uint64(0xFFFFFFFF)
    return (((n ^ (n >> np.uint64(16))) & np.uint64(0xFFFFFF)).astype(np.float32)) / float(0x1000000)


def fbm_grid(h, w, freqs=(6, 14, 34, 82), seed=31):
    ys = np.linspace(0.0, 1.0, h, endpoint=False, dtype=np.float32)
    xs = np.linspace(0.0, 1.0, w, endpoint=False, dtype=np.float32)
    out = np.zeros((h, w), dtype=np.float32)
    amp = 0.5
    total = 0.0
    for idx, f in enumerate(freqs):
        gx = xs * f
        gy = ys * f
        ix0 = np.floor(gx).astype(np.int32)
        iy0 = np.floor(gy).astype(np.int32)
        fx = gx - ix0
        fy = gy - iy0
        sx = fx * fx * (3.0 - 2.0 * fx)
        sy = fy * fy * (3.0 - 2.0 * fy)
        ix1 = (ix0 + 1) % f
        iy1 = (iy0 + 1) % f
        s = seed + idx * 101
        c00 = _hash2(ix0[None, :], iy0[:, None], s)
        c10 = _hash2(ix1[None, :], iy0[:, None], s)
        c01 = _hash2(ix0[None, :], iy1[:, None], s)
        c11 = _hash2(ix1[None, :], iy1[:, None], s)
        v = (c00 * (1 - sx[None, :]) + c10 * sx[None, :]) * (1 - sy[:, None]) + (
            c01 * (1 - sx[None, :]) + c11 * sx[None, :]
        ) * sy[:, None]
        out += v * amp
        total += amp
        amp *= 0.5
    return out / max(total, 1e-6)


def box_blur(img, radius=1):
    """Fast separable box blur for unsharp masking (2D or 3D HxWxC array)."""
    out = img.copy()
    acc = np.zeros_like(out)
    cnt = 0
    for dx in range(-radius, radius + 1):
        acc += np.roll(out, dx, axis=1)
        cnt += 1
    out = acc / cnt
    acc = np.zeros_like(out)
    cnt = 0
    for dy in range(-radius, radius + 1):
        acc += np.roll(out, dy, axis=0)
        cnt += 1
    return acc / cnt


def height_to_normal(height_map, strength=2.0):
    gx = (np.roll(height_map, -1, axis=1) - np.roll(height_map, 1, axis=1)) * 0.5 * strength
    gy = (np.roll(height_map, -1, axis=0) - np.roll(height_map, 1, axis=0)) * 0.5 * strength
    nx = -gx
    ny = -gy
    nz = np.ones_like(nx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    n = np.stack([nx * inv * 0.5 + 0.5, ny * inv * 0.5 + 0.5, nz * inv * 0.5 + 0.5, np.ones_like(nx)], axis=-1)
    return np.clip(n, 0.0, 1.0).astype(np.float32)


def smoothstep(a, b, x):
    t = np.clip((x - a) / max(b - a, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def img_to_np(img):
    w, h = img.size
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape(h, w, 4)


def make_img(name, arr, colorspace):
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, width=w, height=h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.clip(arr, 0.0, 1.0).astype(np.float32).ravel())
    img.pack()
    return img


def bake_vertex_xyz_and_ao(obj, h, w):
    """Splats 3D rest-pose vertex (x, y, z) and mesh cavity AO into UV space so procedural
    strands, rain streaks, mud rise, and contact shadows align cleanly in 3D world space
    regardless of Smart-UV island rotations!"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    n_v = len(bm.verts)
    ao_v = np.ones(n_v, dtype=np.float32)
    xyz_v = np.empty((n_v, 3), dtype=np.float32)
    for i, v in enumerate(bm.verts):
        xyz_v[i] = (v.co.x, v.co.y, v.co.z)
        if not v.link_edges:
            continue
        nbrs = [e.other_vert(v).co for e in v.link_edges]
        mean = sum(nbrs, Vector((0, 0, 0))) / len(nbrs)
        concavity = (mean - v.co).dot(v.normal)
        ao_v[i] = float(np.clip(1.0 - max(0.0, concavity) * 34.0, 0.28, 1.0))
    bm.free()

    uv_data = obj.data.uv_layers.active.data
    xyz_sum = np.zeros((h, w, 3), dtype=np.float32)
    ao_sum = np.zeros((h, w), dtype=np.float32)
    cnt = np.zeros((h, w), dtype=np.float32)
    for loop in obj.data.loops:
        u, v_uv = uv_data[loop.index].uv
        px = int(np.clip((u % 1.0) * (w - 1), 0, w - 1))
        py = int(np.clip((v_uv % 1.0) * (h - 1), 0, h - 1))
        vi = loop.vertex_index
        xyz_sum[py, px] += xyz_v[vi]
        ao_sum[py, px] += ao_v[vi]
        cnt[py, px] += 1.0

    safe_c = np.maximum(cnt, 1.0)
    xyz_map = np.where(cnt[..., None] > 0, xyz_sum / safe_c[..., None], 0.0)
    ao_map = np.where(cnt > 0, ao_sum / safe_c, 0.0)
    mask = (cnt > 0).astype(np.float32)
    for _ in range(18):
        m_acc = np.zeros_like(mask)
        p_acc = np.zeros_like(xyz_map)
        a_acc = np.zeros_like(ao_map)
        pm = xyz_map * mask[..., None]
        am = ao_map * mask
        for dy in (-2, 0, 2):
            for dx in (-2, 0, 2):
                m_s = np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
                p_acc += np.roll(np.roll(pm, dy, axis=0), dx, axis=1)
                a_acc += np.roll(np.roll(am, dy, axis=0), dx, axis=1)
                m_acc += m_s
        valid = m_acc > 1e-4
        inv_m = 1.0 / np.maximum(m_acc, 1e-4)
        xyz_map = np.where(mask[..., None] > 0.5, xyz_map, np.where(valid[..., None], p_acc * inv_m[..., None], xyz_map))
        ao_map = np.where(mask > 0.5, ao_map, np.where(valid, a_acc * inv_m, ao_map))
        mask = np.where(valid, 1.0, mask)
    xyz_map[..., 2] = np.where(mask > 0.1, xyz_map[..., 2], 0.9)
    ao_map = np.where(mask > 0.1, ao_map, 0.92)
    return xyz_map, ao_map


# ------------------------------------------------------------------ 1. Open untouched base blend
if not BACKUP_BLEND.exists():
    shutil.copy2(BLEND, BACKUP_BLEND)
    print(f"[preay_photoreal] backed up untouched blend -> {BACKUP_BLEND}", flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=str(BACKUP_BLEND))

body = bpy.data.objects["preay_body"]
rig = bpy.data.objects["preay_rig"]
coll = body.users_collection[0] if body.users_collection else bpy.context.scene.collection

# Put rig in exact rest pose while modifying meshes & weights
if rig.animation_data:
    rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.scale = (1, 1, 1)
bpy.context.scene.frame_set(1)

# Remove any old grafted meshes if re-running
for old_name in ("preay_legs", "preay_hair_cards"):
    old_o = bpy.data.objects.get(old_name)
    if old_o:
        bpy.data.objects.remove(old_o, do_unlink=True)

# ------------------------------------------------------------------ 2. Trim ragged dress hem to mid-shin (~0.30m)
# Removes old melted nub feet & spiky bottom polygons cleanly and gives the gown an authentic
# ragged wet lower-calf hem with tucked dark inner cloth thickness so her real bare legs emerge cleanly!
arm_mod = next((m for m in body.modifiers if m.type == "ARMATURE"), None)
if arm_mod:
    arm_mod.show_viewport = False

def ragged_hem_z(x, y):
    ang = math.atan2(y, x)
    return (
        0.305
        + 0.022 * math.sin(ang * 3.0 + 0.5)
        + 0.015 * math.cos(ang * 5.0 - 0.8)
        + 0.008 * math.sin(ang * 9.0 + 1.2)
    )

bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# Gently flare the lower gown (z = 0.28..0.80) into a natural flowing A-line bell (with generous
# rear clearance for knee bend) so calves stay cleanly inside the dress across stand, walk & hurry!
for v in bm.verts:
    if 0.24 < v.co.z < 0.80 and abs(v.co.x) < 0.28:
        t = ((0.80 - v.co.z) / 0.56) ** 1.1
        v.co.x *= 1.0 + 0.24 * t
        if v.co.y > 0.0:
            v.co.y *= 1.0 + 0.48 * t
        else:
            v.co.y *= 1.0 + 0.24 * t

# Delete all faces below the organic ragged wet hem height
drop_faces = []
for f in bm.faces:
    c = f.calc_center_median()
    if c.z < ragged_hem_z(c.x, c.y):
        drop_faces.append(f)
bmesh.ops.delete(bm, geom=drop_faces, context="FACES")

# Remove any tiny disconnected leftover islands (e.g. stray ankle/toe shards)
visited = set()
components = []
for v in bm.verts:
    if v in visited:
        continue
    comp = []
    stack = [v]
    visited.add(v)
    while stack:
        cur = stack.pop()
        comp.append(cur)
        for e in cur.link_edges:
            ov = e.other_vert(cur)
            if ov not in visited:
                visited.add(ov)
                stack.append(ov)
    components.append(comp)
if len(components) > 1:
    main_comp = max(components, key=len)
    junk = [v for c in components if c is not main_comp for v in c]
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")

# Snap & smoothly relax the ragged bottom boundary ring so the hem edge has zero sawtooth jags
hem_verts = [v for v in bm.verts if v.is_boundary and v.co.z < 0.42]
for v in hem_verts:
    hz = ragged_hem_z(v.co.x, v.co.y)
    v.co.z = v.co.z * 0.35 + hz * 0.65
for _ in range(4):
    new_pos = {}
    for v in hem_verts:
        b_nbrs = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
        if b_nbrs:
            avg = sum((n.co for n in b_nbrs), Vector((0, 0, 0))) / len(b_nbrs)
            new_pos[v] = v.co.lerp(avg, 0.45)
    for v, p in new_pos.items():
        v.co = p

# Extrude bottom boundary edges slightly inward + upward into a dark shaded inner cuff lining
# so looking slightly upward under the dress shows real wet hem thickness (never a paper-thin gap!)
hem_edges = [e for e in bm.edges if e.is_boundary and all(v.co.z < 0.42 for v in e.verts)]
if hem_edges:
    ret = bmesh.ops.extrude_edge_only(bm, edges=hem_edges)
    ext_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in ext_verts:
        v.co.x *= 0.93
        v.co.y *= 0.91
        v.co.z += 0.045

bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(body.data)
bm.free()
for p in body.data.polygons:
    p.use_smooth = True
body.data.update()

# Re-shape lower dress skin weights on `preay_body` cleanly (ZERO `foot.L/R` weights anywhere on dress!)
co_b = np.empty(len(body.data.vertices) * 3, dtype=np.float32)
body.data.vertices.foreach_get("co", co_b)
co_b = co_b.reshape(-1, 3)

groups = list(body.vertex_groups)
gnames = [g.name for g in groups]
col = {n: i for i, n in enumerate(gnames)}
w_arr = np.zeros((len(body.data.vertices), len(groups)), dtype=np.float32)
for v in body.data.vertices:
    for g in v.groups:
        w_arr[v.index, g.group] = g.weight

bx, by, bz = co_b[:, 0], co_b[:, 1], co_b[:, 2]
hands = (np.abs(bx) > 0.19) & (bz > 0.62) & (bz < 0.93)
dress = (bz < 0.86) & (~hands)
u_d = np.clip((0.86 - bz) / (0.86 - 0.28), 0.0, 1.0)
# Smooth flowing gown weights: gentle knee-bend transition across z=0.66..0.28 avoids any
# horizontal ripple while tracking both legs smoothly across stand, walk, and hurry!
pelvis_w = 0.12 + 0.88 * np.clip(1.0 - u_d / 0.62, 0.0, 1.0) ** 1.45
leg_share = 1.0 - pelvis_w
shin_share = leg_share * 0.44 * smoothstep(0.66, 0.28, bz)
thigh_share = leg_share - shin_share
left_w = smoothstep(-0.12, 0.12, bx)

new_dw = np.zeros_like(w_arr)
new_dw[:, col["root"]] = pelvis_w
new_dw[:, col["upperleg01.L"]] = thigh_share * left_w
new_dw[:, col["upperleg01.R"]] = thigh_share * (1.0 - left_w)
new_dw[:, col["lowerleg01.L"]] = shin_share * left_w
new_dw[:, col["lowerleg01.R"]] = shin_share * (1.0 - left_w)

keep_waist = smoothstep(0.76, 0.86, bz)[:, None]
w_arr[dress] = (w_arr * keep_waist + new_dw * (1.0 - keep_waist))[dress]
# Guarantee zero residual foot weights anywhere on preay_body
for fn in ("foot.L", "foot.R"):
    if fn in col:
        w_arr[:, col[fn]] = 0.0

# Cap to 4 weights per vertex and normalize
np.put_along_axis(w_arr, np.argsort(-w_arr, axis=1)[:, 4:], 0.0, axis=1)
w_arr /= np.maximum(w_arr.sum(axis=1, keepdims=True), 1e-9)
for g in body.vertex_groups:
    g.remove(range(len(body.data.vertices)))
for j, n in enumerate(gnames):
    g = body.vertex_groups[n]
    for vi in np.nonzero(w_arr[:, j] > 1e-4)[0]:
        g.add([int(vi)], float(w_arr[vi, j]), "REPLACE")

if arm_mod:
    arm_mod.show_viewport = True
    arm_mod.use_deform_preserve_volume = True

# ------------------------------------------------------------------ 3. Graft REAL MakeHuman lower legs & bare feet!
verts_mh = []
uvs_mh = []
faces_mh = []
face_uvs_mh = []
grp = ""
for line in (MH_DIR / "base.obj").read_text().splitlines():
    parts = line.split()
    if not parts:
        continue
    if parts[0] == "v":
        verts_mh.append([float(parts[1]), float(parts[2]), float(parts[3])])
    elif parts[0] == "vt":
        uvs_mh.append((float(parts[1]), float(parts[2])))
    elif parts[0] == "g":
        grp = parts[1]
    elif parts[0] == "f" and grp == "body":
        toks = [p.split("/") for p in parts[1:]]
        faces_mh.append([int(t[0]) - 1 for t in toks])
        face_uvs_mh.append([int(t[1]) - 1 for t in toks])

for tname in ("asian-female-young.target", "universal-female-young-averagemuscle-averageweight.target"):
    for line in (MH_DIR / tname).read_text().splitlines():
        if line and not line.startswith("#"):
            p = line.split()
            idx = int(p[0])
            verts_mh[idx][0] += float(p[1])
            verts_mh[idx][1] += float(p[2])
            verts_mh[idx][2] += float(p[3])

body_used = sorted({i for f in faces_mh for i in f})
min_y_mh = min(verts_mh[i][1] for i in body_used)
max_y_mh = max(verts_mh[i][1] for i in body_used)
mh_scale = 1.58 / max(0.01, max_y_mh - min_y_mh)

def mh_to_preay_rig(v):
    """Align MakeHuman's wide A-pose legs cleanly onto `preay_rig`'s exact vertical leg bones:
    upperleg01 (±0.082, 0.000, 0.800) -> knee (±0.078, -0.004, 0.445) -> ankle (±0.074, +0.030, 0.075)."""
    x = v[0] * mh_scale
    y = -v[2] * mh_scale
    z = (v[1] - min_y_mh) * mh_scale
    side = 1.0 if x >= 0.0 else -1.0
    # Pivot each leg inward by 6.2 deg around MakeHuman hip socket (±0.093, -0.034, 0.800)
    hip_x = side * 0.093
    hip_z = 0.800
    dx = x - hip_x
    dz = z - hip_z
    ang = -side * math.radians(6.2)
    ca, sa = math.cos(ang), math.sin(ang)
    rx = hip_x + dx * ca - dz * sa
    rz = hip_z + dx * sa + dz * ca
    # Shift leg axis cleanly onto preay_rig's exact knee/ankle line (x=±0.075, y=+0.030 at ankle)
    # and slenderize calf/shin width (0.88x) for Preay's gaunt ghostly frame; taper subtly near
    # the top edge (z > 0.33m) tucked inside the hollow dress so upper calves NEVER poke through!
    bone_x = side * (0.080 - 0.006 * np.clip((0.800 - rz) / 0.725, 0.0, 1.0))
    cur_center_x = side * 0.089
    top_taper = 1.0 - 0.22 * float(np.clip((rz - 0.29) / 0.10, 0.0, 1.0))
    top_fwd = -0.014 * float(np.clip((rz - 0.29) / 0.10, 0.0, 1.0))
    rx = bone_x + (rx - cur_center_x) * 0.86 * top_taper
    ry = (y + 0.044) * 0.88 * top_taper + top_fwd
    return (float(rx), float(ry), float(rz))

bl_verts = [mh_to_preay_rig(v) for v in verts_mh]

# Keep lower calves, ankles, and bare feet below z = 0.39m (tucked ~8.5cm cleanly inside the
# ragged wet dress hem at z ~0.305m so neither front stride nor rear bend exposes the cut edge!)
LEG_CUT_Z = 0.39
leg_faces = []
leg_face_uvs = []
leg_used = set()
for f, fu in zip(faces_mh, face_uvs_mh):
    if all(bl_verts[i][2] <= LEG_CUT_Z for i in f):
        leg_faces.append(f)
        leg_face_uvs.append(fu)
        leg_used.update(f)

remap = {old: new for new, old in enumerate(sorted(leg_used))}
leg_co = [bl_verts[old] for old in sorted(leg_used)]
# Ground bare soles cleanly at z = 0.000
leg_min_z = min(p[2] for p in leg_co)
leg_co = [(p[0], p[1], p[2] - leg_min_z) for p in leg_co]

leg_mesh = bpy.data.meshes.new("preay_legs")
leg_mesh.from_pydata(leg_co, [], [[remap[i] for i in f] for f in leg_faces])
uv_l = leg_mesh.uv_layers.new(name="UVMap")
for poly, fu in zip(leg_mesh.polygons, leg_face_uvs):
    poly.use_smooth = True
    for loop_idx, uv_idx in zip(poly.loop_indices, fu):
        uv_l.data[loop_idx].uv = uvs_mh[uv_idx]
leg_mesh.update()

legs_obj = bpy.data.objects.new("preay_legs", leg_mesh)
coll.objects.link(legs_obj)

# Keep clean organic MakeHuman quad topology (~5k tris with smooth normals — super clean & keeps preay.glb < 2 MiB!)
for p in legs_obj.data.polygons:
    p.use_smooth = True
legs_obj.data.update()

# Skin `preay_legs` cleanly to `preay_rig` (`upperleg01.L/R`, `lowerleg01.L/R`, `foot.L/R`)
for b in rig.data.bones:
    legs_obj.vertex_groups.new(name=b.name)

for v in legs_obj.data.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    s = "L" if x >= 0.0 else "R"
    # Smooth knee blend around KNEE = 0.445m
    w_thigh = float(smoothstep(0.40, 0.49, z))
    # Smooth ankle/foot blend around ANKLE = 0.075m; toes & forefoot (y < 0.005) follow foot 100%
    w_foot_z = float(smoothstep(0.105, 0.045, z))
    w_forefoot = float(smoothstep(0.035, -0.025, y) * smoothstep(0.11, 0.03, z))
    w_foot = max(w_foot_z * 0.72, w_forefoot)
    w_shin = max(0.0, 1.0 - w_thigh - w_foot)
    tot = w_thigh + w_shin + w_foot
    if tot < 1e-6:
        w_shin, tot = 1.0, 1.0
    if w_thigh / tot > 1e-4:
        legs_obj.vertex_groups[f"upperleg01.{s}"].add([v.index], w_thigh / tot, "REPLACE")
    if w_shin / tot > 1e-4:
        legs_obj.vertex_groups[f"lowerleg01.{s}"].add([v.index], w_shin / tot, "REPLACE")
    if w_foot / tot > 1e-4:
        legs_obj.vertex_groups[f"foot.{s}"].add([v.index], w_foot / tot, "REPLACE")

legs_arm = legs_obj.modifiers.new("Armature", "ARMATURE")
legs_arm.object = rig
legs_arm.use_deform_preserve_volume = True
legs_obj.parent = rig

# ------------------------------------------------------------------ 4. Build AAA layered wet hair cards & recess inner scalp core!
# Build BVH-conformed 3-tier alpha-cutout wet hair cards BEFORE recessing the solid sculpted hair
# shell so the outer wispy strands follow her real head/shoulder contour while the inner solid
# hair shrinks ~8-14mm underneath as an invisible shadow scalp core (ZERO cartoon clay helmet!).
hair_mat, hair_imgs = HC.build_wet_hair_card_material(prefix="preay", seed=1932)
hair_obj = HC.build_preay_hair_cards(body, rig, hair_mat, coll, seed=1932)

# Now load source albedo & gently shrink/recess ONLY the solid hair vertices on `preay_body` inward!
mat = body.data.materials[0]
mat.name = "M_preay_scan"

if BACKUP_BC.exists():
    src_img = bpy.data.images.load(str(BACKUP_BC))
else:
    orig = next(i for i in bpy.data.images if i.size[0] >= 1024)
    orig.filepath_raw = str(BACKUP_BC)
    orig.file_format = "PNG"
    orig.save()
    src_img = orig

W, H = src_img.size
raw = img_to_np(src_img)
rgb_orig = raw[..., :3].copy()

# Recess solid sculpted hair shell on `preay_body` inward (and melt chunky lower hanging tips on
# chest/back flush into the dress!) so layered alpha hair cards define 100% of the hair silhouette!
uv_b = body.data.uv_layers.active.data
vlum = np.ones(len(body.data.vertices), dtype=np.float32)
for l in body.data.loops:
    u_l, v_l = uv_b[l.index].uv
    px_x = min(W - 1, max(0, int((u_l % 1.0) * W)))
    px_y = min(H - 1, max(0, int((v_l % 1.0) * H)))
    r0, g0, b0 = rgb_orig[px_y, px_x]
    vlum[l.vertex_index] = min(vlum[l.vertex_index], 0.2126 * r0 + 0.7152 * g0 + 0.0722 * b0)

if arm_mod:
    arm_mod.show_viewport = False
bm_sh = bmesh.new()
bm_sh.from_mesh(body.data)
bm_sh.verts.ensure_lookup_table()
lower_hair_verts = []
for v in bm_sh.verts:
    if vlum[v.index] < 0.135 and v.co.z > 0.84:
        is_face = v.co.z > 1.34 and v.co.y < -0.04 and abs(v.co.x) < 0.065
        if not is_face:
            if v.co.z > 1.36:
                v.co -= v.normal * 0.009
            else:
                # Flatten chunky sculpted hanging lock lumps smoothly flush into chest/back dress!
                v.co -= v.normal * 0.020
                lower_hair_verts.append(v)
if lower_hair_verts:
    for _ in range(6):
        bmesh.ops.smooth_vert(bm_sh, verts=lower_hair_verts, factor=0.55, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bmesh.ops.recalc_face_normals(bm_sh, faces=bm_sh.faces)
bm_sh.to_mesh(body.data)
bm_sh.free()
body.data.update()

# Clean topology-preserving decimate of `preay_body` from ~51k -> ~36k tris (silky smooth & keeps
# packed KTX2 `preay.glb` well under the 2.0 MiB budget in tests/unit/taxiAssets.test.ts!)
cur_b_tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
if cur_b_tris > 36000:
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    dec = body.modifiers.new("preay_opt_dec", "DECIMATE")
    dec.ratio = 36000.0 / cur_b_tris
    dec.use_collapse_triangulate = True
    bpy.ops.object.modifier_move_to_index(modifier=dec.name, index=0)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    for p in body.data.polygons:
        p.use_smooth = True
    body.data.update()

if arm_mod:
    arm_mod.show_viewport = True

# Multi-scale unsharp mask to recover razor-crisp fine face/knuckle/cloth-fold micro-contrast!
blur_s = box_blur(rgb_orig, radius=2)
blur_m = box_blur(rgb_orig, radius=5)
rgb = np.clip(rgb_orig + 0.42 * (rgb_orig - blur_s) + 0.24 * (rgb_orig - blur_m), 0.0, 1.0)

xyz_uv, ao_uv = bake_vertex_xyz_and_ao(body, H, W)
x_uv, y_uv, z_uv = xyz_uv[..., 0], xyz_uv[..., 1], xyz_uv[..., 2]
n_big = fbm_grid(H, W, freqs=(6, 15, 36, 84), seed=55)
n_med = fbm_grid(H, W, freqs=(16, 42, 108), seed=89)
n_fine = fbm_grid(H, W, freqs=(40, 110, 240), seed=129)

# Load REAL photographed CC0 village materials (handloomed rough linen, forest mud, red laterite, drowned skin pores!)
photo = PS.load_village_photoreal_pack()
linen_bc = PS.sample_cylindrical(photo["linen_bc"], xyz_uv, tile_m=0.14)[..., :3]
linen_n = PS.sample_cylindrical(photo["linen_n"], xyz_uv, tile_m=0.14)
linen_orm = PS.sample_cylindrical(photo["linen_orm"], xyz_uv, tile_m=0.14)
mud_bc = PS.sample_cylindrical(photo["mud_bc"], xyz_uv, tile_m=0.22)[..., :3] * 0.58 + PS.sample_cylindrical(photo["laterite_bc"], xyz_uv, tile_m=0.20)[..., :3] * 0.42
mud_n = PS.sample_cylindrical(photo["mud_n"], xyz_uv, tile_m=0.22)
skin_pore_n = PS.sample_cylindrical(photo["skin_n"], xyz_uv, tile_m=0.12)

# Normalize photographed linen luminance around 1.0 so it imparts REAL woven threads & slub grain!
linen_lum = 0.2126 * linen_bc[..., 0] + 0.7152 * linen_bc[..., 1] + 0.0722 * linen_bc[..., 2]
linen_detail = np.clip(linen_bc / np.maximum(linen_lum.mean(), 0.1), 0.58, 1.38)

# 3D world-aligned vertical wet hair strand breakup (azimuth around head/shoulders + vertical flow!)
# Eliminates smooth plastic bowling-ball sheen across EVERY UV island regardless of rotation!
theta_uv = np.arctan2(y_uv, x_uv)
strand_phase = theta_uv * 115.0 + x_uv * 220.0 + (n_big - 0.5) * 9.5 + np.sin(z_uv * 14.0) * 1.4
strand_coarse = np.sin(strand_phase) * 0.5 + 0.5
strand_fine = np.sin(strand_phase * 2.7 + (n_med - 0.5) * 5.0) * 0.5 + 0.5
hair_strand = np.clip(strand_coarse * 0.55 + strand_fine * 0.45, 0.0, 1.0)

# 3D world-aligned vertical rain drips / cloth drapery creases
drip_phase = theta_uv * 28.0 + (n_big - 0.5) * 6.0
rain_streak = np.clip(np.sin(drip_phase) * 0.5 + 0.5, 0.0, 1.0)

# Pixel classification on sharpened source albedo:
# Strictly separate TRUE crimson dress bloodstains from warm face/forearm/hand skin!
# Note: sculpted lower hair tips below z=1.28m on chest/back are repainted as damp cotton dress so
# ONLY our real 3D layered wet hair cards (`preay_hair_cards`) form the flowing lower hair over the gown!
lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
hair_mask_raw = np.clip((0.145 - lum) * 10.5, 0.0, 1.0) * np.clip((z_uv - 0.65) * 3.0, 0.0, 1.0)
# Keep dark scalp shadow ONLY on the head/upper-neck core (z > 1.28m); replace painted lower hair blotches
# on chest/back with weathered damp cotton cloth so ZERO chunky sculpted black tubes appear beneath hair cards!
lower_painted_hair = hair_mask_raw * np.clip((1.30 - z_uv) / 0.08, 0.0, 1.0)
hair_mask = hair_mask_raw * np.clip((z_uv - 1.24) / 0.08, 0.0, 1.0)

is_face_zone = (z_uv > 1.30) & (y_uv < -0.01) & (np.abs(x_uv) < 0.10)
is_neck_zone = (z_uv > 1.24) & (z_uv <= 1.34) & (np.abs(x_uv) < 0.075)
is_hand_zone = (np.abs(x_uv) > 0.175) & (z_uv > 0.60) & (z_uv < 0.97)
skin_region = (is_face_zone | is_neck_zone | is_hand_zone).astype(np.float32)

red_excess = rgb[..., 0] - np.maximum(rgb[..., 1], rgb[..., 2])
red_ratio = rgb[..., 0] / np.maximum(rgb[..., 1] + 0.04, 0.04)
# Only genuine saturated bloodstains on the dress trigger blood_mask (NEVER warm skin!)
blood_raw = np.clip((red_excess - 0.125) * 6.0, 0.0, 1.0) * np.clip((red_ratio - 1.62) * 2.6, 0.0, 1.0)
# Allow only subtle dried blood traces on fingertips/face without drowning skin in dark maroon
blood_mask = blood_raw * (1.0 - hair_mask) * (1.0 - 0.85 * skin_region)

skin_hue = np.clip((rgb[..., 0] - rgb[..., 2] - 0.025) * 5.5, 0.0, 1.0) * np.clip((0.64 - lum) * 2.8, 0.0, 1.0)
skin_mask = np.clip(np.maximum(skin_region * (1.0 - hair_mask), skin_hue * (1.0 - blood_mask) * (1.0 - hair_mask)), 0.0, 1.0)
skin_mask = np.clip(skin_mask * (1.0 - blood_mask) * (1.0 - hair_mask), 0.0, 1.0)
cloth_mask = np.clip(1.0 - hair_mask - blood_mask - skin_mask, 0.0, 1.0)

# A. Funeral gown cloth: REAL photographed weathered raw Cambodian mourning linen + damp rain stains!
shoulder_soak = np.clip((z_uv - 1.08) / 0.24, 0.0, 1.0) * (0.14 + 0.10 * rain_streak)
cloth_lum_src = np.where(lower_painted_hair > 0.25, 0.44 + 0.08 * n_big, lum)
cloth_lum = np.clip(cloth_lum_src * 0.64 + 0.085 - shoulder_soak, 0.14, 0.58)
damp_stain = (0.74 + 0.30 * n_big) * (0.90 + 0.16 * n_med)
cloth_rgb = (
    cloth_lum[..., None]
    * np.array([0.89, 0.85, 0.76], dtype=np.float32)
    * damp_stain[..., None]
    * (0.58 + 0.42 * linen_detail)
)

# B. Rich coagulated venous dried bloodstains soaking organically into the photographed linen fibers!
blood_clot = np.clip((blood_mask - 0.35) * 2.2, 0.0, 1.0)
blood_rgb = np.stack(
    [
        np.clip(rgb[..., 0] * 0.36 + 0.032 - blood_clot * 0.065, 0.042, 0.24),
        np.clip(rgb[..., 1] * 0.10 + 0.009, 0.007, 0.038),
        np.clip(rgb[..., 2] * 0.09 + 0.008, 0.007, 0.032),
    ],
    axis=-1,
) * (0.72 + 0.36 * linen_detail) * (0.82 + 0.24 * n_fine[..., None])

# C. Drowned-corpse skin (gaunt face behind parted hair, forearms, clawed hands):
# Realistic mottled dead-flesh pallor with faint bluish capillary chill & dirty fingernails/knuckles!
knuckle_grime = (is_hand_zone.astype(np.float32) * np.clip((0.74 - z_uv) / 0.11, 0.0, 1.0)) * (0.26 + 0.32 * n_fine)
skin_desat = lum[..., None] * 0.72 + rgb * 0.28
skin_rgb = (
    np.clip(skin_desat * np.array([0.80, 0.78, 0.71], dtype=np.float32) + 0.105, 0.18, 0.46)
    * (0.82 + 0.26 * n_big[..., None])
    * (0.88 + 0.22 * n_fine[..., None])
)
# Subtle sub-dermal livor mortis bruise & real photographed dirt on fingertips/knuckles
skin_rgb = skin_rgb * (1.0 - knuckle_grime[..., None] * 0.56) + (mud_bc * 0.45) * (knuckle_grime[..., None] * 0.56)

# D. Deep matte shadow scalp core under our 3D layered wet hair cards (zero shiny helmet dome!)
hair_rgb = np.full((H, W, 3), [0.015, 0.013, 0.012], dtype=np.float32)

graded = (
    cloth_rgb * cloth_mask[..., None]
    + blood_rgb * blood_mask[..., None]
    + skin_rgb * skin_mask[..., None]
    + hair_rgb * hair_mask[..., None]
)

# REAL photographed Cambodian village forest/laterite mud wicking up the frayed lower hem (z = 0.27..0.54m)
mud_rise = np.clip((0.54 - z_uv) / 0.27, 0.0, 1.0) ** 1.40
mud_rise = np.clip(mud_rise * (0.50 + 0.58 * n_big), 0.0, 0.82)
mud_color = np.clip(mud_bc * 0.52, 0.04, 0.22)
graded = graded * (1.0 - mud_rise[..., None]) + mud_color * mud_rise[..., None]

# Subtle baked mesh cavity AO (deepens real cloth folds & crevices)
graded *= (0.68 + 0.32 * ao_uv[..., None])
bc_rgba = np.concatenate([np.clip(graded, 0.0, 1.0), np.ones((H, W, 1), dtype=np.float32)], axis=-1)

# Calibrated PBR Roughness driven by real photographed linen & mud ORM!
cloth_rough = np.clip(0.72 + 0.26 * linen_orm[..., 1] - shoulder_soak * 0.30, 0.72, 0.96)
rough = (
    cloth_rough * cloth_mask
    + 0.36 * blood_mask
    + 0.72 * skin_mask
    + 0.90 * hair_mask
)
rough = np.clip(rough + (n_fine - 0.5) * 0.07 - mud_rise * 0.12, 0.28, 0.96)
rm_rgba = np.stack([np.ones_like(rough), rough, np.zeros_like(rough), np.ones_like(rough)], axis=-1)

# High-detail tangent Normal map combining sculpted fold luminance + REAL photographed linen/mud/skin normals!
height_field = (
    lum * 0.72 * (cloth_mask + skin_mask)
    + n_fine * 0.26 * (cloth_mask + skin_mask)
    + blood_mask * (0.22 + 0.14 * n_fine)
)
base_nm = height_to_normal(height_field, strength=1.15)
nm_rgba = PS.blend_tangent_normals(base_nm, linen_n, cloth_mask * 0.78)
nm_rgba = PS.blend_tangent_normals(nm_rgba, skin_pore_n, skin_mask * 0.85)
nm_rgba = PS.blend_tangent_normals(nm_rgba, mud_n, mud_rise * 0.85)

# Downsample ORM & Normal maps cleanly (512x512 body N/ORM, 256x256 leg N/ORM) so full 2048px body
# albedo + 1024px alpha hair cards + 1024px leg albedo pack well UNDER the 2.0 MiB GLB budget!
def _half(arr):
    hh, ww = arr.shape[:2]
    return 0.25 * (arr[0:hh:2, 0:ww:2] + arr[1:hh:2, 0:ww:2] + arr[0:hh:2, 1:ww:2] + arr[1:hh:2, 1:ww:2])

rm_512 = _half(_half(rm_rgba))
nm_512 = _half(_half(nm_rgba))
nv = nm_512[..., :3] * 2.0 - 1.0
nv /= np.sqrt(np.sum(nv * nv, axis=-1, keepdims=True) + 1e-8)
nm_512 = np.concatenate([nv * 0.5 + 0.5, np.ones((nm_512.shape[0], nm_512.shape[1], 1), dtype=np.float32)], axis=-1)

img_bc = make_img("T_preay_photoreal_BC", bc_rgba, "sRGB")
img_rm = make_img("T_preay_photoreal_ORM", rm_512, "Non-Color")
img_nm = make_img("T_preay_photoreal_N", nm_512, "Non-Color")

nt = mat.node_tree
nodes, links = nt.nodes, nt.links
bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
for n in list(nodes):
    if n.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL"):
        nodes.remove(n)

bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Specular IOR Level"].default_value = 0.26

n_bc = nodes.new("ShaderNodeTexImage")
n_bc.image = img_bc
links.new(n_bc.outputs["Color"], bsdf.inputs["Base Color"])

n_rm = nodes.new("ShaderNodeTexImage")
n_rm.image = img_rm
n_sep = nodes.new("ShaderNodeSeparateColor")
links.new(n_rm.outputs["Color"], n_sep.inputs["Color"])
links.new(n_sep.outputs["Green"], bsdf.inputs["Roughness"])
links.new(n_sep.outputs["Blue"], bsdf.inputs["Metallic"])

n_nm = nodes.new("ShaderNodeTexImage")
n_nm.image = img_nm
n_nmap = nodes.new("ShaderNodeNormalMap")
n_nmap.inputs["Strength"].default_value = 1.18
links.new(n_nm.outputs["Color"], n_nmap.inputs["Color"])
links.new(n_nmap.outputs["Normal"], bsdf.inputs["Normal"])

# ------------------------------------------------------------------ 5. Matching PBR maps for grafted `preay_legs`
# 1024x1024 albedo + 512x512 ORM/Normal gives ultra-crisp texel density on bare calves/feet while keeping GLB < 2 MiB!
mh_tex_raw = bpy.data.images.load(str(MH_DIR / "young_lightskinned_female_diffuse3.png"))
w_m, h_m = mh_tex_raw.size
if max(w_m, h_m) > 1024:
    s = 1024 / max(w_m, h_m)
    mh_tex_raw.scale(int(w_m * s), int(h_m * s))
mh_arr = img_to_np(mh_tex_raw)
HL, WL = mh_arr.shape[:2]
l_rgb = mh_arr[..., :3].copy()

l_xyz_uv, l_ao_uv = bake_vertex_xyz_and_ao(legs_obj, HL, WL)
z_leg_uv = l_xyz_uv[..., 2]
ln_big = fbm_grid(HL, WL, freqs=(6, 15, 34, 72), seed=107)
ln_fine = fbm_grid(HL, WL, freqs=(32, 84, 176), seed=211)

l_lum = 0.2126 * l_rgb[..., 0] + 0.7152 * l_rgb[..., 1] + 0.0722 * l_rgb[..., 2]
l_desat = l_lum[..., None] * 0.74 + l_rgb * 0.26
# Exact match to Preay's cold drowned corpse-ash hands & face
leg_skin = np.clip(l_desat * np.array([0.74, 0.72, 0.65], dtype=np.float32) + 0.032, 0.08, 0.46)
leg_skin *= (0.78 + 0.30 * ln_big[..., None]) * (0.88 + 0.18 * ln_fine[..., None])

# Subtle purplish-grey livor mortis bruising & mottled chill on shins & ankles
bruise = np.clip((0.36 - z_leg_uv) / 0.36, 0.0, 1.0) * np.clip((ln_big - 0.36) * 2.2, 0.0, 0.52)
bruise_col = np.array([0.18, 0.16, 0.19], dtype=np.float32)
leg_skin = leg_skin * (1.0 - bruise[..., None]) + bruise_col * bruise[..., None]

# Wet dark photographed Cambodian village mud splashing up bare soles, toes, ankles, and lower shins!
leg_mud_bc = np.clip(
    (PS.sample_cylindrical(photo["mud_bc"], l_xyz_uv, tile_m=0.20)[..., :3] * 0.58
     + PS.sample_cylindrical(photo["laterite_bc"], l_xyz_uv, tile_m=0.18)[..., :3] * 0.42) * 0.52,
    0.04, 0.22,
)
leg_mud_n = PS.sample_cylindrical(photo["mud_n"], l_xyz_uv, tile_m=0.20)
leg_skin_pore_n = PS.sample_cylindrical(photo["skin_n"], l_xyz_uv, tile_m=0.12)

foot_mud = np.clip((0.20 - z_leg_uv) / 0.20, 0.0, 1.0) ** 1.25
foot_mud = np.clip(foot_mud * (0.60 + 0.54 * ln_big), 0.0, 0.85)
leg_skin = leg_skin * (1.0 - foot_mud[..., None]) + leg_mud_bc * foot_mud[..., None]

# Faint dried blood trickles running down from inside the tattered bloody hem onto shins
trickle = np.clip((z_leg_uv - 0.12) / 0.22, 0.0, 1.0) * np.clip((ln_fine - 0.60) * 5.0, 0.0, 0.68)
leg_skin = leg_skin * (1.0 - trickle[..., None]) + np.array([0.15, 0.024, 0.020], dtype=np.float32) * trickle[..., None]

# Deep soft contact shadow directly underneath the dress hem overhang (z > 0.28m)
skirt_ao = np.clip(1.0 - np.clip((z_leg_uv - 0.27) / 0.11, 0.0, 1.0) * 0.74, 0.22, 1.0)
leg_skin *= (0.70 + 0.30 * l_ao_uv[..., None]) * skirt_ao[..., None]

leg_bc_rgba = np.concatenate([np.clip(leg_skin, 0.0, 1.0), np.ones((HL, WL, 1), dtype=np.float32)], axis=-1)
leg_rough = np.clip(0.72 - foot_mud * 0.14 - trickle * 0.34 + (ln_fine - 0.5) * 0.08, 0.30, 0.88)
leg_rm_rgba = np.stack([np.ones_like(leg_rough), leg_rough, np.zeros_like(leg_rough), np.ones_like(leg_rough)], axis=-1)
leg_base_nm = height_to_normal(ln_fine * 0.45 + trickle * 0.50, strength=1.2)
leg_nm_rgba = PS.blend_tangent_normals(leg_base_nm, leg_skin_pore_n, np.full((HL, WL), 0.85, dtype=np.float32))
leg_nm_rgba = PS.blend_tangent_normals(leg_nm_rgba, leg_mud_n, foot_mud * 0.88)

leg_rm_256 = _half(_half(leg_rm_rgba))
leg_nm_256 = _half(_half(leg_nm_rgba))
lnv = leg_nm_256[..., :3] * 2.0 - 1.0
lnv /= np.sqrt(np.sum(lnv * lnv, axis=-1, keepdims=True) + 1e-8)
leg_nm_256 = np.concatenate([lnv * 0.5 + 0.5, np.ones((leg_nm_256.shape[0], leg_nm_256.shape[1], 1), dtype=np.float32)], axis=-1)

leg_bc_img = make_img("T_preay_legs_BC", leg_bc_rgba, "sRGB")
leg_rm_img = make_img("T_preay_legs_ORM", leg_rm_256, "Non-Color")
leg_nm_img = make_img("T_preay_legs_N", leg_nm_256, "Non-Color")

leg_mat = bpy.data.materials.new("M_preay_legs")
leg_mat.use_nodes = True
lnodes = leg_mat.node_tree.nodes
llinks = leg_mat.node_tree.links
lbsdf = next(n for n in lnodes if n.type == "BSDF_PRINCIPLED")
lbsdf.inputs["Metallic"].default_value = 0.0
lbsdf.inputs["Specular IOR Level"].default_value = 0.28

lt_bc = lnodes.new("ShaderNodeTexImage")
lt_bc.image = leg_bc_img
llinks.new(lt_bc.outputs["Color"], lbsdf.inputs["Base Color"])

lt_rm = lnodes.new("ShaderNodeTexImage")
lt_rm.image = leg_rm_img
lsep = lnodes.new("ShaderNodeSeparateColor")
llinks.new(lt_rm.outputs["Color"], lsep.inputs["Color"])
llinks.new(lsep.outputs["Green"], lbsdf.inputs["Roughness"])
llinks.new(lsep.outputs["Blue"], lbsdf.inputs["Metallic"])

lt_nm = lnodes.new("ShaderNodeTexImage")
lt_nm.image = leg_nm_img
lnmap = lnodes.new("ShaderNodeNormalMap")
lnmap.inputs["Strength"].default_value = 0.95
llinks.new(lt_nm.outputs["Color"], lnmap.inputs["Color"])
llinks.new(lnmap.outputs["Normal"], lbsdf.inputs["Normal"])
legs_obj.data.materials.append(leg_mat)

# ------------------------------------------------------------------ 6. Polish `stand` & `hurry` arm clips for realism!
# Keeps `walk`, `reach`, and ALL leg/root keyframes & clip lengths 100% untouched!
def world_delta_to_bone_local(bone, axis_world, angle_rad):
    """Converts a small world-space rotation around `axis_world` into `bone`'s local pose space."""
    inv = bone.matrix_local.to_3x3().inverted()
    local_axis = (inv @ Vector(axis_world)).normalized()
    return Quaternion(local_axis, angle_rad)


def rewrite_arm_fcurves(action, bone_fn):
    """Replaces rotation_quaternion keyframes for arm bones across `action`'s exact frame span
    using Blender 5.x-native `keyframe_insert` (compatible with Slotted Actions)."""
    f0, f1 = int(round(action.frame_range[0])), int(round(action.frame_range[1]))
    span = max(1, f1 - f0)
    target_bones = (
        "clavicle.L", "upperarm01.L", "lowerarm01.L", "wrist.L",
        "clavicle.R", "upperarm01.R", "lowerarm01.R", "wrist.R",
    )
    rig.animation_data_create()
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    # Remove old arm fcurves cleanly in Blender 5.x channelbags (if present)
    fcurves = getattr(action, "fcurves", None)
    if fcurves is None and action.layers and action.layers[0].strips:
        strip = action.layers[0].strips[0]
        if hasattr(strip, "channelbag") and action.slots:
            cb = strip.channelbag(action.slots[0])
            if cb:
                fcurves = cb.fcurves
    if fcurves is not None:
        for bname in target_bones:
            dp = f'pose.bones["{bname}"].rotation_quaternion'
            for fc in [c for c in fcurves if c.data_path == dp]:
                fcurves.remove(fc)

    for bname in target_bones:
        b = rig.data.bones[bname]
        pb = rig.pose.bones[bname]
        pb.rotation_mode = "QUATERNION"
        prev_q = None
        for f in range(f0, f1 + 1):
            phase = 2.0 * math.pi * ((f - f0) / span)
            q = bone_fn(b, bname, phase)
            if prev_q is not None and prev_q.dot(q) < 0.0:
                q = -q
            prev_q = q
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)


# A. `stand`: Replace frozen wide A-pose arms with natural relaxed asymmetric drape + ragged breathing drift!
stand_act = bpy.data.actions.get("stand")
if stand_act:
    def stand_arm_pose(b, bname, ph):
        breath = 0.5 - 0.5 * math.cos(ph)          # smooth 0..1 loopable breath
        sway = math.sin(ph + 0.65)                 # phase-lagged secondary sway
        lag = math.sin(ph - 0.55)
        q = Quaternion((1, 0, 0, 0))
        if bname == "clavicle.L":
            q = world_delta_to_bone_local(b, (0, 1, 0), math.radians(-2.8 + 1.8 * breath))
        elif bname == "clavicle.R":
            q = world_delta_to_bone_local(b, (0, 1, 0), math.radians(1.6 - 1.5 * breath))
        elif bname == "upperarm01.L":
            # Bring arm naturally inward close to ribs/hip + subtle forward drape
            q_in = world_delta_to_bone_local(b, (0, 1, 0), math.radians(8.5 - 1.2 * breath))
            q_fw = world_delta_to_bone_local(b, (1, 0, 0), math.radians(-4.5 + 1.6 * sway))
            q = q_fw @ q_in
        elif bname == "upperarm01.R":
            # Asymmetric: right arm drapes slightly closer & subtly further back
            q_in = world_delta_to_bone_local(b, (0, 1, 0), math.radians(-10.0 + 1.1 * breath))
            q_fw = world_delta_to_bone_local(b, (1, 0, 0), math.radians(-7.5 - 1.4 * sway))
            q = q_fw @ q_in
        elif bname == "lowerarm01.L":
            # Soft natural relaxed elbow bend (~14 deg forward) instead of straight rod!
            q_el = world_delta_to_bone_local(b, (1, 0, 0), math.radians(-14.5 - 2.2 * lag))
            q_in = world_delta_to_bone_local(b, (0, 1, 0), math.radians(3.5))
            q = q_in @ q_el
        elif bname == "lowerarm01.R":
            # Slightly deeper eerie bend on right elbow (~20 deg) so gaunt hand hovers softly
            q_el = world_delta_to_bone_local(b, (1, 0, 0), math.radians(-20.5 + 2.4 * lag))
            q_in = world_delta_to_bone_local(b, (0, 1, 0), math.radians(-5.0))
            q = q_in @ q_el
        elif bname == "wrist.L":
            # Limp lifeless wrist hang with slow trailing drift
            q_w = world_delta_to_bone_local(b, (1, 0, 0), math.radians(10.0 + 3.0 * math.sin(ph - 1.1)))
            q_s = world_delta_to_bone_local(b, (0, 1, 0), math.radians(5.5))
            q = q_s @ q_w
        elif bname == "wrist.R":
            q_w = world_delta_to_bone_local(b, (1, 0, 0), math.radians(13.5 - 3.2 * math.sin(ph - 0.9)))
            q_s = world_delta_to_bone_local(b, (0, 1, 0), math.radians(-6.5))
            q = q_s @ q_w
        return q.normalized()

    rewrite_arm_fcurves(stand_act, stand_arm_pose)

# B. `hurry`: Replace wild overhead flailing (z=1.75m!) with terrifying predatory forward lurching swing!
hurry_act = bpy.data.actions.get("hurry")
if hurry_act:
    def hurry_arm_pose(b, bname, ph):
        # Double-step stride swing synchronized cleanly with hurry's 2-step cycle
        swing = math.sin(ph * 2.0)
        lag = math.sin(ph * 2.0 - 0.55)
        q = Quaternion((1, 0, 0, 0))
        if bname == "clavicle.L":
            q = world_delta_to_bone_local(b, (0, 1, 0), math.radians(-3.0 + 2.5 * swing))
        elif bname == "clavicle.R":
            q = world_delta_to_bone_local(b, (0, 1, 0), math.radians(3.0 + 2.5 * swing))
        elif bname == "upperarm01.L":
            q_in = world_delta_to_bone_local(b, (0, 1, 0), math.radians(7.0))
            q_fw = world_delta_to_bone_local(b, (1, 0, 0), math.radians(-16.0 - 15.0 * swing))
            q = q_fw @ q_in
        elif bname == "upperarm01.R":
            q_in = world_delta_to_bone_local(b, (0, 1, 0), math.radians(-7.0))
            q_fw = world_delta_to_bone_local(b, (1, 0, 0), math.radians(-18.0 + 15.0 * swing))
            q = q_fw @ q_in
        elif bname == "lowerarm01.L":
            q_el = world_delta_to_bone_local(b, (1, 0, 0), math.radians(-34.0 - 10.0 * lag))
            q_in = world_delta_to_bone_local(b, (0, 1, 0), math.radians(5.0))
            q = q_in @ q_el
        elif bname == "lowerarm01.R":
            q_el = world_delta_to_bone_local(b, (1, 0, 0), math.radians(-38.0 + 10.0 * lag))
            q_in = world_delta_to_bone_local(b, (0, 1, 0), math.radians(-5.0))
            q = q_in @ q_el
        elif bname == "wrist.L":
            q = world_delta_to_bone_local(b, (1, 0, 0), math.radians(16.0 + 6.0 * lag))
        elif bname == "wrist.R":
            q = world_delta_to_bone_local(b, (1, 0, 0), math.radians(18.0 - 6.0 * lag))
        return q.normalized()

    rewrite_arm_fcurves(hurry_act, hurry_arm_pose)

# Reset to clean rest pose before saving & exporting
if rig.animation_data:
    rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.location = (0, 0, 0)
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.scale = (1, 1, 1)
bpy.context.scene.frame_set(1)

# Purge unused temporary images before saving & exporting
keep_imgs = {img_bc, img_rm, img_nm, leg_bc_img, leg_rm_img, leg_nm_img, *hair_imgs}
for img in list(bpy.data.images):
    if img not in keep_imgs:
        bpy.data.images.remove(img)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
body.select_set(True)
legs_obj.select_set(True)
hair_obj.select_set(True)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(OUT),
    export_format="GLB",
    use_selection=True,
    export_yup=True,
    export_apply=False,
    export_skins=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_force_sampling=True,
    export_morph=False,
    export_extras=False,
    export_cameras=False,
    export_lights=False,
    export_image_format="AUTO",
)

b_tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
l_tris = sum(len(p.vertices) - 2 for p in legs_obj.data.polygons)
h_tris = sum(len(p.vertices) - 2 for p in hair_obj.data.polygons)
all_z = [v.co.z for o in (body, legs_obj, hair_obj) for v in o.data.vertices]
print(
    f"[preay_photoreal] body={b_tris:,} + legs={l_tris:,} + hair_cards={h_tris:,} tris, "
    f"height={min(all_z):.3f}..{max(all_z):.3f}m, "
    f"mean_rgb={[round(float(graded[..., c].mean()), 3) for c in range(3)]} -> {OUT}",
    flush=True,
)
