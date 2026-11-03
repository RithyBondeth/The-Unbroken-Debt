"""Offerings close enough to pick up, made to read as real things rather than shapes:
pressed sticky rice on a cut banana leaf, lotus buds of overlapping petals, hand-thrown
terracotta bowls and bronze gone green with age. Each has its own colour and relief
map (weathering.save), drawn from what the real material looks like up close.
Metres, X east, Y north.
"""
import math

import bmesh
import bpy
import numpy as np

from kit import image_material, lathe, mesh_object, tube
from weathering import fbm, save, tile_noise


def _with_normal(mat, normal_image, strength):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = normal_image
    n = nodes.new('ShaderNodeNormalMap')
    n.inputs['Strength'].default_value = strength
    links.new(tex.outputs['Color'], n.inputs['Color'])
    links.new(n.outputs['Normal'], nodes['Principled BSDF'].inputs['Normal'])
    return mat


def offering_materials():
    rng = np.random.default_rng(5150)
    s = 512
    u, v = np.meshgrid(np.linspace(0, 1, s), np.linspace(0, 1, s))
    m = {}
    # Sticky rice: packed grains, each catching light along its length.
    grains = tile_noise(s, 150, rng) ** 1.6
    clump = fbm(s, rng, ((12, .6), (40, .4)))
    rgb = np.dstack([.8 + .12 * grains, .77 + .11 * grains, .66 + .08 * grains]) * (.82 + .22 * clump[..., None])
    path, n = save('T_ep2_sticky_rice', rgb, grains * .7 + clump * .3, 3.2)
    m['sticky_rice'] = _with_normal(image_material('M_ep2_sticky_rice', path, rough=.58), n, 1.0)
    # Banana leaf, U along the leaf: pale midrib, close parallel veins running out
    # from it, yellowing and brown, split edges where it has dried.
    side = np.abs(v - .5) * 2
    veins = .5 + .5 * np.sin((u * 70 + side * 9) * math.pi)
    mottle = fbm(s, rng, ((6, .6), (19, .4)))
    green = np.array([.07, .15, .045]) * (.75 + .5 * mottle[..., None]) * (.95 + .05 * veins[..., None])
    rib = np.exp(-((v - .5) / .018) ** 2)[..., None]
    rgb = green * (1 - rib) + np.array([.32, .36, .16]) * rib
    dry = np.clip((side - .78 - .12 * mottle) * 6, 0, 1)[..., None]
    rgb = rgb * (1 - dry) + np.array([.24, .17, .07]) * (.8 + .4 * mottle[..., None]) * dry
    path, n = save('T_ep2_banana_leaf', rgb, veins * .25 + rib[..., 0] * .8, 1.2)
    m['banana_leaf'] = _with_normal(image_material('M_ep2_banana_leaf_real', path, rough=.5), n, .7)
    m['banana_leaf'].use_backface_culling = False
    # Lotus petal, V from base to tip: green-white at the base, blush, a deep pink tip,
    # fine veins running the petal's length.
    t = v[..., None]
    base, blush, tip = np.array([.56, .62, .44]), np.array([.78, .5, .55]), np.array([.62, .16, .3])
    rgb = np.where(t < .45, base + (blush - base) * (t / .45), blush + (tip - blush) * ((t - .45) / .55) ** 1.3)
    fine = .5 + .5 * np.sin(u * 90 * math.pi + np.sin(v * 7) * 2)
    rgb = rgb * (.9 + .1 * fine[..., None]) * (.93 + .14 * fbm(s, rng, ((8, .6), (30, .4)))[..., None])
    path, n = save('T_ep2_lotus_petal', rgb, fine * .4, 1.2)
    m['lotus_petal'] = _with_normal(image_material('M_ep2_lotus_petal', path, rough=.45), n, .5)
    m['lotus_petal'].use_backface_culling = False
    m['lotus_stem'] = image_material('M_ep2_lotus_stem', save('T_ep2_lotus_stem', np.dstack([
        .1 + .04 * fine, .19 + .05 * fine, .07 + .02 * fine]) * (.85 + .3 * fbm(s, rng, ((10, 1),)))[..., None], fine * .3, 1.0)[0], rough=.6)
    # Terracotta: speckled fired clay, grit, darker fire clouds and soot.
    grit = tile_noise(s, 200, rng)
    cloud = fbm(s, rng, ((4, .6), (11, .4)))
    rgb = np.array([.34, .18, .1]) * (.8 + .3 * cloud[..., None]) * (.94 + .08 * grit[..., None])
    soot = np.clip((cloud - .62) * 3, 0, 1)[..., None]
    rgb = rgb * (1 - .7 * soot)
    path, n = save('T_ep2_terracotta', rgb, grit * .3 + cloud * .7, .6)
    m['terracotta'] = _with_normal(image_material('M_ep2_terracotta', path, rough=.88), n, .15)
    # Old bronze: dark brown metal, verdigris crusted in the hollows, worn bright where
    # hands touch it.
    crust = fbm(s, rng, ((9, .4), (31, .35), (90, .25)))
    green = np.clip((crust - .7) * 3, 0, 1)[..., None] * .8
    rgb = np.array([.3, .2, .09]) * (.82 + .25 * crust[..., None])
    rgb = rgb * (1 - green) + np.array([.2, .33, .27]) * (.8 + .3 * crust[..., None]) * green
    path, n = save('T_ep2_bronze_patina', rgb, crust, .5)
    m['bronze'] = _with_normal(image_material('M_ep2_bronze_patina', path, rough=.5, metal=.65), n, .2)
    return m


def _uv_sphere(name, coll, mat, segments=40, rings=26):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1, calc_uvs=True)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return o


def sticky_rice_ball(coll, m, name, x, y, z, rng):
    """Sticky rice pressed in the hand: lumpy, flattened where it sits, its surface
    broken into grains."""
    o = _uv_sphere(name, coll, m['sticky_rice'])
    seed = rng.uniform(0, 9)
    for v in o.data.vertices:
        n = v.co.normalized()
        lump = .07 * math.sin(n.x * 5 + seed) * math.cos(n.y * 4 + seed) + .03 * math.sin(n.z * 9)
        grain = .018 * math.sin(n.x * 61 + n.y * 37) * math.sin(n.y * 53 - n.z * 41)
        v.co = n * (1 + lump + grain)
        v.co.z = max(v.co.z, -.55)
    o.scale = (.062, .058, .05)
    o.location = (x, y, z + .028)
    o.rotation_euler.z = rng.uniform(0, math.tau)
    return o


def banana_leaf_piece(coll, m, name, x, y, z, rng, length=.46, width=.3, yaw=0.0):
    """A square cut of banana leaf as a tray liner: folded a little along the midrib,
    rippled across its veins, its dried edges lifting where they have split."""
    nx, ny = 28, 16
    verts, faces, uvs = [], [], []
    tears = [rng.uniform(.1, .9) for _ in range(3)]
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, t = i / nx, j / ny
            side = abs(t - .5) * 2
            h = .006 * side + .004 * math.sin(u * 46) * side + .012 * side ** 3
            if any(abs(u - tr) < .015 for tr in tears) and side > .55:
                h += .01 * side  # the split lifts
            verts.append(((u - .5) * length, (t - .5) * width * (1 - .06 * math.sin(u * math.pi * 3)), h))
            uvs.append((u, t))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    leaf = mesh_object(name, coll, verts, faces, m['banana_leaf'], uvs=[uvs[i] for f in faces for i in f], smooth=True)
    leaf.location = (x, y, z)
    leaf.rotation_euler.z = yaw
    return leaf


def lotus_bud(coll, m, name, x, y, z, rng, height=.15, lying=True, yaw=None):
    """A closed lotus bud: two whorls of three petals, each a curved shell wrapping
    the one inside, drawn to a point; sepals at the base and a long stem."""
    verts, faces, uvs = [], [], []
    nu, nv = 9, 14
    for whorl, (scale, turn) in enumerate(((1.0, 0.0), (.9, math.pi / 3))):
        for k in range(3):
            a0 = turn + k * math.tau / 3 + rng.normal(0, .08)
            base = len(verts)
            for j in range(nv + 1):
                t = j / nv
                # Full low down, drawn out to a long point: a bud twice as long as wide.
                r = .031 * scale * math.sin(math.pi * min(1, t * 1.6) ** .7) ** .8 * (1 - t) ** .55
                spread = 1.25 * (1 - .35 * t)
                for i in range(nu + 1):
                    s = i / nu * 2 - 1
                    a = a0 + s * spread
                    cup = r * (1 + .06 * (1 - s * s))
                    verts.append((cup * math.cos(a), cup * math.sin(a), height * t * scale + .004 * whorl))
                    uvs.append(((s + 1) / 2, t))
            for j in range(nv):
                for i in range(nu):
                    q = base + j * (nu + 1) + i
                    faces.append((q, q + 1, q + nu + 2, q + nu + 1))
    bud = mesh_object(name, coll, verts, faces, m['lotus_petal'], uvs=[uvs[i] for f in faces for i in f], smooth=True)
    objs = [bud]
    if lying:
        # Laid on its side on the tray, the stem trailing off behind it.
        bud.rotation_euler = (0, math.pi / 2 - .12, rng.uniform(0, math.tau) if yaw is None else yaw)
        bud.location = (x, y, z + .03)
        a = bud.rotation_euler.z
        back = (x - math.cos(a) * .01, y - math.sin(a) * .01, z + .04)
        stem = [back, (back[0] - math.cos(a) * .12, back[1] - math.sin(a) * .12 + .02, z + .012),
                (back[0] - math.cos(a) * .26, back[1] - math.sin(a) * .26 + .01, z + .008)]
        objs.append(tube(name + '_stem', coll, stem, .0065, m['lotus_stem'], sides=8))
    else:
        bud.location = (x, y, z)
    return objs


def terracotta_bowl(coll, m, name, x, y, z, rng, size=.82):
    """A small hand-thrown bowl: foot ring, flared wall, rolled lip; never quite round."""
    prof = [(0, 0), (.035, 0), (.04, .006), (.036, .012), (.06, .017), (.098, .04), (.116, .068),
            (.121, .077), (.115, .081), (.104, .072), (.084, .037), (.046, .023), (0, .021)]
    bowl = lathe(name, coll, [(r * size, h * size) for r, h in prof], x, y, z, m['terracotta'], segments=40)
    wob = rng.uniform(0, 9)
    for v in bowl.data.vertices:
        dx, dy = v.co.x - x, v.co.y - y
        r = math.hypot(dx, dy)
        if r > .03 * size:
            a = math.atan2(dy, dx)
            k = 1 + .025 * math.sin(a * 2 + wob) + .01 * math.sin(a * 5 + wob * 2)
            v.co.x, v.co.y = x + dx * k, y + dy * k
            v.co.z += .003 * math.sin(a * 3 + wob) * (v.co.z - z) / (.08 * size)
    for p in bowl.data.polygons:
        p.use_smooth = True
    return bowl


def tray_places(x, y, count=3, radius=.135, turn=.4):
    """Where `count` offerings sit on one footed tray: spaced evenly in a ring, never
    touching (a 20 cm bowl at radius .135 leaves about 3 cm between neighbours)."""
    return [(x + radius * math.cos(turn + k * math.tau / count), y + radius * math.sin(turn + k * math.tau / count))
            for k in range(count)]


def lotus_bunch(x, y, count=3, yaw=.5, gap=.07):
    """Where the buds of one bunch lie: side by side, heads together, stems all
    trailing the same way, as they are laid down as an offering."""
    side = (-math.sin(yaw), math.cos(yaw))
    return [(x + math.cos(yaw) * .09 + side[0] * gap * (k - (count - 1) / 2),
             y + math.sin(yaw) * .09 + side[1] * gap * (k - (count - 1) / 2), yaw) for k in range(count)]
