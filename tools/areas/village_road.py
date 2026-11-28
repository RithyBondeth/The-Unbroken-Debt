"""Episode 1's village road outside the farm's south gate (the user, Nov 25, 2026: standing
where the taxi leaves Sora and looking back south into the fog, "implement road along with
the shop and shop's poster for each shop just like driving scene").

The laterite road the taxi came by runs east-west 9 m south of the gate, raised on its bank
above two drainage ditches; the cart track crosses the north ditch on an earth causeway over
a concrete culvert. Along it stand eight roadside shops built by the driving scene's own
builder (tools/travel/taxi_roadside_details.py), each with its real 1990s Khmer shop signs
and posters from the same atlas (T_taxi_khmer_posters_BC), gooseneck-lit poster boards
between them, wooden power poles with drop wires to every shop and a bulb at the junction,
storm litter, verge grass and bananas, and a fallen tree across each end where Sora's walk
stops.

Blender space (x east, y north), metres. `build()` runs last in rebuild-farmstead.py, or
alone on the built village file (tools/areas/build-village-road.py); it first deletes what
an earlier run made, so it can run again. `roof_rects()` and the layout constants are plain
maths for export-farm-layout.py (the rain's shelter under the shops' roofs).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for _p in (HERE, os.path.join(ROOT, "tools", "travel")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ------------------------------------------------------------------ the plan

ROAD_Y0 = -51.8          # the centre line at x 0, straight out from the gate (farmstead.TRACK)
REACH = 66.0             # drawn to the terrain's edge each way (data/forestBorder TERRAIN)
WALK_X = 30.5            # walls across the road; a fallen tree lies just beyond each
HALF = 2.7               # the laterite carriageway's half width
SHOULDER = 3.15          # where the grass shoulder breaks down to the ditch
DITCH = (3.75, 4.35)     # each ditch's flat muddy bottom, from the centre line
WALL_L = 4.6             # the line along each ditch's far side Sora can't cross
SHOP_L = 7.12            # a shop's front wall from the centre line: its footbridge spans the ditch
FILL = 0.33              # the fill the shops stand on, above the road's base (level with the shoulder)
CAUSEWAY = (0.0, 1.7, 2.5)   # the track's crossing: x, flat half width, blend out by
SEED = 2511

# Height above the road's base by distance from the centre line: the crown, the shoulder, the
# ditch, its spoil bank, back down to the forest floor (tucked just under it at the edge).
PROFILE = [(0.0, 0.40), (0.9, 0.398), (1.8, 0.388), (2.45, 0.375), (2.7, 0.365), (2.95, 0.352),
           (3.15, 0.34), (3.3, 0.30), (3.45, 0.22), (3.6, 0.12), (3.75, 0.045), (3.9, 0.02),
           (4.05, 0.012), (4.2, 0.02), (4.35, 0.045), (4.5, 0.11), (4.65, 0.165), (4.85, 0.19),
           (5.2, 0.18), (5.6, 0.12), (6.1, 0.05), (6.6, 0.0), (7.3, -0.03), (9.0, -0.03), (11.5, -0.03)]
_PL = np.array([p[0] for p in PROFILE])
_PZ = np.array([p[1] for p in PROFILE])

# The shops, by the trades the driving scene's builder knows: side -1 south of the road (its
# front facing north, to the gate), +1 north (flanking the track's mouth). Posters are slots
# in the atlas (taxi_roadside_details.py lists them): hero = the fascia sign, front = beside
# the door, side = the side wall, hang = the bracket sign over the road.
SHOPS = [
    dict(trade="noodle", side=-1, x=0.0, eyaw=0.04, hw=2.75, open_front=True, parapet=False, tarp=True,
         fluoro=False, dim=False, posters={"hero": 2, "front": (1, 13), "side": (0, 2), "hang": (1, 2)}),
    dict(trade="tv_coffee", side=-1, x=12.6, eyaw=-0.07, hw=2.6, open_front=False, parapet=False, tarp=True,
         fluoro=False, dim=False, posters={"hero": 9, "front": (2, 1), "side": (9, 13), "hang": (9, 1)}),
    dict(trade="moto", side=-1, x=-12.8, eyaw=0.09, hw=2.85, open_front=True, parapet=False, tarp=False,
         fluoro=True, dim=False, posters={"hero": 12, "front": (13, 15), "side": (12, 14), "hang": (12, 14)}),
    dict(trade="grocery", side=-1, x=25.2, eyaw=0.06, hw=2.95, open_front=True, parapet=False, tarp=False,
         fluoro=False, dim=False, posters={"hero": 13, "front": (1, 2), "side": (7, 3), "hang": (13, 1)}),
    dict(trade="outpost", side=-1, x=-25.4, eyaw=-0.05, hw=2.6, open_front=False, parapet=False, tarp=False,
         fluoro=False, dim=True, posters={"hero": 5, "front": (10, 14), "side": (6, 8), "hang": (5, 8)}),
    dict(trade="barber", side=1, x=-11.6, eyaw=-0.06, hw=2.75, open_front=True, parapet=False, tarp=True,
         fluoro=True, dim=False, posters={"hero": 8, "front": (0, 5), "side": (10, 14), "hang": (0, 15)}),
    dict(trade="dentist_salon", side=1, x=11.8, eyaw=0.05, hw=3.15, open_front=True, parapet=True, tarp=False,
         fluoro=True, dim=False, posters={"hero": 6, "front": (4, 3), "side": (7, 11), "hang": (6, 4)}),
    dict(trade="salon", side=1, x=-24.8, eyaw=0.08, hw=2.65, open_front=True, parapet=False, tarp=True,
         fluoro=False, dim=False, posters={"hero": 7, "front": (15, 3), "side": (4, 11), "hang": (7, 3)}),
]
# Gooseneck-lit poster boards on the banks between the shops: side, x, the two posters.
BOARDS = [(1, 5.4, 3, 11), (-1, -6.3, 4, 6), (-1, 6.4, 0, 8), (-1, -19.0, 12, 13), (-1, 18.9, 1, 7),
          (1, 18.2, 15, 14), (1, -18.0, 10, 2)]
# Power poles along the north bank, and the one with the junction's bulb.
POLES = [-31.5, -17.8, -4.2, 4.0, 17.6, 31.2]
JUNCTION_POLE = -4.2


def road_y(x):
    """The centre line's y at x: a slow drift, never ruled straight."""
    return ROAD_Y0 + 0.55 * math.sin(0.052 * x + 0.9) + 0.30 * math.sin(0.13 * x - 0.4) - _K


_K = 0.55 * math.sin(0.9) + 0.30 * math.sin(-0.4)


def road_slope(x):
    return 0.55 * 0.052 * math.cos(0.052 * x + 0.9) + 0.30 * 0.13 * math.cos(0.13 * x - 0.4)


def frame(x):
    """The centre point at x, the way along (east) and the side (north), as 2D tuples."""
    s = road_slope(x)
    k = 1.0 / math.hypot(1.0, s)
    return (x, road_y(x)), (k, s * k), (-s * k, k)


def at(x, lateral):
    """The point `lateral` m north (negative: south) of the centre line at x."""
    (px, py), _t, (nx, ny) = frame(x)
    return px + nx * lateral, py + ny * lateral


def lateral_of(wx, wy):
    """Metres north of the centre line (negative: south) of a world point."""
    return (wy - road_y(wx)) / math.hypot(1.0, road_slope(wx))


def profile(lateral):
    return float(np.interp(abs(lateral), _PL, _PZ))


def smoothstep(a, b, v):
    t = min(1.0, max(0.0, (v - a) / (b - a)))
    return t * t * (3 - 2 * t)


def shop_frame(spec):
    """A shop's origin (x, y), its turn (local +x toward the road) and its half width."""
    side = spec["side"]
    ox, oy = at(spec["x"], side * SHOP_L)
    _c, _t, (nx, ny) = frame(spec["x"])
    yaw = math.atan2(-side * ny, -side * nx) + spec["eyaw"]
    return ox, oy, yaw


def shop_world(spec, lx, ly):
    ox, oy, yaw = shop_frame(spec)
    c, s = math.cos(yaw), math.sin(yaw)
    return ox + c * lx - s * ly, oy + s * lx + c * ly


def roof_rects():
    """Each shop's roof (eaves included) as an axis-aligned rect, with its top: the rain's
    shelter (export-farm-layout.py ROOFS)."""
    out = []
    for sp in SHOPS:
        hw = sp["hw"]
        pts = [shop_world(sp, lx, ly) for lx in (-3.6, 2.25) for ly in (-hw * 1.12, hw * 1.12)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append(((min(xs), max(xs), min(ys), max(ys)), 4.4))
    return out


def pad_weight(px, py, side):
    """1 on the earth pad a shop stands on (its rooms, veranda and steps, a little round),
    falling to 0 within 0.35 m of the pad's edge: a raised platform with a short steep
    side, not a long shallow ramp lying nearly level with the forest floor (where the two
    surfaces crossed, the game drew the bank as dark blots in the grass)."""
    w = 0.0
    for sp in SHOPS:
        if sp["side"] != side:
            continue
        ox, oy, yaw = shop_frame(sp)
        c, s_ = math.cos(-yaw), math.sin(-yaw)
        dx, dy = px - ox, py - oy
        lx, ly = c * dx - s_ * dy, s_ * dx + c * dy
        if lx < -4.2 or lx > 3.2 or abs(ly) > sp["hw"] + 0.9:
            continue
        across = 1.0 - smoothstep(sp["hw"] + 0.25, sp["hw"] + 0.6, abs(ly))
        back = 1.0 - smoothstep(-3.55, -3.9, lx) if lx < -3.55 else 1.0
        w = max(w, across * back)
    return w


def causeway_weight(x):
    cx, flat, out = CAUSEWAY
    return 1.0 - smoothstep(flat, out, abs(x - cx))


# ------------------------------------------------------------------ building (Blender)

def build(coll, ground):
    """Everything above into `coll`; `ground(x, y)` gives the terrain's height."""
    import bpy  # noqa: F401  (Blender only)

    rng = np.random.default_rng(SEED)
    clear_old()
    base = Base(ground)
    cleared = clear_ground(ground)
    m = materials()
    road(coll, ground, base, m)
    gravel(coll, ground, base, m, np.random.default_rng(SEED + 3))
    culvert(coll, ground, base, m, rng)
    insulators, gaps = shops(coll, ground, base, m)
    boards(coll, ground, base, m)
    poles(coll, ground, base, m, insulators, rng)
    fallen_trees(coll, ground, base, rng)
    verge(coll, ground, base, m, rng)
    backdrop(coll, ground, np.random.default_rng(SEED + 1))
    intruders = clear_intruders(base)
    no_shrub_02()
    colliders(coll, ground, base, gaps)
    print(f"[village_road] cleared {cleared} (+{intruders} leaning into shops), objects {len(coll.objects)}", flush=True)


PREFIXES = ("vroad_", "col_vroad_", "light_flame_vroad_", "taxi_road_anchor_", "tpl_ph_", "taxi_road_", "tpl_vgoods_")


def clear_old():
    """What an earlier run made (objects, and their meshes and materials when orphaned)."""
    import bpy

    gone = [o for o in bpy.data.objects if o.name.startswith(PREFIXES)]
    for o in gone:
        bpy.data.objects.remove(o, do_unlink=True)
    for me in [me for me in bpy.data.meshes if me.users == 0 and me.name.startswith(("vroad_", "col_vroad_", "taxi_road_", "tpl_ph_", "tpl_vgoods_"))]:
        bpy.data.meshes.remove(me)
    for mt in [mt for mt in bpy.data.materials if mt.users == 0 and mt.name.startswith(("M_vroad_", "M_taxi_"))]:
        bpy.data.materials.remove(mt)


class Base:
    """The road's level along its length: the ground across its width, averaged and eased
    over 8 m so the bank runs level, as a built road does."""

    def __init__(self, ground):
        self.xs = np.arange(-REACH - 8.0, REACH + 8.01, 0.5)
        raw = np.array([np.mean([ground(*at(x, lt)) for lt in (-3.0, -1.5, 0.0, 1.5, 3.0)]) for x in self.xs])
        k = 17
        self.h = np.convolve(np.pad(raw, k // 2, mode="edge"), np.ones(k) / k, mode="valid")

    def __call__(self, x):
        return float(np.interp(x, self.xs, self.h))


def _potholes():
    """Dry holes worn in the carriageway, in and beside the wheel tracks, often in twos and
    threes (no water stands in them: the user wants rain, not water)."""
    rng = np.random.default_rng(SEED + 7)
    out = []
    x = -REACH + 2.0
    while x < REACH - 2.0:
        x += float(rng.uniform(2.2, 6.5)) if abs(x) < WALK_X + 4 else float(rng.uniform(5.0, 11.0))
        side = 1.0 if rng.random() < 0.5 else -1.0
        r = float(rng.uniform(0.3, 0.62))
        lt = side * float(rng.uniform(0.35, min(1.15, HALF - 0.25 - r)))
        out.append((x, lt, r, float(rng.uniform(0.035, 0.075)) * (0.6 + 0.4 * r / 0.45), float(rng.uniform(0, 6.283))))
        for _k in range(int(rng.choice([0, 0, 1, 2]))):
            r2 = r * float(rng.uniform(0.55, 0.85))
            lt2 = float(np.clip(lt + rng.uniform(-0.45, 0.45), -(HALF - 0.25 - r2), HALF - 0.25 - r2))
            out.append((x + float(rng.uniform(0.55, 1.3)), lt2, r2, out[-1][3] * float(rng.uniform(0.6, 0.9)),
                        float(rng.uniform(0, 6.283))))
    out.sort()
    return out


POTHOLES = _potholes()
_PH_X = [p[0] for p in POTHOLES]


def pothole(x, lt):
    """How deep the holes are at (x, lateral) (m, positive down; a slight lip round each), how
    far inside the nearest one the point is (0 at its edge, 1 at its middle), and how near
    the broken crust just outside one (1 on it)."""
    import bisect

    depth, inside, rim = 0.0, 0.0, 0.0
    i = bisect.bisect_left(_PH_X, x - 0.9)
    while i < len(POTHOLES) and POTHOLES[i][0] < x + 0.9:
        px, pl, r, d, ph = POTHOLES[i]
        i += 1
        dx, dl = x - px, lt - pl
        rr = math.hypot(dx, dl)
        if rr > r * 1.5:
            continue
        th = math.atan2(dl, dx)
        re = r * (1.0 + 0.16 * math.sin(3 * th + ph) + 0.09 * math.sin(5 * th - 2 * ph))
        t = rr / re
        if t < 1.0:
            # A flat-bottomed bowl, steep at the edge where the crust has broken away.
            depth += d * (1.0 - smoothstep(0.55, 1.0, t)) * (0.85 + 0.15 * math.cos(t * 3.0))
            inside = max(inside, 1.0 - t)
        depth -= 0.007 * math.exp(-(((t - 1.08) / 0.13) ** 2))
        rim = max(rim, math.exp(-(((t - 1.2) / 0.22) ** 2)))
    return depth, inside, rim


PLANTS = ("treewall_", "prop_", "fs_", "grass_", "weed_", "fern", "shrub", "bark_debris", "dry_branches", "pachira",
          "banana", "palm", "moss", "stump", "root_", "anthurium", "calathea", "forest_tree", "dead_", "nettle",
          "periwinkle", "island_tree", "single_root", "sugar")


def _foot(o):
    from mathutils import Vector

    if o.type == "MESH" and o.data and len(o.data.vertices):
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        # Trees and plants stand at their origin; litter is judged by its middle.
        if o.name.startswith(("treewall_", "fs_", "forest_tree")):
            return o.matrix_world.translation.x, o.matrix_world.translation.y
        return sum(p.x for p in bb) / 8, sum(p.y for p in bb) / 8
    return o.matrix_world.translation.x, o.matrix_world.translation.y


def _in_shop(spec, x, y, pad):
    ox, oy, yaw = shop_frame(spec)
    c, s = math.cos(-yaw), math.sin(-yaw)
    dx, dy = x - ox, y - oy
    lx, ly = c * dx - s * dy, s * dx + c * dy
    return -4.4 - pad < lx < 4.4 + pad and abs(ly) < spec["hw"] + 1.3 + pad


def clear_ground(ground):
    """The farm's tree wall, the old village's plants and litter where the road, its banks,
    the shops and the boards now stand (big trees by their trunk, so crowns still lean over)."""
    import bpy

    spots = [at(x, s * 5.3) for s, x, *_ in BOARDS] + [at(x, 5.6) for x in POLES]
    gone = 0
    for o in list(bpy.data.objects):
        if o.parent is not None or not o.name.startswith(PLANTS) or o.type not in ("MESH", "EMPTY"):
            continue
        if any(c.name.startswith("_") for c in o.users_collection):
            continue
        x, y = _foot(o)
        if not -REACH - 2 < x < REACH + 2:
            continue
        lt = lateral_of(x, y)
        big = o.name.startswith(("treewall_forest_tree", "treewall_dead", "fs_banyan", "fs_big_tree"))
        hit = abs(lt) < (7.6 if big else 7.0)
        hit = hit or any(_in_shop(sp, x, y, 1.2 if big else 0.4) for sp in SHOPS)
        hit = hit or any(math.hypot(x - sx, y - sy) < (2.2 if big else 1.2) for sx, sy in spots)
        if hit:
            for c in [o] + list(o.children_recursive):
                bpy.data.objects.remove(c, do_unlink=True)
            gone += 1
    return gone


def no_shrub_02():
    """Every shrub_02 in the village goes (the user, Nov 26, 2026: "Remove all of this kind
    of grasses"): the leggy, sparse-leaved stalks read as toys. The game's forest border
    no longer clones it either (ForestBorder.ts)."""
    import bpy

    gone = [o for o in bpy.data.objects if "shrub_02" in o.name]
    for o in gone:
        for c in [o] + list(o.children_recursive):
            if c.name in bpy.data.objects:
                bpy.data.objects.remove(c, do_unlink=True)
    print(f"[village_road] shrub_02 removed: {len(gone)}", flush=True)


def clear_intruders(base):
    """Plants whose leaves reach into a shop: a banana or a tree standing clear of the shop by
    its trunk can still push fronds through its walls or under its veranda roof (a leaf showed
    inside the noodle shop and the dentist's). Any plant with a vertex inside a shop's rooms or
    roofed veranda goes. Returns how many."""
    import bpy
    from mathutils import Vector

    boxes = []
    for sp in SHOPS:
        Minv = shop_matrix(sp, base).inverted()
        hw = sp["hw"]
        boxes.append((Minv, hw))
    gone = 0
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o.parent is not None or not len(o.data.vertices):
            continue
        name = o.name[6:] if o.name.startswith("vroad_") else o.name
        if not name.startswith(PLANTS + ("jungle_", "banana_", "sugar_palm_", "grove_", "fern", "shrub", "grass")):
            continue
        if o.name.startswith("vroad_fallen_tree"):
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        cx, cy = sum(p.x for p in bb) / 8, sum(p.y for p in bb) / 8
        r = max((p - Vector((cx, cy, p.z))).length for p in bb)
        near = [(Minv, hw) for (Minv, hw), sp in zip(boxes, SHOPS)
                if math.hypot(cx - shop_frame(sp)[0], cy - shop_frame(sp)[1]) < r + hw + 4.5]
        if not near:
            continue
        co = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        mw = np.array(o.matrix_world)
        w = co @ mw[:3, :3].T + mw[:3, 3]
        hit = False
        for Minv, hw in near:
            mi = np.array(Minv)
            q = w @ mi[:3, :3].T + mi[:3, 3]
            rooms = (q[:, 0] > -3.32) & (q[:, 0] < 0.06) & (np.abs(q[:, 1]) < hw + 0.06) & (q[:, 2] > 0.1) & (q[:, 2] < 3.6)
            veranda = (q[:, 0] >= 0.06) & (q[:, 0] < 2.2) & (np.abs(q[:, 1]) < hw + 0.08) & (q[:, 2] > 0.15) & (q[:, 2] < 2.6)
            if rooms.any() or veranda.any():
                hit = True
                break
        if hit:
            for c in [o] + list(o.children_recursive):
                bpy.data.objects.remove(c, do_unlink=True)
            gone += 1
    print(f"[village_road] plants reaching into shops removed: {gone}", flush=True)
    return gone


def _vertex_colour_multiply(mat):
    """Multiply the colour map by the mesh's "Col" vertex colours (wet ruts, mossy shoulders)."""
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bc_in = bsdf.inputs["Base Color"]
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    if bc_in.links:
        src = bc_in.links[0].from_socket
        nt.links.remove(bc_in.links[0])
        nt.links.new(src, mix.inputs[6])
    else:
        mix.inputs[6].default_value = tuple(bc_in.default_value)
    nt.links.new(vc.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bc_in)


def _emission(mat, strength):
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Emission Strength"].default_value = strength


def materials():
    from kit import library_material, plain, world_uvs

    import taxi_roadside_details as TRD

    shop, posters = TRD.shop_materials(library_material, plain, world_uvs)
    m = dict(shop)
    m["posters"] = posters
    # The split-bamboo walls (salon, outpost) at half the driving scene's tile: seen up close
    # at 1.8 m a tile, their node rows read as stacked sacks rather than canes.
    m["bamboo_wall"]["tile"] = 0.9
    m["laterite"] = library_material("red_laterite_soil_stones", "M_vroad_laterite", tint=(0.5, 0.39, 0.31), tile=1.8)
    m["bank"] = library_material("brown_mud_leaves_01", "M_vroad_bank", tint=(0.62, 0.56, 0.5), tile=2.0)
    m["gravel"] = library_material("red_laterite_soil_stones", "M_vroad_gravel", tint=(0.66, 0.5, 0.4), tile=0.45)
    for k in ("laterite", "bank", "gravel"):
        _vertex_colour_multiply(m[k])
    # The driving scene's glows are set for headlights and a moving car; on a dark road
    # Sora stands still on, they glare: windows, the noodle cart's case, the tubes and the
    # TV dimmed to a lamp's warmth (the bulbs themselves keep most of theirs).
    for k, strength in (("win_glow", 0.3), ("noodle_glow", 0.55), ("fluoro", 2.2), ("crt", 1.5), ("bulb", 4.0),
                        ("shrine_glow", 3.0)):
        _emission(m[k], strength)
    m["pole"] = library_material("bark_brown_02", "M_vroad_pole", tint=(0.42, 0.36, 0.3), tile=1.2)
    m["porcelain"] = plain("M_vroad_porcelain", (0.62, 0.6, 0.55), 0.22)
    m["transformer"] = library_material("rusty_metal", "M_vroad_transformer", tint=(0.22, 0.25, 0.22), tile=0.8)
    m["bark"] = library_material("bark_brown_02", "M_vroad_bark", tint=(0.5, 0.44, 0.38), tile=1.6)
    m["world_uvs"] = world_uvs
    return m


def _road_height(x, lt, ground, base):
    """The road's surface height at (x, lateral): crown, ruts and grain, ditches, banks, the
    fill before the shops and the causeway where the track comes in."""
    a = abs(lt)
    side = 1 if lt >= 0 else -1
    b = base(x)
    z = b + profile(lt)
    if a < 2.62:
        meander = 0.10 * math.sin(x * 0.14) + 0.05 * math.cos(x * 0.31)
        ls = abs(lt - meander * math.exp(-((lt / 2.3) ** 2)))
        taper = min(1.0, (2.62 - a) / 0.35)
        # Two wheel tracks of the ox carts and the odd truck, deeper where the wet seasons
        # have churned them, wandering a little; a fainter third where wheels ran wide.
        track = 0.74 + 0.05 * math.sin(x * 0.27 + side) + 0.03 * math.sin(x * 0.83 - side)
        churn = 0.5 + 0.5 * math.sin(x * 0.11 + 0.8 * side) * math.sin(x * 0.047 + 1.3)
        rut = (0.032 + 0.05 * churn) * math.exp(-(((ls - track) / (0.17 + 0.05 * churn)) ** 2))
        rut += 0.016 * math.exp(-(((ls - 1.32) / 0.13) ** 2)) * (0.5 + 0.5 * math.sin(x * 0.21 - side))
        berm = 0.02 * math.exp(-(((ls - track - 0.29) / 0.12) ** 2)) + 0.013 * math.exp(-(((ls - track + 0.3) / 0.1) ** 2))
        grain = 0.007 * math.sin(x * 1.8 + lt * 3) + 0.004 * math.sin(x * 4.3 - lt * 7.1) + 0.0025 * math.sin(x * 11.7 + lt * 5.3)
        # In the ruts the mud was trodden by the oxen and dried in clods.
        clods = 0.008 * churn * math.exp(-(((ls - track) / 0.2) ** 2)) * math.sin(x * 9.1 + lt * 13.0) * math.sin(x * 6.3 - lt * 4.0)
        z += (berm - rut + grain + clods) * taper - pothole(x, lt)[0]
    local = ground(*at(x, lt))
    if a >= 3.45:
        # The terrain round the vertex as well as under it: between the road's vertices (0.9 m
        # apart past the walls) a bump of the terrain can rise through the bank's faces.
        h = 0.45 if abs(x) > 34.0 else 0.11
        near = [local] + [ground(*at(x + dx, lt + dl)) for dx, dl in ((h, 0.0), (-h, 0.0), (0.0, 0.09), (0.0, -0.09))]
        hi, lo = max(near), min(near)
    else:
        hi = lo = local
    f = 0.0
    if a > 3.75:
        # Past the ditch's bottom the bank follows the forest floor, not the road's level;
        # beyond the spoil bank its toe runs down into the forest floor, so the terrain takes
        # over along one ragged line. The shops stand on earth pads with short steep sides.
        w = smoothstep(3.75, 4.6, a)
        z = (1 - w) * z + w * (local + profile(lt))
        wob = 0.18 * math.sin(x * 0.9 + side) + 0.1 * math.sin(x * 2.3 - 1.0)
        z -= 0.32 * smoothstep(5.45 + wob, 6.2 + wob, a)
        if a > 4.4:
            f = pad_weight(*at(x, lt), side)
            if f > 0:
                fill = b + FILL - 0.015 * (a - 4.6)
                z = (1 - f) * z + f * max(fill, local + 0.03)
    c = causeway_weight(x) if side > 0 and a > SHOULDER else 0.0
    if c > 0:
        tz = local + 0.03
        cw = b + profile(SHOULDER) + (tz - b - profile(SHOULDER)) * smoothstep(SHOULDER, 5.8, a)
        if a > 5.8:
            cw = local + 0.03 - 0.33 * smoothstep(5.8, 6.4, a)
        z = (1 - c) * z + c * cw
    # Never lying level with the forest floor, where the game can't tell which is in front:
    # on top of it by a clear margin wherever the bank shows, or well under it (`ground` is
    # the terrain as drawn, its triangles: laid 1 cm over a bilinear reading, the bank sank
    # under it in patches the game showed as dark blots; the user, Nov 26, 2026: "Fix these
    # kind of road").
    if a < 3.45:
        z = max(z, local + 0.04)
    elif a < 5.3 or f >= 0.5 or (c >= 0.5 and a < 5.8):
        z = max(z, hi + 0.025)
    elif z < hi + 0.04:
        z = min(z, lo - 0.1)
    return z


def surface_z(x, lt, ground, base):
    """The ground a thing set down at (x, lateral) stands on: the road's bank, or the
    forest floor where the bank has gone under it."""
    return max(_road_height(x, lt, ground, base), ground(*at(x, lt)))


def _road_colour(x, lt, rng_noise):
    """Wet ruts darker, the hump between them greener, the shoulders mossy, the ditch black-wet."""
    a = abs(lt)
    r, g, b = 1.0, 0.97, 0.93
    meander = 0.10 * math.sin(x * 0.14) + 0.05 * math.cos(x * 0.31)
    ls = abs(lt - meander * math.exp(-((lt / 2.3) ** 2)))

    def mix(c, w):
        nonlocal r, g, b
        r, g, b = r * (1 - w) + c[0] * w, g * (1 - w) + c[1] * w, b * (1 - w) + c[2] * w

    if a < 2.7:
        track = 0.74 + 0.05 * math.sin(x * 0.27 + (1 if lt >= 0 else -1)) + 0.03 * math.sin(x * 0.83 - (1 if lt >= 0 else -1))
        mix((0.55, 0.52, 0.5), 0.85 * math.exp(-(((ls - track) / 0.24) ** 2)))
        mix((0.74, 0.8, 0.62), 0.35 * math.exp(-((lt / 0.32) ** 2)) * (0.5 + 0.5 * math.sin(x * 0.37)))
        # Dark wet patches where the rain lies on the crown a while (no standing water).
        mix((0.6, 0.57, 0.54), 0.55 * smoothstep(0.62, 0.85, rng_noise))
        # The holes: damp silt washed into them, darker toward the middle, a paler dry lip.
        _d, inside, _rim = pothole(x, lt)
        if inside > 0:
            mix((0.42, 0.39, 0.37), min(1.0, 0.45 + inside))
        # Dust and fine gravel on the crown and the berms, paler where the wheels don't run.
        mix((1.0, 0.98, 0.95), 0.6 * smoothstep(0.55, 0.8, _noise2(x * 2.3, lt * 3.1)) * (1 - math.exp(-(((ls - track) / 0.3) ** 2))))
    mix((0.66, 0.72, 0.56), 0.8 * smoothstep(2.35, 3.0, a) * (1 - smoothstep(3.6, 3.9, a)))
    mix((0.36, 0.35, 0.33), 0.9 * math.exp(-(((a - 4.05) / 0.33) ** 2)))
    mix((0.7, 0.74, 0.6), 0.5 * smoothstep(4.5, 5.2, a) * (1 - smoothstep(5.0, 5.6, a)))
    # Toward its toe the bank darkens to the forest floor's wet mud, so where the terrain
    # takes over there is no pale edge.
    mix((0.46, 0.43, 0.4), 0.85 * smoothstep(5.0, 5.9, a))
    if lt > SHOULDER:
        mix((0.62, 0.56, 0.5), 0.6 * causeway_weight(x))
    return r, g, b


def _noise2(x, y):
    return 0.5 + 0.25 * math.sin(x * 0.61 + 1.3 * math.sin(y * 0.9)) * math.cos(y * 0.83 - 0.4 * x) + \
        0.25 * math.sin(x * 1.37 - y * 1.11 + 2.0)


def road(coll, ground, base, m):
    """The road as one mesh: laterite over the crown and shoulders, the banks and ditches in
    mud, out to the forest floor (and up to the shops' fill), vertex-coloured, with UVs in
    metres at each material's tile."""
    import bpy

    carriage = [round(v, 3) for v in np.arange(-HALF, HALF + 0.001, 0.15)]
    outer = [p for p, _z in PROFILE if p > HALF]
    lats = sorted(set([-p for p in outer] + carriage + outer))
    xs = list(np.arange(-REACH, -34.0, 0.9)) + list(np.arange(-34.0, 34.0, 0.2)) + list(np.arange(34.0, REACH + 0.01, 0.9))
    verts, cols, uvs_v = [], [], []
    for x in xs:
        for lt in lats:
            px, py = at(x, lt)
            verts.append((px, py, _road_height(x, lt, ground, base)))
            cols.append(_road_colour(x, lt, _noise2(x, lt)))
            uvs_v.append((lt + 0.35 * math.sin(x * 0.07), x))
    n = len(lats)
    faces, slots = [], []
    for j in range(len(xs) - 1):
        for i in range(n - 1):
            a = j * n + i
            faces.append((a, a + n, a + n + 1, a + 1))
            mid = abs(lats[i] + lats[i + 1]) / 2
            slots.append(0 if mid < SHOULDER + 0.12 else 1)
    # Faces lying wholly under the forest floor are left out: nothing would see them.
    hidden = [verts[i][2] < ground(verts[i][0], verts[i][1]) - 0.04 for i in range(len(verts))]
    keep = [k for k, f in enumerate(faces) if not all(hidden[i] for i in f)]
    faces = [faces[k] for k in keep]
    slots = [slots[k] for k in keep]
    me = bpy.data.meshes.new("vroad_road")
    me.from_pydata(verts, [], faces)
    me.materials.append(m["laterite"])
    me.materials.append(m["bank"])
    me.polygons.foreach_set("material_index", slots)
    tiles = (m["laterite"].get("tile", 1.8), m["bank"].get("tile", 2.0))
    uv = me.uv_layers.new(name="UVMap")
    col = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
    for poly in me.polygons:
        t = tiles[poly.material_index]
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv.data[li].uv = (uvs_v[vi][0] / t, uvs_v[vi][1] / t)
            col.data[li].color = (*cols[vi], 1.0)
    me.color_attributes.active_color = col
    me.color_attributes.render_color_index = list(me.color_attributes).index(col)
    for poly in me.polygons:
        poly.use_smooth = True
    me.update()
    obj = bpy.data.objects.new("vroad_road", me)
    coll.objects.link(obj)
    print(f"[village_road] road {len(verts)} verts, {len(faces)} quads", flush=True)
    return obj


def gravel(coll, ground, base, m, rng):
    """Laterite gravel the wheels have worked out of the road: pebbles over the crown and the
    berms, thrown to the shoulders' edge and heaped round the holes' broken crust, few in the
    ruts and the holes; fist-sized lumps along the carriageway's edges. Each sits 40% of its
    height into the road, under the lowest point beneath it, so none rests on top like a toy
    (the user, Nov 26, 2026: "more realistic, detailed, and feel like natural")."""
    import bmesh
    import bpy
    from mathutils import Matrix, Vector

    def proto(sub):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        vs = [tuple(v.co) for v in bm.verts]
        fs = [tuple(v.index for v in f.verts) for f in bm.faces]
        bm.free()
        return vs, fs

    small, big = proto(1), proto(2)
    palette = [(0.95, 0.74, 0.6), (0.82, 0.6, 0.48), (0.66, 0.5, 0.42), (1.0, 0.86, 0.72), (0.56, 0.44, 0.38),
               (0.88, 0.86, 0.82)]
    weights = np.array([0.26, 0.24, 0.18, 0.12, 0.14, 0.06])
    verts, faces, fcols = [], [], []

    def stone(x, lt, size, shape):
        pv, pf = shape
        sx, sy = size * float(rng.uniform(0.8, 1.3)), size * float(rng.uniform(0.65, 1.05))
        sz = size * float(rng.uniform(0.42, 0.72))
        rot = Matrix.Rotation(float(rng.uniform(0, 6.283)), 3, "Z") @ Matrix.Rotation(float(rng.normal(0, 0.22)), 3, "X")
        reach = 0.5 * max(sx, sy)
        lowest = min(surface_z(x + dx, lt + dl, ground, base)
                     for dx, dl in ((0, 0), (reach, 0), (-reach, 0), (0, reach), (0, -reach)))
        px, py = at(x, lt)
        centre = Vector((px, py, lowest - 0.4 * sz + 0.5 * sz))
        o = len(verts)
        bumps = rng.normal(0, 0.11, len(pv))
        for (vx, vy, vz), k in zip(pv, bumps):
            verts.append(tuple(centre + rot @ (Vector((vx * sx / 2, vy * sy / 2, vz * sz / 2)) * (1.0 + float(k)))))
        c = palette[int(rng.choice(len(palette), p=weights / weights.sum()))]
        shade = float(rng.uniform(0.85, 1.08))
        for f in pf:
            faces.append(tuple(o + i for i in f))
            fcols.append((min(1.0, c[0] * shade), min(1.0, c[1] * shade), min(1.0, c[2] * shade)))

    n = 0
    for _ in range(7000):
        x = float(rng.uniform(-WALK_X - 3.0, WALK_X + 3.0))
        lt = float(rng.uniform(-3.3, 3.3))
        a = abs(lt)
        side = 1 if lt >= 0 else -1
        meander = 0.10 * math.sin(x * 0.14) + 0.05 * math.cos(x * 0.31)
        ls = abs(lt - meander * math.exp(-((lt / 2.3) ** 2)))
        track = 0.74 + 0.05 * math.sin(x * 0.27 + side) + 0.03 * math.sin(x * 0.83 - side)
        _d, inside, rim = pothole(x, lt)
        dens = 0.42 * (1.0 - 0.8 * math.exp(-(((ls - track) / 0.2) ** 2)))
        if a > 2.3:
            dens = 0.6 if a < 3.15 else 0.22
        dens = max(dens, 0.9 * rim * (1.0 - inside))
        if inside > 0.1:
            dens = 0.08
        if rng.random() > dens:
            continue
        size = float(np.clip(rng.lognormal(math.log(0.028), 0.38), 0.013, 0.07))
        stone(x, lt, size, small)
        n += 1
    lumps = 0
    for _ in range(420):
        x = float(rng.uniform(-WALK_X - 3.0, WALK_X + 3.0))
        side = 1 if rng.random() < 0.5 else -1
        edge = rng.random() < 0.8
        lt = side * float(rng.uniform(2.35, 3.25) if edge else rng.uniform(0.0, 2.2))
        if pothole(x, lt)[1] > 0 or (side > 0 and lt > SHOULDER - 0.2 and causeway_weight(x) > 0.02):
            continue
        if rng.random() > (0.45 if edge else 0.18):
            continue
        stone(x, lt, float(rng.uniform(0.07, 0.17) if edge else rng.uniform(0.05, 0.1)), big)
        lumps += 1
    me = bpy.data.meshes.new("vroad_gravel")
    me.from_pydata(verts, [], faces)
    me.materials.append(m["gravel"])
    col = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
    for poly, c in zip(me.polygons, fcols):
        for li in poly.loop_indices:
            col.data[li].color = (*c, 1.0)
    me.color_attributes.active_color = col
    me.color_attributes.render_color_index = list(me.color_attributes).index(col)
    for poly in me.polygons:
        poly.use_smooth = True
    me.update()
    obj = bpy.data.objects.new("vroad_gravel", me)
    coll.objects.link(obj)
    m["world_uvs"](obj)
    print(f"[village_road] gravel {n} pebbles, {lumps} lumps, {len(faces)} tris", flush=True)
    return obj


def _box(bm, centre, size, rot=None, bevel=0.0):
    import taxi_roadside_details as TRD

    TRD._box_bm(bm, centre, size, rot=rot, bevel=bevel, segs=1)


def _obj(name, bm, mat, coll, uv=True, smooth=False, m=None):
    import taxi_roadside_details as TRD

    return TRD._bm_obj(name, bm, mat, coll, world_uvs_fn=(m["world_uvs"] if (uv and m) else None), smooth=smooth)


def culvert(coll, ground, base, m, rng):
    """Where the track crosses the north ditch: a concrete pipe through an earth causeway, its
    two headwalls, the pipe's mouths, white-and-red marker posts at the road's edge."""
    import bmesh
    from mathutils import Euler, Vector

    import taxi_roadside_details as TRD

    cx = CAUSEWAY[0]
    _c, (tx, ty), (nx, ny) = frame(cx)
    yaw = math.atan2(ty, tx)
    b = base(cx)
    conc, pipe, post_w, post_r = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    mid = (DITCH[0] + DITCH[1]) / 2
    for s in (-1, 1):
        hx = cx + s * 2.05
        p = at(hx, mid + 0.05)
        top = b + profile(SHOULDER) + 0.05
        bot = b - 0.25
        # The headwall, its face toward the ditch, a little out of square, its top chipped.
        _box(conc, (p[0], p[1], (top + bot) / 2), (0.24, 1.55, top - bot), rot=Euler((0.0, 0.0, yaw + s * 0.03)), bevel=0.02)
        _box(conc, (p[0] + s * 0.02, p[1], top + 0.03), (0.3, 1.62, 0.07), rot=Euler((0.0, 0.0, yaw)), bevel=0.012)
        # The pipe's mouth: a concrete ring standing proud of the headwall, its bore black.
        mouth = at(hx + s * 0.13, mid)
        centre = Vector((mouth[0], mouth[1], b + 0.24))
        TRD._torus_bm(pipe, centre, Vector((tx, ty, 0.0)), 0.25, 0.05, n_maj=20, n_min=8)
        TRD._cyl_bm(pipe, centre - Vector((tx, ty, 0.0)) * 0.06, centre + Vector((tx, ty, 0.0)) * (0.06 + s * 0.0), 0.255, 0.255, segs=18, cap=False)
        # Marker posts at the shoulder's edge, either side of the crossing.
        mp = at(cx + s * 2.2, SHOULDER - 0.08)
        tilt = Euler((float(rng.uniform(-0.05, 0.05)), float(rng.uniform(-0.05, 0.05)), yaw))
        zp = ground(*mp)
        zp = max(zp, b + profile(SHOULDER - 0.08))
        _box(post_w, (mp[0], mp[1], zp + 0.26), (0.11, 0.11, 0.72), rot=tilt, bevel=0.01)
        _box(post_r, (mp[0], mp[1], zp + 0.5), (0.116, 0.116, 0.12), rot=tilt)
    # The pipe's bore, dark, so the mouth reads as a hole.
    dark = bmesh.new()
    for s in (-1, 1):
        mouth = at(cx + s * 2.05, mid)
        _box(dark, (mouth[0], mouth[1], b + 0.24), (0.02, 0.44, 0.44), rot=Euler((0.0, 0.0, yaw)))
    # Headwalls whitewashed, as the public works paint them, so a driver sees the culvert at night.
    _obj("vroad_culvert", conc, m["white_enamel"], coll, m=m)
    _obj("vroad_culvert_pipe", pipe, m["concrete"], coll, smooth=True, m=m)
    _obj("vroad_culvert_bore", dark, m["rubber"], coll, uv=False, m=m)
    _obj("vroad_marker_posts", post_w, m["white_enamel"], coll, m=m)
    _obj("vroad_marker_posts_red", post_r, m["red_plastic"], coll, m=m)


def _rename_since(before, prefix_from, prefix_to):
    import bpy

    for o in bpy.data.objects:
        if o not in before and o.name.startswith(prefix_from):
            o.name = prefix_to + o.name[len(prefix_from):]


def light_marker(coll, name, at_pt, watts, colour):
    """A light_flame_ marker as rebuild-farmstead.light_marker makes: VillageLights lights it."""
    import bpy

    old = bpy.data.objects.get(f"light_flame_{name}")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    e = bpy.data.objects.new(f"light_flame_{name}", None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.05
    e.location = tuple(at_pt)
    coll.objects.link(e)
    e["watts"] = float(watts)
    e["color"] = [round(float(c), 3) for c in colour]
    e["radius"] = round(max(1.8, min(12.0, 3.2 * math.sqrt(watts))), 2)
    return e


def shop_matrix(spec, base):
    from mathutils import Matrix

    ox, oy, yaw = shop_frame(spec)
    oz = base(spec["x"]) + profile(SHOULDER) + 0.249
    return Matrix.Translation((ox, oy, oz)) @ Matrix.Rotation(yaw, 4, "Z")


def shops(coll, ground, base, m):
    """The eight shops, each from the driving scene's builder with its own posters; their
    lamps become village lights. Returns the roof insulators (for the drop wires) and each
    shop's footbridge across the ditch (a gap in the ditch's wall)."""
    import bpy

    import taxi_roadside_details as TRD

    props, ph_props = TRD.shop_props(TRD.full_gltf_group, TRD.import_glb)
    p_verts, p_faces, p_uvs = [], [], []
    insulators, gaps = [], []
    for idx, sp in enumerate(SHOPS):
        before = set(bpy.data.objects)
        M = shop_matrix(sp, base)

        def ground_z(lx, ly, sp=sp, M=M):
            # The bank's height under a point of the shop's frame, in that frame.
            wx, wy = shop_world(sp, lx, ly)
            return _road_height(wx, lateral_of(wx, wy), ground, base) - M.translation.z

        spec = dict(sp, village=True, ground_z=ground_z)
        ins = TRD._build_detailed_shop(coll, M, m, props, ph_props, p_verts, p_faces, p_uvs, spec, idx)
        insulators.append((sp, ins))
        new = [o for o in bpy.data.objects if o not in before]
        # Its lamps: the veranda's pendant, the light inside (a cool tube or a warm bulb).
        for o in new:
            if o.name.startswith("taxi_road_anchor_shop_lamp_"):
                watts = 2.0 if sp["dim"] else 9.0
                light_marker(coll, f"vroad_shop_{idx}", o.location.copy(), watts, (1.0, 0.66, 0.34))
            elif o.name.startswith("taxi_road_anchor_shop_int_lamp_"):
                cool = sp["fluoro"]
                watts = 1.5 if sp["dim"] else (6.5 if cool else 6.0)
                light_marker(coll, f"vroad_shop_in_{idx}", o.location.copy(), watts,
                             (0.8, 0.9, 1.0) if cool else (1.0, 0.62, 0.3))
        for o in new:
            if o.name.startswith("taxi_road_anchor_"):
                bpy.data.objects.remove(o, do_unlink=True)
        _rename_since(before, "taxi_road_", "vroad_")
        # The footbridge (or the moto shop's concrete apron) crossing the ditch.
        half = 1.48 if sp["trade"] == "moto" else 0.78
        step_y = 0.0 if sp["trade"] == "moto" else -0.35
        a = shop_world(sp, 2.52, step_y - half)
        c = shop_world(sp, 2.52, step_y + half)
        gaps.append((sp["side"], min(a[0], c[0]), max(a[0], c[0])))
    if p_verts:
        TRD._mesh_uv("vroad_khmer_posters", p_verts, p_faces, p_uvs, m["posters"], coll, smooth=True)
    # Every shop furnished again in detail, the builder's crude goods taken out (shop_interiors.py).
    import shop_interiors as SI

    SI.dress(coll, [(idx, sp, shop_matrix(sp, base)) for idx, sp in enumerate(SHOPS)], m,
             lambda name, p, w, c: light_marker(coll, name, p, w, c))
    for grp in [*props.values(), *ph_props.values()]:
        for o in grp:
            bpy.data.objects.remove(o, do_unlink=True)
    # Material names follow the village (M_vroad_*), so the game can dress them (VillageRoad.ts).
    for mt in bpy.data.materials:
        if mt.name.startswith("M_taxi_") and mt.users:
            mt.name = "M_vroad_" + mt.name[len("M_taxi_"):]
    return insulators, gaps


def boards(coll, ground, base, m):
    """The gooseneck-lit poster boards on the banks, each turned a little toward the gate."""
    import bpy
    from mathutils import Matrix

    import taxi_roadside_details as TRD

    p_verts, p_faces, p_uvs = [], [], []
    for k, (side, x, pa, pb) in enumerate(BOARDS):
        before = set(bpy.data.objects)
        px, py = at(x, side * 5.3)
        _c, _t, (nx, ny) = frame(x)
        # The posters (local +y) face across the road.
        face = math.atan2(-side * ny, -side * nx)
        yaw = face - math.pi / 2 + (0.2 if x < 0 else -0.2) * side
        z = min(ground(px, py), base(x) + profile(5.3)) - 0.06
        lean = math.radians(1.4 if k % 2 == 0 else -1.2)
        M = Matrix.Translation((px, py, z)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(lean, 4, "Y")
        TRD.build_poster_board(coll, m, M, k, pa, pb, p_verts, p_faces, p_uvs, m["world_uvs"])
        for o in bpy.data.objects:
            if o not in before and o.name.startswith("taxi_road_anchor_poster_lamp_"):
                light_marker(coll, f"vroad_board_{k}", o.location.copy(), 4.0, (1.0, 0.7, 0.4))
                bpy.data.objects.remove(o, do_unlink=True)
                break
        _rename_since(before, "taxi_road_", "vroad_")
    if p_verts:
        TRD._mesh_uv("vroad_board_posters", p_verts, p_faces, p_uvs, bpy.data.materials.get("M_vroad_khmer_posters") or m["posters"], coll, smooth=True)


def poles(coll, ground, base, m, insulators, rng):
    """Wooden power poles along the north bank: crossarms, porcelain insulators, three sagging
    lines from pole to pole, a drop wire to each shop's roof, a pole transformer, and a bare bulb
    under a tin shade over the junction."""
    import bmesh
    from mathutils import Euler, Vector

    import taxi_roadside_details as TRD

    wood, iron, porc, tin, bulb, wires, tank = (bmesh.new() for _ in range(7))
    tops = []
    for k, x in enumerate(POLES):
        px, py = at(x, 5.6)
        z0 = ground(px, py) - 0.6
        h = 7.6 + float(rng.uniform(-0.25, 0.25))
        lean = Vector((float(rng.uniform(-0.04, 0.04)), float(rng.uniform(-0.02, 0.05)), 1.0)).normalized()
        foot = Vector((px, py, z0))
        top = foot + lean * h
        TRD._cyl_bm(wood, foot, top, 0.15, 0.11, segs=10)
        _c, (tx, ty), _n = frame(x)
        arm_z = top.z - 0.45
        arm_c = Vector((top.x, top.y, arm_z))
        yaw = math.atan2(ty, tx) + math.pi / 2       # the crossarm across the line
        _box(wood, arm_c, (0.1, 1.9, 0.11), rot=Euler((0.0, 0.0, yaw - math.pi / 2)))
        across = Vector((-ty, tx, 0.0))
        for s in (-1, 1):                              # braces under the arm
            TRD._cyl_bm(iron, arm_c + across * (s * 0.62) + Vector((0, 0, -0.04)), Vector((top.x, top.y, arm_z - 0.6)), 0.016, 0.016, segs=5)
        pins = []
        for s in (-0.8, 0.0, 0.8):
            p = arm_c + across * s + Vector((0, 0, 0.06))
            TRD._cyl_bm(porc, p, p + Vector((0, 0, 0.13)), 0.045, 0.03, segs=10)
            TRD._torus_bm(porc, p + Vector((0, 0, 0.05)), Vector((0, 0, 1)), 0.05, 0.012, n_maj=12, n_min=5)
            pins.append(p + Vector((0, 0, 0.12)))
        tops.append(pins)
        # Climbing spikes (steps) up the pole, and an old tin number plate.
        for j in range(9):
            sz = 2.2 + j * 0.48
            q = foot + lean * sz
            d = Vector((math.cos(j * 2.4), math.sin(j * 2.4), 0.0))
            TRD._cyl_bm(iron, q, q + d * 0.2, 0.011, 0.011, segs=5)
        if x == POLES[2]:
            # The transformer: a drum on a platform, its bushings and fuse cut-outs.
            pc = foot + lean * 5.2 + Vector((-ty, tx, 0)) * -0.35
            _box(wood, pc + Vector((0, 0, -0.42)), (0.9, 0.7, 0.08))
            TRD._cyl_bm(tank, pc + Vector((0, 0, -0.38)), pc + Vector((0, 0, 0.42)), 0.28, 0.28, segs=18)
            for f in range(6):
                fz = -0.3 + f * 0.13
                TRD._torus_bm(tank, pc + Vector((0, 0, fz)), Vector((0, 0, 1)), 0.285, 0.012, n_maj=18, n_min=4)
            for s in (-0.12, 0.0, 0.12):
                b0 = pc + Vector((-ty, tx, 0)) * s + Vector((0, 0, 0.42))
                TRD._cyl_bm(porc, b0, b0 + Vector((0, 0, 0.16)), 0.028, 0.02, segs=8)
        if x == JUNCTION_POLE:
            # The junction's lamp: a bracket out over the road, a tin cone, a bare bulb.
            _c, _t, (nx, ny) = frame(x)
            out = Vector((-nx, -ny, 0.0))
            b0 = foot + lean * 5.0
            b1 = b0 + out * 1.35 + Vector((0, 0, 0.35))
            TRD._cyl_bm(iron, b0, b1, 0.022, 0.022, segs=6)
            TRD._cyl_bm(iron, b0 + Vector((0, 0, -0.5)), b0 + out * 0.8 + Vector((0, 0, 0.18)), 0.014, 0.014, segs=5)
            shade_top = b1 + Vector((0, 0, -0.05))
            TRD._cyl_bm(tin, shade_top, shade_top + Vector((0, 0, -0.2)), 0.04, 0.24, segs=16, cap=False)
            TRD._cyl_bm(iron, b1, b1 + Vector((0, 0, -0.12)), 0.018, 0.018, segs=6)
            bz = b1 + Vector((0, 0, -0.2))
            TRD._cyl_bm(iron, b1 + Vector((0, 0, -0.1)), bz + Vector((0, 0, 0.005)), 0.016, 0.016, segs=8)
            TRD._cyl_bm(bulb, bz, bz + Vector((0, 0, -0.08)), 0.03, 0.026, segs=10)
            light_marker(coll, "vroad_junction", bz + Vector((0, 0, -0.08)), 10.0, (1.0, 0.7, 0.38))
    # The lines, pole to pole, sagging.
    for a, c in zip(tops, tops[1:]):
        for pa, pc in zip(a, c):
            span = (pc - pa).length
            sag = 0.012 * span + 0.25
            pts = [pa.lerp(pc, f / 10) - Vector((0, 0, sag * math.sin(math.pi * f / 10))) for f in range(11)]
            TRD._tube_bm(wires, pts, 0.008, segs=4)
    # A drop wire from the nearest pole's middle pin to each shop's roof insulator.
    pole_pins = [(x, pins[1]) for x, pins in zip(POLES, tops)]
    for sp, ins in insulators:
        if sp["dim"]:
            continue
        x, pin = min(pole_pins, key=lambda xp: abs(xp[0] - sp["x"]))
        ins = Vector(ins)
        pts = [pin.lerp(ins, f / 10) - Vector((0, 0, 0.55 * math.sin(math.pi * f / 10))) for f in range(11)]
        TRD._tube_bm(wires, pts, 0.009, segs=4)
    _obj("vroad_poles", wood, m["pole"], coll, m=m)
    _obj("vroad_pole_iron", iron, m["iron"], coll, smooth=True, m=m)
    _obj("vroad_pole_insulators", porc, m["porcelain"], coll, uv=False, smooth=True, m=m)
    _obj("vroad_pole_lamp_shade", tin, m["enamel_green"], coll, smooth=True, m=m)
    _obj("vroad_pole_lamp_bulb", bulb, m["bulb"], coll, uv=False, smooth=True, m=m)
    _obj("vroad_transformer", tank, m["transformer"], coll, smooth=True, m=m)
    _obj("vroad_power_lines", wires, m["wire"], coll, uv=False, smooth=True, m=m)


def fallen_trees(coll, ground, base, rng):
    """A tree down across each end of the walkable stretch, as the storm leaves them: roots
    torn up on the north bank, the trunk over the road, its crown in the south ditch."""
    import village_nature as VN

    fl = VN.flora()
    dead = fl["forest_tree_gn"][1]
    for k, (x, yaw_off) in enumerate(((-WALK_X - 1.4, 0.16), (WALK_X + 1.3, -0.12))):
        px, py = at(x, 6.2)
        _c, (tx, ty), _n = frame(x)
        yaw = math.atan2(ty, tx) + yaw_off
        z = ground(px, py) + 0.35
        obj = VN.place(coll, dead, f"vroad_fallen_tree_{k}", px, py, z, yaw, 0.46, tilt=(1.5, 0.0))
        obj["flora"] = "vroad_fallen"     # not a forest template (ForestBorder picks those by flora)


def verge(coll, ground, base, m, rng):
    """Verge grass along the shoulders and banks, ferns and shrubs between the shops, bananas
    and a sugar palm behind them, a little fallen wood on the outer banks (the road clean)."""
    import village_nature as VN

    grass = VN.poly_haven("grass_medium_01") + VN.poly_haven("grass_medium_02")
    ferns = VN.poly_haven("fern_02")
    shrubs = VN.poly_haven("shrub_03") + VN.poly_haven("shrub_04")
    litter = VN.poly_haven("dry_branches_medium_01") + VN.poly_haven("bark_debris_01")
    spots = [(at(x, s * 5.3), 1.1) for s, x, *_ in BOARDS] + [(at(x, 5.6), 0.7) for x in POLES]

    def free(x, lt):
        px, py = at(x, lt)
        if any(_in_shop(sp, px, py, 0.6) for sp in SHOPS):
            return False
        if lt > SHOULDER and causeway_weight(x) > 0.02:
            return False
        if abs(x) > WALK_X + 0.5 and abs(x) < WALK_X + 4.5:
            return False
        return all(math.hypot(px - sx, py - sy) > r for (sx, sy), r in spots)

    def put(src, x, lt, s, yaw=None, sink=0.02):
        # Named vroad_*: the game's snapToGround (groundSnap.GROUNDED) would otherwise lower
        # verge grass and litter from the raised bank to the forest floor under it.
        px, py = at(x, lt)
        # On the lowest of the bank under the tuft (its base is flat, the bank slopes under
        # it), a little in (VN.put sinks 2 cm more): set 9 cm into the bank's middle, most
        # tufts were buried to their tips.
        r = 0.12 * s
        z = min(surface_z(x + dx, lt + dl, ground, base) for dx, dl in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r))) - sink
        o = VN.put(coll, src, px, py, lambda *_: z, float(rng.uniform(0, 6.283)) if yaw is None else yaw, s)
        o.name = "vroad_" + o.name

    n = 0
    x = -REACH + 2
    while x < REACH - 2:
        for side in (-1, 1):
            # Tufts at the shoulder's break and down the ditch's sides.
            lt = side * float(rng.uniform(3.0, 3.5))
            if free(x, lt) and rng.random() < 0.8:
                put(grass[int(rng.integers(len(grass)))], x, lt, float(rng.uniform(0.85, 1.45)))
                n += 1
            lt = side * float(rng.uniform(4.55, 6.6))
            if free(x, lt):
                r = rng.random()
                if r < 0.55:
                    put(grass[int(rng.integers(len(grass)))], x, lt, float(rng.uniform(0.9, 1.7)))
                elif r < 0.75:
                    put(ferns[int(rng.integers(len(ferns)))], x, lt, float(rng.uniform(0.7, 1.15)))
                elif r < 0.88:
                    put(shrubs[int(rng.integers(len(shrubs)))], x, lt, float(rng.uniform(0.55, 0.95)))
                n += 1
        x += float(rng.uniform(0.55, 1.1)) if abs(x) < 36 else float(rng.uniform(1.4, 2.6))
    # Grass on the crown between the wheel tracks and along the carriageway's edges, where
    # neither wheels nor feet run: low, in clumps, with bare stretches between.
    crown = 0
    x = -WALK_X - 2.0
    while x < WALK_X + 2.0:
        x += float(rng.uniform(0.8, 3.2))
        meander = 0.10 * math.sin(x * 0.14) + 0.05 * math.cos(x * 0.31)
        if rng.random() < 0.6:
            lt = meander + float(rng.normal(0, 0.1))
            if pothole(x, lt)[1] == 0 and free(x, lt):
                put(grass[int(rng.integers(len(grass)))], x, lt, float(rng.uniform(0.65, 1.05)))
                crown += 1
        if rng.random() < 0.55:
            lt = (1 if rng.random() < 0.5 else -1) * float(rng.uniform(2.3, 2.8))
            if pothole(x, lt)[1] == 0 and free(x, lt):
                put(grass[int(rng.integers(len(grass)))], x, lt, float(rng.uniform(0.75, 1.15)))
                crown += 1
    n += crown
    # Bananas and a sugar palm or two behind and between the shops, as round any roadside house.
    fl = VN.flora()
    banana, palm = fl["banana_clump"][1], fl["sugar_palm"][1]
    for k, (side, x, lt) in enumerate([(-1, -6.2, 9.2), (-1, 6.0, 10.4), (-1, -19.2, 9.8), (-1, 19.0, 9.0),
                                       (1, -18.2, 8.9), (1, 17.9, 9.6),
                                       (-1, 31.0, 11.0), (-1, -31.5, 10.5)]):
        px, py = at(x, side * lt)
        if any(_in_shop(sp, px, py, 0.8) for sp in SHOPS):
            continue
        VN.place(coll, banana, f"vroad_banana_{k}", px, py, ground(px, py) - 0.05, float(rng.uniform(0, 6.283)),
                 float(rng.uniform(0.85, 1.15)))
    for k, (side, x, lt) in enumerate([(-1, -8.6, 12.5), (-1, 21.0, 12.8), (1, 23.0, 9.6)]):
        px, py = at(x, side * lt)
        VN.place(coll, palm, f"vroad_sugar_palm_{k}", px, py, ground(px, py) - 0.05, float(rng.uniform(0, 6.283)),
                 float(rng.uniform(0.85, 1.0)))
    # The road itself is kept clean (the user, Nov 26, 2026: "cleanup to make the road clean"):
    # no branches, bark or loose stones on the carriageway, shoulders or in the ditches; only
    # a few fallen twigs and bark on the outer banks between the shops, as any verge has.
    for _ in range(40):
        x = float(rng.uniform(-WALK_X - 6, WALK_X + 6))
        lt = float(rng.choice([-1, 1])) * float(rng.uniform(6.2, 7.0))
        if not free(x, lt):
            continue
        put(litter[int(rng.integers(len(litter)))], x, lt, float(rng.uniform(0.6, 1.0)))
    print(f"[village_road] verge plants {n}", flush=True)


def backdrop(coll, ground, rng):
    """The jungle the road runs through: behind the south shops (there was only open ground
    there, the farm's tree wall stands round its fence), past the fence's corners on the north
    side, and closing in at both ends; old trees, bananas, sugar palms and dead wood, the
    nearest row at full detail, an understory of shrubs and ferns in front of it."""
    import village_nature as VN

    fl = VN.flora()
    kinds = [("tree", 0.55), ("banana", 0.22), ("palm", 0.15), ("dead", 0.08)]
    p = np.array([w for _k, w in kinds])
    dead = bpy_object("forest_tree_gn_dead") or fl["forest_tree_gn"][1]
    shrubs = VN.poly_haven("shrub_03") + VN.poly_haven("shrub_04") + VN.poly_haven("fern_02")
    placed = []

    def ok(x, y, r):
        if any(_in_shop(sp, x, y, 1.6) for sp in SHOPS):
            return False
        return all(math.hypot(x - a, y - b) > r + rb for a, b, rb in placed)

    n = 0
    for row, lt in enumerate((-14.0, -19.0, -24.5, -30.0)):
        x = -REACH + float(rng.uniform(0, 3))
        while x < REACH:
            sides = [-1] + ([1] if (abs(x) > 40.0 or row == 0 and abs(x) > 33.0) else [])
            for side in sides:
                l = side * abs(lt) + float(rng.uniform(-1.6, 1.6))
                if side > 0 and abs(x) < 47.0:
                    l = max(l, 9.0)
                px, py = at(x + float(rng.uniform(-1.2, 1.2)), l)
                kind = kinds[int(rng.choice(len(kinds), p=p / p.sum()))][0]
                near = row == 0 and abs(x) < 36.0
                if kind == "dead" and row > 1:
                    kind = "tree"          # bare wood has no lighter version: only near the road
                r = {"tree": 3.0, "banana": 1.6, "palm": 1.8, "dead": 2.6}[kind]
                if not ok(px, py, r):
                    continue
                yaw = float(rng.uniform(0, 6.283))
                z = ground(px, py) - 0.05
                if kind == "tree":
                    src = fl["forest_tree_gn"][1 if near else 2]
                    s = float(rng.uniform(0.78, 1.2))
                elif kind == "banana":
                    src = fl["banana_clump"][1 if near else 2]
                    s = float(rng.uniform(0.85, 1.2))
                elif kind == "palm":
                    src = fl["sugar_palm"][1 if near else 2]
                    s = float(rng.uniform(0.85, 1.05))
                else:
                    src = dead
                    s = float(rng.uniform(0.8, 1.05))
                obj = VN.place(coll, src, f"vroad_jungle_{kind}_{n}", px, py, z, yaw, s)
                obj["flora"] = f"vroad_{kind}"
                placed.append((px, py, r))
                n += 1
            x += float(rng.uniform(4.6, 6.8)) if row < 2 else float(rng.uniform(6.0, 9.0))
    # The understory along the jungle's edge behind the shops, seen between them.
    k = 0
    x = -WALK_X - 6
    while x < WALK_X + 6:
        l = -float(rng.uniform(10.6, 13.5))
        px, py = at(x, l)
        if not any(_in_shop(sp, px, py, 0.6) for sp in SHOPS):
            o = VN.put(coll, shrubs[int(rng.integers(len(shrubs)))], px, py, ground, float(rng.uniform(0, 6.283)),
                       float(rng.uniform(0.7, 1.25)))
            o.name = "vroad_" + o.name
            k += 1
        x += float(rng.uniform(1.4, 2.6))
    print(f"[village_road] jungle {n}, understory {k}", flush=True)


def bpy_object(name):
    import bpy

    return bpy.data.objects.get(name)


def _obox(coll, name, centre, length, thick, z0, z1, yaw, surface="leaves"):
    """An oriented box collider (a box in its own frame: the game makes it a box shape)."""
    import bpy
    from mathutils import Euler

    hx, hy = length / 2, thick / 2
    verts = [(sx * hx, sy * hy, z) for z in (z0, z1) for sx in (-1, 1) for sy in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new(f"col_{name}")
    me.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(f"col_{name}", me)
    coll.objects.link(obj)
    obj.location = (centre[0], centre[1], 0.0)
    obj.rotation_euler = Euler((0.0, 0.0, yaw))
    obj["surface"] = surface
    obj.display_type = "WIRE"
    obj.hide_render = True
    return obj


def _local_box(coll, name, M, x0, x1, y0, y1, z0, z1, surface="teak"):
    """A box in a shop's own frame (M), as a collider."""
    import bpy

    verts = [(x, y, z) for z in (z0, z1) for x in (x0, x1) for y in (y0, y1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new(f"col_{name}")
    me.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(f"col_{name}", me)
    coll.objects.link(obj)
    obj.matrix_world = M
    obj["surface"] = surface
    obj.display_type = "WIRE"
    obj.hide_render = True
    return obj


def _wall_along(coll, name, lt, xa, xb, base, gaps_x=()):
    """Collider boxes following the road at `lt`, from xa to xb, leaving the gaps open."""
    spans, at_x = [], xa
    for g0, g1 in sorted(gaps_x):
        if g1 <= xa or g0 >= xb:
            continue
        if g0 > at_x:
            spans.append((at_x, g0))
        at_x = max(at_x, g1)
    if at_x < xb:
        spans.append((at_x, xb))
    k = 0
    for s0, s1 in spans:
        n = max(1, int(math.ceil((s1 - s0) / 2.0)))
        for j in range(n):
            a, b = s0 + (s1 - s0) * j / n, s0 + (s1 - s0) * (j + 1) / n
            pa, pb = at(a, lt), at(b, lt)
            cx, cy = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
            length = math.hypot(pb[0] - pa[0], pb[1] - pa[1]) + 0.04
            z = base((a + b) / 2)
            _obox(coll, f"{name}_{k}", (cx, cy), length, 0.16, z - 0.6, z + 2.8, math.atan2(pb[1] - pa[1], pb[0] - pa[0]))
            k += 1


def colliders(coll, ground, base, gaps):
    """What Sora walks on and where she stops: the road's surface (a coarse copy of it), the
    lines along the ditches' far sides open only at the causeway and the shops' footbridges,
    walls across the road at the fallen trees, and each shop: its floor, its veranda and
    steps, the footbridge's sides, and its doorway closed (the shops are for looking into)."""
    import bpy

    # The surface, every metre, out over both ditches (and up the causeway).
    lats = [-4.8, -4.35, -4.05, -3.75, -3.45, -3.15, -2.7, -1.35, 0.0, 1.35, 2.7, 3.15, 3.45, 3.75, 4.05, 4.35, 4.8,
            5.4, 6.0, 6.6]
    xs = list(np.arange(-WALK_X - 1.5, WALK_X + 1.51, 1.0))
    verts, faces = [], []
    for x in xs:
        for lt in lats:
            px, py = at(x, lt)
            verts.append((px, py, _road_height(x, lt, ground, base) - 0.005))
    n = len(lats)
    for j in range(len(xs) - 1):
        for i in range(n - 1):
            a = j * n + i
            faces.append((a + 1, a + n + 1, a + n, a))   # facing up
    me = bpy.data.meshes.new("col_vroad_surface")
    me.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new("col_vroad_surface", me)
    coll.objects.link(obj)
    obj["surface"] = "mud"
    obj.display_type = "WIRE"
    obj.hide_render = True

    cx, flat, _out = CAUSEWAY
    north = [(g0 - 0.02, g1 + 0.02) for s, g0, g1 in gaps if s > 0] + [(cx - flat + 0.1, cx + flat - 0.1)]
    south = [(g0 - 0.02, g1 + 0.02) for s, g0, g1 in gaps if s < 0]
    # North: the whole width of the play area, so the bank past the fallen trees is shut too.
    _wall_along(coll, "vroad_ditch_n", WALL_L, -46.0, 46.0, base, north)
    _wall_along(coll, "vroad_ditch_s", -WALL_L, -WALK_X, WALK_X, base, south)
    for k, x in enumerate((-WALK_X, WALK_X)):
        pa, pb = at(x, -WALL_L - 0.1), at(x, WALL_L + 0.1)
        z = base(x)
        _obox(coll, f"vroad_end_{k}", ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2), math.hypot(pb[0] - pa[0], pb[1] - pa[1]),
              0.3, z - 0.6, z + 3.0, math.atan2(pb[1] - pa[1], pb[0] - pa[0]))
    # The culvert's headwalls stand either side of the causeway.
    for s in (-1, 1):
        pa, pb = at(cx + s * 2.05, 3.3), at(cx + s * 2.05, 4.9)
        z = base(cx)
        _obox(coll, f"vroad_headwall_{'we'[s > 0]}", ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2),
              math.hypot(pb[0] - pa[0], pb[1] - pa[1]), 0.26, z - 0.5, z + 0.8, math.atan2(pb[1] - pa[1], pb[0] - pa[0]), "stone")

    from mathutils import Vector

    import farmstead as FS

    for idx, sp in enumerate(SHOPS):
        M = shop_matrix(sp, base)
        hw = sp["hw"]
        moto = sp["trade"] == "moto"
        step_y = 0.0 if moto else -0.35
        half = 1.45 if moto else 0.72
        deck = 0.178
        if sp["open_front"] and not sp["dim"]:
            # Hollow walkable interior: seamless floor, back wall, side walls, and doorway flanks
            door_half = 0.94
            _local_box(coll, f"vroad_shop_{idx}_in_floor", M, -3.5, 0.16, -hw - 0.1, hw + 0.1, -0.7, deck + 0.006)
            _local_box(coll, f"vroad_shop_{idx}_in_back", M, -3.5, -3.22, -hw - 0.14, hw + 0.14, -0.7, 3.7)
            _local_box(coll, f"vroad_shop_{idx}_in_l", M, -3.5, 0.14, -hw - 0.14, -hw + 0.04, -0.7, 3.7)
            _local_box(coll, f"vroad_shop_{idx}_in_r", M, -3.5, 0.14, hw - 0.04, hw + 0.14, -0.7, 3.7)
            _local_box(coll, f"vroad_shop_{idx}_in_fl", M, -0.08, 0.14, -hw - 0.14, -door_half, -0.7, 3.7)
            _local_box(coll, f"vroad_shop_{idx}_in_fr", M, -0.08, 0.14, door_half, hw + 0.14, -0.7, 3.7)
        else:
            _local_box(coll, f"vroad_shop_{idx}_in", M, -3.5, 0.12, -hw - 0.14, hw + 0.14, -0.7, 3.7)
        _local_box(coll, f"vroad_shop_{idx}_deck", M, 0.12, 1.96, -hw, hw, -0.7, deck)
        _local_box(coll, f"vroad_shop_{idx}_side_l", M, 0.1, 1.98, -hw - 0.14, -hw, deck - 0.05, 2.5)
        _local_box(coll, f"vroad_shop_{idx}_side_r", M, 0.1, 1.98, hw, hw + 0.14, deck - 0.05, 2.5)
        # The veranda's front edge, open where the steps (or the apron) come up.
        _local_box(coll, f"vroad_shop_{idx}_front_a", M, 1.96, 2.1, -hw - 0.14, step_y - half, -0.7, 1.3)
        _local_box(coll, f"vroad_shop_{idx}_front_b", M, 1.96, 2.1, step_y + half, hw + 0.14, -0.7, 1.3)
        # The footbridge's (or apron's) sides, from the veranda's edge out to the road's shoulder.
        for s in (-1, 1):
            y0 = step_y + s * half
            _local_box(coll, f"vroad_shop_{idx}_bridge_{'lr'[s > 0]}", M, 1.96, 4.1, min(y0, y0 + s * 0.12),
                       max(y0, y0 + s * 0.12), -1.0, 0.9)
        def world(lx, ly, lz, M=M):
            return tuple(M @ Vector((lx, ly, lz)))

        if moto:
            FS.ramp_collider(coll, f"vroad_shop_{idx}_apron", world(3.62, 0.0, -0.3), world(1.95, 0.0, deck), half)
        else:
            _local_box(coll, f"vroad_shop_{idx}_bridge", M, 2.5, 4.02, step_y - half, step_y + half, -0.9, -0.249)
            FS.ramp_collider(coll, f"vroad_shop_{idx}_steps", world(2.56, step_y, -0.249), world(1.93, step_y, deck), half)
    for o in coll.objects:
        if o.name.startswith("col_vroad_"):
            o.display_type = "WIRE"
            o.hide_render = True
