"""Episode 1's tight compound (November 20, 2026 redesign): the play area shrinks to the
family's yard and the lane up to it, closed in by a weathered timber fence, with a
wall of old trees and the mist past it. Views end within 20 to 30 m.

    road ─ gate (y -40) ─ fenced lane (x ±4) ─ yard fence (y -3) ─ house ─ back fence

The paddies stay only in the two pockets either side of the lane, seen between its
rails. The Neak Ta's banyan stands by the gate; a side path through the lane's east
fence leads to the Preah Phum (saveShrine.ts).

Blender axes: X east, Y north, Z up; Babylon x = -x, z = -y. Run inside Blender.
"""
import math
import re

import bpy
from mathutils import Vector

import rural_kit as RK
import village_nature as VN
from shrine_craft import Batch

# The outer fence (Blender x0, x1, y0, y1) and the gate's half width.
OUTER = (-16.0, 20.0, -40.0, 36.0)
GATE_HALF = 1.9
# The lane between its fences, from the gate to the yard's front fence (fence_s, y -3).
LANE_X = 4.0
LANE_Y = (-40.0, -3.4)
# Openings in the lane's fences: the Neak Ta's banyan by the gate (west) and the side
# path to the Preah Phum (east; SAVE_SHRINE_ROUTE turns off the lane at y -10.5).
LANE_OPEN = {"w": [(-39.6, -31.0)], "e": [(-12.0, -9.0)]}
PREAH_PHUM = (15.2, -10.5)

# What the redesign takes out: the road's and the fields' sugar palms (their scanned
# trunks read as spikes up close), the bamboo the user retired, the old banyan by the
# stupas, the scarecrows out in the far fields, and everything past the outer fence.
RETIRE = re.compile(
    r"^(palm_road_|palm_field_|palm_\d|sugar_[a-z]_|coco|bamboo_clump_\d|tree_stupa_banyan|"
    r"tingmong_[0-3]$|tingmong_6$|ring_p|fence_(n|s|e|w)(_back)?_\d)"
)
# Kept wherever they are: the ground, the paddies' water, the sky.
KEEP = re.compile(r"^(ground|col_ground|paddy_water|sky|night_sky|storm_sky)")


def outside(obj, margin=1.0):
    """True when the object's middle lies past the outer fence."""
    if obj.type not in ("MESH", "CURVE"):
        return False
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    cx = sum(p.x for p in pts) / 8
    cy = sum(p.y for p in pts) / 8
    x0, x1, y0, y1 = OUTER
    return not (x0 - margin <= cx <= x1 + margin and y0 - margin <= cy <= y1 + margin)


def retired(protected=("_protos", "nature_templates")):
    """The objects the compound no longer has."""
    out = []
    for obj in bpy.data.objects:
        if any(c.name in protected for c in obj.users_collection):
            continue
        if KEEP.match(obj.name):
            continue
        if RETIRE.match(obj.name) or outside(obj):
            out.append(obj)
    return out


# ------------------------------------------------------------------ fences


def _fence_run(b, m, ground, rng, a, c, height, bay, panels, rails=(0.32, 0.78), open_spans=()):
    """Posts every `bay` metres from a to c (2D), rails between them, and plank
    panels on a share (`panels`) of the bays, some with boards missing."""
    a, c = Vector((*a, 0)), Vector((*c, 0))
    run = c - a
    length = run.length
    along = run.normalized()
    n = max(1, round(length / bay))
    posts = [a + run * (i / n) for i in range(n + 1)]

    def is_open(p):
        s = p.y if abs(along.y) > abs(along.x) else p.x
        return any(lo <= s <= hi for lo, hi in open_spans)

    for i, p in enumerate(posts):
        if is_open(p) and (i == 0 or is_open(posts[i - 1])) and (i == n or is_open(posts[i + 1])):
            continue
        z = ground(p.x, p.y)
        lean = Vector((rng.normal(0, 0.018), rng.normal(0, 0.018), 0))
        top = p + Vector((0, 0, z + height + rng.uniform(-0.06, 0.08))) + lean
        RK.timber(b, m["hewn"], p + Vector((0, 0, z - 0.35)), top, 0.11, 0.1, rng, jitter=0.006)
    for i in range(n):
        p0, p1 = posts[i], posts[i + 1]
        mid = (p0 + p1) / 2
        if is_open(mid):
            continue
        z0, z1 = ground(p0.x, p0.y), ground(p1.x, p1.y)
        side = Vector((-along.y, along.x, 0)) * 0.07
        for r in rails:
            if rng.random() < 0.06:
                continue  # a rail rotted through and fell
            sag = rng.uniform(0.0, 0.03)
            RK.timber(b, m["planks"], p0 + side + Vector((0, 0, z0 + r * height)),
                      p1 + side + Vector((0, 0, z1 + r * height - sag)), 0.07, 0.035, rng)
        if rng.random() < panels:
            _boards(b, m, ground, rng, p0, p1, along, side, height)


def _boards(b, m, ground, rng, p0, p1, along, side, height):
    """One bay of hand-sawn boards nailed to the rails: each its own width and height,
    silvered by sun and rain, green-black where the wet ground wicks up into it; one
    leaning loose on a nail, a run of them gone where something pushed through."""
    normal = Vector((-along.y, along.x, 0))
    length = (p1 - p0).length
    hole = sorted(rng.uniform(0.1, 0.9, 2)) if rng.random() < 0.28 else None
    t = 0.0
    while t < length - 0.05:
        w = rng.uniform(0.11, 0.21)
        mid = min(t + w / 2, length - 0.03)
        t += w + rng.uniform(0.004, 0.03)
        if hole and hole[0] * length < mid < hole[1] * length:
            continue
        if rng.random() < 0.05:
            continue
        thick = rng.uniform(0.016, 0.026)
        # Nailed flat to the rails' outer face (rails: 0.07 out, 0.035 deep), its foot
        # pushed into the mud so nothing stands proud of the ground.
        foot = p0 + along * mid + normal * (0.07 + 0.0175 + thick / 2 - 0.002)
        z = min(ground(foot.x + along.x * dx, foot.y + along.y * dx) for dx in (-w / 2, 0.0, w / 2)) - rng.uniform(0.03, 0.07)
        top = z + 0.05 + height * rng.uniform(0.84, 0.98)
        lean = Vector((0, 0, 0))
        if rng.random() < 0.05:
            lean = along * rng.choice((-1, 1)) * rng.uniform(0.12, 0.3)
        lean += normal * rng.normal(0, 0.012)
        r = rng.random()
        mat = m["moss_wood"] if r < 0.12 else m["boards"] if r < 0.35 else m["planks"]
        RK.timber(b, mat, foot + Vector((0, 0, z)), foot + lean + Vector((0, 0, top)), w, thick,
                  rng, chamfer=0.004, jitter=0.002, up=normal)


def fences(coll, ground, rng):
    """The outer fence with its gate, and the lane's two fences."""
    m = dict(RK.materials())
    m["moss_wood"] = RK._lib("moss_wood", "moss_wood", tint=(.8, .82, .78), tile=1.0)
    b = Batch("compound_fence")
    x0, x1, y0, y1 = OUTER
    tall, bay = 1.9, 2.1
    # Front: road side, either side of the gate.
    _fence_run(b, m, ground, rng, (x0, y0), (-GATE_HALF, y0), tall, bay, 0.9)
    _fence_run(b, m, ground, rng, (GATE_HALF, y0), (x1, y0), tall, bay, 0.9)
    # Sides and back: closed, old, a board gone here and there.
    _fence_run(b, m, ground, rng, (x0, y0), (x0, y1), tall, bay, 0.92)
    _fence_run(b, m, ground, rng, (x1, y0), (x1, y1), tall, bay, 0.92)
    _fence_run(b, m, ground, rng, (x0, y1), (x1, y1), tall, bay, 0.92)
    # The lane: low post-and-rail; boards on a few bays only, so the paddies show.
    low = 1.2
    _fence_run(b, m, ground, rng, (-LANE_X, LANE_Y[0]), (-LANE_X, LANE_Y[1]), low, 2.4, 0.3,
               open_spans=LANE_OPEN["w"])
    _fence_run(b, m, ground, rng, (LANE_X, LANE_Y[0]), (LANE_X, LANE_Y[1]), low, 2.4, 0.3,
               open_spans=LANE_OPEN["e"])
    # The gate: two round logs and a beam across them, its doors long gone.
    for sx in (-1, 1):
        p = Vector((sx * (GATE_HALF + 0.1), y0, 0))
        z = ground(p.x, p.y)
        RK.log(b, m["bark"], p + Vector((0, 0, z - 0.5)), p + Vector((0, 0, z + 2.75)), 0.15, 0.13, rng)
    zg = ground(0, y0)
    RK.timber(b, m["hewn"], Vector((-GATE_HALF - 0.55, y0, zg + 2.55)), Vector((GATE_HALF + 0.55, y0, zg + 2.6)),
              0.16, 0.14, rng)
    return b.build(coll)


# ------------------------------------------------------------------ the tree wall


def tree_wall(coll, ground, rng, f, depth=(1.5, 16.0), spacing=3.0):
    """Old trees packed outside the fence: broadleaf giants and bananas close in,
    a few sugar palms far back where the mist only shows their crowns."""
    x0, x1, y0, y1 = OUTER
    lo, hi = depth
    placed = []
    gx = math.floor((x0 - hi) / spacing)
    for i in range(gx, math.ceil((x1 + hi) / spacing) + 1):
        for j in range(math.floor((y0 - hi) / spacing), math.ceil((y1 + hi) / spacing) + 1):
            x = i * spacing + rng.uniform(-1.2, 1.2)
            y = j * spacing + rng.uniform(-1.2, 1.2)
            d = max(x0 - x, x - x1, y0 - y, y - y1)
            if not (lo <= d <= hi):
                continue
            # The road runs on out of the gate, into the mist.
            if y < y0 and abs(x) < 4.2:
                continue
            u = rng.random()
            if d > 8 and u < 0.16:
                key, s = "sugar_palm", rng.uniform(0.85, 1.15)
            elif u < 0.62:
                key, s = "forest_tree_gn", rng.uniform(0.7, 1.25)
            elif u < 0.93:
                key, s = "banana_clump", rng.uniform(0.85, 1.25)
            else:
                key, s = "dead", rng.uniform(0.8, 1.1)
            # The scans' lighter versions: the nearest trees stand 6 m or more from
            # anywhere Sora can walk, the far ones are shapes in the mist.
            src = f[key][1] if d < 7 and key != "sugar_palm" else f[key][2]
            z = VN.ground_under(ground, x, y, 0.6)
            placed.append(VN.place(coll, src, f"treewall_{key}", x, y, z, rng.uniform(0, math.tau), s))
    return placed


# ------------------------------------------------------------------ the lane's ground


def _tex(nodes, path, non_color):
    t = nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    if non_color:
        t.image.colorspace_settings.name = "Non-Color"
    return t


def lane_material(name="M_cp_lane", keys=(("red_dirt_mud_01", 1.5), ("muddy_tracks", 2.25)), edge=(3.15, 2.55)):
    """Wet red laterite with cart ruts, rain standing in the low spots, its edges
    feathered into the verge. (Cycles preview look; the game blends the same maps.)"""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = nodes["Principled BSDF"]
    lib = VN.LIB + "/materials/"
    uv = nodes.new("ShaderNodeUVMap")
    sets = {}
    for key, tile in keys:
        mapping = nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1)
        links.new(uv.outputs["UV"], mapping.inputs["Vector"])
        maps = [_tex(nodes, f"{lib}{key}/{key}_{s}.jpg", s != "BC") for s in ("BC", "N", "ORM")]
        for t in maps:
            links.new(mapping.outputs["Vector"], t.inputs["Vector"])
        sets[key] = maps
    geo = nodes.new("ShaderNodeTexCoord")
    n1 = nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 0.18
    n1.inputs["Detail"].default_value = 3
    links.new(geo.outputs["Object"], n1.inputs["Vector"])
    blend = nodes.new("ShaderNodeMapRange")
    blend.inputs["From Min"].default_value = 0.5
    blend.inputs["From Max"].default_value = 0.68
    links.new(n1.outputs["Fac"], blend.inputs["Value"])

    def mix(kind, a, b, fac):
        m = nodes.new("ShaderNodeMix")
        m.data_type = kind
        links.new(fac, m.inputs["Factor"])
        ia, ib = (6, 7) if kind == "RGBA" else (2, 3) if kind == "FLOAT" else (4, 5)
        links.new(a, m.inputs[ia])
        links.new(b, m.inputs[ib])
        return m.outputs[2] if kind == "RGBA" else m.outputs[0] if kind == "FLOAT" else m.outputs[1]

    red, ruts = sets[keys[0][0]], sets[keys[1][0]]
    col = mix("RGBA", red[0].outputs["Color"], ruts[0].outputs["Color"], blend.outputs["Result"])
    orm = mix("RGBA", red[2].outputs["Color"], ruts[2].outputs["Color"], blend.outputs["Result"])
    nrm = mix("RGBA", red[1].outputs["Color"], ruts[1].outputs["Color"], blend.outputs["Result"])
    # Puddles: where a slow noise dips, the mud goes dark, smooth and flat.
    n2 = nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 0.55
    n2.inputs["Detail"].default_value = 6
    links.new(geo.outputs["Object"], n2.inputs["Vector"])
    pud = nodes.new("ShaderNodeMapRange")
    pud.inputs["From Min"].default_value = 0.32
    pud.inputs["From Max"].default_value = 0.28
    links.new(n2.outputs["Fac"], pud.inputs["Value"])
    dark = nodes.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    dark.blend_type = "MULTIPLY"
    dark.inputs[7].default_value = (0.3, 0.28, 0.26, 1)
    links.new(pud.outputs["Result"], dark.inputs["Factor"])
    links.new(col, dark.inputs[6])
    wet = nodes.new("ShaderNodeMix")
    wet.data_type = "RGBA"
    wet.blend_type = "MULTIPLY"
    wet.inputs["Factor"].default_value = 1.0
    wet.inputs[7].default_value = (0.62, 0.58, 0.55, 1)
    links.new(dark.outputs[2], wet.inputs[6])
    links.new(wet.outputs[2], bsdf.inputs["Base Color"])
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(orm, sep.inputs["Color"])
    # Matte mud (the scans' roughness pulled up): only the standing water shines.
    rough = nodes.new("ShaderNodeMath")
    rough.operation = "MULTIPLY_ADD"
    rough.inputs[1].default_value = 0.35
    rough.inputs[2].default_value = 0.62
    links.new(sep.outputs["Green"], rough.inputs[0])
    rmix = nodes.new("ShaderNodeMix")
    rmix.data_type = "FLOAT"
    rmix.inputs[3].default_value = 0.04
    links.new(pud.outputs["Result"], rmix.inputs["Factor"])
    links.new(rough.outputs[0], rmix.inputs[2])
    links.new(rmix.outputs[0], bsdf.inputs["Roughness"])
    nmap = nodes.new("ShaderNodeNormalMap")
    links.new(nrm, nmap.inputs["Color"])
    nstr = nodes.new("ShaderNodeMath")
    nstr.operation = "SUBTRACT"
    nstr.inputs[0].default_value = 1.0
    links.new(pud.outputs["Result"], nstr.inputs[1])
    links.new(nstr.outputs[0], nmap.inputs["Strength"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    # Feathered edge: |x| from the lane's middle, broken by noise.
    sx = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Object"], sx.inputs[0])
    ax = nodes.new("ShaderNodeMath")
    ax.operation = "ABSOLUTE"
    links.new(sx.outputs["X"], ax.inputs[0])
    n3 = nodes.new("ShaderNodeTexNoise")
    n3.inputs["Scale"].default_value = 1.2
    links.new(geo.outputs["Object"], n3.inputs["Vector"])
    jit = nodes.new("ShaderNodeMath")
    jit.operation = "MULTIPLY_ADD"
    jit.inputs[1].default_value = 0.9
    links.new(n3.outputs["Fac"], jit.inputs[0])
    links.new(ax.outputs[0], jit.inputs[2])
    if edge:
        fade = nodes.new("ShaderNodeMapRange")
        fade.inputs["From Min"].default_value = edge[0]
        fade.inputs["From Max"].default_value = edge[1]
        links.new(jit.outputs[0], fade.inputs["Value"])
        links.new(fade.outputs["Result"], bsdf.inputs["Alpha"])
    return mat


def lane_surface(coll, ground, y0=-47.0, y1=-2.6, half=3.4, step=0.25, name="cp_lane", mat=None):
    """The lane's mud as a skin 12 mm over the ground, from the road to the yard."""
    nx = int(2 * half / step)
    ny = int((y1 - y0) / step)
    verts, faces, uvs = [], [], []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        for i in range(nx + 1):
            x = -half + 2 * half * i / nx
            # 35 mm over the sampled ground: the game's triangulated, quantised ground
            # would poke through a thinner skin and show its litter as black blots.
            verts.append((x, y, ground(x, y) + 0.035))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    layer = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        v = verts[loop.vertex_index]
        layer.data[loop.index].uv = (v[0], v[1])
    mesh.materials.append(mat or lane_material())
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def yard_surface(coll, ground):
    """The swept yard before the house: trodden red earth gone to mud, leaves at its edges."""
    mat = lane_material("M_cp_yard", (("red_dirt_mud_01", 1.5), ("brown_mud_leaves_01", 2.0)), edge=None)
    return lane_surface(coll, ground, y0=-3.0, y1=9.6, half=12.8, step=0.3, name="cp_yard", mat=mat)


# The house's own fence (Blender x ±13, y -3..32), rebuilt like the compound's.
YARD = (-13.0, 13.0, -3.0, 32.0)
YARD_GATE = 1.6


def yard_fence(coll, ground, rng):
    m = dict(RK.materials())
    m["moss_wood"] = RK._lib("moss_wood", "moss_wood", tint=(.8, .82, .78), tile=1.0)
    b = Batch("compound_yard_fence")
    x0, x1, y0, y1 = YARD
    h = 1.45
    _fence_run(b, m, ground, rng, (x0, y0), (-YARD_GATE, y0), h, 2.0, 0.55)
    _fence_run(b, m, ground, rng, (YARD_GATE, y0), (x1, y0), h, 2.0, 0.55)
    _fence_run(b, m, ground, rng, (x0, y0), (x0, y1), h, 2.0, 0.7)
    _fence_run(b, m, ground, rng, (x1, y0), (x1, y1), h, 2.0, 0.7)
    _fence_run(b, m, ground, rng, (x0, y1), (x1, y1), h, 2.0, 0.7)
    return b.build(coll)


LANE_CLUTTER = re.compile(r"^(bark_debris|dry_branches|single_root|forest_leaves|leaf_litter|rock_moss|fern|weed_plant|shrub|"
                          r"periwinkle|calathea|anthurium|pachira|nettle|tree_stump|dead_tree_trunk|dead_\d|root_cluster|log_)")


def lane_clutter(half=5.0, y0=-48.0, y1=-2.0, yard=True):
    """Litter and weeds in the lane and the swept yard: they read as black blots on
    the mud, and no one would leave them where the mourners walk."""
    out = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not LANE_CLUTTER.match(obj.name):
            continue
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        cx, cy = sum(q.x for q in pts) / 8, sum(q.y for q in pts) / 8
        if (abs(cx) < half and y0 < cy < y1) or (yard and abs(cx) < 12.6 and -2.8 < cy < 9.4):
            out.append(obj)
    return out


def verges(coll, ground, rng, grass):
    """Tall grass at the feet of the fences and the gate posts, thick where no one walks."""
    x0, x1, y0, y1 = OUTER
    lines = [((-LANE_X, LANE_Y[0]), (-LANE_X, LANE_Y[1])), ((LANE_X, LANE_Y[0]), (LANE_X, LANE_Y[1])),
             ((x0, y0), (-GATE_HALF, y0)), ((GATE_HALF, y0), (x1, y0))]
    placed = 0
    for (ax, ay), (cx, cy) in lines:
        a, c = Vector((ax, ay)), Vector((cx, cy))
        n = int((c - a).length / 0.55)
        for k in range(n):
            p = a + (c - a) * (k / n)
            for side in (-1, 1):
                if rng.random() < 0.35:
                    continue
                off = side * rng.uniform(0.15, 0.75)
                x = p.x + (off if ax == cx else rng.normal(0, 0.1))
                y = p.y + (off if ay == cy else rng.normal(0, 0.1))
                if abs(x) < 2.7 and y < LANE_Y[1]:
                    continue
                VN.put(coll, grass[int(rng.integers(len(grass)))], x, y, ground, rng.uniform(0, math.tau),
                       rng.uniform(1.0, 1.9))
                placed += 1
    return placed


# ------------------------------------------------------------------ the Preah Phum's bund


PP_PATH = ((LANE_X - 0.4, PREAH_PHUM[1]), (PREAH_PHUM[0] - 1.6, PREAH_PHUM[1]))
PP_CLEARING = 2.6


def _in_pp_corridor(x, y, pad=0.0):
    (ax, ay), (cx, _) = PP_PATH
    if ax - pad <= x <= cx and abs(y - ay) <= 0.9 + pad:
        return True
    return math.hypot(x - PREAH_PHUM[0], y - PREAH_PHUM[1]) <= PP_CLEARING + pad


def preah_phum_bund(coll, ground, step=0.2):
    """A raised earth bund off the lane through the paddy to the Preah Phum's mound:
    flat-topped, its sides slumping into the water."""
    def height(x, y):
        (ax, ay), (cx, _) = PP_PATH
        dx = max(ax - x, 0.0, x - cx)
        d_path = math.hypot(dx, y - ay) - 0.8
        d_mound = math.hypot(x - PREAH_PHUM[0], y - PREAH_PHUM[1]) - PP_CLEARING
        d = min(d_path, d_mound)
        top = 0.06
        if d <= 0:
            return top
        return top - min(d / 0.7, 1.0) * 0.5

    x0, x1 = PP_PATH[0][0] - 0.2, PREAH_PHUM[0] + PP_CLEARING + 0.8
    y0, y1 = PREAH_PHUM[1] - PP_CLEARING - 0.8, PREAH_PHUM[1] + PP_CLEARING + 0.8
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x, y = x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny
            verts.append((x, y, max(height(x, y), ground(x, y) + 0.01) if _in_pp_corridor(x, y, 0.75) else ground(x, y) - 0.05))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            if all(_in_pp_corridor(*verts[k][:2], 0.75) for k in (a, a + 1, a + nx + 2, a + nx + 1)):
                faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    mesh = bpy.data.meshes.new("cp_pp_bund")
    mesh.from_pydata(verts, [], faces)
    mesh.validate()
    layer = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        v = verts[loop.vertex_index]
        layer.data[loop.index].uv = (v[0], v[1])
    mesh.materials.append(lane_material("M_cp_bund", (("red_dirt_mud_01", 1.5), ("brown_mud_leaves_01", 2.0)), edge=None))
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    obj = bpy.data.objects.new("cp_pp_bund", mesh)
    coll.objects.link(obj)
    return obj


def cut_rice(pattern=re.compile(r"^paddy_rice_")):
    """Takes the rice out where the bund and the mound now stand."""
    import bmesh
    n = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not pattern.match(obj.name):
            continue
        mw = obj.matrix_world
        pts = [mw @ Vector(c) for c in obj.bound_box]
        if max(p.x for p in pts) < PP_PATH[0][0] - 1 or min(p.y for p in pts) > PREAH_PHUM[1] + PP_CLEARING + 1 \
                or max(p.y for p in pts) < PREAH_PHUM[1] - PP_CLEARING - 1:
            continue
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        dead = [f for f in bm.faces if _in_pp_corridor(*(mw @ f.calc_center_median())[:2], 0.3)]
        if dead:
            bmesh.ops.delete(bm, geom=dead, context="FACES")
            bm.to_mesh(obj.data)
            n += len(dead)
        bm.free()
    return n


# ------------------------------------------------------------------ nothing floats

WALL_MOUNTED = re.compile(r"(frame|peg|hook|calendar|drawing|certificate|shelf|photo|print|rail|receipt|nail|mirror)", re.I)


def settle(region, keep=(), quiet=False):
    """Runs tools/areas/ground_audit.py over `region` (x0, y0, x1, y1) and fixes what
    floats: a loose thing drops onto what is under it; a thing hung on a wall is pushed
    back against the wall; anything with nothing under it goes. Names matching `keep`
    (gameplay pieces) are only reported. Returns the audit's failures, before fixing."""
    import os
    import sys
    tools = os.path.dirname(os.path.abspath(__file__))
    unseen = [o for o in bpy.data.objects if not o.hide_render and (
        o.name.startswith("treewall_") or "flora" in o
        or (o.data is not None and o.data.name.startswith(("grass_medium", "paddy_rice"))))]
    for o in unseen:
        o.hide_render = True
    argv = sys.argv
    sys.argv = [argv[0], "--", "--box", *map(str, region), "--tol", "0.02"]
    ns = {"__name__": "ground_audit_mod", "AUDIT_AS_MODULE": True}
    try:
        exec(compile(open(os.path.join(tools, "ground_audit.py")).read(), "ground_audit.py", "exec"), ns)
        fails, info = ns["audit"]()
    finally:
        sys.argv = argv
        for o in unseen:
            o.hide_render = False
    bvh, tri_part, parts = info["bvh"], info["tri_part"], info["parts"]
    own = {}
    for i, part in enumerate(parts):
        own.setdefault(part[0], set()).add(i)
    by_obj = {}
    for fl in fails:
        by_obj.setdefault(fl["object"], []).append(fl)
    report = {"dropped": [], "to_wall": [], "removed": [], "left": []}
    for name, fl in by_obj.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        if keep and any(re.search(k, name) for k in keep):
            report["left"].append(name)
            continue
        whole = len(fl) == len(own.get(name, ()))
        gaps = [f["gap"] for f in fl if f["gap"] is not None]
        if WALL_MOUNTED.search(name):
            # The nearest wall behind it, along the four horizontal axes.
            pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            mid = sum(pts, Vector()) / 8
            best = None
            for d in (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0))):
                start = mid.copy()
                for _ in range(4):
                    hit = bvh.ray_cast(start, d, 0.6)
                    if hit[0] is None:
                        break
                    other = parts[tri_part[hit[2]]][0]
                    # Look past itself and past other hung things (a frame's photo, its nail).
                    if other == name or WALL_MOUNTED.search(other):
                        start = hit[0] + d * 0.001
                        continue
                    # How far its back face stands off that wall.
                    back = max((p - hit[0]).dot(d) for p in pts)
                    if best is None or abs(back) < abs(best[1]):
                        best = (d, back)
                    break
            if best is not None and abs(best[1]) < 0.5:
                obj.location -= best[0] * (best[1] - 0.002)
                report["to_wall"].append(name)
                continue
        if whole and gaps and max(gaps) < 0.6:
            obj.location.z -= min(gaps) + 0.003
            report["dropped"].append(name)
        elif not whole and gaps and len(gaps) == len(fl) and max(gaps) < 0.6 and obj.type == "MESH" \
                and not obj.modifiers and obj.data.users == 1:
            # Loose pieces of one mesh (scattered rice, petals): each set down on its own.
            sz = obj.matrix_world.to_scale().z or 1.0
            for f in fl:
                for vi in parts[f["part"]][4]:
                    obj.data.vertices[vi].co.z -= (f["gap"] + 0.003) / sz
            obj.data.update()
            report["dropped"].append(name)
        elif whole and not gaps:
            obj.hide_render = True
            report["removed"].append(name)
        else:
            report["left"].append(name)
    if not quiet:
        print("[settle]", {k: len(v) for k, v in report.items()}, "left:", report["left"][:20], flush=True)
    return fails, report



def push_to_walls(names, reach=0.8):
    """Hung things the audit could not pair with a wall: cast from the object's middle
    along the four horizontal axes with Blender's own ray cast (past itself), and set
    it against the nearest surface found."""
    scene = bpy.context.scene
    moved = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            continue
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        mid = sum(pts, Vector()) / 8
        best = None
        for d in (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0))):
            start = mid.copy()
            for _ in range(6):
                hit, loc, _n, _i, ob, _m = scene.ray_cast(dg, start, d, distance=reach)
                if not hit:
                    break
                if ob is not None and (ob.name == name or WALL_MOUNTED.search(ob.name)):
                    start = loc + d * 0.001
                    continue
                back = max((p - loc).dot(d) for p in pts)
                if best is None or abs(back) < abs(best[1]):
                    best = (d, back)
                break
        if best is not None:
            obj.location -= best[0] * (best[1] - 0.002)
            moved.append(name)
    return moved


def meet_roof(prefix="cook_post_", reach=1.0):
    """Posts that stop short of the thatch they hold up: each lengthened to meet it."""
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for post in [o for o in bpy.data.objects if o.name.startswith(prefix) and o.type == "MESH"]:
        pts = [post.matrix_world @ Vector(c) for c in post.bound_box]
        top, low = max(p.z for p in pts), min(p.z for p in pts)
        mid = sum(pts, Vector()) / 8
        hit, loc, *_ = scene.ray_cast(dg, Vector((mid.x, mid.y, top + 0.001)), Vector((0, 0, 1)), distance=reach)
        if hit:
            k = (loc.z + 0.03 - low) / (top - low)
            post.scale.z *= k
            post.location.z = low + (post.location.z - low) * k
            n += 1
    return n
