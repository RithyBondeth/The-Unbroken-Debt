"""Add/refresh only the house's dread pass (house_dread.py) in the current village.

blender -b art-source/blender/ep1/ep1_area_village.blend \\
    -P tools/areas/rebuild-house-dread.py -- art-export/ep1/house-dread.glb
npm run assets -- ep1/house-dread.glb
node tools/areas/update-village-glb.mjs public/assets/ep1/ep1_area_village.glb \\
    public/assets/ep1/house-dread.glb art-export/ep1/house-dread.glb.json \\
    public/assets/ep1/ep1_area_village.glb
rm public/assets/ep1/house-dread.glb

Everything it makes is named house_dread_* and nothing collides, so gameplay,
the Krasue's window sightlines and the hunt's navigation are untouched.
"""
import ast
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
source = os.path.join(os.path.dirname(__file__), 'ep1_area_village.py')
with open(source) as stream:
    tree = ast.parse(stream.read())
tree.body = [node for node in tree.body if not (
    isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    and isinstance(node.value.func, ast.Name) and node.value.func.id == 'build')]
ns = {'__file__': source, '__name__': 'house_dread_rebuild'}
exec(compile(tree, source, 'exec'), ns)
coll = bpy.data.collections['ep1_area_village']
ns['AREA'] = coll
ns['rng'] = np.random.default_rng(1910)
ns['lib'], ns['img'] = ns['library_material'], ns['image_material']
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'materials')
dictionary = next(n.value for n in fn.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict))
m = {}
for key, value in zip(dictionary.keys, dictionary.values):
    names = [a.value for a in value.args if isinstance(a, ast.Constant)
             and isinstance(a.value, str) and a.value.startswith('M_')]
    if names and names[0] in bpy.data.materials:
        m[key.value] = bpy.data.materials[names[0]]
    elif names:
        m[key.value] = eval(compile(ast.Expression(value), source, 'eval'), ns)

from house_dread import house_dread
import khmer

# Reuse the library prototypes the blend already holds, rather than importing
# another copy into _protos on every run.
for obj in bpy.data.objects:
    if obj.name.startswith('proto_') and obj.parent is None and '.' not in obj.name:
        khmer._protos.setdefault(obj.name[len('proto_'):], obj)

remove = {o for o in bpy.data.objects if o.name.startswith('house_dread_')}
old_names = sorted(o.name for o in remove)
untouched = {o.name: (o.matrix_world.copy(), o.data) for o in bpy.data.objects if o not in remove}
for obj in remove:
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
# This pass's own materials and atlas are made afresh every time.
for material in list(bpy.data.materials):
    if material.name.split('.')[0].startswith('M_house_detail_dread_'):
        bpy.data.materials.remove(material, do_unlink=True)
made, props = house_dread(coll, m)
created = list(made) + [o for p in props for o in [p] + list(p.children_recursive)]
bpy.context.view_layer.update()
for name, (matrix, data) in untouched.items():
    obj = bpy.data.objects.get(name)
    assert obj and obj.matrix_world == matrix and obj.data == data, f'Unrelated art changed: {name}'
for obj in created:
    assert obj.name.startswith('house_dread_'), obj.name
    assert not obj.name.startswith('col_')
faces = sum(len(o.data.polygons) for o in created if o.type == 'MESH')
assert faces < 150000, f'House dread budget exceeded: {faces}'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f'House dread: {len(created)} nodes, {faces} faces; preserved {len(untouched)} objects.', flush=True)
if '--' in sys.argv:
    destination = sys.argv[sys.argv.index('--') + 1]
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in created:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=destination, export_format='GLB', use_selection=True,
                             export_extras=True, export_yup=True, export_apply=True,
                             export_cameras=False, export_lights=False)
    with open(destination + '.json', 'w') as stream:
        json.dump({'remove': old_names, 'required': sorted(o.name for o in created)}, stream, indent=2)
    print(f'Focused export: {destination}', flush=True)
