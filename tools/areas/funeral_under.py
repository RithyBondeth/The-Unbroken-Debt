"""Episode 1's funeral on the ground under the house (November 21, 2026 redesign, from the
user's photographs of Cambodian village funerals; modern things allowed as shown):
printed Buddha cloths hung from the joists (Wikimedia Commons murals, credited in
art-source/library/polyhaven.json), the coffin under a white canopy hung with
triangular flags (an oxblood lacquered coffin with gilt kbach panels, a flame-crested
gable lid and lotus finials, a krama across it, marigold swags, the monks' white thread,
candlesticks on the bier's corners: "very detail and very realistic", the user, Nov 21),
the colour portrait in a wreath of
yellow and white chrysanthemums (no lights round it: the user, Nov 21), the white-clothed offering
table (fruit on a footed tray, water in plastic bottles, candles, incense), lotus-cone
candles, red-and-green mats, the monks' table under a red cloth with lacquer vases, a
clay fire pot, a bare bulb on a wire; and in the yard the loudspeaker pole.

Blender metres, X east, Y north, Z up. Builders take a collection, the ground sampler
(x, y) -> z, and a numpy Generator.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

import offerings_kit as ok
from kit import box, cloth, image_material, library_material, mesh_object, plain, sag, tube, world_uvs
from shrine_craft import Batch, frame, kbach_relief, moulding, place, relief_panel

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEX = os.path.join(ROOT, "art-source", "textures", "ep1")
JOISTS = 2.32   # underside of the floor joists above the funeral

# The funeral's ground, under the main block (Blender x, y): banners at the back.
AREA = (-5.6, 5.6, 12.0, 21.0)
# The funeral's axis runs up the bay between the stilts at x 0 and x 3 (a stilt stood in
# the old coffin's middle).
AXIS = 1.5
COFFIN = (AXIS, 17.7)         # centre, long axis along x
WREATH = (AXIS, 16.2)
TABLE = (AXIS, 15.0)
MONKS = (-1.5, 15.9)          # the next bay west, facing the coffin
FIRE = (4.4, 14.9)
SPEAKER_POLE = (4.2, 3.6)     # in the yard, before the house
COFFIN_SIZE = (2.0, 0.62, 0.48)   # body length, width, height
STAND_H = 0.42
# The current house's stilts round the funeral (round 2's house redraws this grid).
PILLARS = [(x, y) for x in (-6.0, -3.0, 0.0, 3.0, 6.0) for y in (14.0, 18.0)]


def clear(x, y, r=0.0):
    """Whether (x, y) stands clear of every stilt's plinth (half-diagonal 0.33 m) by `r`."""
    return all(math.hypot(x - px, y - py) > 0.34 + r for px, py in PILLARS)


# ------------------------------------------------------------------ textures


def _save(name, px):
    h, w = px.shape[:2]
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=False)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = px
    img.pixels[:] = rgba[::-1].ravel()
    path = os.path.join(TEX, name + ".png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


def krama_texture():
    """The checked cotton krama: black and white gingham with a woven thread grain."""
    path = os.path.join(TEX, "T_ep1_krama_check_BC.png")
    if os.path.exists(path):
        return path
    n = 1024
    y, x = np.mgrid[0:n, 0:n]
    cell = 32
    a = (x // cell) % 2
    b = (y // cell) % 2
    v = np.where(a + b == 2, 0.05, np.where(a + b == 1, 0.42, 0.86))
    thread = 0.93 + 0.07 * (np.sin(x * 2.1) * np.sin(y * 2.1) > 0)
    rng = np.random.default_rng(5)
    v = v * thread * (0.95 + 0.05 * rng.random((n, n)))
    return _save("T_ep1_krama_check_BC", np.stack([v, v * 0.98, v * 0.95], -1).astype(np.float32))


def mat_texture():
    """A Khmer woven reed mat (kantel), dyed: red ground, green and yellow bands, black
    diamonds, the reed grain running across."""
    path = os.path.join(TEX, "T_ep1_kantel_mat_BC.png")
    if os.path.exists(path):
        return path
    n = 1024
    y, x = np.mgrid[0:n, 0:n]
    red, green, yellow, black, cream = (np.array(c, np.float32) for c in (
        (0.55, 0.07, 0.06), (0.06, 0.32, 0.12), (0.8, 0.62, 0.12), (0.05, 0.04, 0.03), (0.78, 0.68, 0.48)))
    px = np.empty((n, n, 3), np.float32)
    px[:] = red
    band = (y // 16) % 16
    px[(band == 3) | (band == 4)] = green
    px[band == 5] = yellow
    px[(band == 11) | (band == 12)] = green
    px[band == 13] = cream
    cx, cy = (x % 128) - 64, (y % 256) - 128
    diamond = (np.abs(cx) * 2 + np.abs(cy) < 70) & (np.abs(cx) * 2 + np.abs(cy) > 46) & ((band < 3) | (band > 13) | ((band > 5) & (band < 11)))
    px[diamond] = black
    reed = 0.86 + 0.14 * (np.sin(y * 0.9 + np.sin(x * 0.05) * 2) * 0.5 + 0.5)
    px *= reed[..., None]
    return _save("T_ep1_kantel_mat_BC", px)


def materials():
    m = dict(ok.materials())
    m["banner_nirvana"] = image_material("M_fu_banner_nirvana", os.path.join(TEX, "T_ep1_funeral_banner_nirvana_BC.png"), rough=0.85)
    m["banner_mara"] = image_material("M_fu_banner_mara", os.path.join(TEX, "T_ep1_funeral_banner_mara_BC.png"), rough=0.85)
    for k in ("banner_nirvana", "banner_mara"):
        m[k].use_backface_culling = False
    m["krama"] = image_material("M_fu_krama", krama_texture(), rough=0.92, tile=0.35)
    m["mat"] = image_material("M_fu_kantel_mat", mat_texture(), rough=0.8, tile=1.1)
    m["white"] = library_material("rough_linen", "M_fu_white_cotton", tint=(0.74, 0.71, 0.64), tile=0.5)
    m["white"].use_backface_culling = False
    m["red_cloth"] = library_material("rough_linen", "M_fu_red_cloth", tint=(0.6, 0.06, 0.05), tile=0.4)
    m["red_cloth"].use_backface_culling = False
    m["fringe"] = plain("M_fu_yellow_fringe", (0.75, 0.55, 0.1), rough=0.7)
    m["lacquer"] = plain("M_fu_lacquer_vase", (0.08, 0.025, 0.015), rough=0.25)
    m["steel"] = plain("M_fu_galvanised", (0.5, 0.5, 0.48), rough=0.45, metal=0.9)
    m["horn"] = plain("M_fu_horn_paint", (0.72, 0.72, 0.68), rough=0.5, metal=0.3)
    m["wire"] = plain("M_fu_wire", (0.03, 0.03, 0.03), rough=0.6)
    m["plastic"] = plain("M_fu_bottle", (0.8, 0.85, 0.88), rough=0.08, alpha=0.35)
    m["cap"] = plain("M_fu_bottle_cap", (0.85, 0.2, 0.45), rough=0.4)
    m["water_in"] = plain("M_fu_bottle_water", (0.75, 0.82, 0.85), rough=0.05, alpha=0.25)
    m["orange"] = plain("M_fu_orange", (0.75, 0.32, 0.03), rough=0.55)
    m["apple"] = plain("M_fu_apple", (0.5, 0.06, 0.04), rough=0.35)
    m["grape"] = plain("M_fu_grape", (0.12, 0.03, 0.08), rough=0.25)
    m["gold"] = plain("M_fu_gilt_tray", (0.7, 0.5, 0.15), rough=0.3, metal=1.0)
    m["terracotta"] = library_material("clay_plaster", "M_fu_terracotta", tint=(0.75, 0.42, 0.25), tile=0.5)
    m["bulb"] = plain("M_fu_bulb", (1, 0.85, 0.6), rough=0.2, emission=(1, 0.8, 0.5), strength=12)
    m["fire"] = plain("M_fu_fire", (1, 0.5, 0.1), rough=1, emission=(1, 0.4, 0.06), strength=4, alpha=0.85)
    m["glass_red"] = plain("M_fu_red_glass", (0.7, 0.05, 0.04), rough=0.1, alpha=0.55)
    # Posts and battens: old sawn wood (the poles of a hired funeral set).
    m["bamboo"] = library_material("weathered_brown_planks", "M_fu_post_wood", tint=(0.72, 0.66, 0.6), tile=0.6)
    m["leaf"] = m.get("leaf")
    # The coffin: oxblood lacquer over rosewood, gilt carving, brass handles.
    m["coffin_red"] = library_material("rosewood_veneer1", "M_fu_coffin_lacquer", tint=(0.92, 0.3, 0.2), tile=0.45)
    m["coffin_gold"] = plain("M_fu_coffin_gilt", (0.6, 0.42, 0.15), rough=0.34, metal=1.0)
    m["coffin_dark"] = library_material("dark_wood", "M_fu_coffin_plinth", tint=(0.5, 0.26, 0.2), tile=0.4)
    m["brass"] = plain("M_fu_brass", (0.5, 0.38, 0.18), rough=0.5, metal=1.0)
    m["thread"] = plain("M_fu_cotton_thread", (0.82, 0.8, 0.74), rough=0.95)
    m["seep"] = plain("M_fu_seep", (0.03, 0.018, 0.012), rough=0.1)
    # Inside the coffin: dark cotton padding (CorpseModels.ts reuses it by name).
    m["lining"] = bpy.data.materials.get("M_funeral_lining") or plain("M_funeral_lining", (0.035, 0.026, 0.02), rough=0.97)
    m["krama"].use_backface_culling = False
    return m


# ------------------------------------------------------------------ pieces


def hang_banner(coll, m, key, x0, x1, y, z_top, height, folds=5, axis="x", seed=0):
    """A printed cloth hung from a joist by its top edge, the print sagging in soft folds."""
    obj = cloth(f"fu_banner_{key}_{seed}", coll, x0, x1, z_top - height, z_top, y, m[key], folds=folds, depth=0.03,
                segments=(48, 32), axis=axis)
    # Map the print straight onto the cloth: u along the width, v up its height.
    me = obj.data
    uv = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        a = (co.x - x0) / (x1 - x0) if axis == "x" else (co.y - x0) / (x1 - x0)
        uv.data[loop.index].uv = (a if axis == "x" else 1 - a, (co.z - (z_top - height)) / height)
    # A bamboo batten along the top, wired to the joist.
    if axis == "x":
        tube(f"fu_banner_batten_{key}_{seed}", coll, [(x0 - 0.05, y, z_top + 0.01), (x1 + 0.05, y, z_top + 0.01)], 0.012, m["bamboo"])
        for xx in (x0 + 0.1, x1 - 0.1):
            tube(f"fu_banner_tie_{key}_{seed}_{xx:.1f}", coll, [(xx, y, z_top + 0.01), (xx, y, JOISTS + 0.04)], 0.002, m["wire"])
    else:
        tube(f"fu_banner_batten_{key}_{seed}", coll, [(y, x0 - 0.05, z_top + 0.01), (y, x1 + 0.05, z_top + 0.01)], 0.012, m["bamboo"])
        for yy in (x0 + 0.1, x1 - 0.1):
            tube(f"fu_banner_tie_{key}_{seed}_{yy:.1f}", coll, [(y, yy, z_top + 0.01), (y, yy, JOISTS + 0.04)], 0.002, m["wire"])
    return obj


def canopy(coll, m, ground, cx, cy, w=3.0, d=1.9, h=2.05, seed=1):
    """Four bamboo posts, a white sheet sagging between them, a valance and a row of white
    triangular flags hanging from it."""
    r = np.random.default_rng(seed)
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
    for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        g = ground(x, y)
        tube(f"fu_canopy_post_{x:.1f}_{y:.1f}", coll, [(x, y, g - 0.2), (x, y, g + h + 0.06)], 0.03, m["bamboo"])
    g = ground(cx, cy)
    nx, ny = 30, 20
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            sag = 0.16 * math.sin(math.pi * u) * math.sin(math.pi * v) + 0.01 * r.normal()
            verts.append((x0 + w * u, y0 + d * v, g + h - sag))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    top = mesh_object("fu_canopy_sheet", coll, verts, faces, m["white"], smooth=True)
    world_uvs(top)
    for side, (a0, a1, plane, axis) in enumerate(((x0, x1, y0, "x"), (x0, x1, y1, "x"), (y0, y1, x0, "y"), (y0, y1, x1, "y"))):
        cloth(f"fu_canopy_valance_{side}", coll, a0, a1, g + h - 0.22, g + h + 0.01, plane, m["white"], folds=9, depth=0.02,
              segments=(40, 6), axis=axis)
    # The triangular flags (tung): along the front and the back.
    for yy in (y0 - 0.01, y1 + 0.01):
        n = 7
        for k in range(n):
            x = x0 + 0.2 + (w - 0.4) * k / (n - 1)
            hgt = r.uniform(0.32, 0.42)
            tri = [(x - 0.11, yy, g + h - 0.2), (x + 0.11, yy, g + h - 0.2), (x + r.normal(0, 0.01), yy + r.normal(0, 0.01), g + h - 0.2 - hgt)]
            o = mesh_object(f"fu_flag_{yy:.1f}_{k}", coll, tri, [(0, 1, 2)], m["white"])
            world_uvs(o)


def lotus_cone(b, m, x, y, z, rng, lit=True):
    """A folded banana-leaf lotus cone (the kind in the user's photo), a candle in it."""
    leaf = m["leaf"] or m["leaf_dry"]
    petals = 6
    for k in range(petals):
        a = math.tau * k / petals + rng.normal(0, 0.05)
        pts = [(x + math.cos(a) * 0.025, y + math.sin(a) * 0.025, z), (x + math.cos(a) * 0.06, y + math.sin(a) * 0.06, z + 0.07),
               (x + math.cos(a) * 0.045, y + math.sin(a) * 0.045, z + 0.15)]
        side = Vector((-math.sin(a), math.cos(a), 0)) * 0.04
        quad = [Vector(pts[0]) - side * 0.5, Vector(pts[0]) + side * 0.5, Vector(pts[1]) + side, Vector(pts[1]) - side]
        b.add(leaf, [tuple(p) for p in quad], [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 0.5), (0, 0.5)], smooth=True)
        b.add(leaf, [tuple(Vector(pts[1]) - side), tuple(Vector(pts[1]) + side), pts[2]], [(0, 1, 2)], [(0, 0.5), (1, 0.5), (0.5, 1)])
    b.lathe(m["leaf_dry"], [(0, 0), (0.05, 0), (0.06, 0.01), (0, 0.012)], xf=place(x, y, z - 0.002), segments=16, tile=0.1)
    return ok.candle(b, m, place(x, y, z + 0.01, rz=rng.uniform(0, 6)), rng, height=0.11, radius=0.009, melt=0.5, lit=lit)


def bottle(b, m, x, y, z, rng, full=0.7):
    prof = [(0, 0), (0.033, 0), (0.034, 0.01), (0.033, 0.18), (0.028, 0.2), (0.014, 0.225), (0.013, 0.235), (0, 0.235)]
    b.lathe(m["plastic"], prof, xf=place(x, y, z), segments=20, tile=0.1)
    b.lathe(m["water_in"], [(0, 0.004), (0.031, 0.004), (0.031, 0.18 * full), (0, 0.18 * full)], xf=place(x, y, z), segments=16, tile=0.1)
    b.lathe(m["cap"], [(0, 0.235), (0.015, 0.235), (0.015, 0.252), (0, 0.252)], xf=place(x, y, z), segments=12, tile=0.05)


def fruit_tray(b, m, x, y, z, rng):
    """A gilt footed tray piled with oranges, apples and grapes."""
    b.lathe(m["gold"], [(0, 0), (0.07, 0), (0.07, 0.01), (0.03, 0.03), (0.03, 0.08), (0.17, 0.11), (0.18, 0.125), (0, 0.115)],
            xf=place(x, y, z), segments=32, tile=0.2)
    top = z + 0.12
    for k in range(9):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(0, 0.11)
        kind = "orange" if k % 3 else "apple"
        rad = 0.038 if kind == "orange" else 0.036
        layer = 0 if rr > 0.05 else 1
        prof = [(0, -rad)] + [(rad * math.sin(t), -rad * math.cos(t)) for t in np.linspace(0.2, math.pi - 0.2, 9)] + [(0, rad)]
        b.lathe(m[kind], prof, xf=place(x + rr * math.cos(a), y + rr * math.sin(a), top + rad + layer * 0.05), segments=14, tile=0.1)
    for k in range(26):
        p = (x + 0.08 + rng.normal(0, 0.025), y - 0.04 + rng.normal(0, 0.025), top + 0.02 + abs(rng.normal(0, 0.03)))
        prof = [(0, -0.009)] + [(0.009 * math.sin(t), -0.009 * math.cos(t)) for t in np.linspace(0.3, math.pi - 0.3, 5)] + [(0, 0.009)]
        b.lathe(m["grape"], prof, xf=place(*p), segments=8, tile=0.05)


def offering_table(coll, m, ground, rng, x, y):
    """A low table under a white cloth: the tray of fruit, bottles of water, candles in
    glasses, a bowl of rice with incense in it."""
    g = ground(x, y)
    h = 0.55
    box("fu_table_top", coll, x - 0.6, x + 0.6, y - 0.35, y + 0.35, g + h - 0.03, g + h, m["white"])
    for dx in (-0.55, 0.55):
        for dy in (-0.3, 0.3):
            box(f"fu_table_leg_{dx}_{dy}", coll, x + dx - 0.02, x + dx + 0.02, y + dy - 0.02, y + dy + 0.02, g - 0.02, g + h - 0.03, m["white"])
    cloth("fu_table_cloth_front", coll, x - 0.62, x + 0.62, g + 0.05, g + h, y - 0.36, m["white"], folds=8, depth=0.02, segments=(40, 12))
    b = Batch("fu_table_things")
    top = g + h
    fruit_tray(b, m, x + 0.25, y + 0.05, top, rng)
    for k, dx in enumerate((-0.48, -0.4, 0.5)):
        bottle(b, m, x + dx, y + 0.18 - 0.05 * k, top, rng, full=rng.uniform(0.4, 0.95))
    flames = []
    for dx in (-0.22, 0.02):
        b.lathe(m["glass_red"], [(0, 0), (0.035, 0), (0.038, 0.09), (0, 0.09)], xf=place(x + dx, y - 0.18, top), segments=16, tile=0.1)
        flames.append(ok.candle(b, m, place(x + dx, y - 0.18, top + 0.005), rng, height=0.05, radius=0.016, melt=0.8))
    ok.incense_bowl(b, m, place(x - 0.25, y + 0.1, top), rng, radius=0.08, height=0.07, sticks=20, lit=6)
    b.build(coll)
    return flames


def wreath_portrait(coll, m, ground, rng, x, y, portrait_image):
    """The colour photograph (blue background) in a red-and-gold frame at the heart of a
    round wreath of yellow and white chrysanthemums on a stand, palm fronds behind, white
    bows below."""
    from funeral import Flowers, bow, funeral_materials, pole
    fm = funeral_materials({})
    f = fm["_funeral"]
    g = ground(x, y)
    for dx, dy in ((-0.22, 0.06), (0.22, 0.06), (0, -0.24)):
        pole(f"fu_wreath_leg_{dx}_{dy}", coll, (x + dx, y + dy, g), (x, y - 0.04, g + 1.25), 0.014, f["gilt"], sides=8)
    centre = Vector((x, y, g + 1.42))
    flowers = Flowers("fu_wreath_flowers", coll, fm, 777)
    # Yellow outer ring, white inner ring, the centre left for the photograph.
    for j in range(260):
        a = j * 2.399963 + rng.uniform(-0.05, 0.05)
        outer = j % 3 != 0
        rad = rng.uniform(0.33, 0.43) if outer else rng.uniform(0.25, 0.32)
        p = centre + Vector((math.cos(a) * rad, -0.06 + rng.uniform(-0.02, 0.02), math.sin(a) * rad * 1.12))
        flowers.bloom(p, rng.uniform(0.03, 0.045), normal=(0.15 * math.cos(a), -1, 0.15 * math.sin(a)), yellow=outer, kind="chrysanthemum")
    for j in range(22):
        a = rng.uniform(0, math.tau)
        d = Vector((math.cos(a), 0, math.sin(a)))
        flowers.palm(centre + Vector((d.x * 0.3, 0.05, d.z * 0.34)), centre + Vector((d.x * rng.uniform(0.55, 0.7), 0.08, d.z * rng.uniform(0.6, 0.78))),
                     rng.uniform(0.05, 0.08))
    flowers.finish()
    bow("fu_wreath_bow_l", coll, fm, (x - 0.22, y - 0.1, g + 0.72), 0.17)
    bow("fu_wreath_bow_r", coll, fm, (x + 0.22, y - 0.1, g + 0.72), 0.17)
    # The photograph and its frame.
    photo = image_material("M_fu_portrait", portrait_image, rough=0.4)
    pw, ph = 0.3, 0.4
    frame = plain("M_fu_frame_red_gold", (0.45, 0.06, 0.04), rough=0.35, metal=0.3)
    box("fu_portrait_frame", coll, x - pw / 2 - 0.035, x + pw / 2 + 0.035, y - 0.13, y - 0.1, centre.z - ph / 2 - 0.035, centre.z + ph / 2 + 0.035, frame)
    pic = mesh_object("fu_portrait_photo", coll, [(x - pw / 2, y - 0.135, centre.z - ph / 2), (x + pw / 2, y - 0.135, centre.z - ph / 2),
                                                  (x + pw / 2, y - 0.135, centre.z + ph / 2), (x - pw / 2, y - 0.135, centre.z + ph / 2)],
                      [(0, 1, 2, 3)], photo, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return pic


def monks_table(coll, m, ground, rng, x, y):
    """The monks' place: a low table under a red cloth with a yellow fringe band, two dark
    lacquer vases of flowers, candles in red glasses; their cushions behind it."""
    g = ground(x, y)
    h = 0.62
    box("fu_monks_table", coll, x - 0.45, x + 0.45, y - 0.3, y + 0.3, g + h - 0.03, g + h, m["red_cloth"])
    for side, (a0, a1, plane, axis) in enumerate(((x - 0.46, x + 0.46, y - 0.31, "x"), (y - 0.31, y + 0.31, x + 0.46, "y"))):
        cloth(f"fu_monks_cloth_{side}", coll, a0, a1, g + h - 0.3, g + h, plane, m["red_cloth"], folds=6, depth=0.015, segments=(24, 8), axis=axis)
    box("fu_monks_fringe", coll, x - 0.47, x + 0.47, y - 0.325, y - 0.315, g + h - 0.36, g + h - 0.29, m["fringe"])
    b = Batch("fu_monks_things")
    for dx in (-0.25, 0.25):
        b.lathe(m["lacquer"], [(0, 0), (0.06, 0), (0.07, 0.03), (0.1, 0.15), (0.08, 0.27), (0.04, 0.33), (0.05, 0.37), (0, 0.36)],
                xf=place(x + dx, y + 0.05, g + h), segments=28, tile=0.2)
    flames = []
    for dx in (-0.08, 0.08):
        b.lathe(m["glass_red"], [(0, 0), (0.035, 0), (0.038, 0.1), (0, 0.1)], xf=place(x + dx, y - 0.12, g + h), segments=16, tile=0.1)
        flames.append(ok.candle(b, m, place(x + dx, y - 0.12, g + h + 0.005), rng, height=0.06, radius=0.016, melt=0.7))
    b.build(coll)
    from funeral import Flowers, funeral_materials
    fm = funeral_materials({})
    for dx in (-0.25, 0.25):
        fl = Flowers(f"fu_monks_flowers_{dx}", coll, fm, int(100 + dx * 10))
        fl.bouquet(Vector((x + dx, y + 0.05, g + h + 0.36)), width=0.16, height=0.22, count=40)
        fl.finish()
    return flames


def mats(coll, m, ground, x0, x1, y0, y1, rng):
    """Reed mats laid edge to edge (and over each other) on the packed earth. Each is a
    grid draped over the ground, 2 cm up (flat quads at their middle's height let the
    uneven earth poke through and flicker against them in the game), and the ones laid
    over a neighbour sit 1.5 cm higher still, so the overlaps never fight."""
    n = 0
    y = y0
    nu, nv = 6, 12
    while y < y1:
        x = x0
        while x < x1:
            w, d = 0.9, 1.8
            lift = 0.02 + 0.015 * (n % 2)
            a = rng.normal(0, 0.03)
            c, s = math.cos(a), math.sin(a)
            cx, cy = x + w / 2, y + d / 2
            verts, uvs = [], []
            for j in range(nv + 1):
                for i in range(nu + 1):
                    dx, dy = w * (i / nu - 0.5), d * (j / nv - 0.5)
                    px, py = cx + c * dx - s * dy, cy + s * dx + c * dy
                    verts.append((px, py, ground(px, py) + lift))
                    uvs.append((0.9 * i / nu, 1.8 * j / nv))
            faces = [(j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i)
                     for j in range(nv) for i in range(nu)]
            mesh_object(f"fu_mat_{n}", coll, verts, faces, m["mat"], uvs=[uvs[k] for f in faces for k in f])
            n += 1
            x += w - 0.04
        y += 1.8 - 0.05
    return n


def fire_pot(coll, m, ground, rng, x, y):
    g = ground(x, y)
    b = Batch("fu_fire_pot")
    prof = [(0, 0), (0.12, 0), (0.2, 0.08), (0.24, 0.2), (0.22, 0.3), (0.17, 0.36), (0.18, 0.38), (0.16, 0.39), (0.15, 0.37), (0, 0.33)]
    b.lathe(m["terracotta"], prof, xf=place(x, y, g - 0.01), segments=36, tile=0.3)
    b.build(coll)
    verts, faces = [], []
    for k in range(16):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(0, 0.09)
        base = Vector((x + rr * math.cos(a), y + rr * math.sin(a), g + 0.33))
        hgt = rng.uniform(0.06, 0.2)
        face = rng.uniform(0, math.tau)
        side = Vector((math.cos(face), math.sin(face), 0))
        lean = Vector((rng.normal(0, 0.03), rng.normal(0, 0.03), 0))
        i = len(verts)
        # A curling tongue: wide at the coals, narrowing and bending as it rises.
        for j in range(5):
            t = j / 4
            w = 0.035 * (1 - t) ** 0.8 + 0.002
            c = base + lean * t * t + Vector((0, 0, hgt * t)) + side.cross(Vector((0, 0, 1))) * 0.015 * math.sin(t * 3 + k)
            verts += [tuple(c - side * w), tuple(c + side * w)]
        for j in range(4):
            q = i + 2 * j
            faces.append((q, q + 1, q + 3, q + 2))
    mesh_object("fu_fire_flames", coll, verts, faces, m["fire"])
    return Vector((x, y, g + 0.45))


def bulb(coll, m, x, y, drop=0.55):
    tube("fu_bulb_wire", coll, [(x, y, JOISTS + 0.02), (x, y, JOISTS - drop)], 0.003, m["wire"])
    b = Batch("fu_bulb")
    b.lathe(m["wire"], [(0, 0), (0.016, 0), (0.016, 0.04), (0, 0.04)], xf=place(x, y, JOISTS - drop - 0.04), segments=12, tile=0.05)
    b.lathe(m["bulb"], [(0, -0.09), (0.02, -0.085), (0.032, -0.06), (0.03, -0.03), (0.016, 0), (0, 0)], xf=place(x, y, JOISTS - drop - 0.04),
            segments=16, tile=0.05)
    b.build(coll)
    return Vector((x, y, JOISTS - drop - 0.1))


def loudspeaker_pole(coll, m, ground, rng, x, y, height=8.5):
    """A tall pole in the yard with four horn loudspeakers at the top, guyed with wire,
    the cable running down it: the chanting goes out over the farmstead all night."""
    g = ground(x, y)
    tube("fu_pole", coll, [(x, y, g - 0.6), (x + 0.04, y + 0.02, g + height)], 0.045, m["steel"])
    top = Vector((x + 0.04, y + 0.02, g + height))
    b = Batch("fu_speakers")
    for k, (a, tilt) in enumerate(((0.3, 0.25), (2.0, 0.18), (3.5, 0.3), (5.1, 0.22))):
        d = Vector((math.cos(a), math.sin(a), -tilt)).normalized()
        base = top + Vector((0, 0, 0.1 + 0.18 * (k % 2)))
        m3 = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        xf = Matrix.Translation(base) @ m3
        prof = [(0.05, 0), (0.06, 0.05), (0.09, 0.15), (0.16, 0.3), (0.24, 0.38), (0.25, 0.39), (0.23, 0.39), (0.15, 0.31), (0.08, 0.17), (0.05, 0.06), (0.04, 0)]
        b.lathe(m["horn"], prof, xf=xf, segments=28, tile=0.3, cap=False)
        b.lathe(m["steel"], [(0, -0.12), (0.07, -0.12), (0.08, -0.02), (0.05, 0), (0, 0)], xf=xf, segments=20, tile=0.2)
        b.tube(m["steel"], [tuple(top), tuple(base)], [0.012, 0.012], sides=6)
    b.build(coll)
    for k, a in enumerate((0.6, 2.7, 4.7)):
        foot = (x + math.cos(a) * height * 0.55, y + math.sin(a) * height * 0.55)
        gz = ground(*foot)
        sagged = []
        for i in range(9):
            t = i / 8
            p = Vector((top.x, top.y, top.z - 0.4)).lerp(Vector((foot[0], foot[1], gz + 0.05)), t)
            p.z -= 0.25 * math.sin(math.pi * t)
            sagged.append(tuple(p))
        tube(f"fu_guy_{k}", coll, sagged, 0.004, m["wire"])
        box(f"fu_guy_stake_{k}", coll, foot[0] - 0.03, foot[0] + 0.03, foot[1] - 0.03, foot[1] + 0.03, gz - 0.3, gz + 0.12, m["bamboo"])
    tube("fu_pole_cable", coll, [(x + 0.06, y, g + 0.2), (x + 0.09, y + 0.03, g + height - 0.1)], 0.006, m["wire"])
    return top


def incense_and_candles(coll, m, ground, rng):
    """Joss sticks burning in clay pots of sand at the coffin's corners and before the
    portrait, and rows of candles on the bare earth: lit, guttering, burnt out in pools
    of wax. Returns (flame tips, smoke origins)."""
    cx, cy = COFFIN
    b = Batch("fu_incense_candles")
    flames, smoke = [], []
    pots = [(cx - 1.25, cy - 0.75), (cx + 1.25, cy - 0.75), (cx - 1.25, cy + 0.75), (cx + 1.25, cy + 0.75),
            (WREATH[0] - 0.55, WREATH[1] - 0.35), (WREATH[0] + 0.55, WREATH[1] - 0.35)]
    for k, (x, y) in enumerate(pots):
        if not clear(x, y, 0.12):
            continue
        g = ground(x, y)
        ok.incense_bowl(b, m, place(x, y, g - 0.005), rng, radius=0.1, height=0.09, sticks=30, lit=12)
        ok.rice_grains(b, m, (x, y, g), rng, count=40, spread=0.09)
        smoke.append(Vector((x, y, g + 0.36)))
    def candle_at(x, y):
        if not clear(x, y, 0.05):
            return
        g = ground(x, y)
        ok.candle_dish(b, m, place(x, y, g), rng, radius=0.04, melt=rng.uniform(0.5, 1))
        lit = rng.random() < 0.82
        tip = ok.candle(b, m, place(x, y, g + 0.006, rz=rng.uniform(0, 6)), rng, height=rng.uniform(0.04, 0.15),
                        radius=0.01, melt=rng.uniform(0.4, 1), lit=lit)
        if rng.random() < 0.45:
            ok.wax_spill(b, m, place(x + rng.normal(0, 0.03), y + rng.normal(0, 0.03), g), rng, radius=rng.uniform(0.02, 0.05))
        if lit:
            flames.append(tip)
    # Two rows down the way to the coffin, and a ring round it on the earth.
    for side in (-1, 1):
        y = 13.2
        while y < cy - 1.0:
            candle_at(cx + side * rng.uniform(0.85, 0.95), y + rng.normal(0, 0.03))
            y += rng.uniform(0.2, 0.3)
    for k in range(30):
        # A squared ring hugging the bier's skirt (a superellipse, so its corners clear it).
        a = math.tau * k / 30
        c, s = math.cos(a), math.sin(a)
        x = cx + math.copysign(abs(c) ** 0.5, c) * 1.32 + rng.normal(0, 0.02)
        y = cy + math.copysign(abs(s) ** 0.5, s) * 0.68 + rng.normal(0, 0.02)
        if abs(x - cx) < 0.8 and y < cy:
            continue  # leave the way in to the coffin's side clear
        candle_at(x, y)
    b.build(coll)
    return flames, smoke


def smoke_material():
    mat = bpy.data.materials.get("M_fu_incense_smoke")
    if mat:
        return mat
    mat = bpy.data.materials.new("M_fu_incense_smoke")
    mat.use_nodes = True
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.88, 0.88, 0.9, 1)
    vol.inputs["Anisotropy"].default_value = 0.6
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 24.0
    n1.inputs["Detail"].default_value = 6
    n1.inputs["Distortion"].default_value = 1.5
    nt.links.new(geo.outputs["Position"], n1.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.42
    mr.inputs["From Max"].default_value = 0.75
    mr.inputs["To Max"].default_value = 45.0
    nt.links.new(n1.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], vol.inputs["Density"])
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    return mat


def smoke_wisp(coll, origin, height, seed):
    """A thread of joss-stick smoke for Cycles previews (the game draws its smoke with
    particles): straight off the embers, then curling and widening as it climbs."""
    r = np.random.default_rng(seed)
    cu = bpy.data.curves.new(f"fu_smoke_{seed}", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    n = 40
    sp.points.add(n - 1)
    f1, f2 = r.uniform(1.5, 3.0), r.uniform(3.5, 6.0)
    p1, p2 = r.uniform(0, math.tau, 2)
    for i in range(n):
        t = i / (n - 1)
        a = t ** 1.6
        x = origin[0] + a * (0.1 * math.sin(f1 * t * math.tau + p1) + 0.04 * math.sin(f2 * t * math.tau + p2))
        y = origin[1] + a * (0.08 * math.cos(f1 * t * math.tau + p2) + 0.03 * math.cos(f2 * t * math.tau + p1))
        sp.points[i].co = (x, y, origin[2] + height * t, 1)
        sp.points[i].radius = 0.005 + 0.075 * t ** 1.6
    sp.order_u = 4
    sp.use_endpoint_u = True
    ob = bpy.data.objects.new(f"fu_smoke_{seed}", cu)
    cu.materials.append(smoke_material())
    coll.objects.link(ob)
    return ob


# ------------------------------------------------------------------ the coffin


def _resize(a, h, w):
    """Bilinear resample of a heightmap to h rows by w columns."""
    ys, xs = np.linspace(0, a.shape[0] - 1, h), np.linspace(0, a.shape[1] - 1, w)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    y1, x1 = np.minimum(y0 + 1, a.shape[0] - 1), np.minimum(x0 + 1, a.shape[1] - 1)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return top * (1 - fy) + bot * fy


def panel_relief(w, h, seed):
    """A coffin panel's carving (rows bottom to top): a flame medallion at the centre,
    scroll sprigs turned into the four corners, a double ruled border."""
    p = np.zeros((h, w))
    s = int(h * 0.88)
    r0, c0 = (h - s) // 2, (w - s) // 2
    p[r0:r0 + s, c0:c0 + s] = _resize(kbach_relief(120, 120, seed, kind="crest"), s, s)
    scroll = kbach_relief(200, 124, seed + 1, kind="band")[8:-8, 30:170]
    sh, sw = int(h * 0.38), int(w * 0.27)
    sc = _resize(scroll, sh, sw) * 0.85
    for flip_x in (0, 1):
        for flip_y in (0, 1):
            t = sc[:, ::-1] if flip_x else sc
            t = t[::-1] if flip_y else t
            r, c = (h - 7 - sh if flip_y else 7), (w - 7 - sw if flip_x else 7)
            p[r:r + sh, c:c + sw] = np.maximum(p[r:r + sh, c:c + sw], t)
    for inset, height in ((1, 0.6), (4, 0.4)):
        p[inset:inset + 2, inset:w - inset] = np.maximum(p[inset:inset + 2, inset:w - inset], height)
        p[h - inset - 2:h - inset, inset:w - inset] = np.maximum(p[h - inset - 2:h - inset, inset:w - inset], height)
        p[inset:h - inset, inset:inset + 2] = np.maximum(p[inset:h - inset, inset:inset + 2], height)
        p[inset:h - inset, w - inset - 2:w - inset] = np.maximum(p[inset:h - inset, w - inset - 2:w - inset], height)
    return p


def flame_outline(h, w, curl, n=14):
    """A kbach flame cut-out: broad at its foot, swelling, drawn up to a curling tip."""
    right, left = [], []
    for i in range(n + 1):
        s = i / n
        hw = w / 2 * (1 - s) ** 0.8 * (0.62 + 0.38 * math.sin(math.pi * s))
        c = curl * s ** 2.4
        right.append((c + hw, h * s))
        left.append((c - hw, h * s))
    return right + left[-2::-1]


def _loop(x0, x1, y0, y1, z):
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), (x0, y0, z)]


def coffin(coll, m, ground, rng, cx, cy):
    """A villager's coffin as Cambodian families buy them now: an oxblood lacquered box
    with gilt kbach panels and brass handles, a curved gable lid with a flame crest, lotus
    finials and upswept corner tails, on a bier under a pleated red skirt; a checked krama
    across the lid, marigold and jasmine swags, the monks' white thread tied round it, and
    a dark seep on the earth from under the skirt. The body and the lid are separate
    objects (coffin_body_*, coffin_lid_*) so Act III can open it.
    Returns the point where the monks' thread leaves the coffin, and the corner candles'
    flame tips."""
    L, W, H = COFFIN_SIZE
    g = ground(cx, cy)
    red, gold, dark = m["coffin_red"], m["coffin_gold"], m["coffin_dark"]

    # ---- the bier: a timber frame, a white cloth on top, a pleated red skirt round it
    SL, SW = L + 0.3, W + 0.3
    sx0, sx1, sy0, sy1 = cx - SL / 2, cx + SL / 2, cy - SW / 2, cy + SW / 2
    top = g + STAND_H
    st = Batch("coffin_stand")
    for dx in (-1, 1):
        for dy in (-1, 1):
            st.box(m["bamboo"], (0.06, 0.06, STAND_H), (cx + dx * (SL / 2 - 0.09), cy + dy * (SW / 2 - 0.09), g + STAND_H / 2 - 0.02))
    st.box(m["white"], (SL + 0.02, SW + 0.02, 0.012), (cx, cy, top + 0.006), grain=False)
    # A flat valance under the cloth, a gilt kbach band printed along it between braids.
    for side in (-1, 1):
        st.box(m["red_cloth"], (SL + 0.02, 0.012, 0.1), (cx, cy + side * (SW / 2 + 0.012), top - 0.05), grain=False)
        st.box(m["red_cloth"], (0.012, SW + 0.02, 0.1), (cx + side * (SL / 2 + 0.012), cy, top - 0.05), grain=False)
    bands = [((cx, sy0 - 0.018, top - 0.088), (1, 0, 0), (0, -1, 0), SL - 0.06), ((cx, sy1 + 0.018, top - 0.088), (-1, 0, 0), (0, 1, 0), SL - 0.06),
             ((sx0 - 0.018, cy, top - 0.088), (0, -1, 0), (-1, 0, 0), SW - 0.06), ((sx1 + 0.018, cy, top - 0.088), (0, 1, 0), (1, 0, 0), SW - 0.06)]
    for k, (o, xa, za, width) in enumerate(bands):
        px = int(width / 0.0052)
        relief_panel(st, gold, kbach_relief(px, 30, 60 + k, kind="band"), "rect", width, 0.076, 0.004,
                     frame(o, xa, (0, 0, 1), za), nu=min(px - 1, 260), nv=14, base=0.001)
    for z in (top - 0.006, top - 0.094):
        st.tube(gold, _loop(sx0 - 0.019, sx1 + 0.019, sy0 - 0.019, sy1 + 0.019, z), 0.004, sides=6)
    # Tall brass candlesticks at the bier's four corners, a white candle guttering in each.
    lit = []
    stick = [(0, 0), (0.045, 0), (0.045, 0.01), (0.034, 0.02), (0.014, 0.04), (0.011, 0.11), (0.019, 0.12), (0.011, 0.13), (0.009, 0.25),
             (0.02, 0.262), (0.034, 0.28), (0.03, 0.29), (0, 0.29)]
    for dx in (-1, 1):
        for dy in (-1, 1):
            px, py = cx + dx * (SL / 2 - 0.065), cy + dy * (SW / 2 - 0.065)
            st.lathe(m["brass"], stick, xf=place(px, py, top + 0.012), segments=24, tile=0.1,
                     radial=lambda a, h: 1 + 0.03 * math.sin(a * 6) * (0.04 < h < 0.11))
            ok.wax_spill(st, m, place(px + 0.01, py, top + 0.3), rng, radius=0.022)
            lit.append(ok.candle(st, m, place(px, py, top + 0.3, rz=rng.uniform(0, 6)), rng, height=rng.uniform(0.1, 0.17),
                                 radius=0.014, melt=rng.uniform(0.6, 1.0)))
    st.build(coll)
    skirt = (top - 0.1, g + 0.004)
    cloth("coffin_skirt_front", coll, sx0, sx1, skirt[1], skirt[0], sy0 - 0.01, m["red_cloth"], folds=15, depth=0.012, segments=(90, 8))
    cloth("coffin_skirt_back", coll, sx0, sx1, skirt[1], skirt[0], sy1 + 0.01, m["red_cloth"], folds=15, depth=0.012, segments=(90, 8))
    cloth("coffin_skirt_head", coll, sy0, sy1, skirt[1], skirt[0], sx0 - 0.01, m["red_cloth"], folds=5, depth=0.012, segments=(30, 8), axis="y")
    cloth("coffin_skirt_foot", coll, sy0, sy1, skirt[1], skirt[0], sx1 + 0.01, m["red_cloth"], folds=5, depth=0.012, segments=(30, 8), axis="y")

    # ---- the body: a hollow box (Act III opens the lid on Sok), lined in dark cloth
    z0 = top + 0.012
    zl = z0 + H
    body = Batch("coffin_body")
    tw, fl = 0.035, 0.03       # wall and floor thickness
    for side in (-1, 1):
        body.box(red, (L, tw, H), (cx, cy + side * (W / 2 - tw / 2), z0 + H / 2), chamfer=0.006, tile=0.45)
        body.box(red, (tw, W - 2 * tw, H), (cx + side * (L / 2 - tw / 2), cy, z0 + H / 2), chamfer=0.006, tile=0.45)
    body.box(red, (L - 2 * tw, W - 2 * tw, fl), (cx, cy, z0 + fl / 2), tile=0.45)
    lining = m["lining"]
    li, lt = 0.006, 0.008      # the lining's gap from the walls and its thickness
    body.box(lining, (L - 2 * tw - li, W - 2 * tw - li, 0.02), (cx, cy, z0 + fl + 0.01), chamfer=0.006, grain=False)
    for side in (-1, 1):
        body.box(lining, (L - 2 * tw - li, lt, H - fl - 0.03), (cx, cy + side * (W / 2 - tw - lt / 2), z0 + fl + (H - fl - 0.03) / 2),
                 grain=False)
        body.box(lining, (lt, W - 2 * tw - 2 * lt, H - fl - 0.03), (cx + side * (L / 2 - tw - lt / 2), cy, z0 + fl + (H - fl - 0.03) / 2),
                 grain=False)
    moulding(body, dark, [(0.03, 0.0), (0.03, 0.022), (0.017, 0.033), (0.009, 0.048), (0.0, 0.056)], cx - L / 2, cx + L / 2, cy - W / 2, cy + W / 2, z0)
    moulding(body, gold, [(0.0, -0.042), (0.01, -0.038), (0.014, -0.026), (0.011, -0.013), (0.005, -0.005), (0.0, 0.0)],
             cx - L / 2, cx + L / 2, cy - W / 2, cy + W / 2, zl)
    for dx in (-1, 1):
        for dy in (-1, 1):
            body.box(gold, (0.026, 0.026, H - 0.1), (cx + dx * L / 2, cy + dy * W / 2, z0 + 0.056 + (H - 0.1) / 2), chamfer=0.004)
    zb, ph = z0 + 0.09, H - 0.17
    seed = 40
    faces = [("long", side, cx + px, 0.5) for side in (-1, 1) for px in (-0.64, 0.0, 0.64)]   # three a side
    faces += [("end", side, cy, 0.44) for side in (-1, 1)]                                     # one an end
    for kind, side, along, pw in faces:
        if kind == "long":
            yf = cy + side * W / 2
            xf = frame((along, yf, zb), (-side, 0, 0), (0, 0, 1), (0, side, 0))
            bars = [((pw + 0.028, 0.008, 0.014), (along, yf + side * 0.004, zb - 0.007)), ((pw + 0.028, 0.008, 0.014), (along, yf + side * 0.004, zb + ph + 0.007)),
                    ((0.014, 0.008, ph), (along - pw / 2 - 0.007, yf + side * 0.004, zb + ph / 2)), ((0.014, 0.008, ph), (along + pw / 2 + 0.007, yf + side * 0.004, zb + ph / 2))]
        else:
            xfc = cx + side * L / 2
            xf = frame((xfc, along, zb), (0, side, 0), (0, 0, 1), (side, 0, 0))
            bars = [((0.008, pw + 0.028, 0.014), (xfc + side * 0.004, along, zb - 0.007)), ((0.008, pw + 0.028, 0.014), (xfc + side * 0.004, along, zb + ph + 0.007)),
                    ((0.008, 0.014, ph), (xfc + side * 0.004, along - pw / 2 - 0.007, zb + ph / 2)), ((0.008, 0.014, ph), (xfc + side * 0.004, along + pw / 2 + 0.007, zb + ph / 2))]
        relief_panel(body, gold, panel_relief(int(pw * 400), int(ph * 400), seed), "rect", pw, ph, 0.007, xf, nu=int(pw * 300), nv=int(ph * 300),
                     base=0.003, ground=red, threshold=0.1)
        seed += 3
        for size, centre in bars:
            body.box(gold, size, centre, chamfer=0.003)
    # Brass drop handles between the panels.
    zh = zl - 0.12
    for side in (-1, 1):
        yf = cy + side * W / 2
        for hx in (cx - 0.32, cx + 0.32):
            body.box(m["brass"], (0.075, 0.006, 0.05), (hx, yf + side * 0.003, zh), chamfer=0.002)
            o = side
            pts = [(hx - 0.03, yf + o * 0.012, zh + 0.008), (hx - 0.033, yf + o * 0.018, zh - 0.022), (hx - 0.022, yf + o * 0.021, zh - 0.048),
                   (hx + 0.022, yf + o * 0.021, zh - 0.048), (hx + 0.033, yf + o * 0.018, zh - 0.022), (hx + 0.03, yf + o * 0.012, zh + 0.008)]
            body.tube(m["brass"], pts, 0.0045, sides=8)
            for ex in (-0.03, 0.03):   # the lugs the bail swings in, standing out of the plate
                body.lathe(m["brass"], [(0, 0), (0.008, 0), (0.008, 0.012), (0, 0.012)],
                           xf=Matrix.Translation((hx + ex, yf, zh + 0.008)) @ Matrix.Rotation(-side * math.pi / 2, 4, "X"), segments=10, tile=0.05)
    body.build(coll)

    # ---- the lid: a slab, a curved gable roof, gilt edges, crest, finials, tails
    lid = Batch("coffin_lid")
    lid.box(red, (L + 0.08, W + 0.08, 0.05), (cx, cy, zl + 0.025), chamfer=0.008, tile=0.45)
    lid.tube(gold, _loop(cx - L / 2 - 0.043, cx + L / 2 + 0.043, cy - W / 2 - 0.043, cy + W / 2 + 0.043, zl + 0.022), 0.006, sides=8)
    zr = zl + 0.05
    Wr, rise = W / 2 + 0.02, 0.15

    def roof(t):
        return t * Wr, rise * (1 - abs(t) ** 1.5)

    lid.grid(red, lambda u, v: (cx - L / 2 + L * u, cy + roof(2 * v - 1)[0], zr + roof(2 * v - 1)[1]), 24, 48,
             uv=lambda u, v: (u * L / 0.45, v * 0.75 / 0.45), smooth=True)
    curve = [roof(t) for t in np.linspace(-1, 1, 33)]
    for side in (-1, 1):
        xe = cx + side * L / 2
        verts = [(xe, cy, zr)] + [(xe, cy + yy, zr + zz) for yy, zz in curve]
        tris = [(0, i + 1, i) if side > 0 else (0, i, i + 1) for i in range(1, len(curve))]
        lid.add(red, verts, tris, [(v[1] / 0.45, v[2] / 0.45) for v in verts], smooth=False)
        relief_panel(lid, gold, kbach_relief(260, 64, 90 + side, kind="pediment"), "tri", 2 * Wr - 0.07, rise - 0.016, 0.006,
                     frame((xe + side * 0.0006, cy, zr + 0.004), (0, side, 0), (0, 0, 1), (side, 0, 0)), nu=180, nv=40, base=0.0015)
        lid.tube(gold, [(xe + side * 0.003, cy + yy, zr + zz + 0.004) for yy, zz in curve], 0.007, sides=8)
        # Upswept tails at the eaves (like a temple gable's hang hong).
        for dy in (-1, 1):
            base = Vector((xe, cy + dy * Wr, zr + 0.004))
            pts = [tuple(base + Vector((side * 0.022 * t, dy * 0.055 * math.sin(t * 1.5), 0.13 * t ** 2.1 - 0.008 * t))) for t in np.linspace(0, 1, 9)]
            lid.tube(gold, pts, list(np.linspace(0.011, 0.0025, 9)), sides=8, cap_end=True)
    for dy in (-1, 1):
        lid.tube(gold, [(cx - L / 2, cy + dy * Wr, zr + 0.003), (cx + L / 2, cy + dy * Wr, zr + 0.003)], 0.006, sides=8)
    ridge = zr + rise + 0.004
    lid.tube(gold, [(cx - L / 2 - 0.01, cy, ridge), (cx + L / 2 + 0.01, cy, ridge)], 0.011, sides=10)
    kx = cx - L / 2 + 0.42    # the krama lies across the lid over the head
    flames = np.arange(cx - L / 2 + 0.1, cx + L / 2 - 0.08, 0.1)
    for k, fx in enumerate(flames):
        if abs(fx - kx) < 0.22:
            continue
        hgt = 0.05 + 0.035 * math.cos(math.pi * (fx - cx) / L) ** 2
        outline = flame_outline(hgt, 0.05, 0.012 if k % 2 else -0.012)
        lid.extrude(gold, outline, 0.005, xf=frame((fx, cy, ridge + 0.004), (1, 0, 0), (0, 0, 1), (0, -1, 0)), tile=0.1)
        for sgn in (-1, 1):   # the two curled leaves leaning out from each flame's foot
            leaf = flame_outline(hgt * 0.45, 0.026, sgn * 0.009)
            xf = frame((fx + sgn * 0.017, cy, ridge + 0.006), (1, 0, 0), (0, 0, 1), (0, -1, 0)) @ Matrix.Rotation(-sgn * 0.75, 4, "Z")
            lid.extrude(gold, leaf, 0.004, xf=xf, tile=0.1)
    tips = []
    for side in (-1, 1):
        fx = cx + side * (L / 2 - 0.035)
        lid.box(gold, (0.06, 0.06, 0.026), (fx, cy, ridge + 0.016), chamfer=0.004)
        bud = [(0.028, 0), (0.032, 0.012), (0.022, 0.026), (0.036, 0.05), (0.043, 0.08), (0.036, 0.118), (0.02, 0.148), (0.006, 0.172), (0, 0.18)]
        lid.lathe(gold, bud, xf=place(fx, cy, ridge + 0.029), segments=20, tile=0.1,
                  radial=lambda a, h: 1 + 0.06 * max(0.0, math.cos(a * 8)) * (h > 0.04))
        tips.append(Vector((fx, cy, ridge + 0.21)))
    lid.build(coll)

    # ---- the checked krama across the lid over the head, its fringes hanging
    # Its path across the lid as (y, z): down the front, over the slab's lip, up the roof
    # and over the ridge (riding up over the gilt ridge pole), down the back.
    path = [(cy - W / 2 - 0.052, zl - 0.13), (cy - W / 2 - 0.052, zl + 0.03), (cy - W / 2 - 0.045, zl + 0.056), (cy - Wr - 0.004, zr + 0.008)]
    path += [(cy + yy, zr + zz + 0.008 + 0.014 * math.exp(-(yy / 0.06) ** 2)) for yy, zz in (roof(t) for t in np.linspace(-0.96, 0.96, 41))]
    path += [(cy + Wr + 0.004, zr + 0.008), (cy + W / 2 + 0.045, zl + 0.056), (cy + W / 2 + 0.052, zl + 0.03), (cy + W / 2 + 0.052, zl - 0.1)]
    seg = [0.0] + list(np.cumsum([math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]))
    total = seg[-1]

    def along(s):
        s = min(max(s, 0.0), total)
        i = max(0, min(len(seg) - 2, int(np.searchsorted(seg, s) - 1)))
        f = (s - seg[i]) / max(seg[i + 1] - seg[i], 1e-6)
        return path[i][0] + (path[i + 1][0] - path[i][0]) * f, path[i][1] + (path[i + 1][1] - path[i][1]) * f

    kw = 0.32
    ph_ = rng.uniform(0, 6)

    def krama_pt(u, v):
        yy, zz = along(v * total)
        hang = max(0.0, abs(zz - zl) * (zz < zl + 0.02))
        x = kx - kw / 2 + kw * u + 0.012 * math.sin(v * 9 + ph_) + 0.03 * hang * (u - 0.5)
        lift = 0.004 * math.sin(u * math.pi * 5 + v * 3)
        return (x, yy + (-0.006 if yy < cy else 0.006) * math.sin(u * math.pi * 4) * (hang > 0), zz + lift)

    b = Batch("coffin_krama")
    b.grid(m["krama"], krama_pt, 16, 90, uv=lambda u, v: (u * kw / 0.3, v * total / 0.3), smooth=True)
    for v, sgn in ((0.0, -1), (1.0, 1)):
        for k in range(22):
            u = (k + 0.5) / 22
            p = Vector(krama_pt(u, v))
            b.tube(m["krama"], [tuple(p), tuple(p + Vector((rng.normal(0, 0.003), sgn * 0.004, -rng.uniform(0.025, 0.04))))], [0.0022, 0.0015],
                   sides=4, cap_end=True)
    b.build(coll, prefix="coffin_cloth_krama")

    # ---- marigold and jasmine swags along the front, hung from the lid's edge
    gb = Batch("coffin_garland")
    anchors = [cx - 0.92, cx - 0.31, cx + 0.31, cx + 0.92]
    yf = cy - W / 2 - 0.068
    for a0, a1 in zip(anchors, anchors[1:]):
        n = 18
        line = []
        for i in range(n + 1):
            t = i / n
            line.append(Vector((a0 + (a1 - a0) * t, yf + 0.03 * 4 * t * (1 - t), zl + 0.03 - 0.1 * 4 * t * (1 - t))))
        for i, p in enumerate(line):
            ok.marigold(gb, m, p + Vector((0, 0, -0.017)), rng, radius=rng.uniform(0.015, 0.019), dead=rng.random() < 0.3)
        ok.jasmine_string(gb, m, [tuple(p + Vector((0, -0.02, -0.006))) for p in line], rng)
    for ax in anchors:
        drop = [Vector((ax, yf - 0.004, zl + 0.03 - 0.036 * j)) for j in range(4)]
        for p in drop[1:]:
            ok.marigold(gb, m, p, rng, radius=0.014, dead=rng.random() < 0.3)
        ok.jasmine_string(gb, m, [tuple(p + Vector((0, -0.012, 0))) for p in drop] + [tuple(drop[-1] + Vector((0, -0.012, -0.06)))], rng)
    gb.build(coll)

    # ---- the monks' white thread, wound round the body and run out to their table
    zt = zl - 0.058
    tb = Batch("coffin_thread")
    for k in range(2):
        e = 0.0165 + 0.0035 * k
        tb.tube(m["thread"], _loop(cx - L / 2 - e, cx + L / 2 + e, cy - W / 2 - e, cy + W / 2 + e, zt - 0.006 * k), 0.0016, sides=5)
    tb.build(coll)
    knot = Vector((cx - L / 2 - 0.02, cy - 0.06, zt))

    # ---- the seep: a dark glossy stain spreading on the earth from under the foot
    sxp, syp = sx1 - 0.12, sy0 + 0.05
    for k, (dx, dy, rad) in enumerate(((0.0, 0.0, 0.2), (0.16, -0.22, 0.05), (0.05, -0.3, 0.03))):
        verts = [(sxp + dx, syp + dy, ground(sxp + dx, syp + dy) + 0.004)]
        ph0 = rng.uniform(0, 6)
        for i in range(36):
            a = math.tau * i / 36
            rr = rad * (1 + 0.28 * math.sin(3 * a + ph0) + 0.12 * math.sin(7 * a + 2 * ph0)) * (1.25 if math.sin(a) < 0 else 0.85)
            x, y = sxp + dx + math.cos(a) * rr, syp + dy + math.sin(a) * rr
            verts.append((x, y, ground(x, y) + 0.004))
        mesh_object(f"coffin_seep_{k}", coll, verts, [(0, i + 1, (i + 1) % 36 + 1) for i in range(36)], m["seep"], smooth=True)
    return knot, lit


def thread_to(coll, m, start, end, rng):
    """The monks' thread from the coffin to their table, sagging, coiled at its end."""
    pts = sag(tuple(start), tuple(end), 0.22, n=28)
    coil = [tuple(Vector(end) + Vector((0.035 * math.cos(a), 0.035 * math.sin(a), 0.002 + 0.0008 * a))) for a in np.linspace(0, math.tau * 2.5, 30)]
    tube("coffin_thread_run", coll, pts + coil, 0.0015, m["thread"], sides=5)


def build(coll, ground, rng, portrait_image, coffin_objects=()):
    """The whole funeral under the house. `coffin_objects` (the coffin's meshes) are moved
    under the canopy. Returns (flame tips, light points)."""
    m = materials()
    x0, x1, y0, y1 = AREA
    flames, glows = [], []
    # Banners: the wide parinirvana behind the coffin, the tall ones either side of it and
    # down the sides.
    hang_banner(coll, m, "banner_nirvana", AXIS - 1.45, AXIS + 1.45, y1 - 0.15, JOISTS - 0.05, 2.0, seed=1)
    for k, (bx, by) in enumerate(((AXIS - 2.75, y1 - 0.2), (AXIS + 2.75, y1 - 0.2))):
        hang_banner(coll, m, "banner_mara", bx - 0.6, bx + 0.6, by, JOISTS - 0.05, 1.6, seed=10 + k)
    for k, (sx, sy) in enumerate(((x0 + 0.1, 17.0), (x1 - 0.1, 17.0))):
        hang_banner(coll, m, "banner_mara", sy - 0.6, sy + 0.6, sx, JOISTS - 0.05, 1.6, axis="y", seed=20 + k)
    # The coffin under its canopy (the hall's old coffin is retired).
    cx, cy = COFFIN
    for o in coffin_objects:
        o.hide_render = o.hide_viewport = True
    canopy(coll, m, ground, cx, cy, w=2.4)
    knot, lit = coffin(coll, m, ground, rng, cx, cy)
    flames += lit
    mx, my = MONKS
    thread_to(coll, m, knot, (mx + 0.25, my - 0.12, ground(mx, my) + 0.625), rng)
    wreath_portrait(coll, m, ground, rng, *WREATH, portrait_image)
    lit, smoke = incense_and_candles(coll, m, ground, rng)
    flames += lit
    flames += offering_table(coll, m, ground, rng, *TABLE)
    # Lotus-cone candles round the coffin and along the mats.
    b = Batch("fu_lotus_candles")
    for k in range(14):
        a = math.tau * k / 14
        lx, ly = cx + math.cos(a) * 1.85, cy + math.sin(a) * 1.25
        if ly > y1 - 0.4 or ly < y0 or not clear(lx, ly, 0.07):
            continue
        flames.append(lotus_cone(b, m, lx, ly, ground(lx, ly) + 0.012, rng, lit=rng.random() < 0.8))
    b.build(coll)
    mats(coll, m, ground, AXIS - 3.9, AXIS + 2.0, y0 + 0.2, cy - 0.9, rng)
    flames += monks_table(coll, m, ground, rng, *MONKS)
    glows.append(fire_pot(coll, m, ground, rng, *FIRE))
    glows.append(bulb(coll, m, AXIS + 1.1, 15.6))
    return m, flames, glows, smoke


# ------------------------------------------------------------------ the dread pass (Nov 23)
# The funeral after three nights: the candles guttered, the wreath going brown, the fruit
# rotting, the coffin seeping; bare muddy footprints that walk up to it and not away, long
# black hair caught in its lid, soot handprints on the offering table's cloth, the mourners'
# sandals left where they stood, torn white cloths hanging from the joists. Realistic, not
# gory; the rites themselves stay whole (advisor review: the hair and the footprints).

def _mats_extent(x0, x1, y0, y1, w=0.9, d=1.8):
    """Where mats() really lays its mats: its last row and column run on past x1, y1."""
    xs, ys = [x0], [y0]
    while xs[-1] + w - 0.04 < x1:
        xs.append(xs[-1] + w - 0.04)
    while ys[-1] + d - 0.05 < y1:
        ys.append(ys[-1] + d - 0.05)
    return (x0, xs[-1] + w, y0, ys[-1] + d)


# The mats' extent (x0, x1, y0, y1), as build() lays them (to y 17.5, under the stand's front).
MATS = _mats_extent(AXIS - 3.9, AXIS + 2.0, AREA[2] + 0.2, COFFIN[1] - 0.9)


def _save_rgba(name, rgba):
    h, w = rgba.shape[:2]
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=True)
    img.pixels[:] = np.clip(rgba[::-1], 0, 1).astype(np.float32).ravel()
    path = os.path.join(TEX, name + ".png")
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


def _noise(shape, rng, scales=((8, 0.5), (24, 0.3), (64, 0.2))):
    """Smooth value noise in 0..1 from a few upsampled random grids."""
    h, w = shape
    out = np.zeros(shape, np.float32)
    for cells, amp in scales:
        g = rng.random((cells + 1, cells + 1)).astype(np.float32)
        ys, xs = np.linspace(0, cells, h), np.linspace(0, cells, w)
        y0, x0 = np.floor(ys).astype(int).clip(0, cells - 1), np.floor(xs).astype(int).clip(0, cells - 1)
        fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        a, b = g[y0][:, x0], g[y0][:, x0 + 1]
        c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
    return out / sum(a for _c, a in scales)


def _ellipse(x, y, cx, cy, rx, ry, a=0.0):
    c, s = math.cos(a), math.sin(a)
    dx, dy = x - cx, y - cy
    u, v = c * dx + s * dy, -s * dx + c * dy
    return (u / rx) ** 2 + (v / ry) ** 2


def footprint_texture():
    """A bare muddy footprint, toes up: heel, outer arch, ball and five toes; ragged."""
    path = os.path.join(TEX, "T_ep1_fu_footprint_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(611)
    h, w = 512, 256
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    y, x = 1 - y / h, x / w
    d = np.minimum.reduce([
        _ellipse(x, y, 0.5, 0.17, 0.2, 0.14),            # heel
        _ellipse(x, y, 0.62, 0.42, 0.12, 0.2, 0.15),     # the outer arch
        _ellipse(x, y, 0.5, 0.66, 0.29, 0.11, -0.1),     # ball
        _ellipse(x, y, 0.3, 0.84, 0.085, 0.075),         # big toe
        _ellipse(x, y, 0.47, 0.86, 0.055, 0.05),
        _ellipse(x, y, 0.6, 0.84, 0.05, 0.045),
        _ellipse(x, y, 0.71, 0.8, 0.045, 0.04),
        _ellipse(x, y, 0.8, 0.75, 0.04, 0.036)])
    n = _noise((h, w), rng)
    dd = d + (n - 0.5) * 0.9
    alpha = (dd < 1.0).astype(np.float32)
    col = np.empty((h, w, 4), np.float32)
    # Wet black mud in the middle drying pale at the edges, so it reads on the red mats.
    wet = np.array((0.06, 0.045, 0.032), np.float32)
    dry = np.array((0.3, 0.24, 0.17), np.float32)
    rim = np.clip((dd - 0.45) / 0.55, 0, 1)[..., None]
    col[..., :3] = (wet * (1 - rim) + dry * rim) * (0.8 + 0.4 * n[..., None])
    col[..., 3] = alpha
    return _save_rgba("T_ep1_fu_footprint_BC", col)


def handprint_texture():
    """A soot handprint dragged down: palm, four fingers and a thumb, smeared below."""
    path = os.path.join(TEX, "T_ep1_fu_handprint_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(612)
    h, w = 512, 256
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    y, x = 1 - y / h, x / w
    hand = np.minimum.reduce([
        _ellipse(x, y, 0.5, 0.52, 0.27, 0.13),
        _ellipse(x, y, 0.3, 0.76, 0.055, 0.12, 0.12), _ellipse(x, y, 0.44, 0.8, 0.055, 0.14, 0.03),
        _ellipse(x, y, 0.58, 0.79, 0.052, 0.135, -0.05), _ellipse(x, y, 0.7, 0.73, 0.048, 0.11, -0.15),
        _ellipse(x, y, 0.8, 0.5, 0.05, 0.12, -0.9)])
    # The drag: the palm's lower half run down the cloth in streaks.
    streak = np.sin(x * 70 + _noise((h, w), rng, ((6, 1.0),)) * 6) * 0.5 + 0.5
    drag = (y < 0.45) & (y > 0.05 + 0.25 * np.abs(x - 0.5)) & (np.abs(x - 0.5) < 0.27) & (streak > 0.35 + (0.45 - y))
    n = _noise((h, w), rng)
    alpha = (((hand + (n - 0.5) * 0.7) < 1.0) | drag).astype(np.float32)
    col = np.empty((h, w, 4), np.float32)
    col[..., :3] = np.array((0.035, 0.032, 0.03), np.float32) * (0.7 + 0.6 * n[..., None])
    col[..., 3] = alpha
    return _save_rgba("T_ep1_fu_handprint_BC", col)


def stain_texture(name, colour, seed, runnels=0):
    """An irregular stain (seep, soot, spill): a noisy blob with runnels out of it."""
    path = os.path.join(TEX, name + ".png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    n = 512
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n - 0.5
    r = np.hypot(x, y)
    a = np.arctan2(y, x)
    edge = 0.3 + 0.08 * np.sin(a * 3 + 1) + 0.05 * np.sin(a * 7 + 2) + (_noise((n, n), rng) - 0.5) * 0.18
    alpha = (r < edge).astype(np.float32)
    for k in range(runnels):
        ang = rng.uniform(0, math.tau)
        length = rng.uniform(0.12, 0.2)
        width = rng.uniform(0.012, 0.025)
        along = x * math.cos(ang) + y * math.sin(ang)
        across = -x * math.sin(ang) + y * math.cos(ang)
        alpha[(along > 0.2) & (along < 0.2 + length) & (np.abs(across - 0.02 * np.sin(along * 40)) < width * (1.2 - (along - 0.2) / length))] = 1
    tone = _noise((n, n), rng)
    col = np.empty((n, n, 4), np.float32)
    col[..., :3] = np.array(colour, np.float32) * (0.7 + 0.6 * tone[..., None])
    col[..., 3] = alpha
    return _save_rgba(name, col)


def drips_texture():
    """Runs of seep down a cloth from its top edge: thin, uneven, beaded at their ends."""
    path = os.path.join(TEX, "T_ep1_fu_drips_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(614)
    h, w = 512, 256
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    y, x = y / h, x / w
    alpha = np.zeros((h, w), np.float32)
    for k in range(9):
        cx = rng.uniform(0.08, 0.92)
        length = rng.uniform(0.25, 0.95)
        wid = rng.uniform(0.008, 0.02)
        wob = cx + 0.01 * np.sin(y * rng.uniform(15, 30) + k)
        line = (np.abs(x - wob) < wid * (1.4 - 0.6 * y / length)) & (y < length)
        bead = _ellipse(x, y, cx, length, wid * 1.8, wid * 2.4 * w / h) < 1
        alpha[line | bead] = 1
    alpha[y < 0.04 + 0.03 * np.sin(x * 20)] = 1        # the soaked edge along the top
    col = np.empty((h, w, 4), np.float32)
    col[..., :3] = np.array((0.11, 0.065, 0.03), np.float32) * (0.8 + 0.4 * _noise((h, w), rng)[..., None])
    col[..., 3] = alpha
    return _save_rgba("T_ep1_fu_drips_BC", col)


def dread_materials(m):
    out = {}
    out["footprint"] = image_material("M_fu_footprint", footprint_texture(), rough=0.45, cutout=True)
    out["handprint"] = image_material("M_fu_handprint", handprint_texture(), rough=0.9, cutout=True)
    out["seep"] = image_material("M_fu_seep", stain_texture("T_ep1_fu_seep_BC", (0.05, 0.022, 0.012), 615, runnels=5), rough=0.15, cutout=True)
    out["soot"] = image_material("M_fu_soot", stain_texture("T_ep1_fu_soot_BC", (0.022, 0.021, 0.02), 616), rough=0.95, cutout=True)
    out["spill"] = image_material("M_fu_spill", stain_texture("T_ep1_fu_spill_BC", (0.07, 0.04, 0.03), 617, runnels=2), rough=0.3, cutout=True)
    out["drips"] = image_material("M_fu_drips", drips_texture(), rough=0.35, cutout=True)
    out["hair"] = plain("M_fu_hair", (0.012, 0.011, 0.01), rough=0.42)
    out["petal_brown"] = plain("M_fu_petal_brown", (0.3, 0.17, 0.05), rough=0.85)
    out["petal_yellow"] = plain("M_fu_petal_yellow", (0.5, 0.38, 0.1), rough=0.8)
    out["petal_white"] = plain("M_fu_petal_white", (0.46, 0.41, 0.31), rough=0.85)
    out["rot"] = plain("M_fu_rot_banana", (0.05, 0.035, 0.018), rough=0.55)
    out["mould"] = plain("M_fu_mould", (0.3, 0.33, 0.26), rough=0.95)
    out["sole"] = plain("M_fu_sandal_sole", (0.07, 0.055, 0.04), rough=0.75)
    out["strap"] = plain("M_fu_sandal_strap", (0.17, 0.1, 0.05), rough=0.7)
    out["stool"] = plain("M_fu_stool_wood", (0.22, 0.14, 0.08), rough=0.7)
    out["tin"] = plain("M_fu_tin", (0.42, 0.42, 0.4), rough=0.45, metal=0.8)
    out["liquid"] = plain("M_fu_bowl_seep", (0.025, 0.01, 0.006), rough=0.08)
    out["rag"] = library_material("rough_linen", "M_fu_rag_cloth", tint=(0.58, 0.54, 0.46), tile=0.5)
    for k in ("rag",):
        out[k].use_backface_culling = False
    return out


def _surface(ground, x, y):
    """The top of what lies there: the mats (both layers) or the bare earth."""
    x0, x1, y0, y1 = MATS
    return ground(x, y) + (0.036 if x0 - 0.05 < x < x1 + 0.05 and y0 - 0.05 < y < y1 + 0.05 else 0.004)


def decal(coll, name, mat, ground, cx, cy, w, h, angle, lift=0.003, n=4, flip=False):
    """A flat decal draped over the mats or the earth (toes / top along +v at `angle`)."""
    c, s = math.cos(angle), math.sin(angle)
    verts, faces, uvs = [], [], []
    for j in range(n + 1):
        for i in range(n + 1):
            u, v = i / n, j / n
            dx, dy = w * (u - 0.5), h * (v - 0.5)
            px, py = cx + c * dx - s * dy, cy + s * dx + c * dy
            verts.append((px, py, _surface(ground, px, py) + lift))
            uvs.append((1 - u if flip else u, v))
    faces = [(j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1, (j + 1) * (n + 1) + i) for j in range(n) for i in range(n)]
    return mesh_object(name, coll, verts, faces, mat, uvs=[uvs[k] for f in faces for k in f])


def wall_decal(coll, name, mat, x0, x1, z0, z1, y, facing=-1):
    """An upright decal on a face at y (facing -y or +y)."""
    verts = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    face = [(0, 1, 2, 3)] if facing < 0 else [(3, 2, 1, 0)]
    uv = [(0, 0), (1, 0), (1, 1), (0, 1)] if facing < 0 else [(0, 1), (1, 1), (1, 0), (0, 0)]
    return mesh_object(name, coll, verts, face, mat, uvs=uv)


def dread(coll, m, ground, rng):
    """The funeral gone wrong, over the built funeral (see the section's note)."""
    d = dread_materials(m)
    cx, cy = COFFIN
    L, W, H = COFFIN_SIZE
    g0 = ground(cx, cy)
    top = g0 + STAND_H + H          # the lid's seam
    front = cy - W / 2               # the coffin's south side
    stand_front = cy - (W / 2 + 0.16)

    # The seep: a wet pool spreading from under the stand's front, runs down its cloth,
    # and a clay bowl someone set under the worst of it.
    decal(coll, "fu_dread_seep_pool", d["seep"], ground, cx + 0.15, stand_front - 0.12, 1.1, 0.75, 0.08, lift=0.004)
    decal(coll, "fu_dread_seep_run", d["seep"], ground, cx - 0.35, stand_front - 0.45, 0.45, 0.55, 0.4, lift=0.005)
    wall_decal(coll, "fu_dread_stand_drips", d["drips"], cx - 0.2, cx + 0.55, g0 + 0.02, g0 + STAND_H - 0.01, stand_front - 0.012)
    bb = Batch("fu_dread_bowl")
    bx, by = cx + 0.55, stand_front - 0.18
    bz = _surface(ground, bx, by)
    bb.lathe(m["clay"], [(0, 0), (0.05, 0), (0.075, 0.025), (0.085, 0.05), (0.08, 0.052), (0.07, 0.028), (0.0, 0.02)],
             xf=place(bx, by, bz), segments=24, tile=0.25)
    bb.lathe(d["liquid"], [(0, 0.038), (0.074, 0.038), (0.0, 0.0381)], xf=place(bx, by, bz), segments=24)
    bb.build(coll)

    # Long black hair caught in the lid's seam at the head end, hanging down its side.
    hb = Batch("fu_dread_hair")
    head = cx - L / 2
    for k in range(70):
        x = head + 0.06 + rng.uniform(0, 0.38) ** 1.3
        drop = rng.uniform(0.18, 0.46)
        sway = rng.normal(0, 0.012)
        pts = []
        for i in range(11):
            t = i / 10
            out = 0.004 + 0.02 * math.sin(min(t * 3, 1.0) * math.pi / 2)
            pts.append((x + sway * t + 0.006 * math.sin(t * 9 + k), front - out, top + 0.004 - drop * t ** 1.15))
        hb.tube(d["hair"], pts, [0.0009 - 0.0003 * i / 10 for i in range(11)], sides=4)
    hb.build(coll)

    # Bare muddy footprints out of the dark west, up the mats to the coffin; none go back.
    path = [(-4.6, 13.2), (-3.9, 13.6), (-3.1, 14.0), (-2.35, 14.45), (-1.55, 14.9), (-0.8, 15.4), (-0.1, 15.9), (0.5, 16.35), (0.95, 16.75)]
    for k, (fx, fy) in enumerate(path):
        nx, ny = path[min(k + 1, len(path) - 1)]
        px, py = path[max(k - 1, 0)]
        ang = math.atan2(ny - py, nx - px) - math.pi / 2
        side = 1 if k % 2 else -1
        ox, oy = math.cos(ang) * 0.07 * side, math.sin(ang) * 0.07 * side
        decal(coll, f"fu_dread_foot_{k}", d["footprint"], ground, fx + ox, fy + oy, 0.11, 0.26, ang + rng.normal(0, 0.06),
              lift=0.003 + 0.0005 * k, flip=side > 0)

    # Soot handprints dragged down the offering table's white front cloth.
    tx, ty = TABLE
    tg = ground(tx, ty)
    for k, (hx, hz, a) in enumerate(((tx - 0.35, 0.38, 0.1), (tx + 0.08, 0.3, -0.12), (tx + 0.42, 0.42, 0.05))):
        wall_decal(coll, f"fu_dread_handprint_{k}", d["handprint"], hx - 0.07, hx + 0.07, tg + hz - 0.2, tg + hz + 0.08, ty - 0.375)

    # The candles: burnt to stubs in their pools, some knocked over, soot on the mats.
    cb = Batch("fu_dread_candles")
    spots = [(tx - 0.75, ty - 0.55), (tx + 0.8, ty - 0.5), (tx - 1.3, ty + 0.4), (tx + 1.35, ty + 0.6), (cx - 1.0, cy - 1.1),
             (cx + 1.1, cy - 1.15), (-0.4, 13.2), (2.9, 13.4)]
    for k, (sx, sy) in enumerate(spots):
        if not clear(sx, sy, 0.08):
            continue
        sz = _surface(ground, sx, sy)
        if k % 3 == 2:   # knocked over, rolled a little, its wax run out on the mat
            ok.candle(cb, m, place(sx, sy, sz + 0.011, rz=rng.uniform(0, math.tau)) @ Matrix.Rotation(1.57, 4, "X"), rng,
                      height=rng.uniform(0.07, 0.11), radius=0.011, melt=0.8, lit=False)
            decal(coll, f"fu_dread_soot_{k}", d["soot"], ground, sx + 0.06, sy + 0.04, 0.22, 0.14, rng.uniform(0, 3), lift=0.002)
        else:
            ok.candle_dish(cb, m, place(sx, sy, sz), rng, radius=0.05, melt=1.0)
            ok.candle(cb, m, place(sx, sy, sz + 0.006), rng, height=rng.uniform(0.012, 0.03), radius=0.012, melt=1.0, lit=False)
            if k % 2:
                decal(coll, f"fu_dread_soot_{k}", d["soot"], ground, sx, sy + 0.08, 0.16, 0.2, rng.normal(0, 0.3), lift=0.002)
    cb.build(coll)

    # The wreath going brown: dead petals fallen round its foot and under the table.
    pb = {k: Batch(f"fu_dread_petals_{k}") for k in ("petal_brown", "petal_yellow", "petal_white")}
    wx, wy = WREATH
    for k in range(520):
        if k < 360:
            r, a = abs(rng.normal(0, 0.45)), rng.uniform(0, math.tau)
            px, py = wx + r * math.cos(a) * 1.4, wy + r * math.sin(a) * 0.7 - 0.15
        else:
            px, py = tx + rng.normal(0, 0.45), ty + rng.normal(0, 0.3)
        if not clear(px, py, 0.02):
            continue
        key = ("petal_brown", "petal_yellow", "petal_white")[int(rng.choice(3, p=(0.55, 0.3, 0.15)))]
        pw, pl = rng.uniform(0.008, 0.014), rng.uniform(0.02, 0.035)
        a = rng.uniform(0, math.tau)
        c, s = math.cos(a), math.sin(a)
        z = _surface(ground, px, py) + 0.002 + rng.uniform(0, 0.004)
        curl = rng.uniform(0.002, 0.008)
        q = [(-pw / 2, -pl / 2, curl), (pw / 2, -pl / 2, curl), (pw / 2, pl / 2, 0), (-pw / 2, pl / 2, 0)]
        pts = [(px + c * qx - s * qy, py + s * qx + c * qy, z + qz) for qx, qy, qz in q]
        pb[key].add(d[key], pts, [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)
    for b in pb.values():
        b.build(coll)

    # Fruit fallen from the table and rotting on the mat: blackened bananas, a mouldy orange.
    fb = Batch("fu_dread_fruit")
    for k, (fx, fy, fa) in enumerate(((tx - 0.3, ty - 0.55, 0.4), (tx + 0.25, ty - 0.62, 2.2))):
        fz = _surface(ground, fx, fy)
        pts, rad = [], []
        for i in range(9):
            t = i / 8
            bend = 0.05 * math.sin(t * math.pi)
            lx, ly = (t - 0.5) * 0.19, bend
            pts.append((fx + math.cos(fa) * lx - math.sin(fa) * ly, fy + math.sin(fa) * lx + math.cos(fa) * ly, fz + 0.016))
            rad.append(0.008 + 0.009 * math.sin(math.pi * min(1, t * 1.2)))
        fb.tube(d["rot"], pts, rad, sides=7, cap_end=True)
    ox_, oy_ = tx - 0.62, ty - 0.48
    oz = _surface(ground, ox_, oy_)
    fb.lathe(d["mould"], [(0, 0), (0.025, 0.004), (0.036, 0.02), (0.038, 0.035), (0.03, 0.055), (0.012, 0.064), (0, 0.065)],
             xf=place(ox_, oy_, oz - 0.004) @ Matrix.Scale(1.0, 4) @ Matrix.Diagonal((1.0, 1.0, 0.8, 1.0)), segments=18)
    fb.build(coll)

    # The mourners' sandals, left in pairs at the mats' edge as they knelt; one alone by
    # the coffin, one upturned. An overturned stool and a spilled tin cup by the monks.
    sb = Batch("fu_dread_sandals")
    pairs = [(-1.6, 12.35, 0.05), (-0.7, 12.32, -0.1), (0.4, 12.36, 0.12), (2.3, 12.34, -0.05), (-2.35, 13.6, 1.62), (-2.36, 14.7, 1.5)]
    singles = [(0.45, 16.95, 0.9, False), (3.1, 13.0, 2.4, True)]

    def sandal(x, y, a, upturned=False):
        z = _surface(ground, x, y)
        xf = place(x, y, z, rz=a)
        if upturned:
            xf = xf @ Matrix.Translation((0, 0, 0.012)) @ Matrix.Rotation(math.pi, 4, "Y")
        sb.box(d["sole"], (0.095, 0.25, 0.012), (0, 0, 0.006), xf=xf, chamfer=0.004)
        if not upturned:
            for s_ in (-1, 1):
                sb.tube(d["strap"], [tuple(xf @ Vector(p)) for p in ((0, 0.065, 0.013), (0.02 * s_, 0.03, 0.03), (0.045 * s_, -0.01, 0.013))],
                        0.004, sides=5)
    for x, y, a in pairs:
        c, s = math.cos(a), math.sin(a)
        for k, off in enumerate((-0.06, 0.06)):
            sandal(x + c * off + rng.normal(0, 0.01), y + s * off + rng.normal(0, 0.01), a + rng.normal(0, 0.15))
    for x, y, a, up in singles:
        sandal(x, y, a, up)
    sb.build(coll)
    st = Batch("fu_dread_stool")
    mx, my = MONKS
    sx, sy = mx + 0.95, my - 1.1
    sz = _surface(ground, sx, sy)
    xf = place(sx, sy, sz + 0.15, rz=0.6) @ Matrix.Rotation(math.pi / 2, 4, "X")
    st.box(d["stool"], (0.3, 0.3, 0.03), (0, 0, 0.165), xf=xf, chamfer=0.006)
    for lx in (-0.12, 0.12):
        for ly in (-0.12, 0.12):
            st.box(d["stool"], (0.03, 0.03, 0.3), (lx, ly, 0.0), xf=xf, chamfer=0.003)
    cx_, cy_ = sx + 0.45, sy + 0.2
    cz = _surface(ground, cx_, cy_)
    st.lathe(d["tin"], [(0, 0), (0.035, 0), (0.037, 0.08), (0.034, 0.08), (0.032, 0.004), (0, 0.004)],
             xf=place(cx_, cy_, cz + 0.037, rz=1.1) @ Matrix.Rotation(math.pi / 2, 4, "Y"), segments=18)
    st.build(coll)
    decal(coll, "fu_dread_spill", d["spill"], ground, cx_ + 0.18, cy_ + 0.05, 0.42, 0.3, 1.1, lift=0.002)

    # Torn white cloths hung from the joists round the funeral, stained at their hems.
    for k, (hx, hy, along, width, length) in enumerate((
            (-2.3, 13.3, "x", 0.32, 1.25), (-2.7, 16.4, "y", 0.28, 1.45), (-1.2, 19.7, "x", 0.36, 1.1),
            (4.1, 19.5, "x", 0.3, 1.35), (4.7, 16.2, "y", 0.34, 1.0), (4.3, 13.1, "x", 0.26, 1.5), (-0.7, 12.5, "x", 0.3, 0.9))):
        verts, faces, uvs = [], [], []
        nu, nv = 6, 14
        rr = np.random.default_rng(800 + k)
        hem = [length * rr.uniform(0.82, 1.0) for _ in range(nu + 1)]
        for j in range(nv + 1):
            for i in range(nu + 1):
                u, v = i / nu, j / nv
                a_ = (u - 0.5) * width
                drop = hem[i] * v
                wave = 0.025 * math.sin(u * 7 + k) * v + 0.01 * math.sin(v * 9 + i)
                x, y = (hx + a_, hy + wave) if along == "x" else (hx + wave, hy + a_)
                verts.append((x, y, JOISTS - 0.01 - drop))
                uvs.append((u * width / 0.5, v * length / 0.5))
        faces = [(j * (nu + 1) + i, j * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i + 1, (j + 1) * (nu + 1) + i)
                 for j in range(nv) for i in range(nu)]
        mesh_object(f"fu_dread_rag_{k}", coll, verts, faces, d["rag"], uvs=[uvs[q] for f in faces for q in f], smooth=True)
    return d
