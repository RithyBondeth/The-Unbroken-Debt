"""Episode 1's house and the funeral under it after the user's second review of
November 24, 2026 (ten game screenshots): "very detail and very realistic", "not a
cartoon".

- The hall (the "meeting room"): the low table of offerings beside the altar held a
  coconut that read as a half-sunk watermelon, a plate of smooth orange balls and toy
  bananas. Now scanned fruit (Poly Haven: oranges from the lemon scan's peel, Asian
  pears, an apple, a hand of bananas) on a footed brass tray and a banana leaf, lotus buds
  in a celadon vase, a lit candle and three joss sticks, every piece standing on the
  table's top inside its edges.
- Sok's photograph on the altar: simple, a plain blue studio background (the funeral's
  wreath has the same print), in a plain black frame under glass with a black ribbon and
  jasmine; the altar's two candles lit, its lotus real folded buds, three fresh joss sticks
  smoking (the game: FuneralRoom.ts, the smoke and the flames answer Sora passing them),
  a footed tray of fruit and the rice bowl on the step.
- The washing room, its sheet over a body and its line of cloths gone ("remove the whole
  current thing"); a first rebuild as the washing room after the washing was turned down
  ("I don't really like this room redesign"), the user chose the funeral's store room:
  shelves of folded mourning whites and incense, rolled mats, spare coffin planks and a
  lacquered lid, the guests' folding tables, crates of candles and kerosene tins, the
  rolled canopy, and stools on a table under a white dust cloth (the J2 sheet,
  `wash_room_sheet`). The "floating white box" there was the game's blessed matchbox
  (ArrivalModels.ts, at the old altar's step): now on the hall altar's step, with the spare
  candle, incense bundle and sla thor that stood inside the altar's closed case; Kanha's
  drawing ("beside the upstairs altar") pinned flat on the hall wall beside it.
- Kanha's room: the two upright suitcases stood on two others with a 3 cm gap: all four
  laid flat, stacked.
- The bathroom off the landing, its hair gone and redesigned from scans: two big glazed
  water jars (the MAHS scan) under plank lids, the dipper, a wooden bucket, a low stool,
  an enamel basin, a jug, soap in a coconut shell, a comb and a clay lamp on the shelf,
  towels, the duckboard over the wet corner.
- Under the house: the fruit tray's balls and grapes are scanned fruit now; the floor
  cleared of the scattered candle stubs, petals, sandals, footprints, rotten fruit, the
  stool and its spill, and the two rows of candles down the way in; the soot handprints
  and the black seep are blood that reads as blood (dragged handprints, a pool soaked into
  the earth, runs down the bier's cloth); the wreath's photograph the same blue print.

Blender metres, X east, Y north, Z up. Called at the end of rebuild-farmstead.py.
"""
import math
import os
import re

import bpy
import numpy as np
from mathutils import Matrix, Vector

import house_refine as HR
import offerings_kit as ok
import review_kit as RK
import stilt_house as SH
from kit import ROOT, collider, image_material, library_material, mesh_object, plain
from shrine_craft import Batch, place

F, T = SH.FLOOR, SH.T
TEX = RK.TEX
PHOTO_BLUE = os.path.join(TEX, "T_ep1_photo_sok_blue_BC.png")


def crop(u, v):
    """The blue print framed tighter: the cut-out bust's lower corner stays out of the frame
    (3:4 kept: u 0.09-0.91, v 0.18-1)."""
    return (0.09 + 0.82 * u, 0.18 + 0.82 * v)


def materials(m):
    """The review's own materials on top of the house's."""
    r = dict(m)
    r.update(ok.materials())
    r["brass_bright"] = plain("M_rv_brass", (0.55, 0.38, 0.14), rough=0.32, metal=1.0)
    r["brass_old"] = plain("M_rv_brass_old", (0.34, 0.24, 0.1), rough=0.5, metal=1.0)
    r["black_lacquer"] = plain("M_rv_black_lacquer", (0.012, 0.011, 0.01), rough=0.3)
    r["frame_glass"] = plain("M_rv_frame_glass", (0.6, 0.62, 0.62), rough=0.04, alpha=0.12)
    r["satin_black"] = plain("M_rv_black_satin", (0.01, 0.01, 0.012), rough=0.35)
    r["photo_blue"] = image_material("M_rv_photo_sok_blue", PHOTO_BLUE, rough=0.35)
    r["leaf_green"] = library_material("forest_leaves_02", "M_rv_banana_leaf", colour=(0.07, 0.16, 0.03), tile=0.4)
    r["celadon"] = plain("M_rv_celadon", (0.32, 0.4, 0.33), rough=0.18)
    r["wet_wood"] = library_material("weathered_brown_planks", "M_rv_wet_wood", tint=(0.3, 0.25, 0.21), tile=0.8)
    r["bed_wood"] = library_material("dark_wooden_planks", "M_rv_bed_wood", tint=(0.55, 0.45, 0.38), tile=0.9)
    r["linen_wet"] = library_material("rough_linen", "M_rv_burial_linen", tint=(0.78, 0.76, 0.7), tile=0.35)
    r["linen_dry"] = library_material("rough_linen", "M_rv_folded_linen", tint=(0.86, 0.84, 0.78), tile=0.3)
    r["scented"] = plain("M_rv_scented_water", (0.05, 0.045, 0.03), rough=0.03)
    r["frangipani"] = plain("M_rv_frangipani", (0.78, 0.74, 0.6), rough=0.6)
    r["frangipani_heart"] = plain("M_rv_frangipani_heart", (0.75, 0.55, 0.12), rough=0.6)
    r["lid_wood"] = library_material("old_planks_02", "M_rv_lid_wood", tint=(0.5, 0.42, 0.36), tile=0.6)
    r["tin"] = plain("M_rv_tin_cup", (0.35, 0.34, 0.32), rough=0.4, metal=0.9)
    r["paper"] = image_material("M_rv_kanha_drawing", os.path.join(TEX, "T_ep1_kanha_drawing_BC.png"), rough=0.92)
    r["nail"] = plain("M_rv_nail", (0.05, 0.045, 0.04), rough=0.5, metal=0.8)
    r["paper_bag"] = library_material("dirty_carpet", "M_rv_brown_paper", colour=(0.32, 0.22, 0.12), tile=0.3)
    r["cloth_red"] = plain("M_rv_red_thread", (0.35, 0.03, 0.025), rough=0.8)
    r["pet"] = plain("M_rv_pet_bottle", (0.82, 0.86, 0.9), rough=0.06, alpha=0.22)
    r["water_clear"] = plain("M_rv_bottle_water", (0.6, 0.7, 0.78), rough=0.02, alpha=0.18)
    r["label"] = plain("M_rv_bottle_label", (0.55, 0.62, 0.72), rough=0.45)
    r["cap_blue"] = plain("M_rv_bottle_cap", (0.04, 0.16, 0.45), rough=0.4)
    r["blood_hands"] = RK.soft_material("M_rv_blood_hands", RK.blood_handprint(), rough=0.45)
    r["blood_pool"] = RK.soft_material("M_rv_blood_pool", RK.blood_pool(), rough=0.18)
    r["blood_runs"] = RK.soft_material("M_rv_blood_runs", RK.blood_runs(), rough=0.4)
    return r


def _orange(mat):
    """The lemon scan's material with the orange peel (keeps its normal and ORM maps)."""
    if mat is None:
        return mat
    new = bpy.data.materials.get("M_rv_orange_scan")
    if new:
        return new
    new = mat.copy()
    new.name = "M_rv_orange_scan"
    for n in new.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and "diff" in n.image.name:
            n.image = bpy.data.images.load(RK.orange_peel(), check_existing=True)
    return new


# ------------------------------------------------------------------ fruit


def fruit_pile(coll, scans, prefix, x, y, z, rng, radius, kinds, top=None):
    """Fruit on a tray or plate: a ring of them on its floor at `z`, each turned its own
    way, one more resting in the hollow on top. `kinds`: list of (model, piece, size)."""
    out = []
    n = len(kinds)
    sizes = [k[2] for k in kinds]
    r_ring = max(radius - max(sizes) / 2 - 0.004, 0.0)
    a0 = rng.uniform(0, math.tau)
    for k, (model, piece, size) in enumerate(kinds):
        a = a0 + math.tau * k / n + rng.normal(0, 0.08)
        px, py = x + math.cos(a) * r_ring, y + math.sin(a) * r_ring
        xf = Matrix.Translation((px, py, z)) @ Matrix.Rotation(rng.uniform(0, math.tau), 4, "Z") @ \
            Matrix.Rotation(rng.normal(0, 0.12), 4, "X")
        o = scans.put(coll, model, piece, f"{prefix}_{k}", xf, size=size, tris=1600, retex=_orange if model == "lemon" else None)
        out.append(o)
    if top:
        model, piece, size = top
        lift = z + max(sizes) * 0.55
        xf = Matrix.Translation((x, y, lift)) @ Matrix.Rotation(rng.uniform(0, math.tau), 4, "Z")
        out.append(scans.put(coll, model, piece, f"{prefix}_top", xf, size=size, tris=1600,
                             retex=_orange if model == "lemon" else None))
    return out


def footed_tray(b, m, x, y, z, radius, height=0.07):
    """A brass offering tray on a foot (choeung): returns the height of its floor."""
    prof = [(0, 0), (radius * 0.45, 0), (radius * 0.46, 0.008), (radius * 0.2, 0.02), (radius * 0.18, height * 0.75),
            (radius * 0.9, height * 0.92), (radius, height + 0.012), (radius * 1.02, height + 0.016),
            (radius * 0.97, height + 0.014), (radius * 0.86, height * 0.96), (0, height * 0.92)]
    b.lathe(m["brass_bright"], prof, xf=place(x, y, z), segments=40, tile=0.2)
    return z + height * 0.92


def banana_leaf(b, m, x, y, z, w, d, turn, rng):
    """A square of banana leaf laid under fruit: folded edges, a midrib down it."""
    c, s = math.cos(turn), math.sin(turn)
    def at(u, v):
        lift = 0.004 * (abs(u) > 0.42) + 0.003 * math.sin(u * 9)
        return (x + c * u * w - s * v * d, y + s * u * w + c * v * d, z + 0.0015 + lift)
    b.grid(m["leaf"] or m["leaf_green"], lambda u, v: at(u - 0.5, v - 0.5), 8, 4, uv=lambda u, v: (u, v))


# ------------------------------------------------------------------ 1. the hall's side table


def hall_table(coll, m, scans, rng):
    """The low table beside the altar, set again with real fruit and everything on its top."""
    RK.delete(RK.roots(re.compile(r"^(hall_side_offerings|hall_offering_bananas)")))
    table = bpy.data.objects.get("hall_offering_table")
    if table is None:
        print("[review] hall table missing", flush=True)
        return []
    RK.flames_out(Vector((-1.7, 16.9, 2.8)), Vector((-0.95, 17.4, 3.2)))
    bb = RK.box_of(RK.tree(table))
    x0, x1, y0, y1 = bb[0].x + 0.025, bb[1].x - 0.025, bb[0].y + 0.02, bb[1].y - 0.02
    top = RK.ray_down((x0 + x1) / 2, (y0 + y1) / 2, bb[1].z + 0.2) or bb[1].z
    yc = (y0 + y1) / 2
    b = Batch("hall_table_offerings")
    # A banana leaf over the middle of the top, under the tray and the bananas.
    banana_leaf(b, m, (x0 + x1) / 2 + 0.03, yc, top, x1 - x0 - 0.12, y1 - y0 - 0.03, 0.0, rng)
    leaf_top = top + 0.003
    # Left: the candle in a brass dish, lit.
    flames = []
    cx, cy = x0 + 0.05, y0 + 0.06
    b.lathe(m["brass_old"], [(0, 0), (0.04, 0), (0.042, 0.012), (0.036, 0.014), (0.012, 0.008), (0, 0.008)],
            xf=place(cx, cy, top), segments=24, tile=0.1)
    flames.append(ok.candle(b, m, place(cx, cy, top + 0.008, rz=rng.uniform(0, 6)), rng, height=0.075, radius=0.011, melt=0.55))
    # Behind it, three lotus buds in a slim celadon vase.
    vx, vy = x0 + 0.06, y1 - 0.06
    scans.put(coll, "brass_vase_02", None, "hall_table_vase", Matrix.Translation((vx, vy, top)), size=0.17, along=2, tris=3000)
    for k in range(3):
        ok.lotus_bud(b, m, (vx + (k - 1) * 0.014, vy + rng.normal(0, 0.005), top + 0.17 + 0.11 + 0.025 * (k == 1)),
                     ((k - 1) * 0.18, rng.normal(0, 0.05), 1), rng, size=0.062, stem=0.16)
    # Middle: the footed tray of fruit.
    tx, ty = (x0 + x1) / 2 - 0.02, yc + 0.01
    floor = footed_tray(b, m, tx, ty, leaf_top, 0.1)
    fruit_pile(coll, scans, "hall_table_fruit", tx, ty, floor, rng, 0.09,
               [("lemon", None, 0.064), ("food_pears_asian_01", "food_pears_asian_01_a", 0.07), ("lemon", None, 0.062),
                ("food_apple_01", None, 0.066), ("lemon", None, 0.063)],
               top=("lemon", None, 0.06))
    # Front of the tray: three joss sticks in a little bowl of rice.
    ix, iy = tx - 0.02, y0 + 0.035
    b.lathe(m["porcelain"], [(0, 0), (0.016, 0), (0.03, 0.018), (0.032, 0.034), (0.029, 0.034), (0.026, 0.02), (0, 0.005)],
            xf=place(ix, iy, leaf_top), segments=24, tile=0.1)
    b.lathe(m["rice"], [(0.029, 0.03), (0.016, 0.037), (0, 0.039)], xf=place(ix, iy, leaf_top), segments=20, tile=0.05)
    for k, dx in enumerate((-0.006, 0.0, 0.006)):
        ok.joss_stick(b, m, (ix + dx, iy, leaf_top + 0.032), (dx * 6, -0.05, 1), 0.2, rng, burnt=0.15 + 0.07 * k)
    smoke = [Vector((ix, iy, leaf_top + 0.2))]
    # Right: a hand of bananas lying on the leaf.
    bx = x1 - 0.085
    bananas = scans.put(coll, "bananas", "bananas_bunch", "hall_table_bananas",
                        Matrix.Translation((bx, yc, leaf_top)) @ Matrix.Rotation(math.pi / 2 + 0.15, 4, "Z"), size=0.165, tris=5000)
    b.build(coll)
    RK.vl()
    # Each scanned piece stood on what is under it (the tray's floor, the leaf, the top).
    for o in [bananas] + [o for o in coll.objects if o.name.startswith("hall_table_fruit_")]:
        bb2 = RK.box_of([o])
        if bb2 and (bb2[1].x > x1 + 0.01 or bb2[0].x < x0 - 0.01):
            o.location.x += max(0.0, x0 - bb2[0].x) - max(0.0, bb2[1].x - x1)
    print("[review] hall table set", flush=True)
    return flames, smoke


# ------------------------------------------------------------------ 2. Sok's altar


def altar(coll, m, scans, rng):
    """Sok's photograph, simple on its blue, and the altar's offerings made real."""
    RK.delete(RK.roots(re.compile(r"^(hall_altar_offerings|hall_altar_lotus$)")))
    cab = bpy.data.objects.get("hall_altar_cabinet")
    if cab is None:
        return [], []
    cb = RK.box_of([cab])
    upper = cb[1].z
    wall = SH.ALTAR_Y - T / 2
    b = Batch("hall_altar_review")
    flames, smoke = [], []
    # The photograph: a plain black frame under glass on a low dark riser, leaning back on
    # its strut; a black ribbon over the corner; jasmine across the top.
    pw, ph, fw = 0.24, 0.32, 0.022
    py = wall - 0.07
    b.box(m["dark_teak"], (0.34, 0.13, 0.09), (0.0, py - 0.01, upper + 0.045), chamfer=0.006)
    b.box(m["dark_teak"], (0.3, 0.115, 0.08), (0.0, py - 0.005, upper + 0.13), chamfer=0.006)
    z0 = upper + 0.17
    lean = 0.11
    M = Matrix.Translation((0.0, py + 0.015, z0)) @ Matrix.Rotation(-lean, 4, "X")
    def at(x, z, y=0.0):
        return tuple(M @ Vector((x, y, z)))
    W, H = pw + 2 * fw, ph + 2 * fw
    for (cx_, cz_, sx_, sz_) in ((0, fw / 2, W, fw), (0, H - fw / 2, W, fw), (-W / 2 + fw / 2, H / 2, fw, H), (W / 2 - fw / 2, H / 2, fw, H)):
        b.box(m["black_lacquer"], (sx_, 0.018, sz_), (cx_, 0.0, cz_), xf=M, chamfer=0.004)
    b.box(m["brass_old"], (pw + 0.006, 0.004, 0.004), (0, -0.006, fw - 0.002), xf=M)
    b.box(m["photo_back"], (W - 0.01, 0.008, H - 0.01), (0, 0.011, H / 2), xf=M)
    b.add(m["photo_blue"], [at(-pw / 2, fw), at(pw / 2, fw), at(pw / 2, fw + ph), at(-pw / 2, fw + ph)], [(0, 1, 2, 3)],
          [crop(0, 0), crop(1, 0), crop(1, 1), crop(0, 1)], smooth=False, xf=Matrix.Translation(M.to_3x3() @ Vector((0, -0.004, 0))))
    b.add(m["frame_glass"], [at(-pw / 2 - 0.003, fw - 0.003, -0.007), at(pw / 2 + 0.003, fw - 0.003, -0.007),
                             at(pw / 2 + 0.003, fw + ph + 0.003, -0.007), at(-pw / 2 - 0.003, fw + ph + 0.003, -0.007)],
          [(0, 1, 2, 3)], [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)
    b.tube(m["dark_teak"], [at(0, H * 0.7, 0.02), (0.0, py + 0.12, z0)], 0.006, sides=5)
    # The black ribbon: a band across the top right corner and a small bow.
    rb = [at(W / 2 - 0.07, H + 0.004, -0.012), at(W / 2 + 0.004, H - 0.07, -0.012)]
    b.tube(m["satin_black"], rb, 0.009, sides=4)
    for s_ in (-1, 1):
        b.tube(m["satin_black"], [at(W / 2 - 0.035, H - 0.035, -0.014), at(W / 2 - 0.035 + s_ * 0.03, H - 0.035 + 0.02, -0.016),
                                  at(W / 2 - 0.035 + s_ * 0.026, H - 0.035 - 0.012, -0.016)], 0.006, sides=4)
    # The altar's two candles lit (their wicks were cold).
    for sx in (-1, 1):
        flames.append(Vector((0.25 * sx, 17.25, 4.262)))
    # Real lotus buds in the two brass vases, three each, stems to the vase floor.
    for sx in (-1, 1):
        vx, vy = 0.5 * sx, 17.287
        for k in range(3):
            a = (k - 1) * 0.22 + rng.normal(0, 0.05)
            ok.lotus_bud(b, m, (vx + math.sin(a) * 0.05 * sx, vy + rng.normal(0, 0.01), 4.38 + 0.03 * (k == 1)),
                         (math.sin(a) * 0.9 * sx, rng.normal(0, 0.1), 1), rng, size=0.07, stem=0.27)
    # Three fresh joss sticks in the brass pot before him, smoking.
    for k, dx in enumerate((-0.016, 0.0, 0.016)):
        ok.joss_stick(b, m, (dx, 17.25 + 0.004 * k, 4.035), (dx * 5, -0.04, 1), 0.25, rng, burnt=0.1 + 0.05 * k)
    smoke.append(Vector((0.0, 17.24, 4.29)))
    # On the step: water, rice heaped in a bowl, tea, a footed tray of fruit, bananas.
    step_z, step_y = None, None
    for yy in np.linspace(cb[0].y + 0.02, cb[1].y - 0.02, 30):
        zz = RK.ray_down(-0.4, yy, upper + 0.5)
        if zz is not None and zz < upper - 0.1:
            step_z, step_y = zz, yy
        elif zz is not None:
            break
    if step_z is None:
        step_z, step_y = upper - 0.35, cb[0].y + 0.2
    sy = (cb[0].y + step_y) / 2 + 0.01
    ok.small_cup(b, m, place(-0.68, sy, step_z), rng, radius=0.028, height=0.05, liquid="water")
    rx = -0.5
    b.lathe(m["porcelain"], [(0, 0), (0.025, 0), (0.028, 0.006), (0.05, 0.035), (0.052, 0.05), (0.048, 0.05), (0.046, 0.036),
                             (0.024, 0.01), (0, 0.009)], xf=place(rx, sy, step_z), segments=32, tile=0.1)
    b.lathe(m["porcelain_blue"], [(0.05, 0.04), (0.0515, 0.046), (0.0505, 0.047)], xf=place(rx, sy, step_z, s=1.004), segments=32, tile=0.1, cap=False)
    b.lathe(m["rice"], [(0.047, 0.044), (0.03, 0.062), (0, 0.068)], xf=place(rx, sy, step_z), segments=24, tile=0.05)
    ok.small_cup(b, m, place(-0.34, sy, step_z), rng, radius=0.024, height=0.035, liquid="water")
    floor = footed_tray(b, m, 0.33, sy, step_z, 0.095)
    fruit_pile(coll, scans, "hall_altar_fruit", 0.33, sy, floor, rng, 0.085,
               [("lemon", None, 0.062), ("lemon", None, 0.064), ("food_pears_asian_01", "food_pears_asian_01_c", 0.068),
                ("lemon", None, 0.061)], top=("lemon", None, 0.058))
    banana_leaf(b, m, 0.62, sy, step_z, 0.2, 0.12, 0.1, rng)
    scans.put(coll, "bananas", "bananas_bunch", "hall_altar_bananas",
              Matrix.Translation((0.62, sy, step_z + 0.003)) @ Matrix.Rotation(math.pi / 2, 4, "Z"), size=0.17, tris=5000)
    b.build(coll)
    # The story's things "beside the upstairs altar" stood inside its closed upper case (the
    # old altar's step height): the spare candle, the incense bundle and the sla thor go out
    # on the step's back row (the blessed matches go before them: ArrivalModels.ts).
    for name, x in (("interact_incense_bundle", -0.45), ("hall_slathor", 0.0), ("interact_altar_candle", 0.45)):
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        RK.vl()
        bb = RK.box_of(RK.tree(o)) or (o.matrix_world.translation, o.matrix_world.translation)
        lift = o.matrix_world.translation.z - bb[0].z
        o.matrix_world = Matrix.Translation((x, step_y - 0.07, step_z + lift)) @ Matrix.Rotation(o.matrix_world.to_euler().z, 4, "Z")
    kanha_drawing(coll, m)
    print("[review] altar: blue photograph, candles lit, lotus, incense, fruit", flush=True)
    return flames, smoke


def kanha_drawing(coll, m):
    """Kanha's drawing "beside the upstairs altar" (the story): it hung 2 cm inside the
    washing room's wall where the old altar stood. Pinned flat on the hall's north wall
    east of the altar, under the family's photographs, a nail at its top."""
    holder = bpy.data.objects.get("interact_kanha_drawing")
    drawing = bpy.data.objects.get("kanha_drawing")
    if holder is None or drawing is None:
        return
    cx, cz, w, h = 1.2, 3.84, 0.36, 0.38
    deps = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = bpy.context.scene.ray_cast(deps, Vector((cx, 17.1, cz)), Vector((0, 1, 0)), distance=1.0)
    wy = (loc.y if hit else 17.45) - 0.004
    holder.matrix_world = Matrix.Translation((cx, wy - 0.02, cz)) @ Matrix.Rotation(holder.matrix_world.to_euler().z, 4, "Z")
    RK.vl()
    inv = drawing.matrix_world.inverted()
    verts = []
    for j in range(5):
        for i in range(5):
            u, v = i / 4, j / 4
            curl = 0.006 * (1 - v) ** 2 * (abs(u - 0.5) * 2) ** 2 + 0.003 * v * v
            verts.append(tuple(inv @ Vector((cx - w / 2 + w * u, wy - curl, cz - h / 2 + h * v))))
    faces = [(j * 5 + i, j * 5 + i + 1, (j + 1) * 5 + i + 1, (j + 1) * 5 + i) for j in range(4) for i in range(4)]
    uvs = [(i / 4, j / 4) for j in range(5) for i in range(5)]
    me = drawing.data
    me.clear_geometry()
    me.from_pydata(verts, [], faces)
    layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]
    nb = Batch("kanha_drawing_nail")
    nb.lathe(m["nail"], [(0, 0), (0.005, 0), (0.005, 0.002), (0.0015, 0.003), (0.0015, 0.012), (0, 0.012)],
             xf=Matrix.Translation((cx, wy - 0.001, cz + h / 2 - 0.02)) @ Matrix.Rotation(math.pi / 2, 4, "X"), segments=10, tile=0.05)
    nb.build(coll)


# ------------------------------------------------------------------ 3. the store room behind the altar


def store_room(coll, m, scans, rng):
    """The room behind the altar as the funeral's store (the user chose it, Nov 24, 2026,
    over the washing room): what the household keeps for the days of the funeral, put away
    in the dark. Shelves of folded white mourning clothes and bundled incense, reed mats
    rolled and stood in the corner, spare coffin planks and a red-lacquered lid against the
    wall, the guests' folding tables stacked one on another, crates of candles and tins of
    kerosene, the canopy rolled along the floor, the stools stacked under a white cloth (the
    J2 sheet: it is the cloth that sits up). One candle left burning on a crate."""
    RK.delete(RK.roots(re.compile(r"^(wash_room|wash_stain|wash_wet_feet|wash_pot|dress_wash_)")))
    RK.flames_out(Vector((-3.0, 17.6, 2.4)), Vector((3.0, 21.9, 3.6)))
    X0, X1, Y0, Y1 = -2.93, 2.93, 17.57, 21.93
    b = Batch("wash_room")
    flames = []
    lacquer = bpy.data.materials.get("M_fu_coffin_lacquer") or m["lacquer"]
    gilt = bpy.data.materials.get("M_fu_coffin_gilt") or m["gilt"]
    reed = bpy.data.materials.get("M_reed_mat") or m["bed_wood"]

    def put(model, name, x, y, z, turn=0.0, size=None, along=None, flip=False, tris=6000):
        xf = Matrix.Translation((x, y, z)) @ Matrix.Rotation(turn, 4, "Z")
        if flip:
            xf = xf @ Matrix.Rotation(math.pi, 4, "Y")
        o = scans.put(coll, model, None, name, xf, size=size, along=along, tris=tris)
        RK.vl()
        bb = RK.box_of([o])
        o.location.z += z - bb[0].z
        RK.vl()
        return o, RK.box_of([o])

    # West wall: a tall worn shelf, its back to the wall, filled with the funeral's whites.
    shelf, sb = put("wooden_bookshelf_worn", "wash_room_shelf", X0 + 0.3, 19.55, F, turn=-math.pi / 2, tris=12000)
    shelf.location.x += X0 + 0.01 - sb[0].x
    RK.vl()
    sb = RK.box_of([shelf])
    collider("wash_room_shelf", coll, sb[0].x, sb[1].x, sb[0].y, sb[1].y, F, sb[1].z)
    levels, z = [], sb[1].z - 0.02
    cx_, cy_ = (sb[0].x + sb[1].x) / 2, (sb[0].y + sb[1].y) / 2
    while z > F + 0.1:
        hit = RK.ray_down(cx_, cy_, z, distance=2.5)
        if hit is None or hit < F + 0.05:
            break
        levels.append(hit)
        z = hit - 0.05
    for li, lz in enumerate(levels):
        y = sb[0].y + 0.12
        while y < sb[1].y - 0.2:
            kind = rng.random()
            if kind < 0.6:          # a pile of folded white cloth
                zz = lz
                for k in range(int(rng.integers(3, 6))):
                    hgt = 0.028 + 0.008 * rng.random()
                    b.box(m["linen_dry"], (0.3 + rng.normal(0, 0.01), 0.26 + rng.normal(0, 0.01), hgt),
                          (cx_ + rng.normal(0, 0.012), y + 0.13 + rng.normal(0, 0.008), zz + hgt / 2), chamfer=0.011)
                    zz += hgt
                y += 0.3
            elif kind < 0.8:        # bundles of joss sticks, tied with red thread
                for k in range(int(rng.integers(2, 4))):
                    bx, by = cx_ - 0.1 + 0.08 * k, y + 0.1
                    b.tube(m["incense"] if "incense" in m else m["bed_wood"], [(bx, by - 0.16, lz + 0.012), (bx, by + 0.16, lz + 0.012)],
                           0.012, sides=8, cap_end=True)
                    b.tube(m["cloth_red"] if "cloth_red" in m else m["lacquer"], [(bx, by - 0.02, lz + 0.012), (bx, by + 0.0, lz + 0.012)],
                           0.0135, sides=8)
                y += 0.26
            else:                   # packets of candles in brown paper
                for k in range(int(rng.integers(1, 3))):
                    b.box(m["paper_bag"], (0.2, 0.12, 0.05), (cx_ + rng.normal(0, 0.02), y + 0.1, lz + 0.025 + 0.05 * k), chamfer=0.004)
                y += 0.24
    # The north-west corner: reed mats rolled and stood on end, two leaning out of them.
    for k in range(7):
        a = rng.uniform(0, math.tau)
        r = 0.065 + 0.02 * rng.random()
        px = X0 + 0.18 + 0.22 * (k % 3) + rng.normal(0, 0.02)
        py = Y1 - 0.18 - 0.2 * (k // 3) + rng.normal(0, 0.02)
        L = rng.uniform(0.9, 1.2)
        lean = Vector((rng.normal(0, 0.03), rng.normal(0, 0.03), 1)).normalized()
        if k >= 5:
            lean = Vector((0.35 if k == 5 else 0.1, -0.1 if k == 5 else -0.35, 1)).normalized()
        b.tube(reed, [(px, py, F), tuple(Vector((px, py, F)) + lean * L)], r, sides=14, cap_end=True)
        b.lathe(m["bed_wood"], [(r * 0.98, 0), (r * 0.3, 0.002), (0, 0.003)], xf=Matrix.Translation(Vector((px, py, F)) + lean * (L + 0.001)) @
                lean.to_track_quat("Z", "Y").to_matrix().to_4x4(), segments=14, tile=0.1, cap=False)
    collider("wash_room_mats", coll, X0, X0 + 0.75, Y1 - 0.75, Y1, F, F + 1.2)
    # North wall, west of the door: spare coffin planks leaning on it, the lacquered lid last.
    for k in range(6):
        w, L = 0.3 + 0.04 * rng.random(), 2.0 + 0.1 * rng.random()
        x = -1.75 + 0.27 * k
        foot = Vector((x, Y1 - 0.42 - 0.02 * k, F + 0.002))
        top = Vector((x + rng.normal(0, 0.02), Y1 - 0.04, F + L * 0.92))
        d = (top - foot).normalized()
        M = Matrix.Translation((foot + top) / 2) @ d.to_track_quat("Z", "X").to_matrix().to_4x4()
        mat = lacquer if k == 5 else m["bed_wood"]
        b.box(mat, (w, 0.028, L), (0, 0, 0), xf=M, chamfer=0.004, jitter=0.001, rng=rng)
        if k == 5:
            for s_ in (-1, 1):
                b.box(gilt, (0.012, 0.03, L - 0.06), (s_ * (w / 2 - 0.02), -0.002, 0), xf=M)
    collider("wash_room_planks", coll, -1.95, -0.05, Y1 - 0.5, Y1, F, F + 1.9)
    # The north-east corner: crates of candles and the kerosene tins.
    c1, cb1 = put("wooden_crate_01", "wash_room_crate_0", X1 - 0.5, Y1 - 0.24, F, turn=0.0, tris=4000)
    c2, cb2 = put("wooden_crate_01", "wash_room_crate_1", X1 - 0.52, Y1 - 0.26, cb1[1].z, turn=0.06, tris=4000)
    c3, cb3 = put("wooden_crate_01", "wash_room_crate_2", X1 - 0.27, Y1 - 0.78, F, turn=math.pi / 2 + 0.1, tris=4000)
    collider("wash_room_crates", coll, min(cb1[0].x, cb3[0].x), X1, cb3[0].y, Y1, F, cb2[1].z)
    for k in range(3):
        put("oil_tin", f"wash_room_tin_{k}", X1 - 0.75 - 0.14 * k, Y1 - 0.62 - 0.05 * (k % 2), F, turn=rng.uniform(0, 6), size=0.22, along=2, tris=2000)
    # A candle left burning on the top crate, a few loose candles beside it.
    tx, ty, tz = X1 - 0.62, Y1 - 0.3, cb2[1].z
    ok.candle_dish(b, m, place(tx, ty, tz), rng, radius=0.04, melt=0.9)
    flames.append(ok.candle(b, m, place(tx, ty, tz + 0.005), rng, height=0.05, radius=0.011, melt=0.95))
    for k in range(4):
        a = rng.uniform(-0.4, 0.4)
        ok.candle(b, m, place(tx - 0.2 + 0.03 * k, ty - 0.02 * k, tz + 0.011, rz=math.pi / 2 + a) @ Matrix.Rotation(math.pi / 2, 4, "X"), rng,
                  height=0.16, radius=0.011, melt=0.0, lit=False)
    # East wall: the guests' folding tables, one standing, one on it legs up.
    t1, tb1 = put("wooden_table_02", "wash_room_table_0", X1 - 0.38, 19.55, F, turn=math.pi / 2, tris=2000)
    t1.location.x += X1 - 0.01 - tb1[1].x
    RK.vl()
    tb1 = RK.box_of([t1])
    t2, tb2 = put("wooden_table_02", "wash_room_table_1", (tb1[0].x + tb1[1].x) / 2 - 0.02, 19.58, tb1[1].z, turn=math.pi / 2 + 0.04,
                  flip=True, tris=2000)
    collider("wash_room_tables", coll, tb1[0].x, X1, tb1[0].y, tb1[1].y, F, tb2[1].z)
    # The canopy rolled along the floor against the altar's back, its poles beside it.
    b.tube(m["linen_dry"], [(-1.6, Y0 + 0.14, F + 0.1), (0.9, Y0 + 0.15, F + 0.1)], 0.1, sides=18, cap_end=True)
    for k in range(4):
        b.tube(m["bamboo"], [(-1.7 + 0.03 * k, Y0 + 0.32 + 0.05 * k, F + 0.03), (1.0 - 0.05 * k, Y0 + 0.34 + 0.04 * k, F + 0.03)], 0.022, sides=8)
    collider("wash_room_canopy", coll, -1.75, 1.05, Y0, Y0 + 0.55, F, F + 0.22)
    # Stools turned up on a low table under a white dust cloth to the floor (J2: it sits up).
    sx, sy = 0.72, 19.45
    pile = []
    t, tb = put("small_wooden_table_01", "wash_room_stool_table", sx, sy, F, turn=0.25, tris=3000)
    pile.append(t)
    for k, dx in enumerate((-0.22, 0.22)):
        o, ob = put("wooden_stool_01", f"wash_room_stool_{k}", sx + dx * math.cos(0.25), sy + dx * math.sin(0.25), tb[1].z,
                    turn=rng.uniform(0, 6), flip=True, tris=4000)
        pile.append(o)
    stack = RK.box_of(pile)
    b.build(coll)
    over = stack[1].z - F + 0.25
    RK.box_drape("wash_room_sheet", coll, m["linen_wet"], (stack[0].x, stack[1].x, stack[0].y, stack[1].y), stack[1].z, F,
                 ((stack[0].x + stack[1].x) / 2 + 0.05, (stack[0].y + stack[1].y) / 2 - 0.03),
                 (stack[1].x - stack[0].x + 2 * over, stack[1].y - stack[0].y + 2 * over), rng, nu=60, nv=56, rumple=0.04)
    RK.solidify(bpy.data.objects["wash_room_sheet"], 0.0025)
    collider("wash_room_stools", coll, stack[0].x - 0.1, stack[1].x + 0.1, stack[0].y - 0.1, stack[1].y + 0.1, F, stack[1].z)
    print("[review] store room built behind the altar", flush=True)
    return flames, []


# ------------------------------------------------------------------ 4. the suitcases


def suitcases():
    """Kanha's room: the four suitcases that stood on end, two on two with a gap, laid flat
    and stacked against the wall."""
    lower, upper = bpy.data.objects.get("house_vintage_suitcase_4"), bpy.data.objects.get("house_vintage_suitcase_5")
    if not lower or not upper:
        return
    RK.vl()
    b0 = RK.box_of(RK.tree(lower))
    wall_y = b0[0].y
    base = F
    for k, root in enumerate((lower, upper)):
        # Lay the pair down on its back (the handle side to the room), then stand it on base.
        root.rotation_euler = (math.radians(-90), 0, math.radians((-2.5, 3.5)[k]))
        RK.vl()
        bb = RK.box_of(RK.tree(root))
        root.location += Vector((0.0 if k == 0 else 0.04, wall_y + 0.015 - bb[0].y, base - bb[0].z))
        RK.vl()
        base = RK.box_of(RK.tree(root))[1].z - 0.002
    print("[review] suitcases laid flat, stacked to", round(base, 3), flush=True)


# ------------------------------------------------------------------ 5. the bathroom


def bathroom(coll, m, scans, rng):
    """Redesigned from scans: no hair, every piece a real object."""
    RK.delete(RK.roots(re.compile(r"^bath_")))
    x0, x1 = SH.LAND_X + T / 2, SH.B["x1"] - T
    y0, y1 = SH.ROW2 + T / 2, SH.B["y1"] - T
    RK.flames_out(Vector((x0, y0, F)), Vector((x1, y1, F + 2.6)))
    flames = []
    # The duckboard over the wet corner: teak slats with a finger's gap on three bearers.
    dx0, dy0 = 5.55, 31.25
    b = Batch("bath_duckboard")
    for yy in np.linspace(dy0 + 0.1, y1 - 0.1, 3):
        b.box(m["wet_wood"], (x1 - dx0 - 0.04, 0.07, 0.045), ((dx0 + x1) / 2, yy, F + 0.0225), chamfer=0.004)
    x = dx0
    while x < x1 - 0.05:
        wd = rng.uniform(0.085, 0.1)
        b.box(m["wet_wood"], (wd, y1 - dy0 - 0.02, 0.026), (x + wd / 2, (dy0 + y1) / 2, F + 0.058), chamfer=0.005, jitter=0.0012, rng=rng)
        x += wd + 0.016
    b.build(coll)
    RK.decal(coll, "bath_wet_boards", m["wet_stain"], [(dx0 - 0.3, dy0 - 0.25, F + 0.002), (x1, dy0 - 0.25, F + 0.002),
                                                       (x1, y1, F + 0.002), (dx0 - 0.3, y1, F + 0.002)])
    deck = F + 0.071
    b = Batch("bath_things")
    # The big jar in the corner under a plank lid, the dipper on it; a smaller one beside.
    for k, (jx, jy, hh) in enumerate(((x1 - 0.42, y1 - 0.42, 0.86), (x1 - 1.12, y1 - 0.3, 0.55))):
        jar = scans.put(coll, "water_jar", None, f"bath_jar_{k}", Matrix.Translation((jx, jy, deck)) @
                        Matrix.Rotation(rng.uniform(0, math.tau), 4, "Z"), size=hh, along=2, tris=8000)
        RK.vl()
        jb = RK.box_of([jar])
        rad = (jb[1].x - jb[0].x) / 2
        if k == 0:
            for j, off in enumerate((-0.11, 0.0, 0.11)):
                b.box(m["lid_wood"], (0.5, 0.1, 0.022), (jx - 0.12, jy + off, jb[1].z + 0.011), chamfer=0.003, jitter=0.001, rng=rng)
            b.box(m["lid_wood"], (0.05, 0.34, 0.025), (jx - 0.26, jy, jb[1].z + 0.034), chamfer=0.004)
            b.lathe(m["coconut"], [(0, -0.055), (0.05, -0.05), (0.068, -0.025), (0.072, 0.0), (0.066, 0.0), (0, -0.045)],
                    xf=place(jx + 0.03, jy - 0.08, jb[1].z + 0.08), segments=20, tile=0.1)
            b.tube(m["bamboo"], [(jx + 0.05, jy - 0.06, jb[1].z + 0.075), (jx - 0.22, jy - 0.22, jb[1].z + 0.03)], 0.008, sides=6)
        collider(f"bath_jar_{k}", coll, jx - rad, jx + rad, jy - rad, jy + rad, F, jb[1].z + 0.04)
    # The enamel basin on its three-legged stand by the south wall; the jug beside it.
    sx, sy = 5.05, y0 + 0.32
    for k in range(3):
        a = k * math.tau / 3 + 0.5
        b.tube(m["dark_teak"], [(sx + math.cos(a) * 0.2, sy + math.sin(a) * 0.2, F), (sx + math.cos(a) * 0.15, sy + math.sin(a) * 0.15, F + 0.72)],
               0.017, sides=8)
    b.lathe(m["dark_teak"], [(0.17, 0), (0.19, 0), (0.19, 0.025), (0.17, 0.025)], xf=place(sx, sy, F + 0.7), segments=32, tile=0.3)
    b.lathe(m["dark_teak"], [(0.17, 0), (0.185, 0), (0.185, 0.02), (0.17, 0.02)], xf=place(sx, sy, F + 0.3), segments=32, tile=0.3)
    basin = scans.put(coll, "pot_enamel_01", None, "bath_basin", Matrix.Translation((sx, sy, F + 0.725)), size=0.36, tris=6000)
    jug = scans.put(coll, "metal_jug", None, "bath_jug", Matrix.Translation((sx + 0.34, sy + 0.06, F)) @ Matrix.Rotation(-1.0, 4, "Z"),
                    size=0.24, along=2, tris=4000)
    collider("bath_basin", coll, sx - 0.22, sx + 0.22, sy - 0.22, sy + 0.22, F, F + 0.82)
    # The shelf on the east wall: soap in a coconut shell, a comb, a bottle of oil, the lamp.
    shy0, shy1, shz = 30.9, 31.7, F + 1.22
    b.box(m["dark_teak"], (0.2, shy1 - shy0, 0.028), (x1 - 0.1, (shy0 + shy1) / 2, shz - 0.014), chamfer=0.004)
    for yy in (shy0 + 0.08, shy1 - 0.08):
        b.box(m["dark_teak"], (0.16, 0.025, 0.025), (x1 - 0.08, yy, shz - 0.05), chamfer=0.003)
        b.tube(m["dark_teak"], [(x1 - 0.01, yy, shz - 0.16), (x1 - 0.15, yy, shz - 0.03)], 0.01, sides=6)
    b.lathe(m["coconut"], [(0, 0), (0.045, 0), (0.06, 0.012), (0.058, 0.016), (0, 0.006)], xf=place(x1 - 0.1, shy0 + 0.14, shz), segments=20, tile=0.1)
    b.box(m["soap"], (0.06, 0.085, 0.028), (x1 - 0.1, shy0 + 0.14, shz + 0.02), chamfer=0.01)
    b.box(m["dark_teak"], (0.012, 0.13, 0.04), (x1 - 0.1, shy0 + 0.3, shz + 0.006), chamfer=0.002)
    for k in range(14):
        b.box(m["dark_teak"], (0.004, 0.0025, 0.03), (x1 - 0.1, shy0 + 0.245 + k * 0.0085, shz - 0.002))
    import house_props as HP
    HP.bottle(b, m, x1 - 0.1, shy0 + 0.45, shz, rng, h=0.18)
    b.lathe(m["clay_lamp"], [(0, 0), (0.035, 0), (0.05, 0.012), (0.055, 0.028), (0.045, 0.03), (0, 0.022)],
            xf=place(x1 - 0.1, shy1 - 0.12, shz), segments=20, tile=0.1, radial=lambda a, h: 1 + 0.25 * max(0.0, math.cos(a)) ** 6)
    flames.append(Vector((x1 - 0.1 + 0.052, shy1 - 0.12, shz + 0.04)))
    b.build(coll)
    # The bucket and the low stool on the boards.
    scans.put(coll, "wooden_bucket_01", None, "bath_bucket", Matrix.Translation((6.25, 32.5, deck)) @ Matrix.Rotation(0.7, 4, "Z"),
              size=0.32, along=2, tris=6000)
    scans.put(coll, "wooden_stool_02", None, "bath_stool", Matrix.Translation((6.6, 31.85, deck)) @ Matrix.Rotation(0.26, 4, "Z"),
              size=0.24, along=2, tris=6000)
    collider("bath_bucket", coll, 6.07, 6.43, 32.32, 32.68, F, F + 0.4)
    # Two krama towels on a cord along the south wall, a sarong on a peg by the door.
    cy = y0 + 0.07
    b = Batch("bath_cord")
    b.tube(m["cord"], [(5.7, cy, F + 1.62), (6.6, cy, F + 1.6), (7.6, cy, F + 1.62)], 0.0025, sides=4)
    for xx in (5.7, 7.6):
        b.tube(m["iron"], [(xx, y0, F + 1.62), (xx, cy + 0.01, F + 1.62)], 0.004, sides=5)
    b.build(coll)
    for k, (a, c) in enumerate(((5.9, 6.35), (6.75, 7.25))):
        HP.hung_cloth(coll, m, m["krama"], f"bath_krama_{k}", (a, cy, F + 1.61), (c, cy, F + 1.61), 0.55 + 0.08 * k, folds=6,
                      rng=np.random.default_rng(90 + k))
    print("[review] bathroom rebuilt from scans", flush=True)
    return flames


# ------------------------------------------------------------------ 6. under the house


def _bottle(b, m, x, y, z, rng, full=0.7):
    """A half-litre water bottle: clear ribbed plastic, a paper label round its waist, the
    water inside, a ridged blue cap."""
    prof = [(0, 0), (0.026, 0), (0.031, 0.004), (0.032, 0.03)]
    for k in range(5):
        h0 = 0.035 + k * 0.022
        prof += [(0.032, h0), (0.0295, h0 + 0.006), (0.032, h0 + 0.012)]
    prof += [(0.032, 0.16), (0.03, 0.175), (0.02, 0.198), (0.0135, 0.208), (0.0135, 0.215), (0, 0.215)]
    b.lathe(m["pet"], prof, xf=place(x, y, z), segments=28, tile=0.1)
    b.lathe(m["water_clear"], [(0, 0.004), (0.029, 0.004), (0.029, 0.16 * full), (0, 0.16 * full)], xf=place(x, y, z), segments=20, tile=0.1)
    b.lathe(m["label"], [(0.0325, 0.07), (0.0325, 0.125)], xf=place(x, y, z, rz=rng.uniform(0, 6)), segments=28, tile=0.205, cap=False)
    b.lathe(m["cap_blue"], [(0, 0.213), (0.0145, 0.213), (0.0148, 0.232), (0.012, 0.234), (0, 0.234)], xf=place(x, y, z), segments=20, tile=0.05)
    b.lathe(m["cap_blue"], [(0.0152, 0.205), (0.0152, 0.209), (0.0138, 0.21)], xf=place(x, y, z), segments=20, tile=0.05, cap=False)


FLOOR_CLUTTER = re.compile(r"^fu_dread_(candles|petals|sandals|foot|fruit|soot|spill|stool|bowl|handprint|seep|stand_drips)")


def _drop_islands(o, keep):
    """Deletes the loose parts of a merged mesh whose middles fail `keep(Vector)`."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    seen, gone = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, island = [v], []
        seen.add(v.index)
        while stack:
            a = stack.pop()
            island.append(a)
            for e in a.link_edges:
                b_ = e.other_vert(a)
                if b_.index not in seen:
                    seen.add(b_.index)
                    stack.append(b_)
        c = sum((o.matrix_world @ a.co for a in island), Vector()) / len(island)
        if not keep(c):
            gone += island
    bmesh.ops.delete(bm, geom=gone, context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return len(gone)


def funeral(coll, m, scans, rng, ground):
    """The funeral under the house: real fruit, a clean floor, blood that is blood."""
    import funeral_under as FU
    cx, cy = FU.COFFIN
    tx, ty = FU.TABLE
    gone = RK.delete([o for o in coll.objects if FLOOR_CLUTTER.match(o.name)] +
                     [o for o in bpy.data.objects if re.match(r"^coffin_seep_\d+$", o.name)])
    # The two rows of candles on the mats down the way in (|x - axis| 0.8-1.0, south of the
    # coffin) and their flames and lights; the ring round the coffin and the pots stay.
    def in_rows(p):
        return 0.75 < abs(p.x - cx) < 1.05 and 12.9 < p.y < cy - 0.95 and p.z < 0.4
    n = 0
    for o in [o for o in coll.objects if o.name.startswith("fu_incense_candles_")]:
        n += _drop_islands(o, lambda c: not in_rows(c))
    RK.delete([o for o in bpy.data.objects if o.name.startswith(("fu_flame_", "light_flame_fu_candle_")) and
               in_rows(o.matrix_world.translation if o.type == "EMPTY" else (RK.box_of([o])[0] + RK.box_of([o])[1]) / 2)])
    print("[review] funeral floor cleared:", gone, "pieces,", n, "verts of the candle rows", flush=True)
    # The tray of fruit: scanned oranges, apples, pears and a pomegranate.
    for o in [o for o in coll.objects if re.match(r"^fu_table_things_fu_(orange|apple|grape)", o.name)]:
        RK.delete([o])
    tray = bpy.data.objects.get("fu_table_things_fu_gilt_tray") or next((o for o in coll.objects if "gilt_tray" in o.name), None)
    top = RK.box_of([bpy.data.objects["fu_table_top"]])[1].z
    fx, fy = tx + 0.25, ty + 0.05
    floor = top + 0.12 if tray is None else RK.box_of([tray])[1].z - 0.012
    fruit_pile(coll, scans, "fu_table_fruit", fx, fy, floor, rng, 0.16,
               [("lemon", None, 0.07), ("food_apple_01", None, 0.075), ("lemon", None, 0.068), ("food_pears_asian_01", "food_pears_asian_01_b", 0.08),
                ("lemon", None, 0.07), ("food_apple_01", None, 0.072), ("food_pomegranate_01", None, 0.08)],
               top=("lemon", None, 0.066))
    scans.put(coll, "bananas", "bananas_bunch", "fu_table_bananas",
              Matrix.Translation((tx + 0.5, ty - 0.12, top + 0.001)) @ Matrix.Rotation(2.0, 4, "Z"), size=0.2, tris=5000)
    # The table under a real white cloth, settled over it to the mats (the old front was a
    # stiff pleated board), and bottles of water that look like bottles.
    tg = ground(tx, ty)
    RK.delete([bpy.data.objects.get("fu_table_cloth_front")] +
              [o for o in coll.objects if re.match(r"^fu_table_things_fu_bottle", o.name)])
    import house_new_rooms as HN
    HN.drape_sheet(coll, m["linen_dry"], "fu_table_cloth", (tx, ty, top + 0.25), 2.3, 1.75,
                   [((tx - 0.6, tx + 0.6), (ty - 0.35, ty + 0.35), (tg, top)), ((tx - 1.6, tx + 1.6), (ty - 1.4, ty + 1.4), (tg - 0.1, tg + 0.03))],
                   frames=80, bending=0.12)
    RK.solidify(bpy.data.objects["fu_table_cloth"], 0.002)
    bb = Batch("fu_table_water")
    for k, dx in enumerate((-0.48, -0.4, 0.5)):
        _bottle(bb, m, tx + dx, ty + 0.18 - 0.05 * k, top + 0.004, rng, full=(0.85, 0.5, 0.95)[k])
    bb.build(coll)
    RK.vl()
    # Blood: hands dragged down the table's front cloth (each decal pressed onto the cloth's
    # folds), the pool at the coffin's foot soaking into the earth and the mat, runs down
    # the bier's cloth.
    cloth = bpy.data.objects["fu_table_cloth"]
    for k, (hx, hz0, hz1, flip) in enumerate(((tx - 0.32, 0.14, 0.5, False), (tx + 0.18, 0.08, 0.44, True))):
        u0, u1 = (1, 0) if flip else (0, 1)
        o = RK.decal(coll, f"fu_blood_hands_{k}", m["blood_hands"],
                     [(hx - 0.1, ty - 0.8, tg + hz0), (hx + 0.1, ty - 0.8, tg + hz0), (hx + 0.1, ty - 0.8, tg + hz1), (hx - 0.1, ty - 0.8, tg + hz1)],
                     uv=((u0, 0), (u1, 0), (u1, 1), (u0, 1)), n=8)
        RK.press(o, cloth, Vector((0, 1, 0)), 0.003)
    stand_front = cy - (FU.COFFIN_SIZE[1] / 2 + 0.16)
    RK.ground_decal(coll, "fu_blood_pool", m["blood_pool"], lambda x, y: ground(x, y) + 0.04, cx + 0.35, stand_front - 0.12, 0.95, 0.7,
                    0.15, lift=0.006, n=8)
    RK.decal(coll, "fu_blood_bier_runs", m["blood_runs"],
             [(cx - 0.1, stand_front - 0.013, ground(cx, cy) + 0.02), (cx + 0.75, stand_front - 0.013, ground(cx, cy) + 0.02),
              (cx + 0.75, stand_front - 0.013, ground(cx, cy) + FU.STAND_H - 0.01), (cx - 0.1, stand_front - 0.013, ground(cx, cy) + FU.STAND_H - 0.01)])
    # The wreath's photograph: the same simple blue print.
    photo = bpy.data.objects.get("interact_portrait") or bpy.data.objects.get("fu_portrait_photo")
    if photo is not None:
        photo.data.materials[0] = m["photo_blue"]
        layer = photo.data.uv_layers.active
        if layer is not None:
            for d in layer.data:
                d.uv = crop(*d.uv)
    print("[review] funeral: fruit, blood, photograph", flush=True)


# ------------------------------------------------------------------ all


def review(coll, m, ground):
    """Runs the house and funeral passes; returns nothing (flames and lights made here)."""
    m = materials(m)
    scans = RK.Scans()
    rng = np.random.default_rng(2424)
    flames, smoke = [], []
    f, s = hall_table(coll, m, scans, rng)
    flames += f
    smoke += s
    f, s = altar(coll, m, scans, rng)
    flames += f
    smoke += s
    f, s = store_room(coll, m, scans, rng)
    flames += f
    smoke += s
    suitcases()
    flames += bathroom(coll, m, scans, rng)
    RK.flames_and_lights(coll, flames, "house_flame_90", "house_review", watts=0.6)
    for k, p in enumerate(smoke):
        RK.marker(coll, f"marker_incense_smoke_{k}", p)
    fu = bpy.data.collections.get("funeral_under")
    if fu is not None:
        funeral(fu, m, scans, rng, ground)
    print("[review] house:", len(flames), "flames,", len(smoke), "smoke columns", flush=True)
