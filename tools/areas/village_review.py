"""Episode 1's farm after the user's second review of November 24, 2026 (ten game
screenshots): "very detail and very realistic ... look scary".

- The weeds, grass tufts, ferns, shrubs, nettles, bark and fallen branches the farm was
  strewn with go, everywhere inside its fence ("remove all kind of this grass and leaf
  from the whole village scene, make the ground around the house clean"); the game grows
  no tall grass on the farm any more (ActOne.ts). The trees, palms and bananas stay.
- Wells: the old brick well by the path west of the house and the kitchen house's well
  go ("keep only the well near the entrance"); the one inside the south gate is built new
  as a Khmer village well: a square laterite curb, a timber sweep (a long bamboo pole
  pivoting on a forked post, a basket of stones at its short end) with the bucket on its
  rope, a stone apron dark with spilled water, a jar and a bathing stool.
- Before the house: the crocodile flag (tong kropeu) hangs full size as wet cotton from a
  real bamboo pole, its charcoal crocodile stained by rain; the two blue banners are the
  printed Buddha banners, faded, mildewed and torn; the horn loudspeakers are rusting
  painted horns on a bamboo pole with their cable taped down it; the white porcelain jars
  are big glazed water jars (the MAHS scan) under plank lids with their dippers.
- The Neak Ta shrine and the spirit house beside it: soot and black algae run down the
  limewash, the offerings of the references (a pair of sla thor, two bowls of scented
  water, five candles and five joss sticks, a bottle of rice wine and its glass), rags of
  red, yellow and white cloth tied round the shrine's posts and the banyan's roots, a
  candle at the guardian's feet lighting his faces from below; the spirit house leans on
  its rotten post, a dead garland hanging from its eave, its offerings old.
- The rice fields: fuller hills (more tillers, the panicles heavier), three cards each,
  closer together, so a plot reads as a field of rice and not a row of sticks.
- Four more banyans like the Neak Ta's tree, standing on earth islands in the paddies.

Blender metres, X east, Y north, Z up. Called at the end of rebuild-farmstead.py.
"""
import math
import os
import re

import bpy
import numpy as np
from mathutils import Matrix, Vector

import offerings_kit as ok
import review_kit as RK
from kit import LIB, collider, image_material, library_material, mesh_object, plain
from shrine_craft import Batch, place

TEX = RK.TEX
FARM = (-44.0, 46.0, -40.0, 58.0)          # inside the outer fence (Blender x0, x1, y0, y1)
GROUND_COVER = re.compile(
    r"^(prop_)?(shrub_0[1-4]|bark_debris|dry_branches|calathea|fern_0|nettle_plant|weed_plant|grass_medium|grass_bermuda|"
    r"periwinkle|anthurium|single_root|celandine|dandelion|moss_01|leaf_litter|litter_|tpl_grass_clump\.|smau_)")
WELL = (9.5, -33.0)
BANYANS = [(-27.2, -23.5, 0.82, 0.4), (24.2, -23.0, 0.78, 2.1), (-13.2, -33.0, 0.7, 4.0), (35.5, -31.8, 0.75, 5.3)]


def materials():
    m = dict(ok.materials())
    m["bamboo"] = library_material("bamboo_wall", "M_rv_bamboo_culm", colour=(0.42, 0.35, 0.19), tile=0.5)
    m["bamboo_node"] = plain("M_rv_bamboo_node", (0.2, 0.15, 0.08), rough=0.7)
    m["coir"] = plain("M_rv_coir_rope", (0.22, 0.16, 0.09), rough=0.95)
    m["laterite"] = bpy.data.materials.get("M_neakta_laterite") or library_material("red_laterite_soil_stones", "M_rv_laterite", tile=1.0)
    m["stone"] = library_material("concrete_floor_worn_001", "M_rv_flagstone", tint=(0.42, 0.4, 0.36), tile=0.8)
    m["plaster"] = library_material("white_plaster_rough_01", "M_rv_well_plaster", tint=(0.66, 0.64, 0.58), tile=0.8)
    m["cement"] = library_material("concrete_floor_worn_001", "M_rv_well_lip", tint=(0.5, 0.48, 0.44), tile=0.6)
    m["brick"] = library_material("red_brick", "M_rv_well_brick", tint=(0.6, 0.5, 0.45), tile=0.5)
    m["moss_band"] = library_material("moss_wood", "M_rv_moss_band", tint=(0.4, 0.45, 0.35), tile=0.4)
    m["wet_ground"] = RK.soft_material("M_rv_wet_ground", wet_ground_texture(), rough=0.12)
    m["timber"] = library_material("weathered_brown_planks", "M_rv_rough_timber", tint=(0.45, 0.38, 0.32), tile=0.9)
    m["moss_wood"] = library_material("moss_wood", "M_rv_moss_wood", tint=(0.6, 0.6, 0.55), tile=0.6)
    m["dark_water"] = plain("M_rv_well_water", (0.008, 0.01, 0.009), rough=0.02)
    m["void"] = plain("M_rv_well_dark", (0.004, 0.004, 0.004), rough=1.0)
    m["horn_paint"] = library_material("rusty_metal", "M_rv_horn_paint", tint=(0.36, 0.4, 0.34), tile=0.4)
    m["rust"] = library_material("rusty_metal", "M_rv_rust", tile=0.4)
    m["cable"] = plain("M_rv_cable", (0.015, 0.015, 0.015), rough=0.5)
    m["tape"] = plain("M_rv_tape", (0.03, 0.03, 0.035), rough=0.35)
    m["lid"] = library_material("old_planks_02", "M_rv_jar_lid", tint=(0.48, 0.4, 0.34), tile=0.6)
    m["cloth_red"] = plain("M_rv_rag_red", (0.32, 0.03, 0.025), rough=0.85)
    m["cloth_yellow"] = plain("M_rv_rag_yellow", (0.55, 0.4, 0.06), rough=0.85)
    m["cloth_white"] = library_material("rough_linen", "M_rv_rag_white", tint=(0.7, 0.68, 0.6), tile=0.3)
    m["glass_bottle"] = plain("M_rv_rice_wine_bottle", (0.25, 0.32, 0.22), rough=0.08, alpha=0.45)
    m["rice_wine"] = plain("M_rv_rice_wine", (0.5, 0.42, 0.25), rough=0.05, alpha=0.6)
    m["banana_stem"] = plain("M_rv_banana_stem", (0.2, 0.24, 0.1), rough=0.55)
    m["banana_stem_cut"] = plain("M_rv_banana_stem_cut", (0.42, 0.38, 0.22), rough=0.7)
    m["scented"] = plain("M_rv_scented_water", (0.05, 0.045, 0.03), rough=0.03)
    m["streaks"] = RK.soft_material("M_rv_wall_streaks", streaks_texture(), rough=0.9)
    m["blood_pool"] = RK.soft_material("M_rv_blood_pool", RK.blood_pool(), rough=0.18)
    m["blood_runs"] = RK.soft_material("M_rv_blood_runs", RK.blood_runs(), rough=0.4)
    m["mound"] = bpy.data.materials.get("M_paddy_bund_mud") or library_material("brown_mud_03", "M_rv_mound", tile=1.2)
    return m


# ------------------------------------------------------------------ textures


def streaks_texture():
    """Black algae and soot run down a limewashed wall from its top: dense at the top,
    thinning in long uneven streaks, a green tinge in the wettest."""
    path = os.path.join(TEX, "T_ep1_wall_streaks_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(2410)
    h, w = 1024, 512
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    n = RK.noise((h, w), rng, ((4, 0.5), (30, 0.3), (120, 0.2)))
    a = np.clip((220 * (0.6 + n) - yy) / 160, 0, 1) * 0.8
    for k in range(40):
        x0 = rng.uniform(0, w)
        L = rng.uniform(150, 1000)
        wd = rng.uniform(3, 22)
        line = np.exp(-((xx - x0 - 6 * np.sin(yy / 90 + k)) / wd) ** 2) * np.clip((L - yy) / 200, 0, 1)
        a = np.maximum(a, line * rng.uniform(0.35, 0.8))
    a *= np.clip(0.55 + 0.6 * RK.noise((h, w), rng, ((60, 0.5), (200, 0.5))), 0, 1)
    green = RK.noise((h, w), rng, ((5, 1.0),))[..., None]
    col = np.array([0.06, 0.065, 0.05])[None, None] * (1 - green) + np.array([0.08, 0.11, 0.05])[None, None] * green
    col = np.broadcast_to(col, (h, w, 3))
    return RK.save_png("T_ep1_wall_streaks_BC", np.dstack([col, np.clip(a, 0, 0.92)]))


def wet_ground_texture():
    """Spilled water darkening the earth round the well: soaked near the curb, splashes
    and drying edges further out (its alpha darkens the ground under it)."""
    path = os.path.join(TEX, "T_ep1_wet_ground_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(2414)
    n = 512
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n - 0.5
    r = np.hypot(xx, yy)
    lobes = RK.noise((n, n), rng, ((4, 0.5), (12, 0.3), (40, 0.2)))
    a = np.clip((0.42 + 0.14 * (lobes - 0.5) * 2 - r) * 6, 0, 1) * 0.75
    col = np.broadcast_to(np.array([0.05, 0.035, 0.025]), (n, n, 3))
    return RK.save_png("T_ep1_wet_ground_BC", np.dstack([col, a]))


def aged(src_name, out_name, seed, tear=0.0):
    """A cloth texture after weeks of rain: tide marks and grime from the hem up, black
    mildew spots, the colours faded; `tear` cuts ragged holes and a ragged hem (alpha)."""
    path = os.path.join(TEX, f"{out_name}.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(seed)
    a = RK.load_rgba(os.path.join(TEX, f"{src_name}.png"))
    h, w = a.shape[:2]
    rgb, alpha = a[..., :3], a[..., 3]
    L = rgb.mean(axis=2, keepdims=True)
    rgb = rgb * 0.7 + L * 0.3                      # faded
    yy = np.mgrid[0:h, 0:w][0].astype(np.float32) / h
    n = RK.noise((h, w), rng, ((5, 0.5), (25, 0.3), (90, 0.2)))
    grime = np.clip((yy - 0.45 - 0.25 * n) * 2.2, 0, 1)[..., None]
    rgb = rgb * (1 - 0.55 * grime) + np.array([0.24, 0.19, 0.12]) * 0.55 * grime
    for k in range(5):                              # tide lines where it dried
        y0 = rng.uniform(0.35, 0.95)
        band = np.exp(-((yy - y0 - 0.03 * (n - 0.5)) / 0.006) ** 2)[..., None]
        rgb = rgb * (1 - 0.35 * band) + np.array([0.3, 0.22, 0.12]) * 0.35 * band
    spots = (RK.noise((h, w), rng, ((90, 0.6), (300, 0.4))) > 0.7).astype(np.float32)
    spots *= RK.noise((h, w), rng, ((4, 1.0),)) > 0.45
    rgb = rgb * (1 - 0.6 * spots[..., None]) + np.array([0.05, 0.06, 0.045]) * 0.6 * spots[..., None]
    if tear:
        holes = RK.noise((h, w), rng, ((12, 0.6), (50, 0.4))) > 1 - tear * 0.25
        alpha = alpha * (~holes)
        hem = (yy > 0.93 + 0.06 * RK.noise((h, w), rng, ((40, 1.0),))).astype(np.float32)
        alpha = alpha * (1 - hem)
    return RK.save_png(out_name, np.dstack([np.clip(rgb, 0, 1), alpha]))


# ------------------------------------------------------------------ 1. the ground


def clear_ground_cover():
    """Every weed, tuft, fern, shrub, bark scrap and fallen branch inside the farm's fence."""
    x0, x1, y0, y1 = FARM
    gone = []
    for o in bpy.data.objects:
        if not GROUND_COVER.match(o.name) or o.parent is not None:
            continue
        if any(c.name.startswith("_") or c.name == "nature_templates" for c in o.users_collection):
            continue
        p = o.matrix_world.translation
        if o.type == "MESH":
            bb = RK.box_of([o])
            p = (bb[0] + bb[1]) / 2
        if x0 <= p.x <= x1 and y0 <= p.y <= y1:
            gone.append(o)
    n = RK.delete(gone)
    print("[village] ground cover out:", n, flush=True)


# ------------------------------------------------------------------ 2. the wells


def bamboo(b, m, base, top, r0, r1, rng, node=0.38):
    """A bamboo culm from base to top: tapering, its nodes ringed and swollen."""
    base, top = Vector(base), Vector(top)
    L = (top - base).length
    d = (top - base).normalized()
    n = max(2, int(L / node))
    pts, rad = [], []
    for i in range(n + 1):
        t = i / n
        bend = Vector((0.0, 0.0, 0.0))
        pts.append(tuple(base + d * L * t + bend))
        rad.append(r0 + (r1 - r0) * t)
    b.tube(m["bamboo"], pts, rad, sides=10)
    for i in range(1, n):
        t = i / n
        p = base + d * L * t
        r = (r0 + (r1 - r0) * t) * 1.08
        b.tube(m["bamboo_node"], [tuple(p - d * 0.006), tuple(p + d * 0.006)], [r, r], sides=10)


def well(coll, m, ground, rng):
    """The well inside the south gate; the other two go. Built by village_well.py (the
    user, Nov 26, 2026: the plaster drum and smooth pole read as a cartoon)."""
    import village_well

    RK.delete(RK.roots(re.compile(r"^(well_[01]_|col_well_[01]$|ng_well_|col_ng_well$)")))
    village_well.build(coll, ground)
    print("[village] well built new; old wells out", flush=True)


# ------------------------------------------------------------------ 3. before the house


def hang(coll, mat, name, top_left, width, length, nu, nv, rng, wind=None, colliders=()):
    """A cloth hung from its top edge (a flag, a banner) left to fall limp, then given a
    little thickness. The top edge runs along +x from `top_left`."""
    o = RK.cloth_grid(name, coll, mat, Vector(top_left) - Vector((0, 0, length)), Vector((width, 0, 0)), Vector((0, 0, length)),
                      nu, nv)
    for v in o.data.vertices:
        t = 1 - (v.co.z - (top_left[2] - length)) / length
        v.co.y += 0.03 * math.sin(v.co.x * 9 + rng.uniform(0, 6)) * t + rng.normal(0, 0.002)
    pinned = [v.index for v in o.data.vertices if abs(v.co.z - top_left[2]) < 1e-4]
    RK.simulate_cloth(o, pinned, colliders=colliders, frames=60, mass=0.2, bending=0.08, wind=wind)
    RK.solidify(o, 0.002)
    return o


def funeral_front(coll, m, ground, rng):
    RK.delete(RK.roots(re.compile(r"^(crocodile_flag|flag_crossbar|flag_pole|flag_guy_|col_flag_pole|banner_(2|3|bar_2|bar_3|pole_2|pole_3)$|"
                                  r"col_banner_pole_|water_jar_[012](_lid)?$|col_water_jar_[012]$|fu_speakers_|fu_pole|fu_guy_)")))
    b = Batch("front")
    # The crocodile flag: a 7.6 m bamboo, the flag full size and limp from its crossbar.
    fx, fy = -2.4, -2.2
    fg = ground(fx, fy)
    top = Vector((fx + 0.12, fy + 0.02, fg + 7.6))
    bamboo(b, m, (fx, fy, fg - 0.5), top, 0.055, 0.022, rng)
    cross_z = fg + 7.15
    b.tube(m["bamboo"], [(fx - 0.48, fy - 0.03, cross_z), (fx + 0.62, fy + 0.01, cross_z)], [0.016, 0.013], sides=8)
    for sgn, cx_ in ((-1, fx - 0.03), (1, fx + 0.1)):
        b.tube(m["coir"], [(cx_ - 0.02, fy - 0.04, cross_z + 0.03), (cx_ + 0.02, fy + 0.04, cross_z - 0.03)], 0.006, sides=4)
    for k, a in enumerate((0.9, 2.9, 4.8)):        # coir guys to bamboo stakes
        foot = (fx + math.cos(a) * 3.2, fy + math.sin(a) * 3.2)
        gz = ground(*foot)
        p0 = Vector((fx + 0.06, fy, fg + 4.6))
        pts = [tuple(p0.lerp(Vector((foot[0], foot[1], gz + 0.25)), t) - Vector((0, 0, 0.18 * math.sin(math.pi * t)))) for t in np.linspace(0, 1, 9)]
        b.tube(m["coir"], pts, 0.005, sides=4)
        b.box(m["timber"], (0.05, 0.05, 0.45), (foot[0], foot[1], gz + 0.1), chamfer=0.006)
    collider("flag_pole", coll, fx - 0.08, fx + 0.08, fy - 0.08, fy + 0.08, fg, fg + 3.0)
    flag_mat = image_material("M_rv_crocodile_flag", aged("T_ep1_flag_crocodile_BC", "T_ep1_flag_crocodile_old_BC", 2411, tear=0.25),
                              rough=0.9, cutout=True)
    flag = hang(coll, flag_mat, "crocodile_flag", (fx - 0.42, fy + 0.02, cross_z - 0.02), 0.95, 3.8, 18, 70, rng)
    # The two printed banners either side of the way in, on bamboo with crossbars.
    for k, (bx, src) in enumerate(((-2.3, "nirvana"), (2.3, "mara"))):
        by = -2.4
        bg = ground(bx, by)
        bamboo(b, m, (bx, by, bg - 0.4), (bx + 0.03, by, bg + 4.6), 0.045, 0.024, rng)
        bz = bg + 4.3
        b.tube(m["bamboo"], [(bx - 0.36, by - 0.02, bz), (bx + 0.36, by - 0.02, bz)], 0.014, sides=8)
        mat = image_material(f"M_rv_front_banner_{src}", aged(f"T_ep1_funeral_banner_{src}_BC", f"T_ep1_front_banner_{src}_BC", 2412 + k,
                                                                tear=0.3), rough=0.85, cutout=True)
        hang(coll, mat, f"front_banner_{k}", (bx - 0.33, by - 0.04, bz - 0.02), 0.66, 2.3, 12, 40, rng)
        collider(f"banner_pole_{k}", coll, bx - 0.07, bx + 0.07, by - 0.07, by + 0.07, bg, bg + 2.5)
    # The loudspeakers: a tall bamboo with three horn speakers on a rusted pipe at its top,
    # their cable taped down it, guyed with wire.
    sx, sy = 4.2, 3.6
    sg = ground(sx, sy)
    stop = Vector((sx + 0.05, sy + 0.02, sg + 8.2))
    bamboo(b, m, (sx, sy, sg - 0.6), stop, 0.06, 0.035, rng, node=0.42)
    b.tube(m["rust"], [tuple(stop - Vector((0, 0, 1.0))), tuple(stop + Vector((0, 0, 0.55)))], 0.024, sides=10)
    for zz in (stop.z - 0.9, stop.z - 0.55, stop.z - 0.2):
        b.tube(m["rust"], [(stop.x + 0.05 * math.cos(a), stop.y + 0.05 * math.sin(a), zz + 0.003 * a) for a in np.linspace(0, math.tau, 10)],
               0.003, sides=4)
    for k, (a, tilt, h0) in enumerate(((0.25, 0.22, 0.45), (2.4, 0.18, 0.32), (4.3, 0.25, 0.4))):
        dvec = Vector((math.cos(a), math.sin(a), -tilt)).normalized()
        base = stop + Vector((0, 0, h0))
        M = Matrix.Translation(base + dvec * 0.08) @ dvec.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bell = [(0.045, 0.0), (0.05, 0.05), (0.07, 0.14), (0.11, 0.25), (0.18, 0.34), (0.245, 0.385), (0.255, 0.392),
                (0.258, 0.4), (0.246, 0.398), (0.236, 0.384), (0.17, 0.33), (0.1, 0.24), (0.06, 0.13), (0.04, 0.05), (0.036, 0.0)]
        b.lathe(m["horn_paint"], bell, xf=M, segments=36, tile=0.3, cap=False)
        b.lathe(m["rust"], [(0, -0.16), (0.06, -0.16), (0.075, -0.14), (0.078, -0.03), (0.05, -0.01), (0.045, 0.0), (0, 0.0)], xf=M,
                segments=24, tile=0.2)
        b.box(m["rust"], (0.03, 0.2, 0.03), (0, 0, -0.08), xf=M, chamfer=0.004)
        b.tube(m["rust"], [tuple(stop + Vector((0, 0, h0))), tuple(M @ Vector((0, 0, -0.1)))], 0.012, sides=6)
        b.tube(m["cable"], [tuple(M @ Vector((0, 0, -0.16))), tuple(M @ Vector((0.05, 0, -0.3))), tuple(stop + Vector((0.04, 0, h0 - 0.3)))],
               0.005, sides=5)
    b.tube(m["cable"], [(sx + 0.06, sy - 0.01, sg + 0.2), (sx + 0.065, sy, sg + 4.0), (sx + 0.06, sy + 0.01, stop.z - 0.2)], 0.007, sides=5)
    for zz in np.linspace(sg + 0.8, stop.z - 0.5, 9):
        b.tube(m["tape"], [(sx + 0.06 * math.cos(a), sy + 0.06 * math.sin(a), zz + 0.004 * a) for a in np.linspace(0, math.tau, 9)],
               0.006, sides=4)
    for k, a in enumerate((0.6, 2.7, 4.7)):
        foot = (sx + math.cos(a) * 4.6, sy + math.sin(a) * 4.6)
        gz = ground(*foot)
        p0 = stop - Vector((0, 0, 0.6))
        pts = [tuple(p0.lerp(Vector((foot[0], foot[1], gz + 0.1)), t) - Vector((0, 0, 0.22 * math.sin(math.pi * t)))) for t in np.linspace(0, 1, 9)]
        b.tube(m["cable"], pts, 0.0035, sides=4)
        b.box(m["timber"], (0.05, 0.05, 0.4), (foot[0], foot[1], gz + 0.08), chamfer=0.006)
    collider("speaker_pole", coll, sx - 0.09, sx + 0.09, sy - 0.09, sy + 0.09, sg, sg + 3.0)
    b.build(coll)
    # The water jars at the way in: glazed earthenware under plank lids, a dipper on each.
    scans = RK.Scans()
    lids = Batch("front_jar_lids")
    for k, (jx, jy) in enumerate(((-4.6, 1.4), (4.6, 1.6), (-4.7, 6.5))):
        jg = ground(jx, jy)
        jar = scans.put(coll, "water_jar", None, f"front_water_jar_{k}", Matrix.Translation((jx, jy, jg - 0.02)) @
                        Matrix.Rotation(rng.uniform(0, math.tau), 4, "Z"), size=0.78, along=2, tris=8000)
        RK.vl()
        jb = RK.box_of([jar])
        rad = (jb[1].x - jb[0].x) / 2
        for j, off in enumerate((-0.09, 0.0, 0.09)):
            lids.box(m["lid"], (0.36, 0.085, 0.022), (jx, jy + off, jb[1].z + 0.011), chamfer=0.003, jitter=0.001, rng=rng)
        lids.box(m["lid"], (0.045, 0.3, 0.022), (jx + 0.1, jy, jb[1].z + 0.033), chamfer=0.003)
        lids.lathe(m["coconut"], [(0, -0.055), (0.05, -0.05), (0.068, -0.025), (0.072, 0.0), (0.066, 0.0), (0, -0.045)],
                   xf=place(jx - 0.05, jy + 0.05, jb[1].z + 0.08), segments=20, tile=0.1)
        lids.tube(m["bamboo"], [(jx - 0.03, jy + 0.07, jb[1].z + 0.075), (jx - 0.25, jy + 0.24, jb[1].z + 0.03)], 0.008, sides=6)
        collider(f"water_jar_{k}", coll, jx - rad, jx + rad, jy - rad, jy + rad, jg, jb[1].z + 0.04)
    lids.build(coll)
    print("[village] the funeral's front: flag, banners, loudspeakers, jars", flush=True)


# ------------------------------------------------------------------ 4. the shrines


def _sla_thor(b, m, x, y, z, rng):
    """One sla thor: a cut length of banana trunk on three bamboo legs, folded leaf cones
    pinned round it, a candle and joss sticks on top (the references' Neak Ta offering)."""
    for k in range(3):
        a = k * math.tau / 3 + 0.3
        b.tube(m["bamboo"], [(x + math.cos(a) * 0.035, y + math.sin(a) * 0.035, z), (x + math.cos(a) * 0.02, y + math.sin(a) * 0.02, z + 0.1)],
               0.005, sides=5)
    b.lathe(m["banana_stem"], [(0, 0), (0.034, 0), (0.036, 0.03), (0.035, 0.12), (0, 0.12)], xf=place(x, y, z + 0.08), segments=18, tile=0.1)
    b.lathe(m["banana_stem_cut"], [(0.033, 0.12), (0.022, 0.123), (0, 0.124)], xf=place(x, y, z + 0.08), segments=18, tile=0.05)
    for k in range(6):
        a = k * math.tau / 6
        base = Vector((x + math.cos(a) * 0.047, y + math.sin(a) * 0.047, z + 0.12 + 0.03 * (k % 2)))
        tipv = base + Vector((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.06))
        side = Vector((-math.sin(a), math.cos(a), 0)) * 0.018
        b.add(m["leaf_dry"], [tuple(base - side), tuple(base + side), tuple(tipv)], [(0, 1, 2)], [(0, 0), (1, 0), (0.5, 1)])
    return ok.candle(b, m, place(x, y, z + 0.215), rng, height=0.06, radius=0.008, melt=0.7)


def shrines(coll, m, ground, rng):
    """The Neak Ta shrine and its spirit house: aged, the references' offerings, scary."""
    sh = bpy.data.collections.get("neakta_shrine") or coll
    flames, smoke = [], []
    lime = bpy.data.objects.get("neakta_shrine_neakta_limewash")
    if lime is not None:
        lb = RK.box_of([lime])
        x0, x1, y0, y1, z0, z1 = lb[0].x, lb[1].x, lb[0].y, lb[1].y, lb[0].z, lb[1].z
        # Black streaks down the outer walls (south, north, back), pressed onto them.
        k = 0
        for (ax, ay, bx, by, inward) in ((x0, y0, x1, y0, Vector((0, 1, 0))), (x1, y1, x0, y1, Vector((0, -1, 0))),
                                         (x0, y1, x0, y0, Vector((1, 0, 0)))):
            n = 3
            for j in range(n):
                t0, t1 = j / n, (j + 1) / n
                p0 = Vector((ax + (bx - ax) * t0, ay + (by - ay) * t0, 0)) - inward * 0.3
                p1 = Vector((ax + (bx - ax) * t1, ay + (by - ay) * t1, 0)) - inward * 0.3
                d = RK.decal(sh, f"neakta_streaks_{k}", m["streaks"], [(p0.x, p0.y, z0 + 0.05), (p1.x, p1.y, z0 + 0.05),
                                                                         (p1.x, p1.y, z1 - 0.03), (p0.x, p0.y, z1 - 0.03)], n=6)
                RK.press(d, lime, inward, 0.004)
                k += 1
    # Soot from a hundred years of candles up the wall behind him.
    statue0 = bpy.data.objects.get("neakta_stone_watch")
    if lime is not None and statue0 is not None:
        sb0 = RK.box_of([statue0])
        scy = (sb0[0].y + sb0[1].y) / 2
        d = RK.decal(sh, "neakta_soot", m["streaks"], [(x0 + 0.6, scy - 0.55, z0 + 0.15), (x0 + 0.6, scy + 0.55, z0 + 0.15),
                                                        (x0 + 0.6, scy + 0.55, z1), (x0 + 0.6, scy - 0.55, z1)],
                     uv=((0, 1), (1, 1), (1, 0), (0, 0)), n=6)
        RK.press(d, lime, Vector((-1, 0, 0)), 0.004)
    # Offerings on the platform's lip before him: a pair of sla thor, two bowls of scented
    # water, five candles and five joss sticks, rice wine.
    marker = bpy.data.objects.get("marker_neakta")
    statue = bpy.data.objects.get("neakta_stone_watch")
    b = Batch("neakta_review")
    if statue is not None:
        sb = RK.box_of([statue])
        sx, sy = (sb[0].x + sb[1].x) / 2, (sb[0].y + sb[1].y) / 2
        lip_x = sx + 0.95
        lz = RK.ray_down(lip_x, sy, 1.5) or 0.35
        for k, dy in enumerate((-0.42, 0.42)):
            zz = RK.ray_down(lip_x, sy + dy, 1.5) or lz
            flames.append(_sla_thor(b, m, lip_x, sy + dy, zz, rng))
            bx = lip_x + 0.02
            by = sy + dy * 0.62
            bz = RK.ray_down(bx, by, 1.5) or lz
            b.lathe(m["brass"], [(0, 0), (0.03, 0), (0.05, 0.02), (0.055, 0.04), (0.05, 0.042), (0, 0.03)], xf=place(bx, by, bz), segments=24, tile=0.1)
            b.lathe(m["scented"], [(0.048, 0.034), (0, 0.034)], xf=place(bx, by, bz), segments=20, tile=0.1, cap=False)
            for p in range(4):
                a = rng.uniform(0, math.tau)
                ok.marigold(b, m, (bx + math.cos(a) * 0.02, by + math.sin(a) * 0.02, bz + 0.036), rng, radius=0.009, dead=p % 2 == 0)
        for k in range(5):
            cy_ = sy - 0.18 + k * 0.09
            cz = RK.ray_down(lip_x + 0.1, cy_, 1.5) or lz
            ok.candle_dish(b, m, place(lip_x + 0.1, cy_, cz), rng, radius=0.025, melt=0.8)
            tip = ok.candle(b, m, place(lip_x + 0.1, cy_, cz + 0.004), rng, height=rng.uniform(0.03, 0.08), radius=0.008, melt=0.9,
                            lit=k in (0, 3))
            if k in (0, 3):
                flames.append(tip)
        iz = RK.ray_down(lip_x - 0.1, sy, 1.5) or lz
        ok.incense_bowl(b, m, place(lip_x - 0.1, sy, iz), rng, radius=0.06, height=0.05, sticks=5, lit=5)
        smoke.append(Vector((lip_x - 0.1, sy, iz + 0.28)))
        wz = RK.ray_down(lip_x - 0.05, sy + 0.26, 1.5) or lz
        b.lathe(m["glass_bottle"], [(0, 0), (0.03, 0), (0.032, 0.005), (0.032, 0.17), (0.026, 0.2), (0.012, 0.23), (0.011, 0.27),
                                    (0, 0.27)], xf=place(lip_x - 0.05, sy + 0.26, wz), segments=18, tile=0.1)
        b.lathe(m["rice_wine"], [(0, 0.004), (0.029, 0.004), (0.029, 0.11), (0, 0.11)], xf=place(lip_x - 0.05, sy + 0.26, wz), segments=16, tile=0.1)
        ok.small_cup(b, m, place(lip_x + 0.03, sy + 0.32, wz), rng, radius=0.022, height=0.03, liquid="water")
        # A candle at the guardian's feet, his faces lit from below.
        fz = RK.ray_down(sx + 0.3, sy, sb[1].z) or lz
        ok.candle_dish(b, m, place(sx + 0.3, sy, fz), rng, radius=0.03, melt=0.9)
        flames.append(ok.candle(b, m, place(sx + 0.3, sy, fz + 0.004), rng, height=0.045, radius=0.009, melt=0.95))
    # Rags of red, yellow and white tied round the shrine's two front pillars: each band
    # hugs the pillar's own cross-section, its end hanging down the pillar's front face.
    pillars = [bpy.data.objects.get("neakta_shrine_neakta_limewash"), bpy.data.objects.get("neakta_shrine_neakta_brick")]
    if lime is not None:
        for near_y0 in (True, False):
            sec = RK.section(pillars, 1.0, 1.2, lambda p: p.x > x1 - 0.32 and ((p.y < y0 + 0.4) if near_y0 else (p.y > y1 - 0.4)))
            if sec is None or (sec[1] - sec[0]) > 0.5 or (sec[3] - sec[2]) > 0.5:
                continue
            for j, key in enumerate(("cloth_red", "cloth_yellow", "cloth_white")):
                RK.wrap(b, m[key], sec, 1.04 + 0.045 * j, rng, width=0.03, tail=0.3 + 0.12 * j, side=(1, 0))
    b.build(sh)
    spirit_house(sh, m, ground, rng)
    RK.flames_and_lights(sh, flames, "neakta_flame", "neakta_review", watts=0.45)
    for k, p in enumerate(smoke):
        RK.marker(sh, f"marker_incense_smoke_neakta_{k}", p)
    print("[village] shrines aged and offered to:", len(flames), "flames", flush=True)


# ------------------------------------------------------------------ 4b. the spirit house


def yantra_texture():
    """A cloth talisman (yantra) pinned to the spirit house's post: yellowed cotton, a
    double border, a ring of rays about a circle, a grid of cells with dots, the spiral and
    stroke of an unalome at the top, all in rust-red ink gone brown; water-stained. No
    lettering (Khmer script on props needs the cultural guide's review)."""
    path = os.path.join(TEX, "T_ep1_yantra_cloth_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(2415)
    h, w = 320, 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ink = np.zeros((h, w), np.float32)

    def line(x0, y0, x1, y1, r=1.6):
        px, py, dx, dy = xx - x0, yy - y0, x1 - x0, y1 - y0
        t = np.clip((px * dx + py * dy) / max(1e-3, dx * dx + dy * dy), 0, 1)
        d = np.hypot(px - t * dx, py - t * dy)
        np.maximum(ink, np.clip(r + 0.8 - d, 0, 1), out=ink)

    def ring(cx, cy, rad, r=1.6):
        d = np.abs(np.hypot(xx - cx, yy - cy) - rad)
        np.maximum(ink, np.clip(r + 0.8 - d, 0, 1), out=ink)

    for inset in (10, 17):
        line(inset, inset, w - inset, inset)
        line(w - inset, inset, w - inset, h - inset)
        line(w - inset, h - inset, inset, h - inset)
        line(inset, h - inset, inset, inset)
    cx, cy = w / 2, h * 0.58
    ring(cx, cy, 46)
    ring(cx, cy, 30)
    for k in range(12):
        a = k * math.tau / 12
        line(cx + math.cos(a) * 30, cy + math.sin(a) * 30, cx + math.cos(a) * 46, cy + math.sin(a) * 46)
    for i in range(3):
        for j in range(3):
            x0, y0 = cx - 21 + 14 * i, cy - 21 + 14 * j
            line(x0, y0, x0 + 14, y0, 1.1)
            line(x0, y0, x0, y0 + 14, 1.1)
            ring(x0 + 7, y0 + 7, 1.5, 1.4)
    line(cx - 21, cy + 21, cx + 21, cy + 21, 1.1)
    line(cx + 21, cy - 21, cx + 21, cy + 21, 1.1)
    pts = [(cx + (14 - 1.2 * t) * math.cos(t * 1.1), 62 + (14 - 1.2 * t) * math.sin(t * 1.1)) for t in np.linspace(0, 11, 120)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        line(ax, ay, bx, by, 1.4)
    for k in range(10):
        line(cx + 6 * math.sin(k), 76 + 6 * k, cx + 6 * math.sin(k + 1), 82 + 6 * k, 1.4)
    line(cx, 140, cx, 36, 1.0)
    ink *= np.clip(0.7 + 0.5 * RK.noise((h, w), rng, ((10, 0.6), (40, 0.4))), 0, 1)
    cloth = np.array([0.74, 0.64, 0.42]) * (0.85 + 0.25 * RK.noise((h, w), rng, ((6, 0.5), (60, 0.5))))[..., None]
    stain = np.clip((yy / h - 0.55 - 0.2 * RK.noise((h, w), rng, ((5, 1.0),))) * 2.5, 0, 1)[..., None]
    cloth = cloth * (1 - 0.45 * stain) + np.array([0.3, 0.22, 0.12]) * 0.45 * stain
    col = cloth * (1 - ink[..., None]) + np.array([0.36, 0.08, 0.05]) * ink[..., None]
    return RK.save_png("T_ep1_yantra_cloth_BC", np.dstack([np.clip(col, 0, 1), np.ones((h, w))]))


def doll_cloth_texture():
    """The effigy's cloth: coarse unbleached cotton gone grey-brown, a visible weave, mud
    up from its hem, old blood soaked in at the chest and run down, black mildew."""
    path = os.path.join(TEX, "T_ep1_doll_cloth_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(2416)
    n = 512
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    weave = 0.5 + 0.25 * np.sin(xx * 1.9) * np.sin(yy * 1.9) + 0.25 * RK.noise((n, n), rng, ((128, 1.0),))
    base = np.array([0.5, 0.45, 0.36])[None, None] * (0.8 + 0.25 * weave[..., None]) * \
        (0.85 + 0.3 * RK.noise((n, n), rng, ((5, 0.6), (30, 0.4))))[..., None]
    v = yy / n                                   # 0 at the image top: the cloth's neck (uv v = 1)
    mud = np.clip((v - 0.55 - 0.15 * RK.noise((n, n), rng, ((6, 1.0),))) * 2.6, 0, 1)[..., None]
    col = base * (1 - 0.55 * mud) + np.array([0.2, 0.15, 0.09]) * 0.55 * mud
    blood = np.zeros((n, n), np.float32)
    for k in range(5):
        cx, cy, r = rng.uniform(120, 400), rng.uniform(80, 220), rng.uniform(25, 60)
        blood = np.maximum(blood, np.clip(1 - np.hypot(xx - cx, (yy - cy) * 1.3) / r, 0, 1) ** 0.6)
        for j in range(4):
            x0 = cx + rng.uniform(-r, r)
            L = rng.uniform(60, 260)
            blood = np.maximum(blood, np.exp(-((xx - x0 - 3 * np.sin(yy / 30)) / rng.uniform(2, 5)) ** 2) * ((yy > cy) & (yy < cy + L)) * 0.85)
    blood *= np.clip(0.6 + 0.6 * RK.noise((n, n), rng, ((20, 0.6), (80, 0.4))), 0, 1)
    edge = np.clip(blood - RK.blur(blood, 5), 0, 1) * 1.5
    bc = np.array([0.2, 0.025, 0.02]) * (1 - edge[..., None]) + np.array([0.12, 0.05, 0.03]) * edge[..., None]
    col = col * (1 - 0.92 * blood[..., None]) + bc * 0.92 * blood[..., None]
    spots = (RK.noise((n, n), rng, ((70, 0.6), (200, 0.4))) > 0.72) * (RK.noise((n, n), rng, ((4, 1.0),)) > 0.4)
    col = col * (1 - 0.65 * spots[..., None]) + np.array([0.04, 0.045, 0.035]) * 0.65 * spots[..., None]
    return RK.save_png("T_ep1_doll_cloth_BC", np.dstack([np.clip(col, 0, 1), np.ones((n, n))]))


def doll_face_texture():
    """Its face, drawn on the rag head: two eyes smudged in charcoal with dark runs under
    them, the mouth sewn shut with red thread in crosses."""
    path = os.path.join(TEX, "T_ep1_doll_face_BC.png")
    if os.path.exists(path):
        return path
    rng = np.random.default_rng(2417)
    n = 256
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    ink = np.zeros((n, n), np.float32)
    for ex in (0.34, 0.66):
        cx, cy = ex * n + rng.normal(0, 3), 0.42 * n + rng.normal(0, 3)
        eye = np.clip(1.15 - np.hypot((xx - cx) / 19, (yy - cy) / 15), 0, 1) ** 0.5
        ink = np.maximum(ink, eye)
        for j in range(3):
            x0 = cx + rng.uniform(-10, 10)
            ink = np.maximum(ink, np.exp(-((xx - x0) / rng.uniform(1.5, 3.0)) ** 2) * ((yy > cy) & (yy < cy + rng.uniform(25, 70))) * 0.75)
    ink *= np.clip(0.55 + 0.6 * RK.noise((n, n), rng, ((12, 0.5), (50, 0.5))), 0, 1)
    col = np.zeros((n, n, 3), np.float32) + np.array([0.03, 0.025, 0.022])
    thread = np.zeros((n, n), np.float32)
    my = 0.72 * n
    for k in range(6):
        x = 0.3 * n + k * 0.08 * n
        for sgn in (-1, 1):
            d = np.abs((yy - my) - sgn * (xx - x)) / 1.414
            seg = (np.abs(xx - x) < 9) & (np.abs(yy - my) < 9)
            thread = np.maximum(thread, np.clip(2.2 - d, 0, 1) * seg)
    seam = np.exp(-((yy - my) / 2.0) ** 2) * ((xx > 0.27 * n) & (xx < 0.73 * n)) * 0.8
    col = col * (1 - thread[..., None]) + np.array([0.4, 0.04, 0.03]) * thread[..., None]
    alpha = np.clip(np.maximum(np.maximum(ink * 0.95, thread), seam * 0.7), 0, 1)
    col = np.where(seam[..., None] > thread[..., None], col * 0.5 + np.array([0.06, 0.02, 0.015]) * 0.5, col)
    return RK.save_png("T_ep1_doll_face_BC", np.dstack([np.clip(col, 0, 1), alpha]))


def rag_doll(coll, name, mt, m, D, rng):
    """A rag effigy hung by its neck: a lumpy rag head bound with twine and a face drawn on
    it, a sack body of coarse cloth in folds with a torn hem, twisted rag arms bound at the
    wrists, red thread wound round it and a rusty nail driven through its chest. `D` is its
    neck (local z up, its face toward -y)."""
    ph = rng.uniform(0, 6, 6)
    verts, faces, corner_uv = [], [], []
    nu, nv = 20, 16
    uv = []
    for j in range(nv + 1):
        t = j / nv
        r = 0.011 + 0.034 * min(1.0, t * 1.5) ** 0.75 + 0.006 * t
        for i in range(nu + 1):
            a = math.tau * i / nu
            fold = 1 + 0.2 * t * math.sin(5 * a + ph[0] + t * 2.5) + 0.08 * t * math.sin(13 * a + ph[1])
            z = -0.145 * t
            if j == nv:
                z -= 0.022 * abs(math.sin(3.3 * a + ph[2])) + 0.01 * rng.random()
            verts.append(tuple(D @ Vector((r * fold * math.cos(a), r * fold * math.sin(a), z))))
            uv.append((i / nu, 1 - t))
    for j in range(nv):
        for i in range(nu):
            q = j * (nu + 1) + i
            f = (q, q + nu + 1, q + nu + 2, q + 1)
            faces.append(f)
            corner_uv += [uv[k] for k in f]
    mesh_object(f"{name}_body", coll, verts, faces, mt["doll"], uvs=corner_uv, smooth=True)
    # The head: a rag ball, lumpy, a little squashed, bound across with twine.
    verts, faces, corner_uv, uv = [], [], [], []
    nh, nr = 16, 12
    hc = Vector((0, 0, 0.026))
    for j in range(nr + 1):
        th = math.pi * j / nr
        for i in range(nh + 1):
            a = math.tau * i / nh
            r = 0.024 * (1 + 0.12 * math.sin(3 * a + ph[3]) * math.sin(th) + 0.08 * math.sin(2 * th + ph[4]))
            p = hc + Vector((r * math.sin(th) * math.cos(a), r * math.sin(th) * math.sin(a) * 0.9, r * math.cos(th) * 1.05))
            verts.append(tuple(D @ p))
            uv.append((i / nh * 0.5, 1 - j / nr * 0.4))
    for j in range(nr):
        for i in range(nh):
            q = j * (nh + 1) + i
            f = (q, q + nh + 1, q + nh + 2, q + 1)
            faces.append(f)
            corner_uv += [uv[k] for k in f]
    mesh_object(f"{name}_head", coll, verts, faces, mt["doll"], uvs=corner_uv, smooth=True)
    face = RK.decal(coll, f"{name}_face", mt["doll_face"], [tuple(D @ Vector(p)) for p in ((-0.02, -0.0215, 0.008), (0.02, -0.0215, 0.008),
                                                                                         (0.02, -0.0215, 0.046), (-0.02, -0.0215, 0.046))], n=4)
    head = bpy.data.objects[f"{name}_head"]
    RK.press(face, head, (D.to_3x3() @ Vector((0, 1, 0))).normalized(), 0.0012)
    b = Batch(name)
    # Twine at the neck (many turns) and once over the crown; the arms, twisted rags bound
    # at their wrists; red thread wound round the body; a nail through the chest.
    b.tube(mt["twine"], [tuple(D @ Vector((0.0105 * math.cos(a), 0.0105 * math.sin(a), 0.001 * a / math.tau))) for a in np.linspace(0, math.tau * 5, 60)],
           0.0012, sides=4)
    b.tube(mt["twine"], [tuple(D @ (hc + Vector((0.0245 * math.cos(a), 0, 0.025 * math.sin(a))))) for a in np.linspace(-0.2, math.pi + 0.2, 16)], 0.0011, sides=4)
    for sgn in (-1, 1):
        pts = [Vector((sgn * 0.012, 0.0, -0.014)), Vector((sgn * 0.034, 0.004, -0.04)), Vector((sgn * 0.042, 0.008, -0.07)), Vector((sgn * 0.04, 0.006, -0.09))]
        b.tube(mt["doll"], [tuple(D @ p) for p in pts], [0.0085, 0.007, 0.006, 0.0065], sides=7, cap_end=True)
        w = pts[2] + (pts[3] - pts[2]) * 0.4
        b.tube(mt["twine"], [tuple(D @ (w + Vector((0.0068 * math.cos(a), 0.0068 * math.sin(a), 0.0008 * a)))) for a in np.linspace(0, math.tau * 3, 30)],
               0.001, sides=4)
    b.tube(m["cloth_red"], [tuple(D @ Vector((0.032 * math.cos(a) * (1 + 0.1 * math.sin(5 * a)), 0.032 * math.sin(a), -0.045 - 0.006 * a)))
                            for a in np.linspace(0, math.tau * 3.5, 70)], 0.0011, sides=4)
    b.tube(m["rust"], [tuple(D @ Vector((0.003, -0.045, -0.04))), tuple(D @ Vector((0.0, 0.01, -0.043)))], 0.0022, sides=6)
    b.lathe(m["rust"], [(0, 0), (0.0055, 0), (0.0055, 0.002), (0, 0.003)],
            xf=D @ Matrix.Translation((0.003, -0.045, -0.04)) @ Matrix.Rotation(math.pi / 2, 4, "X"), segments=8, tile=0.05)
    b.build(coll)


def spirit_house(coll, m, ground, rng):
    """The small spirit house by the Neak Ta's shrine, built new (the user, Nov 24, 2026:
    "more very detail and very realistic, scary and horrible"). An old teak house on one
    post, gone grey and green: a two-tier gable roof of split shingles, some fallen, naga
    bargeboards with chofa horns, a red gable with tarnished gilt rays; inside, black with
    soot, the clay Ta and Yey figurines, a third with its head broken off on the floor, a
    faded photograph of a woman, a candle burnt nearly out. On the porch: incense stubs
    overflowing the pot, a cup tipped over, black bananas, a chicken's black feathers and
    its blood, dried, run over the edge and down the post. Rusty nails driven into the post,
    red thread wound round it, cloth talismans pinned under the nails, the house bound to
    its platform with white thread (sai sin); cobwebs under the eaves; flies."""
    old = bpy.data.objects.get("spirit_house")
    cb = RK.box_of([bpy.data.objects["col_spirit_house"]]) if bpy.data.objects.get("col_spirit_house") else None
    fx, fy = ((cb[0].x + cb[1].x) / 2, (cb[0].y + cb[1].y) / 2) if cb else (-4.02, -36.45)
    RK.delete([o for o in (old, bpy.data.objects.get("col_spirit_house")) if o] + RK.roots(re.compile(r"^(spirit_house_|spirit_review)")))
    g = ground(fx, fy)
    face = math.pi / 2                     # its front (local -y) toward the east, the way the track runs
    M = Matrix.Translation((fx, fy, g)) @ Matrix.Rotation(face, 4, "Z") @ Matrix.Rotation(0.035, 4, "X") @ Matrix.Rotation(-0.025, 4, "Y")
    R = M.to_3x3()

    def P(u, v, z):
        return tuple(M @ Vector((u, v, z)))

    mt = {
        "post": library_material("old_planks_02", "M_sp_post", tint=(0.42, 0.4, 0.36), tile=0.45),
        "wood": library_material("weathered_planks", "M_sp_boards", tint=(0.5, 0.46, 0.41), tile=0.35),
        "shingle": library_material("moss_wood", "M_sp_shingle", tint=(0.42, 0.43, 0.38), tile=0.25),
        "shingle2": library_material("weathered_brown_planks", "M_sp_shingle_dark", tint=(0.3, 0.27, 0.23), tile=0.25),
        "red": library_material("wood_shutter", "M_sp_red_paint", tint=(0.17, 0.05, 0.035), tile=0.3),
        "moss": plain("M_sp_moss", (0.06, 0.075, 0.03), rough=1.0),
        "doll": image_material("M_sp_doll_cloth", doll_cloth_texture(), rough=0.95),
        "doll_face": RK.soft_material("M_sp_doll_face", doll_face_texture(), rough=0.9),
        "twine": plain("M_sp_twine", (0.24, 0.18, 0.1), rough=0.95),
        "clay_dark": library_material("clay_plaster", "M_sp_sooty_clay", tint=(0.22, 0.16, 0.12), tile=0.12),
        "cup": plain("M_sp_old_porcelain", (0.48, 0.47, 0.42), rough=0.35),
        "gilt": library_material("rusty_metal", "M_sp_gilt_old", tint=(0.38, 0.29, 0.13), tile=0.2),
        "soot": library_material("weathered_planks", "M_sp_soot", tint=(0.05, 0.043, 0.038), tile=0.3),
        "clay": plain("M_sp_figure_clay", (0.36, 0.3, 0.24), rough=0.9),
        "robe": plain("M_sp_figure_white", (0.52, 0.5, 0.45), rough=0.85),
        "face": plain("M_sp_figure_face", (0.2, 0.15, 0.11), rough=0.8),
        "rot": plain("M_sp_rotten_banana", (0.04, 0.03, 0.018), rough=0.55),
        "feather": plain("M_sp_feather", (0.018, 0.017, 0.016), rough=0.45),
        "thread": plain("M_sp_white_thread", (0.42, 0.4, 0.35), rough=0.9),
        "talisman": image_material("M_sp_talisman", yantra_texture(), rough=0.9),
        "photo": image_material("M_sp_photo", os.path.join(TEX, "T_ep1_family_prints_BC.png"), rough=0.6),
    }
    b = Batch("spirit_house")
    zp = 1.32                              # the platform's top
    # The post, its foot in a mound of earth with old brick round it.
    b.box(mt["post"], (0.13, 0.13, 1.65), (0, 0, zp - 0.04 - 0.8), xf=M, chamfer=0.012, jitter=0.002, rng=rng)
    b.lathe(m["mound"], [(0, 0.1), (0.2, 0.08), (0.36, 0.0), (0.4, -0.06), (0, -0.06)], xf=M @ place(0, 0, 0), segments=24, tile=0.6,
            radial=lambda a, hh: 1 + 0.1 * math.sin(3 * a))
    for k in range(7):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.25, 0.42)
        b.box(m["brick"], (rng.uniform(0.06, 0.12), rng.uniform(0.05, 0.08), 0.04), (math.cos(a) * r, math.sin(a) * r, 0.02),
              xf=M @ Matrix.Rotation(rng.uniform(0, 3), 4, "Z"), chamfer=0.008, jitter=0.004, rng=rng)
    # Under the platform: a cap block, two bearers, braces down to the post.
    b.box(mt["post"], (0.2, 0.2, 0.05), (0, 0, zp - 0.06), xf=M, chamfer=0.006)
    for sv in (-0.2, 0.2):
        b.box(mt["wood"], (0.7, 0.05, 0.05), (0, sv, zp - 0.06), xf=M, chamfer=0.005)
    for (du, dv) in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        b.tube(mt["post"], [P(du * 0.065, dv * 0.065, zp - 0.36), P(du * 0.3, dv * 0.27, zp - 0.08)], 0.018, sides=4)
    # The platform: planks with gaps, a fascia round its edge.
    for k in range(7):
        u = -0.37 + 0.74 * (k + 0.5) / 7
        b.box(mt["wood"], (0.74 / 7 - 0.005, 0.66, 0.03), (u, 0, zp - 0.015), xf=M, chamfer=0.003, jitter=0.0015, rng=rng)
    for sv in (-0.335, 0.335):
        b.box(mt["post"], (0.76, 0.015, 0.06), (0, sv, zp - 0.04), xf=M, chamfer=0.002, jitter=0.001, rng=rng)
    for su in (-0.385, 0.385):
        b.box(mt["post"], (0.015, 0.68, 0.06), (su, 0, zp - 0.04), xf=M, chamfer=0.002, jitter=0.001, rng=rng)
    # A low railing round the sides and back, two balusters gone, one hanging loose.
    rail = []
    for side, (a0, a1, fixed, along) in enumerate(((-0.33, 0.33, -0.36, "v"), (-0.33, 0.33, 0.36, "v"), (-0.36, 0.36, 0.31, "u"))):
        n = 9
        for k in range(n):
            t = a0 + (a1 - a0) * k / (n - 1)
            u, v = (fixed, t) if along == "v" else (t, fixed)
            if rng.random() < 0.1:
                continue
            tilt = place(u, v, zp) @ (Matrix.Rotation(0.5, 4, "X") if rng.random() < 0.05 else Matrix.Identity(4))
            b.lathe(mt["wood"], [(0, 0), (0.009, 0), (0.009, 0.01), (0.006, 0.025), (0.009, 0.045), (0.006, 0.065), (0.007, 0.075), (0, 0.075)],
                    xf=M @ tilt, segments=8, tile=0.1)
        p0 = (fixed, a0, zp + 0.078) if along == "v" else (a0, fixed, zp + 0.078)
        p1 = (fixed, a1, zp + 0.078) if along == "v" else (a1, fixed, zp + 0.078)
        b.box(mt["wood"], (abs(p1[0] - p0[0]) + 0.012, abs(p1[1] - p0[1]) + 0.012, 0.012),
              ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, zp + 0.08), xf=M, chamfer=0.002)
    # The house: floor, plank walls with gaps, side windows barred, an open front.
    zb = zp + 0.03
    zt = zb + 0.4
    v0, v1, hw = -0.08, 0.3, 0.25
    b.box(mt["wood"], (2 * hw + 0.04, v1 - v0 + 0.04, 0.03), (0, (v0 + v1) / 2, zp + 0.015), xf=M, chamfer=0.004)
    u = -hw
    while u < hw - 0.01:
        wd = rng.uniform(0.04, 0.05)
        short = rng.uniform(0, 0.03) if rng.random() < 0.25 else 0.0
        b.box(mt["wood"], (wd - 0.0015, 0.015, 0.4 - short), (u + wd / 2, v1, zb + 0.2 + short / 2), xf=M, chamfer=0.002, jitter=0.001, rng=rng)
        u += wd
    for su in (-1, 1):
        v = v0
        while v < v1 - 0.01:
            wd = rng.uniform(0.04, 0.05)
            vc = v + wd / 2
            if 0.04 < vc < 0.18:
                b.box(mt["wood"], (0.015, wd - 0.0015, 0.15), (su * hw, vc, zb + 0.075), xf=M, chamfer=0.002)
                b.box(mt["wood"], (0.015, wd - 0.0015, 0.09), (su * hw, vc, zt - 0.045), xf=M, chamfer=0.002)
            else:
                b.box(mt["wood"], (0.015, wd - 0.0015, 0.4), (su * hw, vc, zb + 0.2), xf=M, chamfer=0.002, jitter=0.001, rng=rng)
            v += wd
        for k in range(3):
            b.tube(mt["post"], [P(su * hw, 0.06 + 0.04 * k, zb + 0.15), P(su * hw, 0.06 + 0.04 * k, zt - 0.09)], 0.004, sides=5)
        b.box(mt["post"], (0.035, 0.035, 0.42), (su * hw, v0, zb + 0.21), xf=M, chamfer=0.004)
        b.box(mt["post"], (0.035, 0.035, 0.42), (su * hw, v1, zb + 0.21), xf=M, chamfer=0.004)
        b.box(mt["red"], (0.12, 0.014, 0.4), (su * (hw - 0.06), v0, zb + 0.2), xf=M, chamfer=0.002)
    b.box(mt["red"], (2 * hw, 0.016, 0.1), (0, v0, zt - 0.05), xf=M, chamfer=0.003)
    for su in (-1, 1):
        b.box(mt["post"], (0.014, 0.022, 0.31), (su * 0.127, v0 - 0.005, zb + 0.155), xf=M, chamfer=0.002)
    b.box(mt["post"], (0.27, 0.022, 0.016), (0, v0 - 0.005, zb + 0.305), xf=M, chamfer=0.002)
    # Soot over the whole inside: back, sides, the ceiling and the floor.
    b.box(mt["soot"], (2 * hw - 0.03, 0.004, 0.38), (0, v1 - 0.01, zb + 0.2), xf=M)
    for su in (-1, 1):
        b.box(mt["soot"], (0.004, v1 - v0 - 0.02, 0.38), (su * (hw - 0.01), (v0 + v1) / 2, zb + 0.2), xf=M)
    b.box(mt["soot"], (2 * hw - 0.02, v1 - v0 - 0.02, 0.006), (0, (v0 + v1) / 2, zt - 0.004), xf=M)
    b.box(mt["soot"], (2 * hw - 0.02, v1 - v0 - 0.02, 0.003), (0, (v0 + v1) / 2, zb + 0.0015), xf=M)
    # The roof: a main gable front to back on battens, split shingles in courses (one in
    # twelve fallen), a lower porch roof in front; ridge board; naga bargeboards, chofa.
    def roof(vf, vb, e_u, e_z, r_z, name_rows=7, missing=0.08):
        slope = math.hypot(e_u, r_z - e_z)
        for su in (-1, 1):
            for row in range(name_rows):
                t0 = row / name_rows
                for vv in np.arange(vf, vb, 0.056):
                    if rng.random() < missing:
                        continue
                    t = t0 + 0.5 / name_rows
                    uu = su * e_u * (1 - t)
                    zz = e_z + (r_z - e_z) * t
                    ang = math.atan2(r_z - e_z, e_u)
                    xf = M @ Matrix.Translation((uu, vv + 0.028 + rng.normal(0, 0.003), zz + 0.006)) @ Matrix.Rotation(su * ang, 4, "Y") @ \
                        Matrix.Rotation(rng.normal(0, 0.05), 4, "Z") @ Matrix.Rotation(su * rng.uniform(0.0, 0.08), 4, "Y")
                    b.box(mt["shingle"] if rng.random() < 0.6 else mt["shingle2"], (slope / name_rows * 1.35, 0.052, 0.007), (0, 0, 0), xf=xf,
                          chamfer=0.0015, jitter=0.0008, rng=rng)
            for k in range(4):
                t = (k + 0.5) / 4
                b.box(mt["post"], (0.02, vb - vf, 0.015), (su * e_u * (1 - t), (vf + vb) / 2, e_z + (r_z - e_z) * t - 0.012), xf=M)
        b.box(mt["shingle2"], (0.05, vb - vf + 0.02, 0.02), (0, (vf + vb) / 2, r_z + 0.012), xf=M, chamfer=0.004)
        # Naga bargeboards on the front gable: up from a curled hook at each eave to the apex,
        # where the chofa horn rises and turns back.
        for su in (-1, 1):
            pts = [P(su * (e_u + 0.05), vf - 0.01, e_z + 0.07), P(su * (e_u + 0.03), vf - 0.01, e_z + 0.01), P(su * e_u, vf - 0.01, e_z - 0.005)]
            pts += [P(su * e_u * (1 - t), vf - 0.01, e_z + (r_z - e_z) * t) for t in np.linspace(0.12, 1.0, 7)]
            b.tube(mt["gilt"], pts, [0.006, 0.01, 0.013] + [0.013] * 7, sides=6)
        b.tube(mt["gilt"], [P(0, vf - 0.01, r_z), P(0, vf - 0.02, r_z + 0.07), P(0, vf + 0.01, r_z + 0.13), P(0, vf + 0.05, r_z + 0.15)],
               [0.014, 0.011, 0.007, 0.003], sides=6)
    roof(-0.13, v1 + 0.14, hw + 0.11, zt + 0.005, zt + 0.3, 7)
    roof(-0.36, -0.1, hw + 0.06, zt - 0.075, zt + 0.17, 4, missing=0.12)
    for su in (-1, 1):
        b.box(mt["post"], (0.03, 0.03, zt - 0.075 - zp), (su * (hw + 0.02), -0.3, (zt - 0.075 + zp) / 2), xf=M, chamfer=0.003)
    # Moss grown in clumps on the shingles, thickest low on the slopes; two shingles slipped
    # and caught on the eave, hanging.
    ang = math.atan2(0.3 - 0.005, hw + 0.11)
    for k in range(26):
        su = 1 if k % 2 else -1
        t = rng.uniform(0.0, 0.55) ** 1.3
        vv = rng.uniform(-0.1, v1 + 0.1)
        uu = su * (hw + 0.11) * (1 - t)
        zz = zt + 0.005 + 0.295 * t + 0.012
        r = rng.uniform(0.012, 0.03)
        b.lathe(mt["moss"], [(0, 0), (r, 0), (r * 0.8, r * 0.35), (0, r * 0.45)],
                xf=M @ Matrix.Translation((uu, vv, zz)) @ Matrix.Rotation(su * ang, 4, "Y"), segments=10, tile=0.05,
                radial=lambda a_, h_: 1 + 0.25 * math.sin(5 * a_))
    for su, vv in ((-1, 0.05), (1, 0.22)):
        xf = M @ Matrix.Translation((su * (hw + 0.14), vv, zt - 0.03)) @ Matrix.Rotation(su * 1.25, 4, "Y") @ Matrix.Rotation(0.2, 4, "X")
        b.box(mt["shingle2"], (0.09, 0.052, 0.007), (0, 0, 0), xf=xf, chamfer=0.0015)
    # A white cloth doll hung by its neck on red thread from the porch roof's eave.
    du, dv, dz = -0.2, -0.33, zt - 0.08
    neck = dz - 0.17
    b.tube(m["cloth_red"], [P(du, dv, dz), P(du + 0.004, dv, dz - 0.08), P(du + 0.006, dv - 0.004, neck + 0.004)], 0.0008, sides=4)
    D = M @ Matrix.Translation((du + 0.006, dv - 0.004, neck)) @ Matrix.Rotation(0.5, 4, "Z") @ Matrix.Rotation(0.12, 4, "X")
    doll_at = D
    # The red gable under the main roof's front, tarnished gilt rays from its foot.
    gz0, gz1 = zt, zt + 0.28
    b.add(mt["red"], [P(-hw - 0.08, v0 - 0.012, gz0), P(hw + 0.08, v0 - 0.012, gz0), P(0, v0 - 0.012, gz1)], [(0, 1, 2)],
          [(0, 0), (1, 0), (0.5, 1)], smooth=False)
    for k in range(7):
        a = math.pi * (k + 1) / 8
        b.tube(mt["gilt"], [P(0, v0 - 0.016, gz0 + 0.01), P(math.cos(a) * 0.17, v0 - 0.016, gz0 + 0.01 + math.sin(a) * 0.17 * (gz1 - gz0) / 0.33)],
               0.003, sides=4)
    # Inside: the clay Ta and Yey, faded white, faces worn dark; a third with its head
    # off, the head on the floor; a faded photograph of a woman against the back wall; the
    # candle burnt nearly out.
    scans = RK.Scans()
    scans.put(coll, "neakta_guardian", None, "spirit_house_figure_ta", M @ place(-0.075, 0.2, zb, rz=0.12), size=0.13, along=2, tris=3500)
    scans.put(coll, "phra_phum_lady", None, "spirit_house_figure_yey", M @ place(0.065, 0.21, zb, rz=-0.18), size=0.11, along=2, tris=3000)
    scans.put(coll, "phra_phum_lady", None, "spirit_house_figure_fallen", M @ place(0.15, 0.06, zb + 0.026, rz=1.1) @ Matrix.Rotation(1.5, 4, "Y"),
              size=0.1, along=2, tris=3000)
    b.add(mt["photo"], [P(-0.035, v1 - 0.03, zb + 0.005), P(0.035, v1 - 0.03, zb + 0.005), P(0.035, v1 - 0.012, zb + 0.1), P(-0.035, v1 - 0.012, zb + 0.1)],
          [(0, 1, 2, 3)], [(0.53, 0.08), (0.72, 0.08), (0.72, 0.92), (0.53, 0.92)], smooth=False)
    b.box(mt["post"], (0.082, 0.006, 0.106), (0, 0, 0), xf=M @ Matrix.Translation((0, v1 - 0.023, zb + 0.052)) @ Matrix.Rotation(-0.19, 4, "X"),
          chamfer=0.002)
    flames = []
    md = dict(m)
    md["clay"] = mt["clay_dark"]
    ok.candle_dish(b, md, M @ place(-0.17, 0.06, zb), rng, radius=0.022, melt=1.0)
    flames.append(ok.candle(b, m, M @ place(-0.17, 0.06, zb + 0.003), rng, height=0.018, radius=0.009, melt=1.0))
    # The porch: incense stubs overflowing the pot, a cup of water and one tipped over,
    # black bananas, a chicken's black feathers, dead marigolds.
    ok.incense_bowl(b, md, M @ place(0.0, -0.21, zp), rng, radius=0.05, height=0.045, sticks=60, lit=2)
    for k in range(10):                    # ash and fallen stubs spilled round the pot
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.055, 0.1)
        b.box(mt["soot"], (rng.uniform(0.005, 0.01), rng.uniform(0.003, 0.006), 0.002), (0, 0, 0),
              xf=M @ place(math.cos(a) * r, -0.21 + math.sin(a) * r, zp + 0.0015, rz=rng.uniform(0, 3)), chamfer=0.001)
    mc = dict(m)
    mc["clay"] = mt["cup"]
    ok.small_cup(b, mc, M @ place(-0.16, -0.24, zp), rng, radius=0.017, height=0.024, liquid="water")
    ok.small_cup(b, mc, M @ place(0.15, -0.26, zp + 0.017) @ Matrix.Rotation(1.57, 4, "Y"), rng, radius=0.017, height=0.024)
    for k in range(3):
        a = 0.3 + k * 0.25
        pts = [P(-0.22 + 0.11 * t * math.cos(a), -0.12 + 0.11 * t * math.sin(a) + 0.012 * math.sin(t * 3), zp + 0.012) for t in np.linspace(0, 1, 7)]
        b.tube(mt["rot"], pts, [0.006, 0.01, 0.012, 0.012, 0.011, 0.009, 0.005], sides=6, cap_end=True)
    for k in range(16):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0, 0.07)
        cu, cv = 0.12 + math.cos(a) * r, -0.15 + math.sin(a) * r
        L, W = rng.uniform(0.04, 0.09), rng.uniform(0.012, 0.02)
        turn = rng.uniform(0, math.tau)
        xf = M @ place(cu, cv, zp + 0.002 + 0.002 * k / 16, rz=turn)
        b.add(mt["feather"], [tuple(xf @ Vector(p)) for p in ((0, -W / 2, 0), (L, -W / 3, 0.004), (L * 1.1, 0, 0.006), (L, W / 3, 0.004), (0, W / 2, 0))],
              [(0, 1, 2, 3, 4)], [(0, 0), (1, 0), (1, 0.5), (1, 1), (0, 1)], smooth=True)
    for k in range(6):
        ok.marigold(b, m, P(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, -0.1), zp + 0.006), rng, radius=0.01, dead=True)
    # The post: rusty nails driven in all round, red thread wound tight, talismans pinned.
    for k in range(16):
        side = int(rng.integers(4))
        a = side * math.pi / 2
        zz = rng.uniform(0.3, zp - 0.15)
        off = rng.uniform(-0.045, 0.045)
        n_out = Vector((math.cos(a), math.sin(a), 0))
        base = Vector((n_out.x * 0.066 - n_out.y * off, n_out.y * 0.066 + n_out.x * off, zz))
        tip = base + n_out * rng.uniform(0.012, 0.03) + Vector((0, 0, rng.uniform(-0.01, 0.01)))
        b.tube(m["rust"], [P(*base), P(*tip)], 0.0028, sides=5)
        b.lathe(m["rust"], [(0, 0), (0.007, 0), (0.007, 0.002), (0, 0.003)],
                xf=Matrix.Translation(M @ tip) @ (R @ n_out).to_track_quat("Z", "Y").to_matrix().to_4x4(), segments=8, tile=0.05)
    turns = []
    for k in range(70):
        t = k / 69
        a = t * math.tau * 11
        c, s_ = math.cos(a), math.sin(a)
        k_ = 0.068 / max(abs(c), abs(s_))
        turns.append(P(c * k_, s_ * k_, 0.62 + 0.14 * t))
    b.tube(m["cloth_red"], turns, 0.0025, sides=4)
    for k, (side, zz) in enumerate(((0, 1.02), (1, 0.8), (3, 0.5))):
        a = side * math.pi / 2
        n_out = Vector((math.cos(a), math.sin(a), 0))
        tan = Vector((-n_out.y, n_out.x, 0))
        c0 = n_out * 0.067
        quad = [c0 - tan * 0.045 + Vector((0, 0, zz - 0.12)), c0 + tan * 0.045 + Vector((0, 0, zz - 0.12)),
                c0 + tan * 0.045 + Vector((0, 0, zz)), c0 - tan * 0.045 + Vector((0, 0, zz))]
        quad[0] += n_out * 0.006
        quad[1] += n_out * 0.003
        b.add(mt["talisman"], [P(*q) for q in quad], [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)
        b.lathe(m["rust"], [(0, 0), (0.006, 0), (0.006, 0.002), (0, 0.003)],
                xf=Matrix.Translation(M @ (c0 + Vector((0, 0, zz - 0.015)) + n_out * 0.002)) @ (R @ n_out).to_track_quat("Z", "Y").to_matrix().to_4x4(),
                segments=8, tile=0.05)
    # Wax that ran over the platform's front edge.
    for k in range(3):
        u = rng.uniform(-0.25, 0.25)
        L = rng.uniform(0.02, 0.06)
        b.tube(m["wax_old"], [P(u, -0.343, zp - 0.005), P(u + 0.003, -0.344, zp - 0.005 - L * 0.6), P(u + 0.002, -0.344, zp - 0.005 - L)],
               [0.004, 0.003, 0.0045], sides=5)
    # The house bound to its platform with white thread, loop on loop over the roof.
    for k in range(3):
        v = 0.0 + 0.12 * k + rng.normal(0, 0.01)
        tw = rng.normal(0, 0.03)
        pts = [P(-0.36, v + tw, zp + 0.08), P(-hw - 0.11, v, zt - 0.01), P(-hw - 0.12, v, zt + 0.012)]
        pts += [P(-(hw + 0.11) * (1 - t), v, zt + 0.02 + 0.295 * t) for t in np.linspace(0.2, 1, 5)]
        pts += [P((hw + 0.11) * t, v, zt + 0.02 + 0.295 * (1 - t)) for t in np.linspace(0.2, 1, 5)]
        pts += [P(hw + 0.12, v, zt + 0.012), P(hw + 0.11, v, zt - 0.01), P(0.36, v - tw, zp + 0.08)]
        b.tube(mt["thread"], pts, 0.0008, sides=4)
    built = b.build(coll)
    rag_doll(coll, "spirit_house_doll", mt, m, doll_at, rng)
    # Blood: pooled round the feathers, run over the front and down the post's face.
    post = built.get(mt["post"])
    pool = RK.decal(coll, "spirit_house_blood_pool", m["blood_pool"], [P(0.03, -0.27, zp + 0.003), P(0.25, -0.27, zp + 0.003),
                                                                       P(0.25, -0.05, zp + 0.003), P(0.03, -0.05, zp + 0.003)])
    RK.decal(coll, "spirit_house_blood_edge", m["blood_runs"], [P(0.02, -0.347, zp - 0.07), P(0.24, -0.347, zp - 0.07),
                                                               P(0.24, -0.347, zp + 0.002), P(0.02, -0.347, zp + 0.002)])
    if post is not None:
        d = RK.decal(coll, "spirit_house_blood_post", m["blood_runs"], [P(-0.05, -0.3, zp - 0.75), P(0.05, -0.3, zp - 0.75),
                                                                       P(0.05, -0.3, zp - 0.1), P(-0.05, -0.3, zp - 0.1)], n=8)
        RK.press(d, post, R @ Vector((0, 1, 0)), 0.002)
    # Cobwebs in the house's back corners under the roof and under the platform.
    import cobwebs as CW
    sheet, thread = CW.web_materials()
    for k, su in enumerate((-1, 1)):
        CW.corner_cobweb(f"spirit_house_web_{k}", coll, P(su * (hw - 0.01), v1 - 0.01, zt - 0.005), R @ Vector((-su, 0, 0)), R @ Vector((0, -1, 0)),
                         0.1, sheet, thread, seed=40 + k)
    CW.corner_cobweb("spirit_house_web_under", coll, P(0.07, 0.07, zp - 0.09), R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), 0.16, sheet, thread, seed=42)
    for o in [o for o in coll.objects if o.name.startswith("spirit_house_web")]:
        pass
    collider("spirit_house", coll, *(lambda bb: (bb[0].x, bb[1].x, bb[0].y, bb[1].y))(RK.box_of(list(built.values()))), g, g + 2.1)
    RK.flames_and_lights(coll, flames, "spirit_flame", "spirit_house", watts=0.35)
    RK.marker(coll, "marker_incense_smoke_spirit", P(0.0, -0.21, zp + 0.22))
    RK.marker(coll, "marker_flies_spirit", P(0.12, -0.15, zp + 0.25))
    print("[village] spirit house built new", flush=True)


# ------------------------------------------------------------------ 5. rice and banyans


def render_hill_atlas():
    """Fuller ripe hills than the first atlas (more tillers, wider), four to an atlas,
    their colour bled into the clear pixels so alpha testing leaves no dark fringe."""
    path = os.path.join(TEX, "T_ep1_rice_hills_full_BC.png")
    if os.path.exists(path):
        return path
    import rice_field as RF
    rng = np.random.default_rng(2413)
    cells, cell_px, width, height = 4, (512, 1024), 0.78, 1.24
    scene = bpy.data.scenes.new("rice_hills_full")
    sc_coll = scene.collection
    mat = RF.paint_material()
    cam = bpy.data.objects.new("rice_cam", bpy.data.cameras.new("rice_cam"))
    sc_coll.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = height
    cam.data.sensor_fit = "VERTICAL"
    cam.location = (0, -5, height / 2 - 0.04)
    cam.rotation_euler = (math.pi / 2, 0, 0)
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.transparent_max_bounces = 64
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = cell_px
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.world = bpy.data.worlds.new("rice_world")
    tiles = []
    for i in range(cells):
        objs = []
        for j in range(2):                         # two hills grown together: a fuller clump
            o = RF.hill_object("rice_hill_tmp", sc_coll, rng, True, tillers=int(rng.integers(18, 24)))
            o.data.materials.append(mat)
            o.location = (rng.uniform(-0.06, 0.06), rng.uniform(-0.04, 0.04), 0)
            o.rotation_euler = (0, 0, rng.uniform(0, math.tau))
            objs.append(o)
        bpy.context.view_layer.update()
        span = max(abs(v) for o in objs for c in o.bound_box for v in ((o.matrix_world @ Vector(c)).x,)) * 2 + 0.02
        for o in objs:
            o.scale = (min(1.0, width / span),) * 2 + (1.0,)
        scene.render.filepath = f"{path}.cell{i}.png"
        with bpy.context.temp_override(scene=scene):
            bpy.ops.render.render(write_still=True)
        tiles.append(scene.render.filepath)
        for o in objs:
            bpy.data.meshes.remove(o.data)
    w, h = cell_px
    atlas = np.zeros((h, w * cells, 4), dtype=np.float32)
    for i, tile in enumerate(tiles):
        img = bpy.data.images.load(tile)
        atlas[:, i * w:(i + 1) * w] = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
        bpy.data.images.remove(img)
        os.remove(tile)
    # Bleed the colour outward under the clear pixels.
    rgb, a = atlas[..., :3], atlas[..., 3:4]
    acc = rgb * a
    wsum = a.copy()
    for r in (2, 6, 16, 40):
        acc_b = np.stack([RK.blur(acc[..., c], r) for c in range(3)], axis=-1)
        w_b = RK.blur(wsum[..., 0], r)[..., None]
        fill = acc_b / np.maximum(w_b, 1e-5)
        rgb = np.where(a > 0.5, rgb, np.where(w_b > 1e-4, fill, rgb))
    out = np.dstack([rgb, a[..., 0]])[::-1]          # rows top to bottom for save_png
    bpy.data.objects.remove(cam)
    bpy.data.scenes.remove(scene)
    return RK.save_png("T_ep1_rice_hills_full_BC", out)


def rice(coll, ground, rng):
    """The ripe plots replanted with the fuller hills, three cards each, closer."""
    import village_fields as VF
    import village_nature as VN
    RK.delete([o for o in bpy.data.objects if o.name.startswith("paddy_rice_ripe_")])
    mat = VN.rice_material("M_paddy_rice_full", render_hill_atlas())
    spacing, cells, width, height = 0.27, 4, 0.78, 1.2
    meshes = {}
    clear = [(x, y, 3.2 * s) for x, y, s, _ in BANYANS]
    for x0, x1, y0, y1, kind in VF.PLOTS:
        if kind != "ripe":
            continue
        lodged = [(rng.uniform(x0 + 1, x1 - 1), rng.uniform(y0 + 1, y1 - 1), rng.uniform(0.7, 1.5), rng.uniform(0, math.tau))
                  for _ in range(int(rng.integers(0, 3)))]
        y = y0 + rng.uniform(0.05, spacing)
        while y < y1:
            x = x0 + rng.uniform(0, 0.2)
            while x < x1 - rng.uniform(0, 0.2):
                hx, hy = x + rng.normal(0, 0.03), y + rng.normal(0, 0.03)
                if rng.random() > 0.03 and all((hx - cx) ** 2 + (hy - cy) ** 2 > r * r for cx, cy, r in clear):
                    k = rng.uniform(0.86, 1.08)
                    lean = (rng.normal(0, 0.08), rng.normal(0, 0.08))
                    for lx, ly, lr, la in lodged:
                        d = math.hypot(hx - lx, hy - ly)
                        if d < lr:
                            f = 1 - d / lr
                            lean = (lean[0] + math.cos(la) * 1.5 * f, lean[1] + math.sin(la) * 1.5 * f)
                    key = (int(hx // 12), int(hy // 12))
                    meshes.setdefault(key, []).append((hx, hy, ground(hx, hy), k, int(rng.integers(cells)), rng.uniform(0, math.pi), lean))
                x += spacing
            y += spacing
    n = 0
    for (i, j), hills in meshes.items():
        verts, faces, uvs, normals = [], [], [], []
        for hx, hy, gz, k, cell, yaw, lean in hills:
            u0, u1 = cell / cells, (cell + 1) / cells
            up = Vector((lean[0], lean[1], 1)).normalized() * (height * k)
            for turn in (0.0, math.pi / 3, 2 * math.pi / 3):
                a = yaw + turn
                ax = Vector((math.cos(a), math.sin(a), 0)) * (width * k / 2)
                base = Vector((hx, hy, gz - 0.04))
                bi = len(verts)
                verts += [base - ax, base + ax, base + ax + up, base - ax + up]
                faces.append((bi, bi + 1, bi + 2, bi + 3))
                uvs += [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
                for t, sx in ((0, -1), (0, 1), (1, 1), (1, -1)):
                    normals.append((Vector((0, 0, 0.6 + 0.4 * t)) + ax.normalized() * 0.3 * sx).normalized())
            n += 1
        me = bpy.data.meshes.new(f"paddy_rice_ripe_{i}_{j}")
        me.from_pydata([v[:] for v in verts], [], faces)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uv.data[li].uv = uvs[me.loops[li].vertex_index]
        me.materials.append(mat)
        me.normals_split_custom_set([normals[me.loops[li].vertex_index][:] for li in range(len(me.loops))])
        obj = bpy.data.objects.new(me.name, me)
        coll.objects.link(obj)
    print("[village] rice replanted:", n, "hills", flush=True)


def banyans(coll, ground, rng):
    """Four more banyans like the Neak Ta's, on low earth islands in the paddies (their
    rice cleared round them), one shared, lighter copy of the scan."""
    src = bpy.data.objects.get("banyan")
    if src is None:
        print("[village] banyan missing", flush=True)
        return
    tmp = bpy.data.objects.new("_banyan_tmp", src.data)
    bpy.context.scene.collection.objects.link(tmp)
    mod = tmp.modifiers.new("dec", "DECIMATE")
    mod.ratio = 0.42
    deps = bpy.context.evaluated_depsgraph_get()
    light = bpy.data.meshes.new_from_object(tmp.evaluated_get(deps))
    light.name = "forest_banyan_light"
    bpy.data.objects.remove(tmp, do_unlink=True)
    m = materials()
    RK.vl()
    sb = RK.box_of([src])
    trunk = Vector(((sb[0].x + sb[1].x) / 2, (sb[0].y + sb[1].y) / 2, 0))
    col = bpy.data.objects.get("col_banyan")
    if col is not None:
        cb = RK.box_of([col])
        trunk = Vector(((cb[0].x + cb[1].x) / 2, (cb[0].y + cb[1].y) / 2, 0))
    z0 = ground(trunk.x, trunk.y)
    W = src.matrix_world.copy()
    b = Batch("fs_banyan_mounds")
    for k, (x, y, s, turn) in enumerate(BANYANS):
        g = ground(x, y)
        o = bpy.data.objects.new(f"fs_banyan_{k}", light)
        coll.objects.link(o)
        # The source's placement with its trunk moved to the origin, turned and scaled
        # there, then stood on this island.
        o.matrix_world = Matrix.Translation((x, y, g + 0.18)) @ Matrix.Rotation(turn, 4, "Z") @ Matrix.Scale(s, 4) @ \
            Matrix.Translation((-trunk.x, -trunk.y, -z0)) @ W
        r = 3.0 * s
        b.lathe(m["mound"], [(0, 0.3), (r * 0.55, 0.28), (r * 0.85, 0.16), (r, 0.02), (r * 1.08, -0.12), (0, -0.12)],
                xf=place(x, y, g - 0.08), segments=36, tile=1.0, radial=lambda a, h: 1 + 0.08 * math.sin(3 * a + k))
        c = 1.4 * s
        collider(f"fs_banyan_{k}", coll, x - c, x + c, y - c, y + c, g, g + 5.0, surface="mud")
    b.build(coll)
    print("[village] banyans:", len(BANYANS), flush=True)


# ------------------------------------------------------------------ all


def review(coll, ground):
    m = materials()
    rng = np.random.default_rng(2425)
    clear_ground_cover()
    well(coll, m, ground, rng)
    funeral_front(coll, m, ground, rng)
    shrines(coll, m, ground, rng)
    banyans(coll, ground, rng)
    rice(coll, ground, np.random.default_rng(2426))
