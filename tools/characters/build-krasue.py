"""Episode 1's Krasue: the user's Tripo model (art-source/library/scans/krasue.glb, made by
tools/characters/import-krasue.py), rigged here for the game, which moves every joint
itself (src/episodes/ep1/entities/KrasueFlyer.ts): no clips.

blender -b --factory-startup --python-exit-code 1 -P tools/characters/build-krasue.py
Then: npm run assets -- ep1/krasue

The head's centre is the origin (the point the game flies); the face looks down -Y
(glTF +Z), and the model is scaled to SCALE times the source, a head a little over life
size. Joints (their names are the game's contract):
- krasue_root, at the head's centre; krasue_head, pivoting at the neck; krasue_jaw, at
  the hinge of the jaw, carrying the chin, the lower lip and the lower teeth.
- krasue_hair_<k>_<j> (+ krasue_hair_<k>_end): HAIR_SECTORS strands of the blown-out
  hair, by their bearing round the head, each a chain from the scalp out to its tips
  through the mean of the hair at each distance from the head.
- krasue_gut_<j> (+ krasue_gut_end): the hanging viscera, from the throat to the last
  drop of blood; krasue_heart and krasue_lung_L / _R, leaves of the chest joint, for the
  beat and the breath.
- Weights are made here, not by bone heat: each vertex goes by where it is and its colour
  (the black hair, the red viscera, the pale face) to the skull, the jaw, its two nearest
  strands at its distance out, or the viscera chain at its height, blended across every
  joint so no surface tears.
The eyes get an emission map (the red of the irises only), which the game turns up when
she sees Sora.
"""
import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / "art-source/library/scans/krasue.glb"
OUT = ROOT / "art-export/ep1/krasue.glb"
BLEND = ROOT / "art-source/characters/krasue-ep1/krasue.blend"

SCALE = 1.4
# Landmarks in the source's own units (Blender, Z up, the face toward -Y).
CENTRE = np.array((0.0, -0.035, 0.765))          # the head's centre
NECK = np.array((0.0, -0.01, 0.615))             # the head's pivot
JAW = np.array((0.0, -0.045, 0.705))             # the jaw's hinge, under the ears
CHIN = np.array((0.0, -0.17, 0.595))
EYES = [np.array((-0.051, -0.172, 0.765)), np.array((0.048, -0.173, 0.766))]
# The skull: an egg round CENTRE, longer to the face than to the back.
SKULL = dict(x=0.125, front=0.185, back=0.15, up=0.215, down=0.19)
HAIR_SECTORS = 16
HAIR_SHELLS = [0.13, 0.19, 0.25, 0.31, 0.37, 0.44, 0.7]  # distances from the centre
GUT_Z = [0.6, 0.48, 0.36, 0.24, 0.12, 0.0]        # the viscera's joints, top to bottom


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def load():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SCAN))
    body = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
    for o in [o for o in bpy.context.scene.objects if o is not body]:
        bpy.data.objects.remove(o)
    body.data.transform(body.matrix_world)
    body.matrix_world = Matrix()
    body.name = body.data.name = "krasue_body"
    return body


def vertex_colours(body):
    """The atlas colour under each vertex (the mean over its corners), linear RGB."""
    me = body.data
    img = next(n.image for n in me.materials[0].node_tree.nodes
               if n.type == "TEX_IMAGE" and n.image.name.endswith("_BC"))
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    nl = len(me.loops)
    uv = np.empty(nl * 2, np.float32)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    lv = np.empty(nl, np.int64)
    me.loops.foreach_get("vertex_index", lv)
    xi = np.clip((uv[:, 0] % 1) * w, 0, w - 1).astype(int)
    yi = np.clip((uv[:, 1] % 1) * h, 0, h - 1).astype(int)
    n = len(me.vertices)
    col = np.zeros((n, 3))
    cnt = np.zeros(n)
    np.add.at(col, lv, px[yi, xi, :3])
    np.add.at(cnt, lv, 1)
    return col / np.maximum(cnt, 1)[:, None], img, px


def coords(body):
    co = np.empty(len(body.data.vertices) * 3)
    body.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def skull_distance(co):
    d = co - CENTRE
    ay = np.where(d[:, 1] < 0, SKULL["front"], SKULL["back"])
    az = np.where(d[:, 2] > 0, SKULL["up"], SKULL["down"])
    return np.sqrt((d[:, 0] / SKULL["x"]) ** 2 + (d[:, 1] / ay) ** 2 + (d[:, 2] / az) ** 2)


def regions(co, col):
    r, g, b = col.T
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    red = r > 1.5 * np.maximum(g, b)
    dark_hair = (b >= 0.9 * r) & (lum < 0.15)
    x, y, z = co.T
    # By place first: below the throat, all that hangs within the viscera's bounds is
    # viscera, its dark shadowed folds too (by colour they read as hair, and tore away as
    # black blades when the gut swung). Only at the throat, where the hair falls past it,
    # does colour decide.
    box = (z < 0.62) & (np.abs(x) < 0.17) & (y < 0.075)
    viscera = box & ((z < 0.5) | ~(dark_hair & ~red))
    viscera |= red & (z < 0.6)
    # Then by its neighbours: a vertex goes with what most of the surface round it is
    # (a dark fold between the organs is viscera; a red-lit lock is hair).
    tree = KDTree(len(co))
    for i, p in enumerate(co):
        tree.insert(p, i)
    tree.balance()
    near = [[j for _, j, _ in tree.find_range(p, 0.018)] for p in co]
    for _ in range(2):
        vote = np.array([viscera[js].mean() for js in near])
        viscera = (vote > 0.5) & (z < 0.64)
    return viscera, dark_hair, lum


def hair_chains(co, hair):
    """For each bearing round the head, the strand's joints: the scalp, then the mean of
    its hair at each distance out (as far as there is hair)."""
    d = co - CENTRE
    dist = np.linalg.norm(d, axis=1)
    bearing = np.arctan2(d[:, 0], -d[:, 1]) % (2 * math.pi)   # 0 at the face, round to her left
    sector = np.floor(bearing / (2 * math.pi) * HAIR_SECTORS).astype(int) % HAIR_SECTORS
    chains = []
    for k in range(HAIR_SECTORS):
        mine = hair & (sector == k)
        joints = []
        mid = (k + 0.5) / HAIR_SECTORS * 2 * math.pi
        # The scalp: where the strand leaves the skull, along its mean direction.
        near = mine & (dist < HAIR_SHELLS[1])
        direction = d[near].mean(0) if near.sum() > 20 else np.array((math.sin(mid), -math.cos(mid), 0.2))
        direction = direction / np.linalg.norm(direction)
        joints.append(CENTRE + direction * HAIR_SHELLS[0])
        for a, b in zip(HAIR_SHELLS[1:-1], HAIR_SHELLS[2:]):
            shell = mine & (dist >= a) & (dist < b)
            if shell.sum() >= 8:
                joints.append(co[shell].mean(0))
        # Short hair here (round the face) has no strand of its own: it keeps to the skull.
        chains.append(np.array(joints) if len(joints) >= 3 else None)
    return chains, sector, bearing, dist


def gut_chain(co, viscera):
    joints = []
    for z in GUT_Z:
        band = viscera & (np.abs(co[:, 2] - z) < 0.04)
        if band.sum() > 20:
            p = co[band].mean(0)
            joints.append(np.array((p[0], p[1], z)))
        else:
            joints.append(np.array((joints[-1][0] if joints else 0, joints[-1][1] if joints else -0.06, z)))
    return np.array(joints)


def leaf_centres(co, viscera):
    x, y, z = co.T
    heart = viscera & (y < -0.12) & (z > 0.3) & (z < 0.46) & (np.abs(x) < 0.07)
    lungs = [viscera & (x * s > 0.08) & (z > 0.33) & (z < 0.47) for s in (1, -1)]
    return co[heart].mean(0), [co[m].mean(0) for m in lungs]


def place(p):
    """Source units -> the game model's (the head's centre at the origin, scaled)."""
    return Vector(((np.asarray(p) - CENTRE) * SCALE).tolist())


def build_rig(chains, gut, heart, lungs):
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = rig.data.name = "krasue_rig"
    arm = rig.data
    for b in list(arm.edit_bones):
        arm.edit_bones.remove(b)

    def bone(name, head, tail, parent=None, connect=False):
        b = arm.edit_bones.new(name)
        b.head, b.tail = place(head), place(tail)
        if (b.tail - b.head).length < 1e-4:
            b.tail = b.head + Vector((0, 0, 0.02))
        b.roll = 0
        if parent:
            b.parent = arm.edit_bones[parent]
            b.use_connect = connect
        return name

    bone("krasue_root", CENTRE, CENTRE + (0, 0, 0.08))
    bone("krasue_head", NECK, NECK + (0, 0, 0.3), "krasue_root")
    bone("krasue_jaw", JAW, CHIN, "krasue_head")
    for k, joints in enumerate(chains):
        if joints is None:
            continue
        parent = "krasue_head"
        for j in range(len(joints) - 1):
            parent = bone(f"krasue_hair_{k}_{j}", joints[j], joints[j + 1], parent, j > 0)
        tip = joints[-1] + (joints[-1] - joints[-2]) * 0.5
        bone(f"krasue_hair_{k}_end", joints[-1], tip, parent, True)
    parent = "krasue_root"
    for j in range(len(gut) - 1):
        parent = bone(f"krasue_gut_{j}", gut[j], gut[j + 1], parent, j > 0)
    bone("krasue_gut_end", gut[-1], gut[-1] - (0, 0, 0.06), parent, True)
    bone("krasue_heart", heart, heart + (0, -0.04, 0), "krasue_gut_0")
    bone("krasue_lung_L", lungs[0], lungs[0] + (0, 0, 0.05), "krasue_gut_0")
    bone("krasue_lung_R", lungs[1], lungs[1] + (0, 0, 0.05), "krasue_gut_0")
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def chain_weights(u, count):
    """Weights of a vertex at continuous joint index `u` over `count` bones: a hat on
    each bone's middle, so a vertex at a joint is shared by the two bones meeting there."""
    centres = np.arange(count) + 0.5
    w = np.clip(1 - np.abs(u[:, None] - centres[None, :]), 0, 1)
    w[:, 0] = np.where(u < 0.5, 1, w[:, 0])
    w[:, -1] = np.where(u > count - 0.5, 1, w[:, -1])
    return w / np.maximum(w.sum(1, keepdims=True), 1e-9)


def skin(body, rig, chains, gut, heart, lungs, viscera, dark_hair, lum, sector, bearing, dist):
    co = coords(body)
    n = len(co)
    names = [b.name for b in rig.data.bones]
    index = {nm: i for i, nm in enumerate(names)}
    W = np.zeros((n, len(names)))
    x, y, z = co.T

    # The skull (and the face on it); the jaw below the mouth's middle.
    rho = skull_distance(co)
    face = (lum > 0.18) & ~dark_hair & (y < -0.04) & (z > 0.55)
    skull = np.maximum(1 - smoothstep(1.0, 1.3, rho), face.astype(float)) * ~viscera
    jaw = ((1 - smoothstep(0.646, 0.684, z)) * (1 - smoothstep(-0.07, -0.015, y)) *
           (1 - smoothstep(0.1, 0.14, np.abs(x))) * (z > 0.54) * (rho < 1.15))
    W[:, index["krasue_head"]] += skull * (1 - jaw)
    W[:, index["krasue_jaw"]] += skull * jaw

    # The hair: the strands round its bearing that reach as far out as it is, each at
    # its distance along them. Hair beyond every strand's reach keeps to the skull: a
    # vertex hung on a short strand's root would swing far on a small turn of it.
    hair = ~viscera
    share = (1 - skull) * hair
    pos = bearing / (2 * math.pi) * HAIR_SECTORS
    reach = {}
    total = np.zeros(n)
    for k, joints in enumerate(chains):
        if joints is None:
            continue
        jd = np.linalg.norm(joints - CENTRE, axis=1)
        gap = np.abs((pos - (k + 0.5) + HAIR_SECTORS / 2) % HAIR_SECTORS - HAIR_SECTORS / 2)
        reach[k] = np.clip(1 - gap / 1.3, 0, 1) * (1 - smoothstep(jd[-1] - 0.02, jd[-1] + 0.07, dist))
        total += reach[k]
    held = np.minimum(total, 1)
    W[:, index["krasue_head"]] += share * (1 - held)
    for k, r in reach.items():
        joints = chains[k]
        m = (r > 0) & (share > 0)
        if not m.any():
            continue
        jd = np.linalg.norm(joints - CENTRE, axis=1)
        u = np.interp(dist[m], jd, np.arange(len(jd)))
        w = chain_weights(u, len(joints) - 1)
        part = share[m] * held[m] * r[m] / total[m]
        for j in range(len(joints) - 1):
            W[m, index[f"krasue_hair_{k}_{j}"]] += part * w[:, j]

    # The viscera: the chain at its height; the top of the throat goes with the head.
    neck = smoothstep(0.56, 0.63, z) * viscera
    W[:, index["krasue_head"]] += neck
    hang = viscera * (1 - neck)
    u = np.interp(-z, -gut[:, 2], np.arange(len(gut)))
    w = chain_weights(u, len(gut) - 1)
    leaf = np.zeros(n)
    for name, c, r0, r1 in [("krasue_heart", heart, 0.022, 0.06),
                            ("krasue_lung_L", lungs[0], 0.03, 0.085),
                            ("krasue_lung_R", lungs[1], 0.03, 0.085)]:
        wl = (1 - smoothstep(r0, r1, np.linalg.norm(co - c, axis=1))) * hang * (1 - leaf)
        W[:, index[name]] += wl
        leaf += wl
    for j in range(len(gut) - 1):
        W[:, index[f"krasue_gut_{j}"]] += hang * (1 - leaf) * w[:, j]

    # Anything left (stray specks): the head.
    empty = W.sum(1) < 1e-6
    W[empty, index["krasue_head"]] = 1
    # Four influences at most, normalised.
    order = np.argsort(-W, axis=1)
    keep = np.zeros_like(W, dtype=bool)
    np.put_along_axis(keep, order[:, :4], True, axis=1)
    W = np.where(keep, W, 0)
    W /= W.sum(1, keepdims=True)
    groups = {nm: body.vertex_groups.new(name=nm) for nm in names}
    for j, nm in enumerate(names):
        idx = np.nonzero(W[:, j] > 1e-4)[0]
        for i in idx:
            groups[nm].add([int(i)], float(W[i, j]), "REPLACE")
    print("WEIGHTS skull", int((skull > 0.5).sum()), "jaw", int((jaw * skull > 0.5).sum()),
          "hair", int((share > 0.5).sum()), "viscera", int(viscera.sum()), "empty", int(empty.sum()), flush=True)


def eye_glow(body, colours, px):
    """An emission map that is the irises' red and nothing else."""
    me = body.data
    co = coords(body)
    near = np.zeros(len(co), bool)
    for e in EYES:
        near |= np.linalg.norm(co - e, axis=1) < 0.03
    h, w = px.shape[:2]
    mask = np.zeros((h, w), np.float32)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2) * (w, h)
    for p in me.polygons:
        if not all(near[v] for v in p.vertices):
            continue
        tri = uv[list(p.loop_indices)]
        x0, y0 = np.floor(tri.min(0)).astype(int) - 1
        x1, y1 = np.ceil(tri.max(0)).astype(int) + 1
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        pts = np.stack([gx.ravel() + 0.5, gy.ravel() + 0.5], 1)
        a, b, c = tri[:3]
        v0, v1 = b - a, c - a
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-9:
            continue
        q = pts - a
        l1 = (q[:, 0] * v1[1] - v1[0] * q[:, 1]) / den
        l2 = (v0[0] * q[:, 1] - q[:, 0] * v0[1]) / den
        inside = (l1 >= -0.02) & (l2 >= -0.02) & (l1 + l2 <= 1.02)
        xs = np.clip(gx.ravel()[inside], 0, w - 1)
        ys = np.clip(gy.ravel()[inside], 0, h - 1)
        mask[ys, xs] = 1
    rgb = px[..., :3]
    redness = np.clip((rgb[..., 0] - np.maximum(rgb[..., 1], rgb[..., 2])) * 4, 0, 1)
    glow = rgb * (mask * redness)[..., None]
    img = bpy.data.images.new("T_ep1_krasue_E", w, h)
    out = np.ones((h, w, 4), np.float32)
    out[..., :3] = glow
    img.pixels.foreach_set(out.ravel())
    img.file_format = "JPEG"
    img.pack()
    print("EYE GLOW texels", int((mask * redness > 0.1).sum()), flush=True)
    return img


def material(body, glow):
    mat = body.data.materials[0]
    mat.name = "M_ep1_krasue"
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    e = nt.nodes.new("ShaderNodeTexImage")
    e.image = glow
    nt.links.new(e.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0
    bsdf.inputs["Alpha"].default_value = 1.0
    for lk in list(bsdf.inputs["Alpha"].links):
        nt.links.remove(lk)
    mat.surface_render_method = "DITHERED"


def main():
    body = load()
    co = coords(body)
    colours, _, px = vertex_colours(body)
    viscera, dark_hair, lum = regions(co, colours)
    hair = ~viscera & (skull_distance(co) > 0.92)
    chains, sector, bearing, dist = hair_chains(co, hair)
    gut = gut_chain(co, viscera)
    heart, lungs = leaf_centres(co, viscera)
    for k in range(HAIR_SECTORS):
        m = hair & (sector == k)
        print("SECTOR", k, [int((m & (dist >= a) & (dist < b)).sum()) for a, b in zip(HAIR_SHELLS[:-1], HAIR_SHELLS[1:])], flush=True)
    print("HAIR joints", [0 if c is None else len(c) for c in chains], "GUT", gut.round(3).tolist(), "HEART", heart.round(3),
          "LUNGS", [l.round(3) for l in lungs], flush=True)
    glow = eye_glow(body, colours, px)
    rig = build_rig(chains, gut, heart, lungs)
    skin(body, rig, chains, gut, heart, lungs, viscera, dark_hair, lum, sector, bearing, dist)
    # The mesh into the game's frame: the head's centre at the origin, scaled.
    body.data.transform(Matrix.Scale(SCALE, 4) @ Matrix.Translation(Vector((-CENTRE).tolist())))
    body.data.update()
    body.parent = rig
    mod = body.modifiers.new("rig", "ARMATURE")
    mod.object = rig
    material(body, glow)
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=False, export_skins=True, export_animations=False,
                              export_morph=False, export_extras=False, export_cameras=False,
                              export_lights=False, export_image_format="AUTO", export_image_quality=92)
    print("Wrote", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)


main()
