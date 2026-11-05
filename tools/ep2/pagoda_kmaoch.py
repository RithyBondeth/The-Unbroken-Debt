"""The garden's hungry dead: a kmaoch (the Khmer word is both corpse and ghost), a starved
villager washed and laid out in white, up and walking. It replaces the bound Pocong: it
has arms and legs and walks; of the scan only the head survives, cut off above its neck
rope and below its topknot, with the red movie-ghost glow taken out of its eyes because
these dead are blind.

The body is CC0 MakeHuman anatomy (the same source as Episode 1's Sok), starved by hand:
limbs drawn down to the bone between knobbed joints, belly fallen in, the neck a long
cord; ribs, collarbones, spine and hip crests baked in from a sculpted copy. Its skin is
toned to the scan's face (fdhlan21, CC-BY 4.0), so head and body are one dead colour. The
white funeral cloth is simulated over the body so it hangs and folds as cloth does.

Ritual detail (white funeral cloth, white thread at wrists and ankles) is advisor-review.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[2]
MAKEHUMAN = ROOT / 'art-source/library/makehuman-sok'
SCANS = ROOT / 'art-source/library/scans'
TEXTURES = ROOT / 'art-source/textures/ep2'

# Bones the game moves. Everything else (face, tongue, fingers, toes) is merged into its
# nearest kept ancestor, after the hands have been set in their dead curl.
KEEP = {
    'root', 'spine05', 'spine04', 'spine03', 'spine02', 'spine01', 'neck01', 'neck02', 'neck03', 'head',
    *[f'{b}.{s}' for s in 'LR' for b in ('pelvis', 'upperleg01', 'upperleg02', 'lowerleg01', 'lowerleg02', 'foot',
                                         'clavicle', 'shoulder01', 'upperarm01', 'upperarm02', 'lowerarm01',
                                         'lowerarm02', 'wrist')],
}
NECK_LENGTH = .032  # a starved neck looks long; the scan's chin needs room above the collar


def _smooth(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def _read_target(path):
    out = {}
    for line in path.read_text().splitlines():
        if line and not line.startswith('#'):
            a = line.split()
            out[int(a[0])] = np.array(a[1:4], dtype=float)
    return out


def _load_makehuman():
    """Vertices (with the old, thin male targets), faces, UVs and skeleton data."""
    verts, uvs, faces, faceuv = [], [], [], []
    group = ''
    for line in (MAKEHUMAN / 'base.obj').read_text().splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == 'v':
            verts.append([float(x) for x in a[1:4]])
        elif a[0] == 'vt':
            uvs.append((float(a[1]), float(a[2])))
        elif a[0] == 'g':
            group = a[1]
        elif a[0] == 'f' and group == 'body':
            data = [p.split('/') for p in a[1:]]
            faces.append([int(p[0]) - 1 for p in data])
            faceuv.append([int(p[1]) - 1 for p in data])
    verts = np.array(verts)
    # Old, Asian, and as thin as both macro axes go: no muscle and no fat. The two thin
    # targets each hold the average body too, so it is taken out once.
    for name, k in (('asian-male-old', 1), ('universal-male-old-averagemuscle-minweight', 1.25),
                    ('universal-male-old-minmuscle-averageweight', 1.25),
                    ('universal-male-old-averagemuscle-averageweight', -1.25)):
        for i, d in _read_target(MAKEHUMAN / f'{name}.target').items():
            verts[i] += d * k
    skeleton = json.loads((MAKEHUMAN / 'default.mhskel').read_text())
    weights = json.loads((MAKEHUMAN / 'default_weights.mhw').read_text())['weights']
    return verts, faces, uvs, faceuv, skeleton, weights


def _starve(co, dominant, joint):
    """Draws the limbs down to the bone between knobbed joints and hollows the trunk.
    `co` is the metre-space vertex array, `dominant` the strongest bone per vertex."""
    out = co.copy()
    segments = {
        # bone prefix: (from joint, to joint, flesh lost at mid-limb, ramp in, ramp out)
        'upperarm': ('upperarm01', 'lowerarm01', .4, .42, .72),
        'lowerarm': ('lowerarm01', 'wrist', .34, .22, .72),
        'upperleg': ('upperleg01', 'lowerleg01', .5, .5, .72),
        'lowerleg': ('lowerleg01', 'foot', .42, .25, .7),
    }
    for side in 'LR':
        for prefix, (a, b, flesh, rise, fall) in segments.items():
            p, q = joint(f'{a}.{side}'), joint(f'{b}.{side}')
            axis = q - p
            length = np.linalg.norm(axis)
            axis /= length
            for i, name in enumerate(dominant):
                if name.startswith(prefix) and name.endswith('.' + side):
                    t = np.dot(co[i] - p, axis)
                    u = float(np.clip(t / length, 0, 1))
                    centre = p + axis * t
                    keep = 1 - flesh * float(_smooth(0, rise, u) * (1 - _smooth(fall, 1, u)))
                    out[i] = centre + (co[i] - centre) * keep
    # The trunk: the front falls in under the ribs, the flanks narrow to the hip crests.
    pelvis_z = joint('upperleg01.L')[2]
    chest_z = joint('neck01')[2]
    ribs_low = pelvis_z + (chest_z - pelvis_z) * .36
    cy = float(np.median(co[:, 1]))
    for i, name in enumerate(dominant):
        if not name.startswith(('spine', 'pelvis', 'root')):
            continue
        x, y, z = co[i]
        belly = _smooth(pelvis_z + .03, pelvis_z + .1, z) * (1 - _smooth(ribs_low - .02, ribs_low + .09, z))
        if y < cy:
            out[i, 1] += float(belly) * min(.07, (cy - y) * .6)
        out[i, 0] *= 1 - float(belly) * .2
        # Shoulders and chest lose their padding too.
        upper = _smooth(ribs_low, chest_z, z)
        out[i, 0] *= 1 - float(upper) * .04
    # The neck: a cord.
    a, b = joint('neck01'), joint('head')
    axis = (b - a) / np.linalg.norm(b - a)
    for i, name in enumerate(dominant):
        if name.startswith('neck'):
            t = np.dot(co[i] - a, axis)
            centre = a + axis * t
            out[i] = centre + (co[i] - centre) * .72
    # Hips and buttocks wasted away, whichever bone owns the vertex.
    hip = _smooth(pelvis_z - .2, pelvis_z - .04, out[:, 2]) * (1 - _smooth(pelvis_z + .07, pelvis_z + .16, out[:, 2]))
    cyh = float(np.median(out[(out[:, 2] > pelvis_z - .1) & (out[:, 2] < pelvis_z + .1), 1]))
    out[:, 0] *= 1 - hip * .2
    out[:, 1] = cyh + (out[:, 1] - cyh) * (1 - hip * .3)
    return out


def _dead_pose(rig):
    """Rest pose for the cloth and the walk: arms hanging, a little forward and out from
    the ribs, fingers half curled the way dead hands set. Turns are about armature axes."""
    for b in rig.pose.bones:
        b.rotation_mode = 'QUATERNION'

    def turn(name, axis, degrees):
        if name not in rig.pose.bones:
            return
        b = rig.pose.bones[name]
        q = b.bone.matrix_local.to_quaternion()
        b.rotation_quaternion = b.rotation_quaternion @ (q.inverted() @ Quaternion(Vector(axis), math.radians(degrees)) @ q)
    def aim(name, direction):
        """Turns a bone, in place, so it points along `direction` (armature space)."""
        bpy.context.view_layer.update()
        b = rig.pose.bones[name]
        now = (b.tail - b.head).normalized()
        q = b.bone.matrix_local.to_quaternion()
        # In pose space the bone's own frame is its current matrix.
        cur = b.matrix.to_quaternion()
        d = now.rotation_difference(Vector(direction).normalized())
        b.rotation_quaternion = b.rotation_quaternion @ (cur.inverted() @ d @ cur)
        del q
    for side, sign in (('L', -1), ('R', 1)):
        x = 1 if side == 'L' else -1
        # The rig's .L side is the figure's own left: +X when it faces -Y.
        aim(f'upperarm01.{side}', (x * .2, -.07, -1))
        aim(f'lowerarm01.{side}', (x * .1, -.32, -1))
        for finger in range(1, 6):
            for part, angle in ((1, 18), (2, 34), (3, 26)):
                turn(f'finger{finger}-{part}.{side}', (0, 1, 0) if finger == 1 else (1, 0, 0), (sign * angle * .5) if finger == 1 else -angle)
    bpy.context.view_layer.update()


def build_body(coll, name):
    """Skinned, starved MakeHuman body in its rest pose. Returns (mesh object, rig)."""
    raw, faces, uvs, faceuv, skeleton, weights = _load_makehuman()
    used = sorted({i for f in faces for i in f})
    floor = raw[used, 1].min()

    def local(p):
        return np.array([p[0] * .1, -p[2] * .1, (p[1] - floor) * .1])

    def joint(n):
        return local(raw[skeleton['joints'][n]].mean(0))

    joints = {}
    for n, b in skeleton['bones'].items():
        joints[b['head']] = joints.get(b['head']) if b['head'] in joints else joint(b['head'])
        joints[b['tail']] = joints.get(b['tail']) if b['tail'] in joints else joint(b['tail'])
    co = np.array([local(raw[i]) for i in used])
    # A longer neck: everything above its base rises, bones and skin together.
    base = joints[skeleton['bones']['neck01']['head']][2]
    top = joints[skeleton['bones']['head']['head']][2]
    co[:, 2] += NECK_LENGTH * _smooth(base, top, co[:, 2])
    for k in joints:
        joints[k] = joints[k] + np.array([0, 0, NECK_LENGTH * float(_smooth(base, top, joints[k][2]))])
    remap = {i: n for n, i in enumerate(used)}
    # Which bone owns each vertex decides how it starves and what it is cut away with.
    strongest = {}
    for n, entries in weights.items():
        for i, w in entries:
            if i in remap and w > strongest.get(remap[i], ('', 0))[1]:
                strongest[remap[i]] = (n, w)
    dominant = [strongest.get(i, ('', 0))[0] for i in range(len(co))]

    def joint_by_bone(n):
        return joints[skeleton['bones'][n]['head']]
    co = _starve(co, dominant, lambda n: joint_by_bone(n) if n in skeleton['bones'] else joint(n))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(co.tolist(), [], [[remap[i] for i in f] for f in faces])
    mesh.update()
    uv = mesh.uv_layers.new(name='UVMap')
    for poly, indices in zip(mesh.polygons, faceuv):
        for loop, index in zip(poly.loop_indices, indices):
            uv.data[loop].uv = uvs[index]
    for poly in mesh.polygons:
        poly.use_smooth = True
    body = bpy.data.objects.new(name, mesh)
    coll.objects.link(body)

    arm = bpy.data.armatures.new(name + '_rig')
    rig = bpy.data.objects.new(arm.name, arm)
    coll.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for n, b in skeleton['bones'].items():
        bone = arm.edit_bones.new(n)
        bone.head = joints[b['head']].tolist()
        bone.tail = joints[b['tail']].tolist()
        if (bone.tail - bone.head).length < 1e-4:
            bone.tail = bone.head + Vector((0, 0, .01))
    for n, b in skeleton['bones'].items():
        if b['parent']:
            arm.edit_bones[n].parent = arm.edit_bones[b['parent']]
    bpy.ops.object.mode_set(mode='OBJECT')
    for n, entries in weights.items():
        g = body.vertex_groups.new(name=n)
        for i, w in entries:
            if i in remap:
                g.add([remap[i]], w, 'REPLACE')
    mod = body.modifiers.new('rig', 'ARMATURE')
    mod.object = rig
    mod.use_deform_preserve_volume = True

    # Set the rest pose: the mesh takes it for good, then the armature does.
    _dead_pose(rig)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Merge every other bone's weights into its nearest kept ancestor, and drop it.
    parents = {b.name: (b.parent.name if b.parent else None) for b in arm.bones}

    def kept(n):
        while n and n not in KEEP:
            n = parents[n]
        return n or 'root'
    merged = {}
    for v in mesh.vertices:
        acc = {}
        for ge in v.groups:
            k = kept(body.vertex_groups[ge.group].name)
            acc[k] = acc.get(k, 0) + ge.weight
        merged[v.index] = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
    for g in list(body.vertex_groups):
        body.vertex_groups.remove(g)
    for k in KEEP:
        body.vertex_groups.new(name=k)
    for i, acc in merged.items():
        total = sum(w for _, w in acc) or 1
        for k, w in acc:
            body.vertex_groups[k].add([i], w / total, 'REPLACE')
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for b in list(arm.edit_bones):
        if b.name not in KEEP:
            arm.edit_bones.remove(b)
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = body.modifiers.new('rig', 'ARMATURE')
    mod.object = rig
    print('Kmaoch body', len(mesh.polygons), 'faces', len(arm.bones), 'bones', flush=True)
    return body, rig


# ------------------------------------------------------------------ the scan's head


def blind_eyes(image):
    """Takes the scan's glowing red out of its eyes: pale clouded eyes, no pupil."""
    w, h = image.size
    px = np.empty(w * h * 4, np.float32)
    image.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    # The face chart, in the atlas's bottom right (Blender rows run upward).
    x0, x1, y0, y1 = int(w * .76), int(w * .87), int(h * .13), int(h * .31)
    rgb = px[y0:y1, x0:x1, :3]
    other = rgb[..., 1:].max(-1)
    red = np.clip((rgb[..., 0] - other - .06) / .28, 0, 1)
    # Grow the mask a little so the glow's halo goes too.
    grown = red.copy()
    for _ in range(4):
        grown = np.maximum.reduce([grown, np.roll(grown, 1, 0), np.roll(grown, -1, 0), np.roll(grown, 1, 1), np.roll(grown, -1, 1)]) * .92
    milk = np.array([.60, .62, .56], np.float32)
    grey = rgb.mean(-1, keepdims=True) * np.array([.82, .86, .8], np.float32)
    out = rgb * (1 - grown[..., None]) + grey * grown[..., None]
    core = _smooth(.25, .85, red)[..., None]
    out = out * (1 - core) + (milk * (.75 + .25 * rgb.mean(-1, keepdims=True))) * core
    px[y0:y1, x0:x1, :3] = out
    # The hood is the same old cotton as the rest: the scan's near-white is dulled, the
    # face chart left as it is.
    face = np.zeros((h, w), bool)
    face[y0:y1, x0:x1] = True
    lit = px[..., :3].mean(-1)
    pale = _smooth(.45, .8, lit) * ~face
    px[..., :3] *= (1 - pale[..., None] * np.array([.34, .36, .46], np.float32))
    image.pixels.foreach_set(px.ravel())
    image.update()
    image.pack()  # the exporter must take these pixels, not the scan's originals


def graft_head(coll, body, rig):
    """Cuts the scan's head out from above its neck rope to below its topknot, sets it on
    the long neck and binds it to the head bone. The body's own head goes."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SCANS / 'pocong.glb'))
    new = [o for o in bpy.data.objects if o not in before]
    src = next(o for o in new if o.type == 'MESH')
    src.data.transform(src.matrix_world.copy())
    src.parent = None
    src.matrix_world = Matrix.Identity(4)
    for o in new:
        if o is not src:
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(src.users_collection):
        c.objects.unlink(src)
    coll.objects.link(src)
    src.name = 'kmaoch_head'
    me = src.data
    bm = bmesh.new()
    bm.from_mesh(me)
    keep_lo, keep_hi = .512, .752
    doomed = [f for f in bm.faces if not all(keep_lo <= v.co.z <= keep_hi for v in f.verts)]
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()

    # Where the body's head is.
    head_group = body.vertex_groups['head'].index
    heads = []
    for v in body.data.vertices:
        for ge in v.groups:
            if ge.group == head_group and ge.weight > .5:
                heads.append(v.co.copy())
                break
    lo = Vector((min(c[i] for c in heads) for i in range(3)))
    hi = Vector((max(c[i] for c in heads) for i in range(3)))
    vs = [v.co for v in me.vertices]
    slo = Vector((min(c[i] for c in vs) for i in range(3)))
    shi = Vector((max(c[i] for c in vs) for i in range(3)))
    s = .9  # a little under the scan's own size: a starved skull on a thin neck
    me.transform(Matrix.Translation(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2 - .012, hi.z + .012)) @ Matrix.Scale(s, 4)
                 @ Matrix.Translation((-(slo.x + shi.x) / 2, -(slo.y + shi.y) / 2, -shi.z)))
    for p in me.polygons:
        p.use_smooth = True
    # The body's own head is cut away, leaving the neck to run up inside the hood.
    bm = bmesh.new()
    bm.from_mesh(body.data)
    deform = bm.verts.layers.deform.active
    hood_edge = hi.z + .012 - (shi.z - slo.z) * s
    doomed = [f for f in bm.faces if all(v[deform].get(head_group, 0) > .35 and v.co.z > hood_edge + .045 for v in f.verts)]
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(body.data)
    bm.free()
    for name in KEEP:
        src.vertex_groups.new(name=name)
    src.vertex_groups['head'].add([v.index for v in me.vertices], 1.0, 'REPLACE')
    src.modifiers.new('rig', 'ARMATURE').object = rig
    print('Kmaoch head', len(me.polygons), 'faces, scale', round(s, 3), flush=True)
    return src


# ------------------------------------------------------------------ starved skin


def _noise(co, rng, wavelengths, amps):
    """Cheap smooth 3D noise: sums of sine waves in random directions."""
    out = np.zeros(len(co))
    for wave, amp in zip(wavelengths, amps):
        for _ in range(6):
            d = rng.normal(size=3)
            d /= np.linalg.norm(d)
            out += amp / 6 * np.sin(co @ d * (2 * math.pi / wave) + rng.uniform(0, 7))
    return out


def _landmarks(rig):
    b = rig.data.bones
    return {n: np.array(b[n].head_local) for n in ('neck01', 'spine01', 'spine03', 'upperleg01.L', 'upperleg01.R', 'clavicle.L', 'clavicle.R', 'shoulder01.L', 'shoulder01.R')}


def _sculpt_height(co, torso, marks, rng):
    """Metres to push each vertex out along its normal: ribs, breastbone, collarbones,
    spine and shoulder blades, hip crests, and crepey skin over everything."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    h = np.zeros(len(co))
    neck = marks['neck01'][2]
    hip = marks['upperleg01.L'][2]
    cy = np.median(y[torso > .5])
    front = y < cy
    # Ribs: ten ridges falling away from the breastbone and round the flanks.
    low = hip + (neck - hip) * .34
    ax = np.abs(x)
    for k in range(10):
        z0 = neck - .055 - k * .0265 - k * k * .0002
        slope = .16 + .075 * k
        d = (z - (z0 - slope * ax)) / .0085
        h += .0078 * np.exp(-d * d)
    h *= _smooth(.008, .03, ax) * _smooth(low - .03, low + .03, z - .1 * ax) * (1 - _smooth(neck - .05, neck - .015, z)) * torso
    h *= np.where(front, 1, .55)
    # The hollow between the ribs falls away below the last one: a sharp costal arch.
    arch = np.exp(-(((z - (low + .012 - .22 * ax)) / .012) ** 2)) * _smooth(.01, .05, ax) * (1 - _smooth(.14, .2, ax))
    h += .006 * arch * torso * front
    # Breastbone, and a pit at the top of it.
    h += .007 * np.exp(-((x / .012) ** 2)) * _smooth(low + .05, low + .09, z) * (1 - _smooth(neck - .04, neck - .012, z)) * torso * front
    # Collarbones, from the throat out to each shoulder.
    for side in 'LR':
        a, b = marks[f'clavicle.{side}'], marks[f'shoulder01.{side}']
        axis = b - a
        L = np.linalg.norm(axis)
        axis = axis / L
        rel = co - a
        t = np.clip(rel @ axis, 0, L)
        d = np.linalg.norm(rel - np.outer(t, axis), axis=1)
        ridge = np.exp(-(((d - .012) / .012) ** 2))
        h += .007 * ridge * front * torso
    # Spine and shoulder blades at the back.
    back = ~front
    knobs = .5 + .5 * np.cos(z / .031 * 2 * math.pi)
    h += .007 * np.exp(-((x / .013) ** 2)) * knobs ** 2 * back * torso * _smooth(hip, hip + .05, z)
    for sign in (-1, 1):
        d2 = ((x - sign * .085) / .05) ** 2 + ((z - (neck - .13)) / .08) ** 2
        h += .009 * np.exp(-d2 * 2) * back * torso
    # Hip crests standing out over the sunken belly.
    for sign in (-1, 1):
        ridge = (z - (hip + .085 - 1.1 * (ax - .1) ** 2 * 4))
        h += .007 * np.exp(-((ridge / .012) ** 2)) * _smooth(.05, .1, ax) * (x * sign > 0) * torso * front
    # The tendons of the neck, from behind the ears down to the breastbone.
    for sign in (-1, 1):
        t = np.clip((z - (neck - .02)) / .1, 0, 1)
        line_x = sign * (.012 + .03 * t)
        h += .005 * np.exp(-(((x - line_x) / .007) ** 2)) * _smooth(neck - .025, neck, z) * front
    # Slack, crepey skin.
    h += _noise(co, rng, (.018, .009), (.00075, .00035))
    return h


def bake_skin(coll, body, rig, name, rng, size=2048):
    """Starved skin: a sculpted, subdivided copy of the body is baked back onto it as a
    normal map and a colour map (grey-brown dead skin, lividity pooled in the hands and
    feet, earth on the soles, occlusion deep in the ribs)."""
    me = body.data
    torso = np.zeros(len(me.vertices))
    limbs = ('upperarm', 'lowerarm', 'wrist', 'shoulder', 'upperleg', 'lowerleg', 'foot')
    ids = {g.index: g.name for g in body.vertex_groups}
    for v in me.vertices:
        limb = sum(ge.weight for ge in v.groups if ids[ge.group].startswith(limbs))
        torso[v.index] = 1 - min(1, limb)
    attr = me.attributes.new('torso', 'FLOAT', 'POINT')
    attr.data.foreach_set('value', torso.astype(np.float32))

    high = body.copy()
    high.data = me.copy()
    high.name = name + '_high'
    coll.objects.link(high)
    for mod in list(high.modifiers):
        high.modifiers.remove(mod)
    high.vertex_groups.clear()
    sub = high.modifiers.new('sub', 'SUBSURF')
    sub.levels = 2
    bpy.context.view_layer.objects.active = high
    bpy.ops.object.modifier_apply(modifier=sub.name)
    hm = high.data
    n = len(hm.vertices)
    co = np.empty(n * 3)
    hm.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    normal = np.empty(n * 3)
    hm.vertex_normals.foreach_get('vector', normal)
    normal = normal.reshape(-1, 3)
    t = np.empty(n, np.float32)
    hm.attributes['torso'].data.foreach_get('value', t)
    height = _sculpt_height(co, t, _landmarks(rig), rng)
    hm.vertices.foreach_set('co', (co + normal * height[:, None]).ravel())
    hm.update()
    for p in hm.polygons:
        p.use_smooth = True

    # Occlusion, baked into the sculpt's own vertices: the shadows deep between the ribs
    # must stay dark even under a flat lantern.
    sc = bpy.context.scene
    engine = sc.render.engine
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 16
    hm.materials.clear()
    hm.materials.append(bpy.data.materials.new(name + '_blank'))
    occl = hm.color_attributes.new('occlusion', 'FLOAT_COLOR', 'POINT')
    hm.color_attributes.active_color = occl
    body.hide_render = True
    for o in bpy.context.selected_objects:
        o.select_set(False)
    high.select_set(True)
    bpy.context.view_layer.objects.active = high
    sc.render.bake.use_selected_to_active = False
    sc.render.bake.target = 'VERTEX_COLORS'
    bpy.ops.object.bake(type='AO')
    sc.render.bake.target = 'IMAGE_TEXTURES'
    body.hide_render = False
    ao = np.empty(n * 4, np.float32)
    occl.data.foreach_get('color', ao)
    ao = ao[0::4]
    print('Kmaoch occlusion mean', round(float(ao.mean()), 3), flush=True)

    # Colour: the MakeHuman skin map greyed down, multiplied by what death does to it, in
    # the scan's face's palette: grey skin going green-black in webs of cracks.
    decay = np.ones((n, 4), np.float32)
    z = co[:, 2]
    blotch = _noise(co, rng, (.17, .06), (.5, .3))
    shade = (1 - .24 * _smooth(-.1, .5, blotch)) * (.3 + .7 * ao ** 1.3)
    livid = 1 - _smooth(.0, .55, z)  # blood settled low, feet and shins
    decay[:, 0] = shade * .8 * (1 - .46 * livid)
    decay[:, 1] = shade * .86 * (1 - .44 * livid)
    decay[:, 2] = shade * .78 * (1 - .4 * livid)
    # The same cracked, green-dark rot as the jaw of the face, in patches.
    web = _noise(co, rng, (.05, .022), (.6, .4))
    patch = _smooth(.05, .4, _noise(co, rng, (.24, .11), (.6, .4)))
    crack = np.exp(-((web / .05) ** 2)) * patch
    decay[:, :3] *= (1 - crack[:, None] * np.array([.62, .5, .56], np.float32))
    green = patch[:, None] * np.array([.22, .1, .16], np.float32)
    decay[:, :3] *= 1 - green
    earth = 1 - _smooth(.02, .16, z + _noise(co, rng, (.05,), (.03,)))
    decay[:, :3] *= (1 - earth[:, None] * np.array([.45, .56, .68], np.float32))
    colour = hm.color_attributes.new('decay', 'FLOAT_COLOR', 'POINT')
    colour.data.foreach_set('color', decay.ravel())

    src = bpy.data.materials.new(name + '_source')
    nt = src.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(MAKEHUMAN / 'old_lightskinned_male_diffuse2.png'), check_existing=True)
    hue = nt.nodes.new('ShaderNodeHueSaturation')
    # Greyed right down, to the scan's own dead colour.
    hue.inputs['Saturation'].default_value = .16
    hue.inputs['Value'].default_value = .86
    nt.links.new(tex.outputs[0], hue.inputs['Color'])
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1
    nt.links.new(hue.outputs[0], mix.inputs[6])
    at = nt.nodes.new('ShaderNodeVertexColor')
    at.layer_name = 'decay'
    nt.links.new(at.outputs[0], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    hm.materials.clear()
    hm.materials.append(src)

    target = bpy.data.materials.new(name)
    me.materials.clear()
    me.materials.append(target)
    tnt = target.node_tree
    node = tnt.nodes.new('ShaderNodeTexImage')
    tnt.nodes.active = node

    sc.render.bake.use_selected_to_active = True
    sc.render.bake.cage_extrusion = .02
    sc.render.bake.max_ray_distance = .05
    sc.render.bake.margin = 6
    for o in bpy.context.selected_objects:
        o.select_set(False)
    high.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    keep = [m for m in body.modifiers]
    for m in keep:
        m.show_render = False
        m.show_viewport = False

    def bake(kind, tag, **extra):
        # Set a generated image's colour space before baking: changing it afterwards
        # throws the baked pixels away.
        img = bpy.data.images.new(f'T_ep2_kmaoch_skin_{tag}', size, size, is_data=tag == 'N')
        node.image = img
        sc.cycles.samples = 1
        bpy.ops.object.bake(type=kind, **extra)
        return img
    colour_img = bake('DIFFUSE', 'BC', pass_filter={'COLOR'})
    normal_img = bake('NORMAL', 'N', normal_space='TANGENT')
    for m in keep:
        m.show_render = True
        m.show_viewport = True
    sc.render.bake.use_selected_to_active = False
    sc.render.engine = engine
    TEXTURES.mkdir(parents=True, exist_ok=True)
    for img, tag in ((colour_img, 'BC'), (normal_img, 'N')):
        img.filepath_raw = str(TEXTURES / f'T_ep2_kmaoch_skin_{tag}.png')
        img.file_format = 'PNG'
        img.save()
        img.pack()
    bpy.data.objects.remove(high, do_unlink=True)
    bpy.data.meshes.remove(hm)
    bpy.data.materials.remove(src)
    me.attributes.remove(me.attributes['torso'])
    # The finished skin material.
    tnt.nodes.remove(node)
    bsdf = tnt.nodes['Principled BSDF']
    bc_node = tnt.nodes.new('ShaderNodeTexImage')
    bc_node.image = colour_img
    tnt.links.new(bc_node.outputs[0], bsdf.inputs['Base Color'])
    n_node = tnt.nodes.new('ShaderNodeTexImage')
    n_node.image = normal_img
    nmap = tnt.nodes.new('ShaderNodeNormalMap')
    tnt.links.new(n_node.outputs[0], nmap.inputs['Color'])
    tnt.links.new(nmap.outputs[0], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = .66
    return target


# ------------------------------------------------------------------ the funeral cloth


def _fbm(rng, shape, scale, octaves=4):
    """Fractal noise in 0..1 from filtered random fields; `scale` is the largest feature
    in pixels."""
    out = np.zeros(shape, np.float32)
    amp, total = 1.0, 0.0
    fy, fx = np.fft.fftfreq(shape[0])[:, None], np.fft.rfftfreq(shape[1])[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    for o in range(octaves):
        s = scale / 2 ** o
        spectrum = np.fft.rfft2(rng.normal(size=shape)) * np.exp(-(radius * s) ** 2)
        field = np.fft.irfft2(spectrum, s=shape).astype(np.float32)
        out += amp * field / (field.std() + 1e-6)
        total += amp
        amp *= .55
    out /= total
    return np.clip(out * .38 + .5, 0, 1)


def _torn_mask(rng, height, width, ends=False):
    """1 where the cloth still exists. v 0 is the hem: eaten back unevenly, with rips
    running up from it, thin worn patches and a few moth holes. `ends` tears the two
    side ends the same way, for a sheet whose ends hang free."""
    v = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    u = np.linspace(0, 1, width, dtype=np.float32)[None, :]
    edge = _fbm(rng, (height, width), 160, 5)
    hem = v - (.03 + .17 * edge + .012 * _fbm(rng, (height, width), 8, 2))
    alive = hem > 0
    # Rips: narrow wedges up from the hem, wandering as they go.
    wander = (_fbm(rng, (height, width), 90, 3) - .5) * .05
    for _ in range(16):
        cu, wide, tall = rng.uniform(0, 1), rng.uniform(.004, .017), rng.uniform(.14, .42)
        alive &= ~((np.abs(u + wander - cu) < wide * np.clip(1 - v / tall, 0, 1)) & (v < tall))
    # Holes: where the cloth is rotten, more of them low down.
    rot = _fbm(rng, (height, width), 26, 4)
    alive &= rot < (.9 - .2 * np.clip(1 - v / .4, 0, 1))
    if ends:
        side = _fbm(rng, (height, width), 150, 5)
        alive &= np.abs(u - .5) * 2 < 1 - (.03 + .15 * side)
        for _ in range(10):
            cv, wide, tall = rng.uniform(0, 1), rng.uniform(.006, .02), rng.uniform(.05, .17)
            d = 1 - (np.abs(u - .5) * 2)  # distance in from the nearest end
            alive &= ~((np.abs(v + wander - cv) < wide * np.clip(1 - d / tall, 0, 1)) & (d < tall))
    # The far edges of the sheet fray a little too.
    fray = _fbm(rng, (height, width), 12, 3) * .006
    alive &= (u > fray) & (u < 1 - fray) & (v < 1 - fray)
    return alive.astype(np.float32)


def _cloth_texture(atlas, rng, size=2048):
    """One sheet of old white funeral cotton: the upper half for the veil, the lower for
    the waist cloth. Its stains and creases are the Pocong scan's own, from a rope-free
    panel of its shroud repeated at the scale it had on the body; the weave is the
    library's rough linen; the hems are earthy and torn (alpha)."""
    half = size // 2
    w, h = atlas.size
    px = np.empty(w * h * 4, np.float32)
    atlas.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[..., :3]
    panel = px[int(h * (1 - .41)):int(h * (1 - .22)), int(w * .445):int(w * .59)]
    panel = np.concatenate([panel, panel[:, ::-1]], 1)
    panel = np.concatenate([panel, panel[::-1]], 0)
    ph, pw = panel.shape[:2]
    yy, xx = np.mgrid[0:half, 0:size]
    # The panel was about 40 cm across on the body; each half here is about 1 m wide.
    tile = (ph * 1.25) / half
    stains = panel[(yy * tile).astype(int) % ph, (xx * tile * 1.0).astype(int) % pw]
    lib = ROOT / 'art-source/library/materials/rough_linen/rough_linen'
    linen = bpy.data.images.load(str(lib) + '_BC.jpg', check_existing=True)
    lw, lh = linen.size
    lp = np.empty(lw * lh * 4, np.float32)
    linen.pixels.foreach_get(lp)
    lp = lp.reshape(lh, lw, 4)[..., :3].mean(-1)
    lp /= lp.mean()
    weave = lp[(yy * 2) % lh, (xx * 2) % lw]
    out = np.zeros((size, size, 4), np.float32)
    white = np.array([.86, .83, .73], np.float32)
    for k in (0, 1):
        s = stains[:, ::-1] if k else stains
        lum = s.mean(-1)
        lum = (lum - lum.mean()) * .26 + .62
        grime = _fbm(rng, (half, size), 240, 4)
        layer = np.clip(lum, 0, 1)[..., None] * white * (1 - .3 * _smooth(.45, .8, grime))[..., None]
        layer *= (.82 + .18 * weave)[..., None]
        # Earth wicking up from the hem, unevenly.
        v = np.linspace(0, 1, half, dtype=np.float32)[:, None]
        wick = 1 - _smooth(.03, .34, v + (grime - .5) * .22)
        layer *= 1 - wick[..., None] * np.array([.5, .6, .72], np.float32)
        out[k * half:(k + 1) * half, :, :3] = layer
        out[k * half:(k + 1) * half, :, 3] = _torn_mask(rng, half, size, ends=k == 1)
    img = bpy.data.images.new('T_ep2_kmaoch_cloth_BC', size, size, alpha=True)
    img.pixels.foreach_set(out.ravel())
    img.filepath_raw = str(TEXTURES / 'T_ep2_kmaoch_cloth_BC.png')
    img.file_format = 'PNG'
    img.save()
    img.pack()
    # The weave's relief, at the same scale.
    src = bpy.data.images.load(str(lib) + '_N.jpg', check_existing=True)
    src.colorspace_settings.name = 'Non-Color'
    nw, nh = src.size
    np_ = np.empty(nw * nh * 4, np.float32)
    src.pixels.foreach_get(np_)
    np_ = np_.reshape(nh, nw, 4)
    yy, xx = np.mgrid[0:size, 0:size]
    tiled = np_[(yy * 2) % nh, (xx * 2) % nw]
    normal = bpy.data.images.new('T_ep2_kmaoch_cloth_N', size, size, is_data=True)
    normal.pixels.foreach_set(tiled.ravel())
    normal.filepath_raw = str(TEXTURES / 'T_ep2_kmaoch_cloth_N.png')
    normal.file_format = 'PNG'
    normal.save()
    normal.pack()
    return img, normal


def cloth_material(atlas, rng):
    mat = bpy.data.materials.new('M_ep2_kmaoch_cloth')
    mat.use_backface_culling = False
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    colour, normal = _cloth_texture(atlas, rng)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = colour
    nt.links.new(tex.outputs[0], bsdf.inputs['Base Color'])
    # The glTF exporter reads Alpha through a Round node as alphaMode MASK.
    rnd = nt.nodes.new('ShaderNodeMath')
    rnd.operation = 'ROUND'
    nt.links.new(tex.outputs['Alpha'], rnd.inputs[0])
    nt.links.new(rnd.outputs[0], bsdf.inputs['Alpha'])
    ntex = nt.nodes.new('ShaderNodeTexImage')
    ntex.image = normal
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(ntex.outputs[0], nmap.inputs['Color'])
    nt.links.new(nmap.outputs[0], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = .95
    return mat


def _sheet(coll, name, positions, uv_rect, mat):
    """A grid mesh from an (ny, nx, 3) array, its UVs filling `uv_rect` (u0, v0, u1, v1)."""
    ny, nx = positions.shape[:2]
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(positions.reshape(-1, 3).tolist(), [], faces)
    me.update()
    uv = me.uv_layers.new(name='UVMap')
    u0, v0, u1, v1 = uv_rect
    for p in me.polygons:
        p.use_smooth = True
        for l in p.loop_indices:
            vi = me.loops[l].vertex_index
            j, i = divmod(vi, nx)
            uv.data[l].uv = (u0 + (u1 - u0) * i / (nx - 1), v0 + (v1 - v0) * j / (ny - 1))
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.materials.append(mat)
    return obj


def _simulate(obj, pins, frames, tension=14, bending=.7):
    g = obj.vertex_groups.new(name='pin')
    g.add(pins, 1.0, 'REPLACE')
    mod = obj.modifiers.new('cloth', 'CLOTH')
    s = mod.settings
    s.quality = 8
    s.mass = .16
    s.air_damping = 1.8
    s.tension_stiffness = tension
    s.compression_stiffness = tension
    s.shear_stiffness = 5
    s.bending_stiffness = bending
    s.vertex_group_mass = 'pin'
    c = mod.collision_settings
    c.use_collision = True
    c.distance_min = .007
    c.collision_quality = 3
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = frames
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.vertex_groups.remove(obj.vertex_groups['pin'])


def _reduce(obj, ratio):
    """Thins the simulated sheet to a game budget, keeping its folds."""
    dec = obj.modifiers.new('budget', 'DECIMATE')
    dec.ratio = ratio
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=dec.name)


def _body_section(body, z, band=.025):
    """Centre and half-widths of the trunk at height `z`: the arms hanging beside it are
    not part of it."""
    ids = {g.index: g.name for g in body.vertex_groups}
    pts = [v.co for v in body.data.vertices if abs(v.co.z - z) < band
           and sum(g.weight for g in v.groups if ids[g.group].startswith(('spine', 'pelvis', 'root'))) > .6]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2


def dress(coll, body, head, rig, mat, rng):
    """Drapes the funeral cloth by simulation: a veil over the head and shoulders, and a
    wrapped waist cloth, open and overlapping at the front. Returns the two sheets."""
    for o in (body, head):
        o.modifiers.new('collide', 'COLLISION')
        o.collision.thickness_outer = .012
        o.collision.cloth_friction = 8
        o.collision.damping = .4
    hv = [v.co for v in head.data.vertices]
    top = max(c.z for c in hv)
    hx = (min(c.x for c in hv) + max(c.x for c in hv)) / 2
    hy = (min(c.y for c in hv) + max(c.y for c in hv)) / 2

    # A skull's dome for the cloth to settle on, there only during the simulation: the
    # scan's hood ends in an open ring, and cloth on a ring lies flat as a lid.
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=1)
    dome_mesh = bpy.data.meshes.new('kmaoch_dome')
    bm.to_mesh(dome_mesh)
    bm.free()
    dome = bpy.data.objects.new('kmaoch_dome', dome_mesh)
    coll.objects.link(dome)
    rx = (max(c.x for c in hv) - min(c.x for c in hv)) / 2 + .006
    ry = (max(c.y for c in hv) - min(c.y for c in hv)) / 2 + .006
    dome.location = (hx, hy + .012, top - .115)
    dome.scale = (rx, ry, .15)
    dome.modifiers.new('collide', 'COLLISION')
    dome.collision.thickness_outer = .008
    dome.collision.cloth_friction = 8
    top = top - .115 + .15  # the cloth starts above the dome
    # The veil: laid across the crown just behind the face, falling behind the head and
    # past the shoulders; its front corners hang down either side of the face.
    W, L = 1.5, 1.25
    nx, ny = 112, 96
    grid = np.zeros((ny, nx, 3))
    crown = .22
    for j in range(ny):
        s = L * j / (ny - 1)
        for i in range(nx):
            x = W * (i / (nx - 1) - .5)
            y0 = hy - .045
            drape = top + .018 - .7 * x * x
            if s < crown:
                grid[j, i] = (hx + x, y0 + s, drape)
            else:
                grid[j, i] = (hx + x, y0 + crown, drape - (s - crown))
    pins = [j * nx + i for j in (0, 1) for i in range(nx) if abs(W * (i / (nx - 1) - .5)) < .04]
    veil = _sheet(coll, 'kmaoch_veil', grid, (0, .5, 1, 1), mat)
    # v runs down the sheet: flip it so the earthy, torn hem is the free end.
    uv = veil.data.uv_layers.active.data
    for l in uv:
        l.uv = (l.uv[0], 1.5 - l.uv[1])
    _simulate(veil, pins, 140, tension=10, bending=.08)
    bpy.data.objects.remove(dome, do_unlink=True)
    bpy.data.meshes.remove(dome_mesh)
    _reduce(veil, .36)

    # The waist cloth: a long strip wrapped once and a bit round the hips, spiralling out
    # so its end overlaps at the front, gathered at the waist and falling to the shins.
    hip = rig.data.bones['upperleg01.L'].head_local.z
    ztop = hip + .085
    cx, cy, rx, ry = _body_section(body, ztop)
    drop = .6
    nx2, ny2 = 132, 46
    grid2 = np.zeros((ny2, nx2, 3))
    start = math.radians(-125)
    wrap = math.tau + .75
    for j in range(ny2):
        h = j / (ny2 - 1)
        for i in range(nx2):
            a = start + wrap * i / (nx2 - 1)
            spiral = .012 * i / (nx2 - 1)
            flare = 1 + .42 * h ** .7
            pleat = .02 * h * math.sin(a * 7 + 1.3) + .012 * h * math.sin(a * 13)
            grid2[j, i] = (cx + (rx + .01 + spiral) * flare * math.cos(a) + pleat * math.cos(a),
                           cy + (ry + .01 + spiral) * flare * math.sin(a) + pleat * math.sin(a),
                           ztop - drop * h)
    pins2 = list(range(nx2))
    wrapper = _sheet(coll, 'kmaoch_wrap', grid2, (0, 0, 1, .5), mat)
    uv = wrapper.data.uv_layers.active.data
    for l in uv:
        l.uv = (l.uv[0], .5 - l.uv[1])
    _simulate(wrapper, pins2, 90, tension=10, bending=.1)
    _reduce(wrapper, .5)
    for o in (body, head):
        o.modifiers.remove(o.modifiers['collide'])
    return veil, wrapper


def thread_bands(coll, rig, body, rng):
    """White cotton thread wound at the wrists and ankles (advisor-review)."""
    mat = bpy.data.materials.new('M_ep2_kmaoch_thread')
    b = mat.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (.27, .25, .2, 1)
    b.inputs['Roughness'].default_value = .95
    from kit import tube
    out = []
    for bone, along in (('wrist.L', -.03), ('wrist.R', -.03), ('lowerleg02.L', .17), ('lowerleg02.R', .17)):
        data = rig.data.bones[bone]
        axis = (Vector(data.tail_local) - Vector(data.head_local)).normalized()
        origin = Vector(data.head_local) + axis * along
        # Tied snug on what is left of the limb.
        near = [(v.co - origin) for v in body.data.vertices if abs((v.co - origin).dot(axis)) < .01 and (v.co - origin).length < .06]
        radii = sorted((d - axis * d.dot(axis)).length for d in near) or [.024]
        radius = radii[int(len(radii) * .8)] + .001
        centre = origin + sum((d - axis * d.dot(axis) for d in near), Vector()) / max(1, len(near))
        u = axis.orthogonal().normalized()
        v = axis.cross(u)
        points = []
        turns = 4 + int(rng.integers(0, 3))
        for k in range(turns * 14):
            t = k / 14 * math.tau
            r = radius + rng.normal(0, .0005)
            p = centre + u * math.cos(t) * r + v * math.sin(t) * r + axis * (k / (turns * 14) * .009 + rng.normal(0, .0006))
            points.append(tuple(p))
        o = tube(f'kmaoch_thread_{bone}', coll, points, .001, mat, sides=4)
        out.append((o, bone))
    return out


def bind(obj, sources, bones, smooth=10):
    """Skins a cloth sheet from the nearest body surface, then smooths the weights along
    the cloth so it stretches instead of tearing where it crosses from bone to bone."""
    me = obj.data
    names = list(bones)
    index = {n: i for i, n in enumerate(names)}
    w = np.zeros((len(me.vertices), len(names)), np.float32)
    data = []
    for src in sources:
        ids = {g.index: g.name for g in src.vertex_groups}
        table = [[(index[ids[g.group]], g.weight) for g in v.groups if ids[g.group] in index] for v in src.data.vertices]
        data.append((src, table))
    for v in me.vertices:
        best = None
        for src, table in data:
            ok, loc, _n, poly = src.closest_point_on_mesh(v.co)
            if ok:
                d = (loc - v.co).length
                if best is None or d < best[0]:
                    best = (d, src, table, loc, poly)
        _, src, table, loc, poly = best
        verts = src.data.polygons[poly].vertices
        total = 0
        for vi in verts:
            k = 1 / (1e-4 + (src.data.vertices[vi].co - loc).length)
            total += k
            for bi, wt in table[vi]:
                w[v.index, bi] += k * wt
        w[v.index] /= max(total, 1e-6)
    edges = np.array([e.vertices[:] for e in me.edges])
    for _ in range(smooth):
        acc = np.zeros_like(w)
        cnt = np.zeros((len(w), 1), np.float32)
        np.add.at(acc, edges[:, 0], w[edges[:, 1]])
        np.add.at(acc, edges[:, 1], w[edges[:, 0]])
        np.add.at(cnt, edges[:, 0], 1)
        np.add.at(cnt, edges[:, 1], 1)
        w = w * .4 + acc / np.maximum(cnt, 1) * .6
    for n in names:
        obj.vertex_groups.new(name=n)
    for i in range(len(me.vertices)):
        top = np.argsort(-w[i])[:4]
        total = float(w[i, top].sum()) or 1.0
        for k in top:
            if w[i, k] > 1e-3:
                obj.vertex_groups[names[k]].add([i], float(w[i, k]) / total, 'REPLACE')
    mod = obj.modifiers.new('rig', 'ARMATURE')
    return mod


def build(coll, name='kmaoch'):
    """The whole figure in its rest pose. Returns (rig, [mesh objects])."""
    rng = np.random.default_rng(1910)
    body, rig = build_body(coll, name + '_body')
    head = graft_head(coll, body, rig)
    atlas = next(n.image for n in head.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE' and n.image.colorspace_settings.name == 'sRGB')
    blind_eyes(atlas)
    head.data.materials[0].name = 'M_ep2_kmaoch_head'
    bake_skin(coll, body, rig, 'M_ep2_kmaoch_skin', rng)
    mat = cloth_material(atlas, rng)
    veil, wrapper = dress(coll, body, head, rig, mat, rng)
    bones = list(KEEP)
    for sheet, sources in ((veil, (body, head)), (wrapper, (body,))):
        mod = bind(sheet, sources, bones)
        mod.object = rig
    threads = thread_bands(coll, rig, body, rng)
    for o, bone in threads:
        o.vertex_groups.new(name=bone).add([v.index for v in o.data.vertices], 1.0, 'REPLACE')
        o.modifiers.new('rig', 'ARMATURE').object = rig
    parts = [body, head, veil, wrapper] + [o for o, _ in threads]
    for o in parts:
        print('Kmaoch part', o.name, len(o.data.polygons), 'faces', flush=True)
    return rig, parts
