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

import bmesh
import bpy
import numpy as np
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


def hair_material():
    """Long matted hair, wet with rain: dark strands with ragged, see-through tips. The
    strand map is drawn here (no photo hair hangs this long in the library)."""
    rng = np.random.default_rng(1932)
    # Eight card columns (one per strand card's UVs), each a wet hank: some 400 fine
    # strands per hank, gathered into clumps that pinch together towards their tips, as
    # soaked hair does. Strands are antialiased and taper; tips are ragged and see-through.
    w, h = 1024, 2048
    alpha = np.zeros(h * w)
    shade = np.zeros(h * w)
    ys = np.arange(h)
    for column in range(8):
        x0 = column * w / 8
        clumps = rng.uniform(x0 + 12, x0 + w / 8 - 12, rng.integers(3, 6))
        for _ in range(170):
            centre = rng.choice(clumps)
            x = centre + rng.normal(0, 14)
            end = rng.uniform(.5, 1.) * h
            pinch = rng.uniform(.4, .95)
            wave = rng.uniform(0, 6.28)
            t = np.clip(ys / end, 0, 1)
            xs = x + (centre - x) * pinch * t ** 1.5 + 1.2 * np.sin(ys / rng.uniform(30, 70) + wave)
            xs = np.clip(xs, x0 + 1, x0 + w / 8 - 2)
            width = rng.uniform(.35, .8) * (1 - .55 * t)
            fade = np.clip((end - ys) / 90, 0, 1) * (ys < end)
            tone = rng.uniform(.3, 1.)
            for off in (-1, 0, 1, 2):
                px = np.floor(xs).astype(int) + off
                cover = np.clip(width + .5 - np.abs(px + .5 - xs), 0, 1) * fade
                idx = ys * w + np.clip(px, 0, w - 1)
                np.maximum.at(alpha, idx, cover)
                np.maximum.at(shade, idx, cover * tone)
    alpha = alpha.reshape(h, w)
    shade = (shade.reshape(h, w) / np.maximum(alpha, 1e-3)) * (alpha > 0) + .5 * (alpha <= 0)
    rgb = np.stack([shade * .05, shade * .045, shade * .04], -1)
    img = bpy.data.images.new('T_neakta_matted_hair', w, h, alpha=True)
    img.pixels.foreach_set(np.concatenate([rgb, alpha[..., None]], -1)[::-1].astype(np.float32).ravel())
    img.pack()
    m = A.material('M_neakta_matted_hair', (1, 1, 1), .38)
    n, l = m.node_tree.nodes, m.node_tree.links
    p = n['Principled BSDF']
    t = n.new('ShaderNodeTexImage'); t.image = img
    l.new(t.outputs['Color'], p.inputs['Base Color'])
    cut = n.new('ShaderNodeMath'); cut.operation = 'GREATER_THAN'; cut.inputs[1].default_value = .3
    l.new(t.outputs['Alpha'], cut.inputs[0]); l.new(cut.outputs[0], p.inputs['Alpha'])
    m.use_backface_culling = False
    return m


def matted_hair(body, eyes):
    """Clumps of long wet hair hanging from the scalp to the chest, some of it down over
    the face. Strand cards, carried rigidly by the head bone like the eyes."""
    rng = np.random.default_rng(73)
    mid = (eyes[0] + eyes[1]) / 2
    head = [v.co for v in body.data.vertices if v.co.z > mid.z - .02 and (v.co - mid).length < .25]
    top = max(c.z for c in head)
    radius = (top - mid.z) * 1.05
    # The skull's centre: behind the eyes (the figure faces -Y) and a little above them.
    centre = mid + Vector((0, radius * .78, radius * .15))
    mat = hair_material()
    verts, faces, uvs = [], [], []
    r = radius * 1.05

    def on_skull(azimuth, elevation, lift=1.):
        # The figure faces -Y: azimuth 0 is straight ahead.
        return centre + Vector((math.sin(azimuth) * math.cos(elevation), -math.cos(azimuth) * math.cos(elevation),
                                math.sin(elevation))) * r * lift
    for k in range(620):
        azimuth = rng.uniform(-math.pi, math.pi)
        front = abs(azimuth) < .9
        # Over the face only a few thin hanks; most of it falls behind and to the sides.
        if front and rng.random() < .65:
            azimuth = math.copysign(rng.uniform(.9, 1.6), azimuth)
            front = False
        start = rng.uniform(.95, 1.45)
        end = rng.uniform(.05, .25) if front else rng.uniform(-.45, -.15)
        hang = rng.uniform(.14, .26) if front else rng.uniform(.3, .58)
        width = rng.uniform(.015, .03) * (.7 if front else 1)
        lift = rng.uniform(1.0, 1.07)
        path = [on_skull(azimuth + rng.normal(0, .03), start + (end - start) * i / 6, lift + .02 * i / 6) for i in range(7)]
        foot = path[-1]
        out = Vector((foot.x - centre.x, foot.y - centre.y, 0)).normalized()
        for i in range(1, 8):
            t = i / 7
            path.append(foot + out * (.02 * t if not front else .03) + Vector((0, 0, -hang * t))
                        + Vector((rng.normal(0, .005), rng.normal(0, .005), 0)))
        across = Vector((math.cos(azimuth), math.sin(azimuth), 0))
        base = len(verts)
        for i, p in enumerate(path):
            t = i / (len(path) - 1)
            half = across * width * (1 - .6 * t) / 2
            verts += [p - half, p + half]
            uvs += [(k % 8 / 8, 1 - t * .95), ((k % 8 + 1) / 8, 1 - t * .95)]
            if i < len(path) - 1:
                a = base + i * 2
                faces.append((a, a + 1, a + 3, a + 2))
    data = bpy.data.meshes.new(f'{NAME}_hair')
    data.from_pydata([tuple(v) for v in verts], [], faces)
    layer = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[data.loops[li].vertex_index]
    data.materials.append(mat)
    o = bpy.data.objects.new(f'{NAME}_hair', data)
    bpy.context.collection.objects.link(o)
    return o


SCAN = ROOT / 'art-source/library/scans/neakta_body_scan.glb'


def aim(rig, name, child, target):
    """Turns a pose bone about its head so its child joint lies on the line to `target`."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[name]
    head = rig.matrix_world @ pb.head
    cur = rig.matrix_world @ rig.pose.bones[child].head - head
    want = Vector(target) - head
    axis, angle = cur.rotation_difference(want).to_axis_angle()
    inv = rig.matrix_world.inverted().to_3x3()
    R = Matrix.Rotation(angle, 4, (inv @ axis).normalized())
    pb.matrix = Matrix.Translation(pb.head) @ R @ Matrix.Translation(-pb.head) @ pb.matrix
    bpy.context.view_layer.update()


def scanned_body(body, rig, cloth):
    """A real photoscanned man in place of the sculpted body: fitted to the sculpt's height,
    his right side (hidden in the scan under a title belt) rebuilt from his left, the
    shorts the sarong hides taken away, the arms of the skeleton brought down to his, and
    the sculpt's skin weights carried over onto him. Returns the scan; the sculpt goes."""
    from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
    if get_gltf_node_name() not in bpy.data.node_groups:
        create_settings_group(get_gltf_node_name())
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(SCAN))
    scan = next(o for o in bpy.data.objects if o not in before and o.type == 'MESH')
    for o in [o for o in bpy.data.objects if o not in before and o != scan]:
        bpy.data.objects.remove(o)
    scan.data.transform(scan.matrix_world)
    scan.matrix_world = Matrix.Identity(4)
    # His height and stance on the sculpt's.
    H = max(v.co.z for v in body.data.vertices)
    floor = min(v.co.z for v in body.data.vertices)
    top = max(v.co.z for v in scan.data.vertices)
    low = min(v.co.z for v in scan.data.vertices)
    scan.data.transform(Matrix.Translation((0, 0, floor)) @ Matrix.Scale((H - floor) / (top - low), 4)
                        @ Matrix.Translation((0, 0, -low)))
    head = [v.co for v in scan.data.vertices if v.co.z > floor + .9 * (H - floor)]
    cx = sum(c.x for c in head) / len(head)
    cy = sum(c.y for c in head) / len(head)
    bx = sum(v.co.x for v in body.data.vertices if v.co.z > floor + .9 * (H - floor)) / max(1, len(head))
    sculpt_head = [v.co for v in body.data.vertices if v.co.z > floor + .9 * (H - floor)]
    bx = sum(c.x for c in sculpt_head) / len(sculpt_head)
    by = sum(c.y for c in sculpt_head) / len(sculpt_head)
    scan.data.transform(Matrix.Translation((bx - cx, by - cy, 0)))
    cx, h = bx, H - floor
    sarong = next((p for p in cloth if 'sarong' in p.name), None)
    waist = max(v.co.z for v in sarong.data.vertices) if sarong else floor + .58 * h
    hem = min(v.co.z for v in sarong.data.vertices) if sarong else floor + .1 * h
    neck = floor + .845 * h
    arm = .105 * h

    def mirrored(c, side):
        # On `side` of him, above the sarong or out along an arm, and below the neck.
        return side * (c.x - cx) > 0 and c.z < neck and (c.z > waist - .02 or side * (c.x - cx) > arm)
    bm = bmesh.new()
    bm.from_mesh(scan.data)
    # The left (+X, facing -Y) is whole; rebuild the right from it.
    source = [f for f in bm.faces if mirrored(f.calc_center_median(), 1)]
    doomed = [f for f in bm.faces if mirrored(f.calc_center_median(), -1)
              or (hem + .03 < f.calc_center_median().z < waist - .01)]
    copy = bmesh.ops.duplicate(bm, geom=source)
    new_verts = [g for g in copy['geom'] if isinstance(g, bmesh.types.BMVert)]
    new_faces = [g for g in copy['geom'] if isinstance(g, bmesh.types.BMFace)]
    for v in new_verts:
        v.co.x = 2 * cx - v.co.x
    bmesh.ops.reverse_faces(bm, faces=new_faces)
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    seam = [v for v in bm.verts if abs(v.co.x - cx) < .02 and v.is_valid]
    bmesh.ops.remove_doubles(bm, verts=seam, dist=.012)
    bm.to_mesh(scan.data)
    bm.free()
    scan.data.update()
    # The scan's own split normals were copied, not mirrored, onto the rebuilt side: they
    # shaded that arm and flank in hard facets. Plain smooth normals from the surface itself.
    bpy.context.view_layer.objects.active = scan
    with bpy.context.temp_override(object=scan, active_object=scan):
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    # The skeleton's arms brought down from the sculpt's spread rest to hang as his do.
    for side, sign in (('L', 1), ('R', -1)):
        pts = [v.co for v in scan.data.vertices if sign * (v.co.x - cx) > arm * 1.15]
        def band(z, width=.02 * h):
            near = [c for c in pts if abs(c.z - z) < width]
            return sum(near, Vector()) / len(near) if near else None
        elbow = band(floor + .62 * h)
        wrist = band(floor + .485 * h)
        if elbow and wrist:
            aim(rig, f'upperarm01.{side}', f'lowerarm01.{side}', elbow)
            aim(rig, f'lowerarm01.{side}', f'wrist.{side}', wrist)
    pose = body.modifiers.new('to_scan_pose', 'ARMATURE')
    pose.object = rig
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=pose.name)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    # The sculpt's skin weights onto him, nearest surface to nearest surface.
    for g in body.vertex_groups:
        scan.vertex_groups.new(name=g.name)
    bpy.context.view_layer.objects.active = scan
    transfer = scan.modifiers.new('weights_from_sculpt', 'DATA_TRANSFER')
    transfer.object = body
    transfer.use_vert_data = True
    transfer.data_types_verts = {'VGROUP_WEIGHTS'}
    transfer.vert_mapping = 'POLYINTERP_NEAREST'
    transfer.layers_vgroup_select_src = 'ALL'
    transfer.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.modifier_apply(modifier=transfer.name)
    # The sarong a little fuller, so his hips never show through it.
    if sarong:
        c = sum((v.co for v in sarong.data.vertices), Vector()) / len(sarong.data.vertices)
        for v in sarong.data.vertices:
            v.co.x = c.x + (v.co.x - c.x) * 1.08
            v.co.y = c.y + (v.co.y - c.y) * 1.1
    # The cloth over his chest and waist follows his own body, not the sculpt's.
    for part in cloth:
        if 'sarong' in part.name:
            continue
        wrap = part.modifiers.new('onto_scan', 'SHRINKWRAP')
        wrap.target = scan
        wrap.wrap_mode = 'OUTSIDE_SURFACE'
        wrap.offset = .006
        bpy.context.view_layer.objects.active = part
        bpy.ops.object.modifier_apply(modifier=wrap.name)
    old = bpy.data.materials.get('M_neakta_worn_skin')
    if old and old != scan.data.materials[0]:
        old.name = '_sculpt_skin'
    scan.data.materials[0].name = 'M_neakta_worn_skin'
    for poly in scan.data.polygons:
        poly.use_smooth = True
    scan.name = scan.data.name = f'{NAME}_body'
    # The sculpt stays hidden until the cloth has taken its weights from it: the scan has
    # no thighs under the sarong to give them.
    body.hide_render = True
    body.name = '_sculpt_weights'
    print('SCAN body', len(scan.data.polygons), 'faces; sarong', round(hem, 3), '-', round(waist, 3), flush=True)
    return scan


def soot_skin(scan):
    """Its skin from the photoscan's own photo, so every pore, vein, crease and muscle edge
    stays: graded to a deep soot-dark brown, dusted with ash in patches, mud dried in runs
    down the shins and feet, and rain running wet in streaks (the roughness map). The
    photo's fine detail is also baked into relief. 4096 px colour, 2048 relief, 1024 gloss."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 2
    old = scan.data.materials[0]
    photo = next(n.image for n in old.node_tree.nodes if n.type == 'TEX_IMAGE')
    lo = min(v.co.z for v in scan.data.vertices)
    hi = max(v.co.z for v in scan.data.vertices)
    m = bpy.data.materials.new('_soot_bake')
    m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    p = n['Principled BSDF']

    def node(kind, **inputs):
        x = n.new(kind)
        for k, v in inputs.items():
            if k.startswith('_'):
                setattr(x, k[1:], v)
            else:
                x.inputs[k].default_value = v
        return x

    def math(op, a, b=None, clamp=False):
        x = node('ShaderNodeMath', _operation=op, _use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                x.inputs[i].default_value = v
            else:
                l.new(v, x.inputs[i])
        return x.outputs[0]

    tex = node('ShaderNodeTexImage', _image=photo)
    lum = node('ShaderNodeRGBToBW')
    l.new(tex.outputs['Color'], lum.inputs[0])
    coord = node('ShaderNodeTexCoord').outputs['Object']
    height = node('ShaderNodeSeparateXYZ')
    l.new(coord, height.inputs[0])
    up = math('DIVIDE', math('SUBTRACT', height.outputs['Z'], lo), hi - lo)   # 0 at the feet, 1 at the crown
    # Deep soot-brown skin: the photo's light and shade kept, a little steeper.
    detail = math('POWER', math('DIVIDE', lum.outputs[0], .32), 1.25)
    skin = node('ShaderNodeMix', _data_type='RGBA', _blend_type='MULTIPLY', Factor=1)
    skin.inputs[6].default_value = (.055, .037, .029, 1)
    l.new(math('MINIMUM', detail, 2.2), skin.inputs[7])
    # Ash dusted on in patches (dry, grey, rough).
    ash_noise = node('ShaderNodeTexNoise', Scale=5.5, Detail=12, Roughness=.62)
    l.new(coord, ash_noise.inputs['Vector'])
    ash = math('MULTIPLY', math('SUBTRACT', ash_noise.outputs['Fac'], .5), 4.5, clamp=True)
    ash_col = node('ShaderNodeMix', _data_type='RGBA', _blend_type='MULTIPLY', Factor=1)
    ash_col.inputs[6].default_value = (.08, .075, .07, 1)
    l.new(math('MINIMUM', detail, 1.6), ash_col.inputs[7])
    c1 = node('ShaderNodeMix', _data_type='RGBA')
    l.new(math('MULTIPLY', ash, .7), c1.inputs['Factor'])
    l.new(skin.outputs[2], c1.inputs[6])
    l.new(ash_col.outputs[2], c1.inputs[7])
    # Mud dried in runs down from the knees, thickest at the feet.
    stretch = node('ShaderNodeMapping')
    stretch.inputs['Scale'].default_value = (22, 22, 2.2)
    l.new(coord, stretch.inputs['Vector'])
    runs = node('ShaderNodeTexNoise', Scale=1.0, Detail=6, Roughness=.55)
    l.new(stretch.outputs[0], runs.inputs['Vector'])
    low = math('SUBTRACT', 1, math('DIVIDE', up, .32), clamp=True)
    mud = math('MULTIPLY', math('MULTIPLY', math('SUBTRACT', runs.outputs['Fac'], .42), 3.5, clamp=True), low)
    c2 = node('ShaderNodeMix', _data_type='RGBA')
    l.new(math('MINIMUM', math('ADD', mud, math('MULTIPLY', low, low)), .9), c2.inputs['Factor'])
    l.new(c1.outputs[2], c2.inputs[6])
    c2.inputs[7].default_value = (.055, .036, .02, 1)
    l.new(c2.outputs[2], p.inputs['Base Color'])
    # Rain running down it: wet streaks from the shoulders down, dry where the ash lies.
    wet_map = node('ShaderNodeMapping')
    wet_map.inputs['Scale'].default_value = (40, 40, 3)
    wet_map.inputs['Location'].default_value = (3.1, 1.7, 0)
    l.new(coord, wet_map.inputs['Vector'])
    wet_noise = node('ShaderNodeTexNoise', Scale=1.0, Detail=4)
    l.new(wet_map.outputs[0], wet_noise.inputs['Vector'])
    wet = math('MULTIPLY', math('SUBTRACT', wet_noise.outputs['Fac'], .45), 4, clamp=True)
    rough = math('ADD', math('SUBTRACT', .72, math('MULTIPLY', wet, .16)), math('MULTIPLY', ash, .2))
    l.new(math('ADD', rough, math('MULTIPLY', mud, .25)), p.inputs['Roughness'])
    # Relief laid on in the body's own space, so it runs unbroken across the photo's
    # hundreds of UV islands (a bump from the photo itself creased along every one of them):
    # fine wrinkles and creases, then pores.
    creases = node('ShaderNodeTexNoise', Scale=140, Detail=6, Roughness=.6)
    l.new(coord, creases.inputs['Vector'])
    pores = node('ShaderNodeTexVoronoi', Scale=900)
    l.new(coord, pores.inputs['Vector'])
    bump_creases = node('ShaderNodeBump', Strength=.18, Distance=.0012)
    l.new(creases.outputs['Fac'], bump_creases.inputs['Height'])
    bump_pores = node('ShaderNodeBump', Strength=.12, Distance=.0006)
    l.new(pores.outputs['Distance'], bump_pores.inputs['Height'])
    l.new(bump_creases.outputs[0], bump_pores.inputs['Normal'])
    l.new(bump_pores.outputs[0], p.inputs['Normal'])
    scan.data.materials[0] = m
    target = node('ShaderNodeTexImage')
    n.active = target
    images = {}
    for kind, size, colour in (('DIFFUSE', 4096, True), ('NORMAL', 2048, False), ('ROUGHNESS', 1024, False)):
        img = bpy.data.images.new(f'T_neakta_skin_{kind[0]}', size, size)
        if not colour:
            img.colorspace_settings.name = 'Non-Color'
        target.image = img
        bpy.ops.object.select_all(action='DESELECT')
        scan.select_set(True)
        bpy.context.view_layer.objects.active = scan
        bake = sc.render.bake
        bake.use_selected_to_active = False
        bake.margin = 6
        bake.use_pass_direct = bake.use_pass_indirect = False
        bake.use_pass_color = True
        bpy.ops.object.bake(type=kind)
        img.pack()
        images[kind] = img
        print('SOOT baked', kind, flush=True)
    # The glTF material: baked colour, relief and gloss.
    final = bpy.data.materials.new('M_neakta_worn_skin')
    final.use_nodes = True
    fn, fl = final.node_tree.nodes, final.node_tree.links
    fp = fn['Principled BSDF']
    bc = fn.new('ShaderNodeTexImage'); bc.image = images['DIFFUSE']
    fl.new(bc.outputs['Color'], fp.inputs['Base Color'])
    nm = fn.new('ShaderNodeTexImage'); nm.image = images['NORMAL']
    nmap = fn.new('ShaderNodeNormalMap')
    fl.new(nm.outputs['Color'], nmap.inputs['Color']); fl.new(nmap.outputs[0], fp.inputs['Normal'])
    rm = fn.new('ShaderNodeTexImage'); rm.image = images['ROUGHNESS']
    rs = fn.new('ShaderNodeSeparateColor')
    fl.new(rm.outputs['Color'], rs.inputs[0]); fl.new(rs.outputs[1], fp.inputs['Roughness'])
    fp.inputs['Metallic'].default_value = 0
    if old.name == 'M_neakta_worn_skin':
        old.name = '_scan_photo'
    final.name = 'M_neakta_worn_skin'
    scan.data.materials[0] = final


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
    cloth = []
    for part in A.clothing(body, False, 0):
        if part.name.startswith('_'):
            bpy.data.objects.remove(part, do_unlink=True)
            continue
        cloth.append(part)
    # A real man's body, photoscanned, in place of the sculpt: muscle, bone and skin as
    # they are, darkened by the game to soot-black.
    sculpt = body
    body = scanned_body(body, rig, cloth)
    soot_skin(body)
    parts = [body, *cloth]
    # His own eyes are in the scan; the matted hair is carried by the head bone.
    gaze = []
    gaze.append(matted_hair(body, eyes))

    # Into the game's size: everything, skeleton included, scaled about the feet.
    height = max(v.co.z for v in body.data.vertices)
    factor = HEIGHT / height
    for o in [rig, sculpt, *parts, *gaze]:
        o.matrix_world = Matrix.Scale(factor, 4) @ o.matrix_world
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig, sculpt, *parts, *gaze]:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    deform = body.modifiers.new('Armature', 'ARMATURE')
    deform.object = rig
    deform.use_deform_preserve_volume = True
    body.parent = rig
    for part in parts[1:]:
        skin_from(sculpt, rig, part)
        # The arms hang beside the sarong in his rest: it must not lift when they reach.
        # (The sash keeps its shoulder, but not the forearm and hand beside its end.)
        arm_bones = ('lowerarm', 'wrist', 'finger', 'metacarpal')
        if 'sash' not in part.name:
            arm_bones += ('upperarm', 'clavicle', 'shoulder')
        for g in [g for g in part.vertex_groups if g.name.startswith(arm_bones)]:
            part.vertex_groups.remove(g)
    bpy.data.objects.remove(sculpt)
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
