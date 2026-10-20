"""Builds the Spike S3 test room in Blender and saves it as a .blend file.

A corner of a stilt house that uses every convention the pipeline must carry
(Technical Design Document, section 7): textured PBR materials (BC, N, ORM),
an untextured material, `col_` collision boxes including a stair ramp, a
`ladder_` volume with a `facing` property, a `spawn_` point, an
`interact_` prop and `patrol_bot_NN` route nodes.

Run (from the repository root):
    blender -b --factory-startup -P tools/s3/make_test_room.py

Writes art-source/blender/spikes/s3_test_room.blend and its textures in
art-source/textures/s3/. Both are generated, so they are not committed.
Blender axes: X right, Y forward (into the house), Z up; metres.
"""

import math
import os

import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BLEND = os.path.join(ROOT, "art-source", "blender", "spikes", "s3_test_room.blend")
TEXTURES = os.path.join(ROOT, "art-source", "textures", "s3")

DECK_TOP = 2.0
GRANARY_TOP = 2.4
rng = np.random.default_rng(1932)


# ---------------------------------------------------------------- textures


def value_noise(size, cells, octaves=4):
    """Smooth tiling noise in 0..1, built from upsampled random grids."""
    out = np.zeros((size, size))
    amplitude, total = 1.0, 0.0
    for o in range(octaves):
        n = cells * 2**o
        grid = rng.random((n, n))
        # Bilinear upsample with wrap-around so the texture tiles.
        coords = np.arange(size) * n / size
        i0 = np.floor(coords).astype(int)
        t = coords - i0
        t = t * t * (3 - 2 * t)
        i1 = (i0 + 1) % n
        rows = grid[i0][:, i0] * (1 - t)[None, :] + grid[i0][:, i1] * t[None, :]
        rows1 = grid[i1][:, i0] * (1 - t)[None, :] + grid[i1][:, i1] * t[None, :]
        out += amplitude * (rows * (1 - t)[:, None] + rows1 * t[:, None])
        total += amplitude
        amplitude *= 0.5
    return out / total


def normal_from_height(height, strength):
    """Tangent-space normal map (OpenGL / glTF convention) from a height field."""
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    n = np.stack([-dx, -dy, np.ones_like(height)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def save_image(name, rgb, non_color):
    """Writes an RGB array (rows from the top) to a PNG and returns the Blender image."""
    size = rgb.shape[0]
    image = bpy.data.images.new(name, size, size, alpha=False)
    rgba = np.concatenate([rgb, np.ones((size, size, 1))], axis=-1)
    # Blender stores pixels bottom row first.
    image.pixels.foreach_set(np.flipud(rgba).astype(np.float32).ravel())
    image.filepath_raw = os.path.join(TEXTURES, f"{name}.png")
    image.file_format = "PNG"
    image.save()
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    return image


def plank_maps(size, planks, gap, base, grain_scale):
    """Planks along U with dark gaps: returns BC, height, AO and roughness."""
    v = (np.arange(size) / size)[:, None] * planks
    in_plank = np.abs((v % 1) - 0.5) < 0.5 - gap / 2
    index = np.floor(v).astype(int)
    tint = rng.uniform(0.82, 1.12, planks)[index % planks]
    grain = value_noise(size, grain_scale)
    # Whole cycles per tile so the texture repeats without a seam.
    streaks = 0.5 + 0.5 * np.sin(
        (np.arange(size)[None, :] / size) * 2 * math.pi * 6 + grain * 12 + index * 3.7
    )
    shade = (0.75 + 0.25 * streaks) * tint * (0.85 + 0.3 * grain)
    colour = np.clip(np.array(base)[None, None, :] * shade[..., None], 0, 1)
    colour[~np.broadcast_to(in_plank, (size, size))] *= 0.18
    height = np.where(in_plank, 1.0, 0.0) * np.ones((1, size)) + grain * 0.15
    ao = np.where(in_plank, 1.0, 0.35) * np.ones((1, size))
    rough = 0.62 + 0.25 * grain
    return colour, height, ao, rough


def material(name, bc=None, normal=None, orm=None, colour=(0.5, 0.5, 0.5), metal=0.0, rough=0.8):
    """Principled BSDF material wired the way the glTF exporter expects."""
    mat = bpy.data.materials.new(name)
    # Closed meshes only: single-sided materials keep backface culling on in the game.
    mat.use_backface_culling = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if bc:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bc
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if normal:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = normal
        nmap = nodes.new("ShaderNodeNormalMap")
        links.new(tex.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    if orm:
        # glTF packs occlusion (R), roughness (G) and metallic (B) in one texture.
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = orm
        split = nodes.new("ShaderNodeSeparateColor")
        links.new(tex.outputs["Color"], split.inputs["Color"])
        links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
        links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
        output = nodes.new("ShaderNodeGroup")
        output.node_tree = gltf_output_group()
        links.new(split.outputs["Red"], output.inputs["Occlusion"])
    return mat


def gltf_output_group():
    """The node group the glTF exporter reads ambient occlusion from."""
    group = bpy.data.node_groups.get("glTF Material Output")
    if group is None:
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return group


def build_materials():
    os.makedirs(TEXTURES, exist_ok=True)
    mats = {}

    # Teak deck planks: 14 cm planks with 1 cm gaps; 1 m of floor per texture tile.
    bc, height, ao, rough = plank_maps(1024, 7, 0.07, (0.42, 0.26, 0.15), 6)
    mats["teak"] = material(
        "M_teak_planks",
        save_image("T_teak_planks_BC", bc, False),
        save_image("T_teak_planks_N", normal_from_height(height, 6), True),
        save_image("T_teak_planks_ORM", np.stack([ao, rough, np.zeros_like(ao)], -1), True),
    )

    # Woven bamboo wall: rotate the plank pattern into vertical slats.
    bc, height, ao, rough = plank_maps(1024, 20, 0.12, (0.62, 0.52, 0.33), 10)
    bc, height, ao, rough = (np.swapaxes(a, 0, 1) for a in (bc, height, ao, rough))
    mats["bamboo"] = material(
        "M_bamboo_wall",
        save_image("T_bamboo_wall_BC", bc, False),
        save_image("T_bamboo_wall_N", normal_from_height(height, 4), True),
        save_image("T_bamboo_wall_ORM", np.stack([ao, rough, np.zeros_like(ao)], -1), True),
    )

    # Chest: dark wood with two iron bands (metallic in ORM blue).
    size = 1024
    bc, height, ao, rough = plank_maps(size, 5, 0.03, (0.3, 0.17, 0.09), 8)
    u = (np.arange(size) / size)[None, :] * np.ones((size, 1))
    band = (np.abs(u - 0.25) < 0.03) | (np.abs(u - 0.75) < 0.03)
    rust = value_noise(size, 16)
    bc[band] = (np.array([0.16, 0.15, 0.14])[None, :] + 0.12 * rust[band][:, None] * [1, 0.5, 0.2])
    height = np.where(band, 1.3, height)
    rough = np.where(band, 0.45 + 0.3 * rust, rough)
    metal = np.where(band, 1.0, 0.0)
    mats["chest"] = material(
        "M_chest_wood",
        save_image("T_chest_wood_BC", bc, False),
        save_image("T_chest_wood_N", normal_from_height(height, 5), True),
        save_image("T_chest_wood_ORM", np.stack([ao, rough, metal], -1), True),
    )

    # Untextured materials check the plain-factor path through the pipeline.
    mats["dirt"] = material("M_dirt", colour=(0.18, 0.13, 0.09), rough=0.95)
    mats["post"] = material("M_dark_wood", colour=(0.12, 0.07, 0.04), rough=0.7)
    return mats


# ---------------------------------------------------------------- geometry


def box(name, collection, centre, size, mat=None, rotation=(0, 0, 0), uv_scale=1.0, **props):
    """Axis-aligned box mesh; `props` become glTF extras (custom properties)."""
    mesh = bpy.data.meshes.new(name)
    hx, hy, hz = (s / 2 for s in size)
    verts = [(x, y, z) for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = centre
    obj.rotation_euler = rotation
    collection.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
        box_uvs(mesh, uv_scale)
    for key, value in props.items():
        obj[key] = value
    return obj


def box_uvs(mesh, scale):
    """World-size UVs per face (1 texture tile per `scale` metres)."""
    uv = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        n = poly.normal
        axis = max(range(3), key=lambda i: abs(n[i]))
        u_axis, v_axis = [(1, 2), (0, 2), (0, 1)][axis]
        for loop in poly.loop_indices:
            co = mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv = (co[u_axis] / scale, co[v_axis] / scale)


def prism(name, collection, centre, length, width, height, mat=None, **props):
    """Triangular ridge along Y: `length` along X, peak `height` above the base."""
    mesh = bpy.data.meshes.new(name)
    l, w = length / 2, width / 2
    verts = [(-l, -w, 0), (l, -w, 0), (0, -w, height), (-l, w, 0), (l, w, 0), (0, w, height)]
    faces = [(0, 2, 1), (3, 4, 5), (0, 3, 5, 2), (1, 2, 5, 4), (0, 1, 4, 3)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = centre
    collection.objects.link(obj)
    if mat:
        mesh.materials.append(mat)
        box_uvs(mesh, 4)
    for key, value in props.items():
        obj[key] = value
    return obj


def empty(name, collection, location, **props):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.location = location
    collection.objects.link(obj)
    for key, value in props.items():
        obj[key] = value
    return obj


def join(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    objects[0].name = name
    return objects[0]


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = build_materials()

    scene = bpy.context.scene
    area = bpy.data.collections.new("s3_test_room")
    scene.collection.children.link(area)
    # Collections starting with "_" are working files and are never exported.
    scratch = bpy.data.collections.new("_notes")
    scene.collection.children.link(scratch)
    empty("note_scratch_not_exported", scratch, (0, 0, 5))

    # Ground and its collider.
    box("ground", area, (0, 0, -0.05), (20, 20, 0.1), mats["dirt"], uv_scale=4)
    box("col_ground", area, (0, 0, -0.1), (20, 20, 0.2), surface="dirt")

    # Raised deck, 4 m square, top at 2 m, on six stilts.
    box("deck", area, (0, 4, DECK_TOP - 0.05), (4, 4, 0.1), mats["teak"])
    box("col_deck", area, (0, 4, DECK_TOP - 0.05), (4, 4, 0.1), surface="teak")
    stilts = [
        box(f"stilt_{i}", area, (x, y, (DECK_TOP - 0.1) / 2), (0.2, 0.2, DECK_TOP - 0.1), mats["post"])
        for i, (x, y) in enumerate((x, y) for x in (-1.9, 1.9) for y in (2.1, 4, 5.9))
    ]
    join(stilts, "stilts")

    # Walls on the back and left edges of the deck.
    box("wall_back", area, (0, 6, DECK_TOP + 1.15), (4, 0.08, 2.3), mats["bamboo"])
    box("wall_left", area, (-2, 4, DECK_TOP + 1.15), (0.08, 4, 2.3), mats["bamboo"])
    box("col_wall_back", area, (0, 6, DECK_TOP + 1.15), (4, 0.08, 2.3), surface="teak")
    box("col_wall_left", area, (-2, 4, DECK_TOP + 1.15), (0.08, 4, 2.3), surface="teak")

    # Front stairs: 10 steps of 20 cm rise and 26 cm tread up to the deck edge (y = 2).
    rise, tread, steps, width = 0.2, 0.26, 10, 1.2
    y0 = 2 - steps * tread
    blocks = [
        box(
            f"step_{i}",
            area,
            (0, y0 + tread * (i - 0.5), rise * i / 2),
            (width, tread, rise * i),
            mats["teak"],
        )
        for i in range(1, steps + 1)
    ]
    join(blocks, "stairs_front")
    # Hidden ramp over the step noses (S1: the controller cannot climb steps).
    # Nose of step i is at (y0 + tread * (i - 1), rise * i); extend the line to the ground.
    bottom = (y0 - tread, 0.0)
    top = (y0 + tread * (steps - 1), rise * steps)
    run, climb = top[0] - bottom[0], top[1] - bottom[1]
    length, angle = math.hypot(run, climb), math.atan2(climb, run)
    thickness = 0.1
    mid_y, mid_z = (bottom[0] + top[0]) / 2, (bottom[1] + top[1]) / 2
    # Move the centre down along the ramp's normal so its top face lies on the nose line.
    centre = (0, mid_y + math.sin(angle) * thickness / 2, mid_z - math.cos(angle) * thickness / 2)
    box("col_stairs_front", area, centre, (width - 0.04, length, thickness), rotation=(angle, 0, 0), surface="teak")

    # Rice granary beside the house with a ladder on its west face (x = 4.5).
    box("granary", area, (5.5, 0, GRANARY_TOP / 2), (2, 2, GRANARY_TOP), mats["post"])
    box("col_granary", area, (5.5, 0, GRANARY_TOP / 2), (2, 2, GRANARY_TOP), surface="teak")
    # Visible parts must not start with "ladder_": that prefix marks the climb volume.
    rails = [box(f"granary_ladder_rail_{y}", area, (4.42, y, 1.35), (0.05, 0.05, 2.7), mats["teak"]) for y in (-0.38, 0.38)]
    rungs = [
        box(f"granary_ladder_rung_{i}", area, (4.42, 0, 0.3 * i), (0.04, 0.76, 0.04), mats["teak"])
        for i in range(1, 9)
    ]
    join(rails + rungs, "granary_ladder")
    # Ladder volume: 60 cm out from the face, 30 cm above the top (TDD 7.1).
    box("ladder_granary", area, (4.2, 0, (GRANARY_TOP + 0.3) / 2), (0.6, 0.8, GRANARY_TOP + 0.3), facing="-x")

    # A prop with metal and wood, and an interaction tag.
    box("interact_chest", area, (0.9, 5.2, DECK_TOP + 0.25), (0.9, 0.5, 0.5), mats["chest"], uv_scale=0.9,
        action="open", note="s3_chest")
    box("col_chest", area, (0.9, 5.2, DECK_TOP + 0.25), (0.9, 0.5, 0.5), surface="teak")

    # A low earth mound on the bot's path: not a box, so it tests triangle-mesh colliders.
    prism("mound", area, (1.5, -1.6, 0), 1.0, 1.5, 0.08, mats["dirt"])
    prism("col_mound", area, (1.5, -1.6, 0), 1.0, 1.5, 0.08, surface="dirt")

    empty("spawn_player", area, (0, -3, 0), checkpoint="S3")

    # Bot route: ground → stairs → deck → down → ladder → granary roof.
    # `reach` marks nodes whose height must be reached (stairs, ladders).
    route = [
        ((0, -1.4, 0), False),
        ((0, 2.8, DECK_TOP), True),
        ((-1.2, 5, DECK_TOP), False),
        ((1.4, 4.2, DECK_TOP), False),
        ((0, 2.6, DECK_TOP), False),
        ((0, -1.6, 0), True),
        ((3, -1.6, 0), False),
        ((3.6, 0, 0), False),
        ((5.2, 0, GRANARY_TOP), True),
    ]
    for i, (location, reach) in enumerate(route, start=1):
        empty(f"patrol_bot_{i:02d}", area, location, reach=reach)

    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print(f"Saved {BLEND}")


build()
