"""The white enclosure round Sok's coffin in the hall (Episode 1, November 20, 2026):
old unbleached cotton hung on a light frame of squared posts and rails, sagging in a
ceiling over the coffin, its hems pooling on the mat; open at the front to the
portrait altar; and every picture on the hall's walls hung over with the same cloth,
turned away from the dead. Blender metres, X east, Y north, Z up.
"""
import math

import bpy
import numpy as np
from mathutils import Vector, noise

import rural_kit as RK
from kit import library_material, mesh_object, world_uvs
from shrine_craft import Batch

X0, X1, Y0, Y1, TOP, FLOOR = -1.95, 1.45, 14.62, 17.3, 4.78, 2.512


def cloth_material():
    name = "M_ep1_shroud_linen"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = library_material("rough_linen", name, tint=(.8, .73, .6), tile=.9)
    mat.use_backface_culling = False
    return mat


def _sheet(coll, mat, nx=48, ny=40, sag=.22):
    verts, faces = [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = X0 + (X1 - X0) * u, Y0 + (Y1 - Y0) * v
            z = TOP - sag * math.sin(math.pi * u) * math.sin(math.pi * v)
            z += .03 * noise.noise(Vector((x * 2.3, y * 2.3, .5))) + .012 * noise.noise(Vector((x * 9, y * 9, 2.0)))
            z -= .05 * max(0.0, noise.noise(Vector((x * 1.1, y * 1.1, 7.0))))
            # Its edges lie on the frame's rails.
            if i in (0, nx) or j in (0, ny):
                z = TOP + .035
            verts.append((x, y, z))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh_object("hall_shroud_top", coll, verts, faces, mat, smooth=True)


def drape(coll, mat, name, a0, a1, z0, z1, plane, axis="x", folds=9, depth=.06, nx=96, nz=40, seed=0):
    """A hanging cloth, folds of uneven width and depth, gathered at the rail, its
    hem ragged and pooling on the floor."""
    r = np.random.default_rng(seed)
    phases = np.cumsum(r.uniform(.6, 1.4, folds * 2 + 2))
    phases = phases / phases[-1] * folds * 2 * math.pi
    amps = r.uniform(.45, 1.25, len(phases))
    hem = [r.uniform(-.04, .05) for _ in range(nx + 1)]
    verts, faces = [], []
    for j in range(nz + 1):
        t = j / nz
        for i in range(nx + 1):
            u = i / nx
            ph = np.interp(u, np.linspace(0, 1, len(phases)), phases)
            amp = np.interp(u, np.linspace(0, 1, len(amps)), amps)
            off = math.sin(ph) * depth * amp * (.35 + .65 * t)
            off += .012 * noise.noise(Vector((u * 9 + seed, t * 4, .3)))
            along = a0 + (a1 - a0) * u
            z = z1 - (z1 - z0 + hem[i]) * t
            if z < FLOOR + .01:
                off -= (FLOOR + .01 - z) * .9
                z = FLOOR + .004
            verts.append((along, plane + off, z) if axis == "x" else (plane + off, along, z))
    for j in range(nz):
        for i in range(nx):
            q = j * (nx + 1) + i
            faces.append((q, q + 1, q + nx + 2, q + nx + 1))
    obj = mesh_object(name, coll, verts, faces, mat, smooth=True)
    world_uvs(obj)
    return obj


def build(coll, rng):
    mat = cloth_material()
    out = [_sheet(coll, mat)]
    world_uvs(out[0])
    out += [
        drape(coll, mat, "hall_shroud_n", X0, X1, FLOOR - .12, TOP + .03, Y1 + .03, folds=13, seed=1),
        drape(coll, mat, "hall_shroud_w", Y0, Y1, FLOOR - .12, TOP + .03, X0 - .03, axis="y", folds=10, seed=2),
        drape(coll, mat, "hall_shroud_e", Y1, Y0, FLOOR - .12, TOP + .03, X1 + .03, axis="y", folds=10, seed=3),
        drape(coll, mat, "hall_shroud_fw", X0, X0 + .42, FLOOR - .05, TOP + .03, Y0 - .03, folds=5, depth=.07, nx=40, seed=4),
        drape(coll, mat, "hall_shroud_fe", X1 - .42, X1, FLOOR - .05, TOP + .03, Y0 - .03, folds=5, depth=.07, nx=40, seed=5),
    ]
    # The frame: four squared posts standing on the mat and the rails along the top.
    fm = RK.materials()
    fb = Batch("hall_shroud_frame")
    for x, y in ((X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1)):
        RK.timber(fb, fm["hewn"], Vector((x, y, FLOOR - .01)), Vector((x, y, TOP + .05)), .055, .055, rng)
    for a, c in (((X0, Y0), (X1, Y0)), ((X0, Y1), (X1, Y1)), ((X0, Y0), (X0, Y1)), ((X1, Y0), (X1, Y1))):
        RK.timber(fb, fm["hewn"], Vector((a[0], a[1], TOP + .01)), Vector((c[0], c[1], TOP + .01)), .045, .04, rng)
    out += list(fb.build(coll).values())
    # The family's pictures, each hung over with cloth.
    for fr in [o for o in bpy.data.objects if o.name.startswith("family_frame_")]:
        pts = [fr.matrix_world @ Vector(c) for c in fr.bound_box]
        mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        if mx.x - mn.x < mx.y - mn.y:
            x = mn.x - .006 if mn.x > 0 else mx.x + .006
            out.append(drape(coll, mat, f"{fr.name}_cover", mn.y - .05, mx.y + .05, mn.z - .12, mx.z + .04, x, axis="y",
                             folds=3, depth=.012, nx=12, nz=12, seed=9))
        else:
            out.append(drape(coll, mat, f"{fr.name}_cover", mn.x - .05, mx.x + .05, mn.z - .12, mx.z + .04, mn.y - .006,
                             folds=3, depth=.012, nx=12, nz=12, seed=9))
    return out
