"""Sculpts and bakes Episode 2's masonry and statuary, and prints the funeral photographs,
into the kit that the area places (tools/areas/pagoda_kit.py). Run this before the area
whenever they change.
blender -b --factory-startup -P tools/ep2/build-stupas.py [-- stupas|statues|<statue>...]

Stupas are modelled here in full. The statues start from photogrammetry scans already in
the project: seated Buddha (Francesco Coldesina, CC-BY 4.0), Prajnaparamita (Minneapolis
Institute of Art, CC0) and naga finial (Cleveland Museum of Art, CC0). Their shapes are
real; the stone, gilding and damage are this pipeline's.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/areas'), str(ROOT / 'tools/ep2')]
import pagoda_photos as P  # noqa: E402
import pagoda_scans as SC  # noqa: E402
import pagoda_stupa_kit as S  # noqa: E402

STUPAS = (('spire', 4.2, False), ('bell', 9.1, False), ('bud', 13.7, False), ('prang', 21.3, False),
          ('spire', 27.9, True), ('bell', 33.3, True))
HEIGHTS = {'spire': 3.4, 'bell': 3.3, 'bud': 3.2, 'prang': 3.45}


def forget(name):
    """Clears an earlier build of a piece, so a rebuild does not end up named `name.001`."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    for block, key in ((bpy.data.meshes, name), (bpy.data.materials, name + '_stone'),
                       (bpy.data.images, f'T_ep2_{name}_BC'), (bpy.data.images, f'T_ep2_{name}_N')):
        found = block.get(key)
        if found:
            block.remove(found)


def behead(obj, neck, radius, seed):
    """Takes off a scan's head by crushing everything above `neck` down into a rough stump,
    which keeps the scan a closed skin, as the fusing needs. `neck` is in the object's own
    height, base at 0."""
    me = obj.data
    band = [v.co for v in me.vertices if neck - .03 < v.co.z < neck]
    cx = sum(c.x for c in band) / len(band)
    cy = sum(c.y for c in band) / len(band)
    for v in me.vertices:
        if v.co.z <= neck:
            continue
        dx, dy = v.co.x - cx, v.co.y - cy
        r = math.hypot(dx, dy) or 1e-6
        keep = min(r, radius) / r
        v.co.x, v.co.y = cx + dx * keep, cy + dy * keep
        v.co.z = neck + radius * .22 * (S._fbm(Vector((v.co.x, v.co.y, 0)), 3, radius * .55, seed) + .6)
    me.update()


def finish(high, name, coll, palette, seed, voxel, scale, faces, size, chamber=False, before=None, scan=None, relief=.0, real_colour=False, **material):
    """Fuse, sculpt, bake, and throw the sculpt and any source scan away, leaving the game mesh."""
    forget(name)
    S.remesh(high, voxel)
    colours = None
    if scan:
        surface = S.ScanSurface(scan)
        colours = surface.emboss(high, relief, keep_colour=real_colour)
    if before:
        before(high)
    S.weather(high, seed, palette, scale=scale, chamber=chamber, surface_colours=colours)
    if scan:
        mesh = scan.data
        bpy.data.objects.remove(scan, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    low, _ = S.bake_down(high, name, coll, faces=faces, size=size, **material)
    mesh = high.data
    bpy.data.objects.remove(high, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return low


def build_stupas(coll):
    for form, seed, broken in STUPAS:
        name = f'stupa_{form}' + ('_broken' if broken else '')
        high, _ = S.shape(form, coll, name + '_high', height=HEIGHTS[form], broken=broken)
        finish(high, name, coll, 'lime', seed, .0055, 1.0, 26000, 2048, chamber=True)


def _lotus_base(s, r=.46, z0=-.13, h=.13, petals=18):
    """A round pedestal with a row of lotus petals, for a seated image. Top at z0 + h."""
    s.lathe(0, 0, z0, [(r * 1.08, 0), (r * 1.12, h * .25), (r * .96, h * .45), (r * .9, h * .7), (r * 1.02, h), (r * .2, h)], 40)
    for j in range(petals):
        a = j / petals * math.tau
        out = Vector((math.cos(a), math.sin(a), 0))
        along = Vector((-math.sin(a), math.cos(a), 0))
        w = r * .19
        pts = [(-w, 0), (w, 0), (w * .9, h * .4), (0, h * .86), (-w * .9, h * .4)]
        s.prism(pts, out * (r * .93) + Vector((0, 0, z0 + h * .1)), along, Vector((0, 0, 1)) - out * .2, out, .02)


def seated_image(coll, name, palette, seed, headless=False, worn=False, size=1536):
    """The seated Buddha scan on a lotus pedestal, 1.1 m from its seat to its crown."""
    src = SC.scan(coll, 'buddha_seated', name + '_scan', height=1.1)
    if headless:
        behead(src, .7, .085, seed)
    s = S.Solid()
    s.add_object(src)
    _lotus_base(s)
    high = s.build(name + '_high', coll)

    def before(o):
        if worn:
            # Rain has taken the face: nose and lips gone flat, the eyes only hollows.
            me = o.data
            for v in me.vertices:
                if v.co.z > .7 and v.co.y < 0:
                    n = S._fbm(v.co, 3, .045, seed)
                    v.co.y += max(0, (.018 + n * .018)) * min(1, (v.co.z - .7) / .05)
            me.update()
    gilt = palette == 'gilt'
    return finish(high, name, coll, palette, seed, .0035, .5, 24000, size, before=before, scan=src, relief=.0045,
                  roughness=.55 if gilt else .92, metallic=.55 if gilt else 0.0)


def devata(coll, name, seed, headless=False):
    """The real Khmer goddess scan as a weathered guardian on a stepped plinth, base at z 0."""
    plinth = .62
    src = SC.scan(coll, 'prajnaparamita', name + '_scan', height=1.95, at=(0, 0, plinth))
    if headless:
        behead(src, 1.46, .09, seed)
    s = S.Solid()
    s.add_object(src)
    s.box(0, 0, 0, .92, .92, .14)
    s.box(0, 0, .14, .78, .78, .4)
    s.box(0, 0, .54, .88, .88, .08)
    high = s.build(name + '_high', coll)
    return finish(high, name, coll, 'sandstone', seed, .005, .75, 30000, 2048, scan=src, relief=.005, real_colour=True)


def naga_rail(coll, name, seed):
    """A naga balustrade: stepped stone base, a scaled body, and the real naga finial scan as
    its hoods. Authored for its head at y 0 looking along -Y, its tail running away to -5.45,
    the way the old rail was; the game's rail is placed with its head towards the gate."""
    s = S.Solid()
    # Base and coping, y from -5.75 to .1 about this rail's origin.
    s.box(0, -2.72, -.4, .62, 5.8, .18)
    s.box(0, -2.72, -.22, .48, 5.7, .22)
    body = [(0, -5.3, .05), (0, -3.6, .07), (0, -1.8, .1), (0, -.7, .2), (0, -.25, .5), (0, -.05, .85), (0, .03, 1.02)]
    s.tube(body, .165, .15, sides=22)
    s.lathe(0, -5.42, 0, [(.08, 0), (.1, .08), (.04, .15)], 14)
    src = SC.scan(coll, 'naga_finial', name + '_scan', height=1.15, at=(0, .02, .78))
    s.add_object(src)
    high = s.build(name + '_high', coll)

    def before(o):
        # Overlapping scales along the serpent's back.
        me = o.data
        for v in me.vertices:
            if v.co.z > 0 and v.co.z < 1.0 and v.co.y < -.1:
                a = math.atan2(v.co.x, v.co.z - .05)
                k = .5 + .5 * math.sin(v.co.y * 44 + a * 7) * math.sin(v.co.y * 44 - a * 7)
                v.co += v.normal * .012 * (k - .5)
        me.update()
    return finish(high, name, coll, 'sandstone', seed, .0065, .7, 30000, 2048, before=before, scan=src, relief=.004)


def sema(coll, name, seed):
    """A leaf-shaped sema boundary stone on a lotus pedestal."""
    s = S.Solid()
    s.lathe(0, 0, 0, [(.32, 0), (.33, .08), (.25, .12), (.2, .2), (.27, .26), (.27, .3), (.1, .3)], 28)
    outline = [(-.22, 0), (-.26, .2), (-.24, .45), (-.17, .66), (-.07, .8), (0, .9), (.07, .8), (.17, .66), (.24, .45), (.26, .2), (.22, 0)]
    s.prism(outline, (0, -.04, .3), (1, 0, 0), (0, 0, 1), (0, 1, 0), .08)
    boss = [(px * .55, pz * .78 + .07) for px, pz in outline]
    s.prism(boss, (0, -.06, .3), (1, 0, 0), (0, 0, 1), (0, 1, 0), .12)
    for k, pz in enumerate((.18, .34, .5, .63)):
        w = .1 - k * .012
        s.prism([(-w, pz), (w, pz), (w * .7, pz + .03), (-w * .7, pz + .03)], (0, -.072, .3), (1, 0, 0), (0, 0, 1), (0, 1, 0), .15)
    high = s.build(name + '_high', coll)
    return finish(high, name, coll, 'sandstone', seed, .0035, .5, 9000, 1024)


def spirit_house(coll, name, palette, seed, post=.85):
    """A spirit house on a post: a little tiled pavilion of old painted boards, its door a
    black gap, its gable ends carved. Origin at the post's foot."""
    s = S.Solid()
    s.box(0, 0, 0, .15, .15, .08)
    s.box(0, 0, .08, .11, .11, post - .08)
    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        s.tube([(sx * .05, sy * .05, post - .24), (sx * .22, sy * .17, post - .01)], .017, .014, sides=8)
    z = post
    # Floor, with a railing round its front.
    s.box(0, 0, z, .66, .54, .025)
    s.box(0, 0, z + .025, .6, .48, .03)
    z += .055
    # The room: thin walls round a dark inside, open at a tall door.
    w, d, h = .36, .28, .32
    s.box(-w / 2 + .01, .03, z, .02, d, h)
    s.box(w / 2 - .01, .03, z, .02, d, h)
    s.box(0, d / 2 + .02, z, w, .02, h)
    door = .07
    for sx in (-1, 1):
        s.box(sx * (door + (w / 2 - door) / 2), -d / 2 + .04, z, w / 2 - door, .02, h)
    s.box(0, -d / 2 + .04, z + h - .07, door * 2, .02, .07)
    # Wall boards: proud battens, the grain of which the weathering catches.
    for k in range(-4, 5):
        s.box(k * .04, -d / 2 + .028, z, .012, .012, h)
    # Corner posts and carved door jambs.
    for sx in (-1, 1):
        for sy in (-1, 1):
            s.box(sx * .265, sy * .205, z - .01, .035, .035, h + .02)
        s.box(sx * door, -d / 2 + .02, z, .018, .03, h - .05)
    # Railing.
    for sx in (-1, 1):
        s.box(sx * .28, -.06, z + .08, .012, .32, .012)
        for k in range(4):
            s.box(sx * .28, -.2 + k * .1, z, .01, .01, .08)
    z += h
    # Tiered gable roofs, thick enough to read as boards with tile on them.
    for tier, (span, length, rise, lift) in enumerate(((.42, .64, .2, 0.0), (.3, .48, .18, .115))):
        zz = z + lift
        for side in (-1, 1):
            pts = [(0, zz + rise), (side * span, zz), (side * span, zz - .018), (0, zz + rise - .022)]
            s.prism(pts, (0, -length / 2, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0), length)
        # Gable ends with a flame at each eave.
        for sy in (-1, 1):
            for side in (-1, 1):
                pts = [(0, 0), (.016, .03), (.04, .055), (.018, .06), (.02, .1), (-.006, .07), (-.014, .025)]
                s.prism([(side * x, zt) for x, zt in pts], (side * span, sy * length / 2, zz - .012), (1, 0, 0), (0, 0, 1), (0, 1, 0), .012)
    s.tube([(0, 0, z + .3), (0, 0, z + .56)], .018, .003, sides=8)
    high = s.build(name + '_high', coll)
    return finish(high, name, coll, palette, seed, .0032, .35, 16000, 1024)


def hall_throne(coll, name, seed, s_=1.2):
    """The hall image's lotus throne: drum, two rows of petals, cushion. Top at z 0."""
    s = S.Solid()
    s.lathe(0, 0, -.32 * s_, [(.62 * s_, 0), (.6 * s_, .06 * s_), (.48 * s_, .12 * s_), (.46 * s_, .22 * s_), (.55 * s_, .28 * s_), (.55 * s_, .32 * s_), (.1, .32 * s_)], 48)
    for r, z0, h, count, phase in ((.6 * s_, -.22 * s_, .2 * s_, 22, 0), (.55 * s_, -.12 * s_, .16 * s_, 22, .5)):
        for j in range(count):
            a = (j + phase) / count * math.tau
            out = Vector((math.cos(a), math.sin(a), 0))
            along = Vector((-math.sin(a), math.cos(a), 0))
            w = r * math.pi / count * 1.05
            pts = [(-w * .75, 0), (w * .75, 0), (w, h * .42), (w * .5, h * .8), (0, h), (-w * .5, h * .8), (-w, h * .42)]
            s.prism(pts, out * (r - .01) + Vector((0, 0, z0)), along, Vector((0, 0, 1)) + out * .2, -out, .05)
    high = s.build(name + '_high', coll)
    return finish(high, name, coll, 'gilt', seed, .0045, .5, 16000, 1536, roughness=.55, metallic=.55)


def image_cloth(coll, name):
    """A saffron cloth laid over one shoulder of a seated image and tied at the waist: draped by
    simulation over the image itself. Authored against `image_whole`."""
    import pagoda_kmaoch as K
    from kit import library_material
    mat = library_material('rough_linen', 'M_ep2_image_cloth', tint=(.46, .24, .05))
    mat.use_backface_culling = False
    forget(name)
    collide = bpy.data.objects['image_whole'].copy()
    collide.data = bpy.data.objects['image_whole'].data.copy()
    coll.objects.link(collide)
    collide.modifiers.new('collide', 'COLLISION')
    collide.collision.thickness_outer = .006
    collide.collision.cloth_friction = 10
    # Laid over the left shoulder (about x .17, y .115, z .65 on this statue): the front end
    # slanting in across the chest, the back end falling behind.
    nx, ny = 26, 70
    grid = np.zeros((ny, nx, 3))
    for j in range(ny):
        s = 1.0 * (j / (ny - 1) - .55)
        for i in range(nx):
            t = .24 * (i / (nx - 1) - .5)
            over = max(-.17, min(.17, s))
            drop = max(0, abs(s) - .17)
            grid[j, i] = (.17 + t - .28 * max(0, -s - .05), .115 + over, .685 - drop - abs(over) * .12)
    pins = [j * nx + i for j in range(ny) for i in range(nx) if abs(1.0 * (j / (ny - 1) - .55)) < .025]
    sheet = K._sheet(coll, name, grid, (0, 0, 1.3, 3.6), mat)
    K._simulate(sheet, pins, 90, tension=9, bending=.06)
    sheet.data.name = name
    me = collide.data
    bpy.data.objects.remove(collide, do_unlink=True)
    bpy.data.meshes.remove(me)
    print('Baked', name, len(sheet.data.polygons), 'faces (cloth)', flush=True)
    return sheet


def stupa_cloth(coll, name):
    """A length of cloth tied round a stupa's upper tier, its end hanging: draped by simulation
    round the tier's real shape. The area colours each copy."""
    import pagoda_kmaoch as K
    from kit import library_material
    mat = library_material('rough_linen', 'M_ep2_stupa_cloth', tint=(.6, .58, .5))
    mat.use_backface_culling = False
    forget(name)
    blocker = S.Solid()
    blocker.box(0, 0, 1.45, .92, .92, .22)
    blocker.box(0, 0, 1.67, .84, .84, .16)
    collide = blocker.build('stupa_cloth_blocker', coll)
    collide.modifiers.new('collide', 'COLLISION')
    collide.collision.thickness_outer = .006
    collide.collision.cloth_friction = 8
    # The band: a loop round the tier, a little proud, wide and slack, and then a tail.
    nx, ny = 88, 12
    band = np.zeros((ny, nx, 3))
    half = .455
    for i in range(nx):
        u = i / (nx - 1) * 4
        side, f = int(u) % 4, u % 1
        a, b = {0: ((-half, -half), (half, -half)), 1: ((half, -half), (half, half)), 2: ((half, half), (-half, half)), 3: ((-half, half), (-half, -half))}[side]
        for j in range(ny):
            band[j, i] = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, 1.81 - j * .016)
    sheet = K._sheet(coll, name, band, (0, 0, 4.2, .5), mat)
    K._simulate(sheet, [i for i in range(nx) if i % 11 == 0], 70, tension=9, bending=.05)
    tail_grid = np.zeros((42, 11, 3))
    for j in range(42):
        for i in range(11):
            tail_grid[j, i] = (.1 + i * .016 + j * .002, -half - .012, 1.8 - j * .02)
    tail = K._sheet(coll, name + '_tail', tail_grid, (0, 0, .5, 2), mat)
    K._simulate(tail, list(range(11)), 70, tension=9, bending=.05)
    # One mesh, both pieces.
    bpy.ops.object.select_all(action='DESELECT')
    sheet.select_set(True)
    tail.select_set(True)
    bpy.context.view_layer.objects.active = sheet
    bpy.ops.object.join()
    sheet.data.name = name
    me = collide.data
    bpy.data.objects.remove(collide, do_unlink=True)
    bpy.data.meshes.remove(me)
    print('Baked', name, len(sheet.data.polygons), 'faces (cloth)', flush=True)
    return sheet


STATUES = {
    'image_whole': lambda c: seated_image(c, 'image_whole', 'sandstone', 2.3),
    'image_headless': lambda c: seated_image(c, 'image_headless', 'sandstone', 6.1, headless=True),
    'image_worn': lambda c: seated_image(c, 'image_worn', 'sandstone', 11.7, worn=True),
    'image_gilt': lambda c: seated_image(c, 'image_gilt', 'gilt', 15.2, size=1024),
    'image_gilt_headless': lambda c: seated_image(c, 'image_gilt_headless', 'gilt', 18.4, headless=True, size=1024),
    'guardian_whole': lambda c: devata(c, 'guardian_whole', 23.1),
    'guardian_headless': lambda c: devata(c, 'guardian_headless', 29.6, headless=True),
    'naga_rail': lambda c: naga_rail(c, 'naga_rail', 35.2),
    'sema_stone': lambda c: sema(c, 'sema_stone', 41.7),
    'spirit_house_red': lambda c: spirit_house(c, 'spirit_house_red', 'red', 47.3),
    'spirit_house_ochre': lambda c: spirit_house(c, 'spirit_house_ochre', 'ochre', 53.9),
    'spirit_house_stone': lambda c: spirit_house(c, 'spirit_house_stone', 'sandstone', 58.2),
    'hall_throne': lambda c: hall_throne(c, 'hall_throne', 63.4),
    'image_cloth': lambda c: image_cloth(c, 'image_cloth'),
    'stupa_cloth': lambda c: stupa_cloth(c, 'stupa_cloth'),
}


if __name__ == '__main__':
    # Nothing named builds it all; `stupas`, `statues`, or single statue names rebuild those.
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    only = bool(args)
    path = ROOT / 'art-source/kits/stupa_kit.blend'  # not under blender/: it is no export of its own
    if only and path.exists():
        bpy.ops.wm.open_mainfile(filepath=str(path))
        coll = bpy.data.collections['stupa_kit']
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        coll = bpy.data.collections.new('stupa_kit')
        bpy.context.scene.collection.children.link(coll)
    if not args or 'stupas' in args:
        build_stupas(coll)
    for name, build in STATUES.items():
        if not args or 'statues' in args or name in args:
            build(coll)
    if 'M_ep2_funeral_photo' not in bpy.data.materials:
        img = P.photo_sheet()
        for m in P.photo_materials(img):
            m.use_fake_user = True
    for block in bpy.data.images:
        if block.source == 'FILE':
            block.pack()
    for me in bpy.data.meshes:
        me.use_fake_user = True
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print('KIT', sorted(o.name for o in coll.objects), flush=True)
