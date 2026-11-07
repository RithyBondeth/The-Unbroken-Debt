"""Rituals left in the forest round the pagoda: red string, talismans, dolls and a
black-magic altar, after the user's references (3 November 2026). Metres, X east,
Y north. Red cotton cord (sai sin) is tied for protection in Khmer and Thai practice;
here it is strung too thickly, too often, by someone afraid. The skull altar is
sorcery, not temple practice. (Advisor review: every item.)
"""
import fit
import math

import numpy as np

from kit import lathe, mesh_object, plain, tube, library_material, sag
from pagoda_architecture import Craft
from pagoda_ruin import erode, place_object, sculpt, sphere


def ritual_materials():
    m = {
        'red_thread': plain('M_ep2_red_thread', (.42, .015, .015), rough=.8),
        'talisman': plain('M_ep2_talisman_paper', (.62, .52, .3), rough=.95),
        'talisman_red': plain('M_ep2_talisman_red', (.5, .06, .04), rough=.95),
        'bone': library_material('clay_plaster', 'M_ep2_stone_bone', colour=(.5, .44, .33), tile=.4),
        'marigold': plain('M_ep2_marigold', (.62, .28, .02), rough=.9),
        'marigold_dead': plain('M_ep2_marigold_dead', (.3, .14, .03), rough=.95),
        'wax_red': plain('M_ep2_wax_red', (.4, .05, .04), rough=.5),
        'wax_dark': plain('M_ep2_wax_dark', (.17, .018, .014), rough=.42),  # old red wax, gone dark with soot
        'ribbon_yellow': plain('M_ep2_ribbon_yellow', (.6, .45, .05), rough=.6),
        'doll_cloth': library_material('rough_linen', 'M_ep2_doll_cloth', tint=(.24, .2, .16)),  # handled, rained on, grimy
    }
    for key in ('talisman', 'talisman_red', 'ribbon_yellow'):
        m[key].use_backface_culling = False
    return m


def talisman(coll, m, name, p, rng, mat=None):
    """A paper tag on a thread, curled by damp, a few inked strokes on it."""
    w, h = .06, rng.uniform(.12, .18)
    x, y, z = p
    a = rng.uniform(0, math.tau)
    ca, sa = math.cos(a), math.sin(a)
    c = Craft()
    pts = [(x - ca * w / 2, y - sa * w / 2, z), (x + ca * w / 2, y + sa * w / 2, z),
           (x + ca * w / 2 + rng.normal(0, .01), y + sa * w / 2, z - h), (x - ca * w / 2, y - sa * w / 2 + rng.normal(0, .01), z - h)]
    paper = mat or m['talisman']
    c.face(paper, pts)
    c.face(paper, list(reversed(pts)))
    objs = c.build(name, coll)
    objs.append(tube(name + '_tie', coll, [(x, y, z + .06), (x, y, z)], .0015, m['red_thread'], sides=3))
    return objs


def bell_charm(coll, m, name, p):
    x, y, z = p
    return [lathe(name, coll, [(0, 0), (.012, .002), (.014, .02), (.006, .03), (0, .032)], x, y, z - .032, m['bronze'], segments=8),
            tube(name + '_tie', coll, [(x, y, z + .05), (x, y, z)], .0015, m['red_thread'], sides=3)]


def hanging_doll(coll, m, name, p, rng, drop=.6):
    """A small cloth doll hung by the neck on red cord: sewn shut, stuffed, stained."""
    x, y, z = p
    parts = [
        sphere(name + '_head', coll, (0, 0, -.05), (.035, .035, .04), m['doll_cloth']),
        sphere(name + '_body', coll, (0, 0, -.13), (.04, .03, .065), m['doll_cloth']),
    ]
    for s in (-1, 1):
        parts.append(tube(name + '_arm', coll, [(s * .03, 0, -.1), (s * .06, 0, -.16)], .012, m['doll_cloth'], sides=6))
        parts.append(tube(name + '_leg', coll, [(s * .015, 0, -.18), (s * .02, 0, -.25)], .013, m['doll_cloth'], sides=6))
    body = sculpt(parts, name, voxel=.006, smooth=2, ratio=.5, rough=.002)
    place_object(body, x, y, z - drop, rng.uniform(0, math.tau), (rng.normal(0, .15), rng.normal(0, .15)))
    objs = [body]
    objs.append(tube(name + '_cord', coll, [(x, y, z), (x, y, z - drop + .02)], .0025, m['red_thread'], sides=3))
    # Stitched-shut eyes and a band of red thread round the neck.
    for s in (-1, 1):
        objs.append(tube(name + '_eye', coll, [(x + s * .012 - .006, y - .034, z - drop - .045), (x + s * .012 + .006, y - .034, z - drop - .045)],
                         .0018, m['red_thread'], sides=3))
    return objs


def red_string_web(coll, m, name, anchors, rng, density=1.0):
    """Red cord strung between anchors, criss-crossed, sagging, hung with tags, bells and
    the odd doll: a whole stretch of forest someone has tried to bind."""
    objs = []
    n = len(anchors)
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() > .55 * density:
                continue
            a, b = anchors[i], anchors[j]
            if math.dist(a[:2], b[:2]) > 9:
                continue
            drop = .1 + math.dist(a, b) * .06
            line = sag(a, b, drop, n=14)
            objs.append(tube(f'{name}_cord_{i}_{j}', coll, line, .0035, m['red_thread'], sides=3))
            for k in range(2, 13, 3):
                if rng.random() < .55:
                    p = line[k]
                    r = rng.random()
                    if r < .6:
                        objs += talisman(coll, m, f'{name}_tag_{i}_{j}_{k}', p, rng, m['talisman_red'] if rng.random() < .3 else None)
                    elif r < .85:
                        objs += bell_charm(coll, m, f'{name}_bell_{i}_{j}_{k}', p)
                    else:
                        objs += hanging_doll(coll, m, f'{name}_doll_{i}_{j}_{k}', p, rng, drop=rng.uniform(.25, .6))
    return objs


def bound_trunk(coll, m, name, x, y, r, rng, turns=7):
    """Red cord wound round a trunk again and again, a yantra tag tucked under it."""
    pts = []
    z0 = rng.uniform(.8, 1.2)
    for k in range(turns * 16 + 1):
        a = k / 16 * math.tau
        pts.append((x + math.cos(a) * (r + .01), y + math.sin(a) * (r + .01), z0 + k / 16 * .045 + .01 * math.sin(a * 3)))
    objs = [fit.wrap(tube(name, coll, pts, .004, m['red_thread'], sides=3), x, y, r)]
    a = rng.uniform(0, math.tau)
    tag = talisman(coll, m, name + '_tag', (x + math.cos(a) * (r + .02), y + math.sin(a) * (r + .02), z0 + .15), rng)
    objs += [fit.wrap(o, x, y, r) for o in tag]
    return objs


def boundary_stakes(coll, m, name, points, rng):
    """A ritual boundary of bamboo stakes with red cord between them, a tag on each span."""
    objs = []
    tops = []
    for k, (x, y) in enumerate(points):
        h = rng.uniform(.9, 1.2)
        lean = rng.normal(0, .05, 2)
        top = (x + lean[0], y + lean[1], h)
        tops.append(top)
        objs.append(tube(f'{name}_stake_{k}', coll, [(x, y, -.1), top], .02, m['bamboo_dead'] if 'bamboo_dead' in m else m['bark'], sides=5))
    for k in range(len(tops) - 1):
        a, b = tops[k], tops[k + 1]
        for dz in (0, -.35):
            line = sag((a[0], a[1], a[2] + dz), (b[0], b[1], b[2] + dz), .12, n=10)
            objs.append(tube(f'{name}_cord_{k}_{dz}', coll, line, .003, m['red_thread'], sides=3))
        if rng.random() < .7:
            objs += talisman(coll, m, f'{name}_tag_{k}', sag(a, b, .12, n=10)[5], rng)
    return objs


def _carve(body, cutters):
    """Cuts each cutter out of `body` (real hollows, not black stickers), then drops it."""
    import bpy
    for k, c in enumerate(cutters):
        mod = body.modifiers.new(f'cut_{k}', 'BOOLEAN')
        mod.operation, mod.solver, mod.object = 'DIFFERENCE', 'EXACT', c
        with bpy.context.temp_override(object=body, active_object=body):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(c, do_unlink=True)
    return body


def skull_mesh(coll, m, name, rng, jaw=True, broken=False):
    """An old human skull at the origin, facing -Y: a long braincase, brow ridge, cheekbones
    with their arches, the upper jaw and, if it is still there, the lower one. The eye
    sockets and nose are cut in deep; a broken one has a hole stove into the side."""
    b = m['bone']
    parts = [
        sphere(name + '_cranium', coll, (0, .012, .1), (.069, .092, .078), b, segments=24, rings=16),
        sphere(name + '_occiput', coll, (0, .06, .075), (.06, .05, .055), b),
        sphere(name + '_face', coll, (0, -.052, .056), (.054, .042, .048), b),
        sphere(name + '_brow', coll, (0, -.072, .088), (.059, .022, .016), b),
        sphere(name + '_maxilla', coll, (0, -.072, .028), (.034, .026, .02), b),
    ]
    for s in (-1, 1):
        parts.append(sphere(name + '_cheek', coll, (s * .047, -.058, .052), (.02, .022, .018), b))
        parts.append(tube(name + '_arch', coll, [(s * .05, -.05, .05), (s * .064, -.018, .05), (s * .062, .012, .056)], .007, b, sides=6))
        parts.append(sphere(name + '_mastoid', coll, (s * .056, .03, .036), (.012, .014, .02), b))
    if jaw:
        drop = rng.uniform(0, .012)  # the jaw hangs a little open
        parts.append(tube(name + '_jaw', coll, [(-.052, .0, .05), (-.048, -.03, .012 - drop), (-.03, -.07, .0 - drop), (0, -.08, -.004 - drop),
                                                 (.03, -.07, .0 - drop), (.048, -.03, .012 - drop), (.052, .0, .05)], .009, b, sides=7))
        parts.append(sphere(name + '_chin', coll, (0, -.078, -.002 - drop), (.018, .012, .014), b))
    head = sculpt(parts, name, voxel=.0045, smooth=2, ratio=.16, rough=.0025, seed=float(rng.uniform(0, 50)))
    cutters = [sphere(name + '_cut', coll, (s * .025, -.1, .068), (.018, .034, .017), b) for s in (-1, 1)]
    cutters.append(sphere(name + '_cut', coll, (0, -.1, .04), (.009, .03, .015), b))
    for s in (-1, 1):
        cutters.append(sphere(name + '_cut', coll, (s * .07, -.025, .058), (.016, .026, .013), b))
    if broken:
        side = rng.choice((-1, 1))
        cutters.append(sphere(name + '_cut', coll, (side * .07, .03, .13), (.036, .045, .03), b))
    _carve(head, cutters)
    objs = [head]
    # Dark backs to the holes, set inside the skull so they show only through them.
    for s in (-1, 1):
        objs.append(sphere(name + '_socket', coll, (s * .024, -.07, .068), (.016, .012, .015), m['void'], segments=8, rings=6))
    objs.append(sphere(name + '_nose', coll, (0, -.072, .042), (.008, .008, .012), m['void'], segments=8, rings=6))
    # Bake each sphere's place and size into its mesh, so copies only need moving.
    for o in objs[1:]:
        o.data.transform(o.matrix_basis)
        o.matrix_basis.identity()
    c = Craft()
    for k in range(10):
        if rng.random() < .3:
            continue  # lost teeth
        tx = (k - 4.5) * .0072
        ty = -.078 + .00045 * (k - 4.5) ** 2
        c.block(b, tx, ty, .012, .0064, .006, .012 + rng.uniform(-.002, .002))
    objs += c.build(name + '_teeth', coll)
    return objs


def skull_variants(coll, m, rng, n=5, prefix='skull'):
    """A few skulls to copy, each its own shape. The originals are not placed."""
    return [skull_mesh(coll, m, f'{prefix}_v{k}', rng, jaw=k % 3 != 2, broken=k % 4 == 1) for k in range(n)]


def place_copy(coll, protos, x, y, z, yaw=0.0, tilt=(0.0, 0.0), scale=1.0, name=None):
    """Linked copies of prototype objects built at the origin (the meshes are shared)."""
    out = []
    for o in protos:
        dup = o.copy()
        if name:
            dup.name = name
        coll.objects.link(dup)
        place_object(dup, x, y, z, yaw, tilt)
        dup.scale = tuple(v * scale for v in o.scale)
        out.append(dup)
    return out


def drop_protos(coll, variants):
    for objs in variants:
        for o in objs:
            if o.name in coll.objects:
                coll.objects.unlink(o)


def skull(coll, m, name, x, y, z, yaw, rng):
    """One old human skull, placed (see `skull_mesh`)."""
    objs = skull_mesh(coll, m, name, rng)
    for o in objs:
        place_object(o, x, y, z, yaw)
    return objs


def long_bone(coll, m, name, rng, length=.44):
    """A thigh or arm bone at the origin along Y, lying with its shaft .02 m off the ground:
    a bowed shaft, a ball at one end, two knuckles at the other."""
    b = m['bone']
    half = length / 2
    bow = rng.uniform(.004, .01)
    shaft = [(0, -half + .02, .02), (bow, -half / 2, .021), (bow * 1.4, 0, .022), (bow, half / 2, .021), (0, half - .02, .02)]
    r = length * .027
    parts = [tube(name + '_shaft', coll, shaft, r, b, sides=8)]
    parts.append(sphere(name + '_head', coll, (-.012, half - .005, .024), (r * 1.7, r * 1.7, r * 1.7), b))
    parts.append(sphere(name + '_neck', coll, (-.004, half - .03, .022), (r * 1.2, r * 1.6, r * 1.15), b))
    for s in (-1, 1):
        parts.append(sphere(name + '_knuckle', coll, (s * r * .9, -half + .012, .02), (r * 1.25, r * 1.5, r * 1.3), b))
    return [sculpt(parts, name, voxel=.005, smooth=2, ratio=.12, rough=.0015, seed=float(rng.uniform(0, 50)))]


def rib(coll, m, name, x, y, z, yaw, rng):
    """A loose rib: a thin flat curve lying on its side."""
    a0, span, rr = rng.uniform(0, math.tau), rng.uniform(1.6, 2.2), rng.uniform(.09, .14)
    pts = []
    for k in range(9):
        t = a0 + span * k / 8
        pts.append((x + math.cos(t + yaw) * rr, y + math.sin(t + yaw) * rr, z + .006 + .01 * math.sin(math.pi * k / 8)))
    return tube(name, coll, pts, .0055, m['bone'], sides=4, radius_end=.003)


def wrapped_dead(coll, m, name, x, y, z, yaw, rng, length=1.62):
    """A body rolled in an old sleeping mat and tied with cord, the way the poor were carried
    to the cremation ground. This one was laid out here instead and never burnt. Hair spills
    from the head end onto the bricks. Lies along local +Y, head at +Y. (Advisor review.)"""
    ca, sa = math.cos(yaw), math.sin(yaw)

    def at(lx, ly, lz):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z + lz)

    # Radius along the body, feet to head: narrow at the ankles, broad at the shoulders.
    profile = [(0, .1), (.12, .12), (.45, .15), (.8, .19), (1.15, .2), (1.36, .2), (1.48, .16), (1.62, .14)]

    def section(t, r, grow=1.0):
        """A rolled mat flattens under the weight inside it: wide, low, flat beneath."""
        w, h = r * 1.12 * grow, r * .78 * grow
        s_ = math.sin(t)
        return math.cos(t) * w, h * .55 + s_ * h * (1 if s_ > 0 else .55)

    rings, seg = [], 18
    verts = []
    for ly, r in profile:
        ring = []
        sag_ = rng.normal(0, .006)
        for k in range(seg):
            lx, lz = section(math.tau * k / seg, r)
            ring.append(len(verts))
            verts.append(at(lx + rng.normal(0, .004), ly - length / 2, max(0, lz + sag_)))
        rings.append(ring)
    faces = []
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            faces.append((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    objs = [mesh_object(name + '_mat', coll, verts, faces, m['bamboo_wall_2s'], smooth=True)]
    # The open ends: dark inside.
    for ly, r in (profile[0], profile[-1]):
        ring = [section(math.tau * k / 10, r, .85) for k in range(10)]
        objs.append(mesh_object(name + '_end', coll, [at(lx, ly - length / 2, lz + .01) for lx, lz in ring],
                                [tuple(range(10)), tuple(reversed(range(10)))], m['void']))
    # Cord tied round it in four places, knotted on top.
    for ly in (.2, .62, 1.05, 1.42):
        r = next(rr for yy, rr in profile if yy >= ly)
        loop = [section(math.tau * k / 16, r, 1.05) for k in range(17)]
        objs.append(tube(name + '_cord', coll, [at(lx, ly - length / 2, max(.004, lz)) for lx, lz in loop], .006, m['rope'], sides=4))
        top = section(math.pi / 2, r, 1.05)[1]
        objs.append(tube(name + '_knot', coll, [at(-.02, ly - length / 2 - .02, top), at(.03, ly - length / 2 + .03, top + .02)], .012, m['rope'], sides=5))
    # Long black hair out of the head end, lying in strands.
    for k in range(34):
        lx0 = rng.uniform(-.09, .09)
        lz0 = rng.uniform(.06, .2)
        reach = rng.uniform(.25, .7)
        spread = rng.normal(0, .18)
        pts = [at(lx0, length / 2 - .02, lz0)]
        for j in range(1, 6):
            t = j / 5
            pts.append(at(lx0 + spread * t * reach, length / 2 + reach * t, max(.004, lz0 * (1 - t) ** 2)))
        objs.append(tube(name + '_hair', coll, pts, .0028, m['hair'], sides=3, radius_end=.0012))
    return objs


def bier(coll, m, name, x, y, z, yaw, length=1.9, width=.62):
    """Two bamboo carrying poles with slats across: the litter the dead were brought on."""
    ca, sa = math.cos(yaw), math.sin(yaw)

    def at(lx, ly, lz):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z + lz)
    objs = []
    for s in (-1, 1):
        objs.append(tube(name + '_pole', coll, [at(s * width / 2, -length / 2 - .25, .035), at(s * width / 2, length / 2 + .25, .035)], .035, m['bamboo_dead'], sides=7))
    for k in range(9):
        ly = -length / 2 + .1 + k * (length - .2) / 8
        objs.append(tube(name + '_slat', coll, [at(-width / 2 - .03, ly, .072), at(width / 2 + .03, ly, .072)], .016, m['bamboo_dead'], sides=5))
    return objs


def skull_stake(coll, m, name, protos, x, y, rng, height=None):
    """A bamboo stake with a skull jammed on top, red cord wound under it and a tag:
    a warning at the way in. (Advisor review.)"""
    h = height or rng.uniform(1.25, 1.6)
    lean = rng.normal(0, .05, 2)
    top = (x + lean[0], y + lean[1], h)
    objs = [tube(name + '_stake', coll, [(x, y, -.1), top], .024, m['bamboo_dead'], sides=6, radius_end=.018)]
    objs += place_copy(coll, protos, top[0], top[1], top[2] - .035, rng.uniform(-.6, .6) + math.pi, (rng.normal(0, .12), rng.normal(0, .12)))
    pts = []
    z0 = h - .32
    for k in range(5 * 12 + 1):
        a = k / 12 * math.tau
        t = (z0 + k / 12 * .03 - .0) / h
        pts.append((x + lean[0] * t + math.cos(a) * .028, y + lean[1] * t + math.sin(a) * .028, z0 + k / 12 * .03))
    objs.append(tube(name + '_cord', coll, pts, .003, m['red_thread'], sides=3))
    objs += talisman(coll, m, name + '_tag', (x + lean[0] * .8 + .03, y + lean[1] * .8, h - .34), rng, m['talisman_red'] if rng.random() < .4 else None)
    return objs


def pyre_remains(coll, m, name, x, y, z, rng, protos=None):
    """Where something was burnt and left: a grey ash bed, charred logs fallen in on it,
    scorched bricks and bone gone white-grey in the fire."""
    objs = []
    # The ash bed: a low irregular mound.
    seg, verts, faces = 20, [(x, y, z + .05)], []
    for k in range(seg):
        a = math.tau * k / seg
        r = .95 * rng.uniform(.8, 1.15)
        verts.append((x + math.cos(a) * r, y + math.sin(a) * r * .8, z + .004))
    for k in range(seg):
        faces.append((0, 1 + k, 1 + (k + 1) % seg))
    objs.append(mesh_object(name + '_ash', coll, verts, faces, m['ash'], smooth=True))
    # Charred logs, some half burnt through.
    for k in range(7):
        a = rng.uniform(0, math.pi)
        length = rng.uniform(.6, 1.2)
        cx, cy = x + rng.normal(0, .25), y + rng.normal(0, .2)
        dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
        h = .04 + .05 * (k % 3)
        objs.append(tube(name + '_log', coll, [(cx - dx, cy - dy, z + h), (cx, cy, z + h + .03), (cx + dx, cy + dy, z + h * .6)],
                         rng.uniform(.035, .06), m['burnt'], sides=7, radius_end=rng.uniform(.012, .03)))
    # Burnt bone among the ash.
    for k in range(10):
        bx, by = x + rng.normal(0, .35), y + rng.normal(0, .28)
        a = rng.uniform(0, math.tau)
        L = rng.uniform(.05, .16)
        objs.append(tube(name + '_bone', coll, [(bx, by, z + .03), (bx + math.cos(a) * L, by + math.sin(a) * L, z + .035)], rng.uniform(.006, .011), m['ash'], sides=5))
    if protos:
        objs += place_copy(coll, protos, x + .3, y - .1, z + .02, rng.uniform(0, math.tau), (1.2, .3))
    return objs


def funeral_tatter(coll, m, name, x, y, top, rng, drop=None, width=None):
    """A strip of white funeral cloth caught high in the trees, torn ragged at the hem."""
    from kit import cloth
    drop = drop or rng.uniform(1.1, 2.0)
    width = width or rng.uniform(.18, .34)
    a = rng.uniform(0, math.pi)
    o = cloth(name, coll, -width / 2, width / 2, -drop, 0, 0, m['white_cloth'], folds=2, depth=.03, segments=(6, 12))
    # Rag the hem and let it twist as it hangs.
    for v in o.data.vertices:
        t = -v.co.z / drop
        if t > .85:
            v.co.z += rng.uniform(0, .25) * (t - .85) / .15 * drop * .4
        tw = t * rng.uniform(.3, .9)
        vx, vy = v.co.x, v.co.y
        v.co.x, v.co.y = vx * math.cos(tw) - vy * math.sin(tw), vx * math.sin(tw) + vy * math.cos(tw)
    place_object(o, x, y, top, a, (rng.normal(0, .06), rng.normal(0, .06)))
    return [o, tube(name + '_tie', coll, [(x, y, top + .08), (x, y, top)], .004, m['red_thread'], sides=3)]


def candle_cluster(coll, m, name, x, y, z, rng, n=7, r=.22):
    """Red candles burnt down to stubs in their own puddles, stuck to the bricks."""
    objs = []
    for k in range(n):
        a, d = rng.uniform(0, math.tau), r * math.sqrt(rng.random())
        px, py = x + math.cos(a) * d, y + math.sin(a) * d
        h = rng.uniform(.03, .19)
        w = rng.uniform(.009, .013)
        # Thin temple tapers, burnt down unevenly, the wax run down one side into a skin.
        objs.append(lathe(f'{name}_candle', coll, [(.0, 0), (w * 1.5, 0), (w * 1.1, .006), (w, h * .8), (w * .8, h), (w * .3, h + .003), (0, h + .002)],
                          px, py, z, m['wax_dark'], segments=8))
        objs.append(tube(f'{name}_wick', coll, [(px, py, z + h), (px + rng.normal(0, .002), py, z + h + .012)], .0012, m['void'], sides=3))
        pr = rng.uniform(.018, .032)
        objs.append(lathe(f'{name}_pool', coll, [(0, 0), (pr, 0), (pr * .7, .0025), (0, .003)], px + rng.normal(0, .006), py + rng.normal(0, .006), z, m['wax_dark'], segments=9))
    return objs


def marigold_garland(coll, m, name, path, rng, dead=.3):
    objs = []
    for (a, b) in zip(path, path[1:]):
        for t in np.linspace(0, 1, 6, endpoint=False):
            p = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
            mat = m['marigold_dead'] if rng.random() < dead else m['marigold']
            objs.append(sphere(name, coll, p, (.018, .018, .016), mat, segments=8, rings=5))
    return objs


def sorcery_altar(coll, m, name, x, y, yaw, rng):
    """A black-magic altar in the forest: a low stand under a red cloth, a skull on a
    pedestal, melted red candles, a sheaf of burnt-out incense, marigold garlands,
    red and yellow ribbons, little figures. Someone still comes. (Advisor review.)"""
    objs = []
    ca, sa = math.cos(yaw), math.sin(yaw)

    def at(lx, ly, z=0.0):
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z)
    c = Craft()
    for lx, ly, w, d, h, z in [(0, 0, 1.1, .6, .06, .5), (0, .18, 1.0, .25, .45, .56)]:
        px, py, _ = at(lx, ly)
        c.block(m['lacquer'], px, py, z, w, d, h)
    objs += c.build(name + '_stand', coll)
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py, _ = at(sx * .5, sy * .25)
            objs.append(tube(name + '_leg', coll, [(px, py, 0), (px, py, .5)], .025, m['lacquer'], sides=6))
    px, py, _ = at(0, 0)
    objs.append(mesh_object(name + '_cloth', coll, [at(-.56, -.31, .565), at(.56, -.31, .565), at(.56, -.31, .25), at(-.56, -.31, .25)],
                            [(0, 1, 2, 3), (3, 2, 1, 0)], m['red_cloth']))
    sx, sy, _ = at(0, .18)
    objs.append(lathe(name + '_pedestal', coll, [(.08, 0), (.06, .04), (.04, .1), (.07, .14)], sx, sy, 1.01, m['bronze'], segments=12))
    objs += skull(coll, m, name + '_skull', sx, sy, 1.15, yaw, rng)
    for k in range(7):
        lx = -.42 + k * .14
        px, py, _ = at(lx, -.12)
        h = rng.uniform(.05, .2)
        objs.append(lathe(name + f'_candle_{k}', coll, [(.02, 0), (.026, .01), (.016, .02), (.015, h), (0, h + .005)], px, py, .56, m['wax_red'], segments=8))
        objs.append(lathe(name + f'_drip_{k}', coll, [(.03, 0), (.04, .005), (0, .008)], px, py, .56, m['wax_red'], segments=8))
    px, py, _ = at(.32, .05)
    objs.append(lathe(name + '_incense_pot', coll, [(0, 0), (.07, 0), (.09, .06), (.08, .12), (0, .1)], px, py, .56, m['clay'], segments=12))
    for k in range(40):
        a, r = rng.uniform(0, math.tau), rng.uniform(0, .05)
        bx, by = px + math.cos(a) * r, py + math.sin(a) * r
        objs.append(tube(name + '_stick', coll, [(bx, by, .66), (bx + rng.normal(0, .04), by + rng.normal(0, .04), .66 + rng.uniform(.15, .35))],
                         .002, m['red_cloth'], sides=3))
    for side in (-1, 1):
        path = [at(side * .56, -.31, .56), at(side * .45, -.33, .38), at(side * .3, -.32, .46), at(side * .1, -.31, .55)]
        objs += marigold_garland(coll, m, name + '_garland', path, rng)
        rx, ry, _ = at(side * .5, .1)
        for k, mat in enumerate((m['red_cloth'], m['ribbon_yellow'])):
            objs.append(tube(name + '_ribbon', coll, [(rx, ry, 1.0), (rx + side * .05, ry, .8 - k * .1), (rx + side * .02, ry + .03, .6)], .012, mat, sides=3))
    for k in range(4):
        fx, fy, _ = at(-.35 + k * .22, .02)
        objs.append(lathe(name + f'_figure_{k}', coll, [(0, 0), (.02, 0), (.025, .03), (.015, .06), (.02, .075), (0, .1)], fx, fy, .56, m['gold_leaf'], segments=8))
    erode([o for o in objs if o.name.startswith(name + '_stand')], .004, 9)
    return objs


def handprints(coll, m, name, spots, rng):
    """Old rust-red handprints on walls (tools/drawings/ep2.mjs), one print per decal.
    Each spot is (x, y, z, facing): facing -1 for a wall facing south (-Y), 0 for a
    side wall facing out east or west."""
    import os
    from kit import ROOT, image_material
    mat = m.get('handprints')
    if mat is None:
        path = os.path.join(ROOT, 'art-source/textures/ep2', 'T_ep2_handprints_BC.png')
        mat = m['handprints'] = image_material('M_ep2_handprints', path, rough=.9, cutout=True)
    objs = []
    for k, (x, y, z, facing) in enumerate(spots):
        w, h = rng.uniform(.38, .5), rng.uniform(.75, .95)
        cell = int(rng.integers(0, 4))
        u0, u1 = cell / 4, (cell + 1) / 4
        tilt = rng.normal(0, .12)
        if facing:
            corners = [(x - w / 2, y, z - h), (x + w / 2, y, z - h), (x + w / 2 + tilt * h, y, z), (x - w / 2 + tilt * h, y, z)]
        else:
            out = -.012 if x < 22 else .012
            corners = [(x + out, y - w / 2, z - h), (x + out, y + w / 2, z - h), (x + out, y + w / 2 + tilt * h, z), (x + out, y - w / 2 + tilt * h, z)]
        uvs = [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
        objs.append(mesh_object(f'{name}_{k}', coll, corners, [(0, 1, 2, 3)], mat, uvs=uvs))
    return objs
