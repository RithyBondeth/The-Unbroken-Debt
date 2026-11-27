"""Prepares a photorealistic, full-body Khmer Headless Ghost with BOTH anatomical bare legs
for Episode 1 Village, combining the user-supplied sculpted upper scan (`khmer-headless-ghost.glb`)
with real MakeHuman Southeast Asian female lower legs & bare feet (`makehuman-sora`), plus
monsoon-weathered PBR albedo, roughness, micro-detail normal, and cavity AO grading so she blends
naturally into the rain-soaked 1932 Cambodian village instead of looking bright or cartoonish.

Usage:
    blender -b --factory-startup --python-exit-code 1 -P tools/characters/import-headless-ghost.py -- \
        /Users/bondeth/Downloads/models/khmer-headless-ghost.glb
    npm run assets -- ep1/headless_ghost
"""
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hair_cards as HC  # noqa: E402
import photoreal_surfaces as PS  # noqa: E402
SRC = Path(os.path.expanduser(sys.argv[sys.argv.index("--") + 1]))
MH_DIR = ROOT / "art-source/library/makehuman-sora"
OUT = ROOT / "art-export/ep1/headless_ghost.glb"
OUT.parent.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------ deterministic 2D fBM noise
def _hash2(ix, iy, seed):
    ux = ix.astype(np.uint64)
    uy = iy.astype(np.uint64)
    n = (ux * np.uint64(374761393) + uy * np.uint64(668265263) + np.uint64(seed * 1442695041)) & np.uint64(0xFFFFFFFF)
    n = ((n ^ (n >> np.uint64(13))) * np.uint64(1274126177)) & np.uint64(0xFFFFFFFF)
    return (((n ^ (n >> np.uint64(16))) & np.uint64(0xFFFFFF)).astype(np.float32)) / float(0x1000000)


def fbm_grid(h, w, freqs=(6, 14, 34, 82), seed=17):
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
        s = seed + idx * 97
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


def height_to_normal(height_map, strength=1.8):
    gx = (np.roll(height_map, -1, axis=1) - np.roll(height_map, 1, axis=1)) * 0.5 * strength
    gy = (np.roll(height_map, -1, axis=0) - np.roll(height_map, 1, axis=0)) * 0.5 * strength
    nx = -gx
    ny = -gy
    nz = np.ones_like(nx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    n = np.stack([nx * inv * 0.5 + 0.5, ny * inv * 0.5 + 0.5, nz * inv * 0.5 + 0.5, np.ones_like(nx)], axis=-1)
    return np.clip(n, 0.0, 1.0).astype(np.float32)


def img_to_np(img):
    w, h = img.size
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    return arr.reshape(h, w, 4)


def np_to_img(name, arr, colorspace="sRGB"):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, width=w, height=h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.clip(arr, 0.0, 1.0).astype(np.float32).ravel())
    img.pack()
    return img


def bake_vertex_xyz_and_ao_to_uv(obj, h, w):
    """Splats 3D vertex `(x, y, z)` and neighborhood cavity AO into UV space for real photographed
    linen, mud, and skin-pore 3D projection + anatomical face/neck/hem masking."""
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
        ao_v[i] = float(np.clip(1.0 - max(0.0, concavity) * 28.0, 0.35, 1.0))
    bm.free()

    uv_layer = obj.data.uv_layers.active
    if not uv_layer:
        xyz_d = np.zeros((h, w, 3), dtype=np.float32)
        xyz_d[..., 2] = 1.0
        return xyz_d, np.full((h, w), 1.0, dtype=np.float32)

    xyz_sum = np.zeros((h, w, 3), dtype=np.float32)
    ao_sum = np.zeros((h, w), dtype=np.float32)
    cnt = np.zeros((h, w), dtype=np.float32)
    uv_data = uv_layer.data
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
    xyz_map[..., 2] = np.where(mask > 0.1, xyz_map[..., 2], 1.0)
    ao_map = np.where(mask > 0.1, ao_map, 0.92)
    return xyz_map, ao_map


# ------------------------------------------------------------------ 1. Load & prepare sculpted torso
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    raise RuntimeError("No meshes found in headless ghost GLB")

bpy.context.view_layer.update()
for o in meshes:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
if len(meshes) > 1:
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()

torso = bpy.context.view_layer.objects.active
torso.name = torso.data.name = "headless_ghost_torso"

# Place torso at true anatomical height of a 1.62m Cambodian woman (headless neck top = 1.44m,
# mid-thigh sampot hem = 0.50m, torso span = 0.94m) centered over pelvis/hips!
co_raw = np.array([v.co[:] for v in torso.data.vertices], dtype=np.float32)
mn, mx = co_raw.min(0), co_raw.max(0)
raw_h = max(0.01, float(mx[2] - mn[2]))
# Bottom sampot slice gives true hip/thigh center (cx, cy) so legs emerge dead-center under sampot!
bot_band = co_raw[co_raw[:, 2] < mn[2] + raw_h * 0.08]
hip_cx = float((bot_band[:, 0].min() + bot_band[:, 0].max()) * 0.5)
hip_cy = float((bot_band[:, 1].min() + bot_band[:, 1].max()) * 0.5)

torso_scale = 0.94 / raw_h
TORSO_BOTTOM_Z = 0.50  # mid-thigh sampot hem; real MakeHuman knees sit at ~0.44m, feet at 0.00m!
shift = Matrix.Translation((-hip_cx, -hip_cy, -mn[2]))
lift = Matrix.Translation((0.0, 0.0, TORSO_BOTTOM_Z))
torso.data.transform(lift @ Matrix.Scale(torso_scale, 4) @ shift)

# Soften the bottom sampot hem smoothly so cloth falls organically over the knees
bm = bmesh.new()
bm.from_mesh(torso.data)
bm.verts.ensure_lookup_table()
for v in bm.verts:
    if v.co.z < TORSO_BOTTOM_Z + 0.06:
        t = (TORSO_BOTTOM_Z + 0.06 - v.co.z) / 0.06
        ang = math.atan2(v.co.y, v.co.x)
        hem_drop = (0.042 + 0.014 * math.sin(ang * 5.0 + 0.4) + 0.008 * math.cos(ang * 9.0)) * (t ** 1.4)
        v.co.z -= hem_drop
        taper = 1.0 - 0.055 * (t ** 1.6)
        v.co.x *= taper
        v.co.y *= taper
bm.to_mesh(torso.data)
bm.free()

# High-detail decimation: preserve 86,000 tris for razor-crisp sculpted fingers, face, teeth & folds
tri_count = sum(len(p.vertices) - 2 for p in torso.data.polygons)
target_tris = 86000
if tri_count > target_tris:
    mod = torso.modifiers.new(name="Decimate", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = max(0.015, min(1.0, target_tris / tri_count))
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = torso
    bpy.ops.object.modifier_apply(modifier=mod.name)

# ------------------------------------------------------------------ 2. Non-destructive photographic grading of 4K torso maps
torso_mat = torso.data.materials[0]
torso_mat.name = "M_headless_ghost_torso"
torso_mat.use_backface_culling = False  # Prevent backface holes along thin sampot hem edges!
nodes = torso_mat.node_tree.nodes
links = torso_mat.node_tree.links
bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")

bc_img = next((i for i in bpy.data.images if "basecolor" in i.name.lower() or "albedo" in i.name.lower()), bpy.data.images[0])
nm_img = next((i for i in bpy.data.images if "normal" in i.name.lower()), None)
rm_orig_img = next((i for i in bpy.data.images if "_rm" in i.name.lower() or "rough" in i.name.lower()), None)

for img in [i for i in (bc_img, nm_img, rm_orig_img) if i is not None]:
    w, h = img.size
    if max(w, h) > 2048:
        s = 2048 / max(w, h)
        img.scale(int(w * s), int(h * s))

bc_raw = img_to_np(bc_img)
H, W = bc_raw.shape[:2]
rgb = bc_raw[..., :3].copy()

# ------------------------------------------------------------------ 2a. Surgically recess ALL 3 sculpted cartoon clay hair chunks
# (1) Bulky forehead clay visor (z=1.053..1.165), (2) two angular clay side-slabs beside her jaw
# (z=0.85..1.06, |x|>0.062), and (3) curved cartoon clay claw right of her gripping fist (z>1.14, x>0.015)
# — strictly classified by original dark non-red hair albedo + 3D bounds so her pale face, eyes,
# mouth/teeth, gripping fingers, and white chest wrap remain 100.00% untouched!
uv_layer_recess = torso.data.uv_layers.active.data
n_v_t = len(torso.data.vertices)
v_rgb_orig = np.zeros((n_v_t, 3), dtype=np.float32)
v_cnt_orig = np.zeros(n_v_t, dtype=np.float32)
for loop in torso.data.loops:
    u, v_uv = uv_layer_recess[loop.index].uv
    px = int(np.clip((u % 1.0) * (W - 1), 0, W - 1))
    py = int(np.clip((v_uv % 1.0) * (H - 1), 0, H - 1))
    v_rgb_orig[loop.vertex_index] += rgb[py, px]
    v_cnt_orig[loop.vertex_index] += 1.0
v_rgb_orig /= np.maximum(v_cnt_orig[:, None], 1.0)
v_lum_orig = 0.2126 * v_rgb_orig[:, 0] + 0.7152 * v_rgb_orig[:, 1] + 0.0722 * v_rgb_orig[:, 2]
v_red_ex = v_rgb_orig[:, 0] - np.maximum(v_rgb_orig[:, 1], v_rgb_orig[:, 2])


def _sstep(a, b, x):
    if abs(b - a) < 1e-6:
        return 1.0 if x >= a else 0.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


bm_hair = bmesh.new()
bm_hair.from_mesh(torso.data)
bm_hair.verts.ensure_lookup_table()
hair_move_w = np.zeros(len(bm_hair.verts), dtype=np.float32)

for v in bm_hair.verts:
    x, y, z = v.co.x, v.co.y, v.co.z
    if y > -0.165 or z < 0.84 or z > 1.30 or abs(x) > 0.165:
        continue
    # Raw Tripo black clay hair has lum ~0.01-0.08 & red_excess ~0.004 (while skin has red ~0.17 & white cloth has lum >0.28!)
    is_dark_hair = _sstep(0.165, 0.085, float(v_lum_orig[v.index])) * _sstep(0.055, 0.022, float(v_red_ex[v.index]))
    # Front-protruding claw right of fist (y < -0.215, x > 0.015, z > 1.16) can have slight grey UV bleed up to lum 0.28
    is_front_claw = (
        _sstep(0.28, 0.16, float(v_lum_orig[v.index]))
        * _sstep(0.055, 0.022, float(v_red_ex[v.index]))
        * _sstep(-0.205, -0.225, y)
        * _sstep(0.014, 0.026, x)
        * _sstep(1.150, 1.175, z)
    )
    is_dark_hair = max(is_dark_hair, is_front_claw)
    if is_dark_hair < 0.02:
        continue
    # Protect 100% of the face opening (eyes, brows, nose, cheeks, lips, teeth, chin)
    face_protect = (
        _sstep(0.066, 0.052, abs(x))
        * _sstep(1.054, 1.044, z)
        * _sstep(0.845, 0.865, z)
        * _sstep(-0.265, -0.295, y)
    )
    # UNCONDITIONAL 3D-box protection for her entire gripping right fist, knuckles & wrist (x < +0.026, z > 1.150)
    # so zero sculpted fingers or knuckles can EVER be deformed!
    fist_protect = (
        _sstep(0.028, 0.014, x)
        * _sstep(1.148, 1.164, z)
        * _sstep(1.268, 1.250, z)
    )
    w_base = is_dark_hair * (1.0 - face_protect) * (1.0 - fist_protect)
    if w_base < 0.02:
        continue

    moved = 0.0
    # (1) Bulky forehead clay visor/dome (z = 1.052..1.165): pull smoothly inward into a sleek inner scalp core!
    w_visor = w_base * _sstep(1.048, 1.062, z) * _sstep(1.175, 1.152, z)
    if w_visor > 0.01:
        core = Vector((0.0, -0.252, min(z, 1.095)))
        delta = v.co - core
        v.co.x -= delta.x * 0.34 * w_visor
        v.co.y -= delta.y * 0.44 * w_visor
        if v.co.y < -0.308:
            v.co.y = v.co.y * (1.0 - 0.78 * w_visor) + (-0.308) * (0.78 * w_visor)
        moved = max(moved, w_visor)

    # (2) Both chunky angular clay side-flaps beside her cheeks & chin (z = 0.84..1.062):
    # Collapse & tuck them deeply behind the cheekbones/cranium core so ZERO clay triangles hang beside her jaw!
    x_thr_lo = 0.042 if z < 0.94 else 0.052
    x_thr_hi = 0.056 if z < 0.94 else 0.068
    w_flap = w_base * _sstep(x_thr_lo, x_thr_hi, abs(x)) * _sstep(1.070, 1.046, z)
    if w_flap > 0.01:
        core_f = Vector((math.copysign(0.032, x), -0.228, max(z, 1.010)))
        v.co = v.co.lerp(core_f, 0.88 * w_flap)
        moved = max(moved, w_flap)

    # (3) Cartoon clay claw/hook sticking out to the right of & above her clenched fist (x > +0.018, z > 1.142):
    # Collapse 95% inward into the tight hair stalk hidden right beside her fist grip — completely clear of
    # her fingers (x < 0.020) and completely clear of the white chest wrap (lum > 0.28)!
    w_claw_right = w_base * _sstep(1.135, 1.158, z) * _sstep(0.012, 0.026, x)
    w_claw_top = w_base * _sstep(1.228, 1.248, z)
    w_claw = max(w_claw_right, w_claw_top)
    if w_claw > 0.01:
        stalk = Vector((-0.010, -0.248, min(z, 1.184)))
        v.co = v.co.lerp(stalk, 0.95 * w_claw)
        moved = max(moved, w_claw)

    hair_move_w[v.index] = moved

# Weighted Laplacian smoothing ONLY on recessed sculpted hair vertices so transitions stay silky
for _ in range(7):
    new_pos = {}
    for v in bm_hair.verts:
        mw = float(hair_move_w[v.index])
        if mw < 0.05 or not v.link_edges:
            continue
        nbrs = [e.other_vert(v).co for e in v.link_edges]
        avg = sum(nbrs, Vector((0, 0, 0))) / len(nbrs)
        new_pos[v.index] = v.co.lerp(avg, 0.45 * mw)
    for idx, pos in new_pos.items():
        bm_hair.verts[idx].co = pos

bm_hair.normal_update()
bm_hair.to_mesh(torso.data)
bm_hair.free()
print(f"[headless_ghost] recessed sculpted cartoon clay hair chunks: {(hair_move_w > 0.05).sum():,} verts", flush=True)

# Compute 3D vertex `(x, y, z)` & cavity AO in UV space + load REAL photographed village CC0 textures!
xyz_uv, ao_uv = bake_vertex_xyz_and_ao_to_uv(torso, H, W)
x_uv, y_uv, z_uv = xyz_uv[..., 0], xyz_uv[..., 1], xyz_uv[..., 2]
noise_big = fbm_grid(H, W, freqs=(5, 13, 29, 64), seed=41)
noise_fine = fbm_grid(H, W, freqs=(24, 64, 148), seed=93)

photo = PS.load_village_photoreal_pack()
linen_bc = PS.sample_cylindrical(photo["linen_bc"], xyz_uv, tile_m=0.14)[..., :3]
linen_n = PS.sample_cylindrical(photo["linen_n"], xyz_uv, tile_m=0.14)
linen_orm = PS.sample_cylindrical(photo["linen_orm"], xyz_uv, tile_m=0.14)
mud_bc = PS.sample_cylindrical(photo["mud_bc"], xyz_uv, tile_m=0.20)[..., :3] * 0.58 + PS.sample_cylindrical(photo["laterite_bc"], xyz_uv, tile_m=0.18)[..., :3] * 0.42
mud_n = PS.sample_cylindrical(photo["mud_n"], xyz_uv, tile_m=0.20)
skin_pore_n = PS.sample_cylindrical(photo["skin_n"], xyz_uv, tile_m=0.12)

linen_lum = 0.2126 * linen_bc[..., 0] + 0.7152 * linen_bc[..., 1] + 0.0722 * linen_bc[..., 2]
linen_detail = np.clip(linen_bc / np.maximum(linen_lum.mean(), 0.1), 0.65, 1.32)

# Smooth, non-destructive photographic film LUT directly over the original 4K Tripo albedo!
# Preserves 100% of the sculpted face features, eyes, teeth, skin bruises & cloth folds with ZERO
# hard mask edges or blocky synthetic patches!
lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
mx_c = np.max(rgb, axis=-1)
mn_c = np.min(rgb, axis=-1)
sat = (mx_c - mn_c) / np.maximum(mx_c, 1e-4)

# Soft continuous material weights ONLY for subtle photographed linen/skin/mud micro-detail blending
red_excess = rgb[..., 0] - np.maximum(rgb[..., 1], rgb[..., 2])
red_ratio = rgb[..., 0] / np.maximum(rgb[..., 1] + 0.04, 0.04)
blood_w = np.clip((red_excess - 0.15) * 4.5, 0.0, 1.0) * np.clip((red_ratio - 1.65) * 2.2, 0.0, 1.0)
cloth_w = np.clip((lum - 0.36) * 3.0, 0.0, 1.0) * np.clip((0.26 - sat) * 4.5, 0.0, 1.0) * (1.0 - blood_w)
hair_w = np.clip((0.14 - lum) * 7.5, 0.0, 1.0) * (1.0 - blood_w)
skin_w = np.clip(1.0 - cloth_w - hair_w - blood_w, 0.0, 1.0)

# Step 1: Natural monsoon horror film grade preserving ALL 4K sculpted facial & anatomical contours!
desat_rgb = lum[..., None] * 0.48 + rgb * 0.52
venous_scale = np.stack(
    [
        1.0 - 0.34 * blood_w,
        1.0 - 0.46 * blood_w,
        1.0 - 0.46 * blood_w,
    ],
    axis=-1,
)
graded = desat_rgb * venous_scale * np.array([0.88, 0.85, 0.79], dtype=np.float32)

# Step 1b: Smooth Gaussian severed-face readability pass!
# The original scan paints the entire severed face dark muddy red-brown, which sinks into pitch black at
# 4m distance in night rain. Locate ONLY the front-protruding face (y < -0.29, z in 0.87..1.08) and
# smoothly shift its red wash into haunting, pale drowned-corpse grey-ivory (sRGB ~0.46-0.60) while
# keeping sunken dark eye sockets, pale staring eyeballs, dark nostrils, and coagulated dark blood
# specifically along the parted mouth/chin/jaw — ZERO hard seams or blotches!
sev_pts = np.array(
    [v.co[:] for v in torso.data.vertices if v.co.y < -0.29 and 0.87 < v.co.z < 1.08 and abs(v.co.x) < 0.115],
    dtype=np.float32,
)
if len(sev_pts) > 20:
    fcx = float(np.median(sev_pts[:, 0]))
    fcy = float(np.percentile(sev_pts[:, 1], 30))
    fcz = float(np.median(sev_pts[:, 2]))
else:
    fcx, fcy, fcz = 0.00, -0.355, 0.975
print(f"[headless_ghost] severed face center=({fcx:.3f}, {fcy:.3f}, {fcz:.3f}) n={len(sev_pts)}", flush=True)

face_d2 = ((x_uv - fcx) / 0.092) ** 2 + ((y_uv - fcy) / 0.098) ** 2 + ((z_uv - fcz) / 0.114) ** 2
face_gauss = np.exp(-0.5 * face_d2) * (1.0 - hair_w)
# Smooth waxen drowned-corpse ivory across forehead, brow, cheeks, and nose bridge — eliminating
# Tripo's blotchy dark red forehead wash while keeping sunken dark eye sockets, pale staring eyes,
# dark nostrils, and coagulated venous blood strictly around the parted mouth/chin/jaw!
face_lit = np.clip((lum - 0.045) / 0.30, 0.0, 1.0) ** 0.56
# Smooth local contrast on upper face (forehead/cheeks) so pale skin reads continuous & realistic, not patchy
upper_face = np.clip((z_uv - (fcz - 0.015)) / 0.055, 0.0, 1.0)
face_lit_smooth = face_lit * (1.0 - 0.28 * upper_face) + np.clip(face_lit * 0.68 + 0.24, 0.0, 1.0) * (0.28 * upper_face)
# Keep deepest crevices (dark eye sockets, nostrils, mouth interior) deeply recessed!
crevice_keep = np.clip((lum - 0.035) / 0.085, 0.0, 1.0)
face_tone = face_lit_smooth * crevice_keep
pale_corpse_face = np.stack(
    [
        np.clip(0.055 + 0.50 * face_tone, 0.035, 0.58),
        np.clip(0.050 + 0.46 * face_tone, 0.032, 0.54),
        np.clip(0.048 + 0.42 * face_tone, 0.030, 0.50),
    ],
    axis=-1,
) * (0.91 + 0.14 * noise_big[..., None])
# Preserve dark coagulated blood specifically along lower mouth/chin/jaw drip (ZERO blotches on forehead!)
mouth_blood = np.clip((fcz - 0.028 - z_uv) / 0.062, 0.0, 1.0) * blood_w * 0.82
face_blend = face_gauss * (1.0 - mouth_blood) * 0.90
graded = graded * (1.0 - face_blend[..., None]) + pale_corpse_face * face_blend[..., None]

# Suppress stray light blotches on the sculpted hair dome above her forehead (z=1.07..1.21) so the
# dark wet scalp under the layered hair cards stays clean charcoal-black (strictly avoiding her fist!)
dome_zone = (
    np.clip((-0.20 - y_uv) / 0.05, 0.0, 1.0)
    * np.clip((z_uv - 1.072) / 0.025, 0.0, 1.0)
    * np.clip((1.21 - z_uv) / 0.03, 0.0, 1.0)
    * np.clip((0.125 - np.abs(x_uv - fcx)) / 0.03, 0.0, 1.0)
    * (1.0 - np.clip((-0.025 - x_uv) / 0.04, 0.0, 1.0) * np.clip((z_uv - 1.155) / 0.03, 0.0, 1.0))
    * (1.0 - cloth_w)
)
dome_blotch = dome_zone * np.clip((lum - 0.08) * 4.0, 0.0, 1.0) * (1.0 - face_gauss)
wet_scalp = np.array([0.045, 0.040, 0.038], dtype=np.float32) * (0.82 + 0.36 * noise_fine[..., None])
graded = graded * (1.0 - dome_blotch[..., None] * 0.85) + wet_scalp * (dome_blotch[..., None] * 0.85)

# Step 1c: Gently lift overly dark hollow waist/ribcage shadows so her torso & left arm read as
# one solid continuous human body in dark moonlight (never looking detached at the waist!)
torso_skin_lift = skin_w * np.clip((z_uv - 0.74) / 0.14, 0.0, 1.0) * np.clip((y_uv + 0.20) / 0.06, 0.0, 1.0)
graded_lum = 0.2126 * graded[..., 0] + 0.7152 * graded[..., 1] + 0.0722 * graded[..., 2]
dark_skin_boost = torso_skin_lift * np.clip((0.26 - graded_lum) / 0.26, 0.0, 1.0)
graded = graded + dark_skin_boost[..., None] * np.array([0.135, 0.105, 0.086], dtype=np.float32)

# Step 2: Weather bright white sampot/sbai into damp 1932 handloomed raw linen (subtle photographed weave!)
cloth_mod = (0.80 + 0.20 * linen_detail) * (0.90 + 0.14 * noise_big[..., None]) * np.array([0.97, 0.95, 0.89], dtype=np.float32)
graded = graded * (1.0 - cloth_w[..., None]) + (graded * cloth_mod) * cloth_w[..., None]

# Step 3: Subtle photographed Cambodian village mud climbing the bottom 20cm of the sampot hem
hem_mud = np.clip((0.68 - z_uv) / 0.22, 0.0, 1.0) ** 1.55
hem_mud = np.clip(hem_mud * (0.45 + 0.55 * noise_big), 0.0, 0.68) * (1.0 - hair_w)
mud_col = np.clip(mud_bc * 0.52, 0.04, 0.22)
graded = graded * (1.0 - hem_mud[..., None]) + mud_col * hem_mud[..., None]

# Step 4: Gentle baked cavity AO for realistic depth inside folds & joints
graded *= (0.78 + 0.22 * ao_uv[..., None])
graded_rgba = np.concatenate([np.clip(graded, 0.0, 1.0), np.ones((H, W, 1), dtype=np.float32)], axis=-1)

# Measure the EXACT final sRGB mean of her exposed upper-body/arm skin so grafted legs match 1:1!
sev_head_box = (y_uv < -0.11) & (z_uv > 0.82) & (z_uv < 1.22) & (np.abs(x_uv) < 0.16)
arm_skin_mask = (skin_w > 0.60) & (z_uv > 0.82) & (z_uv < 1.38) & (~sev_head_box)
if np.any(arm_skin_mask):
    torso_skin_mean = graded[arm_skin_mask].mean(axis=0).astype(np.float32)
else:
    torso_skin_mean = np.array([0.30, 0.23, 0.19], dtype=np.float32)
print(f"[headless_ghost] measured torso arm skin mean sRGB={[round(float(c), 3) for c in torso_skin_mean]}", flush=True)

# Preserve original 4K roughness detail, calibrated cleanly for wet matte monsoon lighting (zero plastic glare!)
if rm_orig_img is not None:
    orig_r = img_to_np(rm_orig_img)[..., 1]
    rough = np.clip(orig_r * 0.55 + 0.40, 0.42, 0.94)
else:
    rough = 0.72 * skin_w + 0.90 * cloth_w + 0.44 * blood_w + 0.68 * hair_w
rough = np.clip(
    rough * (1.0 - cloth_w) + np.clip(0.76 + 0.22 * linen_orm[..., 1], 0.76, 0.95) * cloth_w - blood_w * 0.22 - hem_mud * 0.08,
    0.38,
    0.96,
)
rm_rgba = np.stack([np.ones_like(rough), rough, np.zeros_like(rough), np.ones_like(rough)], axis=-1)

# Preserve original 4K sculpted normal map at full fidelity + subtle photographed linen/skin/mud micro-detail
# + fine combed hair-fiber ridges on any recessed inner scalp core so zero smooth plastic ever shows!
if nm_img is not None:
    base_n = img_to_np(nm_img)
else:
    base_n = height_to_normal(lum * 0.5 + noise_fine * 0.3, strength=1.0)
scalp_strand_h = np.sin(np.arctan2(x_uv, np.maximum(0.01, -y_uv - 0.25)) * 180.0 + noise_big * 14.0) * 0.5 + 0.5
scalp_strand_n = height_to_normal(scalp_strand_h * 0.7 + noise_fine * 0.3, strength=1.4)
final_n = PS.blend_tangent_normals(base_n, linen_n, cloth_w * 0.42)
final_n = PS.blend_tangent_normals(final_n, skin_pore_n, skin_w * 0.45)
final_n = PS.blend_tangent_normals(final_n, mud_n, hem_mud * 0.65)
final_n = PS.blend_tangent_normals(final_n, scalp_strand_n, hair_w * 0.80)

bc_out = np_to_img("T_headless_torso_BC", graded_rgba, "sRGB")
rm_out = np_to_img("T_headless_torso_ORM", rm_rgba, "Non-Color")
nm_out = np_to_img("T_headless_torso_N", final_n, "Non-Color")

# Rebuild clean glTF-friendly Principled BSDF material for torso
for n in list(nodes):
    if n.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL"):
        nodes.remove(n)
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Specular IOR Level"].default_value = 0.38

tex_bc = nodes.new("ShaderNodeTexImage")
tex_bc.image = bc_out
links.new(tex_bc.outputs["Color"], bsdf.inputs["Base Color"])

tex_rm = nodes.new("ShaderNodeTexImage")
tex_rm.image = rm_out
sep = nodes.new("ShaderNodeSeparateColor")
links.new(tex_rm.outputs["Color"], sep.inputs["Color"])
links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])

tex_nm = nodes.new("ShaderNodeTexImage")
tex_nm.image = nm_out
nmap = nodes.new("ShaderNodeNormalMap")
nmap.inputs["Strength"].default_value = 1.15
links.new(tex_nm.outputs["Color"], nmap.inputs["Color"])
links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

# ------------------------------------------------------------------ 3. Graft BOTH real MakeHuman bare legs & feet!
verts_mh = []
uvs_mh = []
faces_mh = []
face_uvs_mh = []
group = ""
for line in (MH_DIR / "base.obj").read_text().splitlines():
    parts = line.split()
    if not parts:
        continue
    if parts[0] == "v":
        verts_mh.append([float(parts[1]), float(parts[2]), float(parts[3])])
    elif parts[0] == "vt":
        uvs_mh.append((float(parts[1]), float(parts[2])))
    elif parts[0] == "g":
        group = parts[1]
    elif parts[0] == "f" and group == "body":
        toks = [p.split("/") for p in parts[1:]]
        faces_mh.append([int(t[0]) - 1 for t in toks])
        face_uvs_mh.append([int(t[1]) - 1 for t in toks])

# Apply Asian female adult morph targets
for tname in ("asian-female-young.target", "universal-female-young-averagemuscle-averageweight.target"):
    for line in (MH_DIR / tname).read_text().splitlines():
        if line and not line.startswith("#"):
            p = line.split()
            idx = int(p[0])
            verts_mh[idx][0] += float(p[1])
            verts_mh[idx][1] += float(p[2])
            verts_mh[idx][2] += float(p[3])

body_used = sorted({i for f in faces_mh for i in f})
min_y = min(verts_mh[i][1] for i in body_used)
max_y = max(verts_mh[i][1] for i in body_used)
mh_scale = 1.62 / max(0.01, max_y - min_y)

# Convert MakeHuman (Y-up, +Z front) -> Blender (Z-up, -Y front) and bring legs slightly inward
# from MakeHuman's wide A-pose into an authentic haunting standing stance directly beneath her sampot!
def mh_to_bl(v):
    bx = v[0] * mh_scale
    by = -v[2] * mh_scale
    bz = (v[1] - min_y) * mh_scale
    # Pivot each leg inward around its hip socket (x=±0.088, z=0.84) so thighs tuck neatly inside sampot
    if bz < 0.84:
        side = 1.0 if bx >= 0 else -1.0
        hip_x = side * 0.088
        hip_z = 0.84
        dx = bx - hip_x
        dz = bz - hip_z
        # Inward adduction angle (~5.2 degrees)
        ang = -side * math.radians(5.2)
        ca, sa = math.cos(ang), math.sin(ang)
        bx = hip_x + dx * ca - dz * sa
        bz = hip_z + dx * sa + dz * ca
        # Subtle haunting asymmetry: right foot steps 3.5 cm slightly forward
        if side < 0:
            by -= 0.035 * max(0.0, (0.84 - bz) / 0.84)
    return (bx, by, bz)

bl_verts = [mh_to_bl(v) for v in verts_mh]

# Keep only lower-body faces below z = 0.57m (tucked cleanly 7cm inside the z=0.50m sampot hem
# with inward top taper so upper thighs NEVER poke out the sides or back of the narrow skirt!)
LEG_CUT_Z = 0.57
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
# Ground bare soles cleanly at z = 0.000, align Y to torso skirt center, and taper top 6cm inward!
leg_min_z = min(p[2] for p in leg_co)
top_leg_pts = [p for p in leg_co if p[2] > LEG_CUT_Z - 0.05]
leg_cy = (min(p[1] for p in top_leg_pts) + max(p[1] for p in top_leg_pts)) * 0.5
tapered_co = []
for p in leg_co:
    lz = p[2] - leg_min_z
    lx = p[0]
    ly = p[1] - leg_cy + 0.012
    if lz > 0.50:
        tt = min(1.0, (lz - 0.50) / max(LEG_CUT_Z - leg_min_z - 0.50, 0.04))
        shrink = 1.0 - 0.16 * (tt ** 1.4)
        lx *= shrink
        ly *= shrink
    tapered_co.append((lx, ly, lz))
leg_co = tapered_co

leg_mesh = bpy.data.meshes.new("headless_ghost_legs")
leg_mesh.from_pydata(leg_co, [], [[remap[i] for i in f] for f in leg_faces])
uv_l = leg_mesh.uv_layers.new(name="UVMap")
for poly, fu in zip(leg_mesh.polygons, leg_face_uvs):
    poly.use_smooth = True
    for loop_idx, uv_idx in zip(poly.loop_indices, fu):
        uv_l.data[loop_idx].uv = uvs_mh[uv_idx]
leg_mesh.update()

legs = bpy.data.objects.new("headless_ghost_legs", leg_mesh)
bpy.context.scene.collection.objects.link(legs)

# Add one subdivision level for smooth organic knees, calves, ankles, and toes
sub = legs.modifiers.new("Subsurf", "SUBSURF")
sub.levels = 1
sub.render_levels = 1
bpy.context.view_layer.objects.active = legs
bpy.ops.object.modifier_apply(modifier=sub.name)

# Grade MakeHuman skin texture (`young_lightskinned_female_diffuse3.png`) with the EXACT SAME
# drowned-corpse pallor + dark monsoon mud & bruised lividity on shins, ankles, and bare feet!
mh_tex_raw = bpy.data.images.load(str(MH_DIR / "young_lightskinned_female_diffuse3.png"))
w_m, h_m = mh_tex_raw.size
if max(w_m, h_m) > 2048:
    s = 2048 / max(w_m, h_m)
    mh_tex_raw.scale(int(w_m * s), int(h_m * s))
mh_arr = img_to_np(mh_tex_raw)
HL, WL = mh_arr.shape[:2]
l_rgb = mh_arr[..., :3].copy()

l_xyz_uv, ao_leg_uv = bake_vertex_xyz_and_ao_to_uv(legs, HL, WL)
z_leg_uv = l_xyz_uv[..., 2]
ln_big = fbm_grid(HL, WL, freqs=(6, 15, 34, 72), seed=107)
ln_fine = fbm_grid(HL, WL, freqs=(32, 84, 176), seed=211)
leg_mud_bc = np.clip(
    (PS.sample_cylindrical(photo["mud_bc"], l_xyz_uv, tile_m=0.20)[..., :3] * 0.58
     + PS.sample_cylindrical(photo["laterite_bc"], l_xyz_uv, tile_m=0.18)[..., :3] * 0.42) * 0.52,
    0.04, 0.22,
)
leg_mud_n = PS.sample_cylindrical(photo["mud_n"], l_xyz_uv, tile_m=0.20)
leg_skin_pore_n = PS.sample_cylindrical(photo["skin_n"], l_xyz_uv, tile_m=0.12)

l_lum = 0.2126 * l_rgb[..., 0] + 0.7152 * l_rgb[..., 1] + 0.0722 * l_rgb[..., 2]
l_desat = l_lum[..., None] * 0.55 + l_rgb * 0.45

# Normalize MakeHuman shin skin directly onto the EXACT measured sRGB mean of her torso/arms!
shin_ref_mask = (z_leg_uv > 0.18) & (z_leg_uv < 0.46)
ref_mean = l_desat[shin_ref_mask].mean(axis=0) if np.any(shin_ref_mask) else l_desat.mean(axis=0)
scale_to_torso = torso_skin_mean / np.maximum(ref_mean, 1e-4)
leg_skin = np.clip(l_desat * scale_to_torso[None, None, :], 0.05, 0.46)

# Apply the same weathered warm-umber dirt/soot mottling seen on her upper arms & shoulders
arm_grime = np.clip((ln_big - 0.36) * 1.9, 0.0, 0.58) * (0.65 + 0.55 * ln_fine)
grime_col = torso_skin_mean * np.array([0.46, 0.40, 0.36], dtype=np.float32)
leg_skin = leg_skin * (1.0 - arm_grime[..., None]) + grime_col * arm_grime[..., None]

# Re-lock exposed shin mean to torso_skin_mean after mottling so brightness & hue match 1:1!
cur_shin_mean = leg_skin[shin_ref_mask].mean(axis=0) if np.any(shin_ref_mask) else leg_skin.mean(axis=0)
leg_skin = np.clip(leg_skin * (torso_skin_mean / np.maximum(cur_shin_mean, 1e-4))[None, None, :], 0.04, 0.48)

# Wet photographed Cambodian village mud splashing up bare feet, toes, and ankles (below z = 0.18m)
foot_mud = np.clip((0.18 - z_leg_uv) / 0.18, 0.0, 1.0) ** 1.35
foot_mud = np.clip(foot_mud * (0.58 + 0.52 * ln_big), 0.0, 0.78)
leg_skin = leg_skin * (1.0 - foot_mud[..., None]) + leg_mud_bc * foot_mud[..., None]

# Dark dried blood trickles & grime running down from under the sampot hem onto thighs/knees
trickle = np.clip((z_leg_uv - 0.24) / 0.36, 0.0, 1.0) * np.clip((ln_fine - 0.60) * 5.2, 0.0, 0.68)
leg_skin = leg_skin * (1.0 - trickle[..., None]) + np.array([0.14, 0.022, 0.018], dtype=np.float32) * trickle[..., None]

# Natural contact shadow right under the sampot overhang
skirt_ao = np.clip(1.0 - np.clip((z_leg_uv - 0.46) / 0.14, 0.0, 1.0) * 0.55, 0.42, 1.0)
leg_skin *= (0.76 + 0.24 * ao_leg_uv[..., None]) * skirt_ao[..., None]
print(
    f"[headless_ghost] final matched shin skin mean sRGB="
    f"{[round(float(c), 3) for c in leg_skin[shin_ref_mask].mean(axis=0)]}",
    flush=True,
)

leg_bc_rgba = np.concatenate([np.clip(leg_skin, 0.0, 1.0), np.ones((HL, WL, 1), dtype=np.float32)], axis=-1)
leg_rough = np.clip(0.72 - foot_mud * 0.14 - trickle * 0.32 + (ln_fine - 0.5) * 0.10, 0.30, 0.88)
leg_rm_rgba = np.stack([np.ones_like(leg_rough), leg_rough, np.zeros_like(leg_rough), np.ones_like(leg_rough)], axis=-1)
leg_base_nm = height_to_normal(ln_fine * 0.42 + trickle * 0.50, strength=1.2)
leg_nm_rgba = PS.blend_tangent_normals(leg_base_nm, leg_skin_pore_n, np.full((HL, WL), 0.85, dtype=np.float32))
leg_nm_rgba = PS.blend_tangent_normals(leg_nm_rgba, leg_mud_n, foot_mud * 0.85)

leg_bc_img = np_to_img("T_headless_legs_BC", leg_bc_rgba, "sRGB")
leg_rm_img = np_to_img("T_headless_legs_ORM", leg_rm_rgba, "Non-Color")
leg_nm_img = np_to_img("T_headless_legs_N", leg_nm_rgba, "Non-Color")

leg_mat = bpy.data.materials.new("M_headless_ghost_legs")
leg_mat.use_nodes = True
lnodes = leg_mat.node_tree.nodes
llinks = leg_mat.node_tree.links
lbsdf = next(n for n in lnodes if n.type == "BSDF_PRINCIPLED")
lbsdf.inputs["Metallic"].default_value = 0.0
lbsdf.inputs["Specular IOR Level"].default_value = 0.38

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
lnmap.inputs["Strength"].default_value = 1.0
llinks.new(lt_nm.outputs["Color"], lnmap.inputs["Color"])
llinks.new(lnmap.outputs["Normal"], lbsdf.inputs["Normal"])
legs.data.materials.append(leg_mat)

# 4. Add 30 restrained side/jaw-framing wet hair wisps (NEVER blocking the sculpted severed face & ZERO mesh shrinking!)
h_hair_mat, h_hair_imgs = HC.build_wet_hair_card_material(prefix="headless", seed=1933)
h_hair_obj = HC.build_headless_hair_cards(torso, h_hair_mat, bpy.context.scene.collection, seed=1933)

# Remove temporary source images before export
bpy.data.images.remove(mh_tex_raw)
keep_set = {bc_out, rm_out, nm_out, leg_bc_img, leg_rm_img, leg_nm_img, *h_hair_imgs}
for img in list(bpy.data.images):
    if img not in keep_set:
        bpy.data.images.remove(img)

# Report final combined height & tri counts
t_tris = sum(len(p.vertices) - 2 for p in torso.data.polygons)
l_tris = sum(len(p.vertices) - 2 for p in legs.data.polygons)
hc_tris = sum(len(p.vertices) - 2 for p in h_hair_obj.data.polygons) if h_hair_obj else 0
all_z = [v.co.z for o in (torso, legs) for v in o.data.vertices]
print(
    f"[headless_ghost] full-body photoreal built: torso={t_tris:,} + legs={l_tris:,} + hair_cards={hc_tris:,} tris, "
    f"height={min(all_z):.3f}..{max(all_z):.3f}m -> {OUT}",
    flush=True,
)

bpy.ops.object.select_all(action="DESELECT")
torso.select_set(True)
legs.select_set(True)
if h_hair_obj:
    h_hair_obj.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=str(OUT),
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
)
