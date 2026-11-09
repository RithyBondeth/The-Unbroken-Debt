"""Rebuild only the two ox carts (ox_cart.py) in the current village: the hooded
carriage on the road at arrival and the cart behind the house.

blender -b art-source/blender/ep1/ep1_area_village.blend \\
    -P tools/areas/rebuild-ox-carts.py -- art-export/ep1/ox-carts.glb
npm run assets -- ep1/ox-carts.glb
node tools/areas/update-village-glb.mjs public/assets/ep1/ep1_area_village.glb \\
    public/assets/ep1/ox-carts.glb art-export/ep1/ox-carts.glb.json \\
    public/assets/ep1/ep1_area_village.glb
rm public/assets/ep1/ox-carts.glb
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

import math
import khmer
from khmer import ox_cart

for obj in bpy.data.objects:
    if obj.name.startswith('proto_') and obj.parent is None and '.' not in obj.name:
        khmer._protos.setdefault(obj.name[len('proto_'):], obj)

CARTS = (('carriage', 1.8, ns['ROAD_Y'] + 0.3, math.radians(10), True),
         ('yard_cart', 10.6, 19.6, math.radians(-70), False))
names = tuple(c[0] for c in CARTS)
remove = {o for o in bpy.data.objects if o.name.removeprefix('col_').startswith(names)}
for obj in list(remove):
    remove.update(obj.children_recursive)
old_names = sorted(o.name for o in remove)
untouched = {o.name: (o.matrix_world.copy(), o.data) for o in bpy.data.objects if o not in remove}
for obj in remove:
    bpy.data.objects.remove(obj, do_unlink=True)
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
before = set(bpy.data.objects)
for name, x, y, rot, hood in CARTS:
    ox_cart(coll, m, name, x, y, rot, hood=hood)
created = [o for o in bpy.data.objects if o not in before]
bpy.context.view_layer.update()
for name, (matrix, data) in untouched.items():
    obj = bpy.data.objects.get(name)
    assert obj and obj.matrix_world == matrix and obj.data == data, f'Unrelated art changed: {name}'
for obj in created:
    assert obj.name.removeprefix('col_').startswith(names), obj.name
faces = sum(len(o.data.polygons) for o in created if o.type == 'MESH' and not o.name.startswith('col_'))
assert faces < 120000, f'Ox cart budget exceeded: {faces}'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f'Ox carts: {len(created)} nodes, {faces} faces; preserved {len(untouched)} objects.', flush=True)
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
