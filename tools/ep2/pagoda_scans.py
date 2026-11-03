"""Photogrammetry scans of real temple images (art-source/library/scans), brought into
Episode 2: joined, stood upright, reduced to a game budget, pre-mirrored against the
world root's X flip, scaled to life and stood on their base at a named spot.

Sources (Sketchfab): seated monk (Obi.Moz, CC-BY 4.0), seated Buddha (Francesco
Coldesina, CC-BY 4.0), reclining Buddha (sofiarudi, CC-BY 4.0), standing alms monk
(manusainz, CC-BY 4.0), Prajnaparamita (Minneapolis Institute of Art, CC0), naga
finial (Cleveland Museum of Art, CC0); ghosts: Kuntilanak Merah and Pocong (fdhlan21,
CC-BY 4.0).
"""
from mathutils import Quaternion
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
SCANS = ROOT / 'art-source/library/scans'

# Per scan: the rotation (degrees about X, Y, Z) that stands it upright facing -Y,
# the decimation ratio, and baking: 'self' merges many materials into one texture,
# 'high' re-bakes the full scan's colour onto the reduced mesh (for scans whose
# texture atlas is too fragmented to survive decimation).
SPEC = {
    'monk_seated': dict(rot=(-90, 0, 120), ratio=.07, bake=None, motion='monk'),
    'buddha_seated': dict(rot=(0, 0, 180), ratio=1.0, bake=None),
    'buddha_reclining': dict(rot=(0, 0, 0), ratio=.6, bake='self'),
    'monk_alms_standing': dict(rot=(0, 0, 0), ratio=.18, bake=None),
    'prajnaparamita': dict(rot=(0, 0, 0), ratio=.06, bake=None),
    'naga_finial': dict(rot=(0, 0, 0), ratio=1.0, bake=None),
    # The woman in red, posed out of her T-pose: arms hanging limp and a little
    # forward, shoulders hunched, head dropped and tilted. Axes in armature space
    # (Z up, -Y forward), degrees.
    'kuntilanak_red': dict(rot=(0, 0, 0), ratio=.6, bake=None, skip=('Icosphere',), pose={
        'LeftArm_013': [((0, 1, 0), 72), ((1, 0, 0), -24)],
        'RightArm_017': [((0, 1, 0), -72), ((1, 0, 0), -30)],
        'LeftForeArm_014': [((1, 0, 0), -18)],
        'RightForeArm_018': [((1, 0, 0), -12)],
        'Spine_011': [((1, 0, 0), 9)],
        'neck_020': [((1, 0, 0), 10)],
        'Head_021': [((0, 1, 0), 20), ((1, 0, 0), 14)],
    }, pose_keys={
        # Both arms flung up and out at the viewer, head lifting out of the hair.
        'reach': {'LeftArm_013': [((1, 0, 0), -78)], 'RightArm_017': [((1, 0, 0), -72)],
                  'LeftForeArm_014': [((1, 0, 0), 14)], 'RightForeArm_018': [((1, 0, 0), 10)],
                  'Spine_011': [((1, 0, 0), 8)], 'Head_021': [((1, 0, 0), -30)]},
        # The neck snapping over to one side, then the other: too far for a living neck.
        'snap_a': {'neck_020': [((0, 1, 0), 14)], 'Head_021': [((0, 1, 0), 40), ((1, 0, 0), -8)]},
        'snap_b': {'neck_020': [((0, 1, 0), -16)], 'Head_021': [((0, 1, 0), -62), ((1, 0, 0), -6)]},
        # Folded forward, face turned up from under the hair to stare.
        'hunch': {'Spine01_010': [((1, 0, 0), 12)], 'Spine_011': [((1, 0, 0), 22)], 'Head_021': [((1, 0, 0), -38)],
                  'LeftArm_013': [((1, 0, 0), -14)], 'RightArm_017': [((1, 0, 0), -14)]},
        'breathe': {'Spine_011': [((1, 0, 0), -3)], 'LeftShoulder_012': [((0, 1, 0), 4)],
                    'RightShoulder_016': [((0, 1, 0), -4)]},
    }),
    # A corpse bound in its burial shroud, tied at head, neck, waist and feet.
    'pocong': dict(rot=(0, 0, 0), ratio=.6, bake=None, motion='pocong'),
}


def _turn_pose(rig, pose, after=False):
    """Turns bones about armature-space axes: by default ahead of their current pose
    (as from the rest pose); `after` turns the bone from where it now points."""
    for bone_name, turns in pose.items():
        b = rig.pose.bones[bone_name]
        b.rotation_mode = 'QUATERNION'
        q = b.bone.matrix_local.to_quaternion()
        for axis, deg in turns:
            turn = q.inverted() @ Quaternion(Vector(axis), math.radians(deg)) @ q
            b.rotation_quaternion = turn @ b.rotation_quaternion if after else b.rotation_quaternion @ turn


def _pose_keys(objects, spec):
    """Like _pose, but also bakes each of spec['pose_keys'] (turns added to the base
    pose) into a shape key, so the frozen figure can still move in game. The mesh is
    reduced first, so every key matches the final vertices."""
    rig = next(o for o in objects if o.type == 'ARMATURE')
    mesh = next(o for o in objects if o.type == 'MESH')
    bpy.context.view_layer.objects.active = mesh
    # Reduce the rest mesh with the rig switched off, or the pose is baked in twice.
    rigs = [m for m in mesh.modifiers if m.type == 'ARMATURE']
    for mod in rigs:
        mod.show_viewport = False
    dec = mesh.modifiers.new('budget', 'DECIMATE')
    dec.ratio = spec['ratio']
    bpy.ops.object.modifier_apply(modifier=dec.name)
    for mod in rigs:
        mod.show_viewport = True

    # The importer leaves each bone in its own starting pose; every shape builds on it.
    start = {}
    for b in rig.pose.bones:
        b.rotation_mode = 'QUATERNION'
        start[b.name] = (b.rotation_quaternion.copy(), b.location.copy(), b.scale.copy())

    def shape(extra):
        for b in rig.pose.bones:
            b.rotation_quaternion, b.location, b.scale = (v.copy() for v in start[b.name])
        _turn_pose(rig, spec['pose'])
        _turn_pose(rig, extra, after=True)
        bpy.context.view_layer.update()
        ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        out = ev.to_mesh()
        co = [v.co.copy() for v in out.vertices]
        ev.to_mesh_clear()
        return co

    rest = shape({})
    keys = {name: shape(extra) for name, extra in spec['pose_keys'].items()}
    for mod in [m for m in mesh.modifiers if m.type == 'ARMATURE']:
        mesh.modifiers.remove(mod)
    for v, c in zip(mesh.data.vertices, rest):
        v.co = c
    mesh.shape_key_add(name='Basis')
    for name, co in keys.items():
        key = mesh.shape_key_add(name=name)
        key.value = 0
        for d, c in zip(key.data, co):
            d.co = c


def _turned(co, pivot, axis, degrees, weight):
    """`co` turned about `pivot` and `axis` by `degrees` scaled by `weight` (0..1)."""
    if weight <= 0:
        return co.copy()
    return pivot + Quaternion(Vector(axis), math.radians(degrees) * weight) @ (co - pivot)


def _smooth(lo, hi, x):
    t = min(1.0, max(0.0, (x - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def _monk_motion(co):
    """A seated monk (base at 0, facing -Y): head turns either way and nods from the
    neck, the chest rises with breath, the body bows from the hips."""
    top = max(c.z for c in co)
    head = [c for c in co if c.z > top - .2]
    hx, hy = sum(c.x for c in head) / len(head), sum(c.y for c in head) / len(head)
    neck = Vector((hx, hy + .02, top - .25))

    def w_head(c):
        reach = math.hypot(c.x - hx, c.y - hy)
        # The head and neck only: the shoulders and robe stay where they are.
        return _smooth(top - .29, top - .2, c.z) * (1 - _smooth(.11, .16, reach))
    band = [c for c in co if top - .62 < c.z < top - .3]
    tx, ty = sum(c.x for c in band) / len(band), sum(c.y for c in band) / len(band)

    def breathe(c):
        b = math.sin(math.pi * min(1, max(0, (c.z - (top - .62)) / .32)))
        r = Vector((c.x - tx, c.y - ty, 0))
        lift = .004 * _smooth(top - .34, top - .28, c.z)
        return c + r * .018 * b * (1 - _smooth(.25, .32, r.length)) + Vector((0, 0, lift))
    hip = Vector((tx, ty, .28))
    return {
        'look_pos': [_turned(c, neck, (0, 0, 1), 34, w_head(c)) for c in co],
        'look_neg': [_turned(c, neck, (0, 0, 1), -34, w_head(c)) for c in co],
        'nod': [_turned(c, neck, (1, 0, 0), 16, w_head(c)) for c in co],
        'breathe': [breathe(c) for c in co],
        'bow': [_turned(c, hip, (1, 0, 0), 11, _smooth(.28, .5, c.z)) for c in co],
    }


def _pocong_motion(co):
    """A shrouded corpse (base at 0, facing -Y): squashed as it lands from a hop and
    stretched as it leaves the ground, head jerking over to either side, leaning,
    the shroud filling and emptying over the chest."""
    h = max(c.z for c in co)
    cx, cy = sum(c.x for c in co) / len(co), sum(c.y for c in co) / len(co)
    neck = Vector((cx, cy, h - .4))

    def spread(c, z, k):
        b = math.sin(math.pi * min(1, max(0, c.z / h)))
        return Vector((cx + (c.x - cx) * (1 + k * b), cy + (c.y - cy) * (1 + k * b), z))

    def w_head(c):
        return _smooth(h - .46, h - .32, c.z)

    def breathe(c):
        b = math.sin(math.pi * min(1, max(0, (c.z - .95) / .5)))
        return Vector((cx + (c.x - cx) * (1 + .03 * b), cy + (c.y - cy) * (1 + .03 * b), c.z))
    base = Vector((cx, cy, 0))
    return {
        'squash': [spread(c, c.z * .9, .07) for c in co],
        'stretch': [spread(c, c.z * 1.07, -.035) for c in co],
        'head_a': [_turned(_turned(c, neck, (0, 1, 0), 30, w_head(c)), neck, (0, 0, 1), 14, w_head(c)) for c in co],
        'head_b': [_turned(_turned(c, neck, (0, 1, 0), -30, w_head(c)), neck, (0, 0, 1), -14, w_head(c)) for c in co],
        'lean': [_turned(c, base, (1, 0, 0), 11 * c.z / h, 1) for c in co],
        'breathe': [breathe(c) for c in co],
    }


MOTIONS = {'monk': _monk_motion, 'pocong': _pocong_motion}


def _pose(objects, pose):
    """Poses a rigged scan (rotations about armature-space axes) and freezes the
    meshes in that pose, removing the armature."""
    rig = next(o for o in objects if o.type == 'ARMATURE')
    _turn_pose(rig, pose)
    bpy.context.view_layer.update()
    for o in objects:
        if o.type != 'MESH':
            continue
        for mod in [m for m in o.modifiers if m.type == 'ARMATURE']:
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=mod.name)


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
    for o in [o for o in new if o.name.split('.')[0] in spec.get('skip', ())]:
        new.remove(o)
        bpy.data.objects.remove(o, do_unlink=True)
    if spec.get('pose_keys'):
        _pose_keys(new, spec)
    elif spec.get('pose'):
        _pose(new, spec['pose'])
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
    # A posed rig was reduced before its shape keys were baked.
    r = 1.0 if spec.get('pose_keys') else spec['ratio'] if ratio is None else ratio
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
