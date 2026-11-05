"""The woman in red: the Kuntilanak Merah scan (fdhlan21, CC-BY 4.0) on her own real
skeleton, cleaned up into a rig that real human motion can drive (tools/ep2/mocap.py)."""
from pathlib import Path

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / 'art-source/library/scans/kuntilanak_red.glb'
HEIGHT = 1.66

MAP = {'Hips_00': 'Hips', 'Spine02_09': 'LowerBack', 'Spine01_010': 'Spine', 'Spine_011': 'Spine1',
       'neck_020': ('Neck', 'Neck1', .5), 'Head_021': 'Head'}
for prefix, S, ids in (('Left', 'Left', (1, 2, 3, 4, 12, 13, 14, 15)), ('Right', 'Right', (5, 6, 7, 8, 16, 17, 18, 19))):
    up, leg, foot, toe, sh, arm, fore, hand = ids
    MAP.update({f'{prefix}UpLeg_0{up}' if up < 10 else f'{prefix}UpLeg_{up}': f'{S}UpLeg',
                f'{prefix}Leg_0{leg}': f'{S}Leg', f'{prefix}Foot_0{foot}': f'{S}Foot',
                f'{prefix}ToeBase_0{toe}': f'{S}ToeBase',
                f'{prefix}Shoulder_0{sh}': f'{S}Shoulder', f'{prefix}Arm_0{arm}': f'{S}Arm',
                f'{prefix}ForeArm_0{fore}': f'{S}ForeArm', f'{prefix}Hand_0{hand}': f'{S}Hand'})
ARMS = tuple(k for k in MAP if any(p in k for p in ('Shoulder', 'Arm', 'Hand')))
FEET = ('LeftFoot_03', 'RightFoot_07')


def build(coll, name='kuntilanak', ratio=.6):
    """Imports the scan into `coll` with everything baked to world space, her T-pose as the
    rig's rest pose, life size, feet on the floor, facing -Y. Returns (rig, mesh)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SCAN))
    new = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in new if o.type == 'ARMATURE')
    mesh = next(o for o in new if o.type == 'MESH' and o.data.materials)
    # Her T-pose, as the importer left it, becomes the rest pose.
    bpy.context.view_layer.update()
    for mod in list(mesh.modifiers):
        if mod.type == 'ARMATURE':
            bpy.context.view_layer.objects.active = mesh
            bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Bake every parent's transform in, then scale to life with her feet at the origin.
    m_rig = rig.matrix_world.copy()
    m_mesh = mesh.matrix_world.copy()
    for o in (rig, mesh):
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        o.rotation_mode = 'QUATERNION'
    rig.data.transform(m_rig)
    mesh.data.transform(m_mesh)
    vs = [v.co for v in mesh.data.vertices]
    low = min(c.z for c in vs)
    high = max(c.z for c in vs)
    cx = (min(c.x for c in vs) + max(c.x for c in vs)) / 2
    cy = (min(c.y for c in vs) + max(c.y for c in vs)) / 2
    fit = Matrix.Scale(HEIGHT / (high - low), 4) @ Matrix.Translation((-cx, -cy, -low))
    rig.data.transform(fit)
    mesh.data.transform(fit)
    for o in new:
        if o not in (rig, mesh):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in (rig, mesh):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    rig.name = name + '_rig'
    mesh.name = name + '_body'
    if ratio < 1:
        dec = mesh.modifiers.new('budget', 'DECIMATE')
        dec.ratio = ratio
        bpy.context.view_layer.objects.active = mesh
        bpy.ops.object.modifier_apply(modifier=dec.name)
    for p in mesh.data.polygons:
        p.use_smooth = True
    mesh.modifiers.new('rig', 'ARMATURE').object = rig
    print('Red', len(mesh.data.polygons), 'faces', len(rig.data.bones), 'bones', flush=True)
    return rig, mesh
