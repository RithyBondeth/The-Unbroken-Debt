"""Episode 1's Preay: the user-supplied Sketchfab ghost ("Horror Ghost Character - Blood
Stained Spirit" by adhamasalah, CC BY 4.0; a woman in a bloodied white dress, long black
hair over her face), rigged and skinned here and moving on real human performance from the
CMU Motion Capture Database (retargeted with tools/ep2/mocap.py), as the road Neak Ta does.

blender -b --factory-startup --python-exit-code 1 -P tools/characters/build-preay.py
Then: npm run assets -- ep1/preay

The scan is a single unrigged surface (art-source/library/scans/blood_stained_spirit.glb,
made by tools/areas/import-blood-spirit.py). A skeleton with MakeHuman's bone names is fitted
to it, weights come from bone heat on a closed voxel copy of the body, then are reshaped:
the dress is shared smoothly between the legs and the pelvis (so it swings, never splits
between the knees), and the long hair follows the head at the scalp and the chest below.

Clips (30 fps; root kept in place unless noted; the game moves and turns the figure):
- stand: 79_73 standing still, the arms hanging, with a slow deep breath laid over the chest.
- walk: 104_02, a plain walk at a person's ordinary pace, one looped cycle; `WALK_SPEED` m/s at 1x, so the game
  moves her at exactly the pace her feet set down, and never faster than a person.
- hurry: 104_13, a stumbling, lurching hurry (the hunt under the house); `speed` m/s at 1x.
- reach: 104_41, the arms coming up (the taxi ride: her hands at Sora's glass).
The walk's heel strikes (seconds into the cycle) go to the game for her bare footsteps.
Clip facts for the game are written to src/episodes/ep1/data/preayClips.ts.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/ep2')]
import mocap as M  # noqa: E402

NAME = 'preay'
SCAN = ROOT / 'art-source/library/scans/blood_stained_spirit.glb'
OUT = ROOT / f'art-export/ep1/{NAME}.glb'
BLEND = ROOT / f'art-source/characters/preay/{NAME}.blend'
FACTS = ROOT / 'src/episodes/ep1/data/preayClips.ts'

# Landmarks on the 1.58 m scan, facing -Y with her left at +X (Blender metres).
HIP = .80     # hip joints
KNEE = .445
ANKLE = .075
SHOULDER = 1.285
NECK = 1.325
HEAD = 1.43
TOP = 1.58
HEM = .10     # the dress's hem; the bare feet are below it


def import_scan():
    bpy.ops.import_scene.gltf(filepath=str(SCAN))
    body = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
    for o in [o for o in bpy.context.scene.objects if o is not body]:
        bpy.data.objects.remove(o)
    body.data.transform(body.matrix_world)
    body.matrix_world = Matrix()
    # The scan faces +X; the clips (and the game's rigs) face -Y.
    body.data.transform(Matrix.Rotation(-math.pi / 2, 4, 'Z'))
    body.name = body.data.name = f'{NAME}_body'
    body.data.materials[0].name = 'M_preay_scan'
    return body


def coords(obj):
    co = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get('co', co)
    return co.reshape(-1, 3)


def hand_landmarks(co, side):
    """Wrist and fingertip from the hands hanging clear of the dress."""
    hand = co[(co[:, 0] * side > .19) & (co[:, 2] > .64) & (co[:, 2] < .92)]
    wrist = hand[(hand[:, 2] > .80) & (hand[:, 2] < .88)].mean(0)
    tip = hand[hand[:, 2].argmin()]
    return Vector(wrist), Vector(tip)


def build_rig(body):
    co = coords(body)
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = rig.data.name = f'{NAME}_rig'
    arm = rig.data
    for b in list(arm.edit_bones):
        arm.edit_bones.remove(b)

    def bone(name, head, tail, parent=None, connect=False):
        b = arm.edit_bones.new(name)
        b.head, b.tail = Vector(head), Vector(tail)
        b.roll = 0
        if parent:
            b.parent = arm.edit_bones[parent]
            b.use_connect = connect
        return name

    # Trunk: a little behind the dress's centre, as a spine is.
    y = .012
    bone('root', (0, y, .86), (0, y, .95))
    spine = [.95, 1.02, 1.09, 1.16, 1.23, 1.31]
    names = ['spine05', 'spine04', 'spine03', 'spine02', 'spine01']
    parent = 'root'
    for i, n in enumerate(names):
        lean = .006 * i  # the upper back sits slightly behind the waist
        parent = bone(n, (0, y + lean, spine[i]), (0, y + lean + .006, spine[i + 1]), parent, i > 0)
    neck = [NECK, 1.36, 1.395, HEAD]
    parent = 'spine01'
    for i, n in enumerate(['neck01', 'neck02', 'neck03']):
        parent = bone(n, (0, .03 - .008 * i, neck[i]), (0, .022 - .008 * i, neck[i + 1]), parent, i > 0)
    bone('head', (0, .006, HEAD), (0, .006, TOP), 'neck03', True)
    for side, s in ((1, 'L'), (-1, 'R')):
        wrist, tip = hand_landmarks(co, side)
        shoulder = Vector((.15 * side, .02, SHOULDER))
        # Elbow on the line shoulder-wrist, set back a little: a relaxed arm's slight bend.
        elbow = shoulder.lerp(wrist, .5) + Vector((0, .028, 0))
        bone(f'clavicle.{s}', (.025 * side, -.005, 1.27), shoulder, 'spine01')
        bone(f'upperarm01.{s}', shoulder, elbow, f'clavicle.{s}', True)
        bone(f'lowerarm01.{s}', elbow, wrist, f'upperarm01.{s}', True)
        bone(f'wrist.{s}', wrist, tip, f'lowerarm01.{s}', True)
        x = .082 * side
        bone(f'upperleg01.{s}', (x, .0, HIP), (x * .95, -.004, KNEE), 'root')
        bone(f'lowerleg01.{s}', (x * .95, -.004, KNEE), (x * .9, .03, ANKLE), f'upperleg01.{s}', True)
        bone(f'foot.{s}', (x * .9, .03, ANKLE), (x * 1.05, -.13, .015), f'lowerleg01.{s}', True)
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def bone_heat(body, rig):
    """Bone-heat weights, solved on a closed voxel copy (the scan is thousands of loose
    shells) and carried back to the scan's own vertices."""
    proxy = body.copy()
    proxy.data = body.data.copy()
    proxy.name = f'{NAME}_proxy'
    bpy.context.scene.collection.objects.link(proxy)
    bm = bmesh.new()
    bm.from_mesh(proxy.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=.002)
    bm.to_mesh(proxy.data)
    bm.free()
    remesh = proxy.modifiers.new('voxel', 'REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = .012
    bpy.context.view_layer.objects.active = proxy
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    bpy.ops.object.select_all(action='DESELECT')
    proxy.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    for b in rig.data.bones:
        if b.name not in body.vertex_groups:
            body.vertex_groups.new(name=b.name)
    bpy.context.view_layer.objects.active = body
    transfer = body.modifiers.new('weights', 'DATA_TRANSFER')
    transfer.object = proxy
    transfer.use_vert_data = True
    transfer.data_types_verts = {'VGROUP_WEIGHTS'}
    transfer.vert_mapping = 'POLYINTERP_NEAREST'
    transfer.layers_vgroup_select_src = 'ALL'
    transfer.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    bpy.data.objects.remove(proxy, do_unlink=True)


def weights(body):
    """Vertex weights as an array (vertices x bones) in the order of body.vertex_groups."""
    groups = list(body.vertex_groups)
    w = np.zeros((len(body.data.vertices), len(groups)))
    for v in body.data.vertices:
        for g in v.groups:
            w[v.index, g.group] = g.weight
    return w, [g.name for g in groups]


def hair_mask(body):
    """Hair: the near-black texels, read through each vertex's UV."""
    mat = body.data.materials[0]
    tex = next(n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE').image
    w, h = tex.size
    px = np.empty(w * h * 4, dtype=np.float32)
    tex.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    uv = body.data.uv_layers.active.data
    lum = np.full(len(body.data.vertices), 1.0)
    for loop in body.data.loops:
        u, v = uv[loop.index].uv
        x = min(w - 1, max(0, int(u % 1 * w)))
        y = min(h - 1, max(0, int(v % 1 * h)))
        r, g, b, _ = px[y, x]
        lum[loop.vertex_index] = min(lum[loop.vertex_index], .2126 * r + .7152 * g + .0722 * b)
    return lum


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def reshape_weights(body, rig):
    co = coords(body)
    w, names = weights(body)
    col = {n: i for i, n in enumerate(names)}
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    lum = hair_mask(body)
    hands = (np.abs(x) > .19) & (z > .62) & (z < .93)

    # The dress below the hips: one cloth over both legs. Its share of the thighs is split
    # smoothly across the body, so the front and back centre follow both legs half and half
    # (it swings with the stride and never parts between the knees); near the hips the pelvis
    # carries it. (The shins take none: a trailing knee bending would flick the hem out.)
    dress = (z > HEM + .005) & (z < HIP + .06) & ~hands
    u = np.clip((HIP + .06 - z) / (HIP + .06 - HEM), 0, 1)       # 0 at the hips, 1 at the hem
    # A long dress moves about half as far as the legs inside it: the pelvis keeps a share
    # all the way down, and the bare feet step out from under the hem.
    pelvis = .45 + .55 * np.clip(1 - u / .42, 0, 1) ** 1.4
    legs = 1 - pelvis
    shin = legs * 0
    thigh = legs - shin
    left = smoothstep(-.16, .16, x)
    new = np.zeros_like(w)
    new[:, col['root']] = pelvis
    new[:, col['upperleg01.L']] = thigh * left
    new[:, col['upperleg01.R']] = thigh * (1 - left)
    new[:, col['lowerleg01.L']] = shin * left
    new[:, col['lowerleg01.R']] = shin * (1 - left)
    # Blend into the solved weights over the top few centimetres, so the waist has no seam.
    keep = smoothstep(HIP - .02, HIP + .06, z)[:, None]
    w[dress] = (w * keep + new * (1 - keep))[dress]

    # Bare feet under the hem: each to its own foot and shin, by side.
    feet = z <= HEM + .005
    side_l = x > 0
    fw = np.zeros_like(w)
    toe = smoothstep(.045, -.02, y) * smoothstep(.09, .02, z)  # forefoot: the foot bone
    for s, mask in (('L', side_l), ('R', ~side_l)):
        fw[mask, col[f'foot.{s}']] = np.maximum(toe[mask], .35)
        fw[mask, col[f'lowerleg01.{s}']] = 1 - np.maximum(toe[mask], .35)
    w[feet] = fw[feet]

    # The long hair: the scalp turns with the head; the locks hanging over the face and down
    # the back go more and more with the neck and the chest the lower they hang.
    hair = (lum < .055) & (z > .9) & ~hands
    head = smoothstep(1.16, 1.42, z)
    neck = (1 - head) * smoothstep(1.02, 1.2, z) * .6
    chest = 1 - head - neck
    hw = np.zeros_like(w)
    hw[:, col['head']] = head
    hw[:, col['neck02']] = neck
    hw[:, col['spine01']] = chest * .7
    hw[:, col['spine02']] = chest * .3
    w[hair] = hw[hair]

    # Anything bone heat left unweighted (stray shells) goes to its nearest bone, else it
    # would stay behind at the rest pose as she walks off.
    empty = np.nonzero(w.sum(1) < 1e-6)[0]
    if len(empty):
        segs = [(col[b.name], np.array(b.head_local), np.array(b.tail_local)) for b in rig.data.bones]
        for i in empty:
            p = co[i]
            best = min(segs, key=lambda s: np.linalg.norm(
                p - (s[1] + np.clip(np.dot(p - s[1], s[2] - s[1]) / np.dot(s[2] - s[1], s[2] - s[1]), 0, 1) * (s[2] - s[1]))))
            w[i, best[0]] = 1
    print('WEIGHTS unweighted', len(empty), flush=True)

    # Four influences at most, normalised.
    np.put_along_axis(w, np.argsort(-w, axis=1)[:, 4:], 0, axis=1)
    w /= np.maximum(w.sum(1, keepdims=True), 1e-9)
    for g in body.vertex_groups:
        g.remove(range(len(body.data.vertices)))
    for j, n in enumerate(names):
        g = body.vertex_groups[n]
        nz = np.nonzero(w[:, j] > 1e-4)[0]
        for i in nz:
            g.add([int(i)], float(w[i, j]), 'REPLACE')
    print('WEIGHTS dress', int(dress.sum()), 'feet', int(feet.sum()), 'hair', int(hair.sum()), flush=True)


def strikes(rig, name):
    """Heel strikes in a looped walk (seconds into the clip): where each foot is furthest
    forward, the moment it comes down."""
    M.assign(rig, bpy.data.actions[name])
    first, last = (int(v) for v in bpy.data.actions[name].frame_range)
    track = {s: [] for s in 'LR'}
    for f in range(first, last):
        bpy.context.scene.frame_set(f)
        for s in 'LR':
            track[s].append(rig.pose.bones[f'foot.{s}'].head.y)
    n = len(track['L'])
    out = sorted(round(i / 30, 3) for y in track.values() for i in range(n)
                 if y[i] < y[i - 1] and y[i] <= y[(i + 1) % n])
    rig.animation_data.action = None
    # A stumble has small catches between steps: keep only one strike in any tenth of a second.
    kept = []
    for t in out:
        if not kept or t - kept[-1] > .1:
            kept.append(t)
    return kept


def breath(rig):
    """A slow, deep breath (about 5 s) laid over the chest and shoulders: an `extra`."""
    rests = {b.name: b.matrix_local.to_quaternion() for b in rig.data.bones}
    share = {'spine03': .25, 'spine02': .45, 'spine01': .35, 'clavicle.L': .5, 'clavicle.R': .5,
             'neck01': -.4}

    def extra(name, frame, q):
        k = share.get(name)
        if k is None:
            return q
        phase = math.sin(2 * math.pi * frame / (30 * 5.2))
        # Lifting the chest is a turn back about the figure's side-to-side axis.
        axis = Vector((1, 0, 0)) if not name.startswith('clavicle') else Vector((0, -1 if name.endswith('L') else 1, 0))
        lift = Quaternion(axis, math.radians(1.6) * k * (phase * .5 + .5))
        return lift @ q
    return extra


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    coll = bpy.data.collections.new(NAME)
    scene.collection.children.link(coll)
    body = import_scan()
    rig = build_rig(body)
    bone_heat(body, rig)
    reshape_weights(body, rig)
    deform = body.modifiers.get('Armature') or body.modifiers.new('Armature', 'ARMATURE')
    deform.object = rig
    deform.use_deform_preserve_volume = True
    body.parent = rig
    for o in (rig, body):
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
    # Walking, the performer's arms swing; the collarbones and hands keep her own rest (the
    # CMU hands and shoulders read as hands on hips and a shrug on this skeleton).
    walking = {k: v for k, v in mapping.items() if not k.startswith(('clavicle', 'wrist'))}
    feet = ('foot.L', 'foot.R')
    hang = M.limp_arms(rig, {f'{b}.{s}': (Vector(rig.data.bones[f'{b}.{s}'].tail_local)
                                         - Vector(rig.data.bones[f'{b}.{s}'].head_local) + Vector((0, -.004, 0)))
                             for b in ('upperarm01', 'lowerarm01', 'wrist') for s in 'LR'})
    still = breath(rig)

    def stand_extra(name, frame, q):
        return still(name, frame, hang(name, frame, q))

    facts = {}

    def act(name, clip, mapping=mapping, extra=None, travel=False):
        M.retarget(clip, rig, mapping, name, 'root', hips, travel=travel, feet=feet, extra=extra)
        facts[name] = {'seconds': round(clip.count / clip.fps, 3)}
        print('CLIP', name, f'{clip.count / clip.fps:.2f}s', flush=True)
        return clip

    scale = hips / M.Clip('104_02', 0, .1).height()

    stand = M.Clip('79_73', 1.0, 7.3)
    M.make_loop(M.clean_stand(stand), 5.2)
    act('stand', stand, body_only, stand_extra)

    walk = M.Clip('104_02', .5, 5.0)
    speed = walk.stride_speed() * scale
    M.make_loop(M.clean_walk(walk), 2.2)
    act('walk', walk, walking)
    facts['walk']['speed'] = round(speed, 3)

    hurry = M.Clip('104_13', .2, 4.6)
    hurry_speed = hurry.stride_speed() * hips / hurry.height()
    M.make_loop(M.clean_walk(hurry), 1.8)
    act('hurry', hurry, walking)
    facts['hurry']['speed'] = round(hurry_speed, 3)
    act('reach', M.clean_stand(M.Clip('104_41', 1.2, 3.2)), walking)
    facts['walk']['strikes'] = strikes(rig, 'walk')
    facts['hurry']['strikes'] = strikes(rig, 'hurry')

    rig.animation_data.action = None
    for b in rig.pose.bones:
        b.location = (0, 0, 0)
        b.rotation_quaternion = (1, 0, 0, 0)
    scene.frame_set(1)
    for img in bpy.data.images:
        if img.source == 'FILE':
            img.pack()
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    bpy.ops.object.select_all(action='DESELECT')
    for o in coll.all_objects:
        o.select_set(True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=False, export_skins=True, export_animations=True,
                              export_animation_mode='ACTIONS', export_force_sampling=True, export_morph=False,
                              export_extras=False, export_cameras=False, export_lights=False)
    body = ',\n'.join(f'  {k}: {{ ' + ', '.join(f'{a}: {json.dumps(b)}' for a, b in v.items()) + ' }'
                       for k, v in facts.items())
    text = ('// Written by tools/characters/build-preay.py: the Preay\'s clips (seconds), her walking\n'
            '// pace at 1x (m/s) and the walk\'s heel strikes (seconds into the cycle).\n'
            f'export const PREAY_CLIPS = {{\n{body},\n}} as const;\n')
    FACTS.write_text(text)
    print('FACTS', json.dumps(facts), flush=True)


build()
