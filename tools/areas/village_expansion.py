"""Ground for the Episode 1 village expansion (November 2026), run inside Blender.

`extend_ground` widens the authored terrain from 80 x 132 m to the plan in
village_layout.py, keeping every old height exactly: new ground carries on the
forest floor's gentle swell, the road bank and the drowned paddies; the east pond
is cut as a basin with shelving banks; the side lanes are trodden mud.
`clear_open_ground` takes the village's own plants out of the new clearings and
lanes (whole plants by their foot; joined undergrowth part by part), sparing
the trees the runtime forest uses as templates.
"""
import math
import re

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import village_layout as L

ROAD_Y = -63.5
# Trees ForestBorder.ts copies the forest from: never removed.
TEMPLATES = {"tree_0", "tree_3", "tree_12", "tree_301", "tree_305", "tree_311", "tree_10", "tree_11", "tree_317",
             "palm_0", "palm_3", "palm_6", "coco_0", "coco_3", "bamboo_0", "bamboo_3", "bamboo_7", "banana_1",
             "banana_5", "banana_13", "dead_3", "dead_6", "telegraph_2", "dead_tree_trunk.001"}


def _smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _forest_floor(x, y):
    """The old terrain's swell (ep1_area_village.terrain, forest amplitude), its own phase."""
    return 1.8 * (0.06 * math.sin(x * 0.37 + 4.1) * math.cos(y * 0.29 + 1.7)
                  + 0.04 * math.sin(x * 1.1 + y * 0.7 + 2.9) + 0.02 * math.sin(x * 2.3 - y * 1.9 + 0.6))


def _road_and_fields(x, y, h):
    """South of the forest: the road bank and the flooded rice fields, as terrain() lays them."""
    road = abs(y - ROAD_Y)
    if road < 2.6:
        return 0.14 - 0.02 * road - 0.07 * math.exp(-((road - 0.8) / 0.25) ** 2)
    if y > ROAD_Y:
        return min(h, 0.14 - 0.06 * (road - 2.6))
    if y < -86.5:
        return 0.1 + 0.05 * math.sin(x * 0.9)
    h = -0.32 + 0.03 * math.sin(x * 0.7 + y * 0.4)
    if any(abs(y - yd) < 0.45 for yd in (-74.0, -84.0)) or any(abs(x - xd) < 0.45 for xd in (-62, -48, 50, 64)):
        h = 0.03
    return h


POND_WATER = -0.2  # the pond's surface (m): shore below it, banks above


def pond_depth(x, y, z=0.0):
    """The ground `z` cut by the pond: its bed, and banks shelving to the water.
    None away from it (or before the pond is built)."""
    if "east" not in L.BUILT:
        return None
    r = math.sqrt(L.ellipse_value(x, y, L.EAST_POND["water"]))
    if r > 1.35:
        return None
    if r >= 1.0:
        # The bank shelves down to just under the waterline over the last metre or so,
        # except where feet have trodden a landing to the jetty's first boards.
        h = -0.27 + (z + 0.27) * _smooth(1.0, 1.35, r)
        jx, jy, _ = L.EAST_POND["jetty"]
        if abs(y - jy) < 1.4 and x < jx + 0.4:
            h = max(h, min(z, 0.0) - 0.04)
        return h
    return -0.27 - 0.95 * _smooth(1.0, 0.55, r)


def new_height(x, y, edge):
    h = _forest_floor(x, y)
    if L.in_clearing(x, y):
        h *= 0.45
    lane = L.lane_distance(x, y)
    h -= 0.035 * (1 - _smooth(0.0, 0.8, lane))
    if y < -60.5:
        h = _road_and_fields(x, y, h)
    # Meet the old ground at its edge, smoothly.
    if edge is not None:
        d, z = edge
        h = z + (h - z) * _smooth(0.0, 5.0, d)
    return h


def extend_ground():
    """Rebuild `ground` over the new terrain on the same 1 m grid (idempotent)."""
    g = bpy.data.objects["ground"]
    me = g.data
    old_h, old_mat = {}, {}
    if not g.get("expanded"):
        for v in me.vertices:
            old_h[(round(v.co.x), round(v.co.y))] = v.co.z
        for p in me.polygons:
            c = p.center
            old_mat[(math.floor(c.x), math.floor(c.y))] = p.material_index
        g["old_heights"] = np.array([[k[0], k[1], z] for k, z in old_h.items()], dtype=np.float32).ravel().tolist()
        g["old_mats"] = np.array([[k[0], k[1], m] for k, m in old_mat.items()], dtype=np.int32).ravel().tolist()
    else:
        a = np.array(g["old_heights"], dtype=np.float32).reshape(-1, 3)
        old_h = {(int(round(x)), int(round(y))): float(z) for x, y, z in a}
        b = np.array(g["old_mats"], dtype=np.int32).reshape(-1, 3)
        old_mat = {(int(x), int(y)): int(m) for x, y, m in b}
    O, T = L.OLD_TERRAIN, L.TERRAIN
    x0, x1, y0, y1 = int(T["x0"]), int(T["x1"]), int(T["y0"]), int(T["y1"])
    nx, ny = x1 - x0, y1 - y0

    def edge_of(x, y):
        cx, cy = max(O["x0"], min(O["x1"], x)), max(O["y0"], min(O["y1"], y))
        d = math.hypot(x - cx, y - cy)
        return d, old_h[(round(cx), round(cy))]

    verts = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + i, y0 + j
            if (x, y) in old_h:
                z = old_h[(x, y)]
                lane = L.lane_distance(x, y)
                if lane < 0.9:
                    z -= 0.035 * (1 - _smooth(0.0, 0.9, lane))
            else:
                z = new_height(x, y, edge_of(x, y))
            p = pond_depth(x, y, z)
            if p is not None:
                z = p
            verts.append((float(x), float(y), z))
    faces, mats = [], []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
            cx, cy = x0 + i + 0.5, y0 + j + 0.5
            key = (x0 + i, y0 + j)
            if key in old_mat:
                k = old_mat[key]
            else:
                k = 0 if cy < -60.5 else 1
            # Lanes and the pond's bank are not painted here: in the game the ground
            # mask (pathGround.ts) mixes mud and litter softly; previews use
            # preview_ground() for the same look.
            mats.append(k)
    new = bpy.data.meshes.new("ground")
    new.from_pydata(verts, [], faces)
    for m in me.materials:
        new.materials.append(m)
    new.polygons.foreach_set("material_index", np.array(mats, dtype=np.int32))
    new.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
    new.update()
    old = g.data
    g.data = new
    bpy.data.meshes.remove(old)
    g.data.name = "ground"
    g["expanded"] = True
    # World UVs at the ground's 2.25 m tile (GROUND_TILE), as kit.world_uvs lays them.
    uv = new.uv_layers.new(name="UVMap")
    co = np.empty(len(new.vertices) * 3, dtype=np.float32)
    new.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    loops = np.empty(len(new.loops), dtype=np.int32)
    new.loops.foreach_get("vertex_index", loops)
    tile = new.materials[0].get("tile", 2.25)
    uv.data.foreach_set("uv", (co[loops][:, :2] / tile).ravel())
    # The ground collider and the flood over the fields follow.
    col = bpy.data.objects["col_ground"]
    col.location = ((T["x0"] + T["x1"]) / 2, (T["y0"] + T["y1"]) / 2, -0.5)
    col.scale = (1, 1, 1)
    _box_mesh(col, (T["x1"] - T["x0"]) / 2, (T["y1"] - T["y0"]) / 2, 0.5)
    flood = bpy.data.objects["flood_water"]
    for v in flood.data.vertices:
        v.co.x = T["x0"] if v.co.x < 0 else T["x1"]
    flood.data.update()
    return g


def _box_mesh(obj, hx, hy, hz):
    me = obj.data
    for v in me.vertices:
        v.co = Vector((math.copysign(hx, v.co.x), math.copysign(hy, v.co.y), math.copysign(hz, v.co.z)))
    me.update()


def pond_water(coll, mat):
    """The pond's surface, a little ragged at the shore."""
    cx, cy, rx, ry, turn = L.EAST_POND["water"]
    n = 72
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1.08 + 0.04 * math.sin(a * 5 + 1.3) + 0.03 * math.sin(a * 11)
        u, v = math.cos(a) * rx * k, math.sin(a) * ry * k
        pts.append((cx + u * math.cos(turn) - v * math.sin(turn), cy + u * math.sin(turn) + v * math.cos(turn), POND_WATER))
    me = bpy.data.meshes.new("pond_e_water")
    me.from_pydata([(cx, cy, POND_WATER)] + pts, [], [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)])
    me.materials.append(mat)
    obj = bpy.data.objects.new("pond_e_water", me)
    coll.objects.link(obj)
    return obj


# ------------------------------------------------------------ plant clearing

PLANT = re.compile(r"^(tree_\d+|palm_\d+|coco_\d+|bamboo_\d+|banana_\d+|dead_\d+|island_tree|shrub_|fern_|"
                   r"pachira_|grass_medium|weed_|nettle_|moss_|dry_branches|dead_tree_trunk|root_cluster|tree_stump|"
                   r"forest_grass|grove_grass|yard_edge_grass|house_forest_|forest_understory_|forest_litter_|"
                   r"forest_edge_sedge_|jungle_understory_|jungle_litter_)")
JOINED = re.compile(r"^(forest_grass|grove_grass|yard_edge_grass|house_forest_|forest_understory_|forest_litter_|"
                    r"forest_edge_sedge_|jungle_understory_|jungle_litter_)")


def _foot(obj):
    me = obj.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(obj.matrix_world)
    w = co @ mw[:3, :3].T + mw[:3, 3]
    low = w[:, 2].min()
    base = w[w[:, 2] < low + 0.3]
    return float(base[:, 0].mean()), float(base[:, 1].mean())


GRASS = re.compile(r"^(forest_grass|grove_grass|yard_edge_grass|grass_medium|house_forest_house_sedge|forest_edge_sedge)")


def _blocked(x, y, margin, keep_out, grass=False):
    """Plants go from the lanes and the buildings' ground; in the clearings the
    forest floor plants go but grass and sedge stay (an abandoned yard grows over)."""
    if L.lane_distance(x, y) < L.LANE_WIDTH / 2 + .5 + margin:
        return True
    if any(math.hypot(x - kx, y - ky) < kr + margin for kx, ky, kr in keep_out):
        return True
    if grass:
        return False
    return any(L.ellipse_value(x, y, e) < .9 for e in L.CLEARINGS)


def clear_open_ground(keep_out=(), keep=(), log=print):
    """Removes the village's plants that stand in the new clearings and lanes.

    `keep_out` adds (x, y, r) discs (buildings); `keep` names objects to spare.
    Whole plants go by their foot; the joined undergrowth patches lose only the
    parts (loose islands) inside. Returns the names removed."""
    removed, trimmed = [], 0
    for name in [o.name for o in bpy.data.objects]:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH" or not PLANT.match(obj.name) or obj.name in TEMPLATES or obj.name in keep:
            continue
        if obj.users_collection and (obj.users_collection[0].name == "_protos"
                                     or obj.users_collection[0].name.startswith("expansion_")):
            continue
        if JOINED.match(obj.name):
            trimmed += _trim_islands(obj, keep_out, bool(GRASS.match(obj.name)))
            continue
        x, y = _foot(obj)
        tree = re.match(r"^(tree_\d+|palm_\d+|coco_\d+|bamboo_\d+|dead_\d+|island_tree)", obj.name)
        margin = 1.2 if tree else 0.3
        # The giants: only those whose trunk stands well inside a clearing or on a lane.
        if tree and not (any(L.ellipse_value(x, y, e) < 0.75 for e in L.CLEARINGS)
                         or L.lane_distance(x, y) < 1.8
                         or any(math.hypot(x - kx, y - ky) < kr + 1.5 for kx, ky, kr in keep_out)):
            continue
        if not tree and not _blocked(x, y, margin, keep_out, bool(GRASS.match(obj.name))):
            continue
        col = bpy.data.objects.get("col_" + obj.name)
        if col:
            bpy.data.objects.remove(col, do_unlink=True)
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
    log(f"cleared {len(removed)} plants, trimmed {trimmed} undergrowth parts")
    return removed


def _trim_islands(obj, keep_out, grass=False):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    mw = obj.matrix_world
    seen, doomed = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        island, stack = [], [f]
        seen.add(f.index)
        while stack:
            g = stack.pop()
            island.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        pts = [mw @ v.co for g in island for v in g.verts]
        x = sum(p.x for p in pts) / len(pts)
        y = sum(p.y for p in pts) / len(pts)
        if _blocked(x, y, 0.2, keep_out, grass):
            doomed.extend(island)
    n = len(doomed)
    if n:
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
        bm.to_mesh(me)
        me.update()
    bm.free()
    return n


def open_fence(prefix, axis, lo, hi):
    """Cuts the fence's rails and collider at a lane and takes the post there out."""
    i = "xyz".index(axis)
    for o in list(bpy.data.objects):
        if not (o.name.startswith(prefix) or o.name == f"col_{prefix}") or o.get("gap_cut") or o.type != "MESH":
            continue
        mw = o.matrix_world
        pts = [mw @ v.co for v in o.data.vertices]
        a, b = min(p[i] for p in pts), max(p[i] for p in pts)
        if b < lo or a > hi:
            continue
        if b - a < 0.5:
            # A post in the gap: gone (pulled out for firewood).
            bpy.data.objects.remove(o, do_unlink=True)
            continue
        twin = o.copy()
        twin.data = o.data.copy()
        twin.name = o.name + "_n"
        for c in o.users_collection:
            c.objects.link(twin)
        inv = mw.inverted()
        for obj, keep_low in ((o, True), (twin, False)):
            if obj.data.users > 1:
                obj.data = obj.data.copy()
            for v in obj.data.vertices:
                w = mw @ v.co
                if keep_low and w[i] > lo:
                    w[i] = lo
                elif not keep_low and w[i] < hi:
                    w[i] = hi
                v.co = inv @ w
            obj.data.update()
            obj["gap_cut"] = True
    print(f"Opened {prefix} at {axis} {lo}..{hi}", flush=True)


# ------------------------------------------------------------ ground sampling

class Ground:
    """Bilinear heights from the (expanded) ground's 1 m grid."""

    def __init__(self):
        g = bpy.data.objects["ground"]
        co = np.empty(len(g.data.vertices) * 3, dtype=np.float32)
        g.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        self.x0, self.y0 = co[:, 0].min(), co[:, 1].min()
        nx = int(round(co[:, 0].max() - self.x0)) + 1
        ny = int(round(co[:, 1].max() - self.y0)) + 1
        h = np.zeros((ny, nx), dtype=np.float32)
        h[np.rint(co[:, 1] - self.y0).astype(int), np.rint(co[:, 0] - self.x0).astype(int)] = co[:, 2]
        self.h = h

    def __call__(self, x, y):
        fx = min(max(x - self.x0, 0), self.h.shape[1] - 1.0001)
        fy = min(max(y - self.y0, 0), self.h.shape[0] - 1.0001)
        i, j = int(fx), int(fy)
        tx, ty = fx - i, fy - j
        h = self.h
        return float((h[j, i] * (1 - tx) + h[j, i + 1] * tx) * (1 - ty) + (h[j + 1, i] * (1 - tx) + h[j + 1, i + 1] * tx) * ty)

    def lowest(self, pts):
        return min(self(x, y) for x, y in pts)


# ------------------------------------------------------------ preview forest

def preview_forest(coll, rng, centre, radius, spacing=(8.0, 4.0, 2.2)):
    """For Cycles previews only (never saved): fills new ground near `centre` with
    linked copies of the forest's templates, as ForestBorder.ts does in the game."""
    ground = Ground()
    sources = {
        "canopy": [bpy.data.objects[n] for n in ("tree_0", "tree_3", "tree_12", "tree_301", "tree_305", "tree_311")],
        "mid": [bpy.data.objects[n] for n in ("tree_10", "tree_11", "tree_317")]
        + [o for o in bpy.data.objects if o.name.startswith("pachira_aquatica_01_bark_") and o.name.endswith(".001")],
        "under": [o for o in bpy.data.objects if re.match(r"^(shrub_0[234]_[a-d]|fern_02_[a-d])\.001$", o.name)],
    }
    feet = {o.name: _foot(o) for group in sources.values() for o in group}
    placed = 0
    trunks = []
    cx, cy = centre
    for layer, step in zip(("canopy", "mid", "under"), spacing):
        for gx in np.arange(cx - radius, cx + radius, step):
            for gy in np.arange(cy - radius, cy + radius, step):
                x, y = gx + step * rng.uniform(.15, .85), gy + step * rng.uniform(.15, .85)
                if math.hypot(x - cx, y - cy) > radius or not L.in_new_ground(x, y):
                    continue
                if not (L.TERRAIN["x0"] < x < L.TERRAIN["x1"] and L.TERRAIN["y0"] < y < L.TERRAIN["y1"]) or y < -58:
                    continue
                if L.open_ground(x, y, 1.5 if layer == "canopy" else 0.4):
                    continue
                if layer != "under" and any(math.hypot(x - a, y - b) < r for a, b, r in trunks):
                    continue
                if rng.random() > (0.8 if layer == "canopy" else 0.8):
                    continue
                src = sources[layer][int(rng.integers(len(sources[layer])))]
                fx, fy = feet[src.name]
                s = rng.uniform(.65, 1.15) if layer == "canopy" else rng.uniform(.8, 1.6)
                parts = [src] + ([c for c in src.parent.children if c != src] if src.parent and layer == "mid" else [])
                yaw = rng.uniform(0, math.tau)
                rot = Matrix_rz(yaw)
                for part in parts:
                    dup = part.copy()
                    dup.parent = None
                    coll.objects.link(dup)
                    m = np.array(part.matrix_world)
                    m[:3, 3] -= (fx, fy, 0)
                    from mathutils import Matrix
                    dup.matrix_world = Matrix.Translation((x, y, ground(x, y) - .03)) @ rot @ Matrix.Scale(s, 4) @ Matrix(m.tolist())
                placed += 1
                if layer != "under":
                    trunks.append((x, y, 2.2 if layer == "canopy" else 1.0))
    return placed


def Matrix_rz(a):
    from mathutils import Matrix
    return Matrix.Rotation(a, 4, "Z")


def preview_grass(coll, rng, centre, radius, keep_out=(), density=.8):
    """For previews: the tall grass the game grows in the new clearings (grass.ts)."""
    from forest_detail import grass_geometry
    ground = Ground()
    spots = []
    cx, cy = centre
    for gx in np.arange(cx - radius, cx + radius, .7):
        for gy in np.arange(cy - radius, cy + radius, .7):
            x, y = gx + rng.uniform(0, .7), gy + rng.uniform(0, .7)
            if not L.in_clearing(x, y, 1.5) or L.in_pond(x, y, 1.2):
                continue
            if L.lane_distance(x, y) < .9 or any(math.hypot(x - a, y - b) < r for a, b, r in keep_out):
                continue
            edge = min(L.ellipse_value(x, y, e) for e in L.CLEARINGS)
            if rng.random() > density * (.5 + .5 * min(1, edge)):
                continue
            spots.append((x, y, ground(x, y)))
    return grass_geometry("preview_grass", coll, spots, rng, size=(.45, 1.1))


# ------------------------------------------------------------ preview ground

def preview_ground(cuts=2):
    """For Cycles previews only (never saved): the ground as the game draws it.
    A subdivided copy of `ground` carries the game's mud/litter mask (ground_mask.py)
    as a colour attribute, mixing the two ground materials softly."""
    import ground_mask
    g = bpy.data.objects["ground"]
    me = g.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=cuts, use_grid_fill=True)
    bm.to_mesh(me)
    bm.free()
    attr = me.color_attributes.new("mud", "FLOAT_COLOR", "POINT")
    vals = np.zeros(len(me.vertices) * 4, dtype=np.float32)
    for i, v in enumerate(me.vertices):
        mud, wet = ground_mask.ground_mix(-v.co.x, -v.co.y)
        vals[i * 4:i * 4 + 4] = (mud, wet, 0, 1)
    attr.data.foreach_set("color", vals)
    mud_m, litter_m = bpy.data.materials["M_wet_mud"], bpy.data.materials["M_wet_forest_floor"]
    mat = mud_m.copy()
    mat.name = "M_preview_ground_blend"
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    src = {n.name: n for n in litter_m.node_tree.nodes}
    att = nt.nodes.new("ShaderNodeAttribute")
    att.attribute_name = "mud"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(att.outputs["Color"], sep.inputs["Color"])
    uv = nt.nodes.new("ShaderNodeUVMap")
    scale = nt.nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.inputs["Scale"].default_value = mud_m.get("tile", 2.25) / litter_m.get("tile", 2.0)
    nt.links.new(uv.outputs["UV"], scale.inputs[0])
    lit = {}
    for key in ("Image Texture", "Image Texture.001", "Image Texture.002"):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = src[key].image
        nt.links.new(scale.outputs["Vector"], n.inputs["Vector"])
        lit[key] = n
    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = src["Mix"].blend_type
    tint.inputs[0].default_value = src["Mix"].inputs[0].default_value
    tint.inputs[7].default_value = src["Mix"].inputs[7].default_value
    nt.links.new(lit["Image Texture"].outputs["Color"], tint.inputs[6])

    def blend(socket_from_mud, socket_from_litter, to_socket, kind="RGBA"):
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = kind
        nt.links.new(sep.outputs["Red"], mix.inputs[0])
        a, b = (6, 7) if kind == "RGBA" else (2, 3)
        nt.links.new(socket_from_litter, mix.inputs[a])
        nt.links.new(socket_from_mud, mix.inputs[b])
        nt.links.new(mix.outputs[2 if kind == "RGBA" else 0], to_socket)

    base_mud = nt.nodes["Mix"].outputs[2]
    blend(base_mud, tint.outputs[2], bsdf.inputs["Base Color"])
    nmap = nt.nodes["Normal Map"]
    blend(nt.nodes["Image Texture.001"].outputs["Color"], lit["Image Texture.001"].outputs["Color"], nmap.inputs["Color"])
    orm_sep = nt.nodes["Separate Color"]
    lsep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(lit["Image Texture.002"].outputs["Color"], lsep.inputs["Color"])
    blend(orm_sep.outputs["Green"], lsep.outputs["Green"], bsdf.inputs["Roughness"], kind="FLOAT")
    me.materials.clear()
    me.materials.append(mat)
    obj = bpy.data.objects.new("preview_ground", me)
    bpy.context.scene.collection.objects.link(obj)
    g.hide_render = True
    return obj
