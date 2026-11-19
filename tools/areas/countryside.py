"""Countryside round the house (the user, November 19, 2026: "I prefer kind view all
around the house. Only add banana tree and some parts and keep a few big tree just like
for neak ta shrine"; then, with a preview render they chose as the look: rice fields and
palms all round the house, "a very thick of banana and bamboo plants" behind it (then: no
bamboo at all, bananas and palms in its place), big trees
only at the Neak Ta shrine and the stupas, and "the road should be straight to the house
but long along with the rice field and palm trees also scarecrow").

Raised and dry: the compound and its margin, the earth road in from the road bank (dead
straight, a dike between the fields with a sugar palm row along each side), the
expansion's lanes and clearings, the Neak Ta grove round the banyan, the wells, the old
pond, the road bank, the banana and sugar palm grove filling the ground behind the house,
and a band along the walls where the next village's tree line stands. Everything else is
paddy: the ground let down to the fields' mud, cut into plots by earth dikes, flooded,
planted, sugar palms standing over it and scarecrows in it. Two big trees only: the
shrine's banyan and a banyan over the stupas.

Run inside Blender after village_nature (rebuild-village-nature.py calls `build`).
Blender space: x east, y north; Babylon x = -x, z = -y.
"""
import math
import re

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import village_layout as L
import village_nature as VN

FLOOR = VN.PADDY_FLOOR
WATER = VN.WATER_Z
X0, X1, Y0, Y1 = -65.0, 65.0, -92.0, 62.0
PLAY = (-60.0, 60.0, -88.0, 57.0)

# The earth road from the road bank to the compound's gate: one straight line, the game's
# PATH (forestBorder.ts) mirrored. A raised dike ROAD_HALF either side of it.
ROAD_LINE = [(0.0, -60.0), (0.0, -3.0)]
ROAD_HALF = 2.3
# The sugar palms lining it, on the dike's shoulders (west row broken by the Neak Ta
# grove). The game's tree omens are tied to five of them (treeOmens.ts DRESSED_TRUNKS).
ROAD_PALMS = [(-2.9, y) for y in (-50.0, -43.5, -24.5, -17.5, -10.5)] + \
             [(2.9, y) for y in (-53.5, -47.0, -40.5, -34.0, -27.5, -21.0, -14.5, -8.0)]
# Scarecrows (tingmong_N): two at the road's mouth, the rest out in the fields either
# side of the road, facing it. (x, y, front): front is the heading they look along.
SCARECROWS = [(-3.6, -60.4, -1.72), (4.4, -60.8, -1.32), (-7.5, -71.5, math.pi / 2),
              (-9.5, -46.5, -0.45), (8.5, -21.0, math.pi + 0.45), (-10.5, -15.5, -0.3),
              (10.5, -44.0, math.pi + 0.35)]
# Behind the house: one grove of bananas under sugar palms, as thick as a household lets it get.
BACK_GROVE = (-30.0, 30.0, 29.0, 57.5)
# The second big tree: a banyan over the old stupas in the north garden.
STUPA_BANYAN = (-7.5, 55.6)
WELLS = [(-17.0, 7.5), (9.5, -33.0)]
OLD_POND = (-20.0, 19.0)
PLANTS = re.compile(r"^(tree|dead|palm|coco|bamboo|banana|pachira|shrub|fern|grass|moss_01|island_tree|bark_debris|"
                    r"single_root|anthurium|calathea|periwinkle|"
                    r"dry_branches|dead_tree_trunk|tree_stump|root_cluster|weed|nettle)")


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


class Land:
    """Which ground stays raised, and how far each point lies from it (m), on the
    terrain's 1 m grid."""

    def __init__(self, path_distance, in_yard, keep_trees):
        self.path_distance, self.in_yard = path_distance, in_yard
        self.keep_trees = keep_trees
        self.boxes = []
        skip = re.compile(r"^col_(ground|tree|dead|palm|coco|bamboo|banana|pachira|termite|ragtree|old_flag|tingmong|paddy)")
        for o in bpy.data.objects:
            if o.name.startswith("col_") and o.type == "MESH" and not skip.match(o.name):
                bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
                x0, x1 = min(p.x for p in bb), max(p.x for p in bb)
                y0, y1 = min(p.y for p in bb), max(p.y for p in bb)
                if x1 - x0 < 60 and y1 - y0 < 60:
                    self.boxes.append((x0 - 1.5, x1 + 1.5, y0 - 1.5, y1 + 1.5))
        self.nx, self.ny = int(X1 - X0) + 1, int(Y1 - Y0) + 1
        grid = np.zeros((self.ny, self.nx), dtype=bool)
        for j in range(self.ny):
            for i in range(self.nx):
                grid[j, i] = self.raised(X0 + i, Y0 + j)
        self.grid = grid
        self.dist = self._distance(grid)

    def raised(self, x, y):
        if self.in_yard(x, y, 6) or self.path_distance(x, y) < ROAD_HALF:
            return True
        if any(math.hypot(x - a, y - b) < 1.3 for a, b in ROAD_PALMS):
            return True
        if BACK_GROVE[0] < x < BACK_GROVE[1] and BACK_GROVE[2] < y < BACK_GROVE[3]:
            return True
        if L.lane_distance(x, y) < 1.3:
            return True
        if any(L.ellipse_value(x, y, e) < 1.25 for e in L.CLEARINGS):
            return True
        if math.hypot(x - VN.BANYAN[0], y - VN.BANYAN[1]) < 10 or math.hypot(x - VN.SHRINE[0], y - VN.SHRINE[1]) < 6:
            return True
        if any(math.hypot(x - a, y - b) < 3.5 for a, b in WELLS):
            return True
        if any(math.hypot(x - a, y - b) < 3.2 for a, b in self.keep_trees):
            return True
        if math.hypot(x - OLD_POND[0], y - OLD_POND[1]) < 7:
            return True
        if -66.0 < y < -58.6:                       # the road and its bank
            return True
        # The next village's tree line along the walls.
        if min(x - PLAY[0], PLAY[1] - x, y - PLAY[2], PLAY[3] - y) < 3.5:
            return True
        return any(a < x < b and c < y < d for a, b, c, d in self.boxes)

    @staticmethod
    def _distance(grid):
        """Chamfer distance (m) from the raised cells."""
        big = 1e6
        d = np.where(grid, 0.0, big)
        ny, nx = d.shape
        s2 = math.sqrt(2)
        for _ in range(2):
            for j in range(ny):
                for i in range(nx):
                    v = d[j, i]
                    if v == 0:
                        continue
                    if i > 0:
                        v = min(v, d[j, i - 1] + 1)
                    if j > 0:
                        v = min(v, d[j - 1, i] + 1)
                        if i > 0:
                            v = min(v, d[j - 1, i - 1] + s2)
                        if i < nx - 1:
                            v = min(v, d[j - 1, i + 1] + s2)
                    d[j, i] = v
            for j in range(ny - 1, -1, -1):
                for i in range(nx - 1, -1, -1):
                    v = d[j, i]
                    if v == 0:
                        continue
                    if i < nx - 1:
                        v = min(v, d[j, i + 1] + 1)
                    if j < ny - 1:
                        v = min(v, d[j + 1, i] + 1)
                        if i < nx - 1:
                            v = min(v, d[j + 1, i + 1] + s2)
                        if i > 0:
                            v = min(v, d[j + 1, i - 1] + s2)
                    d[j, i] = v
        return d

    def distance(self, x, y):
        """Bilinear distance from raised ground (0 on it)."""
        fx = min(max(x - X0, 0), self.nx - 1.0001)
        fy = min(max(y - Y0, 0), self.ny - 1.0001)
        i, j = int(fx), int(fy)
        tx, ty = fx - i, fy - j
        d = self.dist
        return float((d[j, i] * (1 - tx) + d[j, i + 1] * tx) * (1 - ty) + (d[j + 1, i] * (1 - tx) + d[j + 1, i + 1] * tx) * ty)

    def paddy(self, x, y, margin=1.2):
        return X0 < x < X1 and Y0 < y < Y1 and self.distance(x, y) > margin


class Dikes:
    """The earth dikes cutting the paddies into plots: a slightly skewed grid, about
    17 x 13 m, each line wandering a little; only where it crosses paddy."""

    def __init__(self, land, rng):
        self.land = land
        self.xs = []
        x = X0 + rng.uniform(4, 10)
        while x < X1:
            self.xs.append((x, rng.uniform(-0.04, 0.04)))
            x += rng.uniform(14, 20)
        self.ys = []
        y = Y0 + rng.uniform(3, 8)
        while y < Y1:
            self.ys.append((y, rng.uniform(-0.03, 0.03)))
            y += rng.uniform(11, 16)
        # The old paddies' dikes south of the road stay where they were.
        self.xs += [(x, 0.0) for x in VN.BUND_X if all(abs(x - a) > 4 for a, _ in self.xs)]

    def line_x(self, x0, skew, y):
        return x0 + skew * y + 0.35 * math.sin(y * 0.21 + x0)

    def line_y(self, y0, skew, x):
        return y0 + skew * x + 0.3 * math.sin(x * 0.17 + y0)

    def distance(self, x, y):
        best = min(abs(x - self.line_x(x0, s, y)) for x0, s in self.xs)
        return min(best, min(abs(y - self.line_y(y0, s, x)) for y0, s in self.ys))

    def plot(self, x, y):
        """The plot a point lies in (column, row)."""
        i = sum(1 for x0, s in self.xs if x > self.line_x(x0, s, y))
        j = sum(1 for y0, s in self.ys if y > self.line_y(y0, s, x))
        return i, j

    def segments(self, step=0.5):
        """Runs of each line through paddy, as point lists."""
        out = []
        for x0, s in self.xs:
            run = []
            y = Y0
            while y <= Y1:
                x = self.line_x(x0, s, y)
                if self.land.paddy(x, y, 1.6):
                    run.append((x, y))
                elif len(run) > 3:
                    out.append(run)
                    run = []
                else:
                    run = []
                y += step
            if len(run) > 3:
                out.append(run)
        for y0, s in self.ys:
            run = []
            x = X0
            while x <= X1:
                y = self.line_y(y0, s, x)
                if self.land.paddy(x, y, 1.6):
                    run.append((x, y))
                elif len(run) > 3:
                    out.append(run)
                    run = []
                else:
                    run = []
                x += step
            if len(run) > 3:
                out.append(run)
        return out


def reshape_ground(land, dikes):
    """Lets the paddies down to the fields' mud (a soft bank off the raised ground),
    with a ridge under each dike, and makes the walking collider follow the terrain."""
    g = bpy.data.objects["ground"]
    me = g.data
    if "countryside_orig" not in me.attributes:
        orig = me.attributes.new("countryside_orig", "FLOAT", "POINT")
        orig.data.foreach_set("value", np.array([v.co.z for v in me.vertices], dtype=np.float32))
    orig = np.empty(len(me.vertices), dtype=np.float32)
    me.attributes["countryside_orig"].data.foreach_get("value", orig)
    for v, z0 in zip(me.vertices, orig):
        x, y = v.co.x, v.co.y
        d = land.distance(x, y)
        if d <= 0.05:
            v.co.z = float(z0)
            continue
        t = smooth(0.3, 2.4, d)
        floor = FLOOR + 0.02 * math.sin(x * 0.7 + y * 0.4) + 0.012 * math.sin(x * 2.3 - y * 1.7)
        z = z0 * (1 - t) + floor * t
        dd = dikes.distance(x, y)
        if d > 1.6 and dd < 1.1:
            z = max(z, WATER + 0.1 - 0.42 * max(0.0, dd - 0.25))
        v.co.z = z
    me.update()
    # The collider: the terrain itself (Sora wades on the mud), not a flat box at 0.
    col = bpy.data.objects.get("col_ground")
    if col is not None:
        cme = me.copy()
        cme.name = "col_ground"
        cme.materials.clear()
        old = col.data
        col.data = cme
        col.matrix_world = g.matrix_world.copy()
        if old.users == 0:
            bpy.data.meshes.remove(old)
        col["surface"] = "mud"


def water_and_wading(coll, land):
    """One water surface over every paddy, its edge where it meets the banks, and a
    wading collider 2 cm above the mud under it (footsteps there are water)."""
    g = bpy.data.objects["ground"]
    gm = g.data
    nx, ny = land.nx, land.ny
    zs = np.zeros((ny, nx), dtype=np.float32)
    for v in gm.vertices:
        i, j = int(round(v.co.x - X0)), int(round(v.co.y - Y0))
        if 0 <= i < nx and 0 <= j < ny:
            zs[j, i] = v.co.z
    for name in ("flood_water", "paddy_water", "col_paddy_wading"):
        o = bpy.data.objects.get(name)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    wv, wf, cv, cf = [], [], [], []
    wid, cid = {}, {}

    def vid(table, verts, i, j, z):
        key = (i, j)
        if key not in table:
            table[key] = len(verts)
            verts.append((X0 + i, Y0 + j, z))
        return table[key]

    for j in range(ny - 1):
        for i in range(nx - 1):
            corners = (zs[j, i], zs[j, i + 1], zs[j + 1, i + 1], zs[j + 1, i])
            if land.distance(X0 + i + 0.5, Y0 + j + 0.5) < 0.3:
                continue        # a dip in the raised ground stays dry
            if min(corners) < WATER - 0.004:
                q = [vid(wid, wv, i + a, j + b, WATER) for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
                wf.append(q)
            if max(corners) < WATER - 0.12:
                q = [vid(cid, cv, i + a, j + b, float(zs[j + b, i + a]) + 0.02) for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
                cf.append(q)
    flood = bpy.data.materials.get("M_flood_water")
    wme = bpy.data.meshes.new("paddy_water")
    wme.from_pydata(wv, [], wf)
    uv = wme.uv_layers.new(name="UVMap")
    for poly in wme.polygons:
        for li in poly.loop_indices:
            co = wv[wme.loops[li].vertex_index]
            uv.data[li].uv = (co[0] / 4.0, co[1] / 4.0)
    wme.materials.append(flood)
    water = bpy.data.objects.new("paddy_water", wme)
    coll.objects.link(water)
    cme = bpy.data.meshes.new("col_paddy_wading")
    cme.from_pydata(cv, [], cf)
    col = bpy.data.objects.new("col_paddy_wading", cme)
    coll.objects.link(col)
    col["surface"] = "water"
    col.display_type = "WIRE"
    col.hide_render = True
    return water, col


def dike_meshes(coll, dikes, mud):
    """Each run of dike as a crowned earth bank, its foot in the mud."""
    out = []
    profile = [(-0.8, FLOOR - 0.03), (-0.45, WATER + 0.0), (-0.24, WATER + 0.12), (0.0, WATER + 0.16),
               (0.24, WATER + 0.12), (0.45, WATER + 0.0), (0.8, FLOOR - 0.03)]
    for k, run in enumerate(dikes.segments()):
        verts, faces, uvs = [], [], []
        m = len(profile)
        for i, (x, y) in enumerate(run):
            a = run[max(i - 1, 0)]
            b = run[min(i + 1, len(run) - 1)]
            along = Vector((b[0] - a[0], b[1] - a[1], 0)).normalized()
            side = Vector((-along.y, along.x, 0))
            sag = 0.025 * math.sin(i * 0.37 + k)
            for s, z in profile:
                w = s * (1 + 0.12 * math.sin(i * 0.9 + s * 3))
                p = Vector((x, y, 0)) + side * w
                verts.append((p.x, p.y, z - (sag if abs(s) < 0.3 else 0)))
                uvs.append((p.x / 2.0, p.y / 2.0))
        for i in range(len(run) - 1):
            for j in range(m - 1):
                c = i * m + j
                faces.append((c + m, c + m + 1, c + 1, c))
        me = bpy.data.meshes.new(f"paddy_dike_{k}")
        me.from_pydata(verts, [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            poly.use_smooth = True
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(mud)
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
        out.append(obj)
    return out


def clear_paddies(land, keep):
    """Every plant, log and scrap of litter standing where the fields now are goes, and
    every big tree but the few kept."""
    gone = []
    for name in [o.name for o in bpy.data.objects]:
        o = bpy.data.objects.get(name)      # an earlier step may have removed it (a collider)
        if o is None or o.type != "MESH" or not o.users_collection \
                or o.users_collection[0].name in ("_protos", "nature_templates"):
            continue
        if not PLANTS.match(o.name) and not o.name.endswith("_n") and not re.match(r"puddle_\d+$", o.name):
            continue
        if o.name in keep:
            continue
        col = bpy.data.objects.get(f"col_{o.name}")
        if col:
            x, y = col.location.x, col.location.y
        elif o.get("foot_origin"):
            x, y = o.location.x, o.location.y
        else:
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            x, y = sum(p.x for p in bb) / 8, sum(p.y for p in bb) / 8
        big = re.match(r"^(tree|dead|island_tree)", o.name)
        if land.distance(x, y) > 0.6 or big:
            gone.append(o.name)
            if col:
                bpy.data.objects.remove(col, do_unlink=True)
            bpy.data.objects.remove(o, do_unlink=True)
    return gone


def keepers(path_distance):
    """The big trees kept: none but the shrine's banyan, which `build` keeps by name (the
    user, Nov 19: big trees only at the Neak Ta shrine and the stupas). The old omen
    trees by the path, the shade trees by the fences and the west yard's hero tree go;
    the omens' thread is wound round the road's palms instead."""
    return set()


def rice(coll, land, dikes, rng, atlases, spacing=0.34, cells=4, width=0.62, height=1.24):
    """Every flooded plot planted hill by hill (rice_field.render_hills cards), green at
    grain filling in most, ripe and golden in some, a few left fallow under water."""
    crops = {}
    meshes = {}
    for j in range(land.ny - 1):
        for i in range(land.nx - 1):
            x0, y0 = X0 + i, Y0 + j
            if not land.paddy(x0 + 0.5, y0 + 0.5, 2.0):
                continue
            plot = dikes.plot(x0 + 0.5, y0 + 0.5)
            if plot not in crops:
                h = (plot[0] * 73856093 ^ plot[1] * 19349663) % 100
                # Golden either side of the road in (the look the user chose), green
                # at grain filling further out, a few plots fallow under water.
                by_road = abs(x0 + 0.5) < 22 and -62 < y0 < -2
                crops[plot] = "ripe" if by_road and h >= 6 else "fallow" if h < 6 else "ripe" if h < 34 else "green"
            crop = crops[plot]
            if crop == "fallow":
                continue
            y = y0 + rng.uniform(0.02, spacing)
            while y < y0 + 1:
                x = x0 + rng.uniform(0.02, spacing)
                while x < x0 + 1:
                    if dikes.distance(x, y) > 0.62 and land.distance(x, y) > 2.0 and rng.random() > 0.04:
                        k = rng.uniform(0.86, 1.1)
                        key = (int((x - X0) // 16), int((y - Y0) // 16), crop)
                        meshes.setdefault(key, []).append((x + rng.normal(0, 0.03), y + rng.normal(0, 0.03), k,
                                                           int(rng.integers(cells)), rng.uniform(0, math.pi),
                                                           (rng.normal(0, 0.06), rng.normal(0, 0.06))))
                    x += spacing
                y += spacing
    out = []
    for (i, j, crop), hills in meshes.items():
        verts, faces, uvs, normals = [], [], [], []
        for hx, hy, k, cell, yaw, lean in hills:
            u0, u1 = cell / cells, (cell + 1) / cells
            for turn in (0.0, math.pi / 2):
                a = yaw + turn
                ax = Vector((math.cos(a), math.sin(a), 0)) * (width * k / 2)
                up = Vector((lean[0], lean[1], 1)).normalized() * (height * k)
                base = Vector((hx, hy, WATER - 0.12))
                b = len(verts)
                verts += [base - ax, base + ax, base + ax + up, base - ax + up]
                faces.append((b, b + 1, b + 2, b + 3))
                uvs += [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
                for t, sx in ((0, -1), (0, 1), (1, 1), (1, -1)):
                    normals.append((Vector((0, 0, 0.45 + 0.5 * t)) + ax.normalized() * 0.45 * sx).normalized())
        me = bpy.data.meshes.new(f"paddy_rice_{crop}_{i}_{j}")
        me.from_pydata([v[:] for v in verts], [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(atlases[crop])
        me.normals_split_custom_set([normals[me.loops[li].vertex_index][:] for li in range(len(me.loops))])
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
        out.append(obj)
    return out


def palms_over_fields(coll, land, dikes, ground, rng, n=56):
    """Sugar palms standing over the paddies, singly or in pairs on the dikes and plot
    corners, far apart, as they do across the Khmer plains; a few by the compound."""
    lod0, lod1, lod2 = VN.flora()["sugar_palm"]
    spots = []
    for x0, s in dikes.xs:
        for y0, t in dikes.ys:
            if rng.random() < 0.55:
                spots.append((dikes.line_x(x0, s, y0), dikes.line_y(y0, t, dikes.line_x(x0, s, y0))))
    for _ in range(600):
        x, y = rng.uniform(X0 + 2, X1 - 2), rng.uniform(Y0 + 2, Y1 - 2)
        if dikes.distance(x, y) < 0.15 and land.paddy(x, y, 1.6):
            spots.append((x, y))
    rng.shuffle(spots)
    taken, out = [], []
    for x, y in spots:
        if len(out) >= n or not land.paddy(x, y, 1.6) or dikes.distance(x, y) > 0.3:
            continue
        near = [math.hypot(x - a, y - b) for a, b in taken]
        if any(d < 3.0 for d in near) or sum(d < 9 for d in near) > 1:
            continue
        taken.append((x, y))
        hot = math.hypot(x, y + 30) < 40
        src = lod0 if hot and len(out) % 3 == 0 else lod1
        k = len(out)
        obj = VN.place(coll, src, f"palm_field_{k}", x, y, WATER + 0.11, rng.uniform(0, math.tau),
                       rng.uniform(0.95, 1.4), (rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06)))
        me = bpy.data.meshes.new(f"col_palm_field_{k}")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        bm.to_mesh(me)
        bm.free()
        col = bpy.data.objects.new(me.name, me)
        coll.objects.link(col)
        col.location = (x, y, WATER + 1.6)
        col.scale = (0.5, 0.5, 3.0)
        col.display_type = "WIRE"
        col.hide_render = True
        col["surface"] = "mud"
        out.append(obj)
    return out


def farmstead_plants(coll, land, ground, rng, path_distance, in_yard):
    """Bananas where a household keeps them (round the fence, on the mounds beside the
    path, by the wells and the old pond, along the lanes), and the tree line of bananas
    and sugar palms along the walls."""
    f = VN.flora()
    boxes = VN.obstacles()
    placed = [(o.location.x, o.location.y) for o in bpy.data.objects
              if re.match(r"(banana|bamboo|palm)", o.name) and o.users_collection
              and o.users_collection[0].name not in ("_protos", "nature_templates")]

    def free(x, y, r):
        # A banana's leaves reach 2.5 m out: its foot stays well off the road.
        if path_distance(x, y) < ROAD_HALF + 1.2 + 1.3 * r or in_yard(x, y, 0.6) or L.lane_distance(x, y) < 1.4:
            return False
        if any(a - r < x < b + r and c - r < y < d + r for a, b, c, d in boxes):
            return False
        return all(math.hypot(x - a, y - b) > r + 2.2 for a, b in placed)

    out = []

    def put(src_key, x, y, scale, near_lod=True):
        lod0, lod1, lod2 = f[src_key]
        src = lod0 if near_lod and (path_distance(x, y) < 10 or in_yard(x, y, 6)) else lod1
        obj = VN.place(coll, src, f"{src_key.split('_')[0]}_c{len(out)}", x, y,
                       VN.ground_under(ground, x, y, 1.0) - 0.04, rng.uniform(0, math.tau), scale)
        placed.append((x, y))
        out.append(obj)

    for _ in range(5000):                                # bananas round the farmstead
        if len(out) >= 70:
            break
        x, y = rng.uniform(X0 + 4, X1 - 4), rng.uniform(Y0 + 4, Y1 - 4)
        if land.distance(x, y) > 0 or not free(x, y, 1.6):
            continue
        near_home = in_yard(x, y, 12) or path_distance(x, y) < 6 or any(L.ellipse_value(x, y, e) < 1.3 for e in L.CLEARINGS)
        if not near_home and rng.random() > 0.15:
            continue
        put("banana_clump", x, y, rng.uniform(0.55, 0.85))
    # The tree line along the walls: bananas and sugar palms, close set.
    edge = []
    for t in np.arange(0, 1, 1 / 70):
        for side in range(4):
            if side == 0:
                x, y = PLAY[0] + 1.6, PLAY[2] + t * (PLAY[3] - PLAY[2])
            elif side == 1:
                x, y = PLAY[1] - 1.6, PLAY[2] + t * (PLAY[3] - PLAY[2])
            elif side == 2:
                x, y = PLAY[0] + t * (PLAY[1] - PLAY[0]), PLAY[2] + 1.6
            else:
                x, y = PLAY[0] + t * (PLAY[1] - PLAY[0]), PLAY[3] - 1.6
            edge.append((x + rng.normal(0, 0.8), y + rng.normal(0, 0.8)))
    for x, y in edge:
        if not free(x, y, 1.2) or -66 < y < -58.6:
            continue
        u = rng.random()
        key = "banana_clump" if u < 0.6 else "sugar_palm"
        lod0, lod1, lod2 = f[key]
        obj = VN.place(coll, lod2 if key != "sugar_palm" else lod1, f"{key.split('_')[0]}_e{len(out)}", x, y,
                       VN.ground_under(ground, x, y, 1.0) - 0.04, rng.uniform(0, math.tau),
                       rng.uniform(0.8, 1.1) if key != "banana_clump" else rng.uniform(0.6, 0.85))
        placed.append((x, y))
        out.append(obj)
    return out


def trunk_collider(coll, name, x, y, z, r, h, surface="leaves"):
    """A box round a trunk, as the village's palms and trees have (`surface` is what a
    footstep on it sounds like: physics.ts Surface)."""
    old = bpy.data.meshes.get(name)         # a previous run's, its object already gone
    if old is not None and old.users == 0:
        bpy.data.meshes.remove(old)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bm.to_mesh(me)
    bm.free()
    col = bpy.data.objects.new(name, me)
    coll.objects.link(col)
    col.location = (x, y, z + h / 2)
    col.scale = (2 * r, 2 * r, h)
    col.display_type = "WIRE"
    col.hide_render = True
    col["surface"] = surface
    return col


def road_palms(coll, ground, rng):
    """The sugar palms along the road's two shoulders, full detail: the first thing Sora
    walks between, tall over the ripe fields. Each its own height and lean."""
    # The lighter LOD: thirteen palms at full detail cost 0.9 M triangles in view.
    lod1 = VN.flora()["sugar_palm"][1]
    out = []
    for k, (x, y) in enumerate(ROAD_PALMS):
        x += rng.normal(0, 0.12)
        y += rng.normal(0, 0.5)
        z = VN.ground_under(ground, x, y, 0.5) - 0.05
        lean = (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05))
        obj = VN.place(coll, lod1, f"palm_road_{k}", x, y, z, rng.uniform(0, math.tau), rng.uniform(1.0, 1.3), lean)
        trunk_collider(coll, f"col_palm_road_{k}", x, y, z, 0.28, 3.2)
        out.append(obj)
    return out


def stand_scarecrows():
    """The scarecrows to their places along the road and out in its fields (SCARECROWS),
    two more made from the first if the file has only five. Their height is set once the
    fields are dug (`settle_scarecrows`)."""
    first = bpy.data.objects["tingmong_0"]
    first_col = bpy.data.objects["col_tingmong_0"]
    for k, (x, y, front) in enumerate(SCARECROWS):
        o = bpy.data.objects.get(f"tingmong_{k}")
        col = bpy.data.objects.get(f"col_tingmong_{k}")
        if o is None:
            o = first.copy()
            o.data = first.data.copy()
            o.name = f"tingmong_{k}"
            first.users_collection[0].objects.link(o)
        if col is None:
            col = first_col.copy()
            col.name = f"col_tingmong_{k}"
            first_col.users_collection[0].objects.link(col)
        o.location = (x, y, o.location.z)
        o.rotation_euler = (0, 0, 0)
        o["front"] = front
        col.location = (x, y, col.location.z)


def settle_scarecrows(ground):
    """Each scarecrow's stake down in the ground under it (in a field, the mud)."""
    for k in range(len(SCARECROWS)):
        o = bpy.data.objects[f"tingmong_{k}"]
        col = bpy.data.objects[f"col_tingmong_{k}"]
        z = ground(o.location.x, o.location.y)
        col.location.z += z - o.location.z
        o.location.z = z


ORPHAN_COLLIDERS = re.compile(r"^col_(dead_\d+|dead_tree_trunk[\w.]*|hero_tree_\d+|rock_moss_set_01[\w.]*|"
                              r"root_cluster_01[\w.]*|tree_stump_01[\w.]*)$")


def remove_orphan_colliders():
    """Trunk, rock and root colliders whose tree, rock or root an earlier pass took away:
    invisible walls standing out in the fields."""
    names = {o.name for o in bpy.data.objects if not o.name.startswith("col_")}
    gone = []
    for o in [o for o in bpy.data.objects if ORPHAN_COLLIDERS.match(o.name)]:
        base = o.name[4:]
        if base in names or any(n.startswith((base + "_", base + ".")) for n in names):
            continue
        gone.append(o.name)
        bpy.data.objects.remove(o, do_unlink=True)
    return gone


def remove_termite_mounds():
    """The north garden's termite mounds and the offerings on them (the user asked for
    the mounds gone, Nov 19)."""
    gone = [o.name for o in bpy.data.objects if re.match(r"^(col_)?ng_termite", o.name)]
    for name in gone:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    return len(gone)


def refresh_bananas():
    """Banana clumps an earlier pass placed (and no step now replaces) still carry the
    old clump's mesh: give each the new clump at the matching detail."""
    lod0, lod1, lod2 = VN.flora()["banana_clump"]
    current = {lod0.data, lod1.data, lod2.data}
    done = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or o.get("flora") != "banana_clump" or o.data in current or not o.users_collection \
                or o.users_collection[0].name in ("_protos", "nature_templates"):
            continue
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        o.data = (lod0 if tris > 15000 else lod1 if tris > 2500 else lod2).data
        done += 1
    return done


def clear_road(path_distance):
    """No banana clump within reach of the road: their leaves would hang over it."""
    gone = []
    # By what it is, not its name: old palms that became banana clumps keep theirs.
    for o in [o for o in bpy.data.objects if o.get("flora") == "banana_clump" and o.users_collection
              and o.users_collection[0].name not in ("_protos", "nature_templates")]:
        x, y = o.location.x, o.location.y
        if -62 < y < -2 and path_distance(x, y) < 5.2:
            gone.append(o.name)
            col = bpy.data.objects.get(f"col_{o.name}")
            if col:
                bpy.data.objects.remove(col, do_unlink=True)
            bpy.data.objects.remove(o, do_unlink=True)
    return gone


def stupa_banyan(coll, ground):
    """A banyan over the stupas, the shrine's banyan's twin in another turn and size."""
    src = VN.flora()["forest_banyan"][0]
    x, y = STUPA_BANYAN
    z = VN.ground_under(ground, x, y, 1.2) - 0.05
    obj = VN.place(coll, src, "tree_stupa_banyan", x, y, z, 2.3, 0.92)
    trunk_collider(coll, "col_tree_stupa_banyan", x, y, z, 1.5, 6.0)
    return obj


def back_grove(coll, land, ground, rng, path_distance, in_yard):
    """Behind the house, to the walls: sugar palms over a close-set banana grove crowding every gap
    between them, the lane to the garden and the garden's clearing left open, nothing in
    a building's footprint. Near the house full detail, deeper in the lighter LOD."""
    f = VN.flora()
    boxes = VN.obstacles()
    x0, x1, y0, y1 = BACK_GROVE
    placed = [(o.location.x, o.location.y) for o in bpy.data.objects
              if re.match(r"(banana|bamboo|palm)", o.name) and o.users_collection
              and o.users_collection[0].name not in ("_protos", "nature_templates")]

    def open_ground(x, y, r):
        if in_yard(x, y, 0.8) or L.lane_distance(x, y) < 1.6 + r * 0.4 or path_distance(x, y) < ROAD_HALF + 1:
            return False
        if any(L.ellipse_value(x, y, e) < 1.05 for e in L.CLEARINGS):
            return False
        if math.hypot(x - STUPA_BANYAN[0], y - STUPA_BANYAN[1]) < 3.5:
            return False
        return not any(a - r < x < b + r and c - r < y < d + r for a, b, c, d in boxes)

    out = []
    for key, n, gap, scale in (("sugar_palm", 26, 4.2, (0.85, 1.2)), ("banana_clump", 150, 1.75, (0.6, 0.92))):
        lod0, lod1, lod2 = f[key]
        made = 0
        for _ in range(9000):
            if made >= n:
                break
            x, y = rng.uniform(x0 + 1, x1 - 1), rng.uniform(y0 + 0.5, y1 - 0.6)
            if not open_ground(x, y, 1.0 if key == "banana_clump" else 0.6):
                continue
            if any(math.hypot(x - a, y - b) < gap for a, b in placed):
                continue
            near = in_yard(x, y, 3.5) or L.lane_distance(x, y) < 2.5
            src = lod0 if near else lod1
            obj = VN.place(coll, src, f"{key.split('_')[0]}_b{len(out)}", x, y,
                           VN.ground_under(ground, x, y, 1.0) - 0.04, rng.uniform(0, math.tau),
                           rng.uniform(*scale))
            placed.append((x, y))
            out.append(obj)
            made += 1
    return out


def build(own, area, rng, path_distance, in_yard, ground_cls, hills, mud):
    """The whole countryside pass. Returns counts for the log."""
    orphans = remove_orphan_colliders()
    keep = keepers(path_distance)
    land = Land(path_distance, in_yard, [])
    dikes = Dikes(land, rng)
    gone = clear_paddies(land, keep | {"banyan"})
    for o in list(own.objects):         # the earlier pass's fields and palms are redrawn here
        if o.name.startswith(("paddy_rice_", "paddy_bund_", "palm_field_", "col_palm_field_")):
            bpy.data.objects.remove(o, do_unlink=True)
    mounds = remove_termite_mounds()
    reshape_ground(land, dikes)
    ground = ground_cls()
    settle_scarecrows(ground)
    water, wading = water_and_wading(own, land)
    banks = dike_meshes(own, dikes, mud)
    VN.bund_grass(own, banks, rng)
    crop = rice(own, land, dikes, rng, hills)
    road = road_palms(own, ground, rng)
    stupa_banyan(own, ground)
    palms = palms_over_fields(own, land, dikes, ground, rng, n=84)
    grove = back_grove(own, land, ground, rng, path_distance, in_yard)
    plants = farmstead_plants(own, land, ground, rng, path_distance, in_yard)
    refreshed = refresh_bananas()
    off_road = clear_road(path_distance)
    return {"bananas refreshed": refreshed, "bananas off the road": len(off_road), "removed": len(gone), "orphan colliders": len(orphans), "termite": mounds, "dikes": len(banks), "rice": len(crop), "road palms": len(road),
            "palms": len(palms), "back grove": len(grove), "plants": len(plants), "water": len(water.data.polygons)}
