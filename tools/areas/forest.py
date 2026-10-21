"""The forest round the village and the flooded road for Episode 1 (run inside
Blender by the area scripts): tropical trees with buttress roots, a banyan with
hanging roots wrapped in cloth as a spirit tree, bamboo thickets, dead trees,
termite mounds, the rotting flags of the family's earlier funerals, the
telegraph line along the road and the drowned rice fields beyond it.

Respectful horror (Cultural Guide 1, Art Bible 11): the spirit tree and the
small spirit house are weathered but intact, never damaged or mocked. The cloth
bands on the tree, the house's offerings and the old flags are to confirm with
the cultural advisor.
"""

import math

from kit import collider, lathe, mesh_object, sag, tube
from khmer import join, place, pole


def cards(name, coll, items, mat, cells=(2, 2)):
    """One mesh of leaf cards. Each item is (centre, size, yaw, pitch, cell): a
    square crossed with a second at right angles, showing one cell of an atlas."""
    cx, cy = cells
    verts, faces, uvs = [], [], []
    for (c, s, yaw, pitch, cell) in items:
        u0, v0 = (cell % cx) / cx, 1 - (cell // cx + 1) / cy
        du, dv = 1 / cx, 1 / cy
        for turn in (0.0, math.pi / 2):
            a = yaw + turn
            ax = (math.cos(a) * s / 2, math.sin(a) * s / 2, 0.0)
            up = (-math.sin(a) * math.sin(pitch) * s / 2, math.cos(a) * math.sin(pitch) * s / 2, math.cos(pitch) * s / 2)
            b = len(verts)
            for (i, j) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append(tuple(c[k] + ax[k] * i + up[k] * j for k in range(3)))
            faces.append((b, b + 1, b + 2, b + 3))
            uvs += [(u0, v0), (u0 + du, v0), (u0 + du, v0 + dv), (u0, v0 + dv)]
    return mesh_object(name, coll, verts, faces, mat, uvs=uvs)


def sprays(name, coll, items, mat, rows=2):
    """Bamboo leaf sprays: quads from a twig base outwards, one row of the atlas each.
    Items are (base, direction, length, width, row)."""
    verts, faces, uvs = [], [], []
    for (p, d, length, width, row) in items:
        side = (-d[1], d[0], 0.0)
        sl = math.hypot(side[0], side[1]) or 1
        side = (side[0] / sl * width / 2, side[1] / sl * width / 2, 0.0)
        tip = tuple(p[k] + d[k] * length for k in range(3))
        b = len(verts)
        verts += [tuple(p[k] - side[k] for k in range(3)), tuple(tip[k] - side[k] for k in range(3)),
                  tuple(tip[k] + side[k] for k in range(3)), tuple(p[k] + side[k] for k in range(3))]
        faces.append((b, b + 1, b + 2, b + 3))
        v0, v1 = 1 - (row + 1) / rows, 1 - row / rows
        uvs += [(0, v0), (1, v0), (1, v1), (0, v1)]
    return mesh_object(name, coll, verts, faces, mat, uvs=uvs)


def curve(a, b, lift, n=5):
    """Points from a to b bowed upwards by `lift` (negative droops)."""
    return [tuple(a[k] + (b[k] - a[k]) * t + (lift * 4 * t * (1 - t) if k == 2 else 0) for k in range(3))
            for t in (i / (n - 1) for i in range(n))]


# ----------------------------------------------------------------- trees


def tropical_tree(coll, m, x, y, h, k, rng, crown=1.0):
    """A big broadleaf tree of the lowland forest: a leaning trunk on buttress roots,
    a few heavy limbs and a dark, ragged crown."""
    parts = []
    r0 = rng.uniform(0.28, 0.42)
    lean = (rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8))
    trunk = [(x + lean[0] * t * t, y + lean[1] * t * t, h * 0.62 * t) for t in (i / 6 for i in range(7))]
    parts.append(tube(f"tree_{k}_trunk", coll, trunk, r0, m["bark"], sides=10, metres_per_v=1.5, radius_end=r0 * 0.6))
    for j in range(5):
        a = j * 2 * math.pi / 5 + rng.uniform(-0.3, 0.3)
        reach = r0 + rng.uniform(0.7, 1.4)
        parts.append(tube(f"tree_{k}_buttress_{j}", coll, [(x + math.cos(a) * r0 * 0.4, y + math.sin(a) * r0 * 0.4, 1.6),
                                                            (x + math.cos(a) * (r0 + 0.25), y + math.sin(a) * (r0 + 0.25), 0.5),
                                                            (x + math.cos(a) * reach, y + math.sin(a) * reach, -0.05)],
                          r0 * 0.4, m["bark"], sides=6, radius_end=0.05))
    ends, leaves = [], []
    for j in range(int(rng.integers(3, 6))):
        base = trunk[int(rng.integers(4, 7))]
        a, e = rng.uniform(0, 2 * math.pi), rng.uniform(0.3, 0.85)
        length = h * rng.uniform(0.3, 0.45) * crown
        end = (base[0] + math.cos(a) * math.cos(e) * length, base[1] + math.sin(a) * math.cos(e) * length,
               base[2] + math.sin(e) * length)
        limb = curve(base, end, -0.4 * length * 0.2)
        parts.append(tube(f"tree_{k}_limb_{j}", coll, limb, r0 * 0.45, m["bark"], sides=7, metres_per_v=1.5, radius_end=0.06))
        ends.append(end)
        for s in range(2):
            b = limb[2 + s]
            a2 = a + rng.uniform(-1.0, 1.0)
            l2 = length * rng.uniform(0.35, 0.6)
            end2 = (b[0] + math.cos(a2) * l2, b[1] + math.sin(a2) * l2, b[2] + rng.uniform(0.2, 0.9) * l2)
            parts.append(tube(f"tree_{k}_branch_{j}_{s}", coll, curve(b, end2, 0.2, 4), 0.07, m["bark"], sides=5, radius_end=0.02))
            ends.append(end2)
    for e in ends:
        for c in range(5):
            centre = (e[0] + rng.normal(0, 1.0), e[1] + rng.normal(0, 1.0), e[2] + rng.normal(0, 0.6))
            leaves.append((centre, rng.uniform(2.2, 3.4), rng.uniform(0, math.pi), rng.uniform(-0.4, 0.4),
                           int(rng.choice([0, 1, 2, 2, 3] if rng.random() < 0.15 else [0, 1, 2]))))
    parts.append(cards(f"tree_{k}_crown", coll, leaves, m["leaf_cluster"]))
    collider(f"tree_{k}", coll, x - r0, x + r0, y - r0, y + r0, 0, 3)
    return join(parts, f"tree_{k}")


def dead_tree(coll, m, x, y, h, k, rng):
    """A dead tree standing grey and leafless, its top snapped off, bare limbs clawing up."""
    parts = []
    r0 = rng.uniform(0.18, 0.32)
    lean = (rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2))
    trunk = [(x + lean[0] * t * t, y + lean[1] * t * t, h * t) for t in (i / 6 for i in range(7))]
    parts.append(tube(f"dead_{k}_trunk", coll, trunk, r0, m["bark_dead"], sides=8, metres_per_v=1.5, radius_end=r0 * 0.55))
    # The snapped top: a few jagged splinters.
    top = trunk[-1]
    for j in range(4):
        a = j * math.pi / 2 + rng.uniform(-0.4, 0.4)
        parts.append(tube(f"dead_{k}_splinter_{j}", coll, [top, (top[0] + math.cos(a) * 0.08, top[1] + math.sin(a) * 0.08,
                                                                 top[2] + rng.uniform(0.2, 0.7))], r0 * 0.25, m["bark_dead"], sides=4, radius_end=0.005))
    for j in range(int(rng.integers(3, 7))):
        base = trunk[int(rng.integers(2, 6))]
        a, e = rng.uniform(0, 2 * math.pi), rng.uniform(0.2, 1.0)
        length = rng.uniform(1.2, 3.5)
        end = (base[0] + math.cos(a) * math.cos(e) * length, base[1] + math.sin(a) * math.cos(e) * length, base[2] + math.sin(e) * length)
        limb = curve(base, end, rng.uniform(-0.3, 0.4))
        parts.append(tube(f"dead_{k}_limb_{j}", coll, limb, r0 * 0.35, m["bark_dead"], sides=5, radius_end=0.015))
        for s in range(2):
            b = limb[int(rng.integers(2, 5))]
            a2 = a + rng.uniform(-1.2, 1.2)
            l2 = length * rng.uniform(0.3, 0.6)
            parts.append(tube(f"dead_{k}_twig_{j}_{s}", coll, curve(b, (b[0] + math.cos(a2) * l2, b[1] + math.sin(a2) * l2,
                                                                        b[2] + rng.uniform(0.1, 0.8) * l2), 0.1, 3), 0.03, m["bark_dead"], sides=4, radius_end=0.004))
    collider(f"dead_{k}", coll, x - r0, x + r0, y - r0, y + r0, 0, 3)
    return join(parts, f"dead_{k}")


def banyan(coll, m, x, y, rng):
    """The old banyan (ជ្រៃ) by the path: a trunk of fused roots, roots crawling over the
    ground, hanging aerial roots, a huge crown. Villagers have wrapped its trunk in red,
    white and yellow cloth: a tree a spirit lives in."""
    parts = []
    strands = 16
    for j in range(strands):
        a = 2 * math.pi * j / strands + rng.uniform(-0.1, 0.1)
        pts = []
        for i in range(8):
            t = i / 7
            r = 1.5 - 0.75 * math.sin(min(1, t * 1.2) * math.pi / 2) + 0.7 * max(0, t - 0.75) * 4
            tw = a + t * 0.9
            pts.append((x + math.cos(tw) * r + rng.normal(0, 0.06), y + math.sin(tw) * r + rng.normal(0, 0.06), -0.2 + 6.0 * t))
        parts.append(tube(f"banyan_strand_{j}", coll, pts, rng.uniform(0.2, 0.34), m["bark"], sides=7, metres_per_v=1.5, radius_end=0.18))
    parts.append(tube("banyan_core", coll, [(x, y, -0.2), (x, y, 5.5)], 0.9, m["bark"], sides=10, metres_per_v=1.5, radius_end=0.6))
    for j in range(12):
        a = rng.uniform(0, 2 * math.pi)
        reach = rng.uniform(2.5, 6.0)
        pts = [(x + math.cos(a) * (1.3 + reach * t), y + math.sin(a) * (1.3 + reach * t) + 0.3 * math.sin(t * 6), 0.25 * (1 - t) ** 2 - 0.03)
               for t in (i / 6 for i in range(7))]
        parts.append(tube(f"banyan_root_{j}", coll, pts, rng.uniform(0.12, 0.22), m["bark"], sides=6, radius_end=0.03))
    leaves, hangers = [], []
    for j in range(8):
        a = 2 * math.pi * j / 8 + rng.uniform(-0.3, 0.3)
        base = (x + math.cos(a) * 0.9, y + math.sin(a) * 0.9, rng.uniform(4.6, 6.2))
        length = rng.uniform(6.5, 9.5)
        end = (base[0] + math.cos(a) * length, base[1] + math.sin(a) * length, base[2] + rng.uniform(1.0, 3.0))
        limb = curve(base, end, 1.2, 7)
        parts.append(tube(f"banyan_limb_{j}", coll, limb, 0.42, m["bark"], sides=8, metres_per_v=1.5, radius_end=0.1))
        for p in limb[1:]:
            for c in range(4):
                leaves.append(((p[0] + rng.normal(0, 1.6), p[1] + rng.normal(0, 1.6), p[2] + rng.uniform(0.8, 2.6)),
                               rng.uniform(2.8, 4.0), rng.uniform(0, math.pi), rng.uniform(-0.3, 0.3), int(rng.integers(0, 3))))
            # Aerial roots let down from the limb, a few reaching the ground.
            for c in range(int(rng.integers(1, 4))):
                hx, hy = p[0] + rng.normal(0, 0.3), p[1] + rng.normal(0, 0.3)
                bottom = 0.0 if rng.random() < 0.35 else rng.uniform(1.0, p[2] - 1.2)
                hangers.append(tube(f"banyan_hanger_{j}_{len(hangers)}", coll,
                                    [(hx, hy, p[2]), (hx + rng.normal(0, 0.08), hy + rng.normal(0, 0.08), (p[2] + bottom) / 2), (hx, hy, bottom)],
                                    rng.uniform(0.012, 0.04), m["bark"], sides=4, metres_per_v=1.5, radius_end=0.008))
    parts.append(cards("banyan_crown", coll, leaves, m["leaf_cluster"]))
    tree = join(parts + hangers, "banyan")
    # Cloth wound round the trunk: three bands and their loose ends.
    bands = []
    for j, (z, colour) in enumerate(((1.05, "cloth_red"), (1.3, "cotton"), (1.55, "cloth_yellow"))):
        rr = 1.5 - 0.75 * math.sin(min(1, (z + 0.2) / 6 * 1.2) * math.pi / 2) + 0.24
        # A flat band of cloth pulled round the trunk, creased where it crosses the strands.
        n = 48
        verts, faces = [], []
        for i in range(n + 1):
            a = 2 * math.pi * i / n
            r = rr + 0.04 * math.sin(a * strands) + 0.015 * math.sin(a * 7)
            dz = 0.025 * math.sin(a * 3 + j)
            verts += [(x + math.cos(a) * r, y + math.sin(a) * r, z - 0.07 + dz), (x + math.cos(a) * r, y + math.sin(a) * r, z + 0.07 + dz)]
            if i:
                faces.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
        bands.append(mesh_object(f"banyan_cloth_{j}", coll, verts, faces, m[colour], smooth=True))
        # The knotted ends hanging down.
        a = rng.uniform(0, 2 * math.pi)
        side = (-math.sin(a) * 0.06, math.cos(a) * 0.06)
        for e, lean in enumerate((-0.04, 0.05)):
            top = (x + math.cos(a) * (rr + 0.04), y + math.sin(a) * (rr + 0.04), z)
            bot = (x + math.cos(a + lean) * (rr + 0.12), y + math.sin(a + lean) * (rr + 0.12), z - rng.uniform(0.6, 0.95))
            bands.append(mesh_object(f"banyan_cloth_tail_{j}_{e}", coll,
                                     [(top[0] - side[0], top[1] - side[1], top[2]), (top[0] + side[0], top[1] + side[1], top[2]),
                                      (bot[0] + side[0] * 0.7, bot[1] + side[1] * 0.7, bot[2]), (bot[0] - side[0] * 0.7, bot[1] - side[1] * 0.7, bot[2])],
                                     [(0, 1, 2, 3)], m[colour]))
    join(bands, "banyan_cloth")
    collider("banyan", coll, x - 1.6, x + 1.6, y - 1.6, y + 1.6, 0, 6)
    return tree


def spirit_house(coll, m, x, y, facing, rng):
    """A small spirit house (ខ្ទមអ្នកតា) on a post at the foot of the banyan: weathered
    wood, a tiled gable roof, the old offerings left on its ledge (burnt-out incense, a
    cup, a banana-leaf cone of rice, dried flowers). Intact and cared for once."""
    parts = []
    ca, sa = math.cos(facing), math.sin(facing)

    def at(lx, ly, z):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z)

    parts.append(pole("spirit_post", coll, at(0, 0, -0.1), at(0, 0, 1.15), 0.07, m["post_rough"], sides=6, metres=2.0))
    w, d, h0, h1 = 0.62, 0.48, 1.15, 1.6
    verts = [at(sx * w / 2, sy * d / 2, z) for z in (h0, h1) for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    parts.append(mesh_object("spirit_house_walls", coll, verts, [(0, 1, 5, 4), (1, 2, 6, 5), (3, 0, 4, 7), (3, 2, 1, 0)], m["old_planks"]))
    dark = [at(-w / 2 + 0.04, -d / 2 - 0.002, h0 + 0.05), at(w / 2 - 0.04, -d / 2 - 0.002, h0 + 0.05),
            at(w / 2 - 0.04, -d / 2 - 0.002, h1 - 0.03), at(-w / 2 + 0.04, -d / 2 - 0.002, h1 - 0.03)]
    parts.append(mesh_object("spirit_house_inside", coll, dark, [(0, 1, 2, 3)], m["soot"]))
    ridge = h1 + 0.32
    roof = [at(-w / 2 - 0.12, -d / 2 - 0.15, h1 - 0.05), at(w / 2 + 0.12, -d / 2 - 0.15, h1 - 0.05), at(w / 2 + 0.12, 0, ridge),
            at(-w / 2 - 0.12, 0, ridge), at(-w / 2 - 0.12, d / 2 + 0.15, h1 - 0.05), at(w / 2 + 0.12, d / 2 + 0.15, h1 - 0.05)]
    parts.append(mesh_object("spirit_house_roof", coll, roof, [(0, 1, 2, 3), (5, 4, 3, 2), (3, 2, 1, 0), (2, 3, 4, 5)], m["tiles"]))
    gables = [at(-w / 2, -d / 2, h1), at(-w / 2, d / 2, h1), at(-w / 2, 0, ridge - 0.04), at(w / 2, -d / 2, h1), at(w / 2, d / 2, h1), at(w / 2, 0, ridge - 0.04)]
    parts.append(mesh_object("spirit_house_gables", coll, gables, [(0, 1, 2), (0, 2, 1), (3, 4, 5), (3, 5, 4)], m["old_planks"]))
    for s in (-1, 1):
        parts.append(tube(f"spirit_finial_{s}", coll, [at(s * (w / 2 + 0.12), 0, ridge), at(s * (w / 2 + 0.2), 0, ridge + 0.12)],
                          0.02, m["gold_dull"], sides=4, radius_end=0.004))
    ledge = [at(-w / 2 - 0.06, -d / 2 - 0.22, h0 - 0.03), at(w / 2 + 0.06, -d / 2 - 0.22, h0 - 0.03), at(w / 2 + 0.06, d / 2, h0 - 0.03),
             at(-w / 2 - 0.06, d / 2, h0 - 0.03)]
    parts.append(mesh_object("spirit_house_ledge", coll, ledge + [(p[0], p[1], p[2] + 0.03) for p in ledge],
                             [(4, 5, 6, 7), (3, 2, 1, 0), (0, 1, 5, 4)], m["old_planks"]))
    # Offerings on the ledge, long untended.
    lx, ly, lz = at(0.15, -d / 2 - 0.1, h0)
    parts.append(lathe("spirit_cup", coll, [(0.0, 0.0), (0.025, 0.0), (0.035, 0.04), (0.0, 0.035)], lx, ly, lz, m["clay"], segments=8))
    lx, ly, lz = at(-0.15, -d / 2 - 0.1, h0)
    parts.append(lathe("spirit_rice_cone", coll, [(0.045, 0.0), (0.0, 0.09)], lx, ly, lz, m["betel_leaf_dry"], segments=8))
    lx, ly, lz = at(0.0, -d / 2 - 0.12, h0)
    parts.append(lathe("spirit_incense_can", coll, [(0.03, 0.0), (0.03, 0.06), (0.0, 0.06)], lx, ly, lz, m["iron"], segments=8))
    for j in range(5):
        a = j * 1.3
        tip = (lx + math.cos(a) * 0.02, ly + math.sin(a) * 0.02, lz + 0.06 + rng.uniform(0.05, 0.12))
        parts.append(tube(f"spirit_incense_{j}", coll, [(lx, ly, lz + 0.05), tip], 0.0016, m["incense_burnt"], sides=4))
    house = join(parts, "spirit_house")
    collider("spirit_house", coll, x - 0.45, x + 0.45, y - 0.45, y + 0.45, 0, 1.6)
    return house


def bamboo_clump(coll, m, x, y, k, rng):
    """A clump of thorny bamboo: tall culms arching out from one root, plumes of
    narrow leaves on their upper halves, dead culms leaning and snapped."""
    culms, leaves = [], []
    for j in range(int(rng.integers(18, 28))):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, 0.7)
        bx, by = x + math.cos(a) * r, y + math.sin(a) * r
        h = rng.uniform(7.0, 11.5)
        out = rng.uniform(0.6, 3.2) + r
        dead = rng.random() < 0.12
        if dead:
            h *= rng.uniform(0.3, 0.6)
        pts = []
        for i in range(7):
            t = i / 6
            pts.append((bx + math.cos(a) * out * t * t, by + math.sin(a) * out * t * t, -0.1 + h * (t - 0.12 * t * t * out / 3)))
        culms.append(tube(f"bamboo_{k}_culm_{j}", coll, pts, rng.uniform(0.04, 0.065), m["bamboo_dead" if dead else "bamboo"],
                          sides=6, metres_per_v=0.4, radius_end=0.015))
        if dead:
            continue
        for i in range(3, 7):
            p = pts[i]
            for s in range(3):
                b = a + rng.uniform(-1.4, 1.4)
                d = (math.cos(b) * 0.8, math.sin(b) * 0.8, rng.uniform(-0.6, 0.1))
                leaves.append((p, d, rng.uniform(1.0, 1.6), rng.uniform(0.5, 0.7), int(rng.integers(0, 2))))
    culms.append(sprays(f"bamboo_{k}_leaves", coll, leaves, m["bamboo_leaves"]))
    collider(f"bamboo_{k}", coll, x - 0.8, x + 0.8, y - 0.8, y + 0.8, 0, 3)
    return join(culms, f"bamboo_{k}")


def termite_mound(coll, m, x, y, h, k, rng):
    """A termite mound of red earth, lumpy and spired: the forest is full of them."""
    profile = [(0.0, -0.05)]
    for i in range(1, 9):
        t = i / 8
        profile.append((max(0.05, (1 - t) ** 1.4 * h * 0.45 + rng.uniform(-0.05, 0.05)), h * t))
    profile.append((0.0, h * 1.02))
    obj = lathe(f"termite_{k}", coll, profile, x, y, 0.0, m["termite"], segments=14, v_scale=0.7)
    for v in obj.data.vertices:
        f = 1 + 0.18 * math.sin(v.co.z * 7 + math.atan2(v.co.y - y, v.co.x - x) * 3 + k) + rng.uniform(-0.06, 0.06)
        v.co.x = x + (v.co.x - x) * f
        v.co.y = y + (v.co.y - y) * f
    collider(f"termite_{k}", coll, x - h * 0.4, x + h * 0.4, y - h * 0.4, y + h * 0.4, 0, h)
    return obj


# ------------------------------------------------------- what the dead left


def old_flag(coll, m, x, y, k, rng):
    """The crocodile flag of an earlier funeral, never taken down: the pole leaning,
    the cloth grey with mildew and torn to rags (the family has buried others)."""
    h = rng.uniform(5.0, 6.2)
    lean = (rng.uniform(-1.0, 1.0), rng.uniform(-0.8, 0.8))
    pts = [(x + lean[0] * t * t, y + lean[1] * t * t, h * t) for t in (i / 8 for i in range(9))]
    parts = [tube(f"old_flag_{k}_pole", coll, pts, 0.05, m["bamboo_dead"], sides=6, metres_per_v=0.45, radius_end=0.025)]
    top = pts[-1]
    width, length = 0.7, rng.uniform(2.2, 2.8)
    nx, ny = 4, 20
    verts, uvs = [], []
    twist = rng.uniform(-0.8, 0.8)
    for j in range(ny + 1):
        t = j / ny
        for i in range(nx + 1):
            u = i / nx
            a = twist * t
            dx = (u - 0.5) * width * (1 - 0.2 * t)
            verts.append((top[0] + dx * math.cos(a), top[1] + dx * math.sin(a) + 0.05 * math.sin(u * 9 + t * 7), top[2] - 0.12 - length * t))
            uvs.append((u, 1 - t))
    faces, fuv = [], []
    for j in range(ny):
        for i in range(nx):
            a0 = j * (nx + 1) + i
            q = (a0, a0 + 1, a0 + nx + 2, a0 + nx + 1)
            faces.append(q)
            fuv += [uvs[q_] for q_ in q]
    parts.append(mesh_object(f"old_flag_{k}_cloth", coll, verts, faces, m["flag_old"], uvs=fuv, smooth=True))
    collider(f"old_flag_{k}", coll, x - 0.07, x + 0.07, y - 0.07, y + 0.07, 0, 2.5)
    return join(parts, f"old_flag_{k}")


def path_threads(coll, m, a, b, z, k, rng):
    """White thread strung across the path between two stakes, with strips of cloth
    knotted on it: someone has tried to close the way."""
    parts = []
    for p in (a, b):
        parts.append(pole(f"thread_stake_{k}_{p[0]:.0f}", coll, (p[0], p[1], -0.1), (p[0], p[1], z + 0.15), 0.03, m["bamboo_dead"], sides=5))
    line = sag((a[0], a[1], z), (b[0], b[1], z), 0.18, n=14)
    parts.append(tube(f"path_thread_{k}", coll, line, 0.004, m["thread"], sides=4))
    for i in range(2, 13, 2):
        p = line[i]
        parts.append(tube(f"path_thread_{k}_rag_{i}", coll, [p, (p[0] + rng.normal(0, 0.02), p[1] + rng.normal(0, 0.02), p[2] - rng.uniform(0.2, 0.45))],
                          0.012, m["cotton_dirty"], sides=3, radius_end=0.004))
    return join(parts, f"path_threads_{k}")


def ground_offering(coll, m, x, y, k, rng):
    """At the forest crossing: banana-leaf cones of rice and burnt-out incense in the mud,
    offerings to the spirits of the way."""
    parts = []
    for j in range(3):
        a = rng.uniform(0, 2 * math.pi)
        px, py = x + math.cos(a) * 0.25, y + math.sin(a) * 0.25
        parts.append(lathe(f"offering_{k}_cone_{j}", coll, [(0.06, 0.0), (0.0, 0.12)], px, py, 0.0, m["betel_leaf_dry"], segments=8))
        parts.append(lathe(f"offering_{k}_rice_{j}", coll, [(0.0, 0.11), (0.03, 0.1)], px, py, 0.0, m["rice"], segments=6))
    for j in range(6):
        a = rng.uniform(0, 2 * math.pi)
        px, py = x + math.cos(a) * 0.1, y + math.sin(a) * 0.1
        parts.append(tube(f"offering_{k}_incense_{j}", coll, [(px, py, -0.02), (px + rng.normal(0, 0.03), py + rng.normal(0, 0.03), rng.uniform(0.1, 0.22))],
                          0.0018, m["incense_burnt"], sides=4))
    return join(parts, f"ground_offering_{k}")


# ------------------------------------------------------------- the road


def telegraph_line(coll, m, posts, rng, broken=()):
    """The colonial telegraph along the road: tarred wooden poles with a crossarm and
    glass insulators, wires sagging between them; storms have pushed some over."""
    tops = []
    for k, (x, y, lean) in enumerate(posts):
        h = 6.4
        top = (x + math.sin(lean) * h * 0.7, y + math.sin(lean) * h * 0.25, h * math.cos(lean))
        if k in broken:
            mid = (x + math.sin(lean) * 2.4, y, 2.4)
            parts = [pole(f"telegraph_{k}_stump", coll, (x, y, -0.2), mid, 0.11, m["post_tar"], sides=8, metres=2.0, radius_end=0.1)]
            fallen = (mid[0] + 3.6, mid[1] + 0.8, 0.1)
            parts.append(pole(f"telegraph_{k}_top", coll, mid, fallen, 0.1, m["post_tar"], sides=8, metres=2.0, radius_end=0.09))
            tops.append((fallen[0], fallen[1], 0.25))
            join(parts, f"telegraph_{k}")
            collider(f"telegraph_{k}", coll, x - 0.12, x + 0.12, y - 0.12, y + 0.12, 0, 2.4)
            continue
        parts = [pole(f"telegraph_{k}_pole", coll, (x, y, -0.3), top, 0.12, m["post_tar"], sides=8, metres=2.0, radius_end=0.09)]
        arm_a = (top[0] - 0.6, top[1], top[2] - 0.35)
        arm_b = (top[0] + 0.6, top[1], top[2] - 0.35)
        parts.append(pole(f"telegraph_{k}_arm", coll, arm_a, arm_b, 0.05, m["post_tar"], sides=6, metres=2.0))
        for s, p in enumerate((arm_a, arm_b)):
            parts.append(lathe(f"telegraph_{k}_insulator_{s}", coll, [(0.0, 0.0), (0.04, 0.0), (0.035, 0.07), (0.02, 0.1), (0.0, 0.1)],
                               p[0] + (0.1 if s == 0 else -0.1), p[1], p[2] + 0.04, m["insulator"], segments=8))
        join(parts, f"telegraph_{k}")
        collider(f"telegraph_{k}", coll, x - 0.13, x + 0.13, y - 0.13, y + 0.13, 0, 3)
        tops.append((top[0], top[1], top[2] - 0.2))
    for k, (a, b) in enumerate(zip(tops, tops[1:])):
        for s, dx in enumerate((-0.5, 0.5)):
            pa, pb = (a[0] + dx, a[1], a[2]), (b[0] + dx, b[1], b[2])
            drop = 0.6 if a[2] > 1 and b[2] > 1 else 0.2
            tube(f"telegraph_wire_{k}_{s}", coll, sag(pa, pb, drop, n=12), 0.006, m["iron"], sides=4)


def grass_patch(name, coll, m, spots, rng, size=(0.5, 0.9)):
    """Tufts of grass or rice stubble: crossed cards, all in one mesh."""
    items = [((x, y, z + s * 0.5), s, rng.uniform(0, math.pi), 0.0, 0)
             for (x, y, z) in spots for s in (rng.uniform(*size),)]
    return cards(name, coll, items, m["grass"], cells=(1, 1))


def cobweb(name, coll, m, corner, right, down, size):
    """A cobweb strung into a corner: `corner` is where it is anchored, `right` and
    `down` the two directions it spreads (the threads radiate from the texture's top left)."""
    c = corner
    verts = [c, tuple(c[k] + right[k] * size for k in range(3)),
             tuple(c[k] + right[k] * size + down[k] * size for k in range(3)), tuple(c[k] + down[k] * size for k in range(3))]
    return mesh_object(name, coll, verts, [(0, 1, 2, 3)], m["cobweb"], uvs=[(0, 1), (1, 1), (1, 0), (0, 0)])


def decal(name, coll, m, mat, centre, width, length, yaw, z):
    """A flat quad laid just above a surface (footprints, spills)."""
    x, y = centre
    c, s = math.cos(yaw), math.sin(yaw)
    pts = [(-width / 2, -length / 2), (width / 2, -length / 2), (width / 2, length / 2), (-width / 2, length / 2)]
    verts = [(x + px * c - py * s, y + px * s + py * c, z) for px, py in pts]
    return mesh_object(name, coll, verts, [(0, 1, 2, 3)], m[mat], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])


def ting_mong(coll, m, x, y, facing, k, rng, arms_up=False):
    """`facing` turns the figure from looking south (0). A Ting Mong (តុកតា ទីងមោង): a life-size straw figure in old clothes, a cloth face
    drawn in charcoal, set up at the village's edge to frighten away spirits and
    sickness. It guards; it is not the threat. To confirm with the cultural advisor."""
    ca, sa = math.cos(facing), math.sin(facing)

    def at(lx, ly, z):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z)

    parts = [pole(f"tingmong_{k}_stake", coll, at(0, 0.08, -0.3), at(0, 0.08, 1.55), 0.035, m["bamboo_dead"], sides=5, metres=0.45)]
    # Straw legs bound at the ankles, a sarong of old cloth over the hips.
    for s in (-1, 1):
        parts.append(tube(f"tingmong_{k}_leg_{s}", coll, [at(s * 0.1, 0, 0.02), at(s * 0.11, 0, 0.5), at(s * 0.09, 0, 0.82)], 0.07, m["thatch"],
                          sides=6, metres_per_v=0.6, radius_end=0.09))
    sarong = lathe(f"tingmong_{k}_sarong", coll, [(0.2, 0.0), (0.22, 0.15), (0.2, 0.35), (0.19, 0.45)], 0, 0, 0, m["krama"], segments=12)
    sarong.location = at(0, 0, 0.55)
    parts.append(sarong)
    shirt = lathe(f"tingmong_{k}_shirt", coll, [(0.19, 0.0), (0.21, 0.2), (0.2, 0.42), (0.13, 0.52), (0.06, 0.55)], 0, 0, 0, m["rag"], segments=12)
    shirt.location = at(0, 0, 0.95)
    parts.append(shirt)
    # Arms of bundled straw in sleeves; one guardian holds a stick out at the road.
    for s in (-1, 1):
        if arms_up:
            hand = at(s * 0.55, -0.15, 1.55)
        else:
            hand = at(s * 0.32, -0.12, 0.95)
        parts.append(tube(f"tingmong_{k}_arm_{s}", coll, [at(s * 0.18, 0, 1.4), at(s * 0.3, -0.05, 1.25 if not arms_up else 1.45), hand],
                          0.05, m["rag"], sides=5, radius_end=0.035))
        # Straw bursting from the cuff instead of a hand.
        for j in range(7):
            a = 2 * math.pi * j / 7
            parts.append(tube(f"tingmong_{k}_straw_{s}_{j}", coll, [hand, (hand[0] + math.cos(a) * 0.06 + rng.normal(0, 0.02),
                                                                          hand[1] + math.sin(a) * 0.06, hand[2] - rng.uniform(0.1, 0.22))],
                              0.006, m["straw"], sides=3))
    if not arms_up:
        tip = at(0.35, -0.9, 1.25)
        parts.append(tube(f"tingmong_{k}_stick", coll, [at(0.32, -0.1, 0.9), tip], 0.018, m["post_rough"], sides=5))
    # The head: a stuffed sack with the drawn face, a krama tied round it.
    head = lathe(f"tingmong_{k}_head", coll, [(0.0, -0.12), (0.09, -0.11), (0.13, -0.02), (0.13, 0.06), (0.1, 0.13), (0.0, 0.16)],
                 0, 0, 0, m["tingmong_face"], segments=16, v_scale=2.0)
    head.location = at(0, 0, 1.68)
    head.rotation_euler = (0, 0, facing + math.pi / 2)  # the drawn face (texture centre) to the front
    parts.append(head)
    for j in range(12):
        a = 2 * math.pi * j / 12
        parts.append(tube(f"tingmong_{k}_neck_straw_{j}", coll, [at(0, 0, 1.5), at(math.cos(a) * 0.14, math.sin(a) * 0.14, 1.5 + rng.uniform(0.0, 0.08))],
                          0.006, m["straw"], sides=3))
    band = [at(0.135 * math.cos(a), 0.135 * math.sin(a), 1.76 + 0.01 * math.sin(a * 3)) for a in (2 * math.pi * i / 16 for i in range(17))]
    parts.append(tube(f"tingmong_{k}_krama", coll, band, 0.025, m["krama"], sides=4))
    parts.append(tube(f"tingmong_{k}_krama_tail", coll, [at(0.05, 0.13, 1.76), at(0.08, 0.2, 1.55), at(0.06, 0.22, 1.35)], 0.03, m["krama"],
                      sides=4, radius_end=0.015))
    figure = join(parts, f"tingmong_{k}")
    collider(f"tingmong_{k}", coll, x - 0.3, x + 0.3, y - 0.3, y + 0.3, 0, 1.8)
    return figure


def field_hut(coll, m, x, y, rng):
    """A rice-field shelter left to the flood: four posts, a slatted floor, a thatch roof
    slumped to one side, one wall of woven bamboo hanging loose."""
    parts = []
    w, d, s = 2.4, 2.0, 0.9
    tops = {}
    for i, lx in enumerate((-w / 2, w / 2)):
        for j, ly in enumerate((-d / 2, d / 2)):
            top = 2.4 if i == 0 else 1.7  # the east posts have sunk
            lean = 0.0 if i == 0 else 0.18
            tops[(i, j)] = (x + lx + lean, y + ly, top)
            parts.append(pole(f"field_hut_post_{i}{j}", coll, (x + lx, y + ly, -0.4), tops[(i, j)], 0.06, m["post_rough"], sides=6, metres=2.0))
    floor = [(x - w / 2, y - d / 2, s), (x + w / 2, y - d / 2, s - 0.25), (x + w / 2, y + d / 2, s - 0.25), (x - w / 2, y + d / 2, s)]
    parts.append(mesh_object("field_hut_floor", coll, floor + [(p[0], p[1], p[2] + 0.05) for p in floor],
                             [(4, 5, 6, 7), (3, 2, 1, 0), (0, 1, 5, 4), (2, 3, 7, 6)], m["bamboo_slats"]))
    a, b, c, e = tops[(0, 0)], tops[(1, 0)], tops[(1, 1)], tops[(0, 1)]
    roof = [(a[0] - 0.3, a[1] - 0.4, a[2]), (b[0] + 0.3, b[1] - 0.4, b[2] - 0.1), (c[0] + 0.3, c[1] + 0.4, c[2] - 0.1), (e[0] - 0.3, e[1] + 0.4, e[2])]
    parts.append(mesh_object("field_hut_roof", coll, roof + [(p[0], p[1], p[2] + 0.12) for p in roof],
                             [(4, 5, 6, 7), (3, 2, 1, 0), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m["thatch"]))
    wall = [(x - w / 2, y + d / 2 + 0.02, s + 0.05), (x + w / 2 - 0.3, y + d / 2 + 0.02, s - 0.15),
            (x + w / 2 - 0.5, y + d / 2 + 0.25, s - 0.9), (x - w / 2 + 0.2, y + d / 2 + 0.1, s - 0.6)]
    parts.append(mesh_object("field_hut_wall", coll, wall, [(0, 1, 2, 3)], m["bamboo_wall_2s"]))
    join(parts, "field_hut")
    collider("field_hut", coll, x - w / 2, x + w / 2 + 0.3, y - d / 2, y + d / 2, -0.3, 2.4)


def sampan(coll, m, x, y, yaw, sink, roll):
    """A small wooden boat swamped in the flooded field, half under the water."""
    verts, faces = [], []
    n = 10
    length, beam, depth = 4.2, 0.9, 0.42
    ca, sa = math.cos(yaw), math.sin(yaw)
    cr, sr = math.cos(roll), math.sin(roll)
    for i in range(n + 1):
        t = i / n
        lx = (t - 0.5) * length
        half = beam / 2 * math.sin(math.pi * t) ** 0.6
        sheer = depth * (0.8 + 0.6 * (2 * t - 1) ** 4)
        for (ly, lz) in ((-half, sheer), (-half * 0.6, 0.05), (0.0, 0.0), (half * 0.6, 0.05), (half, sheer)):
            ry, rz = ly * cr - lz * sr, ly * sr + lz * cr
            verts.append((x + lx * ca - ry * sa, y + lx * sa + ry * ca, rz - sink))
    for i in range(n):
        for j in range(4):
            a = i * 5 + j
            faces.append((a, a + 5, a + 6, a + 1))
            faces.append((a + 1, a + 6, a + 5, a))
    mesh_object("sampan", coll, verts, faces, m["old_planks"], smooth=True)


def milestone(coll, m, x, y, facing):
    """A colonial road marker: a white stone with a rounded red cap, the town and its distance."""
    ca, sa = math.cos(facing), math.sin(facing)
    w, d, h = 0.4, 0.22, 0.75
    pts = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    verts = [(x + px * ca - py * sa, y + px * sa + py * ca, z) for z in (-0.05, h) for (px, py) in pts]
    faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    uvs = [(0, 0), (0.5, 0), (0.5, 1), (0, 1), (0.5, 0), (0.5, 0.02), (0.5, 0.02), (0.5, 1),
           (0.5, 0), (1, 0), (1, 1), (0.5, 1), (0.5, 0), (0.5, 0.02), (0.5, 0.02), (0.5, 1)]
    stone = mesh_object("milestone", coll, verts, faces, m["milestone"], uvs=uvs)
    cap = tube("milestone_cap", coll, [(x - w / 2 * ca, y - w / 2 * sa, h), (x + w / 2 * ca, y + w / 2 * sa, h)], d / 2, m["cloth_red"], sides=10)
    join([stone, cap], "milestone")
    collider("milestone", coll, x - 0.25, x + 0.25, y - 0.25, y + 0.25, 0, 0.9)
