"""Weathered surfaces for Episode 1's two shrines (2026-11 redesign): the carved
teak Preah Phum (spirit house) of a well-off 1930s family and the old Neak Ta
shrine under the banyan.

- Red lacquer over teak, faded and flaking back to silver-grey wood.
- Gilt carving: gold leaf on a red bole, rubbed through on the high points and
  gone black with grime in the hollows (metallic in the ORM map).
- Laterite: the porous red-brown building stone of Cambodia, pitted with holes.
- Unglazed earthenware smoked by the fire that made it, and smoke-dark sand.
- Small gradient strips for joss sticks, lotus buds and young coconuts.

Maps are generated (numpy) from the project's CC0 library photographs and saved
in art-source/textures/ep1/. Arrays are rows bottom-to-top as Blender stores
pixels. Run inside Blender.
"""
import math
import os

import bpy
import numpy as np

import weathering
from colonial_materials import aniso_fbm, aniso_noise, painted_boards, photo_rgb
from kit import ROOT, image
from weathering import cracks, fbm, mould_runs, photo_grain, tile_noise

OUT = os.path.join(ROOT, "art-source", "textures", "ep1")


def _write(name, rgb, non_color=False, alpha=None):
    size_y, size_x = rgb.shape[:2]
    os.makedirs(OUT, exist_ok=True)
    rgba = np.ones((size_y, size_x, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(rgb, 0, 1)
    if alpha is not None:
        rgba[:, :, 3] = np.clip(alpha, 0, 1)
    img = bpy.data.images.get(name) or bpy.data.images.new(name, width=size_x, height=size_y, alpha=True)
    if tuple(img.size) != (size_x, size_y):
        img.scale(size_x, size_y)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(OUT, name + ".png")
    img.file_format = "PNG"
    img.save()
    return img


def _normal(height, strength):
    size = height.shape[0]
    gy, gx = np.gradient(height)
    n = np.ones(height.shape + (3,))
    n[:, :, 0] = .5 - np.clip(gx * strength * size / 64, -.45, .45)
    n[:, :, 1] = .5 - np.clip(gy * strength * size / 64, -.45, .45)
    n[:, :, 2] = .9
    return n


def pbr(name, rgb, height, rough, metal=None, occlusion=None, normal_strength=2.2, tile=1.0, backface=True):
    """A glTF material from colour, height (to a normal map) and per-pixel roughness
    and metalness (packed ORM: occlusion R, roughness G, metallic B)."""
    bc = _write(f"T_ep1_{name}_BC", rgb)
    nm = _write(f"T_ep1_{name}_N", _normal(height, normal_strength), non_color=True)
    orm = np.stack((np.ones_like(rough) if occlusion is None else occlusion, rough,
                    np.zeros_like(rough) if metal is None else metal), axis=-1)
    om = _write(f"T_ep1_{name}_ORM", orm, non_color=True)
    mat = bpy.data.materials.get(f"M_{name}") or bpy.data.materials.new(f"M_{name}")
    mat.use_backface_culling = backface
    nt = mat.node_tree
    nt.nodes.clear()
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bc
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = nm
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tn.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    to = nt.nodes.new("ShaderNodeTexImage")
    to.image = om
    split = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(to.outputs["Color"], split.inputs["Color"])
    nt.links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    bsdf.inputs["Specular IOR Level"].default_value = .4
    mat["tile"] = tile
    return mat


def _rename(mat, name):
    old = bpy.data.materials.get(name)
    if old and old != mat:
        old.name = name + "_old"
    mat.name = name
    return mat


def _teak_grey(size, rng, tone=(.33, .32, .29)):
    """Silver-grey weathered teak: the library teak photograph, its grain kept."""
    photo = photo_rgb("teak_veneer", size)
    lum = photo.mean(axis=2)
    grain = lum / (lum.mean() + 1e-6)
    grey = np.array(tone)[None, None, :] * grain[:, :, None]
    return grey * .8 + photo * .2 * .5, grain


# ------------------------------------------------------------- the spirit house


def red_lacquer_teak():
    """Cinnabar lacquer over teak, sun-faded to brick red, flaking along the grain."""
    weathering.OUT = OUT
    mat = painted_boards("T_ep1_pp_red_lacquer", (.36, .055, .035), 2611, boards=1, size=2048, tile=.45,
                         peel=.72, grime=.55, lap=False, wood=(.32, .31, .28), rough=.66, joints=False)
    return _rename(mat, "M_phra_phum_red_lacquer_teak")


def grey_teak():
    """Unpainted teak boards and shingles gone silver, with lichen and old paint ghosts."""
    weathering.OUT = OUT
    mat = painted_boards("T_ep1_pp_grey_teak", (.29, .27, .24), 2612, boards=3, size=1024, tile=.6,
                         peel=.2, grime=.8, lap=False, wood=(.29, .28, .26), rough=.9, joints=True)
    return _rename(mat, "M_phra_phum_grey_teak")


def gilt(name="phra_phum_gilt_carving", seed=2613, size=2048, tile=.14):
    """Gold leaf laid on red bole over teak. Worn through where hands and rain
    reach, so red and then grey wood show; tarnished, with black grime in pits."""
    rng = np.random.default_rng(seed)
    wood, grain = _teak_grey(size, rng)
    bole = np.array([.30, .065, .04])[None, None, :] * (.85 + .3 * fbm(size, rng))[:, :, None]
    film = fbm(size, rng, ((5, .4), (13, .3), (37, .2), (90, .1)))
    gold_tint = np.array([.66, .47, .2])
    tarnish = np.array([.32, .23, .1])
    t = np.clip(fbm(size, rng, ((3, .5), (9, .3), (27, .2))) * 1.4 - .3, 0, 1)
    gold = gold_tint * (1 - t[:, :, None]) + tarnish * t[:, :, None]
    gold = gold * (.8 + .35 * film)[:, :, None]
    # Leaf seams: gold leaf goes on in small squares; their overlaps show faintly.
    yy, xx = np.mgrid[:size, :size]
    leaf = 96
    seam = ((yy % leaf) < 2) | (((xx + (yy // leaf % 2) * 41) % leaf) < 2)
    gold[seam] *= .82
    wear = fbm(size, rng, ((9, .4), (23, .3), (61, .2), (150, .1)))
    keep_gold = wear < np.quantile(wear, .6)
    keep_bole = wear < np.quantile(wear, .84)
    rgb = np.where(keep_gold[:, :, None], gold, np.where(keep_bole[:, :, None], bole, wood))
    edge = (wear > np.quantile(wear, .5)) & (wear < np.quantile(wear, .53))
    rgb[edge] *= .6
    grime = np.clip((fbm(size, rng, ((6, .5), (17, .3), (48, .2))) - .45) * 2.2, 0, 1)
    black = np.array([.03, .025, .02])
    rgb = rgb * (1 - .65 * grime[:, :, None]) + black * .65 * grime[:, :, None]
    runs = mould_runs(size, rng, count=80, strength=.6)
    rgb *= (1 - .45 * runs)[:, :, None]
    craze = cracks(size, rng, count=60) & keep_bole
    rgb[craze] *= .45
    metal = np.where(keep_gold, .95 * (1 - .7 * grime), 0)
    rough = np.where(keep_gold, .32 + .35 * t + .3 * grime, np.where(keep_bole, .62, .9))
    height = np.where(keep_gold, .12, np.where(keep_bole, .08, .1 * grain - .05)) + .05 * film - .05 * craze
    return pbr(name, rgb, height, rough, metal, normal_strength=2.0, tile=tile)


def laterite(name="phra_phum_laterite", seed=2614, size=1024, tile=.5, moss=.7):
    """Laterite blocks: rust and ochre, a vesicular sponge of holes, black crust,
    pale lichen and moss where the soil splashes."""
    rng = np.random.default_rng(seed)
    grain = photo_grain("clay_plaster", size)
    blotch = fbm(size, rng, ((3, .5), (8, .3), (19, .2)))
    rust = np.array([.36, .14, .06])
    ochre = np.array([.50, .31, .13])
    purple = np.array([.20, .085, .07])
    mix = fbm(size, rng, ((5, .5), (14, .5)))
    rgb = rust * (1 - mix[:, :, None]) + ochre * mix[:, :, None]
    dark = np.clip((blotch - .55) * 3, 0, 1)
    rgb = rgb * (1 - dark[:, :, None]) + purple * dark[:, :, None]
    rgb *= (.75 + .35 * grain)[:, :, None]
    # The pores: irregular cells, some deep and black, some half-filled with soil.
    pores = fbm(size, rng, ((40, .5), (90, .35), (200, .15)))
    holes = pores < np.quantile(pores, .14)
    deep = pores < np.quantile(pores, .06)
    rgb[holes] *= .45
    rgb[deep] = np.array([.03, .02, .015])
    crust = np.clip((fbm(size, rng, ((4, .6), (11, .4))) - .58) * 3, 0, 1)
    rgb *= (1 - .55 * crust)[:, :, None]
    lichen = fbm(size, rng, ((28, .6), (64, .4))) > .8
    rgb[lichen & ~holes] = rgb[lichen & ~holes] * .5 + np.array([.42, .43, .34]) * .5
    m = np.clip((fbm(size, rng, ((3, .5), (9, .3), (27, .2))) - .6) * 2.4, 0, 1) * moss
    rgb = rgb * (1 - .7 * m[:, :, None]) + np.array([.06, .09, .03]) * .7 * m[:, :, None]
    height = .4 * blotch + .1 * grain - .9 * holes - .5 * deep + .2 * m
    rough = .93 - .1 * m
    return pbr(name, rgb, height, rough, normal_strength=3.4, tile=tile)


def earthenware(name="phra_phum_offering_clay", seed=2615, size=1024, tile=.25):
    """Low-fired village pottery: orange-buff clay with dark fire clouds, wiped soot."""
    rng = np.random.default_rng(seed)
    grain = photo_grain("clay_plaster", size)
    body = np.array([.46, .23, .12]) * (.8 + .3 * fbm(size, rng))[:, :, None]
    cloud = np.clip((fbm(size, rng, ((2, .6), (5, .4))) - .5) * 2.5, 0, 1)
    rgb = body * (1 - .75 * cloud[:, :, None]) + np.array([.07, .055, .045]) * .75 * cloud[:, :, None]
    rgb *= (.85 + .2 * grain)[:, :, None]
    speck = fbm(size, rng, ((120, .6), (240, .4))) > .85
    rgb[speck] *= .7
    height = .2 * grain + .1 * cloud + .1 * speck
    return pbr(name, rgb, height, np.full((size, size), .86), normal_strength=1.4, tile=tile)


def sand_ash(name="phra_phum_incense_sand", seed=2616, size=512, tile=.12):
    """River sand in the incense bowl, grey with years of fallen ash."""
    rng = np.random.default_rng(seed)
    fine = rng.random((size, size))
    blot = fbm(size, rng, ((4, .5), (11, .5)))
    sand = np.array([.42, .36, .27])
    ash = np.array([.33, .32, .30])
    a = np.clip((blot - .35) * 1.8, 0, 1)
    rgb = sand * (1 - a[:, :, None]) + ash * a[:, :, None]
    rgb *= (.7 + .45 * fine)[:, :, None]
    flecks = fine > .985
    rgb[flecks] = np.array([.04, .03, .03])
    height = .5 * fine + .3 * blot
    return pbr(name, rgb, height, np.full((size, size), .97), normal_strength=1.2, tile=tile)


def beeswax(name="phra_phum_beeswax"):
    """Hand-rolled Khmer beeswax: honey-brown, darker where it has run and gathered dust."""
    mat = bpy.data.materials.get(f"M_{name}") or bpy.data.materials.new(f"M_{name}")
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (.36, .22, .07, 1)
    bsdf.inputs["Roughness"].default_value = .38
    bsdf.inputs["Subsurface Weight"].default_value = .08
    bsdf.inputs["Subsurface Radius"].default_value = (.4, .2, .08)
    bsdf.inputs["Subsurface Scale"].default_value = .01
    mat["tile"] = 1.0
    return mat


def strip(name, stops, size=(16, 256), rough=.8, metal=0.0, noise=.08, seed=0, emissive=None, backface=True):
    """A gradient strip along v (bottom to top) for long thin things: joss sticks,
    lotus petals, coconut. `stops`: [(v, (r, g, b)), ...]."""
    w, h = size
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, h)
    rgb = np.zeros((h, w, 3))
    for c in range(3):
        col = np.interp(v, [s[0] for s in stops], [s[1][c] for s in stops])
        rgb[:, :, c] = col[:, None]
    rgb *= (1 + noise * (rng.random((h, w)) - .5))[:, :, None]
    img = _write(f"T_ep1_{name}_BC", rgb)
    mat = bpy.data.materials.get(f"M_{name}") or bpy.data.materials.new(f"M_{name}")
    mat.use_backface_culling = backface
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.extension = "EXTEND"
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emissive:
        bsdf.inputs["Emission Color"].default_value = (*emissive[0], 1)
        bsdf.inputs["Emission Strength"].default_value = emissive[1]
    mat["tile"] = 0.0
    return mat


def plain(name, colour, rough=.8, metal=0.0, emissive=None, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emissive:
        bsdf.inputs["Emission Color"].default_value = (*emissive[0], 1)
        bsdf.inputs["Emission Strength"].default_value = emissive[1]
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
        mat.use_backface_culling = False
    mat["tile"] = 1.0
    return mat


def soot_teak(name="phra_phum_soot_chamber", seed=2617, size=1024, tile=.6):
    """The inside of the spirit house: teak blackened by decades of candle smoke."""
    rng = np.random.default_rng(seed)
    wood, grain = _teak_grey(size, rng, tone=(.07, .06, .05))
    smoke = fbm(size, rng, ((2, .6), (6, .4)))
    rgb = wood * (.6 + .5 * smoke)[:, :, None]
    height = .3 * grain
    return pbr(name, rgb, height, np.full((size, size), .88), normal_strength=1.8, tile=tile)


# ------------------------------------------------------------- the Neak Ta shrine


def limewash_brick(name="neakta_limewash", seed=2618, size=1024, tile=.7):
    """Old lime over brick: grey-white gone yellow, soft grey-green damp stains
    washing down from the banyan's drip, black lichen crust, a few hairline cracks."""
    rng = np.random.default_rng(seed)
    grain = photo_grain("clay_plaster", size)
    damp = fbm(size, rng)
    lime = np.array([.47, .46, .39]) * (.82 + .25 * damp)[:, :, None] * (.93 + .08 * grain)[:, :, None]
    yellow = np.clip((fbm(size, rng, ((3, .6), (7, .4))) - .4) * 2, 0, 1)
    rgb = lime * (1 - .3 * yellow[:, :, None]) + np.array([.45, .38, .22]) * .3 * yellow[:, :, None]
    # Broad, soft wash-down stains: long vertically, never thin lines.
    wash = aniso_fbm(size, rng, ((10, 2, .5), (22, 4, .3), (45, 7, .2)))
    wash = np.clip((wash - .45) * 1.8, 0, 1) * (.6 + .4 * fbm(size, rng, ((3, .6), (6, .4))))
    stain = np.array([.13, .14, .1])
    rgb = rgb * (1 - .55 * wash[:, :, None]) + stain * .55 * wash[:, :, None]
    algae = np.clip((fbm(size, rng, ((4, .5), (10, .3), (26, .2))) - .55) * 2.2, 0, 1)
    rgb = rgb * (1 - .45 * algae[:, :, None]) + np.array([.08, .11, .05]) * .45 * algae[:, :, None]
    crust = np.clip((fbm(size, rng, ((8, .45), (20, .35), (50, .2))) - .58) * 2.0, 0, 1)
    rgb = rgb * (1 - .5 * crust[:, :, None]) + np.array([.04, .045, .035]) * .5 * crust[:, :, None]
    craze = cracks(size, rng, count=8)
    rgb[craze] *= .85
    height = .3 * damp + .15 * grain + .2 * crust - .05 * craze
    return pbr(name, rgb, height, np.full((size, size), .95) - .1 * algae, normal_strength=1.8, tile=tile)


def old_brick(name="neakta_brick", seed=2619, size=1024, tile=1.0):
    weathering.OUT = OUT
    mat = weathering.old_brick(f"T_ep1_{name}", seed, size=size, tile=tile, soot=.5)
    return _rename(mat, f"M_{name}")


def sandstone(name="neakta_sandstone", seed=2620, size=1024, tile=.45):
    """Grey-green Angkorian sandstone: black crust, lichen rosettes, honeycomb pitting."""
    rng = np.random.default_rng(seed)
    grain = photo_grain("clay_plaster", size)
    blotch = fbm(size, rng)
    base = np.array([.30, .29, .24]) * (.75 + .45 * blotch)[:, :, None] * grain[:, :, None]
    crust = np.clip((fbm(size, rng, ((5, .5), (13, .3), (35, .2))) - .5) * 2.6, 0, 1)
    rgb = base * (1 - .75 * crust[:, :, None]) + np.array([.035, .035, .03]) * .75 * crust[:, :, None]
    rosette = fbm(size, rng, ((10, .6), (24, .4)))
    lichen = np.clip((rosette - .72) * 6, 0, 1) * .45
    rgb = rgb * (1 - lichen[:, :, None]) + np.array([.42, .43, .36]) * lichen[:, :, None]
    algae = np.clip((fbm(size, rng, ((3, .6), (8, .4))) - .55) * 2, 0, 1)
    rgb = rgb * (1 - .5 * algae[:, :, None]) + np.array([.08, .11, .05]) * .5 * algae[:, :, None]
    pits = fbm(size, rng, ((80, .5), (170, .5)))
    hole = pits < np.quantile(pits, .035)
    rgb[hole] *= .62
    runs = mould_runs(size, rng, count=90, strength=.7)
    rgb *= (1 - .5 * runs)[:, :, None]
    height = .5 * blotch + .2 * crust + .3 * lichen - .6 * hole + .1 * grain
    rough = np.full((size, size), .94)
    return pbr(name, rgb, height, rough, normal_strength=2.8, tile=tile)


def cotton(name, colour, seed, size=512, tile=.3, dirt=.6):
    """Cotton cloth from the library linen weave, faded and stained."""
    rng = np.random.default_rng(seed)
    photo = photo_rgb("rough_linen", size)
    lum = photo.mean(axis=2)
    weave = lum / (lum.mean() + 1e-6)
    rgb = np.array(colour)[None, None, :] * weave[:, :, None]
    fade = fbm(size, rng, ((3, .6), (8, .4)))
    rgb = rgb * (1 - .35 * fade[:, :, None]) + np.array([.5, .46, .38]) * .35 * fade[:, :, None] * np.array(colour).mean()
    stain = np.clip((fbm(size, rng, ((4, .5), (11, .5))) - .5) * 2, 0, 1) * dirt
    rgb = rgb * (1 - .55 * stain[:, :, None]) + np.array([.12, .09, .05]) * .55 * stain[:, :, None]
    return pbr(name, rgb, .6 * weave + .2 * stain, np.full((size, size), .97), normal_strength=1.5, tile=tile,
               backface=False)


def banana_skin(name="offering_banana_skin", seed=2622, w=256, h=512):
    """Small Khmer bananas left on the shrine for days: yellow going to brown,
    sugar spots and bruises, a green-brown neck and a black tip (u round, v along)."""
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, h)[:, None] * np.ones((1, w))
    yellow = np.array([.60, .45, .10])
    rgb = yellow * (.85 + .25 * fbm(max(w, h), rng)[:h, :w])[:, :, None]
    ridge = .9 + .1 * np.cos(np.linspace(0, math.tau * 5, w))[None, :]
    rgb *= ridge[:, :, None]
    spots = fbm(max(w, h), rng, ((40, .5), (90, .5)))[:h, :w]
    rgb[spots > .74] = rgb[spots > .74] * .35 + np.array([.12, .06, .02]) * .65
    bruise = np.clip((fbm(max(w, h), rng, ((4, .6), (9, .4)))[:h, :w] - .6) * 3, 0, 1)
    rgb = rgb * (1 - .7 * bruise[:, :, None]) + np.array([.10, .055, .02]) * .7 * bruise[:, :, None]
    neck = np.clip(1 - v / .12, 0, 1)
    rgb = rgb * (1 - neck[:, :, None]) + np.array([.18, .17, .06]) * neck[:, :, None]
    tip = np.clip((v - .95) / .03, 0, 1)
    rgb = rgb * (1 - tip[:, :, None]) + np.array([.03, .025, .02]) * tip[:, :, None]
    img = _write(f"T_ep1_{name}_BC", rgb)
    mat = bpy.data.materials.get(f"M_{name}") or bpy.data.materials.new(f"M_{name}")
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = .5
    mat["tile"] = 0.0
    return mat


def coconut_skin(name="offering_coconut_skin", seed=2623, w=256, h=512):
    """A young green coconut: glossy green, yellowing and scuffed brown, paler
    streaks running pole to pole, the brown calyx end (v = 1)."""
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, h)[:, None] * np.ones((1, w))
    n = fbm(max(w, h), rng, ((4, .5), (11, .3), (29, .2)))[:h, :w]
    streak = aniso_noise(max(w, h), 40, 3, rng)[:h, :w]
    rgb = np.array([.25, .34, .07]) * (.75 + .4 * n)[:, :, None]
    yel = np.clip((n - .55) * 2.5, 0, 1)
    rgb = rgb * (1 - .5 * yel[:, :, None]) + np.array([.42, .38, .1]) * .5 * yel[:, :, None]
    rgb *= (.9 + .2 * streak)[:, :, None]
    scuff = fbm(max(w, h), rng, ((30, .5), (70, .5)))[:h, :w] > .8
    rgb[scuff] = rgb[scuff] * .4 + np.array([.2, .12, .05]) * .6
    cap = np.clip((v - .9) / .06, 0, 1)
    rgb = rgb * (1 - cap[:, :, None]) + np.array([.16, .1, .05]) * cap[:, :, None]
    img = _write(f"T_ep1_{name}_BC", rgb)
    mat = bpy.data.materials.get(f"M_{name}") or bpy.data.materials.new(f"M_{name}")
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = .38
    mat["tile"] = 0.0
    return mat
