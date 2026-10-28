"""Builds Sora's studio in Phnom Penh (Episode 1 prologue) as a near-final room.

Episode 1 Beat Sheet 4.1: a single room 6 x 5 m, ceiling 3.2 m, on the third floor
of a 1930s shophouse; one door (east), one tall window (south); drafting table
under the window, desk with drawer on the west wall, shelf with candle and
satchel (north), brass wall telephone and coat hook with the hurricane lamp by the
door, wall clock above the desk.

Library models and materials come from art-source/library/ (CC0, Poly Haven;
`npm run fetch-library`); the rest is modelled here. Run (repository root):
    blender -b --factory-startup -P tools/areas/ep1_area_studio.py
Sora's drawings and the prints on the walls are rendered first by
`npm run drawings -- ep1` (tools/drawings/ep1.mjs, with Khmer lettering) into
art-source/textures/ep1/. This writes art-source/blender/ep1/ep1_area_studio.blend;
then `npm run export -- ep1 && npm run assets -- ep1`.

Blender axes: X east, Y north, Z up; metres. Object names follow the Technical
Design Document, section 7.1 (col_, interact_, spawn_, light_flame_, marker_).
"""

import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from kit import *  # noqa: E402,F403  (shared materials and geometry)

BLEND = os.path.join(ROOT, "art-source", "blender", "ep1", "ep1_area_studio.blend")

W, D, H = 6.0, 5.0, 3.2
WALL = 0.2
DOOR = {"y0": 2.0, "y1": 3.0, "top": 2.25}
WINDOW = {"x0": 2.25, "x1": 3.75, "bottom": 0.75, "top": 2.85}
rng = np.random.default_rng(1932)


# ------------------------------------------------------------------- room


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    area = bpy.data.collections.new("ep1_area_studio")
    bpy.context.scene.collection.children.link(area)
    layer = bpy.context.view_layer.layer_collection.children[area.name]
    bpy.context.view_layer.active_layer_collection = layer
    os.makedirs(TEXTURES, exist_ok=True)

    m = {
        "floor": library_material("floor_tiles_06", "M_studio_floor_tiles"),
        "plaster": library_material("yellow_plaster", "M_studio_plaster"),
        "ceiling": library_material("dark_wooden_planks", "M_studio_ceiling"),
        "wood": library_material("dark_wood", "M_dark_wood"),
        "teak": library_material("teak_veneer", "M_teak_veneer"),
        "worn": library_material("wood_table_worn", "M_wood_worn"),
        "linen": library_material("rough_linen", "M_linen", colour=(0.78, 0.72, 0.6)),
        "krama": library_material("fabric_pattern_07", "M_krama"),
        "rug": library_material("quatrefoil_jacquard_fabric", "M_rug", tint=(0.75, 0.6, 0.5)),
        "brass": plain("M_brass", (0.62, 0.45, 0.2), rough=0.35, metal=1.0),
        "iron": plain("M_black_iron", (0.03, 0.03, 0.03), rough=0.5, metal=0.8),
        "paper": plain("M_paper", (0.86, 0.82, 0.72), rough=0.95),
        "leather": plain("M_leather", (0.24, 0.12, 0.06), rough=0.55),
        "book": plain("M_book_cover", (0.08, 0.06, 0.05), rough=0.6),
        "glass": plain("M_window_glass", (0.6, 0.65, 0.7), rough=0.05, alpha=0.18),
        "green_glass": plain("M_lamp_green_glass", (0.05, 0.35, 0.15), rough=0.15, emission=(0.2, 0.7, 0.3), strength=0.6),
        "bulb": plain("M_lamp_bulb", (1, 0.9, 0.7), rough=0.3, emission=(1, 0.85, 0.6), strength=6.0),
        "ink": plain("M_ink", (0.02, 0.02, 0.025), rough=0.1),
        "candle": plain("M_candle_wax", (0.9, 0.86, 0.75), rough=0.5),
        "facade": library_material("yellow_plaster", "M_facade_plaster", tint=(0.35, 0.33, 0.3)),
        "neighbour": plain("M_neighbour_window", (0.1, 0.07, 0.04), emission=(1, 0.62, 0.3), strength=0.6),
        "net": plain("M_mosquito_net", (0.9, 0.9, 0.88), rough=0.9, alpha=0.22),
    }
    m["illustration"] = drawing("M_studio_illustration", "T_studio_illustration_BC")
    m["tonle_sap"] = drawing("M_studio_print_tonle_sap", "T_studio_print_tonle_sap_BC")
    m["alphabet"] = drawing("M_studio_print_alphabet", "T_studio_print_alphabet_BC")
    m["angkor"] = drawing("M_studio_print_angkor", "T_studio_print_angkor_BC")
    for study in ("palms", "house", "ornament", "lettering", "boats"):
        m[study] = drawing(f"M_studio_study_{study}", f"T_studio_study_{study}_BC")

    # ---- Shell: floor, timber ceiling with beams, ochre plaster walls, skirting, picture rail.
    box("floor", area, 0, W, 0, D, -0.05, 0, m["floor"])
    collider("floor", area, 0, W, 0, D, -0.2, 0, surface="stone")
    box("ceiling", area, 0, W, 0, D, H, H + 0.05, m["ceiling"])
    for i, x in enumerate([1.0, 2.25, 3.5, 4.75]):
        box(f"ceiling_beam_{i}", area, x - 0.08, x + 0.08, 0, D, H - 0.2, H, m["wood"], edge=0.01)

    def wall(name, x0, x1, y0, y1, z0=0.0, z1=H, solid=True):
        box(name, area, x0, x1, y0, y1, z0, z1, m["plaster"])
        if solid:
            collider(name, area, x0, x1, y0, y1, z0, z1)

    wall("wall_west", -WALL, 0, 0, D)
    wall("wall_north", -WALL, W + WALL, D, D + WALL)
    wall("wall_east_south", W, W + WALL, 0, DOOR["y0"])
    wall("wall_east_north", W, W + WALL, DOOR["y1"], D)
    wall("wall_east_head", W, W + WALL, DOOR["y0"], DOOR["y1"], DOOR["top"], H, solid=False)
    wall("wall_south_west", -WALL, WINDOW["x0"], -WALL, 0)
    wall("wall_south_east", WINDOW["x1"], W + WALL, -WALL, 0)
    wall("wall_south_sill", WINDOW["x0"], WINDOW["x1"], -WALL, 0, 0, WINDOW["bottom"])
    wall("wall_south_head", WINDOW["x0"], WINDOW["x1"], -WALL, 0, WINDOW["top"], H, solid=False)
    # Skirting and picture rail in dark wood (colonial detail).
    for name, a in [("west", (0, 0.02, 0, D)), ("north", (0, W, D - 0.02, D)), ("east_s", (W - 0.02, W, 0, DOOR["y0"] - 0.08)),
                    ("east_n", (W - 0.02, W, DOOR["y1"] + 0.08, D)), ("south_w", (0, WINDOW["x0"], 0, 0.02)), ("south_e", (WINDOW["x1"], W, 0, 0.02))]:
        x0, x1, y0, y1 = a
        box(f"skirting_{name}", area, x0, x1, y0, y1, 0, 0.14, m["wood"], edge=0.004)
        box(f"picture_rail_{name}", area, x0, x1, y0, y1, 2.45, 2.49, m["wood"], edge=0.003)

    # ---- Window: tall casement, glass, sill, linen curtains; louvred shutters outside.
    wx0, wx1, wb, wt = WINDOW["x0"], WINDOW["x1"], WINDOW["bottom"], WINDOW["top"]
    xm = (wx0 + wx1) / 2
    box("window_sill", area, wx0 - 0.08, wx1 + 0.08, -0.12, 0.08, wb - 0.04, wb, m["wood"], edge=0.006)
    for name, a in [("left", (wx0, wx0 + 0.07)), ("right", (wx1 - 0.07, wx1)), ("mid", (xm - 0.035, xm + 0.035))]:
        box(f"window_frame_{name}", area, a[0], a[1], -0.12, -0.06, wb, wt, m["wood"], edge=0.004)
    for z in (wb, (wb + wt) / 2 + 0.3, wt - 0.07):
        box(f"window_bar_{z:.2f}", area, wx0, wx1, -0.12, -0.06, z, z + 0.06, m["wood"], edge=0.004)
    box("window_glass", area, wx0, wx1, -0.1, -0.095, wb, wt, m["glass"])
    for side, (a, b) in {"left": (wx0 - 0.75, wx0 - 0.05), "right": (wx1 + 0.05, wx1 + 0.75)}.items():
        # Shutters folded back against the facade outside, slats catching lightning.
        box(f"shutter_{side}_frame", area, a, b, -0.3, -0.26, wb, wt, m["wood"], edge=0.004)
        for k in range(22):
            z = wb + 0.08 + k * (wt - wb - 0.16) / 22
            box(f"shutter_{side}_slat_{k}", area, a + 0.04, b - 0.04, -0.33, -0.29, z, z + 0.05, m["wood"], tilt=(0.5, 0, 0))
    box("curtain_rail", area, wx0 - 0.5, wx1 + 0.5, 0.06, 0.09, wt + 0.12, wt + 0.15, m["brass"])
    cloth("curtain_left", area, wx0 - 0.48, wx0 + 0.12, 0.2, wt + 0.12, 0.12, m["linen"], folds=5)
    cloth("curtain_right", area, wx1 - 0.12, wx1 + 0.48, 0.2, wt + 0.12, 0.12, m["linen"], folds=5)
    # The street outside: the shophouse opposite, one window lit behind its shutters.
    box("facade_opposite", area, -4, 10, -6.2, -6.0, -8, 6, m["facade"])
    box("facade_opposite_window_lit", area, 2.0, 2.9, -5.99, -5.98, 0.6, 2.4, m["neighbour"])
    box("facade_opposite_window_dark", area, 4.6, 5.5, -5.99, -5.98, 0.6, 2.4, m["ink"])
    empty("marker_lightning", area, (xm, -2.5, 3.0))

    # ---- Door (east): panelled, with frame and brass handle. Closed until Sora has her kit.
    door = box("interact_door", area, W - 0.02, W + 0.03, DOOR["y0"] + 0.02, DOOR["y1"] - 0.02, 0, DOOR["top"] - 0.02, m["wood"],
               edge=0.006, action="open")
    door["requires"] = "ep1.kit.collected"
    for k, (z0, z1) in enumerate([(0.2, 1.0), (1.2, 2.1)]):
        box(f"door_panel_{k}", area, W - 0.04, W - 0.02, DOOR["y0"] + 0.12, DOOR["y1"] - 0.12, z0, z1, m["wood"], edge=0.008)
    box("door_handle", area, W - 0.09, W - 0.04, DOOR["y0"] + 0.1, DOOR["y0"] + 0.22, 1.0, 1.04, m["brass"], edge=0.01)
    for name, a in [("s", (DOOR["y0"] - 0.08, DOOR["y0"])), ("n", (DOOR["y1"], DOOR["y1"] + 0.08))]:
        box(f"door_frame_{name}", area, W - 0.04, W, a[0], a[1], 0, DOOR["top"] + 0.08, m["wood"], edge=0.004)
    box("door_frame_top", area, W - 0.04, W, DOOR["y0"] - 0.08, DOOR["y1"] + 0.08, DOOR["top"], DOOR["top"] + 0.08, m["wood"], edge=0.004)
    collider("door", area, W - 0.05, W + 0.05, DOOR["y0"], DOOR["y1"], 0, DOOR["top"])

    # ---- Drafting table under the window (P02), with Sora's half-finished illustration.
    tx, ty = 3.0, 0.72
    for s in (-1, 1):
        box(f"drafting_trestle_{s}", area, tx + s * 0.55 - 0.03, tx + s * 0.55 + 0.03, ty - 0.3, ty + 0.3, 0.05, 0.86, m["wood"], edge=0.005)
        box(f"drafting_foot_{s}", area, tx + s * 0.55 - 0.04, tx + s * 0.55 + 0.04, ty - 0.34, ty + 0.34, 0, 0.05, m["wood"], edge=0.005)
    box("drafting_stretcher", area, tx - 0.55, tx + 0.55, ty - 0.02, ty + 0.02, 0.2, 0.26, m["wood"], edge=0.004)
    box("drafting_top", area, tx - 0.65, tx + 0.65, ty - 0.38, ty + 0.38, 0.88, 0.91, m["teak"], tilt=(-0.26, 0, 0), edge=0.004)
    box("drafting_ledge", area, tx - 0.62, tx + 0.62, ty + 0.36, ty + 0.4, 0.86, 0.9, m["wood"], edge=0.003)
    collider("drafting_table", area, tx - 0.65, tx + 0.65, ty - 0.4, ty + 0.4, 0, 1.0)
    # Wat Phnom for a Phnom Penh printer, inked up to the middle (seen from the stool, the top is south).
    illustration = box("interact_illustration", area, tx - 0.3, tx + 0.3, ty - 0.21, ty + 0.21, 0.912, 0.914, m["illustration"],
                       tilt=(-0.26, 0, 0), action="examine", beat="P02")
    picture_uvs(illustration, (-1, 0, 0), (0, -1, 0))
    box("t_square_blade", area, tx - 0.5, tx + 0.25, ty + 0.22, ty + 0.25, 0.892, 0.902, m["teak"], tilt=(-0.26, 0, 0))
    box("t_square_head", area, tx - 0.55, tx - 0.5, ty - 0.12, ty + 0.3, 0.9, 0.93, m["wood"], tilt=(-0.26, 0, 0))
    cylinder("ink_jar", area, tx + 0.45, ty + 0.38, 0.9, 0.97, 0.03, m["ink"])
    cylinder("brush_pot", area, tx + 0.55, ty + 0.38, 0.9, 1.0, 0.035, m["worn"])
    for k in range(4):
        b = cylinder(f"brush_{k}", area, tx + 0.55 + (k - 1.5) * 0.008, ty + 0.38, 0.98, 1.16, 0.004, m["wood"], verts=6)
        b.rotation_euler = (0.08 * (k - 1.5), 0.1 * (k - 1.5), 0)
    import_model(area, "chinese_stool", (tx, ty + 0.75, 0), 0, collide=False)
    # Green glass banker's lamp on a stand at the table's left: the key light Sora works by.
    lx, ly = tx - 0.95, ty + 0.05
    box("lamp_stand_top", area, lx - 0.2, lx + 0.2, ly - 0.2, ly + 0.2, 0.86, 0.9, m["wood"], edge=0.005)
    for ox in (-0.16, 0.16):
        for oy in (-0.16, 0.16):
            box(f"lamp_stand_leg_{ox}_{oy}", area, lx + ox - 0.02, lx + ox + 0.02, ly + oy - 0.02, ly + oy + 0.02, 0, 0.86, m["wood"])
    collider("lamp_stand", area, lx - 0.2, lx + 0.2, ly - 0.2, ly + 0.2, 0, 0.9)
    cylinder("desk_lamp_base", area, lx, ly, 0.9, 0.92, 0.07, m["brass"])
    cylinder("desk_lamp_stem", area, lx, ly, 0.92, 1.26, 0.008, m["brass"], verts=8)
    shade = cylinder("desk_lamp_shade", area, lx + 0.08, ly, 1.24, 1.32, 0.11, m["green_glass"], radius_top=0.05)
    shade.scale = (1.6, 1, 1)
    cylinder("desk_lamp_bulb", area, lx + 0.08, ly, 1.22, 1.25, 0.02, m["bulb"], verts=8)
    empty("marker_desk_lamp", area, (lx + 0.12, ly, 1.18))

    # ---- Writing desk on the west wall: drawer (letters and matchbox, P03/P04), lamp, sketchbook.
    dx0, dx1, dy0, dy1 = 0.02, 0.68, 1.75, 3.25
    box("desk_top", area, dx0, dx1, dy0, dy1, 0.74, 0.78, m["wood"], edge=0.006)
    for k, (y0, y1) in enumerate([(dy0 + 0.03, dy0 + 0.08), (dy1 - 0.08, dy1 - 0.03)]):
        for x0, x1 in [(dx0 + 0.03, dx0 + 0.08), (dx1 - 0.08, dx1 - 0.03)]:
            box(f"desk_leg_{k}_{x0:.2f}", area, x0, x1, y0, y1, 0, 0.74, m["wood"], edge=0.004)
    box("desk_apron", area, dx1 - 0.04, dx1 - 0.02, dy0 + 0.08, dy1 - 0.08, 0.6, 0.74, m["wood"], edge=0.003)
    collider("desk", area, dx0, dx1, dy0, dy1, 0, 0.78)
    drawer = box("interact_drawer", area, dx1 - 0.03, dx1 + 0.0, 2.25, 2.75, 0.62, 0.72, m["worn"], edge=0.004,
                 action="open", items="letters,matchbox", beat="P03")
    box("drawer_knob", area, dx1 + 0.0, dx1 + 0.025, 2.48, 2.52, 0.66, 0.68, m["brass"])
    # Yay Mey's letters, tied with red string, and the brass matchbox, inside the drawer.
    for k in range(5):
        box(f"letter_{k}", area, 0.35, 0.55, 2.4 + rng.uniform(-0.01, 0.01), 2.56, 0.64 + k * 0.006, 0.645 + k * 0.006, m["paper"])
    box("letters_string", area, 0.44, 0.46, 2.39, 2.57, 0.64, 0.675, plain("M_red_string", (0.5, 0.05, 0.04)))
    box("matchbox", area, 0.25, 0.3, 2.62, 2.66, 0.64, 0.655, m["brass"], edge=0.002)
    box("interact_sketchbook", area, 0.18, 0.42, 2.0, 2.32, 0.78, 0.805, m["book"], edge=0.004, action="pickup", item="sketchbook")
    for k in range(6):
        box(f"desk_paper_{k}", area, 0.12, 0.42, 2.38 + k * 0.004, 2.68, 0.78 + k * 0.002, 0.781 + k * 0.002, m["paper"],
            tilt=(0, 0, rng.uniform(-0.12, 0.12)))
    cylinder("desk_ink_bottle", area, 0.55, 1.95, 0.78, 0.86, 0.025, m["ink"])
    import_model(area, "standing_picture_frame_01", (0.18, 3.12, 0.78), 70, collide=False)
    import_model(area, "wicker_basket_01", (0.35, 1.45, 0), 0, collide=False)
    # Art Deco clock on a bracket above the desk: stops at 8:12 (P05).
    box("clock_bracket", area, 0.0, 0.26, 2.3, 2.7, 1.92, 1.95, m["wood"], edge=0.004)
    import_model(area, "mantel_clock_01", (0.13, 2.5, 1.95), 90, collide=False)
    empty("marker_clock", area, (0.15, 2.5, 2.1))
    # The gilt frame holds a print of Angkor Wat (its own canvas is a European landscape).
    import_model(area, "fancy_picture_frame_01", (0.02, 1.5, 1.7), 90, collide=False,
                 swap={"fancy_picture_frame_01_canvas": m["angkor"]})
    # Sora's studies pinned to the plaster, a little crooked.
    for k, (y, z, subject, turn) in enumerate([(2.95, 1.5, "lettering", 0.05), (3.35, 1.35, "ornament", -0.08), (2.0, 1.32, "palms", 0.03)]):
        sheet = box(f"pinned_drawing_{k}", area, 0.002, 0.004, y - 0.15, y + 0.15, z - 0.15, z + 0.15, m[subject], tilt=(turn, 0, 0))
        picture_uvs(sheet, (0, math.cos(turn), math.sin(turn)), (0, -math.sin(turn), math.cos(turn)))
        cylinder(f"pin_{k}", area, 0.006, y, z + 0.13, z + 0.135, 0.004, m["brass"], verts=6)
    for k, (x, z, subject, turn) in enumerate([(1.85, 1.55, "house", -0.04), (4.2, 1.6, "boats", 0.06)]):
        sheet = box(f"pinned_drawing_s_{k}", area, x - 0.14, x + 0.14, 0.002, 0.004, z - 0.14, z + 0.14, m[subject], tilt=(0, turn, 0))
        picture_uvs(sheet, (-math.cos(turn), 0, math.sin(turn)), (math.sin(turn), 0, math.cos(turn)))

    # ---- North wall: shelf with the candle and the satchel (P04), books; Chinese cabinet.
    sx0, sx1 = 2.2, 3.8
    box("shelf", area, sx0, sx1, D - 0.3, D, 1.3, 1.34, m["wood"], edge=0.004)
    for x in (sx0 + 0.1, sx1 - 0.1):
        box(f"shelf_bracket_{x:.1f}", area, x - 0.02, x + 0.02, D - 0.25, D, 1.12, 1.3, m["wood"])
    collider("shelf", area, sx0, sx1, D - 0.3, D, 1.1, 1.34)
    stick = import_model(area, "wooden_candlestick", (3.62, D - 0.18, 1.34), 0, collide=False)
    candle_top = top_of(stick)
    cylinder("shelf_candle_wax", area, 3.62, D - 0.18, candle_top - 0.008, candle_top + 0.07, 0.015, m["candle"], verts=32, radius_top=0.013)
    cylinder("shelf_candle_wick", area, 3.62, D - 0.18, candle_top + 0.07, candle_top + 0.081, 0.0015, m["iron"], verts=8)
    empty("light_flame_candle", area, (3.62, D - 0.18, candle_top + 0.091), radius=3.0, intensity=0.85)
    satchel = empty("interact_satchel", area, (2.55, D - 0.16, 1.34), action="pickup", item="satchel")
    for name, a in [("body", (-0.17, 0.17, -0.07, 0.07, 0, 0.25)), ("flap", (-0.175, 0.175, -0.075, 0.02, 0.12, 0.26))]:
        part = box(f"satchel_{name}", area, *a, m["leather"], edge=0.015)
        part.parent = satchel
    build_shelf_books(area, m)
    import_model(area, "chinese_cabinet", (0.75, D - 0.3, 0), 0)
    import_model(area, "vintage_oil_lamp", (0.75, D - 0.3, 1.21), 0, collide=False)
    # Over the bed: one of her own drawings, framed.
    box("bed_frame_picture", area, 4.55, 5.35, D - 0.03, D, 1.15, 1.75, m["wood"], edge=0.006)
    bed_picture = box("bed_picture", area, 4.62, 5.28, D - 0.035, D - 0.03, 1.22, 1.68, m["tonle_sap"])
    picture_uvs(bed_picture, (1, 0, 0), (0, 0, 1))
    import_model(area, "book_encyclopedia_set_01", (1.6, D - 0.25, 0), 15, collide=False)

    # ---- Iron bed in the north-east corner, linen, a krama, mosquito net tied above.
    import_model(area, "old_bed_frame", (4.95, D - 0.55, 0), 90)
    box("mattress", area, 4.0, 5.9, D - 0.98, D - 0.12, 0.42, 0.56, m["linen"], edge=0.05)
    box("pillow", area, 5.45, 5.85, D - 0.9, D - 0.2, 0.56, 0.66, m["linen"], edge=0.04)
    box("krama_folded", area, 4.15, 4.6, D - 0.95, D - 0.15, 0.56, 0.58, m["krama"], edge=0.008)
    # Tied up above the bed: a gathered bundle of net hanging from a hook.
    build_gathered_net(area, m)
    import_model(area, "vintage_suitcase", (3.75, D - 0.35, 0), 90, collide=False)

    # ---- Tea corner by the window: armchair, side table, jug and pot; rug; plant.
    import_model(area, "chinese_armchair", (4.75, 1.35, 0), 205)
    import_model(area, "WoodenTable_02", (4.05, 0.85, 0), 0)
    import_model(area, "jug_01", (4.0, 0.82, 0.42), 30, collide=False)
    import_model(area, "pot_enamel_01", (4.12, 0.92, 0.42), 0, collide=False)
    cylinder("teacup", area, 3.95, 0.95, 0.42, 0.47, 0.03, m["candle"], radius_top=0.035)
    cylinder("saucer", area, 3.95, 0.95, 0.415, 0.42, 0.055, m["candle"])
    cloth("krama_on_chair", area, 1.05, 1.65, 0.25, 0.75, 4.95, m["krama"], folds=3, depth=0.02, segments=(16, 8), axis="y")
    box("rug", area, 2.0, 4.2, 1.7, 3.5, 0.0, 0.012, m["rug"], edge=0.003)
    import_model(area, "potted_plant_02", (1.65, 0.35, 0), 0)

    # ---- By the door: console table, brass wall telephone (P06), coat hook with the lantern (P04).
    import_model(area, "chinese_console_table", (W - 0.2, 0.95, 0), 90)
    # A printed Khmer alphabet chart, framed, above the console table.
    box("alphabet_frame", area, W - 0.03, W, 0.62, 1.1, 1.12, 1.78, m["wood"], edge=0.004)
    chart = box("alphabet_print", area, W - 0.036, W - 0.03, 0.65, 1.07, 1.15, 1.75, m["alphabet"])
    picture_uvs(chart, (0, -1, 0), (0, 0, 1))
    import_model(area, "brass_vase_01", (W - 0.2, 0.45, 0.66), 0, collide=False)
    import_model(area, "ceramic_vase_02", (W - 0.2, 1.3, 0.66), 0, collide=False)
    phone = empty("interact_telephone", area, (W - 0.02, 3.55, 1.45), action="use", beat="P06")
    parts = [
        ("backboard", (-0.03, 0.0, -0.13, 0.13, -0.2, 0.2), m["wood"]),
        ("box", (-0.1, -0.03, -0.1, 0.1, -0.12, 0.12), m["wood"]),
        ("mouth_arm", (-0.18, -0.1, -0.01, 0.01, 0.0, 0.02), m["brass"]),
        ("hook", (-0.13, -0.1, 0.1, 0.12, 0.02, 0.1), m["brass"]),
    ]
    for name, a, mat in parts:
        part = box(f"telephone_{name}", area, *a, mat, edge=0.006)
        part.parent = phone
    for k, y in enumerate((-0.05, 0.05)):
        bell = cylinder(f"telephone_bell_{k}", area, -0.11, y, 0.12, 0.15, 0.04, m["brass"], verts=16)
        bell.rotation_euler = (0, math.pi / 2, 0)
        bell.parent = phone
    mouth = cylinder("telephone_mouthpiece", area, -0.2, 0.0, -0.02, 0.06, 0.03, m["iron"], radius_top=0.045)
    mouth.rotation_euler = (0, math.pi / 2, 0)
    mouth.parent = phone
    ear = cylinder("telephone_earpiece", area, -0.12, 0.13, -0.08, 0.06, 0.02, m["iron"], verts=12)
    ear.parent = phone
    lantern = import_model(area, "Lantern_01", (W - 0.18, 1.575, 1.5), 0, name="interact_lamp", collide=False, action="pickup", item="lamp")
    # Locate the bail's actual highest vertices, rather than guessing from the model origin.
    bail = np.array([tuple(o.matrix_world @ v.co) for o in lantern.children_recursive if o.type == "MESH" for v in o.data.vertices])
    top = float(bail[:, 2].max())
    contact = bail[bail[:, 2] > top - 0.003].mean(axis=0)
    hx, hy = float(contact[0]), float(contact[1])
    box("coat_hook_backplate", area, W - 0.016, W + 0.001, hy - 0.032, hy + 0.032, top - 0.035, top + 0.115, m["brass"], edge=0.009)
    path = [(W - 0.018, hy, top + 0.064), (W - 0.085, hy, top + 0.064), (hx - 0.022, hy, top + 0.049)]
    path += [(hx + math.cos(a) * 0.022, hy, top + 0.016 + math.sin(a) * 0.022) for a in np.linspace(math.pi, 2 * math.pi, 13)]
    path.append((hx + 0.022, hy, top + 0.042))
    tube("coat_hook_curved_arm", area, path, 0.006, m["brass"], sides=12)
    for k, z in enumerate((top - 0.019, top + 0.097)):
        screw = cylinder(f"coat_hook_screw_{k}", area, W - 0.018, hy, z - 0.002, z + 0.002, 0.006, m["iron"], verts=16)
        screw.rotation_euler.y = math.pi / 2

    # ---- 1930s ceiling fan (brass and dark wood), still tonight.
    cylinder("fan_rod", area, 3.0, 2.5, H - 0.5, H - 0.2, 0.012, m["brass"], verts=8)
    cylinder("fan_motor", area, 3.0, 2.5, H - 0.62, H - 0.5, 0.11, m["brass"])
    for k in range(4):
        blade = box(f"fan_blade_{k}", area, 3.12, 3.72, 2.44, 2.56, H - 0.58, H - 0.565, m["wood"], edge=0.004)
        blade.rotation_euler = (0, 0, k * math.pi / 2 + 0.3)
        # rotate around the fan's axis
        blade.location = (3.0 + math.cos(k * math.pi / 2 + 0.3) * 0.42, 2.5 + math.sin(k * math.pi / 2 + 0.3) * 0.42, H - 0.57)

    dress_working_studio(area, m, tx, ty)

    # Sora starts on the stool at the drafting table, facing the window (south).
    empty("spawn_player", area, (tx, ty + 0.95, 0), (0, 0, math.pi), checkpoint="CP0")

    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"Saved {BLEND}")


# ------------------------------------------------------------------- the working studio

def build_gathered_net(area, m):
    """An open, folded gauze bundle tied above the bed, with no solid end caps."""
    n = 512
    yy, xx = np.mgrid[:n, :n]
    thread = ((xx % 8) < 1) | ((yy % 8) < 1)
    rgba = np.empty((n, n, 4), dtype=np.float32)
    rgba[:, :, :3] = (0.80, 0.77, 0.66)
    rgba[:, :, 3] = np.where(thread, 0.70, 0.045)
    image = bpy.data.images.new("T_studio_net_weave_BC", width=n, height=n, alpha=True)
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = os.path.join(TEXTURES, "T_studio_net_weave_BC.png")
    image.file_format = "PNG"; image.save()
    mat = m["net"]; mat.use_backface_culling = False
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    tex = nodes.new("ShaderNodeTexImage"); tex.image = image
    bsdf = nodes.get("Principled BSDF")
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.95
    rows, sides = 48, 96
    vertices, faces, uvs = [], [], []
    for j in range(rows + 1):
        t = j / rows
        # Gather at the ceiling, loosen into folds, cinch at the tie, then drape below it.
        radius = float(np.interp(t, [0, .10, .46, .66, .76, 1], [.018, .10, .16, .055, .10, .23]))
        for i in range(sides + 1):
            a = i / sides * math.tau
            pleat = 1 + .19 * math.sin(a * 13 + t * 2) + .07 * math.sin(a * 23 - t * 3)
            r = radius * pleat
            vertices.append((4.95 + .055 * math.sin(t * 2.5) + math.cos(a) * r,
                             4.45 + .045 * t + math.sin(a) * r * .72,
                             3.06 - t * 1.11 + .028 * t**5 * math.sin(a * 7)))
    for j in range(rows):
        for i in range(sides):
            a = j * (sides + 1) + i
            faces.append((a, a + sides + 1, a + sides + 2, a + 1))
            uvs += [(i / sides * 4, j / rows * 8), (i / sides * 4, (j + 1) / rows * 8),
                    ((i + 1) / sides * 4, (j + 1) / rows * 8), ((i + 1) / sides * 4, j / rows * 8)]
    mesh_object("mosquito_net_folded_gauze", area, vertices, faces, mat, uvs=uvs, smooth=True)
    # A stitched hem follows the irregular open edge rather than a flat cylinder cap.
    hem = vertices[-(sides + 1):]
    tube("mosquito_net_stitched_hem", area, hem, .002, m["linen"], sides=5)
    seam = [vertices[j * (sides + 1)] for j in range(rows + 1)]
    tube("mosquito_net_edge_seam", area, seam, .0016, m["linen"], sides=5)
    tie_z = 3.06 - .66 * 1.11
    tie_x = 4.95 + .055 * math.sin(.66 * 2.5)
    for dz in [-.008, .008]:
        points = [(tie_x + math.cos(a) * .063, 4.48 + math.sin(a) * .046, tie_z + dz) for a in np.linspace(0, math.tau, 49)]
        tube("mosquito_net_cotton_tie", area, points, .005, m["krama"], sides=6)
    tube("mosquito_net_tie_ends", area, [(tie_x, 4.428, tie_z), (tie_x + .055, 4.41, tie_z - .045), (tie_x + .04, 4.405, tie_z - .13)], .008, m["krama"], sides=6)
    tube("mosquito_net_hanging_loop", area, [(4.95, 4.45, 3.055), (4.94, 4.45, 3.13), (4.96, 4.45, 3.16), (4.98, 4.45, 3.13), (4.95, 4.45, 3.055)], .003, m["linen"], sides=6)
    tube("mosquito_net_ceiling_hook", area, [(4.95, 4.45, 3.2), (4.95, 4.45, 3.15), (4.96, 4.45, 3.145), (4.97, 4.45, 3.155)], .004, m["brass"], sides=8)

def build_shelf_books(area, m):
    """Individual clothbound study volumes, clear of the satchel and candle."""
    covers = [(0.12, 0.20, 0.17), (0.24, 0.11, 0.07), (0.10, 0.15, 0.23), (0.30, 0.24, 0.14)]
    titles = ["STUDIES", "BOTANY", "FIGURES", "PERSPECTIVE", "KHMER", "ORNAMENT", "INK", "LETTERS", "PLANTS"]
    widths = [0.055, 0.059, 0.048, 0.064, 0.051, 0.058, 0.046, 0.060, 0.052]
    heights = [0.264, 0.285, 0.248, 0.308, 0.277, 0.292, 0.255, 0.281, 0.268]
    gilt = plain("M_studio_book_stamping", (0.50, 0.37, 0.18), rough=0.85)
    x = 2.84
    def lettering(name, body, at, size):
        text = bpy.data.curves.new(name, "FONT")
        text.body = body; text.size = size; text.align_x = "CENTER"; text.align_y = "CENTER"
        text.space_line = 0.9; text.extrude = 0.0001
        obj = bpy.data.objects.new(name, text); area.objects.link(obj)
        obj.location = at; obj.rotation_euler.x = math.pi / 2
        text.materials.append(gilt)
        bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
    for i, (width, height, title) in enumerate(zip(widths, heights, titles)):
        cover = library_material("rough_linen", f"M_studio_book_cloth_{i}", tint=covers[i % len(covers)], tile=0.16)
        front = 4.724 + (i % 3) * 0.009; back = 4.954 - (i % 2) * 0.015
        bottom = 1.341; top = bottom + height
        box(f"shelf_book_pages_{i}", area, x + 0.004, x + width - 0.004, front + 0.009, back - 0.004, bottom + 0.006, top - 0.006, m["paper"], edge=0.001)
        for side in (x, x + width - 0.003):
            box(f"shelf_book_board_{i}", area, side, side + 0.003, front, back, bottom, top, cover, edge=0.001)
        box(f"shelf_book_spine_{i}", area, x, x + width, front - 0.003, front + 0.007, bottom, top, cover, edge=0.003)
        for z in (bottom + 0.022, top - 0.024):
            box(f"shelf_book_binding_{i}", area, x + 0.004, x + width - 0.004, front - 0.004, front - 0.003, z, z + 0.002, gilt)
        lettering(f"shelf_book_title_{i}", "\n".join(title), (x + width / 2, front - 0.0045, bottom + height * 0.57), 0.010)
        lettering(f"shelf_book_volume_{i}", str(i + 1), (x + width / 2, front - 0.0045, bottom + 0.048), 0.013)
        x += width + 0.004


def crumpled_sheet(name, coll, x, y, radius, mat):
    """A sheet balled up and thrown aside: a lumpy low sphere resting on the floor."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=(x, y, radius * 0.8))
    obj = bpy.context.active_object
    obj.name = name
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    for v in obj.data.vertices:
        v.co *= rng.uniform(0.7, 1.15)
    obj.scale = (1.0, rng.uniform(0.8, 1.0), rng.uniform(0.7, 0.85))
    obj.rotation_euler = (0, 0, rng.uniform(0, math.tau))
    obj.data.materials.append(mat)
    world_uvs(obj)
    return obj


def hanging_sheet(name, coll, centre, along, width, height, mat):
    """A drawing clipped to the drying line by its top edge, facing into the room."""
    angle = math.atan2(along[1], along[0])
    x, y, z = centre
    sheet = box(name, coll, x - width / 2, x + width / 2, y - 0.001, y + 0.001, z - height, z, mat, tilt=(0, 0, angle))
    normal = (-along[1], along[0])
    picture_uvs(sheet, (-normal[1], normal[0], 0), (0, 0, 1))
    return sheet


def dress_working_studio(area, m, tx, ty):
    """Art Bible pillar 'grounded and lived-in': an illustrator works here every day.
    Drawings drying on a line, boards against the wall, rolls of paper, sheets she
    gave up on. Nothing here has a collider, and nothing stands on the route from
    the stool to the desk, the shelf, the hook and the door."""
    newsprint = plain("M_newsprint", (0.62, 0.6, 0.55), rough=0.95)
    string = plain("M_string", (0.55, 0.5, 0.42), rough=0.9)
    umbrella = plain("M_umbrella_cloth", (0.03, 0.03, 0.035), rough=0.75)
    aged = plain("M_aged_paper", (0.66, 0.6, 0.48), rough=0.95)

    # A drying line across the south-west corner, high above head height, with three
    # drawings pegged to it; lightning through the window throws them into silhouette.
    a, b = (0.0, 1.0, 2.32), (1.75, 0.0, 2.32)
    line = sag(a, b, 0.07, n=12)
    tube("drying_line", area, line, 0.002, string, sides=4)
    along = (b[0] - a[0], b[1] - a[1])
    length = math.hypot(*along)
    along = (along[0] / length, along[1] / length)
    for k, (t, subject) in enumerate(((0.26, "palms"), (0.52, "lettering"), (0.78, "ornament"))):
        p = line[round(t * (len(line) - 1))]
        hanging_sheet(f"drying_sheet_{k}", area, (p[0], p[1], p[2] - 0.005), along, 0.26, 0.34, m[subject])
        for s in (-1, 1):
            cx, cy = p[0] + s * 0.1 * along[0], p[1] + s * 0.1 * along[1]
            box(f"drying_peg_{k}_{s}", area, cx - 0.006, cx + 0.006, cy - 0.004, cy + 0.004, p[2] - 0.035, p[2] + 0.01,
                m["worn"], tilt=(0, 0, math.atan2(along[1], along[0])))

    # Stretched canvases leaning on the west wall in the corner: two show their raw
    # backs and stretcher frames, one faces out with a study on it.
    canvas_back = plain("M_canvas_back", (0.46, 0.4, 0.31), rough=0.95)
    for k, (y, w, h, face) in enumerate(((0.32, 0.5, 0.7, False), (0.62, 0.6, 0.8, True), (0.95, 0.45, 0.6, False))):
        lean = -0.13
        cx = 0.03 + 0.01 * k + h / 2 * math.sin(-lean)
        box(f"canvas_board_{k}", area, cx - 0.004, cx + 0.004, y - w / 2, y + w / 2, 0.0, h, canvas_back, tilt=(0, lean, 0))
        if face:
            art = box(f"canvas_study_{k}", area, cx + 0.005, cx + 0.007, y - w / 2 + 0.03, y + w / 2 - 0.03, 0.03, h - 0.03,
                      m["boats"], tilt=(0, lean, 0))
            picture_uvs(art, (0, 1, 0), (math.sin(lean), 0, math.cos(lean)))
            continue
        # Stretcher frame on the back: four bars round the edge and a cross brace.
        bars = [(y - w / 2, y + w / 2, 0.0, 0.035), (y - w / 2, y + w / 2, h - 0.035, h),
                (y - w / 2, y - w / 2 + 0.035, 0.0, h), (y + w / 2 - 0.035, y + w / 2, 0.0, h),
                (y - w / 2, y + w / 2, h / 2 - 0.0175, h / 2 + 0.0175)]
        for j, (y0, y1, z0, z1) in enumerate(bars):
            bar = box(f"canvas_stretcher_{k}_{j}", area, cx + 0.004, cx + 0.022, y0, y1, z0, z1, m["worn"])
            # Lean each bar with the canvas, about the canvas's own centre.
            dz = (z0 + z1) / 2 - h / 2
            bar.location = (cx + 0.013 + dz * math.sin(lean), (y0 + y1) / 2, h / 2 + dz * math.cos(lean))
            bar.rotation_euler = (0, lean, 0)

    # Rolled paper standing in the wicker basket by the desk.
    for k in range(6):
        ang = k * math.tau / 6 + rng.uniform(-0.3, 0.3)
        r = 0.05 + 0.02 * (k % 2)
        x, y = 0.35 + r * math.cos(ang), 1.45 + r * math.sin(ang)
        roll = cylinder(f"paper_roll_{k}", area, x, y, 0.04, 0.04 + rng.uniform(0.6, 0.85), rng.uniform(0.018, 0.028),
                        aged if k % 3 else newsprint, verts=10)
        roll.rotation_euler = (rng.uniform(-0.12, 0.12) + 0.1 * math.sin(ang), rng.uniform(-0.12, 0.12) - 0.1 * math.cos(ang), 0)

    # Sheets she gave up on, balled and thrown under the drafting table.
    for k, (x, y) in enumerate(((tx - 0.35, ty - 0.15), (tx - 0.1, ty + 0.25), (tx + 0.62, ty + 0.35),
                                (tx - 0.75, ty + 0.4), (tx + 0.45, ty + 0.55))):
        crumpled_sheet(f"crumpled_sheet_{k}", area, x, y, rng.uniform(0.035, 0.05), m["paper"])

    # A tied stack of fresh paper on the floor under the drafting table.
    px, py = tx + 0.25, ty - 0.1
    for k in range(14):
        jitter = rng.uniform(-0.008, 0.008)
        box(f"paper_stack_{k}", area, px - 0.21 + jitter, px + 0.21 + jitter, py - 0.15, py + 0.15, k * 0.0035, k * 0.0035 + 0.0025,
            m["paper"], tilt=(0, 0, rng.uniform(-0.03, 0.03)))
    box("paper_stack_string_a", area, px - 0.215, px + 0.215, py - 0.006, py + 0.006, 0.0, 0.051, string)
    box("paper_stack_string_b", area, px - 0.006, px + 0.006, py - 0.155, py + 0.155, 0.0, 0.052, string)

    # Pinned studies spreading along the walls she faces from the desk and the bed.
    for k, (y, z, subject, turn) in enumerate(((4.15, 1.75, "house", 0.04), (4.5, 1.95, "boats", -0.05), (3.85, 1.95, "palms", -0.02))):
        sheet = box(f"pinned_drawing_n_{k}", area, 0.002, 0.004, y - 0.13, y + 0.13, z - 0.17, z + 0.17, m[subject], tilt=(turn, 0, 0))
        picture_uvs(sheet, (0, math.cos(turn), math.sin(turn)), (0, -math.sin(turn), math.cos(turn)))
        cylinder(f"pin_n_{k}", area, 0.006, y, z + 0.15, z + 0.155, 0.004, m["brass"], verts=6)
    for k, (x, z, subject, turn) in enumerate(((1.55, 1.65, "lettering", 0.05), (1.85, 1.95, "ornament", -0.04))):
        sheet = box(f"pinned_drawing_nw_{k}", area, x - 0.14, x + 0.14, D - 0.004, D - 0.002, z - 0.18, z + 0.18, m[subject],
                    tilt=(0, turn, 0))
        picture_uvs(sheet, (math.cos(turn), 0, -math.sin(turn)), (math.sin(turn), 0, math.cos(turn)))
        cylinder(f"pin_nw_{k}", area, x, D - 0.006, z + 0.16, z + 0.165, 0.004, m["brass"], verts=6)

    # A stack of books at the back of the desk, the top one open-faced down.
    for k, (w, d, h, mat) in enumerate(((0.2, 0.28, 0.04, m["book"]), (0.18, 0.25, 0.035, m["leather"]), (0.16, 0.23, 0.03, m["book"]))):
        z = 0.78 + sum(s[2] for s in ((0.2, 0.28, 0.04), (0.18, 0.25, 0.035), (0.16, 0.23, 0.03))[:k])
        box(f"desk_book_{k}", area, 0.3 - w / 2, 0.3 + w / 2, 2.88 - d / 2, 2.88 + d / 2, z, z + h, mat,
            tilt=(0, 0, rng.uniform(-0.15, 0.15)), edge=0.004)

    # Yesterday's newspapers, folded, on the floor by the armchair.
    for k in range(9):
        box(f"newspaper_{k}", area, 5.15, 5.5, 0.35, 0.6, k * 0.004, k * 0.004 + 0.003, newsprint,
            tilt=(0, 0, rng.uniform(-0.2, 0.2)))

    # A black umbrella leaning in the corner by the console table, and slippers by the bed.
    shaft = cylinder("umbrella_folded", area, W - 0.12, 0.12, 0.08, 0.85, 0.045, umbrella, verts=8, radius_top=0.012)
    shaft.rotation_euler = (0.12, -0.1, 0)
    tube("umbrella_handle", area, [(W - 0.08, 0.16, 0.86), (W - 0.07, 0.17, 0.95), (W - 0.1, 0.19, 0.99)], 0.008, m["wood"], sides=6)
    for k, x in enumerate((4.25, 4.42)):
        box(f"slipper_{k}", area, x - 0.05, x + 0.05, D - 1.3, D - 1.06, 0.0, 0.025, m["leather"],
            tilt=(0, 0, rng.uniform(-0.2, 0.2)), edge=0.01)


build()
