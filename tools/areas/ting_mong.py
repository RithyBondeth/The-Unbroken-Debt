"""Weathered straw guardians, built in metres and exported as one watcher each.

Shared by the full village build and the focused rebuild command. Cloth folds,
sack depressions and frayed silhouettes are geometry, so the player's moving
lamp reveals them without a special runtime shader.
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from kit import collider, image_material, mesh_object, texture, tube, image
from khmer import join, pole


def guardian_materials():
    """Dedicated woven cloth; never recolour other village props."""
    materials = {}
    for key, suffix, tile in (("face", "face", 0), ("shirt", "shirt", .45),
                              ("wrap", "wrap", .55), ("binding", "shirt", .12)):
        mat = image_material(f"M_tingmong_{key}", texture(f"T_ep1_tingmong_{suffix}_BC"), rough=.96, tile=tile)
        # Tangent-space weave follows the same UVs as the painted cloth.
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = image(texture('T_ep1_tingmong_weave_N'), True)
        normal = nodes.new('ShaderNodeNormalMap')
        normal.inputs['Strength'].default_value = .42 if key == 'face' else .65
        links.new(tex.outputs['Color'], normal.inputs['Color'])
        links.new(normal.outputs['Normal'], nodes['Principled BSDF'].inputs['Normal'])
        mat.use_backface_culling = False  # Open cuffs and torn hems have an inside.
        materials[key] = mat
    return materials


def ting_mong(coll, m, x, y, facing, k, rng, arms_up=False):
    """A slumped, rain-worn guardian with a charcoal-marked sack face.

    Keep the named watcher, foot pivot, front extra and collider used by
    Apparitions. Each figure gets a repeatable lean and different stuffing.
    """
    rng = np.random.default_rng(1910 + k)
    cloth = guardian_materials() if 'guardian' not in m else m['guardian']
    m['guardian'] = cloth
    ca, sa = math.cos(facing), math.sin(facing)
    lean = -.035 if k % 2 == 0 else .028

    def at(lx, ly, z):
        lx += lean * z
        return (x + lx * ca - ly * sa, y + lx * sa + ly * ca, z)

    parts = [pole(f'tingmong_{k}_stake', coll, at(0, .07, -.3), at(.01, .09, 1.64),
                  .024, m['bamboo_dead'], sides=7, metres=.45)]

    def shell(name, profile, mat, depth=.67, folds=11, phase=0, head=False):
        """Uneven elliptical cloth rings with physical folds and continuous UVs."""
        count = 64 if head else 48
        verts, faces, uvs = [], [], []
        for j, (radius, z) in enumerate(profile):
            v = j / (len(profile) - 1)
            for i in range(count + 1):
                u = i / count
                a = (u - .5) * math.tau  # Front at U=.5, facing local -Y.
                wave = math.sin(a * folds + phase + v * 1.8)
                fine = math.sin(a * (folds + 6) - v * 5 + phase)
                r = radius + (.0025 if head else .008) * (wave + fine * .35)
                px, py = math.sin(a) * r, -math.cos(a) * r * depth
                height = z
                if head:
                    # A sagging sack, pulled over its stuffing, with pressed-in eye marks.
                    front = max(0, math.cos(a)) ** 8
                    eye = sum(math.exp(-((px - ex) / .025) ** 2 - ((v - ev) / .065) ** 2)
                              for ex, ev in ((-.043, .61), (.043, .64)))
                    py += .021 * eye * front
                    py -= .009 * math.exp(-(px / .023) ** 2 - ((v - .48) / .18) ** 2) * front
                    px += .032 * (v - .15)
                    py -= .018 * v * v
                    height += .025 * math.sin(a) * v  # A subtle, fixed head tilt.
                else:
                    # Ragged scalloped edges, tension wrinkles and collapsed shoulders.
                    edge = (1 - v) ** 9
                    height += edge * (.015 * math.sin(a * 13 + phase) + .009 * math.sin(a * 21))
                    px += .012 * math.sin(v * 4 + phase)
                verts.append(at(px, py, height))
        for j in range(len(profile) - 1):
            for i in range(count):
                b = j * (count + 1) + i
                faces.append((b, b + 1, b + count + 2, b + count + 1))
                for jj, ii in ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)):
                    if head:
                        uvs.append((ii / count, jj / (len(profile) - 1)))
                    else:
                        uvs.append((ii / count * .9 / mat['tile'], profile[jj][1] / mat['tile']))
        parts.append(mesh_object(name, coll, verts, faces, mat, uvs=uvs, smooth=True))

    # Narrow, uneven hips and collapsed torso instead of round primitive forms.
    shell(f'tingmong_{k}_sarong', [(.185 + .012 * math.sin(j * .7), .28 + j * .026)
                                  for j in range(27)], cloth['wrap'], depth=.69, phase=k)
    profile = [(.19, .91), (.185, .96), (.17, 1.02), (.155, 1.09), (.15, 1.16),
               (.17, 1.23), (.20, 1.30), (.22, 1.35), (.205, 1.39), (.15, 1.43), (.054, 1.47)]
    shell(f'tingmong_{k}_shirt', profile, cloth['shirt'], depth=.65, phase=k + .8)

    # Hand stitched front opening, loose hem threads, and binding at the waist.
    parts.append(tube(f'tingmong_{k}_placket', coll,
                      [at(.025, -.105, 1.03), at(.015, -.115, 1.20), at(.03, -.125, 1.36), at(.01, -.05, 1.46)],
                      .003, cloth['binding'], sides=4))
    for j in range(17):
        a = j / 17 * math.tau
        z = .28 + .012 * math.sin(a * 13 + k)
        p = at(math.sin(a) * .19, -math.cos(a) * .13, z)
        parts.append(tube(f'tingmong_{k}_hem_thread_{j}', coll,
                          [p, (p[0] + .004, p[1] + .002, p[2] - rng.uniform(.012, .055))],
                          .0008, cloth['binding'], sides=3))
    belt = [at(.18 * math.sin(a), -.125 * math.cos(a), .965 + .01 * math.sin(a * 2))
            for a in (j / 40 * math.tau for j in range(41))]
    parts.append(tube(f'tingmong_{k}_waist_cord', coll, belt, .005, m['straw'], sides=5))

    for s in (-1, 1):
        shoulder = (s * .19, .015, 1.36 - (s + 1) * .018)
        elbow = (s * (.34 if arms_up else .265), -.015, 1.39 if arms_up else 1.12)
        wrist = (s * (.53 if arms_up else .30), -.11, 1.48 if arms_up else .83 + s * .025)
        # Many tapered rings, oval cross sections and crushed cuff folds.
        points = []
        for j in range(13):
            t = j / 12
            a, b, t2 = (shoulder, elbow, t * 2) if t < .5 else (elbow, wrist, (t - .5) * 2)
            points.append(at(*(a[q] + (b[q] - a[q]) * t2 for q in range(3))))
        sleeve = tube(f'tingmong_{k}_sleeve_{s}', coll, points, .066, cloth['shirt'],
                      sides=16, radius_end=.039, metres_per_v=.45)
        for j, vertex in enumerate(sleeve.data.vertices):
            ring, around = divmod(j, 17)
            centre = Vector(points[ring])
            delta = vertex.co - centre
            vertex.co = centre + delta * (1 + .12 * math.sin(around / 16 * math.tau * 5 + ring * 1.5))
        parts.append(sleeve)
        hand = at(*wrist)
        # Thin, broken fibres, grouped into an irregular bundle rather than seven spokes.
        for j in range(19):
            ox, oy = rng.uniform(-.023, .023), rng.uniform(-.018, .018)
            p = (hand[0] + ox, hand[1] + oy, hand[2] + .015)
            length = rng.uniform(.075, .19)
            end = (p[0] + rng.uniform(-.026, .026), p[1] - .018, p[2] - length)
            parts.append(tube(f'tingmong_{k}_fibre_{s}_{j}', coll,
                              [p, (p[0] + ox * .3, p[1] - .008, p[2] - length * .65), end],
                              rng.uniform(.001, .0022), m['straw'], sides=3, radius_end=.0004))
        if not arms_up and s == 1:
            parts.append(pole(f'tingmong_{k}_stick', coll, at(.30, -.10, .76), at(.35, -.70, 1.12),
                              .012, m['post_rough'], sides=6, metres=.6))

    # Long neck binding and a pinched, slightly bowed sack. V maps the full texture once.
    head_profile = []
    control = [(.032, 1.47), (.06, 1.49), (.085, 1.53), (.108, 1.59),
               (.112, 1.68), (.102, 1.75), (.075, 1.80), (.008, 1.82)]
    for j in range(41):
        t = j / 40 * (len(control) - 1)
        idx = min(int(t), len(control) - 2)
        f = t - idx
        head_profile.append(tuple(control[idx][q] * (1 - f) + control[idx + 1][q] * f for q in range(2)))
    shell(f'tingmong_{k}_sack', head_profile, cloth['face'], depth=.79, head=True)
    for j in range(3):
        cord = [at(.051 * math.sin(a) + .004, -.044 * math.cos(a), 1.485 + j * .006)
                for a in (i / 32 * math.tau for i in range(33))]
        parts.append(tube(f'tingmong_{k}_neck_binding_{j}', coll, cord, .0028, cloth['binding'], sides=5))
    for j in range(9):
        p = at(rng.uniform(-.035, .035), rng.uniform(-.02, .025), 1.48)
        parts.append(tube(f'tingmong_{k}_neck_fibre_{j}', coll,
                          [p, (p[0] + rng.uniform(-.015, .015), p[1], p[2] + rng.uniform(.025, .065))],
                          .0013, m['straw'], sides=3, radius_end=.0004))
    # A collapsed cloth strip tied behind the sack; no thick hat-like forehead band.
    parts.append(tube(f'tingmong_{k}_loose_tie', coll,
                      [at(.02, .07, 1.65), at(.08, .10, 1.52), at(.06, .12, 1.30)],
                      .015, cloth['wrap'], sides=8, radius_end=.008, metres_per_v=.55))

    figure = join(parts, f'tingmong_{k}')
    # join() keeps the first pole's transform; bake it before setting the foot pivot.
    world = figure.matrix_world.copy()
    figure.data.transform(Matrix.Translation(Vector((-x, -y, 0))) @ world)
    figure.matrix_world = Matrix.Translation(Vector((x, y, 0)))
    figure['front'] = facing - math.pi / 2
    collider(f'tingmong_{k}', coll, x - .3, x + .3, y - .3, y + .3, 0, 1.85)
    return figure
