"""Neglect, ruin and the forest's return for Episode 2's pagoda. Metres, X east, Y north.

Reference notes (docs/production/episode-2-visual-references.md): strangler-fig roots
gripping Angkorian masonry (Ta Prohm, Preah Khan, Beng Mealea); burnt Ayutthaya chedi
stripped to brick, with rows of damaged Buddha images; worn-out spirit houses left
under old trees; sema boundary stones round an ordination hall; lotus-bud temple walls.
Original geometry: no photograph is used as a texture.
"""
import math

import bmesh
import bpy
import numpy as np

from kit import box, collider, lathe, mesh_object, tube, world_uvs
from forest_detail import Leaves, canopy_sprays, forest_materials
from pagoda_architecture import Craft
from weathering import eroded_stone, mouldy_plaster, old_brick
from kit import library_material, plain


def ruin_materials():
    m = {
        'mould_white': mouldy_plaster('T_ep2_stone_mould_white', (.43, .42, .37), 41, mould=1.25, algae=.6),
        'mould_grey': mouldy_plaster('T_ep2_stone_mould_grey', (.3, .3, .27), 42, mould=1.3, algae=.75, spall=.8),
        'mould_ochre': mouldy_plaster('T_ep2_stone_mould_ochre', (.4, .32, .21), 43, mould=1.15, algae=.5),
        'mould_red': mouldy_plaster('T_ep2_gate_mould_red', (.3, .085, .05), 44, mould=1.1, algae=.35, spall=.7),
        'mould_gold': mouldy_plaster('T_ep2_gate_mould_gold', (.36, .27, .11), 45, mould=.8, algae=.25, spall=.3),
        'burnt': mouldy_plaster('T_ep2_stone_burnt', (.16, .15, .13), 46, mould=.7, algae=.3, spall=1.4),
        'brick': old_brick('T_ep2_stone_brick', 47),
        'statue': eroded_stone('T_ep2_stone_statue', (.25, .245, .21), 48),
    }
    m['saffron'] = library_material('rough_linen', 'M_ep2_cloth_saffron', tint=(.62, .3, .07))
    m['white_cloth'] = library_material('rough_linen', 'M_ep2_cloth_white', tint=(.55, .52, .44))
    m['red_cloth'] = library_material('rough_linen', 'M_ep2_cloth_red', tint=(.38, .07, .05))
    for key in ('saffron', 'white_cloth', 'red_cloth'):
        m[key].use_backface_culling = False
    m['garland_dead'] = plain('M_ep2_garland_dead', (.2, .12, .05), rough=.95)
    m['ash'] = plain('M_ep2_ash', (.3, .29, .27), rough=1)
    m['wax'] = plain('M_ep2_wax', (.55, .5, .36), rough=.6)
    m['glass'] = plain('M_ep2_bottle', (.05, .08, .06), rough=.2, metal=.1)
    return m


# -------------------------------------------------------------- deformation


def _noise3(x, y, z, f, seed):
    return (math.sin(x * f + seed) * math.cos(y * f * 1.3 - seed * .7)
            + math.sin(z * f * .9 + x * f * .4 + seed * 1.9) * .6
            + math.sin((x + y + z) * f * 2.1 + seed * .3) * .3)


def erode(objs, amp=.012, freq=7.0, seed=0.0):
    """Moves every vertex by smooth noise of its position: old masonry sags and
    bellies. Coincident vertices move together, so batched boxes stay closed."""
    for o in objs:
        if o.type != 'MESH':
            continue
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            d = (_noise3(p.x, p.y, p.z, freq, seed), _noise3(p.y, p.z, p.x, freq, seed + 3),
                 _noise3(p.z, p.x, p.y, freq * .7, seed + 7) * .5)
            v.co.x += d[0] * amp
            v.co.y += d[1] * amp
            v.co.z += d[2] * amp * (min(1, p.z / .4))


def lean(objs, x, y, ax, ay):
    """Tilts world-space geometry about its foot (x, y, 0): ax about east, ay about north."""
    cx, sx, cy, sy = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay)
    for o in objs:
        if o.type != 'MESH':
            continue
        for v in o.data.vertices:
            px, py, pz = v.co.x - x, v.co.y - y, v.co.z
            py, pz = py * cx - pz * sx, py * sx + pz * cx
            px, pz = px * cy + pz * sy, -px * sy + pz * cy
            v.co.x, v.co.y, v.co.z = px + x, py + y, pz


def perforate(obj, threshold, seed, freq=2.2):
    """Removes faces where the noise is high: plaster fallen away from a brick core."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = [f for f in bm.faces if _noise3(*f.calc_center_median(), freq, seed) > threshold]
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    bm.to_mesh(obj.data)
    bm.free()


def sphere(name, coll, at, size, mat, segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=at)
    o = bpy.context.object
    o.name = name
    o.scale = size
    for c in list(o.users_collection):
        c.objects.unlink(o)
    coll.objects.link(o)
    o.data.materials.append(mat)
    for f in o.data.polygons:
        f.use_smooth = True
    return o


def sculpt(parts, name, voxel=.02, smooth=4, ratio=.5, rough=.004, seed=0):
    """Fuses primitive masses into one continuous carved surface (as for the Pret)."""
    from khmer import join
    for o in parts:
        bpy.context.view_layer.objects.active = o
        for mod in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        # Voxel remeshing needs closed volumes: cap the open ends of tubes and lathes.
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(o.data)
        bm.free()
    body = join(parts, name)
    bpy.context.view_layer.objects.active = body
    for o in bpy.context.selected_objects:
        o.select_set(False)
    body.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    r = body.modifiers.new('carve', 'REMESH')
    r.mode, r.voxel_size, r.use_smooth_shade = 'VOXEL', voxel, True
    bpy.ops.object.modifier_apply(modifier=r.name)
    s = body.modifiers.new('wear', 'SMOOTH')
    s.factor, s.iterations = .6, smooth
    bpy.ops.object.modifier_apply(modifier=s.name)
    d = body.modifiers.new('budget', 'DECIMATE')
    d.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=d.name)
    for v in body.data.vertices:
        v.co += v.normal * rough * (_noise3(v.co.x, v.co.y, v.co.z, 41, seed) + .5 * _noise3(v.co.x, v.co.y, v.co.z, 97, seed + 1))
    if body.data.uv_layers:
        body.data.uv_layers.remove(body.data.uv_layers[0])
    world_uvs(body)
    return body


def place_object(obj, x, y, z=0.0, yaw=0.0, tilt=(0.0, 0.0)):
    obj.location = (x, y, z)
    obj.rotation_euler = (tilt[0], tilt[1], yaw)
    return obj


# ----------------------------------------------------------- the forest returns


def fig_roots(coll, m, name, cx, cy, top, surface, rng, n=10, spread=1.1, around=(0, math.tau),
              crown=2.5, hang=0.0):
    """A strangler fig seeded on a monument: roots pour over its top and down its
    faces, fuse into a net, then grip the ground. `surface(z)` gives the radius the
    roots must keep outside at each height; `around` limits their bearing."""
    parts, strands = [], []
    for j in range(n):
        a = around[0] + (around[1] - around[0]) * (j + rng.uniform(.15, .85)) / n
        pts = []
        steps = 18
        phase = rng.uniform(0, math.tau)
        for i in range(steps + 1):
            t = i / steps
            z = top * (1 - t) + .06
            # Roots creep sideways as they descend, hugging the masonry.
            a += .05 * math.sin(t * 9 + phase) + rng.normal(0, .02)
            r = surface(z) + .03 + .025 * math.sin(t * 13 + phase * 2)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, z))
        for i in range(1, 4):
            r = surface(.06) + spread * i / 3 * rng.uniform(.6, 1.1)
            a += rng.normal(0, .12)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, .04 - .03 * i))
        strands.append(pts)
        thick = rng.uniform(.06, .12)
        parts.append(tube(f'{name}_root_{j}', coll, pts, thick * .35, m['bark'], sides=7, radius_end=thick))
    # Neighbouring roots fuse into the lattice that makes figs look like they crawl.
    for j in range(n):
        a, b = strands[j], strands[(j + 1) % n]
        for _ in range(int(rng.integers(1, 3))):
            i = int(rng.integers(4, 17))
            p, q = a[i], b[min(len(b) - 1, i + int(rng.integers(-1, 2)))]
            mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2 - .08)
            parts.append(tube(f'{name}_web_{j}', coll, [p, mid, q], .028, m['bark'], sides=5, radius_end=.022))
    if crown:
        lean_a = rng.uniform(0, math.tau)
        trunk = [(cx + math.cos(lean_a) * .4 * t * t, cy + math.sin(lean_a) * .4 * t * t, top + crown * t) for t in np.linspace(0, 1, 6)]
        parts.append(tube(f'{name}_fig_trunk', coll, trunk, .16, m['bark'], sides=8, radius_end=.05))
        leaves = []
        for c in range(int(6 + crown * 3)):
            p = trunk[-1]
            leaves.append(((p[0] + rng.normal(0, crown * .45), p[1] + rng.normal(0, crown * .45), p[2] + rng.normal(0, crown * .25)),
                           rng.uniform(1.4, 2.4) * (crown / 3 + .4), rng.uniform(0, math.pi), 0, int(rng.integers(0, 3))))
        parts.append(canopy_sprays(f'{name}_fig_leaves', coll, leaves, forest_materials()['leaf'], rng, per=12))
    for j in range(int(hang)):
        a = rng.uniform(0, math.tau)
        r = surface(top) + rng.uniform(.1, .6)
        p = (cx + math.cos(a) * r, cy + math.sin(a) * r, top + crown * .6)
        bottom = max(2.3, top - rng.uniform(1, 3))
        parts.append(tube(f'{name}_aerial_{j}', coll, [p, (p[0] + .05, p[1], (p[2] + bottom) / 2), (p[0] + .04, p[1] + .03, bottom)],
                          .015, m['bark'], sides=4, radius_end=.006))
    return parts


def creeper(coll, m, name, path, rng, density=5):
    """A creeper following `path`: a stem with broad leaves hanging off it."""
    stem = tube(name + '_stem', coll, path, .014, m['bark'], sides=4, radius_end=.008)
    leaves = Leaves()
    for a, b in zip(path, path[1:]):
        for t in np.linspace(0, 1, density, endpoint=False):
            p = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            leaves.add(p, rng.uniform(0, math.tau), rng.uniform(.12, .22), rng.uniform(.07, .12), rng.uniform(-.3, .05),
                       int(rng.integers(0, 3)), .2)
    return [stem, leaves.build(name + '_leaves', coll, forest_materials()['leaf'])]


# ----------------------------------------------------------- dressing


def sash(coll, m, name, cx, cy, z, r, mat, rng, tail=.6, squash=1.0):
    """Cloth knotted round a monument or image, its end hanging; faded and stiff."""
    profile = [(r, -.05), (r + .018, 0), (r, .05)]
    band = lathe(name, coll, profile, cx, cy, z, mat, segments=28)
    for v in band.data.vertices:
        a = math.atan2(v.co.y - cy, v.co.x - cx)
        v.co.z += .03 * math.sin(a * 2 + r * 7) + .012 * math.sin(a * 7)
        v.co.y = cy + (v.co.y - cy) * squash
    a = rng.uniform(0, math.tau)
    p = (cx + math.cos(a) * (r + .02), cy + math.sin(a) * (r + .02), z)
    end = tube(name + '_tail', coll, [p, (p[0] + math.cos(a) * .06, p[1] + math.sin(a) * .06, z - tail * .5),
                                      (p[0] + math.cos(a) * .08, p[1] + math.sin(a) * .09, z - tail)], .035, mat, sides=3, radius_end=.025)
    return [band, end]


def incense_pot(coll, m, name, x, y, z, rng):
    parts = [lathe(name, coll, [(0, 0), (.07, .0), (.09, .05), (.08, .1), (.085, .11), (0, .1)], x, y, z, m['clay'], segments=12)]
    for j in range(int(rng.integers(4, 9))):
        a = rng.uniform(0, math.tau)
        bx, by = x + math.cos(a) * .04, y + math.sin(a) * .04
        h = rng.uniform(.04, .2)
        lean_ = rng.normal(0, .03, 2)
        parts.append(tube(f'{name}_stick_{j}', coll, [(bx, by, z + .09), (bx + lean_[0], by + lean_[1], z + .1 + h)], .003, m['red_cloth'], sides=3))
    return parts


def dead_garland(coll, m, name, cx, cy, z, r, rng):
    pts = [(cx + r * math.cos(t), cy + r * math.sin(t) * .6, z + .015 * math.sin(t * 5)) for t in np.linspace(0, math.tau, 19)]
    return [tube(name, coll, pts, .025, m['garland_dead'], sides=5)]


def candles(coll, m, name, x, y, z, rng):
    parts = []
    for j in range(int(rng.integers(2, 5))):
        bx, by = x + rng.normal(0, .06), y + rng.normal(0, .04)
        h = rng.uniform(.015, .08)
        parts.append(lathe(f'{name}_{j}', coll, [(0, 0), (.012, 0), (.012, h), (.016, h + .004), (0, h + .002)], bx, by, z, m['wax'], segments=8))
    return parts


# ----------------------------------------------------------- images and shrines


def seated_image(coll, m, name, x, y, yaw, scale=1.0, headless=False, damage=0, seed=0):
    """A seated Buddha image in eroded sandstone, calling the earth to witness.
    Damaged images are placed respectfully together; none is shown being broken.
    (Advisor review: placement and dressing.)"""
    s = scale
    parts = [
        sphere(name + '_legs', coll, (0, 0, .2 * s), (.42 * s, .3 * s, .13 * s), m['statue']),
        sphere(name + '_hips', coll, (0, .04 * s, .3 * s), (.27 * s, .2 * s, .15 * s), m['statue']),
        sphere(name + '_torso', coll, (0, .05 * s, .55 * s), (.22 * s, .15 * s, .26 * s), m['statue']),
        sphere(name + '_shoulders', coll, (0, .06 * s, .73 * s), (.26 * s, .13 * s, .08 * s), m['statue']),
    ]
    for side in (-1, 1):
        elbow = (side * .27 * s, .02 * s, .5 * s)
        hand = (side * .2 * s, -.2 * s, .24 * s) if side > 0 else (-.04 * s, -.12 * s, .28 * s)
        if not (damage and side > 0):
            parts.append(tube(name + '_arm', coll, [(side * .23 * s, .06 * s, .74 * s), elbow, hand], .055 * s, m['statue'], sides=10, radius_end=.04 * s))
            parts.append(sphere(name + '_hand', coll, hand, (.06 * s, .045 * s, .03 * s), m['statue']))
        else:
            parts.append(tube(name + '_arm', coll, [(side * .23 * s, .06 * s, .74 * s), (side * .26 * s, .05 * s, .63 * s)], .055 * s, m['statue'], sides=10))
        parts.append(sphere(name + '_knee', coll, (side * .32 * s, -.1 * s, .2 * s), (.13 * s, .14 * s, .09 * s), m['statue']))
    if headless:
        parts.append(tube(name + '_neck', coll, [(0, .06 * s, .76 * s), (.01 * s, .06 * s, .83 * s)], .07 * s, m['statue'], sides=10, radius_end=.06 * s))
    else:
        parts += [
            tube(name + '_neck', coll, [(0, .06 * s, .76 * s), (0, .06 * s, .86 * s)], .065 * s, m['statue'], sides=10),
            sphere(name + '_head', coll, (0, .05 * s, .97 * s), (.105 * s, .115 * s, .14 * s), m['statue']),
            sphere(name + '_ushnisha', coll, (0, .06 * s, 1.11 * s), (.06 * s, .06 * s, .06 * s), m['statue']),
            tube(name + '_flame', coll, [(0, .06 * s, 1.14 * s), (0, .06 * s, 1.26 * s)], .025 * s, m['statue'], sides=8, radius_end=.004),
        ]
        for side in (-1, 1):
            parts.append(sphere(name + '_ear', coll, (side * .11 * s, .06 * s, .93 * s), (.022 * s, .035 * s, .1 * s), m['statue']))
    body = sculpt(parts, name, voxel=.013 * s, smooth=6, ratio=.22, seed=seed)
    if headless:
        # A rough break, not a clean cut: chip the neck back.
        for v in body.data.vertices:
            if v.co.z > .8 * s:
                v.co.z = .8 * s + (v.co.z - .8 * s) * .4 + .015 * s * math.sin(v.co.x * 90 + v.co.y * 70)
    base = lathe(name + '_throne', coll, [(.5 * s, 0), (.52 * s, .04 * s), (.46 * s, .07 * s), (.4 * s, .09 * s), (.47 * s, .12 * s), (.47 * s, .13 * s), (0, .13 * s)],
                 0, 0, -.13 * s, m['statue'], segments=24)
    for o in (body, base):
        place_object(o, x, y, .13 * s if o is body else .13 * s, yaw)
    return [body, base]


def spirit_house(coll, m, name, x, y, yaw, rng, fallen=False):
    """A worn-out spirit house: post, platform, pavilion with a tiered roof, painted
    gold and red long ago. Old ones are retired under a big tree; nobody has
    tended these in a generation. (Advisor review.)"""
    parts, c = [], Craft()
    post = 0 if fallen else rng.uniform(.6, 1.1)
    paint = m[['mould_red', 'mould_white', 'mould_gold', 'mould_grey'][int(rng.integers(0, 4))]]
    trim = m['mould_gold']
    if post:
        c.block(m['mould_grey'], 0, 0, 0, .14, .14, post)
    z = post
    c.block(paint, 0, 0, z, .62, .5, .05)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.block(trim, sx * .26, sy * .2, z + .05, .035, .035, .3)
    c.block(paint, 0, .05, z + .05, .38, .3, .3)
    c.block(m['void'], 0, -.105, z + .07, .14, .02, .2)
    parts = c.build(name, coll)
    rz = z + .38
    for side in (-1, 1):
        for tier, (w, h, d) in enumerate(((.36, .2, .62), (.24, .17, .44))):
            zz = rz + tier * .12
            verts = [(0, -d / 2, zz + h), (0, d / 2, zz + h), (side * w, d / 2, zz), (side * w, -d / 2, zz)]
            if side < 0:
                verts = list(reversed(verts))
            parts.append(mesh_object(f'{name}_roof', coll, verts, [(0, 1, 2, 3), (3, 2, 1, 0)], m['tiles']))
        for end in (-1, 1):
            parts.append(tube(f'{name}_finial', coll, [(side * .36, end * .31, rz), (side * .42, end * .33, rz + .06), (side * .4, end * .33, rz + .14)],
                              .012, trim, sides=4, radius_end=.003))
    parts.append(tube(f'{name}_ridge_spire', coll, [(0, 0, rz + .3), (0, 0, rz + .52)], .018, trim, sides=6, radius_end=.002))
    for j in range(int(rng.integers(1, 4))):
        fx, fy = rng.uniform(-.2, .2), rng.uniform(-.22, -.12)
        parts.append(lathe(f'{name}_figure_{j}', coll, [(0, 0), (.025, 0), (.03, .04), (.02, .08), (.028, .1), (0, .13)], fx, fy, z + .05, m['clay'], segments=8))
    if rng.random() < .6:
        parts += dead_garland(coll, m, name + '_garland', 0, -.16, z + .06, .11, rng)
    if rng.random() < .5:
        parts.append(lathe(name + '_bottle', coll, [(0, 0), (.03, 0), (.032, .12), (.012, .16), (.012, .2), (0, .2)], .2, -.16, z + .05, m['glass'], segments=8))
    from khmer import join
    house = join(parts, name)
    tilt = (rng.uniform(1.2, 1.5) * rng.choice([-1, 1]), rng.uniform(-.2, .2)) if fallen else (rng.normal(0, .07), rng.normal(0, .07))
    place_object(house, x, y, 0 if not fallen else .2, yaw, tilt)
    return house


def sema_stone(coll, m, name, x, y, yaw):
    """A leaf-shaped sema boundary stone on a lotus pedestal, marking consecrated ground."""
    parts = [lathe(name + '_pedestal', coll, [(.32, 0), (.33, .08), (.25, .12), (.2, .2), (.27, .26), (.27, .3), (0, .3)], 0, 0, 0, m['mould_grey'], segments=16)]
    from pagoda_props import extrude
    outline = [(-.22, 0), (-.26, .2), (-.24, .45), (-.17, .66), (-.07, .8), (0, .9), (.07, .8), (.17, .66), (.24, .45), (.26, .2), (.22, 0)]
    parts.append(extrude(coll, name + '_leaf', outline, .06, m['statue'], (0, 0, .3)))
    parts.append(extrude(coll, name + '_boss', [(px * .55, pz * .78 + .07) for px, pz in outline], .085, m['statue'], (0, 0, .3)))
    from khmer import join
    stone = join(parts, name)
    place_object(stone, x, y, 0, yaw, (np.random.default_rng(int(abs(x * 31 + y * 7))).normal(0, .05), 0))
    collider(name, coll, x - .34, x + .34, y - .34, y + .34, 0, 1.2, 'stone')
    return stone


def rubble(coll, m, name, x, y, r, n, rng, mats=None, size=(.3, .14, .07)):
    """Fallen brick and plaster chunks heaped low, as one batched mesh per material."""
    c = Craft()
    mats = mats or [m['brick'], m['brick'], m['mould_grey']]
    for j in range(n):
        a = rng.uniform(0, math.tau)
        d = r * math.sqrt(rng.random())
        w, dd, h = (s * rng.uniform(.6, 1.4) for s in size)
        z = max(0, (1 - d / r) * size[2] * rng.uniform(.5, 3))
        bx, by = x + math.cos(a) * d, y + math.sin(a) * d
        yaw = rng.uniform(0, math.pi)
        ca, sa = math.cos(yaw), math.sin(yaw)
        tilt = rng.normal(0, .25)
        pts = []
        for px in (-w / 2, w / 2):
            for py in (-dd / 2, dd / 2):
                for pz in (0, h):
                    pz2 = pz + px * tilt
                    pts.append((bx + px * ca - py * sa, by + px * sa + py * ca, z + pz2))
        mat = mats[j % len(mats)]
        for f in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]:
            c.face(mat, [pts[i] for i in f])
    return c.build(name, coll)


# ----------------------------------------------------------- the great chedi


def great_chedi(coll, m, x, y, rng, s=1.0, facing=math.pi / 2):
    """A burnt, abandoned bell chedi older than the memorial garden: redented
    stepped base, lotus cushions, bell, harmika and ringed spire snapped off. Its
    lime skin has fallen in sheets to the brick; a fig has taken the top."""
    made = set(coll.objects)
    c = Craft()
    for z, w, h in [(0, 5.4, .32), (.32, 4.9, .28), (.6, 4.3, .3), (.9, 3.9, .26)]:
        w *= s
        for a, b in ((w, w * .78), (w * .78, w)):
            c.block(m['mould_grey'], x, y, z * s, a, b, h * s)
        # Exposed brick wherever the plaster skin let go.
        for j in range(5):
            side = int(rng.integers(0, 4))
            ang = side * math.pi / 2
            t = rng.uniform(-.35, .35) * w
            ww = rng.uniform(.3, .9) * s
            hh = h * s * rng.uniform(.5, .95)
            ca, sa = math.cos(ang), math.sin(ang)
            off = w * .5 + .006
            q = [(x + ca * off - sa * (t - ww / 2), y + sa * off + ca * (t - ww / 2), z * s + .02),
                 (x + ca * off - sa * (t + ww / 2), y + sa * off + ca * (t + ww / 2), z * s + .02),
                 (x + ca * off - sa * (t + ww * .4), y + sa * off + ca * (t + ww * .4), z * s + hh),
                 (x + ca * off - sa * (t - ww * .3), y + sa * off + ca * (t - ww * .3), z * s + hh * .8)]
            c.face(m['brick'], q)
    base_objs = c.build('great_chedi_base', coll)
    z0 = 1.16 * s
    bell_profile = [(1.62, 0), (1.66, .1), (1.5, .2), (1.55, .3), (1.42, .42), (1.48, .52), (1.36, .64),
                    (1.5, .9), (1.52, 1.3), (1.44, 1.8), (1.24, 2.3), (.94, 2.75), (.62, 3.05), (.44, 3.15)]
    bell_profile = [(r * s, h * s) for r, h in bell_profile]
    core = lathe('great_chedi_core', coll, [(r * .965, h) for r, h in bell_profile], x, y, z0, m['brick'], segments=48)
    skin = lathe('great_chedi_skin', coll, bell_profile, x, y, z0, m['burnt'], segments=48)
    perforate(skin, .55, rng.uniform(0, 9), 1.4)
    top = z0 + 3.15 * s
    c = Craft()
    c.block(m['burnt'], x, y, top, 1.0 * s, 1.0 * s, .5 * s)
    c.block(m['burnt'], x, y, top + .5 * s, 1.18 * s, 1.18 * s, .1 * s)
    harmika = c.build('great_chedi_harmika', coll)
    rings = []
    for j in range(8):
        r = (.42 - j * .035) * s
        rings.append(lathe(f'great_chedi_ring_{j}', coll, [(r, 0), (r + .05 * s, .06 * s), (r, .14 * s)], x, y, top + (.6 + j * .14) * s, m['burnt'], segments=20))
    snap = top + (.6 + 8 * .14) * s
    shards = [tube('great_chedi_snap', coll, [(x + math.cos(a) * .15 * s, y + math.sin(a) * .15 * s, snap),
                                              (x + math.cos(a) * .1 * s, y + math.sin(a) * .1 * s, snap + rng.uniform(.1, .5) * s)],
                   .06 * s, m['brick'], sides=4, radius_end=.01) for a in np.linspace(0, math.tau, 5, endpoint=False)]
    # The snapped spire lies where it fell, half buried in leaves.
    fallen = lathe('great_chedi_fallen_spire', coll, [(.3 * s, 0), (.26 * s, .4 * s), (.24 * s, .45 * s), (.2 * s, .9 * s), (.16 * s, .95 * s),
                                                       (.1 * s, 1.5 * s), (.02 * s, 1.9 * s)], 0, 0, 0, m['burnt'], segments=16)
    place_object(fallen, x - 2.2 * s, y - 3.1 * s, .25 * s, .4, (0, 1.45))
    # A headless image set on the upper terrace, facing the garden, with old offerings.
    ca, sa = math.cos(facing), math.sin(facing)
    nx, ny = x + ca * 1.84 * s, y + sa * 1.84 * s
    image = seated_image(coll, m, 'great_chedi_image', nx, ny, facing + math.pi / 2, .55, headless=True, seed=3)
    for o in image:
        o.location.z = z0 + .13 * .55
    offerings = incense_pot(coll, m, 'great_chedi_incense', nx + ca * .2 - sa * .3, ny + sa * .2 + ca * .3, z0, rng)
    offerings += candles(coll, m, 'great_chedi_candle', nx + ca * .2 + sa * .3, ny + sa * .2 - ca * .3, z0, rng)
    offerings += sash(coll, m, 'great_chedi_sash', x, y, z0 + 1.4 * s, 1.53 * s, m['saffron'], rng, tail=1.0)

    def surface(z):
        if z < z0:
            return [3.0, 2.75, 2.45, 2.2][min(3, int(z / (.3 * s)))] * s
        return .75 * s if z - z0 > 3.15 * s else _bell_radius(bell_profile, z - z0, s, x) + .02
    roots = fig_roots(coll, m, 'great_chedi_fig', x, y, top + .5 * s, surface, rng,
                      n=14, spread=1.8 * s, crown=4.2 * s, hang=10)
    debris = rubble(coll, m, 'great_chedi_rubble', x + 1.6 * s, y - 2.5 * s, 1.4 * s, 70, rng)
    debris += rubble(coll, m, 'great_chedi_rubble', x - 2.6 * s, y + .8 * s, 1.1 * s, 45, rng)
    erode(base_objs + harmika + rings, .02, 3.1, rng.uniform(0, 9))
    erode([core, skin], .035, 1.7, 2)
    lean(base_objs + harmika + rings + [core, skin] + shards + roots, x, y, .012, -.02)
    collider('great_chedi', coll, x - 2.7 * s, x + 2.7 * s, y - 2.7 * s, y + 2.7 * s, 0, 7 * s, 'stone')
    return [o for o in coll.objects if o not in made]


def _bell_radius(profile, h, s, _x):
    if h < 0:
        return 2.0 * s
    for (r0, h0), (r1, h1) in zip(profile, profile[1:]):
        if h0 <= h <= h1:
            return r0 + (r1 - r0) * (h - h0) / ((h1 - h0) or 1)
    return profile[-1][0]


# ----------------------------------------------------------- the enclosure


def temple_wall(coll, m, name, a, b, rng, body='mould_white', breaches=(), height=1.6, bay=3.2, collide=True):
    """A Thai/Khmer temple enclosure: plinth, plastered brick body, coping with a
    crest of leaf-shaped merlons, piers with lotus-bud finials. Bays lean, the skin
    has scabbed to brick, a few bays have fallen. Axis-aligned from a to b."""
    made = set(coll.objects)
    ax, ay = a
    bx, by = b
    length = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / length, (by - ay) / length
    nx, ny = -uy, ux
    bays = max(1, round(length / bay))
    step = length / bays
    mat, trim = m[body], m['mould_grey']

    def at(t, n=0.0, z=0.0):
        return (ax + ux * t + nx * n, ay + uy * t + ny * n, z)

    def slab(c, mat_, t0, t1, n0, n1, z0, z1):
        p = [at(t, n, z) for t in (t0, t1) for n in (n0, n1) for z in (z0, z1)]
        for f in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]:
            c.face(mat_, [p[i] for i in f])

    leaves_done = []
    for i in range(bays):
        c = Craft()
        t0, t1 = i * step, (i + 1) * step
        fallen = i in breaches
        slab(c, trim, t0, t1, -.36, .36, 0, .24)
        if not fallen:
            slab(c, mat, t0 + .32, t1 - .32, -.23, .23, .24, height)
            slab(c, trim, t0 + .32, t1 - .32, -.3, .3, height, height + .07)
            slab(c, mat, t0 + .32, t1 - .32, -.17, .17, height + .07, height + .14)
            # Leaf-shaped merlons along the crest, some lost.
            for j in range(int((step - .64) / .5)):
                if rng.random() < .12:
                    continue
                tc = t0 + .57 + j * .5
                outline = [(-.14, 0), (-.13, .12), (-.07, .24), (0, .32), (.07, .24), (.13, .12), (.14, 0)]
                for side in (-1, 1):
                    q = [at(tc + px, side * .055, height + .14 + pz) for px, pz in outline]
                    c.face(mat, q if side > 0 else list(reversed(q)))
                for k in range(len(outline) - 1):
                    p0, p1 = outline[k], outline[k + 1]
                    c.face(mat, [at(tc + p0[0], -.055, height + .14 + p0[1]), at(tc + p1[0], -.055, height + .14 + p1[1]),
                                 at(tc + p1[0], .055, height + .14 + p1[1]), at(tc + p0[0], .055, height + .14 + p0[1])])
            # Scabs where the plaster fell: brick shows proud of the face on both sides.
            for _ in range(int(rng.integers(1, 4))):
                side = rng.choice([-1, 1])
                tc = rng.uniform(t0 + .6, t1 - .6)
                w, z0 = rng.uniform(.25, .8), rng.uniform(.3, height - .5)
                h = rng.uniform(.2, .5)
                q = [at(tc - w / 2, side * .236, z0), at(tc + w / 2, side * .236, z0 + rng.uniform(-.05, .05)),
                     at(tc + w * .3, side * .236, z0 + h), at(tc - w * .4, side * .236, z0 + h * .8)]
                c.face(m['brick'], list(reversed(q)) if side > 0 else q)
        else:
            # The fallen bay: a jagged stump of brick courses and a spill of rubble.
            cols = int((step - .64) / .24)
            for j in range(cols):
                tc = t0 + .32 + j * .24
                f = abs(j - cols / 2) / (cols / 2)
                top = .24 + (height - .24) * (f ** 1.6) * rng.uniform(.75, 1.05)
                slab(c, m['brick'] if top < height * .8 else mat, tc, tc + .24, -.22, .22, .24, top)
        objs = c.build(f'{name}_bay_{i}', coll)
        mx, my, _ = at((t0 + t1) / 2)
        lean(objs, mx, my, rng.normal(0, .012) * ux, rng.normal(0, .012) * uy)
        erode(objs, .012, 4, i)
        if fallen:
            for side in (-1, 1):
                rubble(coll, m, f'{name}_spill_{i}', *at((t0 + t1) / 2, side * 1.0)[:2], 1.0, 40, rng)
        # Creepers draped over the coping, down one or both faces.
        if rng.random() < .55 and not fallen:
            tc = rng.uniform(t0 + .5, t1 - .5)
            for side in (-1, 1):
                if rng.random() < .7:
                    drop = rng.uniform(.6, height - .1)
                    path = [at(tc, 0, height + .16), at(tc + .1, side * .26, height + .05), at(tc + .15, side * .27, height - drop * .5),
                            at(tc + .1, side * .28, height - drop)]
                    leaves_done += creeper(coll, m, f'{name}_creeper_{i}', path, rng)
    # Piers at every bay, with stepped caps and a lotus-bud finial.
    for i in range(bays + 1):
        t = i * step
        c = Craft()
        px, py, _ = at(t)
        c.block(trim, px, py, 0, .8, .8, .3)
        c.block(mat, px, py, .3, .62, .62, height + .3)
        c.block(trim, px, py, height + .6, .74, .74, .08)
        c.block(mat, px, py, height + .68, .58, .58, .12)
        objs = c.build(f'{name}_pier_{i}', coll)
        if rng.random() > .1:
            objs.append(lathe(f'{name}_lotus_bud_{i}', coll, [(.2, 0), (.22, .06), (.16, .12), (.19, .2), (.16, .34), (.08, .46), (0, .55)],
                              px, py, height + .8, mat, segments=14))
        erode(objs, .012, 4, i + 50)
    if collide:
        x0, x1 = sorted([ax - nx * .36, bx + nx * .36])
        y0, y1 = sorted([ay - ny * .36, by + ny * .36])
        collider(name, coll, x0, x1, y0, y1, 0, height + .4, 'stone')
    return [o for o in coll.objects if o not in made]


def guardian(coll, m, name, x, y, yaw, rng, headless=False, seed=0):
    """A temple guardian (dvarapala/yaksha) on a plinth, both hands on a club. Weather
    has softened the face to suggestion: bulging eyes, fangs, a tiered crown.
    (Advisor review: Thai yaksha and Khmer dvarapala are both precedents.)"""
    parts = []
    for side in (-1, 1):
        parts.append(tube(name + '_leg', coll, [(side * .17, 0, 0), (side * .2, -.03, .45), (side * .16, 0, .95)], .12, m['statue'], sides=10, radius_end=.14))
        parts.append(sphere(name + '_foot', coll, (side * .18, -.1, .05), (.09, .17, .06), m['statue']))
        parts.append(tube(name + '_arm', coll, [(side * .3, 0, 1.55), (side * .36, -.08, 1.25), (side * .1, -.3, 1.08)], .075, m['statue'], sides=10, radius_end=.065))
        parts.append(sphere(name + '_hand', coll, (side * .07, -.32, 1.1), (.08, .07, .06), m['statue']))
    parts += [
        sphere(name + '_sarong', coll, (0, 0, .95), (.33, .24, .3), m['statue']),
        # A knee-length sampot, pleated at the front, makes the lower body read as solid stone.
        lathe(name + '_sampot', coll, [(.3, .42), (.33, .55), (.34, .8), (.32, 1.0), (.28, 1.1), (0, 1.12)], 0, 0, 0, m['statue'], segments=16),
        tube(name + '_pleat', coll, [(0, -.27, 1.05), (.01, -.33, .7), (0, -.31, .4)], .06, m['statue'], sides=8, radius_end=.09),
        sphere(name + '_belly', coll, (0, -.04, 1.2), (.3, .23, .26), m['statue']),
        sphere(name + '_chest', coll, (0, 0, 1.47), (.33, .2, .2), m['statue']),
        tube(name + '_club', coll, [(0, -.32, .02), (0, -.33, .7), (0, -.32, 1.12)], .07, m['statue'], sides=10, radius_end=.12),
    ]
    if not headless:
        parts += [
            tube(name + '_neck', coll, [(0, 0, 1.6), (0, -.01, 1.74)], .1, m['statue'], sides=10),
            sphere(name + '_head', coll, (0, -.03, 1.86), (.15, .15, .17), m['statue']),
            lathe(name + '_crown', coll, [(.15, 0), (.16, .05), (.12, .1), (.13, .14), (.09, .2), (.1, .24), (.06, .32), (.04, .42), (0, .52)], 0, -.02, 1.96, m['statue'], segments=14),
        ]
        for side in (-1, 1):
            parts.append(sphere(name + '_eye', coll, (side * .06, -.155, 1.89), (.04, .03, .035), m['statue']))
            parts.append(tube(name + '_fang', coll, [(side * .045, -.16, 1.79), (side * .05, -.17, 1.72)], .016, m['statue'], sides=6, radius_end=.004))
            parts.append(sphere(name + '_ear', coll, (side * .15, -.02, 1.86), (.03, .05, .09), m['statue']))
    else:
        parts.append(tube(name + '_neck', coll, [(0, 0, 1.6), (.01, -.01, 1.69)], .11, m['statue'], sides=10))
    body = sculpt(parts, name, voxel=.02, ratio=.45, rough=.008, seed=seed)
    plinth = Craft()
    plinth.block(m['mould_grey'], 0, 0, -.62, .92, .92, .14)
    plinth.block(m['mould_white'], 0, 0, -.48, .78, .78, .4)
    plinth.block(m['mould_grey'], 0, 0, -.08, .88, .88, .08)
    base = plinth.build(name + '_plinth', coll)
    for o in [body] + base:
        place_object(o, x, y, .62, yaw)
    erode(base, .01, 5, seed)
    collider(name, coll, x - .46, x + .46, y - .46, y + .46, 0, 2.7, 'stone')
    return [body] + base
