"""Builders for a 1930s Khmer village (Episode 1): plants, a teak stilt house, the
funeral pavilion with the coffin and its altar, offerings, the white crocodile
flag, carts and fences. Run inside Blender by the area scripts.

References: Léon Busy's 1921 autochromes of Cambodia (Musée Albert-Kahn, CC0):
palm-thatched huts with woven bamboo walls and ladders, a civil servant's teak
house with a tiled roof and X-braced railings, banana and sugar palm groves.
Funeral customs (Cultural Guide 3; to confirm with the advisor): the coffin kept
at home under a pavilion, white cloth, the portrait with candles, incense and
offerings in front of it, a raised seat for the monks who chant in the evening,
the white flag shaped like a crocodile raised outside the house.
"""

import math
import re

import bpy

from kit import (  # noqa: F401
    box, collider, cloth, empty, image_material, import_model, lathe, mesh_object,
    picture_uvs, sag, tube, world_uvs,
)

# ----------------------------------------------------------------- helpers


def rotate_uvs(obj):
    """Turns box-projected UVs a quarter, so plank textures run up and down (board walls)."""
    for d in obj.data.uv_layers.active.data:
        u, v = d.uv
        d.uv = (v, -u)
    return obj


def pole(name, coll, a, b, radius, mat, sides=8, metres=0.4, radius_end=None, **props):
    """A bamboo pole (or post) from a to b; the bamboo texture repeats one node per `metres`."""
    return tube(name, coll, [a, b], radius, mat, sides=sides, metres_per_v=metres, radius_end=radius_end, **props)


def lashing(name, coll, at, radius, mat):
    """Rattan binding where two poles cross."""
    x, y, z = at
    return lathe(name, coll, [(radius, -0.05), (radius * 1.15, -0.03), (radius * 1.15, 0.03), (radius, 0.05)],
                 x, y, z, mat, segments=8)


def join(objs, name):
    """Joins meshes into one object (a plant's leaves): fewer nodes for the game to load."""
    objs = [o for o in objs if o.type == "MESH"]
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


_protos = {}

# Library models far denser than their size on screen needs (Art Bible 5.3: small
# props 500-8,000 triangles): kept at this share of their faces.
DECIMATE = {"bananas": 0.15, "wicker_basket_02": 0.25, "Lantern_01": 0.35, "wooden_bowl_01": 0.3,
            "book_encyclopedia_set_01": 0.2, "vintage_suitcase": 0.4, "fern_02": 0.6,
            "pachira_aquatica_01": 0.06, "dead_tree_trunk": 0.05, "dead_tree_trunk_02": 0.04, "tree_stump_01": 0.12,
            "root_cluster_01": 0.03, "dry_branches_medium_01": 0.3, "rusted_spade_01": 0.3,
            "shrub_01": 0.03, "shrub_02": 0.2, "shrub_03": 0.5, "shrub_04": 0.15, "grass_medium_01": 0.008,
            "grass_medium_02": 0.012, "moss_01": 0.03, "rock_moss_set_01": 0.15, "tree_stump_02": 0.1,
            "island_tree_02": 0.025}


def proto(model_id):
    """Imports a library model once into _protos (an unexported collection) to copy from."""
    if model_id not in _protos:
        hidden = bpy.data.collections.get("_protos")
        if hidden is None:
            hidden = bpy.data.collections.new("_protos")
            bpy.context.scene.collection.children.link(hidden)
        parent = import_model(hidden, model_id, (0, 0, 0), collide=False, name=f"proto_{model_id}")
        ratio = DECIMATE.get(model_id)
        for obj in parent.children_recursive if ratio else ():
            if obj.type != "MESH":
                continue
            mod = obj.modifiers.new("decimate", "DECIMATE")
            mod.ratio = ratio
            with bpy.context.temp_override(object=obj, active_object=obj):
                bpy.ops.object.modifier_apply(modifier=mod.name)
        _protos[model_id] = parent
    return _protos[model_id]


def variants(model_id):
    """A library model's variants: its top-level parts grouped by their letter
    suffix (pachira_aquatica_01_bark_a and _leaves_a are variant a), each with the
    spot it stands on in the model. Poly Haven lays variants out side by side
    metres apart. Parts close together (a bunch of bananas) or a "set" (rocks meant
    to lie together) are one piece."""
    children = list(proto(model_id).children)
    groups = {}
    for child in children:
        found = re.search(r"_([a-z])(\.\d+)?$", child.name)
        groups.setdefault(found.group(1) if found else "", []).append(child)
    spots = [parts[0].location for parts in groups.values()]
    spread = max(((a - b).length for a in spots for b in spots), default=0.0)
    if "_set_" in model_id or spread < 0.75:
        return [(children, None)]
    return [(parts, parts[0].location.copy()) for _, parts in sorted(groups.items())]


_turns = {}


def place(coll, model_id, location, rot_deg=0.0, scale=1.0, name=None, collide=False, surface="teak", **props):
    """A linked copy of a library model: the meshes are shared, so the area stores them
    once. A model with several variants places one of them, in turn, centred on the spot."""
    parent = empty(name or f"prop_{model_id}", coll, location, (0, 0, math.radians(rot_deg)), **props)
    parent.scale = (scale, scale, scale)

    def copy(obj, to):
        dup = obj.copy()
        coll.objects.link(dup)
        dup.parent = to
        for child in obj.children:
            copy(child, dup)
        return dup

    choices = variants(model_id)
    turn = _turns.get(model_id, 0)
    _turns[model_id] = turn + 1
    parts, spot = choices[turn % len(choices)]
    for child in parts:
        dup = copy(child, parent)
        if spot is not None:
            dup.location.x -= spot.x
            dup.location.y -= spot.y
    if collide:
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ v.co for o in parent.children_recursive if o.type == "MESH" for v in o.data.vertices]
        xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
        collider(name or f"{model_id}_{len(coll.objects)}", coll, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), surface)
    return parent


def beads(name, coll, points, radius, mat):
    """A string of small flowers (a jasmine garland): one octahedron per point."""
    verts, faces = [], []
    for (x, y, z) in points:
        b = len(verts)
        r = radius
        verts += [(x + r, y, z), (x - r, y, z), (x, y + r, z), (x, y - r, z), (x, y, z + r), (x, y, z - r)]
        for (i, j) in ((0, 2), (2, 1), (1, 3), (3, 0)):
            faces.append((b + i, b + j, b + 4))
            faces.append((b + j, b + i, b + 5))
    return mesh_object(name, coll, verts, faces, mat, uvs=[(0.5, 0.5)] * (len(faces) * 3))


def flame(name, coll, x, y, z, size, mat):
    """A small flame: two crossed cards of the painted flame (candles, oil lamps),
    `size` tall with the wick at the bottom."""
    verts, faces, uvs = [], [], []
    for a in (0.0, math.pi / 2):
        c, s = math.cos(a) * size * 0.25, math.sin(a) * size * 0.25
        b = len(verts)
        verts += [(x - c, y - s, z - size * 0.05), (x + c, y + s, z - size * 0.05), (x + c, y + s, z + size), (x - c, y - s, z + size)]
        faces.append((b, b + 1, b + 2, b + 3))
        uvs += [(0, 0), (1, 0), (1, 1), (0, 1)]
    return mesh_object(name, coll, verts, faces, mat, uvs=uvs)


def strip(name, coll, centre, across, half, mat, v_top, v_bottom, u0=0.0, u1=1.0, drop=None):
    """A ribbon of quads along `centre` points, `half` wide each side along `across`
    (one vector per point); edges sit `drop` lower than the middle (a leaf's fold).
    U runs along, V across from v_top (left edge) to v_bottom (right edge)."""
    n = len(centre)
    verts, faces, uvs = [], [], []
    for i, (p, w) in enumerate(zip(centre, across)):
        d = drop[i] if drop else 0.0
        verts += [(p[0] + w[0] * half, p[1] + w[1] * half, p[2] + w[2] * half - d), p,
                  (p[0] - w[0] * half, p[1] - w[1] * half, p[2] - w[2] * half - d)]
    vm = (v_top + v_bottom) / 2
    for i in range(n - 1):
        ua, ub = u0 + (u1 - u0) * i / (n - 1), u0 + (u1 - u0) * (i + 1) / (n - 1)
        for (j, va, vb) in ((0, v_top, vm), (1, vm, v_bottom)):
            a, b = i * 3 + j, (i + 1) * 3 + j
            faces.append((a, b, b + 1, a + 1))
            uvs += [(ua, va), (ub, va), (ub, vb), (ua, vb)]
    return mesh_object(name, coll, verts, faces, mat, uvs=uvs, smooth=True)


# ------------------------------------------------------------------ plants


def banana(coll, m, x, y, h, k, rng):
    """A banana plant: a leaning pseudo-stem, broad leaves torn by the wind, and the
    oldest leaves dead and hanging down the stem (Busy, 1921: groves round every house)."""
    lean = (rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15))
    top = (x + lean[0], y + lean[1], h)
    parts = [pole(f"banana_{k}_stem", coll, (x, y, -0.05), top, rng.uniform(0.11, 0.15), m["banana_stem"],
                  sides=8, metres=1.2, radius_end=0.08)]
    leaves = int(rng.integers(6, 10))
    for j in range(leaves):
        a = rng.uniform(0, 2 * math.pi)
        dead = j < 2 and rng.random() < 0.8
        row = 3 if dead else int(rng.choice([0, 0, 1, 1, 2]))
        length = rng.uniform(1.3, 2.0) * (0.85 if dead else 1)
        rise = rng.uniform(-1.4, -1.0) if dead else rng.uniform(0.5, 1.1)
        droop = rng.uniform(0.4, 0.9) if dead else rng.uniform(0.6, 1.4)
        z0 = h - rng.uniform(0.0, 0.35)
        seg = 9
        centre, across, drop = [], [], []
        for s in range(seg):
            t = s / (seg - 1)
            reach = length * t * (0.6 if dead else 1)
            z = z0 + length * (math.sin(rise) * t - droop * t * t * (0.2 if dead else 0.5))
            centre.append((top[0] + math.cos(a) * reach, top[1] + math.sin(a) * reach, z))
            twist = 0.15 * t
            across.append((-math.sin(a + twist), math.cos(a + twist), 0.12 * t))
            drop.append(0.06 + 0.1 * t)
        vc = 1 - (row + 0.5) * 0.25
        parts.append(strip(f"banana_{k}_leaf_{j}", coll, centre, across, rng.uniform(0.26, 0.32), m["banana_leaf"],
                           vc + 0.112, vc - 0.112, 0.006, 0.99, drop))
    return join(parts, f"banana_{k}")


def palm_fan(name, coll, base, a, e, size, mat, droop=0.0):
    """One sugar palm leaf: the petiole and pleated fan on a card folded down its middle."""
    ax = (math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))
    side = (-math.sin(a), math.cos(a), 0.0)
    nrm = (ax[1] * side[2] - ax[2] * side[1], ax[2] * side[0] - ax[0] * side[2], ax[0] * side[1] - ax[1] * side[0])
    verts, uvs = [], []
    for r, v in ((0, 0.0), (1, 0.5), (2, 1.0)):
        along = size * v
        for c, u in ((-1, 0.0), (0, 0.5), (1, 1.0)):
            fold = -0.18 * size * abs(c) * v
            p = [base[i] + ax[i] * along + side[i] * c * size / 2 + nrm[i] * fold for i in range(3)]
            p[2] -= droop * size * v * v
            verts.append(tuple(p))
            uvs.append((u, v))
    faces, fuv = [], []
    for r in range(2):
        for c in range(2):
            a0 = r * 3 + c
            q = (a0, a0 + 1, a0 + 4, a0 + 3)
            faces.append(q)
            fuv += [uvs[i] for i in q]
    return mesh_object(name, coll, verts, faces, mat, uvs=fuv, smooth=True)


def sugar_palm(coll, m, x, y, h, k, rng):
    """A Borassus palm, Cambodia's emblem: a straight dark trunk and a ball of stiff
    fans, the dead ones hanging in a skirt below the living crown."""
    parts = [pole(f"palm_{k}_trunk", coll, (x, y, -0.1), (x, y, h), 0.3, m["palm_trunk"], sides=10, metres=1.6,
                  radius_end=0.22)]
    collider(f"palm_{k}", coll, x - 0.3, x + 0.3, y - 0.3, y + 0.3, 0, 3)
    for j in range(30):
        a = rng.uniform(0, 2 * math.pi)
        dead = j < 7
        e = rng.uniform(-1.45, -1.2) if dead else rng.uniform(-0.35, 1.25)
        base = (x + math.cos(a) * 0.2, y + math.sin(a) * 0.2, h - (0.5 if dead else rng.uniform(0, 0.3)))
        parts.append(palm_fan(f"palm_{k}_fan_{j}", coll, base, a, e, rng.uniform(2.2, 2.7),
                              m["palm_fan_dead" if dead else "palm_fan"], droop=0.0 if dead else rng.uniform(0, 0.12)))
    return join(parts, f"palm_{k}")


def coconut_palm(coll, m, x, y, h, k, rng):
    """A coconut palm: a curving grey trunk, long arching fronds, a cluster of nuts."""
    a = rng.uniform(0, 2 * math.pi)
    bend = rng.uniform(0.8, 2.0)
    pts = [(x + math.cos(a) * bend * (t ** 2), y + math.sin(a) * bend * (t ** 2), h * t) for t in (i / 8 for i in range(9))]
    parts = [tube(f"coco_{k}_trunk", coll, pts, 0.2, m["palm_trunk"], sides=9, metres_per_v=1.6, radius_end=0.13)]
    collider(f"coco_{k}", coll, x - 0.25, x + 0.25, y - 0.25, y + 0.25, 0, 3)
    top = pts[-1]
    for j in range(16):
        b = rng.uniform(0, 2 * math.pi)
        rise = rng.uniform(-0.2, 0.9)
        length = rng.uniform(3.2, 4.2)
        droop = rng.uniform(0.7, 1.3)
        centre, across = [], []
        for s in range(9):
            t = s / 8
            centre.append((top[0] + math.cos(b) * length * t, top[1] + math.sin(b) * length * t,
                           top[2] + length * (math.sin(rise) * t - droop * 0.5 * t * t)))
            across.append((-math.sin(b), math.cos(b), 0.25))
        row = int(rng.integers(0, 2))
        vc = 0.75 if row == 0 else 0.25
        parts.append(strip(f"coco_{k}_frond_{j}", coll, centre, across, 0.6, m["coconut_leaf"], vc + 0.24, vc - 0.24,
                           0.0, 1.0, [0.1 + 0.25 * s / 8 for s in range(9)]))
    for j in range(6):
        b = rng.uniform(0, 2 * math.pi)
        parts.append(lathe(f"coco_{k}_nut_{j}", coll, [(0.0, -0.13), (0.1, -0.1), (0.13, 0.0), (0.1, 0.1), (0.0, 0.13)],
                           top[0] + math.cos(b) * 0.22, top[1] + math.sin(b) * 0.22, top[2] - 0.3 - rng.uniform(0, 0.15),
                           m["coconut"], segments=8))
    return join(parts, f"coco_{k}")


# ------------------------------------------------------------- vessels and offerings


JAR = [(0.0, 0.0), (0.17, 0.0), (0.24, 0.06), (0.33, 0.25), (0.36, 0.42), (0.32, 0.6), (0.2, 0.74),
       (0.13, 0.78), (0.14, 0.82), (0.155, 0.85), (0.12, 0.85), (0.11, 0.8)]


def water_jar(name, coll, x, y, m, scale=1.0, lid=True, **props):
    """A big glazed storage jar (ពាង), the Martaban type with a dark brown glaze."""
    obj = lathe(name, coll, [(r * scale, h * scale) for r, h in JAR], x, y, 0.0, m["glaze"], segments=20, **props)
    if lid:
        lathe(f"{name}_lid", coll, [(0.0, 0.88 * scale), (0.19 * scale, 0.86 * scale), (0.19 * scale, 0.845 * scale),
                                    (0.0, 0.845 * scale)], x, y, 0.0, m["worn"], segments=14)
    return obj


def candle(name, coll, x, y, z, m, height=0.16, lit=True):
    """A beeswax candle in a brass stick; returns the flame's position."""
    lathe(f"{name}_stick", coll, [(0.05, 0.0), (0.05, 0.01), (0.02, 0.03), (0.014, 0.12), (0.035, 0.14),
                                   (0.035, 0.15), (0.0, 0.15)], x, y, z, m["brass"], segments=12)
    lathe(f"{name}_wax", coll, [(0.013, 0.0), (0.013, height), (0.009, height + 0.008), (0.0, height + 0.008)],
          x, y, z + 0.15, m["wax"], segments=8)
    top = z + 0.15 + height + 0.01
    if lit:
        flame(f"{name}_flame", coll, x, y, top, 0.035, m["flame"])
    return (x, y, top + 0.015)


def incense_sticks(name, coll, x, y, z, m, n, rng, length=0.24, spread=0.05, lit=True):
    """Joss sticks standing in sand, red stems, the lit ends glowing."""
    for j in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, spread)
        bx, by = x + math.cos(a) * r, y + math.sin(a) * r
        tilt = rng.uniform(0.0, 0.18)
        tip = (bx + math.cos(a) * tilt * length, by + math.sin(a) * tilt * length, z + length)
        pole(f"{name}_{j}", coll, (bx, by, z - 0.03), tip, 0.0016, m["incense"], sides=4, metres=1.0)
        if lit:
            pole(f"{name}_{j}_ember", coll, tip, (tip[0], tip[1], tip[2] + 0.01), 0.0022, m["ember"], sides=4)


def sla_thor(name, coll, x, y, z, m):
    """ស្លាធម៌: the offering of folded betel leaves in tiers on a banana-trunk base,
    crowned with a flower; set in pairs before the dead and on altars."""
    lathe(f"{name}_base", coll, [(0.05, 0.0), (0.05, 0.14), (0.0, 0.14)], x, y, z, m["banana_stem"], segments=10)
    zz = z + 0.12
    for t, (r, h) in enumerate(((0.075, 0.09), (0.062, 0.08), (0.048, 0.07), (0.034, 0.06), (0.02, 0.05))):
        lathe(f"{name}_tier_{t}", coll, [(r, 0.0), (r * 0.35, h), (0.0, h)], x, y, zz, m["betel_leaf"], segments=10)
        zz += h * 0.62
    beads(f"{name}_flower", coll, [(x + dx, y + dy, zz + 0.02) for dx, dy in ((0, 0), (0.012, 0), (-0.012, 0), (0, 0.012), (0, -0.012))],
          0.009, m["jasmine"])


def lotus_buds(name, coll, x, y, z, m, n=3):
    """Lotus buds on long stems standing in a vase."""
    for j in range(n):
        a = j * 2.1
        tx, ty = x + math.cos(a) * 0.03, y + math.sin(a) * 0.03
        pole(f"{name}_stem_{j}", coll, (x, y, z), (tx, ty, z + 0.2 + j * 0.03), 0.003, m["stem_green"], sides=4)
        lathe(f"{name}_bud_{j}", coll, [(0.0, 0.0), (0.02, 0.015), (0.022, 0.035), (0.012, 0.06), (0.0, 0.075)],
              tx, ty, z + 0.2 + j * 0.03, m["lotus"], segments=8)


# ------------------------------------------------------------- the funeral


def coffin(coll, m, x0, x1, y0, y1, z):
    """The coffin (មឈូស) on its dais: teak with gilt kbach panels on red lacquer, a
    gabled lid with upswept corner finials, the white cloth laid across it and a
    jasmine garland along the ridge. Returns the lid's ridge height."""
    w = y1 - y0
    box("coffin_plinth", coll, x0 - 0.06, x1 + 0.06, y0 - 0.06, y1 + 0.06, z, z + 0.08, m["teak"], edge=0.01)
    zb = z + 0.08
    zt = zb + 0.48
    box("coffin_body", coll, x0, x1, y0, y1, zb, zt, m["lacquer"], edge=0.005)
    # Gilt panels on the four sides, each framed by a gold moulding.
    for name, (a0, a1, b0, b1) in {
        "s": (x0 + 0.04, x1 - 0.04, y0 - 0.006, y0), "n": (x0 + 0.04, x1 - 0.04, y1, y1 + 0.006),
        "w": (x0 - 0.006, x0, y0 + 0.04, y1 - 0.04), "e": (x1, x1 + 0.006, y0 + 0.04, y1 - 0.04),
    }.items():
        panel = box(f"coffin_panel_{name}", coll, a0, a1, b0, b1, zb + 0.05, zt - 0.05, m["coffin_panel"])
        right = (1, 0, 0) if name == "s" else (-1, 0, 0) if name == "n" else (0, -1, 0) if name == "w" else (0, 1, 0)
        picture_uvs(panel, right, (0, 0, 1))
    for zz in (zb + 0.02, zt - 0.02):
        box(f"coffin_band_{zz:.2f}", coll, x0 - 0.012, x1 + 0.012, y0 - 0.012, y1 + 0.012, zz - 0.012, zz + 0.012, m["gold"])
    # The gabled lid: two sloping gilt faces, lacquered ends, a gold ridge.
    ridge = zt + 0.22
    ov = 0.05
    ym = (y0 + y1) / 2
    verts = [(x0 - ov, y0 - ov, zt), (x1 + ov, y0 - ov, zt), (x1 + ov, ym, ridge), (x0 - ov, ym, ridge),
             (x0 - ov, y1 + ov, zt), (x1 + ov, y1 + ov, zt)]
    lid = mesh_object("coffin_lid", coll, verts, [(0, 1, 2, 3), (5, 4, 3, 2)], m["coffin_panel"],
                      uvs=[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (1, 0), (1, 1), (0, 1)])
    lid.data.update()
    mesh_object("coffin_lid_ends", coll, verts, [(0, 3, 4), (1, 5, 2)], m["lacquer"])
    box("coffin_lid_eave_s", coll, x0 - ov, x1 + ov, y0 - ov - 0.02, y0 - ov + 0.02, zt - 0.03, zt + 0.01, m["gold"])
    box("coffin_lid_eave_n", coll, x0 - ov, x1 + ov, y1 + ov - 0.02, y1 + ov + 0.02, zt - 0.03, zt + 0.01, m["gold"])
    pole("coffin_ridge", coll, (x0 - ov - 0.03, ym, ridge), (x1 + ov + 0.03, ym, ridge), 0.022, m["gold"], sides=8)
    # Upswept finials at the corners and the ridge ends, like small flames (ក្បាច់).
    for (cx, cy, cz, dx, dy) in ((x0 - ov, y0 - ov, zt, -1, -1), (x1 + ov, y0 - ov, zt, 1, -1),
                                 (x0 - ov, y1 + ov, zt, -1, 1), (x1 + ov, y1 + ov, zt, 1, 1),
                                 (x0 - ov - 0.03, ym, ridge, -1, 0), (x1 + ov + 0.03, ym, ridge, 1, 0)):
        tube(f"coffin_finial_{cx:.1f}_{cy:.1f}_{cz:.1f}", coll,
             [(cx, cy, cz), (cx + dx * 0.05, cy + dy * 0.04, cz + 0.06), (cx + dx * 0.06, cy + dy * 0.05, cz + 0.13)],
             0.018, m["gold"], sides=6, radius_end=0.003)
    # The white cloth across the coffin (to be drawn off by the monks), falling to each side.
    cx = (x0 + x1) / 2
    pts = [(ym - (w / 2 + ov + 0.02) - 0.0, zt - 0.3), (ym - (w / 2 + ov + 0.01), zt), (ym, ridge + 0.012),
           (ym + (w / 2 + ov + 0.01), zt), (ym + (w / 2 + ov + 0.02), zt - 0.3)]
    verts, faces = [], []
    for i, (yy, zz) in enumerate(pts):
        verts += [(cx - 0.25, yy, zz + 0.005), (cx + 0.25, yy, zz + 0.005)]
        if i:
            faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    mesh_object("coffin_cloth", coll, verts, faces, m["cotton"])
    beads("coffin_garland", coll, [(x0 + 0.1 + (x1 - x0 - 0.2) * t / 40, ym + 0.012 * math.sin(t), ridge + 0.03)
                                   for t in range(41)], 0.016, m["jasmine"])
    collider("coffin", coll, x0 - ov, x1 + ov, y0 - ov, y1 + ov, z, ridge)
    return ridge


def portrait(coll, m, x, y, z, width=0.3):
    """Sok's portrait on the altar: the photograph in a dark carved frame on a stand,
    leaning back a little, facing the mourners (south), with a jasmine garland."""
    h = width / 0.75
    tilt = math.radians(10)
    frame = 0.035
    parent = empty("portrait_sok", coll, (x, y, z), (tilt, 0, 0))
    pieces = [
        box("portrait_frame_l", coll, -width / 2 - frame, -width / 2, -0.012, 0.012, 0, h + 2 * frame, m["frame"], edge=0.004),
        box("portrait_frame_r", coll, width / 2, width / 2 + frame, -0.012, 0.012, 0, h + 2 * frame, m["frame"], edge=0.004),
        box("portrait_frame_b", coll, -width / 2, width / 2, -0.012, 0.012, 0, frame, m["frame"], edge=0.004),
        box("portrait_frame_t", coll, -width / 2, width / 2, -0.012, 0.012, h + frame, h + 2 * frame, m["frame"], edge=0.004),
        box("portrait_back", coll, -width / 2, width / 2, 0.004, 0.012, frame, h + frame, m["frame"]),
    ]
    photo = box("interact_portrait", coll, -width / 2, width / 2, -0.004, 0.004, frame, h + frame, m["photo"], action="examine")
    picture_uvs(photo, (1, 0, 0), (0, 0, 1))
    for obj in pieces + [photo]:
        obj.parent = parent
    # The stand behind it.
    stand = pole("portrait_stand", coll, (0, 0.012, h * 0.6), (0, 0.16, -0.01), 0.008, m["frame"], sides=6)
    stand.parent = parent
    garland = []
    for t in range(48):
        u = t / 47
        a = math.pi * u
        garland.append((-math.cos(a) * (width / 2 + frame + 0.01), -0.03, h * 0.35 + math.sin(a) * (h * 0.72)))
    beads("portrait_garland", coll, garland, 0.013, m["jasmine"]).parent = parent
    return parent


def altar(coll, m, x, y, z, rng):
    """The low table before the coffin: the portrait, two candles, the incense pot, a
    pair of sla thor, lotus buds, bananas, a coconut and rice."""
    w, d, h = 1.5, 0.55, 0.62
    x0, x1, y0, y1 = x - w / 2, x + w / 2, y - d / 2, y + d / 2
    box("altar_top", coll, x0, x1, y0, y1, z + h - 0.04, z + h, m["teak"], edge=0.008)
    for lx in (x0 + 0.05, x1 - 0.05):
        for ly in (y0 + 0.05, y1 - 0.05):
            box(f"altar_leg_{lx:.1f}_{ly:.1f}", coll, lx - 0.03, lx + 0.03, ly - 0.03, ly + 0.03, z, z + h - 0.04, m["teak"])
    cloth("altar_cloth_front", coll, x0, x1, z + 0.12, z + h, y0 - 0.01, m["cotton"], folds=9, depth=0.012)
    collider("altar_table", coll, x0, x1, y0, y1, z, z + h)
    t = z + h
    # The portrait stands raised at the back, above the offerings.
    box("altar_riser", coll, x - 0.24, x + 0.24, y + 0.05, y + 0.25, t, t + 0.14, m["teak"], edge=0.006)
    portrait(coll, m, x, y + 0.15, t + 0.14, 0.3)
    flames = [candle(f"altar_candle_{k}", coll, x + sx * 0.5, y + 0.05, t, m) for k, sx in enumerate((-1, 1))]
    for k, sx in enumerate((-1, 1)):
        sla_thor(f"altar_slathor_{k}", coll, x + sx * 0.29, y + 0.12, t, m)
        place(coll, "brass_vase_03", (x + sx * 0.67, y + 0.13, t), rot_deg=40 * k)
        lotus_buds(f"altar_lotus_{k}", coll, x + sx * 0.67, y + 0.13, t + 0.15, m)
    # Front row: incense pot, bananas, coconut, rice.
    place(coll, "brass_pot_01", (x, y - 0.17, t), scale=0.45)
    lathe("altar_incense_sand", coll, [(0.0, 0.0), (0.062, 0.0)], x, y - 0.17, t + 0.115, m["sand"], segments=12)
    incense_sticks("altar_incense", coll, x, y - 0.17, t + 0.115, m, 7, rng, length=0.17, spread=0.035)
    place(coll, "wooden_bowl_01", (x - 0.4, y - 0.12, t), scale=0.75)
    place(coll, "bananas", (x - 0.4, y - 0.12, t + 0.03), rot_deg=20, scale=0.5)
    lathe("altar_coconut", coll, [(0.0, 0.0), (0.06, 0.01), (0.085, 0.07), (0.07, 0.14), (0.04, 0.17), (0.0, 0.175)],
          x + 0.34, y - 0.12, t, m["coconut"], segments=12)
    place(coll, "wooden_bowl_01", (x + 0.58, y - 0.14, t), scale=0.42)
    lathe("altar_rice", coll, [(0.0, 0.045), (0.055, 0.03), (0.06, 0.02)], x + 0.58, y - 0.14, t, m["rice"], segments=10)
    return flames


def tall_burner(name, coll, x, y, z, m, rng, **props):
    """One of the four tall brass incense urns at the corners of the coffin."""
    lathe(name, coll, [(0.16, 0.0), (0.16, 0.03), (0.07, 0.06), (0.045, 0.12), (0.04, 0.55), (0.06, 0.6),
                       (0.12, 0.66), (0.16, 0.75), (0.17, 0.82), (0.15, 0.84), (0.0, 0.84)], x, y, z, m["brass"], segments=18)
    lathe(f"{name}_sand", coll, [(0.0, 0.0), (0.145, 0.0)], x, y, z + 0.835, m["sand"], segments=14)
    incense_sticks(f"{name}_stick", coll, x, y, z + 0.84, m, 3, rng, length=0.32, spread=0.03)
    collider(name, coll, x - 0.17, x + 0.17, y - 0.17, y + 0.17, z, z + 0.84)


def crocodile_flag(coll, m, x, y, rng):
    """ទង់ក្រពើ: the white crocodile flag on a tall bamboo pole, raised outside a house
    in mourning and kept up until the cremation; soaked, hanging heavy in the rain."""
    h = 6.6
    pts = [(x + 0.35 * (t ** 3), y + 0.1 * (t ** 3), h * t) for t in (i / 10 for i in range(11))]
    tube("flag_pole", coll, pts, 0.055, m["bamboo"], sides=8, metres_per_v=0.45, radius_end=0.025)
    collider("flag_pole", coll, x - 0.08, x + 0.08, y - 0.08, y + 0.08, 0, 3)
    top = pts[-1]
    pole("flag_crossbar", coll, (top[0] - 0.4, top[1], top[2] - 0.15), (top[0] + 0.4, top[1], top[2] - 0.15), 0.015, m["bamboo"])
    width, length = 0.78, 3.1
    nx, ny = 4, 24
    verts, uvs = [], []
    for j in range(ny + 1):
        t = j / ny
        for i in range(nx + 1):
            u = i / nx
            sway = 0.12 * math.sin(t * 2.4) * t
            fold = 0.035 * math.sin(u * math.pi * 3 + t * 5)
            verts.append((top[0] + (u - 0.5) * width * (1 - 0.15 * t), top[1] + sway + fold, top[2] - 0.15 - length * t))
            uvs.append((u, 1 - t))
    faces, fuv = [], []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            q = (a, a + 1, a + nx + 2, a + nx + 1)
            faces.append(q)
            fuv += [uvs[k] for k in q]
    mesh_object("crocodile_flag", coll, verts, faces, m["flag"], uvs=fuv, smooth=True)
    # Guy ropes steadying the pole.
    for a in (0.6, 2.7, 4.6):
        tube(f"flag_guy_{a:.1f}", coll, sag((x, y, 4.5), (x + math.cos(a) * 2.8, y + math.sin(a) * 2.8, 0.0), 0.08),
             0.006, m["rope"], sides=4)


def pavilion(coll, m, t, rng):
    """រោងបុណ្យ, the funeral pavilion: a bamboo frame lashed with rattan under a palm
    thatch roof, lined with white cloth, a scalloped valance along the eaves, white
    drapes at the back and sides, a slatted bamboo floor laid with mats."""
    x0, x1, y0, y1, eave, ridge = t["x0"], t["x1"], t["y0"], t["y1"], t["eave"], t["ridge"]
    ym = (y0 + y1) / 2
    bam = m["bamboo"]
    # Posts: four corners, the middle of the back, and the two gable posts up to the ridge.
    for (px, py, top) in ((x0, y0, eave), (x1, y0, eave), (x0, y1, eave), (0.0, y1, eave), (x1, y1, eave),
                          (x0, ym, ridge), (x1, ym, ridge)):
        pole(f"tent_post_{px:.0f}_{py:.0f}", coll, (px, py, -0.1), (px, py, top + 0.05), 0.065, bam, metres=0.42)
        collider(f"tent_post_{px:.0f}_{py:.0f}", coll, px - 0.08, px + 0.08, py - 0.08, py + 0.08, 0, top)
    # Eave plates, tie beams, the ridge pole and a king post in the middle.
    for py in (y0, y1):
        pole(f"tent_plate_{py:.0f}", coll, (x0 - 0.5, py, eave), (x1 + 0.5, py, eave), 0.055, bam, metres=0.42)
        for px in (x0, x1):
            lashing(f"tent_lash_{px:.0f}_{py:.0f}", coll, (px, py, eave), 0.07, m["rattan"])
    for px in (x0, 0.0, x1):
        pole(f"tent_tie_{px:.0f}", coll, (px, y0 - 0.2, eave - 0.02), (px, y1 + 0.2, eave - 0.02), 0.05, bam, metres=0.42)
    pole("tent_king_post", coll, (0.0, ym, eave), (0.0, ym, ridge), 0.05, bam, metres=0.42)
    pole("tent_ridge", coll, (x0 - 0.7, ym, ridge), (x1 + 0.7, ym, ridge), 0.06, bam, metres=0.42)
    half = ym - y0
    pitch = math.atan2(ridge - eave, half)
    over = 0.55
    # Rafters every metre, running out past the eaves.
    for k in range(int(x1 - x0) + 1):
        px = x0 + k
        for side in (-1, 1):
            ey = ym + side * (half + over)
            ez = eave - over * math.tan(pitch)
            pole(f"tent_rafter_{k}_{side}", coll, (px, ym, ridge + 0.02), (px, ey, ez), 0.035, bam, metres=0.42)
    # Thatch on both slopes, overhanging the gables, and a ridge capping.
    run = math.hypot(half + over, ridge - eave + over * math.tan(pitch))
    for side in (-1, 1):
        r = box(f"tent_roof_{'s' if side < 0 else 'n'}", coll, x0 - 0.7, x1 + 0.7, -run / 2, run / 2, -0.08, 0.08, m["thatch"])
        # Centred on the rafters' line, lifted along the slope's normal to rest on them.
        lift = 0.12
        r.location = (0.0, ym + side * (half + over) / 2 + side * math.sin(pitch) * lift,
                      (ridge + eave - over * math.tan(pitch)) / 2 + math.cos(pitch) * lift)
        r.rotation_euler = (-side * pitch, 0, 0)
    box("tent_roof_cap", coll, x0 - 0.75, x1 + 0.75, ym - 0.25, ym + 0.25, ridge + 0.12, ridge + 0.26, m["thatch"],
        tilt=(0, 0, 0))
    # White cloth lining under the roof, sagging between the rafters.
    for side in (-1, 1):
        verts, faces = [], []
        nx, ny = 32, 6
        for j in range(ny + 1):
            v = j / ny
            for i in range(nx + 1):
                px = x0 + (x1 - x0) * i / nx
                py = ym + side * half * v
                pz = ridge - 0.12 - (ridge - eave) * v - 0.06 * math.sin(math.pi * ((px - x0) % 1.0)) ** 2
                verts.append((px, py, pz))
        for j in range(ny):
            for i in range(nx):
                a = j * (nx + 1) + i
                # Faces look down, into the pavilion.
                faces.append((a, a + 1, a + nx + 2, a + nx + 1) if side < 0 else (a, a + nx + 1, a + nx + 2, a + 1))
        mesh_object(f"tent_lining_{side}", coll, verts, faces, m["cotton"], smooth=True)
    # Scalloped valance along the eaves and the gable tie beams.
    def valance(name, a, b, z, height=0.42):
        length = math.dist(a, b)
        n = max(2, int(length / 0.4))
        verts, faces, uvs = [], [], []
        for i in range(n + 1):
            u = i / n
            p = [a[k] + (b[k] - a[k]) * u for k in range(2)]
            wave = 0.02 * math.sin(u * length * 9)
            dx, dy = (b[1] - a[1]) / length, -(b[0] - a[0]) / length
            verts += [(p[0] + dx * wave, p[1] + dy * wave, z), (p[0] + dx * wave, p[1] + dy * wave, z - height)]
        for i in range(n):
            faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
            u0, u1 = i * length / n / 1.6, (i + 1) * length / n / 1.6
            uvs += [(u0, 1), (u1, 1), (u1, 0), (u0, 0)]
        mesh_object(name, coll, verts, faces, m["valance"], uvs=uvs)
    valance("tent_valance_s", (x0 - 0.45, y0 - 0.06), (x1 + 0.45, y0 - 0.06), eave + 0.02)
    valance("tent_valance_n", (x0 - 0.45, y1 + 0.06), (x1 + 0.45, y1 + 0.06), eave + 0.02)
    for px in (x0, x1):
        valance(f"tent_valance_{px:.0f}", (px + (0.06 if px > 0 else -0.06), y0), (px + (0.06 if px > 0 else -0.06), y1), eave)
    # Drapes: the back and the sides, open at the front.
    cloth("tent_drape_back", coll, x0, x1, 0.06, eave - 0.05, y1 - 0.03, m["cotton"], folds=14, depth=0.07)
    for px, name in ((x0, "w"), (x1, "e")):
        cloth(f"tent_drape_{name}", coll, y0 + 1.6, y1, 0.08, eave - 0.05, px, m["cotton"], folds=8, depth=0.07, axis="y")
        # The front of each side drape gathered and tied back to the corner post.
        cloth(f"tent_drape_{name}_tied", coll, y0 + 0.05, y0 + 0.35, 0.3, eave - 0.05, px, m["cotton"], folds=3, depth=0.05, axis="y")
        tube(f"tent_tieback_{name}", coll, [(px - 0.1, y0 + 0.2, 1.2), (px, y0 + 0.4, 1.18), (px + 0.1, y0 + 0.2, 1.2)],
             0.01, m["rope"], sides=4)
    collider("tent_back", coll, x0, x1, y1 - 0.08, y1 + 0.02, 0, eave)
    for px in (x0, x1):
        collider(f"tent_side_{px:.0f}", coll, px - 0.05, px + 0.05, y0 + 1.6, y1, 0, eave)
    # Floor: bamboo slats on low sleepers, mats laid where the mourners sit.
    box("tent_floor", coll, x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 0.1, 0.0, 0.05, m["bamboo_slats"])
    for k, (mx0, mx1, my0, my1) in enumerate(((-3.0, -1.2, 1.4, 3.6), (1.2, 3.0, 1.4, 3.6), (-1.0, 1.0, 1.3, 2.9))):
        box(f"tent_mat_{k}", coll, mx0, mx1, my0, my1, 0.05, 0.056, m["mat"])


def protective_thread(coll, m, t):
    """The white cotton thread run round the pavilion, tied post to post overhead
    (snaps at A3-01). Kept as one object per side: thread_0 front, then clockwise."""
    x0, x1, y0, y1 = t["x0"], t["x1"], t["y0"], t["y1"]
    z = 2.3
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for k in range(4):
        (ax, ay), (bx, by) = corners[k], corners[(k + 1) % 4]
        span = math.hypot(bx - ax, by - ay)
        tube(f"thread_{k}", coll, sag((ax, ay, z), (bx, by, z), 0.03 * span, n=16), 0.004, m["thread"], sides=4)


def monks_seat(coll, m, x0, x1, y0, y1, h):
    """The raised seat where the monks sit to chant in the evening: white cloth over
    a plank platform, triangular cushions against the drape, a brass bowl of water."""
    box("monk_seat", coll, x0, x1, y0, y1, 0.0, h, m["teak"], edge=0.01)
    box("monk_seat_cloth", coll, x0 - 0.01, x1 + 0.01, y0 - 0.01, y1 + 0.01, h, h + 0.012, m["cotton"])
    cloth("monk_seat_skirt", coll, y0, y1, 0.02, h, x1 + 0.015, m["cotton"], folds=12, depth=0.02, axis="y")
    collider("monk_seat", coll, x0, x1, y0, y1, 0, h)
    n = 4
    for k in range(n):
        cy = y0 + 0.5 + k * (y1 - y0 - 1.0) / (n - 1)
        # ខ្នើយ: a firm triangular cushion leaned against the wall.
        verts = [(x0 + 0.05, cy - 0.22, h), (x0 + 0.05, cy + 0.22, h), (x0 + 0.05, cy + 0.22, h + 0.38),
                 (x0 + 0.05, cy - 0.22, h + 0.38), (x0 + 0.3, cy - 0.22, h), (x0 + 0.3, cy + 0.22, h)]
        mesh_object(f"monk_cushion_{k}", coll, verts, [(3, 2, 1, 0), (5, 2, 3, 4), (4, 3, 0), (2, 5, 1), (1, 5, 4, 0)],
                    m["cushion"])
        box(f"monk_mat_{k}", coll, x0 + 0.3, x1 - 0.05, cy - 0.3, cy + 0.3, h + 0.012, h + 0.018, m["mat"])
    place(coll, "brass_pot_01", (x1 - 0.2, y1 - 0.25, h + 0.012), scale=0.5)


def skor_drums(coll, m, x, y):
    """A pair of skor, the barrel drums of the funeral ensemble, resting on their frame."""
    for k, dx in enumerate((-0.28, 0.28)):
        d = lathe(f"skor_{k}", coll, [(0.21, -0.36), (0.235, -0.2), (0.245, 0.0), (0.235, 0.2), (0.21, 0.36)],
                  0, 0, 0, m["drum_wood"], segments=16)
        d.location = (x + dx, y, 0.42)
        d.rotation_euler = (math.radians(90), 0, math.radians(8))
        for s in (-1, 1):
            # The hide head stretched over each end, laced down the barrel.
            h = lathe(f"skor_{k}_head_{s}", coll, [(0.0, 0.0), (0.215, 0.0), (0.22, -0.02)], 0, 0, 0, m["hide"], segments=16)
            h.location = (x + dx, y + s * 0.362, 0.42)
            h.rotation_euler = (math.radians(-90 * s), 0, 0)
        for j in range(8):
            a = 2 * math.pi * j / 8
            tube(f"skor_{k}_lace_{j}", coll, [(x + dx + math.cos(a) * 0.215, y - 0.35, 0.42 + math.sin(a) * 0.215),
                                              (x + dx + math.cos(a + 0.4) * 0.25, y, 0.42 + math.sin(a + 0.4) * 0.25),
                                              (x + dx + math.cos(a) * 0.215, y + 0.35, 0.42 + math.sin(a) * 0.215)], 0.006, m["rope"], sides=3)
    box("skor_frame", coll, x - 0.6, x + 0.6, y - 0.2, y + 0.2, 0.05, 0.12, m["worn"])
    collider("skor", coll, x - 0.6, x + 0.6, y - 0.32, y + 0.32, 0, 0.7)
    for k in range(2):
        pole(f"skor_stick_{k}", coll, (x - 0.2 + k * 0.1, y - 0.42, 0.06), (x + 0.1 + k * 0.1, y - 0.52, 0.065), 0.012, m["worn"], sides=6)


def bamboo_bed(name, coll, m, x0, x1, y0, y1, h):
    """A គ្រែ: the slatted bamboo platform found under every house and at every gathering."""
    box(f"{name}_top", coll, x0, x1, y0, y1, h - 0.05, h, m["bamboo_slats"])
    for lx in (x0 + 0.06, x1 - 0.06):
        for ly in (y0 + 0.06, (y0 + y1) / 2, y1 - 0.06):
            pole(f"{name}_leg_{lx:.1f}_{ly:.1f}", coll, (lx, ly, 0.0), (lx, ly, h - 0.05), 0.04, m["bamboo"])
    for ly in (y0 + 0.06, y1 - 0.06):
        pole(f"{name}_rail_{ly:.1f}", coll, (x0, ly, h - 0.08), (x1, ly, h - 0.08), 0.035, m["bamboo"])
    collider(name, coll, x0, x1, y0, y1, 0, h)


def sandals(coll, m, pairs):
    """Mourners' sandals left at the edge of the mats."""
    for k, (x, y, a) in enumerate(pairs):
        for s in (-0.06, 0.06):
            b = box(f"sandal_{k}_{s:+.2f}", coll, -0.045, 0.045, -0.12, 0.12, 0.0, 0.018, m["sandal"], edge=0.006)
            b.location = (x + math.cos(a) * s, y + math.sin(a) * s, 0.009)
            b.rotation_euler = (0, 0, a)


# --------------------------------------------------------------- buildings


def ox_cart(coll, m, name, x, y, rot, hood=False):
    """A Khmer ox cart (រទេះគោ): two big spoked wheels, a slatted bed, a long pole,
    and on a passenger cart a curved hood of woven bamboo."""
    parent = empty(name, coll, (x, y, 0), (0, 0, rot))
    parts = []
    r = 0.68
    for side in (-0.78, 0.78):
        rim = [(side, r * math.cos(a), r + r * math.sin(a)) for a in (2 * math.pi * k / 24 for k in range(25))]
        parts.append(tube(f"{name}_rim_{side:+.1f}", coll, rim, 0.04, m["worn"], sides=6, metres_per_v=1.0))
        hub = lathe(f"{name}_hub_{side:+.1f}", coll, [(0.0, -0.12), (0.09, -0.12), (0.11, 0.0), (0.09, 0.12), (0.0, 0.12)],
                    0, 0, 0, m["worn"], segments=10)
        hub.location = (side, 0, r)
        hub.rotation_euler = (0, math.radians(90), 0)
        parts.append(hub)
        for k in range(12):
            a = 2 * math.pi * k / 12
            parts.append(tube(f"{name}_spoke_{side:+.1f}_{k}", coll, [(side, 0, r), (side, r * math.cos(a) * 0.95, r + r * math.sin(a) * 0.95)],
                              0.018, m["worn"], sides=5))
    parts.append(tube(f"{name}_axle", coll, [(-0.9, 0, r), (0.9, 0, r)], 0.045, m["worn"], sides=6))
    parts.append(box(f"{name}_bed", coll, -0.6, 0.6, -1.2, 1.4, r + 0.06, r + 0.12, m["old_planks"]))
    for sx in (-0.6, 0.6):
        for k in range(6):
            sy = -1.1 + k * 0.48
            parts.append(tube(f"{name}_stake_{sx:+.1f}_{k}", coll, [(sx, sy, r + 0.1), (sx * 1.05, sy, r + 0.55)], 0.02, m["bamboo"], sides=5))
        parts.append(tube(f"{name}_side_rail_{sx:+.1f}", coll, [(sx * 1.05, -1.15, r + 0.52), (sx * 1.05, 1.35, r + 0.52)], 0.025, m["bamboo"], sides=5))
    parts.append(tube(f"{name}_pole", coll, [(0, 1.3, r + 0.08), (0, 3.6, 0.55), (0, 4.2, 0.45)], 0.05, m["worn"], sides=6))
    parts.append(tube(f"{name}_yoke_rest", coll, [(0.0, 4.0, 0.0), (0.0, 4.0, 0.5)], 0.04, m["worn"], sides=5))
    if hood:
        verts, faces, uvs = [], [], []
        n = 10
        for i in range(n + 1):
            a = math.pi * i / n
            for yy in (-1.0, 1.1):
                verts.append((-0.68 * math.cos(a), yy, r + 0.5 + 0.65 * math.sin(a)))
        for i in range(n):
            faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
            uvs += [(i / n * 1.1, 0), (i / n * 1.1, 1.05), ((i + 1) / n * 1.1, 1.05), ((i + 1) / n * 1.1, 0)]
        parts.append(mesh_object(f"{name}_hood", coll, verts, faces, m["bamboo_wall_2s"], uvs=uvs))
    for p in parts:
        p.parent = parent
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in parts for v in o.data.vertices]
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    collider(name, coll, min(xs), max(xs), min(ys), max(ys), 0, 1.6)


def bamboo_fence(coll, m, name, a, b, gap=None):
    """A village fence: bamboo posts with three rails, as round the 1921 compounds.
    `gap` (from, to), in metres along the fence, leaves an opening."""
    length = math.dist(a, b)
    d = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
    n = max(1, round(length / 1.6))
    pieces = [(0.0, length)] if not gap else [(0.0, gap[0]), (gap[1], length)]
    for pi, (s0, s1) in enumerate(pieces):
        if s1 - s0 < 0.1:
            continue
        p0 = (a[0] + d[0] * s0, a[1] + d[1] * s0)
        p1 = (a[0] + d[0] * s1, a[1] + d[1] * s1)
        k = max(1, round((s1 - s0) / 1.6))
        for i in range(k + 1):
            px, py = p0[0] + (p1[0] - p0[0]) * i / k, p0[1] + (p1[1] - p0[1]) * i / k
            pole(f"{name}_{pi}_post_{i}", coll, (px, py, -0.2), (px, py, 1.25), 0.045, m["bamboo"])
        for z in (0.35, 0.75, 1.1):
            pole(f"{name}_{pi}_rail_{z:.2f}", coll, (p0[0], p0[1], z), (p1[0], p1[1], z + 0.01), 0.025, m["bamboo"])
        cx0, cx1 = sorted((p0[0], p1[0]))
        cy0, cy1 = sorted((p0[1], p1[1]))
        collider(f"{name}_{pi}", coll, cx0 - 0.06, cx1 + 0.06, cy0 - 0.06, cy1 + 0.06, 0, 1.25)
    return n
