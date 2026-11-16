"""The black Neak Ta as it is met on the taxi road: the same sculpted anatomy, aged face,
cotton sarong and sash as the shrine effigy (ancestor_forms.py), but kept on MakeHuman's own
skeleton and weights and moving on real human performance from the CMU Motion Capture
Database (retargeted with tools/ep2/mocap.py), instead of a rigid statue slid along the road.

blender -b --factory-startup -P tools/characters/build-neakta-roadside.py
Then: npm run assets -- ep1/neakta_roadside

Clips (30 fps, root kept in place; the game moves the figure along its own path):
- stand: 79_73 "scared", standing about with the head turning; the arms hang dead.
- walk: 91_25 "DragBadLegWalk", one leg dragged, the arms hanging dead; it crosses the
  road in the lamps at a person's pace, never faster.
- reach: 104_41 "ZombieWalk", the arms coming up; it reaches for Sora's window.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/characters'), str(ROOT / 'tools/ep2')]
import ancestor_forms as A  # noqa: E402
import mocap as M  # noqa: E402

NAME = 'neakta_roadside'
HEIGHT = 2.02  # a head taller than a man: at the edge of the lamps it reads as a person, wrongly
OUT = ROOT / f'art-export/ep1/{NAME}.glb'


def skin_from(body, rig, part):
    """Gives a cloth part the body's bone weights under it, and the same armature."""
    for g in body.vertex_groups:
        if g.name not in part.vertex_groups:
            part.vertex_groups.new(name=g.name)
    bpy.context.view_layer.objects.active = part
    transfer = part.modifiers.new('weights_from_body', 'DATA_TRANSFER')
    transfer.object = body
    transfer.use_vert_data = True
    transfer.data_types_verts = {'VGROUP_WEIGHTS'}
    transfer.vert_mapping = 'POLYINTERP_NEAREST'
    transfer.layers_vgroup_select_src = 'ALL'
    transfer.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    deform = part.modifiers.new('Armature', 'ARMATURE')
    deform.object = rig
    part.parent = rig


def skin_material():
    """The standing Neak Ta's worn skin maps; the game darkens it to soot-black lacquer."""
    m = A.material('M_neakta_worn_skin', (.35, .39, .32), .72)
    n, l = m.node_tree.nodes, m.node_tree.links
    p = n['Principled BSDF']
    folder = ROOT / 'art-source/characters/ancestors'
    bc = n.new('ShaderNodeTexImage')
    bc.image = bpy.data.images.load(str(folder / 'neakta-skin-BC.png'), check_existing=True)
    l.new(bc.outputs[0], p.inputs['Base Color'])
    tex = n.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(folder / 'neakta-skin-N.png'), check_existing=True)
    tex.image.colorspace_settings.name = 'Non-Color'
    normal = n.new('ShaderNodeNormalMap')
    l.new(tex.outputs['Color'], normal.inputs['Color'])
    l.new(normal.outputs[0], p.inputs['Normal'])
    return m


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    coll = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(coll)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[NAME]

    body, eyes, rig = A.anatomy(NAME, seated=False, variant=0, rest=True)
    body.data.materials.clear()
    body.data.materials.append(skin_material())
    uv = body.data.uv_layers.get('AnatomicalUV')
    if uv:
        uv.name = 'UVMap'
    parts = [body]
    cloth = A.clothing(body, False, 0)
    for part in cloth:
        if part.name.startswith('_'):
            bpy.data.objects.remove(part, do_unlink=True)
            continue
        parts.append(part)
    # Chalk eyes, carried by the head bone.
    eye = A.material('M_ancestor_chalk_eye', (.30, .30, .23), .86)
    iris = A.material('M_ancestor_faded_iris', (.015, .019, .014), .92)
    gaze = []
    for i, centre in enumerate(eyes):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=14, radius=.0108, location=centre)
        o = bpy.context.object
        o.name = f'{NAME}_eye_{i}'
        o.data.materials.append(eye)
        for p in o.data.polygons:
            p.use_smooth = True
        gaze.append(o)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1, location=centre + Vector((-.001, -.0104, 0)))
        o = bpy.context.object
        o.name = f'{NAME}_iris_{i}'
        o.scale = (.0034, .001, .0036)
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(iris)
        gaze.append(o)

    # Into the game's size: everything, skeleton included, scaled about the feet.
    height = max(v.co.z for v in body.data.vertices)
    factor = HEIGHT / height
    for o in [rig, *parts, *gaze]:
        o.matrix_world = Matrix.Scale(factor, 4) @ o.matrix_world
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig, *parts, *gaze]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    deform = body.modifiers.new('Armature', 'ARMATURE')
    deform.object = rig
    deform.use_deform_preserve_volume = True
    body.parent = rig
    for part in parts[1:]:
        skin_from(body, rig, part)
    for o in gaze:
        world = o.matrix_world.copy()
        o.parent = rig
        o.parent_type = 'BONE'
        o.parent_bone = 'head'
        o.matrix_world = world
    for o in [rig, *parts, *gaze]:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)

    hips = rig.data.bones['upperleg01.L'].head_local.z
    mapping = {'root': 'Hips', 'spine05': ('Hips', 'LowerBack', .5), 'spine04': 'LowerBack',
               'spine03': ('LowerBack', 'Spine', .5), 'spine02': 'Spine', 'spine01': 'Spine1',
               'neck01': 'Neck', 'neck02': ('Neck', 'Neck1', .5), 'neck03': 'Neck1', 'head': 'Head'}
    for s, S in (('L', 'Left'), ('R', 'Right')):
        mapping.update({f'upperleg01.{s}': f'{S}UpLeg', f'lowerleg01.{s}': f'{S}Leg', f'foot.{s}': f'{S}Foot',
                        f'clavicle.{s}': f'{S}Shoulder', f'upperarm01.{s}': f'{S}Arm',
                        f'lowerarm01.{s}': f'{S}ForeArm', f'wrist.{s}': f'{S}Hand'})
    arms = ('clavicle', 'upperarm', 'lowerarm', 'wrist')
    body_only = {k: v for k, v in mapping.items() if not k.startswith(arms)}
    feet = ('foot.L', 'foot.R')
    # Facing -Y, the figure's left is +X: long arms hanging dead, a little forward.
    hang = M.limp_arms(rig, {'upperarm01.L': (.1, -.03, -1), 'upperarm01.R': (-.1, -.03, -1),
                             'lowerarm01.L': (.03, -.1, -1), 'lowerarm01.R': (-.03, -.1, -1),
                             'wrist.L': (.02, -.12, -1), 'wrist.R': (-.02, -.12, -1)})

    def act(name, clip, mapping=mapping, extra=None):
        M.retarget(clip, rig, mapping, name, 'root', hips, travel=False, feet=feet, extra=extra)
        print('CLIP', name, f'{clip.count / clip.fps:.2f}s', flush=True)

    stand = M.Clip('79_73', 1.0, 7.3)
    M.make_loop(M.clean_stand(stand), 4.2)
    act('stand', stand, body_only, hang)
    walk = M.Clip('91_25', 16.6, 24.4)
    speed = walk.stride_speed() * hips / walk.height()
    M.make_loop(M.clean_walk(walk), 2.6)
    act('walk', walk, body_only, hang)
    print('CLIP walk speed', f'{speed:.2f} m/s', flush=True)
    act('reach', M.clean_stand(M.Clip('104_41', 1.2, 3.2)))

    rig.animation_data.action = None
    for b in rig.pose.bones:
        b.location = (0, 0, 0)
        b.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.scene.frame_set(1)
    for img in bpy.data.images:
        if img.source == 'FILE':
            img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / f'art-source/characters/ancestors/{NAME}.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for o in coll.all_objects:
        o.select_set(True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=False, export_skins=True, export_animations=True,
                              export_animation_mode='ACTIONS', export_force_sampling=True, export_morph=False,
                              export_extras=False, export_cameras=False, export_lights=False)
    print('ASSET', NAME, len(coll.all_objects), 'height', f'{HEIGHT:.2f}', flush=True)


build()
