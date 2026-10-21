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

from mathutils import Matrix, Vector

from kit import box, collider, empty, lathe, mesh_object, sag, tube
from khmer import beads, join, place, pole


def pivot(obj, x, y, z=0.0):
    """Moves a joined object's origin to (x, y, z), its foot, so the game can turn it there."""
    obj.data.transform(Matrix.Translation(Vector((-x, -y, -z))))
    obj.location = (x, y, z)
    return obj


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
    # Its own pivot at its foot: the game turns and moves it while nobody is looking.
    figure = pivot(join(parts, f"tingmong_{k}"), x, y)
    # Which way it faces, as an angle in the ground plane (radians from +X).
    figure["front"] = facing - math.pi / 2
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


# --------------------------------------------------------- the Neak Ta


def wrapped_stone(name, coll, m, base, r, h, tilt, cover_mat, sash_mat, rng, front=-math.pi / 2):
    """A Neak Ta stone: a rough, lumpy boulder leaning a little, with a cloth draped
    over its head down to a ragged hem, and a sash knotted round its middle whose two
    ends hang down the front (`front`, an angle in the ground plane). Returns the parts."""
    bx, by, bz = base
    ca, sa = math.cos(tilt[0]), math.sin(tilt[0])
    cb, sb = math.cos(tilt[1]), math.sin(tilt[1])
    waves = [(rng.integers(1, 4), rng.integers(1, 3), rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(0.04, 0.09)) for _ in range(5)]
    squash = rng.uniform(0.75, 0.95)

    def point(phi, t, inflate=1.0, out=0.0):
        """The surface at angle `phi`, height fraction `t` (0 base, 1 top)."""
        lump = 1 + sum(a * math.sin(kp * phi + p) * math.cos(kt * t * math.pi + q) for kp, kt, p, q, a in waves)
        # Wider low down, rounded at the top, flat where it stands.
        rho = r * lump * (math.sqrt(max(0.0, 1 - (1.15 * t - 0.15) ** 2)) * 0.85 + 0.15 * (1 - t)) * inflate + out
        lx, ly, lz = rho * math.cos(phi), rho * math.sin(phi) * squash, h * t
        # Lean: about x, then about y, round the foot.
        ly, lz = ly * ca - lz * sa, ly * sa + lz * ca
        lx, lz = lx * cb + lz * sb, -lx * sb + lz * cb
        return (bx + lx, by + ly, bz + lz)

    def shell(name, rows, seg, mat, inflate, out, hem=None):
        verts, faces = [], []
        for i, t in enumerate(rows):
            for j in range(seg):
                phi = 2 * math.pi * j / seg
                tt = t if hem is None or i else hem[j]
                verts.append(point(phi, tt, inflate, out + (0.02 if hem is not None and i == 0 else 0.0)))
        for i in range(len(rows) - 1):
            for j in range(seg):
                a, b = i * seg + j, i * seg + (j + 1) % seg
                faces.append((a, b, b + seg, a + seg))
        top = len(verts)
        verts.append(point(0.0, 1.0, inflate, out))
        last = (len(rows) - 1) * seg
        for j in range(seg):
            faces.append((last + j, last + (j + 1) % seg, top))
        return mesh_object(name, coll, verts, faces, mat, smooth=True)

    seg = 14
    parts = [shell(name, [i / 9 * 0.99 for i in range(10)], seg, m["stone_wet"], 1.0, 0.0)]
    # The cloth over its head: down to a ragged hem at about half its height.
    hem = [rng.uniform(0.38, 0.55) for _ in range(seg)]
    parts.append(shell(f"{name}_cover", [0.45 + 0.54 * i / 6 for i in range(7)], seg, cover_mat, 1.04, 0.012, hem=hem))
    # The sash, knotted at the front, its ends hanging.
    ring = [point(2 * math.pi * j / 16, 0.3, 1.0, 0.02) for j in range(17)]
    parts.append(tube(f"{name}_sash", coll, ring, 0.022, sash_mat, sides=5))
    # The ends hang from the knot against the stone, one longer than the other.
    for k, (side, low) in enumerate(((-0.12, 0.1), (0.1, 0.04))):
        tail = [point(front + side * f, 0.3 - (0.3 - low) * f, 1.0, 0.035 + 0.01 * f) for f in (0.0, 0.35, 0.7, 1.0)]
        parts.append(tube(f"{name}_sash_end_{k}", coll, tail, 0.02, sash_mat, sides=4, radius_end=0.014))
    return parts


def neak_ta_shrine(coll, m, x, y, facing, rng):
    """The village's Neak Ta shrine (អ្នកតា) at the foot of the banyan: a spirit house
    raised on a post under a cloth canopy, and below it the spirit's own seat, worn
    elongated stones wrapped in saffron and red cloth among fragments of old
    sculpture, as Neak Ta are kept in stones and roots. The offerings the custom
    asks for (a pair of sla thor, two bowls of water, five candles, five incense
    sticks, food, flowers, rice spirit) are all there, and all of them old: candles
    burnt down to puddles of wax, the food gone black, the garlands brown. Nobody
    has tended it since Sok died. Intact; to confirm with the cultural advisor."""
    ca, sa = math.cos(facing), math.sin(facing)

    def at(lx, ly, z=0.0):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z)

    parts = []
    # A low platform of old bricks, cracked, roots pushing through.
    w, d = 2.2, 1.6
    verts = [at(sx * w / 2, sy * d / 2, z) for z in (0.0, 0.32) for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    parts.append(mesh_object("neakta_platform", coll, verts, [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m["brick"]))
    for k in range(5):
        a = rng.uniform(0, 2 * math.pi)
        start = at(rng.uniform(-0.8, 0.8), d / 2 - 0.1, 0.33)
        parts.append(tube(f"neakta_root_{k}", coll, [start, at(rng.uniform(-1, 1), rng.uniform(-0.3, 0.6), 0.34),
                                                     at(rng.uniform(-1.3, 1.3), -d / 2 - 0.2, 0.05)], 0.05, m["bark"], sides=5, radius_end=0.015))
    # The spirit's seat: rough stones standing in a row, leaning, each with a cloth
    # draped over its head and a sash knotted round it.
    for k, (lx, h, r, cover, sash) in enumerate(((-0.52, 0.55, 0.15, "cloth_saffron", "cloth_red"),
                                                  (-0.14, 0.78, 0.17, "cloth_red", "cotton_dirty"),
                                                  (0.22, 0.6, 0.15, "cotton_dirty", "cloth_saffron"),
                                                  (0.56, 0.4, 0.16, "cloth_saffron", "cloth_red"))):
        base = at(lx, 0.2 + rng.uniform(-0.06, 0.06), 0.32)
        stone = wrapped_stone(f"neakta_stone_{k}", coll, m, base, r, h,
                              (rng.uniform(-0.18, 0.18), rng.uniform(-0.18, 0.18)), m[cover], m[sash], rng,
                              front=facing - math.pi / 2)
        if k == 1:
            # The tallest, in red: a node of its own the game can turn to face Sora.
            watch = pivot(join(stone, "neakta_stone_watch"), *base)
            watch["front"] = facing - math.pi / 2  # its knot faces out of the shrine
        else:
            parts += stone
    # Fragments of old carved sandstone, half sunk among the stones.
    for k, (lx, ly) in enumerate(((-0.85, -0.1), (0.85, 0.25), (0.6, -0.45))):
        b = box(f"neakta_fragment_{k}", coll, -0.18, 0.18, -0.12, 0.12, 0.0, rng.uniform(0.2, 0.35), m["stone_wet"], edge=0.03)
        b.location = at(lx, ly, 0.3)
        b.rotation_euler = (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), facing + rng.uniform(-1, 1))
        parts.append(b)
    # The spirit house above, on its post, under a stained cloth canopy.
    house = spirit_house(coll, m, *at(0.0, 0.55)[:2], facing, rng)
    house.location.z += 0.32
    for k, (lx, ly) in enumerate(((-1.0, -0.75), (1.0, -0.75), (-1.0, 0.75), (1.0, 0.75))):
        parts.append(pole(f"neakta_canopy_post_{k}", coll, at(lx, ly, 0.2), at(lx, ly, 2.4), 0.03, m["bamboo_dead"], sides=5))
    n = 10
    cverts, cfaces = [], []
    for j in range(n + 1):
        for i in range(n + 1):
            u, v = i / n, j / n
            sagz = 2.35 - 0.25 * math.sin(math.pi * u) * math.sin(math.pi * v)
            cverts.append(at(-1.05 + 2.1 * u, -0.8 + 1.6 * v, sagz))
    for j in range(n):
        for i in range(n):
            a0 = j * (n + 1) + i
            cfaces.append((a0, a0 + 1, a0 + n + 2, a0 + n + 1))
    parts.append(mesh_object("neakta_canopy", coll, cverts, cfaces, m["cloth_red"], smooth=True))
    # Offerings on the platform's front edge.
    edge = -d / 2 + 0.2
    for k, lx in enumerate((-0.35, 0.35)):
        px, py, pz = at(lx, edge, 0.32)
        parts.append(lathe(f"neakta_slathor_{k}", coll, [(0.05, 0.0), (0.05, 0.12), (0.06, 0.13), (0.03, 0.28), (0.0, 0.32)],
                           px, py, pz, m["betel_leaf_dry"], segments=8))
        bx, by, bz = at(lx * 0.5, edge + 0.05, 0.32)
        parts.append(lathe(f"neakta_bowl_{k}", coll, [(0.0, 0.0), (0.05, 0.0), (0.07, 0.05), (0.0, 0.04)], bx, by, bz, m["glaze"], segments=10))
    for k in range(5):
        cx, cy, cz = at(-0.4 + 0.2 * k, edge - 0.12, 0.32)
        hgt = rng.uniform(0.0, 0.05)
        parts.append(lathe(f"neakta_wax_{k}", coll, [(0.0, 0.0), (0.06, 0.0), (0.05, 0.008), (0.015, 0.012 + hgt), (0.0, 0.015 + hgt)],
                           cx, cy, cz, m["wax_dirty"], segments=8))
    for k in range(5):
        a = rng.uniform(0, 2 * math.pi)
        bx, by, bz = at(0.0, edge, 0.32)
        tip = (bx + math.cos(a) * 0.04, by + math.sin(a) * 0.04, bz + rng.uniform(0.05, 0.15))
        parts.append(tube(f"neakta_incense_{k}", coll, [(bx, by, bz), tip], 0.0018, m["incense_burnt"], sides=4))
    # Food gone black on a banana leaf, a bottle of rice spirit, brown garlands.
    fx, fy, fz = at(0.7, edge + 0.1, 0.33)
    parts.append(lathe("neakta_leaf_plate", coll, [(0.0, 0.0), (0.16, 0.0), (0.18, 0.02)], fx, fy, fz, m["betel_leaf_dry"], segments=10))
    parts.append(beads("neakta_rotten_rice", coll, [(fx + rng.normal(0, 0.05), fy + rng.normal(0, 0.05), fz + 0.025) for _ in range(40)], 0.012, m["rot"]))
    parts.append(lathe("neakta_bottle", coll, [(0.0, 0.0), (0.035, 0.0), (0.04, 0.12), (0.015, 0.18), (0.012, 0.24), (0.0, 0.24)],
                       *at(-0.75, edge + 0.15, 0.32), m["bottle"], segments=10))
    garland = [at(-0.9 + 1.8 * t, edge - 0.25 + 0.04 * math.sin(t * 9), 0.33) for t in (i / 50 for i in range(51))]
    parts.append(beads("neakta_dead_garland", coll, garland, 0.014, m["dead_flowers"]))
    # Strips of red and white cloth tied to the canopy posts, hanging limp.
    for k, (lx, ly) in enumerate(((-1.0, -0.75), (1.0, -0.75))):
        top = at(lx, ly, 1.9)
        parts.append(tube(f"neakta_ribbon_{k}", coll, [top, at(lx + 0.05, ly - 0.03, 1.3), at(lx + 0.02, ly - 0.06, 0.8)], 0.03,
                          m["cloth_red" if k else "cotton_dirty"], sides=3, radius_end=0.02))
    # Wax run down over the platform's edge from candles long burnt out.
    for k in range(9):
        lx = rng.uniform(-0.9, 0.9)
        top = at(lx, -d / 2 + 0.02, 0.33)
        parts.append(tube(f"neakta_drip_{k}", coll, [top, at(lx + rng.normal(0, 0.01), -d / 2 - 0.012, 0.3),
                                                      at(lx + rng.normal(0, 0.02), -d / 2 - 0.014, 0.32 - rng.uniform(0.05, 0.25))],
                          rng.uniform(0.006, 0.014), m["wax_dirty"], sides=5, radius_end=0.004))
    # A boiled chicken offered whole, gone black and soft.
    cx, cy, cz = at(-0.25, edge + 0.32, 0.33)
    parts.append(lathe("neakta_plate", coll, [(0.0, 0.0), (0.17, 0.0), (0.19, 0.025), (0.0, 0.015)], cx, cy, cz, m["glaze"], segments=12))
    body = lathe("neakta_chicken", coll, [(0.0, 0.0), (0.09, 0.01), (0.11, 0.06), (0.08, 0.11), (0.0, 0.13)], 0, 0, 0, m["rot_meat"], segments=10)
    body.location = (cx, cy, cz + 0.02)
    body.scale = (1.0, 1.35, 0.8)
    body.rotation_euler = (0.0, 0.0, facing)
    parts.append(body)
    for sgn in (-1, 1):
        parts.append(tube(f"neakta_chicken_leg_{sgn}", coll, [at(-0.25 + sgn * 0.05, edge + 0.4, 0.4), at(-0.25 + sgn * 0.08, edge + 0.52, 0.42),
                                                              at(-0.25 + sgn * 0.08, edge + 0.56, 0.37)], 0.018, m["rot_meat"], sides=5, radius_end=0.008))
    # Incense: a can crammed with burnt stubs, more stubs scattered in the ash.
    gx, gy, gz = at(0.45, edge + 0.3, 0.33)
    parts.append(lathe("neakta_incense_can", coll, [(0.06, 0.0), (0.065, 0.12), (0.0, 0.12)], gx, gy, gz, m["iron"], segments=10))
    for k in range(30):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, 0.05)
        b0 = (gx + math.cos(a) * r, gy + math.sin(a) * r, gz + 0.1)
        parts.append(tube(f"neakta_stub_{k}", coll, [b0, (b0[0] + rng.normal(0, 0.02), b0[1] + rng.normal(0, 0.02), b0[2] + rng.uniform(0.04, 0.2))],
                          0.0016, m["incense_burnt"], sides=3))
    # Dead marigold garlands hung on the canopy posts and heaped on the stones.
    for k, (lx, ly) in enumerate(((-1.0, -0.75), (1.0, -0.75), (0.0, 0.3))):
        cx2, cy2, cz2 = at(lx, ly, 1.6 if k < 2 else 1.0)
        loop = [(cx2 + math.cos(t) * 0.05, cy2 + math.sin(t) * 0.05, cz2 - 0.35 * (0.5 - 0.5 * math.cos(t)))
                for t in (2 * math.pi * i / 30 for i in range(31))]
        parts.append(beads(f"neakta_marigolds_{k}", coll, loop, 0.022, m["dead_marigold"]))
    # Yantra cloths nailed to the posts.
    for k, (lx, ly) in enumerate(((-1.0, -0.78), (1.0, -0.78))):
        px, py, pz = at(lx, ly, 1.25)
        c = (math.cos(facing), math.sin(facing))
        verts = [(px - c[0] * 0.13, py - c[1] * 0.13, pz - 0.15), (px + c[0] * 0.13, py + c[1] * 0.13, pz - 0.15),
                 (px + c[0] * 0.13, py + c[1] * 0.13, pz + 0.15), (px - c[0] * 0.13, py - c[1] * 0.13, pz + 0.15)]
        parts.append(mesh_object(f"neakta_yantra_{k}", coll, verts, [(0, 1, 2, 3)], m["yantra"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)]))
    # Red betel juice spat across the platform.
    sx, sy, _ = at(0.1, -0.1)
    ca2, sa2 = math.cos(facing), math.sin(facing)
    verts = [(sx + px * ca2 - py * sa2, sy + px * sa2 + py * ca2, 0.322) for px, py in ((-1.0, -0.7), (1.0, -0.7), (1.0, 0.7), (-1.0, 0.7))]
    parts.append(mesh_object("neakta_stains", coll, verts, [(0, 1, 2, 3)], m["stains"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)]))
    # The one candle somebody still keeps lit.
    lx, ly, lz = at(0.05, edge - 0.05, 0.33)
    parts.append(lathe("neakta_lit_candle", coll, [(0.014, 0.0), (0.014, 0.07), (0.009, 0.075), (0.0, 0.075)], lx, ly, lz, m["wax_red"], segments=8))
    from khmer import flame as flame_card
    parts.append(flame_card("neakta_candle_flame", coll, lx, ly, lz + 0.08, 0.03, m["flame"]))
    empty("light_flame_shrine", coll, (lx, ly, lz + 0.11), radius=3.0, intensity=0.45)
    # Beside the platform, a sealed clay pot: its mouth bound in cloth and string,
    # black hair spilling out under the cloth, iron nails pushed into the clay.
    # Somebody has asked the spirit for something here. (Advisor review.)
    px, py, _ = at(1.35, 0.35)
    parts.append(lathe("neakta_pot", coll, [(0.0, 0.0), (0.1, 0.0), (0.16, 0.08), (0.17, 0.16), (0.12, 0.26), (0.09, 0.28),
                                           (0.1, 0.31), (0.0, 0.3)], px, py, 0.0, m["clay"], segments=14))
    parts.append(lathe("neakta_pot_cloth", coll, [(0.13, 0.22), (0.12, 0.29), (0.115, 0.32), (0.0, 0.335)], px, py, 0.0, m["rag"], segments=14))
    parts.append(tube("neakta_pot_string", coll, [(px + 0.11 * math.cos(t), py + 0.11 * math.sin(t), 0.275)
                                                  for t in (j * math.pi / 8 for j in range(17))], 0.006, m["rope"], sides=4))
    for j in range(16):
        a = rng.uniform(0, 2 * math.pi)
        r0 = (px + 0.115 * math.cos(a), py + 0.115 * math.sin(a), 0.25)
        parts.append(tube(f"neakta_pot_hair_{j}", coll, [r0, (r0[0] + 0.05 * math.cos(a), r0[1] + 0.05 * math.sin(a), 0.18),
                                                         (r0[0] + 0.07 * math.cos(a) + rng.normal(0, 0.02), r0[1] + 0.07 * math.sin(a), rng.uniform(0.02, 0.1))],
                          0.0025, m["soot"], sides=3))
    for j in range(5):
        a = rng.uniform(0, 2 * math.pi)
        z = rng.uniform(0.06, 0.18)
        o = (px + 0.165 * math.cos(a), py + 0.165 * math.sin(a), z)
        parts.append(pole(f"neakta_pot_nail_{j}", coll, o, (o[0] + 0.05 * math.cos(a), o[1] + 0.05 * math.sin(a), z + 0.01), 0.004, m["iron"], sides=4))
    shrine = join(parts, "neakta_shrine")
    collider("neakta_shrine", coll, x - 1.15, x + 1.15, y - 0.85, y + 0.85, 0, 0.35)
    empty("marker_neakta", coll, at(0.0, edge - 0.3, 0.5))
    empty("marker_flies", coll, at(0.7, edge + 0.1, 0.45))
    return shrine


# ------------------------------------------------------- village life


def lotus_pond(coll, m, x, y, rx, ry, rng):
    """A village pond (ត្រពាំង): dark water, lotus leaves and closed buds, reeds at the edge."""
    n = 24
    pts = [(x + math.cos(2 * math.pi * i / n) * rx * (0.85 + 0.2 * rng.random()), y + math.sin(2 * math.pi * i / n) * ry * (0.85 + 0.2 * rng.random()), -0.04)
           for i in range(n)]
    mesh_object("pond_water", coll, [(x, y, -0.04)] + pts, [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)], m["flood"])
    leaves = []
    for k in range(40):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 0.85
        lx, ly = x + math.cos(a) * rx * r, y + math.sin(a) * ry * r
        s = rng.uniform(0.25, 0.45)
        leaves.append(lathe(f"lotus_leaf_{k}", coll, [(0.0, 0.0), (s, 0.0), (s, 0.01), (0.0, 0.01)], lx, ly, -0.035, m["lotus_leaf"], segments=10))
    for k in range(9):
        a, r = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 0.7
        bx, by = x + math.cos(a) * rx * r, y + math.sin(a) * ry * r
        hgt = rng.uniform(0.3, 0.7)
        leaves.append(pole(f"lotus_stalk_{k}", coll, (bx, by, -0.04), (bx, by, hgt), 0.006, m["stem_green"], sides=4))
        leaves.append(lathe(f"lotus_bud_{k}", coll, [(0.0, 0.0), (0.03, 0.02), (0.035, 0.05), (0.018, 0.09), (0.0, 0.11)], bx, by, hgt, m["lotus"], segments=8))
    join(leaves, "lotus_pond_plants")
    collider("pond", coll, x - rx, x + rx, y - ry, y + ry, -1, 0.02)


def old_well(coll, m, x, y, rng, k=0, cover=False):
    """An old village well (អណ្តូង): a round shaft lined with brick, its rim worn and
    mossy, black water far down, a forked post frame over it with a pulley and a
    rope hanging into the dark. Nobody draws from it now: the bucket lies split
    beside it, a strip of cloth is tied to the post, and with `cover` a few planks
    lie half across the mouth."""
    parts = []
    r_in, r_out, rim = 0.55, 0.75, 0.72
    # The shaft wall above ground, with the inner face going down out of sight.
    parts.append(lathe(f"well_{k}_wall", coll, [(r_in, -0.02), (r_in, rim), (r_in + 0.03, rim + 0.04), (r_out - 0.03, rim + 0.04),
                                                (r_out, rim), (r_out + 0.04, 0.05), (r_out + 0.06, -0.02)], x, y, 0.0, m["brick"], segments=20))
    # Moss and mud on the lower courses, and broken bricks fallen at its foot.
    parts.append(lathe(f"well_{k}_moss", coll, [(r_out + 0.065, -0.01), (r_out + 0.05, 0.22), (r_out + 0.02, 0.3)], x, y, 0.0, m["stone_wet"], segments=20))
    for j in range(6):
        a = rng.uniform(0, 2 * math.pi)
        b = box(f"well_{k}_brick_{j}", coll, -0.11, 0.11, -0.05, 0.05, 0.0, 0.07, m["brick"], edge=0.01)
        b.location = (x + math.cos(a) * rng.uniform(0.95, 1.5), y + math.sin(a) * rng.uniform(0.95, 1.5), 0.0)
        b.rotation_euler = (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 3.1))
        parts.append(b)
    # The dark inside: what the eye takes for a deep shaft, and a glint of water.
    parts.append(lathe(f"well_{k}_dark", coll, [(0.0, 0.03), (r_in + 0.01, 0.03)], x, y, 0.0, m["void"], segments=20))
    # The frame: two forked posts and a cross pole, a wooden pulley, the rope.
    a = rng.uniform(0, math.pi)
    ca, sa = math.cos(a), math.sin(a)
    tops = []
    for side in (-1, 1):
        px, py = x + ca * (r_out + 0.15) * side, y + sa * (r_out + 0.15) * side
        parts.append(pole(f"well_{k}_post_{side}", coll, (px, py, -0.1), (px, py, 1.95), 0.06, m["post_rough"], sides=6))
        for fork in (-1, 1):
            parts.append(pole(f"well_{k}_fork_{side}_{fork}", coll, (px, py, 1.9),
                              (px + sa * 0.12 * fork, py - ca * 0.12 * fork, 2.12), 0.035, m["post_rough"], sides=5))
        tops.append((px, py, 2.02))
    parts.append(pole(f"well_{k}_beam", coll, tops[0], tops[1], 0.045, m["post_rough"], sides=6))
    parts.append(lathe(f"well_{k}_pulley", coll, [(0.0, -0.03), (0.12, -0.03), (0.1, 0.0), (0.12, 0.03), (0.0, 0.03)], 0, 0, 0, m["worn"], segments=12))
    parts[-1].location = (x, y, 2.02)
    parts[-1].rotation_euler = (math.pi / 2, 0.0, a + math.pi / 2)
    parts.append(tube(f"well_{k}_rope", coll, [(x + sa * 0.1, y - ca * 0.1, 2.0), (x + sa * 0.1 + rng.normal(0, 0.02), y - ca * 0.1, 1.0),
                                                (x + sa * 0.11, y - ca * 0.1, 0.05)], 0.012, m["rope"], sides=5))
    # The bucket, split, on its side by the wall; a coil of rotten rope.
    bx, by = x + 1.05, y - 0.35
    bucket = lathe(f"well_{k}_bucket", coll, [(0.0, 0.0), (0.13, 0.0), (0.16, 0.26), (0.15, 0.27), (0.12, 0.02)], 0, 0, 0, m["old_planks"], segments=10)
    bucket.location = (bx, by, 0.14)
    bucket.rotation_euler = (math.pi / 2 - 0.1, 0.0, rng.uniform(0, 6.2))
    parts.append(bucket)
    coil = [(bx - 0.4 + 0.18 * math.cos(t), by + 0.25 + 0.14 * math.sin(t), 0.02 + 0.004 * t) for t in (i * 0.35 for i in range(40))]
    parts.append(tube(f"well_{k}_coil", coll, coil, 0.012, m["rope"], sides=4))
    # A strip of red cloth tied to one post, faded and hanging limp.
    px, py = x - ca * (r_out + 0.15), y - sa * (r_out + 0.15)
    parts.append(tube(f"well_{k}_cloth", coll, [(px, py, 1.55), (px + 0.03, py, 1.2), (px + 0.05, py + 0.02, 0.85)], 0.035,
                      m["cloth_red"], sides=3, radius_end=0.02))
    if cover:
        for j in range(3):
            plank = box(f"well_{k}_plank_{j}", coll, -0.9, 0.9, -0.1, 0.1, 0.0, 0.035, m["old_planks"], edge=0.005)
            plank.location = (x + 0.25 * (j - 1) + 0.3, y + 0.3 * (j - 1), rim + 0.04 + 0.035 * (j % 2))
            plank.rotation_euler = (0.0, 0.05 * (j - 1), a + 0.4 + 0.15 * j)
            parts.append(plank)
    collider(f"well_{k}", coll, x - r_out - 0.2, x + r_out + 0.2, y - r_out - 0.2, y + r_out + 0.2, 0.0, 1.0, surface="stone")
    return parts


def rag_tree(coll, m, x, y, k, rng):
    """A dead tree people have tied things to: strips of red and white cloth and old
    rags hanging limp from its limbs, small woven offering baskets gone black, a
    knotted cord round the trunk. Nobody living ties anything here any more."""
    tree = dead_tree(coll, m, x, y, rng.uniform(7, 10), 500 + k, rng)
    parts = []
    for j in range(int(rng.integers(7, 12))):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.6, 2.4)
        top = (x + math.cos(a) * r, y + math.sin(a) * r, rng.uniform(2.6, 5.5))
        drop = rng.uniform(0.6, 1.6)
        mat = m[("cloth_red", "cotton_dirty", "rag", "rag")[j % 4]]
        parts.append(tube(f"ragtree_{k}_strip_{j}", coll, [top, (top[0] + rng.normal(0, 0.05), top[1] + rng.normal(0, 0.05), top[2] - drop * 0.5),
                                                           (top[0] + rng.normal(0, 0.08), top[1] + rng.normal(0, 0.08), top[2] - drop)],
                          rng.uniform(0.025, 0.05), mat, sides=3, radius_end=0.015))
    for j in range(3):
        a = rng.uniform(0, 2 * math.pi)
        hook = (x + math.cos(a) * 1.2, y + math.sin(a) * 1.2, rng.uniform(2.8, 4.0))
        parts.append(tube(f"ragtree_{k}_cord_{j}", coll, [hook, (hook[0], hook[1], hook[2] - 0.5)], 0.006, m["rope"], sides=3))
        basket = lathe(f"ragtree_{k}_basket_{j}", coll, [(0.0, 0.0), (0.09, 0.02), (0.13, 0.12), (0.12, 0.16)], hook[0], hook[1], hook[2] - 0.66,
                       m["bamboo_wall_2s"], segments=10)
        parts.append(basket)
    ring = [(x + 0.32 * math.cos(t), y + 0.32 * math.sin(t), 1.3 + 0.03 * math.sin(3 * t)) for t in (j * math.pi / 8 for j in range(17))]
    parts.append(tube(f"ragtree_{k}_band", coll, ring, 0.02, m["rope"], sides=4))
    return join([tree] + parts, f"ragtree_{k}")


def ritual_traces(coll, m, x, y, rng):
    """What Sok left under the house the night he tried to undo the debt: a circle of
    ash with four stakes and a cord round them, scraps of burnt yantra cloth, candle
    stubs burnt to the floor, a cracked bowl, and a page of his notes, half burnt.
    (Advisor review: a counter-ritual of our own invention, kept vague.)"""
    parts = []
    r = 0.75
    # A low ridge of ash, thickest where it was poured round, standing off the earth floor.
    parts.append(lathe("sok_ritual_ash", coll, [(r - 0.16, 0.012), (r - 0.06, 0.03), (r, 0.035), (r + 0.06, 0.028), (r + 0.16, 0.012)],
                       x, y, 0.0, m["ash"], segments=28))
    parts.append(lathe("sok_ritual_ash_floor", coll, [(0.0, 0.014), (r - 0.15, 0.014)], x, y, 0.0, m["soot"], segments=28))
    stakes = []
    for j in range(4):
        a = j * math.pi / 2 + math.pi / 4
        sx, sy = x + math.cos(a) * (r + 0.2), y + math.sin(a) * (r + 0.2)
        parts.append(pole(f"sok_ritual_stake_{j}", coll, (sx, sy, -0.05), (sx, sy, 0.38 + rng.uniform(-0.04, 0.04)), 0.018, m["post_rough"], sides=5))
        stakes.append((sx, sy, 0.3))
    for j in range(4):
        a, b = stakes[j], stakes[(j + 1) % 4]
        parts.append(tube(f"sok_ritual_cord_{j}", coll, sag(a, b, 0.06, n=6), 0.004, m["soot"], sides=3))
    for j in range(7):
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0.1, r)
        b = box(f"sok_ritual_yantra_{j}", coll, -0.07, 0.07, -0.05, 0.05, 0.0, 0.003, m["yantra" if j % 3 else "soot"])
        b.location = (x + math.cos(a) * d, y + math.sin(a) * d, 0.018)
        b.rotation_euler = (0.0, 0.0, rng.uniform(0, 3.1))
        parts.append(b)
    for j in range(5):
        a = j * 2 * math.pi / 5
        cx, cy = x + math.cos(a) * (r - 0.05), y + math.sin(a) * (r - 0.05)
        parts.append(lathe(f"sok_ritual_candle_{j}", coll, [(0.0, 0.0), (0.05, 0.0), (0.045, 0.006), (0.012, 0.02), (0.0, 0.025)], cx, cy, 0.0,
                           m["wax_dirty"], segments=8))
    bowl = lathe("sok_ritual_bowl", coll, [(0.0, 0.0), (0.06, 0.0), (0.09, 0.05), (0.08, 0.055), (0.0, 0.01)], 0, 0, 0, m["glaze"], segments=12)
    bowl.location = (x + 0.15, y - 0.1, 0.03)
    bowl.rotation_euler = (0.9, 0.2, 0.4)
    parts.append(bowl)
    join(parts, "sok_ritual")
    # His notes: one page, its corner burnt off, face up by the circle.
    page = mesh_object("sok_notes", coll, [(x + r + 0.3, y - 0.2, 0.02), (x + r + 0.51, y - 0.2, 0.02),
                                           (x + r + 0.51, y + 0.1, 0.02), (x + r + 0.3, y + 0.1, 0.02)],
                       [(0, 1, 2, 3)], m["sok_notes"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    pivot(page, x + r + 0.405, y - 0.05, 0.02).rotation_euler.z = 0.3
    return page

