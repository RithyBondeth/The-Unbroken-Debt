"""Author Episode 2's ghosts as their own rigged, animated assets, moving on real human
performance (tools/ep2/mocap.py, CMU Motion Capture Database).
blender -b --factory-startup -P tools/ep2/build-ghosts.py [-- kmaoch|red]
Then: npm run assets -- ep2/ep2_kmaoch && npm run assets -- ep2/ep2_red

The garden's dead (91_25 "DragBadLegWalk", 104_13 "StumbleWalk", 79_73 "scared") drag a bad
leg on patrol, lurch when they hear something, and stand and listen with arms hanging;
some crawl on hands and knees instead (111_03 "Crawling", played forwards).
The woman in red has one clip per kind of scare: 104_13 bent over and stumbling for the
glimpse, 104_41 "ZombieWalk" arms rising for the lunge and the one behind you, 79_73 with
dead arms for the stare, 111_03 "Crawling" run backwards for rising out of the water.
"""
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ep2'), str(ROOT / 'tools/areas')]
import mocap as M  # noqa: E402
import pagoda_kmaoch as K  # noqa: E402
import pagoda_red as R  # noqa: E402


def fresh(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30  # the clips are resampled to this; the export reads it
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def export(coll, rig, name):
    rig.animation_data.action = None
    for b in rig.pose.bones:
        b.location = (0, 0, 0)
        b.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.scene.frame_set(1)
    for img in bpy.data.images:
        if img.source == 'FILE':
            img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / f'art-source/blender/ep2/{name}.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for o in coll.all_objects:
        o.select_set(True)
    out = ROOT / f'art-export/ep2/{name}.glb'
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(out), export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                              export_skins=True, export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
                              export_morph=False, export_extras=False, export_cameras=False, export_lights=False)
    print('ASSET', name, len(coll.all_objects), flush=True)


def build_kmaoch():
    coll = fresh('ep2_kmaoch')
    rig, _ = K.build(coll)
    hips = rig.data.bones['upperleg01.L'].head_local.z
    mapping = {'root': 'Hips', 'spine05': ('Hips', 'LowerBack', .5), 'spine04': 'LowerBack',
               'spine03': ('LowerBack', 'Spine', .5), 'spine02': 'Spine', 'spine01': 'Spine1',
               'neck01': 'Neck', 'neck02': ('Neck', 'Neck1', .5), 'neck03': 'Neck1', 'head': 'Head'}
    for s, S in (('L', 'Left'), ('R', 'Right')):
        mapping.update({f'upperleg01.{s}': f'{S}UpLeg', f'lowerleg01.{s}': f'{S}Leg', f'foot.{s}': f'{S}Foot',
                        f'clavicle.{s}': f'{S}Shoulder', f'upperarm01.{s}': f'{S}Arm',
                        f'lowerarm01.{s}': f'{S}ForeArm', f'wrist.{s}': f'{S}Hand'})
    body_only = {k: v for k, v in mapping.items() if not k.startswith(('clavicle', 'upperarm', 'lowerarm', 'wrist'))}
    feet = ('foot.L', 'foot.R')

    def walk(name, source, start, end, length):
        clip = M.Clip(source, start, end)
        speed = clip.stride_speed() * hips / clip.height()
        M.make_loop(M.clean_walk(clip), length)
        action = M.retarget(clip, rig, mapping, name, 'root', hips, travel=False, feet=feet)
        # What the game needs: how fast the performer travelled, so playback matches the
        # ground, and at what fraction of the loop each foot comes down.
        M.assign(rig, action)
        heights = {n: [] for n in feet}
        for f in range(1, clip.count + 1):
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            for n in feet:
                heights[n].append(rig.pose.bones[n].head.z)
        steps = []
        for n in feet:
            z = np.array(heights[n])
            low = z.min() + (z.max() - z.min()) * .22
            steps += [round(i / len(z), 3) for i in range(len(z)) if z[i] < low <= z[i - 1]]
        print('CLIP', name, f'{clip.count / clip.fps:.2f}s', f'{speed:.2f} m/s', 'steps', sorted(steps), flush=True)

    walk('walk', '91_25', 16.6, 24.4, 2.6)
    walk('lurch', '104_13', 0.2, 4.6, 1.8)
    # Some of the dead come on hands and knees: 111_03 "Crawling", the stretch going forwards.
    walk('crawl', '111_03', 3.0, 9.5, 2.4)
    # Standing, head turning, listening; the arms hang dead whatever the performer's did.
    stand = M.Clip('79_73', 1.0, 7.3)
    M.make_loop(M.clean_stand(stand), 4.2)
    M.retarget(stand, rig, body_only, 'listen', 'root', hips, travel=False, feet=feet)
    print('CLIP listen', f'{stand.count / stand.fps:.2f}s', flush=True)
    export(coll, rig, 'ep2_kmaoch')


def build_red():
    coll = fresh('ep2_red')
    rig, _ = R.build(coll)
    hips = rig.data.bones['LeftUpLeg_01'].head_local.z
    # Her rest pose is a T: for the clips where the arms do nothing they must hang.
    hang = M.limp_arms(rig, {'LeftArm_013': (.2, -.04, -1), 'RightArm_017': (-.2, -.04, -1),
                             'LeftForeArm_014': (.08, -.22, -1), 'RightForeArm_018': (-.08, -.22, -1),
                             'LeftHand_015': (.04, -.28, -1), 'RightHand_019': (-.04, -.28, -1)})
    no_arms = {k: v for k, v in R.MAP.items() if k not in R.ARMS}

    def act(name, clip, mapping=R.MAP, extra=None):
        M.retarget(clip, rig, mapping, name, 'Hips_00', hips, travel=False, feet=R.FEET, extra=extra)
        print('CLIP', name, f'{clip.count / clip.fps:.2f}s', flush=True)

    act('glimpse', M.clean_walk(M.Clip('104_13', 2.4, 3.7)))
    act('lunge', M.clean_stand(M.Clip('104_41', 1.2, 3.2)))
    act('behind', M.clean_stand(M.Clip('104_41', 1.8, 3.5)))
    act('stare', M.clean_stand(M.Clip('79_73', 1.0, 5.0)), no_arms, hang)
    act('rise', M.clean_stand(M.Clip('111_03', 1.0, 2.7)).reverse())
    export(coll, rig, 'ep2_red')


only = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else None
if only in (None, 'kmaoch'):
    build_kmaoch()
if only in (None, 'red'):
    build_red()
