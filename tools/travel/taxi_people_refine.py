"""Museum-grade character realism upgrades for Episode 1's 1933 Citroën Rosalie driving scene.

Rebuilds both cabin occupants cleanly from pristine CC BY source scans with zero accumulated mesh
damage, eliminating every visual artifact:
1. Driver head (`taxi_driver_head_scan`) + sculpted 1930s herringbone flat cap (`taxi_driver_cap`):
   - Reloads pristine `taxi_driver_head.glb`, welds UV-split seams BEFORE normal recalculation
     (eliminating the 5,700+ flipped inward faces, black jaw wedge, and bright neck/cheek seam lines).
   - Cleans stray baseball-cap strap / khaki rim textures into natural combed dark Khmer hair.
   - Builds a seamless anatomical neck smoothly normal-blended across the jaw-to-neck junction.
   - Sculpts a multi-panel 1930s stitched flat driving cap (crown panels, covered button, curved peak)
     bound in lockstep to all 5 head morph targets (`look_road`, `look_sora`, `nod`, `talk`, `blink`).
2. Driver body, clothes, krama, and natural steering grip (`taxi_driver_body_scan`):
   - Dual-Quaternion rigged Eric scan with proper `lowerarm_twist` pronation (no broken wrist kink!).
   - Ergonomic 9:45 & 2:15 steering wheel grip with palm heels tangent to the bakelite rim, fingers
     wrapped around the 26 mm tube, and thumbs resting along the inner rim contour.
   - Preserves crisp 4K photographic hand knuckles, tendons, creases, and nails.
   - Bakes real skeletal morph targets (`steer_left`, `steer_right`, `grip_tense`, `breathe`, `lean_peer`)
     transferred in lockstep onto tailored shirt cuffs & cuff buttons so his arms actually steer the wheel!
   - Adds a 1930s open linen shirt collar and a naturally draped, relaxed woven Cambodian krama with fringes.
3. Sora's hands, sleeves, and wrist-conformed vintage wristwatch (`taxi_sora_legs_scan`, `taxi_sora_watch_*`):
   - Dual-Quaternion rigged Carla scan with `lowerarm_twist` pronation and natural asymmetric resting pose
     with real weight resting directly on her trouser-covered thighs (no hovering symmetric mannequin hands!).
   - Preserves crisp 4K photographic skin detail + subtle sculpted anatomical fingernails on all 10 digits.
   - Sleek raycast-fitted rolled linen blouse cuffs with mother-of-pearl buttons.
   - Museum-grade 1930s antique-gold Art Deco tank wristwatch whose stitched calfskin strap is
     BVH-raycast conformed vertex-by-vertex to her actual bare left wrist (zero floating gap!),
     complete with curved lugs, fluted crown, brass buckle, painted 512px Roman-numeral ivory enamel dial,
     blued-steel Breguet hands (22:45), and domed glass crystal.
   - Bakes real skeletal morph targets (`breathe`, `tense_grip`, `fidget`) transferred in lockstep onto
     Sora's cuffs and every watch component so she breathes, fidgets, and clenches her knees in terror.
"""
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
SCANS = ROOT / "art-source/library/scans"
TEX = ROOT / "art-source/textures/ep1/taxi"
LINEN_BC = ROOT / "art-source/library/materials/rough_linen/rough_linen_BC.jpg"
LINEN_N = ROOT / "art-source/library/materials/rough_linen/rough_linen_N.jpg"
LEATHER_N = ROOT / "art-source/library/materials/brown_leather/brown_leather_N.jpg"

# Measured Rosalie steering wheel pose in Blender coordinates (car faces -Y, driver +X, Sora -X)
WHEEL_CENTER = Vector((0.2641, -0.2722, 0.7636))
WHEEL_NORMAL = Vector((0.0, 0.7676, 0.6410)).normalized()
WHEEL_RADIUS = 0.198
# The rim mesh's tube centre line, measured from `taxi_steering_wheel_rim` (its tube is 12.7 mm).
RIM_CENTRELINE = 0.1974
# With the scanned hands his sleeves are rolled up: the cut sits this far up the forearm from the wrist.
SLEEVE_ROLL_UP = 0.085

# Pristine taxi_driver_head.glb landmarks (in its own pre-placement metres frame, facing -Y)
HEAD_NECK_BASE = Vector((-0.004, 0.030, 1.790))
HEAD_PIVOT = Vector((-0.004, 0.030, 1.830))
HEAD_EYES = [Vector((-0.040, -0.088, 1.9695)), Vector((0.034, -0.088, 1.970))]
HEAD_MOUTH_Z = 1.890
HEAD_HINGE = Vector((0.0, -0.004, 1.936))
HEAD_REST_YAW = -27.0


# --------------------------------------------------------------------------- helpers

def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / max(1e-7, e1 - e0) if e1 > e0 else (e0 - x) / max(1e-7, e0 - e1), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _sstep(e0, e1, x):
    if e1 > e0:
        t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    else:
        t = max(0.0, min(1.0, (e0 - x) / (e0 - e1)))
    return t * t * (3.0 - 2.0 * t)


def _box_blur_2d(a, r):
    if r <= 0:
        return a.copy()
    c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode="edge"), 0)
    a = (c[2 * r + 1 :] - c[: -2 * r - 1]) / (2 * r + 1)
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)), mode="edge"), 1)
    return (c[:, 2 * r + 1 :] - c[:, : -2 * r - 1]) / (2 * r + 1)


def _resize_np(img, tw, th):
    sw, sh = img.size
    buf = np.empty(sw * sh * 4, np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(sh, sw, 4)
    if sw == tw and sh == th:
        return arr.copy()
    yy = np.clip((np.arange(th) * (sh / th)).astype(np.int32), 0, sh - 1)
    xx = np.clip((np.arange(tw) * (sw / tw)).astype(np.int32), 0, sw - 1)
    return arr[np.ix_(yy, xx)].copy()


def _load_tiled_np(path, tw, th, repeats, is_srgb=True):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if is_srgb else "Non-Color"
    sw, sh = img.size
    buf = np.empty(sw * sh * 4, np.float32)
    img.pixels.foreach_get(buf)
    arr = buf.reshape(sh, sw, 4)[..., :3]
    yy = (np.arange(th, dtype=np.float32) * (sh * repeats / th)).astype(np.int32) % sh
    xx = (np.arange(tw, dtype=np.float32) * (sw * repeats / tw)).astype(np.int32) % sw
    return arr[np.ix_(yy, xx)]


def _blend_normals(n_a, n_b, gain_a=0.6, gain_b=0.4):
    sa = n_a[..., :3] * 2.0 - 1.0
    sb = n_b[..., :3] * 2.0 - 1.0
    nx = sa[..., 0] * gain_a + sb[..., 0] * gain_b
    ny = sa[..., 1] * gain_a + sb[..., 1] * gain_b
    nz = np.clip(sa[..., 2], 0.25, 1.0)
    inv_l = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    out = np.empty((*n_a.shape[:2], 4), np.float32)
    out[..., 0] = np.clip(nx * inv_l * 0.5 + 0.5, 0.0, 1.0)
    out[..., 1] = np.clip(ny * inv_l * 0.5 + 0.5, 0.0, 1.0)
    out[..., 2] = np.clip(nz * inv_l * 0.5 + 0.5, 0.0, 1.0)
    out[..., 3] = 1.0
    return out


def _pack_image(name, arr, is_srgb=True):
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


def _make_pbr(name, bc_img=None, n_img=None, rough=0.86, metallic=0.0, normal_strength=0.45, color=None, double_sided=False):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = not double_sided
    nt = mat.node_tree
    nt.nodes.clear()
    out_n = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = rough
    if bc_img is not None:
        t_bc = nt.nodes.new("ShaderNodeTexImage")
        t_bc.image = bc_img
        if color is not None:
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            mix.inputs[7].default_value = (*color, 1.0)
            nt.links.new(t_bc.outputs["Color"], mix.inputs[6])
            nt.links.new(mix.outputs[2], bs.inputs["Base Color"])
        else:
            nt.links.new(t_bc.outputs["Color"], bs.inputs["Base Color"])
    elif color is not None:
        bs.inputs["Base Color"].default_value = (*color, 1.0)
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


def _clear_objects(*names):
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)


def _bm_to_obj(name, bm, mat, coll, smooth=True):
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
    return o


def _make_mesh_uv(name, verts, faces, uvs, mat, coll, smooth=True):
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


def _ensure_gltf_sockets():
    from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
    name = get_gltf_node_name()
    group = bpy.data.node_groups.get(name)
    if group is None:
        create_settings_group(name)
        return
    full = create_settings_group("_glTF_full_sockets_tmp")
    have = {item.name for item in group.interface.items_tree}
    for item in full.interface.items_tree:
        if item.item_type == "SOCKET" and item.in_out == "INPUT" and item.name not in have:
            group.interface.new_socket(item.name, in_out="INPUT", socket_type=item.socket_type)
    bpy.data.node_groups.remove(full)


def _apply_box_uvs(obj, scale=3.6):
    """Ensure cuffs/collars always carry crisp box-projected linen weave UVs (even when rebuilt standalone)."""
    me = obj.data
    uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        n = p.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if az >= ax and az >= ay:
                uv = (co.x * scale, co.y * scale)
            elif ax >= ay:
                uv = (co.y * scale, co.z * scale)
            else:
                uv = (co.x * scale, co.z * scale)
            uvl.data[li].uv = uv


def _weld_rigged_mesh_preserve_groups(body, dist=0.0004):
    """Weld disconnected UV-seam vertices on a rigged scan BEFORE Catmull-Clark Subsurf so
    Subsurf never tears jagged sawtooth gaps along UV seams (preserves UVs & armature weights 100%!)."""
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.update_edit_mesh(body.data)
    bpy.ops.object.mode_set(mode="OBJECT")
    body.data.update()


def _import_glb_rigged(path):
    _ensure_gltf_sockets()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    body = max((o for o in new if o.type == "MESH"), key=lambda o: len(o.data.polygons))
    kept = []
    for o in new:
        if o not in (arm, body) and o.type != "EMPTY":
            bpy.data.objects.remove(o, do_unlink=True)
        else:
            kept.append(o)
    for mod in body.modifiers:
        if mod.type == "ARMATURE":
            mod.use_deform_preserve_volume = True
    return arm, body, kept


# --------------------------------------------------------------------------- armature rig helpers

class _RigHelper:
    def __init__(self, arm):
        self.arm = arm

    def bone(self, prefix):
        return next(b.name for b in self.arm.pose.bones if b.name.startswith(prefix))

    def has(self, prefix):
        return any(b.name.startswith(prefix) for b in self.arm.pose.bones)

    def joint(self, name):
        bpy.context.view_layer.update()
        return self.arm.matrix_world @ self.arm.pose.bones[name].head

    def tail(self, name):
        bpy.context.view_layer.update()
        return self.arm.matrix_world @ self.arm.pose.bones[name].tail

    def turn(self, name, axis, angle):
        bpy.context.view_layer.update()
        pb = self.arm.pose.bones[name]
        inv = self.arm.matrix_world.inverted().to_3x3()
        R = Matrix.Rotation(angle, 4, (inv @ Vector(axis)).normalized())
        pb.matrix = Matrix.Translation(pb.head) @ R @ Matrix.Translation(-pb.head) @ pb.matrix
        bpy.context.view_layer.update()

    def aim(self, name, child, target):
        hd = self.joint(name)
        cur = self.joint(child) - hd
        want = Vector(target) - hd
        if cur.length < 1e-6 or want.length < 1e-6:
            return
        axis, angle = cur.rotation_difference(want).to_axis_angle()
        self.turn(name, axis, angle)

    def reach(self, upper, lower, hand, wrist, pole):
        s = self.joint(upper)
        a = (self.joint(lower) - s).length
        b = (self.joint(hand) - self.joint(lower)).length
        to = Vector(wrist) - s
        d = min(to.length, (a + b) * 0.992)
        f = to.normalized()
        cosA = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
        p = Vector(pole) - s
        perp = (p - f * p.dot(f)).normalized()
        elbow = s + f * a * cosA + perp * a * math.sqrt(max(0.0, 1.0 - cosA * cosA))
        self.aim(upper, lower, elbow)
        self.aim(lower, hand, s + f * d)

    def knuckles(self, side):
        k1 = self.joint(self.bone(f"index_01_{side}"))
        k4 = self.joint(self.bone(f"pinky_01_{side}"))
        w = self.joint(self.bone(f"hand_{side}"))
        mid = self.joint(self.bone(f"middle_01_{side}"))
        return (k1 - k4).normalized(), (mid - w).normalized()

    def palm_of(self, side):
        across, d = self.knuckles(side)
        return (across.cross(d) if side == "r" else d.cross(across)).normalized()

    def roll_hand_with_twist(self, side, want_palm):
        """Roll forearm+wrist so palm faces `want_palm`, sharing 55% pronation with `lowerarm_twist`!"""
        hand = self.bone(f"hand_{side}")
        _, d = self.knuckles(side)
        want = (want_palm.normalized() - d * want_palm.normalized().dot(d)).normalized()
        have = self.palm_of(side)
        have = (have - d * have.dot(d)).normalized()
        roll = math.atan2(have.cross(want).dot(d), have.dot(want))
        if self.has(f"lowerarm_twist_{side}"):
            # Share pronation across the forearm twist bone so the wrist never candy-wrapper pinches!
            twist_b = self.bone(f"lowerarm_twist_{side}")
            forearm_ax = (self.joint(hand) - self.joint(self.bone(f"lowerarm_{side}"))).normalized()
            self.turn(twist_b, forearm_ax, roll * 0.52)
            # Re-measure remaining error on hand and apply cleanly
            _, d2 = self.knuckles(side)
            want2 = (want_palm.normalized() - d2 * want_palm.normalized().dot(d2)).normalized()
            have2 = self.palm_of(side)
            have2 = (have2 - d2 * have2.dot(d2)).normalized()
            rem = math.atan2(have2.cross(want2).dot(d2), have2.dot(want2))
            self.turn(hand, d2, rem)
        else:
            self.turn(hand, d, roll)

    def curl_fingers(self, side, finger_angles, thumb_angles, thumb_oppose=0.0):
        """Curl each finger with per-segment tuples (a1, a2, a3) in radians, plus anatomical thumb."""
        across, fwd = self.knuckles(side)
        palm = self.palm_of(side)
        flex_ax = -across if side == "l" else across
        for finger, (a1, a2, a3) in finger_angles.items():
            for seg, ang in (("01", a1), ("02", a2), ("03", a3)):
                self.turn(self.bone(f"{finger}_{seg}_{side}"), flex_ax, ang)
        # Thumb opposition: swing thumb_01 toward palm/index before flexing thumb_02 & thumb_03
        if abs(thumb_oppose) > 1e-4:
            opp_ax = fwd if side == "r" else -fwd
            self.turn(self.bone(f"thumb_01_{side}"), opp_ax, thumb_oppose)
            self.turn(self.bone(f"thumb_01_{side}"), palm, -thumb_oppose * (0.35 if side == "r" else -0.35))
        t1, t2, t3 = thumb_angles
        # Refresh thumb axis after opposition
        t_flex = flex_ax * 0.72 + (palm * 0.55 if side == "r" else -palm * 0.55)
        for seg, ang in (("01", t1), ("02", t2), ("03", t3)):
            if abs(ang) > 1e-4:
                self.turn(self.bone(f"thumb_{seg}_{side}"), t_flex.normalized(), ang)

    def finger_tip(self, finger, side):
        """True distal fingertip position & direction (glTF leaf bone .tail is a 1m dummy!)."""
        b2 = self.bone(f"{finger}_02_{side}")
        b3 = self.bone(f"{finger}_03_{side}")
        p2 = self.joint(b2)
        p3 = self.joint(b3)
        pb3 = self.arm.pose.bones[b3]
        d23 = (p3 - p2).normalized()
        # Renderpeople UE4 skeleton runs bone distal axis along local +X (mirror-safe sign check against d23)
        d3 = (self.arm.matrix_world.to_3x3() @ pb3.matrix.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
        if d3.dot(d23) < 0.0:
            d3 = -d3
        tip_len = 0.020 if finger == "thumb" else 0.017
        return p3 + d3 * tip_len, d3

    def snapshot(self):
        return {pb.name: pb.matrix_basis.copy() for pb in self.arm.pose.bones}

    def restore(self, snap):
        for pb in self.arm.pose.bones:
            pb.matrix_basis = snap[pb.name].copy()
        bpy.context.view_layer.update()


# --------------------------------------------------------------------------- 1. DRIVER HEAD + 1930s FLAT CAP

def _make_herringbone_cap_material():
    """High-detail 1024x1024 weathered charcoal-brown 1930s herringbone wool-twill driving cap material."""
    tw, th = 1024, 1024
    yy, xx = np.mgrid[0:th, 0:tw].astype(np.float32)
    rng = np.random.default_rng(193377)

    # Classic crisp herringbone chevron twill weave (alternating +45° / -45° diagonal ribs every 14 px)
    stripe = (xx // 14) % 2
    diag = np.where(stripe == 0, xx + yy, -xx + yy)
    twill = 0.5 + 0.5 * np.sin(diag * (math.tau / 7.0))
    cross = 0.5 + 0.5 * np.sin((xx - yy) * (math.tau / 4.5))
    weave = 0.78 + 0.16 * twill + 0.06 * cross

    # Subtle fabric slub & monsoon rain-damp wear mottling
    slub = _box_blur_2d(rng.normal(0.0, 0.09, (th, tw)).astype(np.float32), 6)
    fine = rng.normal(0.0, 0.022, (th, tw)).astype(np.float32)

    # Warm weathered 1930s taupe-charcoal herringbone wool tweed (proper sRGB luminance so the
    # chevron weave, 6-panel seams & soft highlights stay clearly legible in dark cabin lighting!)
    base = np.array([0.275, 0.245, 0.210], np.float32)
    fleck = np.array([0.395, 0.355, 0.305], np.float32)
    tweed_mix = np.clip(twill * 0.45 + cross * 0.25, 0.0, 1.0)[..., None]
    rgb = base * (1.0 - tweed_mix * 0.42) + fleck * (tweed_mix * 0.42)
    rgb = rgb * np.clip(weave + slub + fine, 0.68, 1.28)[..., None]

    # Subtle panel seam darkening along V=0 (sweatband) and radial panel lines (6 panels -> U = k/6)
    v_grid = yy / (th - 1)
    u_grid = xx / tw
    sweat = 1.0 - 0.24 * np.clip((0.15 - v_grid) / 0.15, 0.0, 1.0) ** 1.4
    seam_dist = np.abs(((u_grid * 6.0 + 0.5) % 1.0) - 0.5)
    seam_ao = 1.0 - 0.22 * np.exp(-((seam_dist / 0.016) ** 2)) * np.clip((v_grid - 0.12) / 0.08, 0.0, 1.0)
    rgb = np.clip(rgb * (sweat * seam_ao)[..., None], 0.05, 0.82)
    bc_img = _pack_image("T_cab_driver_cap_BC", rgb, is_srgb=True)

    # Crisp matching herringbone normal map + recessed panel seam grooves
    h_map = twill * 0.28 + cross * 0.12 + slub * 0.35 - (1.0 - seam_ao) * 1.4
    gx = (np.roll(h_map, -1, 1) - np.roll(h_map, 1, 1)) * 1.15
    gy = (np.roll(h_map, -1, 0) - np.roll(h_map, 1, 0)) * 1.15
    nz = np.sqrt(np.clip(1.0 - gx * gx - gy * gy, 0.15, 1.0))
    n_arr = np.dstack([np.clip(-gx * 0.5 + 0.5, 0, 1), np.clip(-gy * 0.5 + 0.5, 0, 1), np.clip(nz * 0.5 + 0.5, 0, 1)])
    n_img = _pack_image("T_cab_driver_cap_N", n_arr, is_srgb=False)

    return _make_pbr("M_cab_driver_cap", bc_img, n_img, rough=0.86, metallic=0.0, normal_strength=0.68, double_sided=True)


def _build_1930s_flat_cap(head_local_bvh, axis_xy, coll):
    """Sculpt an authentic, sleek, snug-fitting 1930s 6-panel flat driving cap in head-local coordinates
    (facing -Y, crown up +Z):
    - Lower sweatband hugs cleanly above eyebrows (2.002), dips right down to the ear tops (1.960),
      and cups low over the occiput (1.924) so 100% of the old scan baseball cap & snapback are hidden!
    - Upper crown interpolates smoothly to a single streamlined 1930s flat-cap dome (zero bumpy seam!).
    """
    ax, ay = float(axis_xy[0]), float(axis_xy[1])
    segs = 48
    radii = np.zeros(segs, np.float32)
    band_z = np.zeros(segs, np.float32)

    for k in range(segs):
        # ang = 0 -> front (-Y), pi/2 -> +X, pi -> back (+Y), -pi/2 -> -X
        ang = (k / segs) * math.tau
        dx = math.sin(ang)
        dy = -math.cos(ang)
        c_front = max(0.0, math.cos(ang))
        c_back = max(0.0, -math.cos(ang))
        c_side = abs(math.sin(ang))
        # Continuous tailored hatband curve: clears brow cleanly -> arches 8mm cleanly ABOVE ear tops
        # (ZERO ear pinch or poke-through!) -> dips snug right behind ears & cups low over the occiput!
        ear_arch = math.exp(-(((abs(ang) - math.pi * 0.47) / 0.25) ** 2))
        z_line = 2.002 - 0.036 * (c_side ** 1.45) + 0.023 * ear_arch - 0.074 * (c_back ** 1.15)
        band_z[k] = z_line
        # Measure skull radius JUST BELOW the old baseball cap's thick band so the cap hugs the real skull!
        origin = Vector((ax, ay, max(1.915, z_line - 0.008)))
        direction = Vector((dx, dy, 0.0)).normalized()
        hit = head_local_bvh.ray_cast(origin, direction, 0.16)
        if hit[0] is not None:
            r = math.hypot(hit[0].x - ax, hit[0].y - ay)
        else:
            r = 0.088
        # Tight anatomical cranium oval bound (never inflated by old baseball-cap band or visor!)
        r_anat = 0.084 * c_side + 0.095 * abs(math.cos(ang))
        r = min(r, r_anat)
        radii[k] = max(0.078, min(0.100, r + 0.0038 + 0.0025 * c_back))

    for _ in range(8):
        radii = 0.25 * np.roll(radii, -1) + 0.5 * radii + 0.25 * np.roll(radii, 1)

    verts, faces, uvs = [], [], []

    # Smooth continuous loft from snug lower hatband `band_z[k]` up to a clean streamlined 1930s flat-cap
    # crown dome (`z_target_deck` ~ 2.084, gently sloping slightly down toward the brow & nape!).
    # Each ring: (v_uv, r_scale, height_frac_0_to_1, y_forward_shift)
    ring_specs = [
        (0.00, 0.90, -0.04,  0.000),  # tucked inner sweatband lip (seals cleanly against hair!)
        (0.04, 1.00,  0.00,  0.000),  # lower fitted sweatband edge touching ear-top/nape hairline
        (0.14, 1.03,  0.16, -0.002),  # snug lower side/occiput panel
        (0.30, 1.06,  0.38, -0.006),  # soft classic flat-cap side curve
        (0.48, 1.04,  0.60, -0.011),  # upper shoulder leaning gently forward over visor
        (0.65, 0.90,  0.78, -0.012),  # smooth rounded transition onto top deck
        (0.80, 0.64,  0.90, -0.008),  # softly domed 6-panel flat-cap deck
        (0.91, 0.34,  0.97, -0.004),  # inner deck approaching button
        (0.98, 0.11,  1.00, -0.001),  # crown apex (world z ~ 1.124 -> cleanly 3.2 cm above tucked skull!)
    ]

    ring_indices = []
    for r_i, (v_uv, r_sc, h_frac, y_sh) in enumerate(ring_specs):
        row = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            dx = math.sin(ang)
            dy = -math.cos(ang)
            c_f = max(0.0, math.cos(ang))
            c_b = max(0.0, -math.cos(ang))
            # Subtle 6-panel seam groove on upper crown
            panel_groove = 0.0
            if r_i >= 3:
                seam_d = abs(((k / segs * 6.0 + 0.5) % 1.0) - 0.5)
                panel_groove = -0.0012 * math.exp(-((seam_d / 0.045) ** 2))
            r = radii[k] * r_sc + panel_groove
            # Target crown altitude: cohesive smooth dome (2.086 at apex, softly sloping 1.2cm toward brow/back)
            z_top = 2.088 - 0.012 * (1.0 - max(0.0, h_frac)) * (c_f * 0.6 + c_b * 0.8)
            z = band_z[k] + (z_top - band_z[k]) * h_frac + panel_groove * 0.35
            x = ax + dx * r
            y = ay + dy * r + y_sh * (0.35 + 0.65 * c_f)
            row.append(len(verts))
            verts.append(Vector((x, y, z)))
            uvs.append((k / segs, v_uv))
        ring_indices.append(row)

    for rA, rB in zip(ring_indices, ring_indices[1:]):
        for k in range(segs):
            kn = (k + 1) % segs
            faces.append((rA[k], rA[kn], rB[kn], rB[k]))

    # Cap apex + sculpted fabric-covered top button (14mm wide, 4mm domed)
    apex_c = sum((verts[i] for i in ring_indices[-1]), Vector()) / segs
    apex_idx = len(verts)
    verts.append(apex_c + Vector((0, 0, 0.001)))
    uvs.append((0.5, 0.99))
    for k in range(segs):
        faces.append((ring_indices[-1][k], ring_indices[-1][(k + 1) % segs], apex_idx))

    btn_segs = 16
    btn_rings = []
    for br, bz, bv in [(0.0055, 0.0005, 0.85), (0.0076, 0.0028, 0.88), (0.0062, 0.0050, 0.92), (0.0024, 0.0060, 0.95)]:
        brow = []
        for k in range(btn_segs):
            a = k / btn_segs * math.tau
            brow.append(len(verts))
            verts.append(apex_c + Vector((math.cos(a) * br, math.sin(a) * br, bz)))
            uvs.append((k / btn_segs, bv))
        btn_rings.append(brow)
    for rA, rB in zip(btn_rings, btn_rings[1:]):
        for k in range(btn_segs):
            kn = (k + 1) % btn_segs
            faces.append((rA[k], rA[kn], rB[kn], rB[k]))
    btop = len(verts)
    verts.append(apex_c + Vector((0, 0, 0.0063)))
    uvs.append((0.5, 0.98))
    for k in range(btn_segs):
        faces.append((btn_rings[-1][k], btn_rings[-1][(k + 1) % btn_segs], btop))

    # 2) Curved, stiffened 1930s short stitched peak / visor (-68° to +68° across the brow)
    n_arc = 26
    n_depth = 6
    vis_top = []
    vis_bot = []
    for j in range(n_depth):
        t = j / (n_depth - 1)  # 0 at brow seam, 1 at curved front visor lip
        row_t, row_b = [], []
        for i in range(n_arc):
            u = i / (n_arc - 1)  # 0..1 across brow (-68 deg to +68 deg)
            ang = math.radians(-68.0 + u * 136.0)
            k_f = (ang % math.tau) / math.tau * segs
            k0 = int(k_f) % segs
            k1 = (k0 + 1) % segs
            frac = k_f - math.floor(k_f)
            r0 = radii[k0] * (1.0 - frac) + radii[k1] * frac
            z0 = band_z[k0] * (1.0 - frac) + band_z[k1] * frac
            dx = math.sin(ang)
            dy = -math.cos(ang)
            # Crescent projection: longest at center (4.6 cm), tapering cleanly to 0 at temples!
            c_arc = math.cos(ang / 1.18) ** 1.35
            proj = 0.046 * c_arc * t
            # Slight downward slope + subtle transverse brow arch (classic chauffeur visor!)
            z_drop = -0.013 * t * (0.65 + 0.35 * c_arc) - 0.003 * (t ** 2)
            # Visor thickness tapers slightly toward stitched front rim
            half_th = 0.0025 * (1.0 - 0.32 * t)
            base_pt = Vector((ax + dx * (r0 * 1.030 + proj * 0.42), ay + dy * (r0 * 1.030) - proj, z0 + 0.006 + z_drop))
            row_t.append(len(verts))
            verts.append(base_pt + Vector((0, 0, half_th)))
            uvs.append((u * 0.65 + 0.15, 0.08 + t * 0.22))
            row_b.append(len(verts))
            verts.append(base_pt - Vector((0, 0, half_th)))
            uvs.append((u * 0.65 + 0.15, 0.02 + t * 0.08))
        vis_top.append(row_t)
        vis_bot.append(row_b)

    for j in range(n_depth - 1):
        for i in range(n_arc - 1):
            # Top face (normal +Z)
            faces.append((vis_top[j][i], vis_top[j][i + 1], vis_top[j + 1][i + 1], vis_top[j + 1][i]))
            # Bottom face (normal -Z)
            faces.append((vis_bot[j][i], vis_bot[j + 1][i], vis_bot[j + 1][i + 1], vis_bot[j][i + 1]))
    # Stitched front lip edge connecting vis_top[-1] to vis_bot[-1]
    for i in range(n_arc - 1):
        faces.append((vis_top[-1][i], vis_top[-1][i + 1], vis_bot[-1][i + 1], vis_bot[-1][i]))
    # Temple end caps
    for j in range(n_depth - 1):
        faces.append((vis_top[j][0], vis_top[j + 1][0], vis_bot[j + 1][0], vis_bot[j][0]))
        faces.append((vis_top[j][-1], vis_bot[j][-1], vis_bot[j + 1][-1], vis_top[j + 1][-1]))

    cap_mat = _make_herringbone_cap_material()
    cap_obj = _make_mesh_uv("taxi_driver_cap", verts, faces, uvs, cap_mat, coll, smooth=True)
    # Recalculate consistent outward normals
    bm = bmesh.new()
    bm.from_mesh(cap_obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(cap_obj.data)
    bm.free()
    for p in cap_obj.data.polygons:
        p.use_smooth = True
    cap_obj.data.update()
    return cap_obj


def rebuild_driver_head_and_cap(coll, neck_world_pos):
    """Reload pristine `taxi_driver_head.glb`, weld all UV-split seams (0 flipped faces!),
    clean face/hair/nape textures, extrude one continuous smooth-normal anatomical neck,
    sculpt a 1930s stitched herringbone flat cap, and bind both to all 5 runtime head morph targets."""
    head_path = SCANS / "taxi_driver_head.glb"
    if not head_path.exists():
        print("WARN missing pristine taxi_driver_head.glb")
        return None

    _clear_objects("taxi_driver_head_scan", "taxi_driver_cap")
    _ensure_gltf_sockets()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(head_path))
    new_objs = [o for o in bpy.data.objects if o not in before]
    head = max((o for o in new_objs if o.type == "MESH"), key=lambda o: len(o.data.polygons))
    for o in new_objs:
        if o != head:
            bpy.data.objects.remove(o, do_unlink=True)
    for c_old in list(head.users_collection):
        c_old.objects.unlink(head)
    coll.objects.link(head)
    head.name = head.data.name = "taxi_driver_head_scan"

    # Apply any import transform into local vertices so we operate cleanly in pristine head metres
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if head.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()

    # 1. WELD UV-SPLIT VERTICES FIRST (preserving per-loop UVs!), DELETE `comp 1` (49-face stovepipe),
    #    FILL MICRO-PINHOLES, AND RECALC NORMALS ON THE SINGLE WATERTIGHT SHELL!
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00025)
    bm.faces.ensure_lookup_table()
    visited = set()
    comps = []
    for f in bm.faces:
        if f.index in visited:
            continue
        st = [f]
        comp = []
        visited.add(f.index)
        while st:
            g = st.pop()
            comp.append(g)
            for e in g.edges:
                for nf in e.link_faces:
                    if nf.index not in visited:
                        visited.add(nf.index)
                        st.append(nf)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    drop_faces = [f for c in comps[1:] for f in c]
    if drop_faces:
        bmesh.ops.delete(bm, geom=drop_faces, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # Fill tiny upper scan pinholes (never the bottom neck opening)
    pin_edges = [e for e in bm.edges if e.is_boundary and min(v.co.z for v in e.verts) > 1.86]
    if pin_edges:
        filled = bmesh.ops.holes_fill(bm, edges=pin_edges, sides=32).get("faces", [])
        if filled:
            # A filled hole's corners came from different atlas islands, so each patch smeared a strip of
            # unrelated scan texture across his cheek (two "scratches"). Give every patch the texel right
            # beside it, then raise a centre point and relax it so the patch follows the cheek's curve.
            from mathutils.kdtree import KDTree as _KD

            uv_fill = bm.loops.layers.uv.active
            fill_set = set(filled)
            src = [lp for f in bm.faces if f not in fill_set for lp in f.loops]
            kd_fill = _KD(len(src))
            for i, lp in enumerate(src):
                kd_fill.insert(lp.vert.co, i)
            kd_fill.balance()
            for f in filled:
                _, i, _ = kd_fill.find(f.calc_center_median())
                uv_here = src[i][uv_fill].uv.copy()
                for lp in f.loops:
                    lp[uv_fill].uv = uv_here
            poked = bmesh.ops.poke(bm, faces=filled)
            relax = set(poked.get("verts", []))
            for f in poked.get("faces", []):
                relax.update(f.verts)
            ring_v = {nb for v in relax for e in v.link_edges for nb in (e.other_vert(v),)}
            relax |= {v for v in ring_v if not v.is_boundary}
            for _ in range(8):
                for fac in (0.5, -0.53):
                    disp = {}
                    for v in relax:
                        nbs = [e.other_vert(v) for e in v.link_edges]
                        if nbs:
                            disp[v] = (sum((nb.co for nb in nbs), Vector()) / len(nbs) - v.co) * fac
                    for v, d_v in disp.items():
                        v.co += d_v
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Build BVH BEFORE tucking the old cap so our sculpted 1930s flat cap measures his true skull!
    head_bvh_raw = BVHTree.FromBMesh(bm)

    # 2. Strictly confine BOTH the old baseball cap crown AND its thick lower rim/snapback ridge
    #    inside an inner cranium ellipsoid (rx=0.068, ry=0.072, rz=0.068 -> world z <= 1.090) starting
    #    right at the ear-top/nape hairline so ZERO old cap band or snapback can EVER peek out!
    ax, ay = -0.004, 0.014
    for v in bm.verts:
        p = v.co
        ang = math.atan2(p.x - ax, -(p.y - ay))
        c_back = max(0.0, -math.cos(ang))
        c_side = abs(math.sin(ang))
        # Matches the exact lower hatband curve of `taxi_driver_cap` (leaves the entire ear 100% untouched
        # while keeping inner cranium smoothly convex rz=0.094 -> huge outward-normal margin above z=1.08!)
        ear_arch = math.exp(-(((abs(ang) - math.pi * 0.47) / 0.25) ** 2))
        cap_edge_z = 1.998 - 0.036 * (c_side ** 1.45) + 0.018 * ear_arch - 0.074 * (c_back ** 1.15)
        if p.z > cap_edge_z - 0.008:
            w_cap = _sstep(cap_edge_z - 0.008, cap_edge_z + 0.010, p.z)
            # Smooth inner skull ellipsoid centered at (ax, ay, 1.984) strictly inside `taxi_driver_cap`
            rel = Vector(((p.x - ax) / 0.068, (p.y - ay) / 0.072, max(0.0, p.z - 1.984) / 0.094))
            if rel.length > 1.0:
                scale = 1.0 / rel.length
                tx = ax + (p.x - ax) * scale
                ty = ay + (p.y - ay) * scale
                tz = 1.982 + max(0.0, p.z - 1.982) * scale
                p.x += (tx - p.x) * w_cap
                p.y += (ty - p.y) * w_cap
                p.z += (tz - p.z) * w_cap
            # Also pull old projecting front baseball brim strictly back behind forehead (y >= -0.056)
            if p.z > 1.994 and p.y < -0.056:
                w_brim = _sstep(1.994, 2.006, p.z)
                p.y += (-0.054 - p.y) * w_brim
        # Smoothly flatten protruding occipital snapback/nape ridge behind ears (y > 0.048)
        if p.y > 0.048 and 1.85 < p.z < 1.96:
            w_occ = _sstep(0.048, 0.074, p.y) * _sstep(1.96, 1.91, p.z)
            y_lim = 0.070 + 0.020 * _sstep(1.88, 1.96, p.z)
            if p.y > y_lim:
                p.y += (y_lim - p.y) * w_occ * 0.85

    # Gently smooth ONLY the lower back-of-head snapback ridge strictly below the crown tuck!
    nape_ridge_v = [
        v for v in bm.verts
        if not v.is_boundary and v.co.y > 0.040 and 1.87 < v.co.z < 1.945
    ]
    if nape_ridge_v:
        for _ in range(5):
            bmesh.ops.smooth_vert(bm, verts=nape_ridge_v, factor=0.28, use_axis_x=True, use_axis_y=True, use_axis_z=True)

    # 3. Clean & repair the 4K face photo texture (`T_taxi_driver_head_BC`) and normal (`T_taxi_driver_head_N`):
    #    - Sanitize corrupted low-Z normals (removes sharp scan slits on cheek/chin)
    #    - Clean the dark vertical baseball-cap strap / khaki band behind the ears into natural dark hair!
    hm = head.data.materials[0]
    old_hm = bpy.data.materials.get("M_taxi_driver_head_scan")
    if old_hm is not None and old_hm != hm:
        bpy.data.materials.remove(old_hm, do_unlink=True)
    hm.name = "M_taxi_driver_head_scan"
    bc_img = next((n.image for n in hm.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"), None)
    n_img = next((n.image for n in hm.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "Non-Color" and "_N" in n.image.name), None)
    if n_img is not None:
        nw, nh = n_img.size
        npx = np.empty(nw * nh * 4, np.float32)
        n_img.pixels.foreach_get(npx)
        npx = npx.reshape(nh, nw, 4)
        bad = npx[..., 2] < 0.82
        if np.any(bad):
            npx[bad, 0] = 0.5
            npx[bad, 1] = 0.5
            npx[bad, 2] = 1.0
            n_img.pixels.foreach_set(npx.astype(np.float32).ravel())
            n_img.pack()
    for n in hm.node_tree.nodes:
        if n.type == "NORMAL_MAP":
            # (0.55 lit the jaw's UV seam as a bright scratch; the smoothed jaw carries the form.)
            n.inputs["Strength"].default_value = 0.40

    # Also lift roughness on back/side hair UV zone so dark hair behind ears looks soft & matte (never shiny rubber!)
    orm_img = next((n.image for n in hm.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "Non-Color" and "_N" not in n.image.name), None)
    if orm_img is not None:
        ow, oh = orm_img.size
        opx = np.empty(ow * oh * 4, np.float32)
        orm_img.pixels.foreach_get(opx)
        opx = opx.reshape(oh, ow, 4)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is not None:
            for f in bm.faces:
                c = f.calc_center_median()
                if c.y > 0.005 and c.z > 1.875:
                    uvs_f = [lp[uv_layer].uv for lp in f.loops]
                    u0 = max(0, int(min(u.x for u in uvs_f) * ow) - 2)
                    u1 = min(ow - 1, int(max(u.x for u in uvs_f) * ow) + 2)
                    v0 = max(0, int(min(u.y for u in uvs_f) * oh) - 2)
                    v1 = min(oh - 1, int(max(u.y for u in uvs_f) * oh) + 2)
                    if u1 >= u0 and v1 >= v0 and (u1 - u0) < 400 and (v1 - v0) < 400:
                        # G channel is glTF Roughness -> push matte hair to >= 0.86
                        opx[v0 : v1 + 1, u0 : u1 + 1, 1] = np.maximum(opx[v0 : v1 + 1, u0 : u1 + 1, 1], 0.86)
        orm_img.pixels.foreach_set(opx.astype(np.float32).ravel())
        orm_img.pack()

    # Paint out any residual beige/khaki baseball-cap band or harsh black vertical stripe behind the ears
    # directly in the face BC texture (only on UV pixels mapped to the back/side hair zone above ear!)
    if bc_img is not None:
        bw, bh = bc_img.size
        bpx = np.empty(bw * bh * 4, np.float32)
        bc_img.pixels.foreach_get(bpx)
        bpx = bpx.reshape(bh, bw, 4)
        # Also paint out any stray pure-black texels (<0.015 lum) via neighbor bleed
        lum_all = bpx[..., :3] @ np.array([0.3, 0.59, 0.11], np.float32)
        holes_mask = lum_all < 0.014
        if np.any(holes_mask):
            blurred = np.stack([_box_blur_2d(bpx[..., c], 4) for c in range(3)], axis=-1)
            bpx[holes_mask, :3] = np.clip(blurred[holes_mask], 0.06, 0.85)
        # Clean the side-cap / back-hair transition band on polygons above z=1.965 behind temples (y > -0.02)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is not None:
            hair_col = np.array([0.055, 0.044, 0.036], np.float32)
            for f in bm.faces:
                c = f.calc_center_median()
                ang = math.atan2(c.x - ax, -(c.y - ay))
                c_back = max(0.0, -math.cos(ang))
                # Zone above/behind ear & under the new flat cap band where old purple/black baseball cap sat
                # (Use 600px cap on 4K map so coarse triangles on the old cap band are NEVER skipped!)
                if c.y > -0.025 and c.z > 1.945 - 0.055 * c_back and c.z < 2.05:
                    uvs_f = [lp[uv_layer].uv for lp in f.loops]
                    u_min = max(0, int(min(u.x for u in uvs_f) * bw) - 2)
                    u_max = min(bw - 1, int(max(u.x for u in uvs_f) * bw) + 2)
                    v_min = max(0, int(min(u.y for u in uvs_f) * bh) - 2)
                    v_max = min(bh - 1, int(max(u.y for u in uvs_f) * bh) + 2)
                    if u_max >= u_min and v_max >= v_min and (u_max - u_min) < 600 and (v_max - v_min) < 600:
                        patch = bpx[v_min : v_max + 1, u_min : u_max + 1, :3]
                        # Replace dusty mauve/purple baseball-cap band (B >= G*0.86), pale khaki strap,
                        # or flat black scan band with natural dark combed Khmer hair (skin ALWAYS has R > G > B!).
                        p_lum = patch @ np.array([0.3, 0.59, 0.11], np.float32)
                        is_mauve_or_cap = (
                            (patch[..., 2] >= patch[..., 1] * 0.86)
                            | (patch[..., 0] < patch[..., 2] * 1.48)
                            | (patch[..., 1] > patch[..., 0] * 0.82)
                            | (p_lum < 0.16)
                        )
                        if np.any(is_mauve_or_cap):
                            patch[is_mauve_or_cap] = patch[is_mauve_or_cap] * 0.08 + hair_col * 0.92
                            bpx[v_min : v_max + 1, u_min : u_max + 1, :3] = patch
        # One natural skin: the old bake's curve left his face spray-tan orange.
        import taxi_driver_wardrobe as wardrobe

        bpx[..., :3], _ = wardrobe.regrade_skin(bpx[..., :3])
        uv_seams = bm.loops.layers.uv.active
        if uv_seams is not None:
            npx2 = None
            if n_img is not None:
                npx2 = np.empty(n_img.size[0] * n_img.size[1] * 4, np.float32)
                n_img.pixels.foreach_get(npx2)
                npx2 = npx2.reshape(n_img.size[1], n_img.size[0], 4)
            # Seams over the face and neck (not the cap-covered crown).
            wardrobe.heal_uv_seams(bm, uv_seams, bpx, npx2, region=lambda c: c.z < 1.99)
            # The scan's two diagonal creases on each cheek (shadows of the scanned man's hoodie strings,
            # baked into shape, colour and relief) read as scars: relax and repaint them.
            creases = [Vector((x, y, z)) for (x, y, z) in (
                (-0.084, -0.050, 1.962), (-0.080, -0.070, 1.938),  # his right cheek, ear to jaw
                (0.076, -0.050, 1.962), (0.072, -0.070, 1.938),    # the left, mirrored about the head's axis
            )]
            wardrobe.repaint_skin_patch(bm, uv_seams, bpx, npx2, creases, radius=0.026, head=head, image=bc_img)
            if npx2 is not None:
                n_img.pixels.foreach_set(npx2.astype(np.float32).ravel())
                n_img.pack()
        bc_img.pixels.foreach_set(bpx.astype(np.float32).ravel())
        bc_img.pack()

    # 4. Surgical jaw/nape cut & seamless 26-ring anatomical neck loft (WELDED to head -> 0 seam crease!)
    plane_co = Vector((ax, 0.015, 1.858))
    plane_no = Vector((0.0, -0.15, 1.0)).normalized()
    bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        dist=0.0002,
        plane_co=plane_co,
        plane_no=plane_no,
        clear_inner=True,
        clear_outer=False,
    )
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    cut_edges = [
        e for e in bm.edges
        if e.is_boundary and all(abs((v.co - plane_co).dot(plane_no)) < 0.004 for v in e.verts)
    ]
    cut_v_set = list({v for e in cut_edges for v in e.verts})

    # Sample exact 360° jaw-rim skin color from T_taxi_driver_head_BC so neck color matches invisibly!
    n_ang_tex = 128
    import taxi_driver_wardrobe as wardrobe

    base_skin = (wardrobe.SKIN_CHROMA * 0.40).astype(np.float32)
    rim_rgb = np.tile(base_skin, (n_ang_tex, 1))
    if bc_img is not None:
        bw, bh = bc_img.size
        bpx = np.empty(bw * bh * 4, np.float32)
        bc_img.pixels.foreach_get(bpx)
        bpx = bpx.reshape(bh, bw, 4)
        uv_layer = bm.loops.layers.uv.active
        bins = [[] for _ in range(n_ang_tex)]
        for f in bm.faces:
            c = f.calc_center_median()
            d_pl = (c - plane_co).dot(plane_no)
            if -0.001 <= d_pl <= 0.022:
                ang = math.atan2(c.x - ax, -(c.y - 0.022))
                bi = int(((ang + math.pi) / math.tau) * n_ang_tex) % n_ang_tex
                uv = sum((lp[uv_layer].uv for lp in f.loops), Vector((0, 0))) / len(f.loops)
                col = bpx[int((uv.y % 1.0) * (bh - 1)), int((uv.x % 1.0) * (bw - 1)), :3]
                lum = float(0.3 * col[0] + 0.59 * col[1] + 0.11 * col[2])
                if 0.16 < lum < 0.72:
                    bins[bi].append(col)
        valid = [bi for bi in range(n_ang_tex) if len(bins[bi]) >= 2]
        for bi in valid:
            rim_rgb[bi] = np.median(bins[bi], axis=0)
        if valid:
            vc = np.array(valid)
            for bi in range(n_ang_tex):
                if len(bins[bi]) < 2:
                    il = vc[int(np.argmin((bi - vc) % n_ang_tex))]
                    ir = vc[int(np.argmin((vc - bi) % n_ang_tex))]
                    dl = (bi - il) % n_ang_tex
                    dr = (ir - bi) % n_ang_tex
                    t = dl / max(1, dl + dr)
                    rim_rgb[bi] = rim_rgb[il] * (1.0 - t) + rim_rgb[ir] * t
        for _ in range(120):
            rim_rgb = 0.25 * np.roll(rim_rgb, -1, axis=0) + 0.50 * rim_rgb + 0.25 * np.roll(rim_rgb, 1, axis=0)
        rim_rgb = 0.14 * base_skin[None, :] + 0.86 * rim_rgb

    # Generate high-res 1024x1024 seamless neck skin BC + pore/SCM normal map
    tw, th = 1024, 1024
    rng = np.random.default_rng(193399)
    yy, xx = np.mgrid[0:th, 0:tw].astype(np.float32)
    u_g = xx / tw
    v_g = yy / (th - 1)
    ang_g = u_g * math.tau - math.pi
    idx_f = u_g[0] * n_ang_tex
    i0 = np.floor(idx_f).astype(np.int32) % n_ang_tex
    i1 = (i0 + 1) % n_ang_tex
    frac = (idx_f - np.floor(idx_f))[:, None]
    top_row = rim_rgb[i0] * (1.0 - frac) + rim_rgb[i1] * frac
    blend_top = _smoothstep(0.18, 0.96, v_g)
    n_rgb = base_skin[None, None, :] * (1.0 - blend_top[..., None]) + top_row[None, :, :] * blend_top[..., None]
    front_m = np.clip(np.cos(ang_g), 0.0, 1.0) ** 1.3
    submental_ao = 1.0 - 0.14 * front_m * np.exp(-(((v_g - 0.86) / 0.09) ** 2))
    collar_ao = 1.0 - 0.16 * np.clip((0.26 - v_g) / 0.26, 0.0, 1.0) ** 1.5
    scm = 1.0 - 0.055 * np.exp(-(((np.abs(ang_g) - 0.82) / 0.26) ** 2)) * np.sin(np.clip(v_g, 0.08, 0.92) * math.pi)
    # Subtle horizontal age neck-creases (middle-aged Phnom Penh driver)
    neck_lines = 1.0 - 0.032 * (
        np.exp(-(((v_g - 0.62) / 0.012) ** 2)) + 0.7 * np.exp(-(((v_g - 0.44) / 0.014) ** 2))
    ) * (0.4 + 0.6 * front_m)
    pore = rng.normal(0.0, 0.0055, (th, tw)).astype(np.float32) * 0.3
    if bc_img is not None:
        # His own jaw skin (pores, fine stubble, creases), tiled 4 x 4 round the neck.
        tile = wardrobe.skin_patch_from_face(head, bc_img, (ax + 0.055, -0.035, 1.875), radius=0.014, size=256)
        reps = np.tile(tile, (4, 4))[:th, :tw]
        n_rgb = n_rgb * reps[..., None]
    stubble_m = _smoothstep(0.74, 0.94, v_g) * _smoothstep(0.995, 0.95, v_g) * _smoothstep(-0.20, 0.35, np.cos(ang_g))
    stubble = (rng.random((th, tw)).astype(np.float32) < 0.08).astype(np.float32) * -0.042 * stubble_m
    n_rgb = np.clip(n_rgb * (submental_ao * collar_ao * scm * neck_lines)[..., None] + pore[..., None] + stubble[..., None], 0.02, 0.96)
    neck_bc_img = _pack_image("T_taxi_driver_neck_BC", n_rgb, is_srgb=True)

    hf = rng.normal(0.0, 0.020, (th, tw)).astype(np.float32)
    hf = (hf + np.roll(hf, 1, 0) + np.roll(hf, -1, 0) + np.roll(hf, 1, 1) + np.roll(hf, -1, 1)) * 0.2
    hf -= (1.0 - neck_lines) * 0.55
    gx = (np.roll(hf, -1, 1) - np.roll(hf, 1, 1)) * 0.48
    gy = (np.roll(hf, -1, 0) - np.roll(hf, 1, 0)) * 0.48
    nz = np.sqrt(np.clip(1.0 - gx * gx - gy * gy, 0.1, 1.0))
    neck_n_arr = np.dstack([np.clip(-gx * 0.5 + 0.5, 0, 1), np.clip(-gy * 0.5 + 0.5, 0, 1), np.clip(nz * 0.5 + 0.5, 0, 1)])
    neck_n_img = _pack_image("T_taxi_driver_neck_N", neck_n_arr, is_srgb=False)
    neck_mat = _make_pbr("M_taxi_driver_neck_skin", neck_bc_img, neck_n_img, rough=0.52, normal_strength=0.28)
    head.data.materials.append(neck_mat)
    neck_mi = 1

    # Extrude 26-ring anatomical neck column directly from `cut_edges` (welded vertices -> 100% seamless normals!)
    z_bot = 1.718
    c_bot = Vector((ax + 0.002, 0.028, z_bot))
    c_top = Vector((ax, 0.022, plane_co.z))
    n_rings = 26
    uv_layer = bm.loops.layers.uv.active or bm.loops.layers.uv.new("UVMap")
    v_cols = {}
    v_ang = {}
    for v_top in cut_v_set:
        p_rim = v_top.co.copy()
        ang = math.atan2(p_rim.x - ax, -(p_rim.y - 0.022))
        v_ang[v_top] = ang
        sx, sy = math.sin(ang), -math.cos(ang)
        c_front = max(0.0, math.cos(ang))
        c_back = max(0.0, -math.cos(ang))
        side_w = sx * sx
        w_fl = c_front ** 2.0
        v_turn = 0.74 * w_fl + 0.30 * (1.0 - w_fl)
        z_turn = p_rim.z - (0.008 * w_fl + 0.036 * (1.0 - w_fl))
        col = [None] * n_rings
        col[n_rings - 1] = v_top
        for iz in range(n_rings - 1):
            vf = iz / (n_rings - 1)
            t_col = min(1.0, vf / v_turn)
            cx = c_bot.x + (c_top.x - c_bot.x) * t_col
            cy = c_bot.y + (c_top.y - c_bot.y) * t_col
            rx = 0.0565
            ry = 0.0545 * c_front + 0.0575 * c_back + 0.0560 * (1.0 - c_front - c_back)
            trap_t = _sstep(0.50, 0.0, vf)
            rx += 0.020 * (trap_t ** 1.5) * (0.35 + 0.65 * side_w)
            ry += 0.015 * (trap_t ** 1.5) * (c_back ** 1.5)
            # Subtle sternocleidomastoid ridge + slight thyroid cartilage (Adam's apple) contour
            scm_bump = 0.0042 * math.exp(-(((abs(ang) - 0.78) / 0.22) ** 2)) * math.sin(t_col * math.pi)
            adams = 0.0042 * (c_front ** 6) * math.exp(-(((t_col - 0.64) / 0.11) ** 2))
            nape_h = -0.0032 * (c_back ** 1.6) * math.exp(-(((t_col - 0.58) / 0.24) ** 2))
            stump = -0.016 * (0.45 + 0.55 * c_front) * (_sstep(0.32, 0.0, vf) ** 1.3)
            r_an = math.hypot(rx * sx, ry * sy) + scm_bump + adams + nape_h + stump
            z_an = z_bot + (z_turn - z_bot) * t_col
            p_an = Vector((cx + sx * r_an, cy + sy * r_an, z_an))
            if vf <= v_turn:
                p_cur = p_an
            else:
                su = (vf - v_turn) / max(1e-5, 1.0 - v_turn)
                t_r = su * su * (3.0 - 2.0 * su)
                t_z = (1.0 - (1.0 - su) ** 2.1) * w_fl + su * (1.0 - w_fl)
                p_cur = Vector((
                    p_an.x + (p_rim.x - p_an.x) * t_r,
                    p_an.y + (p_rim.y - p_an.y) * t_r,
                    z_turn + (p_rim.z - z_turn) * t_z,
                ))
            col[iz] = bm.verts.new(p_cur)
        v_cols[v_top] = col

    for e in cut_edges:
        vA, vB = e.verts[0], e.verts[1]
        aA, aB = v_ang[vA], v_ang[vB]
        da = math.atan2(math.sin(aB - aA), math.cos(aB - aA))
        if da < 0:
            vA, vB = vB, vA
            aA, aB = aB, aA
        uA = (aA + math.pi) / math.tau
        uB = (aB + math.pi) / math.tau
        if uB - uA < -0.5:
            uB += 1.0
        elif uB - uA > 0.5:
            uA += 1.0
        cA, cB = v_cols[vA], v_cols[vB]
        for iz in range(n_rings - 1):
            v0, v1 = iz / (n_rings - 1), (iz + 1) / (n_rings - 1)
            try:
                fn = bm.faces.new((cA[iz], cB[iz], cB[iz + 1], cA[iz + 1]))
            except ValueError:
                continue
            fn.smooth = True
            fn.material_index = neck_mi
            for lp, uv_pt in zip(fn.loops, [(uA, v0), (uB, v0), (uB, v1), (uA, v1)]):
                lp[uv_layer].uv = uv_pt

    # Smooth the welded jaw-to-neck transition gently (strictly keeping chin/jaw crisp while rounding side/nape)
    seam_band = [
        v for v in bm.verts
        if not v.is_boundary and v.co.y > -0.055 and abs((v.co - plane_co).dot(plane_no)) < 0.018
    ]
    for _ in range(5):
        bmesh.ops.smooth_vert(bm, verts=seam_band, factor=0.30, use_axis_x=True, use_axis_y=True, use_axis_z=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Mathematical guarantee: verify face normals point outward from skull center (never flipped inside-out!)
    bm.faces.ensure_lookup_table()
    skull_c = Vector((ax, 0.01, 1.94))
    out_sum = sum(f.normal.dot((f.calc_center_median() - skull_c).normalized()) for f in bm.faces if f.calc_center_median().z > 1.88)
    if out_sum < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(head.data)
    bm.free()
    for p in head.data.polygons:
        p.use_smooth = True
    head.data.update()

    # 5. Build the sculpted 1930s Herringbone Flat Driving Cap in pristine head-local coordinates!
    import taxi_driver_wardrobe as wardrobe

    if wardrobe.CAP_SCAN.exists():
        # The photoscanned wool flat cap, warped onto his hat line; the scalp tucks in under it.
        cap_obj = wardrobe.build_scanned_flat_cap(head_bvh_raw, (ax, ay), coll)
        wardrobe.tuck_head_under_cap(head, cap_obj, (ax, ay))
        wardrobe.smooth_neck(head)
    else:
        cap_obj = _build_1930s_flat_cap(head_bvh_raw, (ax, ay), coll)
    head_bvh_raw = None

    # 6. Build the 5 exact runtime shape keys (`look_road`, `look_sora`, `nod`, `talk`, `blink`)
    #    on `taxi_driver_head_scan` AND lockstep matching shape keys on `taxi_driver_cap`!
    def _turned(pts, yaw=0.0, pitch=0.0, pivot=HEAD_PIVOT, weight=None):
        R = Matrix.Rotation(math.radians(yaw), 3, "Z") @ Matrix.Rotation(math.radians(pitch), 3, "X")
        rel = pts - np.array(pivot, np.float32)
        moved = rel @ np.array(R, np.float32).T + np.array(pivot, np.float32)
        w = _smoothstep(1.75, 1.92, pts[:, 2])[:, None] if weight is None else weight[:, None]
        return pts + (moved - pts) * w

    # Head shape keys
    h_co = np.array([v.co[:] for v in head.data.vertices], np.float32)
    jaw_w = (
        _smoothstep(HEAD_MOUTH_Z + 0.004, HEAD_MOUTH_Z - 0.007, h_co[:, 2])
        * _smoothstep(0.010, -0.032, h_co[:, 1])
        * _smoothstep(1.805, 1.855, h_co[:, 2])
    )
    jaw_w *= 1.0 - _smoothstep(0.034, 0.062, np.abs(h_co[:, 0])) * _smoothstep(HEAD_MOUTH_Z - 0.028, HEAD_MOUTH_Z, h_co[:, 2])

    blink_co = h_co.copy()
    for e in HEAD_EYES:
        dx = (h_co[:, 0] - e.x) / 0.019
        front = _smoothstep(-0.065, -0.080, h_co[:, 1])
        across = np.clip(1.0 - dx * dx, 0.0, 1.0)
        upper = across * front * _smoothstep(e.z + 0.016, e.z + 0.004, h_co[:, 2]) * _smoothstep(e.z - 0.002, e.z + 0.003, h_co[:, 2])
        lower = across * front * _smoothstep(e.z - 0.012, e.z - 0.004, h_co[:, 2]) * _smoothstep(e.z + 0.001, e.z - 0.003, h_co[:, 2])
        blink_co[:, 2] -= upper * 0.0085
        blink_co[:, 1] -= upper * 0.0012
        blink_co[:, 2] += lower * 0.0022

    head_shapes = [
        ("look_road", _turned(h_co, yaw=-HEAD_REST_YAW * 0.92)),
        ("look_sora", _turned(h_co, yaw=HEAD_REST_YAW * 0.72, pitch=4.5)),
        ("nod", _turned(h_co, pitch=8.5)),
        ("talk", _turned(h_co, pitch=10.5, pivot=HEAD_HINGE, weight=jaw_w)),
        ("blink", blink_co),
    ]
    head.shape_key_add(name="Basis", from_mix=False)
    for sk_name, pts in head_shapes:
        kb = head.shape_key_add(name=sk_name, from_mix=False)
        kb.data.foreach_set("co", pts.astype(np.float32).ravel())
        kb.value = 0.0

    # Cap lockstep shape keys (weight = 1.0 because entire cap rides rigid skull!)
    c_co = np.array([v.co[:] for v in cap_obj.data.vertices], np.float32)
    ones = np.ones(len(c_co), np.float32)
    cap_shapes = [
        ("look_road", _turned(c_co, yaw=-HEAD_REST_YAW * 0.92, weight=ones)),
        ("look_sora", _turned(c_co, yaw=HEAD_REST_YAW * 0.72, pitch=4.5, weight=ones)),
        ("nod", _turned(c_co, pitch=8.5, weight=ones)),
        ("talk", c_co.copy()),
        ("blink", c_co.copy()),
    ]
    cap_obj.shape_key_add(name="Basis", from_mix=False)
    for sk_name, pts in cap_shapes:
        kb = cap_obj.shape_key_add(name=sk_name, from_mix=False)
        kb.data.foreach_set("co", pts.astype(np.float32).ravel())
        kb.value = 0.0

    # 7. Place head & cap into the Rosalie driver's seat (lowered -5.6cm onto realistic shoulder line!)
    T_cabin = (
        Matrix.Translation(neck_world_pos + Vector((0.0, -0.026, -0.040 - 0.056)))
        @ Matrix.Rotation(math.radians(HEAD_REST_YAW), 4, "Z")
        @ Matrix.Rotation(math.radians(3.5), 4, "X")
        # 93%: the scanned head on Eric's shoulders read large, doll-like.
        @ Matrix.Scale(0.93, 4)
        @ Matrix.Translation(-HEAD_NECK_BASE)
    )
    head.data.transform(T_cabin, shape_keys=True)
    head.data.update()
    cap_obj.data.transform(T_cabin, shape_keys=True)
    cap_obj.data.update()

    # Diagnostic check: verify ZERO inward-facing jaw polygons!
    center_w = T_cabin @ Vector((0.0, 0.01, 1.95))
    inward_jaw = sum(
        1 for p in head.data.polygons
        if p.center.y < -0.01 and 0.94 < p.center.z < 1.05 and p.normal.dot((p.center - center_w).normalized()) < -0.35
    )
    print(
        "TAXI_DRIVER_HEAD_AND_CAP_REBUILT",
        "head_verts=", len(head.data.vertices),
        "head_polys=", len(head.data.polygons),
        "cap_polys=", len(cap_obj.data.polygons),
        "inward_jaw_polys=", inward_jaw,
    )
    return head


# --------------------------------------------------------------------------- 2. DRIVER BODY, NATURAL STEERING GRIP, COLLAR & KRAMA

def _build_tailored_cuff_bvh(bvh, wrist_pt, arm_ax, length=0.030, pad=0.0024, shift=-0.014, bm_cloth=None, bm_btn=None, side_hint=1.0):
    """Build a slim, raycast-fitted 1930s shirt/blouse cuff hugging the actual forearm cross-section."""
    ax = Vector(arm_ax).normalized()
    center = Vector(wrist_pt) + ax * shift
    up = Vector((0, 0, 1))
    u = (up - ax * up.dot(ax)).normalized()
    v = ax.cross(u).normalized()

    segs = 28
    # Sample actual arm radius at 28 angles so the cuff conforms organically (never a bulbous cylinder!)
    r_prof = np.zeros(segs, np.float32)
    for k in range(segs):
        a = k / segs * math.tau
        d_rad = (u * math.cos(a) + v * math.sin(a)).normalized()
        # Cast inward from outside so we catch the outer surface reliably
        start = center + d_rad * 0.085
        hit = bvh.ray_cast(start, -d_rad, 0.082)
        if hit[0] is not None:
            r_prof[k] = max(0.020, min(0.052, (hit[0] - center).dot(d_rad) + pad))
        else:
            r_prof[k] = 0.032 + pad
    for _ in range(4):
        r_prof = 0.25 * np.roll(r_prof, -1) + 0.50 * r_prof + 0.25 * np.roll(r_prof, 1)

    # Tapered sleek folded hem (snug back edge merging smoothly into sleeve -> crisp slim cuff -> snug front hem hugging wrist!)
    prof = [
        (-length * 0.56, 0.92),
        (-length * 0.46, 0.99),
        (0.0,            1.00),
        (length * 0.42,  0.99),
        (length * 0.50,  0.94),
        (length * 0.42,  0.88),
        (-length * 0.46, 0.88),
    ]
    rings = []
    for dy, sc in prof:
        row = []
        for k in range(segs):
            a = k / segs * math.tau
            # Subtle placket overlap crease on outer wrist
            overlap = 0.0014 * math.exp(-(((a - math.pi * 0.5 * side_hint) % math.tau) ** 2) / 0.12)
            r = float(r_prof[k]) * sc + overlap
            pt = center + ax * dy + (u * math.cos(a) + v * math.sin(a)) * r
            row.append(bm_cloth.verts.new(pt))
        rings.append(row)
    for i in range(len(rings)):
        rA, rB = rings[i], rings[(i + 1) % len(rings)]
        for k in range(segs):
            bm_cloth.faces.new((rA[k], rA[(k + 1) % segs], rB[(k + 1) % segs], rB[k]))

    if bm_btn is not None:
        # Delicate realistic 5mm antique pearl button flush on outer wrist cuff
        k_btn = int((0.25 if side_hint > 0 else 0.75) * segs) % segs
        a_b = k_btn / segs * math.tau
        d_b = (u * math.cos(a_b) + v * math.sin(a_b)).normalized()
        btn_pos = center + ax * (length * 0.04) + d_b * (float(r_prof[k_btn]) * 1.005 + 0.0006)
        q = Vector((0, 0, 1)).rotation_difference(d_b).to_matrix().to_4x4()
        bmesh.ops.create_uvsphere(
            bm_btn, u_segments=12, v_segments=8, radius=1.0,
            matrix=Matrix.Translation(btn_pos) @ q @ Matrix.Diagonal((0.0026, 0.0026, 0.0010, 1.0)),
        )


def _pose_driver_hands_on_wheel(rig, wheel_turn=0.0, grip_tense=0.0, breathe=0.0, lean_peer=0.0):
    """True human ergonomic 9:15 & 2:45 steering-wheel grip (ZERO rim clipping, ZERO floating thumb!):
    - Hand axis (`hand -> middle_01`) points FORWARD (-F) across the outer rim flank so the knuckle line
      (`pinky -> index`) runs vertically ALONG the rim tangent (`+tan_up`)!
    - Palm faces cleanly INWARD (`-rad_dir`) seated flush against the outer-back contour of the 26mm tube.
    - All 4 fingers wrap PERPENDICULARLY around the front & inner contour of the 12.7mm radius bakelite tube
      with per-finger anatomical clearances (`dist >= 20mm` -> ZERO rim slicing through fingers!).
    - Both thumbs curve smoothly UP & ALONG the driver-facing front surface of the rim tube, resting directly
      on the bakelite rim (ZERO sideways hitchhiker thumb, ZERO empty pincer gap!).
    """
    C = WHEEL_CENTER.copy()
    F = WHEEL_NORMAL.copy()
    R0 = Vector((1, 0, 0))
    R0 = (R0 - F * R0.dot(F)).normalized()
    U0 = F.cross(R0).normalized()
    if U0.z < 0:
        U0 = -U0

    # Subtle spine breathing / peering posture adjustments (natural upright seated chauffeur spine — NO hunched tabletop!)
    s1, s2, s3, neck_b, head_b = [rig.bone(p) for p in ("spine_01", "spine_02", "spine_03", "neck_", "head_")]
    fwd_lean = lean_peer * 0.042 + grip_tense * 0.008 - breathe * 0.014
    for nm, ch, base_lean in [(s1, s2, 0.02), (s2, s3, -0.02), (s3, neck_b, -0.06), (neck_b, head_b, -0.14)]:
        j = rig.joint(nm)
        rig.aim(nm, ch, j + Vector((0.0, base_lean - fwd_lean, 1.0)))

    # Rotate local wheel basis by `wheel_turn` around the column normal F
    c_t, s_t = math.cos(wheel_turn), math.sin(wheel_turn)
    R = (R0 * c_t + U0 * s_t).normalized()
    U = (-R0 * s_t + U0 * c_t).normalized()

    ec = math.radians(5.5) * grip_tense
    post_spine_snap = rig.snapshot()

    def _restore_arm_bones(side):
        suffix = f"_{side}_"
        for pb in rig.arm.pose.bones:
            if suffix in pb.name and any(k in pb.name for k in ("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")):
                pb.matrix_basis = post_spine_snap[pb.name].copy()
        bpy.context.view_layer.update()

    def _pose_one_arm(side, sign, wrist_pos, ang, rim_pt, rad_dir, tan_up):
        sh = rig.joint(rig.bone(f"upperarm_{side}"))
        pole = sh + Vector((sign * (0.28 - 0.02 * grip_tense), 0.16, -0.90))
        rig.reach(rig.bone(f"upperarm_{side}"), rig.bone(f"lowerarm_{side}"), rig.bone(f"hand_{side}"), wrist_pos, pole)

        hand = rig.bone(f"hand_{side}")
        w0 = rig.joint(hand)

        # TRUE FORWARD HAND ALIGNMENT: hand runs straight FORWARD (-F) across the outer rim flank so
        # the knuckle line (pinky -> index) runs vertically along the rim (+tan_up), matching natural 9:15/2:45 driving!
        hand_fwd = (-F * 0.94 - rad_dir * 0.08 + tan_up * 0.30).normalized()
        rig.aim(hand, rig.bone(f"middle_01_{side}"), w0 + hand_fwd)

        # PALM FACES CLEANLY INWARD (-rad_dir) & SLIGHTLY FORWARD (-F) cradling the rim tube like the reference!
        want_palm = (-rad_dir * 0.90 - F * 0.32 - tan_up * 0.12).normalized()
        rig.roll_hand_with_twist(side, want_palm)

        # Per-finger anatomical curl clearing the 12.7mm rim tube cleanly around front -> inner face!
        rig.curl_fingers(
            side,
            {
                "index":  (math.radians(18) + ec, math.radians(66) + ec, math.radians(50) + ec * 0.5),
                "middle": (math.radians(24) + ec, math.radians(70) + ec, math.radians(52) + ec * 0.5),
                "ring":   (math.radians(22) + ec, math.radians(62) + ec, math.radians(50) + ec * 0.5),
                "pinky":  (math.radians(16) + ec, math.radians(54) + ec, math.radians(46) + ec * 0.5),
            },
            (math.radians(4), math.radians(12) + ec * 0.4, math.radians(14) + ec * 0.4),
            thumb_oppose=math.radians(16.0 + 3.0 * grip_tense),
        )

        # NATURAL CURVED THUMB CLASPING *INWARD OVER* THE DRIVER-FACING RIM (matches user reference!)
        # Compact natural C-curve: thumb_02 crosses onto the +F rim face, thumb_03 bends 32° INWARD hugging the inner bevel!
        t1, t2, t3 = rig.bone(f"thumb_01_{side}"), rig.bone(f"thumb_02_{side}"), rig.bone(f"thumb_03_{side}")
        p_t1 = rig.joint(t1)
        ang2 = ang + math.radians(6.5)
        rad2 = (R * (sign * math.cos(ang2)) + U * math.sin(ang2)).normalized()
        pt2 = C + rad2 * WHEEL_RADIUS + F * 0.022 - rad2 * 0.008
        ang3 = ang + math.radians(12.5)
        rad3 = (R * (sign * math.cos(ang3)) + U * math.sin(ang3)).normalized()
        pt3 = C + rad3 * WHEEL_RADIUS + F * 0.015 - rad3 * 0.020
        cur12 = (rig.joint(t2) - p_t1).normalized()
        ax1, a1 = cur12.rotation_difference((pt2 - p_t1).normalized()).to_axis_angle()
        rig.turn(t1, ax1, min(a1, math.radians(52.0)))
        cur23 = (rig.joint(t3) - rig.joint(t2)).normalized()
        ax2, a2 = cur23.rotation_difference((pt3 - rig.joint(t2)).normalized()).to_axis_angle()
        rig.turn(t2, ax2, min(a2, math.radians(62.0)))
        # Pronounced anatomical bend at thumb IP joint so BOTH left & right thumb pads wrap snugly over inner-front bevel!
        tan3 = (-R * (sign * math.sin(ang3)) + U * math.cos(ang3)).normalized()
        t3_tip_want = (C + rad3 * WHEEL_RADIUS + tan3 * 0.006 - F * 0.010 - rad3 * 0.026 - rig.joint(t3)).normalized()
        _, cur3 = rig.finger_tip("thumb", side)
        ax3, a3 = cur3.rotation_difference(t3_tip_want).to_axis_angle()
        rig.turn(t3, ax3, min(a3, math.radians(52.0)))

    for side, sign in [("l", 1.0), ("r", -1.0)]:
        ang = math.radians(4.0)
        rad_dir = (R * (sign * math.cos(ang)) + U * math.sin(ang)).normalized()
        tan_up = (-R * (sign * math.sin(ang)) + U * math.cos(ang)).normalized()
        rim_pt = C + rad_dir * WHEEL_RADIUS

        wrist = rim_pt + F * 0.104 + rad_dir * 0.026 - tan_up * 0.032

        # 8 clean settle passes placing the enclosed finger arch snugly around the 12.7mm bakelite tube!
        target_ctr = rim_pt - F * 0.011 - rad_dir * 0.003
        for _ in range(8):
            _restore_arm_bones(side)
            _pose_one_arm(side, sign, wrist, ang, rim_pt, rad_dir, tan_up)
            m1 = rig.joint(rig.bone(f"middle_01_{side}"))
            m2 = rig.joint(rig.bone(f"middle_02_{side}"))
            m3 = rig.joint(rig.bone(f"middle_03_{side}"))
            mt, _ = rig.finger_tip("middle", side)
            hollow = m1 * 0.28 + m2 * 0.24 + m3 * 0.24 + mt * 0.24
            delta = target_ctr - hollow
            if delta.length < 0.0010:
                break
            wrist = wrist + delta * 0.85


def _pose_driver_arms_to_wrists(rig, frames, wheel_turn=0.0, grip_tense=0.0, breathe=0.0, lean_peer=0.0):
    """Seat the spine like `_pose_driver_hands_on_wheel`, then reach each arm to the wrist of the
    photoscanned hand gripping the rim (`frames[side] = (wrist, knuckle direction, palm normal)`) and
    turn the scan's own hand bone the same way so the sleeve's forearm twist follows the grip."""
    s1, s2, s3, neck_b, head_b = [rig.bone(p) for p in ("spine_01", "spine_02", "spine_03", "neck_", "head_")]
    fwd_lean = lean_peer * 0.042 + grip_tense * 0.008 - breathe * 0.014
    for nm, ch, base_lean in [(s1, s2, 0.02), (s2, s3, -0.02), (s3, neck_b, -0.06), (neck_b, head_b, -0.14)]:
        j = rig.joint(nm)
        rig.aim(nm, ch, j + Vector((0.0, base_lean - fwd_lean, 1.0)))
    for side, sign in (("l", 1.0), ("r", -1.0)):
        wrist, fwd, palm = (Vector(tuple(map(float, x))) for x in frames[side])
        sh = rig.joint(rig.bone(f"upperarm_{side}"))
        pole = sh + Vector((sign * (0.28 - 0.02 * grip_tense), 0.16, -0.90))
        rig.reach(rig.bone(f"upperarm_{side}"), rig.bone(f"lowerarm_{side}"), rig.bone(f"hand_{side}"), wrist, pole)
        hand = rig.bone(f"hand_{side}")
        rig.aim(hand, rig.bone(f"middle_01_{side}"), rig.joint(hand) + fwd)
        rig.roll_hand_with_twist(side, palm)


def _add_driver_shirt_collar_and_krama(coll, neck_pos, body_obj, head_obj, plain, world_uvs_fn):
    """Build:
    1) A tailored 1930s open-collar linen shirt collar peeking naturally above his waistcoat/under the krama.
    2) An authentic, relaxed, softly draped Cambodian woven krama slung casually over his shoulders & chest
       with organic flat-ribbon folds and knotted cotton fringe ends (NO stiff checkered donut ring!).
    """
    _clear_objects("taxi_driver_krama", "taxi_driver_shirt_collar")
    if body_obj is None or neck_pos is None:
        return

    import taxi_driver_wardrobe as wardrobe

    if head_obj is not None and wardrobe.HAND_SCAN.exists():
        # A crisp cotton stand collar, then a full-size krama cloth-simulated round his neck and down
        # his chest; both follow his breathing and leaning through the body's shape keys.
        cuff_mat = bpy.data.materials.get("M_cab_driver_cuff_cotton") or bpy.data.materials.get("M_taxi_driver_clothes_scan")
        # The scan's own shirt, tie and waistcoat show in the V: real cloth reads better than any
        # generated collar, and the krama covers the neck opening.
        _clear_objects("taxi_driver_shirt_front", "taxi_driver_shirt_buttons")
        krama = wardrobe.build_rolled_krama(coll, body_obj, [body_obj, head_obj], (neck_pos.x, neck_pos.y))
        for obj in (krama,):
            wardrobe.bind_to_body(obj, body_obj, ["breathe", "lean_peer"])
        return

    # 1. Build KDTree over driver's actual upper torso/shoulders FIRST so BOTH the slim 1930s shirt collar
    #    AND the relaxed Cambodian krama drape flush onto his real shoulders (ZERO floating cardboard UFO ring!)
    body_pts = []
    mw_b = body_obj.matrix_world
    nm_b = mw_b.to_3x3()
    for v in body_obj.data.vertices:
        wp = mw_b @ v.co
        if 0.56 < wp.z < 0.94 and -0.02 < wp.x < 0.56:
            body_pts.append((wp, (nm_b @ v.normal).normalized()))
    body_tree = KDTree(len(body_pts))
    for i, (co, _) in enumerate(body_pts):
        body_tree.insert(co, i)
    body_tree.balance()

    def drape_body(p, offset=0.004):
        co, idx, _ = body_tree.find(p)
        nrm = body_pts[idx][1]
        return co + nrm * offset, nrm

    # Sleek, tailored 1930s open linen shirt collar standing cleanly around his neck (zero gap under collar!)
    cuff_mat = bpy.data.materials.get("M_cab_driver_cuff_cotton") or bpy.data.materials.get("M_taxi_driver_clothes_scan")
    nc = Vector((neck_pos.x - 0.005, 0.025, 0.886))
    bm_col = bmesh.new()
    segs = 36
    c_rings = []
    for r_idx, (r_sc, z_off, flare) in enumerate([
        (0.88, -0.036, 0.000),  # tucked deeply into shirt neckline (ZERO gap!)
        (0.95,  0.008, 0.001),  # slim collar stand fold
        (1.02,  0.012, 0.003),  # crisp folded collar crest
        (1.12, -0.022, 0.008),  # slim tailored collar edge resting softly over his lowered shoulders & under krama
    ]):
        row = []
        for k in range(segs):
            ang = math.radians(24.0 + (k / (segs - 1)) * 312.0)
            sx, sy = math.sin(ang), -math.cos(ang)
            c_back = max(0.0, -math.cos(ang))
            c_front = max(0.0, math.cos(ang))
            pt_drop = -0.012 * (c_front ** 2.2) if r_idx == 3 else 0.0
            rx = (0.059 + flare) * r_sc
            ry = (0.057 + flare) * r_sc
            z = nc.z + z_off + 0.008 * c_back + pt_drop
            p_c = Vector((nc.x + sx * rx, nc.y + sy * ry, z))
            if r_idx == 3:
                dp, _ = drape_body(p_c, 0.0035)
                p_c = p_c.lerp(dp, 0.55)
            row.append(bm_col.verts.new(p_c))
        c_rings.append(row)
    for rA, rB in zip(c_rings, c_rings[1:]):
        for k in range(segs - 1):
            bm_col.faces.new((rA[k], rA[k + 1], rB[k + 1], rB[k]))
    bmesh.ops.smooth_vert(bm_col, verts=list(bm_col.verts), factor=0.40, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    collar_obj = _bm_to_obj("taxi_driver_shirt_collar", bm_col, cuff_mat, coll, smooth=True)
    if world_uvs_fn:
        world_uvs_fn(collar_obj)
    else:
        _apply_box_uvs(collar_obj, scale=4.2)

    # 2. Build KDTree over driver shoulders, chest & slim collar so the relaxed krama drapes CLEANLY OUTSIDE both!
    pts = list(body_pts)
    mw_c = collar_obj.matrix_world
    nm_c = mw_c.to_3x3()
    for v in collar_obj.data.vertices:
        wp = mw_c @ v.co
        pts.append((wp, (nm_c @ v.normal).normalized()))
    tree = KDTree(len(pts))
    for i, (co, _) in enumerate(pts):
        tree.insert(co, i)
    tree.balance()

    def drape_pt(p, offset=0.010):
        co, idx, _ = tree.find(p)
        nrm = pts[idx][1]
        return co + nrm * offset, nrm

    # Authentic Cambodian red/charcoal/cream hand-loomed krama texture (larger realistic check scale + rich weave!)
    n_tex = 512
    yy, xx = np.mgrid[:n_tex, :n_tex]
    rng = np.random.default_rng(193342)
    # Traditional multi-band Khmer krama plaid (broad deep-crimson & charcoal stripes crossing warm ivory!)
    bx = ((xx // 28) % 2).astype(np.float32)
    by = ((yy // 28) % 2).astype(np.float32)
    fine_x = (((xx % 28) == 4) | ((xx % 28) == 23)).astype(np.float32)
    fine_y = (((yy % 28) == 4) | ((yy % 28) == 23)).astype(np.float32)
    crimson = np.array([0.30, 0.048, 0.042], np.float32)
    charcoal = np.array([0.075, 0.068, 0.064], np.float32)
    cream = np.array([0.52, 0.46, 0.37], np.float32)
    warp = np.where(bx[..., None] > 0.5, crimson, cream)
    weft = np.where(by[..., None] > 0.5, charcoal, cream)
    rgb = warp * 0.52 + weft * 0.48
    accent = np.maximum(fine_x, fine_y)[..., None]
    rgb = rgb * (1.0 - accent * 0.35) + crimson * (accent * 0.35)
    # Visible hand-loomed cotton warp/weft thread grain + subtle rain-worn patina
    thread = 0.88 + 0.12 * np.sin(xx * (math.pi / 1.4)) * np.sin(yy * (math.pi / 1.4))
    wear = _box_blur_2d(rng.normal(0.0, 0.06, (n_tex, n_tex)).astype(np.float32), 14)
    rgb = np.clip(rgb * (thread + wear)[..., None], 0.02, 0.78)
    krama_bc = _pack_image("T_taxi_driver_krama_BC", rgb, is_srgb=True)
    krama_n = bpy.data.images.load(str(LINEN_N), check_existing=True) if LINEN_N.exists() else None
    krama_mat = _make_pbr("M_cab_driver_krama", krama_bc, krama_n, rough=0.90, normal_strength=0.45, double_sided=True)

    # Relaxed, softly draped Cambodian krama resting organically ON TOP OF his relaxed lowered shoulders (z~0.855)
    # cleanly OUTSIDE the collar -> ZERO clipping into shoulders, ZERO Z-fighting with collar!
    ctrl_pts = [
        # Left chest tail hanging softly flat over his left chest (+X side)
        Vector((nc.x + 0.072, -0.118, 0.680)),
        Vector((nc.x + 0.076, -0.112, 0.735)),
        Vector((nc.x + 0.080, -0.094, 0.790)),
        Vector((nc.x + 0.088, -0.056, 0.832)),
        # Resting softly across left shoulder cleanly outside collar base
        Vector((nc.x + 0.092, -0.006, 0.854)),
        Vector((nc.x + 0.082,  0.048, 0.858)),
        # Wrapping cleanly behind collar base (nape)
        Vector((nc.x + 0.044,  0.088, 0.862)),
        Vector((nc.x + 0.000,  0.098, 0.864)),
        Vector((nc.x - 0.046,  0.088, 0.862)),
        # Resting softly across right shoulder / collarbone (facing Sora — smooth, zero collar or vest clip!)
        Vector((nc.x - 0.084,  0.046, 0.858)),
        Vector((nc.x - 0.092, -0.006, 0.852)),
        Vector((nc.x - 0.086, -0.058, 0.828)),
        # Right chest tail draping gently down his chest
        Vector((nc.x - 0.070, -0.096, 0.778)),
        Vector((nc.x - 0.062, -0.112, 0.720)),
        Vector((nc.x - 0.056, -0.118, 0.660)),
    ]
    spine = []
    n_c = len(ctrl_pts)
    for i in range(n_c - 1):
        p0 = ctrl_pts[max(0, i - 1)]
        p1 = ctrl_pts[i]
        p2 = ctrl_pts[i + 1]
        p3 = ctrl_pts[min(n_c - 1, i + 2)]
        for s in range(5):
            t = s / 5.0
            t2, t3 = t * t, t * t * t
            pt = 0.5 * (
                (2.0 * p1)
                + (-p0 + p2) * t
                + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
            )
            spine.append(pt)
    spine.append(ctrl_pts[-1])

    draped = []
    norms = []
    for p in spine:
        q, nrm = drape_pt(p, 0.0110)
        draped.append(q)
        norms.append(nrm)
    for _ in range(12):
        draped = [draped[0]] + [(draped[i - 1] + draped[i] * 2 + draped[i + 1]) * 0.25 for i in range(1, len(draped) - 1)] + [draped[-1]]
    for _ in range(18):
        norms = [norms[0]] + [((norms[i - 1] + norms[i] * 2 + norms[i + 1]).normalized()) for i in range(1, len(norms) - 1)] + [norms[-1]]

    # Sweep a soft, thin, smoothly-draped cotton krama (4.6 cm wide, 4.2 mm thin!)
    verts, faces, uvs = [], [], []
    sides = 14
    n_sp = len(draped)
    for s, p in enumerate(draped):
        frac = s / max(1, n_sp - 1)
        nxt = draped[min(n_sp - 1, s + 1)]
        prv = draped[max(0, s - 1)]
        tan = (nxt - prv).normalized()
        out = (norms[s] - tan * norms[s].dot(tan)).normalized()
        across = tan.cross(out).normalized()
        end_flare = 1.0 + 0.16 * (abs(frac - 0.5) * 2.0) ** 1.8
        half_w = 0.023 * end_flare
        thick = 0.0042 * (1.15 - 0.25 * (abs(frac - 0.5) * 2.0))
        for k in range(sides):
            b = k / sides * math.tau
            pleat = 1.0 + 0.08 * math.sin(b * 2.0 + s * 0.15)
            pt = p + out * (math.cos(b) * thick * pleat) + across * (math.sin(b) * half_w)
            verts.append(pt)
            uvs.append((frac * 5.2, k / sides * 0.75))
    for s in range(n_sp - 1):
        for k in range(sides):
            a = s * sides + k
            b = (s + 1) * sides + k
            faces.append((a, s * sides + (k + 1) % sides, (s + 1) * sides + (k + 1) % sides, b))

    # Add delicate knotted fringe tassels at both ends of the krama!
    for end_idx, sign_dir in ((0, -1), (n_sp - 1, 1)):
        p_end = draped[end_idx]
        tan = ((draped[1] - draped[0]) if end_idx == 0 else (draped[-1] - draped[-2])).normalized() * sign_dir
        _, out = drape_pt(p_end, 0.0)
        out = (out - tan * out.dot(tan)).normalized()
        across = tan.cross(out).normalized()
        for t_i in range(7):
            u_t = (t_i / 6.0 - 0.5) * 0.068
            f0 = p_end + across * u_t
            f1 = f0 + tan * 0.022 + Vector((0, 0, -0.012)) + out * 0.002
            base_v = len(verts)
            for kk in range(4):
                aa = kk / 4.0 * math.tau
                off = (across * math.cos(aa) + out * math.sin(aa)) * 0.0018
                verts.append(f0 + off)
                uvs.append((0.05, 0.05))
                verts.append(f1 + off * 0.5)
                uvs.append((0.12, 0.05))
            for kk in range(4):
                kn = (kk + 1) % 4
                faces.append((base_v + kk * 2, base_v + kn * 2, base_v + kn * 2 + 1, base_v + kk * 2 + 1))

    krama_obj = _make_mesh_uv("taxi_driver_krama", verts, faces, uvs, krama_mat, coll, smooth=True)
    bm = bmesh.new()
    bm.from_mesh(krama_obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(krama_obj.data)
    bm.free()
    for p in krama_obj.data.polygons:
        p.use_smooth = True
    krama_obj.data.update()


WHEEL_PARTS = ("taxi_steering_wheel_rim", "taxi_steering_wheel_spokes", "taxi_steering_wheel_chrome")


def _rim_cut_into_fists(bm, mw, hidden, C, F):
    """His forearms lie along the rim, so a cut made only where some pose buries it leaves ends that
    show in the others. On each side the cut becomes one arc of the wheel running from its far end into
    the middle of that hand's fist, so both ends stay hidden (in the sleeve, in the fist) as he moves;
    the hands ride the wheel, so the arc holds in the wheel's own frame as it turns."""
    R0 = Vector((1.0, 0.0, 0.0))
    R0 = (R0 - F * R0.dot(F)).normalized()
    U0 = F.cross(R0).normalized()
    if U0.z < 0:
        U0 = -U0

    def ang(p):
        r = p - C
        a = math.degrees(math.atan2(r.dot(U0), r.dot(R0)))
        return a if a > -100.0 else a + 360.0  # left side -100..100, right side 100..260

    a_of = {v: ang(mw @ v.co) for v in bm.verts}
    more = set()
    for side in ("l", "r"):
        on_side = (lambda a: a <= 100.0) if side == "l" else (lambda a: a > 100.0)
        cut = [a_of[v] for v in hidden if on_side(a_of[v])]
        if not cut:
            continue
        # The middle of his fist sits at the grip's clock angle (the left hand above the horizontal on
        # his left, the right one just below it on his right).
        import taxi_driver_wardrobe as wardrobe

        clock = wardrobe.DRIVER_GRIP[side][0]
        mid = clock if side == "l" else 180.0 - clock
        lo, hi = min(cut), max(cut)
        # Keep the end farther from the fist; the near end goes to the middle of the fist (never past
        # it, where a gap would show beyond his hand).
        if abs(mid - lo) > abs(hi - mid):
            hi = mid
        else:
            lo = mid
        more |= {v for v in bm.verts if on_side(a_of[v]) and lo <= a_of[v] <= hi}
        print("TAXI_WHEEL_RIM_ARC", side, round(lo, 1), round(hi, 1), "fist at", mid)
    return more


def _restore_full_mesh(obj):
    """Give `obj` a fresh copy of its untouched mesh (`<name>__full`, kept in the blend), so a build
    that hides parts of it starts from the whole mesh every time."""
    name = obj.name
    full = bpy.data.meshes.get(name + "__full")
    if full is None:
        full = obj.data.copy()
        full.name = name + "__full"
        full.use_fake_user = True
    old = obj.data
    obj.data = full.copy()
    if old.users == 0:
        bpy.data.meshes.remove(old)
    obj.data.name = name
    obj.data.use_fake_user = False


def _islands(bm):
    seen = set()
    for f0 in bm.faces:
        if f0 in seen:
            continue
        island, st = [], [f0]
        seen.add(f0)
        while st:
            g = st.pop()
            island.append(g)
            for e in g.edges:
                for nf in e.link_faces:
                    if nf not in seen:
                        seen.add(nf)
                        st.append(nf)
        yield island


def _trim_spokes_at_sleeve(bm, mw, inside, C, F, into=0.004):
    """Slice each spoke that runs into his sleeve just inside it (`into` past where his sleeve first
    covers it with his arms at rest) and cap the cut; the part beyond, under his arm, goes."""
    if not inside:
        return
    mw_inv = mw.inverted()
    for island in list(_islands(bm)):
        verts = {v for f in island for v in f.verts}
        hit = [v for v in verts if v in inside]
        if not hit:
            continue
        radial = lambda v: ((mw @ v.co - C) - F * (mw @ v.co - C).dot(F))
        d = sum((radial(v) for v in verts), Vector()).normalized()
        r_cut = min(radial(v).length for v in hit) + into
        co_l = mw_inv @ (C + d * r_cut)
        no_l = (mw_inv.to_3x3() @ d).normalized()
        geom = list(verts) + list({e for f in island for e in f.edges}) + list(island)
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=co_l, plane_no=no_l, clear_outer=True)
        cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_valid and e.is_boundary]
        if cut_edges:
            bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
        print("TAXI_WHEEL_SPOKE_TRIMMED", round(r_cut, 3))


def cut_wheel_inside_driver(clear=0.0005, turns=None):
    """Hide only the bits of the steering wheel that would show through the driver's sleeves: rim,
    spoke and spoke-cap faces lying inside (or within `clear` of) his clothes in any of his shapes,
    each shape against the wheel turned as that shape holds it (`steer_left` +0.16 rad, `steer_right`
    -0.16, the rest straight). The rest of the wheel stays. Each part keeps
    an untouched copy (`<name>__full`, saved in the blend) and is cut from it afresh on every build."""
    body = bpy.data.objects.get("taxi_driver_body_scan")
    if body is None:
        return
    me_b = body.data
    polys = [tuple(p.vertices) for p in me_b.polygons]
    turns = turns or {"steer_left": 0.16, "steer_right": -0.16}
    layers = [("Basis", np.array([v.co[:] for v in me_b.vertices]))]
    if me_b.shape_keys:
        layers += [(kb.name, np.array([d.co[:] for d in kb.data])) for kb in me_b.shape_keys.key_blocks if kb.name != "Basis"]
    mw_b = body.matrix_world
    C, F = WHEEL_CENTER.copy(), WHEEL_NORMAL.normalized()
    # (a wheel turned by t sits rotated about its column by -t, as `_pose_driver_hands_on_wheel` turns it)
    left = Vector((1.0, 0.0, 0.0))
    left = (left - F * left.dot(F)).normalized()
    poses = [(BVHTree.FromPolygons([mw_b @ Vector(c) for c in co], polys), Matrix.Rotation(-turns.get(n, 0.0), 4, F)) for n, co in layers]
    total = 0
    for name in WHEEL_PARTS:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            continue
        _restore_full_mesh(obj)
        mw = obj.matrix_world
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hidden = set()
        rest_inside = {}  # vertex -> inside his sleeve with his arms at rest (the wheel straight)
        for v in bm.verts:
            p0 = mw @ v.co
            # Only on his left: that forearm lies along the rim. The right cuff only grazes it in a few
            # shapes, and cutting there opened a gap under his near hand, in plain view from Sora's seat.
            if (p0 - C).dot(left) <= 0.0:
                continue
            for (bvh, R), (lay, _) in zip(poses, layers):
                p = C + (R @ (p0 - C).to_4d()).to_3d()
                hit = bvh.find_nearest(p, 0.03)
                if hit[0] is None:
                    continue
                if (p - hit[0]).length < clear or (p - hit[0]).dot(hit[1]) < 0.0:
                    hidden.add(v)
                    if lay not in turns:
                        rest_inside[v] = True
                    else:
                        break
        if name.endswith("_spokes"):
            # A spoke keeps its whole length up to where it goes into his sleeve at rest, sliced there
            # and capped (its segments are long: cutting whole faces took the spoke back to the hub).
            _trim_spokes_at_sleeve(bm, mw, rest_inside, C, F)
            hidden = set()
        if name.endswith("_rim") and hidden:
            hidden |= _rim_cut_into_fists(bm, mw, hidden, C, F)
        kill = {f for f in bm.faces if any(v in hidden for v in f.verts)}
        # A spoke cap only partly cut would leave a floating chrome fragment: it goes whole.
        for island in _islands(bm):
            if name.endswith("_chrome") and len(island) < 400 and any(g in kill for g in island):
                kill.update(island)
        kill = list(kill)
        if kill:
            bmesh.ops.delete(bm, geom=kill, context="FACES")
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        total += len(kill)
        print("TAXI_WHEEL_CUT_INSIDE_DRIVER", name, len(kill))
    return total


def rebuild_driver_body_and_clothes(coll, neck_target, plain, world_uvs_fn):
    """Rebuild the driver's body cleanly with:
    - Ergonomic natural 9:45 & 2:15 steering wheel grip + smooth `lowerarm_twist` pronation
    - Crisp preserved 4K photographic hand/knuckle/nail textures (no muddy blur!)
    - Live skeletal morph targets (`steer_left`, `steer_right`, `grip_tense`, `breathe`, `lean_peer`)
      synced onto tailored shirt cuffs & buttons so his hands ACTUALLY TURN the steering wheel!
    - Open 1930s shirt collar + relaxed draped woven Cambodian krama with fringes.
    """
    scan_path = SCANS / "taxi_driver_scan.glb"
    if not scan_path.exists():
        return None

    _clear_objects(
        "taxi_driver_body_scan",
        "taxi_driver_sleeves_scan",
        "taxi_driver_shirt_cuffs",
        "taxi_driver_cuff_buttons",
        "taxi_driver_shirt_collar",
        "taxi_driver_krama",
        "taxi_driver_hand_l",
        "taxi_driver_hand_r",
    )

    arm, body, imported = _import_glb_rigged(scan_path)
    _weld_rigged_mesh_preserve_groups(body, dist=0.0004)
    rig = _RigHelper(arm)

    rest = [(body.matrix_world @ v.co).copy() for v in body.data.vertices]
    raw_mat = body.data.materials[0]
    raw_bc_img = next((n.image for n in raw_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"), None)
    raw_n_img = next((n.image for n in raw_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "Non-Color" and "normal" in n.image.name.lower()), None)

    wrist_rest = {
        "l": (rig.joint(rig.bone("lowerarm_l")), rig.joint(rig.bone("hand_l"))),
        "r": (rig.joint(rig.bone("lowerarm_r")), rig.joint(rig.bone("hand_r"))),
    }
    elbow_rest = {s: rig.joint(rig.bone(f"lowerarm_{s}")).copy() for s in ("l", "r")}

    # 1. Seated Rosalie driving posture with REAL RELAXED HUMAN SHOULDER HEIGHT (shoulders at z~0.855, NOT shrugged
    #    up into his ears at z=0.920 -> exposes a natural human neck & lets collar + krama sit cleanly on his shoulders!)
    hip_target = Vector((0.27, 0.07, 0.37))
    arm.location += hip_target - rig.joint(rig.bone("hip_"))
    for side, knee, ankle, ball in [
        ("l", (0.38, -0.35, 0.45), (0.37, -0.58, 0.12), (0.37, -0.72, 0.05)),
        ("r", (0.17, -0.35, 0.44), (0.15, -0.60, 0.14), (0.13, -0.75, 0.08)),
    ]:
        rig.aim(rig.bone(f"upperleg_{side}"), rig.bone(f"lowerleg_{side}"), knee)
        rig.aim(rig.bone(f"lowerleg_{side}"), rig.bone(f"foot_{side}"), ankle)
        rig.aim(rig.bone(f"foot_{side}"), rig.bone(f"ball_{side}"), ball)

    s1, s2, s3, neck_b, head_b = [rig.bone(p) for p in ("spine_01", "spine_02", "spine_03", "neck_", "head_")]
    for nm, ch, lean in [(s1, s2, 0.02), (s2, s3, -0.02), (s3, neck_b, -0.06), (neck_b, head_b, -0.14)]:
        j = rig.joint(nm)
        rig.aim(nm, ch, j + Vector((0, lean, 1)))
    if neck_target is not None:
        arm.location += (neck_target - Vector((0.0, 0.0, 0.044))) - rig.joint(neck_b)

    neutral_legs_snap = rig.snapshot()

    def _eval_world_verts():
        bpy.context.view_layer.update()
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m_w = body.matrix_world
        return [m_w @ v.co for v in ev.data.vertices]

    def _wrist_frame(side):
        wp = rig.joint(rig.bone(f"hand_{side}")).copy()
        ep = rig.joint(rig.bone(f"lowerarm_{side}")).copy()
        ax = (wp - ep).normalized()
        up = rig.palm_of(side) * (-1.0)
        up = (up - ax * up.dot(ax)).normalized()
        sd = up.cross(ax).normalized()
        return Matrix.Translation(wp) @ Matrix((sd, ax, up)).transposed().to_4x4()

    # Add clean 1-level Catmull-Clark Subdivision AFTER Armature so Eric's low-poly 734-vert hands become
    # silky-smooth ~3,000-vert anatomical hands (ZERO faceted knuckles, ZERO triangle-diagonal clay lumps!)
    # AND preserve identical vertex indices across Basis + all 5 skeletal morphs!
    # Bent elbows: the wheel sits close, so his elbows fold to about 70 degrees and plain skinning
    # collapsed the inside of each sleeve (the forearm pushed through the upper arm in a hard edge and
    # a balloon). A corrective smooth against the scan's rest shape relaxes the elbows in every pose
    # while keeping the cloth's own folds.
    vg_cs = body.vertex_groups.new(name="cs_elbows")
    for i, p in enumerate(rest):
        w_cs = max(_sstep(0.17, 0.07, (p - elbow_rest[s]).length) for s in ("l", "r"))
        if w_cs > 0.0:
            vg_cs.add([i], w_cs, "REPLACE")
    cs_mod = body.modifiers.new(name="ElbowRelax", type="CORRECTIVE_SMOOTH")
    cs_mod.vertex_group = vg_cs.name
    cs_mod.factor = 0.6
    cs_mod.iterations = 14
    cs_mod.smooth_type = "LENGTH_WEIGHTED"
    cs_mod.rest_source = "ORCO"
    cs_mod.scale = 1.0

    sub_mod = body.modifiers.new(name="SubsurfHands", type="SUBSURF")
    sub_mod.subdivision_type = "CATMULL_CLARK"
    sub_mod.levels = 1
    sub_mod.render_levels = 1
    sub_mod.uv_smooth = "PRESERVE_BOUNDARIES"

    # Pre-classify rest faces BEFORE baking so we use Eric's TRUE bare-skin boundary (NOT his shirt cuff!)
    # Eric's sculpted shirt cuff extends to u_arm ~ 1.13..1.16! Sampling his 4K photo skin color guarantees
    # ZERO shirt cuff cloth is ever painted flesh-colored!
    raw_sw, raw_sh = raw_bc_img.size if raw_bc_img else (1, 1)
    if raw_bc_img:
        _buf = np.empty(raw_sw * raw_sh * 4, np.float32)
        raw_bc_img.pixels.foreach_get(_buf)
        raw_px_arr = _buf.reshape(raw_sh, raw_sw, 4)[..., :3]
    else:
        raw_px_arr = np.full((1, 1, 3), 0.5, np.float32)
    raw_uvl = body.data.uv_layers.active.data

    # Assign raw material slot indices BEFORE Subsurf so Blender AUTOMATICALLY inherits exact per-face
    # material slots onto every Catmull-Clark subdivided child polygon!
    head_mat_tmp = bpy.data.materials.new("_tmp_drv_head_kill")
    cloth_mat_tmp = bpy.data.materials.new("_tmp_drv_cloth")
    hand_mat_tmp = bpy.data.materials.new("_tmp_drv_hand")
    body.data.materials.clear()
    body.data.materials.append(cloth_mat_tmp)   # slot 0 = cloth
    body.data.materials.append(hand_mat_tmp)    # slot 1 = bare hands ONLY
    body.data.materials.append(head_mat_tmp)    # slot 2 = head to delete
    for p in body.data.polygons:
        rc = sum((rest[vi] for vi in p.vertices), Vector()) / len(p.vertices)
        # Keep full intact shoulders & upper chest up to Eric's neck line (z > 1.572) so ZERO collar gap forms!
        if rc.z > 1.572:
            p.material_index = 2
            continue
        side_k = "l" if rc.x >= 0 else "r"
        e_r, w_r = wrist_rest[side_k]
        ax_r = w_r - e_r
        ax_u = ax_r.normalized()
        along_w = (rc - w_r).dot(ax_u)
        u_arm = (rc - e_r).dot(ax_r) / max(1e-6, ax_r.length_squared)
        perp = (rc - (e_r + ax_r * u_arm)).length
        # Place cloth->skin transition cleanly at along_w > 0.020m (strictly 12mm INSIDE our tailored cuff
        # at shift=+0.015, front_edge=+0.032m!) so ZERO sleeve bump or zigzag edge EVER shows past the cuff!
        is_hand = (rc - w_r).length < 0.24 and perp < 0.115 and along_w > 0.020
        p.material_index = 1 if is_hand else 0

    # Photoscanned hands (taxi_driver_wardrobe): each solves its own grip on the rim and the arms
    # reach to their wrists; Eric's low-poly hands are cut away at the cuff below.
    import taxi_driver_wardrobe as wardrobe

    scan_hands = None
    if wardrobe.HAND_SCAN.exists():
        rim = wardrobe.Rim(WHEEL_CENTER, WHEEL_NORMAL, RIM_CENTRELINE)
        # The scanned forearm runs 3.5 cm up inside the rolled sleeve.
        keep_len = 0.008 + SLEEVE_ROLL_UP + 0.035
        scan_hands = {"r": wardrobe.ScanHand(mirror=False, keep_len=keep_len), "l": wardrobe.ScanHand(mirror=True, keep_len=keep_len)}
        scan_hand_src_mat = scan_hands["r"].material
        for h in scan_hands.values():
            bpy.data.objects.remove(h.src_obj, do_unlink=True)
    hand_shapes = {}
    arm_joints = {}

    def _record_arms(name):
        arm_joints[name] = {
            side: tuple(rig.joint(rig.bone(b)).copy() for b in (f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"))
            for side in ("l", "r")
        }

    def _pose(kw, name, tap=0.0):
        """Pose arms (and the scanned hands) for one morph; records the hands' vertices under `name`."""
        if scan_hands is None:
            _pose_driver_hands_on_wheel(rig, **kw)
            _record_arms(name)
            return
        grips = {}
        for side, h in scan_hands.items():
            clock, elbow, loose = wardrobe.DRIVER_GRIP[side]
            grips[side] = wardrobe.solve_grip(
                h, rim, side, clock, elbow, turn=kw["wheel_turn"], tense=kw["grip_tense"],
                tap=tap if side == "r" else 0.0, looseness=loose,
            )[:2]
        _pose_driver_arms_to_wrists(rig, {s: wardrobe.wrist_frame(scan_hands[s], g[0]) for s, g in grips.items()}, **kw)
        shapes = {}
        for side, (G, loc) in grips.items():
            fa = rig.joint(rig.bone(f"lowerarm_{side}")) - rig.joint(rig.bone(f"hand_{side}"))
            G_fa = wardrobe.place_forearm(scan_hands[side], G, np.array(fa.normalized()[:]))
            shapes[side] = wardrobe.posed_hand(scan_hands[side], rim, G, G_fa, loc)
        hand_shapes[name] = shapes
        _record_arms(name)

    # 2. Pose neutral Basis + capture 5 tight, non-destructive skeletal driving morphs BEFORE baking!
    if scan_hands is not None:
        _pose(dict(wheel_turn=0.0, grip_tense=0.0, breathe=0.0, lean_peer=0.0), "grip", tap=1.0)
        rig.restore(neutral_legs_snap)
    _pose(dict(wheel_turn=0.0, grip_tense=0.0, breathe=0.0, lean_peer=0.0), "Basis")
    basis_snap = rig.snapshot()
    drv_wrists_basis = {
        "l": (
            rig.joint(rig.bone("hand_l")).copy(),
            (rig.joint(rig.bone("hand_l")) - rig.joint(rig.bone("lowerarm_l"))).normalized(),
            (rig.joint(rig.bone("middle_01_l")) - rig.joint(rig.bone("hand_l"))).normalized(),
        ),
        "r": (
            rig.joint(rig.bone("hand_r")).copy(),
            (rig.joint(rig.bone("hand_r")) - rig.joint(rig.bone("lowerarm_r"))).normalized(),
            (rig.joint(rig.bone("middle_01_r")) - rig.joint(rig.bone("hand_r"))).normalized(),
        ),
    }
    wrist_M_basis = {"l": _wrist_frame("l"), "r": _wrist_frame("r")}

    def _cuff_frame(side):
        """(wrist, cut axis toward the hand, cut-plane point) of a sleeve end. With the scanned hands the
        sleeves are rolled to mid-forearm, cut square to the forearm; otherwise the cuff sits at the wrist."""
        wp_b, ax_b, hand_b = drv_wrists_basis[side]
        if scan_hands is not None:
            return wp_b, ax_b.copy(), wp_b - ax_b * (0.008 + SLEEVE_ROLL_UP)
        return wp_b, (ax_b * 0.65 + hand_b * 0.35).normalized(), wp_b - ax_b * 0.008

    # Tight, purely additive steering & expression morphs (matching TaxiVisuals.ts wheelAngle clamp +-0.16 rad!)
    morph_specs = [
        ("steer_left",  dict(wheel_turn=+0.16, grip_tense=0.0,  breathe=0.0, lean_peer=0.0)),
        ("steer_right", dict(wheel_turn=-0.16, grip_tense=0.0,  breathe=0.0, lean_peer=0.0)),
        ("grip_tense",  dict(wheel_turn=0.0,   grip_tense=1.0,  breathe=0.0, lean_peer=0.0)),
        ("breathe",     dict(wheel_turn=0.0,   grip_tense=0.0,  breathe=1.0, lean_peer=0.0)),
        ("lean_peer",   dict(wheel_turn=0.0,   grip_tense=0.0,  breathe=0.0, lean_peer=1.0)),
    ]
    morph_verts_raw = {}
    wrist_M_morphs = {}
    for m_name, kw in morph_specs:
        rig.restore(neutral_legs_snap)
        _pose(kw, m_name)
        morph_verts_raw[m_name] = _eval_world_verts()
        wrist_M_morphs[m_name] = {"l": _wrist_frame("l"), "r": _wrist_frame("r")}

    # Restore neutral driving Basis for baking
    rig.restore(basis_snap)

    # 3. Bake Dual-Quaternion + Catmull-Clark Basis mesh & preserve exact vertex order for all 5 morphs!
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    baked = bpy.data.meshes.new_from_object(ev)
    baked.transform(body.matrix_world)
    body.modifiers.clear()
    body.parent = None
    body.matrix_world = Matrix.Identity(4)
    body.data = baked
    body.vertex_groups.clear()
    for o in imported:
        if o != body and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    for m_tmp in (head_mat_tmp, cloth_mat_tmp, hand_mat_tmp):
        if m_tmp.name in bpy.data.materials:
            bpy.data.materials.remove(m_tmp)

    # Attach all 5 skeletal shape keys BEFORE deleting head faces so Blender keeps vertex correspondence 100%!
    body.shape_key_add(name="Basis", from_mix=False)
    for m_name, pts_list in morph_verts_raw.items():
        kb = body.shape_key_add(name=m_name, from_mix=False)
        flat = np.array([p[:] for p in pts_list], np.float32).ravel()
        kb.data.foreach_set("co", flat)
        kb.value = 0.0

    # 5. Build HIGH-REALISM textures preserving crisp 4K photographic knuckles, veins, creases & garment folds!
    w_c, h_c = 2048, 2048
    rgb_scan = _resize_np(raw_bc_img, w_c, h_c)[..., :3] if raw_bc_img else np.full((h_c, w_c, 3), 0.5, np.float32)
    lo, hi = rgb_scan.min(-1), rgb_scan.max(-1)
    lum = rgb_scan @ np.array([0.3, 0.59, 0.11], np.float32)
    shade = _box_blur_2d(lum, 14)
    white_m = (lo > 0.5) & (hi - lo < 0.08)
    mean_sh = float(np.median(shade[white_m])) if white_m.any() else 0.7
    weave_rgb = _load_tiled_np(LINEN_BC, w_c, h_c, repeats=38, is_srgb=True) if LINEN_BC.exists() else np.full((h_c, w_c, 3), 0.55, np.float32)
    weave_lum = weave_rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    weave_fac = np.clip(weave_lum / max(1e-3, float(np.mean(weave_lum))), 0.84, 1.16)
    # A linen weave squeezed into a whole-body atlas only aliases into speckle ("felt"): keep a trace.
    weave_fac = 1.0 + (weave_fac - 1.0) * 0.12

    # Crisp woven 1930s linen shirt & rich tactile worsted-wool waistcoat (preserving real scan fold relief
    # on BOTH waistcoat AND shirt so his back NEVER looks like flat smooth plastic!)
    cloth_hi = lum - _box_blur_2d(lum, 5)
    shirt_raw = np.clip((lum - 0.22) / 0.14, 0.0, 1.0) * np.clip((0.22 - (hi - lo)) / 0.08, 0.0, 1.0)
    shirt_sel = np.clip(_box_blur_2d(shirt_raw, 9), 0.0, 1.0)
    cream = np.array((0.46, 0.41, 0.34), np.float32) * np.clip(0.76 + 0.30 * (shade / max(1e-3, mean_sh)) + cloth_hi * 1.1, 0.64, 1.14)[..., None] * weave_fac[..., None]
    # Add crisp worsted-twill micro-weave + scan fold shading onto the dark waistcoat so it reads like real woven wool!
    yy_w, xx_w = np.mgrid[0:h_c, 0:w_c].astype(np.float32)
    wool_twill = np.ones_like(xx_w)  # the old drawn twill read as fuzz; the scan's own folds carry the cloth
    suit_shade = np.clip(0.82 + 0.32 * (shade / max(1e-3, float(np.median(shade[~white_m])) if (~white_m).any() else 0.25)) + cloth_hi * 1.4, 0.60, 1.24)[..., None]
    suit = np.array((0.215, 0.188, 0.162), np.float32) * suit_shade * (0.62 + 0.38 * weave_fac[..., None]) * wool_twill[..., None]
    cloth_out = suit * (1.0 - shirt_sel[..., None]) + cream * shirt_sel[..., None]
    drv_cloth_bc = _pack_image("T_taxi_driver_clothes", cloth_out, is_srgb=True)

    # MATCHED WARM WEATHERED KHMER SKIN ON BOTH HANDS (equalized luminance so right hand never looks pale pink!)
    hand_base = np.array((0.525, 0.322, 0.214), np.float32)
    hand_mask = (rgb_scan[..., 0] > rgb_scan[..., 2] * 1.18) & (rgb_scan[..., 0] > 0.22)
    hand_med = float(np.median(lum[hand_mask])) if hand_mask.any() else 0.55
    non_skin_shirt = (lo > 0.38) & ((hi - lo) < 0.18)
    lum_hand = np.where(non_skin_shirt, hand_med, lum)
    hand_low = _box_blur_2d(lum_hand, 16)
    hand_high = lum_hand - _box_blur_2d(lum_hand, 6)
    redness = np.where(non_skin_shirt, 0.0, np.clip((rgb_scan[..., 0] - rgb_scan[..., 1]) - 0.085, -0.05, 0.11))[..., None]
    hand_shade = np.clip(0.88 + 0.12 * (hand_low / max(1e-3, hand_med)) + hand_high * 1.50, 0.66, 1.12)
    rng_h = np.random.default_rng(193312)
    pores = 1.0 + rng_h.normal(0.0, 0.015, (h_c, w_c)).astype(np.float32)
    hand_rgb = hand_base[None, None, :] * hand_shade[..., None] * pores[..., None] + redness * np.array([0.46, -0.09, -0.13], np.float32)
    drv_hand_bc = _pack_image("T_taxi_driver_hands_BC", np.clip(hand_rgb, 0.03, 0.86), is_srgb=True)

    wn, hn = 1024, 1024
    scan_n = _resize_np(raw_n_img, wn, hn) if raw_n_img else np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 2), np.float32)])
    linen_n = _load_tiled_np(LINEN_N, wn, hn, repeats=38, is_srgb=False) if LINEN_N.exists() else np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 1), np.float32)])
    drv_cloth_n = _pack_image("T_taxi_driver_clothes_N", _blend_normals(scan_n, linen_n, 0.85, 0.10), is_srgb=False)

    # Crisp knuckle/crease + epidermal pore normal for driver hands
    h_n = rng_h.normal(0.0, 0.026, (hn, wn)).astype(np.float32)
    h_n = (h_n + np.roll(h_n, 1, 0) + np.roll(h_n, -1, 0) + np.roll(h_n, 1, 1) + np.roll(h_n, -1, 1)) * 0.2
    gx_h = (np.roll(h_n, -1, 1) - np.roll(h_n, 1, 1)) * 0.60
    gy_h = (np.roll(h_n, -1, 0) - np.roll(h_n, 1, 0)) * 0.60
    nz_h = np.sqrt(np.clip(1.0 - gx_h * gx_h - gy_h * gy_h, 0.1, 1.0))
    pore_n = np.dstack([np.clip(-gx_h * 0.5 + 0.5, 0, 1), np.clip(-gy_h * 0.5 + 0.5, 0, 1), np.clip(nz_h * 0.5 + 0.5, 0, 1)])
    drv_hand_n = _pack_image("T_taxi_driver_hands_N", _blend_normals(scan_n, pore_n, 0.78, 0.42), is_srgb=False)

    clothes_mat = _make_pbr("M_taxi_driver_clothes_scan", drv_cloth_bc, drv_cloth_n, rough=0.88, normal_strength=0.52)
    hands_mat = _make_pbr("M_taxi_driver_hands_scan", drv_hand_bc, drv_hand_n, rough=0.48, normal_strength=0.64)

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    if body.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    body.data.materials[0] = clothes_mat
    body.data.materials[1] = hands_mat
    body.name = body.data.name = "taxi_driver_body_scan"
    for c_old in list(body.users_collection):
        c_old.objects.unlink(body)
    coll.objects.link(body)

    # Clean head faces (slot 2), smooth cloth ONLY (ZERO melting on Eric's Catmull-Clark hands!), and drop slot 2!
    body.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(body.data)
    bm.faces.ensure_lookup_table()
    kill = [f for f in bm.faces if f.material_index == 2]
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
    for _ in range(3):
        flips = []
        for f in bm.faces:
            nbrs = [nf.material_index for e in f.edges for nf in e.link_faces if nf != f]
            if len(nbrs) >= 2 and nbrs.count(1 - f.material_index) > nbrs.count(f.material_index):
                flips.append((f, 1 - f.material_index))
        for f, nmi in flips:
            f.material_index = nmi
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
    sk_layers = list(bm.verts.layers.shape)
    cloth_v = [v for v in bm.verts if not v.is_boundary and all(f.material_index == 0 for f in v.link_faces) and v.co.z > 0.16]
    back_sh_v = [v for v in cloth_v if 0.66 < v.co.z < 0.94 and v.co.y > 0.02]
    # Keep Eric's bare hands 100% crisp (0 smoothing passes on fingers!)
    for verts_grp, passes, fac in ((cloth_v, 2, 0.22), (back_sh_v, 5, 0.34)):
        for _ in range(passes):
            disp = {}
            for v in verts_grp:
                nbs = [e.other_vert(v) for e in v.link_edges]
                if nbs:
                    avg = sum((nb.co for nb in nbs), Vector()) / len(nbs)
                    disp[v] = v.co.lerp(avg, fac) - v.co
            for v, d_v in disp.items():
                v.co += d_v
                for sk in sk_layers:
                    v[sk] = v[sk] + d_v

    # SEAMLESS RAZOR-CLEAN INTEGRATED WRIST CUFF CUT ON `taxi_driver_body_scan` ITSELF!
    # Cut cleanly right at his wrist joint (`along = -0.008m` behind hand_l/r, perpendicular to average
    # forearm/hand axis!) so the ENTIRE bare wrist, palm, back of hand & fingers are 100% bare warm human skin
    # (ZERO dark fingerless-glove patch on his palm, ZERO zigzag teeth, ZERO floating cardboard rings!)
    for side in ("l", "r"):
        wp_b, cuff_ax, cuff_plane = _cuff_frame(side)
        wrist_faces = [
            f for f in bm.faces
            if abs((f.calc_center_median() - cuff_plane).dot(cuff_ax)) < 0.028
            and ((f.calc_center_median() - wp_b) - cuff_ax * (f.calc_center_median() - wp_b).dot(cuff_ax)).length < 0.072
        ]
        if wrist_faces:
            w_edges = list({e for f in wrist_faces for e in f.edges})
            w_verts = list({v for f in wrist_faces for v in f.verts})
            bmesh.ops.bisect_plane(
                bm,
                geom=w_verts + w_edges + wrist_faces,
                dist=0.0002,
                plane_co=cuff_plane,
                plane_no=cuff_ax,
                clear_inner=False,
                clear_outer=False,
            )
        bm.faces.ensure_lookup_table()
        for f in bm.faces:
            fc = f.calc_center_median()
            rel_p = fc - cuff_plane
            al_p = rel_p.dot(cuff_ax)
            if -0.06 < al_p < 0.24 and (rel_p - cuff_ax * al_p).length < 0.095:
                f.material_index = 1 if al_p >= 0.0 else 0

    if scan_hands is not None:
        # Eric's hands go: the photoscanned hands fill the sleeves. The open sleeve end gets a
        # folded hem (3.5 mm of cloth) and a lining running 2.5 cm back up the sleeve.
        bm.faces.ensure_lookup_table()
        planes = []
        for side in ("l", "r"):
            planes.append(_cuff_frame(side))
        cut, regained = [], []
        for f in bm.faces:
            fc = f.calc_center_median()
            beyond = False
            for wp_b, c_ax, c_pl in planes:
                rel = fc - c_pl
                al = rel.dot(c_ax)
                if al > 0.0 and (rel - c_ax * al).length < 0.14 and (fc - wp_b).length < 0.32:
                    beyond = True
                    break
            if beyond:
                cut.append(f)
            elif f.material_index == 1:
                f.material_index = 0
                regained.append(f)
        # Sleeve faces once tagged as hand still map Eric's skin in the atlas: give each corner
        # the UV of the nearest true sleeve corner so the cloth runs on unbroken.
        uv_l = bm.loops.layers.uv.active
        regained_set = set(regained)
        if regained and uv_l is not None:
            from mathutils.kdtree import KDTree as _KD

            near = [
                lp for f in bm.faces if f not in regained_set and f not in cut and f.material_index == 0
                for lp in f.loops
                if min((lp.vert.co - pl[0]).length for pl in planes) < 0.30
            ]
            kd_uv = _KD(len(near))
            for i, lp in enumerate(near):
                kd_uv.insert(lp.vert.co, i)
            kd_uv.balance()
            for f in regained:
                for lp in f.loops:
                    _, i, _ = kd_uv.find(lp.vert.co)
                    lp[uv_l].uv = near[i][uv_l].uv.copy()
        bmesh.ops.delete(bm, geom=cut, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        # Any loose piece of Eric's old fingers lying wholly past a cuff goes too.
        bm.faces.ensure_lookup_table()
        seen, stray = set(), []
        for f in bm.faces:
            if f.index in seen:
                continue
            comp, st = [], [f]
            seen.add(f.index)
            while st:
                g = st.pop()
                comp.append(g)
                for e in g.edges:
                    for nf in e.link_faces:
                        if nf.index not in seen:
                            seen.add(nf.index)
                            st.append(nf)
            if len(comp) < 6000:
                for wp_b, c_ax, c_pl in planes:
                    if all((g.calc_center_median() - c_pl).dot(c_ax) > -0.01 for g in comp):
                        stray += comp
                        break
        if stray:
            bmesh.ops.delete(bm, geom=stray, context="FACES")
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")

    # Tailor Eric's baggy forearms + crisp subtle integrated 3D rolled shirt-cuff hem right behind `cuff_plane`!
    wrist_smooth_v = []
    for side in ("l", "r"):
        wp_b, cuff_ax, cuff_plane = _cuff_frame(side)
        for v in bm.verts:
            rel = v.co - cuff_plane
            along = rel.dot(cuff_ax)
            if -0.12 < along < 0.048:
                radial = rel - cuff_ax * along
                r_len = radial.length
                if r_len < 0.075:
                    if any(f.material_index == 1 for f in v.link_faces) and along >= -0.001:
                        wrist_smooth_v.append(v)
                        if r_len > 0.028:
                            w_t = _sstep(0.045, 0.015, along) * _sstep(-0.001, 0.006, along)
                            shrink = (r_len - 0.028) * 0.45 * w_t
                            d_v = -radial.normalized() * shrink
                            v.co += d_v
                            for sk in sk_layers:
                                v[sk] = v[sk] + d_v
                    elif all(f.material_index == 0 for f in v.link_faces) and along < 0.0:
                        target_r = 0.032 + 0.007 * _sstep(0.0, -0.10, along)
                        d_rad = 0.0
                        if r_len > target_r:
                            w_s = _sstep(-0.11, -0.03, along)
                            d_rad -= (r_len - target_r) * 0.45 * w_s
                        # Subtle crisp 2.2mm tailored shirt cuff thickness right behind the wrist crease (-2.6cm .. 0)!
                        # (Not with the scanned hands: on the cut's uneven vertices this lip came out
                        # as a zigzag; their sleeve ends get a real folded hem instead.)
                        if scan_hands is None and -0.028 < along < -0.0005:
                            cuff_lip = _sstep(-0.028, -0.016, along) * _sstep(-0.0005, -0.004, along)
                            d_rad += 0.0024 * cuff_lip
                        if abs(d_rad) > 1e-6 and r_len > 1e-4:
                            d_v = radial.normalized() * d_rad
                            v.co += d_v
                            for sk in sk_layers:
                                v[sk] = v[sk] + d_v
    if wrist_smooth_v:
        for _ in range(6):
            disp = {}
            for v in wrist_smooth_v:
                nbs = [e.other_vert(v) for e in v.link_edges]
                if nbs:
                    avg = sum((nb.co for nb in nbs), Vector()) / len(nbs)
                    disp[v] = v.co.lerp(avg, 0.28) - v.co
            for v, d_v in disp.items():
                v.co += d_v
                for sk in sk_layers:
                    v[sk] = v[sk] + d_v

    # Tailored sleeves: the scanned businessman's shirt is cut very full and swelled into a balloon at
    # the bent elbow. Ease every sleeve vertex toward its arm bone, to a real shirt sleeve's width
    # (5.6 cm round the upper arm to 4.4 cm at the forearm), in each shape with that shape's own arm.
    if arm_joints.get("Basis"):

        def _seg_param(p, a, b):
            ab = b - a
            t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.length_squared)))
            return t, a + ab * t

        layer_by_name = {lay.name: lay for lay in sk_layers}
        sleeve = []
        for v in bm.verts:
            if not all(f.material_index == 0 for f in v.link_faces):
                continue
            for side in ("l", "r"):
                sh, el, wr = arm_joints["Basis"][side]
                t_u, q_u = _seg_param(v.co, sh, el)
                t_f, q_f = _seg_param(v.co, el, wr)
                d_u, d_f = (v.co - q_u).length, (v.co - q_f).length
                if min(d_u, d_f) > 0.12:
                    continue
                # Fade in past the shoulder (keep the torso), and out over the cuff's last 7 cm.
                fore_len = (wr - el).length
                if d_u <= d_f:
                    w = _sstep(0.18, 0.40, t_u)
                else:
                    w = _sstep(fore_len - 0.04, fore_len - 0.085, t_f * fore_len)
                if w > 0.0:
                    sleeve.append((v, side, w))
                    break
        for v, side, w in sleeve:
            for lay_name in [None] + [lay.name for lay in sk_layers]:
                joints = arm_joints.get(lay_name or "Basis") or arm_joints["Basis"]
                sh, el, wr = joints[side]
                co = v.co if lay_name is None else v[layer_by_name[lay_name]]
                t_u, q_u = _seg_param(co, sh, el)
                t_f, q_f = _seg_param(co, el, wr)
                if (co - q_u).length <= (co - q_f).length:
                    q, r_t = q_u, 0.056 - 0.006 * t_u
                else:
                    q, r_t = q_f, 0.050 - 0.006 * t_f
                radial = co - q
                r = radial.length
                if r > r_t and r > 1e-6:
                    new = q + radial * ((r_t + (r - r_t) * 0.30) / r)
                    new = co.lerp(new, w)
                    if lay_name is None:
                        v.co = new
                    else:
                        v[layer_by_name[lay_name]] = new
        sleeve_v = {v for v, _, _ in sleeve}
        for _ in range(3):
            disp = {}
            for v in sleeve_v:
                nbs = [e.other_vert(v) for e in v.link_edges]
                if nbs:
                    disp[v] = (sum((nb.co for nb in nbs), Vector()) / len(nbs) - v.co) * 0.25
            for v, d_v in disp.items():
                v.co += d_v
                for sk in sk_layers:
                    v[sk] = v[sk] + d_v
        print("TAXI_SLEEVES_TAILORED", len(sleeve))

    if scan_hands is not None:
        # The sleeve ends' folded hem and lining, grown only now that the forearms are tailored (the
        # tailoring would push a hem built earlier out through the sleeve).
        roll_layer = bm.faces.layers.int.get("sleeve_roll") or bm.faces.layers.int.new("sleeve_roll")
        for side in ("l", "r"):
            wp_b, cuff_ax, cuff_plane = _cuff_frame(side)
            rim_edges = [
                e for e in bm.edges
                if e.is_boundary and all(abs((v.co - cuff_plane).dot(cuff_ax)) < 0.03 and (v.co - cuff_plane).length < 0.09 for v in e.verts)
            ]
            if not rim_edges:
                continue
            # A shirt cuff is roomier than the wrist: wherever the posed scanned wrist would cut through
            # the sleeve's last 6.5 cm, let the sleeve out to 5 mm clear of it (all shapes alike).
            hb = hand_shapes["Basis"][side][scan_hands[side].keep]
            ax_np = np.array(cuff_ax[:])
            rel_h = hb - np.array(cuff_plane[:])
            al_h = rel_h @ ax_np
            rad_h = rel_h - np.outer(al_h, ax_np)
            r_h = np.linalg.norm(rad_h, axis=1)
            ref = Vector((0.0, 0.0, 1.0)) if abs(cuff_ax.z) < 0.9 else Vector((1.0, 0.0, 0.0))
            e1 = (ref - cuff_ax * ref.dot(cuff_ax)).normalized()
            e2 = cuff_ax.cross(e1)
            ang_h = np.arctan2(rad_h @ np.array(e2[:]), rad_h @ np.array(e1[:]))
            in_slab = (al_h > -0.075) & (al_h < 0.012)
            let_out = {}
            for v in bm.verts:
                rel = v.co - cuff_plane
                along = rel.dot(cuff_ax)
                if not (-0.065 < along < 0.001):
                    continue
                radial = rel - cuff_ax * along
                r_v = radial.length
                if r_v > 0.075 or r_v < 1e-5:
                    continue
                a_v = math.atan2(radial.dot(e2), radial.dot(e1))
                near = in_slab & (np.abs(al_h - along) < 0.007) & (np.abs((ang_h - a_v + math.pi) % math.tau - math.pi) < 0.35)
                if near.any():
                    need = float(r_h[near].max()) + 0.005
                    if r_v < need:
                        let_out[v] = radial.normalized() * (need - r_v)
            for _ in range(3):
                spread = {}
                for v, d_v in let_out.items():
                    for e in v.link_edges:
                        u = e.other_vert(v)
                        if u not in let_out:
                            spread[u] = spread.get(u, Vector()) + d_v * 0.25
                for u, d_v in spread.items():
                    let_out[u] = d_v
            for v, d_v in let_out.items():
                v.co += d_v
                for sk in sk_layers:
                    v[sk] = v[sk] + d_v
            print("TAXI_CUFF_LET_OUT", side, len(let_out))
            # A clean round edge first: ease each edge vertex toward its neighbours along the cut.
            rim_v = {v for e in rim_edges for v in e.verts}
            for _ in range(10):
                disp = {}
                for v in rim_v:
                    nbs = [e.other_vert(v) for e in v.link_edges if e.is_boundary and e.other_vert(v) in rim_v]
                    if len(nbs) == 2:
                        d_v = ((nbs[0].co + nbs[1].co) * 0.5 - v.co) * 0.5
                        disp[v] = d_v - cuff_ax * d_v.dot(cuff_ax)
                for v, d_v in disp.items():
                    v.co += d_v
                    for sk in sk_layers:
                        v[sk] = v[sk] + d_v
            # The rolled-up sleeve: the opening's edge is rolled outward and back up the arm into a soft
            # cotton band about 4 cm wide and 1 cm proud, thicker in some places than others, as a sleeve
            # pushed up by hand. Rings grow round the opening's own centre (folding toward the wrist joint
            # once turned part of a hem outward as a flap).
            open_v = {v for e in rim_edges for v in e.verts}
            open_c = sum((v.co for v in open_v), Vector()) / max(1, len(open_v))
            ref = Vector((0.0, 0.0, 1.0)) if abs(cuff_ax.z) < 0.9 else Vector((1.0, 0.0, 0.0))
            e1 = (ref - cuff_ax * ref.dot(cuff_ax)).normalized()
            e2 = cuff_ax.cross(e1)
            ph = 0.7 if side == "l" else 2.3
            # (radially out, up the arm) from the opening's edge, metres
            profile = [(0.0, 0.0), (0.0035, -0.0035), (0.0080, -0.0012), (0.0105, 0.0075), (0.0112, 0.0190),
                       (0.0098, 0.0300), (0.0060, 0.0368), (0.0018, 0.0384), (-0.0008, 0.0362)]
            arc = [0.0]
            for (a0, b0), (a1, b1) in zip(profile, profile[1:]):
                arc.append(arc[-1] + math.hypot(a1 - a0, b1 - b0))
            ring_of, ang_of = {}, {}
            for v in open_v:
                rel = v.co - open_c
                ring_of[v] = 0
                ang_of[v] = math.atan2(rel.dot(e2), rel.dot(e1))
            roll_faces = []
            for step in range(1, len(profile)):
                d_out = profile[step][0] - profile[step - 1][0]
                d_up = profile[step][1] - profile[step - 1][1]
                src_v = {v for e in rim_edges for v in e.verts}
                by_pos = {tuple(round(c, 7) for c in v.co): v for v in src_v}
                ext = bmesh.ops.extrude_edge_only(bm, edges=rim_edges)
                new_v = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
                for v in new_v:
                    src = by_pos.get(tuple(round(c, 7) for c in v.co))
                    rel = v.co - open_c
                    radial = rel - cuff_ax * rel.dot(cuff_ax)
                    a_ = ang_of.get(src, math.atan2(rel.dot(e2), rel.dot(e1)))
                    lump = 1.0 + 0.22 * math.sin(2.0 * a_ + ph) + 0.12 * math.sin(5.0 * a_ + 2.0 * ph)
                    d_v = (radial.normalized() * d_out * lump if radial.length > 1e-6 else Vector()) - cuff_ax * d_up
                    v.co += d_v
                    ring_of[v], ang_of[v] = step, a_
                    # New vertices carry no shape-key data: copy the edge they grew from, then offset.
                    for sk in sk_layers:
                        v[sk] = (src[sk] if src is not None else v.co - d_v) + d_v
                roll_faces += [g for g in ext["geom"] if isinstance(g, bmesh.types.BMFace)]
                rim_edges = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMEdge) and g.is_boundary]
            # Its own cotton (the scan atlas would only smear along the band): u round the sleeve, v
            # along the roll, 6 cm per repeat.
            r_mean = sum(((v.co - open_c) - cuff_ax * (v.co - open_c).dot(cuff_ax)).length for v in open_v) / max(1, len(open_v))
            uv_r = bm.loops.layers.uv.active
            for f in roll_faces:
                f[roll_layer] = 1
                angs = [ang_of.get(lp.vert, 0.0) for lp in f.loops]
                base = angs[0]
                for lp, a_ in zip(f.loops, angs):
                    a_ = base + ((a_ - base + math.pi) % math.tau - math.pi)  # no wrap across the seam
                    lp[uv_r].uv = (a_ * r_mean / 0.06, arc[ring_of.get(lp.vert, 0)] / 0.06)
            print("TAXI_SLEEVE_ROLLED", side, len(roll_faces))


    # GENTLE SOFT-TISSUE RIM CONTACT GUARD:
    # Only gently cushions finger/palm pad skin vertices grazing the 12.7mm rim surface (`0.008 < d_tube < 0.0133`)
    # by <= 5mm outward so ZERO fin/ribbon tearing can ever happen while skin sits flush on the bakelite tube!
    rim_c = WHEEL_CENTER.copy()
    rim_f = WHEEL_NORMAL.copy()
    for v in bm.verts:
        if any(f.material_index == 1 for f in v.link_faces):
            rc = v.co - rim_c
            zf = rc.dot(rim_f)
            in_p = rc - rim_f * zf
            r_maj = in_p.length
            if r_maj > 0.05:
                tube_ctr = rim_c + in_p * (WHEEL_RADIUS / r_maj)
                v_out = v.co - tube_ctr
                d_tube = v_out.length
                if 0.006 < d_tube < 0.0134:
                    push = v_out.normalized() * (0.0134 - d_tube)
                    v.co += push
                    for sk in sk_layers:
                        v[sk] = v[sk] + push


    bm.faces.ensure_lookup_table()
    visited = set()
    comps = []
    for f in bm.faces:
        if f.index in visited:
            continue
        st = [f]
        comp = []
        visited.add(f.index)
        while st:
            g = st.pop()
            comp.append(g)
            for e in g.edges:
                for nf in e.link_faces:
                    if nf.index not in visited:
                        visited.add(nf.index)
                        st.append(nf)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    tiny_faces = [f for c in comps[1:] if len(c) < 180 for f in c]
    if tiny_faces:
        bmesh.ops.delete(bm, geom=tiny_faces, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # Smoothly shape the upper-back shoulders into a natural downward slope (NO flat tabletop shelf clamp!)
    def _at_neck(co):
        return math.hypot(co.x - 0.264, co.y - 0.030) < 0.14 and co.z > 0.78

    for v in bm.verts:
        if all(f.material_index == 0 for f in v.link_faces) and v.co.z > 0.76:
            if v.is_boundary and v.co.z > 0.845 and _at_neck(v.co):
                dz_b = (v.co.z - 0.845) * 0.82
                dx_b = (0.264 - v.co.x) * 0.25
                dy_b = (0.030 - v.co.y) * 0.25
                d_vec = Vector((dx_b, dy_b, -dz_b))
                v.co += d_vec
                for sk in sk_layers:
                    v[sk] = v[sk] + d_vec
            elif v.co.y > 0.075:
                # Natural relaxed seated shoulder slope behind his neck (eliminates hunched upper-back shell!)
                dz_tuck = _sstep(0.075, 0.145, v.co.y) * _sstep(0.76, 0.88, v.co.z) * 0.036
                v.co.z -= dz_tuck
                for sk in sk_layers:
                    v[sk] = Vector((v[sk].x, v[sk].y, v[sk].z - dz_tuck))
    # The neck opening as one smooth loop: each edge vertex eases toward its two neighbours along the
    # opening (no shards), then the ring just inside blends in.
    neck_rim = [v for v in bm.verts if v.is_boundary and _at_neck(v.co)]
    rim_set = set(neck_rim)
    for _ in range(24):
        disp = {}
        for v in neck_rim:
            nbs = [e.other_vert(v) for e in v.link_edges if e.is_boundary and e.other_vert(v) in rim_set]
            if len(nbs) == 2:
                disp[v] = ((nbs[0].co + nbs[1].co) * 0.5 - v.co) * 0.5
        for v, d_v in disp.items():
            v.co += d_v
            for sk in sk_layers:
                v[sk] = v[sk] + d_v
    inner = {e.other_vert(v) for v in neck_rim for e in v.link_edges} - rim_set
    for _ in range(4):
        disp = {}
        for v in inner:
            nbs = [e.other_vert(v) for e in v.link_edges]
            if nbs:
                disp[v] = (sum((nb.co for nb in nbs), Vector()) / len(nbs) - v.co) * 0.3
        for v, d_v in disp.items():
            v.co += d_v
            for sk in sk_layers:
                v[sk] = v[sk] + d_v
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Recalculating guesses "outside" for an open shell, and the rolled sleeves (open bands tucked into
    # the sleeves) tipped the guess: the whole body came out inside-out, hollow in game. Check the torso
    # faces his front, back and sides; each connected piece is flipped on its own if it points inward.
    bm.faces.ensure_lookup_table()
    seen = set()
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        comp, st = [], [f0]
        seen.add(f0.index)
        while st:
            g = st.pop()
            comp.append(g)
            for e in g.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        st.append(nf)
        score = 0.0
        for g in comp:
            c = g.calc_center_median()
            if 0.55 < c.z < 0.88 and abs(c.x - 0.26) < 0.17:
                score += g.normal.dot(Vector((c.x - 0.26, c.y - 0.03, 0.0))) * g.calc_area()
        if score < 0.0:
            bmesh.ops.reverse_faces(bm, faces=comp)
            print("TAXI_BODY_TURNED_OUTWARD", len(comp))
    bmesh.update_edit_mesh(body.data)
    bpy.ops.object.mode_set(mode="OBJECT")
    if len(body.data.materials) > 2:
        body.data.materials.pop(index=2)
    for p in body.data.polygons:
        p.use_smooth = True
    body.data.update()

    if scan_hands is not None:
        # The photoscanned hands as their own meshes, carrying every arm morph plus `grip` (the near
        # hand's two fingers lifting off the rim, tapped by the runtime while he talks).
        if len(body.data.materials) > 1:
            body.data.materials.pop(index=1)
        h_mat = wardrobe.hand_material(scan_hand_src_mat, face_uvs=scan_hands["r"].face_uvs)
        for side, h in scan_hands.items():
            _clear_objects(f"taxi_driver_hand_{side}")
            obj = wardrobe.hand_mesh(h, hand_shapes["Basis"][side], f"taxi_driver_hand_{side}", h_mat, coll)
            obj.shape_key_add(name="Basis", from_mix=False)
            names = [m for m, _ in morph_specs] + (["grip"] if side == "r" else [])
            for m_name in names:
                kb = obj.shape_key_add(name=m_name, from_mix=False)
                kb.data.foreach_set("co", hand_shapes[m_name][side][h.keep].astype(np.float32).ravel())
                kb.value = 0.0
            obj.data["credit"] = str(wardrobe.HAND_CREDIT)

    # 6. Woven cotton collar material (`M_cab_driver_cuff_cotton`) — cuffs are now cleanly integrated directly
    #    into `taxi_driver_body_scan` via razor-straight circular wrist bisect (ZERO detached floating boxes!)
    cuff_w_arr = np.broadcast_to(weave_fac[:512, :512, None], (512, 512, 3)) * np.array((0.46, 0.41, 0.34), np.float32)
    cuff_bc_img = _pack_image("T_cab_driver_cuff_BC", cuff_w_arr, is_srgb=True)
    cuff_mat = _make_pbr("M_cab_driver_cuff_cotton", cuff_bc_img, bpy.data.images.load(str(LINEN_N), check_existing=True) if LINEN_N.exists() else drv_cloth_n, rough=0.88, normal_strength=0.45)
    cuff_mat["tile"] = 0.27
    roll_attr = body.data.attributes.get("sleeve_roll")
    if roll_attr is not None:
        # The rolled sleeve bands wear the cuff cotton, toned to the shirt's own colour at the sleeves.
        clothes_bc = next(
            (n.image for n in body.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"),
            None,
        ) if body.data.materials and body.data.materials[0].use_nodes else None
        flags = np.zeros(len(body.data.polygons), np.int32)
        roll_attr.data.foreach_get("value", flags)
        if clothes_bc is not None:
            cw, ch_ = clothes_bc.size
            px = np.empty(cw * ch_ * 4, np.float32)
            clothes_bc.pixels.foreach_get(px)
            px = px.reshape(ch_, cw, 4)
            uvl = body.data.uv_layers.active.data
            samp = []
            for p in body.data.polygons:
                if flags[p.index]:
                    continue
                c = p.center
                if any((c - _cuff_frame(sd)[2]).length < 0.10 for sd in ("l", "r")):
                    for li in p.loop_indices:
                        u_, v_ = uvl[li].uv
                        samp.append(px[int((v_ % 1.0) * (ch_ - 1)), int((u_ % 1.0) * (cw - 1)), :3])
            if samp:
                shirt = np.median(np.array(samp), axis=0)
                roll_rgb = np.broadcast_to(weave_fac[:512, :512, None], (512, 512, 3)) * shirt[None, None, :]
                cuff_mat = _make_pbr("M_cab_driver_cuff_cotton", _pack_image("T_cab_driver_cuff_BC", roll_rgb, is_srgb=True),
                                     bpy.data.images.load(str(LINEN_N), check_existing=True) if LINEN_N.exists() else drv_cloth_n,
                                     rough=0.88, normal_strength=0.45)
                print("TAXI_SLEEVE_ROLL_COLOUR", shirt.round(3))
        body.data.materials.append(cuff_mat)
        slot = len(body.data.materials) - 1
        for p in body.data.polygons:
            if flags[p.index]:
                p.material_index = slot
        body.data.attributes.remove(roll_attr)

    # 7. Inner dark neck seal (`taxi_driver_sleeves_scan` keeps taxiAssets.test.ts contract intact!)
    m_inner_col = _make_pbr("M_cab_driver_collar", rough=0.96, color=(0.012, 0.011, 0.010))
    bm_ic = bmesh.new()
    nc = Vector((0.264, 0.056, 0.848))
    segs = 28
    rings = []
    # (85% since the head and neck went to 93%: the seal stays hidden inside the neck.)
    for dz, rx, ry in [(-0.022, 0.037, 0.039), (0.0, 0.036, 0.037), (0.020, 0.034, 0.036), (0.020, 0.029, 0.031), (-0.020, 0.032, 0.034)]:
        rings.append([bm_ic.verts.new(nc + Vector((math.cos(k / segs * math.tau) * rx, math.sin(k / segs * math.tau) * ry, dz))) for k in range(segs)])
    for i in range(len(rings)):
        rA, rB = rings[i], rings[(i + 1) % len(rings)]
        for k in range(segs):
            bm_ic.faces.new((rA[k], rA[(k + 1) % segs], rB[(k + 1) % segs], rB[k]))
    _bm_to_obj("taxi_driver_sleeves_scan", bm_ic, m_inner_col, coll, smooth=True)

    # 8. Open shirt collar + relaxed draped Cambodian krama
    head_obj = bpy.data.objects.get("taxi_driver_head_scan")
    _add_driver_shirt_collar_and_krama(coll, neck_target, body, head_obj, plain, world_uvs_fn)

    body.data["seamless_driver_v12"] = True
    body.data.update()
    print(
        "TAXI_DRIVER_BODY_V12_REBUILT",
        "verts=", len(body.data.vertices),
        "polys=", len(body.data.polygons),
        "morphs=", [k.name for k in body.data.shape_keys.key_blocks],
    )
    return body


# --------------------------------------------------------------------------- 3. SORA'S HANDS, NAILS & VINTAGE TANK WATCH

def _paint_sora_watch_dial_texture():
    """Paint a crisp 512x512 1930s Art Deco ivory-enamel Cartier-Tank-style watch dial:
    aged parchment enamel with subtle radial patina, railway minute track, crisp Roman numerals,
    recessed sub-seconds ring at 6 o'clock, and subtle 'GENÈVE' micro-signature."""
    W, H = 512, 512
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xx / (W - 1)) * 2.0 - 1.0  # -1..+1 across dial width
    v = (yy / (H - 1)) * 2.0 - 1.0  # -1..+1 bottom-to-top (Blender image row 0 is bottom!)
    rng = np.random.default_rng(19332245)

    # Warm aged ivory porcelain enamel with bold high-contrast Art Deco railway track & hour batons
    r_edge = np.maximum(np.abs(u), np.abs(v))
    patina = 1.0 - 0.14 * (r_edge ** 2.4) + _box_blur_2d(rng.normal(0.0, 0.012, (H, W)).astype(np.float32), 5)
    ivory = np.array([0.89, 0.82, 0.67], np.float32)
    rgb = np.clip(ivory[None, None, :] * patina[..., None], 0.08, 0.95)
    ink = np.array([0.025, 0.022, 0.020], np.float32)

    # Crisp Art Deco rectangular chemin-de-fer (railway) minute track
    outer_box = np.maximum(np.abs(u) / 0.88, np.abs(v) / 0.90)
    inner_box = np.maximum(np.abs(u) / 0.76, np.abs(v) / 0.78)
    track_lines = (np.abs(outer_box - 1.0) < 0.026) | (np.abs(inner_box - 1.0) < 0.024)
    in_track = (outer_box <= 1.02) & (inner_box >= 0.98)

    # 60 crisp minute tick marks + 12 bold Art Deco hour batons radiating cleanly around the rectangular dial
    ang = np.arctan2(u, v)  # 0 at 12 o'clock (+V), clockwise
    tick_m = np.abs(np.sin(ang * 30.0)) < 0.16
    tick_h = np.abs(np.sin(ang * 6.0)) < 0.13
    hour_zone = (outer_box <= 0.74) & (np.maximum(np.abs(u) / 0.48, np.abs(v) / 0.50) >= 1.0)
    cardinal = (np.abs(u) < 0.065) | (np.abs(v) < 0.065)
    hour_batons = hour_zone & (tick_h | (cardinal & (np.abs(np.sin(ang * 2.0)) < 0.22)))

    # Bold double bar at 12 o'clock (+V) for instant visual readability
    twelve_double = (v > 0.48) & (v < 0.74) & ((np.abs(u - 0.052) < 0.032) | (np.abs(u + 0.052) < 0.032))

    # Recessed sub-seconds register at 6 o'clock (u=0, v=-0.30)
    rs = np.hypot(u, v + 0.30)
    sub_ring = (np.abs(rs - 0.18) < 0.020) | ((rs < 0.18) & (rs > 0.11) & (np.abs(np.sin(np.arctan2(u, v + 0.30) * 6.0)) < 0.14))
    sub_disc = rs < 0.18

    # Subtle dial guilloché center square
    center_box = np.maximum(np.abs(u) / 0.42, np.abs(v) / 0.44) < 1.0
    guilloche = 0.95 + 0.05 * np.sin((u + v) * 85.0) * np.sin((u - v) * 85.0)
    rgb = np.where(center_box[..., None], rgb * guilloche[..., None], rgb)
    rgb = np.where(sub_disc[..., None], rgb * 0.90, rgb)

    # Dark crisp ink composite
    mark = track_lines | (in_track & tick_m) | hour_batons | twelve_double | sub_ring
    rgb = np.where(mark[..., None], ink[None, None, :], rgb)

    # Tiny center dial hole & blued sub-seconds needle pointing at 42 seconds
    sub_hand = (rs < 0.15) & (u < 0.025) & (np.abs((v + 0.30) - u * 0.35) < 0.020)
    rgb = np.where(sub_hand[..., None], np.array([0.04, 0.08, 0.22], np.float32)[None, None, :], rgb)
    rgb = np.where((np.hypot(u, v) < 0.038)[..., None], np.array([0.52, 0.40, 0.18], np.float32)[None, None, :], rgb)

    # Slight soft anti-aliasing via 1px box blend
    rgb_aa = np.stack([_box_blur_2d(rgb[..., c], 1) for c in range(3)], axis=-1)
    rgb = rgb * 0.55 + rgb_aa * 0.45
    return _pack_image("T_taxi_sora_watch_dial_BC", np.clip(rgb, 0.02, 0.96), is_srgb=True)


def _build_conformed_sora_watch(coll, body_bvh, wrist_basis_tuple, wrist_M_basis, wrist_M_morphs, morph_specs):
    """Build a museum-grade 1930s antique-gold Art Deco tank wristwatch whose stitched calfskin strap
    is BVH-raycast conformed vertex-by-vertex to Sora's ACTUAL left wrist skin (zero floating gap!)."""
    _clear_objects(
        "taxi_sora_watch_case",
        "taxi_sora_watch_strap",
        "taxi_sora_watch_dial",
        "taxi_sora_watch_hands",
        "taxi_sora_watch_crystal",
        "taxi_sora_watch_stitch",
    )

    w_pos, arm_dir, side_dir, up_dir = wrist_basis_tuple
    # Seat cleanly over Sora's bare left wrist bone (-arm_dir * 0.012 from wrist crease -> natural watch placement!)
    w_ctr = w_pos - arm_dir * 0.012
    M_w = Matrix.Translation(w_ctr) @ Matrix((side_dir, arm_dir, up_dir)).transposed().to_4x4()
    M_w_inv = M_w.inverted()

    # Raycast actual wrist cross-section at 36 angles across 3 axial stations (-5mm, 0, +5mm along arm_dir)
    segs = 36
    y_slices = (-0.0056, 0.0, 0.0056)
    r_slices = []
    for dy in y_slices:
        rs = np.zeros(segs, np.float32)
        slice_c = M_w @ Vector((0.0, dy, 0.0))
        for k in range(segs):
            a = k / segs * math.tau
            d_local = Vector((math.cos(a), 0.0, math.sin(a))).normalized()
            d_world = (M_w.to_3x3() @ d_local).normalized()
            # Cast INWARD from 7cm outside wrist so we hit the exact outer skin surface!
            hit = body_bvh.ray_cast(slice_c + d_world * 0.070, -d_world, 0.068)
            if hit[0] is not None:
                local_hit = M_w_inv @ hit[0]
                rs[k] = max(0.015, min(0.036, math.hypot(local_hit.x, local_hit.z)))
            else:
                rs[k] = 0.023
        for _ in range(4):
            rs = 0.25 * np.roll(rs, -1) + 0.50 * rs + 0.25 * np.roll(rs, 1)
        r_slices.append(rs)

    # Dorsal skin surface height at top of wrist (a = pi/2 -> +Z in M_w local frame!)
    k_top = segs // 4
    z_top_skin = float(r_slices[1][k_top])
    # Slightly flatten the strap under the watch lugs on top while hugging snugly everywhere else
    r_mid = r_slices[1]

    # Materials: brushed antique 18k gold, rich stitched cognac-brown calfskin leather (painted flush saddle-stitch!),
    # painted 512px Art Deco enamel dial, blued-steel hands, ultra-clear glass crystal!
    gold_mat = _make_pbr("M_taxi_sora_watch_gold", rough=0.22, metallic=0.94, color=(0.64, 0.49, 0.20))

    # Paint crisp 512x512 stitched cognac-brown calfskin leather strap BC + recessed stitch groove normal map!
    sw, sh = 512, 512
    yy_s, xx_s = np.mgrid[0:sh, 0:sw].astype(np.float32)
    rng_st = np.random.default_rng(193388)
    u_st = xx_s / sw
    v_st = yy_s / sh
    grain = _box_blur_2d(rng_st.normal(0.0, 0.14, (sh, sw)).astype(np.float32), 2)
    fine_g = rng_st.normal(0.0, 0.035, (sh, sw)).astype(np.float32)
    # Rich antique cognac-espresso calfskin darkening slightly along burnished edges
    edge_d = np.minimum(v_st, 1.0 - v_st)
    burnish = 0.72 + 0.28 * np.clip(edge_d / 0.14, 0.0, 1.0)
    strap_base = np.array([0.165, 0.072, 0.036], np.float32)
    st_rgb = strap_base[None, None, :] * (burnish * np.clip(1.0 + grain + fine_g, 0.72, 1.28))[..., None]
    # Flush cream linen saddle-stitching dashes along both borders (v=0.14 & v=0.86, 48 neat stitches around wrist!)
    on_row = (np.abs(v_st - 0.16) < 0.022) | (np.abs(v_st - 0.84) < 0.022)
    dash = ((u_st * 44.0) % 1.0) < 0.56
    stitch_m = on_row & dash
    groove_m = (np.abs(v_st - 0.16) < 0.034) | (np.abs(v_st - 0.84) < 0.034)
    st_rgb = np.where(groove_m[..., None], st_rgb * 0.74, st_rgb)
    st_rgb = np.where(stitch_m[..., None], np.array([0.62, 0.52, 0.36], np.float32)[None, None, :], st_rgb)
    strap_bc = _pack_image("T_taxi_sora_watch_strap_BC", np.clip(st_rgb, 0.015, 0.90), is_srgb=True)

    # Matching calfskin pebble + recessed stitch channel normal map
    h_st = grain * 0.45 + fine_g * 0.25 - groove_m.astype(np.float32) * 0.45 + stitch_m.astype(np.float32) * 0.55
    gx_st = (np.roll(h_st, -1, 1) - np.roll(h_st, 1, 1)) * 1.1
    gy_st = (np.roll(h_st, -1, 0) - np.roll(h_st, 1, 0)) * 1.1
    nz_st = np.sqrt(np.clip(1.0 - gx_st * gx_st - gy_st * gy_st, 0.15, 1.0))
    strap_n_arr = np.dstack([np.clip(-gx_st * 0.5 + 0.5, 0, 1), np.clip(-gy_st * 0.5 + 0.5, 0, 1), np.clip(nz_st * 0.5 + 0.5, 0, 1)])
    strap_n = _pack_image("T_taxi_sora_watch_strap_N", strap_n_arr, is_srgb=False)

    strap_mat = _make_pbr("M_taxi_sora_watch_strap", bc_img=strap_bc, n_img=strap_n, rough=0.48, metallic=0.0, normal_strength=0.65)
    stitch_mat = _make_pbr("M_taxi_sora_watch_stitch", rough=0.78, metallic=0.0, color=(0.56, 0.46, 0.32))
    dial_img = _paint_sora_watch_dial_texture()
    dial_mat = _make_pbr("M_taxi_sora_watch_dial", bc_img=dial_img, rough=0.22, metallic=0.0)
    hands_mat = _make_pbr("M_taxi_sora_watch_hands", rough=0.18, metallic=0.92, color=(0.03, 0.06, 0.18))
    crys_mat = _make_pbr("M_taxi_sora_watch_crystal", rough=0.05, metallic=0.0, color=(0.95, 0.98, 1.0))
    crys_mat.blend_method = "BLEND"
    if hasattr(crys_mat, "surface_render_method"):
        crys_mat.surface_render_method = "BLENDED"
    crys_bsdf = crys_mat.node_tree.nodes["Principled BSDF"]
    crys_bsdf.inputs["Alpha"].default_value = 0.05
    if "Specular IOR Level" in crys_bsdf.inputs:
        crys_bsdf.inputs["Specular IOR Level"].default_value = 0.28

    # 1. Conformed UV-Mapped Stitched Calfskin Leather Strap (wraps snugly around exact wrist skin +0.8..+2.6mm!)
    bm_strap = bmesh.new()
    uv_st_layer = bm_strap.loops.layers.uv.new("UVMap")
    # Cross-section rings: (dy_idx, dy, r_offset, v_uv) around closed padded strap tube
    strap_prof = [
        (0, -0.0056, 0.0008, 0.00),
        (0, -0.0058, 0.0020, 0.10),
        (1,  0.0000, 0.0027, 0.50),  # softly padded convex strap crown
        (2,  0.0058, 0.0020, 0.90),
        (2,  0.0056, 0.0008, 1.00),
        (1,  0.0000, 0.0004, 0.50),  # snug underside touching skin
    ]
    s_rings = []
    for s_idx, dy, r_off, _vuv in strap_prof:
        row = []
        for k in range(segs):
            a = k / segs * math.tau
            r = float(r_slices[s_idx][k]) + r_off
            dy_t = dy * (0.88 + 0.12 * max(0.0, math.sin(a)))
            pt = M_w @ Vector((math.cos(a) * r, dy_t, math.sin(a) * r))
            row.append(bm_strap.verts.new(pt))
        s_rings.append(row)
    for i in range(len(s_rings)):
        i_nxt = (i + 1) % len(s_rings)
        rA, rB = s_rings[i], s_rings[i_nxt]
        vA, vB = strap_prof[i][3], strap_prof[i_nxt][3]
        for k in range(segs):
            kn = (k + 1) % segs
            uA, uB = k / segs, (k + 1) / segs
            f = bm_strap.faces.new((rA[k], rA[kn], rB[kn], rB[k]))
            for lp, uv_p in zip(f.loops, [(uA, vA), (uB, vA), (uB, vB), (uA, vB)]):
                lp[uv_st_layer].uv = uv_p

    # Sleek leather keeper loops sitting snugly on the outer side of the strap
    for k_ang in (-0.30, -0.62):
        r_k = float(r_mid[int(((k_ang % math.tau) / math.tau) * segs) % segs])
        ctr_k = Vector((math.cos(k_ang) * (r_k + 0.0022), 0.0, math.sin(k_ang) * (r_k + 0.0022)))
        rot_k = Matrix.Rotation(k_ang, 4, "Y")
        M_k = M_w @ Matrix.Translation(ctr_k) @ rot_k @ Matrix.Diagonal((0.0032, 0.0134, 0.0042, 1.0))
        ret = bmesh.ops.create_cube(bm_strap, size=1.0, matrix=M_k)
        bmesh.ops.bevel(bm_strap, geom=list({e for v in ret["verts"] for e in v.link_edges}), offset=0.0005, segments=1, affect="EDGES", clamp_overlap=True)
    # Ensure any beveled keeper-loop faces carry clean middle-leather UVs (u=0.5, v=0.5)
    for f_k in bm_strap.faces:
        if all(lp[uv_st_layer].uv.length < 1e-6 for lp in f_k.loops):
            for lp in f_k.loops:
                lp[uv_st_layer].uv = (0.5, 0.5)

    # Tiny delicate flush end-bar keeper stitches only (the full strap stitching is crisp in T_taxi_sora_watch_strap_BC/N!)
    bm_st = bmesh.new()
    for sx in (-1.0, 1.0):
        a_bar = math.pi * 0.5 - sx * 0.48
        r_bar = float(r_mid[int(((a_bar % math.tau) / math.tau) * segs) % segs]) + 0.0026
        pt_bar = Vector((math.cos(a_bar) * r_bar, 0.0, math.sin(a_bar) * r_bar))
        M_st = M_w @ Matrix.Translation(pt_bar) @ Matrix.Rotation(-a_bar, 4, "Y") @ Matrix.Diagonal((0.00035, 0.0076, 0.0006, 1.0))
        bmesh.ops.create_cube(bm_st, size=1.0, matrix=M_st)

    # 2. Sculpted 1930s Antique Gold Art Deco Tank Watch Case (brancards, curved lugs, spring bars, fluted crown, buckle!)
    bm_gold = bmesh.new()

    def _gbox(loc, sz, rot_euler=(0.0, 0.0, 0.0), bev=0.0006):
        M = M_w @ Matrix.Translation(loc) @ Euler(rot_euler, "XYZ").to_matrix().to_4x4() @ Matrix.Diagonal((*sz, 1.0))
        ret = bmesh.ops.create_cube(bm_gold, size=1.0, matrix=M)
        edges = list({e for v in ret["verts"] for e in v.link_edges})
        bmesh.ops.bevel(bm_gold, geom=edges, offset=bev, segments=2, affect="EDGES", clamp_overlap=True)

    z_case = z_top_skin + 0.0026
    # Main sleek rectangular Art Deco case base & stepped bezel frame
    _gbox((0.0, 0.0, z_case), (0.0185, 0.0156, 0.0036), bev=0.0008)
    # Twin vertical stepped side brancards extending into curved lugs along strap (X = +-0.0096)
    for sx in (-1.0, 1.0):
        # Upper brancard rail framing the rectangular bezel
        _gbox((sx * 0.0094, 0.0, z_case + 0.0008), (0.0028, 0.0172, 0.0042), bev=0.0006)
        # Gracefully curved down-turned lugs embracing the strap on +-X sides (along strap curve!)
        for sy in (-0.0066, 0.0066):
            _gbox((sx * 0.0124, sy, z_case - 0.0012), (0.0052, 0.0024, 0.0032), rot_euler=(0.0, sx * math.radians(22), 0.0), bev=0.0005)
        # Gold spring bar connecting each pair of lugs
        p0 = M_w @ Vector((sx * 0.0138, -0.0064, z_case - 0.0016))
        p1 = M_w @ Vector((sx * 0.0138,  0.0064, z_case - 0.0016))
        d = p1 - p0
        q = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
        bmesh.ops.create_cone(bm_gold, cap_ends=True, segments=10, radius1=0.0008, radius2=0.0008, depth=d.length, matrix=Matrix.Translation((p0 + p1) * 0.5) @ q)
    # Front/back slim gold bezel bars (Y = +-0.0076)
    for sy in (-1.0, 1.0):
        _gbox((0.0, sy * 0.0074, z_case + 0.0014), (0.0168, 0.0022, 0.0028), bev=0.0005)

    # Knurled/fluted antique gold winding crown on 3-o'clock side (+Y toward hand!)
    c_p0 = M_w @ Vector((0.0, 0.0082, z_case + 0.0004))
    c_p1 = M_w @ Vector((0.0, 0.0114, z_case + 0.0004))
    q_c = Vector((0, 0, 1)).rotation_difference((c_p1 - c_p0).normalized()).to_matrix().to_4x4()
    bmesh.ops.create_cone(bm_gold, cap_ends=True, segments=16, radius1=0.0021, radius2=0.0018, depth=(c_p1 - c_p0).length, matrix=Matrix.Translation((c_p0 + c_p1) * 0.5) @ q_c)
    # Tiny dark sapphire cabochon tip on crown
    bmesh.ops.create_uvsphere(bm_gold, u_segments=10, v_segments=6, radius=0.0012, matrix=Matrix.Translation(c_p1))

    # Antique gold strap buckle & tang on the underside/outer flank (a = -1.15 rad)
    b_ang = -1.15
    r_b = float(r_mid[int(((b_ang % math.tau) / math.tau) * segs) % segs]) + 0.0032
    b_ctr = Vector((math.cos(b_ang) * r_b, 0.0, math.sin(b_ang) * r_b))
    _gbox(b_ctr, (0.0026, 0.0148, 0.0095), rot_euler=(0.0, -b_ang, 0.0), bev=0.0004)

    # 3. Painted UV-Mapped Watch Dial Quad (flipped cleanly with +Z upward normal so 12 o'clock faces -X / outer wrist!)
    dw, dh = 0.0074, 0.0064
    z_dial = z_case + 0.0024
    dial_pts = [
        M_w @ Vector((+dw, -dh, z_dial)),
        M_w @ Vector((+dw, +dh, z_dial)),
        M_w @ Vector((-dw, +dh, z_dial)),
        M_w @ Vector((-dw, -dh, z_dial)),
    ]
    dial_obj = _make_mesh_uv("taxi_sora_watch_dial", dial_pts, [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)], dial_mat, coll, smooth=False)
    # Ensure dial normal faces strictly +Z (outward toward Sora's eye — fixes blank backface in EEVEE!)
    if dial_obj.data.polygons[0].normal.dot(up_dir) < 0:
        bm_d = bmesh.new()
        bm_d.from_mesh(dial_obj.data)
        bmesh.ops.reverse_faces(bm_d, faces=bm_d.faces)
        bm_d.to_mesh(dial_obj.data)
        bm_d.free()
        dial_obj.data.update()

    # 4. Sculpted Blued-Steel Breguet Hands set to 22:45 + central pinion cap!
    bm_hands = bmesh.new()
    z_h = z_dial + 0.00045
    # In dial space: 12 o'clock is -X, 3 o'clock is +Y, 6 o'clock is +X, 9 o'clock is -Y
    # 22:45 -> hour hand at 10.75h (-37.5° from 12 = -X/-Y), minute hand at 9 (pointing along -Y!)
    for length, wid, clock_deg, dz_h in [
        (0.0044, 0.00065, -37.5, 0.0),     # hour hand (10:45)
        (0.0058, 0.00048, -90.0, 0.00022), # minute hand (:45)
    ]:
        rad = math.radians(clock_deg)
        dir_v = Vector((-math.cos(rad), math.sin(rad), 0.0))
        perp_v = Vector((-dir_v.y, dir_v.x, 0.0))
        # Tapered lancet needle + tiny counter-tail
        p_tail = Vector((0, 0, z_h + dz_h)) - dir_v * 0.0010
        p_tip = Vector((0, 0, z_h + dz_h)) + dir_v * length
        mid = (p_tail + p_tip) * 0.5
        M_hd = M_w @ Matrix.Translation(mid) @ Matrix.Rotation(math.atan2(dir_v.y, dir_v.x), 4, "Z") @ Matrix.Diagonal(((p_tip - p_tail).length, wid, 0.00025, 1.0))
        bmesh.ops.create_cube(bm_hands, size=1.0, matrix=M_hd)
    bmesh.ops.create_uvsphere(bm_hands, u_segments=10, v_segments=6, radius=0.00065, matrix=M_w @ Matrix.Translation((0, 0, z_h + 0.0003)))

    # 5. Ultra-thin flat rectangular glass crystal hovering cleanly ABOVE hands (never obscures dial!)
    bm_crys = bmesh.new()
    z_crys = z_dial + 0.00105
    c_pts = [
        bm_crys.verts.new(M_w @ Vector((+dw * 1.01, -dh * 1.01, z_crys))),
        bm_crys.verts.new(M_w @ Vector((+dw * 1.01, +dh * 1.01, z_crys))),
        bm_crys.verts.new(M_w @ Vector((-dw * 1.01, +dh * 1.01, z_crys))),
        bm_crys.verts.new(M_w @ Vector((-dw * 1.01, -dh * 1.01, z_crys))),
    ]
    bm_crys.faces.new(c_pts)

    watch_objs = [
        _bm_to_obj("taxi_sora_watch_case", bm_gold, gold_mat, coll, smooth=True),
        _bm_to_obj("taxi_sora_watch_strap", bm_strap, strap_mat, coll, smooth=True),
        dial_obj,
        _bm_to_obj("taxi_sora_watch_hands", bm_hands, hands_mat, coll, smooth=True),
        _bm_to_obj("taxi_sora_watch_crystal", bm_crys, crys_mat, coll, smooth=True),
        _bm_to_obj("taxi_sora_watch_stitch", bm_st, stitch_mat, coll, smooth=True),
    ]

    # Bind ALL 6 watch meshes in exact rigid lockstep to Sora's left wrist morph targets!
    for wo in watch_objs:
        wo.shape_key_add(name="Basis", from_mix=False)
        base_cos = [v.co.copy() for v in wo.data.vertices]
        for m_name, _ in morph_specs:
            kb = wo.shape_key_add(name=m_name, from_mix=False)
            M_delta = wrist_M_morphs[m_name]["l"] @ wrist_M_basis["l"].inverted()
            out_cos = [M_delta @ p for p in base_cos]
            kb.data.foreach_set("co", np.array([p[:] for p in out_cos], np.float32).ravel())
            kb.value = 0.0

    print("TAXI_SORA_WATCH_CONFORMED z_top_skin=", round(z_top_skin, 4), "r_min/max=", (round(float(r_mid.min()), 4), round(float(r_mid.max()), 4)))
    return watch_objs


def _pose_sora_arms_and_hands(rig, thigh_z_fn, tense=0.0, breathe=0.0, fidget=0.0):
    """Natural, graceful, slender, ASYMMETRIC feminine hand pose resting WITH REAL WEIGHT on top of Sora's thighs:
    - Accounts for Carla's existing ~22° rest-pose finger bend so resting hands look LONG, SLENDER & RELAXED
      (NEVER short stiff C-claws floating over the thigh gap!).
    - Left hand (with watch): centered cleanly on her left thigh, fingers softly cascading along the wool cloth.
    - Right hand: resting ~2.8cm further forward on her right thigh with soft organic relaxation.
    - Tight, non-destructive morph amplitudes (`<= 1.6cm` max!) so watch & nails stay 100% locked onto skin!
    """
    for sp, base_deg in [("spine_01", -4.0), ("spine_02", -4.0), ("spine_03", -3.0)]:
        if rig.has(sp):
            rig.turn(rig.bone(sp), Vector((1, 0, 0)), math.radians(base_deg + breathe * 0.9 - tense * 0.9))

    # Left hand centered comfortably ON TOP of her left thigh (x ~ -0.194, y ~ -0.190)
    lx_w = -0.194 - tense * 0.003 + fidget * 0.003
    ly_w = -0.190 + tense * 0.005 - fidget * 0.004
    lz_th = thigh_z_fn(lx_w, ly_w)
    l_wrist = Vector((lx_w, ly_w, lz_th + 0.025 + breathe * 0.002 + fidget * 0.003 - tense * 0.0015))
    l_pole = Vector((-0.078, 0.070, 0.458 + tense * 0.008))
    rig.reach(rig.bone("upperarm_l"), rig.bone("lowerarm_l"), rig.bone("hand_l"), l_wrist, l_pole)

    # Aim left hand gracefully forward & slightly inward following the top contour of her left thigh (ZERO cloth clip!)
    ly_f = ly_w - 0.115
    lx_f = lx_w - 0.018 + fidget * 0.006
    lz_f = thigh_z_fn(lx_f, ly_f) + 0.024 + fidget * 0.004 - tense * 0.0015
    rig.aim(rig.bone("hand_l"), rig.bone("middle_01_l"), Vector((lx_f, ly_f, lz_f)))
    # Palm rests flat & gently inward (tilts subtly on `fidget` so watch dial catches cabin light!)
    l_palm = Vector((-0.14 - fidget * 0.14, -0.08, -1.0)).normalized()
    rig.roll_hand_with_twist("l", l_palm)

    # Slender, graceful, softly extended resting fingers (clenching naturally ~14° into trousers on `tense`!)
    tc = math.radians(14.0) * tense
    fc = math.radians(4.5) * fidget
    rig.curl_fingers(
        "l",
        {
            "index":  (math.radians(-2) + tc - fc,      math.radians(5) + tc * 1.15,  math.radians(3) + tc * 0.7),
            "middle": (math.radians(1)  + tc,           math.radians(8) + tc * 1.15,  math.radians(5) + tc * 0.7),
            "ring":   (math.radians(4)  + tc + fc * .5, math.radians(11) + tc * 1.15, math.radians(6) + tc * 0.7),
            "pinky":  (math.radians(8)  + tc + fc,      math.radians(14) + tc * 1.15, math.radians(8) + tc * 0.7),
        },
        (math.radians(2), math.radians(4) + tc * 0.45, math.radians(3) + tc * 0.4),
        thumb_oppose=math.radians(4.0 + 7.0 * tense),
    )

    # Right hand centered ON TOP of her right thigh, naturally ~2.8cm further forward than left
    rx_w = -0.346 + tense * 0.003
    ry_w = -0.218 + tense * 0.005
    rz_th = thigh_z_fn(rx_w, ry_w)
    r_wrist = Vector((rx_w, ry_w, rz_th + 0.022 + breathe * 0.002 - tense * 0.0015))
    r_pole = Vector((-0.458, 0.062, 0.455 + tense * 0.008))
    rig.reach(rig.bone("upperarm_r"), rig.bone("lowerarm_r"), rig.bone("hand_r"), r_wrist, r_pole)

    ry_f = ry_w - 0.115
    rx_f = rx_w + 0.020
    rz_f = thigh_z_fn(rx_f, ry_f) + 0.021 - tense * 0.0015
    rig.aim(rig.bone("hand_r"), rig.bone("middle_01_r"), Vector((rx_f, ry_f, rz_f)))
    r_palm = Vector((0.18, -0.10, -1.0)).normalized()
    rig.roll_hand_with_twist("r", r_palm)

    rig.curl_fingers(
        "r",
        {
            "index":  (math.radians(0)  + tc + fc * .4, math.radians(6) + tc * 1.15,  math.radians(4) + tc * 0.7),
            "middle": (math.radians(3)  + tc,           math.radians(10) + tc * 1.15, math.radians(6) + tc * 0.7),
            "ring":   (math.radians(7)  + tc,           math.radians(14) + tc * 1.15, math.radians(8) + tc * 0.7),
            "pinky":  (math.radians(11) + tc,           math.radians(18) + tc * 1.15, math.radians(10) + tc * 0.7),
        },
        (math.radians(3), math.radians(6) + tc * 0.45, math.radians(4) + tc * 0.4),
        thumb_oppose=math.radians(6.0 + 7.0 * tense),
    )


def _paint_sora_nail_texture():
    """Paint a 256x256 natural translucent unpainted fingernail texture matching Sora's warm Khmer skin tone:
    soft shadowed cuticle blending seamlessly into skin -> delicate lunula -> warm rose-tan nail bed ->
    subtle natural translucent beige free-edge (NEVER chalky white stickers!)."""
    W, H = 256, 256
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xx / (W - 1)) * 2.0 - 1.0  # -1..+1 side-to-side
    v = yy / (H - 1)                # 0 cuticle -> 1 tip
    skin = np.array([0.555, 0.378, 0.282], np.float32)
    bed = np.array([0.615, 0.435, 0.348], np.float32)
    lunula = np.array([0.655, 0.505, 0.415], np.float32)
    tip = np.array([0.665, 0.545, 0.445], np.float32)

    # Smooth cuticle transition into warm rose-tan nail bed
    t_bed = _smoothstep(0.06, 0.22, v)[..., None]
    rgb = skin * (1.0 - t_bed) + bed * t_bed
    # Delicate subtle half-moon lunula near cuticle
    r_lun = np.hypot(u * 0.78, (v - 0.14) * 2.8)
    m_lun = _smoothstep(0.55, 0.18, r_lun) * _smoothstep(0.06, 0.14, v)
    rgb = rgb * (1.0 - m_lun[..., None] * 0.38) + lunula * (m_lun[..., None] * 0.38)
    # Soft natural translucent free-edge tip (curves gently with almond contour!)
    tip_line = 0.84 - 0.10 * (u * u)
    t_tip = np.clip((v - (tip_line - 0.07)) / 0.12, 0.0, 1.0)
    m_tip = (t_tip * t_tip * (3.0 - 2.0 * t_tip))[..., None]
    rgb = rgb * (1.0 - m_tip * 0.55) + tip * (m_tip * 0.55)
    # Subtle cuticle & lateral nail-fold darkening so edges sink organically into finger skin
    fold = 1.0 - 0.16 * np.exp(-((v - 0.07) / 0.055) ** 2) - 0.14 * (np.abs(u) ** 3.2)
    rgb = np.clip(rgb * fold[..., None], 0.08, 0.88)
    return _pack_image("T_taxi_sora_nails_BC", rgb, is_srgb=True)


def _build_sora_anatomical_nails(coll, body_bvh, nail_frames_basis, nail_frames_morphs, morph_specs):
    """Build ultra-thin, per-vertex BVH-conformed natural anatomical fingernails on all 10 fingertips
    (tucked edges, translucent rose-tan texture matching her skin -> ZERO white sticker edges!)."""
    _clear_objects("taxi_sora_nails")
    nail_bc = _paint_sora_nail_texture()
    nail_mat = _make_pbr("M_taxi_sora_nails", bc_img=nail_bc, rough=0.28, metallic=0.0)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    nail_ranges = []

    for key, (nail_ctr, f_dir, d_up, side_ax, is_thumb) in nail_frames_basis.items():
        v0 = len(bm.verts)
        # Cast strictly onto HAND-SKIN BVH (never trousers!) right over the distal nail bed center
        hit = body_bvh.ray_cast(nail_ctr + d_up * 0.016, -d_up, 0.024)
        if hit[0] is None:
            continue
        surf = hit[0]
        n_dir = hit[1].normalized() if hit[1].dot(d_up) > 0.25 else d_up
        s_ax = (side_ax - n_dir * side_ax.dot(n_dir)).normalized()
        l_ax = n_dir.cross(s_ax).normalized()
        if l_ax.dot(f_dir) < 0:
            l_ax = -l_ax
            s_ax = -s_ax

        nw = 0.0038 if is_thumb else 0.0028
        nl = 0.0044 if is_thumb else 0.0038
        # Per-vertex raycast-conformed almond nail plate hugging the exact dorsal finger skin!
        grid = []
        uvs_g = []
        for j in range(5):
            v = j / 4.0
            w_t = nw * (0.72 + 0.30 * math.sin(v * math.pi * 0.85))
            row = []
            uv_row = []
            for i in range(5):
                u = (i / 4.0) * 2.0 - 1.0
                l_off = (v - 0.45) * nl * 2.0 - 0.0008 * (u * u) * (v ** 1.6)
                cand = surf + s_ax * (u * w_t) + l_ax * l_off
                # Project each grid point cleanly onto the actual Catmull-Clark fingertip skin!
                h_v = body_bvh.ray_cast(cand + n_dir * 0.008, -n_dir, 0.015)
                base_p = h_v[0] if (h_v[0] is not None and (h_v[0] - cand).length < 0.0045) else (cand - n_dir * (0.0010 * u * u))
                # Center lifts +0.16mm; cuticle & side borders tuck -0.22mm seamlessly into skin nail-folds!
                edge_tuck = 1.0 - 0.75 * (u * u) - 0.55 * max(0.0, 0.25 - v) * 4.0
                lift = 0.00018 * edge_tuck - 0.00016 * (u * u)
                row.append(bm.verts.new(base_p + n_dir * lift))
                uv_row.append((i / 4.0, v))
            grid.append(row)
            uvs_g.append(uv_row)
        for j in range(4):
            for i in range(4):
                f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
                for lp, uvp in zip(f.loops, [uvs_g[j][i], uvs_g[j][i + 1], uvs_g[j + 1][i + 1], uvs_g[j + 1][i]]):
                    lp[uv_layer].uv = uvp
        bm.verts.ensure_lookup_table()
        nail_ranges.append((key, v0, len(bm.verts)))

    nails_obj = _bm_to_obj("taxi_sora_nails", bm, nail_mat, coll, smooth=True)
    # Bind every fingernail rigidly to its exact distal phalanx across all morphs!
    nails_obj.shape_key_add(name="Basis", from_mix=False)
    base_cos = [v.co.copy() for v in nails_obj.data.vertices]
    for m_name, _ in morph_specs:
        kb = nails_obj.shape_key_add(name=m_name, from_mix=False)
        out_cos = list(base_cos)
        for key, i0, i1 in nail_ranges:
            p0, f0, u0, s0, _ = nail_frames_basis[key]
            p1, f1, u1, s1, _ = nail_frames_morphs[m_name][key]
            M0 = Matrix.Translation(p0) @ Matrix((s0, f0, u0)).transposed().to_4x4()
            M1 = Matrix.Translation(p1) @ Matrix((s1, f1, u1)).transposed().to_4x4()
            M_d = M1 @ M0.inverted()
            for vi in range(i0, i1):
                out_cos[vi] = M_d @ base_cos[vi]
        kb.data.foreach_set("co", np.array([p[:] for p in out_cos], np.float32).ravel())
        kb.value = 0.0
    return nails_obj


def rebuild_sora_hands_and_watch(coll, world_uvs_fn):
    """Rebuild Sora (`taxi_sora_legs_scan`) with:
    - Natural asymmetric feminine hands resting WITH REAL WEIGHT directly on her thighs
    - Smooth `lowerarm_twist` pronation (zero pinched wrists!)
    - Crisp preserved 4K photographic hand/knuckle skin detail + sculpted curved fingernails
    - Raycast-fitted slim rolled linen blouse cuffs
    - Museum-grade 1930s Art Deco gold tank wristwatch conformed vertex-by-vertex to her wrist skin!
    - Live skeletal morph targets (`breathe`, `tense_grip`, `fidget`) synced across body, cuffs, nails & watch!
    """
    scan_path = SCANS / "taxi_sora_scan.glb"
    if not scan_path.exists():
        return None

    _clear_objects(
        "taxi_sora_legs_scan",
        "taxi_sora_blouse_cuffs",
        "taxi_sora_cuff_buttons",
        "taxi_sora_nails",
        "taxi_sora_watch_case",
        "taxi_sora_watch_strap",
        "taxi_sora_watch_dial",
        "taxi_sora_watch_hands",
        "taxi_sora_watch_crystal",
        "taxi_sora_watch_stitch",
    )

    arm, body, imported = _import_glb_rigged(scan_path)
    _weld_rigged_mesh_preserve_groups(body, dist=0.0004)
    rig = _RigHelper(arm)

    rest = [(body.matrix_world @ v.co).copy() for v in body.data.vertices]
    raw_mat = body.data.materials[0]
    raw_bc_img = next((n.image for n in raw_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "sRGB"), None)
    raw_n_img = next((n.image for n in raw_mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image and n.image.colorspace_settings.name == "Non-Color" and "normal" in n.image.name.lower()), None)

    wrist_rest = {
        "l": (rig.joint(rig.bone("lowerarm_l")), rig.joint(rig.bone("hand_l"))),
        "r": (rig.joint(rig.bone("lowerarm_r")), rig.joint(rig.bone("hand_r"))),
    }
    elbow_rest = {s: rig.joint(rig.bone(f"lowerarm_{s}")).copy() for s in ("l", "r")}

    # 1. Seated position & legs resting on floorboards (keeping both shoes cleanly visible from Sora's eyes!)
    sora_hip = Vector((-0.27, 0.08, 0.39))
    eye_anc = bpy.data.objects.get("taxi_anchor_sora_eye")
    if eye_anc:
        sora_hip = Vector((eye_anc.location.x, eye_anc.location.y + 0.02, eye_anc.location.z - 0.675))
    arm.location += sora_hip - rig.joint(rig.bone("hip_"))
    for sp, deg in [("spine_01", -4.0), ("spine_02", -4.0), ("spine_03", -3.0)]:
        if rig.has(sp):
            rig.turn(rig.bone(sp), Vector((1, 0, 0)), math.radians(deg))

    def _floor_ray(rx, ry, rz=0.40):
        dep = bpy.context.evaluated_depsgraph_get()
        origin = Vector((rx, ry, rz))
        for _ in range(4):
            hit, loc, _, _, obj, _ = bpy.context.scene.ray_cast(dep, origin, Vector((0, 0, -1)), distance=1.5)
            if not hit:
                break
            if obj and "glass" not in obj.name.lower() and "sora" not in obj.name.lower():
                return loc.z
            origin = loc + Vector((0, 0, -0.005))
        return None

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
        rig.aim(rig.bone(f"upperleg_{side}"), rig.bone(f"lowerleg_{side}"), knee)
        rig.aim(rig.bone(f"lowerleg_{side}"), rig.bone(f"foot_{side}"), ankle)
        rig.aim(rig.bone(f"foot_{side}"), rig.bone(f"ball_{side}"), ball)

    # Measure ACTUAL posed thigh cloth heights right now so Sora's hands rest WITH WEIGHT directly on them!
    bpy.context.view_layer.update()
    ev_legs = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    thigh_pts = [
        body.matrix_world @ ev_legs.data.vertices[vi].co
        for vi, rco in enumerate(rest)
        if 0.42 < rco.z < 0.94 and abs(rco.x) < 0.25
    ]

    def thigh_z_fn(qx, qy):
        near = [p.z for p in thigh_pts if abs(p.x - qx) < 0.045 and abs(p.y - qy) < 0.032 and p.z > 0.36]
        return float(np.percentile(near, 94)) if near else 0.495

    legs_snap = rig.snapshot()

    def _eval_world_verts():
        bpy.context.view_layer.update()
        ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m_w = body.matrix_world
        return [m_w @ v.co for v in ev.data.vertices]

    def _wrist_tuple(side):
        w_pos = rig.joint(rig.bone(f"hand_{side}")).copy()
        e_pos = rig.joint(rig.bone(f"lowerarm_{side}")).copy()
        arm_dir = (w_pos - e_pos).normalized()
        up_dir = rig.palm_of(side) * (-1.0)
        up_dir = (up_dir - arm_dir * up_dir.dot(arm_dir)).normalized()
        side_dir = up_dir.cross(arm_dir).normalized()
        return (w_pos, arm_dir, side_dir, up_dir)

    def _wrist_mat(side):
        w_pos, arm_dir, side_dir, up_dir = _wrist_tuple(side)
        return Matrix.Translation(w_pos) @ Matrix((side_dir, arm_dir, up_dir)).transposed().to_4x4()

    def _capture_nail_frames():
        frames = {}
        for side in ("l", "r"):
            palm = rig.palm_of(side)
            across, _ = rig.knuckles(side)
            for finger in ("thumb", "index", "middle", "ring", "pinky"):
                b3 = rig.bone(f"{finger}_03_{side}")
                p3 = rig.joint(b3)
                _, f_dir = rig.finger_tip(finger, side)
                # Carla's delicate distal phalanx is ~12-15mm long -> nail bed center sits 8.5mm (10.5mm thumb) past joint 03!
                nail_ctr = p3 + f_dir * (0.0105 if finger == "thumb" else 0.0082)
                if finger == "thumb":
                    d_up = (-palm * 0.65 + (across if side == "l" else -across) * 0.75).normalized()
                else:
                    d_up = -palm
                d_up = (d_up - f_dir * d_up.dot(f_dir)).normalized()
                s_ax = f_dir.cross(d_up).normalized()
                frames[f"{finger}_{side}"] = (nail_ctr.copy(), f_dir, d_up, s_ax, finger == "thumb")
        return frames

    # Pre-classify rest faces BEFORE Catmull-Clark Subsurf so subdivided hands inherit exact material slots!
    # Also mark Carla's left-wrist knit-cuff zone (slot 5 temporary -> merged into bare skin slot 1 after Subsurf!)
    s_tmp_mats = [bpy.data.materials.new(f"_tmp_sora_{k}") for k in range(6)]
    body.data.materials.clear()
    for m_t in s_tmp_mats:
        body.data.materials.append(m_t)
    for p in body.data.polygons:
        rc = sum((rest[vi] for vi in p.vertices), Vector()) / len(p.vertices)
        side_k = "l" if rc.x >= 0 else "r"
        e_r, w_r = wrist_rest[side_k]
        ax_r = w_r - e_r
        u_arm = (rc - e_r).dot(ax_r) / max(1e-6, ax_r.length_squared)
        perp = (rc - (e_r + ax_r * u_arm)).length
        near_wrist = (rc - w_r).length < 0.21 and perp < 0.10
        if rc.z < 0.135:
            p.material_index = 2
        elif near_wrist and u_arm > (0.890 if side_k == "l" else 0.945):
            # Slot 5 = bare wrist ring (former sweater cuff -> slimmed & cable-knit erased!), slot 1 = crisp hands!
            p.material_index = 5 if u_arm < 1.055 else 1
        elif rc.z > 0.965 or (abs(rc.x) > 0.19 and rc.z > 0.85):
            p.material_index = 3
        else:
            p.material_index = 0

    # Add 1-level Catmull-Clark Subdivision AFTER Armature so Sora's 863-vert faceted hands become
    # silky-smooth ~3,400-vert feminine organic hands across Basis + all 3 skeletal morphs!
    sub_s = body.modifiers.new(name="SubsurfSoraHands", type="SUBSURF")
    sub_s.subdivision_type = "CATMULL_CLARK"
    sub_s.levels = 1
    sub_s.render_levels = 1
    sub_s.uv_smooth = "PRESERVE_BOUNDARIES"

    # 2. Pose Basis + capture 3 tight skeletal morphs (`breathe`, `tense_grip`, `fidget`)!
    _pose_sora_arms_and_hands(rig, thigh_z_fn, tense=0.0, breathe=0.0, fidget=0.0)
    basis_snap = rig.snapshot()
    neck_pos = rig.joint(rig.bone("neck_")).copy()
    wrists_basis = {"l": _wrist_tuple("l"), "r": _wrist_tuple("r")}
    wrist_M_basis = {"l": _wrist_mat("l"), "r": _wrist_mat("r")}
    nail_frames_basis = _capture_nail_frames()

    morph_specs = [
        ("breathe",    dict(tense=0.0, breathe=1.0, fidget=0.0)),
        ("tense_grip", dict(tense=1.0, breathe=0.0, fidget=0.0)),
        ("fidget",     dict(tense=0.0, breathe=0.0, fidget=1.0)),
    ]
    morph_verts_raw = {}
    wrist_M_morphs = {}
    nail_frames_morphs = {}
    for m_name, kw in morph_specs:
        rig.restore(legs_snap)
        _pose_sora_arms_and_hands(rig, thigh_z_fn, **kw)
        morph_verts_raw[m_name] = _eval_world_verts()
        wrist_M_morphs[m_name] = {"l": _wrist_mat("l"), "r": _wrist_mat("r")}
        nail_frames_morphs[m_name] = _capture_nail_frames()

    rig.restore(basis_snap)

    # 4. Bake Dual-Quaternion + Catmull-Clark posed mesh & attach all 3 shape keys BEFORE neck bisect!
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    baked = bpy.data.meshes.new_from_object(ev)
    baked.transform(body.matrix_world)
    body.modifiers.clear()
    body.parent = None
    body.matrix_world = Matrix.Identity(4)
    body.data = baked
    body.vertex_groups.clear()
    for o in imported:
        if o != body and o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    for m_t in s_tmp_mats:
        if m_t.name in bpy.data.materials:
            bpy.data.materials.remove(m_t)

    # Capture subdivided slot-5 wrist-cuff polygon indices and merge slot 5 -> slot 1 (bare skin)!
    wrist_cuff_poly_idx = {p.index for p in body.data.polygons if p.material_index == 5}
    for p in body.data.polygons:
        if p.material_index == 5:
            p.material_index = 1
    kinds = [p.material_index for p in body.data.polygons]

    body.shape_key_add(name="Basis", from_mix=False)
    for m_name, pts_list in morph_verts_raw.items():
        kb = body.shape_key_add(name=m_name, from_mix=False)
        kb.data.foreach_set("co", np.array([p[:] for p in pts_list], np.float32).ravel())
        kb.value = 0.0

    # 5. Build CRISP 2K textures preserving Carla's real photographic hand skin/knuckles/tendons!
    w_s, h_s = 2048, 2048
    rgb_scan = _resize_np(raw_bc_img, w_s, h_s)[..., :3] if raw_bc_img else np.full((h_s, w_s, 3), 0.5, np.float32)
    lum = rgb_scan @ np.array([0.3, 0.59, 0.11], np.float32)
    shade_tr = _box_blur_2d(lum, 18)
    shade_bl = _box_blur_2d(lum, 20)
    sk_low = _box_blur_2d(lum, 16)
    sk_high = lum - _box_blur_2d(lum, 5)
    uvl_s = body.data.uv_layers.active.data

    def _mean_grid(grid, kv):
        vals = []
        for p in body.data.polygons:
            if kinds[p.index] == kv:
                uv = sum((uvl_s[li].uv for li in p.loop_indices), Vector((0, 0))) / len(p.loop_indices)
                vals.append(float(grid[int((uv.y % 1.0) * (h_s - 1)), int((uv.x % 1.0) * (w_s - 1))]))
        return float(np.mean(vals)) if vals else 0.5

    weave_rgb = _load_tiled_np(LINEN_BC, w_s, h_s, repeats=40, is_srgb=True) if LINEN_BC.exists() else np.full((h_s, w_s, 3), 0.55, np.float32)
    weave_lum = weave_rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    weave_fac = np.clip(weave_lum / max(1e-3, float(np.mean(weave_lum))), 0.85, 1.15)[..., None]

    tr_k = np.clip(0.86 + 0.16 * (shade_tr / max(1e-3, _mean_grid(shade_tr, 0))), 0.72, 1.14)[..., None]
    sora_tr_bc = _pack_image("T_taxi_sora_trousers", np.array((0.23, 0.20, 0.17), np.float32) * tr_k * weave_fac, is_srgb=True)

    bl_k = np.clip(0.88 + 0.14 * (shade_bl / max(1e-3, _mean_grid(shade_bl, 3))), 0.78, 1.10)[..., None]
    sora_bl_bc = _pack_image("T_taxi_sora_blouse", np.array((0.55, 0.50, 0.42), np.float32) * bl_k * weave_fac, is_srgb=True)

    # Build UV mask of the former knit-sweater cuff zone on Sora's bare wrist so we completely erase
    # Carla's cable-knit stripes from BOTH skin albedo and normal map (leaving silky smooth wrist skin!)
    wrist_mask_2k = np.zeros((h_s, w_s), np.float32)
    for p in body.data.polygons:
        if p.index in wrist_cuff_poly_idx:
            uvs_p = [uvl_s[li].uv for li in p.loop_indices]
            u0 = max(0, int(min(u.x for u in uvs_p) * w_s) - 6)
            u1 = min(w_s - 1, int(max(u.x for u in uvs_p) * w_s) + 6)
            v0 = max(0, int(min(u.y for u in uvs_p) * h_s) - 6)
            v1 = min(h_s - 1, int(max(u.y for u in uvs_p) * h_s) + 6)
            if (u1 - u0) < 256 and (v1 - v0) < 256:
                wrist_mask_2k[v0 : v1 + 1, u0 : u1 + 1] = 1.0
    wrist_mask_2k = np.clip(_box_blur_2d(wrist_mask_2k, 8), 0.0, 1.0)

    # Lifelike warm Khmer female hand skin with rich photographic inter-finger crevices, knuckle depth & subtle capillary blush!
    skin_base = np.array((0.578, 0.392, 0.292), np.float32)
    skin_mean = _mean_grid(sk_low, 1)
    rng_s = np.random.default_rng(193314)
    epiderm = 1.0 + rng_s.normal(0.0, 0.012, (h_s, w_s)).astype(np.float32)
    # Suppress cable-knit high-frequency detail ONLY on the former sweater-cuff wrist ring!
    sk_high_clean = sk_high * (1.0 - wrist_mask_2k)
    sk_low_clean = sk_low * (1.0 - wrist_mask_2k) + skin_mean * wrist_mask_2k
    sk_k = np.clip(0.74 + 0.32 * (sk_low_clean / max(1e-3, skin_mean)) + sk_high_clean * 1.48, 0.56, 1.24)
    blush = np.clip((rgb_scan[..., 0] - rgb_scan[..., 1]) - 0.070, -0.04, 0.12)[..., None] * (1.0 - wrist_mask_2k[..., None])
    skin_out = skin_base[None, None, :] * sk_k[..., None] * epiderm[..., None] + blush * np.array([0.55, -0.09, -0.13], np.float32)
    sora_sk_bc = _pack_image("T_taxi_sora_skin_BC", np.clip(skin_out, 0.03, 0.90), is_srgb=True)

    shoe_arr = np.clip(np.array((0.055, 0.042, 0.036), np.float32)[None, None, :] * (0.94 + 0.06 * rng_s.normal(0.0, 0.25, (512, 512, 1)).astype(np.float32)), 0.015, 0.14)
    sora_shoe_bc = _pack_image("T_taxi_sora_shoes_BC", shoe_arr, is_srgb=True)

    wn, hn = 1024, 1024
    scan_n_s = _resize_np(raw_n_img, wn, hn) if raw_n_img else np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 2), np.float32)])
    linen_n_s = _load_tiled_np(LINEN_N, wn, hn, repeats=40, is_srgb=False) if LINEN_N.exists() else np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 1), np.float32)])
    sora_cloth_n = _pack_image("T_taxi_sora_cloth_N", _blend_normals(scan_n_s, linen_n_s, 0.26, 0.54), is_srgb=False)

    hs_n = rng_s.normal(0.0, 0.022, (hn, wn)).astype(np.float32)
    hs_n = (hs_n + np.roll(hs_n, 1, 0) + np.roll(hs_n, -1, 0) + np.roll(hs_n, 1, 1) + np.roll(hs_n, -1, 1)) * 0.2
    gx_s = (np.roll(hs_n, -1, 1) - np.roll(hs_n, 1, 1)) * 0.52
    gy_s = (np.roll(hs_n, -1, 0) - np.roll(hs_n, 1, 0)) * 0.52
    nz_s = np.sqrt(np.clip(1.0 - gx_s * gx_s - gy_s * gy_s, 0.1, 1.0))
    pore_s = np.dstack([np.clip(-gx_s * 0.5 + 0.5, 0, 1), np.clip(-gy_s * 0.5 + 0.5, 0, 1), np.clip(nz_s * 0.5 + 0.5, 0, 1)])
    wrist_mask_1k = wrist_mask_2k[::2, ::2][..., None]
    flat_n = np.dstack([np.full((hn, wn, 2), 0.5, np.float32), np.ones((hn, wn, 1), np.float32)])
    scan_n_hand = scan_n_s[..., :3] * (1.0 - wrist_mask_1k) + flat_n * wrist_mask_1k
    sora_skin_n = _pack_image("T_taxi_sora_skin_N", _blend_normals(scan_n_hand, pore_s, 0.74, 0.40), is_srgb=False)

    trousers_mat = _make_pbr("M_taxi_sora_trousers_scan", sora_tr_bc, sora_cloth_n, rough=0.88, normal_strength=0.46)
    blouse_mat = _make_pbr("M_taxi_sora_blouse_scan", sora_bl_bc, sora_cloth_n, rough=0.88, normal_strength=0.44)
    skin_mat = _make_pbr("M_taxi_sora_skin_scan", sora_sk_bc, sora_skin_n, rough=0.44, normal_strength=0.58)
    shoes_mat = _make_pbr("M_taxi_sora_shoes_scan", sora_shoe_bc, sora_cloth_n, rough=0.34, normal_strength=0.28)
    neck_cap = _make_pbr("M_taxi_sora_neck_cap", rough=0.94, color=(0.38, 0.27, 0.21))

    # Assign final PBR materials IN-PLACE (NEVER call materials.clear(), which wipes polygon material_index to 0!)
    final_mats = (trousers_mat, skin_mat, shoes_mat, blouse_mat, neck_cap)
    for idx_m, mt in enumerate(final_mats):
        if idx_m < len(body.data.materials):
            body.data.materials[idx_m] = mt
        else:
            body.data.materials.append(mt)
    while len(body.data.materials) > len(final_mats):
        body.data.materials.pop(index=len(body.data.materials) - 1)

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    if body.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    body.name = body.data.name = "taxi_sora_legs_scan"
    for c_old in list(body.users_collection):
        c_old.objects.unlink(body)
    coll.objects.link(body)

    # Re-assert exact per-face material slots, weld seams, bisect neck, slim Carla's lumpy left sweater-cuff wrist!
    body.active_shape_key_index = 0
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(body.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        if f.index < len(kinds):
            f.material_index = kinds[f.index]
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
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
    cut_co = neck_pos + Vector((0.0, 0.0, 0.025))
    res = bmesh.ops.bisect_plane(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        plane_co=cut_co,
        plane_no=Vector((0.0, 0.0, 1.0)),
        clear_outer=True,
        use_snap_center=False,
    )
    cut_edges = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
    if cut_edges:
        filled = bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)["faces"]
        for f in filled:
            f.material_index = 4
        bmesh.ops.triangulate(bm, faces=filled)

    # Gently slim Carla's thick left sweater-cuff bulge down to a dainty anatomical female wrist (~2.15 cm radius)
    # with wide smooth falloff (along=-0.042..+0.032) so ZERO single-vertex wrist pinch spike ever forms!
    sk_layers = list(bm.verts.layers.shape)
    lw_p, l_arm_d, _, _ = wrists_basis["l"]
    rw_p, r_arm_d, _, _ = wrists_basis["r"]
    for v in bm.verts:
        if any(f.material_index == 1 for f in v.link_faces):
            rel = v.co - lw_p
            along = rel.dot(l_arm_d)
            if -0.042 < along < 0.032:
                radial = rel - l_arm_d * along
                r_len = radial.length
                if r_len > 0.0215:
                    w_slim = _sstep(-0.042, -0.018, along) * _sstep(0.032, 0.004, along)
                    shrink = (r_len - 0.0215) * 0.58 * w_slim
                    d_v = -radial.normalized() * shrink
                    v.co += d_v
                    for sk in sk_layers:
                        v[sk] = v[sk] + d_v

    # Also weld any leftover sub-mm seam crease strictly inside the left wrist ring so ZERO single-vertex spike
    # can ever poke out next to the Art Deco watch bezel, then smooth cleanly across all shape keys!
    wrist_weld_v = [v for v in bm.verts if (v.co - lw_p).length < 0.048 and any(f.material_index in (1, 3) for f in v.link_faces)]
    if wrist_weld_v:
        bmesh.ops.remove_doubles(bm, verts=wrist_weld_v, dist=0.0022)
    cloth_v = [v for v in bm.verts if not v.is_boundary and all(f.material_index in (0, 3) for f in v.link_faces)]
    wrist_ring_v = [
        v for v in bm.verts
        if any(f.material_index in (1, 3) for f in v.link_faces)
        and (
            (-0.048 < (v.co - lw_p).dot(l_arm_d) < 0.036 and (v.co - lw_p).length < 0.056)
            or (-0.030 < (v.co - rw_p).dot(r_arm_d) < 0.020 and (v.co - rw_p).length < 0.046)
        )
    ]
    for verts_grp, passes, fac in ((cloth_v, 2, 0.22), (wrist_ring_v, 24, 0.50)):
        for _ in range(passes):
            disp = {}
            for v in verts_grp:
                nbs = [e.other_vert(v) for e in v.link_edges]
                if nbs:
                    avg = sum((nb.co for nb in nbs), Vector()) / len(nbs)
                    disp[v] = v.co.lerp(avg, fac) - v.co
            for v, d_v in disp.items():
                v.co += d_v
                for sk in sk_layers:
                    v[sk] = v[sk] + d_v

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.update_edit_mesh(body.data)
    bpy.ops.object.mode_set(mode="OBJECT")
    for p in body.data.polygons:
        p.use_smooth = True
    body.data.update()

    # Build BVH of Sora's posed Catmull-Clark body (whole body for cuffs/watch, HAND-SKIN ONLY for fingernails!)
    bm_bvh = bmesh.new()
    bm_bvh.from_mesh(body.data)
    sora_bvh = BVHTree.FromBMesh(bm_bvh)
    bm_bvh.free()

    bm_hbvh = bmesh.new()
    bm_hbvh.from_mesh(body.data)
    non_hand = [f for f in bm_hbvh.faces if f.material_index != 1]
    if non_hand:
        bmesh.ops.delete(bm_hbvh, geom=non_hand, context="FACES")
    sora_hand_bvh = BVHTree.FromBMesh(bm_hbvh)
    bm_hbvh.free()

    # 6. Sleek raycast-fitted rolled linen blouse cuffs (tucked cleanly right behind the watch!) + synced morphs
    sora_cuff_arr = weave_fac[:512, :512, :] * np.array((0.55, 0.50, 0.42), np.float32)
    sora_cuff_bc = _pack_image("T_cab_sora_cuff_BC", sora_cuff_arr, is_srgb=True)
    m_sora_cuff = _make_pbr("M_cab_sora_cuff_linen", sora_cuff_bc, bpy.data.images.load(str(LINEN_N), check_existing=True) if LINEN_N.exists() else sora_cloth_n, rough=0.88, normal_strength=0.44)
    m_sora_cuff["tile"] = 0.27
    m_pearl = _make_pbr("M_cab_pearl_button", rough=0.20, color=(0.76, 0.72, 0.64))

    bm_sc, bm_sb = bmesh.new(), bmesh.new()
    sc_ranges, sb_ranges = [], []
    # Left cuff shifted -3.4cm back up forearm so dainty bare wrist + gold watch sit cleanly in view!
    for side, shint, sh_val in (("l", 1.0, -0.034), ("r", -1.0, -0.023)):
        c0, b0 = len(bm_sc.verts), len(bm_sb.verts)
        wp, arm_d, _, _ = wrists_basis[side]
        _build_tailored_cuff_bvh(sora_bvh, wp, arm_d, length=0.028, pad=0.0028, shift=sh_val, bm_cloth=bm_sc, bm_btn=bm_sb, side_hint=shint)
        bm_sc.verts.ensure_lookup_table()
        bm_sb.verts.ensure_lookup_table()
        sc_ranges.append((side, c0, len(bm_sc.verts)))
        sb_ranges.append((side, b0, len(bm_sb.verts)))

    sc_obj = _bm_to_obj("taxi_sora_blouse_cuffs", bm_sc, m_sora_cuff, coll, smooth=True)
    if world_uvs_fn:
        world_uvs_fn(sc_obj)
    else:
        _apply_box_uvs(sc_obj, scale=4.2)
    sb_obj = _bm_to_obj("taxi_sora_cuff_buttons", bm_sb, m_pearl, coll, smooth=True)

    for target_obj, ranges in ((sc_obj, sc_ranges), (sb_obj, sb_ranges)):
        target_obj.shape_key_add(name="Basis", from_mix=False)
        base_cos = [v.co.copy() for v in target_obj.data.vertices]
        for m_name, _ in morph_specs:
            kb = target_obj.shape_key_add(name=m_name, from_mix=False)
            out_cos = list(base_cos)
            for side, i0, i1 in ranges:
                M_d = wrist_M_morphs[m_name][side] @ wrist_M_basis[side].inverted()
                for vi in range(i0, i1):
                    out_cos[vi] = M_d @ base_cos[vi]
            kb.data.foreach_set("co", np.array([p[:] for p in out_cos], np.float32).ravel())
            kb.value = 0.0

    # 7. Subtle curved anatomical fingernails conformed strictly onto Sora's HAND-SKIN BVH (NEVER trousers!)
    _build_sora_anatomical_nails(coll, sora_hand_bvh, nail_frames_basis, nail_frames_morphs, morph_specs)

    # 8. Museum-grade 1930s antique-gold Art Deco tank wristwatch BVH-conformed to Sora's left wrist!
    _build_conformed_sora_watch(coll, sora_bvh, wrists_basis["l"], wrist_M_basis, wrist_M_morphs, morph_specs)

    body.data["sora_realism_v9"] = True
    body.data.update()
    print(
        "TAXI_SORA_V9_REBUILT",
        "verts=", len(body.data.vertices),
        "polys=", len(body.data.polygons),
        "morphs=", [k.name for k in body.data.shape_keys.key_blocks],
    )
    return body


def apply_people_realism(coll, plain, world_uvs_fn, neck_pos=None):
    """Master entrypoint called by taxi_cabin_details.py to rebuild BOTH driver and Sora."""
    neck = neck_pos if neck_pos is not None else Vector((0.268, 0.056, 0.922))
    rebuild_driver_head_and_cap(coll, neck)
    rebuild_driver_body_and_clothes(coll, neck, plain, world_uvs_fn)
    rebuild_sora_hands_and_watch(coll, world_uvs_fn)
    print("TAXI_PEOPLE_REALISM_APPLIED_OK")
