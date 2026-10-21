"""Builds the Episode 1 prologue greybox: Sora's studio in Phnom Penh.

Episode 1 Beat Sheet, section 4.1: a single room 6 × 5 m, ceiling 3.2 m, third
floor; one door (east), one tall window (south); drafting table under the
window, desk with drawer on the west wall, shelf with candle and satchel
(north), brass wall telephone by the door, wall clock above the desk, coat hook
with the hurricane lamp by the door.

Run once to make the starting .blend (from the repository root):
    blender -b --factory-startup -P tools/greybox/ep1_area_studio.py
then edit art-source/blender/ep1/ep1_area_studio.blend by hand in Blender;
`npm run export && npm run assets` brings changes into the game.

Blender axes: X east, Y north, Z up; metres. Names follow the Technical
Design Document, section 7.1 (col_, interact_, spawn_, light_flame_, marker_).
"""

import os

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BLEND = os.path.join(ROOT, "art-source", "blender", "ep1", "ep1_area_studio.blend")

W, D, H = 6.0, 5.0, 3.2  # room: X east, Y north, Z up
WALL = 0.15
DOOR = {"y0": 2.0, "y1": 3.0, "top": 2.2}  # east wall
WINDOW = {"x0": 2.3, "x1": 3.7, "bottom": 0.8, "top": 2.9}  # south wall


def material(name, colour, rough=0.85):
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def box(name, coll, x0, x1, y0, y1, z0, z1, mat=None, tilt=0.0, **props):
    """Box from min/max corners, its origin at its centre (so `tilt`, about X, turns it
    in place); `props` become glTF extras."""
    mesh = bpy.data.meshes.new(name)
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    verts = [(x - cx, y - cy, z - cz) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = (cx, cy, cz)
    obj.rotation_euler = (tilt, 0, 0)
    coll.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
    for k, v in props.items():
        obj[k] = v
    return obj


def solid(name, coll, x0, x1, y0, y1, z0, z1, mat, surface="teak", **props):
    """A visible box and its collider."""
    obj = box(name, coll, x0, x1, y0, y1, z0, z1, mat, **props)
    box(f"col_{name}", coll, x0, x1, y0, y1, z0, z1, surface=surface)
    return obj


def empty(name, coll, location, **props):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = "PLAIN_AXES"
    coll.objects.link(obj)
    for k, v in props.items():
        obj[k] = v
    return obj


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    area = bpy.data.collections.new("ep1_area_studio")
    bpy.context.scene.collection.children.link(area)

    m = {
        "floor": material("M_grey_floor", (0.30, 0.26, 0.22)),
        "wall": material("M_grey_wall", (0.55, 0.53, 0.48)),
        "ceiling": material("M_grey_ceiling", (0.45, 0.44, 0.40)),
        "wood": material("M_grey_wood", (0.22, 0.15, 0.10)),
        "paper": material("M_grey_paper", (0.85, 0.82, 0.74)),
        "brass": material("M_grey_brass", (0.55, 0.42, 0.18), rough=0.4),
        "dark": material("M_grey_dark", (0.08, 0.08, 0.08)),
        "glass": material("M_grey_window", (0.10, 0.13, 0.18), rough=0.1),
        "green": material("M_grey_lampshade", (0.10, 0.35, 0.18), rough=0.3),
    }

    # Shell: floor, ceiling, four walls with a door gap (east) and a window gap (south).
    solid("floor", area, 0, W, 0, D, -0.1, 0, m["floor"], surface="teak")
    box("ceiling", area, 0, W, 0, D, H, H + 0.1, m["ceiling"])
    solid("wall_west", area, -WALL, 0, 0, D, 0, H, m["wall"])
    solid("wall_north", area, -WALL, W + WALL, D, D + WALL, 0, H, m["wall"])
    solid("wall_east_south", area, W, W + WALL, 0, DOOR["y0"], 0, H, m["wall"])
    solid("wall_east_north", area, W, W + WALL, DOOR["y1"], D, 0, H, m["wall"])
    box("wall_east_lintel", area, W, W + WALL, DOOR["y0"], DOOR["y1"], DOOR["top"], H, m["wall"])
    solid("wall_south_west", area, -WALL, WINDOW["x0"], -WALL, 0, 0, H, m["wall"])
    solid("wall_south_east", area, WINDOW["x1"], W + WALL, -WALL, 0, 0, H, m["wall"])
    solid("wall_south_sill", area, WINDOW["x0"], WINDOW["x1"], -WALL, 0, 0, WINDOW["bottom"], m["wall"])
    box("wall_south_head", area, WINDOW["x0"], WINDOW["x1"], -WALL, 0, WINDOW["top"], H, m["wall"])
    # Window: dark glass with a cross frame; lightning flashes behind it.
    box("window_glass", area, WINDOW["x0"], WINDOW["x1"], -0.09, -0.07, WINDOW["bottom"], WINDOW["top"], m["glass"])
    xm = (WINDOW["x0"] + WINDOW["x1"]) / 2
    zm = (WINDOW["bottom"] + WINDOW["top"]) / 2 + 0.2
    box("window_frame_v", area, xm - 0.03, xm + 0.03, -0.07, -0.03, WINDOW["bottom"], WINDOW["top"], m["wood"])
    box("window_frame_h", area, WINDOW["x0"], WINDOW["x1"], -0.07, -0.03, zm - 0.03, zm + 0.03, m["wood"])
    empty("marker_lightning", area, (xm, -1.5, 2.4))

    # Door: closed until Sora has her kit (P04), then she leaves through it (P07).
    door = box("interact_door", area, W + 0.01, W + 0.06, DOOR["y0"] + 0.02, DOOR["y1"] - 0.02, 0, DOOR["top"] - 0.02,
               m["wood"], action="open")
    door["requires"] = "ep1.kit.collected"
    box("col_door", area, W - 0.02, W + 0.06, DOOR["y0"], DOOR["y1"], 0, DOOR["top"], surface="teak")

    # Drafting table under the window, sloped top, with the half-finished illustration (P02).
    tx, ty = 3.0, 0.75
    for dx in (-0.6, 0.6):
        for dy in (-0.3, 0.3):
            box(f"drafting_leg_{dx}_{dy}", area, tx + dx - 0.03, tx + dx + 0.03, ty + dy - 0.03, ty + dy + 0.03, 0, 0.9,
                m["wood"])
    # Sloped towards Sora (she sits on the north side): the far, south edge is higher.
    box("drafting_top", area, tx - 0.7, tx + 0.7, ty - 0.4, ty + 0.4, 0.9, 0.93, m["wood"], tilt=-0.25)
    box("col_drafting_table", area, tx - 0.7, tx + 0.7, ty - 0.4, ty + 0.4, 0, 1.0, surface="teak")
    box("interact_illustration", area, tx - 0.32, tx + 0.32, ty - 0.22, ty + 0.22, 0.935, 0.95,
        m["paper"], tilt=-0.25, action="examine", beat="P02")
    solid("stool", area, tx - 0.2, tx + 0.2, ty + 0.55, ty + 0.95, 0, 0.62, m["wood"])

    # Desk on the west wall with its drawer (letters P03, matchbox P04), sketchbook on top.
    solid("desk", area, 0, 0.7, 1.7, 3.3, 0.72, 0.77, m["wood"])
    for y in (1.75, 3.25):
        box(f"desk_side_{y}", area, 0.02, 0.68, y - 0.04, y + 0.04, 0, 0.72, m["wood"])
    box("col_desk_body", area, 0, 0.7, 1.7, 3.3, 0, 0.72, surface="teak")
    box("interact_drawer", area, 0.62, 0.72, 2.2, 2.8, 0.56, 0.7, m["wood"], action="open", items="letters,matchbox")
    box("interact_sketchbook", area, 0.2, 0.42, 2.9, 3.2, 0.77, 0.8, m["dark"], action="pickup", item="sketchbook")
    box("desk_ink_bottle", area, 0.3, 0.36, 1.95, 2.01, 0.77, 0.85, m["dark"])
    # Green glass desk lamp: the key light.
    box("desk_lamp_stem", area, 0.25, 0.29, 2.43, 2.47, 0.77, 1.15, m["brass"])
    box("desk_lamp_shade", area, 0.12, 0.42, 2.35, 2.55, 1.15, 1.25, m["green"])
    empty("marker_desk_lamp", area, (0.3, 2.45, 1.12))

    # Wall clock above the desk: stops at 8:12 (P05).
    box("clock_face", area, 0.0, 0.04, 2.3, 2.7, 2.05, 2.45, m["paper"])
    empty("marker_clock", area, (0.05, 2.5, 2.25))

    # Shelf on the north wall with the candle and the satchel (P04).
    solid("shelf", area, 1.2, 2.8, D - 0.35, D, 1.3, 1.34, m["wood"])
    box("shelf_lower", area, 1.2, 2.8, D - 0.35, D, 0.6, 0.64, m["wood"])
    box("interact_satchel", area, 1.4, 1.8, D - 0.32, D - 0.1, 1.34, 1.62, m["wood"], action="pickup", item="satchel")
    box("candle", area, 2.3, 2.36, D - 0.2, D - 0.14, 1.34, 1.5, m["paper"])
    empty("light_flame_candle", area, (2.33, D - 0.17, 1.53), radius=3.0, intensity=2.0)
    for i in range(5):
        box(f"shelf_book_{i}", area, 1.85 + i * 0.08, 1.92 + i * 0.08, D - 0.3, D - 0.08, 0.64, 0.92, m["dark"])

    # Brass wall telephone by the door (P06).
    box("interact_telephone", area, W - 0.08, W, 3.35, 3.6, 1.35, 1.7, m["brass"], action="use", beat="P06")

    # Coat hook by the door with the hurricane lamp (P04).
    box("coat_hook", area, W - 0.06, W, 1.6, 1.68, 1.75, 1.8, m["brass"])
    box("interact_lamp", area, W - 0.3, W - 0.08, 1.52, 1.76, 1.35, 1.72, m["brass"], action="pickup", item="lamp")

    # A bed corner and a rug, so the room reads as lived in.
    solid("bed", area, 3.9, 5.9, 3.6, D, 0, 0.5, m["paper"])
    box("rug", area, 2.0, 4.0, 1.6, 3.4, 0, 0.01, m["green"])

    # Sora starts at the drafting table, facing the window (south).
    spawn = empty("spawn_player", area, (3.0, 1.75, 0), checkpoint="CP0")
    spawn.rotation_euler = (0, 0, 3.14159)

    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"Saved {BLEND}")


build()
