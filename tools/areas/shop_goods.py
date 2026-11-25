"""Small goods for the village road's shops (the user, Nov 25, 2026: "Inside every single shop
also even small items inside the shop should be more very detailed and very realistic").

Everything here is modelled at the size it is sold at and printed with the labels of
T_ep1_shop_goods_BC (tools/drawings/shopGoods.mjs, the Khmer in its review list): glass
bottles with their liquid, caps and wrapped labels; tins with rolled seams; jars of sweets
and pickles; printed packets and boxes; bowls, spoons, chopsticks; combs, scissors and
razors; spanners and screwdrivers; cloth folded and hung.

Geometry goes into a Kit: one bmesh per material, in a shop's own frame (+x to the road,
the interior floor at z 0.185), turned into one object per material by Kit.emit.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for _p in (HERE, os.path.join(ROOT, "tools", "travel")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import taxi_roadside_details as TRD  # noqa: E402
from kit import image_material, plain  # noqa: E402

SHEET = os.path.join(ROOT, "art-source", "textures", "ep1", "T_ep1_shop_goods_BC.png")
STATIC = os.path.join(ROOT, "art-source", "textures", "ep1", "T_ep1_crt_static_BC.png")

# The label sheet's cells, in shopGoods.mjs's order (keep the two in step).
WRAP = ["fish_sauce", "soy_sauce", "chili", "cooking_oil", "orange", "beer", "rice_spirit", "condensed_milk",
        "coffee", "hair_oil", "balm", "talc", "shampoo", "vinegar", "soda", "canned_fish",
        "engine_oil", "kerosene", "cough_syrup", "perfume", "thread", "sweets", "palm_sugar", "pickles",
        "prahok", "tea", "biscuits", "battery", "grease", "coconut", "lotion", "alcohol"]
FACE = [("cig_red", 0.62), ("cig_blue", 0.62), ("matches", 1.45), ("noodles_red", 1.3), ("noodles_yellow", 1.3),
        ("soap", 1.5), ("incense", 0.34), ("candles", 0.5), ("washing_powder", 0.75), ("tea_box", 0.7),
        ("toothpaste", 3.4), ("medicine", 1.6), ("razor", 1.6), ("cassette_a", 0.62), ("cassette_b", 0.62),
        ("biscuit_box", 1.4), ("snacks", 0.75), ("dried_squid", 0.75), ("shrimp_crackers", 0.75), ("hair_dye", 0.75),
        ("spark_plug", 0.45), ("needles", 1.5), ("calendar", 0.72), ("notebook", 0.72), ("lottery", 2.2),
        ("face_powder", 1.0), ("watch_box", 1.0), ("teeth_chart", 0.72), ("price_list", 0.72), ("shrine_paper", 0.6),
        ("no_credit", 2.0), ("beer_card", 1.0)]
_FACE = {k: i for i, (k, _a) in enumerate(FACE)}


def wrap_rect(name):
    """A wrap label's cell as UV (u0, v0, u1, v1)."""
    i = WRAP.index(name)
    x, y = (i % 4) * 512, (i // 4) * 128
    return x / 2048, 1 - (y + 128) / 2048, (x + 512) / 2048, 1 - y / 2048


def face_rect(name):
    """A face label's printed rectangle as UV (u0, v0, u1, v1) (shopGoods.mjs faceRect)."""
    i = _FACE[name]
    aspect = FACE[i][1]
    cx, cy = (i % 8) * 256 + 128, 1024 + (i // 8) * 256 + 128
    w = 240 if aspect >= 1 else round(240 * aspect)
    h = round(240 / aspect) if aspect >= 1 else 240
    x, y = cx - w // 2, cy - h // 2
    return x / 2048, 1 - (y + h) / 2048, (x + w) / 2048, 1 - y / 2048


# ------------------------------------------------------------------ materials

def crt_static():
    """A frame of television snow with scan lines (the TVs left on in the empty shop)."""
    if os.path.exists(STATIC):
        return STATIC
    rng = np.random.default_rng(77)
    w, h = 256, 192
    n = rng.random((h, w)) ** 1.6
    n = np.clip(n * 0.85 + 0.15 * rng.random((h, 1)), 0, 1)
    n[::2] *= 0.7
    px = np.ones((h, w, 4), dtype=np.float32)
    px[..., 0] = n * 0.86
    px[..., 1] = n * 0.92
    px[..., 2] = n
    img = bpy.data.images.new("T_ep1_crt_static_BC", w, h)
    img.pixels = px[::-1].ravel()
    img.filepath_raw = STATIC
    img.file_format = "PNG"
    img.save()
    return STATIC


def materials(m):
    """The goods' materials, the shops' own (m) reused where they fit."""
    G = {}

    def p(key, *a, **k):
        G[key] = bpy.data.materials.get(f"M_vroad_goods_{key}") or plain(f"M_vroad_goods_{key}", *a, **k)
        return G[key]

    lab = bpy.data.materials.get("M_vroad_goods_labels")
    if lab is None:
        lab = image_material("M_vroad_goods_labels", SHEET, rough=0.62)
    G["label"] = lab
    for key, colour, alpha in (("glass", (0.1, 0.12, 0.12), 0.2), ("glass_amber", (0.3, 0.13, 0.02), 0.6),
                               ("glass_green", (0.05, 0.2, 0.08), 0.55), ("glass_blue", (0.08, 0.13, 0.3), 0.5)):
        mt = p(key, colour, rough=0.03, alpha=alpha)
        mt.surface_render_method = "BLENDED"
        mt.use_backface_culling = False
    for key, colour, rough in (("fish_sauce", (0.3, 0.1, 0.03), 0.08), ("soy", (0.04, 0.02, 0.01), 0.08),
                               ("oil", (0.72, 0.5, 0.06), 0.06), ("petrol", (0.86, 0.42, 0.12), 0.05),
                               ("orange", (0.9, 0.42, 0.06), 0.1), ("beer", (0.36, 0.16, 0.03), 0.08),
                               ("chili", (0.55, 0.05, 0.02), 0.2), ("syrup", (0.25, 0.04, 0.03), 0.1),
                               ("coffee", (0.09, 0.04, 0.02), 0.1), ("iced_coffee", (0.42, 0.24, 0.12), 0.15),
                               ("tea", (0.5, 0.2, 0.05), 0.1), ("water", (0.55, 0.6, 0.58), 0.05)):
        p(key, colour, rough=rough)
    p("tinplate", (0.72, 0.72, 0.7), rough=0.32, metal=0.92)
    p("chrome", (0.86, 0.86, 0.86), rough=0.12, metal=1.0)
    p("brass", (0.72, 0.52, 0.22), rough=0.3, metal=1.0)
    p("steel", (0.5, 0.5, 0.52), rough=0.38, metal=0.9)
    p("cast_iron", (0.07, 0.07, 0.07), rough=0.55, metal=0.6)
    p("black_paint", (0.025, 0.025, 0.028), rough=0.35, metal=0.1)
    p("gold_paint", (0.62, 0.44, 0.12), rough=0.35, metal=0.7)
    for key, colour in (("red", (0.5, 0.05, 0.04)), ("blue", (0.05, 0.14, 0.42)), ("green", (0.05, 0.3, 0.12)),
                        ("yellow", (0.75, 0.55, 0.05)), ("white", (0.78, 0.77, 0.72)), ("pink", (0.82, 0.4, 0.5)),
                        ("black", (0.02, 0.02, 0.022)), ("orange_plastic", (0.85, 0.32, 0.04)), ("cream", (0.8, 0.72, 0.55))):
        p(f"plastic_{key}", colour, rough=0.42)
    p("porcelain", (0.86, 0.85, 0.8), rough=0.18)
    p("enamel_blue", (0.1, 0.22, 0.48), rough=0.2, metal=0.05)
    p("cork", (0.5, 0.36, 0.2), rough=0.85)
    p("rubber", (0.03, 0.03, 0.03), rough=0.75)
    p("tyre", (0.035, 0.034, 0.032), rough=0.82)
    p("inner_tube", (0.25, 0.05, 0.04), rough=0.6)
    p("leather_black", (0.035, 0.03, 0.028), rough=0.42)
    p("leather_red", (0.3, 0.04, 0.03), rough=0.45)
    p("vinyl_cream", (0.62, 0.56, 0.44), rough=0.4)
    p("noodles", (0.82, 0.62, 0.25), rough=0.55)
    p("rice_noodles", (0.86, 0.84, 0.76), rough=0.5)
    p("meat", (0.42, 0.08, 0.04), rough=0.3)
    p("herbs", (0.08, 0.3, 0.06), rough=0.6)
    p("lime", (0.22, 0.45, 0.08), rough=0.45)
    p("chili_fresh", (0.62, 0.04, 0.02), rough=0.35)
    p("egg", (0.8, 0.68, 0.52), rough=0.5)
    p("candy", (0.7, 0.2, 0.25), rough=0.2)
    p("candy_b", (0.9, 0.75, 0.2), rough=0.2)
    p("candy_c", (0.2, 0.55, 0.3), rough=0.2)
    p("bristle", (0.25, 0.2, 0.14), rough=0.8)
    p("hair", (0.03, 0.025, 0.02), rough=0.6)
    p("wax", (0.92, 0.88, 0.76), rough=0.4)
    p("wax_red", (0.6, 0.06, 0.05), rough=0.4)
    p("incense", (0.42, 0.12, 0.06), rough=0.8)
    p("paper", (0.82, 0.78, 0.66), rough=0.85)
    p("cardboard", (0.5, 0.38, 0.24), rough=0.9)
    p("thread_red", (0.6, 0.05, 0.06), rough=0.7)
    p("thread_blue", (0.06, 0.12, 0.45), rough=0.7)
    p("thread_white", (0.82, 0.8, 0.74), rough=0.7)
    p("thread_yellow", (0.8, 0.6, 0.1), rough=0.7)
    p("felt_green", (0.04, 0.16, 0.08), rough=0.95)
    p("velvet_red", (0.3, 0.02, 0.03), rough=0.95)
    p("gum_pink", (0.75, 0.32, 0.35), rough=0.3)
    p("tooth", (0.9, 0.88, 0.8), rough=0.25)
    p("dial_glow", (0.95, 0.62, 0.25), rough=0.3, emission=(1.0, 0.55, 0.2), strength=0.8)
    p("led_red", (0.8, 0.05, 0.03), rough=0.3, emission=(1.0, 0.05, 0.02), strength=2.0)
    stat = bpy.data.materials.get("M_vroad_goods_crt_static")
    if stat is None:
        stat = image_material("M_vroad_goods_crt_static", crt_static(), rough=0.08)
        bsdf = stat.node_tree.nodes["Principled BSDF"]
        tex = [n for n in stat.node_tree.nodes if n.type == "TEX_IMAGE"][0]
        stat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 0.9
    G["crt_static"] = stat
    # The shops' own: wood, cloth, paper, metal.
    for key in ("table_wood", "dark_wood", "planks", "krama", "hol_silk", "news", "kantel", "iron", "white_enamel",
                "linen_towel", "leather_barber", "bamboo", "deck", "concrete", "bulb", "wire", "mirror", "tin",
                "enamel_green", "rubber"):
        if key in m:
            G[f"shop_{key}"] = m[key]
    return G


# ------------------------------------------------------------------ the kit

# Kit keys whose geometry carries its own UVs (labels, the static); the rest get box-projected
# world UVs where their material is a tiled texture.
UV_KEYS = {"label", "crt_static"}
WORLD_UV = {"shop_table_wood", "shop_dark_wood", "shop_planks", "shop_krama", "shop_hol_silk", "shop_news",
            "shop_kantel", "shop_iron", "shop_white_enamel", "shop_linen_towel", "shop_leather_barber",
            "shop_bamboo", "shop_deck", "shop_concrete", "shop_tin", "shop_enamel_green"}
SMOOTH = {"glass", "glass_amber", "glass_green", "glass_blue", "fish_sauce", "soy", "oil", "petrol", "orange", "beer",
          "chili", "syrup", "coffee", "iced_coffee", "tea", "water", "tinplate", "chrome", "brass", "steel",
          "porcelain", "enamel_blue", "cork", "rubber", "tyre", "inner_tube", "noodles", "rice_noodles", "meat",
          "lime", "chili_fresh", "egg", "candy", "candy_b", "candy_c", "wax", "wax_red", "thread_red", "thread_blue",
          "thread_white", "thread_yellow", "tooth", "gum_pink", "leather_black", "leather_red", "vinyl_cream",
          "plastic_red", "plastic_blue", "plastic_green", "plastic_yellow", "plastic_white", "plastic_pink",
          "plastic_black", "plastic_orange_plastic", "plastic_cream", "label", "cast_iron", "black_paint",
          "gold_paint", "herbs", "shop_bulb", "dial_glow"}


class Kit:
    """One bmesh per material, in a shop's frame."""

    def __init__(self, G):
        self.G = G
        self.b = {}
        self.tris = 0

    def __getitem__(self, key):
        bm = self.b.get(key)
        if bm is None:
            bm = self.b[key] = bmesh.new()
            if key in UV_KEYS:
                bm.loops.layers.uv.verify()
        return bm

    def emit(self, coll, prefix, M):
        """One object per textured, glass or glowing material; the plain-coloured rest merged
        into three objects (matte, glossy, metal) coloured per vertex, so a shop's hundreds
        of small things cost the game a handful of draw calls, not sixty."""
        from kit import world_uvs

        out = []
        groups = {}
        for key, bm in self.b.items():
            if not len(bm.faces):
                bm.free()
                continue
            mt = self.G.get(key)
            grp = _group(key, mt)
            if grp:
                me = bpy.data.meshes.new("_vgoods_tmp")
                bm.to_mesh(me)
                bm.free()
                if key in SMOOTH or key.startswith("plastic_"):
                    for poly in me.polygons:
                        poly.use_smooth = True
                groups.setdefault(grp, []).append((me, _base_colour(mt)))
                continue
            me = bpy.data.meshes.new(f"{prefix}_{key}")
            bm.to_mesh(me)
            bm.free()
            if me.uv_layers:
                me.uv_layers[0].name = "UVMap"
            if key in SMOOTH or key.startswith("plastic_"):
                for poly in me.polygons:
                    poly.use_smooth = True
            if mt:
                me.materials.append(mt)
            obj = bpy.data.objects.new(f"{prefix}_{key}", me)
            coll.objects.link(obj)
            obj.matrix_world = M
            if key in WORLD_UV and mt:
                world_uvs(obj)
            self.tris += sum(len(p.vertices) - 2 for p in me.polygons)
            out.append(obj)
        for grp, parts in groups.items():
            bm = bmesh.new()
            col = bm.loops.layers.float_color.new("Col")
            for me, rgba in parts:
                before = set(bm.faces)
                bm.from_mesh(me)
                for f in bm.faces:
                    if f not in before:
                        for loop in f.loops:
                            loop[col] = rgba
                bpy.data.meshes.remove(me)
            me = bpy.data.meshes.new(f"{prefix}_{grp}")
            bm.to_mesh(me)
            bm.free()
            me.materials.append(group_material(grp))
            obj = bpy.data.objects.new(f"{prefix}_{grp}", me)
            coll.objects.link(obj)
            obj.matrix_world = M
            self.tris += sum(len(p.vertices) - 2 for p in me.polygons)
            out.append(obj)
        self.b = {}
        return out


def _bsdf(mt):
    return mt.node_tree.nodes.get("Principled BSDF") if mt and mt.use_nodes else None


def _base_colour(mt):
    b = _bsdf(mt)
    return tuple(b.inputs["Base Color"].default_value) if b else (0.5, 0.5, 0.5, 1.0)


def _group(key, mt):
    """Which merged plain material a kit key goes into (None: it keeps its own)."""
    if key in UV_KEYS or key.startswith("shop_") or mt is None:
        return None
    b = _bsdf(mt)
    if b is None or b.inputs["Base Color"].links:
        return None
    if b.inputs["Alpha"].default_value < 1.0 or b.inputs["Emission Strength"].default_value > 0.0:
        return None
    if b.inputs["Metallic"].default_value >= 0.5:
        return "metal"
    return "gloss" if b.inputs["Roughness"].default_value < 0.25 else "matte"


GROUP_FINISH = {"matte": (0.55, 0.0), "gloss": (0.16, 0.0), "metal": (0.28, 0.95)}


def group_material(grp):
    """The merged material: its colour from the mesh's "Col" vertex colours."""
    name = f"M_vroad_goods_{grp}"
    mt = bpy.data.materials.get(name)
    if mt is None:
        rough, metal = GROUP_FINISH[grp]
        mt = plain(name, (1.0, 1.0, 1.0), rough=rough, metal=metal)
        nt = mt.node_tree
        vc = nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        nt.links.new(vc.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    return mt


# ------------------------------------------------------------------ primitives

def T(x, y, z, yaw=0.0, tilt=(0.0, 0.0), s=1.0):
    """A placement matrix: at (x, y, z), turned yaw, tilted (about x, y), scaled."""
    return (Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(tilt[0], 4, "X")
            @ Matrix.Rotation(tilt[1], 4, "Y") @ Matrix.Scale(s, 4))


def lathe(bm, prof, M, segs=14, cap_bottom=True, cap_top=False):
    """A surface of revolution about local z: prof is [(radius, z)] from the bottom up."""
    rings = []
    for r, z in prof:
        if r <= 1e-5:
            rings.append([bm.verts.new(M @ Vector((0, 0, z)))])
            continue
        rings.append([bm.verts.new(M @ Vector((math.cos(a) * r, math.sin(a) * r, z)))
                      for a in (k / segs * math.tau for k in range(segs))])
    for ra, rb in zip(rings, rings[1:]):
        if len(ra) == 1 and len(rb) == 1:
            continue
        if len(ra) == 1:
            for k in range(segs):
                bm.faces.new((ra[0], rb[k], rb[(k + 1) % segs]))
        elif len(rb) == 1:
            for k in range(segs):
                bm.faces.new((ra[k], rb[0], ra[(k + 1) % segs]))
        else:
            for k in range(segs):
                bm.faces.new((ra[k], ra[(k + 1) % segs], rb[(k + 1) % segs], rb[k]))
    if cap_bottom and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])


def band(bm, r, z0, z1, M, rect, segs=16, turns=1.0, a0=0.0):
    """An open label band round local z, UV-mapped onto rect (u round, v up)."""
    uv = bm.loops.layers.uv.verify()
    u0, v0, u1, v1 = rect
    n = segs
    lo, hi = [], []
    for k in range(n + 1):
        a = a0 + k / n * math.tau * turns
        lo.append(bm.verts.new(M @ Vector((math.cos(a) * r, math.sin(a) * r, z0))))
        hi.append(bm.verts.new(M @ Vector((math.cos(a) * r, math.sin(a) * r, z1))))
    for k in range(n):
        f = bm.faces.new((lo[k], lo[k + 1], hi[k + 1], hi[k]))
        ua, ub = u0 + (u1 - u0) * k / n, u0 + (u1 - u0) * (k + 1) / n
        for loop, (u, v) in zip(f.loops, ((ua, v0), (ub, v0), (ub, v1), (ua, v1))):
            loop[uv].uv = (u, v)


def quad(bm, M, w, h, rect, both=False):
    """A flat printed sheet in local x-z (facing -y), w by h, centred at the origin."""
    uv = bm.loops.layers.uv.verify()
    u0, v0, u1, v1 = rect
    pts = [M @ Vector((x, 0, z)) for x, z in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    for loop, (u, v) in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        loop[uv].uv = (u, v)
    if both:
        vs2 = [bm.verts.new(p) for p in reversed(pts)]
        f = bm.faces.new(vs2)
        for loop, (u, v) in zip(f.loops, ((u1, v0), (u0, v0), (u0, v1), (u1, v1))):
            loop[uv].uv = (u, v)


def printed_box(bm, M, sx, sy, sz, rect, front_axis="y"):
    """A printed carton sx by sy by sz (centred, on its base at z 0): the label on the two
    faces across `front_axis` (y: standing packs, z: things lying flat), its border colour
    (a strip of the label's own edge) round the rest."""
    uv = bm.loops.layers.uv.verify()
    u0, v0, u1, v1 = rect
    du, dv = (u1 - u0) * 0.04, (v1 - v0) * 0.04
    edge = (u0 + du * 0.3, v0 + dv * 0.3, u0 + du, v1 - dv * 0.3)
    hx, hy = sx / 2, sy / 2
    c = [M @ Vector((x, y, z)) for z in (0, sz) for y in (-hy, hy) for x in (-hx, hx)]
    v = [bm.verts.new(p) for p in c]
    # Faces: -y, +y (fronts), -x, +x, top, bottom.
    big = {"y": (0, 1), "x": (2, 3), "z": (4, 5)}[front_axis]
    quads = [(0, 1, 5, 4), (3, 2, 6, 7), (2, 0, 4, 6), (1, 3, 7, 5), (4, 5, 7, 6), (0, 2, 3, 1)]
    faces = [(q, rect if k in big else edge) for k, q in enumerate(quads)]
    for (ia, ib, ic, idd), (ru0, rv0, ru1, rv1) in faces:
        f = bm.faces.new((v[ia], v[ib], v[ic], v[idd]))
        for loop, (uu, vv) in zip(f.loops, ((ru0, rv0), (ru1, rv0), (ru1, rv1), (ru0, rv1))):
            loop[uv].uv = (uu, vv)


def box(bm, centre, size, rot=None, bevel=0.0):
    TRD._box_bm(bm, centre, size, rot=rot, bevel=bevel, segs=1 if bevel < 0.006 else 2)


def boxm(bm, M, centre, size, bevel=0.0, segs=2):
    """A box in a frame M (centre and size in that frame), its edges bevelled (rounded with
    more segments: cushions)."""
    mt = M @ Matrix.Translation(centre) @ Matrix.Diagonal((*size, 1.0))
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=mt)
    if bevel > 0:
        edges = list({e for v in ret["verts"] for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=segs, profile=0.5, affect="EDGES", clamp_overlap=True)


def cyl(bm, p0, p1, r0, r1=None, segs=12, cap=True):
    TRD._cyl_bm(bm, p0, p1, r0, r1, segs=segs, cap=cap)


def cylm(bm, M, p0, p1, r0, r1=None, segs=12, cap=True):
    TRD._cyl_bm(bm, M @ Vector(p0), M @ Vector(p1), r0, r1, segs=segs, cap=cap)


def torus(bm, M, centre, axis, rmaj, rmin, n=16, m=6):
    c = M @ Vector(centre)
    ax = M.to_3x3() @ Vector(axis)
    TRD._torus_bm(bm, c, ax, rmaj, rmin, n_maj=n, n_min=m)


def sphere(bm, M, centre, r, u=10, v=6, scale=(1, 1, 1)):
    mt = M @ Matrix.Translation(centre) @ Matrix.Diagonal((*scale, 1.0))
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r, matrix=mt)


def tube(bm, M, pts, r, segs=6):
    TRD._tube_bm(bm, [M @ Vector(p) for p in pts], r, segs=segs)


def extrude_outline(bm, M, outline, thick):
    """A flat part from a 2D outline in local x-y (closed, counter-clockwise), thick in z."""
    top = [bm.verts.new(M @ Vector((x, y, thick / 2))) for x, y in outline]
    bot = [bm.verts.new(M @ Vector((x, y, -thick / 2))) for x, y in outline]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(outline)
    for k in range(n):
        bm.faces.new((bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k]))


# ------------------------------------------------------------------ bottles, tins, jars

# Bottle shapes: outer profile (radius, z) in metres, the neck's top, liquid key, glass.
BOTTLES = {
    # A 640 ml beer: shoulder, long neck, crown cap.
    "beer": ([(0.0, 0.0), (0.03, 0.0), (0.0345, 0.006), (0.0355, 0.02), (0.0355, 0.15), (0.034, 0.175), (0.024, 0.205),
              (0.0145, 0.235), (0.0135, 0.27), (0.0155, 0.276), (0.0155, 0.284)], "beer", "glass_amber", "crown"),
    # A 300 ml soft drink: a waist and ribs.
    "soda": ([(0.0, 0.0), (0.024, 0.0), (0.029, 0.006), (0.03, 0.03), (0.027, 0.06), (0.03, 0.1), (0.03, 0.13),
              (0.022, 0.16), (0.013, 0.19), (0.0125, 0.215), (0.014, 0.22), (0.014, 0.226)], "orange", "glass", "crown"),
    # A 700 ml sauce bottle: tall, straight, long neck, screw cap.
    "sauce": ([(0.0, 0.0), (0.03, 0.0), (0.034, 0.006), (0.034, 0.17), (0.031, 0.19), (0.016, 0.22), (0.0125, 0.25),
               (0.0125, 0.27)], "fish_sauce", "glass", "screw"),
    # A litre of cooking oil in square-shouldered glass.
    "oil": ([(0.0, 0.0), (0.036, 0.0), (0.04, 0.008), (0.04, 0.2), (0.036, 0.225), (0.018, 0.25), (0.014, 0.275),
             (0.014, 0.29)], "oil", "glass", "screw"),
    # Petrol sold by the litre in old spirit bottles, plugged with a twist of plastic.
    "petrol": ([(0.0, 0.0), (0.034, 0.0), (0.038, 0.008), (0.038, 0.19), (0.033, 0.215), (0.016, 0.24),
                (0.0125, 0.275), (0.0135, 0.285)], "petrol", "glass", "cork"),
    # Rice spirit in a flat-shouldered clear flask.
    "spirit": ([(0.0, 0.0), (0.03, 0.0), (0.033, 0.006), (0.033, 0.16), (0.022, 0.185), (0.012, 0.2), (0.011, 0.23),
                (0.012, 0.235)], "water", "glass", "screw"),
    # 120 ml tonic or hair oil.
    "tonic": ([(0.0, 0.0), (0.019, 0.0), (0.022, 0.004), (0.022, 0.085), (0.017, 0.1), (0.009, 0.11), (0.009, 0.125)],
              "oil", "glass_green", "screw"),
    # A small brown medicine bottle.
    "medicine": ([(0.0, 0.0), (0.016, 0.0), (0.018, 0.004), (0.018, 0.065), (0.012, 0.076), (0.008, 0.082),
                  (0.008, 0.094)], "syrup", "glass_amber", "screw"),
    # A perfume bottle, faceted and squat.
    "perfume": ([(0.0, 0.0), (0.026, 0.0), (0.028, 0.006), (0.028, 0.05), (0.02, 0.064), (0.006, 0.07),
                 (0.006, 0.078)], "water", "glass", "screw"),
}


def bottle(K, M, kind="beer", liquid=None, glass=None, label=None, fill=0.82, segs=14, cap=None):
    """A bottle standing at M's origin: its glass, the liquid to `fill`, its cap or plug and
    its label wrapped round below the shoulder."""
    prof, liq, gl, cap_kind = BOTTLES[kind]
    liq = liquid or liq
    gl = glass or gl
    cap_kind = cap or cap_kind
    lathe(K[gl], prof, M, segs=segs, cap_bottom=True, cap_top=False)
    top = prof[-1][1]
    body = max(z for r, z in prof if r >= prof[3][0] * 0.98)
    if liq and fill > 0:
        h = body * fill
        inner = [(0.0, 0.004)] + [(r * 0.86, max(0.004, min(z, h))) for r, z in prof[1:] if z < h] + [(prof[3][0] * 0.86, h), (0.0, h)]
        lathe(K[liq], inner, M, segs=max(8, segs - 4), cap_bottom=False)
    rn = prof[-1][0]
    if cap_kind == "crown":
        lathe(K["gold_paint" if kind == "beer" else "plastic_red"], [(rn + 0.0012, top - 0.008), (rn + 0.002, top - 0.006),
                                                                      (rn + 0.0016, top + 0.002), (0.0, top + 0.004)], M, segs=21, cap_bottom=False)
    elif cap_kind == "screw":
        key = {"tonic": "gold_paint", "perfume": "gold_paint", "medicine": "plastic_black"}.get(kind, "plastic_white")
        lathe(K[key], [(rn + 0.0015, top - 0.016), (rn + 0.0025, top - 0.015), (rn + 0.0025, top + 0.002),
                       (rn + 0.001, top + 0.004), (0.0, top + 0.004)], M, segs=16, cap_bottom=True)
    elif cap_kind == "cork":
        lathe(K["plastic_red"], [(rn * 0.9, top - 0.012), (rn * 1.08, top + 0.004), (rn * 0.9, top + 0.016),
                                 (rn * 0.4, top + 0.026), (0.0, top + 0.028)], M, segs=10, cap_bottom=True)
    if label:
        r = prof[3][0] + 0.0008
        z0 = body * 0.3
        z1 = min(body * 0.86, z0 + 2 * math.pi * r / 4.0)
        band(K["label"], r, z0, z1, M, wrap_rect(label), segs=segs + 2)
    return top + 0.004


def tin(K, M, r, h, label=None, lid="tinplate", seams=True, segs=18, open_top=False):
    """A tin can on its base at M's origin: rolled rims top and bottom, a ribbed body,
    its label round the middle."""
    k = K["tinplate"]
    prof = [(0.0, 0.0), (r - 0.004, 0.0), (r, 0.004), (r + 0.0012, 0.006), (r, 0.01)]
    if seams and h > 0.06:
        for z in np.linspace(0.02, h - 0.02, 4):
            prof += [(r, z - 0.003), (r - 0.0009, z), (r, z + 0.003)]
    prof += [(r, h - 0.01), (r + 0.0012, h - 0.006), (r, h - 0.003), (r - 0.004, h)]
    prof += [(r - 0.006, h - 0.003)] if open_top else [(0.0, h - 0.002)]
    lathe(k, prof, M, segs=segs)
    if lid != "tinplate" and not open_top:
        lathe(K[lid], [(r + 0.002, h - 0.02), (r + 0.003, h - 0.018), (r + 0.003, h + 0.004), (0.0, h + 0.006)], M, segs=segs)
    if label:
        band(K["label"], r + 0.0006, 0.012, h - 0.012, M, wrap_rect(label), segs=segs + 2)


def jar(K, M, r, h, label=None, contents=None, lid="plastic_red", segs=16):
    """A glass jar with a screw lid, filled with `contents` (sweets, pickles, sugar)."""
    prof = [(0.0, 0.0), (r - 0.006, 0.0), (r, 0.006), (r, h - 0.02), (r - 0.008, h - 0.01), (r - 0.008, h)]
    lathe(K["glass"], prof, M, segs=segs)
    lathe(K[lid], [(r - 0.006, h - 0.012), (r - 0.003, h - 0.011), (r - 0.003, h + 0.012), (r - 0.006, h + 0.016),
                   (0.0, h + 0.017)], M, segs=segs)
    if contents == "sweets":
        rng = np.random.default_rng(int(abs(M.translation.x * 1000 + M.translation.y * 77)) % 9999)
        fill = h * 0.72
        lathe(K["candy"], [(0.0, 0.004), (r * 0.9, 0.004), (r * 0.9, fill * 0.9), (0.0, fill * 0.9)], M, segs=segs - 4)
        for _ in range(14):
            a, d = rng.uniform(0, math.tau), r * 0.78 * math.sqrt(rng.random())
            sphere(K[("candy", "candy_b", "candy_c")[int(rng.integers(3))]], M,
                   (math.cos(a) * d, math.sin(a) * d, fill * 0.9 + rng.uniform(-0.004, 0.006)), 0.008, 8, 5)
    elif contents:
        lathe(K[contents], [(0.0, 0.004), (r * 0.9, 0.004), (r * 0.9, h * 0.75), (0.0, h * 0.76)], M, segs=segs - 4)
    if label:
        band(K["label"], r + 0.0006, h * 0.25, h * 0.62, M, wrap_rect(label), segs=segs + 2)


def carton(K, M, sx, sy, sz, face, front_axis="y"):
    """A printed box (cigarettes, soap, tea, matches...) on its base at M's origin."""
    printed_box(K["label"], M, sx, sy, sz, face_rect(face), front_axis)


def packet(K, M, sx, sy, sz, face):
    """A pillow packet (noodles, snacks): printed faces bulging, crimped seals at the ends."""
    printed_box(K["label"], M, sx, sy * 0.86, sz, face_rect(face))
    for s in (-1, 1):
        boxm(K["paper"], M, (0, 0, sz * 0.5 + s * sz * 0.5), (sx * 1.02, sy * 0.18, 0.006))


def bowl(K, M, r, h, key="porcelain", rim=None, inner=None, segs=18):
    """A bowl on its foot ring at M's origin; `rim` a coloured band; `inner` food in it."""
    t = 0.003
    prof = [(0.0, 0.004), (r * 0.36, 0.004), (r * 0.36, 0.0), (r * 0.42, 0.0), (r * 0.44, 0.006),
            (r * 0.72, h * 0.3), (r * 0.94, h * 0.75), (r, h), (r - t, h + 0.001), (r * 0.92 - t, h * 0.72),
            (r * 0.68 - t, h * 0.28), (0.0, 0.008)]
    lathe(K[key], prof, M, segs=segs, cap_bottom=False)
    if rim:
        lathe(K[rim], [(r * 0.995, h - 0.006), (r * 1.002, h - 0.005), (r * 1.002, h - 0.001), (r * 0.995, h)], M,
              segs=segs, cap_bottom=False)
    if inner:
        lathe(K[inner], [(0.0, h * 0.55), (r * 0.86, h * 0.55), (r * 0.82, h * 0.62), (0.0, h * 0.66)], M, segs=segs - 4,
              cap_bottom=False)


def bowl_stack(K, M, n, r=0.075, h=0.05, key="porcelain", rim="enamel_blue"):
    for k in range(n):
        bowl(K, M @ T(0, 0, k * h * 0.42), r, h, key, rim)


def tumbler(K, M, r=0.032, h=0.11, liquid=None, ice=False):
    """A ribbed drinking glass, its drink and the ice in it."""
    prof = [(0.0, 0.0), (r * 0.86, 0.0), (r * 0.9, 0.006), (r, h), (r - 0.002, h)]
    lathe(K["glass"], prof, M, segs=16, cap_bottom=True)
    if liquid:
        lathe(K[liquid], [(0.0, 0.006), (r * 0.84, 0.006), (r * 0.93, h * 0.72), (0.0, h * 0.72)], M, segs=12, cap_bottom=False)
    if ice:
        for k in range(3):
            boxm(K["glass"], M @ T(0, 0, 0, yaw=k * 1.9), (r * 0.35 * math.cos(k * 2.1), r * 0.35 * math.sin(k * 2.1),
                                                           h * 0.66 + k * 0.004), (0.016, 0.016, 0.014), bevel=0.003)


def spoon(K, M, key="porcelain"):
    """A Chinese soup spoon lying on its back."""
    lathe(K[key], [(0.0, 0.0), (0.016, 0.002), (0.022, 0.008), (0.023, 0.012)], M @ Matrix.Diagonal((1.25, 1.0, 1.0, 1.0)),
          segs=12, cap_bottom=False)
    boxm(K[key], M, (0.05, 0, 0.012), (0.06, 0.012, 0.005), bevel=0.002)


def chopsticks(K, M, n=24, key="shop_bamboo"):
    """A holder of chopsticks: a tin cup and the sticks standing loose in it."""
    lathe(K["tinplate"], [(0.0, 0.0), (0.03, 0.0), (0.03, 0.11), (0.028, 0.11), (0.028, 0.006), (0.0, 0.006)], M, segs=16)
    rng = np.random.default_rng(n)
    for _ in range(n):
        a, d = rng.uniform(0, math.tau), 0.022 * math.sqrt(rng.random())
        p0 = Vector((math.cos(a) * d, math.sin(a) * d, 0.006))
        lean = Vector((rng.normal(0, 0.03), rng.normal(0, 0.03), 1)).normalized()
        cylm(K[key], M, p0, p0 + lean * 0.24, 0.0032, 0.002, segs=5, cap=False)


def towel(K, M, w=0.32, d=0.24, h=0.035, key="shop_linen_towel"):
    """A folded towel: soft-edged, the fold's roll along one side."""
    boxm(K[key], M, (0, 0, h / 2), (w, d, h), bevel=h * 0.45)
    cylm(K[key], M, (-w / 2 + 0.01, -d / 2, h / 2), (-w / 2 + 0.01, d / 2, h / 2), h * 0.52, segs=8)


def comb(K, M, length=0.17, key="plastic_black"):
    """A comb: its spine and fine teeth on one half, coarse on the other."""
    boxm(K[key], M, (0, 0, 0.0025), (length, 0.012, 0.005), bevel=0.0015)
    n = int(length / 0.004)
    for k in range(n):
        x = -length / 2 + 0.003 + k * (length - 0.006) / n
        boxm(K[key], M, (x, 0.012 + 0.0, 0.0025), (0.0016 if k < n // 2 else 0.0024, 0.02, 0.0035))


def scissors(K, M, s=1.0, key="chrome"):
    """Barber's scissors, half open: two blades crossed at the pivot, two finger rings."""
    for sgn in (-1, 1):
        a = sgn * 0.14
        R = M @ Matrix.Rotation(a, 4, "Z") @ Matrix.Scale(s, 4)
        extrude_outline(K[key], R, [(0.0, -0.004), (0.11, -0.0015), (0.115, 0.0), (0.11, 0.002), (0.0, 0.005),
                                    (-0.03, 0.004), (-0.03, -0.004)], 0.0025)
        torus(K["plastic_black"], R, (-0.052, sgn * 0.004, 0), (0, 0, 1), 0.014, 0.0035, n=14, m=5)
    cylm(K["brass"], M, (0, 0, -0.003), (0, 0, 0.004), 0.003, segs=8)


def straight_razor(K, M):
    """A straight razor folded in its handle."""
    boxm(K["plastic_cream"], M, (0, 0, 0.004), (0.13, 0.018, 0.008), bevel=0.003)
    extrude_outline(K["chrome"], M @ T(0.004, 0, 0.0095), [(-0.06, -0.008), (0.06, -0.006), (0.066, 0.0), (0.06, 0.008),
                                                            (-0.06, 0.008)], 0.0012)
    cylm(K["brass"], M, (-0.058, 0, 0), (-0.058, 0, 0.011), 0.0025, segs=8)


def shaving_brush(K, M):
    lathe(K["plastic_cream"], [(0.0, 0.0), (0.016, 0.0), (0.018, 0.01), (0.013, 0.03), (0.015, 0.05), (0.0, 0.05)], M, segs=14)
    lathe(K["bristle"], [(0.0, 0.048), (0.014, 0.048), (0.02, 0.07), (0.016, 0.09), (0.0, 0.098)], M, segs=14, cap_bottom=False)


def clippers(K, M):
    """Hand hair clippers: two handles and the toothed head."""
    for sgn in (-1, 1):
        R = M @ Matrix.Rotation(sgn * 0.12, 4, "Z")
        cylm(K["chrome"], R, (0, 0, 0.006), (-0.14, 0, 0.006), 0.006, 0.0045, segs=8)
    boxm(K["chrome"], M, (0.025, 0, 0.007), (0.05, 0.045, 0.01), bevel=0.003)
    for k in range(12):
        boxm(K["steel"], M, (0.052, -0.02 + k * 0.0036, 0.004), (0.008, 0.0016, 0.004))


def spray_bottle(K, M):
    lathe(K["plastic_white"], [(0.0, 0.0), (0.03, 0.0), (0.032, 0.006), (0.032, 0.13), (0.02, 0.15), (0.012, 0.155),
                               (0.012, 0.16)], M, segs=16)
    lathe(K["water"], [(0.0, 0.004), (0.029, 0.004), (0.029, 0.08), (0.0, 0.08)], M, segs=12, cap_bottom=False)
    boxm(K["plastic_red"], M, (0.004, 0, 0.18), (0.05, 0.022, 0.04), bevel=0.005)
    boxm(K["plastic_red"], M, (0.012, 0, 0.152), (0.012, 0.012, 0.04), bevel=0.003)


def spanner(K, M, length=0.18, key="chrome"):
    """An open-ended spanner, flat."""
    w = length * 0.11
    extrude_outline(K[key], M, [(-length / 2 + w, -w * 0.35), (length / 2 - w, -w * 0.3), (length / 2 - w, w * 0.3),
                                (-length / 2 + w, w * 0.35)], 0.004)
    for sgn in (-1, 1):
        cx = sgn * (length / 2 - w * 0.6)
        pts = []
        for k in range(14):
            a = (k / 13) * math.pi * 1.5 - math.pi * 0.75 + (0 if sgn > 0 else math.pi)
            pts.append((cx + math.cos(a) * w, math.sin(a) * w))
        extrude_outline(K[key], M, pts, 0.005)


def screwdriver(K, M, length=0.2, handle="plastic_yellow"):
    lathe(K[handle], [(0.0, 0.0), (0.011, 0.002), (0.013, 0.02), (0.012, 0.07), (0.008, 0.085), (0.0, 0.088)],
          M @ Matrix.Rotation(-math.pi / 2, 4, "Y"), segs=10)
    cylm(K["steel"], M, (0.085, 0, 0), (length, 0, 0), 0.003, 0.0024, segs=6)


def pliers(K, M):
    for sgn in (-1, 1):
        R = M @ Matrix.Rotation(sgn * 0.09, 4, "Z")
        cylm(K["plastic_red"], R, (-0.02, 0, 0.005), (-0.14, sgn * 0.002, 0.005), 0.0065, 0.0055, segs=8)
        extrude_outline(K["steel"], R, [(-0.02, -0.005), (0.06, -0.002), (0.062, 0.0), (0.06, sgn * 0.004),
                                        (-0.02, 0.005)], 0.006)


def hammer(K, M):
    cylm(K["shop_table_wood"], M, (0, 0, 0.012), (-0.28, 0, 0.012), 0.012, 0.011, segs=10)
    boxm(K["cast_iron"], M, (0.0, 0, 0.012), (0.03, 0.1, 0.026), bevel=0.004)


def wall_paper(K, M, w, h, face, both=False):
    """A printed sheet pinned flat (a calendar, a chart, a notice), facing local -y."""
    quad(K["label"], M, w, h, face_rect(face), both=both)


def noodle_nest(K, M, r=0.036, key="noodles", seed=0):
    """A nest of fresh noodles: strands looped and tangled on themselves, not a ring."""
    rng = np.random.default_rng(seed)
    for k in range(7):
        tilt = (rng.normal(0, 0.35), rng.normal(0, 0.35))
        rr = r * rng.uniform(0.55, 1.0)
        z = rng.uniform(0.006, 0.022)
        a0 = rng.uniform(0, math.tau)
        pts = []
        for j in range(23):
            a = a0 + j / 22 * math.tau * 1.05
            wob = 1 + 0.18 * math.sin(a * 3 + k) + 0.08 * math.sin(a * 7 + 2 * k)
            pts.append((math.cos(a) * rr * wob, math.sin(a) * rr * wob, z + 0.006 * math.sin(a * 2 + k)))
        tube(K[key], M @ Matrix.Rotation(tilt[0], 4, "X") @ Matrix.Rotation(tilt[1], 4, "Y"), pts, 0.0032, segs=4)


def curved_sheet(bm, M, centre, radius, a0, a1, width, n=14, thick=0.004):
    """A strip of sheet metal bent round local y (a mudguard): from angle a0 to a1 (radians,
    in x-z), `width` across, closed at its edges."""
    c = Vector(centre)
    outer, inner = [], []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        d = Vector((math.cos(a), 0, math.sin(a)))
        row_o, row_i = [], []
        for y in (-width / 2, -width * 0.35, width * 0.35, width / 2):
            lip = 0.012 if abs(y) == width / 2 else 0.0
            row_o.append(bm.verts.new(M @ (c + d * (radius + thick - lip) + Vector((0, y, 0)))))
            row_i.append(bm.verts.new(M @ (c + d * (radius - lip) + Vector((0, y, 0)))))
        outer.append(row_o)
        inner.append(row_i)
    for k in range(n):
        for j in range(3):
            bm.faces.new((outer[k][j], outer[k][j + 1], outer[k + 1][j + 1], outer[k + 1][j]))
            bm.faces.new((inner[k + 1][j], inner[k + 1][j + 1], inner[k][j + 1], inner[k][j]))
        bm.faces.new((outer[k][0], outer[k + 1][0], inner[k + 1][0], inner[k][0]))
        bm.faces.new((inner[k][3], inner[k + 1][3], outer[k + 1][3], outer[k][3]))
