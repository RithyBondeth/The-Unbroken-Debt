"""Photogrammetry scans of real temple images (art-source/library/scans), brought into
Episode 2: joined, stood upright, reduced to a game budget, pre-mirrored against the
world root's X flip, scaled to life and stood on their base at a named spot.

Sources (Sketchfab): seated monk (Obi.Moz, CC-BY 4.0), seated Buddha (Francesco
Coldesina, CC-BY 4.0), reclining Buddha (sofiarudi, CC-BY 4.0), standing alms monk
(manusainz, CC-BY 4.0), Prajnaparamita (Minneapolis Institute of Art, CC0), naga
finial (Cleveland Museum of Art, CC0). The ghosts are their own rigged assets:
tools/ep2/build-ghosts.py.
"""
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
SCANS = ROOT / 'art-source/library/scans'

# Per scan: the rotation (degrees about X, Y, Z) that stands it upright facing -Y,
# the decimation ratio, and baking: 'self' merges many materials into one texture,
# 'high' re-bakes the full scan's colour onto the reduced mesh (for scans whose
# texture atlas is too fragmented to survive decimation).
SPEC = {
    # The scan's white cloth and the table under it are cut away: everything colourless
    # below the robe (the robe and skin are never that pale; see _strip_pale).
    'monk_seated': dict(rot=(-90, 0, 120), ratio=.1, bake=None, motion='monk', strip=dict(below=-2.5, saturation=.3, floor=-4.7, crumbs=400)),
    'buddha_seated': dict(rot=(0, 0, 180), ratio=1.0, bake=None),
    'buddha_reclining': dict(rot=(0, 0, 0), ratio=.6, bake='self'),
    'monk_alms_standing': dict(rot=(0, 0, 0), ratio=.18, bake=None),
    'prajnaparamita': dict(rot=(0, 0, 0), ratio=.06, bake=None),
    'naga_finial': dict(rot=(0, 0, 0), ratio=1.0, bake=None),
}


def _turned(co, pivot, axis, degrees, weight):
    """`co` turned about `pivot` and `axis` by `degrees` scaled by `weight` (0..1)."""
    if weight <= 0:
        return co.copy()
    return pivot + Quaternion(Vector(axis), math.radians(degrees) * weight) @ (co - pivot)


def _smooth(lo, hi, x):
    t = min(1.0, max(0.0, (x - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def _monk_motion(co):
    """A seated monk (base at 0, about .82 m tall, facing -Y): head turns either way and
    nods from the neck, the chest rises with breath, the body bows from the hips."""
    top = max(c.z for c in co)
    head = [c for c in co if c.z > top - .26]
    hx, hy = sum(c.x for c in head) / len(head), sum(c.y for c in head) / len(head)
    neck = Vector((hx, hy + .026, top - .32))

    def w_head(c):
        reach = math.hypot(c.x - hx, c.y - hy)
        # The head and neck only: the shoulders and robe stay where they are.
        return _smooth(top - .375, top - .26, c.z) * (1 - _smooth(.14, .205, reach))
    band = [c for c in co if top - .8 < c.z < top - .39]
    tx, ty = sum(c.x for c in band) / len(band), sum(c.y for c in band) / len(band)

    def breathe(c):
        b = math.sin(math.pi * min(1, max(0, (c.z - (top - .8)) / .41)))
        r = Vector((c.x - tx, c.y - ty, 0))
        lift = .005 * _smooth(top - .44, top - .36, c.z)
        return c + r * .018 * b * (1 - _smooth(.32, .41, r.length)) + Vector((0, 0, lift))
    hip = Vector((tx, ty, -.04))
    return {
        'look_pos': [_turned(c, neck, (0, 0, 1), 34, w_head(c)) for c in co],
        'look_neg': [_turned(c, neck, (0, 0, 1), -34, w_head(c)) for c in co],
        'nod': [_turned(c, neck, (1, 0, 0), 16, w_head(c)) for c in co],
        'breathe': [breathe(c) for c in co],
        'bow': [_turned(c, hip, (1, 0, 0), 11, _smooth(-.04, .24, c.z)) for c in co],
    }


MOTIONS = {'monk': _monk_motion}


def _strip_pale(obj, below, saturation, floor, crumbs):
    """Deletes what a scan picked up around its subject: every face under height `below`
    whose texture is paler than `saturation` (white cloth, grey table), everything at all
    under `floor`, then any loose scraps of fewer than `crumbs` faces left behind. Runs
    on the full scan, before it is reduced, in the scan's own upright units."""
    import numpy as np
    me = obj.data
    colours = []
    for mat in me.materials:
        img = next(n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.colorspace_settings.name == 'sRGB')
        w, h = img.size
        px = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(px)
        colours.append((px.reshape(h, w, 4), w, h))
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    doomed = []
    for f in bm.faces:
        z = f.calc_center_median().z
        if z >= below:
            continue
        if z < floor:
            doomed.append(f)
            continue
        px, w, h = colours[f.material_index]
        u = sum(l[uv].uv.x for l in f.loops) / len(f.loops)
        v = sum(l[uv].uv.y for l in f.loops) / len(f.loops)
        c = px[min(h - 1, max(0, int(v * h))), min(w - 1, max(0, int(u * w))), :3]
        top = float(c.max())
        if (top - float(c.min())) / max(top, 1e-4) < saturation:
            doomed.append(f)
    removed = len(doomed)
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    # Loose scraps: walked across shared positions, because the scan's vertices split at
    # every texture seam.
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    at = {}
    parent = list(range(len(bm.verts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for v in bm.verts:
        key = (round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4))
        if key in at:
            parent[find(v.index)] = find(at[key])
        else:
            at[key] = v.index
    for e in bm.edges:
        parent[find(e.verts[0].index)] = find(e.verts[1].index)
    size = {}
    for f in bm.faces:
        r = find(f.verts[0].index)
        size[r] = size.get(r, 0) + 1
    scraps = [f for f in bm.faces if size[find(f.verts[0].index)] < crumbs]
    bmesh.ops.delete(bm, geom=scraps, context='FACES')
    bm.to_mesh(me)
    bm.free()
    print('Stripped', removed, 'pale faces and', len(scraps), 'scrap faces,', len(me.polygons), 'left', flush=True)


def _bake(obj, name, high=None, size=2048):
    """Bakes colour into one texture on fresh UVs: from every material on `obj`
    itself, or from the full-detail `high` scan onto the reduced `obj`."""
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    me = obj.data
    src_uv_name = me.uv_layers.active.name  # adding a layer invalidates references to the others
    baked_uv = me.uv_layers.new(name='baked')
    me.uv_layers.active = baked_uv
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=.003)
    bpy.ops.object.mode_set(mode='OBJECT')
    img = bpy.data.images.new(name + '_BC', size, size)
    if high:
        # The reduced mesh only needs somewhere to write; the colour comes from `high`.
        target = bpy.data.materials.new(name + '_target')
        target.use_nodes = True
        me.materials.clear()
        me.materials.append(target)
        high.select_set(True)
        bpy.context.view_layer.objects.active = obj
    for mat in me.materials:
        nt = mat.node_tree
        node = nt.nodes.new('ShaderNodeTexImage')
        node.image = img
        nt.nodes.active = node
        # Sample the source textures through their own UVs while writing the new ones.
        for n in nt.nodes:
            if n.type == 'TEX_IMAGE' and n is not node and not any(l.from_node.type == 'UVMAP' for l in n.inputs[0].links):
                uv = nt.nodes.new('ShaderNodeUVMap')
                uv.uv_map = src_uv_name
                nt.links.new(uv.outputs[0], n.inputs[0])
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 1
    sc.cycles.device = 'CPU'
    sc.render.bake.use_pass_direct = False
    sc.render.bake.use_pass_indirect = False
    sc.render.bake.margin = 4
    if high:
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, use_selected_to_active=True,
                            cage_extrusion=.02, max_ray_distance=.05)
    else:
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    out = ROOT / f'art-source/textures/ep2/{name}_BC.png'
    img.filepath_raw = str(out)
    img.file_format = 'PNG'
    img.save()
    mat = bpy.data.materials.new(name + '_baked')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = img
    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = .55
    me.materials.clear()
    me.materials.append(mat)
    # Keep only the baked UVs.
    for layer in [l for l in me.uv_layers if l.name != 'baked']:
        me.uv_layers.remove(layer)
    sc.render.engine = 'BLENDER_EEVEE'


def scan(coll, key, name, height=None, at=(0, 0, 0), yaw=0.0, ratio=None, extra_rot=(0, 0, 0), length=None):
    """Imports scan `key` once and returns its object, `height` metres tall (or `length`
    metres long), its base centred on `at`, turned `yaw` radians from facing -Y."""
    spec = SPEC[key]
    before = set(bpy.data.objects)
    # The kit's minimal "glTF Material Output" group lacks sockets the importer needs;
    # set it aside so the importer builds its own (the kit then reuses that one).
    kit_group = bpy.data.node_groups.get('glTF Material Output')
    if kit_group and 'Iridescence Factor' not in kit_group.interface.items_tree:
        kit_group.name = 'glTF Material Output (kit)'
    bpy.ops.import_scene.gltf(filepath=str(SCANS / f'{key}.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    leftovers = [o.name for o in new if o.type != 'MESH']
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    # Bake parents' transforms into the meshes (shape keys too, which transform_apply
    # would leave behind), then join them into one.
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    for o in meshes:
        o.data.transform(o.matrix_world.copy(), shape_keys=True)
        o.matrix_world = Matrix.Identity(4)
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    for n in leftovers:
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    obj.name = name
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    me = obj.data
    rx, ry, rz = (a + b for a, b in zip(spec['rot'], extra_rot))
    me.transform(Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Rotation(math.radians(ry), 4, 'Y')
                 @ Matrix.Rotation(math.radians(rx), 4, 'X'), shape_keys=True)
    if spec.get('strip'):
        _strip_pale(obj, **spec['strip'])
    r = spec['ratio'] if ratio is None else ratio
    high = None
    if spec['bake'] == 'high':
        high = obj.copy()
        high.data = obj.data.copy()
        coll.objects.link(high)
    if r < 1:
        dec = obj.modifiers.new('budget', 'DECIMATE')
        dec.ratio = r
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=dec.name)
    if spec['bake']:
        _bake(obj, 'T_ep2_' + key, high)
    if high:
        bpy.data.objects.remove(high, do_unlink=True)
    # Life size, base on the ground, centred.
    vs = [v.co for v in me.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    s = height / (hi.z - lo.z) if height else length / max(hi.x - lo.x, hi.y - lo.y)
    centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    me.transform(Matrix.Scale(s, 4) @ Matrix.Translation(-centre), shape_keys=True)
    # Motion shapes are built in the scan's own true space, before the mirror below.
    if spec.get('motion'):
        rest = [v.co.copy() for v in me.vertices]
        obj.shape_key_add(name='Basis')
        for key_name, co in MOTIONS[spec['motion']](rest).items():
            key = obj.shape_key_add(name=key_name)
            key.value = 0
            for d, c in zip(key.data, co):
                d.co = c
    # The world root mirrors X for Babylon: mirror the scan first, so it reads true in game.
    me.transform(Matrix.Scale(-1, 4, (1, 0, 0)), shape_keys=True)
    me.flip_normals()
    for p in me.polygons:
        p.use_smooth = True
    obj.location = at
    obj.rotation_mode = 'XYZ'  # the glTF importer leaves objects in quaternion mode
    obj.rotation_euler = (0, 0, yaw)
    print('Scan', name, len(me.polygons), 'faces', [round(v, 2) for v in (hi - lo) * s], flush=True)
    return obj


def instance(coll, src, name, at, yaw=0.0, scale=1.0, own=False):
    """Another placement of an imported scan, sharing its mesh (or with its `own`
    copy, for figures whose shape keys move independently)."""
    o = bpy.data.objects.new(name, src.data.copy() if own else src.data)
    coll.objects.link(o)
    o.location = at
    o.rotation_euler = (0, 0, yaw)
    o.scale = (scale, scale, scale)
    return o
