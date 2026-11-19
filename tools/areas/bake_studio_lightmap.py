"""Bakes the Ep1 studio's static light into one lightmap (run inside Blender, after
tools/areas/ep1_area_studio.py):

    blender -b art-source/blender/ep1/ep1_area_studio.blend -P tools/areas/bake_studio_lightmap.py
    blender -b art-source/blender/ep1/ep1_area_studio.blend -P tools/areas/bake_studio_lightmap.py -- preview OUTDIR

What is baked: the banker's lamp, the writing sconce, the oil lamp on the altar, the
bulb at the foot of the stairs and the storm-dark night sky, with Cycles' soft
shadows and bounce light, times a grime pass (contact darkening, water stains running
down from the ceiling, scuffs along the skirting). What is not: the shelf candle (it
is put out in P05) and the lightning, which stay runtime lights.

Receivers are the room's large static surfaces and furniture. Each gets a second UV
map ("Lightmap", TEXCOORD_1 in the glTF) packed into one shared atlas, and its
materials are swapped for copies named *_LM, which the game finds by name and lights
with the lightmap instead of the baked lights (src/episodes/ep1/prologue/Studio.ts).
Small props, glass, cloth and everything the player picks up or moves are left to
runtime lights; they still cast their shadows into the bake.

Writes art-source/textures/ep1/T_studio_lightmap.png, RGBD-encoded as Babylon decodes
it (rgb gamma-encoded and divided by alpha; light x LIGHTMAP_GAIN), so the dark room keeps
precision in 8 bits and the lamp's hotspot does not clip, and saves the .blend with the
lightmap UVs and _LM materials, ready for export.
"""

import math
import os
import sys

import bpy
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "art-source", "textures", "ep1", "T_studio_lightmap.png")
SIZE = 4096
# Light is stored x GAIN before RGBD encoding; the game sets the lightmap's level to 1/GAIN
# (STUDIO_LIGHTMAP_GAIN in src/episodes/ep1/prologue/Studio.ts).
LIGHTMAP_GAIN = 8.0
SAMPLES = 1536

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sys.stdout.reconfigure(line_buffering=True)
scene = bpy.context.scene
area = bpy.data.collections["ep1_area_studio"]


def obj(name):
    return bpy.data.objects[name]


# ------------------------------------------------------------------ lights


def setup_lights():
    """The lights that are baked (kept out of the export: their collection starts with _)."""
    coll = bpy.data.collections.get("_bake_lights") or bpy.data.collections.new("_bake_lights")
    if coll.name not in scene.collection.children:
        scene.collection.children.link(coll)
    for o in list(coll.objects):
        bpy.data.objects.remove(o)

    def point(name, at, watts, colour, radius):
        data = bpy.data.lights.new(name, "POINT")
        data.energy = watts
        data.color = colour
        data.shadow_soft_size = radius
        o = bpy.data.objects.new(name, data)
        o.location = at
        coll.objects.link(o)
        return o

    lamp = obj("marker_desk_lamp").location
    point("bake_desk_lamp", lamp, 24.0, (1.0, 0.82, 0.56), 0.02)
    point("bake_writing_sconce", obj("marker_writing_sconce").location, 14.0, (1.0, 0.8, 0.52), 0.015)
    point("bake_altar_lamp", obj("marker_altar_lamp").location, 7.0, (1.0, 0.55, 0.22), 0.01)
    point("bake_stair_glow", obj("marker_stair_glow").location, 90.0, (1.0, 0.7, 0.4), 0.05)
    point("bake_airwell_bulb", obj("marker_airwell_bulb").location, 55.0, (1.0, 0.78, 0.5), 0.02)
    point("bake_tea_lamp", obj("marker_tea_lamp").location, 9.0, (1.0, 0.58, 0.26), 0.012)
    # The candle by Sora's diary on the writing desk (the save point; flickered live, Studio.ts).
    point("bake_desk_candle", obj("light_flame_desk_candle").location, 1.2, (1.0, 0.6, 0.26), 0.006)

    world = scene.world or bpy.data.worlds.new("night")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
    bg.inputs["Strength"].default_value = 1.0


# What Sora picks up or lifts: kept out of the bake altogether, so taking it leaves no
# baked shadow behind on the desk or the shelf (the game gives each a contact shadow of
# its own that goes with it, StudioDetails.ts).
TAKEN = ("interact_satchel", "interact_sketchbook", "interact_lamp", "matchbox", "letters_string", "telephone_earpiece")


def taken(o):
    while o:
        if o.name in TAKEN or o.name.startswith("letter_"):
            return True
        o = o.parent
    return False


def hide_helpers():
    """Colliders and interaction volumes are invisible in the game: hide them from Cycles.
    So are the things Sora takes, and the crack decals (blended over walls in the game)."""
    for o in bpy.data.objects:
        if o.name.startswith("col_") or "pickup_volume" in o.name or "crack" in o.name or taken(o):
            o.hide_render = True
        # Bulbs and flames are opaque meshes round their point lights: in the bake they
        # would swallow the light (the shades and chimneys around them stay).
        if o.type == "MESH" and any(k in o.name for k in ("bulb", "flame")) and "holder" not in o.name:
            o.hide_render = True


def cycles(samples):
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.refresh_devices()
    for d in prefs.devices:
        d.use = d.type != "CPU"
    print("Cycles devices:", [(d.name, d.type, d.use) for d in prefs.devices])
    scene.cycles.device = "GPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 2
    scene.cycles.transparent_max_bounces = 4


# ------------------------------------------------------------------ preview


def preview(outdir):
    """Renders a few eye-level views (no lightmap) to check the room before baking."""
    os.makedirs(outdir, exist_ok=True)
    cycles(64)
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = float(os.environ.get("PREVIEW_EXPOSURE", 3.2))
    cam_data = bpy.data.cameras.new("preview")
    cam_data.lens = 18
    cam = bpy.data.objects.new("preview", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    views = {
        "01_spawn_south": ((3.0, 1.75, 1.45), (2.9, -1.0, 1.0)),
        "02_studio_north": ((2.6, 0.45, 1.6), (1.6, 6.0, 1.2)),
        "03_desk_west": ((2.2, 2.6, 1.55), (0.0, 2.6, 1.1)),
        "04_tea_east": ((1.4, 2.2, 1.55), (4.6, 3.6, 1.6)),
        "05_airwell": ((0.6, 6.4, 1.55), (3.4, 8.8, 0.8)),
        "06_phone": ((2.8, 7.3, 1.55), (2.9, 6.1, 1.3)),
        "07_back_room": ((0.7, 9.6, 1.6), (3.5, 13.6, 1.0)),
        "08_altar": ((2.6, 11.5, 1.6), (1.1, 14.0, 1.9)),
        "09_kitchen": ((1.25, 8.6, 1.45), (0.0, 7.3, 0.8)),
        "10_hall_north": ((2.3, 6.35, 1.6), (2.0, 9.12, 0.8)),
        "11_hall_west": ((3.25, 8.5, 1.55), (0.0, 7.3, 0.95)),
        "12_sleeping_mat": ((3.0, 7.3, 1.7), (4.6, 6.7, 1.6)),
        "13_drafting_table": ((3.0, 1.75, 1.55), (3.0, 0.6, 0.85)),
        "14_back_room_door": ((0.6, 9.5, 1.6), (2.2, 13.5, 1.1)),
    }
    only = argv[2:] if len(argv) > 2 else None
    for name, (eye, target) in views.items():
        if only and not any(name.startswith(o) for o in only):
            continue
        cam.location = eye
        d = np.array(target) - np.array(eye)
        cam.rotation_euler = (math.atan2(math.hypot(d[0], d[1]), -d[2]), 0, math.atan2(d[1], d[0]) - math.pi / 2)
        scene.render.filepath = os.path.join(outdir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name)


# ------------------------------------------------------------------ bake

# Never lightmapped: what moves or is picked up, see-through or glowing surfaces, thin
# strands, and paper props too small to carry a lightmap.
SKIP_NAMES = ("glass", "net", "water", "flame", "bulb", "shade", "cord", "wire", "string", "line", "fringe", "pin_", "_pin",
              "letter", "envelope", "matchbox", "pencil", "ribbon", "wick", "candle_drip", "wax_pool", "drawer", "satchel", "sketchbook", "illustration", "incense", "cleat", "hook",
              "chain", "pull", "rain", "puddle", "telephone", "earpiece", "krama", "sampot", "towel", "peg",
              "laundry", "fern", "moss", "banana", "branch", "firewood", "lantern_", "birdcage", "chilli", "garlic", "ladle",
              "bowl", "jar_lid", "dipper", "kettle", "shrine_orange", "shrine_incense", "blind", "cobweb", "crack",
              "food_cover", "chopstick", "hat_", "coat", "screen", "ant_", "drip_water", "lamp_rose")
SKIP_MATERIALS = ("glass", "net", "water", "bulb", "flame", "opal", "neighbour", "dark_room", "mesh", "cobweb")


def under_dynamic(o):
    while o:
        if o.name.startswith(("interact_", "marker_", "spawn_", "col_", "light_flame_")):
            return True
        o = o.parent
    return False


def mesh_area(o):
    mw = o.matrix_world
    return sum((mw.to_3x3() @ p.normal).length * p.area for p in o.data.polygons) if o.data.polygons else 0.0


def receivers():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in area.all_objects:
        if o.type != "MESH" or o.hide_render or under_dynamic(o):
            continue
        if any(k in o.name.lower() for k in SKIP_NAMES):
            continue
        mats = [s.material for s in o.material_slots if s.material]
        if not mats or any(any(k in mt.name.lower() for k in SKIP_MATERIALS) for mt in mats):
            continue
        dims = o.evaluated_get(depsgraph).dimensions
        if max(dims) < 0.22:
            continue
        out.append(o)
    return out


def apply_modifiers(objs):
    """Bevels and decimation applied for good, so the lightmap UVs match what is exported."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        mesh = bpy.data.meshes.new_from_object(o.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
        o.modifiers.clear()
        old = o.data
        o.data = mesh
        if old.users == 0:
            bpy.data.meshes.remove(old)


def lightmap_uvs(objs):
    for o in objs:
        uvs = o.data.uv_layers
        if not uvs:
            uvs.new(name="UVMap")
        # Keep only the UV map the materials render with, so the lightmap's is always the
        # second (TEXCOORD_1). Cylinders from bpy.ops keep a spare default layer otherwise.
        render = next((layer for layer in uvs if layer.active_render), uvs[0])
        for layer in [layer for layer in uvs if layer != render and layer.name != "Lightmap"]:
            uvs.remove(layer)
        uvs[0].name = "UVMap"
        lm = uvs.get("Lightmap") or uvs.new(name="Lightmap")
        uvs.active = lm
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    scene.tool_settings.use_uv_select_sync = True
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=0.0025)
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in objs:
        # The colour UVs stay first (TEXCOORD_0) and active for rendering.
        o.data.uv_layers.active = o.data.uv_layers["UVMap"]
        o.data.uv_layers["UVMap"].active_render = True


def lightmap_materials(objs, images):
    """Each receiver's materials become *_LM copies holding the bake target node."""
    copies = {}
    for o in objs:
        for slot in o.material_slots:
            mat = slot.material
            if mat is None or mat.name.endswith("_LM"):
                continue
            if mat.name not in copies:
                lm = mat.copy()
                lm.name = f"{mat.name}_LM"
                # An extra, so the asset build's dedup cannot merge it back into the original.
                lm["lightmap"] = 1
                nodes = lm.node_tree.nodes
                uv = nodes.new("ShaderNodeUVMap")
                uv.uv_map = "Lightmap"
                uv.name = "lightmap_uv"
                tex = nodes.new("ShaderNodeTexImage")
                tex.name = "lightmap_target"
                lm.node_tree.links.new(uv.outputs["UV"], tex.inputs["Vector"])
                copies[mat.name] = lm
            slot.link = "OBJECT" if slot.link == "OBJECT" else slot.link
            slot.material = copies[mat.name]
    return list(copies.values())


def set_target(mats, img):
    for mat in mats:
        node = mat.node_tree.nodes["lightmap_target"]
        node.image = img
        mat.node_tree.nodes.active = node


# Local grime, multiplied into the bake (world centre, radii in metres, colour at full
# strength, fill, tide-line ring). Where they are: tools/areas/ep1_area_studio.py, hall().
MARKS = (
    ((0.0, 7.55, 1.25), (0.45, 0.55, 1.15), (0.16, 0.14, 0.12), 0.85, 0.0),     # soot over the cooking fire
    ((0.0, 7.6, 3.3), (0.9, 0.9, 0.5), (0.3, 0.27, 0.24), 0.7, 0.0),           # soot spread under the ceiling
    ((3.0, 7.4, 3.45), (0.55, 0.48, 0.12), (0.62, 0.45, 0.28), 0.55, 0.5),    # roof leak on the hall ceiling
    ((4.6, 7.55, 2.6), (0.12, 0.35, 0.95), (0.65, 0.5, 0.33), 0.5, 0.35),     # its run down the east wall
    ((2.95, 9.12, 0.35), (0.7, 0.12, 0.45), (0.58, 0.55, 0.45), 0.6, 0.45),   # damp rising behind the water jar
    ((0.9, 14.0, 3.2), (0.8, 0.15, 0.7), (0.62, 0.48, 0.32), 0.45, 0.4),      # an old leak in the back room
)


def stain_field():
    """Grime that a clean, old room collects: contact darkness in corners and under things,
    tea-coloured water stains running down the walls from the ceiling, scuffs above the
    skirting, a slow mottle. Output: a grey multiplier (1 = clean)."""
    g = bpy.data.node_groups.new("studio_stain_field", "ShaderNodeTree")
    g.interface.new_socket("Dirt", in_out="OUTPUT", socket_type="NodeSocketColor")
    n, l = g.nodes, g.links
    out = n.new("NodeGroupOutput")
    geo = n.new("ShaderNodeNewGeometry")
    xyz = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Position"], xyz.inputs[0])
    nz = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Normal"], nz.inputs[0])
    wallness = n.new("ShaderNodeMath"); wallness.operation = "ABSOLUTE"; l.new(nz.outputs["Z"], wallness.inputs[0])
    wall = n.new("ShaderNodeMath"); wall.operation = "SUBTRACT"; wall.inputs[0].default_value = 1.0; l.new(wallness.outputs[0], wall.inputs[1])
    # Streaks: noise stretched vertically, strongest near the ceiling.
    scale = n.new("ShaderNodeVectorMath"); scale.operation = "MULTIPLY"; scale.inputs[1].default_value = (2.6, 2.6, 0.35)
    l.new(geo.outputs["Position"], scale.inputs[0])
    streak = n.new("ShaderNodeTexNoise"); streak.inputs["Scale"].default_value = 1.0; streak.inputs["Detail"].default_value = 6.0
    l.new(scale.outputs[0], streak.inputs["Vector"])
    st = n.new("ShaderNodeMapRange"); st.inputs[1].default_value = 0.55; st.inputs[2].default_value = 0.72
    l.new(streak.outputs["Fac"], st.inputs[0])
    top = n.new("ShaderNodeMapRange"); top.inputs[1].default_value = 1.6; top.inputs[2].default_value = 3.3
    l.new(xyz.outputs["Z"], top.inputs[0])
    stains = n.new("ShaderNodeMath"); stains.operation = "MULTIPLY"; l.new(st.outputs[0], stains.inputs[0]); l.new(top.outputs[0], stains.inputs[1])
    stains_w = n.new("ShaderNodeMath"); stains_w.operation = "MULTIPLY"; l.new(stains.outputs[0], stains_w.inputs[0]); l.new(wall.outputs[0], stains_w.inputs[1])
    stain_amt = n.new("ShaderNodeMath"); stain_amt.operation = "MULTIPLY"; stain_amt.inputs[1].default_value = 0.32; l.new(stains_w.outputs[0], stain_amt.inputs[0])
    # Scuffs above the skirting on walls.
    low = n.new("ShaderNodeMapRange"); low.inputs[1].default_value = 0.45; low.inputs[2].default_value = 0.1
    l.new(xyz.outputs["Z"], low.inputs[0])
    scuffn = n.new("ShaderNodeTexNoise"); scuffn.inputs["Scale"].default_value = 9.0
    scuff = n.new("ShaderNodeMath"); scuff.operation = "MULTIPLY"; l.new(low.outputs[0], scuff.inputs[0]); l.new(scuffn.outputs["Fac"], scuff.inputs[1])
    scuff_w = n.new("ShaderNodeMath"); scuff_w.operation = "MULTIPLY"; l.new(scuff.outputs[0], scuff_w.inputs[0]); l.new(wall.outputs[0], scuff_w.inputs[1])
    scuff_amt = n.new("ShaderNodeMath"); scuff_amt.operation = "MULTIPLY"; scuff_amt.inputs[1].default_value = 0.28; l.new(scuff_w.outputs[0], scuff_amt.inputs[0])
    # Contact darkness.
    ao = n.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.35; ao.samples = 16
    aomix = n.new("ShaderNodeMapRange"); aomix.inputs[3].default_value = 0.5; aomix.inputs[4].default_value = 1.0
    l.new(ao.outputs["AO"], aomix.inputs[0])
    # Slow mottle.
    mot = n.new("ShaderNodeTexNoise"); mot.inputs["Scale"].default_value = 1.4
    motr = n.new("ShaderNodeMapRange"); motr.inputs[3].default_value = 0.93; motr.inputs[4].default_value = 1.05
    l.new(mot.outputs["Fac"], motr.inputs[0])
    clean = n.new("ShaderNodeMath"); clean.operation = "SUBTRACT"; clean.inputs[0].default_value = 1.0; l.new(stain_amt.outputs[0], clean.inputs[1])
    clean2 = n.new("ShaderNodeMath"); clean2.operation = "SUBTRACT"; l.new(clean.outputs[0], clean2.inputs[0]); l.new(scuff_amt.outputs[0], clean2.inputs[1])
    m1 = n.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; l.new(clean2.outputs[0], m1.inputs[0]); l.new(aomix.outputs[0], m1.inputs[1])
    m2 = n.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; l.new(m1.outputs[0], m2.inputs[0]); l.new(motr.outputs[0], m2.inputs[1])
    # Water stains are tea-coloured, not grey.
    tint = n.new("ShaderNodeMix"); tint.data_type = "RGBA"; tint.blend_type = "MULTIPLY"
    l.new(stains_w.outputs[0], tint.inputs["Factor"])
    l.new(m2.outputs[0], tint.inputs[6])
    tint.inputs[7].default_value = (1.0, 0.86, 0.68, 1)
    comb = n.new("ShaderNodeCombineXYZ")
    for k in "XYZ":
        l.new(m2.outputs[0], comb.inputs[k])
    l.new(comb.outputs[0], tint.inputs[6])
    acc = tint.outputs[2]
    # Local marks, each a soft blob with a broken edge: soot over the cooking fire, the
    # roof leaks, damp rising behind the water jar.
    for k, (centre, radii, colour, fill, ring) in enumerate(MARKS):
        rel = n.new("ShaderNodeVectorMath"); rel.operation = "SUBTRACT"; rel.inputs[1].default_value = centre
        l.new(geo.outputs["Position"], rel.inputs[0])
        sc = n.new("ShaderNodeVectorMath"); sc.operation = "MULTIPLY"; sc.inputs[1].default_value = tuple(1.0 / r for r in radii)
        l.new(rel.outputs[0], sc.inputs[0])
        shift = n.new("ShaderNodeVectorMath"); shift.operation = "ADD"; shift.inputs[1].default_value = (k * 7.3, k * 3.1, k * 5.7)
        l.new(geo.outputs["Position"], shift.inputs[0])
        wob = n.new("ShaderNodeTexNoise"); wob.inputs["Scale"].default_value = 3.0; wob.inputs["Detail"].default_value = 8.0
        l.new(shift.outputs[0], wob.inputs["Vector"])
        cen = n.new("ShaderNodeVectorMath"); cen.operation = "SUBTRACT"; cen.inputs[1].default_value = (0.5, 0.5, 0.5)
        l.new(wob.outputs["Color"], cen.inputs[0])
        amp = n.new("ShaderNodeVectorMath"); amp.operation = "SCALE"; amp.inputs["Scale"].default_value = 0.55
        l.new(cen.outputs[0], amp.inputs[0])
        bent = n.new("ShaderNodeVectorMath"); bent.operation = "ADD"; l.new(sc.outputs[0], bent.inputs[0]); l.new(amp.outputs[0], bent.inputs[1])
        d = n.new("ShaderNodeVectorMath"); d.operation = "LENGTH"; l.new(bent.outputs[0], d.inputs[0])
        body = n.new("ShaderNodeMapRange"); body.interpolation_type = "SMOOTHSTEP"
        body.inputs[1].default_value = 1.0; body.inputs[2].default_value = 0.15
        l.new(d.outputs["Value"], body.inputs[0])
        edge = n.new("ShaderNodeMath"); edge.operation = "SUBTRACT"; edge.inputs[1].default_value = 0.9
        l.new(d.outputs["Value"], edge.inputs[0])
        edge_abs = n.new("ShaderNodeMath"); edge_abs.operation = "ABSOLUTE"; l.new(edge.outputs[0], edge_abs.inputs[0])
        tide = n.new("ShaderNodeMapRange"); tide.interpolation_type = "SMOOTHSTEP"
        tide.inputs[1].default_value = 0.07; tide.inputs[2].default_value = 0.0
        l.new(edge_abs.outputs[0], tide.inputs[0])
        f1 = n.new("ShaderNodeMath"); f1.operation = "MULTIPLY"; f1.inputs[1].default_value = fill; l.new(body.outputs[0], f1.inputs[0])
        f2 = n.new("ShaderNodeMath"); f2.operation = "MULTIPLY_ADD"; l.new(tide.outputs[0], f2.inputs[0]); f2.inputs[1].default_value = ring
        l.new(f1.outputs[0], f2.inputs[2])
        clampf = n.new("ShaderNodeClamp"); l.new(f2.outputs[0], clampf.inputs[0])
        mark = n.new("ShaderNodeMix"); mark.data_type = "RGBA"; mark.blend_type = "MULTIPLY"
        l.new(clampf.outputs[0], mark.inputs["Factor"]); l.new(acc, mark.inputs[6])
        mark.inputs[7].default_value = (*colour, 1)
        acc = mark.outputs[2]
    l.new(acc, out.inputs["Dirt"])
    return g


def with_emission(mats, group):
    """Temporarily routes the stain field into each material's emission for an EMIT bake."""
    undo = []
    for mat in mats:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = next((nd for nd in nodes if nd.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        gn = nodes.new("ShaderNodeGroup"); gn.node_tree = group
        old = [(lk.from_socket, lk.to_socket) for lk in links if lk.to_socket in (bsdf.inputs["Emission Color"], bsdf.inputs["Emission Strength"])]
        prev = (tuple(bsdf.inputs["Emission Color"].default_value), bsdf.inputs["Emission Strength"].default_value)
        for lk in [lk for lk in links if lk.to_socket in (bsdf.inputs["Emission Color"], bsdf.inputs["Emission Strength"])]:
            links.remove(lk)
        links.new(gn.outputs["Dirt"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
        undo.append((mat, bsdf, gn, old, prev))
    return undo


def restore_emission(undo):
    for mat, bsdf, gn, old, prev in undo:
        mat.node_tree.nodes.remove(gn)
        bsdf.inputs["Emission Color"].default_value = prev[0]
        bsdf.inputs["Emission Strength"].default_value = prev[1]
        for a, b in old:
            mat.node_tree.links.new(a, b)


def new_float_image(name):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    return bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=True)


def pixels(img):
    a = np.empty(SIZE * SIZE * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(SIZE, SIZE, 4)


def merged_copy(objs):
    """One object holding copies of every receiver: Cycles bakes each selected object in a
    session of its own (rebuilding the scene each time), so hundreds of receivers took
    over half an hour; one merged copy bakes in one session. The receivers themselves are
    hidden from the render meanwhile (the copy stands in for them as an occluder too)."""
    copies = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        c.parent = None
        c.matrix_world = o.matrix_world.copy()
        area.objects.link(c)
        copies.append(c)
        o.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    for c in copies:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    merged = bpy.context.view_layer.objects.active
    merged.name = "_bake_receivers"
    merged.data.uv_layers.active = merged.data.uv_layers["Lightmap"]
    return merged


def release_copy(merged, objs):
    bpy.data.objects.remove(merged)
    for o in objs:
        o.hide_render = False


def soften(px, sigma=1.1):
    """Removes the bake's remaining sample noise: a small Gaussian over covered texels only,
    so empty atlas space never bleeds in (islands are 10 px apart, the blur reaches 3)."""
    rgb = px[..., :3]
    mask = (rgb.max(axis=-1) > 0).astype(np.float32)
    r = 3
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2).astype(np.float32)
    k /= k.sum()

    def blur(img):
        out = np.zeros_like(img)
        for i, w in enumerate(k):
            out += w * np.roll(img, i - r, axis=0)
        img, out = out, np.zeros_like(out)
        for i, w in enumerate(k):
            out += w * np.roll(img, i - r, axis=1)
        return out

    num = blur(rgb * mask[..., None])
    den = blur(mask)[..., None]
    soft = np.where(den > 1e-4, num / np.maximum(den, 1e-4), 0.0) * mask[..., None]
    out = px.copy()
    out[..., :3] = soft
    return out


def bake_pass(objs, kind, img, **kw):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    t = __import__("time").time()
    bpy.ops.object.bake(type=kind, margin=16, margin_type="EXTEND", use_clear=True, target="IMAGE_TEXTURES", **kw)
    print(f"baked {kind} in {__import__('time').time() - t:.0f} s")


def bake():
    cycles(SAMPLES)
    scene.cycles.use_denoising = False
    objs = receivers()
    print(f"{len(objs)} receivers")
    apply_modifiers(objs)
    lightmap_uvs(objs)
    mats = lightmap_materials(objs, None)
    merged = merged_copy(objs)
    irr = new_float_image("lm_irradiance")
    set_target(mats, irr)
    bake_pass([merged], "DIFFUSE", irr, pass_filter={"DIRECT", "INDIRECT"})
    dirt = new_float_image("lm_dirt")
    set_target(mats, dirt)
    scene.cycles.samples = 64
    undo = with_emission(mats, stain_field())
    bake_pass([merged], "EMIT", dirt)
    restore_emission(undo)
    release_copy(merged, objs)
    a, d = soften(pixels(irr)), soften(pixels(dirt))
    lit = a[..., :3] * np.clip(d[..., :3], 0.3, 1.1) * LIGHTMAP_GAIN
    # Babylon's toRGBD: D = floor(min(255 / max(rgb), 255)) / 255, rgb' = gamma(rgb * D).
    peak = np.maximum(lit.max(axis=-1), 1e-6)
    D = np.clip(np.floor(np.maximum(255.0 / peak, 1.0)), 1, 255) / 255.0
    out = np.ones((SIZE, SIZE, 4), np.float32)
    out[..., :3] = np.clip(lit * D[..., None], 0, 1) ** (1 / 2.2)
    out[..., 3] = D
    final = bpy.data.images.new("T_studio_lightmap", SIZE, SIZE, alpha=True)
    final.colorspace_settings.name = "Non-Color"
    final.alpha_mode = "STRAIGHT"
    final.pixels.foreach_set(out.ravel())
    final.filepath_raw = OUT
    final.file_format = "PNG"
    final.save()
    # The bake targets are working data; the game reads the PNG (as KTX2).
    for mat in mats:
        mat.node_tree.nodes["lightmap_target"].image = None
    for img in (irr, dirt, final):
        bpy.data.images.remove(img)
    for o in objs:
        o["lightmap"] = 1
    covered = lit.max(axis=-1) > 0
    print(f"Lightmap written: {OUT}: {100 * covered.mean():.0f}% of the atlas used, median light "
          f"{float(np.median(lit[covered].max(axis=-1))) / LIGHTMAP_GAIN:.4f}, {len(mats)} _LM materials")
    bpy.ops.wm.save_mainfile()


if __name__ == "__main__":
    setup_lights()
    hide_helpers()
    if argv and argv[0] == "preview":
        preview(argv[1])
    else:
        bake()
