"""Procedural AAA-grade wet alpha-clipped hair-card generator for Episode 1 ghosts (Preay & Headless Ghost).

Replaces solid sculpted clay-helmet hair silhouettes with:
  1. A 4-column 1024x1024 multi-strand RGBA wet hair card texture atlas (dense inner locks,
     clumped damp mid-locks, frayed split-tip locks, and gossamer face-veil / silhouette flyaways)
     paired with cylindrical per-strand tangent normals (`_N`, 512x512) and damp strand roughness (`_ORM`, 512x512).
  2. BVH surface-conforming, V-cupped 3-tier curved hair-card ribbons (`doubleSided`, `alphaMode=MASK`)
     draped organically from the scalp part over temples, cheeks, shoulders, chest, and back —
     breaking up every solid helmet edge into hundreds of fine, wispy wet hair strands.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _make_img(name, arr, colorspace):
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    h, w = arr.shape[:2]
    img = bpy.data.images.new(name, width=w, height=h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.clip(arr, 0.0, 1.0).astype(np.float32).ravel())
    img.pack()
    return img


def _downsample2x(arr):
    h, w = arr.shape[:2]
    return 0.25 * (arr[0:h:2, 0:w:2] + arr[1:h:2, 0:w:2] + arr[0:h:2, 1:w:2] + arr[1:h:2, 1:w:2])


def _height_to_normal(height_map, strength=2.4):
    gx = (np.roll(height_map, -1, axis=1) - np.roll(height_map, 1, axis=1)) * 0.5 * strength
    gy = (np.roll(height_map, -1, axis=0) - np.roll(height_map, 1, axis=0)) * 0.5 * strength
    nx = -gx
    ny = -gy
    nz = np.ones_like(nx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    n = np.stack([nx * inv * 0.5 + 0.5, ny * inv * 0.5 + 0.5, nz * inv * 0.5 + 0.5, np.ones_like(nx)], axis=-1)
    return np.clip(n, 0.0, 1.0).astype(np.float32)


def build_wet_hair_card_material(prefix="preay", seed=1932):
    """Generates a 4-column 1024x1024 photorealistic wet hair-card atlas (BC+A, 512 ORM, 512 N)
    and returns `(material, [images])` configured for glTF alphaMode=MASK and doubleSided=True.

    UV convention:
      u in [0..1] across 4 distinct card styles (0=dense inner, 1=clumped mid, 2=split wispy, 3=flyaways)
      v = 1.0 at scalp root -> v = 0.0 at frayed wet tips!
    """
    N = 1024
    rng = np.random.default_rng(seed)
    # y_idx = 0 at bottom (tips, v=0), y_idx = N-1 at top (roots, v=1)
    v_grid = np.linspace(0.0, 1.0, N, dtype=np.float32)[:, None]
    u_grid = np.linspace(0.0, 1.0, N, dtype=np.float32)[None, :]

    alpha = np.zeros((N, N), dtype=np.float32)
    height = np.zeros((N, N), dtype=np.float32)
    tone_acc = np.zeros((N, N, 3), dtype=np.float32)
    tone_w = np.zeros((N, N), dtype=np.float32)
    rough_acc = np.zeros((N, N), dtype=np.float32)

    # Column specs: (col_idx, n_strands, n_clumps, width_range, tip_min, tip_max, root_fill)
    cols = [
        (0, 74, 4, (0.0020, 0.0046), 0.02, 0.34, 0.88),  # Dense inner curtain lock
        (1, 56, 3, (0.0018, 0.0040), 0.03, 0.42, 0.72),  # Matted wet mid-clump
        (2, 42, 3, (0.0015, 0.0034), 0.02, 0.50, 0.50),  # Split-tip frayed outer lock
        (3, 26, 2, (0.0013, 0.0028), 0.04, 0.58, 0.22),  # Delicate face-veil & silhouette flyaways
    ]

    for col_idx, n_strands, n_clumps, (w_lo, w_hi), tip_lo, tip_hi, root_fill in cols:
        u0 = col_idx * 0.25 + 0.014
        u1 = (col_idx + 1) * 0.25 - 0.014
        u_mid = 0.5 * (u0 + u1)
        u_half = 0.5 * (u1 - u0)

        # Clump anchor positions in column so wet strands organically pull together toward tips!
        clump_centers = np.linspace(u0 + 0.035, u1 - 0.035, n_clumps) + rng.uniform(-0.012, 0.012, n_clumps)

        # Soft opaque root band for inner columns so roots blend seamlessly into scalp with zero gaps
        if root_fill > 0.3:
            edge_fade = np.clip(1.0 - (np.abs(u_grid - u_mid) / max(u_half, 1e-4)) ** 2.6, 0.0, 1.0)
            root_band = np.clip((v_grid - (0.76 - 0.14 * root_fill)) / 0.26, 0.0, 1.0) ** 1.4
            base_a = edge_fade * root_band * root_fill
            alpha = np.maximum(alpha, base_a)
            height = np.maximum(height, base_a * 0.22)
            base_col = np.array([0.022, 0.019, 0.017], dtype=np.float32)
            tone_acc += base_col[None, None, :] * base_a[..., None] * 0.5
            tone_w += base_a * 0.5
            rough_acc += 0.58 * base_a * 0.5

        for _ in range(n_strands):
            # Pick a clump & lateral offset
            ci = int(rng.integers(0, n_clumps))
            c_u = clump_centers[ci]
            start_u = float(np.clip(rng.uniform(u0 + 0.01, u1 - 0.01), u0 + 0.006, u1 - 0.006))
            # Wet hairs pull subtly toward their clump center as they hang down (v: 1 -> 0)
            clump_pull = float(rng.uniform(0.28, 0.72))
            wave_amp = float(rng.uniform(0.0025, 0.0095))
            wave_freq = float(rng.uniform(5.0, 12.5))
            wave_phase = float(rng.uniform(0.0, math.tau))
            tip_v = float(rng.uniform(tip_lo, tip_hi))
            root_v = float(rng.uniform(0.92, 1.00)) if col_idx < 3 else float(rng.uniform(0.75, 1.00))
            base_w = float(rng.uniform(w_lo, w_hi))

            # Center curve x(v): root at v=1 -> tapered wet tip at v=tip_v
            hang = 1.0 - v_grid  # 0 at root, 1 at bottom tip
            center_u = (
                start_u * (1.0 - clump_pull * (hang ** 1.25))
                + c_u * (clump_pull * (hang ** 1.25))
                + wave_amp * np.sin(hang * wave_freq + wave_phase) * (0.25 + 0.75 * hang)
            )
            # Keep strands cleanly inside their own column margin
            center_u = np.clip(center_u, u0 + 0.004, u1 - 0.004)

            # Strand tapers sharply toward its wet tip & gently at root
            tip_taper = np.clip((v_grid - tip_v) / max(0.18, 0.34 - tip_v * 0.3), 0.0, 1.0) ** 0.75
            root_taper = np.clip((root_v - v_grid) / 0.08 + 0.85, 0.0, 1.0)
            width_v = np.maximum(base_w * (0.35 + 0.65 * tip_taper), 0.00085)

            dx = (u_grid - center_u) / width_v
            # Crisp rounded cylindrical strand profile
            profile = np.exp(-1.85 * dx * dx) * tip_taper * root_taper
            strand_h = np.clip(1.0 - 0.75 * dx * dx, 0.0, 1.0) * tip_taper * root_taper

            # Subtle per-strand natural damp dark Asian hair color (dark charcoal-espresso with natural gleam!)
            val = float(rng.uniform(0.028, 0.088))
            warm = float(rng.uniform(0.92, 1.06))
            s_col = np.array([val * warm, val * 0.89, val * 0.81], dtype=np.float32)
            # Natural darkening at roots & wet clumped tips, subtle luster in mid-lengths
            v_shade = 0.74 + 0.34 * np.sin(v_grid * math.pi)
            s_rough = float(rng.uniform(0.42, 0.64))

            alpha = np.maximum(alpha, profile)
            # Keep foreground strand's rounded normal & color where it's thicker
            height = np.maximum(height, strand_h * float(rng.uniform(0.65, 1.0)))
            w_add = profile * profile
            tone_acc += s_col[None, None, :] * v_shade[..., None] * w_add[..., None]
            tone_w += w_add
            rough_acc += s_rough * w_add

    safe_w = np.maximum(tone_w, 1e-4)
    bc_rgb = np.where(
        tone_w[..., None] > 1e-3,
        tone_acc / safe_w[..., None],
        np.array([0.025, 0.022, 0.020], dtype=np.float32)[None, None, :],
    )
    # Softly taper top 5% crown root edge into wispy scalp roots so card tops never read as stepped strips!
    root_feather = np.clip((1.0 - v_grid) / 0.055, 0.0, 1.0) ** 0.65
    alpha = np.clip(alpha * root_feather, 0.0, 1.0)
    bc_rgba = np.concatenate([np.clip(bc_rgb, 0.012, 0.14), alpha[..., None]], axis=-1)

    rough = np.where(tone_w > 1e-3, rough_acc / safe_w, 0.56)
    rough_512 = _downsample2x(np.clip(rough, 0.38, 0.74))
    ao_512 = _downsample2x(np.clip(0.55 + 0.45 * height, 0.45, 1.0))
    orm_512 = np.stack([ao_512, rough_512, np.zeros_like(rough_512), np.ones_like(rough_512)], axis=-1)

    nm_1024 = _height_to_normal(height, strength=3.4)
    nm_512 = _downsample2x(nm_1024)
    # Re-normalize downsampled tangent normal
    nv = nm_512[..., :3] * 2.0 - 1.0
    nv /= np.sqrt(np.sum(nv * nv, axis=-1, keepdims=True) + 1e-8)
    nm_512 = np.concatenate([nv * 0.5 + 0.5, np.ones((512, 512, 1), dtype=np.float32)], axis=-1)

    img_bc = _make_img(f"T_{prefix}_hair_BC", bc_rgba, "sRGB")
    img_orm = _make_img(f"T_{prefix}_hair_ORM", orm_512, "Non-Color")
    img_nm = _make_img(f"T_{prefix}_hair_N", nm_512, "Non-Color")

    mat = bpy.data.materials.new(f"M_{prefix}_hair_cards")
    mat.use_nodes = True
    mat.use_backface_culling = False
    if hasattr(mat, "blend_method"):
        mat.blend_method = "CLIP"
    if hasattr(mat, "alpha_threshold"):
        mat.alpha_threshold = 0.32

    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.30 if prefix == "headless" else 0.34

    t_bc = nodes.new("ShaderNodeTexImage")
    t_bc.image = img_bc
    links.new(t_bc.outputs["Color"], bsdf.inputs["Base Color"])
    # Blender 4.2+/5.x glTF exporter emits `alphaMode: "MASK"` + `alphaCutoff` when Alpha passes
    # through a Math GREATER_THAN threshold (avoiding broken BLEND depth-sorting in WebGPU!)
    n_clip = nodes.new("ShaderNodeMath")
    n_clip.operation = "GREATER_THAN"
    n_clip.inputs[1].default_value = 0.34
    links.new(t_bc.outputs["Alpha"], n_clip.inputs[0])
    links.new(n_clip.outputs["Value"], bsdf.inputs["Alpha"])

    t_orm = nodes.new("ShaderNodeTexImage")
    t_orm.image = img_orm
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(t_orm.outputs["Color"], sep.inputs["Color"])
    links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])

    t_nm = nodes.new("ShaderNodeTexImage")
    t_nm.image = img_nm
    nmap = nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.92
    links.new(t_nm.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    return mat, [img_bc, img_orm, img_nm]


def _append_card(verts, faces, uvs, spine_pts, spine_nrms, width_fn, cup_depth, col_idx, twist_rad=0.0, v_range=(1.0, 0.0)):
    """Appends one 3-across V-cupped curved hair card strip along `spine_pts` into batched buffers."""
    n_seg = len(spine_pts)
    u0 = col_idx * 0.25 + 0.008
    u1 = (col_idx + 1) * 0.25 - 0.008
    u_mid = 0.5 * (u0 + u1)
    v_start, v_end = v_range
    base_idx = len(verts)

    for i in range(n_seg):
        t = i / max(1, n_seg - 1)  # 0 at root, 1 at tip
        p = spine_pts[i]
        nrm = spine_nrms[i].normalized()
        if i == 0:
            tan = (spine_pts[1] - spine_pts[0]).normalized()
        elif i == n_seg - 1:
            tan = (spine_pts[-1] - spine_pts[-2]).normalized()
        else:
            tan = (spine_pts[i + 1] - spine_pts[i - 1]).normalized()

        side = tan.cross(nrm)
        if side.length < 1e-4:
            side = Vector((1.0, 0.0, 0.0))
        else:
            side.normalize()
        # Re-orthogonalize normal & apply subtle twist so cards catch light from oblique angles
        nrm_o = side.cross(tan).normalized()
        tw = twist_rad * t
        ct, st = math.cos(tw), math.sin(tw)
        s_rot = side * ct + nrm_o * st
        n_rot = -side * st + nrm_o * ct

        half_w = 0.5 * width_fn(t)
        cup = cup_depth * (0.35 + 0.65 * math.sin(t * math.pi))
        p_left = p - s_rot * half_w
        p_mid = p + n_rot * cup
        p_right = p + s_rot * half_w
        verts.extend([p_left, p_mid, p_right])

        v_uv = v_start * (1.0 - t) + v_end * t
        uvs.extend([(u0, v_uv), (u_mid, v_uv), (u1, v_uv)])

    for i in range(n_seg - 1):
        r0 = base_idx + i * 3
        r1 = base_idx + (i + 1) * 3
        faces.append((r0, r0 + 1, r1 + 1, r1))
        faces.append((r0 + 1, r0 + 2, r1 + 2, r1 + 1))


def build_preay_hair_cards(body, rig, mat, coll, seed=1932):
    """Creates a 3-tier BVH-conformed layered wet hair-card groom (`preay_hair_cards`) over Preay's
    skull, temples, cheeks, shoulders, chest, and upper back, skinned cleanly to `preay_rig`!"""
    rng = np.random.default_rng(seed)

    # Build BVH from current (unshrunk!) `body` mesh so cards conform cleanly over head & dress
    bm_ref = bmesh.new()
    bm_ref.from_mesh(body.data)
    bvh = BVHTree.FromBMesh(bm_ref)
    bm_ref.free()

    verts, faces, uvs = [], [], []
    head_c = Vector((0.0, -0.010, 1.465))

    def trace_card(az, start_z, length, width, offset_base, offset_tip, wave_amp, wave_freq, col_idx,
                   cup=0.0045, twist=0.0, front_sweep=0.0):
        """Traces a natural gravity-draped hair ribbon along `bvh` from crown/scalp down over
        temples, cheeks, shoulders, chest, or back."""
        n_steps = 13
        pts, nrms = [], []
        ph = float(rng.uniform(0.0, math.tau))
        # Azimuth 0 = -Y (front center of face), +pi/2 = +X (left ear), pi = +Y (back)
        for i in range(n_steps):
            t = i / (n_steps - 1)
            z = start_z - length * t
            # Gently sweep front face-framing locks slightly around nose/eyes (or across for wisps)
            a_cur = az + front_sweep * math.sin(min(1.0, t * 1.6) * math.pi * 0.6)
            a_cur += (wave_amp * 2.4) * math.sin(t * wave_freq + ph) * t

            # Initial ray probe outward from spine centerline at height z
            # Crown dome tapers radius smoothly near z = 1.58
            dome = math.sqrt(max(0.04, 1.0 - max(0.0, (z - 1.47) / 0.12) ** 2))
            probe_r = 0.22 if z < 1.33 else 0.14 * dome + 0.04
            px = math.sin(a_cur) * probe_r
            py = -math.cos(a_cur) * probe_r + (-0.008 if z > 1.32 else 0.005)
            probe = Vector((px, py, z))
            # Snap cleanly onto Preay's real surface via BVH closest point
            loc, nrm, _, _ = bvh.find_nearest(probe)
            if loc is None:
                loc = Vector((px * 0.5, py * 0.5, z))
                nrm = Vector((math.sin(a_cur), -math.cos(a_cur), 0.15)).normalized()

            # Ensure normal points generally outward from head/torso center
            out_dir = (loc - Vector((0.0, -0.008, min(z, 1.48))))
            if out_dir.length > 1e-4 and nrm.dot(out_dir) < 0.0:
                nrm = -nrm
            if nrm.length < 1e-4:
                nrm = out_dir.normalized()

            # Keep roots hugging 3-5mm OUTSIDE the dark scalp dome so the sculpted skull cap NEVER
            # pokes above the hair cards (silky natural crown part & cascading wet locks)!
            root_zone = max(0.0, 1.0 - t / 0.18)
            off = (offset_base * (1.0 - t) + offset_tip * t) + 0.0045 * root_zone
            off += wave_amp * 0.55 * math.sin(t * wave_freq * 1.3 + ph) * (t ** 0.85)
            p = loc + nrm.normalized() * off

            # Keep face-veil wisps hovering gently in front of forehead/cheek (never poking into eyes)
            if abs(a_cur) < 0.52 and 1.34 < z < 1.52:
                p.y = min(p.y, -0.106 - max(0.0, off) * 0.65)
            pts.append(p)
            nrms.append(nrm.normalized())

        # Arch root cleanly right up to the natural center scalp part along the crown ridge (z=1.580)!
        if start_z > 1.53:
            part_y = max(-0.075, min(0.065, -0.012 - 0.065 * math.cos(az)))
            part_x = 0.004 * (1 if az >= 0 else -1)
            part_pt = Vector((part_x, part_y, 1.582))
            pts[0] = pts[0].lerp(part_pt, 0.72)
            pts[1] = pts[1].lerp(Vector((part_x + 0.028 * math.sin(az), part_y - 0.025 * math.cos(az), 1.564)), 0.45)

        # Slight smoothing along the traced spline so crown & shoulder transitions stay silky
        for _ in range(3):
            sm = [pts[0]]
            for j in range(1, len(pts) - 1):
                sm.append(pts[j] * 0.55 + (pts[j - 1] + pts[j + 1]) * 0.225)
            sm.append(pts[-1])
            pts = sm

        def width_fn(t):
            # Full root overlap across crown part -> lush mid-lock -> softly tapered wispy tips
            return width * (0.68 + 0.32 * math.sin(min(1.0, t * 1.25 + 0.15) * math.pi * 0.80)) * (1.0 - 0.18 * (t ** 2))

        _append_card(verts, faces, uvs, pts, nrms, width_fn, cup, col_idx, twist)

    # ---- Tier 0: Dedicated Crown-Part Arch Cap (34 overlapping cards arching cleanly OVER the top
    # skull dome from the natural center part down past temples/forehead/nape — ZERO bald egg cap!)
    for k in range(34):
        side_s = 1.0 if (k % 2 == 0) else -1.0
        frac = (k // 2) / 16.0  # front-to-back along the center part line (y = -0.085..+0.075)
        py_root = -0.082 + frac * 0.155
        az = side_s * (0.30 + frac * 2.55) + float(rng.uniform(-0.06, 0.06))
        pts_c, nrms_c = [], []
        n_st = 11
        length_c = float(rng.uniform(0.28, 0.44))
        ph_c = float(rng.uniform(0.0, math.tau))
        for i in range(n_st):
            t = i / (n_st - 1)
            # First 35% arches smoothly outward over the crown dome; then cascades down sides/back!
            if t < 0.35:
                u_a = t / 0.35
                ang_dome = u_a * (math.pi * 0.48)
                rx = side_s * math.sin(ang_dome) * (0.088 + 0.014 * math.sin(frac * math.pi))
                ry = py_root - math.cos(az) * math.sin(ang_dome) * 0.032
                rz = 1.495 + math.cos(ang_dome) * 0.089
                probe = Vector((rx, ry, rz))
            else:
                u_d = (t - 0.35) / 0.65
                rz = 1.495 - u_d * length_c
                rad = 0.105 + 0.065 * u_d
                a_w = az + 0.08 * math.sin(u_d * 6.5 + ph_c)
                probe = Vector((math.sin(a_w) * rad, py_root * (1.0 - 0.4 * u_d) - math.cos(a_w) * rad * 0.55, rz))
            loc, nrm, _, _ = bvh.find_nearest(probe)
            if loc is None:
                loc = probe
                nrm = (probe - head_c).normalized()
            out_v = loc - Vector((0.0, -0.010, min(probe.z, 1.47)))
            if out_v.length > 1e-4 and nrm.dot(out_v) < 0:
                nrm = -nrm
            nrm = nrm.normalized() if nrm.length > 1e-4 else Vector((0, 0, 1))
            off_c = 0.0055 + 0.008 * t
            pts_c.append(loc + nrm * off_c)
            nrms_c.append(nrm)
        for _ in range(2):
            sm = [pts_c[0]]
            for j in range(1, len(pts_c) - 1):
                sm.append(pts_c[j] * 0.55 + (pts_c[j - 1] + pts_c[j + 1]) * 0.225)
            sm.append(pts_c[-1])
            pts_c = sm
        _append_card(
            verts, faces, uvs, pts_c, nrms_c,
            lambda t, w=float(rng.uniform(0.036, 0.052)): w * (0.78 + 0.22 * math.sin(t * math.pi)) * (1.0 - 0.2 * t * t),
            cup_depth=0.004,
            col_idx=0 if (k % 3 != 2) else 1,
            twist_rad=float(rng.uniform(-0.12, 0.12)),
        )

    # ---- Tier 1: Inner Dense Curtain (64 cards covering full 360° scalp & shoulders with parted face!)
    for k in range(64):
        az = -math.pi + (k + 0.5) * (math.tau / 64) + float(rng.uniform(-0.03, 0.03))
        # Leave natural parting slit over center nose & one peering pale eye (az near 0)
        if abs(az) < 0.17:
            continue
        is_front = abs(az) < 0.85
        start_z = float(rng.uniform(1.552, 1.568)) if not is_front else float(rng.uniform(1.540, 1.560))
        length = float(rng.uniform(0.54, 0.72)) if not is_front else float(rng.uniform(0.46, 0.64))
        sweep = (0.14 if az > 0 else -0.16) if abs(az) < 0.55 else 0.0
        col = 0 if (k % 2 == 0) else 1
        trace_card(
            az=az,
            start_z=start_z,
            length=length,
            width=float(rng.uniform(0.044, 0.062)),
            offset_base=float(rng.uniform(0.002, 0.004)),
            offset_tip=float(rng.uniform(0.007, 0.014)),
            wave_amp=float(rng.uniform(0.004, 0.010)),
            wave_freq=float(rng.uniform(4.5, 7.5)),
            col_idx=col,
            cup=0.0045,
            twist=float(rng.uniform(-0.14, 0.14)),
            front_sweep=sweep,
        )

    # ---- Tier 2: Mid-Layer Clumped Wet Locks (62 wavy ragged locks across temples, chest, shoulders, back)
    for k in range(62):
        az = -math.pi + (k + 0.35) * (math.tau / 62) + float(rng.uniform(-0.05, 0.05))
        if abs(az) < 0.13:
            continue
        is_back = abs(az) > 1.35
        start_z = float(rng.uniform(1.515, 1.562))
        # Dramatic uneven tattered wet lengths (long cascading back veil 52..74cm!)
        length = float(rng.uniform(0.52, 0.74)) if is_back else float(rng.uniform(0.42, 0.68))
        sweep = (0.10 if az > 0 else -0.14) if abs(az) < 0.48 else 0.0
        col = 1 if (k % 2 == 0) else 2
        trace_card(
            az=az,
            start_z=start_z,
            length=length,
            width=float(rng.uniform(0.032, 0.048)),
            offset_base=float(rng.uniform(0.004, 0.008)),
            offset_tip=float(rng.uniform(0.012, 0.022)),
            wave_amp=float(rng.uniform(0.007, 0.016)),
            wave_freq=float(rng.uniform(5.5, 9.5)),
            col_idx=col,
            cup=0.0055,
            twist=float(rng.uniform(-0.26, 0.26)),
            front_sweep=sweep,
        )

    # ---- Tier 3: Outer Wispy Flyaways & Haunting Face-Veil Strands (46 gossamer cards!)
    for k in range(38):
        az = -math.pi + (k + 0.5) * (math.tau / 38) + float(rng.uniform(-0.08, 0.08))
        start_z = float(rng.uniform(1.47, 1.555))
        length = float(rng.uniform(0.30, 0.74))
        col = 2 if (k % 3 == 0) else 3
        trace_card(
            az=az,
            start_z=start_z,
            length=length,
            width=float(rng.uniform(0.022, 0.038)),
            offset_base=float(rng.uniform(0.006, 0.011)),
            offset_tip=float(rng.uniform(0.016, 0.028)),
            wave_amp=float(rng.uniform(0.010, 0.022)),
            wave_freq=float(rng.uniform(6.0, 11.0)),
            col_idx=col,
            cup=0.0045,
            twist=float(rng.uniform(-0.36, 0.36)),
            front_sweep=0.0,
        )

    # Dedicated haunting face-veil wisps: asymmetric strands hanging over her forehead & shadowed left eye
    face_azs = [-0.26, -0.18, -0.11, -0.05, 0.03, 0.12, 0.20, 0.28, -0.34, 0.34]
    for idx, az in enumerate(face_azs):
        trace_card(
            az=az,
            start_z=float(rng.uniform(1.535, 1.568)),
            length=float(rng.uniform(0.22, 0.46)),
            width=float(rng.uniform(0.018, 0.028)),
            offset_base=0.006,
            offset_tip=float(rng.uniform(0.012, 0.020)),
            wave_amp=float(rng.uniform(0.006, 0.014)),
            wave_freq=float(rng.uniform(6.5, 10.0)),
            col_idx=3,
            cup=0.003,
            twist=float(rng.uniform(-0.22, 0.22)),
            front_sweep=(0.06 if idx % 2 else -0.06),
        )

    mesh = bpy.data.meshes.new("preay_hair_cards")
    mesh.from_pydata(verts, [], faces)
    uv_l = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            uv_l.data[li].uv = uvs[mesh.loops[li].vertex_index]
    mesh.materials.append(mat)
    mesh.update()

    hair_obj = bpy.data.objects.new("preay_hair_cards", mesh)
    coll.objects.link(hair_obj)

    # Skin `preay_hair_cards` smoothly to `preay_rig` (head -> neck -> chest/shoulders!)
    for b in rig.data.bones:
        hair_obj.vertex_groups.new(name=b.name)

    def sstep(a, b, x):
        t = max(0.0, min(1.0, (x - a) / max(b - a, 1e-6)))
        return t * t * (3.0 - 2.0 * t)

    for v in mesh.vertices:
        x, y, z = v.co.x, v.co.y, v.co.z
        w_head = sstep(1.22, 1.44, z)
        w_neck = (1.0 - w_head) * sstep(1.08, 1.26, z) * 0.58
        rem = max(0.0, 1.0 - w_head - w_neck)
        w_clav = rem * 0.25 * sstep(0.09, 0.16, abs(x)) * sstep(1.05, 1.24, z)
        w_chest = rem - w_clav
        w_s1 = w_chest * 0.68
        w_s2 = w_chest * 0.32

        if w_head > 1e-4:
            hair_obj.vertex_groups["head"].add([v.index], w_head, "REPLACE")
        if w_neck > 1e-4:
            hair_obj.vertex_groups["neck02"].add([v.index], w_neck, "REPLACE")
        if w_s1 > 1e-4:
            hair_obj.vertex_groups["spine01"].add([v.index], w_s1, "REPLACE")
        if w_s2 > 1e-4:
            hair_obj.vertex_groups["spine02"].add([v.index], w_s2, "REPLACE")
        if w_clav > 1e-4:
            cname = "clavicle.L" if x >= 0.0 else "clavicle.R"
            hair_obj.vertex_groups[cname].add([v.index], w_clav, "REPLACE")

    arm = hair_obj.modifiers.new("Armature", "ARMATURE")
    arm.object = rig
    arm.use_deform_preserve_volume = True
    hair_obj.parent = rig
    return hair_obj


def build_headless_hair_cards(torso, mat, coll, seed=1933):
    """Builds a cinema-grade 174-card multi-tier layered wet hair groom (`MASK` alpha, ~6,600 tris)
    completely replacing Headless Ghost's recessed cartoon clay hair with Preay-grade photorealistic
    wet Cambodian monsoon hair:
      - Tier 1 (46 pulled-up dome-to-fist locks): converge tightly inside her gripping right fist and
        hug 100% of the upper forehead/crown dome right down to the organic hairline (`z = 1.044..1.058`)
        with generous outward clearance (+5..+10mm) so ZERO smooth scalp ever pokes through!
      - Tier 2 (66 cascading inner & mid-layer side/back curtains): root tucked snugly inside the
        recessed crown/temples and drape lushly down past her cheekbones, ears, and 10-20cm below her
        severed jaw — completely replacing the removed clay side-flabs with layered individual wet locks!
      - Tier 3 (18 fist-spill wet hair tails): real fine wet locks spilling naturally out from above
        and beside her clenched knuckles (replacing the removed cartoon clay claw!).
      - Tier 4 (44 hairline baby-wisps & outer gossamer flyaways): organic irregular wisps breaking up
        the hairline and jaw silhouette while keeping both staring eyes, nose & bloody teeth 100% clear."""
    rng = np.random.default_rng(seed)

    co = np.array([v.co[:] for v in torso.data.vertices], dtype=np.float32)
    sev = co[(co[:, 1] < -0.22) & (co[:, 2] > 0.86) & (co[:, 2] < 1.24) & (np.abs(co[:, 0]) < 0.14)]
    if len(sev) < 20:
        return None
    face_pts = sev[(sev[:, 1] < -0.29) & (sev[:, 2] > 0.87) & (sev[:, 2] < 1.055)]
    hx = float(np.median(face_pts[:, 0])) if len(face_pts) > 10 else float(np.median(sev[:, 0]))
    hy_front = float(np.percentile(face_pts[:, 1], 10)) if len(face_pts) > 10 else float(np.percentile(sev[:, 1], 10))
    hy = hy_front + 0.098  # anatomical center of the severed cranium (~ -0.282)
    # Exact center of the pulled hair bundle tucked right beneath her gripping knuckles (never piercing her fingers!)
    grip_pt = Vector((hx - 0.006, hy - 0.006, 1.202))

    bm_ref = bmesh.new()
    bm_ref.from_mesh(torso.data)
    bvh = BVHTree.FromBMesh(bm_ref)
    bm_ref.free()

    verts, faces, uvs = [], [], []

    def smooth_dome_point(az, u, r_scale=1.0, z_bottom=1.045):
        """Returns `(pos, smooth_outward_normal)` on a silky C2-continuous teardrop cranium loft
        running from the clenched fist `grip_pt` (`u=0`) down to the curved hairline (`u=1`).
        Uses smooth analytical normals so hair cards NEVER kink or twist on bumpy mesh creases!"""
        # Smooth S-curve profile from tight 1.6cm hair bundle inside fist -> full 9.0cm cranium dome
        r_prof = (0.016 + 0.076 * (math.sin(u * math.pi * 0.54) ** 0.88)) * r_scale
        # Front forehead sits slightly further forward (-Y) than sides
        ry_boost = 1.04 if abs(az) < 1.1 else 0.96
        z = grip_pt.z * (1.0 - u) + z_bottom * u
        cx = grip_pt.x * (1.0 - u) + hx * u
        cy = grip_pt.y * (1.0 - u) + hy * u
        px = cx + math.sin(az) * r_prof
        py = cy - math.cos(az) * r_prof * ry_boost
        p = Vector((px, py, z))
        # Smooth analytical outward normal (tilted slightly upward on the dome cone!)
        nrm = Vector((math.sin(az), -math.cos(az), 0.34 * (1.0 - u))).normalized()
        return p, nrm

    def ensure_outside_smooth(pts, nrms, min_clear, start_i=1, z_min=1.01):
        """Gently nudges any point along its OWN smooth analytical normal if the recessed scalp mesh
        comes within `min_clear` — preserving 100% silky normals (zero crumpled/twisted card facets!)."""
        for i in range(start_i, len(pts)):
            p = pts[i]
            if p.z < z_min:
                continue
            loc, _, _, _ = bvh.find_nearest(p)
            if loc is None:
                continue
            nrm = nrms[i]
            # Distance of `p` ahead of `loc` along the smooth outward normal
            clearance = (p - loc).dot(nrm)
            if clearance < min_clear and (p - loc).length < 0.055:
                pts[i] = p + nrm * (min_clear - clearance)
        # Re-smooth spine gently once so any clearance nudge stays silky C2-continuous
        for _ in range(2):
            sm = [pts[0]]
            for j in range(1, len(pts) - 1):
                sm.append(pts[j] * 0.56 + (pts[j - 1] + pts[j + 1]) * 0.22)
            sm.append(pts[-1])
            pts[:] = sm

    # ---- Tier 1A: 36 Front & Temple Pulled-Up Dome Locks rooted directly INTO her forehead hairline!
    # Curving the final 18% of `u` snugly INWARD onto her forehead skull (`tuck_in`) makes the taut
    # pulled-up wet hair strands emerge organically from her forehead skin (NOT hovering straight bangs!),
    # while layer 1 adds staggered irregular wispy baby-hairs softening the hairline!
    for layer_idx in (0, 1):
        n_front = 18
        for k in range(n_front):
            az = -1.24 + (k + 0.5 * layer_idx) / max(1, n_front - 0.5) * 2.48 + float(rng.uniform(-0.03, 0.03))
            # Natural arched hairline dipping softly at temples + organic strand-to-strand stagger
            z_end = 1.045 - 0.026 * (abs(az) / 1.15) ** 1.4 + float(rng.uniform(-0.008, 0.008))
            ph = float(rng.uniform(0.0, math.tau))
            r_sc = 0.96 if layer_idx == 0 else 1.01
            pts, nrms = [], []
            n_st = 11
            for i in range(n_st):
                t = i / (n_st - 1)
                a_c = az + 0.035 * math.sin(t * 5.0 + ph) * math.sin(t * math.pi)
                # Tuck bottom hairline smoothly inward onto the forehead skin so roots emerge seamlessly!
                root_tuck = 1.0 - (0.16 if layer_idx == 0 else 0.11) * (max(0.0, (t - 0.72) / 0.28) ** 1.6)
                p, nrm = smooth_dome_point(a_c, t, r_scale=r_sc * root_tuck, z_bottom=z_end)
                pts.append(p)
                nrms.append(nrm)
            # Enforce clearance on upper dome (`z_min = 1.064`), leaving hairline tips free to hug forehead skin!
            ensure_outside_smooth(pts, nrms, min_clear=0.004 if layer_idx == 0 else 0.008, start_i=1, z_min=1.064)
            w0 = float(rng.uniform(0.026, 0.036)) if layer_idx == 0 else float(rng.uniform(0.016, 0.024))
            _append_card(
                verts, faces, uvs, pts, nrms,
                lambda t, w=w0: w * (0.38 + 0.68 * math.sin(min(1.0, t * 1.15) * math.pi * 0.78)),
                cup_depth=0.0024,
                col_idx=0 if layer_idx == 0 else (1 if k % 2 == 0 else 2),
                twist_rad=float(rng.uniform(-0.08, 0.08)),
                # Layer 0 roots smoothly INTO hairline (dense `v=0.38..0.98`, zero hovering bangs gap!);
                # Layer 1 overlays delicate staggered wisps (`v=0.06..0.94`) softening the scalp border!
                v_range=(0.98, 0.38) if layer_idx == 0 else (0.94, 0.06),
            )

    # ---- Tier 1B: 28 Full-Length Pulled-Up Side & Back Crown-to-Jaw Locks (one continuous silky spline
    # from inside her fist grip over the smooth analytical dome and cascading 12-20cm below her jaw!)
    for k in range(28):
        side = -1.0 if (k % 2 == 0) else 1.0
        frac = (k // 2) / 13.0
        az = side * (0.76 + frac * 2.26) + float(rng.uniform(-0.04, 0.04))
        length_below = float(rng.uniform(0.22, 0.36))
        ph = float(rng.uniform(0.0, math.tau))
        w_amp = float(rng.uniform(0.005, 0.011))
        cheek_sweep = side * 0.14 if abs(az) < 1.02 else 0.0
        pts, nrms = [], []
        n_st = 14
        for i in range(n_st):
            t = i / (n_st - 1)
            if t < 0.42:
                u = t / 0.42
                a_c = az + 0.03 * math.sin(u * 4.5 + ph)
                p, nrm = smooth_dome_point(a_c, u, r_scale=1.03, z_bottom=1.045)
            else:
                u = (t - 0.42) / 0.58
                a_c = az + cheek_sweep * math.sin(min(1.0, u * 1.4) * math.pi * 0.7) + 0.09 * math.sin(u * 6.5 + ph) * u
                rad = 0.094 + 0.012 * math.sin(u * math.pi * 0.65)
                z = 1.045 - u * length_below
                p = Vector((
                    hx + math.sin(a_c) * rad + w_amp * math.sin(u * 7.5 + ph) * u,
                    hy - math.cos(a_c) * rad * 0.96 + w_amp * 0.5 * math.cos(u * 6.5 + ph) * u,
                    z,
                ))
                nrm = Vector((math.sin(a_c), -math.cos(a_c), 0.06 * (1.0 - u))).normalized()
            pts.append(p)
            nrms.append(nrm)
        ensure_outside_smooth(pts, nrms, min_clear=0.005, start_i=1, z_min=0.98)
        w0 = float(rng.uniform(0.025, 0.036))
        _append_card(
            verts, faces, uvs, pts, nrms,
            lambda t, w=w0: w * (0.36 + 0.68 * math.sin(min(1.0, t * 1.15) * math.pi * 0.85)) * (1.0 - 0.22 * t * t),
            cup_depth=0.0032,
            col_idx=0 if (k % 3 == 0) else 1,
            twist_rad=float(rng.uniform(-0.16, 0.16)),
        )

    # ---- Tier 2: 64 Lush Layered Side, Cheek & Back Wet Curtains (flowing seamlessly from the smooth
    # analytical upper dome down past her cheekbones and dangling 10-20cm below her severed jaw!)
    for tier_sub in (0, 1):
        n_curt = 34 if tier_sub == 0 else 30
        for k in range(n_curt):
            side = -1.0 if (k % 2 == 0) else 1.0
            frac = (k // 2) / max(1, (n_curt // 2) - 1)
            az = side * (0.78 + frac * 2.24) + float(rng.uniform(-0.04, 0.04))
            # Start smoothly along the upper dome cone (`u_start = 0.45..0.75`) tucked cleanly behind Tier 1!
            u_start = float(rng.uniform(0.42, 0.72)) if tier_sub == 0 else float(rng.uniform(0.50, 0.80))
            length_below = float(rng.uniform(0.20, 0.34)) if tier_sub == 0 else float(rng.uniform(0.22, 0.38))
            ph = float(rng.uniform(0.0, math.tau))
            w_amp = float(rng.uniform(0.006, 0.013))
            cheek_sweep = side * 0.16 if abs(az) < 1.02 else 0.0
            r_sc = 1.01 if tier_sub == 0 else 1.08
            pts, nrms = [], []
            n_st = 12
            p0, _ = smooth_dome_point(az, u_start, r_scale=r_sc * 0.94, z_bottom=1.045)
            z0 = p0.z
            for i in range(n_st):
                t = i / (n_st - 1)
                if t < 0.28:
                    uu = u_start + (1.0 - u_start) * (t / 0.28)
                    p, nrm = smooth_dome_point(az, uu, r_scale=r_sc * (0.94 + 0.08 * (t / 0.28)), z_bottom=1.045)
                else:
                    v = (t - 0.28) / 0.72
                    a_c = az + cheek_sweep * math.sin(min(1.0, v * 1.4) * math.pi * 0.7) + 0.10 * math.sin(v * 7.5 + ph) * v
                    rad = (0.091 if tier_sub == 0 else 0.101) + 0.014 * math.sin(v * math.pi * 0.6)
                    z = 1.045 - v * length_below
                    p = Vector((
                        hx + math.sin(a_c) * rad + w_amp * math.sin(v * 8.0 + ph) * v,
                        hy - math.cos(a_c) * rad * 0.96 + w_amp * 0.45 * math.cos(v * 7.0 + ph) * v,
                        z,
                    ))
                    nrm = Vector((math.sin(a_c), -math.cos(a_c), 0.04)).normalized()
                pts.append(p)
                nrms.append(nrm)
            ensure_outside_smooth(pts, nrms, min_clear=0.004 if tier_sub == 0 else 0.008, start_i=2, z_min=0.98)
            w0 = float(rng.uniform(0.022, 0.034)) if tier_sub == 0 else float(rng.uniform(0.016, 0.026))
            _append_card(
                verts, faces, uvs, pts, nrms,
                lambda t, w=w0: w * (0.18 + 0.84 * math.sin(min(1.0, t * 1.35) * math.pi * 0.78)) * (1.0 - 0.25 * t * t),
                cup_depth=0.0032,
                col_idx=(0 if k % 2 == 0 else 1) if tier_sub == 0 else (1 if k % 2 == 0 else 2),
                twist_rad=float(rng.uniform(-0.22, 0.22)),
            )

    # ---- Tier 3: 14 Delicate Wet Hair Tails spilling softly downward from the right side of her clenched fist
    # (narrow `col=3` gossamer strands ONLY — zero stiff blocky ribbons!)
    spill_origin = Vector((hx + 0.008, hy - 0.006, 1.204))
    for k in range(14):
        ang = 0.55 + (k / 13.0) * 1.35 + float(rng.uniform(-0.08, 0.08))
        arch_h = float(rng.uniform(0.010, 0.032))
        spill_len = float(rng.uniform(0.10, 0.22))
        ph = float(rng.uniform(0.0, math.tau))
        pts, nrms = [], []
        n_st = 9
        for i in range(n_st):
            t = i / (n_st - 1)
            dx = math.sin(ang) * (0.004 + 0.048 * (t ** 0.85)) + 0.005 * math.sin(t * 7.0 + ph) * t
            dy = -math.cos(ang) * (0.003 + 0.022 * t)
            dz = arch_h * math.sin(min(1.0, t * 1.9) * math.pi * 0.70) - spill_len * (t ** 1.65)
            pts.append(Vector((spill_origin.x + dx, spill_origin.y + dy, spill_origin.z + dz)))
            nrms.append(Vector((math.sin(ang), -math.cos(ang), 0.15)).normalized())
        w0 = float(rng.uniform(0.008, 0.015))
        _append_card(
            verts, faces, uvs, pts, nrms,
            lambda t, w=w0: w * (0.25 + 0.75 * math.sin(t * math.pi)) * (1.0 - 0.30 * t * t),
            cup_depth=0.0015,
            col_idx=3,
            twist_rad=float(rng.uniform(-0.24, 0.24)),
        )

    # ---- Tier 4A: 14 Fine Forehead & Temple Baby-Hair Wisps clinging organically along the hairline & outer cheeks
    # (strictly clear of both staring eyes, nose & bloody teeth!)
    forehead_azs = [-0.94, -0.82, -0.70, -0.54, -0.36, -0.16, 0.08, 0.26, 0.44, 0.58, 0.72, 0.84, 0.96, -1.02]
    for az in forehead_azs:
        is_center = abs(az) < 0.52
        length = float(rng.uniform(0.024, 0.048)) if is_center else float(rng.uniform(0.11, 0.24))
        ph = float(rng.uniform(0.0, math.tau))
        pts, nrms = [], []
        n_st = 8
        p_root, _ = smooth_dome_point(az, 0.78, r_scale=1.03, z_bottom=1.052)
        for i in range(n_st):
            t = i / (n_st - 1)
            z = p_root.z - length * t
            sweep = (0.16 if az > 0 else -0.16) * t if not is_center else 0.04 * math.sin(t * 5.0 + ph)
            a_c = az + sweep
            rad = 0.088 + 0.008 * t
            pts.append(Vector((hx + math.sin(a_c) * rad, hy - math.cos(a_c) * rad * 1.03, z)))
            nrms.append(Vector((math.sin(a_c), -math.cos(a_c), 0.08)).normalized())
        ensure_outside_smooth(pts, nrms, min_clear=0.004, start_i=0, z_min=0.98)
        w0 = float(rng.uniform(0.009, 0.015))
        _append_card(
            verts, faces, uvs, pts, nrms,
            lambda t, w=w0: w * (0.22 + 0.78 * math.sin(t * math.pi)) * (1.0 - 0.35 * t * t),
            cup_depth=0.0015,
            col_idx=3,
            twist_rad=float(rng.uniform(-0.18, 0.18)),
        )

    # ---- Tier 4B: 28 Outer Gossamer Monsoon Flyaways framing the entire left, right & jaw silhouette
    for k in range(28):
        side = -1.0 if (k % 2 == 0) else 1.0
        frac = (k // 2) / 13.0
        az = side * (0.76 + frac * 2.15) + float(rng.uniform(-0.06, 0.06))
        u_start = float(rng.uniform(0.52, 0.88))
        length_below = float(rng.uniform(0.20, 0.38))
        ph = float(rng.uniform(0.0, math.tau))
        w_amp = float(rng.uniform(0.008, 0.016))
        pts, nrms = [], []
        n_st = 11
        for i in range(n_st):
            t = i / (n_st - 1)
            if t < 0.22:
                uu = u_start + (1.0 - u_start) * (t / 0.22)
                p, nrm = smooth_dome_point(az, uu, r_scale=1.06, z_bottom=1.045)
            else:
                v = (t - 0.22) / 0.78
                a_c = az + 0.13 * math.sin(v * 8.5 + ph) * v
                rad = 0.100 + 0.020 * math.sin(v * math.pi * 0.65)
                z = 1.045 - v * length_below
                p = Vector((
                    hx + math.sin(a_c) * rad + w_amp * math.sin(v * 9.0 + ph) * v,
                    hy - math.cos(a_c) * rad * 0.96 + w_amp * 0.5 * math.cos(v * 8.0 + ph) * v,
                    z,
                ))
                nrm = Vector((math.sin(a_c), -math.cos(a_c), 0.0)).normalized()
            pts.append(p)
            nrms.append(nrm)
        w0 = float(rng.uniform(0.011, 0.019))
        _append_card(
            verts, faces, uvs, pts, nrms,
            lambda t, w=w0: w * (0.12 + 0.88 * math.sin(t * math.pi)) * (1.0 - 0.25 * t * t),
            cup_depth=0.002,
            col_idx=3 if (k % 3 != 0) else 2,
            twist_rad=float(rng.uniform(-0.30, 0.30)),
        )

    mesh = bpy.data.meshes.new("headless_hair_cards")
    mesh.from_pydata(verts, [], faces)
    uv_l = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            uv_l.data[li].uv = uvs[mesh.loops[li].vertex_index]
    mesh.materials.append(mat)
    mesh.update()

    obj = bpy.data.objects.new("headless_hair_cards", mesh)
    coll.objects.link(obj)
    return obj
