"""Hand-scale props for the stilt house interior that the player inspects closely:
the kitchen hearth and Sok's palm-leaf manuscripts (sleuk rith).

Shared by ep1_area_village.py (full build) and rebuild-interior-props.py (focused
update of the shipped village), so both produce the same objects. `m` is the
village material set; new surfaces are named M_house_detail_* so the focused
merge (update-house-details-glb.mjs) accepts them.

Looks follow the Art Bible (sections 1 and 6: worn, used for decades, no flat
colour on what the lamp shows up close). The hearth is the common Khmer kitchen
fire of the period: a timber box packed with earth so the fire cannot reach the
floorboards, three hearth stones holding the pot, and wood fed in from the side.
"""

import math

import bpy
import numpy as np

from kit import box, library_material, plain, tube, world_uvs

rng = np.random.default_rng(1932)


def detail(name, factory):
    """A detail material, reused if this file already has it (focused rebuilds)."""
    return bpy.data.materials.get(name) or factory(name)


def rock(name, coll, x, y, z, size, mat, squash=0.85, seed=0, height=None):
    """An irregular stone resting with its base at z: a jittered icosphere, made
    exactly `height` tall when given."""
    r = np.random.default_rng(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    for v in obj.data.vertices:
        v.co *= r.uniform(0.82, 1.12)
    sx, sy, sz = size
    obj.scale = (sx, sy, sz * squash)
    bpy.context.view_layer.update()
    if height:
        zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
        obj.scale.z *= height / (max(zs) - min(zs))
        bpy.context.view_layer.update()
    lowest = min((obj.matrix_world @ v.co).z for v in obj.data.vertices)
    obj.location = (x, y, z - lowest)
    obj.rotation_euler = (0, 0, r.uniform(0, math.tau))
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.materials.append(mat)
    world_uvs(obj)
    return obj


def kitchen_hearth(coll, m, x0, x1, y0, y1, floor, pot_seat, pot_at):
    """The hearth box against the kitchen's west wall: three stones centred under
    the pot at `pot_at` (x, y), their tops at `pot_seat`, where its base rests."""
    earth = detail("M_house_detail_hearth_earth", lambda n: library_material("red_dirt_mud_01", n, tint=(0.55, 0.45, 0.38)))
    char = detail("M_house_detail_char", lambda n: plain(n, (0.025, 0.02, 0.018), rough=0.95))
    bark = detail("M_house_detail_firewood", lambda n: library_material("bark_brown_02", n, tint=(0.7, 0.6, 0.5)))
    scorched = detail("M_house_detail_scorched_stone", lambda n: plain(n, (0.075, 0.068, 0.06), rough=0.92))
    ash = detail("M_house_detail_ash", lambda n: plain(n, (0.16, 0.15, 0.14), rough=1.0))
    rim = floor + 0.42
    t = 0.045  # plank thickness
    # The box: four planks, their top edges scorched where the fire licks over them.
    for name, (a0, a1, b0, b1) in {
        "w": (x0, x0 + t, y0, y1), "e": (x1 - t, x1, y0, y1),
        "s": (x0 + t, x1 - t, y0, y0 + t), "n": (x0 + t, x1 - t, y1 - t, y1),
    }.items():
        box(f"kitchen_hearth_plank_{name}", coll, a0, a1, b0, b1, floor, rim, m["worn"], edge=0.006)
        box(f"kitchen_hearth_scorch_{name}", coll, a0 - 0.001, a1 + 0.001, b0 - 0.001, b1 + 0.001, rim - 0.035, rim + 0.001, char)
    # Packed earth to just under the rim, a bed of ash where the fire sits.
    box("kitchen_hearth_earth", coll, x0 + t, x1 - t, y0 + t, y1 - t, floor + 0.05, rim - 0.02, earth)
    cx, cy = pot_at
    # Ash drifts in soft overlapping heaps, not a slab.
    for k in range(5):
        a, d = k * 1.3, 0.05 + 0.04 * (k % 2)
        rock(f"kitchen_hearth_ash_{k}", coll, cx + d * math.cos(a), cy + d * math.sin(a), rim - 0.022,
             (rng.uniform(0.12, 0.17), rng.uniform(0.1, 0.14), 0.01), ash, seed=20 + k, height=0.016)
    # Three hearth stones in a triangle under the pot, blackened by years of fire.
    top = pot_seat
    for k, ang in enumerate((math.pi / 2, math.pi / 2 + 2.1, math.pi / 2 - 2.1)):
        sx, sy = cx + 0.13 * math.cos(ang), cy + 0.13 * math.sin(ang)
        # A common height, so the pot sits level on all three.
        rock(f"hearth_stone_{k}", coll, sx, sy, rim - 0.008, (0.075, 0.065, 0.16), scorched, seed=31 + k, height=top - (rim - 0.008))
    # Banked charcoal between the stones, two embers still faintly alive.
    for k in range(9):
        a, d = rng.uniform(0, math.tau), rng.uniform(0, 0.09)
        rock(f"hearth_charcoal_{k}", coll, cx + d * math.cos(a), cy + d * math.sin(a), rim - 0.008,
             (0.02, 0.016, 0.014), m["embers"] if k < 2 else char, seed=60 + k)
    # Firewood pushed in from the open south side, ends burnt to charcoal.
    for k, (dx, ang, length) in enumerate(((-0.08, 1.75, 0.55), (0.03, 1.55, 0.6), (0.12, 1.38, 0.5))):
        ex, ey = cx + dx * 0.4, cy - 0.04
        sx, sy = ex + length * math.cos(ang + math.pi), ey + length * math.sin(ang + math.pi)
        z0, z1 = rim + 0.02, rim + 0.035
        r = 0.022 + 0.004 * k
        tube(f"hearth_firewood_{k}", coll, [(sx, sy, z0 + 0.06), (ex, ey, z1)], r, bark, sides=7)
        tube(f"hearth_firewood_end_{k}", coll, [(ex - 0.02 * math.cos(ang), ey - 0.02 * math.sin(ang), z1), (ex, ey, z1)],
             r * 1.05, char, sides=7)


def palm_leaf_manuscripts(coll, m, x, y, z):
    """Sok's sleuk rith on his desk: two bound bundles between wooden covers, tied
    with cord through their holes, one more wrapped in cloth, and three loose
    leaves he was reading. Leaves are long and narrow, edges lacquered red."""
    leaf = detail("M_house_detail_palm_leaf", lambda n: plain(n, (0.5, 0.39, 0.22), rough=0.75))
    cloth = detail("M_house_detail_manuscript_cloth", lambda n: plain(n, (0.42, 0.2, 0.08), rough=0.9))
    cover = detail("M_house_detail_manuscript_cover", lambda n: plain(n, (0.09, 0.045, 0.025), rough=0.45))
    L, W = 0.5, 0.052  # leaf length (along x) and width
    for k, (dy, h, turn) in enumerate(((0.0, 0.032, 0.03), (0.085, 0.024, -0.05))):
        cy = y + dy
        covers = 0.007
        box(f"manuscript_cover_lower_{k}", coll, x - L / 2 - 0.01, x + L / 2 + 0.01, cy - W / 2 - 0.004, cy + W / 2 + 0.004,
            z, z + covers, cover, tilt=(0, 0, turn), edge=0.002)
        box(f"manuscript_leaves_{k}", coll, x - L / 2, x + L / 2, cy - W / 2, cy + W / 2, z + covers, z + covers + h, leaf,
            tilt=(0, 0, turn))
        # Red lacquer on the long edges of the stacked leaves.
        for s in (-1, 1):
            box(f"manuscript_edge_{k}_{s}", coll, x - L / 2, x + L / 2, cy + s * W / 2 - 0.0008, cy + s * W / 2 + 0.0008,
                z + covers, z + covers + h, m["lacquer"], tilt=(0, 0, turn))
        top = z + covers + h
        box(f"manuscript_cover_upper_{k}", coll, x - L / 2 - 0.01, x + L / 2 + 0.01, cy - W / 2 - 0.004, cy + W / 2 + 0.004,
            top, top + covers, cover, tilt=(0, 0, turn), edge=0.002)
        # Cord wound round the bundle a third of the way along, its tail trailing.
        for j, fx in enumerate((-L / 6, L / 6)):
            px = x + fx * math.cos(turn)
            py = cy + fx * math.sin(turn)
            ring = [(px - 0.003, py - W / 2 - 0.006, z + 0.002), (px - 0.003, py - W / 2 - 0.006, top + covers + 0.002),
                    (px + 0.003, py + W / 2 + 0.006, top + covers + 0.002), (px + 0.003, py + W / 2 + 0.006, z + 0.002)]
            tube(f"manuscript_cord_{k}_{j}", coll, ring, 0.0018, m["rope"], sides=4)
        tail = [(x - L / 6, cy + W / 2 + 0.006, z + 0.003), (x - L / 6 + 0.03, cy + W / 2 + 0.05, z + 0.002),
                (x - L / 6 + 0.09, cy + W / 2 + 0.06, z + 0.002)]
        tube(f"manuscript_cord_tail_{k}", coll, tail, 0.0016, m["rope"], sides=4)
    # A third bundle wrapped in faded cloth at the back of the desk.
    box("manuscript_wrapped", coll, x - 0.27, x + 0.27, y + 0.18, y + 0.25, z, z + 0.05, cloth, tilt=(0, 0, 0.04), edge=0.012)
    # Three loose leaves fanned out from their left ends, where he left off reading.
    px, py = x - L / 2 + 0.02, y - 0.1
    for k in range(3):
        ang = -0.05 - k * 0.11
        lx, ly = px + (L / 2) * math.cos(ang), py + (L / 2) * math.sin(ang)
        box(f"manuscript_loose_leaf_{k}", coll, lx - L / 2, lx + L / 2, ly - W / 2, ly + W / 2, z + 0.0006 * k, z + 0.0006 * k + 0.0008,
            leaf, tilt=(0, 0, ang))
