"""Neglect, ruin and the forest's return for Episode 2's pagoda. Metres, X east, Y north.

Reference notes (docs/production/episode-2-visual-references.md): strangler-fig roots
gripping Angkorian masonry (Ta Prohm, Preah Khan, Beng Mealea); burnt Ayutthaya chedi
stripped to brick, with rows of damaged Buddha images; worn-out spirit houses left
under old trees; sema boundary stones round an ordination hall; lotus-bud temple walls.
Original geometry: no photograph is used as a texture.
"""
import fit
import math
from mathutils import Matrix

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
    """Tilts world-space geometry about its foot (x, y, 0): ax about east, ay about north.
    Kit pieces share their mesh with others, so those lean as whole objects instead."""
    cx, sx, cy, sy = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay)
    tilt = (Matrix.Translation((x, y, 0)) @ Matrix.Rotation(ay, 4, 'Y') @ Matrix.Rotation(ax, 4, 'X')
            @ Matrix.Translation((-x, -y, 0)))
    for o in objs:
        if o.type != 'MESH':
            continue
        if o.get('kit_piece'):
            o.matrix_basis = tilt @ o.matrix_basis  # basis: world matrices are stale until an update
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
    n = int(n * 1.5)  # more, thinner roots: a net, not a few logs
    for j in range(n):
        a = around[0] + (around[1] - around[0]) * (j + rng.uniform(.15, .85)) / n
        pts = []
        steps = 30
        phase = rng.uniform(0, math.tau)
        for i in range(steps + 1):
            t = i / steps
            z = top * (1 - t) + .06
            # Roots creep sideways as they descend, hugging the masonry.
            a += .05 * math.sin(t * 9 + phase) + rng.normal(0, .02)
            r = surface(z) + .02 + .012 * math.sin(t * 13 + phase * 2)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, z))
        for i in range(1, 4):
            r = surface(.06) + spread * i / 3 * rng.uniform(.6, 1.1)
            a += rng.normal(0, .12)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, .04 - .03 * i))
        strands.append(pts)
        thick = rng.uniform(.035, .085)
        root = fit.wrap(tube(f'{name}_root_{j}', coll, pts, thick * .3, m['bark'], sides=10, radius_end=thick), cx, cy, surface, top)
        for f in root.data.polygons:
            f.use_smooth = True
        parts.append(root)
        # Fine rootlets feeling their way off the main root over the masonry.
        for _ in range(int(rng.integers(1, 4))):
            i = int(rng.integers(5, steps - 4))
            p = pts[i]
            da = rng.choice([-1, 1]) * rng.uniform(.15, .4)
            ra = math.atan2(p[1] - cy, p[0] - cx)
            twig = [p]
            for k in range(1, 5):
                z = p[2] - k * rng.uniform(.06, .14)
                rr = surface(max(z, .06)) + .012
                twig.append((cx + math.cos(ra + da * k / 4) * rr, cy + math.sin(ra + da * k / 4) * rr, max(z, .04)))
            parts.append(fit.wrap(tube(f'{name}_rootlet_{j}', coll, twig, .012, m['bark'], sides=5, radius_end=.003), cx, cy, surface, top))
    # Neighbouring roots fuse into the lattice that makes figs look like they crawl.
    for j in range(n):
        a, b = strands[j], strands[(j + 1) % n]
        for _ in range(int(rng.integers(1, 3))):
            i = int(rng.integers(4, 17))
            i = min(i, len(a) - 5)
            p, q = a[i], b[min(len(b) - 5, i + int(rng.integers(-2, 3)))]
            # The link hugs the surface between the two roots instead of cutting across.
            link = []
            a0 = math.atan2(p[1] - cy, p[0] - cx)
            turn = (math.atan2(q[1] - cy, q[0] - cx) - a0 + math.pi) % math.tau - math.pi  # the short way round
            for k in range(7):
                t = k / 6
                ang = a0 + turn * t
                z = p[2] * (1 - t) + q[2] * t - .05 * math.sin(math.pi * t)
                rr = surface(max(z, .06)) + .016
                link.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr, z))
            parts.append(fit.wrap(tube(f'{name}_web_{j}', coll, link, .018, m['bark'], sides=6, radius_end=.014), cx, cy, surface, top))
    if crown:
        lean_a = rng.uniform(0, math.tau)
        trunk = [(cx + math.cos(lean_a) * .4 * t * t, cy + math.sin(lean_a) * .4 * t * t, top + crown * t) for t in np.linspace(0, 1, 6)]
        crown_parts = [tube(f'{name}_fig_trunk', coll, trunk, .16, m['bark'], sides=8, radius_end=.05)]
        parts += crown_parts
        leaves = []
        for c in range(int(6 + crown * 3)):
            p = trunk[-1]
            leaves.append(((p[0] + rng.normal(0, crown * .45), p[1] + rng.normal(0, crown * .45), p[2] + rng.normal(0, crown * .25)),
                           rng.uniform(1.4, 2.4) * (crown / 3 + .4), rng.uniform(0, math.pi), 0, int(rng.integers(0, 3))))
        crown_parts.append(canopy_sprays(f'{name}_fig_leaves', coll, leaves, forest_materials()['leaf'], rng, per=12))
        parts.append(crown_parts[-1])
    for j in range(int(hang)):
        a = rng.uniform(0, math.tau)
        r = surface(top) + rng.uniform(.1, .6)
        p = (cx + math.cos(a) * r, cy + math.sin(a) * r, top + crown * .6)
        bottom = max(2.3, top - rng.uniform(1, 3))
        if not crown:
            continue  # aerial roots hang from a living tree; with none, they would hang from air
        aerial = tube(f'{name}_aerial_{j}', coll, [p, (p[0] + .05, p[1], (p[2] + bottom) / 2), (p[0] + .04, p[1] + .03, bottom)],
                      .015, m['bark'], sides=4, radius_end=.006)
        fit.crown([aerial], cx, cy, top)
        parts.append(aerial)
    if crown:
        fit.crown(crown_parts, cx, cy, top)
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
    return fit.rest(parts)


def dead_garland(coll, m, name, cx, cy, z, r, rng):
    pts = [(cx + r * math.cos(t), cy + r * math.sin(t) * .6, z + .015 * math.sin(t * 5)) for t in np.linspace(0, math.tau, 19)]
    return fit.rest([tube(name, coll, pts, .025, m['garland_dead'], sides=5)])


def candles(coll, m, name, x, y, z, rng):
    parts = []
    for j in range(int(rng.integers(2, 5))):
        bx, by = x + rng.normal(0, .06), y + rng.normal(0, .04)
        h = rng.uniform(.015, .08)
        parts.append(fit.rest([lathe(f'{name}_{j}', coll, [(0, 0), (.012, 0), (.012, h), (.016, h + .004), (0, h + .002)], bx, by, z, m['wax'], segments=8)])[0])
    return parts


# ----------------------------------------------------------- images and shrines


def seated_image(coll, m, name, x, y, yaw, scale=1.0, headless=False, damage=0, seed=0, gilt=False):
    """A seated Buddha image: the real scan in eroded sandstone or worn gilding, from the kit.
    Damaged images are placed respectfully together; none is shown being broken.
    (Advisor review: placement and dressing.)"""
    from pagoda_kit import piece
    if gilt:
        mesh = 'image_gilt_headless' if headless else 'image_gilt'
    else:
        mesh = 'image_headless' if headless else 'image_worn' if damage else 'image_whole'
    return [piece(coll, mesh, name, x, y, .13 * scale, yaw, scale)]


def spirit_house(coll, m, name, x, y, yaw, rng, fallen=False):
    """A worn-out spirit house from the kit: a little board pavilion on a post, its paint long
    gone. Old ones are retired under a big tree; nobody has tended these in a generation.
    Inside each, what was left: a small image, clay figures, a garland, sometimes a
    photograph. (Advisor review.)"""
    from pagoda_kit import material, piece
    from pagoda_photos import plaque
    mesh = ('spirit_house_red', 'spirit_house_ochre', 'spirit_house_stone')[int(rng.integers(0, 3))]
    tilt = (rng.uniform(1.2, 1.5) * rng.choice([-1, 1]), rng.uniform(-.2, .2)) if fallen else (rng.normal(0, .07), rng.normal(0, .07))
    house = piece(coll, mesh, name, x, y, .2 if fallen else 0, yaw, tilt=tilt)
    floor = .905  # post .85 + floor boards
    parts = []
    if rng.random() < .55:
        parts += seated_image(coll, m, name + '_image', 0, .02, 0, .13, headless=rng.random() < .3, gilt=True)
        parts[-1].location.z = floor + .13 * .13
    for j in range(int(rng.integers(1, 4))):
        fx, fy = rng.uniform(-.2, .2), rng.uniform(-.22, -.14)
        parts.append(lathe(f'{name}_figure_{j}', coll, [(0, 0), (.022, 0), (.026, .035), (.017, .07), (.024, .09), (0, .115)], fx, fy, floor, m['clay'], segments=8))
    if rng.random() < .6:
        parts += dead_garland(coll, m, name + '_garland', 0, -.17, floor + .01, .1, rng)
    if rng.random() < .5:
        parts.append(lathe(name + '_bottle', coll, [(0, 0), (.03, 0), (.032, .12), (.012, .16), (.012, .2), (0, .2)], .2, -.18, floor, m['glass'], segments=8))
    if rng.random() < .3:
        parts.append(plaque(coll, material('M_ep2_funeral_photo'), material('M_ep2_funeral_photo_rim'), name + '_photo',
                            (0, .14, floor + .17), 0, int(rng.choice((4, 5, 8, 10, 0, 3))), height=.16))
    for o in parts:
        o.parent = house
    return house


def sema_stone(coll, m, name, x, y, yaw):
    """A leaf-shaped sema boundary stone on a lotus pedestal, marking consecrated ground."""
    from pagoda_kit import piece
    stone = piece(coll, 'sema_stone', name, x, y, 0, yaw, tilt=(np.random.default_rng(int(abs(x * 31 + y * 7))).normal(0, .05), 0))
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


def temple_wall(coll, m, name, a, b, rng, body='mould_white', breaches=(), height=1.6, bay=3.2, collide=True, open_bays=()):
    """A Thai/Khmer temple enclosure: plinth, plastered brick body, coping with a
    crest of leaf-shaped merlons, piers with lotus-bud finials. Bays lean, the skin
    has scabbed to brick, a few bays have fallen. Axis-aligned from a to b. The
    fallen bays in `open_bays` can be walked through."""
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
        # One collider per run of standing bays, leaving the open breaches clear.
        cuts = [0.0] + [t for i in sorted(open_bays) for t in (i * step, (i + 1) * step)] + [length]
        for k in range(0, len(cuts), 2):
            t0, t1 = cuts[k], cuts[k + 1]
            if t1 - t0 < .01:
                continue
            p0, p1 = at(t0, -.36), at(t1, .36)
            x0, x1 = sorted([p0[0], p1[0]])
            y0, y1 = sorted([p0[1], p1[1]])
            collider(name if k == 0 else f'{name}_{k // 2}', coll, x0, x1, y0, y1, 0, height + .4, 'stone')
    return [o for o in coll.objects if o not in made]


def guardian(coll, m, name, x, y, yaw, rng, headless=False, seed=0):
    """A temple guardian on its plinth: the real Khmer stone figure scan, from the kit, one
    of the pair having lost its head. (Advisor review.)"""
    from pagoda_kit import piece
    body = piece(coll, 'guardian_headless' if headless else 'guardian_whole', name, x, y, 0, yaw)
    collider(name, coll, x - .46, x + .46, y - .46, y + .46, 0, 2.7, 'stone')
    return [body]