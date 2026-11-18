"""The family's Preah Phum (ព្រះភូមិ, spirit house), Episode 1 save point.

A well-off 1930s household's carved teak spirit house, sixty years of rain and
candle smoke on it: a single turned post on a laterite block, scroll brackets
under a balustraded offering tray, a panelled house with an open doorway (one
leaf thrown back, the other hanging off a broken hinge), and two stacked gables
with naga bargeboards, flame teeth and horn finials. The red lacquer has
faded and flaked to silver-grey wood; the gilt has rubbed through to its red
bole. Inside, black with soot, a small lacquered figure of a kneeling lady
beckoning with her raised hand kneels at the back on her lotus pedestal,
her colours gone dark (art-source/library/scans/phra_phum_lady.glb, the
user's own model, prepared by tools/areas/import-phra-phum-statue.py), and one
candle burns on the floor in front of her. A termite tunnel climbs the post; a mud
wasp has built under the eave; cobweb veils hang in the porch corners.

Blender axes: x east, y north, z up; the doorway faces -y (glTF +Z, the game's
+Z). Game contract (src/episodes/ep1/act1/PhraPhum.ts):
  tray top 1.125 m; chamber floor 1.29 m; candle wicks at (+-0.44, -0.35,
  ~1.28) and one candle inside the chamber at (0, 0.06, ~1.39), in front of
  the figure (phra_phum_lady, pedestal foot at (0, LADY_Y, FLOOR)).
Cultural details are advisor-review items (Cultural Guide).
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

import offerings_kit as kit
import shrine_surfaces as surf
from shrine_craft import Batch, frame, kbach_relief, moulding, place, relief_panel

TRAY_TOP = 1.125
FLOOR = 1.29
EFFIGY = (0.0, 0.10, FLOOR)
LADY_Y = .26             # the figure kneels at the back of the chamber, facing the doorway
WICKS = ((-0.44, -0.35), (0.44, -0.35))
WICK_Z = 1.278

# House body and roofs.
HX = 0.33            # half width of the house body (outer face of the walls)
HY0, HY1 = -0.19, 0.41   # front and back faces of the walls
WALL_TOP = 1.90
# The main roof rests on the side walls; the narrower porch roof sits under its
# front rake, so the stacked gables read from the path.
MAIN = dict(y0=-0.335, y1=0.555, eave_x=0.50, eave_z=1.80, ridge_z=2.40)
PORCH = dict(y0=-0.635, y1=-0.20, eave_x=0.45, eave_z=1.84, ridge_z=2.22)
COLUMNS = ((-0.40, -0.46), (0.40, -0.46))
DOOR_W, DOOR_TOP = .17, 1.755

_mats = {}


def materials():
    if _mats:
        return _mats
    k = kit.materials()
    _mats.update(k)
    _mats["lacquer"] = surf.red_lacquer_teak()
    _mats["gilt"] = surf.gilt()
    _mats["grey"] = surf.grey_teak()
    _mats["soot"] = surf.soot_teak()
    _mats["laterite"] = surf.laterite()
    _mats["cloth"] = surf.cotton("phra_phum_red_cloth", (.42, .05, .04), 2621)
    _mats["mud"] = surf.plain("M_phra_phum_termite_mud", (.20, .12, .07), rough=1.0)
    return _mats


def _naga_mesh():
    """The Cleveland Museum of Art's Khmer bronze naga finial (CC0 scan),
    decimated and normalised: stem foot at the origin, 1 m tall, hood facing -y."""
    name = "phra_phum_naga_source"
    if name in bpy.data.meshes:
        return bpy.data.meshes[name]
    import os
    from kit import LIB
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(LIB, "scans", "naga_finial.glb"))
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    bpy.context.view_layer.update()
    obj = new[0]
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    mesh = obj.data
    # Scans are split along their UV seams; weld them so the decimator can work.
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.0004)
    bm.to_mesh(mesh)
    bm.free()
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.ratio = 2600 / max(1, sum(len(p.vertices) - 2 for p in mesh.polygons))
    with bpy.context.temp_override(object=obj, active_object=obj):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    small = obj.data.copy()
    small.name = name
    for o in [o for o in bpy.data.objects if o not in before]:
        bpy.data.objects.remove(o, do_unlink=True)
    co = np.array([v.co[:] for v in small.vertices])
    zmin, zmax = co[:, 2].min(), co[:, 2].max()
    foot = co[co[:, 2] < zmin + .02 * (zmax - zmin)].mean(axis=0)
    small.transform(Matrix.Scale(1 / (zmax - zmin), 4) @ Matrix.Translation(-Vector(foot)))
    small.update()
    return small


def _gable(b, m, g, front_y, facing, rng, relief=True, naga=True, lacquer_ground=True, tie=True):
    """Bargeboards with flame teeth, naga ends, a horn finial and the pediment
    for a gable in the plane y = front_y. `facing` -1 for a front gable."""
    e, ze, zr = g["eave_x"], g["eave_z"], g["ridge_z"]
    span = math.hypot(e, zr - ze)
    yb = front_y
    yp = front_y - facing * .022  # the pediment sits just inside the bargeboards
    # Tie beam and pediment.
    zb = 1.95
    if tie:
        b.box(m["lacquer"], (2 * (HX + .05), .03, .04), (0, yp, zb + .02), chamfer=.004, tile=.45)
        b.tube(m["gilt"], [(-HX - .04, yp + facing * .016, zb + .04), (HX + .04, yp + facing * .016, zb + .04)], .006, sides=6)
    zb += .04
    if relief:
        # The pediment runs from its base line up into the bargeboards' apex.
        base_z = zb if tie else ze + .02
        half = e * (zr - .03 - base_z) / (zr - ze)
        width = 2 * half
        height = (zr - .03) - base_z
        heights = kbach_relief(512, int(512 * height / width), int(abs(front_y) * 1000) + 7, "pediment")
        # Local x across, y up, z out of the face (toward the viewer).
        out = Vector((0, facing, 0))
        xf = frame((0, yp, base_z), (-facing, 0, 0) if facing > 0 else (1, 0, 0), (0, 0, 1),
                   tuple(out))
        relief_panel(b, m["gilt"], heights, "tri", width, height, .016, xf, nu=120 if g is PORCH else 70,
                     nv=56 if g is PORCH else 32, tile=.14,
                     ground=m["lacquer"] if lacquer_ground else m["gilt"])
    else:
        # Plain upright boards, red, behind the bargeboards.
        half = e * (zr - .03 - zb) / (zr - ze)
        n = 9
        for k in range(n):
            x0 = -half + k * 2 * half / n
            x1 = x0 + 2 * half / n - .003
            xm = (x0 + x1) / 2
            top = zr - .03 - (zr - ze) * abs(xm) / e
            if top - zb > .02:
                b.box(m["lacquer"], (x1 - x0, .02, top - zb), (xm, yp, (top + zb) / 2), tile=.45)
    for s in (-1, 1):
        d = Vector((s * e, 0, ze - zr)).normalized()
        p = Vector((s * (zr - ze), 0, e)).normalized()
        apex = Vector((0, yb, zr))
        end = Vector((s * e, yb, ze)) + d * .06
        w = .055
        pts = [apex + d * (span + .06) * t + p * (w / 2 + .004) for t in np.linspace(0, 1, 8)]
        b.sweep(m["lacquer"], [tuple(q) for q in pts], (0, 1, 0), w, .026, tile=.45)
        # Gilt beading along both edges of the board.
        for off in (.004, w + .004):
            line = [apex + d * (span + .06) * t + p * off + Vector((0, facing * .014, 0)) for t in (0, 1)]
            b.tube(m["gilt"], [tuple(q) for q in line], .0045, sides=5)
        # Flame teeth (bai raka) along the upper edge, leaning toward the apex.
        z_axis = d.cross(p)
        steps = int((span + .02) / .034)
        for k in range(1, steps):
            t = k / steps
            root = apex + d * (span + .06) * t + p * (w + .006)
            tw, th = .011, rng.uniform(.026, .032)
            if rng.random() < .07:
                continue  # broken off
            lean = -.006
            outline = [(-tw, 0), (-tw * .4, th * .35), (lean - tw * .2, th * .7), (lean, th), (lean + tw * .3, th * .62),
                       (tw * .55, th * .3), (tw, 0)]
            b.extrude(m["gilt"], outline, .009, xf=frame(tuple(root), tuple(d), tuple(p), tuple(d.cross(p))), tile=.2)
        if naga:
            # The naga rises from the board's foot, its hood turned out and forward.
            mesh = _naga_mesh()
            scale = .11 if g is MAIN else .10
            yaw = s * math.radians(62) if facing < 0 else s * math.radians(118)
            xf = Matrix.Translation(end + p * .02) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Scale(scale, 4)
            b.add_mesh(m["gilt"], mesh, xf, tile=.25)
    # Horn finial (chofa) at the apex: a slender blade curving up and over.
    pts, widths = [], []
    for k in range(13):
        t = k / 12
        ang = math.radians(10 + 150 * t ** 1.6)
        r = .16
        pts.append((0, yb + facing * (.01 + r * .42 * (1 - math.cos(ang)) * .6),
                    zr + .03 + r * math.sin(min(ang, math.pi / 2)) * (.9 if ang < math.pi / 2 else 1)
                    + (r * .18 * math.sin(ang - math.pi / 2) if ang > math.pi / 2 else 0)))
        widths.append(.034 * (1 - .78 * t) + .004)
    b.sweep(m["gilt"], pts, (1, 0, 0), widths, .02, tile=.25, taper_thick=.007)


def _roof(b, m, g, rng, deck_mat, rafters=True):
    """Two slopes of teak shingles with pointed tips, laid in courses on a deck."""
    e, ze, zr = g["eave_x"], g["eave_z"], g["ridge_z"]
    y0, y1 = g["y0"] - .01, g["y1"] + .01
    run, rise = e, zr - ze
    L = math.hypot(run, rise)
    for s in (-1, 1):
        sd = Vector((-s * run, 0, rise)).normalized()
        nd = Vector((s * rise, 0, run)).normalized()
        ad = sd.cross(nd)
        origin = Vector((s * e, y0 if ad.y > 0 else y1, ze))
        xf = frame(tuple(origin), tuple(ad), tuple(sd), tuple(nd))
        length_a = y1 - y0
        # The deck: boards under the shingles, seen from below.
        b.box(deck_mat, (length_a, L + .02, .012), (length_a / 2, L / 2, -.008), xf=xf, tile=.6)
        pitch, w = .031, .041
        courses = int(L / pitch)
        tiles = int(length_a / w)
        wa = length_a / tiles
        for j in range(courses):
            s0 = j * pitch + .004
            for i in range(tiles):
                if rng.random() < .018 and 1 < j < courses - 2:
                    continue
                a = (i + .5 * (j % 2) + .5) * wa
                if a > length_a - wa * .45:
                    continue
                ja = rng.normal(0, .0012)
                js = rng.normal(0, .0012) - (.008 if rng.random() < .02 else 0)
                lift = .0065 + (.006 if rng.random() < .05 else 0)
                hw = wa / 2 - .0012
                top_s = min(s0 + .085, L + .002)
                mat = m["grey"]
                tip = (a + ja, s0 + js - .013, lift)
                ls = (a + ja - hw, s0 + js + .004, lift - .0008)
                rs = (a + ja + hw, s0 + js + .004, lift - .0008)
                tl = (a + ja - hw, top_s, .0012)
                tr = (a + ja + hw, top_s, .0012)
                low = (0, 0, -.0048)
                verts = [tip, rs, tr, tl, ls,
                         tuple(Vector(ls) + Vector(low)), tuple(Vector(tip) + Vector(low)), tuple(Vector(rs) + Vector(low))]
                faces = [(0, 1, 2, 3, 4), (5, 6, 0, 4), (6, 7, 1, 0)]
                uvs = [(q[0] / .5, q[1] / .5) for q in verts]
                b.add(mat, verts, faces, uvs, smooth=False, xf=xf)
        if rafters:
            # Rafter tails under the eave.
            for k in range(int(length_a / .075) + 1):
                a = .03 + k * .075
                if a > length_a - .02:
                    break
                b.box(m["grey"], (.016, .1, .024), (a, .03, -.026), xf=xf, chamfer=.003, tile=.4)
        # Ridge board.
    b.box(m["lacquer"], (.04, y1 - y0, .04), (0, (y0 + y1) / 2, zr + .012), chamfer=.006, tile=.45)
    for k in range(int((y1 - y0) / .05)):
        y = y0 + .03 + k * .05
        if rng.random() < .1:
            continue
        th = rng.uniform(.026, .034)
        outline = [(-.012, 0), (-.005, th * .4), (-.003, th), (.004, th * .55), (.012, 0)]
        b.extrude(m["gilt"], outline, .008, xf=frame((0, y, zr + .03), (0, 1, 0), (0, 0, 1), (1, 0, 0)), tile=.2)


def _baluster(b, m, x, y, z, h, rng):
    r = .0085
    prof = [(r * 1.1, 0), (r * .6, .01), (r * .55, h * .25), (r * 1.2, h * .5), (r * .6, h * .78), (r * .55, h - .01),
            (r * 1.1, h)]
    b.lathe(m["lacquer"], prof, xf=place(x, y, z), segments=8, tile=.5, cap=False)


def _balustrade(b, m, rng):
    z0 = TRAY_TOP
    h = .062
    runs = [((-0.585, -0.46), (-0.585, 0.47)), ((0.585, -0.46), (0.585, 0.47)), ((-0.585, 0.47), (0.585, 0.47)),
            ((-0.585, -0.465), (-0.50, -0.465)), ((0.50, -0.465), (0.585, -0.465))]
    for (xa, ya), (xb, yb) in runs:
        length = math.hypot(xb - xa, yb - ya)
        cx, cy = (xa + xb) / 2, (ya + yb) / 2
        along_y = abs(yb - ya) > abs(xb - xa)
        size_bot = (.024, length, .014) if along_y else (length, .024, .014)
        size_top = (.03, length + .02, .02) if along_y else (length + .02, .03, .02)
        b.box(m["lacquer"], size_bot, (cx, cy, z0 + .007), chamfer=.003, tile=.45)
        top = m["lacquer"]
        b.box(top, size_top, (cx, cy, z0 + h + .024), chamfer=.004, tile=.45)
        n = max(2, int(length / .052))
        for k in range(1, n):
            t = k / n
            if rng.random() < .04:
                continue  # one gone
            _baluster(b, m, xa + (xb - xa) * t, ya + (yb - ya) * t, z0 + .014, h, rng)
    for x, y in ((-0.585, -0.465), (0.585, -0.465), (-0.585, 0.47), (0.585, 0.47), (-0.50, -0.465), (0.50, -0.465)):
        b.box(m["lacquer"], (.034, .034, .11), (x, y, z0 + .055), chamfer=.004, tile=.45)
        b.lathe(m["gilt"], [(.012, 0), (.016, .008), (.014, .022), (.007, .034), (0, .042)],
                xf=place(x, y, z0 + .11), segments=12, tile=.2)


def _post(b, m, rng):
    cracks = rng.uniform(0, math.tau, 3)

    def radial(a, h):
        r = 1 + .012 * math.sin(a * 2 + h * 7) + .008 * math.sin(a * 5 + 1)
        for c in cracks:
            if .3 < h < .9:
                r -= .07 * math.exp(-((math.remainder(a - c, math.tau)) / .035) ** 2)
        return r

    prof = [(.075, .20), (.075, .232), (.068, .238), (.06, .258), (.07, .276), (.07, .296), (.058, .312),
            (.056, .33)]
    for k in range(1, 10):
        hz = .33 + (.80 - .33) * k / 9
        prof.append((.056 - .006 * k / 9 + .002 * math.sin(k), hz))
    b.lathe(m["lacquer"], prof, segments=32, tile=.45, radial=radial)
    # Gilt rings and the inverted-lotus capital.
    b.lathe(m["gilt"], [(.05, .80), (.058, .806), (.06, .82), (.058, .834), (.05, .84)], segments=32, tile=.25)
    b.lathe(m["lacquer"], [(.05, .84), (.052, .862), (.07, .89), (.1, .925), (.124, .95), (.13, .962), (.13, .975)],
            segments=32, tile=.45)
    for k in range(14):
        a = k * math.tau / 14
        outline = [(-.02, 0), (-.019, .02), (-.012, .04), (0, .056), (.012, .04), (.019, .02), (.02, 0)]
        r0, z0 = .056, .855
        xf = (Matrix.Translation((r0 * math.cos(a), r0 * math.sin(a), z0)) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
              @ Matrix.Rotation(math.radians(52), 4, "X"))
        b.extrude(m["gilt"], outline, .006, xf=xf @ Matrix.Translation((0, 0, .004)), tile=.2)
    b.box(m["lacquer"], (.30, .30, .026), (0, 0, .988), chamfer=.006, tile=.45)
    # Scroll brackets to the tray, each with its curl tucked against the post.
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        d = Vector((sx * .78, sy * .62, 0)).normalized()
        n = Vector((-d.y, d.x, 0))
        pts, widths = [], []
        for k in range(9):  # the curl
            a = math.pi * 1.6 * (1 - k / 8)
            r = .024 * (.4 + .6 * k / 8)
            c = Vector((0, 0, .64)) + d * .09
            pts.append(c + d * (r * math.cos(a + math.pi)) + Vector((0, 0, r * math.sin(a + math.pi))))
            widths.append(.03 + .012 * k / 8)
        p0, p1, p2, p3 = (Vector((0, 0, .64)) + d * .066, Vector((0, 0, .9)) + d * .085, Vector((0, 0, 1.05)) + d * .27,
                          Vector((0, 0, 1.092)) + d * .46)
        for k in range(1, 15):
            t = k / 14
            q = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3
            pts.append(q)
            widths.append(.046 * (1 - .45 * t))
        b.sweep(m["lacquer"], [tuple(q) for q in pts], tuple(n), widths, .028, tile=.45)
        # A gilt leaf carved on its face.
        mid = (p1 + p2) / 2
        ax = (p2 - p1).normalized()
        for side in (1, -1):
            z = n * side
            b.extrude(m["gilt"], [(-.03, -.012), (0, -.016), (.03, -.008), (.045, 0), (.03, .008), (0, .016), (-.03, .012)],
                      .004, xf=frame(tuple(mid + z * .015), tuple(ax), tuple(z.cross(ax)), tuple(z)), tile=.2)


def _tray(b, m, rng):
    # Bearers on the post cap, then the plank floor flush to 1.125.
    for y in (-.12, .12):
        b.box(m["lacquer"], (1.2, .07, .1), (0, y, 1.05), chamfer=.006, tile=.45)
    widths = [.16] * 6
    y = -.48
    for k, w in enumerate(widths):
        tilt = rng.normal(0, .006)
        mat = m["grey"]
        if k == 3:
            # A split plank: two pieces and a dark gap.
            b.box(mat, (.58, w - .004, .025), (-.31, y + w / 2, TRAY_TOP - .0125), xf=None, chamfer=.003, tile=.6)
            b.box(mat, (.61, w - .004, .025), (.295, y + w / 2 - .002, TRAY_TOP - .0128), chamfer=.003, tile=.6)
        else:
            b.box(mat, (1.2, w - .004, .025), (0, y + w / 2, TRAY_TOP - .0125 + tilt * .01), chamfer=.003, tile=.6,
                  jitter=.0006, rng=rng)
        y += w
    # Fascia boards, their lip a centimetre proud of the floor, gilt beads, and
    # a cut fringe hanging below like a row of teeth.
    for side in ("front", "back", "left", "right"):
        if side in ("front", "back"):
            sy = -1 if side == "front" else 1
            b.box(m["lacquer"], (1.26, .022, .108), (0, sy * .49, 1.081), chamfer=.004, tile=.45)
            b.tube(m["gilt"], [(-.63, sy * .503, 1.128), (.63, sy * .503, 1.128)], .006, sides=6)
            b.tube(m["gilt"], [(-.63, sy * .503, 1.036), (.63, sy * .503, 1.036)], .005, sides=6)
            origin, xa = (0, sy * .496, 1.027), ((1, 0, 0) if sy < 0 else (-1, 0, 0))
            zout = (0, sy, 0)
            length = 1.24
        else:
            sx = -1 if side == "left" else 1
            b.box(m["lacquer"], (.022, .96, .108), (sx * .61, 0, 1.081), chamfer=.004, tile=.45)
            b.tube(m["gilt"], [(sx * .623, -.49, 1.128), (sx * .623, .49, 1.128)], .006, sides=6)
            origin, xa = (sx * .606, 0, 1.027), ((0, -1, 0) if sx < 0 else (0, 1, 0))
            zout = (sx, 0, 0)
            length = .96
        outline = [(-length / 2, 0)]
        n = int(length / .05)
        step = length / n
        for k in range(n):
            x0 = -length / 2 + k * step
            outline += [(x0 + step * .12, -.014), (x0 + step * .26, -.022), (x0 + step * .4, -.024), (x0 + step * .5, -.036),
                        (x0 + step * .6, -.024), (x0 + step * .74, -.022), (x0 + step * .88, -.014), (x0 + step, -.006)]
        outline[-1] = (length / 2, -.004)
        outline.append((length / 2, 0))
        xa_v = Vector(xa)
        y_v = Vector((0, 0, 1))
        z_v = xa_v.cross(y_v)
        b.extrude(m["gilt"], outline, .01, xf=frame(origin, tuple(xa_v), tuple(y_v), tuple(z_v)), tile=.25)


def _house(b, m, rng):
    x0, x1, y0, y1 = -HX, HX, HY0, HY1
    # Stepped base under the house, its middle band a row of gilt lotus petals.
    b.box(m["lacquer"], (2 * HX, y1 - y0, FLOOR - .02 - TRAY_TOP), (0, (y0 + y1) / 2, (TRAY_TOP + FLOOR - .02) / 2),
          tile=.45)
    moulding(b, m["lacquer"], [(.034, 0), (.034, .03), (.022, .036), (.02, .042)], x0, x1, y0, y1, TRAY_TOP, tile=.45)
    for side, (ox, oy, ax, ay, length) in {
        "front": (0, y0 - .016, 1, 0, 2 * HX), "back": (0, y1 + .016, -1, 0, 2 * HX),
        "left": (x0 - .016, (y0 + y1) / 2, 0, -1, y1 - y0), "right": (x1 + .016, (y0 + y1) / 2, 0, 1, y1 - y0),
    }.items():
        n = int(length / .048)
        out = Vector((ay, -ax, 0))
        for k in range(n):
            t = (k + .5) / n - .5
            c = Vector((ox, oy, TRAY_TOP + .043)) + Vector((ax, ay, 0)) * t * length
            outline = [(-.021, 0), (-.02, .016), (-.012, .03), (0, .038), (.012, .03), (.02, .016), (.021, 0)]
            b.extrude(m["gilt"], outline, .008, xf=frame(tuple(c + out * .002), (ax, ay, 0), (0, 0, 1), tuple(out)),
                      tile=.2)
    moulding(b, m["lacquer"], [(.0, 0), (.014, .008), (.022, .022), (.022, .036), (.012, .046), (.0, .054)],
             x0, x1, y0, y1, TRAY_TOP + .085, tile=.45)
    b.box(m["lacquer"], (2 * HX + .03, y1 - y0 + .03, .022), (0, (y0 + y1) / 2, FLOOR - .011), chamfer=.005, tile=.45)
    # Soot-black floor inside.
    b.box(m["soot"], (2 * HX - .07, y1 - y0 - .07, .002), (0, (y0 + y1) / 2 + .005, FLOOR + .0005), tile=.6)
    wall_h = WALL_TOP - FLOOR
    zc = FLOOR + wall_h / 2
    # Corner pilasters with gilt capitals and bases.
    for x in (x0 + .025, x1 - .025):
        for y in (y0 + .02, y1 - .02):
            b.box(m["lacquer"], (.05, .05, wall_h), (x, y, zc), chamfer=.005, tile=.45)
            for zz, hh in ((FLOOR + .02, .04), (WALL_TOP - .045, .03), (WALL_TOP - .015, .03)):
                b.box(m["gilt"], (.06, .06, hh), (x, y, zz), chamfer=.006, tile=.2)
    # Side walls: framed panels round a small window of turned balusters.
    win = (.0, .2, 1.50, 1.69)
    for sx in (-1, 1):
        xo = sx * (HX - .012)
        xi = sx * (HX - .03)
        for (ya, yb, za, zb) in ((y0 + .045, y1 - .045, FLOOR, win[2]), (y0 + .045, y1 - .045, win[3], WALL_TOP),
                                 (y0 + .045, win[0], win[2], win[3]), (win[1], y1 - .045, win[2], win[3])):
            b.box(m["lacquer"], (.018, yb - ya, zb - za), (xo, (ya + yb) / 2, (za + zb) / 2), tile=.45)
            b.box(m["soot"], (.012, yb - ya, zb - za), (xi, (ya + yb) / 2, (za + zb) / 2), tile=.6)
        # Panel frames (stiles and rails standing proud).
        for za, zb in ((FLOOR + .02, win[2] - .03), (win[3] + .03, WALL_TOP - .05)):
            for ya, yb in ((y0 + .07, win[0] - .02), (win[1] + .02, y1 - .07)):
                if zb - za < .04:
                    continue
                for (a, c, la, lc) in ((ya, za, yb - ya, .016), (ya, zb, yb - ya, .016)):
                    b.box(m["lacquer"], (.008, la, lc), (sx * HX, a + la / 2, c), chamfer=.002, tile=.45)
                for yy in (ya, yb):
                    b.box(m["lacquer"], (.008, .016, zb - za), (sx * HX, yy, (za + zb) / 2), chamfer=.002, tile=.45)
        # Window: sill, head, turned balusters and gilt surround.
        b.box(m["lacquer"], (.04, win[1] - win[0] + .05, .018), (sx * HX, (win[0] + win[1]) / 2, win[2] - .009), chamfer=.003, tile=.45)
        b.box(m["lacquer"], (.04, win[1] - win[0] + .05, .02), (sx * HX, (win[0] + win[1]) / 2, win[3] + .01), chamfer=.003, tile=.45)
        for k in range(4):
            yy = win[0] + (k + .5) * (win[1] - win[0]) / 4
            r = .009
            h = win[3] - win[2]
            b.lathe(m["lacquer"], [(r, 0), (r * .6, .02), (r * 1.2, h * .35), (r * 1.25, h * .5), (r * .6, h * .8),
                                   (r, h)], xf=place(sx * (HX - .012), yy, win[2]), segments=10, tile=.5)
        b.tube(m["gilt"], [(sx * (HX + .006), win[0] - .02, win[3] + .025), (sx * (HX + .006), win[1] + .02, win[3] + .025)],
               .005, sides=5)
    # Back wall.
    b.box(m["lacquer"], (2 * HX - .09, .018, wall_h), (0, y1 - .012, zc), tile=.45)
    b.box(m["soot"], (2 * HX - .09, .012, wall_h), (0, y1 - .03, zc), tile=.6)
    # Front wall: narrow panels either side of the doorway, lintel and crest.
    door_w, door_top = DOOR_W, DOOR_TOP
    for sx in (-1, 1):
        xa, xb = sx * door_w, sx * (HX - .045)
        lo, hi = min(xa, xb), max(xa, xb)
        b.box(m["lacquer"], (hi - lo, .018, door_top - FLOOR), ((lo + hi) / 2, y0 + .012, (FLOOR + door_top) / 2), tile=.45)
        b.box(m["soot"], (hi - lo, .012, door_top - FLOOR), ((lo + hi) / 2, y0 + .03, (FLOOR + door_top) / 2), tile=.6)
        # Jambs: gilt-edged architrave.
        b.box(m["lacquer"], (.026, .036, door_top - FLOOR + .03), (sx * (door_w + .013), y0 + .004, (FLOOR + door_top + .03) / 2),
              chamfer=.004, tile=.45)
        b.tube(m["gilt"], [(sx * (door_w + .001), y0 - .015, FLOOR + .01), (sx * (door_w + .001), y0 - .015, door_top + .02)],
               .0045, sides=5)
    b.box(m["lacquer"], (2 * HX - .09, .018, WALL_TOP - door_top), (0, y0 + .012, (door_top + WALL_TOP) / 2), tile=.45)
    b.box(m["soot"], (2 * HX - .09, .012, WALL_TOP - door_top), (0, y0 + .03, (door_top + WALL_TOP) / 2), tile=.6)
    b.box(m["lacquer"], (2 * door_w + .1, .04, .026), (0, y0 + .002, door_top + .013), chamfer=.005, tile=.45)
    b.tube(m["gilt"], [(-door_w - .04, y0 - .019, door_top + .004), (door_w + .04, y0 - .019, door_top + .004)], .0045, sides=5)
    # Soot ceiling inside, and the wall plate and cornice outside.
    b.box(m["soot"], (2 * HX - .06, y1 - y0 - .06, .015), (0, (y0 + y1) / 2, WALL_TOP - .0075), tile=.6)
    moulding(b, m["lacquer"], [(0, 0), (.016, .008), (.026, .022), (.028, .036), (.016, .046)], x0, x1, y0, y1, WALL_TOP,
             tile=.45)
    b.box(m["lacquer"], (2 * HX + .06, y1 - y0 + .06, .02), (0, (y0 + y1) / 2, WALL_TOP + .055), chamfer=.004, tile=.45)
    b.tube(m["gilt"], [(x0 - .02, y0 - .03, WALL_TOP + .044), (x1 + .02, y0 - .03, WALL_TOP + .044)], .0055, sides=5)
    # Door leaves: carved panels; one thrown open, one hanging off its hinge.
    for sx, angle, sag in ((-1, math.radians(158), 0.0), (1, math.radians(68), .022)):
        hinge = Vector((sx * door_w, y0 - .01, FLOOR + .006))
        xf = (Matrix.Translation(hinge) @ Matrix.Rotation(sx * angle, 4, "Z") @ Matrix.Rotation(-sx * sag, 4, "Y"))
        leaf_w, leaf_h = door_w - .004, door_top - FLOOR - .012
        b.box(m["lacquer"], (leaf_w, .018, leaf_h), (-sx * leaf_w / 2, 0, leaf_h / 2), xf=xf, chamfer=.003, tile=.45)
        for zz in (leaf_h * .27, leaf_h * .71):
            b.box(m["lacquer"], (leaf_w - .05, .008, leaf_h * .36), (-sx * leaf_w / 2, -.012, zz), xf=xf, chamfer=.004, tile=.45)
            b.extrude(m["gilt"], [(-.025, -.05), (-.03, 0), (-.015, .05), (0, .07), (.015, .05), (.03, 0), (.025, -.05)],
                      .004, xf=xf @ frame((-sx * leaf_w / 2, -.018, zz), (1, 0, 0), (0, 0, 1), (0, -1, 0)), tile=.2)
        for zz in (.07, leaf_h - .07):
            b.box(m["char"], (.03, .012, .012), (-sx * .015, -.012, zz), xf=xf, tile=.2)


def _porch(b, m, rng):
    zt = PORCH["eave_z"]
    beam_lo = zt - .045
    H = beam_lo - .03 - TRAY_TOP
    for (x, y) in COLUMNS:
        prof = [(.027, 0), (.027, .02), (.021, .03), (.02, .1)]
        for k in range(1, 8):
            prof.append((.02 - .002 * k / 7, .1 + (H - .2) * k / 7))
        prof += [(.022, H - .09), (.022, H - .075), (.018, H - .066), (.02, H - .05), (.03, H - .02), (.034, H - .006),
                 (.034, H)]
        b.lathe(m["lacquer"], prof, xf=place(x, y, TRAY_TOP), segments=16, tile=.45)
        b.lathe(m["gilt"], [(.02, 0), (.025, .008), (.025, .028), (.02, .036)], xf=place(x, y, TRAY_TOP + H - .12),
                segments=16, tile=.2)
        b.box(m["lacquer"], (.06, .06, .03), (x, y, beam_lo - .015), chamfer=.004, tile=.45)
    # Front beam, side plates and the rear beam against the house front.
    b.box(m["lacquer"], (2 * PORCH["eave_x"] + .02, .045, .045), (0, -.46, zt - .0225), chamfer=.005, tile=.45)
    b.tube(m["gilt"], [(-.46, -.484, zt - .008), (.46, -.484, zt - .008)], .005, sides=5)
    for x in (-.43, .43):
        b.box(m["lacquer"], (.04, .25, .04), (x, -.34, zt - .02), chamfer=.004, tile=.45)
    b.box(m["lacquer"], (.96, .04, .04), (0, -.215, zt - .02), chamfer=.004, tile=.45)
    band = kbach_relief(640, 40, 41, "band")
    relief_panel(b, m["gilt"], band, "rect", .9, .034, .006,
                 frame((0, -.236, zt - .037), (1, 0, 0), (0, 0, 1), (0, -1, 0)), nu=200, nv=10, tile=.3,
                 ground=m["lacquer"])
    # A cusped arch fringe from column to column, high in the middle so the
    # doorway stays in sight.
    half = COLUMNS[1][0] - .02
    outline = [(-half, 0)]
    n = 7
    for k in range(n + 1):
        x = -half + 2 * half * k / n
        depth = .095 * (abs(x) / half) ** 1.6 + .012
        outline.append((x, -depth))
        if k < n:
            xm = x + half / n
            dm = .095 * (abs(xm) / half) ** 1.6 + .012
            outline.append((xm - .018, -dm + .006))
            outline.append((xm, -dm - .012))
            outline.append((xm + .018, -dm + .006))
    outline.append((half, 0))
    b.extrude(m["gilt"], outline, .012, xf=frame((0, -.47, beam_lo), (1, 0, 0), (0, 0, 1), (0, -1, 0)), tile=.25)


def _decay(b, m, rng, coll):
    """Termite mud up the post, a mud-wasp nest under the eave, cloth tied on the
    post, a dead garland on the porch, wax down the fascia."""
    # Termite tunnel: a meandering mud gallery from the laterite up the post.
    pts, a = [], rng.uniform(0, math.tau)
    for k in range(40):
        z = .19 + k * .016
        a += rng.normal(0, .08)
        r = .058 + .004 * math.sin(k)
        pts.append((r * math.cos(a), r * math.sin(a), z))
    b.tube(m["mud"], pts, [.009 + .003 * math.sin(k * .7) for k in range(40)], sides=6, flatten=.6, cap_end=True)
    for k in range(6):
        q = pts[rng.integers(5, 38)]
        b.tube(m["mud"], [q, (q[0] * 1.15, q[1] * 1.15, q[2] + rng.uniform(-.03, .03))], .007, sides=5, cap_end=True)
    # Mud-wasp cells under the back eave.
    base = Vector((.36, .38, 1.985))
    for k in range(7):
        p = base + Vector((rng.normal(0, .018), rng.normal(0, .03), 0))
        b.tube(m["mud"], [tuple(p), tuple(p + Vector((rng.normal(0, .01), rng.normal(0, .01), -.045 - rng.uniform(0, .02))))],
               [.008, .009], sides=6, cap_end=True)
    # Red cloth tied round the post, its tails hanging.
    z = .74
    ring = [(.064 * math.cos(t), .064 * math.sin(t), z + .006 * math.sin(t * 3)) for t in np.linspace(0, math.tau, 25)]
    b.tube(m["cloth"], ring, .012, sides=6, flatten=.45)
    for k, dx in enumerate((-.012, .014)):
        tail = [(.066 + dx * .2, -.012 + dx, z), (.075, -.02 + dx, z - .06), (.072 + k * .01, -.018 + dx, z - .16),
                (.07, -.02 + dx * 1.3, z - .24 - k * .05)]
        b.sweep(m["cloth"], tail, (1, 0, 0), .026, .003, tile=.3)
    # A dead garland of jasmine and marigold hanging from the left porch beam.
    top = PORCH["eave_z"] - .047
    hang = [(-.39, -.485, top)]
    for k in range(1, 12):
        t = k / 11
        hang.append((-.39 + .24 * t, -.487, top - .15 * math.sin(math.pi * t)))
    kit.jasmine_string(b, m, hang, rng)
    for k in range(3):
        kit.marigold(b, m, (-.27 + rng.normal(0, .01), -.488, top - .155 - k * .022), rng, .011, dead=True)
    # Wax that ran off the tray edge under each candle, down the fascia.
    for x, y in WICKS:
        for k in range(rng.integers(2, 5)):
            kit.wax_run_over(b, m, (x + rng.normal(0, .025), -.501, 1.133), (0, 0, -1), (0, -1, 0), rng,
                             length=rng.uniform(.03, .11))


def _offerings(b, m, rng, coll):
    wicks = []
    for (x, y), height in zip(WICKS, (.1305, .1305)):
        kit.candle_dish(b, m, place(x, y, TRAY_TOP), rng, radius=.052, melt=.8)
        tip = kit.candle(b, m, place(x, y, TRAY_TOP + .0095, rz=rng.uniform(0, 6)), rng, height=height, radius=.0105,
                         melt=.75, lean=rng.normal(0, .025))
        wicks.append(tuple(tip))
        for k in range(3):
            kit.wax_spill(b, m, place(x + rng.normal(0, .05), y + rng.normal(0, .04), TRAY_TOP), rng,
                          radius=rng.uniform(.012, .03))
    kit.incense_bowl(b, m, place(0, -.375, TRAY_TOP, rz=.4), rng, radius=.07, height=.055, sticks=14, lit=3)
    for sx in (-1, 1):
        # A small brass vase of closed lotus buds either side of the door.
        x, y = sx * .23, -.27
        b.lathe(m["brass"], [(.022, 0), (.026, .01), (.028, .03), (.018, .06), (.013, .075), (.02, .09), (.019, .093),
                             (.012, .085), (0, .08)], xf=place(x, y, TRAY_TOP), segments=20, tile=.15, cap=False)
        for k in range(3):
            a = k * math.tau / 3 + sx
            axis = Vector((math.cos(a) * .25, math.sin(a) * .25, 1))
            base = Vector((x, y, TRAY_TOP + .085)) + axis.normalized() * rng.uniform(.06, .1)
            kit.lotus_bud(b, m, base, axis, rng, size=.07, old=(sx > 0 and k == 0), stem=.1)
        # Banana-leaf cups of flowers and betel, and tiny cups of water.
        kit.leaf_cup(b, m, place(sx * .31, -.41, TRAY_TOP, rz=rng.uniform(-.3, .3)), rng, size=.07, height=.035,
                     fill="flowers" if sx < 0 else "betel", old=sx > 0)
        kit.small_cup(b, m, place(sx * .125, -.44, TRAY_TOP), rng, liquid="water")
    # Beside the house: a young coconut, bananas on a clay plate, old leaf cones,
    # spilled rice, dead flowers and ash.
    kit.coconut(b, m, place(-.47, .2, TRAY_TOP, rz=.7), rng, height=.17, radius=.07)
    b.lathe(m["clay"], [(0, 0), (.06, 0), (.11, .012), (.115, .016), (.105, .016), (.06, .006), (0, .005)],
            xf=place(-.46, -.06, TRAY_TOP), segments=28, tile=.25, cap=False)
    kit.leaf_cup(b, m, place(.47, .22, TRAY_TOP, rz=.4), rng, size=.08, height=.035, fill="rice", old=True)
    kit.leaf_cup(b, m, place(.45, .07, TRAY_TOP, rz=-.3), rng, size=.065, height=.03, fill="flowers", old=True)
    kit.rice_grains(b, m, (.45, -.1, TRAY_TOP), rng, count=70, spread=.03)
    for k in range(5):
        x = rng.choice([-1, 1]) * rng.uniform(.38, .55)
        kit.marigold(b, m, (x, rng.uniform(-.45, .4), TRAY_TOP + .002), rng, .009, dead=True)
    # Inside, the chamber is empty but for one candle burning on the floor, in
    # a dish crusted with the wax of every candle before it.
    kit.candle_dish(b, m, place(0, .06, FLOOR), rng, radius=.045, melt=1)
    for k in range(4):
        kit.wax_spill(b, m, place(rng.normal(0, .05), .06 + rng.normal(0, .05), FLOOR + .0005), rng,
                      radius=rng.uniform(.015, .03))
    inner = kit.candle(b, m, place(0, .06, FLOOR + .0095, rz=1.1), rng, height=.085, radius=.0105, melt=1,
                       lean=.03)
    wicks.append(tuple(inner))
    kit.bananas(b, m, place(-.52, -.06, TRAY_TOP + .006, rz=.1), rng, count=6, length=.095)
    return wicks, None


def _lady(coll):
    """The library figure, joined, its pedestal foot on the chamber floor."""
    from kit import LIB
    from khmer import join
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(LIB, "scans", "phra_phum_lady.glb"))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    bpy.context.view_layer.update()
    for o in meshes:
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
        o.parent = None
    for o in new:
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    obj = join(meshes, "phra_phum_lady")
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    obj.data.transform(Matrix.Translation((0, LADY_Y, FLOOR)))
    return obj


def build(coll, rng=None, effigy=False):
    """Build the spirit house into `coll` at the origin. Returns its objects."""
    rng = rng or np.random.default_rng(1932)
    m = materials()
    b = Batch("phra_phum")
    # Laterite: a big block sunk in the earth and a smaller one on it.
    b.box(m["laterite"], (.6, .58, .17), (0, 0, .015), chamfer=.02, tile=.5, rough=(.012, 9), rng=rng)
    b.box(m["laterite"], (.42, .42, .1), (.003, .004, .148), chamfer=.016, tile=.5, rough=(.008, 12), rng=rng)
    _post(b, m, rng)
    _tray(b, m, rng)
    _balustrade(b, m, rng)
    _house(b, m, rng)
    _porch(b, m, rng)
    _roof(b, m, MAIN, rng, m["grey"])
    _roof(b, m, PORCH, rng, m["soot"])
    _gable(b, m, MAIN, MAIN["y0"], -1, rng, relief=True, tie=False)
    _gable(b, m, MAIN, MAIN["y1"], 1, rng, relief=False)
    _gable(b, m, PORCH, PORCH["y0"], -1, rng, relief=True)
    _decay(b, m, rng, coll)
    wicks, banana = _offerings(b, m, rng, coll)
    inner = wicks.pop()
    objs = list(b.build(coll).values())
    objs.append(_lady(coll))
    # Cobweb veils: porch corners and the black corners of the chamber.
    from cobwebs import corner_cobweb, web_materials
    sheet, thread = web_materials()
    webs = []
    webs += corner_cobweb("phra_phum_web_porch_l", coll, (-.41, -.44, PORCH["eave_z"] - .046), (1, 0, 0), (0, 1, 0), .11,
                          sheet, thread, seed=5)
    webs += corner_cobweb("phra_phum_web_porch_r", coll, (.41, -.235, PORCH["eave_z"] - .042), (-1, 0, 0), (0, -1, 0), .08,
                          sheet, thread, seed=6)
    webs += corner_cobweb("phra_phum_web_chamber", coll, (.27, HY1 - .045, WALL_TOP - .02), (-1, 0, 0), (0, -1, 0), .12,
                          sheet, thread, seed=7)
    webs += corner_cobweb("phra_phum_web_tray", coll, (.15, .15, .975), (-1, 0, 0), (0, -1, 0), .09, sheet, thread, seed=8)
    return {"objects": objs, "webs": webs, "wicks": wicks, "inner_wick": inner}
