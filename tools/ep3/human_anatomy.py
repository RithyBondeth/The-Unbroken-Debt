"""Episode 3 actors: shared anatomical rig, true child targets and complete eyes.

Reuse the project anatomy function without running the Ep2 scene builder. The
child target choice is an AST substitution, not a second divergent rig builder.
"""
import ast
import json
import math
from functools import lru_cache
from pathlib import Path

import bpy
import numpy as np
from mathutils import Quaternion, Vector
from kit import ROOT, image_material, library_material, plain


@lru_cache(maxsize=2)
def source_topology(old):
    source = Path(ROOT)/('art-source/library/makehuman-sok' if old else 'art-source/library/makehuman-sora')
    faces, face_uv, uv = [], [], []
    group = ''
    for line in (source/'base.obj').read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'g':
            group = parts[1]
        elif parts[0] == 'vt':
            uv.append(tuple(map(float, parts[1:3])))
        elif parts[0] == 'f' and group == 'body':
            indices = [p.split('/') for p in parts[1:]]
            faces.append([int(p[0])-1 for p in indices])
            face_uv.append([int(p[1])-1 for p in indices])
    used = sorted({i for face in faces for i in face})
    remap = {original:index for index,original in enumerate(used)}
    regions = {}
    for name, weights in json.loads((source/'default_weights.mhw').read_text())['weights'].items():
        for index, weight in weights:
            if index in remap and weight > regions.get(remap[index], ('', 0))[1]:
                regions[remap[index]] = name, weight
    return [[remap[i] for i in face] for face in faces], face_uv, uv, regions


def classify_clothes(body, old):
    _, _, _, regions = source_topology(old)
    for poly in body.data.polygons:
        names = [regions.get(i, ('', 0))[0] for i in poly.vertices]
        shirt = sum(n.startswith(('spine', 'pelvis', 'root', 'upperarm', 'breast', 'clavicle', 'shoulder', 'scapula')) for n in names)
        leg = sum(n.startswith(('upperleg', 'lowerleg')) for n in names)
        poly.material_index = 2 if leg > len(names)/2 else 1 if shirt > len(names)/2 else 0


def restore_topology(body):
    """Restore source faces on retained indexed vertices, without rerunning IK."""
    old = bool(body.get('ep3_old'))
    faces, face_uv, uv, _ = source_topology(old)
    source = body.data
    poses = [(key.name, [v.co.copy() for v in key.data]) for key in source.shape_keys.key_blocks]
    data = bpy.data.meshes.new(body.name+'_full_anatomy')
    data.from_pydata([v.co[:] for v in source.vertices], [], faces)
    for material in source.materials:
        data.materials.append(material)
    layer = data.uv_layers.new(name='MakeHumanUV')
    for poly, indices in zip(data.polygons, face_uv):
        poly.use_smooth = True
        for loop, index in zip(poly.loop_indices, indices):
            layer.data[loop].uv = uv[index]
    body.data = data
    for name, points in poses:
        key = body.shape_key_add(name=name, from_mix=False)
        key.value = 0
        key.data.foreach_set('co', np.asarray(points, dtype=np.float32).ravel())
    data.update()
    classify_clothes(body, old)
    body['ep3_finished_human'] = False


def source_function(child):
    path = Path(ROOT)/'tools/ep2/build-cinematics.py'
    tree = ast.parse(path.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'anatomy')
    if child:
        for node in ast.walk(function):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'targets' for t in node.targets):
                node.value = ast.List(elts=[ast.Constant(str(Path(ROOT)/'art-source/library/makehuman-ep3'/name)) for name in ['asian-male-child.target', 'universal-male-child-averagemuscle-averageweight.target']], ctx=ast.Load())
    return ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))


def build_body(collection, name, old=False, child=False):
    namespace = dict(ROOT=Path(ROOT), COL=collection, bpy=bpy, json=json, math=math,
                     Vector=Vector, Quaternion=Quaternion, image_material=image_material,
                     library_material=library_material, plain=plain)
    exec(compile(source_function(child), 'shared_actor_anatomy', 'exec'), namespace)
    body = namespace['anatomy'](name, old=old)
    body['ep3_anatomy_version'] = 2
    body['ep3_child_proportions'] = child
    body['ep3_actor_source'] = 'MakeHuman male child' if child else 'MakeHuman older male' if old else 'MakeHuman adult female'
    body['ep3_old'] = old
    classify_clothes(body, old)
    add_eyes(collection, body, old, child)
    return body


def eye_centres(old, child):
    source = Path(ROOT)/('art-source/library/makehuman-sok' if old else 'art-source/library/makehuman-sora')
    verts = [Vector(map(float, line.split()[1:4])) for line in (source/'base.obj').read_text().splitlines() if line.startswith('v ')]
    if child:
        targets = [Path(ROOT)/'art-source/library/makehuman-ep3'/n for n in ['asian-male-child.target', 'universal-male-child-averagemuscle-averageweight.target']]
    else:
        targets = [source/n for n in (['asian-male-old.target','universal-male-old-minmuscle-averageweight.target'] if old else ['asian-female-young.target','universal-female-young-averagemuscle-averageweight.target'])]
    for path in targets:
        for line in path.read_text().splitlines():
            if line and not line.startswith('#'):
                parts = line.split()
                verts[int(parts[0])] += Vector(map(float, parts[1:4]))
    skeleton = json.loads((source/'default.mhskel').read_text())
    # Only the body determines the contact plane; helper shapes extend below it.
    group = ''
    used = set()
    for line in (source/'base.obj').read_text().splitlines():
        parts = line.split()
        if parts and parts[0] == 'g': group = parts[1]
        elif parts and parts[0] == 'f' and group == 'body': used.update(int(v.split('/')[0])-1 for v in parts[1:])
    floor = min(verts[i].y for i in used)
    result = []
    for side in ['L', 'R']:
        joint = skeleton['joints'][skeleton['bones']['eye.'+side]['head']]
        p = sum((verts[i] for i in joint), Vector())/len(joint)
        result.append(Vector((p.x*.1, -p.z*.1, (p.y-floor)*.1)))
    return result


def add_eyes(collection, body, old, child):
    centres = eye_centres(old, child)
    sclera = bpy.data.materials.get('M_ep3_eyeball') or plain('M_ep3_eyeball', (.32,.29,.23), rough=.27)
    iris = bpy.data.materials.get('M_ep3_iris') or plain('M_ep3_iris', (.025,.013,.006), rough=.21)
    pupil = bpy.data.materials.get('M_ep3_pupil') or plain('M_ep3_pupil', (.001,.001,.0008), rough=.16)
    for mat in [sclera, iris, pupil]:
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Coat Weight'].default_value = .35
        bsdf.inputs['Coat Roughness'].default_value = .12
    h = max(v.co.z for v in body.data.vertices)
    keys = body.data.shape_keys.key_blocks
    head = [v.index for v in body.data.vertices if v.co.z > h*.88]
    basis = np.array([keys[0].data[i].co[:] for i in head])
    centre = basis.mean(axis=0)
    transforms = {}
    for key in list(keys)[1:]:
        target = np.array([key.data[i].co[:] for i in head])
        u, _, vt = np.linalg.svd((basis-centre).T @ (target-target.mean(axis=0)))
        rotation = vt.T @ u.T
        if np.linalg.det(rotation) < 0:
            vt[-1] *= -1
            rotation = vt.T @ u.T
        transforms[key.name] = rotation, target.mean(axis=0)
    for side, eye in enumerate(centres):
        radius = .011 if child else .012
        vertices, faces, materials = [], [], []
        for row in range(33):
            phi = row*math.pi/32
            for column in range(49):
                theta = column*math.tau/48
                vertices.append(eye+Vector((radius*math.sin(phi)*math.cos(theta), -radius*math.cos(phi), radius*math.sin(phi)*math.sin(theta))))
        for row in range(32):
            for column in range(48):
                n = row*49+column
                faces.append((n,n+49,n+50,n+1))
                angle = (row+.5)*math.pi/32
                materials.append(2 if angle < .20 else 1 if angle < .48 else 0)
        mesh = bpy.data.meshes.new('anatomical_eye')
        mesh.from_pydata(vertices, [], faces)
        for mat in [sclera,iris,pupil]: mesh.materials.append(mat)
        for poly, material in zip(mesh.polygons,materials):
            poly.material_index = material
            poly.use_smooth = True
        obj = bpy.data.objects.new('ep3_human_'+body.name+'_eye_'+str(side), mesh)
        collection.objects.link(obj)
        obj.parent = body
        obj.shape_key_add(name='Basis')
        for name,(rotation,target_centre) in transforms.items():
            key = obj.shape_key_add(name=name, from_mix=False)
            key.value = 0
            for vertex,p in zip(key.data,vertices):
                vertex.co = Vector(rotation @ (np.array(p)-centre)+target_centre)


def replace_existing(collection):
    actors = [o for o in collection.objects if o.type == 'EMPTY' and (o.name in ['kanha','pich','npc_seller','npc_lok','npc_vuthy'] or o.name.startswith('market_resident_'))]
    for root in actors:
        original = next((o for o in root.children if o.name.endswith('_body') and o.type == 'MESH'), None)
        if original and original.get('ep3_anatomy_version') == 2 and not original.get('ep3_finished_human'):
            continue
        name = root.name+'_body'
        old = root.name in ['npc_lok','npc_vuthy','market_resident_0','market_resident_2']
        for obj in list(root.children_recursive)[::-1]: bpy.data.objects.remove(obj,do_unlink=True)
        body = build_body(collection,name,old=old,child=root.name=='pich')
        body.parent = root
        # The source now carries actual child anatomy, rather than a shrunken woman.
        body.scale = (1,1,1)
        print('EP3 human anatomy:',root.name,round(max(v.co.z for v in body.data.vertices),3),'m',flush=True)
