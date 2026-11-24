"""Dressing for the rooms the re-planned house (tools/areas/stilt_house.py) adds or
changes, November 21, 2026: the washing room behind the altar (the slatted board the
body was washed on, the basin under it, water jars, coconut halves, the clothes folded
for the coffin), Yay Mey's floor loom with a hol silk half woven, Kanha's room kept as
it was in 1920 (her rag doll, her drawings pinned up, the mirror covered), the
padlocked room of Sok's clinic logs (ledgers, specimen jars, a chair turned to the
wall), and the attic's old belongings (trunks, baskets, a dress form under a sheet).

Blender metres, X east, Y north, Z up. Builders take a collection, the materials dict
from `materials()` and a numpy Generator; each returns the flame tips it lit.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import offerings_kit as ok
import stilt_house as SH
from kit import ROOT, box, cloth, image_material, import_model, library_material, mesh_object, plain, tube
from shrine_craft import Batch, place

FLOOR, ZW = SH.FLOOR, SH.ZW
TEX = os.path.join(ROOT, "art-source", "textures", "ep1")


# ------------------------------------------------------------------ textures


def _save(name, px):
    path = os.path.join(TEX, name + ".png")
    h, w = px.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=px.shape[2] == 4)
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :px.shape[2]] = px
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


def silk_texture():
    """A Khmer hol silk: a maroon ground with ikat diamonds and zigzags in gold, green and
    black, their edges feathered where the tie-dyed threads slipped."""
    path = os.path.join(TEX, "T_ep1_hol_silk_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(1931)
    n = 512
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    x = x + rng.normal(0, 2.2, (n, 1)).astype(np.float32)  # each weft row slips a little
    u, v = (x % 64) / 64.0, (y % 96) / 96.0
    d = np.abs(u - 0.5) * 2 + np.abs(v - 0.5) * 2
    col = np.zeros((n, n, 3), np.float32)
    col[:] = (0.34, 0.05, 0.06)
    col[(d > 0.55) & (d < 0.7)] = (0.66, 0.48, 0.12)
    col[(d > 0.25) & (d < 0.35)] = (0.08, 0.22, 0.14)
    col[d < 0.12] = (0.03, 0.02, 0.02)
    band = (y % 192) < 14
    zig = np.abs(((x + (y % 192) * 2) % 24) - 12) < 3
    col[band & zig] = (0.7, 0.55, 0.2)
    col *= (0.88 + 0.12 * rng.random((n, n, 1))).astype(np.float32)
    return _save("T_ep1_hol_silk_BC", col)


def warp_texture():
    """Warp threads with gaps between them (alpha), maroon and undyed."""
    path = os.path.join(TEX, "T_ep1_loom_warp_BC.png")
    if os.path.exists(path):
        return path
    n = 256
    px = np.zeros((n, n, 4), np.float32)
    for i in range(0, n, 3):
        c = (0.42, 0.08, 0.08) if (i // 3) % 5 else (0.75, 0.68, 0.55)
        px[:, i, :3] = c
        px[:, i, 3] = 1.0
    return _save("T_ep1_loom_warp_BC", px)


def materials(hm):
    m = dict(ok.materials())
    m.update(hm)
    m["wet_wood"] = library_material("weathered_brown_planks", "M_nr_wet_planks", tint=(0.4, 0.34, 0.28), tile=1.0)
    m["linen"] = library_material("rough_linen", "M_nr_linen", tint=(0.78, 0.76, 0.7), tile=0.45)
    m["linen"].use_backface_culling = False
    m["jar"] = plain("M_nr_glazed_jar", (0.12, 0.07, 0.04), rough=0.28)
    m["wet_stain"] = plain("M_nr_wet_stain", (0.045, 0.032, 0.024), rough=0.14)
    m["glass"] = plain("M_nr_glass", (0.72, 0.78, 0.72), rough=0.05, alpha=0.28)
    m["murk"] = plain("M_nr_murk", (0.3, 0.28, 0.14), rough=0.2, alpha=0.8)
    m["paper"] = plain("M_nr_paper", (0.7, 0.64, 0.5), rough=0.92)
    m["ledger"] = plain("M_nr_ledger", (0.2, 0.11, 0.07), rough=0.7)
    m["silk"] = image_material("M_nr_silk", silk_texture(), rough=0.45)
    m["warp"] = image_material("M_nr_warp", warp_texture(), rough=0.6, cutout=True)
    m["doll"] = library_material("rough_linen", "M_nr_doll_cloth", tint=(0.66, 0.56, 0.44), tile=0.15)
    m["doll_dress"] = library_material("rough_linen", "M_nr_doll_dress", tint=(0.42, 0.1, 0.1), tile=0.15)
    m["hair"] = plain("M_nr_doll_hair", (0.02, 0.018, 0.016), rough=0.8)
    m["drawing"] = image_material("M_nr_kanha_drawing", os.path.join(TEX, "T_ep1_kanha_drawing_BC.png"), rough=0.92)
    m["clay_lamp"] = library_material("clay_plaster", "M_nr_clay_lamp", tint=(0.55, 0.33, 0.2), tile=0.3)
    return m


def _uvs_planar(obj, u_axis, v_axis, size_u, size_v, off=(0.0, 0.0)):
    me = obj.data
    layer = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = obj.matrix_world @ me.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = ((co[u_axis] - off[0]) / size_u, (co[v_axis] - off[1]) / size_v)


def _stain(name, coll, mat, x, y, z, rx, ry, rng, n=40):
    ph = rng.uniform(0, 6, 3)
    verts = [(x, y, z)]
    for i in range(n):
        a = math.tau * i / n
        r = 1 + 0.25 * math.sin(3 * a + ph[0]) + 0.12 * math.sin(7 * a + ph[1]) + 0.06 * math.sin(13 * a + ph[2])
        verts.append((x + math.cos(a) * rx * r, y + math.sin(a) * ry * r, z))
    return mesh_object(name, coll, verts, [(0, i + 1, (i + 1) % n + 1) for i in range(n)], mat, smooth=True)


def _flame_lamp(b, m, x, y, z):
    """A small clay oil lamp: a dish with a pinched spout, its wick burning."""
    b.lathe(m["clay_lamp"], [(0, 0), (0.035, 0), (0.05, 0.012), (0.055, 0.028), (0.045, 0.03), (0, 0.022)], xf=place(x, y, z),
            segments=18, tile=0.1, radial=lambda a, h: 1 + 0.25 * max(0.0, math.cos(a)) ** 6)
    return Vector((x + 0.052, y, z + 0.04))


# ------------------------------------------------------------------ the washing room


def drape_sheet(coll, mat, name, centre, size_x, size_y, boxes, frames=48):
    """A cloth sheet dropped from `centre` over boxes ((x0, x1), (y0, y1), (z0, z1)) and
    left to settle (Blender's cloth solver), then kept as a plain smooth mesh."""
    sc = bpy.context.scene
    proxies = []
    for k, ((ax, bx), (ay, by), (az, bz)) in enumerate(boxes):
        p = box(f"_{name}_proxy_{k}", coll, ax, bx, ay, by, az, bz)
        p.modifiers.new("collision", "COLLISION")
        p.collision.thickness_outer = 0.012
        p.collision.cloth_friction = 6
        proxies.append(p)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=44, y_segments=52, size=0.5)
    bmesh.ops.scale(bm, vec=(size_x, size_y, 1), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    sheet = bpy.data.objects.new(name, me)
    coll.objects.link(sheet)
    sheet.location = centre
    cl = sheet.modifiers.new("cloth", "CLOTH")
    cl.settings.quality = 8
    cl.settings.mass = 0.25
    cl.settings.tension_stiffness = cl.settings.compression_stiffness = 12
    cl.settings.bending_stiffness = 0.25
    cl.collision_settings.distance_min = 0.006
    cl.collision_settings.use_self_collision = False
    start = sc.frame_current
    cl.point_cache.frame_start, cl.point_cache.frame_end = 1, frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    deps = bpy.context.evaluated_depsgraph_get()
    settled = bpy.data.meshes.new_from_object(sheet.evaluated_get(deps))
    sheet.modifiers.clear()
    sheet.data = settled
    for poly in sheet.data.polygons:
        poly.use_smooth = True
    sheet.data.materials.clear()
    sheet.data.materials.append(mat)
    uv = sheet.data.uv_layers.active or sheet.data.uv_layers.new(name="UVMap")
    for loop in sheet.data.loops:
        v = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (v.x / 0.45 + 0.5, v.y / 0.45 + 0.5)
    sc.frame_set(start)
    for p in proxies:
        bpy.data.objects.remove(p, do_unlink=True)
    return sheet


def washing_room(coll, m, rng):
    """Behind the altar: the slatted board Sok was washed on, wet still."""
    b = Batch("wash_room")
    x0, x1, yc, w = -1.75, 0.25, 19.85, 0.66
    top = FLOOR + 0.46
    for k in range(7):
        y = yc - w / 2 + k * w / 7
        b.box(m["wet_wood"], (x1 - x0, w / 7 - 0.018, 0.035), ((x0 + x1) / 2, y + (w / 7) / 2, top - 0.0175), chamfer=0.004)
    for xt in (x0 + 0.28, x1 - 0.28):
        b.box(m["wet_wood"], (0.08, w + 0.12, 0.06), (xt, yc, top - 0.065))
        for s in (-1, 1):
            b.tube(m["wet_wood"], [(xt + 0.02 * s, yc + s * 0.34, FLOOR), (xt, yc + s * 0.27, top - 0.09)], 0.03, sides=5)
    b.box(m["wet_wood"], (0.22, 0.24, 0.07), (x0 + 0.13, yc, top + 0.035), chamfer=0.01)    # the head block
    # The basin under it, and the water that ran through the slats into the boards.
    b.lathe(m["clay_lamp"], [(0, 0), (0.2, 0), (0.3, 0.06), (0.36, 0.16), (0.37, 0.18), (0.34, 0.175), (0, 0.04)],
            xf=place(-0.75, yc, FLOOR), segments=40, tile=0.4)
    _stain("wash_stain", coll, m["wet_stain"], -0.7, yc + 0.05, FLOOR + 0.003, 1.25, 0.62, rng)
    _stain("wash_stain_drip", coll, m["wet_stain"], 0.9, yc - 0.55, FLOOR + 0.003, 0.18, 0.1, rng)
    # Two glazed water jars by the north door, a coconut-shell dipper on one.
    for k, (x, y) in enumerate(((2.45, 21.45), (1.85, 21.55))):
        b.lathe(m["jar"], [(0, 0), (0.17, 0), (0.24, 0.06), (0.29, 0.25), (0.27, 0.45), (0.2, 0.56), (0.13, 0.6), (0.145, 0.64),
                           (0.125, 0.655), (0, 0.62)], xf=place(x, y, FLOOR), segments=32, tile=0.5)
    b.lathe(m["coconut"], [(0, -0.06), (0.05, -0.055), (0.068, -0.03), (0.07, 0.0), (0.064, 0.0), (0, -0.05)],
            xf=place(2.4, 21.42, FLOOR + 0.71), segments=16, tile=0.1)
    b.tube(m["wet_wood"], [(2.46, 21.42, FLOOR + 0.69), (2.62, 21.3, FLOOR + 0.8)], 0.008, sides=5)
    # Young coconuts by the head (their water washed him), one split open in a tray.
    for k, (x, y) in enumerate(((-2.35, 20.6), (-2.1, 20.85))):
        ok.coconut(b, m, place(x, y, FLOOR, rz=rng.uniform(0, 6)), rng)
    b.lathe(m["wet_wood"], [(0, 0), (0.22, 0), (0.23, 0.03), (0.21, 0.035), (0, 0.01)], xf=place(-2.3, 19.2, FLOOR), segments=24, tile=0.3)
    for k in range(2):
        xf = place(-2.36 + 0.13 * k, 19.2, FLOOR + 0.07) @ Matrix.Rotation(0.4 * (1 - 2 * k), 4, "X")
        b.lathe(m["coconut"], [(0, -0.07), (0.06, -0.06), (0.085, -0.03), (0.088, 0.0), (0, 0.0)], xf=xf, segments=20, tile=0.1)
        b.lathe(m["jasmine"], [(0, -0.055), (0.07, -0.02), (0.075, -0.002), (0, -0.002)], xf=xf, segments=20, tile=0.1)
    # The clothes for the coffin folded on a stool, a comb on them.
    b.box(m["wet_wood"], (0.42, 0.32, 0.03), (2.2, 18.56, FLOOR + 0.36), chamfer=0.004)
    for dx in (-0.17, 0.17):
        for dy in (-0.12, 0.12):
            b.box(m["wet_wood"], (0.035, 0.035, 0.34), (2.2 + dx, 18.56 + dy, FLOOR + 0.17))
    for k in range(4):
        b.box(m["linen"], (0.34 - 0.02 * k, 0.26, 0.035), (2.2 + rng.normal(0, 0.01), 18.56 + rng.normal(0, 0.01), FLOOR + 0.395 + 0.036 * k),
              chamfer=0.012)
    b.box(m["wet_wood"], (0.12, 0.03, 0.01), (2.22, 18.54, FLOOR + 0.55))
    # A white sheet thrown over the foot of the board and the folded cloths left on it,
    # settled by a cloth simulation into real folds down both sides (two flat grids read
    # as a stiff white box).
    drape_sheet(coll, m["linen"], "wash_room_sheet", (x1 - 0.42, yc, top + 0.3), 1.05, 1.25,
                [((x0, x1), (yc - w / 2, yc + w / 2), (top - 0.07, top)),
                 ((x1 - 0.75, x1 - 0.2), (yc - 0.2, yc + 0.18), (top, top + 0.11))])
    # The white thread still looped round the board, marigold petals on the wet boards.
    loop = [(x0 + 0.5, yc - w / 2 - 0.01, top + 0.002), (x0 + 0.5, yc + w / 2 + 0.01, top + 0.002),
            (x0 + 0.52, yc + w / 2 + 0.01, top - 0.04), (x0 + 0.55, yc + 0.4, FLOOR + 0.1), (x0 + 0.9, yc + 0.6, FLOOR + 0.004)]
    b.tube(m["linen"], loop, 0.0015, sides=4)
    for k in range(34):
        x, y = rng.uniform(-2.2, 1.0), yc + rng.normal(0, 0.7)
        ok.marigold(b, m, (x, y, FLOOR + 0.004), rng, radius=rng.uniform(0.008, 0.013), dead=rng.random() < 0.6)
    ok.incense_bowl(b, m, place(x0 - 0.3, yc + 0.32, FLOOR), rng, radius=0.07, height=0.06, sticks=9, lit=3)
    flames = [_flame_lamp(b, m, x0 - 0.35, yc - 0.2, FLOOR)]
    b.build(coll)
    import_model(coll, "pot_enamel_01", (-0.85, 21.45, FLOOR), rot_deg=30, name="wash_pot", collide=False)   # clear of the north door
    return flames


# ------------------------------------------------------------------ the loom


def loom(coll, m, rng, cx=-3.95, cy=18.27):   # (at 18.1 its front beam stood in the door from Yay Mey's room)
    """Yay Mey's floor loom (kei), a hol silk half woven, its bench at the weaver's end."""
    L, W, Hh = 1.9, 1.05, 1.35
    b = Batch("loom")
    wood = m["cl_trim"]
    y0, y1, x0, x1 = cy - L / 2, cy + L / 2, cx - W / 2, cx + W / 2
    for x in (x0, x1):
        for y in (y0, y1):
            b.box(wood, (0.07, 0.07, Hh), (x, y, FLOOR + Hh / 2), chamfer=0.006)
        b.box(wood, (0.06, L + 0.07, 0.07), (x, cy, FLOOR + Hh - 0.035), chamfer=0.006)
        b.box(wood, (0.06, L + 0.07, 0.06), (x, cy, FLOOR + 0.18), chamfer=0.006)
    for y in (y0, y1):
        b.box(wood, (W + 0.07, 0.06, 0.07), (cx, y, FLOOR + Hh - 0.035), chamfer=0.006)
    zb = FLOOR + 0.78
    b.tube(wood, [(x0, y0 + 0.12, zb), (x1, y0 + 0.12, zb)], 0.035, sides=10)
    b.tube(wood, [(x0, y1 - 0.12, zb + 0.05), (x1, y1 - 0.12, zb + 0.05)], 0.05, sides=10)
    b.tube(m["silk"], [(x0 + 0.08, y0 + 0.24, FLOOR + 0.55), (x1 - 0.08, y0 + 0.24, FLOOR + 0.55)], 0.075, sides=18)
    fell = y0 + 0.62
    b.grid(m["silk"], lambda u, v: (x0 + 0.1 + (W - 0.2) * u, y0 + 0.12 + (fell - y0 - 0.12) * v, zb + 0.036),
           6, 4, uv=lambda u, v: (u * (W - 0.2) / 0.3, v * 0.5 / 0.3))
    b.grid(m["warp"], lambda u, v: (x0 + 0.1 + (W - 0.2) * u, fell + (y1 - 0.12 - fell) * v, zb + 0.036 + 0.05 * v),
           1, 1, uv=lambda u, v: (u * 3, v * 3))
    for k, yh in enumerate((fell + 0.34, fell + 0.46)):
        for z in (zb + 0.22, zb - 0.12):
            b.box(wood, (W - 0.1, 0.02, 0.025), (cx, yh, z))
        for x in (x0 + 0.15, x1 - 0.15):
            b.tube(m["rope"] if "rope" in m else wood, [(x, yh, FLOOR + Hh - 0.07), (x, yh, zb + 0.23)], 0.004, sides=4)
            b.tube(m["rope"] if "rope" in m else wood, [(x, yh, zb - 0.13), (x, yh - 0.05, FLOOR + 0.06)], 0.004, sides=4)
        b.grid(m["warp"], lambda u, v, yh=yh: (x0 + 0.12 + (W - 0.24) * u, yh, zb - 0.12 + 0.34 * v), 1, 1, uv=lambda u, v: (u * 3, v * 0.5))
    yb = fell + 0.13
    for z in (zb - 0.1, zb + 0.13):
        b.box(wood, (W - 0.06, 0.035, 0.04), (cx, yb, z), chamfer=0.006)
    for x in (x0 + 0.04, x1 - 0.04):
        b.tube(wood, [(x, yb, zb - 0.12), (x, yb + 0.25, FLOOR + Hh - 0.07)], 0.018, sides=6)
    for k, x in enumerate((cx - 0.15, cx + 0.15)):
        b.box(wood, (0.09, L * 0.7, 0.03), (x, cy + 0.1, FLOOR + 0.03 + 0.02 * k), chamfer=0.004)
    # The bench at the weaver's end, a basket of skeins beside it.
    b.box(wood, (W - 0.05, 0.28, 0.04), (cx, y0 - 0.34, FLOOR + 0.44), chamfer=0.006)
    for dx in (-W / 2 + 0.08, W / 2 - 0.08):
        for dy in (-0.1, 0.1):
            b.box(wood, (0.04, 0.04, 0.42), (cx + dx, y0 - 0.34 + dy, FLOOR + 0.21))
    for k in range(5):
        p = (cx - W / 2 - 0.28 + rng.normal(0, 0.04), y0 - 0.1 + rng.normal(0, 0.05), FLOOR + 0.03 + 0.02 * k)
        b.tube(m["silk"], [p, (p[0] + 0.1, p[1] + 0.02, p[2] + 0.01)], 0.022, sides=8, cap_end=True)
    b.build(coll)
    import_model(coll, "wicker_basket_01", (cx - W / 2 - 0.28, y0 - 0.1, FLOOR), rot_deg=20, name="loom_basket", collide=False)
    return []


# ------------------------------------------------------------------ Kanha's room


def kanha_room(coll, m, rng, bed_top):
    """Her room kept as it was: the rag doll left on the bed, her drawings pinned to the
    wall, the mirror covered, dried flowers in a cup, her small sandals by the door."""
    b = Batch("kanha")
    x, y, z = bed_top
    # The doll lying on its back, head on the pillow end, its dress faded red.
    b.lathe(m["doll_dress"], [(0, 0), (0.05, 0), (0.045, 0.08), (0.03, 0.13), (0, 0.14)],
            xf=place(x, y, z + 0.03) @ Matrix.Rotation(math.pi / 2, 4, "Y"), segments=14, tile=0.1)
    b.lathe(m["doll"], [(0, -0.045), (0.035, -0.035), (0.045, 0.0), (0.035, 0.035), (0, 0.045)],
            xf=place(x - 0.19, y, z + 0.04), segments=14, tile=0.08)
    for k in range(9):
        a = rng.uniform(-1.2, 1.2)
        b.tube(m["hair"], [(x - 0.2, y + 0.03 * math.sin(a), z + 0.08), (x - 0.27, y + 0.08 * math.sin(a), z + 0.02)], 0.004, sides=4)
    for s in (-1, 1):
        b.tube(m["doll"], [(x - 0.06, y + s * 0.05, z + 0.03), (x - 0.02, y + s * 0.11, z + 0.02)], 0.012, sides=6, cap_end=True)
        b.tube(m["doll"], [(x + 0.13, y + s * 0.025, z + 0.025), (x + 0.24, y + s * 0.04, z + 0.02)], 0.014, sides=6, cap_end=True)
    # Drawings pinned to the north wall, curling.
    yw = SH.ROW1 - SH.T / 2 - 0.003
    # Her own drawing, and the colour pictures of the royal dancers she pinned up beside it
    # (Busy's 1921 autochromes and a dancers' postcard from the studio atlases).
    import colonial_house as CH
    from colonial_parts import wall_print
    for k, (atlas, item, cx, cz, width) in enumerate((("colour", "A36107", 2.05, 1.5, 0.27), ("colour", "A36112", 2.5, 1.32, 0.25),
                                                     ("cards", "DIEU1658", 3.0, 1.55, 0.22))):
        mat = image_material(f"M_nr_kanha_{atlas}", os.path.join(TEX, CH.PRINTS_SPEC[atlas]["file"] + ".png"), rough=0.9)
        wall_print(f"kanha_print_{k}", coll, CH.PRINTS_SPEC[atlas], item, mat, (cx, yw - 0.002, FLOOR + cz), (-1, 0, 0), (0, 0, 1), width,
                   curl=0.014, pins=m["brass"] or m["iron"], seed=40 + k)
    for k, (cx, cz, w, h, rz) in enumerate(((3.4, 1.22, 0.26, 0.2, 0.08),)):
        verts = []
        for j in range(3):
            for i in range(4):
                u, v = i / 3, j / 2
                verts.append((cx - w / 2 + w * u, yw - 0.012 * (u - 0.5) ** 2 * 4 * (1 - v) - 0.004 * k, FLOOR + cz - h / 2 + h * v))
        faces = [(j * 4 + i, j * 4 + i + 1, (j + 1) * 4 + i + 1, (j + 1) * 4 + i) for j in range(2) for i in range(3)]
        o = mesh_object(f"kanha_drawing_{k}", coll, verts, faces, m["drawing"], smooth=True)
        o.data.materials[0].use_backface_culling = False
        _uvs_planar(o, 0, 2, w * 2.6, h * 2.6, off=(cx - w / 2 - 0.2 * k, FLOOR + cz - h / 2 - 0.15 * k))
        o.rotation_euler.y = rz
        b.lathe(m["brass"] or m["iron"], [(0, 0), (0.004, 0), (0.004, 0.006), (0, 0.006)],
                xf=place(cx, yw - 0.012, FLOOR + cz + h / 2 - 0.02) @ Matrix.Rotation(math.pi / 2, 4, "X"), segments=8, tile=0.02)
    # The mirror turned to the wall under a cloth, by the door.
    mirror = import_model(coll, "ornate_mirror_01", (SH.LC + 0.06, 26.6, FLOOR + 1.0), rot_deg=-90, name="kanha_mirror", collide=False)
    cloth("kanha_mirror_cloth", coll, 26.15, 27.05, FLOOR + 0.62, FLOOR + 1.62, SH.LC + 0.14, m["linen"], folds=5, depth=0.025,
          segments=(24, 16), axis="y")
    # A cup of dried marigolds and jasmine on a little chest; her sandals by the door.
    b.box(m["cl_trim"], (0.5, 0.32, 0.3), (2.1, 23.75, FLOOR + 0.15), chamfer=0.01)
    b.lathe(m["clay_lamp"], [(0, 0), (0.04, 0), (0.05, 0.08), (0.045, 0.085), (0, 0.075)], xf=place(2.0, 23.75, FLOOR + 0.3), segments=16, tile=0.1)
    for k in range(7):
        a = rng.uniform(0, math.tau)
        top = (2.0 + 0.04 * math.cos(a), 23.75 + 0.04 * math.sin(a), FLOOR + 0.45 + rng.uniform(0, 0.08))
        b.tube(m["stem"] if "stem" in m else m["cl_trim"], [(2.0, 23.75, FLOOR + 0.34), top], 0.0025, sides=4)
        ok.marigold(b, m, top, rng, radius=0.012, dead=True)
    for s in (-1, 1):
        b.box(m["cl_trim"], (0.09, 0.19, 0.012), (1.1 + 0.06 * s, 25.95 + 0.02 * s, FLOOR + 0.006), chamfer=0.004)
    b.build(coll)
    return []


# ------------------------------------------------------------------ the padlocked room


def locked_room(coll, m, rng):
    """Sok's logs from the lake clinic: shelves of ledgers and specimen jars, a table
    with the last ledger open under a lamp gone cold, papers on the floor, and a chair
    turned to face the corner."""
    b = Batch("locked")
    ys = SH.ROW2 + SH.T / 2 + 0.01
    for k, x in enumerate((-6.6, -4.6)):
        # A plain shelf unit against the south wall: uprights, four shelves.
        for dx in (-0.62, 0.62):
            b.box(m["cl_trim"], (0.04, 0.34, 1.9), (x + dx, ys + 0.17, FLOOR + 0.95))
        for j in range(4):
            zs = FLOOR + 0.12 + j * 0.5
            b.box(m["cl_trim"], (1.28, 0.34, 0.025), (x, ys + 0.17, zs), chamfer=0.003)
            xx = x - 0.58
            while xx < x + 0.55:
                if (j + k) % 2 == 0 and rng.random() < 0.55:
                    r = rng.uniform(0.045, 0.07)
                    hgt = rng.uniform(0.14, 0.24)
                    b.lathe(m["glass"], [(0, 0), (r, 0), (r, hgt * 0.8), (r * 0.6, hgt * 0.9), (r * 0.62, hgt), (0, hgt)],
                            xf=place(xx + r, ys + 0.17, zs + 0.0125), segments=16, tile=0.1)
                    b.lathe(m["murk"], [(0, 0.004), (r * 0.92, 0.004), (r * 0.92, hgt * rng.uniform(0.4, 0.75)), (0, hgt * 0.6)],
                            xf=place(xx + r, ys + 0.17, zs + 0.0125), segments=12, tile=0.1)
                    b.lathe(m["ledger"], [(0, hgt), (r * 0.66, hgt), (r * 0.66, hgt + 0.02), (0, hgt + 0.02)],
                            xf=place(xx + r, ys + 0.17, zs + 0.0125), segments=12, tile=0.1)
                    xx += 2 * r + 0.03
                else:
                    th = rng.uniform(0.03, 0.06)
                    hgt = rng.uniform(0.24, 0.32)
                    lean = rng.uniform(-0.08, 0.08) if rng.random() < 0.2 else 0.0
                    bx = Matrix.Translation((xx + th / 2, ys + 0.16, zs + 0.0125 + hgt / 2)) @ Matrix.Rotation(lean, 4, "Y")
                    b.box(m["ledger"], (th, 0.22, hgt), (0, 0, 0), xf=bx, chamfer=0.003)
                    xx += th + 0.004
    # The table, the open ledger, the lamp; papers drifted over the floor.
    # A writing table (0.8 m; WoodenTable_02 is a 42 cm side table, and the ledger, the lamp
    # and the bottles stood in the air over it).
    table = import_model(coll, "wooden_table_02", (-3.0, 32.9, FLOOR), rot_deg=90, name="locked_table", collide=False)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in table.children_recursive if o.type == "MESH" for c in o.bound_box]
    tz = max(p.z for p in pts) if pts else FLOOR + 0.78
    import_model(coll, "vintage_oil_lamp", (-2.75, 32.75, tz), rot_deg=0, name="locked_lamp", collide=False)
    for k in range(12):
        x, y = rng.uniform(-7.6, -1.2), rng.uniform(31.0, 33.7)
        a = rng.uniform(0, math.tau)
        c, s = math.cos(a), math.sin(a)
        pts = [(x + c * dx - s * dy, y + s * dx + c * dy, FLOOR + 0.002 + 0.0004 * k) for dx, dy in ((-0.1, -0.14), (0.1, -0.14), (0.1, 0.14), (-0.1, 0.14))]
        b.add(m["paper"], pts, [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)
    b.box(m["ledger"], (0.34, 0.24, 0.025), (-3.15, 32.95, tz + 0.0125), chamfer=0.003)
    b.add(m["paper"], [(-3.31, 32.84, tz + 0.027), (-3.0, 32.84, tz + 0.027), (-3.0, 33.06, tz + 0.03), (-3.31, 33.06, tz + 0.03)],
          [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)])
    b.build(coll)
    chair = import_model(coll, "chinese_armchair", (-7.35, 33.45, FLOOR), rot_deg=135, name="locked_chair", collide=False)
    return []


# ------------------------------------------------------------------ the attic


def attic_things(coll, m, rng):
    """Old belongings along the plank paths, a dress form under a sheet at the end of
    the east path, looking back at the hatch."""
    jz = ZW + 0.165
    # The second suitcase stands behind the first (crossed over it at 80 degrees it went
    # through it, and out over the path's corner).
    for k, (mid, x, y, rot) in enumerate((("vintage_suitcase", -4.6, 16.55, 10), ("vintage_suitcase", -4.65, 17.1, 10),
                                         ("wooden_crate_01", -2.2, 15.4, 5), ("wooden_crate_01", -2.25, 15.45, 40),
                                         ("wicker_basket_01", 1.1, 16.55, 0), ("painted_wooden_cabinet", 3.6, 15.42, 0),
                                         ("folding_wooden_stool", 0.4, 13.4, 30), ("standing_picture_frame_01", 2.6, 19.3, 180),
                                         ("wicker_basket_01", -0.2, 12.9, 60))):
        z = jz + (0.3 if k == 3 else 0.0)
        import_model(coll, mid, (x, y, z), rot_deg=rot, name=f"attic_{mid}_{k}", collide=False)
    b = Batch("attic_form")
    fx, fy = 1.7, 16.0
    b.tube(m["cl_trim"], [(fx, fy, jz), (fx, fy, jz + 1.05)], 0.015, sides=8)
    for a in range(3):
        ang = a * math.tau / 3
        b.tube(m["cl_trim"], [(fx, fy, jz + 0.05), (fx + 0.25 * math.cos(ang), fy + 0.25 * math.sin(ang), jz)], 0.012, sides=6)
    b.lathe(m["linen"], [(0, 0), (0.13, 0), (0.17, 0.12), (0.15, 0.3), (0.17, 0.45), (0.12, 0.55), (0.05, 0.6), (0, 0.62)],
            xf=place(fx, fy, jz + 1.0) @ Matrix.Scale(0.75, 4, Vector((1, 0, 0))), segments=24, tile=0.3)
    # The sheet over it: draped from the shoulders to the boards, in folds.
    def sheet(u, v):
        a = u * math.tau
        r = 0.2 + 0.2 * v + 0.03 * math.sin(a * 7 + v * 4)
        z = jz + 1.6 - 1.55 * v
        return (fx + r * math.cos(a) * (0.85 if v < 0.3 else 1.0), fy + r * math.sin(a), max(jz + 0.01, z))
    b.grid(m["linen"], sheet, 48, 14, uv=lambda u, v: (u * 3, v * 2))
    b.build(coll)
    # Rolled mats leaned in the low eave, and an old portrait face to the roof.
    for k in range(4):
        x = -3.2 + 0.18 * k
        tube(f"attic_mat_roll_{k}", coll, [(x, 12.15, jz), (x + 0.05, 12.7, jz + 0.55)], 0.07, m["mat"] if "mat" in m else m["cl_trim"], sides=10)
    return []


def corridor_lamp(coll, m, rng):
    """One hurricane lamp left burning on a nail far down the long corridor, near the
    nailed door: the only light back there."""
    x, y, z = -SH.LC + SH.T / 2 + 0.16, 33.15, FLOOR + 1.62
    tube("corridor_lamp_nail", coll, [(-SH.LC + SH.T / 2, y, z + 0.32), (x, y, z + 0.33)], 0.004, m["iron"], sides=5)
    lamp = import_model(coll, "Lantern_01", (x, y, z), rot_deg=rng.uniform(0, 90), name="corridor_lamp", collide=False)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in lamp.children_recursive if o.type == "MESH" for c in o.bound_box]
    if pts:
        top = max(p.z for p in pts)
        lamp.location.z += (z + 0.32) - top
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ Vector(c) for o in lamp.children_recursive if o.type == "MESH" for c in o.bound_box]
        c = Vector((sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), sum(p.z for p in pts) / len(pts)))
        # Just outside the globe (the model's glass would hold the light in), on the corridor side.
        return [c + Vector((0.13, 0, -0.08))]
    return []


def study_extras(coll, m, rng):
    """Sok's study, filled out: a Chinese cabinet and a shelf of his books against the
    corridor-side wall, Busy's photograph of a royal dancer at the palace (1921) and the Phnom
    temple print pinned over them (the map of Siam came down, the user, November 23)."""
    import colonial_house as CH
    from colonial_parts import wall_print
    ys = SH.CORR + SH.T / 2 + 0.005
    import_model(coll, "chinese_cabinet", (-6.6, ys + 0.3, FLOOR), rot_deg=0, name="study_cabinet", collide=False)
    shelves = import_model(coll, "painted_wooden_shelves", (-4.3, ys + 0.2, FLOOR), rot_deg=0, name="study_shelves", collide=False)
    bpy.context.view_layer.update()
    b = Batch("study_books")
    pts = [o.matrix_world @ Vector(c) for o in shelves.children_recursive if o.type == "MESH" for c in o.bound_box]
    if pts:
        x0, x1 = min(p.x for p in pts) + 0.05, max(p.x for p in pts) - 0.05
        z1 = max(p.z for p in pts)
        for level in (0.32, 0.62):
            zs = FLOOR + (z1 - FLOOR) * level
            xx = x0
            while xx < x1 - 0.05:
                th, hgt = rng.uniform(0.025, 0.055), rng.uniform(0.17, 0.26)
                b.box(m["ledger"] if rng.random() < 0.7 else m["paper"], (th, 0.16, hgt), (xx + th / 2, ys + 0.14, zs + hgt / 2), chamfer=0.002)
                xx += th + 0.003
    b.build(coll)
    mats = {k: image_material(f"M_nr_print_{k}", os.path.join(TEX, CH.PRINTS_SPEC[k]["file"] + ".png"), rough=0.9)
            for k in ("posters", "colour")}
    for k, (name, atlas, item, x, z, width) in enumerate((("study_print_dancer", "colour", "A36107", -5.3, FLOOR + 1.5, 0.4),
                                                       ("study_print_vatphnom", "posters", "A35914", -3.2, FLOOR + 1.55, 0.4))):
        wall_print(name, coll, CH.PRINTS_SPEC[atlas], item, mats[atlas], (x, ys + 0.002, z), (-1, 0, 0), (0, 0, 1), width,
                   curl=0.012, pins=m["brass"], seed=k)
    return []


def hall_extras(coll, m, rng):
    """The hall laid for prayers: two reed mats before the altar, cushions on them, and
    an unlit lamp hung from the ceiling on a chain."""
    for k, (x, y, a) in enumerate(((-0.75, 15.9, 0.03), (0.85, 15.75, -0.05))):
        c, sn = math.cos(a), math.sin(a)
        pts = [(x + c * dx - sn * dy, y + sn * dx + c * dy, FLOOR + 0.004 + 0.002 * k) for dx, dy in ((-0.9, -0.55), (0.9, -0.55), (0.9, 0.55), (-0.9, 0.55))]
        mesh_object(f"hall_prayer_mat_{k}", coll, pts, [(0, 1, 2, 3)], m.get("mat") or m["cl_trim"], uvs=[(0, 0), (1.8, 0), (1.8, 1.1), (0, 1.1)])
    b = Batch("hall_cushions")
    for k, (x, y) in enumerate(((-1.2, 15.75), (-0.35, 15.8), (0.5, 15.6), (1.3, 15.85))):
        if "pillow_embroidered" in m:   # soft stuffed cushions (house_props), not boxes
            import house_props as HP
            key = ("pillow_embroidered", "pillow_floral", "pillow_triangle", "pillow_gingham")[k]
            HP.pillow(b, m[key], place(x, y, FLOOR + 0.006, rz=rng.normal(0, 0.15)), L=0.44, W=0.38, H=0.11, rng=rng, dent=0.5)
        else:
            b.box(m.get("cushion") or m["doll_dress"], (0.42, 0.3, 0.1), (x, y, FLOOR + 0.06), chamfer=0.04)
    b.build(coll)
    tube("hall_lamp_chain", coll, [(0.0, 14.6, ZW - 0.02), (0.0, 14.6, ZW - 0.7)], 0.004, m["iron"], sides=4)
    import_model(coll, "Lantern_01", (0.0, 14.6, ZW - 1.05), rot_deg=20, name="hall_lamp", collide=False)
    return []


def furnish(coll, m, rng, kanha_bed_top):
    flames = corridor_lamp(coll, m, rng)
    flames += hall_extras(coll, m, rng)
    flames += study_extras(coll, m, rng)
    flames += washing_room(coll, m, rng)
    flames += loom(coll, m, rng)
    flames += kanha_room(coll, m, rng, kanha_bed_top)
    flames += locked_room(coll, m, rng)
    flames += attic_things(coll, m, rng)
    return flames
