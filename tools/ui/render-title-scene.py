"""Renders the title-screen background: the village house hall dressed for a binding ritual.

Key art, not the Episode 1 layout: red binding threads web the hall from the
altar, cloth effigies hang from them, Uncle Sok's coffin lies open in a circle
of floor candles under incense smoke and paper charms are pinned to the walls.

Never saves the .blend. Run from the repository root:
  blender -b art-source/blender/ep1/ep1_area_village.blend -P tools/ui/render-title-scene.py -- <out> <mode> [width] [samples]

Modes (all share one camera and seed):
  empty | far | near      still plate (<out> is a .png); far/near add the black Neak Ta
  loop [w] [samples] [frames]  the empty hall as a seamless 8 s, 12 fps loop (<out> is a folder of PNGs):
                          candles gutter, the lantern swings, effigies sway and one turns,
                          smoke drifts, and at 5.0 s something knocks the coffin lid from inside
  figure-far | figure-near  only the Neak Ta, everything else held out, on a transparent PNG
                          to lay over the loop
  threads-empty | threads-far | threads-near  only the red cords, their dolls and hair on a
                          transparent PNG (the room, and the Neak Ta where present, cut them out);
                          the still plates leave them out and keep their shadows
  threads-data            writes <out>.ts: the cords projected into the frame
Metres, Blender Z up.
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = os.getcwd()
argv = sys.argv[sys.argv.index("--") + 1 :]
OUT = os.path.abspath(argv[0])
MODE = argv[1] if len(argv) > 1 else "empty"
WIDTH = int(argv[2]) if len(argv) > 2 else 1920
SAMPLES = int(argv[3]) if len(argv) > 3 else 160
FLOOR = 2.5
FPS, FRAMES = 12, 96  # ffmpeg blends to 24 fps
KNOCK = 5.0  # seconds into the loop; WelcomeScreen syncs its knock sound to this
FIGURE = MODE.startswith("figure-")
SHIFT = -0.2
s = bpy.context.scene
rng = np.random.default_rng(1932)

# Colliders and other runtime-only helpers are never seen.
for o in s.objects:
    if o.name.lower().startswith(("col_", "trg_", "trigger", "nav", "zone", "spawn", "probe", "sound", "audio")):
        o.hide_render = True

s.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "METAL"
prefs.get_devices()
for d in prefs.devices:
    d.use = True
s.cycles.device = "GPU"
s.cycles.samples = SAMPLES
s.cycles.seed = 7
s.cycles.use_denoising = True
s.cycles.max_bounces = 6
s.cycles.volume_bounces = 1
s.render.resolution_x, s.render.resolution_y = WIDTH, WIDTH * 9 // 16
s.render.resolution_percentage = 100
s.view_settings.view_transform = "AgX"
s.view_settings.exposure = 1.0

world = bpy.data.worlds.new("title_night")
s.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.008, 0.012, 0.02, 1)


def light(kind, name, loc, color, energy, size=0.05, rot=None):
    d = bpy.data.lights.new(name, kind)
    d.color, d.energy = color, energy
    if kind in ("POINT", "SPOT"):
        d.shadow_soft_size = size
    if kind == "SUN":
        d.angle = math.radians(1.2)
    o = bpy.data.objects.new(name, d)
    o.location = loc
    if rot:
        o.rotation_euler = rot
    s.collection.objects.link(o)
    return o


def material(name, color, rough=0.6, emit=None, strength=0.0, image=None, alpha=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        if alpha:
            # Decals: flat paint colour, the image only shapes it.
            nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        else:
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def numpy_image(name, rgba):
    """rgba: H x W x 4 floats, top row first."""
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel())
    img.pack()
    return img


def link(obj):
    s.collection.objects.link(obj)
    return obj


def plane(name, size, loc, rot, mat):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], 1)
    o.data.materials.append(mat)
    return o


# --- Light: moon through slats and the back door, lamps turned low -------------------------
light("SUN", "moon", (0, 0, 20), (0.6, 0.74, 1.0), 1.1, rot=(math.radians(62), 0, math.radians(-128)))
light("POINT", "lantern", (0.0, 14.5, 4.12), (1.0, 0.5, 0.22), 10, 0.04)
light("POINT", "altar_lamp", (0.0, 17.4, 3.75), (1.0, 0.42, 0.16), 9, 0.02)
light("AREA", "back_door_moon", (2.35, 19.2, 4.2), (0.55, 0.72, 1.0), 800, rot=(math.radians(-90), 0, 0)).data.size = 1.2
light("AREA", "cold_fill", (0.3, 12.4, 5.2), (0.55, 0.7, 0.85), 3, rot=(math.radians(-30), 0, 0)).data.size = 4
light("AREA", "window_moon", (-7.5, 15.5, 4.0), (0.55, 0.72, 1.0), 160, rot=(0, math.radians(-90), 0)).data.size = 2

# --- Haze through the room and a heavier incense smoke along the floor ----------------------
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 8, 3))
haze = bpy.context.active_object
haze.name, haze.scale = "title_haze", (30, 30, 8)
m = bpy.data.materials.new("title_haze")
m.use_nodes = True
nt = m.node_tree
nt.nodes.clear()
vol = nt.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Density"].default_value = 0.012
vol.inputs["Color"].default_value = (0.75, 0.85, 1, 1)
nt.links.new(vol.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Volume"])
haze.data.materials.append(m)

bpy.ops.mesh.primitive_cube_add(size=1, location=(0.3, 15.0, FLOOR + 0.42))
smoke = bpy.context.active_object
smoke.name, smoke.scale = "title_smoke", (5.9, 6.4, 0.84)
m = bpy.data.materials.new("title_smoke")
m.use_nodes = True
nt = m.node_tree
nt.nodes.clear()
vol = nt.nodes.new("ShaderNodeVolumePrincipled")
vol.inputs["Color"].default_value = (0.8, 0.82, 0.84, 1)
noise = nt.nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 1.6
noise.inputs["Detail"].default_value = 6
coord = nt.nodes.new("ShaderNodeTexCoord")
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.45, (0, 0, 0, 1)
ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.75, (0.22, 0.22, 0.22, 1)
# Thickest on the boards, thinning upward.
grad = nt.nodes.new("ShaderNodeTexGradient")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
fall = nt.nodes.new("ShaderNodeMath")
fall.operation = "POWER"
fall.inputs[1].default_value = 2.2
inv = nt.nodes.new("ShaderNodeMath")
inv.operation = "SUBTRACT"
inv.inputs[0].default_value = 1.0
mul = nt.nodes.new("ShaderNodeMath")
mul.operation = "MULTIPLY"
nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(coord.outputs["Generated"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], inv.inputs[1])
nt.links.new(inv.outputs[0], fall.inputs[0])
nt.links.new(ramp.outputs["Color"], mul.inputs[0])
nt.links.new(fall.outputs[0], mul.inputs[1])
nt.links.new(mul.outputs[0], vol.inputs["Density"])
nt.links.new(vol.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Volume"])
smoke.data.materials.append(m)
del grad

# --- Red binding threads webbed out from the altar -----------------------------------------
# Cords, the dolls on them and the hair tied to them form their own layer, which the
# welcome screen draws over the plates and sets trembling.
CORDS = []
LINES = []  # projected for the screen's blood beads


def wet_cord_material():
    """Cotton cord soaked dark in blood: fibrous, wet sheen, black where it has dried."""
    m = material("title_thread", (0.2, 0.008, 0.006), 0.42)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Coat Weight"].default_value = 0.5
    bsdf.inputs["Coat Roughness"].default_value = 0.18
    coord = nt.nodes.new("ShaderNodeTexCoord")
    fibre = nt.nodes.new("ShaderNodeTexNoise")
    fibre.inputs["Scale"].default_value = 900
    fibre.inputs["Detail"].default_value = 4
    dried = nt.nodes.new("ShaderNodeTexNoise")
    dried.inputs["Scale"].default_value = 9
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.45, (0.2, 0.008, 0.006, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.62, (0.035, 0.004, 0.003, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    nt.links.new(coord.outputs["Object"], fibre.inputs["Vector"])
    nt.links.new(coord.outputs["Object"], dried.inputs["Vector"])
    nt.links.new(dried.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(fibre.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


thread_mat = wet_cord_material()
hair_mat = material("title_hair", (0.006, 0.005, 0.0045), 0.42)
blood_mat = material("title_blood_bead", (0.09, 0.003, 0.002), 0.12)


def cord(pts, radius=0.0065, name="title_thread", parent=None, layer=True):
    """A cord along the given points."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(pts) - 1)
    for sp, p in zip(spline.points, pts):
        sp.co = (*p, 1)
    obj = link(bpy.data.objects.new(name, curve))
    obj.data.materials.append(thread_mat)
    if parent:
        bpy.context.view_layer.update()
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    if layer:
        CORDS.append(obj)
    return obj


def thread(a, b, sag, radius=0.0065, name="title_thread", parent=None):
    """A sagging cord from a to b, returned with its sample points."""
    a, b = Vector(a), Vector(b)
    pts = []
    for i in range(25):
        t = i / 24
        p = a.lerp(b, t)
        p.z -= sag * 4 * t * (1 - t)
        pts.append(p)
    cord(pts, radius, name, parent)
    if parent is None:
        LINES.append(pts)
    return pts


def hair_tuft(top, length):
    """A hank of long black hair knotted to a cord, hanging limp."""
    for _ in range(46):
        ln = length * rng.uniform(0.55, 1.0)
        dx, dy = rng.normal(0, 0.012, 2)
        bend = rng.normal(0, 0.02, 2)
        pts = []
        for i in range(9):
            t = i / 8
            pts.append(Vector((top[0] + dx * t + bend[0] * t * t, top[1] + dy * t + bend[1] * t * t, top[2] - ln * t)))
        c = cord(pts, 0.0011, "title_hair")
        c.data.materials[0] = hair_mat
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.012, location=top)
    knot = bpy.context.active_object
    knot.name = "title_thread_knot"
    knot.data.materials.append(thread_mat)
    CORDS.append(knot)


def bead(at, size=1.0):
    """A drop of blood clinging under a cord."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=1, location=(at[0], at[1], at[2] - 0.009 * size))
    b = bpy.context.active_object
    b.name, b.scale = "title_thread_bead", (0.0042 * size, 0.0042 * size, 0.0075 * size)
    b.data.materials.append(blood_mat)
    CORDS.append(b)


ALTAR = (0.0, 17.55, 3.62)
webs = []
# Radiating from the altar to the right wall, the ridge beam and the back door frame; the
# left of the frame stays clear for the menu.
for target, sag in [
    ((2.95, 13.2, 4.55), 0.25), ((2.95, 14.6, 4.05), 0.3), ((2.95, 16.2, 3.7), 0.18),
    ((2.95, 13.6, 3.6), 0.3), ((2.2, 17.95, 4.55), 0.06), ((0.35, 16.2, 4.9), 0.3), ((1.0, 14.0, 4.9), 0.45),
]:
    webs.append(thread(ALTAR, target, sag))
# Cross-ties from the right wall to the ridge, so the cords read as a net.
for a, b, sag in [
    ((2.95, 14.3, 4.45), (0.95, 14.0, 4.85), 0.2), ((2.95, 15.6, 4.6), (0.45, 15.9, 4.88), 0.25),
    ((2.95, 16.8, 3.9), (0.2, 16.6, 4.6), 0.2),
]:
    webs.append(thread(a, b, sag))
# A few that sag almost to head height in front of the back door.
webs.append(thread((2.95, 15.2, 4.5), (0.9, 17.9, 3.3), 0.35))
webs.append(thread((1.87, 17.95, 4.4), (2.95, 16.8, 3.2), 0.12))

# --- Cloth effigies hanging by the neck from the threads ------------------------------------
cloth = material("title_effigy_cloth", (0.11, 0.095, 0.075), 0.9)
straw = material("title_effigy_straw", (0.13, 0.095, 0.05), 0.95)


def effigy(top, drop, height, tilt):
    """Hangs from `top`; the returned pivot swings the cord and doll together."""
    pivot = link(bpy.data.objects.new("title_effigy_pivot", None))
    pivot.location = top
    thread(top, (top[0], top[1], top[2] - drop), 0.0, 0.0025, "title_effigy_cord", parent=pivot)
    root = link(bpy.data.objects.new("title_effigy", None))
    root.parent = pivot
    parts = [
        ("UV_SPHERE", (0, 0, -0.09), (0.045, 0.042, 0.05), cloth),
        ("CYLINDER", (0, 0, -0.2), (0.05, 0.035, 0.09), cloth),
        ("CYLINDER", (0.075, 0, -0.17), (0.012, 0.012, 0.06), straw),
        ("CYLINDER", (-0.075, 0, -0.17), (0.012, 0.012, 0.06), straw),
        ("CYLINDER", (0.025, 0, -0.33), (0.014, 0.014, 0.07), straw),
        ("CYLINDER", (-0.025, 0, -0.33), (0.014, 0.014, 0.07), straw),
        ("TORUS", (0, 0, -0.14), (0.03, 0.03, 0.03), thread_mat),
    ]
    for kind, loc, scale, mat in parts:
        if kind == "UV_SPHERE":
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8)
        elif kind == "TORUS":
            bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.25)
        else:
            bpy.ops.mesh.primitive_cylinder_add(vertices=10)
        o = bpy.context.active_object
        o.location, o.scale = loc, scale
        if loc[0] and kind == "CYLINDER" and loc[2] > -0.25:
            o.rotation_euler = (0, math.copysign(0.5, loc[0]), 0)
        o.data.materials.append(mat)
        o.parent = root
    root.scale = (height / 0.4,) * 3
    root.location = (0, 0, -drop)
    root.rotation_euler = (0, 0, tilt)
    pivot.rotation_euler = (rng.normal(0, 0.05), rng.normal(0, 0.05), 0)
    return pivot


effigies = []
for web, k, drop, h in [(0, 14, 0.42, 0.34), (1, 12, 0.55, 0.3), (3, 11, 0.3, 0.32), (7, 13, 0.6, 0.36), (8, 9, 0.38, 0.28), (10, 16, 0.5, 0.33)]:
    p = webs[web][k]
    effigies.append(effigy((p.x, p.y, p.z), drop, h, rng.uniform(-1.2, 1.2)))
for pivot in effigies:
    CORDS.extend(o for o in pivot.children_recursive if o.type == "MESH")

# Hanks of hair knotted along the cords, and blood beading under them.
for web, k, length in [(1, 9, 0.34), (2, 15, 0.26), (4, 10, 0.3), (6, 6, 0.4), (9, 17, 0.28), (11, 11, 0.36), (5, 7, 0.22)]:
    p = webs[web][k]
    hair_tuft((p.x, p.y, p.z), length)
for pts in webs:
    for k in rng.choice(np.arange(3, 22), 4, replace=False):
        bead(pts[k], rng.uniform(0.7, 1.4))

# --- Painted ritual circle, a drag smear and paper charms ------------------------------------
def scribble(canvas, cx, cy, size, strokes, value, width):
    """Hand-drawn mark: jittered polyline segments splatted into canvas."""
    h, w = canvas.shape
    for _ in range(strokes):
        x, y = cx + rng.normal(0, size * 0.3), cy + rng.normal(0, size * 0.3)
        ang = rng.uniform(0, math.tau)
        for _ in range(rng.integers(3, 7)):
            ang += rng.normal(0, 1.1)
            n = int(size * rng.uniform(0.3, 0.8))
            for i in range(n):
                x += math.cos(ang)
                y += math.sin(ang)
                xi, yi = int(x), int(y)
                r = width
                if 0 <= xi - r and xi + r < w and 0 <= yi - r and yi + r < h:
                    canvas[yi - r : yi + r + 1, xi - r : xi + r + 1] = np.maximum(canvas[yi - r : yi + r + 1, xi - r : xi + r + 1], value)


def blur(a, r):
    k = 2 * r + 1
    c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode="edge"), axis=0)
    a = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)), mode="edge"), axis=1)
    return (c[:, k:] - c[:, :-k]) / k


N = 1024
yy, xx = np.mgrid[0:N, 0:N] / N - 0.5
rad = np.hypot(xx, yy)
ang = np.arctan2(yy, xx)
wob = 0.006 * np.sin(ang * 7 + 1.3) + 0.004 * np.sin(ang * 19)
paint = np.zeros((N, N), np.float32)
for r0, wdt in [(0.46, 0.012), (0.43, 0.006), (0.3, 0.008)]:
    paint = np.maximum(paint, np.clip(1 - np.abs(rad - r0 - wob) / wdt, 0, 1))
# Spokes between the rings and marks in each bay.
for k in range(13):
    a = k / 13 * math.tau + 0.2
    spoke = np.abs(np.sin(ang - a)) * rad
    paint = np.maximum(paint, np.clip(1 - spoke / 0.004, 0, 1) * ((rad > 0.3) & (rad < 0.43)) * (np.cos(ang - a) > 0))
    mx, my = (0.5 + 0.365 * math.cos(a + 0.24)) * N, (0.5 + 0.365 * math.sin(a + 0.24)) * N
    scribble(paint, mx, my, 34, 2, 0.9, 2)
# A triangle in the centre, where the figure stands.
for k in range(3):
    a0, a1 = k / 3 * math.tau - math.pi / 2, (k + 1) / 3 * math.tau - math.pi / 2
    p0 = np.array([0.5 + 0.26 * math.cos(a0), 0.5 + 0.26 * math.sin(a0)]) * N
    p1 = np.array([0.5 + 0.26 * math.cos(a1), 0.5 + 0.26 * math.sin(a1)]) * N
    for t in np.linspace(0, 1, 600):
        x, y = (p0 + (p1 - p0) * t + rng.normal(0, 0.6, 2)).astype(int)
        paint[y - 3 : y + 4, x - 3 : x + 4] = 1
fray = rng.random((N, N)) * 0.35 + blur(rng.random((N, N)).astype(np.float32), 6) * 0.8
alpha = np.clip(blur(paint, 1) * 1.6 - fray * 0.55, 0, 1) * 0.92
rgba = np.zeros((N, N, 4), np.float32)
rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3] = 0.2, 0.008, 0.006, alpha
circle_mat = material("title_ritual_circle", (0.045, 0.002, 0.002), 0.5, image=numpy_image("title_circle", rgba), alpha=True)
CIRCLE = (1.45, 15.55)
plane("title_ritual_circle", (3.3, 3.3), (*CIRCLE, FLOOR + 0.004), (0, 0, 0.3), circle_mat)

# Something was dragged from the circle out of the back door.
SW, SH = 256, 1024
streak = np.zeros((SH, SW), np.float32)
for _ in range(26):
    x = rng.normal(SW / 2, SW * 0.14)
    wgt = rng.uniform(1.5, 7)
    x0 = np.clip(x + np.cumsum(rng.normal(0, 0.25, SH)), 0, SW - 1)
    fade = np.clip(np.linspace(1.0, rng.uniform(-0.6, 0.4), SH), 0, 1) * rng.uniform(0.4, 1)
    cols = np.arange(SW)[None, :]
    streak = np.maximum(streak, np.clip(1 - np.abs(cols - x0[:, None]) / wgt, 0, 1) * fade[:, None])
rgba = np.zeros((SH, SW, 4), np.float32)
rgba[..., 0], rgba[..., 1], rgba[..., 2] = 0.16, 0.006, 0.005
rgba[..., 3] = np.clip(streak * 1.2 - rng.random((SH, SW)) * 0.25, 0, 1) * 0.85
smear_mat = material("title_smear", (0.04, 0.002, 0.002), 0.4, image=numpy_image("title_smear", rgba), alpha=True)
start, end = Vector((CIRCLE[0] + 0.3, CIRCLE[1] + 1.2, 0)), Vector((2.35, 18.1, 0))
mid = (start + end) / 2
d = end - start
plane("title_smear", (0.42, d.length), (mid.x, mid.y, FLOOR + 0.003), (0, 0, math.atan2(-d.x, d.y)), smear_mat)

# Paper charms with red brush marks (abstract marks, not writing).
PW, PH = 160, 256
for i, (loc, rot) in enumerate([
    ((2.94, 12.9, 3.85), (math.pi / 2, 0, -math.pi / 2)),
    ((2.94, 14.9, 3.55), (math.pi / 2, 0.08, -math.pi / 2)),
    ((2.94, 15.4, 3.95), (math.pi / 2, -0.12, -math.pi / 2)),
    ((1.82, 17.93, 3.6), (math.pi / 2, 0.05, 0)),
    ((0.55, 17.93, 4.05), (math.pi / 2, -0.1, 0)),
    ((-0.6, 17.93, 3.7), (math.pi / 2, 0.15, 0)),
    ((2.94, 16.6, 4.25), (math.pi / 2, 0.2, -math.pi / 2)),
]):
    ink = np.zeros((PH, PW), np.float32)
    for row in range(rng.integers(3, 6)):
        scribble(ink, PW / 2 + rng.normal(0, 8), 40 + row * 44, 30, 2, 1.0, 2)
    paper = np.ones((PH, PW, 4), np.float32)
    stain = blur(rng.random((PH, PW)).astype(np.float32), 9)
    base = np.stack([0.55 + 0.2 * stain, 0.48 + 0.18 * stain, 0.33 + 0.12 * stain], -1) * (0.75 + 0.25 * rng.random((PH, PW, 1)))
    red = np.array([0.28, 0.015, 0.012])
    k = np.clip(blur(ink, 1) * 1.4, 0, 1)[..., None]
    paper[..., :3] = base * (1 - k) + red * k
    pm = material(f"title_charm_{i}", (0.5, 0.45, 0.32), 0.85, image=numpy_image(f"title_charm_{i}", paper))
    plane(f"title_charm_{i}", (0.13, 0.2), loc, rot, pm)

# --- Floor candles around the circle ---------------------------------------------------------
wax = material("title_wax", (0.62, 0.57, 0.48), 0.55)
flame = material("title_flame", (1, 0.6, 0.25), 0.5, emit=(1.0, 0.52, 0.18), strength=40)
candles = []
for k in range(13):
    a = k / 13 * math.tau + 0.1
    r = 1.0 + rng.normal(0, 0.03)
    x, y = CIRCLE[0] + 0.85 * r * math.cos(a), CIRCLE[1] + 1.45 * r * math.sin(a)
    h = rng.uniform(0.05, 0.15)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.022, depth=h, location=(x, y, FLOOR + h / 2))
    bpy.context.active_object.data.materials.append(wax)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=1, location=(x, y, FLOOR + h + 0.018))
    f = bpy.context.active_object
    f.scale = (0.006, 0.006, 0.016)
    f.data.materials.append(flame)
    f.visible_shadow = False
    candles.append((f, light("POINT", f"title_candle_{k}", (x, y, FLOOR + h + 0.03), (1.0, 0.42, 0.15), 0.9, 0.01)))

# --- Uncle Sok's coffin, carried in from the tent, lid pushed half open -------------------------
def moved(obj, matrix):
    dup = obj.copy()
    s.collection.objects.link(dup)
    dup.matrix_world = matrix @ obj.matrix_world
    dup.hide_render = False
    return dup


parts = [o for o in s.objects if o.name.startswith("coffin_") and o.type == "MESH"]
bpy.context.view_layer.update()
bottom = min((o.matrix_world @ Vector(c)).z for o in parts if not o.name.startswith(("coffin_lid", "coffin_lamp")) for c in o.bound_box)
TENT = Vector((0.0, 5.9, bottom))

# Long axis down the hall, head toward the altar.
place = Matrix.Translation(Vector((*CIRCLE, FLOOR))) @ Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Translation(-TENT)
# In the tent's frame the coffin is long in X: slide the lid across its width and twist it.
slide = Matrix.Translation(TENT) @ Matrix.Translation((0.12, -0.36, 0.05)) @ Matrix.Rotation(0.2, 4, "Z") @ Matrix.Translation(-TENT)
lid = link(bpy.data.objects.new("title_coffin_lid", None))
lid.location = place @ slide @ (TENT + Vector((0, 0, 0.5)))
bpy.context.view_layer.update()
for o in parts:
    dup = moved(o, place @ slide if o.name.startswith("coffin_lid") else place)
    if o.name.startswith("coffin_lid"):
        dup.parent = lid
        dup.matrix_parent_inverse = lid.matrix_world.inverted()
# --- A new lid: old black lacquer over teak, worn gilt, and everything that went wrong -------------
LID = place @ slide
for o in list(s.objects):
    if o.parent == lid and o.name.startswith(("coffin_lid.", "coffin_lid_gilt_seam")):
        o.hide_render = True
# The tent's gabled profile (across, height), so the garland and cloth still sit on it.
PROFILE = [(0.40, 1.12), (0.40, 1.152), (0.388, 1.166), (0.13, 1.317), (0.05, 1.338), (0.0, 1.342),
           (-0.05, 1.338), (-0.13, 1.317), (-0.388, 1.166), (-0.40, 1.152), (-0.40, 1.12)]
LX = 1.05


def lid_at(x, across, z):
    return LID @ Vector((x, 5.9 + across, z))


def lacquer_material():
    """Black lacquer gone to craquelure, flaking off the teak along a few patches."""
    teak_src = bpy.data.materials["M_funeral_wood"].node_tree
    teak_img = next(n.image for n in teak_src.nodes if n.type == "TEX_IMAGE" and "BC" in n.image.name)
    m = bpy.data.materials.new("title_lid_lacquer")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    teak = nt.nodes.new("ShaderNodeTexImage")
    teak.image = teak_img
    teak.projection = "BOX"
    teak.projection_blend = 0.3
    scale = nt.nodes.new("ShaderNodeMapping")
    scale.inputs["Scale"].default_value = (1.4, 1.4, 1.4)
    nt.links.new(coord.outputs["Object"], scale.inputs["Vector"])
    nt.links.new(scale.outputs["Vector"], teak.inputs["Vector"])
    crack = nt.nodes.new("ShaderNodeTexVoronoi")
    crack.feature = "DISTANCE_TO_EDGE"
    crack.inputs["Scale"].default_value = 38
    crack_line = nt.nodes.new("ShaderNodeMapRange")
    crack_line.inputs["From Min"].default_value, crack_line.inputs["From Max"].default_value = 0.0, 0.035
    crack_line.inputs["To Min"].default_value, crack_line.inputs["To Max"].default_value = 1.0, 0.0
    flake = nt.nodes.new("ShaderNodeTexNoise")
    flake.inputs["Scale"].default_value = 3.2
    flake.inputs["Detail"].default_value = 8
    flake.inputs["Roughness"].default_value = 0.65
    flake_mask = nt.nodes.new("ShaderNodeMapRange")
    flake_mask.inputs["From Min"].default_value, flake_mask.inputs["From Max"].default_value = 0.6, 0.64
    reveal = nt.nodes.new("ShaderNodeMath")
    reveal.operation = "MAXIMUM"
    for n in (crack, flake):
        nt.links.new(coord.outputs["Object"], n.inputs["Vector"])
    nt.links.new(crack.outputs["Distance"], crack_line.inputs["Value"])
    nt.links.new(flake.outputs["Fac"], flake_mask.inputs["Value"])
    nt.links.new(crack_line.outputs["Result"], reveal.inputs[0])
    nt.links.new(flake_mask.outputs["Result"], reveal.inputs[1])
    # Lacquer is near-black with a red undertone; the teak under it is dried and dark.
    dark_teak = nt.nodes.new("ShaderNodeMix")
    dark_teak.data_type = "RGBA"
    dark_teak.blend_type = "MULTIPLY"
    dark_teak.inputs["Factor"].default_value = 1.0
    dark_teak.inputs["B"].default_value = (0.42, 0.3, 0.24, 1)
    nt.links.new(teak.outputs["Color"], dark_teak.inputs["A"])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["A"].default_value = (0.016, 0.008, 0.007, 1)
    nt.links.new(reveal.outputs[0], col.inputs["Factor"])
    nt.links.new(dark_teak.outputs["Result"], col.inputs["B"])
    nt.links.new(col.outputs["Result"], bsdf.inputs["Base Color"])
    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value, rough.inputs["To Max"].default_value = 0.3, 0.75
    nt.links.new(reveal.outputs[0], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], bsdf.inputs["Roughness"])
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 140
    nt.links.new(coord.outputs["Object"], grain.inputs["Vector"])
    height = nt.nodes.new("ShaderNodeMath")
    height.operation = "MULTIPLY_ADD"
    height.inputs[1].default_value = -0.6
    nt.links.new(reveal.outputs[0], height.inputs[0])
    nt.links.new(grain.outputs["Fac"], height.inputs[2])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(height.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def worn_gilt_material():
    m = material("title_gilt_worn", (0.55, 0.38, 0.13), 0.38)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    grime = nt.nodes.new("ShaderNodeTexNoise")
    grime.inputs["Scale"].default_value = 22
    grime.inputs["Detail"].default_value = 6
    mask = nt.nodes.new("ShaderNodeMapRange")
    mask.inputs["From Min"].default_value, mask.inputs["From Max"].default_value = 0.42, 0.58
    nt.links.new(grime.outputs["Fac"], mask.inputs["Value"])
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["A"].default_value = (0.55, 0.38, 0.13, 1)
    col.inputs["B"].default_value = (0.03, 0.02, 0.012, 1)
    nt.links.new(mask.outputs["Result"], col.inputs["Factor"])
    nt.links.new(col.outputs["Result"], bsdf.inputs["Base Color"])
    metal = nt.nodes.new("ShaderNodeMapRange")
    metal.inputs["To Min"].default_value, metal.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(mask.outputs["Result"], metal.inputs["Value"])
    nt.links.new(metal.outputs["Result"], bsdf.inputs["Metallic"])
    return m


lacquer, gilt = lacquer_material(), worn_gilt_material()
bm = bmesh.new()
rings = []
for i in range(43):
    x = -LX + 2 * LX * i / 42
    # Old boards are not true: a faint sag along the length and a lift at the corners.
    sag = -0.004 * math.sin(math.pi * i / 42)
    rings.append([bm.verts.new(lid_at(x, a, z + sag * (z > 1.2))) for a, z in PROFILE])
for r0, r1 in zip(rings, rings[1:]):
    n = len(r0)
    for j in range(n):
        bm.faces.new((r0[j], r1[j], r1[(j + 1) % n], r0[(j + 1) % n]))
bm.faces.new(list(reversed(rings[0])))
bm.faces.new(rings[-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
mesh = bpy.data.meshes.new("title_lid")
bm.to_mesh(mesh)
bm.free()
for poly in mesh.polygons:
    poly.use_smooth = True
lid_body = link(bpy.data.objects.new("title_lid", mesh))
lid_body.data.materials.append(lacquer)
bev = lid_body.modifiers.new("bevel", "BEVEL")
bev.width, bev.segments, bev.limit_method, bev.harden_normals = 0.006, 3, "ANGLE", True
lid_body.modifiers.new("normals", "WEIGHTED_NORMAL").keep_sharp = True


def strip(points, radius, mat, name="title_lid_trim", resolution=3):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    sp = curve.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, v in zip(sp.points, points):
        p.co = (*v, 1)
    o = link(bpy.data.objects.new(name, curve))
    o.data.materials.append(mat)
    return o


# Gilt mouldings along the eaves and the ridge, and round both gables.
for a, z in [(0.392, 1.162), (-0.392, 1.162), (0.0, 1.344)]:
    strip([lid_at(-LX - 0.004, a, z), lid_at(LX + 0.004, a, z)], 0.006, gilt)
for x in (-LX - 0.006, LX + 0.006):
    inset = [(a * 0.86, 1.12 + (z - 1.12) * 0.86 + 0.012) for a, z in PROFILE[2:-2]]
    strip([lid_at(x, a, z) for a, z in inset] + [lid_at(x, inset[0][0], inset[0][1])], 0.004, gilt)
# A gilt medallion on the foot gable.
bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.045, depth=0.008, location=lid_at(-LX - 0.006, 0, 1.225))
medal = bpy.context.active_object
medal.rotation_euler = (LID.to_3x3() @ Vector((1, 0, 0))).to_track_quat("Z", "Y").to_euler()
medal.data.materials.append(gilt)


def paint(w, h):
    return np.zeros((h, w), np.float32)


def capsule(c, p0, p1, r, value=1.0):
    """Splats a rounded stroke from p0 to p1 into c (pixels)."""
    h, w = c.shape
    x0, y0 = int(max(0, min(p0[0], p1[0]) - r - 2)), int(max(0, min(p0[1], p1[1]) - r - 2))
    x1, y1 = int(min(w, max(p0[0], p1[0]) + r + 3)), int(min(h, max(p0[1], p1[1]) + r + 3))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.array(p1, np.float32) - np.array(p0, np.float32)
    t = np.clip(((xx - p0[0]) * d[0] + (yy - p0[1]) * d[1]) / max(1e-6, d @ d), 0, 1)
    dist = np.hypot(xx - p0[0] - t * d[0], yy - p0[1] - t * d[1])
    c[y0:y1, x0:x1] = np.maximum(c[y0:y1, x0:x1], np.clip((r - dist) / 1.5, 0, 1) * value)


def handprint(c, cx, cy, size, angle, drag=0.0, drag_angle=None):
    """A bloody hand pressed flat (pixels, size = hand length), optionally dragged."""
    ca, sa = math.cos(angle), math.sin(angle)

    def at(u, v):
        return (cx + (u * ca - v * sa) * size, cy + (u * sa + v * ca) * size)

    capsule(c, at(-0.08, 0.12), at(0.08, 0.12), 0.2 * size)  # palm
    capsule(c, at(-0.04, 0.02), at(0.04, 0.24), 0.17 * size)
    for u, ln, wd in [(-0.13, 0.34, 0.045), (-0.045, 0.4, 0.05), (0.045, 0.38, 0.048), (0.13, 0.3, 0.042)]:
        capsule(c, at(u * 0.9, -0.02), at(u * 1.25, -ln), wd * size)
    capsule(c, at(0.17, 0.16), at(0.36, -0.02), 0.055 * size)  # thumb
    if drag:
        da = angle + math.pi / 2 if drag_angle is None else drag_angle
        src = c.copy()
        steps = int(drag * size)
        for k in range(1, steps, 2):
            dx, dy = int(math.cos(da) * k), int(math.sin(da) * k)
            fade = (1 - k / steps) ** 1.5 * 0.85
            c[:] = np.maximum(c, np.roll(np.roll(src, dy, 0), dx, 1) * fade)


def drips(c, mask_rows, count, max_len, rnd):
    """Runs of blood falling from the lower edge of what is already painted (down = +y)."""
    h, w = c.shape
    cols = np.where(c.max(0) > 0.5)[0]
    if not len(cols):
        return
    for x in rnd.choice(cols, count):
        ys = np.where(c[:, x] > 0.5)[0]
        y = ys.max()
        ln = int(rnd.uniform(0.2, 1) * max_len)
        wd = rnd.uniform(1.2, 2.6)
        xs = x + np.cumsum(rnd.normal(0, 0.15, ln))
        for k in range(ln):
            capsule(c, (xs[k], y + k), (xs[k], y + k + 1), wd * (1 - 0.4 * k / ln))
        capsule(c, (xs[-1], y + ln), (xs[-1], y + ln + 2), wd * 1.6)


def gouges(c, x, y, angle, length, rnd, n=4):
    """Fingernail gouges: parallel jagged scratches."""
    for k in range(n):
        ox, oy = -math.sin(angle) * k * 11, math.cos(angle) * k * 11
        px, py = x + ox, y + oy
        ln = length * rnd.uniform(0.6, 1)
        for i in range(int(ln / 4)):
            a = angle + rnd.normal(0, 0.12)
            nx, ny = px + math.cos(a) * 4, py + math.sin(a) * 4
            capsule(c, (px, py), (nx, ny), 1.4 * (1 - i * 4 / ln) + 0.4)
            px, py = nx, ny


def decal_material(name, blood, scratch=None):
    """Blood (wet, near black-red) and, optionally, gouges down to pale wood."""
    h, w = blood.shape
    alpha = blood if scratch is None else np.maximum(blood, scratch)
    fresh = blur(rng.random((h, w)).astype(np.float32), 12)
    rgba = np.zeros((h, w, 4), np.float32)
    # Byte images are sRGB: these read as wet arterial red in the lamp light, near black in shadow.
    col_blood = np.stack([0.42 + 0.18 * fresh, 0.03 + 0.02 * fresh, 0.022 + 0.01 * fresh], -1)
    if scratch is not None:
        k = np.clip(scratch - blood, 0, 1)[..., None]
        col_blood = col_blood * (1 - k) + np.array([0.66, 0.5, 0.34]) * k
    rgba[..., :3] = col_blood
    rgba[..., 3] = np.clip(alpha * (0.85 + 0.15 * fresh), 0, 1)
    m = material(name, (0.1, 0.004, 0.003), 0.2, image=numpy_image(name, rgba))
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Coat Weight"].default_value = 0.4
    if scratch is not None:
        sc = numpy_image(name + "_depth", np.repeat(blur(scratch, 1)[..., None], 4, -1))
        stex = nt.nodes.new("ShaderNodeTexImage")
        stex.image = sc
        bump = nt.nodes.new("ShaderNodeBump")
        bump.invert = True
        bump.inputs["Strength"].default_value = 0.8
        bump.inputs["Distance"].default_value = 0.002
        nt.links.new(stex.outputs["Color"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def decal(name, corners, mat):
    """A quad laid on the lid from four world-space corners (UV 0..1, top row = v 1)."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(c) for c in corners], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new()
    for li, (u, v) in zip(mesh.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[li.index].uv = (u, v)
    o = link(bpy.data.objects.new(name, mesh))
    o.data.materials.append(mat)
    return o


drnd = np.random.default_rng(66)
# The near slope (the side the lid was pushed toward): hands that slid off it, and gouges.
SW_, SH_ = 2100, 330
slope_blood, slope_scratch = paint(SW_, SH_), paint(SW_, SH_)
handprint(slope_blood, 1220, 120, 190, 0.25, 0.9)
handprint(slope_blood, 1540, 150, 175, -0.35, 1.1)
handprint(slope_blood, 760, 170, 160, 0.1, 0.5)
drips(slope_blood, None, 14, 120, drnd)
gouges(slope_scratch, 380, 60, 0.5, 260, drnd)
gouges(slope_scratch, 1780, 40, 1.2, 240, drnd, 3)
slope_blood = np.clip(blur(slope_blood, 1) - blur(drnd.random((SH_, SW_)).astype(np.float32), 3) * 0.35, 0, 1)
off = 0.0018
(a0, z0), (a1, z1) = PROFILE[8], PROFILE[7]  # eave to ridge shoulder on the -across side
nrm = Vector((0, -(z1 - z0), (a1 - a0))).normalized()  # outward in the tent frame
nrm = Vector((0, -abs(nrm.y), abs(nrm.z)))
def on_slope(x, t):
    a, z = a0 + (a1 - a0) * t, z0 + (z1 - z0) * t
    return LID @ (Vector((x, 5.9 + a, z)) + nrm * off)
decal("title_lid_hands", [on_slope(-LX + 0.02, 0), on_slope(LX - 0.02, 0), on_slope(LX - 0.02, 1), on_slope(-LX + 0.02, 1)],
      decal_material("title_lid_hands", slope_blood, slope_scratch))

# The foot gable, toward the camera: one hand pressed flat and dragged down it.
GW, GH = 820, 300
gable = paint(GW, GH)
handprint(gable, 560, 205, 170, -0.25, 0.5, math.pi / 2 + 0.3)
handprint(gable, 250, 250, 120, 0.4, 0.35, math.pi / 2)
drips(gable, None, 9, 110, drnd)
gable = np.clip(blur(gable, 1) - blur(drnd.random((GH, GW)).astype(np.float32), 3) * 0.3, 0, 1)
# Only on the gable itself: nothing above the roof line.
gu = 0.41 - (np.arange(GW) + 0.5) / GW * 0.82
roof = np.interp(gu, [a for a, _ in PROFILE[::-1]], [z for _, z in PROFILE[::-1]])
gz = 1.42 - (np.arange(GH)[:, None] + 0.5) / GH * 0.30
gable *= gz < roof[None, :] - 0.006
gx = -LX - 0.0075
decal("title_lid_gable_hand", [lid_at(gx, 0.41, 1.12), lid_at(gx, -0.41, 1.12), lid_at(gx, -0.41, 1.42), lid_at(gx, 0.41, 1.42)],
      decal_material("title_lid_gable_hand", gable))

# Red binding cords that tied the lid down, snapped where it was forced; frayed ends hang.
for x in (-0.78, -0.26, 0.3, 0.82):
    wrap = [lid_at(x, a * 1.02, 1.12 + (z - 1.12) * 1.03 + 0.003) for a, z in PROFILE]
    hang = [lid_at(x + 0.01 * k, -0.415 - 0.006 * k, 1.12 - 0.035 * k) for k in range(1, 8)]
    cord([*wrap[1:], *hang], 0.0055, "title_lid_cord", layer=False)
    fray_top = wrap[0]
    for k in range(5):
        tip = fray_top + LID.to_3x3() @ Vector((rng.normal(0, 0.01), rng.uniform(0.01, 0.04), -rng.uniform(0.04, 0.08)))
        cord([fray_top, fray_top.lerp(tip, 0.5) + Vector((0, 0, -0.01)), tip], 0.0014, "title_lid_fray", layer=False)
    end = hang[-1]
    for k in range(5):
        tip = end + Vector((rng.normal(0, 0.012), rng.normal(0, 0.012), -rng.uniform(0.02, 0.05)))
        cord([end, tip], 0.0014, "title_lid_fray", layer=False)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.011, location=lid_at(x, 0.0, 1.352))
    bpy.context.active_object.data.materials.append(thread_mat)

# Long black hair spilling out of the gap and over the foot of the coffin.
edge = (slide @ Vector((-0.95, 6.3, 1.12))).y
hrnd = np.random.default_rng(51)
for clump in range(11):
    cy = hrnd.uniform(edge + 0.03, 6.22)
    length = hrnd.choice([hrnd.uniform(0.1, 0.22), hrnd.uniform(0.3, 0.5)])
    lift = hrnd.uniform(0.0, 0.012)
    for _ in range(36):
        spread = hrnd.normal(0, 0.018)
        stray = hrnd.random() < 0.18
        ln = length * hrnd.uniform(0.55, 1.1)
        phase, freq = hrnd.uniform(0, math.tau), hrnd.uniform(4, 9)
        x0 = hrnd.uniform(-0.88, -0.7)
        rim = Vector((-1.028, cy + spread, 1.122 + lift + hrnd.uniform(0, 0.006)))
        pts = [Vector((x0, cy + spread * 1.6, 0.98)), Vector(((x0 - 1.02) / 2, cy + spread * 1.3, 1.11 + lift)), rim]
        for k in range(1, 11):
            t = k / 10
            # Strands draw together toward the tips; a few wander off on their own.
            y = cy + spread * (1 - 0.65 * t) + 0.008 * math.sin(freq * t + phase) + (hrnd.normal(0, 0.02) * t if stray else 0)
            pts.append(Vector((-1.04 - 0.012 * math.sin(math.pi * min(1, t * 1.5)), y, rim.z - 0.01 - ln * t)))
        c = cord([place @ p for p in pts], 0.0009, "title_coffin_hair", layer=False)
        c.data.materials[0] = hair_mat

# The lid is still tethered to the roof and the altar by cords pulled taut.
for (x, a, z), target, sag in [
    ((-0.55, 0.0, 1.36), (2.95, 14.0, 4.3), 0.12), ((0.45, 0.0, 1.36), (0.6, 15.8, 4.9), 0.08),
    ((0.9, -0.2, 1.3), ALTAR, 0.18),
]:
    thread(lid_at(x, a, z), target, sag)

# Nails torn up along the rim where the lid was forced, bent outward.
iron = material("title_iron", (0.05, 0.032, 0.022), 0.7)
iron.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.5
for k, x in enumerate(np.linspace(-0.9, 0.9, 7)):
    if (slide.inverted() @ Vector((x, 6.215, 1.114))).y - 5.9 < 0.42:
        continue  # still under the lid
    base = place @ Vector((x, 6.215, 1.114))
    lean = place.to_3x3() @ Vector((rng.normal(0, 0.15), rng.uniform(0.25, 0.7), 1)).normalized()
    up = base + lean * rng.uniform(0.035, 0.06)
    tip = up + place.to_3x3() @ Vector((0, 0.03, 0.005))
    strip([base, up, tip], 0.0028, iron, "title_nail", 2)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.007, depth=0.003, location=tip)
    head = bpy.context.active_object
    head.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    head.data.materials.append(iron)

# The funeral flowers on the lid have blackened and dried.
for m in bpy.data.materials:
    if m.name.startswith(("M_funeral_petal", "M_funeral_leaf", "M_funeral_flower_heart", "M_funeral_stem")) and m.use_nodes:
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf:
            for l in list(bsdf.inputs["Base Color"].links):
                m.node_tree.links.remove(l)
            leaf = "leaf" in m.name or "stem" in m.name
            bsdf.inputs["Base Color"].default_value = (0.03, 0.025, 0.012, 1) if leaf else (0.07, 0.03, 0.018, 1)
            bsdf.inputs["Roughness"].default_value = 0.85

lamp = next((o for o in s.objects if o.name == "light_flame_coffin"), None)
if lamp:
    light("POINT", "title_coffin_lamp", place @ lamp.matrix_world.translation + Vector((0, 0, 0.04)), (1.0, 0.45, 0.16), 2.5, 0.01)

# --- The black Neak Ta ------------------------------------------------------------------------
if MODE.endswith(("far", "near")):
    src = os.path.join(ROOT, "art-source", "characters", "ancestors", "ancestor-forms.blend")
    with bpy.data.libraries.load(src, link=False) as (_, into):
        into.collections = ["ancestor_shadow"]
    col = into.collections[0]
    s.collection.children.link(col)
    soot = material("title_soot", (0.01, 0.009, 0.008), 0.62)
    eye = material("title_eye", (0.1, 0.05, 0.02), 0.3, emit=(1.0, 0.36, 0.08), strength=18)
    root = link(bpy.data.objects.new("title_presence", None))
    for o in col.objects:
        o.parent = root
        if o.type == "MESH":
            mat = eye if "eye" in o.name or "iris" in o.name else soot
            for i in range(len(o.data.materials)):
                o.data.materials[i] = mat
    root.scale = (0.75,) * 3
    if MODE.endswith("far"):
        root.location, root.rotation_euler = (1.7, 17.35, FLOOR), (0, 0, math.radians(-6))
    else:
        # Beside the open coffin, as if it has just climbed out.
        root.location, root.rotation_euler = (CIRCLE[0] + 0.82, CIRCLE[1] - 0.55, FLOOR), (0, 0, math.radians(-8))

# --- Animation: one seamless loop, every motion periodic in FRAMES -------------------------------
def flicker(t, seed, depth=0.25):
    """Candle-like unsteadiness from whole-cycle sines, so frame FRAMES matches frame 0."""
    r = np.random.default_rng(seed)
    v = sum(r.uniform(0.3, 1) * math.sin(math.tau * (m * t + r.random())) for m in r.choice(np.arange(6, 41), 5, replace=False))
    return 1 + depth * v / 2.5


def kick(t, at=KNOCK / (FRAMES / FPS), tau=0.1):
    """0 before the knock, then a decaying jolt (t in loop fractions)."""
    d = t - at
    return 0.0 if d < 0 else math.exp(-d / tau)


lantern_pivot = None
if MODE == "loop":
    # The hanging lantern swings on a cord from the ridge beam, its light with it.
    lantern_pivot = link(bpy.data.objects.new("title_lantern_pivot", None))
    lantern_pivot.location = (0.0, 14.5, 4.95)
    bpy.context.view_layer.update()
    for o in list(s.objects):
        if o.name in ("Lantern_01.006", "Lantern_01_glass.006", "lantern"):
            o.parent = lantern_pivot
            o.matrix_parent_inverse = lantern_pivot.matrix_world.inverted()
    thread((0.0, 14.5, 4.95), (0.0, 14.5, 4.54), 0.0, 0.003, "title_lantern_cord", parent=lantern_pivot)

    smoke_map = bpy.data.materials["title_smoke"].node_tree
    mapping = smoke_map.nodes.new("ShaderNodeMapping")
    noise_node = next(n for n in smoke_map.nodes if n.type == "TEX_NOISE")
    coord_node = next(n for n in smoke_map.nodes if n.type == "TEX_COORD")
    smoke_map.links.new(coord_node.outputs["Object"], mapping.inputs["Vector"])
    smoke_map.links.new(mapping.outputs["Vector"], noise_node.inputs["Vector"])

    lid_rest = lid.location.copy()
    lights = {o.name: o for o in s.objects if o.type == "LIGHT"}
    for frame in range(1, FRAMES + 1):
        t = (frame - 1) / FRAMES
        gust = kick(t, tau=0.06)
        for k, (fl, li) in enumerate(candles):
            f = flicker(t, 100 + k) * (1 - 0.7 * gust)
            li.data.energy = 0.9 * f
            li.data.keyframe_insert("energy", frame=frame)
            fl.scale = (0.006, 0.006, 0.016 * (0.75 + 0.3 * f))
            fl.rotation_euler = (0, 0.45 * gust + 0.06 * math.sin(math.tau * (9 * t + k * 0.37)), 0)
            fl.keyframe_insert("scale", frame=frame)
            fl.keyframe_insert("rotation_euler", frame=frame)
        for name, base, seed in (("lantern", 10, 200), ("altar_lamp", 9, 201), ("title_coffin_lamp", 2.5, 202)):
            if name in lights:
                lights[name].data.energy = base * flicker(t, seed, 0.12) * (1 - 0.5 * gust)
                lights[name].data.keyframe_insert("energy", frame=frame)
        swing = math.radians(3.5) * math.sin(math.tau * 2 * t) + math.radians(6) * kick(t, tau=0.12) * math.sin(math.tau * 14 * t)
        lantern_pivot.rotation_euler = (swing, swing * 0.4, 0)
        lantern_pivot.keyframe_insert("rotation_euler", frame=frame)
        for n, pivot in enumerate(effigies):
            k = kick(t, tau=0.15)
            ax = math.radians(5) * math.sin(math.tau * ((n % 2) + 1) * t + n) + math.radians(9) * k * math.sin(math.tau * 12 * t + n)
            ay = math.radians(4) * math.sin(math.tau * ((n % 3) + 1) * t + 2 * n)
            # One doll slowly turns round on its cord, toward the door and back.
            az = math.radians(70) * math.sin(math.tau * t) if n == 2 else 0
            pivot.rotation_euler = (ax, ay, az)
            pivot.keyframe_insert("rotation_euler", frame=frame)
        # Something inside lifts the lid three times, hard, then it settles askew.
        hits = sum(kick(t, KNOCK / 8 + n / FRAMES, 0.008) for n in (0, 3, 6))
        lid.location = lid_rest + Vector((0.012 * math.sin(frame * 2.3) * hits, 0.008 * hits, 0.028 * hits))
        lid.rotation_euler = (0.02 * hits, -0.015 * hits, 0)
        lid.keyframe_insert("location", frame=frame)
        lid.keyframe_insert("rotation_euler", frame=frame)
        a = math.tau * t
        mapping.inputs["Location"].default_value = (0.35 * math.cos(a), 0.35 * math.sin(a), 0.1 * math.sin(2 * a))
        mapping.inputs["Location"].keyframe_insert("default_value", frame=frame)
    for action in bpy.data.actions:
        for fc in getattr(action, "fcurves", []):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    s.frame_start, s.frame_end = 1, FRAMES
    s.render.fps = FPS
    # A video frame is on screen for 40 ms under grain: trade samples for frames.
    s.render.use_persistent_data = True
    s.cycles.volume_step_rate = 3
    s.cycles.max_bounces = 4

THREADS = MODE.startswith("threads-")
if MODE in ("empty", "far", "near"):
    # The cords are their own layer; the plates keep only their shadows.
    for o in CORDS:
        o.visible_camera = False
if THREADS:
    # Only the cords, dolls and hair render; the room and the Neak Ta cut them out.
    s.render.film_transparent = True
    keep = set(CORDS)
    for o in s.objects:
        if o.type in ("MESH", "CURVE") and o not in keep:
            o.is_holdout = True
    bpy.data.objects["title_haze"].hide_render = True
    bpy.data.objects["title_smoke"].hide_render = True

if FIGURE:
    # Only the figure renders; everything in front of it cuts it out, nothing else shows.
    s.render.film_transparent = True
    for o in s.objects:
        if o.type in ("MESH", "CURVE") and not o.name.startswith("ancestor_"):
            o.is_holdout = True
    bpy.data.objects["title_haze"].hide_render = True
    bpy.data.objects["title_smoke"].hide_render = True

# Just inside the front door, looking down the hall to the altar and the back door.
cam_data = bpy.data.cameras.new("title_cam")
cam_data.lens, cam_data.clip_start = 20, 0.05
cam = bpy.data.objects.new("title_cam", cam_data)
s.collection.objects.link(cam)
cam.location = (1.95, 11.75, 3.9)
cam.rotation_euler = (Vector((1.45, 18, 3.6)) - cam.location).to_track_quat("-Z", "Y").to_euler()
# Lens shift puts the hall in the right of the frame, leaving the dark left for the menu.
cam_data.shift_x = SHIFT
s.camera = cam

s.render.image_settings.file_format = "PNG"
if FIGURE or THREADS:
    s.render.image_settings.color_mode = "RGBA"
if MODE == "loop" and len(argv) > 4:
    # Spot-check chosen frames, e.g. "1,121,124".
    for frame in (int(f) for f in argv[4].split(",")):
        s.frame_set(frame)
        s.render.filepath = os.path.join(OUT, f"check_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
elif MODE == "loop":
    s.render.filepath = os.path.join(OUT, "frame_")
    bpy.ops.render.render(animation=True)
elif MODE == "threads-data":
    # Each web cord as a polyline in frame fractions (0..1, y down), for the screen's blood beads.
    from bpy_extras.object_utils import world_to_camera_view

    bpy.context.view_layer.update()
    lines = []
    for pts in LINES:
        uv = [world_to_camera_view(s, cam, p) for p in pts]
        if any(0 < c.x < 1 and 0 < c.y < 1 and c.z > 0 for c in uv):
            lines.append([[round(c.x, 4), round(1 - c.y, 4)] for c in uv])
    altar = world_to_camera_view(s, cam, Vector(ALTAR))
    with open(OUT, "w") as f:
        f.write("// Generated by tools/ui/render-title-scene.py (threads-data); do not edit.\n")
        f.write("/** Where the red cords cross the title plates, in frame fractions (y down). */\n")
        f.write(f"export const ALTAR: [number, number] = [{altar.x:.4f}, {1 - altar.y:.4f}];\n")
        f.write("export const CORDS: [number, number][][] = " + str(lines).replace(" ", "") + ";\n")
else:
    s.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
