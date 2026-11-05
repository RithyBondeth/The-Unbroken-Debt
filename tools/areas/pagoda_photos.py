"""Funeral photographs set into the stupas: real Cambodians photographed by Léon Busy in 1921
(Archives de la Planète, Musée Albert-Kahn; CC0 on Wikimedia Commons, see the `archive`
section of art-source/library/polyhaven.json), cropped to head and shoulders and printed
as old glazed oval portraits: faded to sepia, crazed, water-stained, and some with the
eyes or the whole face scratched away by someone who did not want to be looked at.

These are real, unnamed people, so all of this is an advisor-review item. Colonial
anthropometric photographs must never be used here.
"""
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / 'art-source/library/archive'
TEXTURES = ROOT / 'art-source/textures/ep2'

FAMILY = 'Un_fonctionnaire_cambodgien_et_sa_famille_A36130.jpg'
MONK = 'Un_bonze_revenant_de_la_quete_A35898.jpg'
# Who is in the frame: file, centre of the crop in source pixels, width of the crop, and
# where the eyes sit in the crop (x, y from the top), for the scratches that seek them.
SITTERS = {
    'woman': (FAMILY, (1298, 905), 250, (.535, .4)),
    'man': (FAMILY, (1617, 880), 250, (.535, .28)),
    'elder_girl': (FAMILY, (1803, 925), 210, (.53, .48)),
    'girl': (FAMILY, (2087, 925), 210, (.535, .46)),
    'small_girl': (FAMILY, (989, 1115), 170, (.525, .55)),
    'monk': (MONK, (742, 880), 230, (.555, .46)),
}
# The sheet: (sitter, what has been done to it). The cell order is the index used to place one.
SHEET = [('woman', 'faded'), ('man', 'stained'), ('monk', 'faded'), ('elder_girl', 'crazed'),
         ('woman', 'eyes'), ('man', 'face'), ('girl', 'stained'), ('small_girl', 'faded'),
         ('monk', 'eyes'), ('girl', 'mould'), ('elder_girl', 'face'), ('small_girl', 'burnt')]
COLS, ROWS = 4, 3
CELL_W, CELL_H = 512, 682


def _load(name):
    img = bpy.data.images.load(str(ARCHIVE / name), check_existing=True)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)[::-1, :, :3]  # row 0 at the top, as the coordinates above


def _resize(a, w, h):
    """Bilinear resize of an (h, w) array."""
    ys = np.linspace(0, a.shape[0] - 1, h)
    xs = np.linspace(0, a.shape[1] - 1, w)
    y0, x0 = ys.astype(int), xs.astype(int)
    y1, x1 = np.minimum(y0 + 1, a.shape[0] - 1), np.minimum(x0 + 1, a.shape[1] - 1)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    return (a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx) * (1 - fy) + (a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx) * fy


def _noise(rng, h, w, scale, octaves=4):
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.rfftfreq(w)[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    for o in range(octaves):
        s = scale / 2 ** o
        field = np.fft.irfft2(np.fft.rfft2(rng.normal(size=(h, w))) * np.exp(-(radius * s) ** 2), s=(h, w))
        out += amp * (field / (field.std() + 1e-6)).astype(np.float32)
        total += amp
        amp *= .55
    return np.clip(out / total * .4 + .5, 0, 1)


def _scratch(img, rng, x0, y0, x1, y1, width, value, wander=.06):
    """A gouge from (x0, y0) to (x1, y1), in cell fractions, wandering a little."""
    h, w = img.shape
    steps = int(math.hypot((x1 - x0) * w, (y1 - y0) * h)) + 2
    dx = rng.normal(0, wander)
    dy = rng.normal(0, wander)
    for k in range(steps):
        t = k / steps
        bow = math.sin(t * math.pi)
        x = int((x0 + (x1 - x0) * t + dx * bow) * w)
        y = int((y0 + (y1 - y0) * t + dy * bow) * h)
        r = max(1, int(width * (.5 + .7 * bow) * rng.uniform(.6, 1.3)))
        img[max(0, y - r):min(h, y + r), max(0, x - r):min(w, x + r)] = value


def _print(sitter, damage, rng):
    name, (cx, cy), crop_w, eyes = SITTERS[sitter]
    src = _load(name)
    crop_h = int(crop_w * CELL_H / CELL_W)
    x0, y0 = max(0, cx - crop_w // 2), max(0, cy - crop_h // 2)
    lum = src[y0:y0 + crop_h, x0:x0 + crop_w].mean(-1)
    lum = _resize(lum, CELL_W, CELL_H)
    # A soft old print: blurred by a slow lens and years, faded, its blacks gone brown.
    lo, hi = np.percentile(lum, 3), np.percentile(lum, 97)
    lum = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)
    tone = .12 + lum * .68
    tone += (_noise(rng, CELL_H, CELL_W, 3, 2) - .5) * .022  # grain
    h, w = CELL_H, CELL_W
    yy, xx = np.mgrid[0:h, 0:w]
    u, v = (xx + .5) / w, (yy + .5) / h
    oval = np.hypot((u - .5) / .46, (v - .5) / .48)
    # Printed as a vignette, fading to the paper at the oval's edge.
    tone = tone * (1 - np.clip((oval - .72) / .28, 0, 1)) + .76 * np.clip((oval - .72) / .28, 0, 1)
    ex, ey = eyes
    if damage in ('stained', 'mould', 'burnt'):
        # Water got behind the glaze once or twice: a soft browned stain with a dark edge,
        # risen from the bottom of the oval.
        field = _noise(rng, h, w, 210, 3) + (v - .5) * .5
        level = rng.uniform(.5, .62)
        tide = np.abs(field - level)
        wet = np.clip((field - level) / .1, 0, 1)
        tone = tone * (1 - .32 * np.exp(-((tide / .007) ** 2))) * (1 - .3 * wet)
    if damage == 'crazed' or damage == 'eyes' or damage == 'face':
        web = np.abs(_noise(rng, h, w, 36, 3) - .5)
        tone *= 1 - .5 * np.exp(-((web / .006) ** 2))
    if damage == 'eyes':
        # Gouged out: bright bare enamel where the eyes were, again and again.
        for sx in (-.1, .1):
            for _ in range(int(rng.integers(9, 15))):
                a = rng.uniform(0, math.tau)
                ln = rng.uniform(.03, .07)
                _scratch(tone, rng, ex + sx - math.cos(a) * ln, ey - math.sin(a) * ln, ex + sx + math.cos(a) * ln, ey + math.sin(a) * ln, 2.2, rng.uniform(.82, .97), .01)
    if damage == 'face':
        for _ in range(int(rng.integers(48, 70))):
            cx_, cy_ = rng.normal(ex, .08), rng.normal(ey + .06, .08)
            a = rng.uniform(0, math.tau)
            ln = rng.uniform(.05, .2)
            _scratch(tone, rng, cx_ - math.cos(a) * ln, cy_ - math.sin(a) * ln, cx_ + math.cos(a) * ln, cy_ + math.sin(a) * ln, 2.5, rng.uniform(.8, .98), .03)
    colour = np.dstack([tone * 1.0, tone * .87, tone * .66])
    if damage == 'mould':
        # Mould creeping in from one side, soft at its edge and speckled ahead of it.
        front = _noise(rng, h, w, 110, 4) * 1.1 + (v - .42) * .9 + (u - .5) * .4
        bloom = np.clip((front - .62) / .14, 0, 1)
        speck = np.clip((_noise(rng, h, w, 7, 3) - .56) * 12, 0, 1) * np.clip((front - .42) / .2, 0, 1)
        bloom = np.maximum(bloom, speck)
        colour = colour * (1 - bloom[..., None] * .86) + np.array([.035, .05, .03]) * bloom[..., None] * .86
    if damage == 'burnt':
        d = np.hypot(u - (ex + .03), (v - (ey + .1)) * h / w) + (_noise(rng, h, w, 18, 3) - .5) * .12
        char = np.clip((.2 - d) / .03, 0, 1)
        scorch = np.clip((.31 - d) / .11, 0, 1)
        colour *= 1 - scorch[..., None] * .75
        colour = colour * (1 - char[..., None]) + .012 * char[..., None]
    return np.clip(colour, 0, 1).astype(np.float32)


def photo_sheet(seed=1921):
    """Prints every portrait onto one texture. Returns the image."""
    rng = np.random.default_rng(seed)
    sheet = np.zeros((CELL_H * ROWS, CELL_W * COLS, 3), np.float32)
    for k, (sitter, damage) in enumerate(SHEET):
        c, r = k % COLS, k // COLS
        sheet[r * CELL_H:(r + 1) * CELL_H, c * CELL_W:(c + 1) * CELL_W] = _print(sitter, damage, rng)
    h, w = sheet.shape[:2]
    img = bpy.data.images.new('T_ep2_funeral_photos_BC', w, h)
    rgba = np.dstack([sheet, np.ones((h, w), np.float32)])
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = str(TEXTURES / 'T_ep2_funeral_photos_BC.png')
    img.file_format = 'PNG'
    img.save()
    img.pack()
    return img


def photo_materials(img):
    """Glazed enamel for the portrait, old bronze for its rim."""
    glaze = bpy.data.materials.new('M_ep2_funeral_photo')
    nt = glaze.node_tree
    b = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    nt.links.new(tex.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = .24
    rim = bpy.data.materials.new('M_ep2_funeral_photo_rim')
    b = rim.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (.08, .07, .045, 1)
    b.inputs['Metallic'].default_value = .85
    b.inputs['Roughness'].default_value = .62
    return glaze, rim


def plaque(coll, glaze, rim, name, at, facing_yaw, cell, height=.2, tilt=0.0):
    """An oval portrait `height` metres tall on a wall: convex glazed face, bronze rim, set
    at `at` and facing along `facing_yaw` (0 faces -Y). Returns the object."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    half_h, half_w = height / 2, height / 2 * CELL_W / CELL_H
    c, r = cell % COLS, cell // COLS
    u0, u1 = c / COLS, (c + 1) / COLS
    v1, v0 = 1 - r / ROWS, 1 - (r + 1) / ROWS
    rings = 5
    segments = 28
    verts = [[None] * segments for _ in range(rings)]
    centre = bm.verts.new((0, -.012, 0))
    for j in range(rings):
        t = (j + 1) / rings
        bulge = .012 * (1 - t * t)
        for s in range(segments):
            a = s / segments * math.tau
            verts[j][s] = bm.verts.new((math.cos(a) * half_w * t, -bulge, math.sin(a) * half_h * t))

    def uvs(face):
        for loop in face.loops:
            co = loop.vert.co
            loop[uv].uv = (u0 + (u1 - u0) * (.5 + co.x / (2 * half_w) * .96), v0 + (v1 - v0) * (.5 + co.z / (2 * half_h) * .96))
    for s in range(segments):
        t = (s + 1) % segments
        uvs(bm.faces.new((centre, verts[0][s], verts[0][t])))
        for j in range(rings - 1):
            uvs(bm.faces.new((verts[j][s], verts[j + 1][s], verts[j + 1][t], verts[j][t])))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(glaze)
    me.materials.append(rim)
    # The rim, a raised bronze band round the portrait, in the same mesh.
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    prof = [(1.0, -.002), (1.04, -.012), (1.1, -.012), (1.14, -.002), (1.14, .004)]
    rim_rings = []
    for k, y in prof:
        ring = []
        for s in range(segments):
            a = s / segments * math.tau
            ring.append(bm.verts.new((math.cos(a) * half_w * k, y, math.sin(a) * half_h * k)))
        rim_rings.append(ring)
    for j in range(len(prof) - 1):
        for s in range(segments):
            t = (s + 1) % segments
            f = bm.faces.new((rim_rings[j][s], rim_rings[j + 1][s], rim_rings[j + 1][t], rim_rings[j][t]))
            f.material_index = 1
            f.smooth = True
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    o.rotation_mode = 'XYZ'
    o.rotation_euler = (tilt, 0, facing_yaw)
    o.location = at
    return o
