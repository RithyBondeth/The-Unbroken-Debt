"""Shared forest surfaces and geometry, authored in Blender metres.

Original procedural textures; no reference photographs are shipped as assets.
Foliage is built in local patches so the renderer can cull the undergrowth.
"""
import math
import os

import bpy
import numpy as np

from kit import TEXTURES, image_material, mesh_object, tube
from khmer import join


def save_map(name, pixels):
    h, w, _ = pixels.shape
    path = os.path.join(TEXTURES, name + '.png')
    image = bpy.data.images.get(name)
    if image is None:
        image = bpy.data.images.new(name, width=w, height=h, alpha=True)
    image.scale(w, h)
    image.colorspace_settings.name = 'Non-Color' if name.endswith('_N') else 'sRGB'
    image.pixels.foreach_set(np.asarray(pixels, dtype=np.float32).ravel())
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    return path


def forest_materials():
    """Veined leaf atlas, ribbed grass and moss with explicit normal maps."""
    result = {}
    if bpy.data.materials.get('M_forest_leaf'):
        return {key: bpy.data.materials['M_forest_' + key]
                for key in ('leaf', 'grass', 'moss', 'litter')}
    rng = np.random.default_rng(6241910)
    size = 1024
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    u, v = (xx % 512) / 511, (yy % 512) / 511
    cell = (xx // 512 + 2 * (yy // 512)).astype(int)
    # Each atlas cell is a single leaf: pointed drip tip, asymmetric margins,
    # midrib, branching lateral veins, mottling and small insect bites.
    width = np.maximum(0, np.sin(np.pi * np.clip((v - .035) / .93, 0, 1))) ** .82 * .45
    mid = .5 + .035 * np.sin(v * 5 + cell)
    side = (u - mid) / np.maximum(width, .001)
    edge = np.abs(side)
    alpha = (edge < 1) & (v > .035) & (v < .965)
    rib = np.exp(-((u - mid) / .008) ** 2)
    veins = np.exp(-(np.sin((v - .15 * edge) * np.pi * 12) / .12) ** 2)
    grain = rng.normal(0, .018, (size, size))
    mottles = np.sin(xx * .037 + np.sin(yy * .023) * 2) * np.sin(yy * .052) * .07
    light = .72 + .22 * (1 - edge) + .07 * rib + .05 * veins + grain + mottles
    # The cursed forest's leaves: dead browns, ash greys and rust; nothing green is left.
    palette = np.array([[.29, .23, .16], [.25, .22, .19], [.2, .19, .17], [.37, .24, .13]])
    leaf = np.ones((size, size, 4))
    leaf[:, :, :3] = palette[cell] * np.clip(light, .4, 1.2)[:, :, None]
    for k in range(24):
        cx, cy = rng.uniform(0, size, 2)
        bite = ((xx - cx) ** 2 + (yy - cy) ** 2 < rng.uniform(2, 6) ** 2) & (edge > .75)
        alpha[bite] = False
    leaf[:, :, 3] = alpha
    normal = np.ones_like(leaf)
    normal[:, :, 0] = .5 + .16 * np.clip(side, -1, 1)
    normal[:, :, 1] = .5 + .05 * np.sin((v - .15 * edge) * np.pi * 24)
    normal[:, :, 2] = .97
    normal[:, :, 3] = 1
    leaf_path = save_map('T_ep1_forest_leaf_BC', leaf)
    leaf_normal = save_map('T_ep1_forest_leaf_N', normal)
    grass = np.ones((512, 128, 4))
    gy, gx = np.mgrid[0:512, 0:128].astype(float)
    t = gy / 511
    bands = .82 + .09 * np.sin(gx * .37) + rng.normal(0, .022, gx.shape)
    base, tip = np.array([.16, .14, .1]), np.array([.44, .38, .27])
    grass[:, :, :3] = (base[None, None, :] * (1 - t[:, :, None]) + tip * t[:, :, None]) * bands[:, :, None]
    # A dried tip and a narrow central rib catch the warm player lamp.
    grass[t > .91, :3] *= np.array([1.12, .96, .78])
    grass_path = save_map('T_ep1_forest_grass_BC', grass)
    gn = np.ones_like(grass)
    gn[:, :, 0] = .5 + .09 * np.cos(gx * .37)
    gn[:, :, 1] = .5
    gn[:, :, 2] = .99
    grass_normal = save_map('T_ep1_forest_grass_N', gn)
    moss = np.ones((256, 256, 4))
    my, mx = np.mgrid[0:256, 0:256].astype(float)
    noise = rng.random((256, 256))
    threads = .65 + .2 * np.sin(mx * .4 + np.sin(my * .12) * 2) + .15 * noise
    # Pale grey-green lichen rather than living moss.
    moss[:, :, :3] = threads[:, :, None] * np.array([.36, .37, .32])
    moss_path = save_map('T_ep1_forest_moss_BC', moss)
    for key, path, rough, normal_path in (
        ('leaf', leaf_path, .57, leaf_normal),
        ('grass', grass_path, .72, grass_normal),
        ('moss', moss_path, .92, None),
        ('litter', leaf_path, .87, leaf_normal),
    ):
        material = image_material('M_forest_' + key, path, rough=rough,
                                  cutout=key in ('leaf', 'litter'),
                                  tint=(.58, .39, .22) if key == 'litter' else None)
        material.use_backface_culling = False
        if normal_path:
            nodes, links = material.node_tree.nodes, material.node_tree.links
            tex = nodes.new('ShaderNodeTexImage')
            tex.image = bpy.data.images.load(normal_path, check_existing=True)
            tex.image.colorspace_settings.name = 'Non-Color'
            n = nodes.new('ShaderNodeNormalMap')
            n.inputs['Strength'].default_value = .55
            links.new(tex.outputs['Color'], n.inputs['Color'])
            links.new(n.outputs['Normal'], nodes['Principled BSDF'].inputs['Normal'])
        result[key] = material
    return result


class Leaves:
    """Folded, drooping leaf surfaces with one stable UV rectangle per leaf."""
    def __init__(self):
        self.verts, self.faces, self.uvs = [], [], []

    def add(self, base, yaw, length, width, rise, cell=0, curl=.12):
        forward = np.array([math.cos(yaw), math.sin(yaw), 0.])
        side = np.array([-math.sin(yaw), math.cos(yaw), 0.])
        base = np.array(base)
        b = len(self.verts)
        # A centre crease makes the leaf reflect differently on each half.
        for t in (0., .5, 1.):
            centre = base + forward * length * t
            centre[2] += rise * t - curl * length * t * t
            for s in (-1, 0, 1):
                p = centre + side * s * width / 2
                p[2] += (1 - abs(s)) * width * .13 * math.sin(math.pi * t)
                self.verts.append(tuple(p))
        for row in range(2):
            for col in range(2):
                i = b + row * 3 + col
                self.faces.append((i, i + 1, i + 4, i + 3))
                u0, v0 = (cell % 2) / 2, (cell // 2) / 2
                self.uvs += [(u0 + col / 4, v0 + row / 4),
                             (u0 + (col + 1) / 4, v0 + row / 4),
                             (u0 + (col + 1) / 4, v0 + (row + 1) / 4),
                             (u0 + col / 4, v0 + (row + 1) / 4)]

    def build(self, name, coll, material):
        return mesh_object(name, coll, self.verts, self.faces, material, uvs=self.uvs, smooth=True)

    def stem(self, points, width):
        """A thin continuous rachis joining a fern's paired leaflets."""
        start = len(self.verts)
        for i, point in enumerate(points):
            a, b = points[max(0, i-1)], points[min(len(points)-1, i+1)]
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy) or 1.
            w = width * (1 - .8 * i / (len(points)-1))
            self.verts += [(point[0]-dy/length*w, point[1]+dx/length*w, point[2]),
                           (point[0]+dy/length*w, point[1]-dx/length*w, point[2])]
        for i in range(len(points)-1):
            j = start + i*2
            self.faces.append((j, j+1, j+3, j+2))
            self.uvs += [(.245, .25), (.255, .25), (.255, .26), (.245, .26)]


def canopy_sprays(name, coll, items, material, rng, per=18):
    leaves = Leaves()
    for centre, size, yaw, _pitch, cell in items:
        for j in range(per):
            a = yaw + rng.uniform(0, math.tau)
            reach = rng.uniform(.05, .38) * size
            base = (centre[0] + math.cos(a) * reach, centre[1] + math.sin(a) * reach,
                    centre[2] + rng.uniform(-.22, .22) * size)
            length = size * rng.uniform(.24, .42)
            leaves.add(base, a, length, length * rng.uniform(.34, .52),
                       rng.uniform(-.18, .25) * size, cell)
    return leaves.build(name, coll, material)


def grass_geometry(name, coll, spots, rng, size=(.5, .9)):
    """Bent tapering blades, in 8m patches; no rectangular alpha overdraw."""
    mat = forest_materials()['grass']
    patches = {}
    for x, y, z in spots:
        key = (math.floor(x / 8), math.floor(y / 8))
        patches.setdefault(key, []).append((x, y, z))
    objects = []
    for cell, points in sorted(patches.items()):
        verts, faces, uvs = [], [], []
        for x, y, z in points:
            h = rng.uniform(*size)
            wind = rng.uniform(0, math.tau)
            for _ in range(int(rng.integers(8, 14))):
                a = rng.uniform(0, math.tau)
                height = h * rng.uniform(.45, 1.12)
                width = rng.uniform(.012, .032) * min(1.4, h / .55)
                reach = height * rng.uniform(.24, .7)
                bx, by = x + rng.normal(0, .1), y + rng.normal(0, .1)
                bend = a * .65 + wind * .35
                side = np.array([-math.sin(a), math.cos(a), 0.])
                b = len(verts)
                for t in (0., .42, .76, 1.):
                    centre = np.array([bx + math.cos(bend) * reach * t * t,
                                       by + math.sin(bend) * reach * t * t,
                                       z - .025 + height * (t - .18 * t ** 3)])
                    w = width * (1 - t) ** .7 / 2
                    for sign in (-1, 1):
                        verts.append(tuple(centre + side * sign * w))
                for row in range(3):
                    i = b + row * 2
                    faces.append((i, i + 1, i + 3, i + 2))
                    uvs += [(0, row / 3), (1, row / 3), (1, (row + 1) / 3), (0, (row + 1) / 3)]
        objects.append(mesh_object(f'{name}_{cell[0]}_{cell[1]}', coll, verts, faces, mat, uvs=uvs, smooth=True))
    return objects


def tree_surface_details(coll, m, x, y, h, radius, k, rng):
    """Solid flared buttresses, low moss ridges and climbing lianas."""
    parts = []
    for j in range(5):
        a = j * math.tau / 5 + rng.uniform(-.18, .18)
        reach = radius + rng.uniform(1.2, 2.6)
        c, s = math.cos(a), math.sin(a)
        height = rng.uniform(1.8, 3.2)
        verts, faces, uvs = [], [], []
        # Convex ribs taper into the soil. Outward winding is essential here:
        # an inverted fin looked like a black triangular cutout by lamplight.
        for station in range(7):
            t = station / 6
            r = radius * .65 + (reach - radius * .65) * t
            w = radius * (.46 * (1-t) ** 1.4 + .018)
            z = .025 + height * (1-t) ** 2.1
            for side, lift in ((-1, 0), (-.65, .65), (0, 1), (.65, .65), (1, 0)):
                verts.append((x + c*r - s*w*side, y + s*r + c*w*side,
                              -.035 + z*lift))
        for station in range(6):
            for side in range(4):
                a = station*5 + side
                faces.append((a, a+5, a+6, a+1))
                uvs += [(side/4, station/6*reach), (side/4, (station+1)/6*reach),
                         ((side+1)/4, (station+1)/6*reach), ((side+1)/4, station/6*reach)]
        parts.append(mesh_object(f'tree_{k}_fin_{j}', coll, verts, faces,
                                 m['bark'], uvs=uvs, smooth=True))
        pts = [(x + c * (radius + reach * t * .72), y + s * (radius + reach * t * .72),
                .13 * (1 - t) - .015) for t in (0., .3, .6, 1.)]
        parts.append(tube(f'tree_{k}_moss_{j}', coll, pts, .075, m['moss'], sides=5, radius_end=.007))
        # A sleeve of moss runs up the bole between the fins, thickest at the foot.
        sleeve = [(x + c * radius * 1.04, y + s * radius * 1.04, z) for z in (.2, 1.4, 2.8, 4.2)]
        parts.append(tube(f'tree_{k}_moss_sleeve_{j}', coll, sleeve, .06, m['moss'], sides=5, radius_end=.012))
    for j in range(int(rng.integers(4, 8))):
        a = rng.uniform(0, math.tau)
        height = h * rng.uniform(.45, .85)
        pts = []
        for i in range(13):
            t = i / 12
            twist = a + t * rng.uniform(2.8, 3.2)
            r = radius * (1 - .35 * t) + .025
            pts.append((x + math.cos(twist) * r, y + math.sin(twist) * r, height * t))
        parts.append(tube(f'tree_{k}_liana_{j}', coll, pts, rng.uniform(.022, .06),
                          m['bark'], sides=5, radius_end=.009))
    # Roots hanging clear of the player make threatening vertical silhouettes.
    for j in range(int(rng.integers(6, 11))):
        a = rng.uniform(0, math.tau)
        bx, by = x + math.cos(a) * rng.uniform(1.2, 3.2), y + math.sin(a) * rng.uniform(1.2, 3.2)
        z = h * rng.uniform(.4, .65)
        pts = [(x, y, z + .3), (bx, by, z), (bx + .18, by - .12, z - 1.0),
               (bx + .23, by - .2, max(2.4, z - rng.uniform(3.0, 7.5)))]
        parts.append(tube(f'tree_{k}_hanging_vine_{j}', coll, pts, .022, m['bark'], sides=4, radius_end=.004))
    return parts


def understory(coll, spots, rng, prefix='forest'):
    """Fern rosettes and broad juvenile leaves mixed with curled dead litter."""
    mats = forest_materials()
    patches = {}
    for x, y in spots:
        patches.setdefault((math.floor(x / 8), math.floor(y / 8)), []).append((x, y))
    for cell, points in sorted(patches.items()):
        plants, litter = Leaves(), Leaves()
        for x, y in points:
            scale = rng.uniform(.65, 1.3)
            if rng.random() < .65:
                # Paired pinnae on an arching frond; fine silhouettes at eye level.
                for j in range(6):
                    a = j * math.tau / 6 + rng.uniform(-.2, .2)
                    length = scale * rng.uniform(.65, 1.1)
                    plants.stem([(x + math.cos(a) * length * t,
                                  y + math.sin(a) * length * t,
                                  .08 + scale * .6 * math.sin(t * 2.1))
                                 for t in (i/9 for i in range(10))], .008 * scale)
                    for n in range(1, 9):
                        t = n / 9
                        base = (x + math.cos(a) * length * t,
                                y + math.sin(a) * length * t,
                                .08 + scale * (.6 * math.sin(t * 2.1)))
                        for sign in (-1, 1):
                            l = length * .3 * math.sin(t * math.pi) + .035
                            plants.add(base, a + sign * 1.04, l, l * .27, -.04, n % 3)
            else:
                for j in range(8):
                    a = j * math.tau / 8 + rng.uniform(-.2, .2)
                    length = scale * rng.uniform(.55, .95)
                    plants.add((x, y, .07), a, length, length * .4, scale * rng.uniform(.35, .7), j % 3, .4)
            for _ in range(10):
                bx, by = x + rng.normal(0, .7), y + rng.normal(0, .7)
                litter.add((bx, by, .025), rng.uniform(0, math.tau), rng.uniform(.1, .26),
                           rng.uniform(.04, .1), .015, 3, -.1)
        plants.build(f'{prefix}_understory_{cell[0]}_{cell[1]}', coll, mats['leaf'])
        litter.build(f'{prefix}_litter_{cell[0]}_{cell[1]}', coll, mats['litter'])
