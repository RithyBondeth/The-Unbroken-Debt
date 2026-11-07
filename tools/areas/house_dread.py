"""The family house on the night of the vigil: a working 1930s Khmer kitchen, and
signs through the house that something has been feeding here.

The kitchen is dressed as a village kitchen was: a smoke rack of bamboo hung over
the hearth with fish drying in the smoke, a soot-black wok and coconut-shell
ladles on nails, a shelf of clay jars and a jar of prahok under a weighted lid,
a winnowing tray and a rice steamer on the wall, garlic and chillies hanging,
split firewood stacked under the window, a stone mortar, a chopping block.

Then the wrongness. A hen was killed on the block and not eaten as people eat:
feathers everywhere, the block and the table black with blood, run over the edge
and pooled on the boards. The thorny branches the family tied across both
windows against the Krasue (its trailing gut catches on thorns) are torn, with
long black hairs snagged in them. Blood has run down the wall under the west
window and drops lead from it across the floor into the hall. The rice pot lies
on its side. In the hall: the trail fades out over the mat, old stains in the
weave, a ring of burnt-down candles round a pile of ash and thrown rice where
someone tried to keep it out, torn yantra papers by the door, the dead man's
clothes still on their cord, claw marks gouged in Sok's door.

Additive only: nothing here collides or replaces gameplay geometry, and it
stays clear of the Krasue's window sightlines (data/krasue.ts). Shared by the
full village builder and rebuild-house-dread.py. Blender metres, Z up.
Procedural decal atlas T_ep1_house_dread_BC; no photographs. The Krasue lore
(thorns at windows, blood and raw food) is for the cultural advisor's review.
"""
import math

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from kit import TEXTURES, image_material, lathe, mesh_object, tube
from khmer import join, place
from house_detail import corner_web, detail_material
from house_decay import Decals
from shrine import box, grains

F, ZW = 2.5, 5.1
# The kitchen's inside faces (ep1_area_village.py: house walls and partitions).
KX0, KX1, KY0, KY1 = -5.94, -3.0, 11.5, 14.47
SILL, HEAD = F + 0.8, F + 1.75
# Atlas cells (2 × 2): blood pooled and spattered, blood run down, a smear, claw gouges.
POOL, RUNS, SMEAR, CLAW = range(4)


def dread_atlas():
    """Soft cutout decals in one RGBA atlas: old blood (near black where thick,
    rust-brown where thin) and four torn gouges with splintered edges."""
    path = f'{TEXTURES}/T_ep1_house_dread_BC.png'
    rng = np.random.default_rng(7243101)
    size, half = 1024, 512
    yy, xx = np.mgrid[0:half, 0:half].astype(float)
    u, v = xx / (half - 1), yy / (half - 1)  # v = 0 at the bottom (Blender pixel rows)
    fine = rng.normal(0, 1, (half, half))
    blur = sum(np.roll(np.roll(fine, i, 0), j, 1) for i in range(-3, 4) for j in range(-3, 4)) / 49
    cells = []
    # Pool: an irregular body with a dark crust and drops flung round it.
    a = np.zeros((half, half))
    for _ in range(7):
        cx, cy, r = rng.uniform(.35, .65), rng.uniform(.35, .65), rng.uniform(.08, .2)
        a = np.maximum(a, np.clip(1 - np.hypot((u - cx) / r, (v - cy) / (r * rng.uniform(.6, 1.2))), 0, 1) ** .4)
    for _ in range(90):
        ang, dist = rng.uniform(0, 6.3), rng.uniform(.22, .48)
        cx, cy, r = .5 + np.cos(ang) * dist, .5 + np.sin(ang) * dist, rng.uniform(.004, .018)
        a = np.maximum(a, np.clip(1 - np.hypot(u - cx, v - cy) / r, 0, 1) * 1.3)
    cells.append((a, (.2, .02, .014)))
    # Runs: thick at the top, thinning, each ending in a bead.
    a = np.zeros((half, half))
    for _ in range(14):
        c, w, length = rng.uniform(.1, .9), rng.uniform(.006, .02), rng.uniform(.3, .95)
        end = 1 - length
        wob = .008 * np.sin(v * rng.uniform(8, 18) + rng.uniform(0, 6))
        run = np.clip((v - end) / length, 0, 1) ** .5 * (v > end)
        a = np.maximum(a, np.exp(-((u - c - wob) / (w * (.4 + .6 * run + 1e-3))) ** 2) * (v > end) * (.6 + .4 * run))
        a = np.maximum(a, np.clip(1 - np.hypot(u - c, (v - end) * 1.3) / (w * 1.6), 0, 1) * 1.2)
    a = np.maximum(a, np.clip((v - .86) / .14, 0, 1) * (.7 + 1.6 * blur))
    cells.append((a, (.22, .022, .016)))
    # Smear: something wet dragged across, streaked along its length, a palm at one end.
    streak = .6 + .4 * np.sin(v * 80 + np.sin(u * 7) * 3)
    band = np.exp(-((v - .5 - .08 * np.sin(u * 5)) / (.12 + .1 * u)) ** 2) * np.clip(u * 1.4, 0, 1)
    palm = np.clip(1 - np.hypot((u - .82) / .11, (v - .5) / .13), 0, 1) ** .5
    for k in range(4):
        palm = np.maximum(palm, np.exp(-((v - .38 - k * .08) / .018) ** 2) * (u > .88) * (u < .99))
    cells.append((np.clip(band * streak + palm, 0, 1), (.19, .02, .014)))
    # Claws: four ragged gouges, raking down, deep and dark in the wood.
    a = np.zeros((half, half))
    for k in range(4):
        c = .22 + k * .18 + rng.uniform(-.02, .02)
        drift = .12 * (1 - v)
        line = np.exp(-((u - c - drift) / (.012 + .006 * np.sin(v * 31 + k))) ** 2)
        a = np.maximum(a, line * np.clip((v - .05) / .1, 0, 1) * np.clip((.95 - v) / .3, 0, 1))
    cells.append((np.clip(a * (1.1 + .8 * blur), 0, 1), (.03, .022, .016)))
    grain = rng.normal(0, 1, (half, half))
    pixels = np.zeros((size, size, 4))
    for k, (alpha, colour) in enumerate(cells):
        alpha = np.where(alpha > .05, alpha * 1.9 + (.5 * blur + .15 * grain) * .6 - .1, 0)
        x, y = (k % 2) * half, (1 - k // 2) * half
        # Thin blood dries rust-brown at its edges; thick stays near black.
        edge = np.clip(1 - alpha, 0, 1)[..., None]
        tone = np.array(colour) * (1 + .25 * blur[..., None]) * (1 - .35 * (1 - edge)) + edge * np.array([.06, .02, .01]) * (k != CLAW)
        pixels[y:y + half, x:x + half, :3] = np.clip(tone, 0, 1)
        pixels[y:y + half, x:x + half, 3] = np.clip(alpha, 0, 1)
    from forest_detail import save_map
    save_map('T_ep1_house_dread_BC', pixels)
    return path


def dread_materials(m):
    stains = (bpy.data.materials.get('M_house_detail_dread_stains')
              or image_material('M_house_detail_dread_stains', dread_atlas(), rough=.6, cutout=True))
    d = {
        'stains': stains,
        'gore': detail_material('M_house_detail_dread_gore', (.28, .02, .02), .3),
        'fish': detail_material('M_house_detail_dread_smoked_fish', (.17, .1, .045), .62),
        'soot_bamboo': detail_material('M_house_detail_dread_sooted_bamboo', (.045, .036, .026), .8),
        'iron': detail_material('M_house_detail_dread_black_iron', (.028, .026, .025), .55, .7),
        'shell': detail_material('M_house_detail_dread_coconut_shell', (.11, .065, .035), .7),
        'chilli': detail_material('M_house_detail_dread_dried_chilli', (.32, .03, .018), .5),
        'garlic': detail_material('M_house_detail_dread_garlic', (.52, .47, .39), .75),
        'feather': detail_material('M_house_detail_dread_feather', (.2, .12, .06), .9),
        'feather_white': detail_material('M_house_detail_dread_feather_white', (.55, .52, .45), .9),
        'hair': detail_material('M_house_detail_dread_black_hair', (.008, .007, .006), .45),
        'stone': detail_material('M_house_detail_dread_mortar_stone', (.2, .19, .17), .9),
        'thorn': (bpy.data.materials.get('M_house_detail_thorn_wood')
                  or detail_material('M_house_detail_thorn_wood', (.12, .08, .05), .85)),
        'cotton': detail_material('M_house_detail_dread_worn_cotton', (.46, .44, .4), .95),
        'firewood': bpy.data.materials.get('M_house_detail_firewood') or m['worn'],
        'char': bpy.data.materials.get('M_house_detail_char') or m['soot'],
    }
    for key in ('feather', 'feather_white', 'cotton', 'fish'):
        d[key].use_backface_culling = False
    return d


class Room:
    """Collects one room's pieces by material, so each room costs a few draws."""

    def __init__(self, coll, label):
        self.coll, self.label, self.parts, self.n = coll, label, {}, 0

    def name(self, what):
        self.n += 1
        return f'house_dread_{self.label}_{what}_{self.n}'

    def add(self, obj):
        if obj is None:
            return obj
        for o in (obj if isinstance(obj, (list, tuple)) else [obj]):
            if o.type == 'MESH':
                self.parts.setdefault(o.active_material.name if o.active_material else '', []).append(o)
        return obj

    def finish(self):
        out = []
        for i, (key, objs) in enumerate(sorted(self.parts.items())):
            out.append(join(objs, f'house_dread_{self.label}_{i:02d}') if len(objs) > 1 else objs[0])
            out[-1].name = f'house_dread_{self.label}_{i:02d}'
        return out


def transformed(obj, location, rotation=(0, 0, 0)):
    obj.matrix_world = Matrix.Translation(Vector(location)) @ Euler(rotation).to_matrix().to_4x4()
    bpy.context.view_layer.update()
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    return obj


def blob(name, coll, mat, centre, size, rng, rough=.25, seg=8):
    """A lumpy closed solid (raw meat, a garlic bulb, a stone)."""
    verts, faces = [], []
    rings = seg
    for r in range(rings + 1):
        lat = -math.pi / 2 + math.pi * r / rings
        for c in range(seg * 2):
            a = math.pi * c / seg
            k = 1 + rng.uniform(-rough, rough) if 0 < r < rings else 1
            verts.append((centre[0] + math.cos(lat) * math.cos(a) * size[0] * k,
                          centre[1] + math.cos(lat) * math.sin(a) * size[1] * k,
                          centre[2] + math.sin(lat) * size[2] * k))
    n = seg * 2
    for r in range(rings):
        for c in range(n):
            a, b = r * n + c, r * n + (c + 1) % n
            faces.append((a, b, b + n, a + n))
    return mesh_object(name, coll, verts, faces, mat, uvs=[(0, 0)] * (len(faces) * 4), smooth=True)


def fish(room, mat, head, tail, width, rng):
    """A split, flattened, smoked fish: a tapering body and a forked tail."""
    head, tail = Vector(head), Vector(tail)
    axis = tail - head
    side = axis.cross(Vector((0, 0, 1))).normalized()
    if side.length < .5:
        side = Vector((1, 0, 0))
    verts, faces = [], []
    for i in range(9):
        t = i / 8
        w = width * math.sin(math.pi * min(1, t * 1.15)) ** .7 * (1 - .4 * t)
        p = head + axis * t * .85
        verts += [tuple(p - side * w), tuple(p + side * w)]
    for i in range(8):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    b = len(verts)
    root = head + axis * .85
    verts += [tuple(root), tuple(tail - side * width * .7), tuple(tail + side * width * .7)]
    faces.append((b, b + 1, b + 2))
    return room.add(mesh_object(room.name('fish'), room.coll, verts, faces, mat,
                                uvs=[(0, 0)] * (8 * 4 + 3), smooth=True))


def thorn_branch(room, d, points, rng, thorns=26):
    """A twig of a thorny shrub, its thorns standing off it in every direction."""
    room.add(tube(room.name('thorn_twig'), room.coll, points, .007, d['thorn'], sides=5, radius_end=.003))
    pts = [Vector(p) for p in points]
    for k in range(thorns):
        t = rng.uniform(0, 1)
        seg = min(len(pts) - 2, int(t * (len(pts) - 1)))
        f = t * (len(pts) - 1) - seg
        at = pts[seg].lerp(pts[seg + 1], f)
        along = (pts[seg + 1] - pts[seg]).normalized()
        out = Vector((rng.normal(), rng.normal(), rng.normal())).cross(along).normalized()
        length = rng.uniform(.018, .04)
        room.add(tube(room.name('thorn'), room.coll, [tuple(at), tuple(at + out * length + along * length * .4)],
                      .0028, d['thorn'], sides=3, radius_end=.0003))


def hairs(room, d, root, rng, count=7, length=.6, droop=(0, 0, -1)):
    """Long black hairs torn out and caught at `root`: tangled, looping back on
    themselves, a few hanging a little way."""
    droop = Vector(droop).normalized()
    for k in range(count):
        p = Vector(root) + Vector((rng.normal(0, .025), rng.normal(0, .03), rng.normal(0, .015)))
        n = rng.uniform(.4, 1) * length
        phase = rng.uniform(0, 6.3)
        path = []
        for i in range(11):
            t = i / 10
            loop = Vector((math.sin(t * 9 + phase), math.cos(t * 7 + phase), math.sin(t * 5 + k))) * .05 * (1 - t * .5)
            path.append(tuple(p + droop * n * t * t + loop * t))
        room.add(tube(room.name('hair'), room.coll, path, .0006, d['hair'], sides=3, radius_end=.0003))


def feathers(room, d, centre, spread, count, z, rng):
    """A hen's feathers: curved, tapering vanes on a pale shaft, mostly brown,
    some white, lying where they fell or caught on their edge."""
    for k in range(count):
        x = centre[0] + rng.normal(0, spread)
        y = centre[1] + rng.normal(0, spread)
        a = rng.uniform(0, math.tau)
        L = rng.uniform(.03, .075)
        W = L * rng.uniform(.18, .3)
        curl = rng.uniform(-.25, .25)
        lift = rng.uniform(.0005, .004)
        along = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-math.sin(a), math.cos(a), 0))
        verts, faces = [], []
        for j in range(6):
            t = j / 5
            w = W * math.sin(math.pi * min(1, .15 + t * .95)) * (1 - .3 * t)
            p = Vector((x, y, z + lift + .006 * t * t)) + along * (t - .5) * L + side * curl * L * t * t
            verts += [tuple(p - side * w * .8), tuple(p), tuple(p + side * w)]
        for j in range(5):
            q = j * 3
            faces += [(q, q + 1, q + 4, q + 3), (q + 1, q + 2, q + 5, q + 4)]
        room.add(mesh_object(room.name('feather'), room.coll, verts, faces,
                             d['feather_white'] if k % 4 == 0 else d['feather'],
                             uvs=[(0, 0)] * (len(faces) * 4), smooth=True))


def clay_jar(room, mat, x, y, z, height, radius, neck=.45):
    h, r = height, radius
    prof = [(0, 0), (r * .55, 0), (r * .9, h * .18), (r, h * .45), (r * .82, h * .78),
            (r * neck, h * .9), (r * neck * 1.15, h), (r * neck * .95, h * 1.01), (r * neck * .8, h * .93), (0, h * .9)]
    return room.add(lathe(room.name('jar'), room.coll, prof, x, y, z, mat, segments=20))


def kitchen(coll, m, d, rng):
    room = Room(coll, 'kitchen')
    decals = Decals()
    rack_z = F + 1.78
    # --- The smoke rack over the hearth, hung on four cords from the wall plate.
    x0, x1, y0, y1 = -5.74, -4.66, 11.76, 12.5
    for px in (x0, x1):
        for py in (y0, y1):
            room.add(tube(room.name('rack_cord'), coll, [(px, py, rack_z), (px + (.03 if px < -5 else -.03), py, ZW - .05)],
                          .004, m['rope'], sides=4))
    for py in (y0, y1):
        room.add(tube(room.name('rack_rail'), coll, [(x0 - .05, py, rack_z), (x1 + .05, py, rack_z)], .016, d['soot_bamboo'], sides=7))
    for k in range(15):
        px = x0 + (x1 - x0) * k / 14
        room.add(tube(room.name('rack_slat'), coll, [(px, y0 - .03, rack_z + .018), (px + rng.normal(0, .004), y1 + .03, rack_z + .018)],
                      .008, d['soot_bamboo'], sides=5))
    for k in range(6):
        px = x0 + .12 + k * .16 + rng.normal(0, .01)
        fish(room, d['fish'], (px, y0 + .08, rack_z + .03), (px + rng.normal(0, .03), y0 + .5 + rng.uniform(0, .1), rack_z + .03),
             .045, rng)
    for k in range(4):
        py = y0 + .52 + k * .05
        room.add(tube(room.name('rack_wood'), coll, [(x0 + .08, py, rack_z + .045), (x0 + .55, py + rng.normal(0, .01), rack_z + .045)],
                      .02, d['firewood'], sides=6))
    # Soot thick on everything above the fire, and a web blackened with it.
    room.add(corner_web(room.name('rack_web'), coll, (KX0 + .01, KY0 + .01, ZW - .05), (1, 0, 0), (0, 0, -1), .45))
    # --- On nails on the south wall above the hearth: the wok and two coconut-shell ladles.
    wok = lathe(room.name('wok'), coll, [(0, 0), (.08, .004), (.16, .025), (.21, .065), (.22, .072), (.205, .07), (.15, .03), (.07, .01), (0, .006)],
                0, 0, 0, d['iron'], segments=28)
    room.add(transformed(wok, (-5.35, KY0 + .075, F + 1.32), (math.radians(-90), 0, 0)))
    for k, px in enumerate((-4.98, -4.84)):
        shell = lathe(room.name('ladle_cup'), coll, [(0, 0), (.035, .004), (.055, .025), (.06, .05), (.055, .051), (.05, .028), (.03, .008), (0, .004)],
                      0, 0, 0, d['shell'], segments=16)
        room.add(transformed(shell, (px, KY0 + .07, F + 1.06), (math.radians(-80), 0, 0)))
        room.add(tube(room.name('ladle_handle'), coll, [(px, KY0 + .05, F + 1.1), (px, KY0 + .02, F + 1.48)], .008, m['bamboo'], sides=6))
        room.add(tube(room.name('nail'), coll, [(px, KY0, F + 1.47), (px, KY0 + .04, F + 1.48)], .003, d['iron'], sides=4))
    room.add(tube(room.name('nail'), coll, [(-5.35, KY0, F + 1.5), (-5.35, KY0 + .05, F + 1.51)], .003, d['iron'], sides=4))
    # --- Split firewood stacked on the floor under the south window.
    for layer in range(3):
        for k in range(5 - layer):
            px = -4.48 + k * .1 + layer * .05
            room.add(tube(room.name('stack_log'), coll, [(px, KY0 + .05, F + .05 + layer * .085), (px + rng.normal(0, .01), KY0 + .62, F + .05 + layer * .085)],
                          .042 + rng.uniform(-.006, .006), d['firewood'], sides=6))
    # --- The shelf on the north wall: clay jars, a glazed jar under cloth, bowls, a bottle.
    sy = KY1 - .14
    room.add(box(room.name('shelf'), coll, -5.5, -3.55, KY1 - .24, KY1, F + 1.24, F + 1.27, m['worn'], edge=.004))
    for bx in (-5.3, -3.75):
        room.add(box(room.name('shelf_bracket'), coll, bx - .02, bx + .02, KY1 - .2, KY1, F + 1.04, F + 1.24, m['post']))
    top = F + 1.27
    for k, (px, h, r) in enumerate(((-5.32, .2, .085), (-5.12, .26, .1), (-4.88, .17, .075), (-4.36, .22, .09))):
        clay_jar(room, m['clay'] if k != 1 else m['glaze'], px, sy, top, h, r)
    # The glazed jar's mouth tied over with cloth.
    room.add(lathe(room.name('jar_cloth'), coll, [(0, .255), (.06, .25), (.063, .232), (.058, .222)], -5.12, sy, top, d['cotton'], segments=16))
    room.add(lathe(room.name('jar_tie'), coll, [(.058, .226), (.06, .232)], -5.12, sy, top, m['rope'], segments=12))
    for k in range(3):
        room.add(lathe(room.name('bowl'), coll, [(0, 0), (.035, 0), (.07, .035), (.075, .045), (.069, .045), (.03, .008), (0, .006)],
                       -4.62, sy, top + k * .02, m['glaze'], segments=20))
    room.add(lathe(room.name('bottle'), coll, [(0, 0), (.032, 0), (.034, .14), (.013, .19), (.012, .23), (0, .23)], -4.1, sy, top, m['bottle'], segments=14))
    for k, px in enumerate((-3.95, -3.82)):
        room.add(lathe(room.name('coconut_half'), coll, [(0, 0), (.04, .004), (.06, .03), (.062, .05), (0, .05)], px, sy + .02, top, d['shell'], segments=14))
    # Dried chillies and a braid of garlic hanging under the shelf.
    for k, px in enumerate((-5.42, -3.62)):
        cord = [(px, KY1 - .12, F + 1.24), (px, KY1 - .12, F + .82)]
        room.add(tube(room.name('hang_cord'), coll, cord, .003, m['rope'], sides=4))
        for j in range(9):
            z = F + 1.2 - j * .045
            if k == 0:
                a = j * 2.1
                room.add(tube(room.name('chilli'), coll, [(px, KY1 - .12, z), (px + .05 * math.cos(a), KY1 - .12 + .05 * math.sin(a), z - .05)],
                              .007, d['chilli'], sides=5, radius_end=.002))
            else:
                room.add(blob(room.name('garlic'), coll, d['garlic'], (px + .025 * math.cos(j * 2.4), KY1 - .12 + .025 * math.sin(j * 2.4), z),
                              (.026, .026, .022), rng, rough=.12, seg=6))
    # --- The winnowing tray on the hall wall, the rice-steamer basket below it.
    tray = lathe(room.name('winnow_tray'), coll, [(0, 0), (.3, .01), (.33, .035), (.335, .04), (.31, .03), (0, .012)], 0, 0, 0, m['rattan'], segments=32)
    room.add(transformed(tray, (KX1 - .045, 14.05, F + 1.55), (0, math.radians(-90), 0)))
    steamer = lathe(room.name('steamer'), coll, [(0, 0), (.06, 0), (.11, .07), (.15, .2), (.155, .27), (.14, .27), (.1, .08), (.04, .015), (0, .012)],
                    0, 0, 0, m['rattan'], segments=20)
    # The steamer basket stands on the floor in the corner, where it was left to dry.
    room.add(transformed(steamer, (-3.62, 13.72, F), (0, 0, 0)))
    room.add(tube(room.name('nail'), coll, [(KX1, 14.05, F + 1.88), (KX1 - .04, 14.05, F + 1.89)], .003, d['iron'], sides=4))
    # --- A big jar of prahok in the corner, its lid a plaited tray weighted with a stone.
    clay_jar(room, m['clay'], -3.3, 14.18, F, .52, .21, neck=.62)
    room.add(lathe(room.name('jar_lid'), coll, [(0, .535), (.16, .528), (.17, .522)], -3.3, 14.18, F, m['rattan'], segments=20))
    room.add(blob(room.name('lid_stone'), coll, d['stone'], (-3.29, 14.17, F + .58), (.07, .06, .045), rng, rough=.15))
    # --- Under the table: the stone mortar and its pestle.
    room.add(lathe(room.name('mortar'), coll, [(0, 0), (.13, 0), (.15, .04), (.16, .14), (.14, .16), (.1, .15), (.06, .06), (0, .05)],
                   -4.2, 13.72, F, d['stone'], segments=20))
    room.add(tube(room.name('pestle'), coll, [(-4.22, 13.72, F + .07), (-4.08, 13.86, F + .3)], .025, m['worn'], sides=8, radius_end=.018))
    # --- The block on the table, the cleaver in it, and what was done on it.
    tx, ty, ttop = -4.78, 13.92, F + .75
    room.add(lathe(room.name('block'), coll, [(0, 0), (.15, 0), (.155, .015), (.152, .09), (.145, .1), (0, .1)], tx, ty, ttop, d['firewood'], segments=24))
    room.add(lathe(room.name('block_top'), coll, [(0, .1005), (.146, .1005)], tx, ty, ttop, m['worn'], segments=24))
    blade = box(room.name('cleaver_blade'), coll, -.09, .09, -.002, .002, -.03, .07, d['iron'], edge=.001)
    room.add(transformed(blade, (tx + .02, ty - .02, ttop + .13), (math.radians(8), math.radians(-12), math.radians(25))))
    handle = tube(room.name('cleaver_handle'), coll, [(0, 0, 0), (.13, 0, 0)], .014, m['worn'], sides=7)
    room.add(transformed(handle, (tx + .1, ty + .02, ttop + .15), (0, math.radians(-12), math.radians(25))))
    # Torn meat and a hen's foot on the block, and blood soaked into its end grain.
    for k in range(7):
        room.add(blob(room.name('gore'), coll, d['gore'], (tx + rng.normal(0, .045), ty + rng.normal(0, .045), ttop + .112),
                      (rng.uniform(.025, .045), rng.uniform(.02, .035), rng.uniform(.012, .02)), rng, rough=.4))
    for k in range(3):
        a = .4 + k * .45
        room.add(tube(room.name('hen_toe'), coll, [(tx + .09, ty - .1, ttop + .11), (tx + .09 + .07 * math.cos(a), ty - .1 + .07 * math.sin(a), ttop + .104)],
                      .005, d['feather'], sides=5, radius_end=.002))
    decals.add(POOL, (tx, ty - .14, ttop + .1), (1, 0, 0), (0, 1, 0), .3, .28, (0, 0, 1), offset=.003)
    # Run off the block across the table, over its front edge, pooled on the boards.
    decals.add(POOL, (tx + .1, ty - .55, ttop), (1, 0, 0), (0, 1, 0), .55, .45, (0, 0, 1), offset=.002)
    decals.add(RUNS, (tx + .1, 13.2 - .002, ttop - .4), (1, 0, 0), (0, 0, 1), .3, .43, (0, -1, 0), offset=.002)
    decals.add(POOL, (tx + .1, 12.95, F), (1, 0, 0), (0, 1, 0), .5, .38, (0, 0, 1), offset=.004)
    feathers(room, d, (tx, ty), .12, 14, ttop + .002, rng)
    feathers(room, d, (-4.6, 13.0), .4, 26, F + .004, rng)
    feathers(room, d, (-5.6, 13.0), .12, 7, F + .004, rng)
    # --- The rice pot knocked off the hearth, on its side, the rice spilt and soured.
    pot = lathe(room.name('rice_pot'), coll, [(0, 0), (.09, 0), (.14, .06), (.15, .13), (.12, .19), (.1, .2), (.105, .215), (.08, .21), (0, .2)],
                0, 0, 0, m['clay'], segments=22)
    room.add(transformed(pot, (-4.38, 12.85, F + .14), (math.radians(90), 0, math.radians(35))))
    room.add(grains(room.name('spilt_rice'), coll, [(-4.3 + rng.normal(0, .09), 12.98 + rng.uniform(0, .25), F + .004) for _ in range(260)],
                    m['rice'], rng))
    # --- The thorns across both windows, torn aside, black hair caught in them.
    for k in range(3):
        y = 12.66 + k * .015
        thorn_branch(room, d, [(KX0 + .02, y, SILL + .03 + k * .05), (KX0 + .03, y + .2, SILL + .1 + k * .03),
                               (KX0 + .02, y + .45, SILL + .05), (KX0 + .03, 13.36, SILL + .12 + k * .04)], rng)
    # One branch hangs down inside, ripped loose from its tie.
    thorn_branch(room, d, [(KX0 + .03, 13.34, HEAD - .05), (KX0 + .12, 13.3, HEAD - .45), (KX0 + .2, 13.25, SILL - .3)], rng, thorns=16)
    for k in range(3):
        x = -4.56 + k * .014
        thorn_branch(room, d, [(x, KY0 + .02, SILL + .04 + k * .05), (x + .25, KY0 + .03, SILL + .1), (x + .5, KY0 + .02, SILL + .06),
                               (-3.84, KY0 + .03, SILL + .11 + k * .03)], rng)
    hairs(room, d, (KX0 + .05, 13.1, SILL + .12), rng, 9, .3)
    hairs(room, d, (KX0 + .12, 13.27, SILL - .1), rng, 5, .25)
    hairs(room, d, (-4.1, KY0 + .05, SILL + .1), rng, 6, .3)
    # Gouged into the west window's frame, and blood run down the wall below it.
    decals.add(CLAW, (KX0 - .001, 13.47, SILL + .1), (0, 1, 0), (0, 0, 1), .16, .5, (1, 0, 0), offset=.004)
    decals.add(RUNS, (KX0, 13.0, F), (0, 1, 0), (0, 0, 1), .6, .8, (1, 0, 0), offset=.004)
    decals.add(SMEAR, (KX0 + .3, 13.0, F), (0, 1, 0), (1, 0, 0), .7, .45, (0, 0, 1), offset=.004)
    # And drops from there across the floor into the hall, spreading out as they go.
    for k in range(16):
        t = k / 15
        px = KX0 + .6 + (KX1 + .2 - KX0 - .6) * t + rng.normal(0, .05)
        py = 13.0 - .1 * math.sin(t * 3) + rng.normal(0, .05)
        s = .07 + .07 * (1 - t) * rng.uniform(.5, 1)
        decals.add(POOL, (px, py, F), (1, 0, 0), (0, 1, 0), s, s, (0, 0, 1), offset=.0035 + k * .00005)
    # Cobwebs in the kitchen's upper corners.
    room.add(corner_web(room.name('web'), coll, (KX1 - .01, KY1 - .01, ZW - .05), (-1, 0, 0), (0, 0, -1), .5))
    room.add(corner_web(room.name('web'), coll, (KX0 + .01, KY1 - .01, ZW - .08), (0, -1, 0), (0, 0, -1), .4))
    room.add(decals.finish(room.name('stains'), coll, d['stains']))
    # A few library pieces: an enamel pot by the hearth, a basket of rice.
    props = [place(coll, 'pot_enamel_01', (-4.48, 12.25, F), rot_deg=40, scale=.7),
             place(coll, 'wicker_basket_01', (-5.62, 13.9, F + .0), rot_deg=-20, scale=.8)]
    return room.finish(), props


SOOT_CELL, MILDEW_CELL, MUD_CELL = 3, 1, 2  # house_decay.py's weathering atlas


def hall(coll, m, d, rng):
    room = Room(coll, 'hall')
    decals = Decals()
    grime = Decals()
    # Damp and dirt worked into the mat and the boards by three days of mourners.
    for k in range(16):
        x, y = rng.uniform(-1.7, 1.7), rng.uniform(12.5, 18.5)
        s = rng.uniform(.25, .7)
        a = rng.uniform(0, math.tau)
        grime.add(MILDEW_CELL if k % 3 else MUD_CELL, (x, y - s / 2, F + .0065), (math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0),
                  s, s, (0, 0, 1), offset=.0009 + k * .00003)
    # The trail comes in from the kitchen door and fades over the mat.
    for k in range(12):
        t = k / 11
        px = -2.9 + 2.0 * t + rng.normal(0, .06)
        py = 12.95 + .7 * t * t + rng.normal(0, .06)
        s = .09 * (1 - .6 * t) * rng.uniform(.6, 1)
        z = F + (.0065 if -1.8 < px < 1.8 and 12.4 < py < 18.6 else 0)
        decals.add(POOL, (px, py, z), (1, 0, 0), (0, 1, 0), s, s, (0, 0, 1), offset=.002 + k * .00005)
    # Old stains in the mat's weave, dark where something lay.
    for k, (px, py, s) in enumerate(((.7, 15.6, .6), (-.9, 16.8, .45), (1.2, 13.4, .35))):
        decals.add(POOL, (px, py, F + .0065), (math.cos(k), math.sin(k), 0), (-math.sin(k), math.cos(k), 0), s, s * .8, (0, 0, 1), offset=.002)
    # A ring of candles burnt to stubs round a heap of ash and thrown rice.
    cx, cy = -1.05, 14.25
    for k in range(9):
        a = k / 9 * math.tau + rng.normal(0, .08)
        x, y = cx + math.cos(a) * .42, cy + math.sin(a) * .42
        h = rng.uniform(.01, .045)
        room.add(lathe(room.name('candle_stub'), coll, [(0, 0), (.026, 0), (.024, h), (.018, h + .004), (0, h)], x, y, F + .0065, m['wax_dirty'], segments=10))
        room.add(lathe(room.name('wax_pool'), coll, [(0, .001), (.05 + rng.uniform(0, .02), 0)], x, y, F + .0065, m['wax_dirty'], segments=12))
    for k in range(5):
        room.add(blob(room.name('ash'), coll, m['ash'], (cx + rng.normal(0, .05), cy + rng.normal(0, .05), F + .012),
                      (rng.uniform(.06, .11), rng.uniform(.05, .1), rng.uniform(.015, .03)), rng, rough=.3))
    for k in range(7):
        a = rng.uniform(0, math.tau)
        base = (cx + math.cos(a) * .05, cy + math.sin(a) * .05, F + .02)
        tip = (base[0] + rng.normal(0, .03), base[1] + rng.normal(0, .03), F + rng.uniform(.06, .14))
        room.add(tube(room.name('incense_stalk'), coll, [base, tip], .0016, m['incense_burnt'], sides=4))
    grime.add(SOOT_CELL, (cx, cy - .35, F + .0065), (1, 0, 0), (0, 1, 0), .8, .7, (0, 0, 1), offset=.0012)
    room.add(grains(room.name('thrown_rice'), coll, [(cx + rng.normal(0, .35), cy + rng.normal(0, .35), F + .008) for _ in range(320)],
                    m['rice'], rng))
    shard = lathe(room.name('broken_bowl'), coll, [(0, 0), (.04, 0), (.08, .04), (.085, .05), (.079, .05), (0, .008)], 0, 0, 0, m['glaze'], segments=7)
    room.add(transformed(shard, (cx + .2, cy - .16, F + .03), (math.radians(110), 0, .6)))
    # Torn yantra papers blown in from the door.
    for k in range(9):
        x, y = rng.uniform(-.6, 1.1), rng.uniform(11.62, 12.5)
        a, s = rng.uniform(0, math.tau), rng.uniform(.06, .11)
        c, sn = math.cos(a) * s, math.sin(a) * s
        z = F + (.0075 if -1.8 < x < 1.8 and y > 12.4 else .002) + k * .0003
        room.add(mesh_object(room.name('yantra_paper'), coll, [(x - c, y - sn, z), (x + sn, y - c, z), (x + c, y + sn, z), (x - sn * .7, y + c * .8, z)],
                             [(0, 1, 2, 3)], m['yantra'], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)]))
    # The dead man's shirt and sarong still on the cord in the hall's corner.
    a, b = (2.15, 11.56, F + 1.95), (2.92, 12.1, F + 1.92)
    room.add(tube(room.name('clothes_cord'), coll, [a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, a[2] - .06), b], .003, m['rope'], sides=4))
    along = (Vector(b) - Vector(a)).normalized()
    across = along.cross(Vector((0, 0, 1))).normalized()

    def cord_at(t):
        return Vector(a).lerp(Vector(b), t) - Vector((0, 0, .06 * math.sin(t * math.pi)))

    # The shirt: shoulders pegged to the cord, sleeves hanging, the hem lifting.
    top = cord_at(.3)
    verts, faces, index = [], [], {}
    for j in range(13):
        v = j / 12
        for i in range(13):
            u = i / 12 - .5
            body = abs(u) < .3
            sleeve = .3 <= abs(u) <= .5 and v < .55 and abs(u) - .3 < .2 * (1 - v * .4)
            if not (body or sleeve):
                continue
            shoulder = -.07 * max(0, abs(u) - .12)
            fold = .014 * math.sin(i * 2.3 + v * 3) * v + .02 * v * v
            p = top + along * u * .62 + Vector((0, 0, shoulder - v * (.7 if body else .4))) + across * fold
            index[(i, j)] = len(verts)
            verts.append(tuple(p))
    for (i, j), q in index.items():
        if (i + 1, j) in index and (i, j + 1) in index and (i + 1, j + 1) in index:
            faces.append((q, index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]))
    room.add(mesh_object(room.name('dead_shirt'), coll, verts, faces, d['cotton'], smooth=True))
    # The sarong, its two halves hanging either side of the cord.
    verts, faces = [], []
    for side in (-1, 1):
        base = len(verts)
        for j in range(9):
            v = j / 8
            for i in range(11):
                u = i / 10
                t = .58 + u * .32
                p = cord_at(t) + Vector((0, 0, .015 - v * (.55 if side < 0 else .45))) + across * side * (.012 + .03 * v + .012 * math.sin(i * 1.9 + v * 4) * v)
                verts.append(tuple(p))
        for j in range(8):
            for i in range(10):
                q = base + j * 11 + i
                faces.append((q, q + 1, q + 12, q + 11) if side > 0 else (q, q + 11, q + 12, q + 1))
    room.add(mesh_object(room.name('dead_sarong'), coll, verts, faces, m['cotton_dirty'], smooth=True))
    # Claw marks raked down Sok's door, at the height of a face, and on its frame.
    decals.add(CLAW, (2.93, 13.45, F + .9), (0, -1, 0), (0, 0, 1), .32, .85, (-1, 0, 0), offset=.006)
    decals.add(CLAW, (2.93, 13.95, F + 1.3), (0, -1, 0), (0, 0, 1), .14, .5, (-1, 0, 0), offset=.006, flip=True)
    decals.add(SMEAR, (-3.0 + .07, 12.48, F + 1.0), (0, 1, 0), (0, 0, 1), .25, .5, (1, 0, 0), offset=.004)
    # Long black hairs on the boards by the kitchen door.
    hairs(room, d, (-2.7, 12.9, F + .004), rng, 8, .5, droop=(1, .3, 0))
    room.add(decals.finish(room.name('stains'), coll, d['stains']))
    weather = bpy.data.materials.get('M_house_detail_weather_stains')
    if weather:
        room.add(grime.finish(room.name('grime'), coll, weather))
    return room.finish()


def house_dread(coll, m):
    rng = np.random.default_rng(1932107)
    d = dread_materials(m)
    made, props = kitchen(coll, m, d, rng)
    made += hall(coll, m, d, rng)
    for i, parent in enumerate(props):
        for j, obj in enumerate([parent] + list(parent.children_recursive)):
            obj.name = f'house_dread_prop_{i:02d}_{j:02d}'
    return made, props
